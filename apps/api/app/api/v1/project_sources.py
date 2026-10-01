"""Link sources to projects (project-level usage tracking)."""

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import ApiError
from app.db.session import get_db
from app.ingestion import queries
from app.models import Project, ProjectSource, SourceVideo
from app.models.enums import SourceStatus
from app.schemas.source_api import ProjectSourceIn, ProjectSourceLink

router = APIRouter(prefix="/projects/{project_id}/sources", tags=["projects"])


def _require_project(db: Session, project_id: uuid.UUID) -> None:
    if db.get(Project, project_id) is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "not_found", "project not found")


@router.get("", response_model=list[ProjectSourceLink])
def list_project_sources(
    project_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[ProjectSourceLink]:
    _require_project(db, project_id)
    return queries.project_sources(db, project_id)


@router.put("/{source_id}", response_model=ProjectSourceLink)
def link_source(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    body: ProjectSourceIn | None = None,
    db: Session = Depends(get_db),
) -> ProjectSourceLink:
    """Idempotent: linking twice updates the role and returns the same link."""
    _require_project(db, project_id)
    source = db.get(SourceVideo, source_id)
    if source is None:
        raise ApiError(status.HTTP_404_NOT_FOUND, "not_found", "source not found")
    if source.status is not SourceStatus.IMPORTED:
        raise ApiError(409, "source_not_ready", "only imported sources can be added to a project")
    role = (body or ProjectSourceIn()).role
    link = db.scalars(
        select(ProjectSource).where(
            ProjectSource.project_id == project_id, ProjectSource.source_video_id == source_id
        )
    ).first()
    if link is None:
        db.add(ProjectSource(project_id=project_id, source_video_id=source_id, role=role))
    else:
        link.role = role
    db.commit()
    return next(
        item for item in queries.project_sources(db, project_id) if item.source.id == source_id
    )


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_source(
    project_id: uuid.UUID, source_id: uuid.UUID, db: Session = Depends(get_db)
) -> Response:
    _require_project(db, project_id)
    link = db.scalars(
        select(ProjectSource).where(
            ProjectSource.project_id == project_id, ProjectSource.source_video_id == source_id
        )
    ).first()
    if link is not None:
        db.delete(link)
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
