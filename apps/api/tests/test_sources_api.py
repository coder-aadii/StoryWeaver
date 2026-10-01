"""Source Library HTTP API (P1). Needs TEST_DATABASE_URL. Network is never touched: YouTube is faked."""

import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ingestion.registry import override_extractors
from tests.support import FakeYouTube, fixture_bytes

URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
V = "/api/v1"


@pytest.fixture
def yt(api: TestClient) -> Iterator[FakeYouTube]:
    fake = FakeYouTube()
    with override_extractors([fake]):
        yield fake


def upload(api: TestClient, name: str = "simple.srt", title: str = "Volcano talk", **form: str):  # type: ignore[no-untyped-def]
    return api.post(
        f"{V}/sources/from-transcript",
        data={"title": title, **form},
        files={"file": (name, fixture_bytes(name))},
    )


def add_url(api: TestClient, url: str = URL):  # type: ignore[no-untyped-def]
    return api.post(f"{V}/sources/from-url", json={"url": url})


def project(api: TestClient, title: str = "p") -> str:
    return api.post(f"{V}/projects", json={"title": title}).json()["id"]


# ---- add by URL -------------------------------------------------------------------------------
def test_from_url_returns_202_and_the_run_completes(api: TestClient, yt: FakeYouTube) -> None:
    r = add_url(api)
    assert r.status_code == 202
    body = r.json()
    assert body["already_exists"] is False and body["source"]["status"] == "importing"
    run = api.get(f"{V}/runs/{body['run']['id']}").json()
    assert run["status"] == "succeeded" and run["kind"] == "source.add" and run["error"] is None
    detail = api.get(f"{V}/sources/{body['source']['id']}").json()
    assert (
        detail["status"] == "imported"
        and detail["searchable"] is True
        and detail["kind"] == "youtube"
    )
    assert detail["title"] == "Volcanoes explained" and detail["channel_title"] == "Earth Channel"
    assert detail["transcript"]["status"] == "ready" and detail["transcript"]["timed"] is True
    assert detail["thumbnail_url"] and detail["url"] == URL and detail["active_run"] is None


def test_adding_the_same_url_again_is_a_no_op(api: TestClient, yt: FakeYouTube) -> None:
    first = add_url(api).json()
    for variant in (URL, "https://youtu.be/dQw4w9WgXcQ"):
        r = add_url(api, variant)
        assert r.status_code == 200
        body = r.json()
        assert body["already_exists"] is True and body["match"] == "identity"
        assert body["source"]["id"] == first["source"]["id"]
    assert api.get(f"{V}/sources").json()["total"] == 1
    assert yt.extract_calls == 1


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("https://www.youtube.com/@Some/videos", "unsupported_kind"),
        ("https://www.youtube.com/playlist?list=PLabcdefghij123", "unsupported_kind"),
        ("https://evil.example/watch?v=dQw4w9WgXcQ", "invalid_source"),
        ("file:///etc/passwd", "invalid_source"),
        ("https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ", "invalid_source"),
        ("javascript:alert(1)", "invalid_source"),
    ],
)
def test_from_url_rejects_unsupported_and_foreign_urls(
    api: TestClient, yt: FakeYouTube, url: str, code: str
) -> None:
    r = add_url(api, url)
    assert r.status_code == 422 and r.json()["code"] == code
    assert api.get(f"{V}/sources").json()["total"] == 0 and yt.extract_calls == 0


def test_missing_ytdlp_gives_an_actionable_error_and_creates_nothing(api: TestClient) -> None:
    with override_extractors([FakeYouTube("not_installed")]):
        r = add_url(api)
    assert r.status_code == 409 and r.json()["code"] == "provider_not_configured"
    assert "uv sync --extra ingestion" in r.json()["detail"]
    assert api.get(f"{V}/sources").json()["total"] == 0


def test_no_captions_source_is_listed_but_not_searchable_and_offers_a_fallback(
    api: TestClient,
) -> None:
    with override_extractors([FakeYouTube("no_captions")]):
        body = add_url(api).json()
    sid = body["source"]["id"]
    run = api.get(f"{V}/runs/{body['run']['id']}").json()
    assert (
        run["status"] == "failed"
        and run["error"]["code"] == "no_captions"
        and run["error"]["retryable"] is False
    )
    detail = api.get(f"{V}/sources/{sid}").json()
    assert detail["status"] == "imported" and detail["transcript"]["status"] == "failed"
    assert detail["searchable"] is False and "no_captions" in detail["transcript_error"]
    assert [i["id"] for i in api.get(f"{V}/sources").json()["items"]] == [sid]
    failed_tr = api.get(f"{V}/sources/{sid}/transcript").json()  # the failed attempt stays visible
    assert failed_tr["transcript"]["status"] == "failed" and failed_tr["text"] == ""
    assert failed_tr["segments"]["total"] == 0
    assert api.get(f"{V}/sources/{sid}/chunks").json()["total"] == 0
    # the fallback: attach a transcript to the SAME source
    r = api.post(
        f"{V}/sources/{sid}/transcript", files={"file": ("t.srt", fixture_bytes("simple.srt"))}
    )
    assert r.status_code == 200
    fixed = r.json()
    assert (
        fixed["id"] == sid
        and fixed["searchable"] is True
        and fixed["transcript"]["origin"] == "upload"
    )
    assert api.get(f"{V}/sources").json()["total"] == 1


def test_retry_after_a_transient_failure(api: TestClient) -> None:
    fake = FakeYouTube("transient_then_ok")
    with override_extractors([fake]):
        body = add_url(api).json()
        sid = body["source"]["id"]
        first = api.get(f"{V}/runs/{body['run']['id']}").json()
        assert first["status"] == "failed" and first["error"]["retryable"] is True
        r = api.post(f"{V}/sources/{sid}/retry")
        assert r.status_code == 202 and r.json()["run"]["kind"] == "source.fetch_transcript"
        assert api.get(f"{V}/runs/{r.json()['run']['id']}").json()["status"] == "succeeded"
        assert api.get(f"{V}/sources/{sid}").json()["searchable"] is True
        # now healthy: nothing left to retry
        again = api.post(f"{V}/sources/{sid}/retry")
        assert again.status_code == 409 and again.json()["code"] == "nothing_to_retry"
    assert api.post(f"{V}/sources/{uuid.uuid4()}/retry").status_code == 404


# ---- add by transcript upload / paste -----------------------------------------------------------
def test_upload_creates_then_dedupes_across_formats(api: TestClient) -> None:
    a = upload(api, "simple.srt")
    assert a.status_code == 201
    first = a.json()
    assert first["already_exists"] is False and first["source"]["kind"] == "transcript"
    assert first["source"]["searchable"] is True and first["transcript"]["version"] == 1
    for name in ("simple.vtt", "simple.txt"):
        r = upload(api, name, title="Same words again")
        assert r.status_code == 200 and r.json()["already_exists"] is True
        assert (
            r.json()["match"] == "fingerprint" and r.json()["source"]["id"] == first["source"]["id"]
        )
    assert api.get(f"{V}/sources").json()["total"] == 1


def test_pasted_text_works_and_vtt_is_sniffed(api: TestClient) -> None:
    r = api.post(
        f"{V}/sources/from-transcript",
        data={"title": "Pasted", "text": "Hello world. Second sentence here."},
    )
    assert r.status_code == 201 and r.json()["transcript"]["timed"] is False
    vtt = fixture_bytes("simple.vtt").decode()
    r2 = api.post(f"{V}/sources/from-transcript", data={"title": "Pasted vtt", "text": vtt})
    assert r2.status_code == 201 and r2.json()["transcript"]["timed"] is True


def test_changed_transcript_text_becomes_version_two(api: TestClient) -> None:
    sid = upload(api).json()["source"]["id"]
    edited = fixture_bytes("simple.srt").replace(b"volcanoes", b"glaciers")
    r = api.post(f"{V}/sources/{sid}/transcript", files={"file": ("e.srt", edited)})
    assert r.status_code == 200 and r.json()["transcript"]["version"] == 2
    assert api.get(f"{V}/sources/search", params={"q": "glaciers"}).json()["total"] == 1
    assert api.get(f"{V}/sources/search", params={"q": "volcanoes"}).json()["total"] == 0
    same = api.post(f"{V}/sources/{sid}/transcript", files={"file": ("e.srt", edited)})
    assert same.json()["transcript"]["version"] == 2, "identical content is a no-op"


def test_upload_validation_errors(api: TestClient) -> None:
    f = {"file": ("a.srt", fixture_bytes("simple.srt"))}
    assert (
        api.post(f"{V}/sources/from-transcript", data={"title": "t"}).json()["code"]
        == "invalid_input"
    )
    both = api.post(f"{V}/sources/from-transcript", data={"title": "t", "text": "x"}, files=f)
    assert both.status_code == 422 and both.json()["code"] == "invalid_input"
    assert (
        api.post(f"{V}/sources/from-transcript", data={"title": "  ", "text": "hello"}).status_code
        == 422
    )
    assert (
        api.post(f"{V}/sources/from-transcript", data={"text": "hello"}).status_code == 422
    )  # title required
    bad_ext = api.post(
        f"{V}/sources/from-transcript", data={"title": "t"}, files={"file": ("a.exe", b"x")}
    )
    assert bad_ext.status_code == 422 and bad_ext.json()["code"] == "unsupported_file_type"
    ref = api.post(
        f"{V}/sources/from-transcript",
        data={"title": "t", "text": "hi there", "reference_url": "file:///etc/passwd"},
    )
    assert ref.status_code == 422
    assert api.get(f"{V}/sources").json()["total"] == 0


def test_malformed_srt_reports_the_line(api: TestClient) -> None:
    r = api.post(
        f"{V}/sources/from-transcript",
        data={"title": "t"},
        files={"file": ("m.srt", fixture_bytes("malformed.srt"))},
    )
    assert r.status_code == 422 and r.json()["code"] == "transcript_parse_error"
    assert "line" in r.json()["detail"]


def test_oversize_upload_is_413_and_nothing_is_stored(
    api: TestClient, monkeypatch: pytest.MonkeyPatch, storage_root: Path
) -> None:
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "max_transcript_bytes", 50)
    r = api.post(
        f"{V}/sources/from-transcript",
        data={"title": "t"},
        files={"file": ("big.txt", b"word " * 100)},
    )
    assert r.status_code == 413 and r.json()["code"] == "file_too_large"
    assert api.get(f"{V}/sources").json()["total"] == 0
    assert not [p for p in storage_root.rglob("*") if p.is_file()]


def test_non_utf8_and_empty_uploads_are_422(api: TestClient) -> None:
    latin = api.post(
        f"{V}/sources/from-transcript",
        data={"title": "t"},
        files={"file": ("l.txt", "café résumé".encode("latin-1"))},
    )
    assert latin.status_code == 422 and latin.json()["code"] == "transcript_parse_error"
    empty = api.post(
        f"{V}/sources/from-transcript", data={"title": "t"}, files={"file": ("e.txt", b"   \n ")}
    )
    assert empty.status_code == 422


def test_hostile_filenames_never_reach_the_filesystem(api: TestClient, storage_root: Path) -> None:
    for name in ("../../etc/passwd.txt", "..\\..\\evil.txt", "a/b/../../c.txt"):
        r = api.post(
            f"{V}/sources/from-transcript",
            data={"title": name},
            files={"file": (name, b"unique words " + name.encode())},
        )
        assert r.status_code == 201, (name, r.text)
    files = [p for p in storage_root.rglob("*") if p.is_file()]
    assert files and all(p.is_relative_to(storage_root) for p in files)
    assert {p.name for p in files} == {"raw.txt"}, "stored names are generated, never user-supplied"


# ---- list / detail / edit / delete --------------------------------------------------------------
def test_list_filters_and_pagination(api: TestClient, yt: FakeYouTube) -> None:
    add_url(api)
    api.post(
        f"{V}/sources/from-transcript",
        data={"title": "Other", "text": "Completely different words here."},
    )
    assert api.get(f"{V}/sources").json()["total"] == 2
    assert api.get(f"{V}/sources", params={"kind": "youtube"}).json()["total"] == 1
    assert (
        api.get(f"{V}/sources", params={"kind": "transcript"}).json()["items"][0]["platform"]
        == "upload"
    )
    assert api.get(f"{V}/sources", params={"status": "imported"}).json()["total"] == 2
    page = api.get(f"{V}/sources", params={"limit": 1, "offset": 1}).json()
    assert len(page["items"]) == 1 and page["total"] == 2 and page["offset"] == 1
    assert api.get(f"{V}/sources", params={"limit": 0}).status_code == 422
    assert api.get(f"{V}/sources", params={"status": "bogus"}).status_code == 422


def test_detail_404_and_patch_rules(api: TestClient) -> None:
    assert api.get(f"{V}/sources/{uuid.uuid4()}").json()["code"] == "not_found"
    sid = upload(api).json()["source"]["id"]
    ok = api.patch(f"{V}/sources/{sid}", json={"title": "Renamed", "description": "d"})
    assert (
        ok.status_code == 200
        and ok.json()["title"] == "Renamed"
        and ok.json()["description"] == "d"
    )
    assert api.patch(f"{V}/sources/{sid}", json={"description": None}).json()["description"] is None
    assert api.patch(f"{V}/sources/{sid}", json={"title": None}).status_code == 422
    assert api.patch(f"{V}/sources/{sid}", json={"title": "x" * 2000}).status_code == 422
    assert (
        api.patch(f"{V}/sources/{sid}", json={"status": "failed"}).status_code == 422
    )  # not editable
    assert api.patch(f"{V}/sources/{sid}", json={"url": "https://x"}).status_code == 422


def test_delete_removes_source_but_not_when_used(api: TestClient, storage_root: Path) -> None:
    sid = upload(api).json()["source"]["id"]
    pid = project(api)
    assert api.put(f"{V}/projects/{pid}/sources/{sid}").status_code == 200
    blocked = api.delete(f"{V}/sources/{sid}")
    assert blocked.status_code == 409 and blocked.json()["code"] == "source_in_use"
    assert [p for p in storage_root.rglob("*") if p.is_file()]
    assert api.delete(f"{V}/projects/{pid}/sources/{sid}").status_code == 204
    assert api.delete(f"{V}/sources/{sid}").status_code == 204
    assert api.get(f"{V}/sources/{sid}").status_code == 404
    assert not [p for p in storage_root.rglob("*") if p.is_file()]
    assert api.delete(f"{V}/sources/{sid}").status_code == 404


# ---- transcript / chunks -------------------------------------------------------------------------
def test_transcript_and_chunk_paging(api: TestClient) -> None:
    sid = upload(api).json()["source"]["id"]
    body = api.get(f"{V}/sources/{sid}/transcript", params={"limit": 2, "offset": 1}).json()
    assert body["transcript"]["segment_count"] == 4 and body["segments"]["total"] == 4
    assert [s["text"] for s in body["segments"]["items"]] == [
        "Today we talk about volcanoes.",
        "They erupt without warning.",
    ]
    assert body["segments"]["items"][0]["start"] == 3.0 and "Welcome to the show." in body["text"]
    chunks = api.get(f"{V}/sources/{sid}/chunks").json()
    assert (
        chunks["total"] >= 1
        and chunks["items"][0]["chunk_index"] == 0
        and chunks["items"][0]["start_seconds"] == 0.0
    )
    assert api.get(f"{V}/sources/{uuid.uuid4()}/transcript").status_code == 404


def test_the_transcript_collection_is_read_only(api: TestClient) -> None:
    sid = upload(api).json()["source"]["id"]
    tid = api.get(f"{V}/sources/{sid}").json()["transcript"]["id"]
    assert api.get(f"{V}/transcripts/{tid}").status_code == 200
    assert api.delete(f"{V}/transcripts/{tid}").status_code == 405
    assert api.patch(f"{V}/transcripts/{tid}", json={"text": "x"}).status_code == 405


# ---- search ------------------------------------------------------------------------------------------
def test_search_route_is_not_shadowed_by_the_id_route(api: TestClient) -> None:
    r = api.get(f"{V}/sources/search", params={"q": "anything"})
    assert r.status_code == 200 and r.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_search_finds_highlights_and_locates_hits(api: TestClient) -> None:
    sid = upload(api).json()["source"]["id"]
    body = api.get(f"{V}/sources/search", params={"q": "volcanoes"}).json()
    assert body["total"] == 1
    hit = body["items"][0]
    assert hit["source"]["id"] == sid and hit["source"]["searchable"] is True
    assert (
        "<mark>volcanoes</mark>" in hit["snippet"].lower()
        and hit["start_seconds"] == 0.0
        and hit["rank"] > 0
    )
    assert api.get(f"{V}/sources/search", params={"q": "zzzznothing"}).json()["total"] == 0


def test_search_snippets_are_html_safe(api: TestClient) -> None:
    api.post(
        f"{V}/sources/from-transcript",
        data={
            "title": "Hostile",
            "text": "<script>alert(1)</script> volcano <img src=x onerror=alert(2)> eruption",
        },
    )
    snippet = api.get(f"{V}/sources/search", params={"q": "volcano"}).json()["items"][0]["snippet"]
    assert "<script>" not in snippet and "<img" not in snippet and "<mark>volcano</mark>" in snippet
    assert "&lt;img" in snippet, "markup from the transcript is shown as text, never as HTML"


@pytest.mark.parametrize(
    "q",
    [
        '"',
        "a & | b",
        "((",
        "'",
        "-",
        "\\",
        "OR OR",
        "!!!",
        "' OR 1=1 --",
        "; DROP TABLE source_videos;",
    ],
)
def test_search_survives_odd_and_hostile_syntax(api: TestClient, q: str) -> None:
    upload(api)
    assert api.get(f"{V}/sources/search", params={"q": q}).status_code == 200
    assert api.get(f"{V}/sources").json()["total"] == 1


def test_search_parameter_validation(api: TestClient) -> None:
    assert api.get(f"{V}/sources/search").status_code == 422
    assert api.get(f"{V}/sources/search", params={"q": ""}).status_code == 422
    assert api.get(f"{V}/sources/search", params={"q": "x" * 201}).status_code == 422
    assert api.get(f"{V}/sources/search", params={"q": "x", "limit": 51}).status_code == 422


def test_search_can_exclude_used_sources_and_restrict_to_one_source(api: TestClient) -> None:
    a = upload(api, "simple.srt").json()["source"]["id"]
    b = api.post(
        f"{V}/sources/from-transcript",
        data={"title": "B", "text": "Volcanoes facts and more volcanoes facts"},
    ).json()["source"]["id"]
    assert api.get(f"{V}/sources/search", params={"q": "volcanoes"}).json()["total"] == 2
    api.put(f"{V}/projects/{project(api)}/sources/{a}")
    unused = api.get(
        f"{V}/sources/search", params={"q": "volcanoes", "exclude_used": "true"}
    ).json()
    assert [h["source"]["id"] for h in unused["items"]] == [b]
    only_a = api.get(f"{V}/sources/search", params={"q": "volcanoes", "source_id": a}).json()
    assert only_a["total"] == 1 and only_a["items"][0]["source"]["id"] == a
    assert (
        api.get(f"{V}/sources/search", params={"q": "volcanoes", "source_id": b}).json()["total"]
        == 1
    )


# ---- usage / project links ---------------------------------------------------------------------------
def test_project_link_is_idempotent_and_usage_is_visible(api: TestClient) -> None:
    sid = upload(api).json()["source"]["id"]
    pid = project(api, "Ancient volcanoes")
    first = api.put(f"{V}/projects/{pid}/sources/{sid}", json={"role": "primary"})
    second = api.put(f"{V}/projects/{pid}/sources/{sid}", json={"role": "supporting"})
    assert first.status_code == second.status_code == 200
    assert second.json()["role"] == "supporting" and second.json()["source"]["usage_count"] == 1
    assert [u["project_title"] for u in api.get(f"{V}/sources/{sid}/usage").json()] == [
        "Ancient volcanoes"
    ]
    assert len(api.get(f"{V}/projects/{pid}/sources").json()) == 1
    assert api.get(f"{V}/sources", params={"used": "true"}).json()["total"] == 1
    assert api.get(f"{V}/sources", params={"used": "false"}).json()["total"] == 0
    assert api.delete(f"{V}/projects/{pid}/sources/{sid}").status_code == 204
    assert api.delete(f"{V}/projects/{pid}/sources/{sid}").status_code == 204  # idempotent
    assert api.get(f"{V}/sources/{sid}/usage").json() == []


def test_project_link_errors(api: TestClient, yt: FakeYouTube) -> None:
    sid = upload(api).json()["source"]["id"]
    pid = project(api)
    assert api.put(f"{V}/projects/{uuid.uuid4()}/sources/{sid}").status_code == 404
    assert api.put(f"{V}/projects/{pid}/sources/{uuid.uuid4()}").status_code == 404
    assert api.get(f"{V}/projects/{uuid.uuid4()}/sources").status_code == 404
    assert api.get(f"{V}/sources/{uuid.uuid4()}/usage").status_code == 404
    assert api.put(f"{V}/projects/{pid}/sources/{sid}", json={"role": ""}).status_code == 422
    with override_extractors([FakeYouTube("extract_error")]):
        failed = add_url(api, "https://www.youtube.com/watch?v=bbbbbbbbbbb").json()["source"]["id"]
    not_ready = api.put(f"{V}/projects/{pid}/sources/{failed}")
    assert not_ready.status_code == 409 and not_ready.json()["code"] == "source_not_ready"


# ---- runs -------------------------------------------------------------------------------------------------
def test_runs_endpoints(api: TestClient, yt: FakeYouTube) -> None:
    body = add_url(api).json()
    rid, sid = body["run"]["id"], body["source"]["id"]
    assert api.get(f"{V}/runs/{rid}").json()["subject_id"] == sid
    page = api.get(f"{V}/runs", params={"subject_id": sid}).json()
    assert page["total"] == 1 and page["items"][0]["id"] == rid
    assert api.get(f"{V}/runs", params={"subject_id": str(uuid.uuid4())}).json()["total"] == 0
    assert api.get(f"{V}/runs/{uuid.uuid4()}").json()["code"] == "not_found"
    assert api.get(f"{V}/runs", params={"limit": 0}).status_code == 422


def test_attach_is_refused_while_an_import_is_running(api: TestClient) -> None:
    from sqlalchemy.orm import sessionmaker

    from app.db.session import get_engine
    from app.models import SourceVideo
    from app.models.enums import SourceStatus
    from app.workflows.runs import RunService

    with sessionmaker(bind=get_engine(), expire_on_commit=False)() as db:
        src = SourceVideo(
            platform="youtube",
            external_id="busy",
            kind="youtube",
            url="https://www.youtube.com/watch?v=busy0000000",
            title="t",
            status=SourceStatus.IMPORTING,
        )
        db.add(src)
        db.flush()
        RunService(db).start("source.add", "source_video", src.id)
        db.commit()
        sid = str(src.id)
    r = api.post(
        f"{V}/sources/{sid}/transcript", files={"file": ("t.srt", fixture_bytes("simple.srt"))}
    )
    assert r.status_code == 409 and r.json()["code"] == "source_busy"
    # a second retry request returns the active run instead of starting another
    retry = api.post(f"{V}/sources/{sid}/retry").json()["run"]
    assert (
        retry["status"] == "queued"
        and api.get(f"{V}/runs", params={"subject_id": sid}).json()["total"] == 1
    )


def test_openapi_documents_the_new_routes(api: TestClient) -> None:
    paths = api.get("/openapi.json").json()["paths"]
    for path in ("/api/v1/sources/from-url", "/api/v1/sources/from-transcript", "/api/v1/sources/search",
                 "/api/v1/sources/{source_id}", "/api/v1/sources/{source_id}/retry", "/api/v1/runs/{run_id}",
                 "/api/v1/projects/{project_id}/sources/{source_id}"):  # fmt: skip
        assert path in paths, path
    assert "post" not in paths["/api/v1/transcripts"]
