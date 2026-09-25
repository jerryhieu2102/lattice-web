"""Synthetic fixtures with an independent, one-obligation capacity oracle."""

from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
import numpy as np

SEED = 17
KINDS = (
    "insufficient",
    "exact",
    "cross_currency",
    "fast_vs_slow",
    "tomorrow",
    "delayed_scholarship",
    "protected_reserve",
    "parent_permission",
    "expected_funding",
    "unverified_funding",
    "route_minimum",
    "restricted_funding",
)


def base_state(amount=1200, owed=1000):
    return {
        "as_of": "2026-09-16",
        "horizon_days": 45,
        "funding": [
            {
                "id": "f1",
                "owner_actor_id": "student",
                "owner_type": "STUDENT",
                "source_type": "STUDENT_BALANCE",
                "label": "Synthetic balance",
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
                "owner_actor_id": "student",
                "label": "Synthetic tuition",
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
                "provider_name": "Synthetic local route",
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


def planning_cases(count, seed=SEED):
    rng = np.random.default_rng(seed)
    for i in range(count):
        owed = int(rng.integers(100, 3000))
        s = base_state(owed + 100, owed)
        f, o, r = s["funding"][0], s["obligations"][0], s["routes"][0]
        kind = KINDS[i % len(KINDS)]
        if kind == "insufficient":
            f["amount"] = owed // 2
        elif kind == "exact":
            f["amount"] = owed
        elif kind == "cross_currency":
            f["amount"] = owed // 3
            s["funding"].append(dict(f, id="usd", currency="USD", amount=owed))
            s["routes"].append(dict(r, id="usd-route", from_currency="USD", fx_rate=0.9, fixed_fee=3))
        elif kind == "fast_vs_slow":
            o["due_date"] = "2026-09-17"
            r.update(settlement_p50_days=2, settlement_p95_days=4)
            s["routes"].append(dict(r, id="fast", fixed_fee=20, settlement_p50_days=0, settlement_p95_days=0))
        elif kind == "tomorrow":
            o["due_date"] = "2026-09-17"
            r.update(settlement_p50_days=2, settlement_p95_days=4)
        elif kind == "delayed_scholarship":
            f.update(source_type="SCHOLARSHIP", available_from="2026-10-10", availability_status="EXPECTED")
        elif kind == "protected_reserve":
            f.update(restriction_type="EMERGENCY", minimum_remaining_balance=f["amount"])
        elif kind == "parent_permission":
            f.update(owner_type="PARENT", owner_actor_id="father", authorized=False)
        elif kind == "expected_funding":
            f.update(source_type="SCHOLARSHIP", availability_status="EXPECTED")
        elif kind == "unverified_funding":
            f["verification_status"] = "EXTRACTED"
        elif kind == "route_minimum":
            r["min_transfer"] = f["amount"] + 1
        elif kind == "restricted_funding":
            f["restriction_type"] = "TUITION_ONLY"
            o["type"] = "RENT"
        yield kind, s


def capacity_oracle(state, certain=False):
    """Independent Decimal arithmetic, no optimizer helper imports.

    Dataset scope: one obligation, unlimited single-route capacity per source;
    at most two alternative routes. It is not an oracle for arbitrary graphs.
    """
    o = state["obligations"][0]
    total = Decimal(0)
    for f in state["funding"]:
        if f["verification_status"] not in {"USER_CONFIRMED", "SOURCE_VERIFIED"}:
            continue
        if f["availability_status"] in {"LOCKED", "DISPUTED", "CANCELLED"}:
            continue
        if certain and f["availability_status"] not in {"AVAILABLE", "PLANNED"}:
            continue
        if f["restriction_type"] == "EMERGENCY" or (
            f["restriction_type"] == "TUITION_ONLY" and o["type"] != "TUITION"
        ):
            continue
        if f["owner_type"] in {"PARENT", "SPONSOR"} and not f["authorized"]:
            continue
        budget = Decimal(str(f["amount"])) - Decimal(str(f["minimum_remaining_balance"]))
        capacities = [Decimal(0)]
        for r in state["routes"]:
            if (r["from_currency"], r["to_currency"]) != (f["currency"], o["currency"]):
                continue
            arrival = max(
                date.fromisoformat(state["as_of"]), date.fromisoformat(f["available_from"])
            ) + timedelta(days=r["settlement_p95_days"])
            if arrival > date.fromisoformat(o["due_date"]):
                continue
            quantum = Decimal(1) if f["currency"] == "VND" else Decimal(".01")
            p = min(
                Decimal(str(r["max_transfer"])),
                (budget - Decimal(str(r["fixed_fee"]))) / (1 + Decimal(str(r["percentage_fee"]))),
            )
            p = p.quantize(quantum, rounding=ROUND_FLOOR)
            fee = (p * Decimal(str(r["percentage_fee"]))).quantize(quantum, rounding=ROUND_CEILING) + Decimal(
                str(r["fixed_fee"])
            )
            if p + fee > budget:
                p -= quantum
            if p < max(quantum, Decimal(str(r["min_transfer"]))):
                continue
            capacities.append(
                (p * Decimal(str(r["fx_rate"])) * (1 - Decimal(str(r["fx_markup"])))).quantize(
                    Decimal(".01"), rounding=ROUND_FLOOR
                )
            )
        total += max(capacities)
    return float(min(total, Decimal(str(o["amount"]))) / Decimal(str(o["amount"])))


def replanning_case(index):
    s = base_state(1700 + index % 5 * 10, 3200)
    s["obligations"][0]["installment_option"] = {
        "amounts": [1600, 1600],
        "dates": ["2026-09-30", "2026-11-15"],
        "fee": 20,
    }
    s["funding"].append(
        dict(
            deepcopy(s["funding"][0]),
            id="scholarship",
            source_type="SCHOLARSHIP",
            amount=2000,
            availability_status="EXPECTED",
            available_from="2026-09-25",
        )
    )
    return s
