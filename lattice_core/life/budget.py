"""Conservative spend capacity: preserve verified plans, reserves and active commitments.

Only remaining, owned, available money can be spent. Future dates are conditional on the
recorded state remaining unchanged. Routes use their actual demo quotes and p95 timing.
"""

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from lattice_core.currencies import BASE_RATE, SCALE
from optimizer.model.solver import optimize, day, verified


def dec(n):
    return Decimal(str(n))


def ceil_minor(n, currency):
    return (dec(n) * SCALE[currency]).to_integral_value(rounding=ROUND_CEILING) / SCALE[currency]


def quote_debit(state, fund, amount, currency, spend_date):
    """Smallest source debit for a fixed destination. None means no timely valid route."""
    choices = []
    for r in state["routes"]:
        if (
            (r["from_currency"], r["to_currency"]) != (fund["currency"], currency)
            or r["availability"] != "AVAILABLE"
            or r["verification_status"] not in {"USER_CONFIRMED", "SOURCE_VERIFIED"}
        ):
            continue
        if max(day(state["as_of"]), day(fund["available_from"])) + timedelta(
            days=r["settlement_p95_days"]
        ) > day(spend_date):
            continue
        rate = dec(r["fx_rate"]) * (1 - dec(r["fx_markup"]))
        if rate <= 0:
            continue
        principal = ceil_minor(dec(amount) / rate, fund["currency"])
        if not dec(r["min_transfer"]) <= principal <= dec(r["max_transfer"]):
            continue
        fee = ceil_minor(dec(r["fixed_fee"]) + principal * dec(r["percentage_fee"]), fund["currency"])
        choices.append((principal + fee, r["id"], fee))
    return min(choices, default=None)


def eligible(f, when):
    return (
        f.get("owner_type") == "STUDENT"
        and verified(f)
        and f["availability_status"] == "AVAILABLE"
        and f["restriction_type"] == "UNRESTRICTED"
        and day(f["available_from"]) <= day(when)
    )


def metrics(state, plan):
    coverage = [c for c in plan["coverage"] if c["in_horizon"] and c["priority"] in {"CRITICAL", "HIGH"}]
    total = sum(c["amount"] * BASE_RATE[c["currency"]] for c in coverage)
    shortfall = sum(c["shortfall"] * BASE_RATE[c["currency"]] for c in coverage)
    return {
        "plan_state": "SAFE" if shortfall < 0.005 else "AT_RISK",
        "verified_coverage": 1 if not total else max(0, 1 - shortfall / total),
        "shortfall_eur": round(shortfall, 2),
        "reserve_eur": round(
            sum(
                (
                    float(f["amount"])
                    if f["restriction_type"] == "EMERGENCY"
                    else float(f["minimum_remaining_balance"])
                )
                * BASE_RATE[f["currency"]]
                for f in state["funding"]
                if f.get("owner_type") == "STUDENT"
            ),
            2,
        ),
        "liquid_eur": round(
            sum(
                float(f["amount"]) * BASE_RATE[f["currency"]]
                for f in state["funding"]
                if eligible(f, state["as_of"])
            ),
            2,
        ),
        "coverage": plan["coverage"],
    }


def budget(state, currency="EUR", active_allocations=None):
    copy = deepcopy(state)
    copy["horizon_days"] = 365
    plan = optimize(copy, verified_only=True)
    snapshot = metrics(copy, plan)
    today = day(state["as_of"])
    ends = [
        today,
        today + timedelta(days=6 - today.weekday()),
        (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
    ]
    protected = {}
    for allocations in (plan["allocations"], active_allocations or []):
        totals = {}
        for a in allocations:
            key = a["funding_source_id"]
            totals[key] = totals.get(key, Decimal(0)) + dec(a["source_amount"]) + dec(a["estimated_fee"])
        for key, total in totals.items():
            protected[key] = max(protected.get(key, Decimal(0)), total)
    values = []
    for when in ends:
        capacity = Decimal(0)
        if snapshot["plan_state"] == "SAFE":
            for f in copy["funding"]:
                if not eligible(f, when):
                    continue
                remaining = max(
                    Decimal(0),
                    dec(f["amount"])
                    - dec(f["minimum_remaining_balance"])
                    - protected.get(f["id"], Decimal(0)),
                )
                outputs = []
                for r in copy["routes"]:
                    if (
                        (r["from_currency"], r["to_currency"]) != (f["currency"], currency)
                        or r["availability"] != "AVAILABLE"
                        or r["verification_status"] not in {"SOURCE_VERIFIED", "USER_CONFIRMED"}
                    ):
                        continue
                    if max(today, day(f["available_from"])) + timedelta(days=r["settlement_p95_days"]) > when:
                        continue
                    principal = min(
                        dec(r["max_transfer"]),
                        (remaining - dec(r["fixed_fee"])) / (1 + dec(r["percentage_fee"])),
                    )
                    principal = (principal * SCALE[f["currency"]]).to_integral_value(
                        rounding=ROUND_FLOOR
                    ) / SCALE[f["currency"]]
                    if principal <= 0 or principal < dec(r["min_transfer"]):
                        continue
                    output = (
                        principal * dec(r["fx_rate"]) * (1 - dec(r["fx_markup"])) * SCALE[currency]
                    ).to_integral_value(rounding=ROUND_FLOOR) / SCALE[currency]
                    check = quote_debit(copy, f, output, currency, when)
                    if check and check[0] <= remaining:
                        outputs.append(output)
                capacity += max(outputs, default=Decimal(0))
        values.append(float(capacity))
    return {
        "currency": currency,
        "today": values[0],
        "this_week": values[1],
        "this_month": values[2],
        "dates": [d.isoformat() for d in ends],
        "horizon_days": 365,
        "committed_eur": round(
            sum(
                float(v) * BASE_RATE[next(f["currency"] for f in copy["funding"] if f["id"] == k)]
                for k, v in protected.items()
            ),
            2,
        ),
        "pending_events": len(state.get("pending_life_events", [])),
        "explanation": "Verified critical and essential commitments are protected for 365 days. Expected income and emergency reserves are excluded. Future budgets assume recorded funds remain available. Demo FX routes and fees apply.",
        **snapshot,
    }


def runway(state):
    copy = deepcopy(state)
    copy["horizon_days"] = 365
    today = day(state["as_of"])
    verified_plan = optimize(copy, verified_only=True)
    forecast = optimize(copy)

    def bound(plan, key):
        gaps = sorted(
            [
                c
                for c in plan["coverage"]
                if c["in_horizon"] and c["priority"] in {"CRITICAL", "HIGH"} and c[key] < 1
            ],
            key=lambda c: c["due_date"],
        )
        return {
            "days": max(0, (day(gaps[0]["due_date"]) - today).days) if gaps else 365,
            "bounded": not bool(gaps),
            "first_gap": gaps[0] if gaps else None,
        }

    critical = sorted(
        [c for c in verified_plan["coverage"] if c["priority"] == "CRITICAL"], key=lambda c: c["due_date"]
    )
    return {
        "verified": bound(verified_plan, "on_time_verified"),
        "including_expected": bound(forecast, "nominal"),
        "next_critical": critical[0] if critical else None,
        "horizon_days": 365,
        "limitation": "Runway covers recorded essential commitments only. Unrecorded daily living costs can shorten it. Expected funding is conditional, not guaranteed.",
    }
