"""Finite intervention search. Feasibility is conditional on disclosed approvals and receipt."""

import os
from copy import deepcopy
from datetime import timedelta
from optimizer.model.solver import optimize, day, BASE_RATE
from simulation.scenarios.engine import simulate


def apply_installment(state):
    changes = []
    for o in list(state["obligations"]):
        option = o.get("installment_option")
        if not option or o["status"] != "OPEN":
            continue
        original = deepcopy(o)
        o.update(
            amount=option["amounts"][0],
            due_date=option["dates"][0],
            label=original["label"] + " · installment 1",
            installment_option=None,
        )
        state["obligations"].append(
            dict(
                original,
                id=original["id"] + "-part2",
                amount=option["amounts"][1],
                due_date=option["dates"][1],
                label=original["label"] + " · installment 2",
                installment_option=None,
            )
        )
        if option.get("fee", 0) > 0:
            state["obligations"].append(
                dict(
                    original,
                    id=original["id"] + "-installment-fee",
                    amount=option["fee"],
                    due_date=option["dates"][0],
                    label="Sandbox installment fee",
                    type="OTHER",
                    installment_option=None,
                )
            )
        changes.append({"obligation_id": original["id"], "currency": original["currency"], "option": option})
    return changes


def variants(state):
    """Each candidate changes only the fields disclosed in its proposal."""
    yield "REALLOCATE_UNRESTRICTED_FUNDS", deepcopy(state), {}, []
    trial = deepcopy(state)
    changes = apply_installment(trial)
    if changes:
        yield (
            "USE_INSTALLMENT_OPTION",
            trial,
            {"changes": changes},
            [
                "Institution accepts the installment schedule; every deferred payment remains visible, including beyond the planning horizon."
            ],
        )
    trial = deepcopy(state)
    released = []
    for f in trial["funding"]:
        if f["restriction_type"] == "EMERGENCY" and f.get("owner_type") == "STUDENT":
            released.append(
                {
                    "funding_source_id": f["id"],
                    "owner_actor_id": f["owner_actor_id"],
                    "amount": float(f["amount"]),
                    "currency": f["currency"],
                }
            )
            f.update(restriction_type="UNRESTRICTED", minimum_remaining_balance=0)
    if released:
        yield (
            "USE_RESERVE_WITH_APPROVAL",
            trial,
            {"reserve_changes": released},
            ["Student explicitly releases the listed emergency reserves; no release is automatic."],
        )
    trial = deepcopy(state)
    delayed = []
    for o in trial["obligations"]:
        if o["priority"] == "OPTIONAL" and o["status"] == "OPEN":
            o["due_date"] = str(
                max(
                    day(o["due_date"]),
                    day(state["as_of"]) + timedelta(days=state.get("horizon_days", 45) + 1),
                )
            )
            delayed.append(
                {"obligation_id": o["id"], "due_date": o["due_date"], "institution_consent": False}
            )
    if delayed:
        yield (
            "DELAY_OPTIONAL_EXPENSE",
            trial,
            {"deadline_changes": delayed},
            ["Student accepts deferring the listed optional commitments; debt is retained."],
        )
    trial = deepcopy(state)
    extended = []
    horizon = day(state["as_of"]) + timedelta(days=state.get("horizon_days", 45))
    for o in trial["obligations"]:
        if o["priority"] == "CRITICAL" and o["status"] == "OPEN" and day(o["due_date"]) < horizon:
            new_date = min(horizon, day(o["due_date"]) + timedelta(days=14))
            if new_date >= day(state["as_of"]):
                o["due_date"] = str(new_date)
                extended.append(
                    {"obligation_id": o["id"], "due_date": str(new_date), "institution_consent": True}
                )
    if extended:
        yield (
            "REQUEST_DEADLINE_EXTENSION",
            trial,
            {"deadline_changes": extended},
            [
                "Institution explicitly accepts the listed deadline extensions in the sandbox. No critical debt is moved outside the planning horizon."
            ],
        )
    trial = deepcopy(state)
    accelerated = []
    for f in trial["funding"]:
        if (
            f.get("owner_type") in {"PARENT", "SPONSOR"}
            and f["availability_status"] == "PLANNED"
            and day(f["available_from"]) > day(state["as_of"])
        ):
            f["available_from"] = state["as_of"]
            accelerated.append(
                {
                    "funding_source_id": f["id"],
                    "owner_actor_id": f["owner_actor_id"],
                    "available_from": state["as_of"],
                }
            )
    if accelerated:
        yield (
            "EXPEDITE_TRANSFER",
            trial,
            {"funding_changes": accelerated},
            [
                "Funding owner confirms earlier dispatch; the optimizer still uses only existing verified routes and their settlement delays."
            ],
        )


def rescue(state):
    baseline = optimize(state, verified_only=True)
    candidates = []
    student = next((o["owner_actor_id"] for o in state["obligations"]), "student")
    for kind, trial, adjustments, assumptions in variants(state):
        changes = adjustments.get("changes", [])
        reserves = adjustments.get("reserve_changes", [])
        reserve_effect = sum(r["amount"] * BASE_RATE[r["currency"]] for r in reserves)
        direct_cost = sum(x["option"].get("fee", 0) * BASE_RATE[x["currency"]] for x in changes)
        parent = next((f for f in trial["funding"] if f.get("owner_type") == "PARENT"), None)
        contribution = dict(
            id="rescue-proposed-eur",
            owner_actor_id=parent["owner_actor_id"] if parent else "father",
            owner_type="PARENT",
            source_type="PARENT_SUPPORT",
            label="Proposed contribution, requires approval and sandbox receipt",
            amount=0,
            currency="EUR",
            available_from=trial["as_of"],
            availability_status="AVAILABLE",
            verification_status="USER_CONFIRMED",
            restriction_type="UNRESTRICTED",
            minimum_remaining_balance=0,
            authorized=True,
        )
        trial["funding"].append(contribution)
        low, high = (
            0,
            int(
                sum(float(o["amount"]) * BASE_RATE[o["currency"]] for o in trial["obligations"]) * 200
                + 100000
            ),
        )
        contribution["amount"] = high / 100
        feasible_upper = optimize(trial, verified_only=True)["verified_feasible"]
        if feasible_upper:
            while low < high:
                mid = (low + high) // 2
                contribution["amount"] = mid / 100
                if optimize(trial, verified_only=True)["verified_feasible"]:
                    high = mid
                else:
                    low = mid + 1
        contribution["amount"] = low / 100 if feasible_upper else 0
        plan = optimize(trial, verified_only=True)
        required = contribution["amount"]
        if kind == "REALLOCATE_UNRESTRICTED_FUNDS" and required:
            kind = "INCREASE_FAMILY_TRANSFER"
        friction = (
            len(changes)
            + len(adjustments.get("deadline_changes", []))
            + len(adjustments.get("funding_changes", []))
            + int(required > 0)
            + int(bool(reserves))
        )
        score = round(
            direct_cost
            + required * float(os.getenv("RESCUE_FAMILY_WEIGHT", ".08"))
            + reserve_effect * float(os.getenv("RESCUE_RESERVE_WEIGHT", ".15"))
            + friction * float(os.getenv("RESCUE_FRICTION_WEIGHT", "10")),
            2,
        )
        actors = {student}
        if required:
            actors.add(contribution["owner_actor_id"])
            assumptions.append(
                "Parent explicitly approves the additional EUR contribution and the sandbox connector confirms receipt before use. This is not a live cross-border quote."
            )
        if changes or any(c["institution_consent"] for c in adjustments.get("deadline_changes", [])):
            actors.add("admin")
        actors.update(c["owner_actor_id"] for c in adjustments.get("funding_changes", []))
        simulation = (
            simulate(trial, plan, {"transfer_delay": 3, "fx_shock": 3}, 100) if plan["allocations"] else None
        )
        candidates.append(
            dict(
                type=kind,
                feasible=plan["verified_feasible"],
                conditional=bool(assumptions),
                title=kind.replace("_", " ").title(),
                family_contribution_eur=round(required, 2),
                direct_cost_eur=round(direct_cost, 2),
                reserve_impact_eur=round(reserve_effect, 2),
                friction=friction,
                people_involved=len(actors),
                required_actors=sorted(actors),
                score=score,
                assumptions=assumptions,
                changes=changes,
                reserve_release=bool(reserves),
                reserve_changes=reserves,
                deadline_changes=adjustments.get("deadline_changes", []),
                funding_changes=adjustments.get("funding_changes", []),
                proposed_parent_id=contribution["owner_actor_id"],
                coverage=plan["coverage"],
                scenario_failure_rate=simulation["scenario_failure_rate"] if simulation else 1,
                total_estimated_cost=plan["total_estimated_cost"],
                search_scope="Minimum score among enumerated intervention bundles; family amount minimized to one euro cent per bundle",
            )
        )
    candidates.sort(key=lambda c: (not c["feasible"], c["score"], c["type"]))
    return {
        "shortfall_eur": baseline["objective_value"],
        "candidates": candidates,
        "best_index": 0 if candidates and candidates[0]["feasible"] else None,
    }
