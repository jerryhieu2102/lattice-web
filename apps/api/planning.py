from datetime import date
from sqlalchemy import select, func
from fastapi import HTTPException
from lattice_core.models import Plan, PlanAllocation, PreparedAction, ScenarioRun, ScenarioResult
from lattice_core.state import financial_state, state_hash
from lattice_core.audit.service import record
from lattice_core.serialization import public
from optimizer.model.solver import optimize
from simulation.scenarios.engine import simulate
from connectors.llm.mock import provider


def generate(db, student_id, actor_id):
    state = financial_state(db, student_id)
    result = optimize(state)
    version = (db.scalar(select(func.max(Plan.version)).where(Plan.student_id == student_id)) or 0) + 1
    plan = Plan(
        student_id=student_id,
        version=version,
        status="DRAFT" if result.get("feasible") else "FAILED",
        state_hash=state_hash(state),
        summary=result,
        snapshot=state,
        objective_value=result.get("objective_value", 0),
        total_estimated_cost=result.get("total_estimated_cost", 0),
    )
    db.add(plan)
    db.flush()
    for a in result["allocations"]:
        db.add(
            PlanAllocation(
                plan_id=plan.id,
                **{
                    k: v
                    for k, v in a.items()
                    if k
                    in {
                        "funding_source_id",
                        "obligation_id",
                        "transfer_route_id",
                        "source_amount",
                        "destination_amount",
                        "estimated_fee",
                        "status",
                    }
                },
                scheduled_date=date.fromisoformat(a["scheduled_date"]),
                expected_arrival_date=date.fromisoformat(a["expected_arrival_date"]),
            )
        )
    record(
        db,
        actor_id,
        student_id,
        "PLAN_GENERATED",
        "FINANCIAL",
        {
            "plan_id": plan.id,
            "version": version,
            "solver_status": result["solver_status"],
            "verified_feasible": result.get("verified_feasible", False),
        },
    )
    return plan


def output(plan):
    return {**public(plan), "explanation": provider.explain_plan(plan.summary)}


def require_fresh(db, plan):
    if plan.status in {"STALE", "SUPERSEDED"} or plan.state_hash != state_hash(
        financial_state(db, plan.student_id)
    ):
        raise HTTPException(409, "Plan is stale. Generate a new plan before action.")


def run_scenario(db, plan, actor_id, parameters, iterations=1000, seed=17):
    require_fresh(db, plan)
    result = simulate(plan.snapshot, plan.summary, parameters, iterations, seed)
    run = ScenarioRun(
        student_id=plan.student_id, plan_id=plan.id, parameters=parameters, seed=seed, iterations=iterations
    )
    db.add(run)
    db.flush()
    db.add(ScenarioResult(run_id=run.id, result=result))
    plan.stress_failure_rate = result["scenario_failure_rate"]
    record(
        db,
        actor_id,
        plan.student_id,
        "SCENARIO_RUN",
        "FINANCIAL",
        {
            "run_id": run.id,
            "iterations": iterations,
            "scenario_failure_rate": result["scenario_failure_rate"],
        },
    )
    return {"id": run.id, **result}


def invalidate(db, student_id, actor_id, event, details, replan=True):
    invalidated = []
    for plan in db.scalars(
        select(Plan).where(Plan.student_id == student_id, Plan.status.in_(["ACTIVE", "DRAFT", "FAILED"]))
    ):
        plan.status = "STALE"
        invalidated.append(plan.id)
    for action in db.scalars(
        select(PreparedAction).where(
            PreparedAction.student_id == student_id, PreparedAction.status.in_(["PREPARED", "APPROVED"])
        )
    ):
        action.status = "BLOCKED"
    db.flush()
    record(
        db,
        actor_id,
        student_id,
        "PLAN_INVALIDATED",
        "FINANCIAL",
        {"trigger": event, "plan_ids": invalidated, **details},
    )
    replacement = generate(db, student_id, actor_id) if replan and invalidated else None
    scenario = run_scenario(db, replacement, actor_id, {}, 100) if replacement else None
    return {
        "invalidated_plan_ids": invalidated,
        "replacement_plan": output(replacement) if replacement else None,
        "scenario": scenario,
    }
