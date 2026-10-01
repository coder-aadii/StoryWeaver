"""Persisted workflow runs (D1). Every background job is a `WorkflowRun` row, so the UI can poll it,
a crash leaves a visible record, and a double click returns the run that is already active.

The service takes the caller's Session and only `flush`es; callers own the commit.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import WorkflowRun
from app.models.enums import RunStatus

ACTIVE = (RunStatus.QUEUED, RunStatus.RUNNING)
TERMINAL = (RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.INTERRUPTED)


def _now() -> datetime:
    return datetime.now(UTC)


class RunService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # -- queries -----------------------------------------------------------------------------
    def get(self, run_id: uuid.UUID) -> WorkflowRun | None:
        return self.db.get(WorkflowRun, run_id)

    def active_for(self, kind: str, subject_id: uuid.UUID) -> WorkflowRun | None:
        return self.db.scalars(
            select(WorkflowRun).where(
                WorkflowRun.kind == kind,
                WorkflowRun.subject_id == subject_id,
                WorkflowRun.status.in_(ACTIVE),
            )
        ).first()

    def latest_for(self, subject_id: uuid.UUID, kind: str | None = None) -> WorkflowRun | None:
        stmt = select(WorkflowRun).where(WorkflowRun.subject_id == subject_id)
        if kind:
            stmt = stmt.where(WorkflowRun.kind == kind)
        return self.db.scalars(stmt.order_by(WorkflowRun.created_at.desc())).first()

    def list(
        self, *, subject_id: uuid.UUID | None = None, limit: int = 50, offset: int = 0
    ) -> tuple[list[WorkflowRun], int]:
        stmt = select(WorkflowRun)
        if subject_id:
            stmt = stmt.where(WorkflowRun.subject_id == subject_id)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self.db.scalars(
            stmt.order_by(WorkflowRun.created_at.desc()).limit(limit).offset(offset)
        ).all()
        return list(rows), total

    # -- lifecycle ---------------------------------------------------------------------------
    def start(
        self,
        kind: str,
        subject_type: str,
        subject_id: uuid.UUID,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[WorkflowRun, bool]:
        """Create a queued run, or return the active one. Returns (run, created)."""
        existing = self.active_for(kind, subject_id)
        if existing:
            return existing, False
        attempt = (
            self.db.scalar(
                select(func.coalesce(func.max(WorkflowRun.attempt), 0)).where(
                    WorkflowRun.kind == kind, WorkflowRun.subject_id == subject_id
                )
            )
            or 0
        ) + 1
        run = WorkflowRun(
            kind=kind,
            subject_type=subject_type,
            subject_id=subject_id,
            attempt=attempt,
            idempotency_key=f"{kind}:{subject_id}:{attempt}",
            params=params or {},
            progress={},
        )
        try:
            with self.db.begin_nested():  # a lost race must not poison the outer transaction
                self.db.add(run)
                self.db.flush()
        except IntegrityError:
            existing = self.active_for(kind, subject_id)
            if existing is None:
                raise
            return existing, False
        return run, True

    def mark_running(self, run: WorkflowRun) -> None:
        run.status = RunStatus.RUNNING
        run.started_at = run.started_at or _now()
        self.db.flush()

    def set_progress(self, run: WorkflowRun, **values: Any) -> None:
        run.progress = {**run.progress, **values}  # new dict: JSONB change detection
        self.db.flush()

    def mark_succeeded(self, run: WorkflowRun) -> None:
        run.status = RunStatus.SUCCEEDED
        run.error = None
        run.finished_at = _now()
        self.db.flush()

    def mark_failed(self, run: WorkflowRun, *, code: str, message: str, retryable: bool) -> None:
        run.status = RunStatus.FAILED
        run.error = {"code": code, "message": message[:500], "retryable": retryable}
        run.finished_at = _now()
        self.db.flush()

    def interrupt_stale(self) -> int:
        """Startup reconciliation: nothing survives a process restart, so every active run is dead."""
        result = self.db.execute(
            update(WorkflowRun)
            .where(WorkflowRun.status.in_(ACTIVE))
            .values(
                status=RunStatus.INTERRUPTED,
                finished_at=_now(),
                error={
                    "code": "interrupted",
                    "message": "the server stopped while this was running",
                    "retryable": True,
                },
            )
        )
        self.db.flush()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
