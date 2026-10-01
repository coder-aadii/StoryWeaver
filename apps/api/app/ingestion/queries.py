"""Read side of the Source Library: list/detail views with derived fields, keyword search, usage.

`searchable` and `usage_count` are always derived from the tables, never stored as flags.
"""

import html
import uuid

from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session

from app.models import (
    Channel,
    Project,
    ProjectSource,
    SourceVideo,
    Transcript,
    TranscriptChunk,
    WorkflowRun,
)
from app.models.enums import RunStatus, SourceStatus, TranscriptStatus
from app.schemas.source import TranscriptSegment
from app.schemas.source_api import (
    ChunkRead,
    Page,
    ProjectSourceLink,
    RunRead,
    SearchHit,
    SourceDetail,
    SourceListItem,
    SourceUsage,
    TranscriptContent,
    TranscriptSummary,
)
from app.workflows.runs import RunService

# ts_headline markers. Control characters cannot occur in stored text (the normalizer strips them), so
# they are unambiguous; everything else in the snippet is HTML-escaped before the markers become <mark>.
_START, _STOP = "\x01", "\x02"
_HEADLINE_OPTIONS = (
    f"StartSel={_START}, StopSel={_STOP}, MaxFragments=1, MaxWords=35, MinWords=15, ShortWord=2"
)


def run_read(run: WorkflowRun) -> RunRead:
    return RunRead.model_validate(run)


def transcript_summary(t: Transcript) -> TranscriptSummary:
    segments = t.segments or []
    return TranscriptSummary(
        id=t.id,
        version=t.version,
        status=t.status,
        origin=t.origin,
        language=t.language,
        segment_count=len(segments),
        char_count=len(t.text or ""),
        timed=bool(segments) and segments[0].get("start") is not None,
        normalizer_version=t.normalizer_version,
        error=t.error,
        created_at=t.created_at,
    )


def list_items(db: Session, sources: list[SourceVideo]) -> list[SourceListItem]:
    """Build list items for a batch of sources with a fixed number of queries."""
    if not sources:
        return []
    ids = [s.id for s in sources]
    current = {
        t.source_video_id: t
        for t in db.scalars(
            select(Transcript).where(Transcript.source_video_id.in_(ids), Transcript.is_current)
        )
    }
    chunk_counts: dict[uuid.UUID, int] = {
        sid: n
        for sid, n in db.execute(
            select(Transcript.source_video_id, func.count(TranscriptChunk.id))
            .join(TranscriptChunk, TranscriptChunk.transcript_id == Transcript.id)
            .where(Transcript.source_video_id.in_(ids), Transcript.is_current)
            .group_by(Transcript.source_video_id)
        )
    }
    usage: dict[uuid.UUID, int] = {
        sid: n
        for sid, n in db.execute(
            select(ProjectSource.source_video_id, func.count())
            .where(ProjectSource.source_video_id.in_(ids))
            .group_by(ProjectSource.source_video_id)
        )
    }
    channel_ids = {s.channel_id for s in sources if s.channel_id}
    channels = (
        {c.id: c.title for c in db.scalars(select(Channel).where(Channel.id.in_(channel_ids)))}
        if channel_ids
        else {}
    )
    items: list[SourceListItem] = []
    for s in sources:
        t = current.get(s.id)
        n_chunks = chunk_counts.get(s.id, 0)
        items.append(
            SourceListItem(
                id=s.id,
                title=s.title,
                platform=s.platform,
                kind="transcript" if s.kind == "transcript" else "youtube",
                url=s.url,
                thumbnail_url=s.thumbnail_url,
                duration_seconds=s.duration_seconds,
                language=s.language,
                status=s.status,
                error=s.error,
                channel_title=channels.get(s.channel_id) if s.channel_id else None,
                transcript_status=t.status if t else None,
                transcript_error=t.error if t else None,
                chunk_count=n_chunks,
                searchable=bool(t and t.status is TranscriptStatus.READY and n_chunks >= 1),
                usage_count=usage.get(s.id, 0),
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
        )
    return items


def list_item(db: Session, source: SourceVideo) -> SourceListItem:
    return list_items(db, [source])[0]


def detail(db: Session, source: SourceVideo) -> SourceDetail:
    base = list_item(db, source)
    t = db.scalars(
        select(Transcript).where(Transcript.source_video_id == source.id, Transcript.is_current)
    ).first()
    runs = RunService(db)
    active = runs.active_for("source.add", source.id) or runs.active_for(
        "source.fetch_transcript", source.id
    )
    return SourceDetail(
        **base.model_dump(),
        description=source.description,
        published_at=source.published_at,
        fingerprint=source.fingerprint,
        transcript=transcript_summary(t) if t else None,
        active_run=run_read(active) if active else None,
    )


def query_sources(
    db: Session,
    *,
    status: SourceStatus | None,
    kind: str | None,
    used: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[SourceVideo], int]:
    stmt = select(SourceVideo)
    if status is not None:
        stmt = stmt.where(SourceVideo.status == status)
    if kind is not None:
        stmt = stmt.where(SourceVideo.kind == kind)
    if used is not None:
        has_link = exists().where(ProjectSource.source_video_id == SourceVideo.id)
        stmt = stmt.where(has_link if used else ~has_link)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(SourceVideo.created_at.desc(), SourceVideo.id).limit(limit).offset(offset)
    ).all()
    return list(rows), total


def current_transcript_of(db: Session, source_id: uuid.UUID) -> Transcript | None:
    return db.scalars(
        select(Transcript).where(Transcript.source_video_id == source_id, Transcript.is_current)
    ).first()


def transcript_content(t: Transcript, *, limit: int, offset: int) -> TranscriptContent:
    segments = t.segments or []
    page = [TranscriptSegment.model_validate(s) for s in segments[offset : offset + limit]]
    return TranscriptContent(
        transcript=transcript_summary(t),
        text=t.text or "",
        segments=Page[TranscriptSegment](
            items=page, total=len(segments), limit=limit, offset=offset
        ),
    )


def chunks_page(db: Session, t: Transcript, *, limit: int, offset: int) -> Page[ChunkRead]:
    total = (
        db.scalar(
            select(func.count())
            .select_from(TranscriptChunk)
            .where(TranscriptChunk.transcript_id == t.id)
        )
        or 0
    )
    rows = db.scalars(
        select(TranscriptChunk)
        .where(TranscriptChunk.transcript_id == t.id)
        .order_by(TranscriptChunk.chunk_index)
        .limit(limit)
        .offset(offset)
    ).all()
    items = [
        ChunkRead(
            id=c.id,
            chunk_index=c.chunk_index,
            text=c.text,
            start_seconds=c.start_seconds,
            end_seconds=c.end_seconds,
        )
        for c in rows
    ]
    return Page[ChunkRead](items=items, total=total, limit=limit, offset=offset)


def safe_snippet(raw: str) -> str:
    """HTML-escape everything, then turn the unambiguous ts_headline markers into <mark> tags."""
    if raw.count(_START) != raw.count(_STOP):  # defensive: never emit unbalanced markup
        raw = raw.replace(_START, "").replace(_STOP, "")
    return html.escape(raw, quote=True).replace(_START, "<mark>").replace(_STOP, "</mark>")


def search(
    db: Session,
    q: str,
    *,
    exclude_used: bool,
    limit: int,
    offset: int,
    source_id: uuid.UUID | None = None,
) -> tuple[list[SearchHit], int]:
    """Keyword search over current, ready transcripts. `websearch_to_tsquery` never raises on odd syntax."""
    query = func.websearch_to_tsquery("simple", q)
    match = and_(
        Transcript.is_current,
        Transcript.status == TranscriptStatus.READY,
        TranscriptChunk.search_vector.op("@@")(query),
    )
    base = (
        select(TranscriptChunk, SourceVideo)
        .join(Transcript, TranscriptChunk.transcript_id == Transcript.id)
        .join(SourceVideo, Transcript.source_video_id == SourceVideo.id)
        .where(match)
    )
    if source_id is not None:
        base = base.where(SourceVideo.id == source_id)
    if exclude_used:
        base = base.where(~exists().where(ProjectSource.source_video_id == SourceVideo.id))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rank = func.ts_rank(TranscriptChunk.search_vector, query).label("rank")
    headline = func.ts_headline("simple", TranscriptChunk.text, query, _HEADLINE_OPTIONS).label(
        "headline"
    )
    rows = db.execute(
        base.add_columns(rank, headline)
        .order_by(rank.desc(), SourceVideo.created_at.desc(), TranscriptChunk.chunk_index)
        .limit(limit)
        .offset(offset)
    ).all()
    sources = {r[1].id: r[1] for r in rows}
    items = {i.id: i for i in list_items(db, list(sources.values()))}
    hits = [
        SearchHit(
            source=items[src.id],
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            snippet=safe_snippet(snip),
            start_seconds=chunk.start_seconds,
            end_seconds=chunk.end_seconds,
            rank=float(rk),
        )
        for chunk, src, rk, snip in rows
    ]
    return hits, total


def usage_of(db: Session, source_id: uuid.UUID) -> list[SourceUsage]:
    rows = db.execute(
        select(Project.id, Project.title, ProjectSource.role, ProjectSource.created_at)
        .join(ProjectSource, ProjectSource.project_id == Project.id)
        .where(ProjectSource.source_video_id == source_id)
        .order_by(ProjectSource.created_at.desc())
    ).all()
    return [SourceUsage(project_id=p, project_title=t, role=r, linked_at=c) for p, t, r, c in rows]


def project_sources(db: Session, project_id: uuid.UUID) -> list[ProjectSourceLink]:
    links = db.execute(
        select(ProjectSource, SourceVideo)
        .join(SourceVideo, ProjectSource.source_video_id == SourceVideo.id)
        .where(ProjectSource.project_id == project_id)
        .order_by(ProjectSource.created_at.desc())
    ).all()
    items = {i.id: i for i in list_items(db, [s for _, s in links])}
    return [
        ProjectSourceLink(source=items[s.id], role=link.role, linked_at=link.created_at)
        for link, s in links
    ]


def active_run_status() -> tuple[RunStatus, ...]:
    return (RunStatus.QUEUED, RunStatus.RUNNING)
