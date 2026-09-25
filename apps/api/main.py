import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, Request, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from lattice_core.db import SessionLocal
from lattice_core.models import Actor, AuthSession, AuditEvent
from lattice_core.serialization import public
from lattice_core.audit.service import verify_chain
from apps.api.auth import (
    seed_accounts,
    check_password,
    create_session,
    token_hash,
    require_admin,
    require_student,
)
from apps.api.deps import DB, User
from lattice_core.currencies import catalog
from connectors.mock_fx.routes import ensure_demo_routes
from apps.api.planning import invalidate
from apps.api.schemas import Login
from apps.api import (
    routes_life,
    routes_data,
    routes_documents,
    routes_plans,
    routes_actions,
    routes_benchmark,
    demo,
)


@asynccontextmanager
async def lifespan(app):
    with SessionLocal() as db:
        seed_accounts(db)
        if os.getenv("DEMO_MODE", "true").lower() == "true":
            added = ensure_demo_routes(db)
            if added:
                invalidate(
                    db, "maya", "admin", "TRANSFER_ROUTES_ADDED", {"added_routes": added}, replan=False
                )
        db.commit()
    yield


app = FastAPI(
    title="LATTICE v1.0",
    description="Verified financial orchestration. All execution is SANDBOX.",
    version="1.0.0",
    lifespan=lifespan,
)
write_lock = asyncio.Lock()


@app.middleware("http")
async def request_guard(request: Request, call_next):
    if request.method in {"POST", "PATCH", "DELETE", "PUT"}:
        if request.headers.get("x-lattice-request") != "1":
            return JSONResponse({"detail": "Missing same-origin request header"}, status_code=403)
        length = request.headers.get("content-length")
        if length:
            try:
                size = int(length)
            except ValueError:
                return JSONResponse({"detail": "Invalid content length"}, status_code=400)
            if size < 0 or size > 3 * 1024 * 1024:
                return JSONResponse({"detail": "Request too large"}, status_code=413)
        async with write_lock:
            response = await call_next(request)
    else:
        response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    return response


router = APIRouter(prefix="/api/v1")


@router.get("/currencies")
def currencies():
    return catalog()


@router.get("/health")
def health(db: DB):
    db.execute(text("SELECT 1"))
    return {
        "as_of": demo.as_of(),
        "status": "ok",
        "version": "1.0.0",
        "environment": "SANDBOX",
        "provider": "MockLLMProvider",
        "fx": "deterministic demo rates",
    }


@router.post("/auth/login")
def login(data: Login, db: DB, response: Response):
    actor = db.scalar(select(Actor).where(Actor.email == data.email.lower()))
    if not actor or not check_password(data.password, actor.password_hash):
        raise HTTPException(401, "Invalid email or password")
    token = create_session(db, actor)
    response.set_cookie(
        "lattice_session",
        token,
        httponly=True,
        samesite="strict",
        secure=os.getenv("COOKIE_SECURE", "false") == "true",
        max_age=28800,
        path="/",
    )
    return public(actor)


@router.get("/auth/me")
def me(actor: User):
    return public(actor)


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: DB, actor: User):
    session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == token_hash(request.cookies.get("lattice_session", ""))
        )
    )
    if session:
        db.delete(session)
    response.delete_cookie("lattice_session")
    return {"signed_out": True}


@router.post("/demo/reset")
def reset(db: DB, actor: User):
    require_admin(actor)
    demo.reset(db, actor.id)
    return {"reset": True, "audit_preserved": True}


@router.post("/demo/load-maya")
def load_maya(db: DB, actor: User):
    require_admin(actor)
    return demo.load_maya(db)


@router.get("/audit")
def audit(db: DB, actor: User, category: str | None = None):
    query = select(AuditEvent).order_by(AuditEvent.sequence.desc())
    if actor.role in {"PARENT", "SPONSOR"}:
        query = query.where(
            AuditEvent.actor_id == actor.id, AuditEvent.category.in_(["PERMISSION", "ACTION"])
        )
    else:
        query = query.where(AuditEvent.student_id == require_student(actor))
    if category:
        query = query.where(AuditEvent.category == category)
    return [public(e) for e in db.scalars(query.limit(500))]


@router.get("/audit/verify-chain")
def chain(db: DB, actor: User):
    require_admin(actor)
    events = list(db.scalars(select(AuditEvent).order_by(AuditEvent.sequence)))
    return {"valid": verify_chain(events), "events": len(events)}


for sub in [
    routes_life.router,
    routes_data.router,
    routes_documents.router,
    routes_plans.router,
    routes_actions.router,
    routes_benchmark.router,
]:
    router.include_router(sub)
app.include_router(router)
