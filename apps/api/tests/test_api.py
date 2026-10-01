import uuid

from fastapi.testclient import TestClient


def test_project_crud_roundtrip(client: TestClient) -> None:
    created = client.post("/api/v1/projects", json={"title": "Ice Age Survival"})
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "draft"

    patched = client.patch(f"/api/v1/projects/{body['id']}", json={"status": "scripting"})
    assert patched.json()["status"] == "scripting"
    assert client.get("/api/v1/projects").json()[0]["id"] == body["id"]
    assert client.delete(f"/api/v1/projects/{body['id']}").status_code == 204
    assert client.get(f"/api/v1/projects/{body['id']}").status_code == 404


def test_invalid_status_rejected(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"title": "x"}).json()["id"]
    assert client.patch(f"/api/v1/projects/{pid}", json={"status": "nope"}).status_code == 422


def test_duplicate_source_conflicts(client: TestClient) -> None:
    payload = {"external_id": "dQw4w9WgXcQ", "url": "https://youtu.be/dQw4w9WgXcQ", "title": "t"}
    assert client.post("/api/v1/sources", json=payload).status_code == 201
    assert client.post("/api/v1/sources", json=payload).status_code == 409


def test_bad_foreign_key_is_409_not_500(client: TestClient) -> None:
    r = client.post("/api/v1/scenes", json={"project_id": str(uuid.uuid4()), "sequence": 1})
    assert r.status_code == 409
