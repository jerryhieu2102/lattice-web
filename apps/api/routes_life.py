from datetime import date
from fastapi import APIRouter, HTTPException
from lattice_core.currencies import Currency, SCALE
from lattice_core.models import LifeEvent, FundingSource, Obligation
from lattice_core.life import service
from lattice_core.life.schemas import Capture, Review, Confirm, Version, Receipt, Resolve, Proposal
from lattice_core.life.effects import EXPECTED, OVERLAYS, transform
from lattice_core.life.budget import budget, runway
from lattice_core.life.inbox import reminders, recurring_summary
from lattice_core.audit.service import record
from lattice_core.state import as_of, financial_state
from lattice_ai.life.examples import EXAMPLES
from apps.api.auth import require_student
from apps.api.deps import DB, User, owned
from apps.api.planning import invalidate

router = APIRouter()


def get_event(db, actor, id):
    return owned(db, LifeEvent, id, "actor_id", require_student(actor))


@router.get("/life-events/examples")
def examples(actor: User):
    require_student(actor)
    return EXAMPLES


@router.post("/life-events/interpret")
@router.post("/life-events")
def capture(data: Capture, db: DB, actor: User):
    return service.output(service.capture(db, require_student(actor), actor, data))


@router.get("/life-events")
def list_events(db: DB, actor: User):
    return [service.output(e) for e in service.event_rows(db, require_student(actor))]


@router.get("/life-events/{id}")
def detail(id: str, db: DB, actor: User):
    e = get_event(db, actor, id)
    return {**service.output(e), "recurring_summary": recurring_summary(e, as_of())}


@router.post("/life-events/{id}/simulate")
def simulate(id: str, data: Review, db: DB, actor: User):
    return service.output(service.simulation(db, actor, get_event(db, actor, id), data))


@router.post("/purchase-check")
def purchase_check(data: Capture, db: DB, actor: User):
    student = require_student(actor)
    e = service.capture(db, student, actor, data)
    p = Proposal.model_validate(e.metadata_json["proposal"])
    # This endpoint can only simulate, even if raw text describes an actual expense.
    p.mode = "HYPOTHETICAL"
    return service.output(service.simulation(db, actor, e, Review(proposal=p, version=e.version)))


@router.post("/life-events/{id}/confirm")
def confirm(id: str, data: Confirm, db: DB, actor: User):
    return service.output(service.confirm(db, actor, get_event(db, actor, id), data))


@router.post("/life-events/{id}/apply")
def apply(id: str, data: Version, db: DB, actor: User):
    return service.apply(db, actor, get_event(db, actor, id), data.version)


@router.post("/life-events/{id}/dismiss")
def dismiss(id: str, data: Version, db: DB, actor: User):
    e = get_event(db, actor, id)
    service.check_version(e, data.version)
    p = Proposal.model_validate(e.metadata_json["proposal"])
    if e.status in {"RESOLVED", "DISMISSED"} or (e.status == "APPLIED" and p.event_type not in EXPECTED):
        raise HTTPException(409, "Applied ledger entries cannot be undone by dismissal")
    was_pending = e.status == "CONFIRMED"
    if e.status == "APPLIED" and e.linked_funding_source_id:
        f = db.get(FundingSource, e.linked_funding_source_id)
        if f.owner_actor_id != e.actor_id or f.availability_status != "EXPECTED":
            raise HTTPException(409, "Received funds cannot be cancelled as an expectation")
        f.availability_status = "DISPUTED"
    e.status = "DISMISSED"
    e.version += 1
    db.flush()
    if was_pending or e.metadata_json.get("funding_ids"):
        invalidate(db, e.actor_id, actor.id, "LIFE_EVENT_DISMISSED", {"life_event_id": e.id})
    record(db, actor.id, e.actor_id, "LIFE_EVENT_DISMISSED", "FINANCIAL", {"life_event_id": e.id})
    return service.output(e)


@router.post("/life-events/{id}/received")
def received(id: str, data: Receipt, db: DB, actor: User):
    e = get_event(db, actor, id)
    service.check_version(e, data.version)
    p = Proposal.model_validate(e.metadata_json["proposal"])
    if (
        e.status in {"RESOLVED", "DISMISSED"}
        or p.event_type not in EXPECTED
        or p.security_flags
        or p.amount_minor is None
        or not p.currency
    ):
        raise HTTPException(409, "Only an unresolved expected receipt can be marked received")
    if data.received_date > date.fromisoformat(as_of()):
        raise HTTPException(422, "Receipt date cannot be in the future")
    if e.linked_funding_source_id:
        f = db.get(FundingSource, e.linked_funding_source_id)
        if f.owner_actor_id != e.actor_id or f.availability_status != "EXPECTED":
            raise HTTPException(403, "Only your own expected receipt may be confirmed")
        f.availability_status = "AVAILABLE"
        f.available_from = data.received_date
        f.verification_status = "USER_CONFIRMED"
    else:
        receipt = p.model_copy(
            update={"event_type": "FUNDING_RECEIVED", "mode": "ACTUAL", "event_date": data.received_date}
        )
        _, changes = transform(financial_state(db, e.actor_id), receipt, e.id, e.actor_id)
        f = service.add_financial(db, FundingSource, changes["new_funding"][0])
        e.linked_funding_source_id = f.id
    f.confirmation_note = data.confirmation_note
    e.status = "RESOLVED"
    e.version += 1
    e.verification_status = "USER_CONFIRMED"
    e.metadata_json = {
        **e.metadata_json,
        "received_date": str(data.received_date),
        "receipt_note": data.confirmation_note,
    }
    db.flush()
    record(
        db,
        actor.id,
        e.actor_id,
        "REIMBURSEMENT_RECEIVED" if p.event_type == "REIMBURSEMENT_EXPECTED" else "LIFE_EVENT_RECEIVED",
        "FINANCIAL",
        {"life_event_id": e.id, "funding_source_id": f.id, "authority": "T0_USER_CONFIRMATION"},
    )
    invalidate(db, e.actor_id, actor.id, "FUNDING_RECEIVED", {"life_event_id": e.id})
    return service.output(e)


@router.post("/life-events/{id}/resolve")
def resolve(id: str, data: Resolve, db: DB, actor: User):
    e = get_event(db, actor, id)
    service.check_version(e, data.version)
    p = Proposal.model_validate(e.metadata_json["proposal"])
    if e.status != "APPLIED" or p.event_type in EXPECTED:
        raise HTTPException(
            409, "Apply the event first; expected receipts require explicit receipt confirmation"
        )
    if p.recurrence_rule:
        raise HTTPException(409, "Use the reminder and recurrence controls for an active subscription")
    e.status = "RESOLVED"
    e.version += 1
    e.metadata_json = {**e.metadata_json, "resolution_note": data.confirmation_note}
    db.flush()
    if p.event_type in OVERLAYS:
        invalidate(db, e.actor_id, actor.id, "FUNDING_AVAILABILITY_REVIEWED", {"life_event_id": e.id})
    record(
        db,
        actor.id,
        e.actor_id,
        "LIFE_EVENT_RESOLVED",
        "FINANCIAL",
        {"life_event_id": e.id, "balances_restored": False},
    )
    return service.output(e)


@router.post("/life-events/{id}/reminder")
def reminder(id: str, data: Version, db: DB, actor: User):
    e = get_event(db, actor, id)
    service.check_version(e, data.version)
    e.version += 1
    e.metadata_json = {**e.metadata_json, "reminder_muted": not e.metadata_json.get("reminder_muted", False)}
    record(
        db,
        actor.id,
        e.actor_id,
        "LIFE_REMINDER_CHANGED",
        "FINANCIAL",
        {"life_event_id": e.id, "external_subscription_changed": False},
    )
    return service.output(e)


@router.post("/life-events/{id}/pause-scenario")
def pause_scenario(id: str, data: Version, db: DB, actor: User):
    e = get_event(db, actor, id)
    service.check_version(e, data.version)
    p = Proposal.model_validate(e.metadata_json["proposal"])
    if not p.recurrence_rule or e.status != "APPLIED":
        raise HTTPException(409, "An applied recurring event is required")
    s = service.budget_state(db, e.actor_id)
    before = budget(s, p.currency)
    ids = e.metadata_json.get("obligation_ids", [])
    s["obligations"] = [o for o in s["obligations"] if o["id"] not in ids or o["due_date"] < as_of()]
    after = budget(s, p.currency)
    record(
        db,
        actor.id,
        e.actor_id,
        "LIFE_EVENT_SIMULATED",
        "FINANCIAL",
        {"life_event_id": e.id, "pause_scenario": True},
    )
    return {
        "before": before,
        "after": after,
        "options": [],
        "affected": [],
        "variants": [],
        "missing": [],
        "shadow_only": True,
        "effects": {
            "assumptions": [
                "Pausing is a scenario only. Contact the provider to change the actual subscription."
            ]
        },
    }


@router.post("/life-events/{id}/recurrence")
def change_recurrence(id: str, data: Confirm, db: DB, actor: User):
    e = get_event(db, actor, id)
    service.check_version(e, data.version)
    original = Proposal.model_validate(e.metadata_json["proposal"])
    p = data.proposal
    if (
        e.status != "APPLIED"
        or not original.recurrence_rule
        or p.amount_minor is None
        or p.amount_minor <= 0
        or p.currency != original.currency
        or p.recurrence_rule != original.recurrence_rule
    ):
        raise HTTPException(422, "Recurring amount changes must preserve currency and cadence")
    changed = []
    for oid in e.metadata_json.get("obligation_ids", []):
        o = db.get(Obligation, oid)
        if o and o.owner_actor_id == e.actor_id and o.status == "OPEN" and str(o.due_date) >= as_of():
            o.amount = p.amount_minor / SCALE[p.currency]
            o.version += 1
            changed.append(o.id)
    original.amount_minor = p.amount_minor
    service.store_proposal(e, original)
    e.version += 1
    e.metadata_json = {**e.metadata_json, "revision_note": data.confirmation_note}
    db.flush()
    invalidate(
        db, e.actor_id, actor.id, "RECURRING_AMOUNT_CHANGED", {"life_event_id": e.id, "obligations": changed}
    )
    record(
        db,
        actor.id,
        e.actor_id,
        "LIFE_EVENT_APPLIED",
        "FINANCIAL",
        {"life_event_id": e.id, "recurring_amount_changed": True},
    )
    return service.output(e)


@router.get("/safe-to-spend")
def safe_to_spend(db: DB, actor: User, currency: Currency = "EUR"):
    student = require_student(actor)
    return budget(service.budget_state(db, student), currency, service.active_allocations(db, student))


@router.get("/runway")
def get_runway(db: DB, actor: User):
    return runway(service.budget_state(db, require_student(actor)))


@router.get("/life-inbox")
def inbox(db: DB, actor: User, currency: Currency = "EUR"):
    student = require_student(actor)
    events = service.event_rows(db, student)
    state = service.budget_state(db, student)
    safe = budget(state, currency, service.active_allocations(db, student))
    return {
        "events": [{**service.output(e), "recurring_summary": recurring_summary(e, as_of())} for e in events],
        "budget": safe,
        "runway": runway(state),
        "notifications": reminders(state, events, safe),
    }
