import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import get_db
from app.ingestion.queries import run_read
from app.schemas.source_api import Page, RunRead
from app.workflows.runs import RunService

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> RunRead:
    run = RunService(db).get(run_id)
    if run is None:
        raise ApiError(404, "not_found", "run not found")
    return run_read(run)


@router.get("", response_model=Page[RunRead])
def list_runs(
    db: Session = Depends(get_db),
    subject_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[RunRead]:
    rows, total = RunService(db).list(subject_id=subject_id, limit=limit, offset=offset)
    return Page[RunRead](items=[run_read(r) for r in rows], total=total, limit=limit, offset=offset)
