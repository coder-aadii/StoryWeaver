"""Run lifecycle (needs TEST_DATABASE_URL)."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import WorkflowRun
from app.models.enums import RunStatus
from app.workflows.runner import InlineRunner, LocalRunner, get_runner, set_runner
from app.workflows.runs import RunService

SUBJECT = uuid.uuid4()


def test_start_creates_a_queued_run_with_a_deterministic_key(db: Session) -> None:
    run, created = RunService(db).start("source.add", "source_video", SUBJECT)
    assert created and run.status is RunStatus.QUEUED and run.attempt == 1
    assert run.idempotency_key == f"source.add:{SUBJECT}:1"


def test_double_start_returns_the_active_run(db: Session) -> None:
    svc = RunService(db)
    first, _ = svc.start("source.add", "source_video", SUBJECT)
    again, created = svc.start("source.add", "source_video", SUBJECT)
    assert not created and again.id == first.id
    svc.mark_running(first)
    assert svc.start("source.add", "source_video", SUBJECT)[0].id == first.id


def test_a_finished_run_allows_a_new_attempt(db: Session) -> None:
    svc = RunService(db)
    first, _ = svc.start("source.add", "source_video", SUBJECT)
    svc.mark_running(first)
    svc.mark_failed(first, code="timeout", message="slow", retryable=True)
    assert first.error == {"code": "timeout", "message": "slow", "retryable": True}
    second, created = svc.start("source.add", "source_video", SUBJECT)
    assert created and second.attempt == 2 and second.idempotency_key.endswith(":2")


def test_different_kinds_and_subjects_do_not_collide(db: Session) -> None:
    svc = RunService(db)
    a, _ = svc.start("source.add", "source_video", SUBJECT)
    b, cb = svc.start("source.fetch_transcript", "source_video", SUBJECT)
    c, cc = svc.start("source.add", "source_video", uuid.uuid4())
    assert cb and cc and len({a.id, b.id, c.id}) == 3


def test_database_refuses_two_active_runs_for_one_subject(db: Session) -> None:
    db.add_all(
        [
            WorkflowRun(kind="k", subject_type="s", subject_id=SUBJECT, idempotency_key="k:1:1", params={}, progress={}),
            WorkflowRun(kind="k", subject_type="s", subject_id=SUBJECT, idempotency_key="k:1:2", params={}, progress={}),
        ]
    )  # fmt: skip
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_progress_merges_and_success_clears_error(db: Session) -> None:
    svc = RunService(db)
    run, _ = svc.start("source.add", "source_video", SUBJECT)
    svc.mark_running(run)
    svc.set_progress(run, step="metadata")
    svc.set_progress(run, segment_count=12)
    assert run.progress == {"step": "metadata", "segment_count": 12} and run.started_at is not None
    svc.mark_succeeded(run)
    assert run.status is RunStatus.SUCCEEDED and run.error is None and run.finished_at is not None


def test_interrupt_stale_marks_every_active_run_retryable(db: Session) -> None:
    svc = RunService(db)
    q, _ = svc.start("a", "s", uuid.uuid4())
    r, _ = svc.start("b", "s", uuid.uuid4())
    svc.mark_running(r)
    done, _ = svc.start("c", "s", uuid.uuid4())
    svc.mark_succeeded(done)
    assert svc.interrupt_stale() == 2
    for row in (q, r, done):
        db.refresh(row)
    assert q.status is r.status is RunStatus.INTERRUPTED and done.status is RunStatus.SUCCEEDED
    assert r.error is not None and r.error["code"] == "interrupted" and r.error["retryable"] is True


def test_list_filters_by_subject_and_paginates(db: Session) -> None:
    svc = RunService(db)
    for kind in ("a", "b", "c"):
        run, _ = svc.start(kind, "s", SUBJECT)
        svc.mark_succeeded(run)
    other, _ = svc.start("a", "s", uuid.uuid4())
    rows, total = svc.list(subject_id=SUBJECT, limit=2)
    assert total == 3 and len(rows) == 2 and other.id not in {r.id for r in rows}
    assert svc.latest_for(SUBJECT) is not None


def test_inline_runner_runs_immediately_and_contains_failures() -> None:
    seen: list[int] = []
    InlineRunner().submit("t", seen.append, 1)
    InlineRunner().submit("t", lambda: 1 / 0)  # failure is logged, never raised
    assert seen == [1]


def test_set_runner_swaps_and_restores_the_process_runner() -> None:
    inline = InlineRunner()
    set_runner(inline)
    try:
        assert get_runner() is inline
    finally:
        set_runner(None)
    assert isinstance(get_runner(), LocalRunner)


def test_app_startup_interrupts_work_left_by_a_dead_process(db: Session) -> None:
    """Acceptance: after a crash and restart nothing stays 'running' or 'importing' forever."""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.models import SourceVideo
    from app.models.enums import SourceStatus

    src = SourceVideo(
        platform="youtube",
        external_id="crash",
        kind="youtube",
        url="u",
        title="t",
        status=SourceStatus.IMPORTING,
    )
    db.add(src)
    db.flush()
    svc = RunService(db)
    run, _ = svc.start("source.add", "source_video", src.id)
    svc.mark_running(run)
    db.commit()

    with TestClient(app):  # entering the context runs the lifespan startup
        pass

    db.expire_all()
    assert db.get(SourceVideo, src.id).status is SourceStatus.FAILED  # type: ignore[union-attr]
    stuck = db.get(WorkflowRun, run.id)
    assert stuck is not None and stuck.status is RunStatus.INTERRUPTED
    assert stuck.error is not None and stuck.error["retryable"] is True


def test_startup_survives_an_unreachable_database(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    import app.ingestion.service as ingestion_service
    from app.main import app

    def boom(*_: object, **__: object) -> None:
        raise RuntimeError("database is down")

    monkeypatch.setattr(ingestion_service, "reconcile_stale", boom)
    with TestClient(app) as client:  # must still boot
        assert client.get("/api/v1/health").status_code == 200
