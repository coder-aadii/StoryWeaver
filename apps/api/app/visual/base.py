"""Image generation interface. Concrete providers are optional; a mock keeps the pipeline testable."""

import struct
import zlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.errors import ProviderError, ProviderNotConfiguredError


class ImageRequest(BaseModel):
    prompt: str
    negative_prompt: str = ""
    width: int = 1344
    height: int = 768
    seed: int | None = None
    # Future: reference_images, character_ids, style_id, lora, controlnet, init_image
    reference_asset_ids: list[str] = []


@dataclass(slots=True)
class ImageResult:
    data: bytes
    mime_type: str = "image/png"
    metadata: dict[str, object] = field(default_factory=dict)


class ImageGenerator(ABC):
    name: str

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def generate(self, request: ImageRequest) -> ImageResult: ...


def _solid_png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    def chunk(tag: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body))

    row = b"\x00" + bytes(rgb) * width
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(row * height))
        + chunk(b"IEND", b"")
    )


class MockImageGenerator(ImageGenerator):
    """Returns a clearly-fake solid placeholder. Never presented as real output."""

    name = "mock"

    def is_configured(self) -> bool:
        return True

    def generate(self, request: ImageRequest) -> ImageResult:
        return ImageResult(_solid_png(64, 36, (40, 44, 62)), metadata={"mock": True})


class ComfyUIProvider(ImageGenerator):
    """ComfyUI client. Workflow submission is implemented in a later phase."""

    name = "comfyui"

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = base_url if base_url is not None else get_settings().comfyui_base_url

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def is_reachable(self) -> bool:
        if not self.is_configured():
            return False
        try:
            return httpx.get(f"{self.base_url}/system_stats", timeout=2.0).is_success
        except httpx.HTTPError:
            return False

    def generate(self, request: ImageRequest) -> ImageResult:
        if not self.is_configured():
            raise ProviderNotConfiguredError("COMFYUI_BASE_URL is not set")
        raise ProviderError("ComfyUI workflow execution is not implemented yet")


def get_image_generator() -> ImageGenerator:
    comfy = ComfyUIProvider()
    return comfy if comfy.is_configured() else MockImageGenerator()
