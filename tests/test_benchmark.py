import csv
import io
import json
from benchmark.run import run_benchmark, persist, to_csv
from benchmark.generator.cases import planning_cases, capacity_oracle
from optimizer.model.solver import optimize


def test_benchmark_computes_and_persists_all_48_cases(tmp_path):
    result = run_benchmark("FAST")
    assert result["case_count"] == 48
    assert result["passed"] == 48, [c for c in result["cases"] if not c["passed"]]
    assert result["failed"] == 0
    assert all(c["duration_ms"] > 0 for c in result["cases"])
    assert result["baselines"][4]["constraint_violations"] == 0
    assert result["baselines"][0]["constraint_violations"] > 0
    assert result["categories"]["planning"]["metrics"]["on_time_coverage"] < 1
    assert result["categories"]["security"]["metrics"]["unauthorized_action_rate"] == 0
    persist(result, tmp_path)
    assert json.loads((tmp_path / "latest.json").read_text()) == result
    assert len(list(csv.DictReader(io.StringIO(to_csv(result))))) == 48
    assert (tmp_path / "fast.csv").exists()


def test_independent_oracle_tracks_changed_input():
    _, state = next(planning_cases(1))
    first = capacity_oracle(state)
    state["funding"][0]["amount"] = 0
    assert first > 0
    assert capacity_oracle(state) == 0
    assert optimize(state)["coverage"][0]["nominal"] == 0
