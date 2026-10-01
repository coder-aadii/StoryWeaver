from app.core.config import get_settings
from app.intelligence.providers.base import EmbeddingProvider, LLMProvider, http_client

_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GoogleProvider(LLMProvider, EmbeddingProvider):
    name = "google"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else get_settings().google_ai_api_key

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        return {"x-goog-api-key": self._api_key}  # header, never in the URL/logs

    def _complete(self, prompt, *, system, model, temperature, max_tokens):  # type: ignore[no-untyped-def]
        body: dict[str, object] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        with http_client(_BASE, self._headers()) as c:
            r = c.post(f"/models/{model}:generateContent", json=body)
            r.raise_for_status()
            d = r.json()
        parts = d["candidates"][0]["content"]["parts"]
        usage = d.get("usageMetadata") or {}
        return (
            "".join(p.get("text", "") for p in parts),
            usage.get("promptTokenCount"),
            usage.get("candidatesTokenCount"),
        )

    def embed(self, texts: list[str], *, model: str) -> list[list[float]]:
        reqs = [{"model": f"models/{model}", "content": {"parts": [{"text": t}]}} for t in texts]
        with http_client(_BASE, self._headers()) as c:
            r = c.post(f"/models/{model}:batchEmbedContents", json={"requests": reqs})
            r.raise_for_status()
            return [e["values"] for e in r.json()["embeddings"]]
