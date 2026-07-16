from typing import List, Protocol

class EmbeddingServiceProtocol(Protocol):
    def generate(self, text: str) -> List[float]:
        pass