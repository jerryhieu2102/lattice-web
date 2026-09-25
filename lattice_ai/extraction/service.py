from datetime import date
from lattice_core.currencies import precise_amount
from sqlalchemy import select
from fastapi import HTTPException
from connectors.llm.mock import provider
from lattice_ai.adversarial.detection import security_flags
from lattice_core.provenance.validation import supported
from lattice_core.models import DocumentBlock, FinancialFact, Obligation, FundingSource
from lattice_core.audit.service import record

CRITICAL_FIELDS = {"amount", "currency", "due_date", "beneficiary"}


def extract(db, doc, actor_id):
    if db.scalar(select(FinancialFact.id).where(FinancialFact.document_id == doc.id).limit(1)):
        return list(db.scalars(select(FinancialFact).where(FinancialFact.document_id == doc.id)))
    doc.document_type = provider.classify_document(doc.text)
    flags = security_flags(doc.text)
    blocks = list(
        db.scalars(
            select(DocumentBlock)
            .where(DocumentBlock.document_id == doc.id)
            .order_by(DocumentBlock.page, DocumentBlock.block_index)
        )
    )
    if not blocks:
        for index, line in enumerate(doc.text.splitlines()):
            block = DocumentBlock(document_id=doc.id, page=1, block_index=index, text=line)
            db.add(block)
            blocks.append(block)
        db.flush()
    block_data = [{"text": b.text, "page": b.page} for b in blocks]
    proposals = provider.extract_financial_facts(block_data)
    currencies = {p.normalized_value for p in proposals if p.field == "currency" and supported(p, block_data)}
    for currency in currencies:
        for p in proposals:
            if p.field == "amount" and supported(p, block_data):
                try:
                    precise_amount(p.normalized_value, currency)
                except ValueError:
                    flags.append("INVALID_CURRENCY_MINOR_UNITS")
    existing = db.get(Obligation, doc.target_obligation_id) if doc.target_obligation_id else None
    results = []
    for proposal in proposals:
        if existing and proposal.field == "beneficiary" and proposal.normalized_value != existing.beneficiary:
            existing.security_hold = True
            flags.append("BENEFICIARY_CHANGE_BLOCKED")
        if not supported(proposal, block_data):
            flags.append("UNSUPPORTED_FACT")
            continue
        values = {p.normalized_value for p in proposals if p.field == proposal.field}
        conflict = len(values) > 1
        if existing and proposal.field in CRITICAL_FIELDS:
            prior = str(getattr(existing, proposal.field))
            current = proposal.normalized_value
            if proposal.field == "amount":
                conflict = conflict or float(prior) != float(current)
            else:
                conflict = conflict or prior != current
            if conflict and proposal.field == "beneficiary":
                existing.security_hold = True
                flags.append("BENEFICIARY_CHANGE_BLOCKED")
        fact = FinancialFact(
            document_id=doc.id,
            field=proposal.field,
            raw_value=proposal.raw_value,
            normalized_value=proposal.normalized_value,
            currency=proposal.normalized_value if proposal.field == "currency" else None,
            date_value=date.fromisoformat(proposal.normalized_value)
            if proposal.field in {"due_date", "available_from"}
            else None,
            confidence=proposal.confidence,
            verification_status="CONFLICTED" if conflict else "REVIEW_REQUIRED" if flags else "EXTRACTED",
            source_page=proposal.page,
            source_block=blocks[proposal.block_index].id,
            evidence_text=proposal.evidence_text,
        )
        db.add(fact)
        results.append(fact)
    doc.security_flags = sorted(set(flags))
    doc.status = "SECURITY_REVIEW" if flags else "EXTRACTED"
    if flags:
        record(
            db,
            actor_id,
            doc.owner_id,
            "SECURITY_BLOCK",
            "SECURITY",
            {
                "document_id": doc.id,
                "flags": doc.security_flags,
                "effect": "No tool invocation or verified replacement",
            },
        )
    db.flush()
    record(
        db,
        actor_id,
        doc.owner_id,
        "FACT_EXTRACTED",
        "AI",
        {
            "document_id": doc.id,
            "fact_ids": [f.id for f in results],
            "provider": "deterministic fixture parser",
        },
    )
    return results


def confirm(db, fact, doc, actor_id):
    if fact.verification_status in {"CONFLICTED", "REJECTED"} or doc.security_flags:
        raise HTTPException(
            409,
            "Conflicting or unsafe evidence cannot be promoted. Resolve through explicit source verification.",
        )
    block = db.get(DocumentBlock, fact.source_block)
    if (
        not block
        or block.document_id != doc.id
        or not fact.evidence_text
        or fact.evidence_text not in block.text
        or fact.raw_value not in fact.evidence_text
    ):
        raise HTTPException(409, "Evidence validation failed")
    fact.verification_status = "USER_CONFIRMED"
    db.flush()
    record(
        db,
        actor_id,
        doc.owner_id,
        "FACT_CONFIRMED",
        "AI",
        {"fact_id": fact.id, "authority": "Explicit user confirmation; not institutional verification"},
    )
    facts = list(db.scalars(select(FinancialFact).where(FinancialFact.document_id == doc.id)))
    values = {f.field: f.normalized_value for f in facts if f.verification_status == "USER_CONFIRMED"}
    if doc.document_type in {"SCHOLARSHIP_NOTICE", "SPONSOR_DECLARATION"}:
        required = {"amount", "currency", "available_from"}
        if not required.issubset(values):
            return {"updated": False, "missing_fields": sorted(required - set(values))}
        amount_fact = next(f for f in facts if f.field == "amount")
        funding = db.scalar(select(FundingSource).where(FundingSource.source_fact_id == amount_fact.id))
        if not funding:
            funding = FundingSource(
                owner_actor_id=doc.owner_id,
                student_id=doc.owner_id,
                source_type="SCHOLARSHIP" if doc.document_type == "SCHOLARSHIP_NOTICE" else "OTHER",
                label=doc.filename,
                amount=float(values["amount"]),
                currency=values["currency"],
                available_from=date.fromisoformat(values["available_from"]),
                availability_status="EXPECTED",
                verification_status="USER_CONFIRMED",
                restriction_type="UNRESTRICTED",
                minimum_remaining_balance=0,
                source_fact_id=amount_fact.id,
                confirmation_note="Confirmed notice; receipt remains uncertain.",
            )
            db.add(funding)
            db.flush()
        doc.status = "CONFIRMED"
        return {"updated": True, "funding_source_id": funding.id}
    if not CRITICAL_FIELDS.issubset(values):
        return {"updated": False, "missing_fields": sorted(CRITICAL_FIELDS - set(values))}
    existing = (
        db.get(Obligation, doc.target_obligation_id)
        if doc.target_obligation_id
        else db.scalar(select(Obligation).where(Obligation.source_document_id == doc.id))
    )
    if existing:
        if (
            float(existing.amount) != float(values["amount"])
            or existing.beneficiary != values["beneficiary"]
            or str(existing.due_date) != values["due_date"]
            or existing.currency != values["currency"]
        ):
            raise HTTPException(
                409, "Verified state conflict; document cannot overwrite existing commitments"
            )
    else:
        type_ = {
            "TUITION_INVOICE": "TUITION",
            "HOUSING_CONTRACT": "HOUSING_DEPOSIT",
            "INSURANCE_INVOICE": "INSURANCE",
        }.get(doc.document_type, "OTHER")
        existing = Obligation(
            owner_actor_id=doc.owner_id,
            type=type_,
            label=doc.filename,
            beneficiary=values["beneficiary"],
            amount=float(values["amount"]),
            currency=values["currency"],
            due_date=date.fromisoformat(values["due_date"]),
            priority="CRITICAL",
            verification_status="USER_CONFIRMED",
            beneficiary_verified=True,
            source_document_id=doc.id,
            confirmation_note="All critical facts explicitly confirmed against evidence.",
        )
        db.add(existing)
    doc.status = "CONFIRMED"
    db.flush()
    return {"updated": True, "obligation_id": existing.id}
