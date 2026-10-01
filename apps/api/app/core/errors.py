class StoryWeaverError(Exception):
    """Base error."""


class ProviderNotConfiguredError(StoryWeaverError):
    """An optional provider was used without being configured."""


class ProviderError(StoryWeaverError):
    """A provider call failed (network, bad response, ...)."""


class UnsafePathError(StoryWeaverError):
    """A storage key attempted to escape the storage root."""


class InvalidSourceError(StoryWeaverError):
    """A user-supplied URL/source failed validation."""
