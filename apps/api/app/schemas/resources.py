"""API request/response models for the CRUD resources."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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


class _Patch(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- channels
class ChannelCreate(BaseModel):
    platform: str = "youtube"
    external_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=512)
    url: str = Field(min_length=1, max_length=2048)


class ChannelUpdate(_Patch):
    title: str | None = None
    status: SourceStatus | None = None
    video_count: int | None = None


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
    platform: str = "youtube"
    external_id: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=1024)
    description: str | None = None
    duration_seconds: float | None = None
    language: str | None = None


class SourceVideoUpdate(_Patch):
    title: str | None = None
    description: str | None = None
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
    origin: str = "upload"
    language: str | None = None
    text: str | None = None
    segments: list[dict[str, Any]] = []


class TranscriptUpdate(_Patch):
    status: TranscriptStatus | None = None
    text: str | None = None


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
    description: str | None = None


class TopicUpdate(_Patch):
    name: str | None = None
    description: str | None = None


class TopicRead(ReadModel):
    name: str
    slug: str
    description: str | None


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class CollectionUpdate(_Patch):
    name: str | None = None
    description: str | None = None


class CollectionRead(ReadModel):
    name: str
    description: str | None


# --- projects
class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    settings: dict[str, Any] = {}


class ProjectUpdate(_Patch):
    title: str | None = None
    description: str | None = None
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
    title: str | None = None


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
