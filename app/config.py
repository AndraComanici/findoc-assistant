"""Application settings, loaded from environment variables or a local .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
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

    # Embeddings
    embedding_provider: Literal["voyage", "fake"] = "voyage"
    embedding_model: str = "voyage-4"
    embedding_dimensions: int = 1024
    embedding_batch_size: int = 64
    # Client-side limits, so that indexing never exceeds the provider's quota. The defaults
    # match Voyage AI's free trial (no payment method): 3 requests and 10,000 tokens per minute.
    embedding_requests_per_minute: int = 3
    embedding_tokens_per_minute: int = 10_000
    voyage_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
