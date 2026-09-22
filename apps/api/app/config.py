from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def project_env_file() -> Path:
    """Find the repository .env locally, while remaining valid inside the worker image."""
    source_path = Path(__file__).resolve()
    for parent in source_path.parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    # Docker supplies settings as environment variables; this is only the safe fallback path.
    return source_path.parents[1] / ".env"


PROJECT_ENV_FILE = project_env_file()
PROJECT_ROOT = PROJECT_ENV_FILE.parent


class Settings(BaseSettings):
    app_name: str = "Codele API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    web_origin: str = "http://localhost:3000"
    admin_origin: str = "http://localhost:5173"
    database_url: str = "postgresql+psycopg://codele:change-me-for-local-only@localhost:5432/codele"
    jwt_secret_key: str = "change-me-before-production-use-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    redis_url: str = "redis://localhost:6379/0"
    execution_timeout_seconds: int = 5
    execution_memory_mb: int = 128
    streak_timezone: str = "Asia/Kolkata"
    upload_dir: Path = PROJECT_ROOT / "uploads"

    # Resolve the repository-level file so `uvicorn app.main:app` works when run from apps/api.
    model_config = SettingsConfigDict(env_file=PROJECT_ENV_FILE, extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [self.web_origin, self.admin_origin]


@lru_cache
def get_settings() -> Settings:
    return Settings()
