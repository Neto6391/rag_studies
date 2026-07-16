from typing import List, Protocol


class LLMServiceProtocol(Protocol):
    def generate(self, prompt: str, context: List[dict]) -> str:
        pass
