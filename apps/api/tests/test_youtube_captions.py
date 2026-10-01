"""YouTube caption fetching (P1-T3). Fully offline: yt-dlp is faked, HTTP uses httpx.MockTransport.

Fixtures under tests/fixtures/ytdlp/ are recordings of real responses (see README there). Nothing here
proves the live service still behaves this way — that is the manual check in P1-T16.
"""

import copy
import json
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from app.core.config import get_settings
from app.core.errors import (
    FileTooLargeError,
    InvalidSourceError,
    ProviderError,
    ProviderNotConfiguredError,
    SourceUnavailableError,
    TranscriptParseError,
)
from app.ingestion.youtube import YouTubeExtractor, is_allowed_caption_url

REAL_CLIENT = httpx.Client  # captured before any test patches it
FIX = Path(__file__).parent / "fixtures" / "ytdlp"
URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
INFO: dict[str, Any] = json.loads((FIX / "info_jNQXAC9IVRw.json").read_text())
JSON3 = (FIX / "caption_en.json3").read_bytes()
VTT = (FIX / "caption_en.vtt").read_bytes()
AUTO_SEGMENT = (FIX / "auto_segment_en.vtt").read_bytes()
AUTO_PLAYLIST = (FIX / "auto_playlist_en.m3u8").read_bytes()


class FakeYDL:
    def __init__(self, info: dict[str, Any] | None, error: Exception | None) -> None:
        self.info, self.error = info, error

    def __enter__(self) -> "FakeYDL":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
        assert download is False, "media must never be downloaded"
        if self.error:
            raise self.error
        return copy.deepcopy(self.info or {})


@pytest.fixture
def use_info(monkeypatch: pytest.MonkeyPatch) -> Callable[..., list[dict[str, Any]]]:
    seen_opts: list[dict[str, Any]] = []

    def install(
        info: dict[str, Any] | None = None, error: Exception | None = None
    ) -> list[dict[str, Any]]:
        def fake(opts: dict[str, Any]) -> FakeYDL:
            seen_opts.append(opts)
            return FakeYDL(info, error)

        monkeypatch.setattr(YouTubeExtractor, "_ydl", staticmethod(fake))
        return seen_opts

    return install


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(**kwargs: object) -> None:
        raise AssertionError("test attempted a real HTTP client; install mock_http first")

    monkeypatch.setattr(httpx, "Client", blocked)


@pytest.fixture
def mock_http(monkeypatch: pytest.MonkeyPatch) -> Callable[..., list[httpx.Request]]:
    real = REAL_CLIENT

    def install(handler: Callable[[httpx.Request], httpx.Response]) -> list[httpx.Request]:
        seen: list[httpx.Request] = []

        def wrapped(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return handler(request)

        monkeypatch.setattr(
            httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(wrapped), **kw)
        )
        return seen

    return install


def routes(request: httpx.Request) -> httpx.Response:
    """Default fake of the real hosts, keyed on what the recorded URLs look like."""
    url = request.url
    if url.host == "manifest.googlevideo.com":
        return httpx.Response(
            200, content=AUTO_PLAYLIST, headers={"content-type": "application/vnd.apple.mpegurl"}
        )
    if url.path == "/api/timedtext" and url.params.get("caps") == "asr":
        return httpx.Response(200, content=AUTO_SEGMENT, headers={"content-type": "text/vtt"})
    fmt = url.params.get("fmt")
    if fmt == "json3":
        return httpx.Response(200, content=JSON3, headers={"content-type": "application/json"})
    if fmt == "vtt":
        return httpx.Response(200, content=VTT, headers={"content-type": "text/vtt"})
    return httpx.Response(404)


def info_with(**overrides: Any) -> dict[str, Any]:
    info = copy.deepcopy(INFO)
    info.update(overrides)
    return info


# ---- selection -------------------------------------------------------------------------------------
def test_manual_captions_prefer_json3_and_keep_raw_bytes(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    opts = use_info(INFO)
    seen = mock_http(routes)
    tr = YouTubeExtractor().fetch_transcript(URL, ["en"])
    assert tr is not None
    assert (tr.origin, tr.language, tr.raw_ext) == ("manual", "en", "json3")
    assert tr.raw == JSON3, "raw bytes must be stored exactly as received"
    assert tr.segments and tr.segments[0].start is not None
    assert [r.url.params.get("fmt") for r in seen] == ["json3"], (
        "only the single chosen caption file is fetched"
    )
    assert opts[0].get("noplaylist") is True


def test_falls_back_to_vtt_when_json3_is_not_offered(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    info = info_with()
    info["subtitles"]["en"] = [f for f in info["subtitles"]["en"] if f["ext"] != "json3"]
    use_info(info)
    mock_http(routes)
    tr = YouTubeExtractor().fetch_transcript(URL, ["en"])
    assert tr is not None and (tr.raw_ext, tr.raw, tr.origin) == ("vtt", VTT, "manual")


def test_formats_other_than_json3_and_vtt_are_not_used(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    info = info_with(
        subtitles={"en": [{"ext": "srv3", "url": "https://www.youtube.com/api/timedtext?fmt=srv3"}]}
    )
    info["automatic_captions"] = {}
    use_info(info)
    seen = mock_http(routes)
    assert YouTubeExtractor().fetch_transcript(URL, ["en"]) is None
    assert seen == []


def test_manual_is_preferred_over_automatic_even_for_a_later_language(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    use_info(INFO)  # has manual and automatic tracks for en and de
    seen = mock_http(routes)
    tr = YouTubeExtractor().fetch_transcript(URL, ["de", "en"])
    assert tr is not None and tr.origin == "manual"
    assert all(r.url.host != "manifest.googlevideo.com" for r in seen)


def test_automatic_captions_resolve_the_hls_playlist(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    info = info_with(subtitles={})
    use_info(info)
    seen = mock_http(routes)
    tr = YouTubeExtractor().fetch_transcript(URL, ["en"])
    assert tr is not None
    assert (tr.origin, tr.language, tr.raw_ext) == ("auto", "en", "vtt")
    assert tr.raw == AUTO_SEGMENT and tr.segments
    assert [r.url.host for r in seen] == ["manifest.googlevideo.com", "www.youtube.com"]


def test_original_language_auto_track_is_preferred_over_the_bare_code(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    hls = lambda tag: {  # noqa: E731
        "ext": "vtt",
        "protocol": "m3u8_native",
        "url": f"https://manifest.googlevideo.com/api/manifest/hls_timedtext_playlist/{tag}",
    }
    use_info(
        info_with(
            subtitles={},
            automatic_captions={"en": [hls("TRANSLATED")], "en-orig": [hls("ORIGINAL")]},
        )
    )
    seen = mock_http(routes)
    tr = YouTubeExtractor().fetch_transcript(URL, ["en"])
    assert tr is not None and tr.language == "en"
    assert seen[0].url.path.endswith("/ORIGINAL")


@pytest.mark.parametrize(
    ("tracks", "wanted", "expect"),
    [
        ({"en": 1}, ["en-US"], "en"),  # wanted is more specific than the track
        ({"en-GB": 1}, ["en"], "en-GB"),  # track is more specific than wanted
        ({"EN": 1}, ["en"], "EN"),  # case-insensitive
        ({"de": 1, "en": 1}, ["en", "de"], "en"),  # preference order of wanted languages
        ({"de": 1}, ["fr", "de"], "de"),
    ],
)
def test_language_matching(use_info, mock_http, tracks, wanted, expect) -> None:  # type: ignore[no-untyped-def]
    subs = {
        k: [{"ext": "vtt", "url": "https://www.youtube.com/api/timedtext?fmt=vtt"}] for k in tracks
    }
    use_info(info_with(subtitles=subs, automatic_captions={}))
    mock_http(routes)
    tr = YouTubeExtractor().fetch_transcript(URL, wanted)
    assert tr is not None and tr.language == expect


@pytest.mark.parametrize(
    "info", [info_with(subtitles={}, automatic_captions={}), info_with(), {"id": "jNQXAC9IVRw"}]
)
def test_no_acceptable_caption_returns_none(use_info, mock_http, info) -> None:  # type: ignore[no-untyped-def]
    use_info(info)
    seen = mock_http(routes)
    assert YouTubeExtractor().fetch_transcript(URL, ["fr"]) is None
    assert seen == []


# ---- SSRF guard ------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/api/timedtext?fmt=vtt",
        "https://youtube.com/api/timedtext",
        "https://manifest.googlevideo.com/api/manifest/hls_timedtext_playlist/x",
        "https://r1---sn-abc.googlevideo.com/x",
        "https://www.youtube.com:443/api/timedtext",
    ],
)
def test_allowed_caption_urls(url: str) -> None:
    assert is_allowed_caption_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.youtube.com/api/timedtext",  # not https
        "https://youtube.com.evil.com/api/timedtext",  # suffix trick
        "https://evil.com/www.youtube.com/api/timedtext",  # host in path
        "https://notyoutube.com/x",
        "https://evilgooglevideo.com/x",  # no dot boundary
        "https://www.youtube.com@evil.com/x",  # userinfo trick: real host is evil.com
        "https://user:pw@www.youtube.com/x",  # credentials
        "https://www.youtube.com:8443/x",  # unusual port
        "https://127.0.0.1/x",
        "https://localhost/x",
        "file:///etc/passwd",
        "ftp://www.youtube.com/x",
        "//www.youtube.com/x",
        "",
    ],
)
def test_refused_caption_urls(url: str) -> None:
    assert not is_allowed_caption_url(url)


def test_a_foreign_host_in_the_info_dict_is_never_contacted(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    bad = info_with(
        subtitles={"en": [{"ext": "json3", "url": "https://evil.example/captions.json3"}]}
    )
    use_info(bad)
    seen = mock_http(routes)
    with pytest.raises(ProviderError, match="allow-listed"):
        YouTubeExtractor().fetch_transcript(URL, ["en"])
    assert seen == []


def test_hls_segment_on_a_foreign_host_is_refused(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    use_info(info_with(subtitles={}))

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "manifest.googlevideo.com":
            return httpx.Response(
                200, content=b"#EXTM3U\n#EXTINF:5,\nhttps://evil.example/seg.vtt\n#EXT-X-ENDLIST\n"
            )
        return httpx.Response(200, content=AUTO_SEGMENT)

    seen = mock_http(handler)
    with pytest.raises(ProviderError, match="allow-listed"):
        YouTubeExtractor().fetch_transcript(URL, ["en"])
    assert all(r.url.host != "evil.example" for r in seen)


def test_redirect_to_a_foreign_host_is_not_followed(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    use_info(INFO)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.youtube.com":
            return httpx.Response(302, headers={"location": "https://evil.example/steal"})
        return httpx.Response(200, content=b"gotcha")

    seen = mock_http(handler)
    with pytest.raises(ProviderError):
        YouTubeExtractor().fetch_transcript(URL, ["en"])
    assert [r.url.host for r in seen] == ["www.youtube.com"]


def test_redirect_within_allowed_hosts_is_followed(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    use_info(INFO)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "www.youtube.com":
            return httpx.Response(
                302, headers={"location": "https://r1.googlevideo.com/api/timedtext?fmt=json3"}
            )
        return httpx.Response(200, content=JSON3)

    mock_http(handler)
    tr = YouTubeExtractor().fetch_transcript(URL, ["en"])
    assert tr is not None and tr.raw == JSON3


def test_redirect_loop_is_bounded(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    use_info(INFO)
    seen = mock_http(
        lambda r: httpx.Response(302, headers={"location": "https://www.youtube.com/loop"})
    )
    with pytest.raises(ProviderError, match="redirects"):
        YouTubeExtractor().fetch_transcript(URL, ["en"])
    assert len(seen) <= 5


# ---- limits and bad content ----------------------------------------------------------------------
@pytest.fixture
def small_cap() -> Any:
    settings = get_settings()
    old, settings.max_transcript_bytes = settings.max_transcript_bytes, 100
    yield
    settings.max_transcript_bytes = old


def test_oversize_caption_is_refused_while_streaming(use_info, mock_http, small_cap) -> None:  # type: ignore[no-untyped-def]
    use_info(INFO)
    mock_http(lambda r: httpx.Response(200, content=b"x" * 5000))
    with pytest.raises(FileTooLargeError):
        YouTubeExtractor().fetch_transcript(URL, ["en"])


def test_oversize_declared_content_length_is_refused(use_info, mock_http, small_cap) -> None:  # type: ignore[no-untyped-def]
    use_info(INFO)
    mock_http(lambda r: httpx.Response(200, content=b"x", headers={"content-length": "999999"}))
    with pytest.raises(FileTooLargeError):
        YouTubeExtractor().fetch_transcript(URL, ["en"])


@pytest.mark.parametrize("body", [b"not json at all", b"{}", b"\xff\xfe\x00"])
def test_malformed_json3_is_a_parse_error(use_info, mock_http, body) -> None:  # type: ignore[no-untyped-def]
    use_info(info_with(automatic_captions={}))
    mock_http(lambda r: httpx.Response(200, content=body))
    with pytest.raises(TranscriptParseError):
        YouTubeExtractor().fetch_transcript(URL, ["en"])


def test_http_error_on_the_caption_is_a_provider_error_without_the_url(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    use_info(INFO)
    mock_http(lambda r: httpx.Response(403))
    with pytest.raises(ProviderError) as exc:
        YouTubeExtractor().fetch_transcript(URL, ["en"])
    assert "403" in str(exc.value) and "timedtext" not in str(exc.value)


def test_timeout_is_a_provider_error(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    use_info(INFO)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    mock_http(handler)
    with pytest.raises(ProviderError, match="timed out"):
        YouTubeExtractor().fetch_transcript(URL, ["en"])


def test_an_empty_hls_playlist_means_no_transcript(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    use_info(
        info_with(subtitles={}, automatic_captions={"en": [INFO["automatic_captions"]["en"][0]]})
    )
    mock_http(lambda r: httpx.Response(200, content=b"#EXTM3U\n#EXT-X-ENDLIST\n"))
    assert YouTubeExtractor().fetch_transcript(URL, ["en"]) is None


def test_hls_playlist_with_too_many_segments_is_refused(use_info, mock_http) -> None:  # type: ignore[no-untyped-def]
    use_info(info_with(subtitles={}))
    playlist = "#EXTM3U\n" + "".join(
        f"https://www.youtube.com/api/timedtext?n={i}\n" for i in range(600)
    )
    mock_http(lambda r: httpx.Response(200, content=playlist.encode()))
    with pytest.raises(ProviderError, match="too many segments"):
        YouTubeExtractor().fetch_transcript(URL, ["en"])


# ---- yt-dlp errors and installation --------------------------------------------------------------
@pytest.mark.parametrize(
    "message",
    [
        "ERROR: [youtube] x: Private video. Sign in if you've been granted access to this video",
        "ERROR: [youtube] x: Video unavailable",
        "ERROR: [youtube] x: This video has been removed by the uploader",
        "ERROR: [youtube] x: The uploader has not made this video available in your country",
        "ERROR: [youtube] x: Sign in to confirm your age. This video may be inappropriate for some users.",
    ],
)
def test_unavailable_videos_map_to_source_unavailable(use_info, message: str) -> None:  # type: ignore[no-untyped-def]
    use_info(error=Exception(message))
    with pytest.raises(SourceUnavailableError):
        YouTubeExtractor().extract(URL)
    with pytest.raises(SourceUnavailableError):
        YouTubeExtractor().fetch_transcript(URL, ["en"])


def test_other_extractor_failures_are_provider_errors_without_the_original_message(
    use_info,
) -> None:  # type: ignore[no-untyped-def]
    use_info(
        error=OSError("connection reset by https://www.youtube.com/watch?v=jNQXAC9IVRw?sig=SECRET")
    )
    with pytest.raises(ProviderError) as exc:
        YouTubeExtractor().extract(URL)
    assert "SECRET" not in str(exc.value) and "OSError" in str(exc.value)


def test_missing_ytdlp_is_a_configuration_error_with_an_install_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "yt_dlp", None)  # makes `import yt_dlp` raise ImportError
    for call in (
        lambda: YouTubeExtractor().extract(URL),
        lambda: YouTubeExtractor().fetch_transcript(URL, ["en"]),
    ):
        with pytest.raises(ProviderNotConfiguredError, match="uv sync --extra ingestion"):
            call()


def test_ytdlp_is_always_configured_to_skip_downloads(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    class Recorder:
        def __init__(self, params: dict[str, Any]) -> None:
            captured.update(params)

    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=Recorder))
    # a caller must not be able to turn skip_download off
    YouTubeExtractor._ydl({"noplaylist": True, "skip_download": False})  # pyright: ignore[reportPrivateUsage]
    assert captured["noplaylist"] is True
    assert captured["skip_download"] is True


@pytest.mark.parametrize(
    "bad",
    [
        "https://www.youtube.com/@SomeChannel/videos",
        "https://www.youtube.com/playlist?list=PLabcdefghij123",
    ],
)
def test_channels_and_playlists_are_not_single_video_inputs(use_info, bad: str) -> None:  # type: ignore[no-untyped-def]
    use_info(INFO)
    with pytest.raises(InvalidSourceError):
        YouTubeExtractor().extract(bad)
    with pytest.raises(InvalidSourceError):
        YouTubeExtractor().fetch_transcript(bad, ["en"])


# ---- identify / ensure_available (no network) ------------------------------------------------------
@pytest.mark.parametrize(
    ("url", "kind", "external_id", "canonical"),
    [
        (
            "https://youtu.be/jNQXAC9IVRw",
            "video",
            "jNQXAC9IVRw",
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        ),
        (
            "https://www.youtube.com/watch?v=jNQXAC9IVRw&list=PLx&t=5",
            "video",
            "jNQXAC9IVRw",
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        ),
        (
            "https://www.youtube.com/shorts/jNQXAC9IVRw",
            "video",
            "jNQXAC9IVRw",
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        ),
        (
            "https://m.youtube.com/watch?v=jNQXAC9IVRw",
            "video",
            "jNQXAC9IVRw",
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        ),
        (
            "https://www.youtube.com/playlist?list=PLabcdefghij123",
            "playlist",
            "PLabcdefghij123",
            "https://www.youtube.com/playlist?list=PLabcdefghij123",
        ),
        (
            "https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A/videos",
            "channel",
            "UC4QobU6STFB0P71PMvOGN5A",
            "https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A",
        ),
        (
            "https://www.youtube.com/@SomeChannel/videos",
            "channel",
            "@SomeChannel",
            "https://www.youtube.com/@SomeChannel",
        ),
    ],
)
def test_identify_is_pure_and_canonical(monkeypatch, url, kind, external_id, canonical) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setitem(sys.modules, "yt_dlp", None)  # prove identify() does not need yt-dlp
    ref = YouTubeExtractor().identify(url)  # httpx.Client is also blocked by the autouse fixture
    assert (ref.platform, ref.kind, ref.external_id, ref.canonical_url) == (
        "youtube",
        kind,
        external_id,
        canonical,
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/watch?v=jNQXAC9IVRw",
        "file:///etc/passwd",
        "not a url",
        "https://www.youtube.com/watch?v=short",
    ],
)
def test_identify_rejects_unrecognised_urls(url: str) -> None:
    with pytest.raises(InvalidSourceError):
        YouTubeExtractor().identify(url)


def test_ensure_available_reports_a_missing_ytdlp_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "yt_dlp", None)
    with pytest.raises(ProviderNotConfiguredError, match="uv sync --extra ingestion"):
        YouTubeExtractor().ensure_available()
    monkeypatch.setitem(sys.modules, "yt_dlp", SimpleNamespace(YoutubeDL=object))
    YouTubeExtractor().ensure_available()  # returns silently
