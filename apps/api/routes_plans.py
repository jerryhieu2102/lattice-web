from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from apps.api.deps import DB, User, owned
from apps.api.auth import require_student
from apps.api.schemas import ScenarioInput, IntentInput
from apps.api.planning import generate, output, require_fresh, run_scenario
from lattice_core.models import Plan, ScenarioRun, ScenarioResult, InterventionCandidate
from lattice_core.state import financial_state
from lattice_core.serialization import public
from lattice_core.graph.service import graph
from lattice_core.audit.service import record
from lattice_core.permissions.service import can_view_funding, can_view_obligation
from lattice_core.models import FundingSource, Obligation
from optimizer.rescue.planner import rescue
from connectors.llm.mock import provider

router = APIRouter()


@router.post("/intent")
def intent(data: IntentInput, db: DB, actor: User):
    student = require_student(actor)
    result = provider.parse_financial_intent(data.text)
    record(
        db,
        actor.id,
        student,
        "SECURITY_BLOCK" if result["flags"] else "INTENT_PARSED",
        "SECURITY" if result["flags"] else "AI",
        result,
    )
    return result


@router.get("/graph")
def get_graph(db: DB, actor: User):
    student = actor.student_id if actor.role in {"PARENT", "SPONSOR"} else require_student(actor)
    state = financial_state(db, student, viewer_id=actor.id if actor.role in {"PARENT", "SPONSOR"} else None)
    plans = db.scalar(select(Plan).where(Plan.student_id == student).order_by(Plan.version.desc()).limit(1))
    allocations = (
        plans.summary["allocations"] if plans and plans.status not in {"STALE", "SUPERSEDED"} else []
    )
    if actor.role in {"PARENT", "SPONSOR"}:
        state["funding"] = [
            f for f in state["funding"] if can_view_funding(db, actor, db.get(FundingSource, f["id"]))
        ]
        state["obligations"] = [
            o for o in state["obligations"] if can_view_obligation(db, actor, db.get(Obligation, o["id"]))
        ]
        allocations = [
            a
            for a in allocations
            if a["funding_source_id"] in {f["id"] for f in state["funding"]}
            and a["obligation_id"] in {o["id"] for o in state["obligations"]}
        ]
    return graph(state, allocations)


@router.post("/plans/generate")
def generate_plan(db: DB, actor: User):
    return output(generate(db, require_student(actor), actor.id))


@router.get("/plans")
def plans(db: DB, actor: User):
    student = require_student(actor)
    return [
        output(p)
        for p in db.scalars(select(Plan).where(Plan.student_id == student).order_by(Plan.version.desc()))
    ]


@router.get("/plans/{id}")
def plan(id: str, db: DB, actor: User):
    return output(owned(db, Plan, id, "student_id", require_student(actor)))


@router.post("/plans/{id}/activate")
def activate(id: str, db: DB, actor: User):
    from lattice_core.permissions.service import has_permission

    p = db.get(Plan, id)
    if not p or not (
        actor.role == "ADMIN_DEMO"
        or actor.id == p.student_id
        or has_permission(db, actor.id, "PLAN", id, "APPROVE_PLAN")
    ):
        raise HTTPException(403, "Plan approval permission required")
    student = p.student_id
    require_fresh(db, p)
    for old in db.scalars(select(Plan).where(Plan.student_id == student, Plan.status == "ACTIVE")):
        old.status = "SUPERSEDED"
    p.status = "ACTIVE"
    record(
        db,
        actor.id,
        student,
        "PLAN_ACTIVATED",
        "FINANCIAL",
        {
            "plan_id": id,
            "safe": p.summary["verified_feasible"],
            "meaning": "Selected working plan; activation does not authorize payments",
        },
    )
    return (
        {"id": p.id, "status": p.status, "financial_details_redacted": True}
        if actor.role in {"PARENT", "SPONSOR"}
        else output(p)
    )


@router.post("/plans/{id}/simulate")
def simulate_plan(id: str, data: ScenarioInput, db: DB, actor: User):
    p = owned(db, Plan, id, "student_id", require_student(actor))
    return run_scenario(
        db,
        p,
        actor.id,
        data.model_dump(exclude={"plan_id", "iterations", "seed"}),
        data.iterations,
        data.seed,
    )


@router.post("/scenarios/run")
def scenario(data: ScenarioInput, db: DB, actor: User):
    if not data.plan_id:
        raise HTTPException(422, "plan_id is required")
    return simulate_plan(data.plan_id, data, db, actor)


@router.get("/scenarios/{id}")
def scenario_result(id: str, db: DB, actor: User):
    run = owned(db, ScenarioRun, id, "student_id", require_student(actor))
    result = db.scalar(select(ScenarioResult).where(ScenarioResult.run_id == id))
    return {**public(run), **result.result}


@router.post("/rescue/generate")
def generate_rescue(db: DB, actor: User):
    student = require_student(actor)
    p = db.scalar(select(Plan).where(Plan.student_id == student).order_by(Plan.version.desc()).limit(1))
    if not p:
        p = generate(db, student, actor.id)
    require_fresh(db, p)
    result = rescue(financial_state(db, student))
    for candidate in result["candidates"]:
        row = InterventionCandidate(
            student_id=student, plan_id=p.id, type=candidate["type"], result=candidate
        )
        db.add(row)
        db.flush()
        candidate["id"] = row.id
        candidate["plan_id"] = p.id
    record(
        db,
        actor.id,
        student,
        "RESCUE_EVALUATED",
        "FINANCIAL",
        {"plan_id": p.id, "candidates": len(result["candidates"]), "shortfall_eur": result["shortfall_eur"]},
    )
    return result


@router.get("/rescue/{id}")
def rescue_result(id: str, db: DB, actor: User):
    return public(owned(db, InterventionCandidate, id, "student_id", require_student(actor)))
