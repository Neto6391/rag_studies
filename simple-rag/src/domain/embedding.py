from typing import List, Protocol


class EmbeddingServiceProtocol(Protocol):
    def generate(self, text: str) -> List[float]:
        ...

    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        ...
