from typing import List, Protocol


class LLMServiceProtocol(Protocol):
    async def generate(self, prompt: str, context: List[dict]) -> str:
        ...

    async def is_grounded(
        self, answer: str, context: List[dict], question: str = ""
    ) -> bool:
        ...
