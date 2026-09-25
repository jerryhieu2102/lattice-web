"""Private ledger lifecycle. All writes require structured, explicit user confirmation."""

from datetime import date
from uuid import uuid5, NAMESPACE_URL
from fastapi import HTTPException
from sqlalchemy import select
from lattice_core.models import LifeEvent, FundingSource, Obligation, Plan, PlanAllocation
from lattice_core.life.schemas import Proposal
from lattice_core.life.effects import EXPENSES, OVERLAYS, transform, missing_fields
from lattice_core.life.analysis import analyze
from lattice_core.life.budget import dec
from lattice_core.currencies import SCALE
from lattice_core.audit.service import record
from lattice_core.serialization import public
from lattice_core.state import as_of, financial_state, state_hash
from lattice_core.permissions.service import can_view_funding
from connectors.llm.mock import provider


def event_rows(db, student):
    return list(
        db.scalars(
            select(LifeEvent)
            .where(LifeEvent.actor_id == student)
            .order_by(LifeEvent.created_at.desc(), LifeEvent.id)
        )
    )


def check_version(event, version):
    if event.version != version:
        raise HTTPException(409, "Life event changed. Refresh and review it again.")


def output(e):
    return {
        **public(e),
        "proposal": e.metadata_json["proposal"],
        "impact": e.metadata_json.get("impact"),
        "missing": missing_fields(
            Proposal.model_validate(e.metadata_json["proposal"]),
            actual=e.metadata_json["proposal"]["mode"] != "HYPOTHETICAL",
        ),
    }


def store_proposal(e, p):
    data = p.model_dump(mode="json")
    columns = {c.name for c in LifeEvent.__table__.columns}
    for key, value in p.model_dump().items():
        if key in columns:
            setattr(e, key, value)
    e.recurring = bool(p.recurrence_rule)
    e.linked_funding_source_id = p.funding_source_id
    e.linked_obligation_id = p.obligation_id
    e.metadata_json = {**(e.metadata_json or {}), "proposal": data}


def capture(db, student, actor, data):
    p = Proposal.model_validate(provider.interpret_life_event(data.raw_input, as_of(), data.locale))
    for key in ("amount_minor", "currency", "event_date"):
        if getattr(data, key) is not None:
            setattr(p, key, getattr(data, key))
    if data.amount_minor is not None:
        p.amount_min_minor = p.amount_max_minor = None
    p = Proposal.model_validate(p.model_dump())
    # Provider links are proposals, never authorized resource lookups.
    p.funding_source_id = p.obligation_id = None
    e = LifeEvent(
        actor_id=student,
        raw_input=data.raw_input,
        event_type=p.event_type,
        title=p.title,
        metadata_json={"original_security_flags": p.security_flags, "locale": data.locale},
    )
    store_proposal(e, p)
    e.status = "REVIEW_REQUIRED" if missing_fields(p) else "INTERPRETED"
    db.add(e)
    db.flush()
    record(
        db,
        actor.id,
        student,
        "SECURITY_BLOCK"
        if p.security_flags
        else "PURCHASE_INTENT_CAPTURED"
        if p.event_type == "PURCHASE_INTENT"
        else "LIFE_EVENT_CAPTURED",
        "SECURITY" if p.security_flags else "AI",
        {
            "life_event_id": e.id,
            "event_type": e.event_type,
            "flags": p.security_flags,
            "authority": "PROPOSAL_ONLY",
        },
    )
    return e


def validate_links(db, actor, student, p):
    if p.funding_source_id:
        f = db.get(FundingSource, p.funding_source_id)
        if not f or f.student_id != student or not can_view_funding(db, actor, f):
            raise HTTPException(404, "Resource not found")
        if p.event_type not in OVERLAYS and f.owner_actor_id != student:
            raise HTTPException(403, "Only your own funds may be used for a life event")
        if p.event_type == "FUNDING_REDUCED" and f.currency != p.currency:
            raise HTTPException(422, "Event currency must match the linked funding source")
    if p.obligation_id:
        o = db.get(Obligation, p.obligation_id)
        if not o or o.owner_actor_id != student:
            raise HTTPException(404, "Resource not found")
        if p.event_type == "OBLIGATION_CHANGED" and o.currency != p.currency:
            raise HTTPException(422, "Event currency must match the linked commitment")
        if p.event_type == "EXPENSE_OCCURRED":
            if not o.budget_only:
                raise HTTPException(
                    403, "Payment commitments require the existing approval-controlled action flow"
                )
            if (
                p.currency != o.currency
                or p.amount_minor is None
                or dec(p.amount_minor) / SCALE[p.currency] != dec(o.amount)
            ):
                raise HTTPException(
                    422, "The recorded payment must match the full budget commitment amount and currency"
                )
        if o.status != "OPEN":
            raise HTTPException(409, "Only open commitments can be changed")


def reviewed(db, actor, e, data):
    check_version(e, data.version)
    if e.status in {"APPLIED", "RESOLVED", "DISMISSED"}:
        raise HTTPException(409, "This event is closed for editing")
    p = data.proposal
    p.security_flags = sorted(set(p.security_flags + e.metadata_json.get("original_security_flags", [])))
    validate_links(db, actor, e.actor_id, p)
    return p


def active_allocations(db, student):
    plans = select(Plan.id).where(Plan.student_id == student, Plan.status == "ACTIVE")
    return [public(a) for a in db.scalars(select(PlanAllocation).where(PlanAllocation.plan_id.in_(plans)))]


def budget_state(db, student, exclude=None):
    s = financial_state(db, student)
    for e in event_rows(db, student):
        if (
            e.status == "CONFIRMED"
            and e.id != exclude
            and e.metadata_json["proposal"]["mode"] != "HYPOTHETICAL"
        ):
            s, _ = transform(s, Proposal.model_validate(e.metadata_json["proposal"]), e.id, student)
    return s


def simulation(db, actor, e, data):
    p = reviewed(db, actor, e, data)
    was_pending = e.status == "CONFIRMED" and e.metadata_json["proposal"]["mode"] != "HYPOTHETICAL"
    result = analyze(budget_state(db, e.actor_id, e.id), p, active_allocations(db, e.actor_id))
    store_proposal(e, p)
    e.status = "REVIEW_REQUIRED" if result["missing"] else "SIMULATED"
    e.verification_status = "REVIEW_REQUIRED"
    e.version += 1
    e.metadata_json = {**e.metadata_json, "impact": result}
    db.flush()
    if was_pending:
        from apps.api.planning import invalidate

        invalidate(
            db, e.actor_id, actor.id, "LIFE_EVENT_REVIEW_REOPENED", {"life_event_id": e.id}, replan=False
        )
    record(
        db,
        actor.id,
        e.actor_id,
        "LIFE_EVENT_SIMULATED",
        "FINANCIAL",
        {"life_event_id": e.id, "shadow_only": True},
    )
    return e


def confirm(db, actor, e, data):
    p = reviewed(db, actor, e, data)
    if p.security_flags or p.event_type == "SECURITY_INCIDENT":
        raise HTTPException(
            409, "Security report requires beneficiary verification in Documents and Commitments"
        )
    missing = missing_fields(p, actual=p.mode != "HYPOTHETICAL")
    if missing:
        raise HTTPException(422, "Complete the required life event details before confirmation")
    if (
        p.mode != "HYPOTHETICAL"
        and p.event_type in EXPENSES | {"FUNDING_RECEIVED", "BORROWING"}
        and p.event_date > date.fromisoformat(as_of())
    ):
        raise HTTPException(422, "A completed expense or receipt cannot be dated in the future")
    if p.event_type == "BORROWING" and p.repayment_date < p.event_date:
        raise HTTPException(422, "Repayment date cannot precede borrowing")
    store_proposal(e, p)
    e.version += 1
    e.status = "CONFIRMED"
    e.verification_status = "USER_CONFIRMED"
    e.metadata_json = {**e.metadata_json, "confirmation_note": data.confirmation_note}
    db.flush()
    if p.mode != "HYPOTHETICAL":
        from apps.api.planning import invalidate

        invalidate(db, e.actor_id, actor.id, "LIFE_EVENT_CONFIRMED", {"life_event_id": e.id}, replan=False)
    e.metadata_json = {**e.metadata_json, "confirmed_state_hash": state_hash(financial_state(db, e.actor_id))}
    record(
        db,
        actor.id,
        e.actor_id,
        "LIFE_EVENT_CONFIRMED",
        "FINANCIAL",
        {"life_event_id": e.id, "authority": "T0_USER_CONFIRMATION", "mode": p.mode},
    )
    return e


def add_financial(db, model, data):
    data = dict(data)
    data["id"] = str(uuid5(NAMESPACE_URL, data["id"]))
    columns = {c.name for c in model.__table__.columns}
    values = {k: v for k, v in data.items() if k in columns}
    for key in ("due_date", "available_from"):
        if key in values:
            values[key] = date.fromisoformat(str(values[key]))
    obj = model(**values)
    db.add(obj)
    db.flush()
    return obj


def apply(db, actor, e, version):
    from apps.api.planning import invalidate, generate, output as plan_output, run_scenario

    check_version(e, version)
    p = Proposal.model_validate(e.metadata_json["proposal"])
    if (
        e.status != "CONFIRMED"
        or p.mode == "HYPOTHETICAL"
        or p.event_type
        in {"PURCHASE_INTENT", "TRAVEL_PLAN", "SAVINGS_GOAL", "SECURITY_INCIDENT", "OTHER", "FX_CONCERN"}
        or p.security_flags
    ):
        raise HTTPException(409, "Only confirmed real events can update the sandbox ledger")
    if missing_fields(p, actual=True):
        raise HTTPException(422, "Complete the required life event details before confirmation")
    validate_links(db, actor, e.actor_id, p)
    state = financial_state(db, e.actor_id)
    if state_hash(state) != e.metadata_json.get("confirmed_state_hash"):
        raise HTTPException(409, "Financial state changed. Review and confirm this event again.")
    _, changes = transform(state, p, e.id, e.actor_id)
    if changes["cash_gap_eur"] > 0.000001:
        raise HTTPException(
            409, "Selected funds cannot cover the expense without violating reserve or timing limits"
        )
    for debit in changes["debits"]:
        f = db.get(FundingSource, debit["funding_source_id"])
        if (
            f.owner_actor_id != e.actor_id
            or f.restriction_type != "UNRESTRICTED"
            or f.availability_status != "AVAILABLE"
        ):
            raise HTTPException(403, "Only your own available unrestricted funds may be debited")
        f.amount = dec(f.amount) - dec(debit["amount"])
        if f.amount < dec(f.minimum_remaining_balance):
            raise HTTPException(409, "Protected reserve cannot be spent")
    funding_ids = [add_financial(db, FundingSource, f).id for f in changes["new_funding"]]
    obligation_ids = [add_financial(db, Obligation, o).id for o in changes["new_obligations"]]
    for data in changes["changed_obligations"]:
        o = db.get(Obligation, data["id"])
        o.amount = dec(data["amount"])
        o.due_date = date.fromisoformat(str(data["due_date"]))
        o.status = data["status"]
        o.version += 1
    e.status = "APPLIED"
    e.version += 1
    e.metadata_json = {
        **e.metadata_json,
        "ledger": changes,
        "funding_ids": funding_ids,
        "obligation_ids": obligation_ids,
        "overlay": changes["overlay"],
    }
    if funding_ids:
        e.linked_funding_source_id = funding_ids[0]
    if obligation_ids:
        e.linked_obligation_id = obligation_ids[0]
    if p.receivable_minor or p.event_type == "LENDING":
        child_p = Proposal(
            event_type="REIMBURSEMENT_EXPECTED",
            mode="EXPECTED",
            title="Expected reimbursement",
            amount_minor=p.receivable_minor or p.amount_minor,
            currency=p.currency,
            counterparty=p.counterparty,
            expected_date=p.repayment_date,
        )
        child = LifeEvent(
            actor_id=e.actor_id,
            event_type=child_p.event_type,
            title=child_p.title,
            raw_input=e.raw_input,
            source="LINKED_EVENT",
            status="REVIEW_REQUIRED",
            metadata_json={"parent_event_id": e.id, "proposal": child_p.model_dump(mode="json")},
        )
        store_proposal(child, child_p)
        db.add(child)
        db.flush()
        e.metadata_json = {**e.metadata_json, "receivable_event_id": child.id}
    db.flush()
    record(
        db,
        actor.id,
        e.actor_id,
        "FUNDING_DELAY_REPORTED"
        if p.event_type == "FUNDING_DELAYED"
        else "EMERGENCY_DECLARED"
        if p.event_type == "EMERGENCY"
        else "LIFE_EVENT_APPLIED",
        "FINANCIAL",
        {"life_event_id": e.id, "ledger": changes, "environment": "SANDBOX"},
    )
    update = invalidate(db, e.actor_id, actor.id, "LIFE_EVENT_APPLIED", {"life_event_id": e.id})
    if update["replacement_plan"] is None:
        plan = generate(db, e.actor_id, actor.id)
        update["replacement_plan"] = plan_output(plan)
        update["scenario"] = run_scenario(db, plan, actor.id, {}, 100)
    return {"event": output(e), "planning": update}
