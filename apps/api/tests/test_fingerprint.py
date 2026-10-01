"""Content fingerprint: insensitive to format/markup/timing/case/punctuation, sensitive to words."""

import hashlib
from pathlib import Path

from app.ingestion.normalize import fingerprint, fingerprint_text
from app.ingestion.parsers import parse_json3, parse_srt, parse_txt, parse_vtt
from app.schemas.source import TranscriptSegment

FIX = Path(__file__).parent / "fixtures" / "transcripts"


def seg(start: float | None, end: float | None, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, end=end, text=text)


def test_srt_vtt_and_txt_of_the_same_words_share_a_fingerprint() -> None:
    srt = fingerprint(parse_srt((FIX / "simple.srt").read_bytes()))
    vtt = fingerprint(parse_vtt((FIX / "simple.vtt").read_bytes()))
    txt = fingerprint(parse_txt((FIX / "simple.txt").read_bytes()))
    assert srt == vtt == txt
    assert len(srt) == 64 and all(c in "0123456789abcdef" for c in srt)


def test_fingerprint_text_is_lowercase_alphanumeric_tokens() -> None:
    assert (
        fingerprint_text(parse_srt((FIX / "simple.srt").read_bytes()))
        == "welcome to the show today we talk about volcanoes they erupt without warning scientists watch them closely"
    )


def test_case_punctuation_markup_and_timing_do_not_matter() -> None:
    a = [seg(0, 2, "Hello, WORLD!"), seg(2, 4, "It's <i>fine</i>.")]
    b = [seg(10, 30, "hello world its fine")]
    assert (
        fingerprint_text(a) == "hello world it s fine" != fingerprint_text(b)
    )  # apostrophe splits a token
    assert fingerprint(a) == fingerprint([seg(0, 9, "hello    world"), seg(9, 12, "it's FINE")])


def test_different_words_give_a_different_fingerprint() -> None:
    assert fingerprint([seg(0, 2, "volcanoes erupt")]) != fingerprint(
        [seg(0, 2, "volcanoes sleep")]
    )
    assert fingerprint([seg(0, 2, "a b")]) != fingerprint([seg(0, 2, "b a")]), "word order matters"


def test_accepts_raw_or_already_normalized_segments() -> None:
    from app.ingestion.normalize import normalize_segments

    raw = parse_vtt((FIX / "rolling_captions.vtt").read_bytes())
    assert fingerprint(raw) == fingerprint(normalize_segments(raw))


def test_rolling_captions_do_not_change_the_fingerprint() -> None:
    rolling = parse_vtt((FIX / "rolling_captions.vtt").read_bytes())
    clean = [seg(0, 9, "so today we are going to talk about rolling captions and why they repeat")]
    assert fingerprint(rolling) == fingerprint(clean)


def test_json3_matches_equivalent_srt_text() -> None:
    j = fingerprint(parse_json3((FIX / "sample.json3").read_bytes()))
    assert j == fingerprint([seg(0, 5, "welcome to the show. Today we talk about volcanoes.")])


def test_unicode_is_nfkc_folded_and_cjk_emoji_handled() -> None:
    assert fingerprint([seg(0, 2, "ｆｕｌｌｗｉｄｔｈ")]) == fingerprint(
        [seg(0, 2, "fullwidth")]
    )  # NFKC
    assert fingerprint_text([seg(0, 2, "Café 日本語 🌋 test")]) == "café 日本語 test"
    assert fingerprint([seg(0, 2, "é")]) == fingerprint([seg(0, 2, "é")])


def test_empty_transcript_has_the_sha256_of_the_empty_string() -> None:
    assert fingerprint_text([]) == ""
    assert fingerprint([]) == hashlib.sha256(b"").hexdigest()
    assert fingerprint([seg(0, 2, "  <i></i> ")]) == fingerprint([])
