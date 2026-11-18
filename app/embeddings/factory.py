"""Build the embedder selected in the settings."""

from app.config import Settings
from app.embeddings.base import Embedder
from app.embeddings.fake import FakeEmbedder
from app.embeddings.voyage import VoyageEmbedder


def get_embedder(settings: Settings) -> Embedder:
    if settings.embedding_provider == "fake":
        return FakeEmbedder(dimensions=settings.embedding_dimensions)
    key = settings.voyage_api_key.get_secret_value() if settings.voyage_api_key else ""
    return VoyageEmbedder(
        api_key=key,
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        batch_size=settings.embedding_batch_size,
    )
