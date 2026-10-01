"""Text-to-speech interface. Piper / Kokoro / XTTS / cloud providers plug in here later."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.errors import ProviderNotConfiguredError


@dataclass(slots=True)
class VoiceResult:
    data: bytes
    mime_type: str
    duration_seconds: float  # measured by code from the audio, never guessed by an LLM


class VoiceProvider(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def synthesize(self, text: str, *, voice: str | None = None) -> VoiceResult: ...


class UnconfiguredVoiceProvider(VoiceProvider):
    """Default until a real TTS engine is configured; fails loudly instead of faking audio."""

    name = "none"

    def is_configured(self) -> bool:
        return False

    def synthesize(self, text: str, *, voice: str | None = None) -> VoiceResult:
        raise ProviderNotConfiguredError("no voice provider configured")


def get_voice_provider() -> VoiceProvider:
    return UnconfiguredVoiceProvider()
