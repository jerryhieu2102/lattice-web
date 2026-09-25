"""Pure shadow transformations. Persistence and permissions are separate responsibilities."""

import calendar
from copy import deepcopy
from datetime import timedelta
from lattice_core.currencies import BASE_RATE, SCALE
from lattice_core.life.budget import dec, eligible, quote_debit
from optimizer.model.solver import day

EXPENSES = {"PURCHASE_INTENT", "EXPENSE_OCCURRED", "LENDING", "TRAVEL_PLAN"}
EXPECTED = {
    "FUNDING_EXPECTED",
    "REFUND_EXPECTED",
    "REIMBURSEMENT_EXPECTED",
    "TRANSFER_PENDING",
    "FAMILY_SUPPORT",
}
OBLIGATIONS = {
    "NEW_OBLIGATION",
    "EDUCATION_EXPENSE",
    "HOUSING_EVENT",
    "HEALTH_EXPENSE",
    "EMERGENCY",
    "RECURRING_EXPENSE",
}
OVERLAYS = {"FUNDING_DELAYED", "FUNDING_REDUCED", "TRANSFER_FAILED", "ACCOUNT_UNAVAILABLE"}


def recurrence_dates(start, rule, clock):
    start, limit = day(start), day(clock) + timedelta(days=365)
    result = []
    for n in range(54):
        if rule == "WEEKLY":
            current = start + timedelta(weeks=n)
        else:
            months = n * (12 if rule == "YEARLY" else 1)
            year = start.year + (start.month - 1 + months) // 12
            month = (start.month - 1 + months) % 12 + 1
            current = start.replace(
                year=year, month=month, day=min(start.day, calendar.monthrange(year, month)[1])
            )
        if current > limit:
            break
        result.append(current.isoformat())
    return result


def major(p):
    return (p.amount_minor or 0) / SCALE[p.currency] if p.currency else 0


def obligation(id_, p, amount, when, student):
    return dict(
        id=id_,
        owner_actor_id=student,
        type="OTHER",
        label=p.title,
        beneficiary="",
        budget_only=True,
        beneficiary_verified=False,
        security_hold=False,
        amount=float(amount),
        currency=p.currency,
        due_date=str(when),
        priority=p.priority,
        status="OPEN",
        verification_status="USER_CONFIRMED",
        partial_payment_allowed=False,
        minimum_payment=0,
        version=1,
        confirmation_note="Explicitly confirmed budget commitment; no payment destination provided",
    )


def funding(id_, p, amount, when, student, received=False):
    return dict(
        id=id_,
        owner_actor_id=student,
        student_id=student,
        owner_type="STUDENT",
        authorized=True,
        source_type="OTHER",
        label=p.title,
        amount=float(amount),
        currency=p.currency,
        available_from=str(when),
        availability_status="AVAILABLE" if received else "EXPECTED",
        verification_status="USER_CONFIRMED",
        restriction_type="UNRESTRICTED",
        minimum_remaining_balance=0,
        confidence=1 if received else 0.5,
        confirmation_note="User-confirmed ledger record; no independent bank verification",
    )


def transform(state, p, event_id="shadow", student_id=None):
    s = deepcopy(state)
    student = student_id or next(
        (f["owner_actor_id"] for f in s["funding"] if f.get("owner_type") == "STUDENT"), "shadow"
    )
    when = p.event_date or p.date_window_start or day(s["as_of"])
    amount = major(p)
    changes = {
        "cash_gap_eur": 0,
        "debits": [],
        "new_funding": [],
        "new_obligations": [],
        "changed_obligations": [],
        "overlay": None,
        "assumptions": [],
    }
    if not p.event_date:
        changes["assumptions"].append(
            "Simulation date uses the selected window or planning clock; confirm the actual date before applying."
        )
    if p.security_flags or p.event_type == "SECURITY_INCIDENT":
        changes["assumptions"].append(
            "Security report cannot change a beneficiary. Verify the destination in Documents and Commitments."
        )
        if p.obligation_id:
            for o in s["obligations"]:
                if o["id"] == p.obligation_id:
                    o["security_hold"] = True
                    changes["changed_obligations"].append(o)
        return s, changes
    if amount <= 0 and not p.envelope and p.event_type not in OVERLAYS | {"OBLIGATION_CHANGED"}:
        return s, changes
    if p.event_type in EXPENSES:
        costs = (
            [(x.amount_minor / SCALE[x.currency], x.currency) for x in p.envelope]
            if p.event_type == "TRAVEL_PLAN" and p.envelope
            else [(amount, p.currency)]
        )
        for value, currency in costs:
            if not currency or value <= 0:
                continue
            options = []
            for f in s["funding"]:
                if not eligible(f, when) or (p.funding_source_id and f["id"] != p.funding_source_id):
                    continue
                q = quote_debit(s, f, value, currency, when)
                if q:
                    capacity = max(dec(0), dec(f["amount"]) - dec(f["minimum_remaining_balance"]))
                    options.append((q[0] > capacity, float(q[0]) * BASE_RATE[f["currency"]], f, q, capacity))
            if not options:
                changes["cash_gap_eur"] += value * BASE_RATE[currency]
                continue
            _, _, f, q, capacity = min(options, key=lambda x: (x[0], x[1], x[2]["id"]))
            debit = min(capacity, q[0])
            f["amount"] = float(dec(f["amount"]) - debit)
            changes["cash_gap_eur"] += float(max(dec(0), q[0] - capacity)) * BASE_RATE[f["currency"]]
            changes["debits"].append(
                {
                    "funding_source_id": f["id"],
                    "amount": float(debit),
                    "currency": f["currency"],
                    "route_id": q[1],
                    "fee": float(q[2]),
                }
            )
        if p.event_type == "EXPENSE_OCCURRED" and p.obligation_id:
            for o in s["obligations"]:
                if (
                    o["id"] == p.obligation_id
                    and o.get("budget_only")
                    and o["currency"] == p.currency
                    and dec(o["amount"]) == dec(amount)
                ):
                    o["status"] = "PAID"
                    changes["changed_obligations"].append(o)
    elif p.event_type in OBLIGATIONS:
        dates = (
            recurrence_dates(when, p.recurrence_rule, s["as_of"])
            if p.event_type == "RECURRING_EXPENSE" and p.recurrence_rule
            else [str(when)]
        )
        for index, d in enumerate(dates):
            o = obligation(f"{event_id}:o:{index}", p, amount, d, student)
            s["obligations"].append(o)
            changes["new_obligations"].append(o)
    elif p.event_type == "OBLIGATION_CHANGED":
        for o in s["obligations"]:
            if o["id"] == p.obligation_id:
                o["amount"] = float(dec(o["amount"]) + dec(amount)) if p.amount_is_delta else amount
                if p.event_date:
                    o["due_date"] = str(p.event_date)
                changes["changed_obligations"].append(o)
    elif p.event_type in EXPECTED | {"FUNDING_RECEIVED", "BORROWING"}:
        available = p.expected_date or when
        f = funding(
            f"{event_id}:f", p, amount, available, student, p.event_type in {"FUNDING_RECEIVED", "BORROWING"}
        )
        s["funding"].append(f)
        changes["new_funding"].append(f)
        if p.event_type == "BORROWING":
            debt = p.model_copy(update={"priority": "CRITICAL", "title": "Repayment"})
            o = obligation(
                f"{event_id}:debt",
                debt,
                (p.repayment_minor or p.amount_minor or 0) / SCALE[p.currency],
                p.repayment_date or when,
                student,
            )
            s["obligations"].append(o)
            changes["new_obligations"].append(o)
    elif p.event_type in OVERLAYS:
        for f in s["funding"]:
            if f["id"] != p.funding_source_id:
                continue
            overlay = {"funding_source_id": f["id"]}
            if p.event_type == "FUNDING_DELAYED" and p.delay_days:
                overlay["available_from"] = (
                    day(f["available_from"]) + timedelta(days=p.delay_days)
                ).isoformat()
            elif p.event_type == "FUNDING_REDUCED":
                overlay["amount"] = (
                    max(0, float(f["amount"]) - amount)
                    if p.amount_is_delta
                    else min(float(f["amount"]), amount)
                )
            else:
                overlay["availability_status"] = "LOCKED"
            f.update({k: v for k, v in overlay.items() if k != "funding_source_id"})
            f["minimum_remaining_balance"] = min(float(f["minimum_remaining_balance"]), float(f["amount"]))
            changes["overlay"] = overlay
    changes["cash_gap_eur"] = round(changes["cash_gap_eur"], 2)
    return s, changes


def missing_fields(p, actual=False):
    missing = []
    if p.security_flags or p.event_type == "SECURITY_INCIDENT":
        return ["Beneficiary review in Documents and Commitments"]
    if p.question or p.event_type in {"OTHER", "FX_CONCERN"}:
        return [] if not actual else ["Supported event type"]
    if p.event_type not in OVERLAYS:
        if p.amount_minor is None and not (p.envelope or (not actual and p.amount_min_minor is not None)):
            missing.append("Amount")
        if not p.currency and not p.envelope:
            missing.append("Currency")
        if p.amount_minor == 0 and p.event_type != "SAVINGS_GOAL":
            missing.append("Positive amount")
    if (
        actual
        and not (p.event_date or (p.event_type in EXPECTED and p.expected_date))
        and p.event_type not in OVERLAYS
    ):
        missing.append("Event date")
    if p.event_type in OVERLAYS or (actual and p.event_type in EXPENSES):
        if not p.funding_source_id:
            missing.append("Funding source")
    if p.event_type == "FUNDING_DELAYED" and not p.delay_days:
        missing.append("Delay days")
    if p.event_type == "FUNDING_REDUCED" and (p.amount_minor is None or not p.currency):
        missing.extend(["Amount", "Currency"])
    if p.event_type == "OBLIGATION_CHANGED" and not p.obligation_id:
        missing.append("Linked commitment")
    if p.event_type == "BORROWING" and not p.repayment_date:
        missing.append("Repayment date")
    if p.event_type == "SAVINGS_GOAL" and not (p.event_date or p.date_window_start):
        missing.append("Target date")
    if p.event_type == "RECURRING_EXPENSE" and not p.recurrence_rule:
        missing.append("Recurrence")
    return list(dict.fromkeys(missing))
