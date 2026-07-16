from typing import List

from src.domain.search import Search
from src.infrastructure.redis_cache import CacheService
from src.use_cases.search_use_case import SearchUseCase


class SearchService:
    """Orquestra a busca: consulta o cache primeiro; em miss, roda o pipeline
    (use case) e guarda o resultado no cache. Instância única (singleton via
    app.state), então o controller nunca recria services por request."""

    def __init__(self, use_case: SearchUseCase, cache_service: CacheService) -> None:
        self._use_case = use_case
        self._cache = cache_service

    async def search(self, query: str) -> Search:
        cached = await self._cache.get(query)
        if cached is not None:
            return cached

        result = await self._use_case.execute(query)
        await self._cache.set(query, result)
        return result

    async def retrieve(self, query: str) -> List[dict]:
        """Recupera documentos sem gerar resposta (e sem cache miss de LLM)."""
        cached = await self._cache.get(query)
        if cached is not None:
            return cached.results
        return await self._use_case.retrieve(query)
