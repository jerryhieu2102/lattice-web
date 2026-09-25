from optimizer.model.solver import optimize
from simulation.scenarios.engine import simulate
from tests.factories import state


def test_seeded_sensitivity():
    s = state()
    p = optimize(s)
    assert simulate(s, p, {}, 100)["scenario_failure_rate"] == 0
    stressed = simulate(s, p, {"unexpected_expense": 1000}, 100)
    assert stressed["scenario_failure_rate"] > 0
    assert stressed == simulate(s, p, {"unexpected_expense": 1000}, 100)
    assert sum(x["count"] for x in stressed["histogram"]) == 100


def test_delayed_arrival_excluded():
    s = state()
    s["obligations"][0]["due_date"] = "2026-09-16"
    p = optimize(s)
    assert simulate(s, p, {"transfer_delay": 7}, 100)["scenario_failure_rate"] > 0.5


def test_named_scenarios_apply_shocks_but_respect_explicit_zero():
    from apps.api.schemas import ScenarioInput

    assert ScenarioInput(scenario="SCHOLARSHIP_DELAY").scholarship_delay == 14
    assert ScenarioInput(scenario="FX_STRESS").fx_shock == 5
    assert ScenarioInput(scenario="TRANSFER_DELAY").transfer_delay == 4
    assert ScenarioInput(scenario="COMBINED_STRESS").unexpected_expense == 300
    assert ScenarioInput(scenario="SCHOLARSHIP_DELAY", scholarship_delay=0).scholarship_delay == 0
