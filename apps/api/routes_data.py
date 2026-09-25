from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from apps.api.deps import DB, User, owned
from apps.api.auth import require_student, require_admin
from apps.api.schemas import (
    FundingInput,
    FundingPatch,
    ObligationInput,
    ObligationPatch,
    RouteInput,
    PermissionInput,
    BeneficiaryVerification,
    precise_amount,
)
from apps.api.planning import invalidate
from lattice_core.models import (
    FundingSource,
    Obligation,
    TransferRoute,
    Permission,
    Plan,
    PreparedAction,
    Actor,
    now,
)
from lattice_core.serialization import public
from lattice_core.permissions.service import can_view_obligation, can_view_funding
from lattice_core.audit.service import record

router = APIRouter()


@router.get("/funding-sources")
def funds(db: DB, actor: User):
    return [public(f) for f in db.scalars(select(FundingSource)) if can_view_funding(db, actor, f)]


@router.post("/funding-sources")
def add_fund(data: FundingInput, db: DB, actor: User):
    student = actor.student_id if actor.role in {"PARENT", "SPONSOR"} else require_student(actor)
    f = FundingSource(
        **data.model_dump(),
        owner_actor_id=actor.id if actor.role != "ADMIN_DEMO" else student,
        student_id=student,
        verification_status="USER_CONFIRMED",
    )
    db.add(f)
    db.flush()
    change = invalidate(db, student, actor.id, "FUNDING_CHANGED", {"funding_source_id": f.id})
    return {
        "funding": public(f),
        **({"financial_state_updated": True} if actor.role in {"PARENT", "SPONSOR"} else change),
    }


@router.patch("/funding-sources/{id}")
def patch_fund(id: str, data: FundingPatch, db: DB, actor: User):
    f = db.get(FundingSource, id)
    if not f or (f.owner_actor_id != actor.id and actor.role != "ADMIN_DEMO"):
        raise HTTPException(404, "Funding source not found")
    if data.amount is not None and data.amount < float(f.minimum_remaining_balance):
        raise HTTPException(422, "Protected reserve cannot be reduced")
    merged = {key: getattr(f, key) for key in FundingInput.model_fields}
    merged.update(data.model_dump(exclude_none=True))
    try:
        FundingInput.model_validate(merged)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(f, key, value)
    db.flush()
    change = invalidate(
        db,
        f.student_id,
        actor.id,
        "SCHOLARSHIP_DELAYED"
        if f.source_type == "SCHOLARSHIP" and data.available_from
        else "FUNDING_CANCELLED"
        if data.availability_status == "LOCKED"
        else "FUNDING_CHANGED",
        {"funding_source_id": id},
    )
    return {
        "funding": public(f),
        **({"financial_state_updated": True} if actor.role in {"PARENT", "SPONSOR"} else change),
    }


@router.get("/obligations")
def obligations(db: DB, actor: User):
    return [public(o) for o in db.scalars(select(Obligation)) if can_view_obligation(db, actor, o)]


@router.get("/obligations/{id}")
def obligation(id: str, db: DB, actor: User):
    o = db.get(Obligation, id)
    if not o or not can_view_obligation(db, actor, o):
        raise HTTPException(404, "Obligation not found")
    return public(o)


@router.post("/obligations")
def add_obligation(data: ObligationInput, db: DB, actor: User):
    student = require_student(actor)
    o = Obligation(
        **data.model_dump(),
        owner_actor_id=student,
        verification_status="USER_CONFIRMED",
        beneficiary_verified=True,
    )
    db.add(o)
    db.flush()
    return {
        "obligation": public(o),
        **invalidate(db, student, actor.id, "NEW_OBLIGATION", {"obligation_id": o.id}),
    }


@router.patch("/obligations/{id}")
def patch_obligation(id: str, data: ObligationPatch, db: DB, actor: User):
    student = require_student(actor)
    o = owned(db, Obligation, id, "owner_actor_id", student)
    if data.amount is not None:
        try:
            precise_amount(data.amount, o.currency)
        except ValueError as error:
            raise HTTPException(422, str(error)) from None
    if data.amount is not None and data.amount < float(o.minimum_payment):
        raise HTTPException(422, "Amount is below minimum payment")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(o, key, value)
    o.version += 1
    db.flush()
    return {
        "obligation": public(o),
        **invalidate(
            db,
            student,
            actor.id,
            "AMOUNT_CHANGED" if data.amount is not None else "DEADLINE_CHANGED",
            {"obligation_id": id},
        ),
    }


@router.post("/obligations/{id}/verify-beneficiary")
def verify_beneficiary(id: str, data: BeneficiaryVerification, db: DB, actor: User):
    student = require_student(actor)
    o = owned(db, Obligation, id, "owner_actor_id", student)
    old = o.beneficiary
    o.beneficiary = data.beneficiary
    o.beneficiary_verified = True
    o.security_hold = False
    o.version += 1
    o.confirmation_note = data.confirmation_note
    record(
        db,
        actor.id,
        student,
        "BENEFICIARY_USER_CONFIRMED",
        "SECURITY",
        {
            "obligation_id": id,
            "previous": old,
            "new": o.beneficiary,
            "authority": "T0 explicit user attestation, no external bank verification",
        },
    )
    return invalidate(db, student, actor.id, "BENEFICIARY_CHANGED", {"obligation_id": id})


@router.get("/transfer-routes")
def routes(db: DB, actor: User):
    return [public(r) for r in db.scalars(select(TransferRoute))]


@router.post("/transfer-routes")
def add_route(data: RouteInput, db: DB, actor: User):
    require_admin(actor)
    r = TransferRoute(**data.model_dump())
    db.add(r)
    db.flush()
    invalidate(db, "maya", actor.id, "FX_THRESHOLD_CROSSED", {"route_id": r.id})
    return public(r)


@router.get("/permissions")
def permissions(db: DB, actor: User):
    return [
        public(p)
        for p in db.scalars(select(Permission))
        if actor.role == "ADMIN_DEMO" or actor.id in {p.owner_actor_id, p.target_actor_id}
    ]


@router.post("/permissions")
def grant(data: PermissionInput, db: DB, actor: User):
    table = {"FUNDING": FundingSource, "OBLIGATION": Obligation, "PLAN": Plan, "ACTION": PreparedAction}
    field = {
        "FUNDING": "owner_actor_id",
        "OBLIGATION": "owner_actor_id",
        "PLAN": "student_id",
        "ACTION": "student_id",
    }
    resource = db.get(table[data.resource_type], data.resource_id)
    if not resource or getattr(resource, field[data.resource_type]) != actor.id:
        raise HTTPException(403, "Only the resource owner may grant access")
    target = db.get(Actor, data.target_actor_id)
    if not target or not (target.id == actor.student_id or target.student_id == actor.id):
        raise HTTPException(403, "Recipient is outside the established relationship")
    allowed = {
        "FUNDING": {"VIEW_OWN_CONTRIBUTION", "APPROVE_OWN_FUNDS", "VIEW_PRIVATE_FINANCES"},
        "OBLIGATION": {"VIEW_SHARED_OBLIGATION"},
        "PLAN": {"APPROVE_PLAN"},
        "ACTION": {"APPROVE_ACTION"},
    }
    if data.permission_type not in allowed[data.resource_type]:
        raise HTTPException(422, "Permission does not match resource type")
    p = Permission(**data.model_dump(), owner_actor_id=actor.id)
    db.add(p)
    db.flush()
    student = resource.student_id if hasattr(resource, "student_id") else resource.owner_actor_id
    record(db, actor.id, student, "PERMISSION_GRANTED", "PERMISSION", data.model_dump())
    if data.permission_type == "APPROVE_OWN_FUNDS":
        invalidate(db, student, actor.id, "PERMISSION_CHANGED", {"permission_id": p.id})
    if data.permission_type == "APPROVE_ACTION":
        refresh_action_approvers(db, resource)
    return public(p)


def refresh_action_approvers(db, action):
    if action.status not in {"PREPARED", "APPROVED"}:
        raise HTTPException(409, "Action no longer accepts permission changes")
    base = action.payload.get("base_required_approvals", action.payload["required_approvals"])
    delegated = list(
        db.scalars(
            select(Permission.target_actor_id).where(
                Permission.resource_type == "ACTION",
                Permission.resource_id == action.id,
                Permission.permission_type == "APPROVE_ACTION",
                Permission.revoked_at.is_(None),
            )
        )
    )
    action.payload = {
        **action.payload,
        "base_required_approvals": base,
        "required_approvals": sorted(set(base) | set(delegated)),
        "approvals": [],
    }
    action.status = "PREPARED"
    action.approved_by = None


@router.delete("/permissions/{id}")
def revoke(id: str, db: DB, actor: User):
    p = owned(db, Permission, id, "owner_actor_id", actor.id)
    p.revoked_at = now()
    student = actor.student_id or actor.id
    record(db, actor.id, student, "PERMISSION_REVOKED", "PERMISSION", {"permission_id": id})
    db.flush()
    if p.permission_type == "APPROVE_ACTION":
        refresh_action_approvers(db, db.get(PreparedAction, p.resource_id))
    else:
        invalidate(db, student, actor.id, "PERMISSION_CHANGED", {"permission_id": id})
    return {"revoked": True}
