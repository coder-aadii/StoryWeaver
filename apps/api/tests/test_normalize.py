"""Normalizer: tag stripping, rolling-caption collapse, merging, ordering, idempotence, Unicode."""

import json
import unicodedata
from pathlib import Path

import pytest

from app.ingestion.normalize import (
    NORMALIZER_VERSION,
    cleaned_text,
    fingerprint,
    normalize_segments,
)
from app.ingestion.parsers import parse_srt, parse_txt, parse_vtt
from app.schemas.source import TranscriptSegment

FIX = Path(__file__).parent / "fixtures" / "transcripts"


def seg(start: float | None, end: float | None, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, end=end, text=text)


def dump(segs: list[TranscriptSegment]) -> list[dict[str, object]]:
    return [s.model_dump() for s in segs]


def test_version_constant() -> None:
    assert NORMALIZER_VERSION == "2"


def test_rolling_auto_captions_golden() -> None:
    out = normalize_segments(parse_vtt((FIX / "rolling_captions.vtt").read_bytes()))
    assert dump(out) == json.loads((FIX / "rolling_captions.expected.json").read_text())


def test_caption_markup_entities_and_annotations_golden() -> None:
    out = normalize_segments(parse_srt((FIX / "tags.srt").read_bytes()))
    assert dump(out) == json.loads((FIX / "tags.expected.json").read_text())


def test_music_style_annotations_are_kept() -> None:
    assert (
        normalize_segments([seg(0, 2, "[Music] hello [Applause]")])[0].text
        == "[Music] hello [Applause]"
    )


def test_comparison_text_is_not_mistaken_for_markup() -> None:
    assert (
        normalize_segments([seg(0, 2, "if x < y and y > z then 5 < 6")])[0].text
        == "if x < y and y > z then 5 < 6"
    )


def test_whitespace_control_chars_and_nbsp_are_collapsed() -> None:
    out = normalize_segments([seg(0, 2, "  a\tb\n\nc\xa0d\x07e\u200bf\ufeff ")])
    # tab/newline/NBSP become single spaces; other control chars, ZWSP and BOM are removed.
    assert out[0].text == "a b c def"


def test_empty_segments_are_dropped() -> None:
    assert normalize_segments([seg(0, 1, "  "), seg(1, 3, "<i></i>"), seg(3, 5, "x")]) == [
        seg(3.0, 5.0, "x")
    ]


def test_nfc_normalization() -> None:
    nfd = unicodedata.normalize("NFD", "café")
    assert nfd != "café"
    assert normalize_segments([seg(0, 2, nfd)])[0].text == "café"


def test_unicode_round_trip_cjk_and_emoji_sequences() -> None:
    text = "日本語のテスト 🌋 👨‍👩‍👧 ❤️ naïve"
    assert normalize_segments([seg(0, 2, text)])[0].text == text


def test_identical_consecutive_segments_collapse() -> None:
    assert normalize_segments([seg(0, 2, "hello there"), seg(2, 4, "hello there")]) == [
        seg(0.0, 4.0, "hello there")
    ]


def test_shorter_echo_of_previous_is_absorbed() -> None:
    out = normalize_segments([seg(0, 3, "so today we go"), seg(3, 4, "so today")])
    assert out == [seg(0.0, 4.0, "so today we go")]


def test_chain_of_rolling_repeats_collapses_into_one() -> None:
    chain = [seg(i, i + 1.5, " ".join(["w"] * (i + 1))) for i in range(5)]
    out = normalize_segments(chain)
    assert len(out) == 1 and out[0].text == "w w w w w" and (out[0].start, out[0].end) == (0.0, 5.5)


def test_sub_second_segments_merge_into_previous() -> None:
    out = normalize_segments(
        [seg(0, 3, "first part"), seg(3, 3.4, "tiny"), seg(3.4, 6, "second part")]
    )
    assert [(s.start, s.end, s.text) for s in out] == [
        (0.0, 3.4, "first part tiny"),
        (3.4, 6.0, "second part"),
    ]


def test_first_segment_is_kept_even_if_short() -> None:
    assert normalize_segments([seg(0, 0.2, "hi"), seg(0.2, 3, "there")])[0].text == "hi"


def test_exactly_one_second_is_not_merged() -> None:
    assert len(normalize_segments([seg(0, 3, "aaa"), seg(3, 4, "bbb")])) == 2


def test_out_of_order_segments_are_sorted_stably() -> None:
    out = normalize_segments([seg(5, 8, "late"), seg(0, 3, "early"), seg(0, 3, "tied")])
    assert [s.text for s in out] == ["early", "tied", "late"]


def test_missing_end_is_set_to_start_and_end_never_before_start() -> None:
    out = normalize_segments([TranscriptSegment(start=2.0, text="x"), seg(5, 8, "y")])
    assert (out[0].start, out[0].end) == (2.0, 2.0)
    bad = TranscriptSegment.model_construct(
        start=4.0, end=1.0, text="z", speaker=None
    )  # bypass validation
    assert normalize_segments([bad])[0].end == 4.0


def test_untimed_segments_pass_through_unmerged_and_in_order() -> None:
    segs = [seg(None, None, "para one"), seg(None, None, "para one and more"), seg(None, None, "x")]
    assert [s.text for s in normalize_segments(segs)] == ["para one", "para one and more", "x"]
    assert all(s.start is None for s in normalize_segments(segs))


def test_untimed_segments_split_timed_runs() -> None:
    segs = [seg(0, 2, "a b"), seg(2, 4, "a b c"), seg(None, None, "note"), seg(4, 6, "a b c d")]
    out = normalize_segments(segs)
    assert [s.text for s in out] == ["a b c", "note", "a b c d"], (
        "rolling repeats never merge across untimed text"
    )


def test_speaker_of_first_segment_is_preserved_on_merge() -> None:
    first = TranscriptSegment(start=0, end=2, text="a b", speaker="Ann")
    out = normalize_segments([first, seg(2, 4, "a b c")])
    assert out[0].speaker == "Ann" and out[0].text == "a b c"


def test_empty_input() -> None:
    assert normalize_segments([]) == []


# ---- determinism and idempotence --------------------------------------------------------------------
@pytest.mark.parametrize(
    "build",
    [
        lambda: parse_vtt((FIX / "rolling_captions.vtt").read_bytes()),
        lambda: parse_srt((FIX / "tags.srt").read_bytes()),
        lambda: parse_srt((FIX / "simple.srt").read_bytes()),
        lambda: parse_txt((FIX / "simple.txt").read_bytes()),
        lambda: [seg(0, 3, "a b"), seg(3, 3.2, "c"), seg(3.2, 6, "a b c d"), seg(6, 6.1, "e")],
        lambda: [
            seg(0, 1, "&amp;lt;c&amp;gt;x&amp;lt;/c&amp;gt;"),
            seg(1, 3, "&lt;b&gt;bold&lt;/b&gt;"),
        ],
    ],
)
def test_normalize_is_idempotent_and_deterministic(build) -> None:  # type: ignore[no-untyped-def]
    once = normalize_segments(build())
    assert normalize_segments(once) == once
    assert dump(normalize_segments(build())) == dump(once)


def test_does_not_mutate_its_input() -> None:
    src = [seg(0, 3, "<i>a</i>"), seg(3, 3.1, "b")]
    snapshot = dump(src)
    normalize_segments(src)
    assert dump(src) == snapshot


# ---- cleaned_text -------------------------------------------------------------------------------------
def test_cleaned_text_timed_segments_join_with_single_spaces() -> None:
    assert cleaned_text([seg(0, 2, "one"), seg(2, 4, "two")]) == "one two"


def test_cleaned_text_untimed_paragraphs_get_blank_lines_but_mixed_neighbours_do_not() -> None:
    untimed = [seg(None, None, "p1"), seg(None, None, "p2")]
    assert cleaned_text(untimed) == "p1\n\np2"
    assert cleaned_text([seg(0, 2, "t"), seg(None, None, "u")]) == "t u"
    assert cleaned_text([]) == ""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("we saw <c>volcanoes</c>.", "we saw volcanoes."),
        ("He said <b>hello</b>, then left.", "He said hello, then left."),
        ("<i>Wait</i>... what?", "Wait... what?"),
        ('<font color="#ff0000">Red</font>alert', "Redalert"),
        ("line one<br>line two", "line one line two"),
        ("line one<br/>line two", "line one line two"),
        ("Welcome<00:00:00.500><c> to</c><00:00:00.900><c> the</c> show", "Welcome to the show"),
    ],
)
def test_inline_tags_vanish_without_leaving_a_space(raw: str, expected: str) -> None:
    """Regression (KI-27): stripping a tag must not detach punctuation from the word before it."""
    out = normalize_segments([TranscriptSegment(start=0.0, end=3.0, text=raw)])
    assert [s.text for s in out] == [expected]
    assert normalize_segments(out) == out  # still idempotent


def test_tag_stripping_does_not_change_the_fingerprint() -> None:
    tagged = [TranscriptSegment(start=0.0, end=3.0, text="we saw <c>volcanoes</c>.")]
    plain = [TranscriptSegment(start=0.0, end=3.0, text="we saw volcanoes.")]
    assert fingerprint(tagged) == fingerprint(plain)
