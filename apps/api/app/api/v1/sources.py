"""Source Library routes. Thin: validation and HTTP shape here, logic in `app.ingestion.service`."""

import re
import time
import uuid
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.storage import get_storage, sanitize_filename
from app.db.session import get_db
from app.ingestion import queries, service
from app.ingestion.parsers import parse_transcript
from app.models import SourceVideo
from app.models.enums import SourceStatus
from app.schemas.resources import SourceVideoUpdate
from app.schemas.source import TranscriptSegment
from app.schemas.source_api import (
    AddSourceResult,
    ChunkRead,
    Page,
    RetryResult,
    SearchHit,
    SourceDetail,
    SourceFromUrl,
    SourceListItem,
    SourceUsage,
    TranscriptContent,
)
from app.workflows.runs import RunService

router = APIRouter(prefix="/sources", tags=["sources"])
UPLOAD_EXTENSIONS = {"txt", "srt", "vtt"}
_SRT_TIMING = re.compile(r"\d{1,2}:\d\d:\d\d[,.]\d{1,3}\s*-->")


def _get_source(db: Session, source_id: uuid.UUID) -> SourceVideo:
    source = db.get(SourceVideo, source_id)
    if source is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "not_found", "source not found")
    return source


def _result(db: Session, result: service.AddResult) -> AddSourceResult:
    transcript = result.transcript
    return AddSourceResult(
        source=queries.list_item(db, result.source),
        run=queries.run_read(result.run) if result.run else None,
        already_exists=result.already_exists,
        match=result.match,  # type: ignore[arg-type]
        transcript=queries.transcript_summary(transcript) if transcript else None,
    )


@router.post("/from-url", response_model=AddSourceResult, status_code=status.HTTP_202_ACCEPTED)
def add_from_url(
    body: SourceFromUrl, response: Response, db: Session = Depends(get_db)
) -> AddSourceResult:
    """Start adding a YouTube video: metadata + captions, no media download. Poll `run` for progress."""
    result = service.start_add_from_url(db, body.url.strip())
    db.commit()
    if result.run is not None and not result.already_exists:
        service.submit_run(result.run)
    if result.already_exists:
        response.status_code = status.HTTP_200_OK
    return _result(db, result)


def _sniff_extension(text: str) -> str:
    head = text.lstrip()[:2000]
    if head.startswith("WEBVTT"):
        return "vtt"
    return "srt" if _SRT_TIMING.search(head) else "txt"


def _read_transcript_input(
    file: UploadFile | None, text: str | None
) -> tuple[list[TranscriptSegment], bytes, str]:
    """Validate an upload/paste and return (segments, raw bytes, extension). Never trusts the filename."""
    has_text = text is not None and text.strip() != ""
    if (file is not None) == has_text:
        raise ApiError(422, "invalid_input", "provide exactly one of 'file' or 'text'")
    limit = get_settings().max_transcript_bytes
    if file is not None:
        ext = Path(sanitize_filename(file.filename or "")).suffix.lstrip(".").lower()
        if ext not in UPLOAD_EXTENSIONS:
            raise ApiError(422, "unsupported_file_type", "upload a .txt, .srt or .vtt file")
        data = file.file.read(limit + 1)  # parse_transcript enforces the cap (413)
    else:
        assert text is not None
        data = text.encode("utf-8")
        ext = _sniff_extension(text)
    return parse_transcript(ext, data, limit), data, ext


@router.post(
    "/from-transcript", response_model=AddSourceResult, status_code=status.HTTP_201_CREATED
)
def add_from_transcript(
    response: Response,
    title: Annotated[str, Form(min_length=1, max_length=1024)],
    db: Session = Depends(get_db),
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form(max_length=5_000_000)] = None,
    language: Annotated[str | None, Form(max_length=16)] = None,
    reference_url: Annotated[str | None, Form(max_length=2048)] = None,
) -> AddSourceResult:
    """Add a transcript with no remote origin (.txt/.srt/.vtt upload or pasted text)."""
    if title.strip() == "":
        raise ApiError(422, "invalid_input", "title must not be blank")
    if reference_url and urlparse(reference_url).scheme not in ("http", "https"):
        raise ApiError(422, "invalid_input", "reference_url must start with http:// or https://")
    segments, data, ext = _read_transcript_input(file, text)
    result = service.add_source_from_transcript(
        db,
        get_storage(),
        title=title,
        segments=segments,
        raw=data,
        raw_ext=ext,
        language=(language or "").strip() or None,
        reference_url=reference_url,
    )
    db.commit()
    if result.already_exists:
        response.status_code = status.HTTP_200_OK
    return _result(db, result)


@router.get("", response_model=Page[SourceListItem])
def list_sources(
    db: Session = Depends(get_db),
    status_: Annotated[SourceStatus | None, Query(alias="status")] = None,
    kind: Literal["youtube", "transcript"] | None = None,
    used: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[SourceListItem]:
    rows, total = queries.query_sources(
        db, status=status_, kind=kind, used=used, limit=limit, offset=offset
    )
    return Page[SourceListItem](
        items=queries.list_items(db, rows), total=total, limit=limit, offset=offset
    )


# NOTE: registered before "/{source_id}", otherwise "search" would be parsed as a UUID (422).
@router.get("/search", response_model=Page[SearchHit])
def search_sources(
    db: Session = Depends(get_db),
    q: str = Query(min_length=1, max_length=200),
    exclude_used: bool = False,
    source_id: uuid.UUID | None = None,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> Page[SearchHit]:
    started = time.perf_counter()
    hits, total = queries.search(
        db, q, exclude_used=exclude_used, source_id=source_id, limit=limit, offset=offset
    )
    get_logger().info(  # length only: the query text may be sensitive
        "search.executed",
        query_length=len(q),
        hit_count=total,
        duration=round(time.perf_counter() - started, 4),
        status="ok",
    )
    return Page[SearchHit](items=hits, total=total, limit=limit, offset=offset)


@router.get("/{source_id}", response_model=SourceDetail)
def get_source(source_id: uuid.UUID, db: Session = Depends(get_db)) -> SourceDetail:
    return queries.detail(db, _get_source(db, source_id))


@router.patch("/{source_id}", response_model=SourceDetail)
def update_source(
    source_id: uuid.UUID, body: SourceVideoUpdate, db: Session = Depends(get_db)
) -> SourceDetail:
    source = _get_source(db, source_id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(source, key, value)
    db.commit()
    return queries.detail(db, source)


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source(source_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    source = _get_source(db, source_id)
    if not service.delete_source(db, get_storage(), source):
        raise ApiError(409, "source_in_use", "this source is used by a project; unlink it first")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{source_id}/transcript", response_model=TranscriptContent)
def get_transcript(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> TranscriptContent:
    _get_source(db, source_id)
    transcript = queries.current_transcript_of(db, source_id)
    if transcript is None:
        raise ApiError(404, "no_transcript", "this source has no transcript yet")
    return queries.transcript_content(transcript, limit=limit, offset=offset)


@router.get("/{source_id}/chunks", response_model=Page[ChunkRead])
def get_chunks(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[ChunkRead]:
    _get_source(db, source_id)
    transcript = queries.current_transcript_of(db, source_id)
    if transcript is None:
        raise ApiError(404, "no_transcript", "this source has no transcript yet")
    return queries.chunks_page(db, transcript, limit=limit, offset=offset)


@router.post("/{source_id}/transcript", response_model=SourceDetail)
def attach_transcript(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form(max_length=5_000_000)] = None,
    language: Annotated[str | None, Form(max_length=16)] = None,
) -> SourceDetail:
    """Attach (or replace with a new version) a transcript on an existing source — the fallback for
    videos without captions. Re-sending identical content is a no-op."""
    source = _get_source(db, source_id)
    runs = RunService(db)
    if runs.active_for(service.RUN_ADD, source_id) or runs.active_for(service.RUN_FETCH, source_id):
        raise ApiError(
            409, "source_busy", "this source is still being imported; try again when it finishes"
        )
    segments, data, ext = _read_transcript_input(file, text)
    service.ingest_transcript(
        db,
        get_storage(),
        source,
        segments=segments,
        origin="upload",
        language=(language or "").strip() or None,
        raw=data,
        raw_ext=ext,
    )
    if (
        source.status is not SourceStatus.IMPORTED
    ):  # metadata may never have arrived; the text is enough
        source.status, source.error = SourceStatus.IMPORTED, None
    db.commit()
    return queries.detail(db, source)


@router.post("/{source_id}/retry", response_model=RetryResult, status_code=status.HTTP_202_ACCEPTED)
def retry_source(source_id: uuid.UUID, db: Session = Depends(get_db)) -> RetryResult:
    _get_source(db, source_id)
    try:
        run, created = service.retry_source(db, source_id)
    except service.NothingToRetryError as exc:
        raise ApiError(409, "nothing_to_retry", str(exc)) from exc
    db.commit()
    if created:
        service.submit_run(run)
    return RetryResult(run=queries.run_read(run))


@router.get("/{source_id}/usage", response_model=list[SourceUsage])
def source_usage(source_id: uuid.UUID, db: Session = Depends(get_db)) -> list[SourceUsage]:
    _get_source(db, source_id)
    return queries.usage_of(db, source_id)
