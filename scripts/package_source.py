"""Build a portable, source-only archive and check every ZIP member."""

from hashlib import sha256
import os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT.parent / "LATTICE_v1.0_SOURCE.zip"
EXCLUDED = {
    ".git",
    ".venv",
    "node_modules",
    ".next",
    ".browser",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
}
files = []
for directory, dirs, names in os.walk(ROOT):
    dirs[:] = sorted(
        d for d in dirs if d not in EXCLUDED and not d.startswith(".pgdata") and not d.endswith(".egg-info")
    )
    for name in sorted(names):
        path = Path(directory) / name
        relative = path.relative_to(ROOT)
        if path.is_symlink() or name == ".env" or (name.startswith(".env.") and name != ".env.example"):
            continue
        if path.suffix in {".pyc", ".zip", ".db", ".tsbuildinfo"}:
            continue
        if path.suffix == ".log" and relative.parts[:2] != ("docs", "verification"):
            continue
        files.append((path, "lattice/" + relative.as_posix()))
with ZipFile(DEST, "w", ZIP_DEFLATED, compresslevel=9) as archive:
    for path, name in files:
        archive.write(path, name)
with ZipFile(DEST) as archive:
    assert archive.testzip() is None, "Corrupt member in source archive"
    names = set(archive.namelist())
    required = [
        "README.md",
        "docker-compose.yml",
        "apps/api/main.py",
        "apps/web/package-lock.json",
        "migrations/versions/0001_initial.py",
        "migrations/versions/0002_life_events.py",
        "apps/api/routes_life.py",
        "apps/web/components/life/capture.tsx",
        "docs/LIFE_EVENTS_GUIDE_VI.md",
        "docs/verification/final-results.json",
        "benchmark/results/full.json",
        "benchmark/results/full.csv",
    ]
    assert all("lattice/" + name in names for name in required)
    assert not any(
        any(part in EXCLUDED or part.startswith(".pgdata") for part in Path(name).parts) for name in names
    )
print(
    f"Archive: {DEST}\nSource files: {len(files)}\nBytes: {DEST.stat().st_size}\nSHA-256: {sha256(DEST.read_bytes()).hexdigest()}"
)
