from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_engine
from app.intelligence.providers.ollama import OllamaProvider
from app.intelligence.registry import llm_status
from app.visual.base import ComfyUIProvider

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    """Liveness: the process is up. Touches no external dependency."""
    return {"status": "ok", "service": get_settings().app_name}


@router.get("/ready")
def ready(response: Response) -> dict[str, Any]:
    """Readiness: database reachable and pgvector enabled."""
    checks: dict[str, Any] = {"database": False, "pgvector": False}
    error: str | None = None
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
            checks["database"] = True
            checks["pgvector"] = (
                conn.execute(text("SELECT 1 FROM pg_extension WHERE extname='vector'")).first()
                is not None
            )
    except Exception as exc:
        # Type only in the response (no host/user leak); the sanitised message goes to the log.
        error = type(exc).__name__
        get_logger().warning(
            "health.ready.failed", error=error, detail=str(exc)[:200], status="failed"
        )
    ok = all(checks.values())
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    body: dict[str, Any] = {"status": "ready" if ok else "not_ready", **checks}
    if error:
        body["error"] = error
    return body


@router.get("/providers")
def providers() -> dict[str, Any]:
    """Optional-provider configuration/availability. Never returns credentials."""
    s = get_settings()
    return {
        "default_llm_provider": s.default_llm_provider,
        "default_llm_model_set": bool(s.default_llm_model),
        "llm": llm_status(),
        "ollama_reachable": OllamaProvider().is_reachable(),
        "comfyui": {
            "configured": bool(s.comfyui_base_url),
            "reachable": ComfyUIProvider().is_reachable(),
        },
        "temporal_configured": bool(s.temporal_address),
    }
