from src.domain.embedding import EmbeddingServiceProtocol
from sentence_transformers import SentenceTransformer
from typing import List

_model_instance: SentenceTransformer | None = None


class SentenceTransformerService(EmbeddingServiceProtocol):
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        global _model_instance
        if _model_instance is None:
            _model_instance = SentenceTransformer(model_name)
        self._model = _model_instance

    def generate(self, text: str) -> List[float]:
        embedding = self._model.encode(text).tolist()
        return embedding

    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.encode(texts, show_progress_bar=True)
        return embeddings.tolist()