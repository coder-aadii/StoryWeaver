import io
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel

from app.core.errors import (
    InvalidSourceError,
    ProviderError,
    ProviderNotConfiguredError,
    UnsafePathError,
)
from app.core.storage import LocalStorage, sanitize_filename
from app.ingestion.chunking import chunk_segments
from app.ingestion.youtube import YouTubeExtractor, classify_youtube_url
from app.intelligence.providers.base import LLMProvider, extract_json
from app.intelligence.providers.ollama import OllamaProvider
from app.schemas.scene import SceneSpec
from app.schemas.source import TranscriptSegment
from app.video.timeline import build_timeline, estimate_duration


# ---- storage security
@pytest.mark.parametrize("key", ["../etc/passwd", "/abs/path", "a/../../x", "", "a\x00b"])
def test_storage_rejects_traversal(tmp_path: Path, key: str) -> None:
    with pytest.raises(UnsafePathError):
        LocalStorage(tmp_path).path_for(key)


def test_storage_put_streams_and_hashes(tmp_path: Path) -> None:
    size, digest = LocalStorage(tmp_path).put("images/a.png", io.BytesIO(b"hello"))
    assert size == 5
    assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert (tmp_path / "images" / "a.png").read_bytes() == b"hello"


def test_sanitize_filename() -> None:
    assert sanitize_filename("../../my file?.mp3") == "my_file_.mp3"
    with pytest.raises(UnsafePathError):
        sanitize_filename("..")


# ---- ingestion
@pytest.mark.parametrize(
    ("url", "kind"),
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video"),
        ("https://youtu.be/dQw4w9WgXcQ", "video"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "video"),
        ("https://www.youtube.com/@SomeChannel/videos", "channel"),
        ("https://www.youtube.com/playlist?list=PLabcdefghij123", "playlist"),
    ],
)
def test_classify_youtube(url: str, kind: str) -> None:
    assert classify_youtube_url(url)[0] == kind


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://evil.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=bad",
        "javascript:alert(1)",
    ],
)
def test_reject_bad_urls(url: str) -> None:
    with pytest.raises(InvalidSourceError):
        classify_youtube_url(url)
    assert not YouTubeExtractor().supports(url)


def test_chunking_preserves_timing() -> None:
    segs = [TranscriptSegment(start=i, end=i + 1, text="word " * 100) for i in range(6)]
    chunks = chunk_segments(segs, max_chars=1000)
    assert len(chunks) > 1
    assert chunks[0][1] == 0 and chunks[-1][2] == 6


# ---- timeline determinism
def test_timeline_is_deterministic_and_contiguous() -> None:
    scenes = [
        SceneSpec(scene_id="b", sequence=2, narration="word " * 5, duration=3.0),
        SceneSpec(scene_id="a", sequence=1, narration="short"),
    ]
    t = build_timeline(scenes)
    assert [s.scene_id for s in t.scenes] == ["a", "b"]
    assert t.scenes[1].start == t.scenes[0].duration
    assert t.duration_seconds == t.scenes[0].duration + 3.0
    assert estimate_duration("x " * 1000) == 7.0


# ---- providers
class _Out(BaseModel):
    title: str


class _Fake(LLMProvider):
    name = "fake"

    def __init__(self, replies: list[str]) -> None:
        self.replies = replies

    def is_configured(self) -> bool:
        return True

    def _complete(self, prompt, *, system, model, temperature, max_tokens):  # type: ignore[no-untyped-def]
        return self.replies.pop(0), 1, 1


def test_structured_output_retries_then_succeeds() -> None:
    p = _Fake(["not json", '```json\n{"title": "ok"}\n```'])
    assert p.generate_structured("x", _Out, model="m").title == "ok"


def test_structured_output_gives_up() -> None:
    with pytest.raises(ProviderError):
        _Fake(["nope", "still nope"]).generate_structured("x", _Out, model="m")


def test_unconfigured_provider_fails_clearly_not_at_startup() -> None:
    with pytest.raises(ProviderNotConfiguredError):
        OllamaProvider(base_url="").generate("x", model="m")


def test_extract_json_strips_prose() -> None:
    assert extract_json('Sure! {"a": 1} hope that helps') == '{"a": 1}'


def test_ollama_provider_http_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        return httpx.Response(
            200, json={"message": {"content": "hi"}, "prompt_eval_count": 3, "eval_count": 2}
        )

    real = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )
    res = OllamaProvider(base_url="http://ollama.test").generate("hello", model="m")
    assert (res.text, res.output_tokens, seen["path"]) == ("hi", 2, "/api/chat")
