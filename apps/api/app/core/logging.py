"""Structured logging. Secrets are redacted by key name before anything is emitted."""

import logging
from collections.abc import MutableMapping
from typing import Any

import structlog

_SENSITIVE = ("key", "token", "secret", "password", "authorization", "credential")


def _redact(_logger: Any, _name: str, event: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    for k in list(event):
        if any(s in k.lower() for s in _SENSITIVE):
            event[k] = "***"
    return event


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
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
