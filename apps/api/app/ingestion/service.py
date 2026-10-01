"""Source Library ingestion: add a source, store its transcript, make it searchable.

Deterministic only — no model calls. Functions take the caller's Session and `flush`; the caller commits.
`run_source_add` is the background worker body and owns its own session.
"""

import io
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import (
    FileTooLargeError,
    NoCaptionsError,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderTimeoutError,
    SourceUnavailableError,
    TranscriptParseError,
    UnsupportedSourceKindError,
)
from app.core.logging import get_logger
from app.core.storage import LocalStorage, get_storage
from app.db.session import get_sessionmaker
from app.ingestion.base import SourceExtractor
from app.ingestion.chunking import chunk_segments
from app.ingestion.normalize import (
    NORMALIZER_VERSION,
    cleaned_text,
    fingerprint,
    normalize_segments,
)
from app.ingestion.registry import get_extractor
from app.models import (
    Channel,
    ProjectSource,
    SourceVideo,
    Transcript,
    TranscriptChunk,
    WorkflowRun,
)
from app.models.enums import RunStatus, SourceStatus, TranscriptStatus
from app.schemas.source import NormalizedSource, TranscriptOrigin, TranscriptSegment
from app.workflows.runner import get_runner
from app.workflows.runs import RunService

RUN_ADD = "source.add"
RUN_FETCH = "source.fetch_transcript"


@dataclass
class AddResult:
    source: SourceVideo
    run: WorkflowRun | None
    already_exists: bool
    match: str | None = None  # "identity" | "fingerprint"
    transcript: Transcript | None = None


class NothingToRetryError(Exception):
    """The source is healthy; there is nothing to retry."""


# ------------------------------------------------------------------------------------ helpers
def raw_storage_key(source_id: uuid.UUID, version: int, ext: str) -> str:
    return f"transcripts/{source_id}/v{version}/raw.{ext}"


def current_transcript(db: Session, source_id: uuid.UUID) -> Transcript | None:
    return db.scalars(
        select(Transcript).where(Transcript.source_video_id == source_id, Transcript.is_current)
    ).first()


def _segments_json(segments: list[TranscriptSegment]) -> list[dict[str, Any]]:
    return [s.model_dump(mode="json") for s in segments]


# ----------------------------------------------------------------------------- transcripts
def ingest_transcript(
    db: Session,
    storage: LocalStorage,
    source: SourceVideo,
    *,
    segments: list[TranscriptSegment],
    origin: TranscriptOrigin,
    language: str | None,
    raw: bytes,
    raw_ext: str,
) -> Transcript:
    """Normalize, store raw, and make a new current transcript version (idempotent).

    Re-ingesting identical content with the same normalizer version returns the existing current
    transcript. The raw file is removed again if the database work fails.
    """
    normalized = normalize_segments(segments)
    if not normalized:
        raise TranscriptParseError("the transcript has no text")
    fp = fingerprint(normalized)
    current = current_transcript(db, source.id)
    if (
        current is not None
        and current.status is TranscriptStatus.READY
        and source.fingerprint == fp
        and current.normalizer_version == NORMALIZER_VERSION
    ):
        return current

    version = (
        db.scalar(
            select(func.coalesce(func.max(Transcript.version), 0)).where(
                Transcript.source_video_id == source.id
            )
        )
        or 0
    ) + 1
    key = raw_storage_key(source.id, version, raw_ext)
    _, digest = storage.put(key, io.BytesIO(raw))
    try:
        with db.begin_nested():
            if current is not None:
                current.is_current = False
                db.flush()  # free the partial-unique slot before inserting the new current row
            transcript = Transcript(
                source_video_id=source.id,
                version=version,
                is_current=True,
                status=TranscriptStatus.READY,
                origin=origin,
                language=language,
                text=cleaned_text(normalized),
                segments=_segments_json(normalized),
                raw_storage_key=key,
                raw_sha256=digest,
                normalizer_version=NORMALIZER_VERSION,
            )
            db.add(transcript)
            db.flush()
            db.add_all(
                TranscriptChunk(
                    transcript_id=transcript.id,
                    chunk_index=i,
                    text=text,
                    start_seconds=start,
                    end_seconds=end,
                )
                for i, (text, start, end) in enumerate(chunk_segments(normalized))
            )
            source.fingerprint = fp
            if language and not source.language:
                source.language = language
            db.flush()
    except Exception:
        storage.delete(key)
        raise
    return transcript


def record_transcript_failure(db: Session, source: SourceVideo, *, code: str, message: str) -> None:
    """Make a failed transcript visible. Never replaces a working (ready) current transcript."""
    current = current_transcript(db, source.id)
    text = f"{code}: {message}"[:1000]
    if current is not None and current.status is TranscriptStatus.READY:
        return  # the run carries the error; the working transcript stays current
    if current is not None:
        current.status, current.error = TranscriptStatus.FAILED, text
        db.flush()
        return
    next_version = (
        db.scalar(
            select(func.coalesce(func.max(Transcript.version), 0)).where(
                Transcript.source_video_id == source.id
            )
        )
        or 0
    ) + 1
    db.add(
        Transcript(
            source_video_id=source.id,
            version=next_version,
            is_current=True,
            status=TranscriptStatus.FAILED,
            origin="unknown",
            error=text,
        )
    )
    db.flush()


# ------------------------------------------------------------------------------ add: upload
def add_source_from_transcript(
    db: Session,
    storage: LocalStorage,
    *,
    title: str,
    segments: list[TranscriptSegment],
    raw: bytes,
    raw_ext: str,
    language: str | None = None,
    reference_url: str | None = None,
) -> AddResult:
    """Add a transcript with no remote origin. Identical content (by fingerprint) returns the existing source."""
    normalized = normalize_segments(segments)
    if not normalized:
        raise TranscriptParseError("the transcript has no text")
    fp = fingerprint(normalized)

    def existing() -> AddResult | None:
        found = (
            db.scalars(select(SourceVideo).where(SourceVideo.fingerprint == fp)).first()
            or db.scalars(
                select(SourceVideo).where(
                    SourceVideo.platform == "upload", SourceVideo.external_id == fp
                )
            ).first()
        )
        if found is None:
            return None
        return AddResult(found, None, True, "fingerprint", current_transcript(db, found.id))

    if (dup := existing()) is not None:
        return dup
    source = SourceVideo(
        platform="upload",
        external_id=fp,
        kind="transcript",
        url=None,
        title=title.strip()[:1024],
        language=language,
        status=SourceStatus.IMPORTED,
        meta={"reference_url": reference_url} if reference_url else {},
    )
    try:
        with db.begin_nested():
            db.add(source)
            db.flush()
    except IntegrityError:  # lost a race with an identical upload
        if (dup := existing()) is not None:
            return dup
        raise
    transcript = ingest_transcript(
        db,
        storage,
        source,
        segments=segments,
        origin="upload",
        language=language,
        raw=raw,
        raw_ext=raw_ext,
    )
    return AddResult(source, None, False, None, transcript)


# ---------------------------------------------------------------------------------- add: URL
def upsert_channel(db: Session, meta: NormalizedSource) -> Channel | None:
    """Channel row keyed by the canonical platform id (never a URL handle)."""
    if not meta.channel_external_id:
        return None

    def find() -> Channel | None:
        return db.scalars(
            select(Channel).where(
                Channel.platform == meta.platform, Channel.external_id == meta.channel_external_id
            )
        ).first()

    channel = find()
    title = (meta.channel_title or meta.channel_external_id)[:512]
    if channel is not None:
        if meta.channel_title and channel.title != title:
            channel.title = title
        return channel
    channel = Channel(
        platform=meta.platform,
        external_id=meta.channel_external_id,
        title=title,
        url=(meta.channel_url or meta.url)[:2048],
        status=SourceStatus.DISCOVERED,
    )
    try:
        with db.begin_nested():
            db.add(channel)
            db.flush()
    except IntegrityError:
        found = find()
        if found is None:
            raise
        return found
    return channel


def start_add_from_url(db: Session, url: str) -> AddResult:
    """Validate the URL, create the source row and a queued run (idempotent). Caller commits, then
    calls `submit_run` so the worker only starts after the rows are durable."""
    extractor = get_extractor(url)
    ref = extractor.identify(url)
    if ref.kind != "video":
        raise UnsupportedSourceKindError(
            f"this is a {ref.kind} URL; channel and playlist import arrives in a later release — add a single video URL"
        )
    extractor.ensure_available()  # 503 with an install hint before anything is created

    def existing() -> SourceVideo | None:
        return db.scalars(
            select(SourceVideo).where(
                SourceVideo.platform == ref.platform, SourceVideo.external_id == ref.external_id
            )
        ).first()

    runs = RunService(db)
    found = existing()
    if found is not None:
        return AddResult(
            found, runs.active_for(RUN_ADD, found.id) or runs.active_for(RUN_FETCH, found.id), True,
            "identity", current_transcript(db, found.id),
        )  # fmt: skip
    source = SourceVideo(
        platform=ref.platform,
        external_id=ref.external_id,
        kind=ref.platform,
        url=ref.canonical_url,
        title=ref.external_id,  # placeholder until metadata arrives
        status=SourceStatus.IMPORTING,
    )
    try:
        with db.begin_nested():
            db.add(source)
            db.flush()
    except IntegrityError:
        found = existing()
        if found is None:
            raise
        return AddResult(found, runs.active_for(RUN_ADD, found.id), True, "identity", None)
    run, _ = runs.start(RUN_ADD, "source_video", source.id, params={"url": ref.canonical_url})
    return AddResult(source, run, False)


def submit_run(run: WorkflowRun) -> None:
    """Hand a committed, queued run to the process runner."""
    get_runner().submit(run.kind, run_source_workflow, run.id)


def retry_source(db: Session, source_id: uuid.UUID) -> tuple[WorkflowRun, bool]:
    """Start the missing half again. Returns (run, created); the active run if there already is one."""
    source = db.get(SourceVideo, source_id)
    if source is None:
        raise LookupError("source not found")
    runs = RunService(db)
    active = runs.active_for(RUN_ADD, source.id) or runs.active_for(RUN_FETCH, source.id)
    if active is not None:
        return active, False
    transcript = current_transcript(db, source.id)
    if source.status in (SourceStatus.FAILED, SourceStatus.DISCOVERED, SourceStatus.IMPORTING):
        kind = RUN_ADD
    elif source.kind == "youtube" and (
        transcript is None or transcript.status is not TranscriptStatus.READY
    ):
        kind = RUN_FETCH
    else:
        raise NothingToRetryError("nothing to retry: the source and its transcript are fine")
    if source.status is not SourceStatus.IMPORTED:
        source.status, source.error = SourceStatus.IMPORTING, None
    return runs.start(kind, "source_video", source.id, params={"url": source.url})


# ----------------------------------------------------------------------------------- worker
def _classify(exc: Exception) -> tuple[str, bool, str]:
    """(code, retryable, safe message) for a failure. Unknown errors never leak their text."""
    if isinstance(exc, SourceUnavailableError):
        return "video_unavailable", False, str(exc)
    if isinstance(exc, NoCaptionsError):
        return "no_captions", False, str(exc) or "this video has no captions"
    if isinstance(exc, FileTooLargeError):
        return "transcript_too_large", False, str(exc)
    if isinstance(exc, TranscriptParseError):
        return "transcript_parse_error", False, str(exc)
    if isinstance(exc, ProviderNotConfiguredError):
        return "provider_not_configured", False, str(exc)
    if isinstance(exc, ProviderTimeoutError):
        return "provider_timeout", True, str(exc)
    if isinstance(exc, ProviderError):
        return "provider_error", True, str(exc)
    return "internal_error", True, "unexpected error (see server logs)"


def _apply_metadata(db: Session, source: SourceVideo, meta: NormalizedSource) -> None:
    channel = upsert_channel(db, meta)
    source.title = (meta.title or source.title)[:1024]
    source.description = meta.description
    source.duration_seconds = meta.duration_seconds
    source.published_at = meta.published_at
    source.thumbnail_url = meta.thumbnail_url
    if meta.language:
        source.language = meta.language
    if channel is not None:
        source.channel_id = channel.id
    source.meta = {**(source.meta or {}), **meta.extra}
    source.status, source.error = SourceStatus.IMPORTED, None


def run_source_workflow(
    run_id: uuid.UUID,
    *,
    session_factory: Callable[[], Session] | None = None,
    storage: LocalStorage | None = None,
    extractor: SourceExtractor | None = None,
) -> None:
    """Worker body for `source.add` and `source.fetch_transcript`. Owns its session; never raises."""
    session_factory = session_factory or get_sessionmaker()
    storage = storage or get_storage()
    with session_factory() as db:
        runs = RunService(db)
        run = runs.get(run_id)
        if run is None or run.status is not RunStatus.QUEUED:
            return
        source = db.get(SourceVideo, run.subject_id)
        if source is None:
            runs.mark_failed(
                run, code="source_missing", message="the source was deleted", retryable=False
            )
            db.commit()
            return
        log = get_logger(
            workflow_id=str(run.id), source_id=str(source.id), platform=source.platform
        )
        runs.mark_running(run)
        db.commit()
        log.info("source.add.started", status="running")
        started = datetime.now(UTC)
        step = "metadata"
        try:
            ex = extractor or get_extractor(source.url or "")
            if run.kind == RUN_ADD:
                runs.set_progress(run, step="metadata")
                db.commit()
                _apply_metadata(db, source, ex.extract(source.url or ""))
                db.commit()
            step = "transcript"
            runs.set_progress(run, step="transcript")
            db.commit()
            fetched = ex.fetch_transcript(source.url or "", get_settings().caption_languages)
            if fetched is None:
                raise NoCaptionsError("this video has no captions in an accepted language")
            transcript = ingest_transcript(
                db, storage, source, segments=fetched.segments, origin=fetched.origin,
                language=fetched.language, raw=fetched.raw, raw_ext=fetched.raw_ext,
            )  # fmt: skip
            chunk_count = db.scalar(
                select(func.count())
                .select_from(TranscriptChunk)
                .where(TranscriptChunk.transcript_id == transcript.id)
            )
            runs.set_progress(
                run, step="done", segment_count=len(transcript.segments), chunk_count=chunk_count
            )
            runs.mark_succeeded(run)
            db.commit()
            log.info("source.add.finished", status="ok", chunk_count=chunk_count,
                     duration=round((datetime.now(UTC) - started).total_seconds(), 3))  # fmt: skip
        except Exception as exc:  # noqa: BLE001 — the error boundary for background work
            db.rollback()
            code, retryable, message = _classify(exc)
            log.warning(
                "source.add.failed", status="failed", error_code=code, error=type(exc).__name__
            )
            source = db.get(SourceVideo, run.subject_id)
            if source is not None:
                if step == "metadata":
                    source.status, source.error = SourceStatus.FAILED, f"{code}: {message}"[:1000]
                else:
                    record_transcript_failure(db, source, code=code, message=message)
            runs = RunService(db)
            run = runs.get(run_id)
            if run is not None:
                runs.mark_failed(run, code=code, message=message, retryable=retryable)
            db.commit()


# ------------------------------------------------------------------------- housekeeping
def reconcile_stale(db: Session) -> dict[str, int]:
    """Startup: nothing survives a restart, so active runs are dead and half-imported rows are failed."""
    interrupted = RunService(db).interrupt_stale()
    stuck_sources = db.scalars(
        select(SourceVideo).where(SourceVideo.status == SourceStatus.IMPORTING)
    ).all()
    for s in stuck_sources:
        s.status, s.error = SourceStatus.FAILED, "interrupted: the server stopped during import"
    stuck_tr = db.scalars(
        select(Transcript).where(Transcript.status == TranscriptStatus.PROCESSING)
    ).all()
    for t in stuck_tr:
        t.status, t.error = TranscriptStatus.FAILED, "interrupted: the server stopped during import"
    db.flush()
    return {"runs": interrupted, "sources": len(stuck_sources), "transcripts": len(stuck_tr)}


def delete_source(db: Session, storage: LocalStorage, source: SourceVideo) -> bool:
    """Delete a source and its raw files. Returns False (nothing deleted) if any project uses it."""
    if db.scalar(
        select(func.count())
        .select_from(ProjectSource)
        .where(ProjectSource.source_video_id == source.id)
    ):
        return False
    keys = [
        k
        for k in db.scalars(
            select(Transcript.raw_storage_key).where(Transcript.source_video_id == source.id)
        )
        if k
    ]
    db.execute(delete(WorkflowRun).where(WorkflowRun.subject_id == source.id))
    db.delete(source)  # transcripts, chunks, links cascade
    db.flush()
    for key in keys:  # after the rows are gone; best effort
        try:
            storage.delete(key)
        except Exception:  # noqa: BLE001
            get_logger(source_id=str(source.id)).warning("source.delete.file_failed", status="warn")
    return True
