"""Transcript file parsers: SRT, WebVTT, YouTube json3 and plain text → `TranscriptSegment` lists.

Pure functions, no I/O. Parsers keep cue text as found (inline caption markup is stripped later by
`normalize.normalize_segments`); they only join cue lines with spaces. Plain text is untimed: segment
times are `None`, never invented. Errors are `TranscriptParseError` carrying the 1-based input line
where known; oversize input raises `FileTooLargeError`.

Decisions (documented because callers rely on them):
- An empty / whitespace-only file is an error ("empty transcript"), as is a file that parses to zero
  segments ("no transcript text found") — the service reports both as an unusable upload.
- SRT index lines are optional; a digit-only line directly before a timestamp line is treated as the
  index of the next cue even when the blank separator line is missing.
- Timestamps accept `,` or `.` before the milliseconds, optional hours, 1–3 millisecond digits.
"""

import json
import re
from typing import Any

from app.core.errors import FileTooLargeError, TranscriptParseError
from app.schemas.source import TranscriptSegment

ALLOWED_EXTENSIONS = frozenset({"txt", "srt", "vtt", "json3"})
MAX_SEGMENTS = 200_000
MAX_CUE_LINE_CHARS = 20_000  # SRT/VTT cue lines; plain text may legitimately be one long line
TXT_MAX_SEGMENT_CHARS = 1000

_TS = r"(?:(\d{1,3}):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?"
_ARROW = re.compile(rf"^\s*{_TS}\s*-->\s*{_TS}(?:\s+.*)?$")
_VTT_SKIP_BLOCK = re.compile(r"^(NOTE|STYLE|REGION)(\s|$)")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+|(?<=[。！？])")
_PARAGRAPH_SPLIT = re.compile(r"\n[ \t]*\n")


def decode_text(data: bytes | str) -> str:
    """UTF-8 (BOM tolerated) → str with `\\n` newlines. Raises TranscriptParseError if not UTF-8."""
    if isinstance(data, bytes):
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise TranscriptParseError("not valid UTF-8") from exc
    else:
        text = data.removeprefix("﻿")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _seconds(h: str | None, m: str, s: str, ms: str | None, line: int) -> float:
    minutes, seconds = int(m), int(s)
    if minutes > 59 or seconds > 59:
        raise TranscriptParseError(
            "invalid timestamp (minutes and seconds must be < 60)", line=line
        )
    millis = int((ms or "0").ljust(3, "0"))
    return int(h or 0) * 3600 + minutes * 60 + seconds + millis / 1000


def _parse_arrow(text: str, line: int) -> tuple[float, float]:
    m = _ARROW.match(text)
    if not m:
        raise TranscriptParseError("malformed timestamp line", line=line)
    g = m.groups()
    start = _seconds(g[0], g[1], g[2], g[3], line)
    end = _seconds(g[4], g[5], g[6], g[7], line)
    if end < start:
        raise TranscriptParseError("end time is before start time", line=line)
    return start, end


def _check_count(count: int) -> None:
    if count > MAX_SEGMENTS:
        raise TranscriptParseError(f"too many segments (limit {MAX_SEGMENTS})")


def _parse_cues(text: str, *, vtt: bool) -> list[TranscriptSegment]:
    lines = text.split("\n")
    n = len(lines)
    i = 0
    if vtt:
        while i < n and not lines[i].strip():
            i += 1
        if i >= n or not lines[i].lstrip().startswith("WEBVTT"):
            raise TranscriptParseError("missing WEBVTT header", line=i + 1 if i < n else 1)
        i += 1
        # Header metadata runs to the first blank line (or straight into a cue).
        while i < n and lines[i].strip() and "-->" not in lines[i]:
            i += 1

    segments: list[TranscriptSegment] = []
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if vtt and _VTT_SKIP_BLOCK.match(stripped):
            while i < n and lines[i].strip():
                i += 1
            continue
        if "-->" in line:
            arrow = i
        elif i + 1 < n and "-->" in lines[i + 1]:
            arrow = i + 1  # this line is the cue index (SRT) / identifier (VTT)
        else:
            raise TranscriptParseError("expected a cue timestamp line", line=i + 1)
        start, end = _parse_arrow(lines[arrow], arrow + 1)

        j = arrow + 1
        parts: list[str] = []
        while j < n and lines[j].strip():
            cue_line = lines[j]
            if not vtt and cue_line.strip().isdigit() and j + 1 < n and "-->" in lines[j + 1]:
                break  # missing blank line: this digit line is the next cue's index
            if "-->" in cue_line:
                raise TranscriptParseError("unexpected '-->' inside cue text", line=j + 1)
            if len(cue_line) > MAX_CUE_LINE_CHARS:
                raise TranscriptParseError("cue line too long", line=j + 1)
            parts.append(cue_line.strip())
            j += 1
        cue_text = " ".join(parts).strip()
        if cue_text:
            segments.append(TranscriptSegment(start=start, end=end, text=cue_text))
            _check_count(len(segments))
        i = j
    return segments


def parse_srt(data: bytes | str) -> list[TranscriptSegment]:
    return _parse_cues(decode_text(data), vtt=False)


def parse_vtt(data: bytes | str) -> list[TranscriptSegment]:
    return _parse_cues(decode_text(data), vtt=True)


def parse_json3(data: bytes | str) -> list[TranscriptSegment]:
    """YouTube json3 captions: `events[].tStartMs / dDurationMs / segs[].utf8`."""
    text = decode_text(data)
    try:
        doc: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TranscriptParseError(f"invalid JSON ({exc.msg})", line=exc.lineno) from exc
    events = doc.get("events") if isinstance(doc, dict) else None  # pyright: ignore[reportUnknownMemberType]
    if not isinstance(events, list):
        raise TranscriptParseError("json3 document has no 'events' list")
    segments: list[TranscriptSegment] = []
    for index, event in enumerate(events):  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
        if not isinstance(event, dict) or not isinstance(event.get("segs"), list):  # pyright: ignore[reportUnknownMemberType]
            continue  # window/position events carry no text
        start_ms = event.get("tStartMs", 0)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        dur_ms = event.get("dDurationMs", 0)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        if (
            not isinstance(start_ms, int | float)
            or not isinstance(dur_ms, int | float)
            or isinstance(start_ms, bool)
            or isinstance(dur_ms, bool)
            or start_ms < 0
            or dur_ms < 0
        ):
            raise TranscriptParseError(f"event {index} has invalid timing")
        pieces = [s.get("utf8", "") for s in event["segs"] if isinstance(s, dict)]  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        cue_text = " ".join("".join(p for p in pieces if isinstance(p, str)).split())  # pyright: ignore[reportUnknownVariableType]
        if not cue_text:
            continue
        start = round(start_ms / 1000, 3)
        segments.append(
            TranscriptSegment(start=start, end=round(start + dur_ms / 1000, 3), text=cue_text)
        )
        _check_count(len(segments))
    return segments


def _sentences(text: str) -> list[tuple[str, str]]:
    """(sentence, separator-that-followed-it); the separator is " " after Latin punctuation, "" for CJK."""
    out: list[tuple[str, str]] = []
    pos = 0
    for m in _SENTENCE_SPLIT.finditer(text):
        sentence = text[pos : m.start()]
        if sentence:
            out.append((sentence, " " if m.group() else ""))
        pos = m.end()
    if text[pos:]:
        out.append((text[pos:], ""))
    return out


def _split_long(text: str, limit: int) -> list[str]:
    """Split one over-long paragraph into pieces ≤ `limit` chars, preferring sentence boundaries."""
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    current = ""
    pending_sep = ""
    for sentence, sep in _sentences(text):
        candidate = f"{current}{pending_sep}{sentence}" if current else sentence
        if len(candidate) <= limit:
            current, pending_sep = candidate, sep
            continue
        if current:
            pieces.append(current)
        while len(sentence) > limit:  # one sentence longer than the limit: break on whitespace
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit  # no whitespace at all (e.g. unspaced CJK): hard cut
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        current, pending_sep = sentence, sep
    if current:
        pieces.append(current)
    return [p for p in pieces if p]


def parse_txt(data: bytes | str) -> list[TranscriptSegment]:
    """Untimed text → one segment per paragraph (blank-line separated); long paragraphs are split."""
    text = decode_text(data)
    segments: list[TranscriptSegment] = []
    for paragraph in _PARAGRAPH_SPLIT.split(text):
        joined = " ".join(line.strip() for line in paragraph.split("\n") if line.strip())
        for piece in _split_long(joined, TXT_MAX_SEGMENT_CHARS) if joined else []:
            segments.append(TranscriptSegment(text=piece))
            _check_count(len(segments))
    return segments


_PARSERS = {"srt": parse_srt, "vtt": parse_vtt, "json3": parse_json3, "txt": parse_txt}


def parse_transcript(ext: str, data: bytes, max_bytes: int) -> list[TranscriptSegment]:
    """Validate and parse an uploaded/fetched transcript file.

    Order of checks: extension allow-list → size cap → UTF-8 → empty → format parse → non-empty result.
    """
    fmt = ext.lower().lstrip(".")
    if fmt not in ALLOWED_EXTENSIONS:
        raise TranscriptParseError(
            f"unsupported transcript format '.{fmt}' (allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))})"
        )
    if len(data) > max_bytes:
        raise FileTooLargeError(f"transcript exceeds the {max_bytes}-byte limit")
    text = decode_text(data)
    if not text.strip():
        raise TranscriptParseError("empty transcript")
    segments = _PARSERS[fmt](text)
    if not segments:
        raise TranscriptParseError("no transcript text found")
    return segments
