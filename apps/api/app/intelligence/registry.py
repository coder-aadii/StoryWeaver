"""Lazy provider registry. Nothing is instantiated, connected or loaded at import/startup."""

from collections.abc import Callable

from app.core.config import get_settings
from app.core.errors import ProviderNotConfiguredError
from app.intelligence.providers.base import EmbeddingProvider, LLMProvider
from app.intelligence.providers.claude_compatible import ClaudeCompatibleProvider
from app.intelligence.providers.google import GoogleProvider
from app.intelligence.providers.grok import grok
from app.intelligence.providers.ollama import OllamaProvider
from app.intelligence.providers.openrouter import openrouter

_LLM: dict[str, Callable[[], LLMProvider]] = {
    "ollama": OllamaProvider,
    "google": GoogleProvider,
    "openrouter": openrouter,
    "grok": grok,
    "claude": ClaudeCompatibleProvider,
}
_EMBEDDING: dict[str, Callable[[], EmbeddingProvider]] = {
    "ollama": OllamaProvider,
    "google": GoogleProvider,
}


def get_llm(name: str | None = None) -> LLMProvider:
    key = name or get_settings().default_llm_provider
    if key not in _LLM:
        raise ProviderNotConfiguredError(f"unknown LLM provider '{key}'")
    return _LLM[key]()


def get_embeddings(name: str | None = None) -> EmbeddingProvider:
    key = name or get_settings().embedding_provider
    if key not in _EMBEDDING:
        raise ProviderNotConfiguredError(f"unknown embedding provider '{key}'")
    return _EMBEDDING[key]()


def llm_status() -> dict[str, bool]:
    """Which LLM providers are configured (never exposes credentials)."""
    return {name: factory().is_configured() for name, factory in _LLM.items()}
