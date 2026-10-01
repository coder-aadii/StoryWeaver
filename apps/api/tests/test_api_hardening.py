"""P0-T5: PATCH/create validation (KI-4, KI-12), error mapping (KI-8), readiness (KI-5)."""

import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api.errors import ApiError, install_exception_handlers
from app.core.errors import (
    FileTooLargeError,
    InvalidSourceError,
    ProviderError,
    ProviderNotConfiguredError,
    ProviderResponseError,
    ProviderTimeoutError,
    StoryWeaverError,
    UnsafePathError,
)


# ---- schema-level validation: needs no database -----------------------------------------------
@pytest.mark.parametrize("field", ["title", "status"])
def test_patch_null_on_required_field_is_422(plain_client: TestClient, field: str) -> None:
    r = plain_client.patch(f"/api/v1/projects/{uuid.uuid4()}", json={field: None})
    assert r.status_code == 422
    assert "cannot be null" in r.text


def test_patch_over_long_value_is_422_not_500(plain_client: TestClient) -> None:
    r = plain_client.patch(f"/api/v1/projects/{uuid.uuid4()}", json={"title": "x" * 600})
    assert r.status_code == 422


def test_patch_unknown_field_is_422(plain_client: TestClient) -> None:
    assert (
        plain_client.patch(f"/api/v1/projects/{uuid.uuid4()}", json={"nope": 1}).status_code == 422
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example/watch?v=dQw4w9WgXcQ",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
    ],
)
def test_from_url_rejects_non_youtube_urls(plain_client: TestClient, url: str) -> None:
    r = plain_client.post("/api/v1/sources/from-url", json={"url": url})
    assert r.status_code == 422 and r.json()["code"] == "invalid_source"


def test_from_url_rejects_channel_urls_with_a_clear_code(plain_client: TestClient) -> None:
    r = plain_client.post(
        "/api/v1/sources/from-url", json={"url": "https://www.youtube.com/@SomeChannel/videos"}
    )
    assert r.status_code == 422 and r.json()["code"] == "unsupported_kind"
    assert "later release" in r.json()["detail"]


def test_raw_source_and_transcript_write_routes_are_gone(plain_client: TestClient) -> None:
    """KI-12/KI-13: sources and transcripts are only created through the validating service."""
    assert plain_client.post("/api/v1/sources", json={"title": "x"}).status_code == 405
    assert plain_client.post("/api/v1/transcripts", json={}).status_code == 405
    assert plain_client.patch(f"/api/v1/transcripts/{uuid.uuid4()}", json={}).status_code == 405
    assert plain_client.delete(f"/api/v1/transcripts/{uuid.uuid4()}").status_code == 405


def test_create_channel_requires_a_channel_url(plain_client: TestClient) -> None:
    body = {"external_id": "@x", "title": "c", "url": "https://youtu.be/dQw4w9WgXcQ"}
    assert plain_client.post("/api/v1/channels", json=body).status_code == 422


def test_other_platforms_need_http_urls(plain_client: TestClient) -> None:
    body = {"platform": "vimeo", "external_id": "1", "title": "c", "url": "ftp://x/y"}
    assert plain_client.post("/api/v1/channels", json=body).status_code == 422


# ---- exception mapping -------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (InvalidSourceError("bad url"), 422, "invalid_source"),
        (UnsafePathError("escape"), 400, "unsafe_path"),
        (FileTooLargeError("too big"), 413, "file_too_large"),
        (ProviderNotConfiguredError("no key"), 409, "provider_not_configured"),
        (ProviderTimeoutError("slow"), 504, "provider_timeout"),
        (ProviderResponseError("garbage"), 502, "provider_bad_response"),
        (ProviderError("down"), 502, "provider_error"),
        (ApiError(418, "teapot", "short and stout"), 418, "teapot"),
    ],
)
def test_domain_errors_map_to_http_with_stable_codes(
    exc: Exception, status: int, code: str
) -> None:
    from fastapi import FastAPI

    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise exc

    r = TestClient(app).get("/boom")
    assert r.status_code == status
    assert r.json()["code"] == code and isinstance(r.json()["detail"], str)


def test_unknown_domain_error_is_500_without_leaking_details() -> None:
    from fastapi import FastAPI

    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise StoryWeaverError("secret internal detail")

    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500 and "secret" not in r.text and r.json()["code"] == "internal_error"


def test_storage_size_cap_raises_a_typed_error(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import io

    from app.core.config import get_settings
    from app.core.storage import LocalStorage

    get_settings().max_upload_bytes  # noqa: B018  (settings are cached; patch the instance)
    s = get_settings()
    old, s.max_upload_bytes = s.max_upload_bytes, 10
    try:
        with pytest.raises(FileTooLargeError):
            LocalStorage(tmp_path).put("a/b.bin", io.BytesIO(b"x" * 100))
        assert not list(tmp_path.rglob("*.part")), "partial file must be cleaned up"
    finally:
        s.max_upload_bytes = old


# ---- readiness (KI-5) --------------------------------------------------------------------------
@pytest.fixture
def unreachable_database(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """Point the app at a closed port (connection refused) for the duration of one test."""
    from tests.conftest import reset_app_caches

    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://storyweaver_nodb@127.0.0.1:9/storyweaver_nodb_test"
    )
    reset_app_caches()
    yield
    monkeypatch.undo()
    reset_app_caches()


def test_ready_reports_failure_typed_and_logged(
    unreachable_database,
    plain_client: TestClient,
    capsys,  # type: ignore[no-untyped-def]
) -> None:
    r = plain_client.get("/api/v1/health/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "not_ready" and body["database"] is False
    assert body["error"] == "OperationalError"
    assert "127.0.0.1" not in r.text and "storyweaver_nodb" not in r.text, "no host/user leak"
    logged = [
        json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")
    ]
    assert any(e.get("event") == "health.ready.failed" for e in logged)


def test_connect_timeout_is_applied_to_the_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.db.session as session
    from tests.conftest import reset_app_caches

    captured: dict[str, object] = {}

    def fake_create_engine(url: str, **kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setenv("DB_CONNECT_TIMEOUT_SECONDS", "3")
    monkeypatch.setattr(session, "create_engine", fake_create_engine)
    reset_app_caches()
    try:
        session.get_engine()
        assert captured["connect_args"] == {"connect_timeout": 3}
    finally:
        monkeypatch.undo()
        reset_app_caches()


# ---- with a database -----------------------------------------------------------------------------
def test_valid_patch_still_works_and_null_description_clears_it(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"title": "p", "description": "d"}).json()["id"]
    r = client.patch(f"/api/v1/projects/{pid}", json={"description": None, "title": "p2"})
    assert r.status_code == 200 and r.json()["description"] is None and r.json()["title"] == "p2"


def test_error_bodies_are_uniform_for_not_found_and_conflicts(client: TestClient) -> None:
    r = client.get(f"/api/v1/projects/{uuid.uuid4()}")
    assert r.status_code == 404 and r.json() == {
        "detail": "projects not found",
        "code": "not_found",
    }
    channel = {
        "external_id": "UC" + "a" * 22,
        "title": "c",
        "url": "https://www.youtube.com/channel/UC" + "a" * 22,
    }
    assert client.post("/api/v1/channels", json=channel).status_code == 201
    dup = client.post("/api/v1/channels", json=channel)
    assert dup.status_code == 409 and dup.json()["code"] == "duplicate"
    bad_fk = client.post("/api/v1/scenes", json={"project_id": str(uuid.uuid4()), "sequence": 1})
    assert bad_fk.status_code == 409 and bad_fk.json()["code"] == "invalid_reference"
