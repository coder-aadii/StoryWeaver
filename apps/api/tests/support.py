"""Test doubles for the Source Library."""

from pathlib import Path

from app.core.errors import ProviderError, ProviderNotConfiguredError, SourceUnavailableError
from app.ingestion.parsers import parse_vtt
from app.ingestion.youtube import YouTubeExtractor
from app.schemas.source import ExtractedTranscript, NormalizedSource

FIXTURES = Path(__file__).parent / "fixtures"
CHANNEL_ID = "UC" + "a" * 22


class FakeYouTube(YouTubeExtractor):
    """The real, pure URL identification — with canned network behaviour instead of yt-dlp.

    `mode` controls the transcript step: ok | no_captions | unavailable | transient_then_ok |
    extract_error | not_installed. Counters let tests assert how often the network would be hit.
    """

    def __init__(self, mode: str = "ok", title: str = "Volcanoes explained") -> None:
        self.mode, self.title = mode, title
        self.extract_calls = 0
        self.transcript_calls = 0

    def ensure_available(self) -> None:
        if self.mode == "not_installed":
            raise ProviderNotConfiguredError(
                "yt-dlp is not installed; run `uv sync --extra ingestion`"
            )

    def extract(self, url: str) -> NormalizedSource:
        self.extract_calls += 1
        if self.mode == "extract_error":
            raise ProviderError("youtube request failed: ConnectError")
        if self.mode == "unavailable":
            raise SourceUnavailableError("this video is private or has been removed")
        ref = self.identify(url)
        return NormalizedSource(
            platform="youtube",
            kind="video",
            external_id=ref.external_id,
            url=ref.canonical_url,
            title=self.title,
            description="A talk about volcanoes",
            duration_seconds=15.25,
            language="en",
            channel_external_id=CHANNEL_ID,
            channel_title="Earth Channel",
            channel_url=f"https://www.youtube.com/channel/{CHANNEL_ID}",
            thumbnail_url="https://i.ytimg.com/vi/x/hqdefault.jpg",
            extra={"view_count": 42},
        )

    def fetch_transcript(self, url: str, languages: list[str]) -> ExtractedTranscript | None:
        self.transcript_calls += 1
        if self.mode == "no_captions":
            return None
        if self.mode == "transient_then_ok" and self.transcript_calls == 1:
            raise ProviderError("youtube request timed out")
        raw = (FIXTURES / "transcripts" / "simple.vtt").read_bytes()
        return ExtractedTranscript(
            segments=parse_vtt(raw), language="en", origin="manual", raw=raw, raw_ext="vtt"
        )


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / "transcripts" / name).read_bytes()
