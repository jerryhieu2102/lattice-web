"""Capability decisions are code, never model output."""


def payment_block_reason(obligation, plan, state):
    if state.get("pending_life_events"):
        return "Apply or dismiss confirmed life events before preparing a payment"
    if obligation.get("budget_only"):
        return "Budget commitment has no verified payment beneficiary; payment blocked"
    if obligation.get("security_hold") or not obligation.get("beneficiary_verified"):
        return "Beneficiary verification is required; payment blocked"
    coverage = next((c for c in plan["coverage"] if c["obligation_id"] == obligation["id"]), None)
    if not coverage or coverage["on_time_verified"] < 1:
        return "Full on-time verified coverage is required before preparing payment"
    if obligation["verification_status"] not in {"USER_CONFIRMED", "SOURCE_VERIFIED"}:
        return "Obligation is not verified"
    if obligation["status"] != "OPEN":
        return "Obligation is not open"
    return None


def may_approve(actor_id, required):
    return actor_id in required


def may_execute(required, approvals, status):
    return status == "APPROVED" and set(required).issubset(approvals)
