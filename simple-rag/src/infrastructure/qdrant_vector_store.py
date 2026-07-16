from typing import List

from qdrant_client import AsyncQdrantClient


class QdrantVectorStore:
    """Busca vetorial no Qdrant. Os embeddings ficam persistidos no banco,
    então a aplicação não precisa re-vetorizar o corpus a cada startup."""

    TEXT_PREVIEW_CHARS = 1500

    def __init__(self, url: str, collection: str) -> None:
        self._client = AsyncQdrantClient(url=url)
        self._collection = collection

    async def count(self) -> int:
        if not await self._client.collection_exists(self._collection):
            return 0
        result = await self._client.count(self._collection)
        return result.count

    async def search(self, query_embedding: List[float], top_k: int = 5) -> List[dict]:
        response = await self._client.query_points(
            collection_name=self._collection,
            query=query_embedding,
            limit=top_k,
            with_payload=True,
        )
        results = []
        for point in response.points:
            payload = point.payload or {}
            results.append(
                {
                    "id": payload["id"],
                    "title": payload["title"],
                    "source": payload["source"],
                    "score": float(point.score),
                    "text": payload["text"][: self.TEXT_PREVIEW_CHARS],
                }
            )
        return results

    async def close(self) -> None:
        await self._client.close()
