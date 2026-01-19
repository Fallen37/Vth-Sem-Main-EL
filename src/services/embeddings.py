"""Embeddings service with support for local and API-based embeddings."""

from typing import Optional
import numpy as np

from config.settings import get_settings


class EmbeddingsService:
    """Generate embeddings using local or API-based models."""
    
    def __init__(self):
        self.settings = get_settings()
        self.model = None
        self._init_model()
    
    def _init_model(self):
        """Initialize embedding model."""
        if self.settings.use_local_embeddings:
            self._init_local_embeddings()
        else:
            self._init_api_embeddings()
    
    def _init_local_embeddings(self):
        """Initialize local sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            model_name = self.settings.embedding_model_name
            self.model = SentenceTransformer(model_name)
            print(f"Loaded local embeddings model: {model_name}")
        except Exception as e:
            print(f"Error loading local embeddings: {e}")
            self.model = None
    
    def _init_api_embeddings(self):
        """Initialize API-based embeddings (OpenAI)."""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.settings.openai_api_key)
            print(f"Initialized OpenAI embeddings: {self.settings.openai_embedding_model}")
        except Exception as e:
            print(f"Error initializing OpenAI embeddings: {e}")
            self.client = None
    
    def embed_text(self, text: str) -> Optional[np.ndarray]:
        """Embed a single text."""
        if not text or not text.strip():
            return None
        
        try:
            if self.settings.use_local_embeddings:
                if self.model is None:
                    return None
                embedding = self.model.encode(text, convert_to_numpy=True)
                return embedding
            else:
                if self.client is None:
                    return None
                response = self.client.embeddings.create(
                    input=text,
                    model=self.settings.openai_embedding_model
                )
                return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            print(f"Error embedding text: {e}")
            return None
    
    def embed_batch(self, texts: list[str]) -> list[Optional[np.ndarray]]:
        """Embed multiple texts."""
        if not texts:
            return []
        
        try:
            if self.settings.use_local_embeddings:
                if self.model is None:
                    return [None] * len(texts)
                embeddings = self.model.encode(texts, convert_to_numpy=True)
                return [emb for emb in embeddings]
            else:
                if self.client is None:
                    return [None] * len(texts)
                response = self.client.embeddings.create(
                    input=texts,
                    model=self.settings.openai_embedding_model
                )
                return [np.array(item.embedding, dtype=np.float32) for item in response.data]
        except Exception as e:
            print(f"Error embedding batch: {e}")
            return [None] * len(texts)
