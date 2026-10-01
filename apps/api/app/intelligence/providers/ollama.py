from app.core.config import get_settings
from app.intelligence.providers.base import EmbeddingProvider, LLMProvider, http_client


class OllamaProvider(LLMProvider, EmbeddingProvider):
    name = "ollama"

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url if base_url is not None else get_settings().ollama_base_url

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _complete(self, prompt, *, system, model, temperature, max_tokens):  # type: ignore[no-untyped-def]
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        body = {
            "model": model, "messages": messages, "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }  # fmt: skip
        with http_client(self.base_url) as c:
            r = c.post("/api/chat", json=body)
            r.raise_for_status()
            d = r.json()
        return d["message"]["content"], d.get("prompt_eval_count"), d.get("eval_count")

    def _embed(self, texts: list[str], *, model: str) -> list[list[float]]:
        with http_client(self.base_url) as c:
            r = c.post("/api/embed", json={"model": model, "input": texts})
            r.raise_for_status()
            return r.json()["embeddings"]

    def is_reachable(self) -> bool:
        try:
            with http_client(self.base_url) as c:
                return c.get("/api/tags", timeout=2.0).is_success
        except Exception:
            return False
