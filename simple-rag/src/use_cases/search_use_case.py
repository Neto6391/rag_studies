import asyncio

from src.domain.embedding import EmbeddingServiceProtocol
from src.domain.llm import LLMServiceProtocol
from src.domain.search import Search
from src.infrastructure.keyword_store import KeywordStore
from src.infrastructure.qdrant_vector_store import QdrantVectorStore
from src.use_cases.pipeline import Pipeline


class SearchUseCase:
    """Pipeline de RAG: retrieve -> generate.

    Cada etapa é um step do pipeline e lê de cima para baixo. As dependências
    são injetadas no construtor (uma vez), não passadas a cada chamada."""

    def __init__(
        self,
        embedding_service: EmbeddingServiceProtocol,
        vector_store: QdrantVectorStore,
        keyword_store: KeywordStore,
        llm_service: LLMServiceProtocol,
        top_k: int = 5,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._keyword_store = keyword_store
        self._llm_service = llm_service
        self._top_k = top_k
        self._pipeline = Pipeline([self._retrieve, self._generate])

    @staticmethod
    def _merge_docs(dense_docs: list[dict], keyword_docs: list[dict], top_k: int) -> list[dict]:
        """União dense ∪ keyword; keyword primeiro (sem reranker, prioriza match lexical)."""
        seen: set[str] = set()
        merged: list[dict] = []
        for doc in keyword_docs + dense_docs:
            if doc["id"] in seen:
                continue
            seen.add(doc["id"])
            merged.append(doc)
        return merged[:top_k]

    async def _retrieve(self, ctx: dict) -> dict:
        query = ctx["query"]
        embedding = await asyncio.to_thread(self._embedding_service.generate, query)
        dense_docs, keyword_docs = await asyncio.gather(
            self._vector_store.search(embedding, top_k=self._top_k),
            asyncio.to_thread(self._keyword_store.search, query),
        )
        ctx["results"] = self._merge_docs(dense_docs, keyword_docs, self._top_k)
        return ctx

    async def _generate(self, ctx: dict) -> dict:
        ctx["answer"] = await self._llm_service.generate(ctx["query"], ctx["results"])
        return ctx

    async def execute(self, query: str) -> Search:
        ctx = await self._pipeline.run({"query": query})
        return Search(results=ctx["results"], response=ctx["answer"])

    async def retrieve(self, query: str) -> list[dict]:
        """Só retrieve — usado para hidratar citações em mensagens antigas."""
        ctx = await self._retrieve({"query": query})
        return ctx["results"]
