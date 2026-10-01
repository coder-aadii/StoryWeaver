"""Structured logging with secret redaction.

Redaction is two-layered: (1) values of keys that *are* secrets, matched by key name — a key is secret
only if its final word is a secret word (so `api_key`, `access_token`, `authorization` are masked, but
`output_tokens`, `max_tokens`, `cache_key`, `monkey` are not); (2) a scrub of secret-shaped *values*
inside any string (known key formats, bearer tokens, credentials in URLs), which also covers free text
such as exception messages. Redaction is best-effort: never log request bodies or prompts at INFO.
"""

import logging
import re
from collections.abc import MutableMapping
from typing import Any

import structlog

_SECRET_KEY = re.compile(
    r"(?:^|[_\-.])(?:"
    r"api[_\-]?key|apikey|secret(?:[_\-]?key)?|private[_\-]?key|password|passwd|pwd|"
    r"authorization|credentials?|bearer|(?:access|auth|refresh|id|session|bot)?[_\-]?token"
    r")$",
    re.IGNORECASE,
)
_SECRET_VALUES = (
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),  # OpenAI/OpenRouter-style
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),  # Google API keys
    re.compile(r"\bAQ\.[A-Za-z0-9_\-]{20,}"),  # Google token-style keys
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),  # GitHub tokens
    re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}"),  # Slack tokens
    re.compile(r"\bSG\.[A-Za-z0-9_\-]{16,}\.[A-Za-z0-9_\-]{16,}"),  # SendGrid
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/\-]{16,}=*"),
)
_URL_CREDENTIALS = re.compile(r"(://[^/\s:@]+:)[^@/\s]+(@)")
MASK = "***"


def is_secret_key(name: str) -> bool:
    return bool(_SECRET_KEY.search(name))


def scrub(text: str) -> str:
    """Mask secret-shaped substrings in free text."""
    text = _URL_CREDENTIALS.sub(rf"\g<1>{MASK}\g<2>", text)
    for pattern in _SECRET_VALUES:
        text = pattern.sub(MASK, text)
    return text


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return scrub(value)
    if isinstance(value, dict):
        return {k: (MASK if is_secret_key(str(k)) else _redact_value(v)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return type(value)(_redact_value(v) for v in value)
    return value


def _redact(_logger: Any, _name: str, event: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    for k in list(event):
        event[k] = MASK if is_secret_key(k) else _redact_value(event[k])
    return event


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            _redact,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
        ),
    )


def get_logger(**ctx: Any) -> Any:
    """Logger bound with workflow context, e.g. workflow_id, project_id, scene_id, provider."""
    return structlog.get_logger().bind(**ctx)
