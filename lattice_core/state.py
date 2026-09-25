import os
from sqlalchemy import select
from lattice_core.models import Actor, FundingSource, Obligation, TransferRoute, LifeEvent
from lattice_core.serialization import public
from lattice_core.permissions.service import has_permission, can_view_funding
from lattice_core.audit.service import digest


def as_of():
    return os.getenv("DEMO_DATE", "2026-09-16")


def financial_state(db, student_id, viewer_id=None):
    funds = []
    viewer = db.get(Actor, viewer_id or student_id)
    for source in db.scalars(
        select(FundingSource).where(FundingSource.student_id == student_id).order_by(FundingSource.id)
    ):
        if not can_view_funding(db, viewer, source):
            continue
        owner = db.get(Actor, source.owner_actor_id)
        f = public(source)
        f["owner_type"] = owner.type
        f["authorized"] = owner.id == student_id or has_permission(
            db, student_id, "FUNDING", source.id, "APPROVE_OWN_FUNDS"
        )
        funds.append(f)
    state = dict(
        as_of=as_of(),
        horizon_days=45,
        funding=funds,
        obligations=[
            public(o)
            for o in db.scalars(
                select(Obligation).where(Obligation.owner_actor_id == student_id).order_by(Obligation.id)
            )
        ],
        routes=[public(r) for r in db.scalars(select(TransferRoute).order_by(TransferRoute.id))],
    )

    if viewer.role in {"STUDENT", "ADMIN_DEMO"}:
        events = list(
            db.scalars(select(LifeEvent).where(LifeEvent.actor_id == student_id).order_by(LifeEvent.id))
        )
        pending = []
        for event in events:
            meta = event.metadata_json
            if event.status == "CONFIRMED" and meta["proposal"]["mode"] != "HYPOTHETICAL":
                pending.append({"id": event.id, "version": event.version})
            overlay = meta.get("overlay") if event.status == "APPLIED" else None
            if overlay:
                for f in state["funding"]:
                    if f["id"] != overlay["funding_source_id"]:
                        continue
                    if "available_from" in overlay:
                        f["available_from"] = max(f["available_from"], overlay["available_from"])
                    if "amount" in overlay:
                        f["amount"] = min(f["amount"], overlay["amount"])
                        f["minimum_remaining_balance"] = min(f["amount"], f["minimum_remaining_balance"])
                    if "availability_status" in overlay:
                        f["availability_status"] = "LOCKED"
        if pending:
            state["pending_life_events"] = pending
    return state


def state_hash(state):
    return digest(state)
