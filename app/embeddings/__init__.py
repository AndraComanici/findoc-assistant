"""Turn text into vectors so that texts with similar meaning are close to each other."""

from app.embeddings.base import Embedder, cosine_similarity
from app.embeddings.factory import get_embedder

__all__ = ["Embedder", "cosine_similarity", "get_embedder"]
