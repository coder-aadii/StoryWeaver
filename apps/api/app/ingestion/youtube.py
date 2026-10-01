"""YouTube extractor. All YouTube specifics live here; yt-dlp is an optional, lazily-imported extra.

Only METADATA and small CAPTION FILES are ever fetched — `skip_download` is always on and no media is
requested. Observed against a real yt-dlp info dict (2026-10, video jNQXAC9IVRw):
  * manual captions (`subtitles`): many formats (json3, vtt, srt, ttml, srv1-3) served directly from
    `https://www.youtube.com/api/timedtext`;
  * automatic captions (`automatic_captions`): `vtt` with protocol `m3u8_native` — the URL on
    `manifest.googlevideo.com` is an HLS *playlist* whose segment URLs (complete WebVTT files) are again
    on `www.youtube.com/api/timedtext`. The playlist is therefore resolved and each segment fetched.
Hence the SSRF allow-list is exactly: https, no credentials, hostname == or a subdomain of
`youtube.com` / `googlevideo.com`.
"""

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx

from app.core.config import get_settings
from app.core.errors import (
    FileTooLargeError,
    InvalidSourceError,
    ProviderError,
    ProviderNotConfiguredError,
    SourceUnavailableError,
    TranscriptParseError,
)
from app.ingestion import parsers
from app.ingestion.base import SourceExtractor
from app.schemas.source import (
    ExtractedTranscript,
    NormalizedSource,
    SourceKind,
    SourceRef,
    TranscriptOrigin,
    TranscriptSegment,
)

_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_PLAYLIST_ID = re.compile(r"^[A-Za-z0-9_-]{10,64}$")
_CHANNEL = re.compile(r"^/(@[A-Za-z0-9._-]+|channel/[A-Za-z0-9_-]+|c/[^/]+|user/[^/]+)")
_CANONICAL_CHANNEL_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")

CAPTION_HOST_SUFFIXES = ("youtube.com", "googlevideo.com")
CAPTION_FORMAT_PREFERENCE = ("json3", "vtt")
CAPTION_TIMEOUT_SECONDS = 20.0
MAX_CAPTION_REDIRECTS = 3
MAX_HLS_SEGMENTS = 500

# yt-dlp reports why a video cannot be read only as text; match the stable phrases.
_UNAVAILABLE_PATTERNS = (
    "private video",
    "video unavailable",
    "this video is unavailable",
    "this video is not available",
    "has been removed",
    "removed by the uploader",
    "account associated with this video has been terminated",
    "available in your country",
    "blocked it in your country",
    "who has blocked it",
    "members-only",
    "join this channel",
    "confirm your age",
    "age-restricted",
    "this video is no longer available",
)
_EXTRA_WHITELIST = (
    "view_count",
    "like_count",
    "comment_count",
    "channel_follower_count",
    "age_limit",
    "availability",
    "live_status",
    "uploader_id",
    "categories",
)


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


def canonical_video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def canonical_channel_url(channel_id: str) -> str:
    return f"https://www.youtube.com/channel/{channel_id}"


def is_allowed_caption_url(url: str) -> bool:
    """SSRF guard for caption fetches: https, no credentials, YouTube/googlevideo hosts only."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme != "https" or parsed.username or parsed.password or port not in (None, 443):
        return False
    return any(host == s or host.endswith("." + s) for s in CAPTION_HOST_SUFFIXES)


def _published_at(info: dict[str, Any]) -> datetime | None:
    ts = info.get("timestamp")
    if isinstance(ts, int | float):
        return datetime.fromtimestamp(ts, UTC)
    day = info.get("upload_date")
    if isinstance(day, str) and re.fullmatch(r"\d{8}", day):
        try:
            return datetime.strptime(day, "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            return None
    return None


def _thumbnail(info: dict[str, Any]) -> str | None:
    candidates = [info.get("thumbnail")] + [
        t.get("url") for t in reversed(info.get("thumbnails") or [])
    ]
    for url in candidates:
        if isinstance(url, str) and url.startswith("https://"):
            return url
    return None


def _extras(info: dict[str, Any]) -> dict[str, Any]:
    """A small whitelist of descriptive fields. Never the raw info dict (it holds signed URLs)."""
    extra: dict[str, Any] = {}
    for key in _EXTRA_WHITELIST:
        value = info.get(key)
        if isinstance(value, str | int | float | bool):
            extra[key] = value
        elif key == "categories" and isinstance(value, list):
            extra[key] = [str(v)[:64] for v in value[:10]]
    tags = info.get("tags")
    if isinstance(tags, list):
        extra["tags"] = [str(t)[:64] for t in tags[:20]]
    return extra


def entry_to_source(info: dict[str, Any], kind: SourceKind = "video") -> NormalizedSource:
    channel_id = info.get("channel_id")
    canonical_channel = (
        channel_id
        if isinstance(channel_id, str) and _CANONICAL_CHANNEL_ID.match(channel_id)
        else None
    )
    return NormalizedSource(
        platform="youtube",
        kind=kind,
        external_id=str(info["id"]),
        url=canonical_video_url(str(info["id"])),
        title=info.get("title") or str(info["id"]),
        description=info.get("description"),
        duration_seconds=info.get("duration"),
        published_at=_published_at(info),
        language=info.get("language"),
        # Only the canonical UC… id identifies a channel; handles/URLs can change (KI-24).
        channel_external_id=canonical_channel,
        channel_title=info.get("channel") or info.get("uploader"),
        channel_url=canonical_channel_url(canonical_channel) if canonical_channel else None,
        thumbnail_url=_thumbnail(info),
        extra=_extras(info),
    )


def _map_ytdlp_error(exc: Exception) -> Exception:
    text = str(exc).lower()
    if any(p in text for p in _UNAVAILABLE_PATTERNS):
        return SourceUnavailableError(
            "the video is private, removed, age/region restricted or otherwise unavailable"
        )
    # Type only: yt-dlp messages can embed URLs.
    return ProviderError(f"yt-dlp failed: {type(exc).__name__}")


def _language_candidates(available: list[str], wanted: str, *, automatic: bool) -> list[str]:
    """Track keys to try for one wanted language, best first.

    Automatic tracks: `<lang>-orig` is yt-dlp's name for the original-language ASR text and is
    preferred over the bare code (which may be a translation). Then exact, then prefix matches in
    either direction ('en' ~ 'en-US').
    """
    w = wanted.lower()
    lower = {k.lower(): k for k in available}
    ordered: list[str] = []
    if automatic and f"{w}-orig" in lower:
        ordered.append(lower[f"{w}-orig"])
    if w in lower:
        ordered.append(lower[w])
    ordered += [
        lower[k] for k in sorted(lower) if k.startswith(w + "-") and not k.endswith("-orig")
    ]
    ordered += [lower[k] for k in sorted(lower) if w.startswith(k + "-")]
    seen: set[str] = set()
    return [k for k in ordered if not (k in seen or seen.add(k))]


def _pick_format(formats: list[dict[str, Any]]) -> dict[str, Any] | None:
    for ext in CAPTION_FORMAT_PREFERENCE:
        for f in formats:
            if f.get("ext") == ext and isinstance(f.get("url"), str):
                return f
    return None


class YouTubeExtractor(SourceExtractor):
    platform = "youtube"

    def supports(self, url: str) -> bool:
        try:
            classify_youtube_url(url)
        except InvalidSourceError:
            return False
        return True

    def identify(self, url: str) -> SourceRef:
        kind, token = classify_youtube_url(url)
        if kind == "video":
            canonical = canonical_video_url(token)
        elif kind == "playlist":
            canonical = f"https://www.youtube.com/playlist?list={token}"
        elif token.startswith("channel/"):
            token = token.split("/", 1)[1]  # the canonical UC… id appears in the URL itself
            canonical = canonical_channel_url(token)
        else:
            canonical = (
                f"https://www.youtube.com/{token}"  # @handle, c/name, user/name: best effort
            )
        return SourceRef(
            platform=self.platform, external_id=token, kind=kind, canonical_url=canonical
        )

    def ensure_available(self) -> None:
        try:
            import yt_dlp  # noqa: F401  # pyright: ignore[reportMissingImports, reportUnusedImport]
        except ImportError as exc:
            raise ProviderNotConfiguredError(
                "yt-dlp is not installed; run `uv sync --extra ingestion`"
            ) from exc

    @staticmethod
    def _ydl(opts: dict[str, Any]) -> Any:
        try:
            from yt_dlp import YoutubeDL  # pyright: ignore[reportMissingImports]
        except ImportError as exc:
            raise ProviderNotConfiguredError(
                "yt-dlp is not installed; run `uv sync --extra ingestion`"
            ) from exc
        # skip_download comes LAST so no caller can ever re-enable media downloads.
        params: Any = {"quiet": True, "no_warnings": True, **opts, "skip_download": True}
        return YoutubeDL(params)

    def _video_info(self, url: str) -> dict[str, Any]:
        kind, _ = classify_youtube_url(url)
        if kind != "video":
            raise InvalidSourceError("expected a single video URL; channels/playlists arrive later")
        with self._ydl({"noplaylist": True}) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except ProviderNotConfiguredError:
                raise
            except Exception as exc:
                raise _map_ytdlp_error(exc) from exc
        if not isinstance(info, dict) or "id" not in info:
            raise ProviderError("yt-dlp returned no video information")
        return info

    def extract(self, url: str) -> NormalizedSource:
        return entry_to_source(self._video_info(url))

    # -- captions ------------------------------------------------------------------------------
    def fetch_transcript(self, url: str, languages: list[str]) -> ExtractedTranscript | None:
        info = self._video_info(url)
        for automatic, tracks in (
            (False, info.get("subtitles")),
            (True, info.get("automatic_captions")),
        ):
            tracks = tracks if isinstance(tracks, dict) else {}
            for wanted in languages:
                for key in _language_candidates(list(tracks), wanted, automatic=automatic):
                    chosen = _pick_format(tracks[key])
                    if chosen is None:
                        continue
                    result = self._download_track(chosen, key, automatic)
                    if result is not None:
                        return result
        return None

    def _download_track(
        self, fmt: dict[str, Any], key: str, automatic: bool
    ) -> ExtractedTranscript | None:
        url, ext = fmt["url"], fmt["ext"]
        limit = get_settings().max_transcript_bytes
        origin: TranscriptOrigin = "auto" if automatic else "manual"
        language = key[: -len("-orig")] if key.endswith("-orig") else key
        with httpx.Client(timeout=CAPTION_TIMEOUT_SECONDS, follow_redirects=False) as client:
            try:
                if str(fmt.get("protocol", "")).startswith("m3u8"):
                    segments, raw = self._download_hls_vtt(client, url, limit)
                    ext = "vtt"
                else:
                    raw = self._get_capped(client, url, limit)
                    segments = (
                        parsers.parse_json3(raw) if ext == "json3" else parsers.parse_vtt(raw)
                    )
            except (FileTooLargeError, TranscriptParseError, ProviderError):
                raise
            except httpx.TimeoutException as exc:
                raise ProviderError("caption download timed out") from exc
            except httpx.HTTPError as exc:
                raise ProviderError(f"caption download failed: {type(exc).__name__}") from exc
        if not segments:
            return None
        return ExtractedTranscript(
            segments=segments, language=language, origin=origin, raw=raw, raw_ext=ext
        )

    @staticmethod
    def _get_capped(client: httpx.Client, url: str, limit: int) -> bytes:
        """GET one small caption resource: allow-listed host at every hop, hard byte cap, no media."""
        for _ in range(MAX_CAPTION_REDIRECTS + 1):
            if not is_allowed_caption_url(url):
                raise ProviderError("refusing to fetch captions from a non-allow-listed host")
            with client.stream("GET", url) as resp:
                if resp.is_redirect:
                    location = resp.headers.get("location", "")
                    url = urljoin(url, location)  # re-validated at the top of the loop
                    continue
                if resp.status_code >= 400:
                    raise ProviderError(f"caption download returned HTTP {resp.status_code}")
                declared = resp.headers.get("content-length")
                if declared and declared.isdigit() and int(declared) > limit:
                    raise FileTooLargeError(f"caption file exceeds {limit} bytes")
                chunks: list[bytes] = []
                size = 0
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    if size > limit:
                        raise FileTooLargeError(f"caption file exceeds {limit} bytes")
                    chunks.append(chunk)
                return b"".join(chunks)
        raise ProviderError("too many redirects while fetching captions")

    def _download_hls_vtt(
        self, client: httpx.Client, playlist_url: str, limit: int
    ) -> tuple[list[TranscriptSegment], bytes]:
        """Auto captions: resolve the HLS playlist, fetch each WebVTT segment, parse and concatenate.

        UNVERIFIED for videos longer than one segment (playlist TARGETDURATION is 600 s): segments
        are assumed to carry absolute cue times; normalization re-sorts regardless.
        """
        playlist = self._get_capped(client, playlist_url, limit).decode("utf-8", "replace")
        urls = [
            urljoin(playlist_url, line.strip())
            for line in playlist.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        if not urls:
            return [], b""
        if len(urls) > MAX_HLS_SEGMENTS:
            raise ProviderError("caption playlist has too many segments")
        segments: list[TranscriptSegment] = []
        raws: list[bytes] = []
        remaining = limit
        for seg_url in urls:
            data = self._get_capped(client, seg_url, remaining)
            remaining -= len(data)
            raws.append(data)
            segments.extend(parsers.parse_vtt(data))
        return segments, b"\n".join(raws)

    def list_videos(self, url: str, limit: int | None = None) -> list[NormalizedSource]:
        kind, _ = classify_youtube_url(url)
        if kind not in ("channel", "playlist"):
            raise InvalidSourceError("list_videos() expects a channel or playlist URL")
        opts: dict[str, Any] = {"extract_flat": True}
        if limit:
            opts["playlistend"] = limit
        with self._ydl(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except ProviderNotConfiguredError:
                raise
            except Exception as exc:
                raise _map_ytdlp_error(exc) from exc
        return [entry_to_source(e) for e in (info.get("entries") or []) if e and e.get("id")]
