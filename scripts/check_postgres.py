from sqlalchemy import text
from lattice_core.db import SessionLocal, engine
from apps.api.auth import seed_accounts
from apps.api.demo import load_maya, reset
from lattice_core.state import financial_state
from optimizer.model.solver import optimize

with engine.connect() as c:
    print(c.scalar(text("SELECT version()")))
with SessionLocal() as db:
    seed_accounts(db)
    reset(db)
    print(load_maya(db))
    result = optimize(financial_state(db, "maya"))
    assert result["constraint_violations"] == 0
    db.commit()
    print("PostgreSQL migration + seed + optimizer: PASS")
