"""Application settings. Every AI provider is optional; nothing here fails when keys are absent."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "StoryWeaver"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3100",
        "http://127.0.0.1:3100",
    ]

    database_url: str = "postgresql+psycopg://storyweaver:storyweaver@localhost:5433/storyweaver"
    storage_root: Path = REPO_ROOT / "data"
    max_upload_bytes: int = 512 * 1024 * 1024
    llm_timeout_seconds: float = Field(default=120.0, gt=0)
    db_connect_timeout_seconds: int = Field(default=10, ge=1, le=120)

    # Providers (all optional)
    ollama_base_url: str = "http://localhost:11434"
    google_ai_api_key: str = ""
    grok_api_key: str = ""
    openrouter_api_key: str = ""
    anthropic_base_url: str = ""
    anthropic_api_key: str = ""
    comfyui_base_url: str = ""
    temporal_address: str = ""

    # Model selection — never hard-code model names in business logic.
    default_llm_provider: str = "ollama"
    default_llm_model: str = ""
    analysis_llm_model: str = ""
    story_llm_model: str = ""
    script_llm_model: str = ""
    classification_llm_model: str = ""
    embedding_provider: str = "ollama"
    embedding_model: str = ""
    embedding_dimensions: int = Field(default=768, ge=1)

    @field_validator("storage_root", mode="before")
    @classmethod
    def _storage_root_default(cls, value: object) -> object:
        """An empty value (e.g. `STORAGE_ROOT=` in .env) means "unset", never the working directory.

        Relative paths are resolved against the repository root, not the process CWD.
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return REPO_ROOT / "data"
        path = Path(str(value)).expanduser()
        return path if path.is_absolute() else REPO_ROOT / path

    def model_for(self, task: str) -> str:
        """Model for a task (analysis/story/script/classification), falling back to default."""
        return getattr(self, f"{task}_llm_model", "") or self.default_llm_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
