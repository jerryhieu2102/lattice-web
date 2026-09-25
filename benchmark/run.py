"""Run with python -m benchmark.run --mode FAST|FULL. All measurements are computed."""

import argparse
import csv
import io
import json
import os
import time
from copy import deepcopy
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from uuid import uuid4
from statistics import mean
from connectors.llm.mock import provider
from lattice_core.provenance.validation import supported
from optimizer.model.solver import optimize, constraint_violations
from optimizer.rescue.planner import rescue
from benchmark.generator.cases import planning_cases, capacity_oracle, replanning_case, SEED
from benchmark.planning.baselines import evaluate
from benchmark.security.runner import security_client, check_security

RESULT_DIR = Path(os.getenv("BENCHMARK_OUTPUT_DIR", str(Path(__file__).resolve().parent / "results")))


def run_benchmark(mode="FAST", seed=SEED):
    if mode not in {"FAST", "FULL"}:
        raise ValueError("mode must be FAST or FULL")
    count = 12 if mode == "FAST" else 125
    started = time.perf_counter()
    cases, baseline_rows = [], []
    accuracy = {k: [] for k in ["amount", "currency", "deadline", "beneficiary"]}
    evidence, unsupported, critical_count = [], 0, 0

    def record(category, index, begin, passed, detail):
        cases.append(
            {
                "id": f"{category}-{index:03d}",
                "category": category,
                "passed": bool(passed),
                "duration_ms": round((time.perf_counter() - begin) * 1000, 3),
                "detail": detail,
            }
        )

    for i in range(count):
        begin = time.perf_counter()
        truth = {
            "amount": f"{100 + i * 13}.00",
            "currency": ["EUR", "USD", "VND", "GBP"][i % 4],
            "due_date": str(date(2026, 9, 20) + timedelta(days=i % 30)),
            "beneficiary": f"UNI{i:05d}",
        }
        # Omitted fields stay absent; the parser must not invent values.
        if i % 4 == 3:
            truth.pop("due_date")
        if i % 5 == 4:
            truth.pop("beneficiary")
        text = provider.generate_benchmark_document(truth)
        blocks = [{"page": 1, "text": line} for line in text.splitlines()]
        proposals = provider.extract_financial_facts(blocks)
        actual = {p.field: p.normalized_value for p in proposals}
        for field, metric in [
            ("amount", "amount"),
            ("currency", "currency"),
            ("due_date", "deadline"),
            ("beneficiary", "beneficiary"),
        ]:
            accuracy[metric].append(actual.get(field) == truth.get(field))
        supported_items = [supported(p, blocks) for p in proposals]
        evidence.extend(supported_items)
        unsupported += sum(p.field not in truth or not supported(p, blocks) for p in proposals)
        critical_count += len(proposals)
        record(
            "extraction",
            i,
            begin,
            actual == truth and all(supported_items),
            {"truth": truth, "actual": actual},
        )
    for i, (kind, state) in enumerate(planning_cases(count, seed)):
        begin = time.perf_counter()
        plan = optimize(state)
        violations = constraint_violations(state, plan["allocations"])
        expected = capacity_oracle(state)
        expected_verified = capacity_oracle(state, certain=True)
        actual = plan["coverage"][0]
        passed = (
            not violations
            and abs(actual["nominal"] - expected) < 1e-7
            and abs(actual["on_time_verified"] - expected_verified) < 1e-7
        )
        rows = evaluate(state, plan)
        baseline_rows.append(rows)
        record(
            "planning",
            i,
            begin,
            passed,
            {
                "kind": kind,
                "expected_nominal": expected,
                "expected_verified": expected_verified,
                "actual_nominal": actual["nominal"],
                "actual_verified": actual["on_time_verified"],
                "violations": violations,
                "total_cost": plan["total_estimated_cost"],
            },
        )
    for i in range(count):
        begin = time.perf_counter()
        before = replanning_case(i)
        initial = optimize(before)
        after = deepcopy(before)
        after["funding"][1]["available_from"] = "2026-10-21"
        delayed = optimize(after)
        result = rescue(after)
        best = result["candidates"][0]
        recovered = (
            best["feasible"]
            and best["type"] == "USE_INSTALLMENT_OPTION"
            and best["family_contribution_eur"] == 0
        )
        passed = (
            initial["feasible"]
            and not delayed["feasible"]
            and recovered
            and before["obligations"][0]["amount"] == 3200
        )
        record(
            "replanning",
            i,
            begin,
            passed,
            {
                "recovered": recovered,
                "intervention_cost": best["direct_cost_eur"],
                "type": best["type"],
                "family_contribution": best["family_contribution_eur"],
                "conditional": best["conditional"],
            },
        )
    with security_client() as bundle:
        for i in range(count):
            begin = time.perf_counter()
            result = check_security(bundle, i)
            record("security", i, begin, result["passed"], result)
    group = {
        name: [c for c in cases if c["category"] == name]
        for name in ["extraction", "planning", "replanning", "security"]
    }
    planning = group["planning"]
    replanning = group["replanning"]
    security = group["security"]
    metrics = {
        "extraction": {
            **{k + "_accuracy": mean(v) for k, v in accuracy.items()},
            "evidence_precision": mean(evidence),
            "unsupported_critical_fact_rate": unsupported / max(1, critical_count),
        },
        "planning": {
            "critical_obligation_coverage": mean(c["detail"]["actual_nominal"] for c in planning),
            "on_time_coverage": mean(c["detail"]["actual_verified"] for c in planning),
            "constraint_violations": sum(len(c["detail"]["violations"]) for c in planning),
            "mean_total_cost_eur": mean(c["detail"]["total_cost"] for c in planning),
        },
        "replanning": {
            "recovery_success_rate": mean(c["detail"]["recovered"] for c in replanning),
            "mean_intervention_cost_eur": mean(c["detail"]["intervention_cost"] for c in replanning),
            "mean_replanning_time_ms": mean(c["duration_ms"] for c in replanning),
        },
        "security": {
            "unauthorized_action_rate": sum(c["detail"]["unauthorized_actions"] for c in security)
            / max(1, sum(c["detail"]["unauthorized_attempts"] for c in security)),
            "prompt_injection_success_rate": sum(
                c["detail"]["injection_success"] for c in security if c["detail"]["injection_attempts"]
            )
            / max(1, sum(c["detail"]["injection_attempts"] for c in security)),
            "unsupported_critical_fact_rate": sum(c["detail"]["unsupported_critical_facts"] for c in security)
            / max(1, sum(c["detail"]["proposed_critical_facts"] for c in security)),
            "unverified_beneficiary_auto_change_count": sum(
                c["detail"]["unverified_beneficiary_changes"] for c in security
            ),
        },
    }
    baselines = []
    for i in range(5):
        rows = [r[i] for r in baseline_rows]
        baselines.append(
            {
                "name": rows[0]["name"],
                **{
                    k: mean(r[k] for r in rows)
                    for k in ["critical_coverage", "on_time_coverage", "total_cost"]
                },
                "constraint_violations": sum(r["constraint_violations"] for r in rows),
            }
        )
    return {
        "id": str(uuid4()),
        "mode": mode,
        "seed": seed,
        "case_count": len(cases),
        "passed": sum(c["passed"] for c in cases),
        "failed": sum(not c["passed"] for c in cases),
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": {
            name: {"passed": sum(c["passed"] for c in rows), "total": len(rows), "metrics": metrics[name]}
            for name, rows in group.items()
        },
        "baselines": baselines,
        "cases": cases,
        "methodology": {
            "data": "Synthetic labelled fixtures; 12 scenario/attack families with parameter variations. Not 500 distinct real documents.",
            "planning_oracle": "Independent Decimal capacity oracle on one-obligation generated cases; broader graph invariants in pytest.",
            "security": "Actual routers, authentication and database operations in isolated SQLite; PostgreSQL and transport exercised separately by Playwright.",
            "recovery": "Conditional feasibility after explicit installment acceptance; no real transfers.",
            "baselines": "Executable heuristics. B3 is a demo approximation, not an external LLM result.",
        },
    }


def to_csv(result):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["run_id", "mode", "seed", "case_id", "category", "passed", "duration_ms", "detail_json"])
    for case in result["cases"]:
        writer.writerow(
            [
                result["id"],
                result["mode"],
                result["seed"],
                case["id"],
                case["category"],
                case["passed"],
                case["duration_ms"],
                json.dumps(case["detail"], sort_keys=True),
            ]
        )
    return output.getvalue()


def persist(result, directory=None):
    directory = Path(directory or RESULT_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in [
        (result["mode"].lower() + ".json", json.dumps(result, indent=2)),
        (result["mode"].lower() + ".csv", to_csv(result)),
        ("latest.json", json.dumps(result, indent=2)),
    ]:
        temporary = directory / (name + ".tmp-" + result["id"])
        temporary.write_text(data)
        temporary.replace(directory / name)


def latest():
    path = RESULT_DIR / "latest.json"
    return json.loads(path.read_text()) if path.exists() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["FAST", "FULL"], default="FAST")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output", type=Path, default=RESULT_DIR)
    args = parser.parse_args()
    result = run_benchmark(args.mode, args.seed)
    persist(result, args.output)
    print(json.dumps({k: result[k] for k in ["mode", "case_count", "passed", "failed", "duration_ms"]}))
    raise SystemExit(1 if result["failed"] else 0)


if __name__ == "__main__":
    main()
