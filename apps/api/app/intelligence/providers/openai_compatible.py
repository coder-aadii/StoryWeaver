"""OpenRouter and Grok (xAI) both speak the OpenAI chat-completions dialect."""

from app.core.config import get_settings
from app.intelligence.providers.base import LLMProvider, http_client


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, name: str, base_url: str, api_key: str) -> None:
        self.name = name
        self.base_url = base_url
        self._api_key = api_key

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _complete(self, prompt, *, system, model, temperature, max_tokens):  # type: ignore[no-untyped-def]
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        body = {"model": model, "messages": messages, "temperature": temperature,
                "max_tokens": max_tokens}  # fmt: skip
        with http_client(self.base_url, {"Authorization": f"Bearer {self._api_key}"}) as c:
            r = c.post("/chat/completions", json=body)
            r.raise_for_status()
            d = r.json()
        usage = d.get("usage") or {}
        return (
            d["choices"][0]["message"]["content"],
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
        )


def openrouter() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        "openrouter", "https://openrouter.ai/api/v1", get_settings().openrouter_api_key
    )


def grok() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider("grok", "https://api.x.ai/v1", get_settings().grok_api_key)
