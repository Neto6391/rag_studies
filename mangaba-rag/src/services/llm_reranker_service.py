import logging
import re
from typing import List

import httpx

from src.domain.reranker import RerankerServiceProtocol

logger = logging.getLogger(__name__)

_ID_RE = re.compile(r"machado-[a-z0-9-]+")

_SYSTEM = (
    "Você reordena capítulos de obras de Machado de Assis por relevância a uma "
    "pergunta. Receberá a pergunta e uma lista de candidatos no formato 'id: trecho'. "
    "Se a pergunta for sobre uma expressão, personagem ou conceito, priorize o "
    "capítulo onde ele é APRESENTADO ou EXPLICADO, não os que apenas o repetem "
    "de passagem. Responda APENAS com os ids mais relevantes, um por linha, do "
    "mais para o menos relevante. Não escreva mais nada além dos ids."
)


class LLMReranker(RerankerServiceProtocol):
    """Reordena os candidatos usando um LLM (via OpenRouter). Entende o português
    de 1881 que o cross-encoder erra. Em qualquer falha (rede, créditos, parse),
    cai no reranker de fallback — a busca nunca quebra."""

    def __init__(
        self,
        api_key: str | None,
        model: str,
        fallback: RerankerServiceProtocol,
        base_url: str = "https://openrouter.ai/api/v1",
        snippet_chars: int = 400,
    ) -> None:
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY não definida no .env")
        self._model = model
        self._fallback = fallback
        self._snippet_chars = snippet_chars
        
        self._cache: dict[str, List[str]] = {}
        self._client = httpx.Client(
            base_url=base_url,
            timeout=30,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    def rerank(self, query: str, documents: List[dict], top_k: int = 5) -> List[dict]:
        if not documents:
            return []
        try:
            ordered_ids = self._llm_order(query, documents)
        except Exception:
            logger.exception("LLM-reranker falhou — usando fallback (cross-encoder)")
            return self._fallback.rerank(query, documents, top_k=top_k)

        rank_of = {doc_id: i for i, doc_id in enumerate(ordered_ids)}
        tail = len(documents)
        ranked = sorted(documents, key=lambda doc: rank_of.get(doc["id"], tail))
        for i, doc in enumerate(ranked):
            doc["rerank_score"] = float(len(ranked) - i)
        return ranked[:top_k]

    def _llm_order(self, query: str, documents: List[dict]) -> List[str]:
        cache_key = query + "|" + ",".join(sorted(doc["id"] for doc in documents))
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        candidates = "\n".join(
            f"{doc['id']}: {self._snippet(doc['text'])}" for doc in documents
        )
        payload = {
            "model": self._model,
            "temperature": 0,
            "top_p": 1,
            "seed": 42,
            "max_tokens": 200,
 
            "provider": {"order": ["OpenAI"], "allow_fallbacks": False},
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Pergunta: {query}\n\nCandidatos:\n{candidates}"},
            ],
        }
        response = self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        valid = {doc["id"] for doc in documents}
        ordered: List[str] = []
        for token in _ID_RE.findall(content):
            if token in valid and token not in ordered:
                ordered.append(token)
        if not ordered:
            raise ValueError("LLM não retornou ids válidos")
        self._cache[cache_key] = ordered
        return ordered

    def _snippet(self, text: str) -> str:
        return " ".join(text.split())[: self._snippet_chars]

    def close(self) -> None:
        self._client.close()
