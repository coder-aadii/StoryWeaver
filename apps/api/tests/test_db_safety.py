import os

import pytest

from tests.db_safety import UnsafeTestDatabaseError, check_test_database_url

APP = "postgresql+psycopg://u:p@localhost:5433/storyweaver"


def test_accepts_disposable_test_database() -> None:
    check_test_database_url("postgresql+psycopg://u:p@localhost:5433/storyweaver_test", APP)


@pytest.mark.parametrize(
    "name", ["storyweaver", "neondb", "story_weaver_development", "test", "prod"]
)
def test_rejects_names_not_ending_in_test(name: str) -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="_test"):
        check_test_database_url(f"postgresql+psycopg://u:p@db.example/{name}", APP)


def test_rejects_the_application_database_even_if_named_test() -> None:
    url = "postgresql+psycopg://u:p@localhost:5433/storyweaver_test"
    with pytest.raises(UnsafeTestDatabaseError, match="application database"):
        check_test_database_url(url, url)


def test_same_database_over_a_different_driver_is_still_the_same() -> None:
    with pytest.raises(UnsafeTestDatabaseError):
        check_test_database_url(
            "postgresql://u:p@localhost:5433/x_test",
            "postgresql+psycopg://u:p@localhost:5433/x_test",
        )


def test_unix_socket_urls_are_compared_by_socket_dir() -> None:
    a = "postgresql+psycopg://postgres@/storyweaver_test?host=/tmp/pg"
    check_test_database_url(a, "postgresql+psycopg://postgres@/storyweaver?host=/tmp/pg")
    with pytest.raises(UnsafeTestDatabaseError):
        check_test_database_url(a, a)


def test_explicit_override_allows_unusual_names_but_never_the_app_database() -> None:
    check_test_database_url("postgresql+psycopg://u:p@h/scratch", APP, allow_destructive=True)
    with pytest.raises(UnsafeTestDatabaseError):
        check_test_database_url(APP, APP, allow_destructive=True)


def test_error_message_never_contains_the_password() -> None:
    with pytest.raises(UnsafeTestDatabaseError) as exc:
        check_test_database_url("postgresql+psycopg://user:s3cr3tpw@host/prod", APP)
    assert "s3cr3tpw" not in str(exc.value)


def test_test_session_cannot_reach_real_configuration() -> None:
    """conftest overrides the real DATABASE_URL and provider keys for the whole session."""
    from app.core.config import get_settings

    s = get_settings()
    assert "neon.tech" not in s.database_url
    assert (s.google_ai_api_key, s.openrouter_api_key, s.grok_api_key) == ("", "", "")
    assert os.environ["DATABASE_URL"] != ""
