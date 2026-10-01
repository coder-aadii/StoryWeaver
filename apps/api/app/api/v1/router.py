from fastapi import APIRouter

from app.api.crud import crud_router
from app.api.v1 import health
from app.models import (
    Asset,
    Channel,
    Collection,
    Project,
    Render,
    Scene,
    Script,
    SourceVideo,
    Topic,
    Transcript,
)
from app.schemas import resources as r

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)

for _model, _create, _update, _read, _prefix, _tag in [
    (Channel, r.ChannelCreate, r.ChannelUpdate, r.ChannelRead, "/channels", "channels"),
    (SourceVideo, r.SourceVideoCreate, r.SourceVideoUpdate, r.SourceVideoRead, "/sources", "sources"),
    (Transcript, r.TranscriptCreate, r.TranscriptUpdate, r.TranscriptRead, "/transcripts", "transcripts"),
    (Topic, r.TopicCreate, r.TopicUpdate, r.TopicRead, "/topics", "topics"),
    (Collection, r.CollectionCreate, r.CollectionUpdate, r.CollectionRead, "/collections", "collections"),
    (Project, r.ProjectCreate, r.ProjectUpdate, r.ProjectRead, "/projects", "projects"),
    (Script, r.ScriptCreate, r.ScriptUpdate, r.ScriptRead, "/scripts", "scripts"),
    (Scene, r.SceneCreate, r.SceneUpdate, r.SceneRead, "/scenes", "scenes"),
    (Asset, r.AssetCreate, r.AssetUpdate, r.AssetRead, "/assets", "assets"),
    (Render, r.RenderCreate, r.RenderUpdate, r.RenderRead, "/renders", "renders"),
]:  # fmt: skip
    api_router.include_router(
        crud_router(
            model=_model, create=_create, update=_update, read=_read, prefix=_prefix, tag=_tag
        )
    )
