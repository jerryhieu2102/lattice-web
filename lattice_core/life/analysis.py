from lattice_core.currencies import SCALE, BASE_RATE
from lattice_core.life.budget import budget, runway
from lattice_core.life.effects import transform, missing_fields
from optimizer.rescue.planner import rescue
from optimizer.model.solver import day


def analyze(state, p, active=None):
    currency = p.currency or "EUR"
    before = budget(state, currency, active)
    missing = missing_fields(p)
    if missing:
        return {
            "before": before,
            "after": None,
            "missing": missing,
            "options": [],
            "variants": [],
            "runway": runway(state),
        }
    cases = [("EXPECTED_CASE", p.amount_minor, p.event_date)]
    if p.amount_min_minor is not None or p.date_window_start:
        lo = p.amount_min_minor if p.amount_min_minor is not None else p.amount_minor
        hi = p.amount_max_minor if p.amount_max_minor is not None else p.amount_minor
        cases = [
            ("BEST_CASE", lo, p.event_date or p.date_window_end),
            (
                "EXPECTED_CASE",
                (lo + hi) // 2 if lo is not None and hi is not None else None,
                p.event_date or p.date_window_start,
            ),
            ("WORST_CASE", hi, p.event_date or p.date_window_start),
        ]
    variants = []
    for label, amount, when in cases:
        proposal = p.model_copy(update={"amount_minor": amount, "event_date": when})
        shadow, changes = transform(state, proposal)
        after = budget(shadow, currency, active)
        if changes["cash_gap_eur"]:
            after["plan_state"] = "BLOCKED"
        variants.append(
            {
                "label": label,
                "amount_minor": amount,
                "event_date": str(when or state["as_of"]),
                "after": after,
                "effects": changes,
            }
        )
    middle = variants[min(1, len(variants) - 1)]
    after = middle["after"]
    affected = []
    old = {c["obligation_id"]: c for c in before["coverage"]}
    for c in after["coverage"]:
        prior = old.get(c["obligation_id"], {})
        if c["on_time_verified"] < prior.get("on_time_verified", 1) or c["shortfall"] > prior.get(
            "shortfall", 0
        ):
            affected.append({**c, "before_coverage": prior.get("on_time_verified", 1)})
    options = [
        {"type": "LOWER_BUDGET", "amount": before["today"], "currency": currency},
        {
            "type": "SAVE_TOWARD_PURCHASE",
            "amount": min(before["today"], (p.amount_minor or 0) / SCALE[currency]),
            "currency": currency,
        },
    ]
    if (
        after["plan_state"] == "SAFE"
        and (p.amount_minor or 0) > 0
        and p.event_type in {"PURCHASE_INTENT", "TRAVEL_PLAN"}
    ):
        options.insert(
            0, {"type": "BUY_NOW", "currency": currency, "amount": (p.amount_minor or 0) / SCALE[currency]}
        )
    for key, when in zip(["this_week", "this_month"], before["dates"][1:]):
        if before[key] > before["today"]:
            options.append({"type": "CHANGE_DATE", "date": when, "amount": before[key], "currency": currency})
    expected_dates = sorted(
        {
            f["available_from"]
            for f in state["funding"]
            if f["availability_status"] in {"EXPECTED", "CONDITIONAL", "PLANNED"}
            and f["available_from"] > state["as_of"]
        }
    )
    if expected_dates:
        options.append({"type": "WAIT_FOR_VERIFICATION", "date": expected_dates[0], "conditional": True})
    if p.event_type not in {"PURCHASE_INTENT", "TRAVEL_PLAN", "SAVINGS_GOAL"} and not p.question:
        options = []
    result = {
        "before": before,
        "after": after,
        "difference": {
            "liquid_eur": round(after["liquid_eur"] - before["liquid_eur"], 2),
            "reserve_eur": round(after["reserve_eur"] - before["reserve_eur"], 2),
            "safe_to_spend": after["today"] - before["today"],
        },
        "affected": affected,
        "options": options,
        "variants": variants,
        "missing": [],
        "runway": runway(state),
        "effects": middle["effects"],
        "shadow_only": True,
    }
    if p.event_type == "EMERGENCY":
        shadow, _ = transform(
            state,
            p.model_copy(
                update={"amount_minor": middle["amount_minor"], "event_date": day(middle["event_date"])}
            ),
        )
        result["rescue"] = rescue(shadow)
    if p.event_type == "SAVINGS_GOAL":
        months = max(1, ((p.event_date or p.date_window_start) - day(state["as_of"])).days / 30)
        result["goal"] = {
            "monthly_required": round((p.amount_minor or 0) / SCALE[currency] / months, 2),
            "safe_initial_contribution": before["today"],
            "soft_goal": True,
        }
    if p.envelope:
        result["trip_total_eur"] = round(
            sum(x.amount_minor / SCALE[x.currency] * BASE_RATE[x.currency] for x in p.envelope), 2
        )
    return result
