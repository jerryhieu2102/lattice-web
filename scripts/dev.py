"""Launch the local stack; optionally verify it through the real browser and PostgreSQL."""

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

import httpx
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
p = argparse.ArgumentParser()
p.add_argument("--verify", action="store_true")
p.add_argument("--production", action="store_true")
p.add_argument("--portable-postgres", action="store_true")
p.add_argument(
    "--fresh-db", action="store_true", help="Use a new temporary portable database, preserving existing data"
)
p.add_argument(
    "--startup-check", action="store_true", help="Exit after migration, HTTP health, and session checks"
)
args = p.parse_args()
if args.fresh_db and not args.portable_postgres:
    p.error("--fresh-db requires --portable-postgres")
env = dict(os.environ)
env.setdefault("DATABASE_URL", "postgresql+psycopg://lattice:lattice_dev@127.0.0.1:5432/lattice")
env.setdefault("DEMO_MODE", "true")
env.setdefault("DEMO_DATE", "2026-09-16")
env["API_INTERNAL_URL"] = "http://127.0.0.1:8000"
processes, logs = [], []
log_dir = ROOT / "docs" / "verification"
log_dir.mkdir(parents=True, exist_ok=True)
temporary = tempfile.TemporaryDirectory(prefix="lattice-pg-") if args.fresh_db else None


def start(cmd, cwd, name):
    log = open(log_dir / f"{name}.log", "w")
    logs.append(log)
    child = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
    processes.append(child)
    return child


def wait_http(url, child):
    for _ in range(240):
        if child.poll() is not None:
            raise RuntimeError(f"Process exited; inspect docs/verification/*.log: {url}")
        try:
            with httpx.Client(trust_env=False, timeout=2) as client:
                if client.get(url).status_code == 200:
                    return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"Service did not become ready: {url}")


def verify_session(base):
    with httpx.Client(base_url=base, trust_env=False, timeout=15, headers={"x-lattice-request": "1"}) as c:
        r = c.post(
            "/api/v1/auth/login", json={"email": "student@lattice.demo", "password": "LatticeDemo2026!"}
        )
        r.raise_for_status()
        r = c.get("/api/v1/auth/me")
        r.raise_for_status()
        assert r.json()["id"] == "maya"
        c.post("/api/v1/auth/logout").raise_for_status()
        assert c.get("/api/v1/auth/me").status_code == 401
    print("Login/session/logout verified:", base, flush=True)


try:
    if args.portable_postgres:
        env["DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/template1"
        env["PGLITE_DATA"] = (
            str(Path(temporary.name) / "data") if temporary else str(ROOT / "scripts/postgres/.pgdata-dev")
        )
        pg = start(["node", "server.mjs"], ROOT / "scripts/postgres", "postgres")
        for _ in range(160):
            if pg.poll() is not None:
                raise RuntimeError("Portable PostgreSQL exited; inspect docs/verification/postgres.log")
            try:
                with psycopg.connect(
                    "postgresql://postgres:postgres@127.0.0.1:5432/template1", connect_timeout=1
                ) as c:
                    print("PostgreSQL:", c.execute("SELECT version()").fetchone()[0], flush=True)
                    break
            except psycopg.OperationalError:
                time.sleep(0.25)
        else:
            raise RuntimeError("Portable PostgreSQL startup failed")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env, check=True)
    subprocess.run([sys.executable, "-m", "alembic", "check"], cwd=ROOT, env=env, check=True)
    api = start(
        [sys.executable, "-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        ROOT,
        "api",
    )
    wait_http("http://127.0.0.1:8000/api/v1/health", api)
    web = start(["npm", "run", "start" if args.production else "dev"], ROOT / "apps/web", "web")
    wait_http("http://127.0.0.1:3000", web)
    if args.verify or args.startup_check:
        verify_session("http://127.0.0.1:8000")
        verify_session("http://127.0.0.1:3000")
    print("LATTICE ready: http://127.0.0.1:3000 (SANDBOX)", flush=True)
    if args.verify:
        sys.exit(subprocess.call(["npm", "run", "e2e"], cwd=ROOT / "apps/web", env=env))
    if not args.startup_check:
        while all(proc.poll() is None for proc in processes):
            time.sleep(1)
        raise RuntimeError("A service exited unexpectedly; inspect docs/verification/*.log")
except KeyboardInterrupt:
    pass
finally:
    for proc in reversed(processes):
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    for proc in reversed(processes):
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
    for log in logs:
        log.close()
    if temporary:
        temporary.cleanup()
