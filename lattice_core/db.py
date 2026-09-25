import os
from sqlalchemy import create_engine, text
from fastapi import Request
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://lattice:lattice_dev@localhost:5432/lattice")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg://",
        1,
    )
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )
    
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    **(
        {"connect_args": {"check_same_thread": False}}
        if DATABASE_URL.startswith("sqlite")
        else {"pool_size": int(os.getenv("DB_POOL_SIZE", "1")), "max_overflow": 0}
    ),
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db(request: Request):
    with SessionLocal() as db:
        try:
            if request.method in {"POST", "PUT", "PATCH", "DELETE"} and db.bind.dialect.name == "postgresql":
                # Serialize financial mutations across API workers before reading state.
                db.execute(text("SELECT pg_advisory_xact_lock(1279349844)"))
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
