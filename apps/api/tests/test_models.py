import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Project,
    ProjectSource,
    Scene,
    SceneVersion,
    SourceVideo,
    Transcript,
    TranscriptChunk,
)
from app.models.enums import ProjectStatus, SceneStatus


def test_defaults_and_timestamps(db: Session) -> None:
    p = Project(title="p")
    db.add(p)
    db.commit()
    assert p.status is ProjectStatus.DRAFT
    assert p.created_at is not None and p.id is not None


def test_source_shared_by_many_projects(db: Session) -> None:
    v = SourceVideo(external_id="abc", url="u", title="t")
    p1, p2 = Project(title="a"), Project(title="b")
    db.add_all([v, p1, p2])
    db.flush()
    db.add_all([ProjectSource(project_id=p.id, source_video_id=v.id) for p in (p1, p2)])
    db.commit()
    assert len(db.scalars(select(SourceVideo)).all()) == 1  # one source row, two projects


def test_scene_versions_are_unique_per_scene(db: Session) -> None:
    p = Project(title="p")
    db.add(p)
    db.flush()
    s = Scene(project_id=p.id, sequence=1)
    db.add(s)
    db.flush()
    db.add_all(
        [
            SceneVersion(scene_id=s.id, version=1, data={}),
            SceneVersion(scene_id=s.id, version=1, data={}),
        ]
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert SceneStatus.DRAFT.value == "draft"


def test_embedding_roundtrip_and_cosine_search(db: Session) -> None:
    v = SourceVideo(external_id="e", url="u", title="t")
    db.add(v)
    db.flush()
    t = Transcript(source_video_id=v.id)
    db.add(t)
    db.flush()
    near, far = [1.0] + [0.0] * 767, [0.0, 1.0] + [0.0] * 766
    db.add_all(
        [
            TranscriptChunk(transcript_id=t.id, chunk_index=0, text="near", embedding=near),
            TranscriptChunk(transcript_id=t.id, chunk_index=1, text="far", embedding=far),
        ]
    )
    db.commit()
    best = db.scalars(
        select(TranscriptChunk).order_by(TranscriptChunk.embedding.cosine_distance(near)).limit(1)
    ).one()
    assert best.text == "near"
