from copy import deepcopy
from tests.factories import state
from lattice_core.life.budget import budget, runway


def test_safe_spend_is_surplus_not_balance():
    s = state(1200, 1000)
    assert budget(s)["today"] == 200
    assert budget(state(1000, 1000))["today"] == 0
    assert budget(state(900, 1000))["today"] == 0


def test_preserves_reserves_expected_and_active_allocations():
    s = state(1500, 1000)
    s["funding"][0]["minimum_remaining_balance"] = 100
    assert budget(s)["today"] == 400
    active = [{"funding_source_id": "f1", "source_amount": 1300, "estimated_fee": 0}]
    assert budget(s, active_allocations=active)["today"] == 100
    s["funding"][0]["availability_status"] = "EXPECTED"
    assert budget(s)["today"] == 0


def test_deadline_and_unverified_obligation_conservative():
    s = state(1200, 1000)
    s["obligations"][0]["beneficiary_verified"] = False
    assert budget(s)["today"] == 0
    s["obligations"][0]["beneficiary_verified"] = True
    s["routes"][0]["settlement_p95_days"] = 20
    assert budget(s)["today"] == 0


def test_multicurrency_capacity_uses_fee_and_timing():
    s = state(1200, 1000)
    s["routes"].append(
        {
            **s["routes"][0],
            "id": "usd",
            "to_currency": "USD",
            "fx_rate": 2,
            "fixed_fee": 10,
            "settlement_p95_days": 1,
        }
    )
    result = budget(s, "USD")
    assert result["today"] == 0 and result["this_week"] == 380


def test_budget_and_runway_are_pure_and_expected_is_separate():
    s = state(900, 1000)
    s["funding"].append(
        {**s["funding"][0], "id": "expected", "amount": 500, "availability_status": "EXPECTED"}
    )
    before = deepcopy(s)
    result = runway(s)
    assert result["verified"]["days"] == 14
    assert result["including_expected"]["bounded"]
    budget(s)
    assert s == before


def test_unknown_purchase_question_does_not_offer_buy_now():
    from lattice_core.life.analysis import analyze
    from lattice_ai.life.interpretation import interpret

    result = analyze(state(), interpret("Can I afford this?", "2026-09-16"))
    assert not any(o["type"] == "BUY_NOW" for o in result["options"])


def test_unknown_savings_deadline_is_review_required():
    from lattice_core.life.analysis import analyze
    from lattice_ai.life.interpretation import interpret

    result = analyze(state(), interpret("I want to save EUR 1000", "2026-09-16"))
    assert "Target date" in result["missing"]


def test_reminders_cover_late_legacy_sources_and_locked_accounts():
    from lattice_core.life.inbox import reminders

    s = state()
    s["funding"][0]["availability_status"] = "EXPECTED"
    s["funding"][0]["available_from"] = "2026-09-15"
    assert any(n["type"] == "EXPECTED_RECEIPT_OVERDUE" for n in reminders(s, [], budget(s)))
    s["funding"][0]["availability_status"] = "LOCKED"
    assert any(n["type"] == "FUNDING_AT_RISK" for n in reminders(s, [], budget(s)))


def test_emergency_priority_cannot_be_downgraded_by_provider():
    from lattice_core.life.schemas import Proposal

    p = Proposal(event_type="EMERGENCY", priority="OPTIONAL", essentiality="DISCRETIONARY")
    assert p.priority == "CRITICAL" and p.essentiality == "ESSENTIAL"


def test_zero_lower_bound_does_not_create_zero_value_obligations():
    from lattice_core.life.schemas import Proposal
    from lattice_core.life.analysis import analyze

    p = Proposal(event_type="NEW_OBLIGATION", amount_min_minor=0, amount_max_minor=10000, currency="EUR")
    result = analyze(state(), p)
    assert len(result["variants"]) == 3
    assert result["variants"][0]["after"]["shortfall_eur"] == 0
