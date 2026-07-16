import asyncio

from src.domain.search import Search
from src.services.a2a_agents import A2APipeline


class SearchUseCase:
    """Caso de uso GraphRAG orquestrado por agentes Mangaba A2A."""

    def __init__(self, pipeline: A2APipeline) -> None:
        self._pipeline = pipeline

    async def execute(self, query: str) -> Search:
        docs = await asyncio.to_thread(self._pipeline.retrieve, query)
        answer = await self._pipeline.generate(query, docs)
        return Search(results=docs, response=answer)

    async def retrieve(self, query: str) -> list[dict]:
        """Só retrieve + rerank — usado para hidratar citações em mensagens antigas."""
        return await asyncio.to_thread(self._pipeline.retrieve, query)
