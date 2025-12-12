"""Service for generating text embeddings using sentence transformers."""

import logging
from dataclasses import dataclass
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class TextWithEmbedding:
    """Text paired with its embedding vector."""

    text: str
    embedding: np.ndarray


class EmbeddingsService:
    """
    Service for generating semantic embeddings from text.

    Uses paraphrase-multilingual-MiniLM-L12-v2 which generates
    384-dimensional vectors for 50+ languages including Ukrainian.
    """

    MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM = 384

    def __init__(self):
        """
        Initialize embeddings service.

        Model (~450MB) downloads on first use to ~/.cache/torch/sentence_transformers/
        """
        logger.info(f"Loading model: {self.MODEL_NAME}")
        self.model = SentenceTransformer(self.MODEL_NAME)
        logger.info(f"Model loaded. Embedding dimension: {self.EMBEDDING_DIM}")

    def encode_texts(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[TextWithEmbedding]:
        """
        Generate 384-dimensional embeddings for texts.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for encoding (default: 32, good for CPU)
            show_progress: Show progress bar (default: False)

        Returns:
            List of TextWithEmbedding objects pairing each text with its embedding

        Example:
            >>> service = EmbeddingsService()
            >>> text_embeddings = service.encode_texts(["телевізор", "ноутбук"])
            >>> len(text_embeddings)
            2
            >>> text_embeddings[0].text
            'телевізор'
            >>> text_embeddings[0].embedding.shape
            (384,)
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )

        return [
            TextWithEmbedding(text=txt, embedding=emb)
            for txt, emb in zip(texts, embeddings)
        ]


# Global instance for dependency injection
_embeddings_service = None


def get_embeddings_service() -> EmbeddingsService:
    """
    Get the global EmbeddingsService instance.
    Creates one if it doesn't exist yet.

    Model (~450MB) loads once on first call, subsequent calls reuse the instance.

    Returns:
        EmbeddingsService instance
    """
    global _embeddings_service
    if _embeddings_service is None:
        _embeddings_service = EmbeddingsService()
    return _embeddings_service
