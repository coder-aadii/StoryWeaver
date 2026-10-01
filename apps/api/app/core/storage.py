"""Storage abstraction. Local filesystem now; S3/MinIO can implement the same protocol later."""

import hashlib
import re
from pathlib import Path
from typing import BinaryIO, Protocol

from app.core.config import get_settings
from app.core.errors import UnsafePathError

BUCKETS = (
    "sources", "transcripts", "embeddings", "images", "audio", "music", "sfx", "projects",
    "renders", "temporary",
)  # fmt: skip
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str) -> str:
    base = Path(name.replace("\\", "/")).name.strip(". ")
    cleaned = _SAFE_NAME.sub("_", base)[:200]
    if not cleaned:
        raise UnsafePathError("empty filename after sanitisation")
    return cleaned


class Storage(Protocol):
    def put(self, key: str, data: BinaryIO) -> tuple[int, str]: ...
    def open(self, key: str) -> BinaryIO: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path_for(self, key: str) -> Path:
        """Resolve a storage key, refusing anything that escapes the root."""
        if not key or key.startswith(("/", "\\")) or "\x00" in key:
            raise UnsafePathError(f"invalid storage key: {key!r}")
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root) or path == self.root:
            raise UnsafePathError(f"storage key escapes root: {key!r}")
        return path

    def put(self, key: str, data: BinaryIO) -> tuple[int, str]:
        """Stream data to disk; returns (size_bytes, sha256). Never loads the file into RAM."""
        path = self.path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        digest, size, limit = hashlib.sha256(), 0, get_settings().max_upload_bytes
        tmp = path.with_suffix(path.suffix + ".part")
        try:
            with tmp.open("wb") as out:
                while chunk := data.read(1024 * 1024):
                    size += len(chunk)
                    if size > limit:
                        raise ValueError(f"file exceeds max size of {limit} bytes")
                    digest.update(chunk)
                    out.write(chunk)
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
        return size, digest.hexdigest()

    def open(self, key: str) -> BinaryIO:
        return self.path_for(key).open("rb")

    def exists(self, key: str) -> bool:
        return self.path_for(key).is_file()

    def delete(self, key: str) -> None:
        self.path_for(key).unlink(missing_ok=True)


def get_storage() -> LocalStorage:
    return LocalStorage(get_settings().storage_root)
