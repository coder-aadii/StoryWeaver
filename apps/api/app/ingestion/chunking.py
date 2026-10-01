from app.schemas.source import TranscriptSegment


def chunk_segments(
    segments: list[TranscriptSegment], max_chars: int = 1200
) -> list[tuple[str, float, float]]:
    """Group consecutive segments into chunks of ~max_chars, keeping start/end times."""
    chunks: list[tuple[str, float, float]] = []
    buf: list[str] = []
    start = end = 0.0
    for seg in segments:
        if buf and sum(len(t) + 1 for t in buf) + len(seg.text) > max_chars:
            chunks.append((" ".join(buf), start, end))
            buf = []
        if not buf:
            start = seg.start
        buf.append(seg.text)
        end = seg.end
    if buf:
        chunks.append((" ".join(buf), start, end))
    return chunks
