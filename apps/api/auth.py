import hashlib
import hmac
import os
import secrets
from datetime import timedelta, timezone
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from lattice_core.db import get_db
from lattice_core.models import Actor, AuthSession, now

DEMO_PASSWORD = "LatticeDemo2026!"


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ":" + hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200000).hex()


def check_password(password, encoded):
    return hmac.compare_digest(hash_password(password, encoded.split(":")[0]), encoded)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def session_expired(expires_at, at=None):
    expiry = (
        expires_at.replace(tzinfo=timezone.utc)
        if expires_at.tzinfo is None
        else expires_at.astimezone(timezone.utc)
    )
    return expiry < (at or now())


def current_actor(request: Request, db=Depends(get_db)):
    token = request.cookies.get("lattice_session", "")
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(token)))
    if not session or session_expired(session.expires_at):
        raise HTTPException(401, "Sign in to LATTICE")
    return db.get(Actor, session.actor_id)


def require_student(actor):
    if actor.role not in {"STUDENT", "ADMIN_DEMO"}:
        raise HTTPException(403, "Student-only private financial workspace")
    return actor.id if actor.role == "STUDENT" else "maya"


def require_admin(actor):
    if actor.role != "ADMIN_DEMO" or os.getenv("DEMO_MODE", "true").lower() != "true":
        raise HTTPException(403, "ADMIN_DEMO required; demo mode must be enabled")


def create_session(db, actor):
    token = secrets.token_urlsafe(48)
    db.add(
        AuthSession(actor_id=actor.id, token_hash=token_hash(token), expires_at=now() + timedelta(hours=8))
    )
    return token


def seed_accounts(db):
    for id_, role, type_, name, email, student in [
        ("maya", "STUDENT", "STUDENT", "Maya Nguyen", "student@lattice.demo", "maya"),
        ("father", "PARENT", "PARENT", "Minh Nguyen", "parent@lattice.demo", "maya"),
        ("sponsor", "SPONSOR", "SPONSOR", "Demo scholarship office", "sponsor@lattice.demo", "maya"),
        ("admin", "ADMIN_DEMO", "SYSTEM", "Demo administrator", "admin@lattice.demo", None),
    ]:
        if not db.get(Actor, id_):
            db.add(
                Actor(
                    id=id_,
                    role=role,
                    type=type_,
                    display_name=name,
                    email=email,
                    student_id=student,
                    password_hash=hash_password(DEMO_PASSWORD),
                    relationship="father" if role == "PARENT" else "demo",
                    country="VN",
                )
            )
    db.flush()
