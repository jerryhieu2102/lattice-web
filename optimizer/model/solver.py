"""Deterministic integer CP-SAT planner. No model-provider code is imported here."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR, ROUND_CEILING
from fractions import Fraction
from ortools.sat.python import cp_model
from lattice_core.currencies import SCALE, BASE_RATE

VERIFIED = {"USER_CONFIRMED", "SOURCE_VERIFIED"}
CERTAIN = {"AVAILABLE", "PLANNED"}


def minor(amount, currency):
    return int((Decimal(str(amount)) * SCALE[currency]).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def day(value):
    return date.fromisoformat(str(value)[:10])


def verified(source):
    return source["verification_status"] in VERIFIED and source["availability_status"] in CERTAIN


def usable(source, verified_only=False):
    return (
        source["availability_status"] in {"AVAILABLE", "PLANNED", "EXPECTED", "CONDITIONAL"}
        and source["verification_status"] in VERIFIED
        and (source.get("owner_type") not in {"PARENT", "SPONSOR"} or source.get("authorized", False))
        and (not verified_only or verified(source))
    )


def optimize(state, verified_only=False):
    today = day(state["as_of"])
    horizon = today + timedelta(days=state.get("horizon_days", 45))
    funds, routes = state["funding"], state["routes"]
    obligations = [o for o in state["obligations"] if o["status"] == "OPEN" and day(o["due_date"]) <= horizon]
    model = cp_model.CpModel()
    candidates = []
    for f in funds:
        if not usable(f, verified_only):
            continue
        capacity = minor(f["amount"], f["currency"]) - minor(f["minimum_remaining_balance"], f["currency"])
        if f["restriction_type"] == "EMERGENCY" or capacity <= 0:
            continue
        for o in obligations:
            if (
                o["verification_status"] not in VERIFIED
                or o.get("security_hold")
                or (not o.get("beneficiary_verified") and not o.get("budget_only", False))
            ):
                continue
            if f["restriction_type"] == "TUITION_ONLY" and o["type"] != "TUITION":
                continue
            for r in routes:
                if (
                    r["availability"] != "AVAILABLE"
                    or r["verification_status"] not in VERIFIED
                    or r["from_currency"] != f["currency"]
                    or r["to_currency"] != o["currency"]
                ):
                    continue
                scheduled = max(today, day(f["available_from"]))
                arrival = scheduled + timedelta(days=r["settlement_p95_days"])
                if arrival > day(o["due_date"]):
                    continue
                rate = (
                    Fraction(str(r["fx_rate"]))
                    * (1 - Fraction(str(r["fx_markup"])))
                    * Fraction(SCALE[o["currency"]], SCALE[f["currency"]])
                )
                # Conservatively quantize the minor-unit quote to keep CP-SAT coefficients in int64.
                rate = Fraction((rate * 1000000).__floor__(), 1000000)
                if rate <= 0:
                    continue
                percent = Fraction(str(r["percentage_fee"]))
                max_p = min(
                    capacity,
                    (minor(o["amount"], o["currency"]) * rate.denominator + rate.numerator - 1)
                    // rate.numerator,
                    int(
                        (Decimal(str(r["max_transfer"])) * SCALE[f["currency"]]).to_integral_value(
                            rounding=ROUND_FLOOR
                        )
                    ),
                )
                if max_p <= 0:
                    continue
                active = model.new_bool_var("route_used")
                principal = model.new_int_var(0, max_p, "principal")
                proportional = model.new_int_var(0, capacity, "variable_fee")
                destination = model.new_int_var(0, minor(o["amount"], o["currency"]), "destination")
                fixed = int(
                    (Decimal(str(r["fixed_fee"])) * SCALE[f["currency"]]).to_integral_value(
                        rounding=ROUND_CEILING
                    )
                )
                model.add(
                    principal
                    >= max(
                        1,
                        int(
                            (Decimal(str(r["min_transfer"])) * SCALE[f["currency"]]).to_integral_value(
                                rounding=ROUND_CEILING
                            )
                        ),
                    )
                    * active
                )
                model.add(principal <= max_p * active)
                model.add(proportional * percent.denominator >= principal * percent.numerator)
                model.add(
                    proportional * percent.denominator
                    <= principal * percent.numerator + percent.denominator - 1
                )
                model.add(destination * rate.denominator <= principal * rate.numerator)
                # Fixed-output quote: round source debit up to fund the requested destination minor units.
                # Any conversion residue is disclosed as rounding cost, never created as destination money.
                model.add(destination * rate.denominator >= (principal - active) * rate.numerator + active)
                model.add(destination >= active)
                candidates.append(
                    dict(
                        f=f,
                        o=o,
                        r=r,
                        p=principal,
                        d=destination,
                        fee=proportional + fixed * active,
                        used=active,
                        scheduled=scheduled,
                        arrival=arrival,
                    )
                )
        model.add(sum(c["p"] + c["fee"] for c in candidates if c["f"]["id"] == f["id"]) <= capacity)
    missing = {}
    for o in obligations:
        required = minor(o["amount"], o["currency"])
        slack = model.new_int_var(0, required, "uncovered")
        model.add(sum(c["d"] for c in candidates if c["o"]["id"] == o["id"]) + slack == required)
        missing[o["id"]] = slack
    # Lexicographic stages ensure fees can NEVER outweigh a critical commitment.
    groups = ["CRITICAL", "HIGH", "NORMAL", "OPTIONAL"]
    goals = []
    for priority in groups:
        goals.append(
            sum(
                missing[o["id"]] * max(1, int(BASE_RATE[o["currency"]] * 1000000 / SCALE[o["currency"]]))
                for o in obligations
                if o["priority"] == priority
            )
        )
        goals.append(
            sum(c["d"] for c in candidates if c["o"]["priority"] == priority and not verified(c["f"]))
        )
    goals += [
        sum(c["used"] * max(0, 2 - (day(c["o"]["due_date"]) - c["arrival"]).days) for c in candidates),
        sum(
            (c["p"] + c["fee"])
            * max(1, int(BASE_RATE[c["f"]["currency"]] * 1000000 / SCALE[c["f"]["currency"]]))
            for c in candidates
        ),
    ]
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 17
    solver.parameters.max_time_in_seconds = state.get("solver_timeout_seconds", 5)
    all_optimal = True
    for goal in goals:
        model.minimize(goal)
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return {
                "allocations": [],
                "coverage": coverage_for(state, []),
                "solver_status": solver.status_name(status),
                "feasible": False,
                "verified_feasible": False,
                "objective_value": sum(
                    float(o["amount"]) * BASE_RATE[o["currency"]]
                    for o in obligations
                    if o["priority"] == "CRITICAL"
                ),
                "total_estimated_cost": 0,
                "constraint_violations": 0,
                "horizon_end": horizon.isoformat(),
                "safe_to_spend": {},
                "error": "No verified solver result; no allocation emitted.",
            }
        all_optimal = all_optimal and status == cp_model.OPTIMAL
        model.add(goal == int(solver.value(goal)))
    allocations = []
    for c in candidates:
        if solver.value(c["p"]) == 0:
            continue
        allocations.append(
            dict(
                funding_source_id=c["f"]["id"],
                obligation_id=c["o"]["id"],
                transfer_route_id=c["r"]["id"],
                source_amount=solver.value(c["p"]) / SCALE[c["f"]["currency"]],
                destination_amount=solver.value(c["d"]) / SCALE[c["o"]["currency"]],
                estimated_fee=solver.value(c["fee"]) / SCALE[c["f"]["currency"]],
                source_currency=c["f"]["currency"],
                currency=c["o"]["currency"],
                estimated_fx_cost_eur=round(
                    solver.value(c["p"])
                    / SCALE[c["f"]["currency"]]
                    * float(c["r"]["fx_rate"])
                    * float(c["r"]["fx_markup"])
                    * BASE_RATE[c["o"]["currency"]],
                    6,
                ),
                estimated_rounding_cost_eur=round(
                    max(
                        0,
                        solver.value(c["p"])
                        / SCALE[c["f"]["currency"]]
                        * float(c["r"]["fx_rate"])
                        * (1 - float(c["r"]["fx_markup"]))
                        - solver.value(c["d"]) / SCALE[c["o"]["currency"]],
                    )
                    * BASE_RATE[c["o"]["currency"]],
                    8,
                ),
                scheduled_date=c["scheduled"].isoformat(),
                expected_arrival_date=c["arrival"].isoformat(),
                verified=verified(c["f"]),
                status="VERIFIED" if verified(c["f"]) else "EXPECTED",
            )
        )
    errors = constraint_violations(state, allocations)
    if errors:
        raise RuntimeError(f"Post-solve hard constraint validation failed: {errors}")
    coverage = coverage_for(state, allocations)
    critical = [c for c in coverage if c["priority"] == "CRITICAL" and c["in_horizon"]]
    cost = round(
        sum(
            a["estimated_fee"] * BASE_RATE[a["source_currency"]]
            + a["estimated_fx_cost_eur"]
            + a["estimated_rounding_cost_eur"]
            for a in allocations
        ),
        2,
    )
    return dict(
        allocations=allocations,
        coverage=coverage,
        feasible=all(c["nominal"] >= 1 for c in critical),
        verified_feasible=all(c["on_time_verified"] >= 1 for c in critical),
        solver_status="OPTIMAL" if all_optimal else "FEASIBLE",
        objective_value=round(sum(c["shortfall"] * BASE_RATE[c["currency"]] for c in critical), 2),
        total_estimated_cost=cost,
        constraint_violations=0,
        horizon_end=horizon.isoformat(),
        safe_to_spend=safe_to_spend(state, allocations),
    )


def coverage_for(state, allocations):
    result = []
    horizon = day(state["as_of"]) + timedelta(days=state.get("horizon_days", 45))
    lookup = {f["id"]: f for f in state["funding"]}
    for o in state["obligations"]:
        if o["status"] != "OPEN":
            continue
        matches = [a for a in allocations if a["obligation_id"] == o["id"]]
        amount = Decimal(str(o["amount"]))
        nominal = sum((Decimal(str(a["destination_amount"])) for a in matches), Decimal(0))
        verified_amount = sum(
            (
                Decimal(str(a["destination_amount"]))
                for a in matches
                if verified(lookup[a["funding_source_id"]])
            ),
            Decimal(0),
        )
        ontime = sum(
            (
                Decimal(str(a["destination_amount"]))
                for a in matches
                if verified(lookup[a["funding_source_id"]])
                and day(a["expected_arrival_date"]) <= day(o["due_date"])
            ),
            Decimal(0),
        )
        result.append(
            dict(
                obligation_id=o["id"],
                type=o["type"],
                label=o["label"],
                amount=float(amount),
                currency=o["currency"],
                due_date=o["due_date"],
                priority=o["priority"],
                nominal=float(min(1, nominal / amount)),
                verified=float(min(1, verified_amount / amount)),
                on_time_verified=float(min(1, ontime / amount)),
                shortfall=float(round(max(0, amount - ontime), 2)),
                forecast_shortfall=float(round(max(0, amount - nominal), 2)),
                in_horizon=day(o["due_date"]) <= horizon,
            )
        )
    return result


def safe_to_spend(state, allocations):
    result = {}
    for f in state["funding"]:
        if (
            not verified(f)
            or f["availability_status"] != "AVAILABLE"
            or f.get("owner_type") != "STUDENT"
            or f["restriction_type"] != "UNRESTRICTED"
            or day(f["available_from"]) > day(state["as_of"])
        ):
            continue
        protected = sum(
            a["source_amount"] + a["estimated_fee"] for a in allocations if a["funding_source_id"] == f["id"]
        )
        result[f["currency"]] = round(
            result.get(f["currency"], 0)
            + max(0, float(f["amount"]) - protected - float(f["minimum_remaining_balance"])),
            2,
        )
    return result


def constraint_violations(state, allocations):
    errors = []
    funds = {f["id"]: f for f in state["funding"]}
    obligations = {o["id"]: o for o in state["obligations"]}
    routes = {r["id"]: r for r in state["routes"]}
    for a in allocations:
        f, o, r = (
            funds[a["funding_source_id"]],
            obligations[a["obligation_id"]],
            routes[a["transfer_route_id"]],
        )
        p = Decimal(str(a["source_amount"]))
        if p <= 0 or a["destination_amount"] <= 0 or a["estimated_fee"] < 0:
            errors.append("invalid_amount")
        if (
            o["verification_status"] not in VERIFIED
            or (not o.get("beneficiary_verified") and not o.get("budget_only", False))
            or o.get("security_hold")
            or o["status"] != "OPEN"
        ):
            errors.append("unverified_obligation")
        if r["verification_status"] not in VERIFIED or r["availability"] != "AVAILABLE":
            errors.append("unverified_route")
        if not usable(f) or f["restriction_type"] == "EMERGENCY":
            errors.append("permission_or_reserve")
        if f["restriction_type"] == "TUITION_ONLY" and o["type"] != "TUITION":
            errors.append("restricted_source")
        if (r["from_currency"], r["to_currency"]) != (f["currency"], o["currency"]):
            errors.append("currency_mismatch")
        if not Decimal(str(r["min_transfer"])) <= p <= Decimal(str(r["max_transfer"])):
            errors.append("route_bounds")
        if (
            day(a["scheduled_date"]) < max(day(state["as_of"]), day(f["available_from"]))
            or day(a["expected_arrival_date"])
            != day(a["scheduled_date"]) + timedelta(days=r["settlement_p95_days"])
            or day(a["expected_arrival_date"]) > day(o["due_date"])
        ):
            errors.append("deadline")
        actual = p * Decimal(str(r["fx_rate"])) * (1 - Decimal(str(r["fx_markup"])))
        if Decimal(str(a["destination_amount"])) > actual:
            errors.append("created_money")
        expected_fee = Decimal(str(r["fixed_fee"])) + p * Decimal(str(r["percentage_fee"]))
        if Decimal(str(a["estimated_fee"])) < expected_fee:
            errors.append("undercharged_fee")
    for f in funds.values():
        used = sum(
            Decimal(str(a["source_amount"])) + Decimal(str(a["estimated_fee"]))
            for a in allocations
            if a["funding_source_id"] == f["id"]
        )
        if used > Decimal(str(f["amount"])) - Decimal(str(f["minimum_remaining_balance"])):
            errors.append("source_overspend")
    for o in obligations.values():
        paid = sum(
            Decimal(str(a["destination_amount"])) for a in allocations if a["obligation_id"] == o["id"]
        )
        if paid > Decimal(str(o["amount"])):
            errors.append("overpayment")
    return errors
