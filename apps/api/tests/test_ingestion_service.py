"""P1 ingestion service with a fake extractor and temp storage (needs TEST_DATABASE_URL)."""

import io
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.errors import TranscriptParseError
from app.core.storage import get_storage
from app.ingestion import queries, service
from app.ingestion.normalize import NORMALIZER_VERSION
from app.ingestion.parsers import parse_srt, parse_txt, parse_vtt
from app.ingestion.registry import override_extractors
from app.models import Channel, ProjectSource, SourceVideo, Transcript, TranscriptChunk, WorkflowRun
from app.models.enums import RunStatus, SourceStatus, TranscriptStatus
from app.workflows.runner import InlineRunner, set_runner
from tests.support import CHANNEL_ID, FakeYouTube, fixture_bytes

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.fixture
def factory(engine) -> sessionmaker[Session]:  # type: ignore[no-untyped-def]
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _inline_runner(storage_root: Path) -> None:  # type: ignore[misc]
    set_runner(InlineRunner())
    yield  # type: ignore[misc]
    set_runner(None)


def add_url(db: Session, fake: FakeYouTube, url: str = URL) -> service.AddResult:
    with override_extractors([fake]):
        result = service.start_add_from_url(db, url)
        db.commit()
        if result.run is not None and not result.already_exists:
            service.submit_run(result.run)
    return result


def reload(db: Session, source: SourceVideo) -> SourceVideo:
    db.expire_all()
    return db.get(SourceVideo, source.id)  # type: ignore[return-value]


# ---- add by URL ------------------------------------------------------------------------------
def test_add_by_url_end_to_end(db: Session) -> None:
    fake = FakeYouTube()
    result = add_url(db, fake)
    assert not result.already_exists and result.run is not None
    source = reload(db, result.source)
    assert source.status is SourceStatus.IMPORTED and source.title == "Volcanoes explained"
    assert source.kind == "youtube" and source.url == URL and source.external_id == "dQw4w9WgXcQ"
    assert (
        source.thumbnail_url
        and source.duration_seconds == 15.25
        and source.meta["view_count"] == 42
    )
    transcript = service.current_transcript(db, source.id)
    assert transcript is not None and transcript.status is TranscriptStatus.READY
    assert transcript.origin == "manual" and transcript.is_current and transcript.version == 1
    assert transcript.normalizer_version == NORMALIZER_VERSION and source.fingerprint
    run = db.get(WorkflowRun, result.run.id)
    assert run is not None and run.status is RunStatus.SUCCEEDED
    assert run.progress["step"] == "done" and run.progress["chunk_count"] >= 1
    item = queries.list_item(db, source)
    assert item.searchable and item.chunk_count >= 1 and item.channel_title == "Earth Channel"


def test_channel_is_upserted_by_canonical_id_not_handle(db: Session) -> None:
    add_url(db, FakeYouTube())
    add_url(db, FakeYouTube(), "https://www.youtube.com/watch?v=aaaaaaaaaaa")
    channels = db.scalars(select(Channel)).all()
    assert len(channels) == 1 and channels[0].external_id == CHANNEL_ID
    assert channels[0].url == f"https://www.youtube.com/channel/{CHANNEL_ID}"
    assert (
        db.scalar(
            select(func.count())
            .select_from(SourceVideo)
            .where(SourceVideo.channel_id == channels[0].id)
        )
        == 2
    )


def test_adding_the_same_url_twice_is_one_source_and_one_transcript(db: Session) -> None:
    first = add_url(db, FakeYouTube())
    for variant in (
        URL,
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s",
    ):
        again = add_url(db, FakeYouTube(), variant)
        assert (
            again.already_exists
            and again.match == "identity"
            and again.source.id == first.source.id
        )
        assert again.run is None  # nothing running; no second run is started
    assert db.scalar(select(func.count()).select_from(SourceVideo)) == 1
    assert db.scalar(select(func.count()).select_from(Transcript)) == 1
    assert db.scalar(select(func.count()).select_from(WorkflowRun)) == 1


def test_no_captions_leaves_source_imported_and_transcript_failed(db: Session) -> None:
    result = add_url(db, FakeYouTube("no_captions"))
    source = reload(db, result.source)
    assert source.status is SourceStatus.IMPORTED  # metadata is fine
    transcript = service.current_transcript(db, source.id)
    assert transcript is not None and transcript.status is TranscriptStatus.FAILED
    assert transcript.error is not None and transcript.error.startswith("no_captions")
    run = db.get(WorkflowRun, result.run.id)  # type: ignore[union-attr]
    assert run is not None and run.status is RunStatus.FAILED
    assert run.error == {"code": "no_captions", "message": run.error["message"], "retryable": False}  # type: ignore[index]
    assert not queries.list_item(db, source).searchable


def test_unavailable_video_fails_the_source_without_retry(db: Session) -> None:
    result = add_url(db, FakeYouTube("unavailable"))
    source = reload(db, result.source)
    assert source.status is SourceStatus.FAILED and "video_unavailable" in (source.error or "")
    run = db.get(WorkflowRun, result.run.id)  # type: ignore[union-attr]
    assert run is not None and run.error is not None and run.error["retryable"] is False


def test_transient_failure_then_retry_completes_it(db: Session) -> None:
    fake = FakeYouTube("transient_then_ok")
    result = add_url(db, fake)
    source = reload(db, result.source)
    assert source.status is SourceStatus.IMPORTED  # metadata step succeeded
    failed = db.get(WorkflowRun, result.run.id)  # type: ignore[union-attr]
    assert failed is not None and failed.error is not None and failed.error["retryable"] is True
    assert service.current_transcript(db, source.id).status is TranscriptStatus.FAILED  # type: ignore[union-attr]

    with override_extractors([fake]):
        run, created = service.retry_source(db, source.id)
        db.commit()
        assert created and run.kind == service.RUN_FETCH and run.attempt == 1
        service.submit_run(run)
    db.expire_all()
    assert db.get(WorkflowRun, run.id).status is RunStatus.SUCCEEDED  # type: ignore[union-attr]
    transcript = service.current_transcript(db, source.id)
    assert transcript is not None and transcript.status is TranscriptStatus.READY
    assert fake.extract_calls == 1, "retry of the transcript half must not re-fetch metadata"
    rows = db.scalars(
        select(Transcript)
        .where(Transcript.source_video_id == source.id)
        .order_by(Transcript.version)
    ).all()
    assert [(t.version, t.status, t.is_current) for t in rows] == [
        (1, TranscriptStatus.FAILED, False),  # the failed attempt stays as history
        (2, TranscriptStatus.READY, True),
    ]


def test_retry_of_a_healthy_source_is_refused(db: Session) -> None:
    source = reload(db, add_url(db, FakeYouTube()).source)
    with pytest.raises(service.NothingToRetryError):
        service.retry_source(db, source.id)


def test_failed_metadata_is_retried_as_a_full_run(db: Session) -> None:
    fake = FakeYouTube("extract_error")
    source = add_url(db, fake).source
    assert reload(db, source).status is SourceStatus.FAILED
    fake.mode = "ok"
    with override_extractors([fake]):
        run, created = service.retry_source(db, source.id)
        db.commit()
        service.submit_run(run)
    assert created and run.kind == service.RUN_ADD and run.attempt == 2
    assert reload(db, source).status is SourceStatus.IMPORTED


def test_channel_and_playlist_urls_are_refused_before_anything_is_created(db: Session) -> None:
    from app.core.errors import UnsupportedSourceKindError

    for url in (
        "https://www.youtube.com/@Some/videos",
        "https://www.youtube.com/playlist?list=PLabcdefghij123",
    ):
        with override_extractors([FakeYouTube()]), pytest.raises(UnsupportedSourceKindError):
            service.start_add_from_url(db, url)
    assert db.scalar(select(func.count()).select_from(SourceVideo)) == 0


def test_missing_ytdlp_is_reported_before_anything_is_created(db: Session) -> None:
    from app.core.errors import ProviderNotConfiguredError

    with (
        override_extractors([FakeYouTube("not_installed")]),
        pytest.raises(ProviderNotConfiguredError),
    ):
        service.start_add_from_url(db, URL)
    assert db.scalar(select(func.count()).select_from(SourceVideo)) == 0


def test_no_media_is_stored_only_the_raw_caption_file(db: Session, storage_root: Path) -> None:
    add_url(db, FakeYouTube())
    files = [p for p in storage_root.rglob("*") if p.is_file()]
    assert [p.suffix for p in files] == [".vtt"] and files[0].parent.name == "v1"
    assert files[0].read_bytes() == fixture_bytes("simple.vtt"), (
        "raw file is stored exactly as received"
    )


# ---- add by transcript upload -----------------------------------------------------------------
def upload(db: Session, name: str, parse, title: str = "Volcano talk", **kw):  # type: ignore[no-untyped-def]
    raw = fixture_bytes(name)
    result = service.add_source_from_transcript(
        db,
        get_storage(),
        title=title,
        segments=parse(raw),
        raw=raw,
        raw_ext=name.rsplit(".", 1)[1],
        **kw,
    )
    db.commit()
    return result


def test_same_words_as_txt_srt_and_vtt_are_one_source(db: Session) -> None:
    a = upload(db, "simple.srt", parse_srt)
    b = upload(db, "simple.vtt", parse_vtt, title="Other title")
    c = upload(db, "simple.txt", parse_txt, title="Third")
    assert not a.already_exists
    assert b.already_exists and b.match == "fingerprint" and b.source.id == a.source.id
    assert c.already_exists and c.source.id == a.source.id
    assert db.scalar(select(func.count()).select_from(SourceVideo)) == 1
    assert db.scalar(select(func.count()).select_from(Transcript)) == 1


def test_upload_source_shape(db: Session) -> None:
    src = upload(
        db, "simple.srt", parse_srt, language="en", reference_url="https://example.com/talk"
    ).source
    assert src.platform == "upload" and src.kind == "transcript" and src.url is None
    assert src.status is SourceStatus.IMPORTED and src.external_id == src.fingerprint
    assert src.meta == {"reference_url": "https://example.com/talk"}
    transcript = service.current_transcript(db, src.id)
    assert transcript is not None and transcript.origin == "upload" and transcript.language == "en"


def test_untimed_text_has_chunks_with_null_times(db: Session) -> None:
    src = upload(db, "simple.txt", parse_txt).source
    chunks = db.scalars(
        select(TranscriptChunk).join(Transcript).where(Transcript.source_video_id == src.id)
    ).all()
    assert chunks and all(c.start_seconds is None and c.end_seconds is None for c in chunks)
    assert queries.transcript_summary(service.current_transcript(db, src.id)).timed is False  # type: ignore[arg-type]


def test_changed_text_creates_version_two_and_flips_current(db: Session) -> None:
    src = upload(db, "simple.srt", parse_srt).source
    storage = get_storage()
    edited = parse_srt(fixture_bytes("simple.srt").replace(b"volcanoes", b"glaciers"))
    t2 = service.ingest_transcript(
        db,
        storage,
        src,
        segments=edited,
        origin="upload",
        language=None,
        raw=b"edited",
        raw_ext="srt",
    )
    db.commit()
    rows = db.scalars(
        select(Transcript).where(Transcript.source_video_id == src.id).order_by(Transcript.version)
    ).all()
    assert [(t.version, t.is_current) for t in rows] == [(1, False), (2, True)] and t2.version == 2
    assert storage.exists(rows[0].raw_storage_key) and storage.exists(rows[1].raw_storage_key)  # type: ignore[arg-type]
    chunk_owner = db.scalars(select(TranscriptChunk.transcript_id).distinct()).all()
    assert len(chunk_owner) == 2, "old version keeps its chunks as history"
    assert queries.search(db, "glaciers", exclude_used=False, limit=5, offset=0)[1] == 1
    assert queries.search(db, "volcanoes", exclude_used=False, limit=5, offset=0)[1] == 0, (
        "only the current version is searchable"
    )


def test_ingesting_identical_content_twice_is_a_noop(db: Session) -> None:
    src = upload(db, "simple.srt", parse_srt).source
    before = db.scalar(select(func.count()).select_from(TranscriptChunk))
    again = service.ingest_transcript(
        db,
        get_storage(),
        src,
        segments=parse_srt(fixture_bytes("simple.srt")),
        origin="upload",
        language=None,
        raw=b"x",
        raw_ext="srt",
    )
    db.commit()
    assert again.version == 1 and db.scalar(select(func.count()).select_from(Transcript)) == 1
    assert db.scalar(select(func.count()).select_from(TranscriptChunk)) == before


def test_empty_transcript_is_rejected_and_nothing_is_stored(
    db: Session, storage_root: Path
) -> None:
    from app.schemas.source import TranscriptSegment

    with pytest.raises(TranscriptParseError):
        service.add_source_from_transcript(
            db,
            get_storage(),
            title="t",
            segments=[TranscriptSegment(text="  ")],
            raw=b" ",
            raw_ext="txt",
        )
    assert db.scalar(select(func.count()).select_from(SourceVideo)) == 0
    assert not list(storage_root.rglob("*.txt"))


def test_database_failure_rolls_back_chunks_and_removes_the_raw_file(
    db: Session, storage_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = SourceVideo(
        platform="upload",
        external_id="x",
        kind="transcript",
        title="t",
        status=SourceStatus.IMPORTED,
    )
    db.add(src)
    db.commit()

    def boom(*_: object, **__: object) -> list[tuple[str, float, float]]:
        raise RuntimeError("chunking exploded")

    monkeypatch.setattr(service, "chunk_segments", boom)
    with pytest.raises(RuntimeError):
        service.ingest_transcript(
            db,
            get_storage(),
            src,
            segments=parse_srt(fixture_bytes("simple.srt")),
            origin="upload",
            language=None,
            raw=b"raw",
            raw_ext="srt",
        )
    db.rollback()
    assert db.scalar(select(func.count()).select_from(Transcript)) == 0
    assert db.scalar(select(func.count()).select_from(TranscriptChunk)) == 0
    assert not [p for p in storage_root.rglob("*") if p.is_file()], (
        "raw file must be removed on failure"
    )


# ---- search, usage, delete, reconcile -----------------------------------------------------------
def test_search_returns_highlighted_escaped_snippet_and_timestamps(db: Session) -> None:
    upload(db, "simple.srt", parse_srt)
    hits, total = queries.search(db, "volcanoes", exclude_used=False, limit=5, offset=0)
    assert total == 1 and hits[0].source.searchable and hits[0].start_seconds == 0.0
    assert "<mark>volcanoes</mark>" in hits[0].snippet.lower()


def test_snippet_escapes_html_from_the_transcript() -> None:
    assert queries.safe_snippet(
        "<script>alert(1)</script> \x01volcano\x02 <img src=x onerror=1>"
    ) == ("&lt;script&gt;alert(1)&lt;/script&gt; <mark>volcano</mark> &lt;img src=x onerror=1&gt;")
    assert "<mark>" not in queries.safe_snippet("a \x01b")  # unbalanced markers are dropped


@pytest.mark.parametrize(
    "q", ['"', "a & | b", "((", "'", "-", "\\", "OR OR", "volcanoes OR", "!!!", "x" * 200]
)
def test_search_never_errors_on_odd_syntax(db: Session, q: str) -> None:
    upload(db, "simple.srt", parse_srt)
    queries.search(db, q, exclude_used=False, limit=5, offset=0)


def test_search_excludes_used_sources_when_asked(db: Session) -> None:
    from app.models import Project

    src = upload(db, "simple.srt", parse_srt).source
    project = Project(title="p")
    db.add(project)
    db.flush()
    db.add(ProjectSource(project_id=project.id, source_video_id=src.id))
    db.commit()
    assert queries.search(db, "volcanoes", exclude_used=False, limit=5, offset=0)[1] == 1
    assert queries.search(db, "volcanoes", exclude_used=True, limit=5, offset=0)[1] == 0
    assert queries.list_item(db, src).usage_count == 1
    assert [u.project_title for u in queries.usage_of(db, src.id)] == ["p"]


def test_failed_transcript_is_listed_but_not_searchable(db: Session) -> None:
    source = add_url(db, FakeYouTube("no_captions")).source
    assert queries.search(db, "volcanoes", exclude_used=False, limit=5, offset=0)[1] == 0
    rows, total = queries.query_sources(db, status=None, kind=None, used=None, limit=10, offset=0)
    assert total == 1 and rows[0].id == source.id


def test_delete_removes_rows_and_raw_files_unless_used(db: Session, storage_root: Path) -> None:
    from app.models import Project

    src = upload(db, "simple.srt", parse_srt).source
    project = Project(title="p")
    db.add(project)
    db.flush()
    link = ProjectSource(project_id=project.id, source_video_id=src.id)
    db.add(link)
    db.commit()
    assert service.delete_source(db, get_storage(), src) is False
    assert [p for p in storage_root.rglob("*") if p.is_file()], "refused delete must keep files"
    db.delete(link)
    db.commit()
    assert service.delete_source(db, get_storage(), src) is True
    db.commit()
    assert db.scalar(select(func.count()).select_from(SourceVideo)) == 0
    assert db.scalar(select(func.count()).select_from(TranscriptChunk)) == 0
    assert not [p for p in storage_root.rglob("*") if p.is_file()]


def test_startup_reconciliation_marks_dead_work_interrupted(db: Session) -> None:
    from app.workflows.runs import RunService

    stuck = SourceVideo(
        platform="youtube",
        external_id="s1",
        kind="youtube",
        url="u",
        title="t",
        status=SourceStatus.IMPORTING,
    )
    fine = SourceVideo(
        platform="youtube",
        external_id="s2",
        kind="youtube",
        url="u",
        title="t",
        status=SourceStatus.IMPORTED,
    )
    db.add_all([stuck, fine])
    db.flush()
    run, _ = RunService(db).start("source.add", "source_video", stuck.id)
    RunService(db).mark_running(run)
    db.add(Transcript(source_video_id=fine.id, version=1, status=TranscriptStatus.PROCESSING))
    db.commit()
    counts = service.reconcile_stale(db)
    db.commit()
    db.expire_all()
    assert counts == {"runs": 1, "sources": 1, "transcripts": 1}
    assert db.get(SourceVideo, stuck.id).status is SourceStatus.FAILED  # type: ignore[union-attr]
    assert db.get(SourceVideo, fine.id).status is SourceStatus.IMPORTED  # type: ignore[union-attr]
    interrupted = db.get(WorkflowRun, run.id)
    assert interrupted is not None and interrupted.status is RunStatus.INTERRUPTED
    assert interrupted.error is not None and interrupted.error["retryable"] is True
    # and a retry is possible afterwards
    with override_extractors([FakeYouTube()]):
        new_run, created = service.retry_source(db, stuck.id)
    assert created and new_run.kind == service.RUN_ADD


def test_worker_ignores_runs_that_are_not_queued_and_survives_a_deleted_source(
    db: Session, factory
) -> None:  # type: ignore[no-untyped-def]
    from app.workflows.runs import RunService

    src = SourceVideo(
        platform="youtube",
        external_id="gone",
        kind="youtube",
        url="https://www.youtube.com/watch?v=gone0000000",
        title="t",
        status=SourceStatus.IMPORTING,
    )
    db.add(src)
    db.flush()
    run, _ = RunService(db).start("source.add", "source_video", src.id)
    db.commit()
    db.delete(src)
    db.commit()
    service.run_source_workflow(run.id, session_factory=factory, extractor=FakeYouTube())
    db.expire_all()
    done = db.get(WorkflowRun, run.id)
    assert done is not None and done.status is RunStatus.FAILED
    assert done.error is not None and done.error["code"] == "source_missing"
    service.run_source_workflow(
        run.id, session_factory=factory, extractor=FakeYouTube()
    )  # no longer queued: no-op
    assert io.BytesIO is not None
