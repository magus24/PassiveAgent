import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Generates sentence embeddings using sentence-transformers.
    
    Uses a multilingual model that supports 50+ languages including
    EN, RU, and UZ in a shared embedding space.
    Model is loaded lazily on first call to avoid startup delay.
    """

    MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM = 384

    def __init__(self):
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.MODEL_NAME}...")
                self._model = SentenceTransformer(self.MODEL_NAME)
                logger.info("Embedding model loaded successfully.")
            except ImportError:
                logger.error(
                    "sentence-transformers not installed. "
                    "Run: pip install sentence-transformers"
                )
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")

    def generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate a 384-dimensional embedding vector for the given text.
        
        Args:
            text: Input text to embed (any language).
            
        Returns:
            List of floats (384 dimensions) or None if model unavailable.
        """
        if not text or not text.strip():
            return None

        self._load_model()
        if self._model is None:
            return None

        try:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None


embedding_engine = EmbeddingEngine()
