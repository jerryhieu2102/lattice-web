"""Internal, clock-based reminders; no external notification or cancellation provider."""

from datetime import timedelta
from lattice_core.currencies import SCALE
from lattice_core.life.schemas import Proposal
from lattice_core.life.effects import recurrence_dates, EXPECTED, OVERLAYS
from optimizer.model.solver import day


def reminders(state, events, budget):
    today = day(state["as_of"])
    result = []
    for o in state["obligations"]:
        if (
            o["status"] == "OPEN"
            and o["priority"] in {"CRITICAL", "HIGH"}
            and day(o["due_date"]) <= today + timedelta(days=7)
        ):
            result.append(
                {
                    "id": o["id"],
                    "type": "COMMITMENT_DUE",
                    "title": o["label"],
                    "date": o["due_date"],
                    "href": "/commitments",
                }
            )
    tracked_funds = {e.linked_funding_source_id for e in events if e.linked_funding_source_id}
    for f in state["funding"]:
        if f["id"] in tracked_funds or f["restriction_type"] == "EMERGENCY":
            continue
        if (
            f["availability_status"] in {"PLANNED", "EXPECTED", "CONDITIONAL"}
            and day(f["available_from"]) < today
        ):
            result.append(
                {
                    "id": f["id"],
                    "type": "EXPECTED_RECEIPT_OVERDUE",
                    "title": f["label"],
                    "date": f["available_from"],
                    "href": "/funding",
                }
            )
        elif f["availability_status"] in {"LOCKED", "DISPUTED"}:
            result.append(
                {
                    "id": f["id"],
                    "type": "FUNDING_AT_RISK",
                    "title": f["label"],
                    "date": state["as_of"],
                    "href": "/funding",
                }
            )
    for e in events:
        if e.status in {"DISMISSED", "RESOLVED"} or e.metadata_json.get("reminder_muted"):
            continue
        p = Proposal.model_validate(e.metadata_json["proposal"])
        if (
            p.event_type in EXPECTED
            and (p.expected_date or p.event_date)
            and (p.expected_date or p.event_date) < today
        ):
            result.append(
                {
                    "id": e.id,
                    "type": "EXPECTED_RECEIPT_OVERDUE",
                    "title": p.title,
                    "date": str(p.expected_date or p.event_date),
                    "href": "/life",
                }
            )
        if p.event_type in OVERLAYS and e.status == "APPLIED":
            result.append(
                {
                    "id": e.id,
                    "type": "FUNDING_AT_RISK",
                    "title": p.title,
                    "date": str(p.event_date or today),
                    "href": "/life",
                }
            )
        if p.recurrence_rule and p.event_date and e.status == "APPLIED":
            dates = [
                d
                for d in recurrence_dates(p.event_date, p.recurrence_rule, state["as_of"])
                if day(d) >= today
            ]
            if dates and day(dates[0]) <= today + timedelta(days=1):
                result.append(
                    {"id": e.id, "type": "RENEWAL_DUE", "title": p.title, "date": dates[0], "href": "/life"}
                )
        impact = e.metadata_json.get("impact")
        if (
            impact
            and impact.get("after")
            and impact["after"]["today"] < impact["before"]["today"]
            and e.status in {"CONFIRMED", "APPLIED"}
        ):
            result.append(
                {
                    "id": e.id + "-budget",
                    "type": "SAFE_BUDGET_DECREASED",
                    "title": p.title,
                    "date": state["as_of"],
                    "href": "/life",
                }
            )
    if budget["plan_state"] != "SAFE":
        result.append(
            {
                "id": "plan-risk",
                "type": "PLAN_AT_RISK",
                "title": "Critical commitments have a verified funding gap",
                "date": state["as_of"],
                "href": "/rescue",
            }
        )
    return result


def recurring_summary(event, clock):
    p = Proposal.model_validate(event.metadata_json["proposal"])
    if not p.recurrence_rule or p.amount_minor is None or not p.currency:
        return None
    amount = p.amount_minor / SCALE[p.currency]
    annual = amount * ({"MONTHLY": 12, "WEEKLY": 52, "YEARLY": 1}[p.recurrence_rule])
    dates = recurrence_dates(p.event_date, p.recurrence_rule, clock) if p.event_date else []
    upcoming = [d for d in dates if d >= clock]
    return {
        "monthly_cost": round(annual / 12, 2),
        "annual_cost": annual,
        "currency": p.currency,
        "next_renewal": upcoming[0] if upcoming else None,
        "materialized_horizon_days": 365,
    }
