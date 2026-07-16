from dataclasses import dataclass, field
from typing import List

from src.domain.llm import LLMServiceProtocol
from src.domain.embedding import EmbeddingServiceProtocol
from src.infrastructure.corpus_vector_store import CorpusVectorStore


@dataclass
class Answer:
    question: str
    response: str
    sources: List[dict] = field(default_factory=list)


class AnswerUseCase:
    def execute(
        self,
        question: str,
        embedding_service: EmbeddingServiceProtocol,
        llm_service: LLMServiceProtocol,
        top_k: int = 5,
    ) -> Answer:
        query_embedding = embedding_service.generate(question)
        store = CorpusVectorStore.get_instance()
        results = store.search(query_embedding, top_k=top_k)

        response = llm_service.generate(question, results)

        return Answer(
            question=question,
            response=response,
            sources=results,
        )
