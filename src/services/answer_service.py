from src.use_cases.answer_use_case import AnswerUseCase, Answer
from src.domain.llm import LLMServiceProtocol
from src.domain.embedding import EmbeddingServiceProtocol


class AnswerService:
    def __init__(
        self,
        use_case: AnswerUseCase | None = None,
        embedding_service: EmbeddingServiceProtocol | None = None,
        llm_service: LLMServiceProtocol | None = None,
    ) -> None:
        self._use_case = use_case or AnswerUseCase()
        self._embedding_service = embedding_service
        self._llm_service = llm_service

    def get_answer(self, question: str) -> Answer:
        return self._use_case.execute(
            question,
            self._embedding_service,
            self._llm_service,
        )
