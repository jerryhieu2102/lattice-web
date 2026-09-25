from pathlib import Path
from tests.test_api import BASE, post


def test_real_pdf_upload_evidence_page_and_confirmed_state(client):
    content = (Path(__file__).resolve().parents[1] / "fixtures/documents/tuition.pdf").read_bytes()
    uploaded = client.post(
        BASE + "/documents",
        files={"file": ("tuition.pdf", content, "application/pdf")},
        data={"target_obligation_id": "tuition"},
    )
    assert uploaded.status_code == 200, uploaded.text
    extracted = post(client, "/documents/" + uploaded.json()["id"] + "/extract")
    assert len(extracted["facts"]) == 5
    assert all(f["source_page"] == 2 for f in extracted["facts"])
    for fact in extracted["facts"]:
        post(client, "/facts/" + fact["id"] + "/confirm", {"confirmed": True})
    assert client.get(BASE + "/obligations/tuition").json()["amount"] == 3200
    assert len(client.get(BASE + "/obligations").json()) == 4


def test_empty_pdf_does_not_fabricate_ocr(client):
    from io import BytesIO
    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=600, height=800)
    data = BytesIO()
    w.write(data)
    r = client.post(BASE + "/documents", files={"file": ("scan.pdf", data.getvalue(), "application/pdf")})
    assert r.status_code == 422 and "OCR is not available" in r.text


def test_new_document_becomes_a_payable_commitment(client):
    doc = post(
        client,
        "/documents",
        {
            "filename": "new-tuition.txt",
            "text": "Type: TUITION\nAmount: 10\nCurrency: EUR\nDue date: 2026-09-22\nBeneficiary: NEW123",
        },
    )
    facts = post(client, "/documents/" + doc["id"] + "/extract")["facts"]
    result = None
    for fact in facts:
        result = post(client, "/facts/" + fact["id"] + "/confirm", {"confirmed": True})
    obligations = client.get(BASE + "/obligations").json()
    o = next(o for o in obligations if o["label"] == "new-tuition.txt")
    assert result and o["verification_status"] == "USER_CONFIRMED"
    client.patch(
        BASE + "/funding-sources/student-eur",
        json={"amount": 10000, "confirmation_note": "Explicit test funding confirmed"},
    )
    p = post(client, "/plans/generate")
    assert next(c for c in p["summary"]["coverage"] if c["obligation_id"] == o["id"])["type"] == "TUITION"
    action = post(
        client, "/actions/prepare", {"type": "TUITION_PAYMENT", "plan_id": p["id"], "obligation_id": o["id"]}
    )
    post(client, "/actions/" + action["id"] + "/approve", {"confirmed": True})
    assert post(client, "/actions/" + action["id"] + "/sandbox-execute")["real_money_moved"] is False
    assert client.get(BASE + "/obligations/" + o["id"]).json()["status"] == "SANDBOX_PAID"


def test_admin_can_read_every_document_listed_in_demo_workspace(client):
    from tests.conftest import login

    login(client, "admin")
    docs = client.get(BASE + "/documents").json()
    assert any(d["owner_id"] == "father" for d in docs)
    for doc in docs:
        assert client.get(BASE + "/documents/" + doc["id"]).status_code == 200
    parent_doc = next(d for d in docs if d["owner_id"] == "father")
    assert client.post(BASE + "/documents/" + parent_doc["id"] + "/extract").status_code == 404
