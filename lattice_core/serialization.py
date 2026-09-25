from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import inspect


def clean(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def public(obj):
    return {
        c.key: clean(getattr(obj, c.key))
        for c in inspect(obj).mapper.column_attrs
        if c.key not in {"password_hash", "token_hash"}
    }
