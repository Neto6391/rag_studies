import hashlib
import json
from typing import Optional

import redis.asyncio as redis

from src.domain.search import Search


class CacheService:
    """Cache das buscas no Redis, com TTL. Evita re-executar embedding +
    retrieval + LLM para queries repetidas."""

    def __init__(self, url: str, namespace: str, ttl_seconds: int) -> None:
        self._client = redis.from_url(url, decode_responses=True)
        self._namespace = namespace
        self._ttl = ttl_seconds

    def _key(self, query: str) -> str:
        digest = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        return f"{self._namespace}:search:{digest}"

    async def get(self, query: str) -> Optional[Search]:
        raw = await self._client.get(self._key(query))
        if raw is None:
            return None
        data = json.loads(raw)
        return Search(results=data["results"], response=data["response"])

    async def set(self, query: str, result: Search) -> None:
        payload = json.dumps({"results": result.results, "response": result.response})
        await self._client.set(self._key(query), payload, ex=self._ttl)

    async def close(self) -> None:
        await self._client.aclose()
