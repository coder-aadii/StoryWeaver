"""Core domain tables. Binary media lives on disk/object storage; only metadata lives here."""

import enum
import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Computed,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin
from app.models.enums import (
    AssetStatus,
    AssetType,
    ProjectStatus,
    RenderStatus,
    RunStatus,
    SceneStatus,
    SourceStatus,
    TranscriptStatus,
)

# Must match Settings.embedding_dimensions; changing it requires a migration.
EMBEDDING_DIM = 768


def _enum(cls: type[enum.Enum], name: str) -> Enum:
    # VARCHAR (no native PG enum): adding a status never needs ALTER TYPE.
    return Enum(
        cls, name=name, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e]
    )


def _fk(target: str, *, nullable: bool = False, ondelete: str = "CASCADE") -> Mapped[Any]:
    return mapped_column(ForeignKey(target, ondelete=ondelete), nullable=nullable, index=True)


# ---------------------------------------------------------------- source library
class Channel(IdMixin, TimestampMixin, Base):
    __tablename__ = "channels"
    __table_args__ = (UniqueConstraint("platform", "external_id"),)

    platform: Mapped[str] = mapped_column(String(32), default="youtube")
    external_id: Mapped[str] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(2048))
    status: Mapped[SourceStatus] = mapped_column(
        _enum(SourceStatus, "source_status"), default=SourceStatus.DISCOVERED, index=True
    )
    video_count: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict)


class SourceVideo(IdMixin, TimestampMixin, Base):
    __tablename__ = "source_videos"
    __table_args__ = (UniqueConstraint("platform", "external_id"),)

    channel_id: Mapped[uuid.UUID | None] = _fk("channels.id", nullable=True, ondelete="SET NULL")
    platform: Mapped[str] = mapped_column(String(32), default="youtube")
    external_id: Mapped[str] = mapped_column(String(128))
    # NULL for sources with no remote origin (uploaded transcripts).
    url: Mapped[str | None] = mapped_column(String(2048))
    # What the source is, independent of platform: "youtube" | "transcript".
    kind: Mapped[str] = mapped_column(String(16), default="youtube")
    # sha256 of the normalized transcript's fingerprint text; detects the same content across sources.
    fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(1024))
    description: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    language: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[SourceStatus] = mapped_column(
        _enum(SourceStatus, "source_status"), default=SourceStatus.DISCOVERED, index=True
    )
    error: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict)


class Transcript(IdMixin, TimestampMixin, Base):
    __tablename__ = "transcripts"
    __table_args__ = (
        UniqueConstraint("source_video_id", "version"),
        # At most one current transcript per source.
        Index(
            "uq_transcripts_current",
            "source_video_id",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    source_video_id: Mapped[uuid.UUID] = _fk("source_videos.id")
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[TranscriptStatus] = mapped_column(
        _enum(TranscriptStatus, "transcript_status"), default=TranscriptStatus.PENDING, index=True
    )
    origin: Mapped[str] = mapped_column(String(32), default="unknown")  # manual|auto|whisper|upload
    language: Mapped[str | None] = mapped_column(String(16))
    text: Mapped[str | None] = mapped_column(Text)
    segments: Mapped[list[Any]] = mapped_column(default=list)  # [{start,end,text,speaker?}]
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    # Raw file exactly as received (never mutated), stored via LocalStorage.
    raw_storage_key: Mapped[str | None] = mapped_column(String(1024))
    raw_sha256: Mapped[str | None] = mapped_column(String(64))
    normalizer_version: Mapped[str | None] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(Text)


class TranscriptChunk(IdMixin, TimestampMixin, Base):
    __tablename__ = "transcript_chunks"
    __table_args__ = (
        UniqueConstraint("transcript_id", "chunk_index"),
        Index(
            "ix_transcript_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_transcript_chunks_search_vector", "search_vector", postgresql_using="gin"),
    )

    transcript_id: Mapped[uuid.UUID] = _fk("transcripts.id")
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    start_seconds: Mapped[float | None] = mapped_column(Float)
    end_seconds: Mapped[float | None] = mapped_column(Float)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    embedding_model: Mapped[str | None] = mapped_column(String(128))
    # Keyword search (language-neutral 'simple' config). Generated by Postgres; never written by code.
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR, Computed("to_tsvector('simple', text)", persisted=True), deferred=True
    )


class Topic(IdMixin, TimestampMixin, Base):
    __tablename__ = "topics"

    name: Mapped[str] = mapped_column(String(255), unique=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class Collection(IdMixin, TimestampMixin, Base):
    __tablename__ = "collections"

    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class CollectionVideo(TimestampMixin, Base):
    __tablename__ = "collection_videos"

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True
    )
    source_video_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_videos.id", ondelete="CASCADE"), primary_key=True, index=True
    )


# ---------------------------------------------------------------- projects
class Project(IdMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(
        _enum(ProjectStatus, "project_status"), default=ProjectStatus.DRAFT, index=True
    )
    settings: Mapped[dict[str, Any]] = mapped_column(default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class ProjectSource(TimestampMixin, Base):
    """A source video can feed many projects; a project can use many source videos."""

    __tablename__ = "project_sources"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    source_video_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_videos.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(32), default="primary")


class Script(IdMixin, TimestampMixin, Base):
    __tablename__ = "scripts"

    project_id: Mapped[uuid.UUID] = _fk("projects.id")
    title: Mapped[str] = mapped_column(String(512))


class ScriptVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "script_versions"
    __table_args__ = (UniqueConstraint("script_id", "version"),)

    script_id: Mapped[uuid.UUID] = _fk("scripts.id")
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict[str, Any]] = mapped_column(default=dict)
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(128))


class Scene(IdMixin, TimestampMixin, Base):
    __tablename__ = "scenes"
    __table_args__ = (Index("ix_scenes_project_sequence", "project_id", "sequence"),)

    project_id: Mapped[uuid.UUID] = _fk("projects.id")
    script_id: Mapped[uuid.UUID | None] = _fk("scripts.id", nullable=True, ondelete="SET NULL")
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[SceneStatus] = mapped_column(
        _enum(SceneStatus, "scene_status"), default=SceneStatus.DRAFT, index=True
    )
    error: Mapped[str | None] = mapped_column(Text)


class SceneVersion(IdMixin, TimestampMixin, Base):
    __tablename__ = "scene_versions"
    __table_args__ = (UniqueConstraint("scene_id", "version"),)

    scene_id: Mapped[uuid.UUID] = _fk("scenes.id")
    version: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict[str, Any]] = mapped_column(
        default=dict
    )  # validated by schemas.scene.SceneSpec


class Character(IdMixin, TimestampMixin, Base):
    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    project_id: Mapped[uuid.UUID] = _fk("projects.id")
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[dict[str, Any]] = mapped_column(default=dict)  # age, clothing, style, ...


class Location(IdMixin, TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("project_id", "name"),)

    project_id: Mapped[uuid.UUID] = _fk("projects.id")
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    attributes: Mapped[dict[str, Any]] = mapped_column(default=dict)


class Asset(IdMixin, TimestampMixin, Base):
    __tablename__ = "assets"

    project_id: Mapped[uuid.UUID] = _fk("projects.id")
    scene_id: Mapped[uuid.UUID | None] = _fk("scenes.id", nullable=True, ondelete="SET NULL")
    type: Mapped[AssetType] = mapped_column(_enum(AssetType, "asset_type"), index=True)
    status: Mapped[AssetStatus] = mapped_column(
        _enum(AssetStatus, "asset_status"), default=AssetStatus.PENDING, index=True
    )
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    checksum: Mapped[str | None] = mapped_column(String(128))  # sha256 hex
    error: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", default=dict)


class Render(IdMixin, TimestampMixin, Base):
    __tablename__ = "renders"

    project_id: Mapped[uuid.UUID] = _fk("projects.id")
    status: Mapped[RenderStatus] = mapped_column(
        _enum(RenderStatus, "render_status"), default=RenderStatus.QUEUED, index=True
    )
    timeline: Mapped[dict[str, Any]] = mapped_column(default=dict)  # snapshot rendered
    output_asset_id: Mapped[uuid.UUID | None] = _fk("assets.id", nullable=True, ondelete="SET NULL")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


# ---------------------------------------------------------------- workflow runs
class WorkflowRun(IdMixin, TimestampMixin, Base):
    """One persisted execution of a background workflow (D1). Generalised by later phases."""

    __tablename__ = "workflow_runs"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        Index("ix_workflow_runs_subject", "subject_type", "subject_id"),
        # At most one active run per (kind, subject): a double click returns the running one.
        Index(
            "uq_workflow_runs_active",
            "kind",
            "subject_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    kind: Mapped[str] = mapped_column(String(64))  # e.g. "source.add"
    subject_type: Mapped[str] = mapped_column(String(32))  # e.g. "source_video"
    subject_id: Mapped[uuid.UUID] = mapped_column()
    status: Mapped[RunStatus] = mapped_column(
        _enum(RunStatus, "run_status"), default=RunStatus.QUEUED, index=True
    )
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(255))
    params: Mapped[dict[str, Any]] = mapped_column(default=dict)
    progress: Mapped[dict[str, Any]] = mapped_column(
        default=dict
    )  # {step, segments, chunk_count, ...}
    error: Mapped[dict[str, Any] | None] = mapped_column()  # {code, message, retryable}
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
