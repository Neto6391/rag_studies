from src.use_cases.search_use_case import SearchUseCase
from src.domain.search import Search
from src.domain.embedding import EmbeddingServiceProtocol
from src.domain.llm import LLMServiceProtocol
from src.domain.reranker import RerankerServiceProtocol


class SearchService:
    def __init__(
        self,
        use_case: SearchUseCase | None = None,
    ) -> None:
        self._use_case = use_case or SearchUseCase()

    def get_search(
        self,
        query: str,
        embedding_service: EmbeddingServiceProtocol,
        llm_service: LLMServiceProtocol,
        reranker_service: RerankerServiceProtocol,
    ) -> Search:
        return self._use_case.execute(query, embedding_service, llm_service, reranker_service)

