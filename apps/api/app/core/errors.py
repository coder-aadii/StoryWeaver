class StoryWeaverError(Exception):
    """Base error."""


class ProviderNotConfiguredError(StoryWeaverError):
    """An optional provider was used without being configured."""


class ProviderError(StoryWeaverError):
    """A provider call failed (network, HTTP error, bad response, ...)."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ProviderTimeoutError(ProviderError):
    """The provider did not answer within the configured timeout."""


class ProviderResponseError(ProviderError):
    """The provider answered, but the response was empty, blocked or not in the expected shape."""


class UnsafePathError(StoryWeaverError):
    """A storage key attempted to escape the storage root."""


class InvalidSourceError(StoryWeaverError):
    """A user-supplied URL/source failed validation."""


class FileTooLargeError(StoryWeaverError, ValueError):
    """An upload/stream exceeded the configured size cap. (Also a ValueError for older callers.)"""
