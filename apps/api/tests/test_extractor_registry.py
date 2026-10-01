import pytest

from app.core.errors import InvalidSourceError
from app.ingestion import registry
from app.ingestion.base import SourceExtractor
from app.ingestion.youtube import YouTubeExtractor
from app.schemas.source import ExtractedTranscript, NormalizedSource, SourceRef


class FakeExtractor(SourceExtractor):
    """A stand-in 'platform' used to prove the domain only talks to the registry."""

    def __init__(self, platform: str, prefix: str) -> None:
        self.platform, self.prefix = platform, prefix

    def supports(self, url: str) -> bool:
        return url.startswith(self.prefix)

    def identify(self, url: str) -> SourceRef:
        return SourceRef(platform=self.platform, external_id="x", kind="video", canonical_url=url)

    def ensure_available(self) -> None:
        return None

    def extract(self, url: str) -> NormalizedSource:
        raise NotImplementedError

    def fetch_transcript(self, url: str, languages: list[str]) -> ExtractedTranscript | None:
        return None

    def list_videos(self, url: str, limit: int | None = None) -> list[NormalizedSource]:
        return []


def test_default_registry_resolves_youtube_urls() -> None:
    ex = registry.get_extractor("https://youtu.be/jNQXAC9IVRw")
    assert isinstance(ex, YouTubeExtractor) and ex.platform == "youtube"
    assert isinstance(registry.extractors()[0], YouTubeExtractor)


@pytest.mark.parametrize(
    "url",
    [
        "https://vimeo.com/1",
        "file:///etc/passwd",
        "",
        "not a url",
        "https://www.youtube.com/feed/trending",
    ],
)
def test_unknown_urls_raise_invalid_source(url: str) -> None:
    with pytest.raises(InvalidSourceError, match="no extractor"):
        registry.get_extractor(url)


def test_override_replaces_and_always_restores() -> None:
    fake = FakeExtractor("fake", "https://fake.example/")
    before = list(registry.extractors())
    with registry.override_extractors([fake]):
        assert registry.get_extractor("https://fake.example/a") is fake
        with pytest.raises(InvalidSourceError):
            registry.get_extractor("https://youtu.be/jNQXAC9IVRw")
    assert registry.extractors() == before
    with pytest.raises(RuntimeError), registry.override_extractors([fake]):
        raise RuntimeError("boom")
    assert registry.extractors() == before, "restored even when the body raises"


def test_registration_order_decides_priority() -> None:
    a, b = FakeExtractor("a", "https://same.example/"), FakeExtractor("b", "https://same.example/")
    with registry.override_extractors([]):
        registry.register_extractor(a)
        registry.register_extractor(b)
        assert registry.get_extractor("https://same.example/x") is a
        registry.register_extractor(b, first=True)
        assert registry.get_extractor("https://same.example/x") is b


def test_the_registry_module_imports_no_platform_code_until_used() -> None:
    """Checked in a fresh interpreter so it cannot disturb module identity in this test session."""
    import subprocess
    import sys

    code = (
        "import sys, app.ingestion.registry as r\n"
        "assert 'app.ingestion.youtube' not in sys.modules, 'platform module imported eagerly'\n"
        "assert r.get_extractor('https://youtu.be/jNQXAC9IVRw').platform == 'youtube'\n"
        "assert 'yt_dlp' not in sys.modules, 'yt-dlp must stay lazy'\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
