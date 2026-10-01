from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # Lazy: importing the app never opens a database connection.
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        # Fail fast instead of hanging on an unreachable host (Neon may need a few seconds to wake).
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with get_sessionmaker()() as session:
        yield session
