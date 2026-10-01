"""API request/response models for the CRUD resources."""

import uuid
from datetime import datetime
from typing import Any, ClassVar
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.errors import InvalidSourceError
from app.ingestion.youtube import classify_youtube_url
from app.models.enums import (
    AssetStatus,
    AssetType,
    ProjectStatus,
    RenderStatus,
    SceneStatus,
    SourceStatus,
    TranscriptStatus,
)


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


DESCRIPTION = (
    20_000  # characters; descriptions are TEXT columns but unbounded input is a DoS vector
)
TRANSCRIPT_TEXT = 5_000_000


class _Patch(BaseModel):
    """Base for PATCH bodies: unknown fields are rejected and NOT NULL fields cannot be set to null.

    Only fields listed in `nullable_fields` accept an explicit `null` (which clears the column).
    """

    model_config = ConfigDict(extra="forbid")
    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def _reject_null_for_required_fields(self) -> "_Patch":
        for name in self.model_fields_set:
            if getattr(self, name) is None and name not in self.nullable_fields:
                raise ValueError(f"'{name}' cannot be null")
        return self


def _validate_source_url(platform: str, url: str, kinds: tuple[str, ...]) -> None:
    """URL must be http(s); for YouTube it must also be a recognised URL of an allowed kind."""
    if platform == "youtube":
        try:
            kind, _ = classify_youtube_url(url)
        except InvalidSourceError as exc:
            raise ValueError(str(exc)) from exc
        if kind not in kinds:
            raise ValueError(f"expected a YouTube {' or '.join(kinds)} URL, got a {kind} URL")
    elif urlparse(url).scheme not in ("http", "https"):
        raise ValueError("url must start with http:// or https://")


# --- channels
class ChannelCreate(BaseModel):
    platform: str = Field(default="youtube", min_length=1, max_length=32)
    external_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=512)
    url: str = Field(min_length=1, max_length=2048)

    @model_validator(mode="after")
    def _check_url(self) -> "ChannelCreate":
        _validate_source_url(self.platform, self.url, ("channel",))
        return self


class ChannelUpdate(_Patch):
    nullable_fields = frozenset({"video_count"})
    title: str | None = Field(default=None, min_length=1, max_length=512)
    status: SourceStatus | None = None
    video_count: int | None = Field(default=None, ge=0)


class ChannelRead(ReadModel):
    platform: str
    external_id: str
    title: str
    url: str
    status: SourceStatus
    video_count: int | None
    error: str | None


# --- source videos
class SourceVideoCreate(BaseModel):
    channel_id: uuid.UUID | None = None
    platform: str = Field(default="youtube", min_length=1, max_length=32)
    external_id: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=1024)
    description: str | None = Field(default=None, max_length=DESCRIPTION)
    duration_seconds: float | None = Field(default=None, ge=0)
    language: str | None = Field(default=None, max_length=16)

    @model_validator(mode="after")
    def _check_url(self) -> "SourceVideoCreate":
        _validate_source_url(self.platform, self.url, ("video",))
        return self


class SourceVideoUpdate(_Patch):
    nullable_fields = frozenset({"description"})
    title: str | None = Field(default=None, min_length=1, max_length=1024)
    description: str | None = Field(default=None, max_length=DESCRIPTION)
    status: SourceStatus | None = None


class SourceVideoRead(ReadModel):
    channel_id: uuid.UUID | None
    platform: str
    external_id: str
    url: str
    title: str
    description: str | None
    duration_seconds: float | None
    language: str | None
    status: SourceStatus
    error: str | None


# --- transcripts
class TranscriptCreate(BaseModel):
    source_video_id: uuid.UUID
    origin: str = Field(default="upload", min_length=1, max_length=32)
    language: str | None = Field(default=None, max_length=16)
    text: str | None = Field(default=None, max_length=TRANSCRIPT_TEXT)
    segments: list[dict[str, Any]] = Field(default=[], max_length=100_000)


class TranscriptUpdate(_Patch):
    nullable_fields = frozenset({"text"})
    status: TranscriptStatus | None = None
    text: str | None = Field(default=None, max_length=TRANSCRIPT_TEXT)


class TranscriptRead(ReadModel):
    source_video_id: uuid.UUID
    version: int
    status: TranscriptStatus
    origin: str
    language: str | None
    text: str | None
    error: str | None


# --- topics / collections
class TopicCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = Field(default=None, max_length=DESCRIPTION)


class TopicUpdate(_Patch):
    nullable_fields = frozenset({"description"})
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=DESCRIPTION)


class TopicRead(ReadModel):
    name: str
    slug: str
    description: str | None


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=DESCRIPTION)


class CollectionUpdate(_Patch):
    nullable_fields = frozenset({"description"})
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=DESCRIPTION)


class CollectionRead(ReadModel):
    name: str
    description: str | None


# --- projects
class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=DESCRIPTION)
    settings: dict[str, Any] = {}


class ProjectUpdate(_Patch):
    nullable_fields = frozenset({"description"})
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=DESCRIPTION)
    status: ProjectStatus | None = None
    settings: dict[str, Any] | None = None


class ProjectRead(ReadModel):
    title: str
    description: str | None
    status: ProjectStatus
    settings: dict[str, Any]
    error: str | None


# --- scripts / scenes
class ScriptCreate(BaseModel):
    project_id: uuid.UUID
    title: str = Field(min_length=1, max_length=512)


class ScriptUpdate(_Patch):
    title: str | None = Field(default=None, min_length=1, max_length=512)


class ScriptRead(ReadModel):
    project_id: uuid.UUID
    title: str


class SceneCreate(BaseModel):
    project_id: uuid.UUID
    script_id: uuid.UUID | None = None
    sequence: int = Field(ge=1)


class SceneUpdate(_Patch):
    sequence: int | None = Field(default=None, ge=1)
    status: SceneStatus | None = None


class SceneRead(ReadModel):
    project_id: uuid.UUID
    script_id: uuid.UUID | None
    sequence: int
    status: SceneStatus
    error: str | None


# --- assets / renders
class AssetCreate(BaseModel):
    project_id: uuid.UUID
    scene_id: uuid.UUID | None = None
    type: AssetType


class AssetUpdate(_Patch):
    status: AssetStatus | None = None


class AssetRead(ReadModel):
    project_id: uuid.UUID
    scene_id: uuid.UUID | None
    type: AssetType
    status: AssetStatus
    storage_key: str | None
    mime_type: str | None
    size_bytes: int | None
    checksum: str | None
    error: str | None


class RenderCreate(BaseModel):
    project_id: uuid.UUID


class RenderUpdate(_Patch):
    status: RenderStatus | None = None


class RenderRead(ReadModel):
    project_id: uuid.UUID
    status: RenderStatus
    output_asset_id: uuid.UUID | None
    error: str | None
