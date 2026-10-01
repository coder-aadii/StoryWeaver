"""Request/response models of the Source Library API (P1). The OpenAPI contract the web app builds on."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RunStatus, SourceStatus, TranscriptStatus
from app.schemas.source import TranscriptSegment


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class RunError(BaseModel):
    code: str  # stable machine code, e.g. "no_captions", "video_unavailable", "interrupted"
    message: str
    retryable: bool


class RunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    subject_type: str
    subject_id: uuid.UUID
    status: RunStatus
    attempt: int
    progress: dict[str, Any]  # {step, segment_count, chunk_count, ...}
    error: RunError | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class SourceFromUrl(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class SourceListItem(BaseModel):
    id: uuid.UUID
    title: str
    platform: str
    kind: Literal["youtube", "transcript"]
    url: str | None
    thumbnail_url: str | None
    duration_seconds: float | None
    language: str | None
    status: SourceStatus
    error: str | None
    channel_title: str | None
    transcript_status: TranscriptStatus | None  # status of the current transcript, if any
    transcript_error: str | None
    chunk_count: int
    searchable: bool  # derived: current transcript is ready and has >= 1 chunk
    usage_count: int  # number of projects linked to this source
    created_at: datetime
    updated_at: datetime


class TranscriptSummary(BaseModel):
    id: uuid.UUID
    version: int
    status: TranscriptStatus
    origin: str
    language: str | None
    segment_count: int
    char_count: int
    timed: bool  # False for plain-text transcripts (no timestamps)
    normalizer_version: str | None
    error: str | None
    created_at: datetime


class SourceDetail(SourceListItem):
    description: str | None
    published_at: datetime | None
    fingerprint: str | None
    transcript: TranscriptSummary | None
    active_run: RunRead | None  # a queued/running run for this source, if any


class AddSourceResult(BaseModel):
    source: SourceListItem
    run: RunRead | None  # set when a background run was started or is already active
    already_exists: bool
    match: Literal["identity", "fingerprint"] | None = None
    transcript: TranscriptSummary | None = None


class TranscriptContent(BaseModel):
    transcript: TranscriptSummary
    text: str
    segments: Page[TranscriptSegment]


class ChunkRead(BaseModel):
    id: uuid.UUID
    chunk_index: int
    text: str
    start_seconds: float | None
    end_seconds: float | None


class SearchHit(BaseModel):
    source: SourceListItem
    chunk_id: uuid.UUID
    chunk_index: int
    snippet: str  # plain text with matches wrapped in <mark>…</mark> (everything else HTML-escaped)
    start_seconds: float | None
    end_seconds: float | None
    rank: float


class RetryResult(BaseModel):
    run: RunRead


class SourceUsage(BaseModel):
    project_id: uuid.UUID
    project_title: str
    role: str
    linked_at: datetime


class ProjectSourceLink(BaseModel):
    source: SourceListItem
    role: str
    linked_at: datetime


class ProjectSourceIn(BaseModel):
    role: str = Field(default="primary", min_length=1, max_length=32)
