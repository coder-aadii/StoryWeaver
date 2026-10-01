"""Anthropic Messages-API compatible endpoints (including proxies such as FreeLLMAPI)."""

from app.core.config import get_settings
from app.intelligence.providers.base import LLMProvider, http_client


class ClaudeCompatibleProvider(LLMProvider):
    name = "claude"

    def __init__(self, base_url: str | None = None, api_key: str | None = None) -> None:
        s = get_settings()
        self.base_url = base_url if base_url is not None else s.anthropic_base_url
        self._api_key = api_key if api_key is not None else s.anthropic_api_key

    def is_configured(self) -> bool:
        return bool(self.base_url and self._api_key)

    def _complete(self, prompt, *, system, model, temperature, max_tokens):  # type: ignore[no-untyped-def]
        body: dict[str, object] = {
            "model": model, "max_tokens": max_tokens, "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }  # fmt: skip
        if system:
            body["system"] = system
        headers = {"x-api-key": self._api_key, "anthropic-version": "2023-06-01"}
        with http_client(self.base_url.rstrip("/"), headers) as c:
            r = c.post("/v1/messages", json=body)
            r.raise_for_status()
            d = r.json()
        usage = d.get("usage") or {}
        text = "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
        return text, usage.get("input_tokens"), usage.get("output_tokens")
