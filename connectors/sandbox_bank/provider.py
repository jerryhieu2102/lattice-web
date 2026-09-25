from lattice_core.audit.service import digest


def sandbox_receipt(action_id, amount, currency):
    return {
        "receipt_id": "SIM-" + digest({"action": action_id})[:20],
        "amount": amount,
        "currency": currency,
        "environment": "SANDBOX",
        "real_money_moved": False,
    }
