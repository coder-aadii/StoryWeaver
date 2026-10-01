import os
from collections.abc import Iterator
from pathlib import Path

import pytest

# --- Isolate the whole test session from real configuration -------------------------------------
# Environment variables beat the git-ignored .env, so a developer's real DATABASE_URL and API keys
# can never be reached by an accidentally DB-less or provider-calling test. Must run before the
# `app` modules are imported (the app reads settings at import time).
from app.core.config import Settings  # noqa: E402  (imports only settings; no engine is created)

REAL_DATABASE_URL = Settings().database_url
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "")
_UNREACHABLE_DB = "postgresql+psycopg://storyweaver_nodb@127.0.0.1:9/storyweaver_nodb_test"
os.environ["DATABASE_URL"] = TEST_DB_URL or _UNREACHABLE_DB
for _key in (
    "GOOGLE_AI_API_KEY",
    "GROK_API_KEY",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "COMFYUI_BASE_URL",
):
    os.environ[_key] = ""

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from alembic import command  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.session import get_db, get_engine, get_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402
from tests.db_safety import check_test_database_url  # noqa: E402

API_ROOT = Path(__file__).resolve().parents[1]


def reset_app_caches() -> None:
    """Drop cached settings/engine so the next use rebinds to the current environment."""
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


def alembic_config() -> Config:
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    return cfg


@pytest.fixture(scope="session")
def engine() -> Iterator[object]:
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL not set (needs PostgreSQL with pgvector)")
    check_test_database_url(TEST_DB_URL, REAL_DATABASE_URL)  # raises before any DDL
    eng = create_engine(TEST_DB_URL)
    try:
        eng.connect().close()
    except Exception as exc:
        pytest.skip(f"test database unreachable: {type(exc).__name__}")
    reset_app_caches()  # the app's own engine/settings must also point at the test database
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield eng
    reset_app_caches()
    eng.dispose()


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


# --- Source Library fixtures -----------------------------------------------------------------------
@pytest.fixture
def storage_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point LocalStorage at a throwaway directory (nothing is written under the repo's data/)."""
    root = tmp_path / "storage"
    monkeypatch.setenv("STORAGE_ROOT", str(root))
    get_settings.cache_clear()
    return root


@pytest.fixture
def api(engine, db: Session, storage_root: Path) -> Iterator[TestClient]:  # type: ignore[no-untyped-def]
    """A client whose requests each get their own session (like production), background work runs
    inline, and storage is a temp dir. `db` is requested for its TRUNCATE-on-teardown cleanup."""
    from app.workflows.runner import InlineRunner, set_runner

    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def per_request_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = per_request_session
    set_runner(InlineRunner())
    try:
        yield TestClient(app)
    finally:
        set_runner(None)
        app.dependency_overrides.clear()
        get_settings.cache_clear()
