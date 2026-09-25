from datetime import datetime, timedelta, timezone
import pytest
from apps.api.auth import session_expired


@pytest.mark.parametrize("offset", [-8, 0, 7])
def test_session_expiration_preserves_timezone_instant(offset):
    at = datetime(2026, 9, 16, 16, tzinfo=timezone.utc)
    local = (at + timedelta(hours=8)).astimezone(timezone(timedelta(hours=offset)))
    assert not session_expired(local, at)
    assert session_expired(local, at + timedelta(hours=9))


def test_sqlite_naive_utc_expiry():
    at = datetime(2026, 9, 16, 16, tzinfo=timezone.utc)
    assert not session_expired(datetime(2026, 9, 16, 17), at)
    assert session_expired(datetime(2026, 9, 16, 15), at)
