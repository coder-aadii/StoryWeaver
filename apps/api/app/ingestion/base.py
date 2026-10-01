from abc import ABC, abstractmethod

from app.schemas.source import NormalizedSource


class SourceExtractor(ABC):
    """Turns a platform-specific reference into NormalizedSource objects."""

    platform: str

    @abstractmethod
    def supports(self, url: str) -> bool: ...

    @abstractmethod
    def extract(self, url: str) -> NormalizedSource:
        """Fetch metadata (+ transcript when available) for one video/channel/playlist."""

    @abstractmethod
    def list_videos(self, url: str, limit: int | None = None) -> list[NormalizedSource]:
        """Enumerate videos of a channel/playlist (for the 'how many to import?' step)."""
