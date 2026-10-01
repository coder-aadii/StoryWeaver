"""YouTube extractor. All YouTube specifics live here; yt-dlp is an optional, lazily-imported extra."""

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.core.errors import InvalidSourceError, ProviderNotConfiguredError
from app.ingestion.base import SourceExtractor
from app.schemas.source import NormalizedSource, SourceKind

_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PLAYLIST_ID = re.compile(r"^[A-Za-z0-9_-]{10,64}$")
_CHANNEL = re.compile(r"^/(@[A-Za-z0-9._-]+|channel/[A-Za-z0-9_-]+|c/[^/]+|user/[^/]+)")


def classify_youtube_url(url: str) -> tuple[SourceKind, str]:
    """Validate a URL and return (kind, canonical id). Raises InvalidSourceError."""
    if len(url) > 2048:
        raise InvalidSourceError("URL too long")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or (parsed.hostname or "") not in _HOSTS:
        raise InvalidSourceError("not a YouTube URL")
    host, path, qs = parsed.hostname, parsed.path, parse_qs(parsed.query)
    if host == "youtu.be":
        vid = path.lstrip("/")
        if _VIDEO_ID.match(vid):
            return "video", vid
    elif path == "/watch" and _VIDEO_ID.match((qs.get("v") or [""])[0]):
        return "video", qs["v"][0]
    elif path.startswith(("/shorts/", "/embed/")):
        vid = path.split("/")[2] if len(path.split("/")) > 2 else ""
        if _VIDEO_ID.match(vid):
            return "video", vid
    elif path == "/playlist" and _PLAYLIST_ID.match((qs.get("list") or [""])[0]):
        return "playlist", qs["list"][0]
    elif m := _CHANNEL.match(path):
        return "channel", m.group(1)
    raise InvalidSourceError("unrecognised YouTube URL")


def _entry_to_source(info: dict[str, Any], kind: SourceKind = "video") -> NormalizedSource:
    ts = info.get("timestamp")
    return NormalizedSource(
        platform="youtube",
        kind=kind,
        external_id=str(info["id"]),
        url=info.get("webpage_url") or f"https://www.youtube.com/watch?v={info['id']}",
        title=info.get("title") or str(info["id"]),
        description=info.get("description"),
        duration_seconds=info.get("duration"),
        published_at=datetime.fromtimestamp(ts, UTC) if ts else None,
        language=info.get("language"),
        channel_external_id=info.get("channel_id"),
        channel_title=info.get("channel") or info.get("uploader"),
    )


class YouTubeExtractor(SourceExtractor):
    platform = "youtube"

    def supports(self, url: str) -> bool:
        try:
            classify_youtube_url(url)
        except InvalidSourceError:
            return False
        return True

    @staticmethod
    def _ydl(opts: dict[str, Any]) -> Any:
        try:
            from yt_dlp import YoutubeDL  # pyright: ignore[reportMissingImports]
        except ImportError as exc:
            raise ProviderNotConfiguredError(
                "yt-dlp is not installed; run `uv sync --extra ingestion`"
            ) from exc
        params: Any = {"quiet": True, "no_warnings": True, "skip_download": True, **opts}
        return YoutubeDL(params)

    def extract(self, url: str) -> NormalizedSource:
        kind, _ = classify_youtube_url(url)
        if kind != "video":
            raise InvalidSourceError("extract() expects a single video URL; use list_videos()")
        with self._ydl({"noplaylist": True}) as ydl:
            info = ydl.extract_info(url, download=False)
        return _entry_to_source(info)

    def list_videos(self, url: str, limit: int | None = None) -> list[NormalizedSource]:
        kind, _ = classify_youtube_url(url)
        if kind not in ("channel", "playlist"):
            raise InvalidSourceError("list_videos() expects a channel or playlist URL")
        opts: dict[str, Any] = {"extract_flat": True}
        if limit:
            opts["playlistend"] = limit
        with self._ydl(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return [_entry_to_source(e) for e in (info.get("entries") or []) if e and e.get("id")]
