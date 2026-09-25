from typing import Literal
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from apps.api.deps import User
from apps.api.auth import require_student
from apps.api.schemas import Input
from benchmark.run import run_benchmark, persist, latest, to_csv

router = APIRouter()


class BenchmarkInput(Input):
    mode: Literal["FAST", "FULL"] = "FAST"


@router.post("/benchmark/run")
def run(data: BenchmarkInput, actor: User):
    require_student(actor)
    result = run_benchmark(data.mode)
    persist(result)
    return result


@router.get("/benchmark/latest")
def result(actor: User):
    require_student(actor)
    return latest()


@router.get("/benchmark/export")
def export(actor: User, format: Literal["json", "csv"] = "json"):
    import json

    require_student(actor)
    result = latest()
    if result is None:
        raise HTTPException(404, "No benchmark has been computed")
    body = json.dumps(result, indent=2) if format == "json" else to_csv(result)
    return Response(
        body,
        media_type="application/json" if format == "json" else "text/csv",
        headers={"Content-Disposition": f'attachment; filename="lattice-benchmark.{format}"'},
    )
