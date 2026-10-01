from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

SourceKind = Literal["video", "channel", "playlist", "transcript", "file"]


class TranscriptSegment(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str
    speaker: str | None = None


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
    segments: list[TranscriptSegment] = []
    extra: dict[str, Any] = {}
