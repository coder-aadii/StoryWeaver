"""Uniform error responses: `{"detail": <human message>, "code": <stable machine code>}`.

Stable codes let the UI show specific messages without parsing text. Provider and storage failures
never include URLs, headers or bodies in `detail`.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import (
    FileTooLargeError,
    InvalidSourceError,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderResponseError,
    ProviderTimeoutError,
    StoryWeaverError,
    UnsafePathError,
)
from app.core.logging import get_logger


class ApiError(StoryWeaverError):
    """An expected, client-visible failure with an explicit HTTP status and code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code, self.code, self.message = status_code, code, message


# Most specific first; the first isinstance match wins.
_MAPPING: list[tuple[type[StoryWeaverError], int, str]] = [
    (InvalidSourceError, 422, "invalid_source"),
    (UnsafePathError, 400, "unsafe_path"),
    (FileTooLargeError, 413, "file_too_large"),
    (ProviderNotConfiguredError, 409, "provider_not_configured"),
    (ProviderTimeoutError, 504, "provider_timeout"),
    (ProviderResponseError, 502, "provider_bad_response"),
    (ProviderError, 502, "provider_error"),
]


def _json(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": message, "code": code})


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _json(exc.status_code, exc.code, exc.message)

    @app.exception_handler(StoryWeaverError)
    async def _domain_error(_: Request, exc: StoryWeaverError) -> JSONResponse:
        for cls, status, code in _MAPPING:
            if isinstance(exc, cls):
                return _json(status, code, str(exc))
        get_logger().error("api.unhandled_domain_error", error=type(exc).__name__)
        return _json(500, "internal_error", "internal error")
