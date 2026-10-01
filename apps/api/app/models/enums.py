import enum


class SourceStatus(enum.StrEnum):
    DISCOVERED = "discovered"
    IMPORTING = "importing"
    IMPORTED = "imported"
    FAILED = "failed"


class TranscriptStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ProjectStatus(enum.StrEnum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    SCRIPTING = "scripting"
    STORYBOARDING = "storyboarding"
    GENERATING = "generating"
    RENDERING = "rendering"
    QA = "qa"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetStatus(enum.StrEnum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class RenderStatus(enum.StrEnum):
    QUEUED = "queued"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"


class SceneStatus(enum.StrEnum):
    """Per-scene state so a single scene can be regenerated independently."""

    DRAFT = "draft"
    READY = "ready"
    GENERATING = "generating"
    FAILED = "failed"


class AssetType(enum.StrEnum):
    IMAGE = "image"
    AUDIO = "audio"
    VOICE = "voice"
    MUSIC = "music"
    SFX = "sfx"
    VIDEO = "video"
    THUMBNAIL = "thumbnail"
    SUBTITLE = "subtitle"
    REFERENCE = "reference"
    RENDER = "render"
