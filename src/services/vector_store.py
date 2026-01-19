"""Vector store management using FAISS for local storage."""

import os
import json
from pathlib import Path
from typing import Optional
import numpy as np

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False


class VectorStore:
    """Local vector store using FAISS."""
    
    def __init__(self, embedding_dim: int = 384, persist_dir: str = "data/vector_store"):
        self.embedding_dim = embedding_dim
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_path = self.persist_dir / "faiss.index"
        self.metadata_path = self.persist_dir / "metadata.json"
        
        self.index = None
        self.metadata = {}
        self.chunk_id_counter = 0
        
        self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing index or create new one."""
        if not HAS_FAISS:
            print("Warning: FAISS not installed. Vector store will not work.")
            return
        
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, 'r') as f:
                data = json.load(f)
                self.metadata = data.get('metadata', {})
                self.chunk_id_counter = data.get('chunk_id_counter', 0)
            print(f"Loaded vector store with {self.index.ntotal} vectors")
        else:
            # Create new index
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self._save_index()
            print("Created new vector store")
    
    def add_chunks(self, chunks: list[str], embeddings: list[np.ndarray], metadata: dict) -> list[int]:
        """Add chunks to the vector store."""
        if not HAS_FAISS or self.index is None:
            return []
        
        chunk_ids = []
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Add to FAISS index
        self.index.add(embeddings_array)
        
        # Store metadata
        for i, chunk in enumerate(chunks):
            chunk_id = self.chunk_id_counter
            self.metadata[str(chunk_id)] = {
                'chunk': chunk,
                'metadata': metadata,
                'embedding_index': self.index.ntotal - len(chunks) + i,
            }
            chunk_ids.append(chunk_id)
            self.chunk_id_counter += 1
        
        self._save_index()
        return chunk_ids
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[dict]:
        """Search for similar chunks."""
        if not HAS_FAISS or self.index is None or self.index.ntotal == 0:
            return []
        
        query_embedding = np.array([query_embedding], dtype=np.float32)
        distances, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1:  # Invalid index
                continue
            
            # Find metadata for this index
            for chunk_id, meta in self.metadata.items():
                if meta['embedding_index'] == idx:
                    results.append({
                        'chunk_id': int(chunk_id),
                        'chunk': meta['chunk'],
                        'metadata': meta['metadata'],
                        'distance': float(distance),
                        'similarity': 1 / (1 + float(distance)),  # Convert distance to similarity
                    })
                    break
        
        return results
    
    def _save_index(self):
        """Save index and metadata to disk."""
        if not HAS_FAISS or self.index is None:
            return
        
        faiss.write_index(self.index, str(self.index_path))
        
        with open(self.metadata_path, 'w') as f:
            json.dump({
                'metadata': self.metadata,
                'chunk_id_counter': self.chunk_id_counter,
            }, f)
    
    def clear(self):
        """Clear the vector store."""
        if HAS_FAISS:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.metadata = {}
            self.chunk_id_counter = 0
            self._save_index()
