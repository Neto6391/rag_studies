from langgraph.graph import StateGraph, END

from src.domain.search import Search
from src.domain.graph_state import GraphState
from src.domain.embedding import EmbeddingServiceProtocol
from src.domain.llm import LLMServiceProtocol
from src.domain.reranker import RerankerServiceProtocol
from src.infrastructure.corpus_vector_store import CorpusVectorStore


class SearchUseCase:
    def __init__(
        self,
        embedding_service: EmbeddingServiceProtocol | None = None,
        llm_service: LLMServiceProtocol | None = None,
        reranker_service: RerankerServiceProtocol | None = None,
    ) -> None:
        self._embedding_service = embedding_service
        self._llm_service = llm_service
        self._reranker_service = reranker_service

    def _retrieve(self, state: GraphState) -> dict:
        query_embedding = self._embedding_service.generate(state["query"])
        store = CorpusVectorStore.get_instance()
        docs = store.search(query_embedding, top_k=10)
        return {"retrieved_docs": docs}

    def _rerank(self, state: GraphState) -> dict:
        docs = self._reranker_service.rerank(state["query"], state["retrieved_docs"])
        return {"reranked_docs": docs}

    def _generate(self, state: GraphState) -> dict:
        answer = self._llm_service.generate(state["query"], state["reranked_docs"])
        return {"answer": answer}

    def _build_graph(self):
        workflow = StateGraph(GraphState)
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("rerank", self._rerank)
        workflow.add_node("generate", self._generate)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "rerank")
        workflow.add_edge("rerank", "generate")
        workflow.add_edge("generate", END)
        return workflow.compile()

    def execute(
        self,
        query: str,
        embedding_service: EmbeddingServiceProtocol,
        llm_service: LLMServiceProtocol,
        reranker_service: RerankerServiceProtocol,
    ) -> Search:
        self._embedding_service = embedding_service
        self._llm_service = llm_service
        self._reranker_service = reranker_service

        graph = self._build_graph()
        result = graph.invoke({"query": query})

        return Search(
            results=result["reranked_docs"],
            response=result["answer"],
        )
