"""Application settings, loaded from environment variables or a local .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://findoc:findoc@localhost:5432/findoc"

    # Ingestion
    sources_file: Path = Path("corpus/sources.yaml")
    data_dir: Path = Path("data/raw")
    migrations_dir: Path = Path("db/migrations")
    chunk_max_words: int = 200
    chunk_overlap_words: int = 40


@lru_cache
def get_settings() -> Settings:
    return Settings()
