"""Deterministic, versioned transcript normalization and content fingerprinting.

Pure functions, no I/O. Output depends only on the input segments and `NORMALIZER_VERSION`; bump the
version whenever a rule changes so stored transcripts can be re-normalized as a new version.

Rules (see implementation-plan/02-source-library.md §5.4), applied per segment then across segments:
 1. NFC; strip control characters (and BOM / zero-width space); strip caption markup (`<c>`,
    `<c.colour>`, `<i>`, `<font …>`, `<00:00:01.000>`, `{\\an8}`); unescape HTML entities.
    `[Music]`-style annotations are KEPT (they are source content). Zero-width joiners are kept so
    emoji sequences survive. Applied to a fixpoint, so the result never changes if cleaned again.
 2. Collapse all whitespace (incl. newlines, NBSP) to single spaces; drop segments left empty.
 3. Timed segments only (untimed segments pass through untouched and are never merged):
    sort stably by start; set a missing end to start; enforce end ≥ start; collapse YouTube
    auto-caption rolling repeats (a segment whose text starts with the previous one's — or is
    contained at its start — keeps the longer text and the union of the times); merge segments
    shorter than 1.0 s into the previous one.
 4. Steps 1–3 repeat until the output stops changing, which makes `normalize_segments` idempotent.
"""

import hashlib
import html
import re
import unicodedata

from app.schemas.source import TranscriptSegment

# v2: inline caption tags are removed without leaving a space ("volcanoes</c>." -> "volcanoes.");
# <br>/<p> now act as whitespace. Bump whenever output changes so transcripts can be re-normalized.
NORMALIZER_VERSION = "2"
MIN_SEGMENT_SECONDS = 1.0

_CAPTION_TAG = re.compile(
    r"</?(?:c|b|i|u|v|ruby|rt|lang|font)(?:[.\s][^<>]*)?>"  # <c>, <c.colorE5E5E5>, <font color="…">
    r"|<\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3}>"  # inline timestamps <00:00:01.000>
    r"|\{\\an?\d{1,2}\}",  # SSA/ASS positioning {\an8}
    re.IGNORECASE,
)
_LINE_BREAK_TAG = re.compile(
    r"</?(?:br|p)\s*/?>", re.IGNORECASE
)  # separates words: becomes a space
_NON_TEXT_CHARS = frozenset({"\u200b", "\ufeff"})  # zero-width space, BOM (ZWJ/ZWNJ are kept)
_TOKEN = re.compile(r"[^\W_]+")


def _clean_text_once(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = _LINE_BREAK_TAG.sub(" ", text)
    text = _CAPTION_TAG.sub("", text)  # no space: "word</c>." must stay "word."
    text = html.unescape(text)
    kept: list[str] = []
    for ch in text:
        if ch in _NON_TEXT_CHARS:
            continue
        if ch in "\t\n\r":
            kept.append(" ")
        elif unicodedata.category(ch) != "Cc":  # other control characters are dropped
            kept.append(ch)
    return " ".join("".join(kept).split())  # also folds NBSP and other Unicode whitespace


def _clean_text(text: str) -> str:
    """Apply the per-segment cleanup until it no longer changes (guarantees idempotence)."""
    for _ in range(8):
        cleaned = _clean_text_once(text)
        if cleaned == text:
            return cleaned
        text = cleaned
    return text


def _is_timed(seg: TranscriptSegment) -> bool:
    return seg.start is not None


def _merge_pass(run: list[TranscriptSegment]) -> list[TranscriptSegment]:
    """Collapse rolling repeats, then fold sub-second segments into their predecessor (timed run)."""
    out: list[TranscriptSegment] = []
    for seg in run:
        assert seg.start is not None and seg.end is not None
        prev = out[-1] if out else None
        if prev is not None and prev.end is not None and prev.start is not None:
            if seg.text.startswith(prev.text):  # next repeats the previous and extends it
                out[-1] = TranscriptSegment(
                    start=prev.start,
                    end=max(prev.end, seg.end),
                    text=seg.text,
                    speaker=prev.speaker,
                )
                continue
            if prev.text.startswith(seg.text):  # next is a shorter echo of the previous
                out[-1] = prev.model_copy(update={"end": max(prev.end, seg.end)})
                continue
            if seg.end - seg.start < MIN_SEGMENT_SECONDS:
                out[-1] = TranscriptSegment(
                    start=prev.start,
                    end=max(prev.end, seg.end),
                    text=f"{prev.text} {seg.text}",
                    speaker=prev.speaker,
                )
                continue
        out.append(seg)
    return out


def _normalize_run(run: list[TranscriptSegment]) -> list[TranscriptSegment]:
    fixed: list[TranscriptSegment] = []
    for seg in run:
        assert seg.start is not None
        end = seg.start if seg.end is None else max(seg.end, seg.start)
        fixed.append(seg.model_copy(update={"end": end}))
    fixed.sort(key=lambda s: s.start or 0.0)  # stable
    return _merge_pass(fixed)


def _normalize_once(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    cleaned = [
        seg.model_copy(update={"text": text}) for seg in segments if (text := _clean_text(seg.text))
    ]
    result: list[TranscriptSegment] = []
    run: list[TranscriptSegment] = []
    for seg in cleaned:
        if _is_timed(seg):
            run.append(seg)
            continue
        result.extend(_normalize_run(run))
        run = []
        result.append(seg)  # untimed: pass through untouched
    result.extend(_normalize_run(run))
    return result


def normalize_segments(segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
    """Normalize per the module rules. Deterministic and idempotent."""
    current = segments
    for _ in range(10):
        nxt = _normalize_once(current)
        if nxt == current:
            return nxt
        current = nxt
    return current


def cleaned_text(segments: list[TranscriptSegment]) -> str:
    """Display/search text of (normalized) segments.

    Segments are joined with a single space, except between two *untimed* segments, which are joined
    with a blank line: each untimed segment is one paragraph of a plain-text upload (or one ≤1000-char
    piece of an oversized paragraph, which therefore also gets a paragraph break).
    """
    out: list[str] = []
    prev_untimed = False
    for seg in segments:
        untimed = not _is_timed(seg)
        if out:
            out.append("\n\n" if untimed and prev_untimed else " ")
        out.append(seg.text)
        prev_untimed = untimed
    return "".join(out).strip()


def fingerprint_text(segments: list[TranscriptSegment]) -> str:
    """Formatting- and timing-insensitive text: NFKC, lowercase, alphanumeric tokens, single spaces.

    Normalizes first (idempotent), so raw and already-normalized segments give the same result.
    """
    joined = " ".join(seg.text for seg in normalize_segments(segments))
    folded = unicodedata.normalize("NFKC", joined).lower()
    return " ".join(_TOKEN.findall(folded))


def fingerprint(segments: list[TranscriptSegment]) -> str:
    """sha256 (hex) of `fingerprint_text`. For an empty transcript this is sha256 of the empty string."""
    return hashlib.sha256(fingerprint_text(segments).encode("utf-8")).hexdigest()
