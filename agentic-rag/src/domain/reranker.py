from typing import List, Protocol


class RerankerServiceProtocol(Protocol):
    def rerank(self, query: str, documents: List[dict]) -> List[dict]:
        pass
