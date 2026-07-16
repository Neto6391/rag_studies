import json
from pathlib import Path
from typing import List, Optional

import numpy as np

from src.services.sentence_transformer_service import SentenceTransformerService


class CorpusVectorStore:
    _instance: Optional["CorpusVectorStore"] = None

    def __init__(self) -> None:
        self._documents: List[dict] = []
        self._embeddings: Optional[np.ndarray] = None

    @classmethod
    def get_instance(cls) -> "CorpusVectorStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load(self, embedding_service: SentenceTransformerService, corpus_path: Path) -> None:
        self._documents = []
        with open(corpus_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self._documents.append(json.loads(line))

        texts = [doc["text"] for doc in self._documents]
        vectors = embedding_service.generate_batch(texts)
        self._embeddings = np.array(vectors)

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[dict]:
        if self._embeddings is None or len(self._documents) == 0:
            return []

        query_vec = np.array(query_embedding)
        scores = self._embeddings @ query_vec
        norms = np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_vec)
        norms[norms == 0] = 1e-10
        cosine_scores = scores / norms

        top_indices = np.argsort(cosine_scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            doc = self._documents[idx]
            results.append({
                "id": doc["id"],
                "title": doc["title"],
                "source": doc["source"],
                "score": float(cosine_scores[idx]),
                "text": doc["text"][:1500],
            })
        return results

    def clear(self) -> None:
        self._documents = []
        self._embeddings = None
