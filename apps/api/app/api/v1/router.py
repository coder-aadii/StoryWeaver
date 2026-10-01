from fastapi import APIRouter

from app.api.crud import crud_router
from app.api.v1 import health, project_sources, runs, sources
from app.models import (
    Asset,
    Channel,
    Collection,
    Project,
    Render,
    Scene,
    Script,
    Topic,
    Transcript,
)
from app.schemas import resources as r

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
# Service-backed routers are registered BEFORE the generic CRUD ones (route order matters).
api_router.include_router(sources.router)
api_router.include_router(runs.router)
api_router.include_router(project_sources.router)

for _model, _create, _update, _read, _prefix, _tag in [
    (Channel, r.ChannelCreate, r.ChannelUpdate, r.ChannelRead, "/channels", "channels"),
    (Transcript, None, None, r.TranscriptRead, "/transcripts", "transcripts"),  # read-only: ingestion owns writes
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
            model=_model,
            create=_create,
            update=_update,
            read=_read,
            prefix=_prefix,
            tag=_tag,
            allow_delete=_model is not Transcript,
        )
    )
