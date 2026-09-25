from datetime import date
from decimal import Decimal
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from apps.api.deps import DB, User, owned
from apps.api.auth import require_student
from apps.api.schemas import ActionInput, Confirmation
from apps.api.planning import require_fresh, invalidate, generate
from lattice_core.models import (
    Plan,
    PreparedAction,
    Obligation,
    FundingSource,
    InterventionCandidate,
    Actor,
    now,
)
from lattice_core.state import financial_state, state_hash
from lattice_core.serialization import public
from lattice_core.policy.engine import payment_block_reason, may_approve, may_execute
from lattice_core.audit.service import record
from connectors.sandbox_bank.provider import sandbox_receipt

router = APIRouter()


def blocked(db, actor, student, reason, action=None):
    if action:
        action.status = "BLOCKED"
    record(
        db,
        actor.id,
        student,
        "ACTION_BLOCKED",
        "SECURITY",
        {"reason": reason, "action_id": action.id if action else None},
    )
    db.commit()  # A rejected request must not roll back its security event.
    raise HTTPException(409, reason)


def visible(action, actor):
    return (
        actor.role == "ADMIN_DEMO"
        or actor.id == action.student_id
        or actor.id in action.payload["required_approvals"]
    )


def action_output(action, actor):
    if actor.role in {"PARENT", "SPONSOR"}:
        return {
            "id": action.id,
            "type": action.type,
            "status": action.status,
            "environment": "SANDBOX",
            "contribution_eur": action.payload.get("candidate", {}).get("family_contribution_eur", 0),
            "required_approvals": [actor.id],
            "approvals": [x for x in action.payload.get("approvals", []) if x == actor.id],
        }
    return {**public(action), "environment": "SANDBOX"}


@router.get("/actions")
def actions(db: DB, actor: User):
    return [
        action_output(a, actor)
        for a in db.scalars(select(PreparedAction).order_by(PreparedAction.created_at.desc()))
        if visible(a, actor)
    ]


@router.post("/actions/prepare")
def prepare(data: ActionInput, db: DB, actor: User):
    student = require_student(actor)
    plan = owned(db, Plan, data.plan_id, "student_id", student)
    state = financial_state(db, student)
    payload = {"required_approvals": [student], "approvals": [], "environment": "SANDBOX"}
    if data.type in {"TUITION_PAYMENT", "SCHEDULE_TRANSFER"}:
        obligation = owned(db, Obligation, data.obligation_id, "owner_actor_id", student)
        reason = payment_block_reason(public(obligation), plan.summary, state)
        if reason:
            blocked(db, actor, student, reason)
        allocation = [a for a in plan.summary["allocations"] if a["obligation_id"] == obligation.id]
        payload.update(
            beneficiary=obligation.beneficiary, obligation_version=obligation.version, allocations=allocation
        )
        owners = {db.get(FundingSource, a["funding_source_id"]).owner_actor_id for a in allocation}
        payload["required_approvals"] = sorted(owners | {student})
    else:
        candidate = owned(db, InterventionCandidate, data.candidate_id, "student_id", student)
        if candidate.plan_id != plan.id or not candidate.result["feasible"]:
            blocked(
                db, actor, student, "Rescue candidate does not belong to a feasible current plan proposal"
            )
        if data.type == "ACTIVATE_INSTALLMENT" and not candidate.result["changes"]:
            blocked(db, actor, student, "Selected candidate has no installment to activate")
        if data.type == "PARENT_FUNDING_REQUEST" and candidate.result["type"] != "INCREASE_FAMILY_TRANSFER":
            blocked(db, actor, student, "A funding request must use the family contribution candidate")
        payload["candidate"] = candidate.result
        required = set(candidate.result.get("required_actors", [student]))
        if candidate.result["family_contribution_eur"] > 0:
            required.add(candidate.result["proposed_parent_id"])
        if candidate.result["changes"]:
            required.add("admin")  # Demo-only institutional consent, explicitly simulated.
        payload["required_approvals"] = sorted(required)
    for approver_id in payload["required_approvals"]:
        approver = db.get(Actor, approver_id)
        if not approver or (approver_id not in {student, "admin"} and approver.student_id != student):
            blocked(
                db, actor, student, "Required funding owner has no established relationship with this student"
            )
    try:
        require_fresh(db, plan)
    except HTTPException:
        blocked(db, actor, student, "Plan changed; prepare a fresh proposal")
    payload["base_required_approvals"] = list(payload["required_approvals"])
    action = PreparedAction(
        student_id=student,
        requested_by=actor.id,
        type=data.type,
        plan_id=plan.id,
        obligation_id=data.obligation_id,
        funding_source_id=data.funding_source_id,
        payload=payload,
        state_hash=state_hash(state),
    )
    db.add(action)
    db.flush()
    record(
        db,
        actor.id,
        student,
        "ACTION_PREPARED",
        "ACTION",
        {
            "action_id": action.id,
            "type": action.type,
            "required_approvals": payload["required_approvals"],
            "environment": "SANDBOX",
        },
    )
    return action_output(action, actor)


@router.post("/actions/{id}/approve")
def approve(id: str, data: Confirmation, db: DB, actor: User):
    action = db.get(PreparedAction, id)
    if not action or not visible(action, actor):
        raise HTTPException(404, "Action not found")
    if not may_approve(actor.id, action.payload["required_approvals"]):
        raise HTTPException(403, "You cannot approve another actor’s funds")
    if action.status not in {"PREPARED", "APPROVED"}:
        blocked(db, actor, action.student_id, "Action is no longer awaiting approval", action)
    if action.state_hash != state_hash(financial_state(db, action.student_id)):
        blocked(db, actor, action.student_id, "Financial state changed; approval invalidated", action)
    approvals = sorted(set(action.payload["approvals"]) | {actor.id})
    action.payload = {**action.payload, "approvals": approvals}
    action.approved_by = actor.id
    if set(action.payload["required_approvals"]).issubset(approvals):
        action.status = "APPROVED"
    record(
        db,
        actor.id,
        action.student_id,
        "ACTION_APPROVED",
        "ACTION",
        {"action_id": id, "status": action.status},
    )
    return action_output(action, actor)


@router.post("/actions/{id}/sandbox-execute")
def execute(id: str, db: DB, actor: User):
    student = require_student(actor)
    action = owned(db, PreparedAction, id, "student_id", student)
    if action.executed_at:
        raise HTTPException(409, "Action already executed; duplicate execution refused")
    if not may_execute(action.payload["required_approvals"], action.payload["approvals"], action.status):
        blocked(db, actor, student, "All required approvals must be present before sandbox execution")
    if action.state_hash != state_hash(financial_state(db, student)):
        blocked(db, actor, student, "State or permissions changed; approved proposal invalidated", action)
    receipt = None
    if action.type in {"TUITION_PAYMENT", "SCHEDULE_TRANSFER"}:
        o = owned(db, Obligation, action.obligation_id, "owner_actor_id", student)
        if (
            o.security_hold
            or o.beneficiary != action.payload["beneficiary"]
            or o.version != action.payload["obligation_version"]
        ):
            blocked(db, actor, student, "Beneficiary or obligation changed", action)
        for a in action.payload["allocations"]:
            f = db.get(FundingSource, a["funding_source_id"])
            debit = Decimal(str(a["source_amount"])) + Decimal(str(a["estimated_fee"]))
            if f.amount - debit < f.minimum_remaining_balance:
                blocked(db, actor, student, "Protected reserve or balance would be violated", action)
            f.amount -= debit
        o.status = "SANDBOX_PAID"
        receipt = sandbox_receipt(action.id, float(o.amount), o.currency)
    else:
        c = action.payload["candidate"]
        for change in c["changes"]:
            o = owned(db, Obligation, change["obligation_id"], "owner_actor_id", student)
            option = change["option"]
            part2 = Obligation(
                owner_actor_id=student,
                type=o.type,
                label=o.label + " · installment 2",
                beneficiary=o.beneficiary,
                amount=option["amounts"][1],
                currency=o.currency,
                due_date=date.fromisoformat(option["dates"][1]),
                priority=o.priority,
                verification_status="USER_CONFIRMED",
                beneficiary_verified=o.beneficiary_verified,
                confirmation_note="Simulated institutional installment acceptance.",
            )
            db.add(part2)
            o.amount = option["amounts"][0]
            o.due_date = date.fromisoformat(option["dates"][0])
            o.label += " · installment 1"
            o.installment_option = None
            o.version += 1
            if option.get("fee", 0) > 0:
                db.add(
                    Obligation(
                        owner_actor_id=student,
                        type="OTHER",
                        label="Sandbox installment fee",
                        beneficiary=o.beneficiary,
                        amount=option["fee"],
                        currency=o.currency,
                        due_date=o.due_date,
                        priority="CRITICAL",
                        verification_status="USER_CONFIRMED",
                        beneficiary_verified=True,
                        confirmation_note="Simulated institution fee.",
                    )
                )
        for change in c.get("deadline_changes", []):
            o = owned(db, Obligation, change["obligation_id"], "owner_actor_id", student)
            o.due_date = date.fromisoformat(change["due_date"])
            o.version += 1
        for change in c.get("funding_changes", []):
            f = owned(db, FundingSource, change["funding_source_id"], "student_id", student)
            f.available_from = date.fromisoformat(change["available_from"])
        for change in c.get("reserve_changes", []):
            f = owned(db, FundingSource, change["funding_source_id"], "owner_actor_id", student)
            f.restriction_type = "UNRESTRICTED"
            f.minimum_remaining_balance = 0
        if c["family_contribution_eur"] > 0:
            # The bank connector returns a fictional receipt only after all actors approve.
            receipt = sandbox_receipt(action.id, c["family_contribution_eur"], "EUR")
            db.add(
                FundingSource(
                    owner_actor_id=student,
                    student_id=student,
                    source_type="PARENT_SUPPORT",
                    label="SANDBOX received family contribution",
                    amount=c["family_contribution_eur"],
                    currency="EUR",
                    available_from=date.fromisoformat(financial_state(db, student)["as_of"]),
                    availability_status="AVAILABLE",
                    verification_status="USER_CONFIRMED",
                    restriction_type="UNRESTRICTED",
                    minimum_remaining_balance=0,
                    confirmation_note="Explicit approval plus simulated receipt " + receipt["receipt_id"],
                )
            )
    action.status = "EXECUTED"
    action.level = "P3_SANDBOX_EXECUTE"
    action.executed_at = now()
    db.flush()
    invalidate(db, student, actor.id, "SANDBOX_STATE_CHANGED", {"action_id": id}, replan=False)
    new_plan = generate(db, student, actor.id)
    record(
        db,
        actor.id,
        student,
        "PLAN_REPAIRED"
        if action.type not in {"TUITION_PAYMENT", "SCHEDULE_TRANSFER"}
        else "SANDBOX_EXECUTED",
        "ACTION",
        {"action_id": id, "plan_id": new_plan.id, "receipt": receipt, "real_money_moved": False},
    )
    return {
        "action": action_output(action, actor),
        "new_plan_id": new_plan.id,
        "receipt": receipt,
        "real_money_moved": False,
    }
