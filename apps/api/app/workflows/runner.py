"""Workflow abstraction. LocalRunner executes in-process; a Temporal runner can replace it
without touching callers. Workflow functions should be idempotent so they are safely retryable."""

import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Protocol

from app.core.logging import get_logger


class WorkflowRunner(Protocol):
    def submit(self, name: str, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> str:
        """Start `fn` in the background; return a workflow_id."""
        ...


class LocalRunner:
    def __init__(self, max_workers: int = 2) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sw-workflow")

    def submit(self, name: str, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> str:
        workflow_id = f"{name}-{uuid.uuid4().hex[:12]}"
        log = get_logger(workflow_id=workflow_id, workflow=name)

        def run() -> Any:
            log.info("workflow.started")
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:  # error boundary: a failed job never takes down the app
                log.error("workflow.failed", status="failed", error=f"{type(exc).__name__}: {exc}")
                raise
            log.info("workflow.finished", status="ok")
            return result

        future: Future[Any] = self._pool.submit(run)
        future.add_done_callback(lambda f: f.exception())  # mark retrieved; already logged
        return workflow_id


class InlineRunner:
    """Runs the workflow immediately, in the caller's thread. For tests and deterministic tooling."""

    def submit(self, name: str, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> str:
        workflow_id = f"{name}-{uuid.uuid4().hex[:12]}"
        log = get_logger(workflow_id=workflow_id, workflow=name)
        try:
            fn(*args, **kwargs)
        except Exception as exc:
            log.error("workflow.failed", status="failed", error=f"{type(exc).__name__}: {exc}")
        return workflow_id


def set_runner(runner: WorkflowRunner | None) -> None:
    """Replace the process-wide runner (None restores the default LocalRunner on next use)."""
    global _runner
    _runner = runner


_runner: WorkflowRunner | None = None


def get_runner() -> WorkflowRunner:
    global _runner
    if _runner is None:
        _runner = LocalRunner()
    return _runner
