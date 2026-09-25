from copy import deepcopy
import pytest
from optimizer.model.solver import optimize, constraint_violations
from tests.factories import state


@pytest.mark.parametrize(
    "available,owed,coverage", [(500, 1000, 0.5), (1000, 1000, 1), (1200, 1000, 1), (0, 1000, 0)]
)
def test_funding_levels(available, owed, coverage):
    s = state(available, owed)
    p = optimize(s)
    assert p["coverage"][0]["on_time_verified"] == coverage
    assert not constraint_violations(s, p["allocations"])


def test_reserve_never_spent():
    s = state(1200)
    s["funding"][0]["minimum_remaining_balance"] = 600
    assert optimize(s)["coverage"][0]["nominal"] == 0.6
    s["funding"][0]["restriction_type"] = "EMERGENCY"
    assert not optimize(s)["allocations"]


def test_parent_needs_authority():
    s = state()
    s["funding"][0].update(owner_type="PARENT", authorized=False)
    assert not optimize(s)["allocations"]


def test_expected_not_verified():
    s = state()
    s["funding"][0]["availability_status"] = "EXPECTED"
    p = optimize(s)
    assert p["coverage"][0]["nominal"] == 1
    assert p["coverage"][0]["verified"] == 0
    assert not optimize(s, verified_only=True)["allocations"]


def test_delayed_scholarship():
    s = state()
    s["funding"][0]["available_from"] = "2026-10-02"
    assert not optimize(s)["allocations"]


def test_tomorrow_fast_vs_slow():
    s = state(1100)
    s["obligations"][0]["due_date"] = "2026-09-17"
    cheap = s["routes"][0]
    cheap["settlement_p95_days"] = 4
    fast = dict(cheap, id="fast", fixed_fee=20, settlement_p95_days=1)
    s["routes"].append(fast)
    p = optimize(s)
    assert p["allocations"][0]["transfer_route_id"] == "fast"
    assert p["total_estimated_cost"] == 20


def test_currency_and_fees():
    s = state(30000000, 1000)
    s["funding"][0]["currency"] = "VND"
    s["routes"][0].update(
        from_currency="VND", fx_rate=0.000036, fixed_fee=50000, percentage_fee=0.002, max_transfer=50000000
    )
    p = optimize(s)
    assert p["feasible"]
    assert not constraint_violations(s, p["allocations"])


def test_route_min_max_and_impossible():
    s = state(1000)
    s["routes"][0].update(min_transfer=1100)
    assert not optimize(s)["allocations"]
    s["routes"][0].update(min_transfer=0, max_transfer=500)
    assert optimize(s)["coverage"][0]["nominal"] == 0.5


def test_installment_defers_but_does_not_delete_debt():
    s = state(1600, 3200)
    s["obligations"][0]["amount"] = 1600
    s["obligations"].append(dict(s["obligations"][0], id="o2", due_date="2026-11-15"))
    p = optimize(s)
    assert p["feasible"]
    assert len(p["coverage"]) == 2
    assert p["coverage"][1]["in_horizon"] is False
    assert p["coverage"][1]["nominal"] == 0


@pytest.mark.parametrize("seed", range(12))
def test_deterministic_adversarial_constraints(seed):
    s = state(1050 + seed, 1000)
    s["routes"][0].update(percentage_fee=0.003, fixed_fee=2.17, fx_markup=0.001)
    s["funding"][0]["minimum_remaining_balance"] = seed * 4
    s["funding"].append(dict(deepcopy(s["funding"][0]), id="f2", amount=42.43, minimum_remaining_balance=0))
    p = optimize(s)
    assert not constraint_violations(s, p["allocations"])
    assert p == optimize(s)


def test_cheap_route_when_time_is_sufficient():
    s = state(1200)
    s["routes"][0]["settlement_p95_days"] = 4
    s["routes"].append(dict(s["routes"][0], id="fast", fixed_fee=20, settlement_p95_days=1))
    assert optimize(s)["allocations"][0]["transfer_route_id"] == "r1"


def test_exact_fractional_money_coverage_uses_decimal_sums():
    s = state(0.1, 0.8)
    s["funding"].append(dict(s["funding"][0], id="second", amount=0.7))
    p = optimize(s)
    assert p["verified_feasible"] and p["coverage"][0]["on_time_verified"] == 1


def test_planned_student_funds_are_not_liquid_safe_to_spend():
    s = state(1200, 1000)
    s["funding"][0]["availability_status"] = "PLANNED"
    assert optimize(s)["safe_to_spend"] == {}


def test_route_cost_includes_fx_markup():
    s = state(1100, 1000)
    s["routes"][0]["fx_markup"] = 0.01
    p = optimize(s)
    assert p["total_estimated_cost"] == 10.11  # Includes source-cent rounding residue.
    assert p["allocations"][0]["estimated_fx_cost_eur"] > 10
