"""Two-way synthetic quotes for every supported pair; no bank or FX service is called."""

from decimal import Decimal, ROUND_DOWN, ROUND_UP
from itertools import product
from sqlalchemy import select
from lattice_core.currencies import CURRENCIES, SCALE
from lattice_core.models import TransferRoute


def demo_route_data():
    legacy = [
        dict(
            id="eur-local",
            provider_name="Demo SEPA · local",
            from_currency="EUR",
            to_currency="EUR",
            fixed_fee=0,
            percentage_fee=0,
            fx_rate=1,
            fx_markup=0,
            min_transfer=0,
            max_transfer=100000,
            settlement_p50_days=0,
            settlement_p95_days=0,
        ),
        dict(
            id="vnd-standard",
            provider_name="Demo VND → EUR · standard",
            from_currency="VND",
            to_currency="EUR",
            fixed_fee=50000,
            percentage_fee=0.002,
            fx_rate=0.000036,
            fx_markup=0,
            min_transfer=0,
            max_transfer=100000000,
            settlement_p50_days=2,
            settlement_p95_days=4,
        ),
        dict(
            id="vnd-express",
            provider_name="Demo VND → EUR · express",
            from_currency="VND",
            to_currency="EUR",
            fixed_fee=150000,
            percentage_fee=0.005,
            fx_rate=0.000036,
            fx_markup=0,
            min_transfer=0,
            max_transfer=100000000,
            settlement_p50_days=1,
            settlement_p95_days=1,
        ),
        dict(
            id="usd-standard",
            provider_name="Demo USD → EUR",
            from_currency="USD",
            to_currency="EUR",
            fixed_fee=3,
            percentage_fee=0.002,
            fx_rate=0.90,
            fx_markup=0,
            min_transfer=0,
            max_transfer=100000,
            settlement_p50_days=1,
            settlement_p95_days=3,
        ),
    ]
    yield from legacy
    covered = {(r["from_currency"], r["to_currency"]) for r in legacy}
    for source, target in product(CURRENCIES, repeat=2):
        if (source, target) in covered:
            continue
        same = source == target
        source_value = Decimal(CURRENCIES[source]["eur_value"])
        target_value = Decimal(CURRENCIES[target]["eur_value"])
        rate = (source_value / target_value).quantize(Decimal(".0000000001"), rounding=ROUND_DOWN)
        fee = (
            Decimal(0)
            if same
            else (Decimal(2) / source_value * SCALE[source]).to_integral_value(rounding=ROUND_UP)
            / SCALE[source]
        )
        cap = min(Decimal(1000000000), (Decimal(50000) / source_value).to_integral_value(rounding=ROUND_DOWN))
        yield dict(
            id=f"demo-{source.lower()}-{target.lower()}",
            provider_name=f"Demo {source} → {target} · " + ("local" if same else "standard"),
            from_currency=source,
            to_currency=target,
            fixed_fee=fee,
            percentage_fee=0 if same else 0.002,
            fx_rate=rate,
            fx_markup=0,
            min_transfer=0,
            max_transfer=cap,
            settlement_p50_days=0 if same else 2,
            settlement_p95_days=0 if same else 4,
        )


def ensure_demo_routes(db):
    existing = set(db.scalars(select(TransferRoute.id)))
    rows = [TransferRoute(**row) for row in demo_route_data() if row["id"] not in existing]
    db.add_all(rows)
    db.flush()
    return len(rows)
