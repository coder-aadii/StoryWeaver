"""chunk_segments with and without timestamps (P1: plain-text uploads are untimed)."""

from app.ingestion.chunking import chunk_segments
from app.schemas.source import TranscriptSegment


def seg(start: float | None, end: float | None, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, end=end, text=text)


def test_all_untimed_chunks_have_none_times() -> None:
    chunks = chunk_segments(
        [seg(None, None, "a" * 700), seg(None, None, "b" * 700)], max_chars=1200
    )
    assert len(chunks) == 2
    assert all(c[1] is None and c[2] is None for c in chunks)


def test_timed_chunks_keep_first_start_and_last_end() -> None:
    chunks = chunk_segments([seg(1.0, 2.0, "x"), seg(2.0, 3.5, "y"), seg(3.5, 9.0, "z")])
    assert chunks == [("x y z", 1.0, 9.0)]


def test_mixed_chunk_uses_first_non_none_start_and_last_non_none_end() -> None:
    chunks = chunk_segments([seg(None, None, "x"), seg(2.0, 3.0, "y"), seg(None, None, "z")])
    assert chunks == [("x y z", 2.0, 3.0)]


def test_split_behaviour_at_max_chars_is_unchanged() -> None:
    segs = [seg(float(i), float(i + 1), "w" * 500) for i in range(5)]
    chunks = chunk_segments(segs, max_chars=1200)
    assert [len(c[0]) for c in chunks] == [1001, 1001, 500]  # 2 + 2 + 1 segments, joined by spaces
    assert chunks[0][1] == 0.0 and chunks[0][2] == 2.0
    assert chunks[1][1] == 2.0 and chunks[2][2] == 5.0


def test_oversized_single_segment_is_its_own_chunk() -> None:
    chunks = chunk_segments([seg(0, 1, "a" * 3000), seg(1, 2, "b")], max_chars=1200)
    assert [c[0][:1] for c in chunks] == ["a", "b"]


def test_empty_input() -> None:
    assert chunk_segments([]) == []
