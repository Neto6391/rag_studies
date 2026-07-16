from src.use_cases.search_use_case import SearchUseCase
from src.domain.search import Search
from src.services.sentence_transformer_service import EmbeddingServiceProtocol
from src.domain.llm import LLMServiceProtocol


class SearchService:
    def __init__(
        self,
        use_case: SearchUseCase | None = None,
        embedding_service: EmbeddingServiceProtocol | None = None,
        llm_service: LLMServiceProtocol | None = None,
    ) -> None:
        self._use_case = use_case or SearchUseCase()
        self._embedding_service = embedding_service
        self._llm_service = llm_service

    def get_search(self, query: str, embedding_service: EmbeddingServiceProtocol, llm_service: LLMServiceProtocol) -> Search:
        return self._use_case.execute(query, embedding_service, llm_service)

