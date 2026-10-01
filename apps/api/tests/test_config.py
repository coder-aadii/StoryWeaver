from pathlib import Path

import pytest

from app.core.config import REPO_ROOT, Settings
from app.models.domain import EMBEDDING_DIM


def _settings(**env: str) -> Settings:
    return Settings(_env_file=None, **env)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_storage_root_means_unset_not_cwd(value: str) -> None:
    assert _settings(storage_root=value).storage_root == REPO_ROOT / "data"  # type: ignore[arg-type]


def test_storage_root_default_and_relative_resolution() -> None:
    assert _settings().storage_root == REPO_ROOT / "data"
    assert _settings(storage_root="var/media").storage_root == REPO_ROOT / "var" / "media"  # type: ignore[arg-type]
    assert _settings(storage_root="/srv/sw").storage_root == Path("/srv/sw")  # type: ignore[arg-type]


def test_storage_root_from_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STORAGE_ROOT", "")
    assert Settings(_env_file=None).storage_root == REPO_ROOT / "data"  # type: ignore[call-arg]


def test_embedding_dimension_setting_matches_the_database_column() -> None:
    """Guard for KI-6: the setting is unused today, but must not silently diverge from the column."""
    assert _settings().embedding_dimensions == EMBEDDING_DIM
