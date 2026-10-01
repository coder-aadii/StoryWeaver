"""Contract tests every provider adapter must pass. All HTTP is mocked (`httpx.MockTransport`).

This verifies request shape and error handling only. It is NOT evidence that any adapter works
against the live service.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
import pytest

from app.core.errors import (
    ProviderError,
    ProviderNotConfiguredError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from app.intelligence.providers.base import EmbeddingProvider, LLMProvider
from app.intelligence.providers.claude_compatible import ClaudeCompatibleProvider
from app.intelligence.providers.google import GoogleProvider
from app.intelligence.providers.ollama import OllamaProvider
from app.intelligence.providers.openai_compatible import OpenAICompatibleProvider

SECRET = "test-secret-key-0123456789"
Handler = Callable[[httpx.Request], httpx.Response]


@dataclass
class LLMCase:
    id: str
    make: Callable[[], LLMProvider]
    path: str  # expected request path suffix
    auth_header: str | None  # header that must carry the secret (None = no auth)
    ok: dict[str, Any]  # a valid success body for text "hello"


LLM_CASES = [
    LLMCase(
        "ollama",
        lambda: OllamaProvider(base_url="http://ollama.test"),
        "/api/chat",
        None,
        {"message": {"content": "hello"}, "prompt_eval_count": 3, "eval_count": 2},
    ),
    LLMCase(
        "google",
        lambda: GoogleProvider(api_key=SECRET),
        ":generateContent",
        "x-goog-api-key",
        {
            "candidates": [{"content": {"parts": [{"text": "hello"}]}}],
            "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 2},
        },
    ),
    LLMCase(
        "openrouter",
        lambda: OpenAICompatibleProvider("openrouter", "https://openrouter.test/api/v1", SECRET),
        "/chat/completions",
        "authorization",
        {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        },
    ),
    LLMCase(
        "grok",
        lambda: OpenAICompatibleProvider("grok", "https://grok.test/v1", SECRET),
        "/chat/completions",
        "authorization",
        {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        },
    ),
    LLMCase(
        "claude",
        lambda: ClaudeCompatibleProvider(base_url="https://claude.test", api_key=SECRET),
        "/v1/messages",
        "x-api-key",
        {
            "content": [{"type": "text", "text": "hello"}],
            "usage": {"input_tokens": 3, "output_tokens": 2},
        },
    ),
]


@pytest.fixture
def mock_http(monkeypatch: pytest.MonkeyPatch) -> Callable[[Handler], None]:
    real = httpx.Client

    def install(handler: Handler) -> None:
        monkeypatch.setattr(
            httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
        )

    return install


def ids(cases: list[Any]) -> list[str]:
    return [c.id for c in cases]


@pytest.mark.parametrize("case", LLM_CASES, ids=ids(LLM_CASES))
class TestLLMContract:
    def test_success_request_shape_and_parse(self, case: LLMCase, mock_http) -> None:  # type: ignore[no-untyped-def]
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=case.ok)

        mock_http(handler)
        res = case.make().generate("hi", system="be brief", model="m1", max_tokens=16)
        assert (res.text, res.input_tokens, res.output_tokens) == ("hello", 3, 2)
        assert res.provider == case.id and res.model == "m1"
        req = seen[0]
        assert req.method == "POST"
        assert case.path in str(req.url)
        if case.auth_header:
            assert SECRET in req.headers[case.auth_header]
        assert SECRET not in str(req.url), "credentials must never be placed in the URL"

    @pytest.mark.parametrize("status", [400, 401, 429, 500, 503])
    def test_http_errors_become_provider_error_with_status(self, case, mock_http, status) -> None:  # type: ignore[no-untyped-def]
        mock_http(lambda r: httpx.Response(status, text=f"nope {SECRET}"))
        with pytest.raises(ProviderError) as exc:
            case.make().generate("hi", model="m1")
        assert exc.value.status_code == status
        assert SECRET not in str(exc.value)

    def test_timeout_becomes_provider_timeout_error(self, case, mock_http) -> None:  # type: ignore[no-untyped-def]
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("slow", request=request)

        mock_http(handler)
        with pytest.raises(ProviderTimeoutError):
            case.make().generate("hi", model="m1")

    def test_connection_error_becomes_provider_error(self, case, mock_http) -> None:  # type: ignore[no-untyped-def]
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        mock_http(handler)
        with pytest.raises(ProviderError):
            case.make().generate("hi", model="m1")

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"unexpected": True},
            {"choices": []},
            {"candidates": []},
            {"content": []},
            {"message": {}},
        ],
    )
    def test_malformed_200_becomes_response_error_not_a_raw_exception(
        self, case, mock_http, body
    ) -> None:  # type: ignore[no-untyped-def]
        mock_http(lambda r: httpx.Response(200, json=body))
        with pytest.raises(ProviderResponseError):
            case.make().generate("hi", model="m1")

    def test_non_json_200_becomes_response_error(self, case, mock_http) -> None:  # type: ignore[no-untyped-def]
        mock_http(lambda r: httpx.Response(200, text="<html>gateway</html>"))
        with pytest.raises(ProviderResponseError):
            case.make().generate("hi", model="m1")

    def test_missing_model_is_a_configuration_error(self, case) -> None:  # type: ignore[no-untyped-def]
        with pytest.raises(ProviderNotConfiguredError):
            case.make().generate("hi", model="")

    def test_secret_never_appears_in_logs(self, case, mock_http, caplog) -> None:  # type: ignore[no-untyped-def]
        mock_http(lambda r: httpx.Response(500, text=SECRET))
        with caplog.at_level(logging.DEBUG), pytest.raises(ProviderError):
            case.make().generate("hi", model="m1")
        assert SECRET not in caplog.text


def test_google_empty_candidate_from_exhausted_budget_is_a_clear_error(mock_http) -> None:  # type: ignore[no-untyped-def]
    """Regression for KI-3: a 'thinking' model can spend max_tokens and return content without parts."""
    mock_http(
        lambda r: httpx.Response(
            200, json={"candidates": [{"content": {}, "finishReason": "MAX_TOKENS"}]}
        )
    )
    with pytest.raises(ProviderResponseError, match="MAX_TOKENS"):
        GoogleProvider(api_key=SECRET).generate("hi", model="m1", max_tokens=8)


def test_google_safety_block_reports_the_reason(mock_http) -> None:  # type: ignore[no-untyped-def]
    mock_http(lambda r: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}))
    with pytest.raises(ProviderResponseError, match="SAFETY"):
        GoogleProvider(api_key=SECRET).generate("hi", model="m1")


def test_empty_completion_is_a_response_error(mock_http) -> None:  # type: ignore[no-untyped-def]
    mock_http(lambda r: httpx.Response(200, json={"message": {"content": "  "}}))
    with pytest.raises(ProviderResponseError, match="empty"):
        OllamaProvider(base_url="http://ollama.test").generate("hi", model="m1")


def test_generate_structured_retries_after_an_unusable_reply(mock_http) -> None:  # type: ignore[no-untyped-def]
    from pydantic import BaseModel

    class Out(BaseModel):
        title: str

    replies = iter([{"message": {"content": ""}}, {"message": {"content": '{"title": "ok"}'}}])
    mock_http(lambda r: httpx.Response(200, json=next(replies)))
    out = OllamaProvider(base_url="http://ollama.test").generate_structured("x", Out, model="m1")
    assert out.title == "ok"


# --- embeddings -------------------------------------------------------------------------------

EMBED_CASES = [
    LLMCase("ollama", lambda: OllamaProvider(base_url="http://ollama.test"), "/api/embed", None, {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}),  # type: ignore[arg-type]
    LLMCase("google", lambda: GoogleProvider(api_key=SECRET), ":batchEmbedContents", "x-goog-api-key", {"embeddings": [{"values": [0.1, 0.2]}, {"values": [0.3, 0.4]}]}),  # type: ignore[arg-type]
]  # fmt: skip


@pytest.mark.parametrize("case", EMBED_CASES, ids=ids(EMBED_CASES))
class TestEmbeddingContract:
    def test_success(self, case: LLMCase, mock_http) -> None:  # type: ignore[no-untyped-def]
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json=case.ok)

        mock_http(handler)
        provider = case.make()
        assert isinstance(provider, EmbeddingProvider)
        assert provider.embed(["a", "b"], model="e1") == [[0.1, 0.2], [0.3, 0.4]]
        assert case.path in str(seen[0].url)
        if case.auth_header:
            assert SECRET in seen[0].headers[case.auth_header]
        assert SECRET not in str(seen[0].url)

    def test_errors_are_wrapped(self, case, mock_http) -> None:  # type: ignore[no-untyped-def]
        provider: EmbeddingProvider = case.make()  # type: ignore[assignment]
        mock_http(lambda r: httpx.Response(500, text=SECRET))
        with pytest.raises(ProviderError) as exc:
            provider.embed(["a"], model="e1")
        assert SECRET not in str(exc.value)

    def test_malformed_and_count_mismatch(self, case, mock_http) -> None:  # type: ignore[no-untyped-def]
        provider: EmbeddingProvider = case.make()  # type: ignore[assignment]
        mock_http(lambda r: httpx.Response(200, json={}))
        with pytest.raises(ProviderResponseError):
            provider.embed(["a"], model="e1")
        mock_http(lambda r: httpx.Response(200, json=case.ok))
        with pytest.raises(ProviderResponseError, match="embeddings for"):
            provider.embed(["only-one"], model="e1")

    def test_requires_a_model(self, case) -> None:  # type: ignore[no-untyped-def]
        provider: EmbeddingProvider = case.make()  # type: ignore[assignment]
        with pytest.raises(ProviderNotConfiguredError):
            provider.embed(["a"], model="")
