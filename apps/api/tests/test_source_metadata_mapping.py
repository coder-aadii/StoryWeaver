"""P1-T11: yt-dlp info dict -> NormalizedSource. Uses the recorded real info (tests/fixtures/ytdlp)."""

import copy
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.ingestion.youtube import YouTubeExtractor, entry_to_source
from app.schemas.source import NormalizedSource

INFO: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "ytdlp" / "info_jNQXAC9IVRw.json").read_text()
)


def mapped(**overrides: Any) -> NormalizedSource:
    info = copy.deepcopy(INFO)
    info.update(overrides)
    return entry_to_source(info)


def test_recorded_info_maps_to_the_normalized_fields() -> None:
    s = mapped()
    assert (s.platform, s.kind, s.external_id) == ("youtube", "video", "jNQXAC9IVRw")
    assert s.url == "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    assert s.title == "Me at the zoo" and s.duration_seconds == INFO["duration"]
    assert s.description == INFO.get("description")
    assert s.thumbnail_url and s.thumbnail_url.startswith("https://")
    assert s.channel_title == INFO["channel"]
    assert s.published_at is not None and s.published_at.tzinfo is not None
    assert s.published_at.year == 2005 and s.published_at.month == 4  # upload date in the recording


def test_channel_is_identified_by_the_canonical_id_never_a_handle() -> None:
    s = mapped()
    assert re.fullmatch(r"UC[A-Za-z0-9_-]{22}", s.channel_external_id or "")
    assert s.channel_external_id == INFO["channel_id"]
    assert s.channel_url == f"https://www.youtube.com/channel/{INFO['channel_id']}"
    for bogus in ("@jawed", "channel/UC4QobU6STFB0P71PMvOGN5A", "jawed", "", None, 123):
        m = mapped(channel_id=bogus)
        assert m.channel_external_id is None and m.channel_url is None, bogus


def test_publication_date_prefers_the_timestamp_then_upload_date() -> None:
    assert mapped(timestamp=1114300800, upload_date="20990101").published_at == datetime(
        2005, 4, 24, tzinfo=UTC
    )
    only_date = mapped(timestamp=None, upload_date="20050424")
    assert only_date.published_at == datetime(2005, 4, 24, tzinfo=UTC)
    for bad in (None, "", "2005-04-24", "20051399", "garbage"):
        assert mapped(timestamp=None, upload_date=bad).published_at is None, bad


def test_thumbnail_selection_and_https_only() -> None:
    assert (
        mapped(thumbnail="https://i.ytimg.com/vi/x/maxres.jpg").thumbnail_url
        == "https://i.ytimg.com/vi/x/maxres.jpg"
    )
    fallback = mapped(
        thumbnail=None,
        thumbnails=[
            {"url": "https://i.ytimg.com/small.jpg"},
            {"url": "https://i.ytimg.com/large.jpg"},
        ],
    )
    assert fallback.thumbnail_url == "https://i.ytimg.com/large.jpg", (
        "the last (largest) thumbnail wins"
    )
    assert mapped(thumbnail="http://insecure.example/t.jpg", thumbnails=[]).thumbnail_url is None
    assert mapped(thumbnail=None, thumbnails=[]).thumbnail_url is None


def test_canonical_url_ignores_playlist_and_tracking_parameters() -> None:
    assert mapped(
        webpage_url="https://www.youtube.com/watch?v=jNQXAC9IVRw&list=PLx&si=abc"
    ).url == ("https://www.youtube.com/watch?v=jNQXAC9IVRw")


def test_extras_are_a_small_whitelist_without_urls_or_signed_data() -> None:
    s = mapped()
    allowed = {"view_count", "like_count", "comment_count", "channel_follower_count", "age_limit",
               "availability", "live_status", "uploader_id", "categories", "tags"}  # fmt: skip
    assert set(s.extra) <= allowed and s.extra, "should keep some descriptive fields"
    blob = json.dumps(s.model_dump(mode="json"))
    for forbidden in (
        "signature=",
        "expire=",
        "ipbits",
        "sparams",
        "subtitles",
        "automatic_captions",
        "formats",
    ):
        assert forbidden not in blob, forbidden


def test_extras_are_bounded_and_typed() -> None:
    s = mapped(
        tags=[f"tag{i}" + "x" * 200 for i in range(100)],
        categories=["Film"] * 50,
        view_count={"nested": "dict"},
    )
    assert len(s.extra["tags"]) == 20 and all(len(t) <= 64 for t in s.extra["tags"])
    assert len(s.extra["categories"]) <= 10
    assert "view_count" not in s.extra, "non-scalar values are dropped"


def test_missing_optional_fields_do_not_break_mapping() -> None:
    s = entry_to_source({"id": "jNQXAC9IVRw"})
    assert s.title == "jNQXAC9IVRw" and s.channel_external_id is None and s.thumbnail_url is None
    assert s.duration_seconds is None and s.published_at is None and s.extra == {}


def test_no_transcript_is_attached_by_extract() -> None:
    """extract() is metadata-only; transcripts come from fetch_transcript()."""
    assert mapped().segments == []


def test_list_videos_entries_use_the_same_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeYDL:
        def __enter__(self) -> "FakeYDL":
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def extract_info(self, url: str, download: bool = False) -> dict[str, Any]:
            return {
                "entries": [
                    {"id": "jNQXAC9IVRw", "title": "A", "channel_id": INFO["channel_id"]},
                    None,
                    {"title": "no id"},
                ]
            }

    monkeypatch.setattr(YouTubeExtractor, "_ydl", staticmethod(lambda opts: FakeYDL()))
    out = YouTubeExtractor().list_videos("https://www.youtube.com/@SomeChannel/videos", limit=5)
    assert [(v.external_id, v.url, v.channel_external_id) for v in out] == [
        ("jNQXAC9IVRw", "https://www.youtube.com/watch?v=jNQXAC9IVRw", INFO["channel_id"])
    ]
