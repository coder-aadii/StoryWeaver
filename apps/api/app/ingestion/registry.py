"""Extractor registry: domain code asks for an extractor by URL and never imports a platform module.

Extractors are built lazily (importing this module imports no network client and no yt-dlp).
"""

from collections.abc import Generator
from contextlib import contextmanager

from app.core.errors import InvalidSourceError
from app.ingestion.base import SourceExtractor

_extractors: list[SourceExtractor] | None = None


def _default_extractors() -> list[SourceExtractor]:
    from app.ingestion.youtube import YouTubeExtractor

    return [YouTubeExtractor()]


def extractors() -> list[SourceExtractor]:
    """The registered extractors, in priority order."""
    global _extractors
    if _extractors is None:
        _extractors = _default_extractors()
    return _extractors


def get_extractor(url: str) -> SourceExtractor:
    """First extractor that supports `url`; InvalidSourceError if none does."""
    for extractor in extractors():
        if extractor.supports(url):
            return extractor
    raise InvalidSourceError("no extractor for this URL")


def register_extractor(extractor: SourceExtractor, *, first: bool = False) -> None:
    """Add an extractor (e.g. a future platform). `first=True` gives it priority."""
    items = extractors()
    if first:
        items.insert(0, extractor)
    else:
        items.append(extractor)


@contextmanager
def override_extractors(replacement: list[SourceExtractor]) -> Generator[None]:
    """Temporarily replace the registry (tests inject fakes); always restores the previous list."""
    global _extractors
    previous = _extractors
    _extractors = list(replacement)
    try:
        yield
    finally:
        _extractors = previous
