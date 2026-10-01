"""Guard for the destructive test database.

The DB fixtures run `alembic downgrade base` and TRUNCATE every table, so they must never be
pointed at a real database. This module holds the (pure, DB-free) decision logic.
"""

import os

from sqlalchemy.engine import make_url

ALLOW_ENV = "STORYWEAVER_ALLOW_DESTRUCTIVE_TESTS"


class UnsafeTestDatabaseError(RuntimeError):
    """TEST_DATABASE_URL looks like a database that must not be wiped."""


def _identity(url: str) -> tuple[str | None, str | None, int | None, str | None, str | None]:
    """(user, host, port, database, unix-socket-dir) — ignores the driver and other query params."""
    u = make_url(url)
    return (u.username, u.host, u.port, u.database, u.query.get("host") if u.query else None)  # type: ignore[return-value]


def _describe(url: str) -> str:
    u = make_url(url)
    return f"{u.host or u.query.get('host', 'socket')}/{u.database}"  # never includes the password


def check_test_database_url(
    test_url: str, app_url: str | None = None, *, allow_destructive: bool | None = None
) -> None:
    """Raise UnsafeTestDatabaseError unless `test_url` is safe to wipe.

    Safe means: the database name ends in `_test` (unless the explicit override env var is set),
    and it is not the same database as the application's DATABASE_URL.
    """
    if allow_destructive is None:
        allow_destructive = os.environ.get(ALLOW_ENV) == "1"
    name = make_url(test_url).database or ""
    if app_url and _identity(test_url) == _identity(app_url):
        raise UnsafeTestDatabaseError(
            f"TEST_DATABASE_URL points at the application database ({_describe(test_url)}); refusing."
        )
    if not name.endswith("_test") and not allow_destructive:
        raise UnsafeTestDatabaseError(
            f"Test database name '{name}' does not end with '_test' ({_describe(test_url)}). "
            f"The tests drop and recreate every table. Use a disposable '*_test' database, or set "
            f"{ALLOW_ENV}=1 if you are certain."
        )
