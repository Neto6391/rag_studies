from src.domain.search import Search
from src.services.sentence_transformer_service import EmbeddingServiceProtocol
from src.domain.llm import LLMServiceProtocol
from src.infrastructure.corpus_vector_store import CorpusVectorStore


class SearchUseCase:
    def execute(
        self,
        query: str,
        embedding_service: EmbeddingServiceProtocol,
        llm_service: LLMServiceProtocol,
    ) -> Search:
        query_embedding = embedding_service.generate(query)
        store = CorpusVectorStore.get_instance()
        results = store.search(query_embedding, top_k=5)
        response = llm_service.generate(query, results)
        return Search(results=results, response=response)
