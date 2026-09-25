import hashlib
import json
from sqlalchemy import select, text
from lattice_core.models import AuditEvent, now


def digest(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def event_digest(event):
    return digest(
        {
            k: getattr(event, k)
            for k in (
                "sequence",
                "actor_id",
                "student_id",
                "event_type",
                "category",
                "payload",
                "previous_hash",
            )
        }
    )


def record(db, actor_id, student_id, event_type, category, payload):
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(710012)"))
    last = db.scalar(select(AuditEvent).order_by(AuditEvent.sequence.desc()).limit(1))
    event = AuditEvent(
        sequence=last.sequence + 1 if last else 1,
        actor_id=actor_id,
        student_id=student_id,
        event_type=event_type,
        category=category,
        payload={**payload, "recorded_at": now().isoformat()},
        previous_hash=last.event_hash if last else "0" * 64,
    )
    event.event_hash = event_digest(event)
    db.add(event)
    db.flush()
    return event


def verify_chain(events):
    previous = "0" * 64
    for index, event in enumerate(events, 1):
        if (
            event.sequence != index
            or event.previous_hash != previous
            or event.event_hash != event_digest(event)
        ):
            return False
        previous = event.event_hash
    return True
