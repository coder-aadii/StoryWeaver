from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_exception_handlers
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """On startup, mark work that died with the previous process as interrupted.

    Must never stop the app from booting: the database may be down or still migrating.
    """
    try:
        from app.db.session import get_sessionmaker
        from app.ingestion.service import reconcile_stale

        with get_sessionmaker()() as db:
            counts = reconcile_stale(db)
            db.commit()
        get_logger().info("startup.reconciled", status="ok", **counts)
    except Exception as exc:  # noqa: BLE001
        get_logger().warning(
            "startup.reconcile_skipped", status="skipped", error=type(exc).__name__
        )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="StoryWeaver API",
        description="From source to story to video.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
