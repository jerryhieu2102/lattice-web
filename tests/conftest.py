import os

os.environ.setdefault("DATABASE_URL", "sqlite://")
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from lattice_core.db import Base, get_db
from apps.api import main
from apps.api.auth import DEMO_PASSWORD


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def constraints(conn, record):
        conn.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with engine.begin() as c:
        c.exec_driver_sql(
            "CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit history is append only'); END"
        )
        c.exec_driver_sql(
            "CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit history is append only'); END"
        )
    sessions = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(main, "SessionLocal", sessions)

    def db():
        with sessions() as s:
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise

    main.app.dependency_overrides[get_db] = db
    with TestClient(main.app, headers={"x-lattice-request": "1"}) as c:
        c.sessions = sessions
        login(c, "admin")
        assert c.post("/api/v1/demo/load-maya").status_code == 200
        login(c, "student")
        yield c
    main.app.dependency_overrides.clear()
    engine.dispose()


def login(client, role):
    r = client.post("/api/v1/auth/login", json={"email": f"{role}@lattice.demo", "password": DEMO_PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()
