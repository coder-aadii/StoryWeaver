from abc import ABC, abstractmethod

from app.schemas.source import ExtractedTranscript, NormalizedSource, SourceRef


class SourceExtractor(ABC):
    """Turns a platform-specific reference into NormalizedSource objects.

    Implementations are the only place platform-specific logic may live; domain code reaches them
    through `app.ingestion.registry.get_extractor`.
    """

    platform: str

    @abstractmethod
    def supports(self, url: str) -> bool: ...

    @abstractmethod
    def identify(self, url: str) -> SourceRef:
        """Classify a URL and derive its stable id + canonical URL. Pure: NO network, no yt-dlp.

        Raises `InvalidSourceError` for anything this extractor does not recognise.
        """

    @abstractmethod
    def ensure_available(self) -> None:
        """Cheap, network-free check that the extractor's optional dependency is usable.

        Raises `ProviderNotConfiguredError` (with an install hint) when it is not.
        """

    @abstractmethod
    def extract(self, url: str) -> NormalizedSource:
        """Fetch METADATA ONLY for one video (no transcript, no media)."""

    @abstractmethod
    def fetch_transcript(self, url: str, languages: list[str]) -> ExtractedTranscript | None:
        """Fetch the best available caption track as text — never the media itself.

        `languages` is a preference order (e.g. ["en"]). Returns None when the source has no caption
        in any acceptable language (the caller decides what that means). Raises
        `SourceUnavailableError` for private/removed/blocked videos and `ProviderError` for transient
        failures.
        """

    @abstractmethod
    def list_videos(self, url: str, limit: int | None = None) -> list[NormalizedSource]:
        """Enumerate videos of a channel/playlist (for the 'how many to import?' step). P11."""
