from datetime import date
import hashlib
from sqlalchemy import select, delete
from lattice_core.models import (
    LifeEvent,
    FundingSource,
    Obligation,
    TransferRoute,
    Document,
    DocumentBlock,
    FinancialFact,
    Permission,
    Plan,
    PlanAllocation,
    ScenarioRun,
    ScenarioResult,
    InterventionCandidate,
    PreparedAction,
)
from lattice_core.state import as_of
from connectors.mock_fx.routes import ensure_demo_routes
from lattice_core.audit.service import record

DEMO_ANCHOR = date(2026, 9, 16)


def demo_date(month, day):
    return date(2026, month, day) + (date.fromisoformat(as_of()) - DEMO_ANCHOR)


def reset(db, actor_id="admin"):
    # Explicitly scoped to the fictional Maya tenant. Audit history and logins survive reset.
    db.execute(delete(LifeEvent).where(LifeEvent.actor_id == "maya"))
    plans = select(Plan.id).where(Plan.student_id == "maya")
    runs = select(ScenarioRun.id).where(ScenarioRun.student_id == "maya")
    db.execute(delete(ScenarioResult).where(ScenarioResult.run_id.in_(runs)))
    db.execute(delete(ScenarioRun).where(ScenarioRun.student_id == "maya"))
    db.execute(delete(PreparedAction).where(PreparedAction.student_id == "maya"))
    db.execute(delete(InterventionCandidate).where(InterventionCandidate.student_id == "maya"))
    db.execute(delete(PlanAllocation).where(PlanAllocation.plan_id.in_(plans)))
    db.execute(delete(Plan).where(Plan.student_id == "maya"))
    db.execute(delete(TransferRoute).where(~TransferRoute.id.in_(select(PlanAllocation.transfer_route_id))))
    db.execute(delete(Permission).where(Permission.owner_actor_id.in_(["maya", "father", "sponsor"])))
    db.execute(delete(FundingSource).where(FundingSource.student_id == "maya"))
    db.execute(delete(Obligation).where(Obligation.owner_actor_id == "maya"))
    docs = select(Document.id).where(Document.owner_id.in_(["maya", "father", "sponsor"]))
    db.execute(delete(FinancialFact).where(FinancialFact.document_id.in_(docs)))
    db.execute(delete(DocumentBlock).where(DocumentBlock.document_id.in_(docs)))
    db.execute(delete(Document).where(Document.owner_id.in_(["maya", "father", "sponsor"])))
    record(
        db,
        actor_id,
        "maya",
        "DEMO_RESET",
        "FINANCIAL",
        {"scope": "Fictional Maya data only; audit preserved"},
    )


def evidence(db, owner, filename, type_, values, confirmed=True):
    text = "\n".join(f"{key}: {value}" for key, value in values.items())
    doc = Document(
        owner_id=owner,
        filename=filename,
        document_type=type_,
        trust_level="T2",
        status="CONFIRMED" if confirmed else "UPLOADED",
        sha256=hashlib.sha256(text.encode()).hexdigest(),
        text=text,
    )
    db.add(doc)
    db.flush()
    facts = []
    if confirmed:
        for index, (key, value) in enumerate(values.items()):
            block = DocumentBlock(document_id=doc.id, page=1, block_index=index, text=f"{key}: {value}")
            db.add(block)
            db.flush()
            fact = FinancialFact(
                document_id=doc.id,
                field=key.lower().replace(" ", "_"),
                raw_value=str(value),
                normalized_value=str(value),
                confidence=1,
                verification_status="USER_CONFIRMED",
                source_page=1,
                source_block=block.id,
                evidence_text=block.text,
            )
            db.add(fact)
            facts.append(fact)
        db.flush()
    return doc, facts


def load_maya(db):
    if db.scalar(select(FundingSource.id).where(FundingSource.student_id == "maya").limit(1)):
        return {"loaded": False, "message": "Maya is already loaded. Reset first for a clean run."}
    for id_, owner, kind, label, amount, currency, available, availability, restriction, reserve in [
        (
            "student-eur",
            "maya",
            "STUDENT_BALANCE",
            "Maya · EUR account",
            1700,
            "EUR",
            as_of(),
            "AVAILABLE",
            "UNRESTRICTED",
            0,
        ),
        (
            "parent-vnd",
            "father",
            "PARENT_SUPPORT",
            "Father · VND contribution",
            33333334,
            "VND",
            as_of(),
            "PLANNED",
            "UNRESTRICTED",
            0,
        ),
        (
            "scholarship",
            "maya",
            "SCHOLARSHIP",
            "Merit scholarship",
            2000,
            "EUR",
            demo_date(9, 25),
            "EXPECTED",
            "UNRESTRICTED",
            0,
        ),
        (
            "reserve",
            "maya",
            "EMERGENCY_RESERVE",
            "Protected emergency reserve",
            600,
            "EUR",
            as_of(),
            "AVAILABLE",
            "EMERGENCY",
            600,
        ),
    ]:
        _, facts = evidence(
            db,
            owner,
            f"{id_}.txt",
            "SCHOLARSHIP_NOTICE" if kind == "SCHOLARSHIP" else "SPONSOR_DECLARATION",
            {"Amount": amount, "Currency": currency, "Available from": available, "Status": availability},
        )
        db.add(
            FundingSource(
                id=id_,
                owner_actor_id=owner,
                student_id="maya",
                source_type=kind,
                label=label,
                amount=amount,
                currency=currency,
                available_from=date.fromisoformat(str(available)),
                availability_status=availability,
                verification_status="USER_CONFIRMED",
                restriction_type=restriction,
                minimum_remaining_balance=reserve,
                confidence=0.85 if kind == "SCHOLARSHIP" else 1,
                source_fact_id=facts[0].id,
                confirmation_note="Explicitly confirmed fictional demo fixture; expected income is not guaranteed.",
            )
        )
    for id_, type_, label, amount, due, priority, beneficiary in [
        ("housing", "HOUSING_DEPOSIT", "Housing deposit", 900, demo_date(9, 23), "CRITICAL", "HOUSE123"),
        ("tuition", "TUITION", "Autumn tuition", 3200, demo_date(9, 30), "CRITICAL", "ABC123"),
        ("rent", "RENT", "October rent", 1100, demo_date(10, 1), "CRITICAL", "RENT123"),
        ("insurance", "INSURANCE", "Student insurance", 250, demo_date(10, 5), "HIGH", "INSURE123"),
    ]:
        doc, _ = evidence(
            db,
            "maya",
            f"{id_}-confirmed.txt",
            "TUITION_INVOICE"
            if type_ == "TUITION"
            else "HOUSING_CONTRACT"
            if type_ in {"RENT", "HOUSING_DEPOSIT"}
            else "INSURANCE_INVOICE",
            {"Type": type_, "Amount": amount, "Currency": "EUR", "Due date": due, "Beneficiary": beneficiary},
        )
        db.add(
            Obligation(
                id=id_,
                owner_actor_id="maya",
                type=type_,
                label=label,
                beneficiary=beneficiary,
                amount=amount,
                currency="EUR",
                due_date=due,
                priority=priority,
                verification_status="USER_CONFIRMED",
                beneficiary_verified=True,
                source_document_id=doc.id,
                confirmation_note="Explicitly confirmed fictional fixture.",
                installment_option={
                    "amounts": [1600, 1600],
                    "dates": [str(demo_date(9, 30)), str(demo_date(11, 15))],
                    "fee": 20,
                    "requires_institution_consent": True,
                }
                if id_ == "tuition"
                else None,
            )
        )
    db.flush()
    for target, rtype, rid, ptype, owner in [
        ("father", "OBLIGATION", "tuition", "VIEW_SHARED_OBLIGATION", "maya"),
        ("maya", "FUNDING", "parent-vnd", "VIEW_OWN_CONTRIBUTION", "father"),
        ("maya", "FUNDING", "parent-vnd", "APPROVE_OWN_FUNDS", "father"),
    ]:
        db.add(
            Permission(
                owner_actor_id=owner,
                target_actor_id=target,
                resource_type=rtype,
                resource_id=rid,
                permission_type=ptype,
            )
        )
        record(
            db,
            owner,
            "maya",
            "PERMISSION_GRANTED",
            "PERMISSION",
            {
                "resource_id": rid,
                "permission_type": ptype,
                "target_actor_id": target,
                "source": "Explicit demo consent fixture",
            },
        )
    ensure_demo_routes(db)
    review, _ = evidence(
        db,
        "maya",
        "tuition-review.txt",
        "TUITION_INVOICE",
        {
            "Type": "TUITION",
            "Amount": 3200,
            "Currency": "EUR",
            "Due date": demo_date(9, 30),
            "Beneficiary": "ABC123",
        },
        False,
    )
    review.target_obligation_id = "tuition"
    db.flush()
    record(
        db,
        "admin",
        "maya",
        "MAYA_LOADED",
        "FINANCIAL",
        {"fictional": True, "as_of": as_of(), "rate_source": "deterministic fixtures, not live"},
    )
    return {"loaded": True, "student_id": "maya", "as_of": as_of()}
