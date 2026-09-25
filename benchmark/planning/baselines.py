"""Executable, deliberately simple baselines. They are not external LLM evaluations."""

from datetime import timedelta
from math import floor, ceil
from optimizer.model.solver import day, SCALE, BASE_RATE, coverage_for, constraint_violations, optimize

NAMES = [
    "B0 balance-only",
    "B1 earliest-deadline greedy",
    "B2 cheapest-route greedy",
    "B3 generic planner approximation (demo)",
    "B4 full LATTICE",
]


def greedy(state, baseline):
    available = {f["id"]: float(f["amount"]) for f in state["funding"]}
    allocations = []
    obligations = sorted(state["obligations"], key=lambda o: o["due_date"])
    for o in obligations:
        remaining = float(o["amount"])
        for f in state["funding"]:
            routes = [
                r
                for r in state["routes"]
                if r["from_currency"] == f["currency"] and r["to_currency"] == o["currency"]
            ]
            if not routes:
                continue
            if baseline == 2:
                routes.sort(key=lambda r: r["fixed_fee"] * BASE_RATE[f["currency"]])
            elif baseline in {1, 3}:
                routes.sort(key=lambda r: r["settlement_p95_days"])
            r = routes[0]
            if baseline == 3 and (
                f["restriction_type"] != "UNRESTRICTED"
                or f["verification_status"] not in {"USER_CONFIRMED", "SOURCE_VERIFIED"}
            ):
                continue
            rate = r["fx_rate"] * (1 - r["fx_markup"])
            budget = available[f["id"]]
            fixed = 0 if baseline == 0 else r["fixed_fee"]
            pct = 0 if baseline == 0 else r["percentage_fee"]
            principal = min(remaining / rate, max(0, (budget - fixed) / (1 + pct)))
            principal = floor((principal + 1e-8) * SCALE[f["currency"]]) / SCALE[f["currency"]]
            destination = min(
                remaining, floor((principal * rate + 1e-8) * SCALE[o["currency"]]) / SCALE[o["currency"]]
            )
            if destination <= 0:
                continue
            fee = fixed + ceil(principal * pct * SCALE[f["currency"]]) / SCALE[f["currency"]]
            scheduled = max(day(state["as_of"]), day(f["available_from"]))
            allocations.append(
                dict(
                    funding_source_id=f["id"],
                    obligation_id=o["id"],
                    transfer_route_id=r["id"],
                    source_amount=principal,
                    destination_amount=destination,
                    source_currency=f["currency"],
                    currency=o["currency"],
                    estimated_fee=fee,
                    scheduled_date=str(scheduled),
                    expected_arrival_date=str(scheduled + timedelta(days=r["settlement_p95_days"])),
                )
            )
            available[f["id"]] -= principal + fee
            remaining = round(remaining - destination, 2)
    return allocations


def evaluate(state, full_plan=None):
    rows = []
    for i, name in enumerate(NAMES):
        allocations = (full_plan or optimize(state))["allocations"] if i == 4 else greedy(state, i)
        coverage = coverage_for(state, allocations)
        critical = [c for c in coverage if c["priority"] == "CRITICAL" and c["in_horizon"]]
        nominal = sum(c["nominal"] for c in critical) / max(1, len(critical))
        ontime = sum(c["on_time_verified"] for c in critical) / max(1, len(critical))
        violations = constraint_violations(state, allocations)
        rows.append(
            {
                "name": name,
                "critical_coverage": nominal,
                "on_time_coverage": ontime,
                "constraint_violations": len(violations),
                "total_cost": sum(a["estimated_fee"] * BASE_RATE[a["source_currency"]] for a in allocations),
            }
        )
    return rows
