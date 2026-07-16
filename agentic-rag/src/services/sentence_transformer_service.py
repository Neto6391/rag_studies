from typing import List

from sentence_transformers import SentenceTransformer

from src.domain.embedding import EmbeddingServiceProtocol

_model_instance: SentenceTransformer | None = None


class SentenceTransformerService(EmbeddingServiceProtocol):
    """Embeddings via sentence-transformers. O modelo é carregado uma única vez
    (singleton de módulo) e reaproveitado por todas as instâncias."""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        global _model_instance
        if _model_instance is None:
            _model_instance = SentenceTransformer(model_name)
        self._model = _model_instance

    def generate(self, text: str) -> List[float]:
        return self._model.encode(text).tolist()

    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        return self._model.encode(texts, show_progress_bar=True).tolist()
