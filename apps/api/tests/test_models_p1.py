"""P1 schema: source identity, current-transcript rule, keyword search column (needs TEST_DATABASE_URL)."""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import SourceVideo, Transcript, TranscriptChunk
from app.models.enums import TranscriptStatus


def _source(db: Session, **kw: object) -> SourceVideo:
    defaults: dict[str, object] = {
        "external_id": "abc",
        "url": "https://youtu.be/abc",
        "title": "t",
    }
    src = SourceVideo(**{**defaults, **kw})
    db.add(src)
    db.flush()
    return src


def test_upload_sources_have_no_url_and_a_kind(db: Session) -> None:
    src = _source(
        db,
        platform="upload",
        external_id="f" * 64,
        url=None,
        kind="transcript",
        fingerprint="f" * 64,
    )
    db.commit()
    assert src.url is None and src.kind == "transcript"


def test_kind_defaults_to_youtube_and_identity_stays_unique(db: Session) -> None:
    assert _source(db).kind == "youtube"
    db.add(SourceVideo(external_id="abc", url="u", title="again"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_only_one_current_transcript_per_source(db: Session) -> None:
    src = _source(db)
    db.add(Transcript(source_video_id=src.id, version=1, is_current=True))
    db.add(Transcript(source_video_id=src.id, version=2, is_current=False))  # history is fine
    db.flush()
    db.add(Transcript(source_video_id=src.id, version=3, is_current=True))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_two_sources_can_each_have_a_current_transcript(db: Session) -> None:
    a, b = _source(db, external_id="a"), _source(db, external_id="b")
    db.add_all(
        [Transcript(source_video_id=a.id, version=1), Transcript(source_video_id=b.id, version=1)]
    )
    db.commit()


def test_transcript_defaults_and_new_columns(db: Session) -> None:
    src = _source(db)
    t = Transcript(
        source_video_id=src.id,
        version=1,
        raw_storage_key="transcripts/x/v1/raw.srt",
        raw_sha256="a" * 64,
        normalizer_version="1",
    )
    db.add(t)
    db.commit()
    assert (
        t.is_current is True
        and t.status is TranscriptStatus.PENDING
        and t.normalizer_version == "1"
    )


def test_search_vector_is_generated_and_matches_by_word(db: Session) -> None:
    src = _source(db)
    t = Transcript(source_video_id=src.id, version=1)
    db.add(t)
    db.flush()
    db.add_all(
        [
            TranscriptChunk(
                transcript_id=t.id, chunk_index=0, text="Ancient humans survived the ice age"
            ),
            TranscriptChunk(
                transcript_id=t.id, chunk_index=1, text="Fire changed everything for them"
            ),
        ]
    )
    db.commit()
    query = func.websearch_to_tsquery("simple", "survived ice")
    hits = db.scalars(
        select(TranscriptChunk).where(TranscriptChunk.search_vector.op("@@")(query))
    ).all()
    assert [h.chunk_index for h in hits] == [0]
    # unusual syntax must never raise
    for q in ['"', "a & | b", "((", "'", "-", "\\", "OR OR"]:
        db.execute(select(func.websearch_to_tsquery("simple", q))).all()


def test_search_vector_index_is_gin(db: Session) -> None:
    definition = db.execute(
        text(
            "SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_transcript_chunks_search_vector'"
        )
    ).scalar_one()
    assert "USING gin" in definition
