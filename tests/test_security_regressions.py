from copy import deepcopy
import pytest
from connectors.llm.provider import FactProposal
from lattice_core.provenance.validation import supported
from tests.conftest import login
from tests.test_api import post, plan, BASE
from tests.factories import state
from optimizer.model.solver import optimize, constraint_violations
from simulation.scenarios.engine import simulate


@pytest.mark.parametrize("operation", ["create", "patch"])
def test_parent_mutation_response_never_leaks_replanned_private_state(client, operation):
    plan(client)
    login(client, "parent")
    if operation == "patch":
        r = client.patch(
            BASE + "/funding-sources/parent-vnd",
            json={"amount": 40000000, "confirmation_note": "Confirmed my own contribution only"},
        )
    else:
        r = client.post(
            BASE + "/funding-sources",
            json={
                "label": "Own contribution",
                "source_type": "PARENT_SUPPORT",
                "amount": 100,
                "currency": "EUR",
                "available_from": "2026-09-16",
                "availability_status": "PLANNED",
                "confirmation_note": "My explicitly confirmed contribution",
            },
        )
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"funding", "financial_state_updated"}
    assert not any(
        private in r.text
        for private in [
            "student-eur",
            "scholarship",
            "reserve",
            "snapshot",
            "replacement_plan",
            "October rent",
        ]
    )


@pytest.mark.parametrize(
    "field,raw,normalized",
    [
        ("amount", "3200", "1"),
        ("beneficiary", "ABC123", "ABC999"),
        ("due_date", "2026-09-30", "2026-09-17"),
        ("currency", "EUR", "USD"),
    ],
)
def test_provider_cannot_forge_normalized_value_with_valid_raw_evidence(field, raw, normalized):
    line = field.replace("_", " ").title() + ": " + raw
    proposal = FactProposal(
        field=field,
        raw_value=raw,
        normalized_value=normalized,
        confidence=1,
        evidence_text=line,
        page=1,
        block_index=0,
    )
    assert not supported(proposal, [{"text": line, "page": 1}])


def test_provider_cannot_cite_other_field_as_evidence():
    p = FactProposal(
        field="beneficiary",
        raw_value="ABC123",
        normalized_value="ABC123",
        confidence=1,
        evidence_text="Comment: ABC123",
        page=1,
        block_index=0,
    )
    assert not supported(p, [{"text": "Comment: ABC123", "page": 1}])


def test_scholarship_patch_cannot_claim_planned_receipt(client):
    r = client.patch(
        BASE + "/funding-sources/scholarship",
        json={"availability_status": "PLANNED", "confirmation_note": "A notice is not proof of receipt"},
    )
    assert r.status_code == 422


@pytest.mark.parametrize(
    "path,body",
    [
        (
            "/funding-sources/parent-vnd",
            {"amount": 10000000.5, "confirmation_note": "A fractional dong must be rejected"},
        ),
        (
            "/obligations/tuition",
            {"amount": 3200.005, "confirmation_note": "Fractional cents are not valid money"},
        ),
    ],
)
def test_money_precision_is_not_silently_rounded(client, path, body):
    if "parent" in path:
        login(client, "parent")
    assert client.patch(BASE + path, json=body).status_code == 422


def test_solver_timeout_fails_closed_with_a_complete_result():
    s = state()
    s["solver_timeout_seconds"] = 0
    p = optimize(s)
    assert not p["feasible"] and not p["allocations"] and p["error"]
    assert simulate(s, p, {}, 10)["scenario_failure_rate"] == 1


def test_validator_independently_checks_trust_and_route():
    s = state()
    allocation = optimize(s)["allocations"]
    modified = deepcopy(s)
    modified["obligations"][0]["security_hold"] = True
    modified["routes"][0]["verification_status"] = "EXTRACTED"
    assert {"unverified_obligation", "unverified_route"} <= set(constraint_violations(modified, allocation))


def test_fractional_route_fee_rounds_up_not_down():
    s = state(1001, 1000)
    s["routes"][0]["fixed_fee"] = 0.001
    p = optimize(s)
    assert p["allocations"][0]["estimated_fee"] == 0.01
    assert not constraint_violations(s, p["allocations"])


def test_benchmark_api_exports_real_run_and_denies_parent(client, tmp_path, monkeypatch):
    from benchmark import run

    monkeypatch.setattr(run, "RESULT_DIR", tmp_path)
    r = post(client, "/benchmark/run", {"mode": "FAST"})
    assert r["passed"] == 48 and r["failed"] == 0
    assert client.get(BASE + "/benchmark/latest").json()["id"] == r["id"]
    csv = client.get(BASE + "/benchmark/export?format=csv")
    assert csv.status_code == 200 and len(csv.text.splitlines()) == 49
    login(client, "parent")
    assert client.get(BASE + "/benchmark/latest").status_code == 403
    assert client.post(BASE + "/benchmark/run", json={"mode": "FAST"}).status_code == 403


def test_unicode_change_sets_hold_even_when_proposal_validation_rejects_it(client):
    from tests.test_api import malicious

    malicious(client, "Beneficiary: АBC123")
    o = client.get(BASE + "/obligations/tuition").json()
    assert o["beneficiary"] == "ABC123" and o["security_hold"]


def test_request_without_same_origin_header_is_rejected(client):
    client.headers.pop("x-lattice-request")
    assert client.post(BASE + "/plans/generate").status_code == 403


def test_unshared_parent_source_cannot_leak_through_student_plan_or_graph(client):
    login(client, "parent")
    private = post(
        client,
        "/funding-sources",
        {
            "label": "Parent private savings",
            "source_type": "OTHER",
            "amount": 98765,
            "currency": "EUR",
            "available_from": "2026-09-16",
            "availability_status": "AVAILABLE",
            "confirmation_note": "Private until explicitly shared",
        },
    )["funding"]["id"]
    assert private in {n["id"] for n in client.get(BASE + "/graph").json()["nodes"]}
    login(client, "student")
    assert private not in {f["id"] for f in client.get(BASE + "/funding-sources").json()}
    assert private not in {n["id"] for n in client.get(BASE + "/graph").json()["nodes"]}
    assert private not in {f["id"] for f in plan(client)["snapshot"]["funding"]}


def test_document_rejects_fractional_vnd_before_confirmation(client):
    doc = post(
        client,
        "/documents",
        {
            "filename": "tuition-vnd.txt",
            "text": "Type: TUITION\nAmount: 1000.50\nCurrency: VND\nDue date: 2026-09-30\nBeneficiary: ABC123",
        },
    )
    r = post(client, "/documents/" + doc["id"] + "/extract")
    assert "INVALID_CURRENCY_MINOR_UNITS" in r["document"]["security_flags"]
    for fact in r["facts"]:
        assert (
            client.post(BASE + "/facts/" + fact["id"] + "/confirm", json={"confirmed": True}).status_code
            == 409
        )


def test_delegated_action_approval_never_replaces_fund_owner(client):
    client.patch(
        BASE + "/funding-sources/student-eur",
        json={"amount": 10000, "confirmation_note": "Explicit test balance confirmation"},
    )
    p = plan(client)
    action = post(
        client,
        "/actions/prepare",
        {"type": "SCHEDULE_TRANSFER", "plan_id": p["id"], "obligation_id": "housing"},
    )
    post(client, "/actions/" + action["id"] + "/approve", {"confirmed": True})
    permission = post(
        client,
        "/permissions",
        {
            "target_actor_id": "father",
            "resource_type": "ACTION",
            "resource_id": action["id"],
            "permission_type": "APPROVE_ACTION",
        },
    )
    updated = next(a for a in client.get(BASE + "/actions").json() if a["id"] == action["id"])
    assert updated["payload"]["required_approvals"] == ["father", "maya"]
    assert not updated["payload"]["approvals"] and updated["status"] == "PREPARED"
    login(client, "parent")
    post(client, "/actions/" + action["id"] + "/approve", {"confirmed": True})
    login(client, "student")
    assert client.post(BASE + "/actions/" + action["id"] + "/sandbox-execute").status_code == 409
    assert client.delete(BASE + "/permissions/" + permission["id"]).status_code == 200
    updated = next(a for a in client.get(BASE + "/actions").json() if a["id"] == action["id"])
    assert updated["payload"]["required_approvals"] == ["maya"] and not updated["payload"]["approvals"]
    post(client, "/actions/" + action["id"] + "/approve", {"confirmed": True})
    assert post(client, "/actions/" + action["id"] + "/sandbox-execute")["real_money_moved"] is False


def test_plan_approval_permission_does_not_grant_private_plan_access(client):
    p = plan(client)
    post(
        client,
        "/permissions",
        {
            "target_actor_id": "father",
            "resource_type": "PLAN",
            "resource_id": p["id"],
            "permission_type": "APPROVE_PLAN",
        },
    )
    login(client, "parent")
    r = post(client, "/plans/" + p["id"] + "/activate")
    assert r == {"id": p["id"], "status": "ACTIVE", "financial_details_redacted": True}
    assert client.get(BASE + "/plans/" + p["id"]).status_code == 403
    assert "snapshot" not in r
