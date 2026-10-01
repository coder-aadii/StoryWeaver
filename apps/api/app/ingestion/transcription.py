"""Speech-to-text interface. faster-whisper is optional and loaded lazily (never at startup)."""

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel

from app.core.errors import ProviderNotConfiguredError
from app.schemas.source import TranscriptSegment


class TranscriptionResult(BaseModel):
    language: str | None
    segments: list[TranscriptSegment]
    # Word-level timestamps / speaker diarisation will extend this model.


class Transcriber(ABC):
    @abstractmethod
    def transcribe(
        self, audio_path: Path, *, language: str | None = None
    ) -> TranscriptionResult: ...


class FasterWhisperTranscriber(Transcriber):
    def __init__(self, model_size: str = "small", compute_type: str = "int8") -> None:
        self.model_size, self.compute_type = model_size, compute_type
        self._model = None  # loaded on first use

    def transcribe(self, audio_path: Path, *, language: str | None = None) -> TranscriptionResult:
        try:
            from faster_whisper import WhisperModel  # pyright: ignore[reportMissingImports]
        except ImportError as exc:
            raise ProviderNotConfiguredError(
                "faster-whisper is not installed; run `uv sync --extra transcription`"
            ) from exc
        if self._model is None:
            self._model = WhisperModel(
                self.model_size, device="cpu", compute_type=self.compute_type
            )
        segs, info = self._model.transcribe(str(audio_path), language=language)  # streams lazily
        return TranscriptionResult(
            language=info.language,
            segments=[
                TranscriptSegment(start=s.start, end=s.end, text=s.text.strip()) for s in segs
            ],
        )
