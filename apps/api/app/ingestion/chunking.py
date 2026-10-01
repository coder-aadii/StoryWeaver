from app.schemas.source import TranscriptSegment


def chunk_segments(
    segments: list[TranscriptSegment], max_chars: int = 1200
) -> list[tuple[str, float | None, float | None]]:
    """Group consecutive segments into chunks of ~max_chars, keeping start/end times.

    Untimed segments (plain text) yield chunks whose times are None; a chunk mixing timed and untimed
    segments uses the first non-None start and the last non-None end.
    """
    chunks: list[tuple[str, float | None, float | None]] = []
    buf: list[str] = []
    start: float | None = None
    end: float | None = None
    for seg in segments:
        if buf and sum(len(t) + 1 for t in buf) + len(seg.text) > max_chars:
            chunks.append((" ".join(buf), start, end))
            buf, start, end = [], None, None
        buf.append(seg.text)
        if start is None:
            start = seg.start
        if seg.end is not None:
            end = seg.end
    if buf:
        chunks.append((" ".join(buf), start, end))
    return chunks
