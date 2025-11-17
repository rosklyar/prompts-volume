"""Service for generating keyword embeddings using sentence transformers."""

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class KeywordEmbedding:
    """Keyword paired with its embedding vector."""

    keyword: str
    embedding: np.ndarray


class EmbeddingsService:
    """
    Service for generating semantic embeddings from keywords.

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

    def encode_keywords(
        self,
        keywords: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> List[KeywordEmbedding]:
        """
        Generate 384-dimensional embeddings for keywords.

        Args:
            keywords: List of keywords to embed
            batch_size: Batch size for encoding (default: 32, good for CPU)
            show_progress: Show progress bar (default: False)

        Returns:
            List of KeywordEmbedding objects pairing each keyword with its embedding

        Example:
            >>> service = EmbeddingsService()
            >>> keyword_embeddings = service.encode_keywords(["телевізор", "ноутбук"])
            >>> len(keyword_embeddings)
            2
            >>> keyword_embeddings[0].keyword
            'телевізор'
            >>> keyword_embeddings[0].embedding.shape
            (384,)
        """
        embeddings = self.model.encode(
            keywords,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )

        return [
            KeywordEmbedding(keyword=kw, embedding=emb)
            for kw, emb in zip(keywords, embeddings)
        ]


@lru_cache()
def get_embeddings_service() -> EmbeddingsService:
    """
    Get singleton instance of EmbeddingsService.

    Model loads once, subsequent calls reuse the same instance.
    """
    return EmbeddingsService()
