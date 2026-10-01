"""Provider-independent LLM/embedding interfaces. Business logic depends only on these."""

import json
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.errors import (
    ProviderError,
    ProviderNotConfiguredError,
    ProviderResponseError,
    ProviderTimeoutError,
)
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


@contextmanager
def provider_errors(provider: str) -> Generator[None]:
    """Translate every failure inside a provider call into the ProviderError family.

    Messages carry only the provider name, exception type and HTTP status — never URLs, bodies or
    headers, which could contain credentials.
    """
    try:
        yield
    except ProviderError:
        raise
    except httpx.TimeoutException as exc:
        raise ProviderTimeoutError(f"{provider} request timed out") from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise ProviderError(f"{provider} returned HTTP {status}", status_code=status) from exc
    except httpx.HTTPError as exc:
        raise ProviderError(f"{provider} request failed: {type(exc).__name__}") from exc
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
        # ValueError covers json.JSONDecodeError; the rest cover unexpected response shapes.
        raise ProviderResponseError(
            f"{provider} returned an unexpected response ({type(exc).__name__})"
        ) from exc


class LLMProvider(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def _complete(
        self, prompt: str, *, system: str | None, model: str, temperature: float, max_tokens: int
    ) -> tuple[str, int | None, int | None]:
        """Return (text, input_tokens, output_tokens). May raise anything; generate() wraps it."""

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
            with provider_errors(self.name):
                text, tin, tout = self._complete(
                    prompt,
                    system=system,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if not text.strip():
                    raise ProviderResponseError(f"{self.name} returned an empty completion")
        except ProviderError as exc:
            log.warning("llm.failed", error=type(exc).__name__, status="failed")
            raise
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
        """Ask for JSON matching `schema`; validate; retry with the error on invalid output."""
        instruction = (
            f"{prompt}\n\nRespond with ONLY a JSON object matching this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        last_error = ""
        for _ in range(retries + 1):
            full = (
                instruction if not last_error else f"{instruction}\n\nFix this error: {last_error}"
            )
            try:
                result = self.generate(
                    full,
                    system=system,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return schema.model_validate_json(extract_json(result.text))
            except ProviderResponseError as exc:  # empty / blocked / malformed reply: retry
                last_error = str(exc)[:500]
            except (ValidationError, ValueError) as exc:
                last_error = str(exc)[:500]
        raise ProviderResponseError(
            f"{self.name} did not return valid structured output: {last_error}"
        )


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
    def _embed(self, texts: list[str], *, model: str) -> list[list[float]]:
        """Return one vector per text. May raise anything; embed() wraps it."""

    def embed(self, texts: list[str], *, model: str) -> list[list[float]]:
        if not self.is_configured():
            raise ProviderNotConfiguredError(f"embedding provider '{self.name}' is not configured")
        if not model:
            raise ProviderNotConfiguredError("no embedding model selected (set EMBEDDING_MODEL)")
        with provider_errors(self.name):
            vectors = self._embed(texts, model=model)
            if len(vectors) != len(texts):
                raise ProviderResponseError(
                    f"{self.name} returned {len(vectors)} embeddings for {len(texts)} inputs"
                )
            return vectors


def http_client(base_url: str = "", headers: dict[str, Any] | None = None) -> httpx.Client:
    return httpx.Client(
        base_url=base_url,
        headers=headers or {},
        timeout=httpx.Timeout(get_settings().llm_timeout_seconds),
    )
