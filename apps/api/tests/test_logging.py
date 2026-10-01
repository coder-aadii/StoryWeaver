import json

import pytest

from app.core.logging import MASK, configure_logging, get_logger, is_secret_key, scrub


@pytest.mark.parametrize(
    "key",
    ["api_key", "OPENROUTER_API_KEY", "x-api-key", "apikey", "authorization", "Authorization", "password",
     "db_password", "secret", "client_secret", "secret_key", "private_key", "token", "access_token",
     "refresh_token", "auth_token", "credentials", "bearer"],
)  # fmt: skip
def test_secret_keys_are_detected(key: str) -> None:
    assert is_secret_key(key)


@pytest.mark.parametrize(
    "key",
    ["output_tokens", "input_tokens", "max_tokens", "tokens", "token_count", "cache_key", "monkey",
     "keyword", "request_hash", "duration", "provider", "model", "status", "workflow_id", "passwords_checked"],
)  # fmt: skip
def test_non_secret_keys_are_not_masked(key: str) -> None:
    assert not is_secret_key(key)


@pytest.mark.parametrize(
    ("text", "leaked"),
    [
        ("call failed with key sk-or-v1-0123456789abcdef0123456789abcdef", "0123456789abcdef"),
        ("AIzaSyA-0123456789abcdefghijklmnop rejected", "0123456789abcdefghij"),
        ("Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123456789", "abcdefghijklmnop"),
        ("connect postgresql://neondb_owner:hunter2hunter2@host/db failed", "hunter2hunter2"),
        ("ghp_abcdefghijklmnopqrstuvwxyz0123456789", "abcdefghijklmnop"),
    ],
)
def test_secret_shaped_values_are_scrubbed(text: str, leaked: str) -> None:
    out = scrub(text)
    assert leaked not in out
    assert MASK in out


def test_scrub_leaves_ordinary_text_alone() -> None:
    text = "scene_001 rendered in 3.2s using gemini-3.6-flash (output_tokens=17)"
    assert scrub(text) == text


def test_logged_events_keep_token_counts_and_mask_secrets(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging("INFO")
    get_logger(provider="google").info(
        "llm.generated",
        output_tokens=5,
        max_tokens=9,
        api_key="abc123",
        error="boom sk-or-v1-0123456789abcdef0123456789abcdef",
        nested={"authorization": "Bearer x", "ok": 1},
    )
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["output_tokens"] == 5 and line["max_tokens"] == 9
    assert line["api_key"] == MASK
    assert "0123456789abcdef" not in line["error"]
    assert line["nested"] == {"authorization": MASK, "ok": 1}
    assert line["provider"] == "google"
