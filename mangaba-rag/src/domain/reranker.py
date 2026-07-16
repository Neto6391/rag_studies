from typing import List, Protocol


class RerankerServiceProtocol(Protocol):
    def rerank(self, query: str, documents: List[dict], top_k: int = 5) -> List[dict]:
        ...
