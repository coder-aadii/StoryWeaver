import os
from collections.abc import Iterator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.db.session import get_db
from app.main import app

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "")


@pytest.fixture(scope="session")
def engine():  # type: ignore[no-untyped-def]
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL not set (needs PostgreSQL with pgvector)")
    eng = create_engine(TEST_DB_URL)
    try:
        eng.connect().close()
    except Exception as exc:
        pytest.skip(f"test database unreachable: {type(exc).__name__}")
    # Run the real migrations against the test DB.
    os.environ["DATABASE_URL"] = TEST_DB_URL
    from app.core.config import get_settings

    get_settings.cache_clear()
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    return eng


@pytest.fixture
def db(engine) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        yield session
    with engine.begin() as conn:
        tables = conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                "AND tablename <> 'alembic_version'"
            )
        ).scalars()
        conn.execute(text("TRUNCATE " + ",".join(tables) + " CASCADE"))


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def plain_client() -> TestClient:
    """Client with no database — proves optional infra never blocks the app."""
    return TestClient(app)
