"""Run reproducible release gates and save exact, machine-readable outcomes."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/verification"
OUT.mkdir(parents=True, exist_ok=True)
report = {"generated_at": datetime.now(timezone.utc).isoformat(), "checks": [], "tests": {}}
env = dict(os.environ, DATABASE_URL="sqlite://", NEXT_TELEMETRY_DISABLED="1")


def save():
    (OUT / "final-results.json").write_text(json.dumps(report, indent=2) + "\n")


def run(name, command, cwd=ROOT):
    print("RUN", name, flush=True)
    started = time.perf_counter()
    with (OUT / (name + ".log")).open("w") as log:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
    row = {
        "name": name,
        "command": command,
        "cwd": str(cwd),
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "exit_code": result.returncode,
        "duration_seconds": round(time.perf_counter() - started, 3),
    }
    report["checks"].append(row)
    save()
    print(row["status"], name, row["duration_seconds"], "seconds", flush=True)
    if result.returncode:
        print((OUT / (name + ".log")).read_text()[-16000:])
        raise SystemExit(result.returncode)


run(
    "backend-tests",
    [sys.executable, "-m", "pytest", "-q", "tests", "--junitxml=docs/verification/pytest.xml"],
)
run(
    "python-lint",
    [
        sys.executable,
        "-m",
        "ruff",
        "check",
        "apps/api",
        "lattice_core",
        "lattice_ai",
        "optimizer",
        "simulation",
        "connectors",
        "benchmark",
        "tests",
        "scripts",
        "migrations",
    ],
)
run(
    "frontend-tests",
    ["npm", "run", "test", "--", "--reporter=json", "--outputFile=" + str(OUT / "vitest.json")],
    ROOT / "apps/web",
)
run("typescript", ["npm", "run", "typecheck"], ROOT / "apps/web")
run("frontend-lint", ["npm", "run", "lint"], ROOT / "apps/web")
run("production-build", ["npm", "run", "build"], ROOT / "apps/web")
run(
    "postgres-browser",
    [sys.executable, "scripts/dev.py", "--portable-postgres", "--production", "--fresh-db", "--verify"],
)
run(
    "development-startup",
    [sys.executable, "scripts/dev.py", "--portable-postgres", "--fresh-db", "--startup-check"],
)
run("benchmark-fast", [sys.executable, "-m", "benchmark.run", "--mode", "FAST"])
run("benchmark-full", [sys.executable, "-m", "benchmark.run", "--mode", "FULL"])
root = ElementTree.parse(OUT / "pytest.xml").getroot()
suite = root.find("testsuite")
report["tests"]["backend"] = {
    key: int(suite.attrib[key]) for key in ["tests", "failures", "errors", "skipped"]
}
v = json.loads((OUT / "vitest.json").read_text())
report["tests"]["frontend"] = {
    key: v[key] for key in ["numTotalTests", "numPassedTests", "numFailedTests", "numPendingTests"]
}
shutil.copy2(ROOT / "apps/web/test-results/results.json", OUT / "playwright.json")
v = json.loads((OUT / "playwright.json").read_text())
report["tests"]["playwright"] = v["stats"]
for mode in ["fast", "full"]:
    v = json.loads((ROOT / "benchmark/results" / f"{mode}.json").read_text())
    report["tests"][mode] = {k: v[k] for k in ["id", "case_count", "passed", "failed", "duration_ms"]}
for screenshot in (ROOT / "apps/web/test-results").glob("*.png"):
    (ROOT / "docs/screenshots").mkdir(exist_ok=True)
    shutil.copy2(screenshot, ROOT / "docs/screenshots" / screenshot.name)
if shutil.which("docker"):
    run("docker-compose-config", ["docker", "compose", "config", "--quiet"])
    run("docker-build", ["docker", "compose", "build"])
else:
    report["checks"].append(
        {
            "name": "docker-build-compose",
            "status": "BLOCKED",
            "reason": "Docker CLI/daemon is not installed; no Docker build or native Compose runtime was executed.",
        }
    )
report["completed_at"] = datetime.now(timezone.utc).isoformat()
save()
print(json.dumps(report["tests"], indent=2), flush=True)
