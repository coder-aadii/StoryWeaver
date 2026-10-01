from fastapi.testclient import TestClient


def test_liveness_needs_no_database(plain_client: TestClient) -> None:
    r = plain_client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_providers_never_expose_credentials(plain_client: TestClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-super-secret")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        r = plain_client.get("/api/v1/health/providers")
        assert r.status_code == 200
        assert "sk-super-secret" not in r.text
        assert r.json()["llm"]["openrouter"] is True
    finally:
        get_settings.cache_clear()


def test_ready_with_database(client: TestClient) -> None:
    r = client.get("/api/v1/health/ready")
    # engine in this process is lazily bound to DATABASE_URL, set by the engine fixture
    assert r.status_code == 200, r.text
    assert r.json()["pgvector"] is True
