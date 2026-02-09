"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./core.db"

    # Redis (Phase 2)
    redis_url: str = "redis://localhost:6379"

    # Job Board APIs
    ba_api_key: str = "jobboerse-jobsuche"  # Bundesagentur für Arbeit

    # France Travail
    france_travail_client_id: str = ""
    france_travail_client_secret: str = ""

    # USAJobs
    usajobs_api_key: str = ""
    usajobs_email: str = ""

    # Adzuna
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""

    # LLM APIs (Phase 4)
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database."""
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
