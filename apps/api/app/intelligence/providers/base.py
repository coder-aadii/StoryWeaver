"""Provider-independent LLM/embedding interfaces. Business logic depends only on these."""

import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.errors import ProviderError, ProviderNotConfiguredError
from app.core.logging import get_logger

T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class LLMResult:
    text: str
    provider: str
    model: str
    duration_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def _complete(
        self, prompt: str, *, system: str | None, model: str, temperature: float, max_tokens: int
    ) -> tuple[str, int | None, int | None]:
        """Return (text, input_tokens, output_tokens)."""

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResult:
        if not self.is_configured():
            raise ProviderNotConfiguredError(f"LLM provider '{self.name}' is not configured")
        if not model:
            raise ProviderNotConfiguredError("no model selected (set DEFAULT_LLM_MODEL)")
        start = time.perf_counter()
        log = get_logger(provider=self.name, model=model)
        try:
            text, tin, tout = self._complete(
                prompt, system=system, model=model, temperature=temperature, max_tokens=max_tokens
            )
        except httpx.HTTPError as exc:
            log.warning("llm.failed", error=type(exc).__name__)
            raise ProviderError(f"{self.name} request failed: {type(exc).__name__}") from exc
        elapsed = time.perf_counter() - start
        log.info("llm.generated", duration=round(elapsed, 3), output_tokens=tout, status="ok")
        return LLMResult(text, self.name, model, elapsed, tin, tout)

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        retries: int = 1,
    ) -> T:
        """Ask for JSON matching `schema`; validate; retry once with the validation error."""
        instruction = (
            f"{prompt}\n\nRespond with ONLY a JSON object matching this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        last_error = ""
        for _ in range(retries + 1):
            full = (
                instruction if not last_error else f"{instruction}\n\nFix this error: {last_error}"
            )
            result = self.generate(
                full, system=system, model=model, temperature=temperature, max_tokens=max_tokens
            )
            try:
                return schema.model_validate_json(extract_json(result.text))
            except (ValidationError, ValueError) as exc:
                last_error = str(exc)[:500]
        raise ProviderError(f"{self.name} did not return valid structured output: {last_error}")


def extract_json(text: str) -> str:
    """Strip code fences / prose around a JSON object."""
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object found in model output")
    return text[start : end + 1]


class EmbeddingProvider(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def embed(self, texts: list[str], *, model: str) -> list[list[float]]: ...


def http_client(base_url: str = "", headers: dict[str, Any] | None = None) -> httpx.Client:
    return httpx.Client(base_url=base_url, headers=headers or {}, timeout=httpx.Timeout(120.0))
