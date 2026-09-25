from optimizer.rescue.planner import rescue
from tests.factories import state


def test_installment_preferred_to_unnecessary_family_topup():
    s = state(1700, 3200)
    s["obligations"][0]["installment_option"] = {
        "amounts": [1600, 1600],
        "dates": ["2026-09-30", "2026-11-15"],
        "fee": 20,
    }
    result = rescue(s)
    best = result["candidates"][0]
    assert best["type"] == "USE_INSTALLMENT_OPTION"
    assert best["family_contribution_eur"] == 0
    assert best["feasible"]
    assert s["obligations"][0]["amount"] == 3200
    assert len(best["coverage"]) == 3
    assert any(c["label"] == "Sandbox installment fee" for c in best["coverage"])


def test_rescue_reports_assumptions():
    best = rescue(state(500, 1000))["candidates"][0]
    assert best["family_contribution_eur"] == 500
    assert best["conditional"]
    assert best["assumptions"]


def test_deadline_extension_can_repair_verified_future_funding():
    s = state(1200, 1000)
    s["funding"][0]["available_from"] = "2026-10-05"
    result = rescue(s)
    best = result["candidates"][0]
    assert best["type"] == "REQUEST_DEADLINE_EXTENSION"
    assert best["feasible"] and best["family_contribution_eur"] == 0
    assert "admin" in best["required_actors"]
    assert s["obligations"][0]["due_date"] == "2026-09-30"


def test_parent_reserve_cannot_be_released_by_student_rescue():
    s = state(1000, 1500)
    s["funding"][0].update(owner_type="PARENT", owner_actor_id="father", restriction_type="EMERGENCY")
    result = rescue(s)
    assert all(not c["reserve_changes"] for c in result["candidates"])


def test_all_seven_intervention_types_are_evaluated_when_applicable():
    from copy import deepcopy

    s = state(1700, 3200)
    s["funding"].append(
        dict(
            deepcopy(s["funding"][0]),
            id="parent",
            owner_actor_id="father",
            owner_type="PARENT",
            amount=300,
            availability_status="PLANNED",
            available_from="2026-10-15",
        )
    )
    s["funding"].append(
        dict(
            deepcopy(s["funding"][0]),
            id="reserve",
            restriction_type="EMERGENCY",
            amount=600,
            minimum_remaining_balance=600,
        )
    )
    s["obligations"][0]["installment_option"] = {
        "amounts": [1600, 1600],
        "dates": ["2026-09-30", "2026-11-15"],
        "fee": 20,
    }
    s["obligations"].append(
        dict(
            deepcopy(s["obligations"][0]),
            id="optional",
            amount=100,
            priority="OPTIONAL",
            installment_option=None,
        )
    )
    kinds = {c["type"] for c in rescue(s)["candidates"]}
    assert {
        "INCREASE_FAMILY_TRANSFER",
        "EXPEDITE_TRANSFER",
        "USE_INSTALLMENT_OPTION",
        "DELAY_OPTIONAL_EXPENSE",
        "USE_RESERVE_WITH_APPROVAL",
        "REQUEST_DEADLINE_EXTENSION",
    } <= kinds
    assert rescue(state())["candidates"][0]["type"] == "REALLOCATE_UNRESTRICTED_FUNDS"
