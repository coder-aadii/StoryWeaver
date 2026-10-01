"""Transcript parsers: golden fixtures, malformed input with line numbers, limits, encodings."""

from pathlib import Path

import pytest

from app.core.errors import FileTooLargeError, TranscriptParseError
from app.ingestion.parsers import (
    ALLOWED_EXTENSIONS,
    parse_json3,
    parse_srt,
    parse_transcript,
    parse_txt,
    parse_vtt,
)
from app.schemas.source import TranscriptSegment

FIX = Path(__file__).parent / "fixtures" / "transcripts"
SIMPLE_TEXTS = [
    "Welcome to the show.",
    "Today we talk about volcanoes.",
    "They erupt without warning.",
    "Scientists watch them closely.",
]


def seg(start: float | None, end: float | None, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, end=end, text=text)


def test_srt_golden() -> None:
    segs = parse_srt((FIX / "simple.srt").read_bytes())
    assert [s.text for s in segs] == SIMPLE_TEXTS
    assert [(s.start, s.end) for s in segs] == [(0, 3), (3, 7.5), (7.5, 11), (11, 15.25)]


def test_vtt_golden_handles_header_note_style_ids_settings_and_multiline_cues() -> None:
    segs = parse_vtt((FIX / "simple.vtt").read_bytes())
    # Markup is kept by the parser (the normalizer strips it); multi-line cues are joined with a space.
    assert [s.text for s in segs] == [
        "Welcome to the show.",
        "Today we talk about <c.highlight>volcanoes</c>.",
        "They erupt without warning.",
        "Scientists <b>watch</b> them closely.",
    ]
    assert (segs[0].start, segs[0].end) == (0.0, 3.0)  # "00:00.000" has no hours
    assert (segs[3].start, segs[3].end) == (11.0, 15.25)


def test_json3_golden_skips_window_events_and_blank_events() -> None:
    segs = parse_json3((FIX / "sample.json3").read_bytes())
    assert [(s.start, s.end, s.text) for s in segs] == [
        (0.0, 2.5, "Welcome to the show."),
        (2.5, 7.0, "Today we talk about volcanoes."),
    ]


def test_txt_paragraphs_are_untimed_segments() -> None:
    segs = parse_txt((FIX / "simple.txt").read_bytes())
    assert [s.text for s in segs] == [
        "Welcome to the show. Today we talk about volcanoes.",
        "They erupt without warning. Scientists watch them closely.",
    ]
    assert all(s.start is None and s.end is None for s in segs), "times must never be invented"


def test_txt_long_paragraph_is_split_at_sentences_within_limit() -> None:
    para = " ".join(f"Sentence number {i} is here." for i in range(200))
    segs = parse_txt(para)
    assert len(segs) > 1 and all(len(s.text) <= 1000 for s in segs)
    assert " ".join(s.text for s in segs) == para


def test_txt_unspaced_text_is_hard_split() -> None:
    segs = parse_txt("日" * 2500)
    assert [len(s.text) for s in segs] == [1000, 1000, 500]


def test_txt_cjk_sentences_split_without_whitespace() -> None:
    text = ("これは文章です。" * 200).strip()
    segs = parse_txt(text)
    assert len(segs) > 1 and all(len(s.text) <= 1000 for s in segs)
    assert "".join(s.text for s in segs) == text


# ---- tolerance ----------------------------------------------------------------------------------
def test_crlf_and_bom_are_tolerated() -> None:
    raw = (FIX / "simple.srt").read_bytes().replace(b"\n", b"\r\n")
    assert [s.text for s in parse_srt(b"\xef\xbb\xbf" + raw)] == SIMPLE_TEXTS


def test_srt_index_lines_are_optional_and_dot_millis_accepted() -> None:
    segs = parse_srt("00:00:01.500 --> 00:00:02.000\nhi\n")
    assert [(s.start, s.end, s.text) for s in segs] == [(1.5, 2.0, "hi")]


def test_srt_missing_blank_line_between_cues_does_not_leak_the_index() -> None:
    srt = "1\n00:00:00,000 --> 00:00:01,000\nfirst\n2\n00:00:01,000 --> 00:00:02,000\nsecond\n"
    assert [s.text for s in parse_srt(srt)] == ["first", "second"]


def test_short_millisecond_digits_are_scaled() -> None:
    assert parse_vtt("WEBVTT\n\n00:01.5 --> 00:02.25\nx\n")[0].start == 1.5


# ---- malformed input -----------------------------------------------------------------------------
def test_malformed_timestamp_reports_the_line() -> None:
    with pytest.raises(TranscriptParseError) as exc:
        parse_srt((FIX / "malformed.srt").read_bytes())
    assert exc.value.line == 6 and "malformed timestamp" in str(exc.value)


def test_end_before_start_is_rejected_with_line() -> None:
    with pytest.raises(TranscriptParseError) as exc:
        parse_srt((FIX / "backwards.srt").read_bytes())
    assert exc.value.line == 2 and "before start" in str(exc.value)


def test_invalid_minutes_are_rejected() -> None:
    with pytest.raises(TranscriptParseError, match="minutes and seconds"):
        parse_srt("1\n00:75:00,000 --> 00:76:00,000\nx\n")


def test_stray_text_before_a_cue_is_rejected_with_line() -> None:
    with pytest.raises(TranscriptParseError) as exc:
        parse_srt("hello there\n\n1\n00:00:00,000 --> 00:00:01,000\nx\n")
    assert exc.value.line == 1


def test_vtt_requires_header() -> None:
    with pytest.raises(TranscriptParseError, match="WEBVTT"):
        parse_vtt("00:00:00.000 --> 00:00:01.000\nx\n")


def test_arrow_inside_cue_text_is_rejected() -> None:
    with pytest.raises(TranscriptParseError) as exc:
        parse_vtt("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello\nx --> y\n")
    assert exc.value.line == 5


def test_json3_errors() -> None:
    with pytest.raises(TranscriptParseError, match="invalid JSON"):
        parse_json3("{not json")
    with pytest.raises(TranscriptParseError, match="events"):
        parse_json3('{"foo": 1}')
    with pytest.raises(TranscriptParseError, match="timing"):
        parse_json3('{"events": [{"tStartMs": -5, "dDurationMs": 1, "segs": [{"utf8": "x"}]}]}')


def test_cue_without_text_is_skipped() -> None:
    assert (
        parse_srt("1\n00:00:00,000 --> 00:00:01,000\n\n2\n00:00:01,000 --> 00:00:02,000\nx\n")[
            0
        ].text
        == "x"
    )


# ---- dispatcher: limits and encodings -------------------------------------------------------------
def test_dispatcher_picks_parser_by_extension_case_and_dot_insensitively() -> None:
    srt = (FIX / "simple.srt").read_bytes()
    assert [s.text for s in parse_transcript(".SRT", srt, 10_000)] == SIMPLE_TEXTS
    assert len(parse_transcript("txt", b"hello world", 100)) == 1


@pytest.mark.parametrize("ext", ["exe", "pdf", "", "srt.exe", "../x"])
def test_unsupported_extension_is_rejected(ext: str) -> None:
    with pytest.raises(TranscriptParseError, match="unsupported"):
        parse_transcript(ext, b"x", 100)


def test_allow_list_is_exactly_the_documented_formats() -> None:
    assert {"txt", "srt", "vtt", "json3"} == ALLOWED_EXTENSIONS


def test_oversize_input_raises_file_too_large_before_parsing() -> None:
    with pytest.raises(FileTooLargeError):
        parse_transcript("txt", b"x" * 101, 100)
    parse_transcript("txt", b"x" * 100, 100)  # exactly at the limit is fine


def test_non_utf8_is_rejected() -> None:
    with pytest.raises(TranscriptParseError, match="UTF-8"):
        parse_transcript("txt", "café".encode("latin-1"), 100)


@pytest.mark.parametrize("data", [b"", b"   \n\t\n"])
def test_empty_file_is_an_error(data: bytes) -> None:
    with pytest.raises(TranscriptParseError, match="empty transcript"):
        parse_transcript("txt", data, 100)


def test_file_with_no_cues_is_an_error() -> None:
    with pytest.raises(TranscriptParseError, match="no transcript text"):
        parse_transcript("vtt", b"WEBVTT\n\nNOTE only a note\n", 1000)


def test_segment_count_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.ingestion.parsers as parsers

    monkeypatch.setattr(parsers, "MAX_SEGMENTS", 3)
    srt = "".join(f"{i}\n00:00:0{i},000 --> 00:00:0{i},500\nx{i}\n\n" for i in range(1, 6))
    with pytest.raises(TranscriptParseError, match="too many segments"):
        parse_srt(srt)


def test_pathologically_long_cue_line_is_rejected() -> None:
    with pytest.raises(TranscriptParseError, match="too long"):
        parse_srt("1\n00:00:00,000 --> 00:00:01,000\n" + "a" * 25_000 + "\n")


def test_unicode_survives_parsing() -> None:
    segs = parse_srt((FIX / "unicode.srt").read_bytes())
    assert segs[0].text == "Café déjà vu 日本語のテスト 🌋 erupts"
