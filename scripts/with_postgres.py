"""Run a command beside portable PostgreSQL in the same process network namespace."""

import os
from pathlib import Path
import subprocess
import sys
import time
import psycopg

ROOT = Path(__file__).resolve().parents[1]
env = dict(
    os.environ,
    DATABASE_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/template1",
    PGLITE_DATA=str(ROOT / "scripts/postgres/.pgdata-run"),
)
process = subprocess.Popen(
    ["node", "server.mjs"], cwd=ROOT / "scripts/postgres", env=env, stdout=subprocess.DEVNULL
)
try:
    for _ in range(100):
        try:
            with psycopg.connect(
                "postgresql://postgres:postgres@127.0.0.1:5432/template1", connect_timeout=1
            ):
                break
        except psycopg.OperationalError:
            time.sleep(0.1)
    else:
        raise RuntimeError("Portable PostgreSQL failed to start")
    sys.exit(subprocess.call(sys.argv[1:], cwd=ROOT, env=env))
finally:
    process.terminate()
    process.wait(timeout=10)
