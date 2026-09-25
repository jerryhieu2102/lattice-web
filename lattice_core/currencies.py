"""Supported currencies and fixed synthetic valuations; never live market quotes."""

from decimal import Decimal
from typing import Literal

# Values are EUR per major currency unit. Central to extraction, planning and UI metadata.
CURRENCIES = {
    "EUR": {"decimals": 2, "eur_value": "1"},
    "USD": {"decimals": 2, "eur_value": "0.90"},
    "CNY": {"decimals": 2, "eur_value": "0.127"},
    "VND": {"decimals": 0, "eur_value": "0.000036"},
    "GBP": {"decimals": 2, "eur_value": "1.17"},
    "JPY": {"decimals": 0, "eur_value": "0.0062"},
    "KRW": {"decimals": 0, "eur_value": "0.00067"},
    "SGD": {"decimals": 2, "eur_value": "0.69"},
    "HKD": {"decimals": 2, "eur_value": "0.115"},
    "AUD": {"decimals": 2, "eur_value": "0.60"},
    "CAD": {"decimals": 2, "eur_value": "0.66"},
    "CHF": {"decimals": 2, "eur_value": "1.05"},
    "THB": {"decimals": 2, "eur_value": "0.026"},
}
Currency = Literal[tuple(CURRENCIES)]
SCALE = {code: 10 ** data["decimals"] for code, data in CURRENCIES.items()}
BASE_RATE = {code: float(data["eur_value"]) for code, data in CURRENCIES.items()}


def precise_amount(value, currency):
    scaled = Decimal(str(value)) * SCALE[currency]
    if not scaled.is_finite() or scaled != scaled.to_integral_value():
        raise ValueError(f"{currency} amount must use its supported minor units")


def catalog():
    return {
        "rate_source": "DETERMINISTIC_DEMO",
        "base_currency": "EUR",
        "currencies": [
            {"code": code, "decimals": data["decimals"], "eur_value": float(data["eur_value"])}
            for code, data in CURRENCIES.items()
        ],
    }
