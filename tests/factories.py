def state(amount=1200, owed=1000):
    return {
        "as_of": "2026-09-16",
        "horizon_days": 45,
        "funding": [
            {
                "id": "f1",
                "owner_actor_id": "s",
                "owner_type": "STUDENT",
                "source_type": "STUDENT_BALANCE",
                "label": "Balance",
                "amount": amount,
                "currency": "EUR",
                "available_from": "2026-09-16",
                "availability_status": "AVAILABLE",
                "verification_status": "USER_CONFIRMED",
                "restriction_type": "UNRESTRICTED",
                "minimum_remaining_balance": 0,
                "authorized": True,
            }
        ],
        "obligations": [
            {
                "id": "o1",
                "owner_actor_id": "s",
                "label": "Tuition",
                "type": "TUITION",
                "amount": owed,
                "currency": "EUR",
                "due_date": "2026-09-30",
                "priority": "CRITICAL",
                "verification_status": "USER_CONFIRMED",
                "beneficiary_verified": True,
                "beneficiary": "ABC123",
                "security_hold": False,
                "status": "OPEN",
                "installment_option": None,
            }
        ],
        "routes": [
            {
                "id": "r1",
                "provider_name": "Local demo",
                "from_currency": "EUR",
                "to_currency": "EUR",
                "fixed_fee": 0,
                "percentage_fee": 0,
                "fx_rate": 1,
                "fx_markup": 0,
                "min_transfer": 0,
                "max_transfer": 10000000,
                "settlement_p50_days": 0,
                "settlement_p95_days": 0,
                "availability": "AVAILABLE",
                "verification_status": "SOURCE_VERIFIED",
            }
        ],
    }
