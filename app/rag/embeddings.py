import os
from typing import List
from fastembed import TextEmbedding
from app.core.config import settings
from app.core.logging import log_event

# Suppress HuggingFace symlinks warning on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


class EmbeddingService:
    """
    Singleton embedding service using FastEmbed (ONNX runtime).
    Generates 384-dimensional dense vectors locally on CPU in <10ms.
    """
    _instance = None
    _model = None

    @classmethod
    def get_model(cls) -> TextEmbedding:
        if cls._model is None:
            log_event("RETRIEVAL", f"Loading local embedding model: {settings.EMBEDDING_MODEL}")
            cls._model = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
            log_event("RETRIEVAL", "Embedding model loaded and ready.")
        return cls._model

    @classmethod
    def embed_texts(cls, texts: List[str]) -> List[List[float]]:
        """Generates normalized vector embeddings for a list of text strings."""
        if not texts:
            return []
        model = cls.get_model()
        # fastembed returns generator of numpy arrays
        embeddings_gen = model.embed(texts)
        return [arr.tolist() for arr in embeddings_gen]

    @classmethod
    def embed_query(cls, query: str) -> List[float]:
        """Embeds a single search query."""
        results = cls.embed_texts([query])
        return results[0] if results else []
