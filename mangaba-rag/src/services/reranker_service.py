from typing import List

from sentence_transformers import CrossEncoder

from src.domain.reranker import RerankerServiceProtocol

_model_instance: CrossEncoder | None = None


class CrossEncoderService(RerankerServiceProtocol):
    """Reordena os documentos recuperados com um cross-encoder. O modelo é
    carregado uma única vez (singleton de módulo)."""

    def __init__(self, model_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1") -> None:
        global _model_instance
        if _model_instance is None:
            _model_instance = CrossEncoder(model_name)
        self._model = _model_instance

    def rerank(self, query: str, documents: List[dict], top_k: int = 5) -> List[dict]:
        if not documents:
            return []

        pairs = [(query, doc["text"]) for doc in documents]
        scores = self._model.predict(pairs)
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        documents.sort(key=lambda d: d["rerank_score"], reverse=True)
        return documents[:top_k]
