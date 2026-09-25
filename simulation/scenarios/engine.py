"""Seeded scenario sensitivity, not an actuarial probability model."""

from copy import deepcopy
from datetime import timedelta
import numpy as np
from optimizer.model.solver import day, coverage_for, BASE_RATE


def simulate(state, plan, parameters, iterations=1000, seed=17):
    rng = np.random.default_rng(seed)
    critical = {
        o["id"]: o
        for o in state["obligations"]
        if o["priority"] == "CRITICAL"
        and o["status"] == "OPEN"
        and day(o["due_date"]) <= day(plan["horizon_end"])
    }
    funding = {f["id"]: f for f in state["funding"]}
    fails, forecast_fails, shortfalls = 0, 0, []
    for _ in range(iterations):
        transfer = int(rng.integers(0, parameters.get("transfer_delay", 0) + 1))
        scholarship = int(rng.integers(0, parameters.get("scholarship_delay", 0) + 1))
        fx = float(rng.uniform(0, parameters.get("fx_shock", 0))) / 100
        expense = float(rng.uniform(0, parameters.get("unexpected_expense", 0)))
        allocations = deepcopy(plan["allocations"])
        for a in allocations:
            f = funding[a["funding_source_id"]]
            delay = transfer + (scholarship if f["source_type"] == "SCHOLARSHIP" else 0)
            a["expected_arrival_date"] = str(day(a["expected_arrival_date"]) + timedelta(days=delay))
            if f["currency"] != a["currency"]:
                a["destination_amount"] *= 1 - fx
            if f["id"] in parameters.get("funding_cancellation", []):
                a["destination_amount"] = 0
        coverage = coverage_for(state, allocations)
        guaranteed_miss = sum(
            c["shortfall"] * BASE_RATE[c["currency"]] for c in coverage if c["obligation_id"] in critical
        )
        nominal_miss = sum(
            max(
                0,
                float(o["amount"])
                - sum(
                    a["destination_amount"]
                    for a in allocations
                    if a["obligation_id"] == o["id"] and day(a["expected_arrival_date"]) <= day(o["due_date"])
                ),
            )
            * BASE_RATE[o["currency"]]
            for o in critical.values()
        )
        buffer = sum(v * BASE_RATE[k] for k, v in plan.get("safe_to_spend", {}).items())
        expense_gap = max(0, expense - buffer)
        guaranteed_miss += expense_gap
        nominal_miss += expense_gap
        fails += guaranteed_miss > 0.005
        forecast_fails += nominal_miss > 0.005
        shortfalls.append(guaranteed_miss)
    worst = deepcopy(plan["allocations"])
    for a in worst:
        f = funding[a["funding_source_id"]]
        delay = parameters.get("transfer_delay", 0) + (
            parameters.get("scholarship_delay", 0) if f["source_type"] == "SCHOLARSHIP" else 0
        )
        a["expected_arrival_date"] = str(day(a["expected_arrival_date"]) + timedelta(days=delay))
        if f["currency"] != a["currency"]:
            a["destination_amount"] *= 1 - parameters.get("fx_shock", 0) / 100
        if f["id"] in parameters.get("funding_cancellation", []):
            a["destination_amount"] = 0
    after = coverage_for(state, worst)
    for c in after:
        c["on_time_nominal"] = min(
            1,
            sum(
                a["destination_amount"]
                for a in worst
                if a["obligation_id"] == c["obligation_id"]
                and day(a["expected_arrival_date"]) <= day(c["due_date"])
            )
            / c["amount"],
        )
    return {
        "after_coverage": after,
        "scenario_failure_rate": fails / iterations,
        "forecast_failure_rate": forecast_fails / iterations,
        "mean_shortfall_eur": round(float(np.mean(shortfalls)), 2),
        "p95_shortfall_eur": round(float(np.quantile(shortfalls, 0.95)), 2),
        "iterations": iterations,
        "seed": seed,
        "parameters": parameters,
        "baseline_coverage": plan["coverage"],
        "label": "Seeded sensitivity analysis; not a real-world probability",
        "histogram": [
            {"bucket": f"{int(lo)}–{int(hi)}", "count": int(n)} for n, lo, hi in zip(*_histogram(shortfalls))
        ],
    }


def _histogram(values):
    counts, edges = np.histogram(values, bins=8)
    return counts, edges[:-1], edges[1:]
