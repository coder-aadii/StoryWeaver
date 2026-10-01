from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

SourceKind = Literal["video", "channel", "playlist", "transcript", "file"]
# Where a transcript came from. `manual`/`auto` are platform captions; `upload` is user-supplied.
TranscriptOrigin = Literal["manual", "auto", "upload"]


class TranscriptSegment(BaseModel):
    """One timed (or untimed) piece of transcript text.

    `start`/`end` are None for untimed sources such as plain .txt — times are never fabricated.
    """

    start: float | None = Field(default=None, ge=0)
    end: float | None = Field(default=None, ge=0)
    text: str
    speaker: str | None = None

    @model_validator(mode="after")
    def _end_not_before_start(self) -> "TranscriptSegment":
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("end must not be before start")
        return self


class ExtractedTranscript(BaseModel):
    """A transcript as obtained from a source provider or an upload, before normalization."""

    segments: list[TranscriptSegment]
    language: str | None = None
    origin: TranscriptOrigin
    raw: bytes = Field(repr=False)  # exactly as received; never mutated, stored as the raw file
    raw_ext: str = Field(pattern=r"^[a-z0-9]{1,8}$")  # "srt", "vtt", "json3", "txt"


class SourceRef(BaseModel):
    """What a URL points at, determined WITHOUT any network access (see SourceExtractor.identify).

    For `kind == "video"`, `external_id` is the platform's stable video id and `canonical_url` the
    normalized form used for storage and dedupe. For channels, `external_id` is only the token found in
    the URL (a handle such as "@name" can change) — the canonical channel id comes from `extract()`.
    """

    platform: str
    external_id: str
    kind: SourceKind
    canonical_url: str


class NormalizedSource(BaseModel):
    """Platform-neutral result of any SourceExtractor. YouTube specifics stop at this boundary."""

    platform: str
    kind: SourceKind
    external_id: str
    url: str
    title: str
    description: str | None = None
    duration_seconds: float | None = None
    published_at: datetime | None = None
    language: str | None = None
    channel_external_id: str | None = None
    channel_title: str | None = None
    channel_url: str | None = None  # built from the canonical channel id; None when unknown
    thumbnail_url: str | None = None
    segments: list[TranscriptSegment] = []
    extra: dict[str, Any] = {}
