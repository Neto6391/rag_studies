import asyncio

from langgraph.graph import END, StateGraph

from src.domain.embedding import EmbeddingServiceProtocol
from src.domain.graph_state import GraphState
from src.domain.llm import LLMServiceProtocol
from src.domain.reranker import RerankerServiceProtocol
from src.domain.search import Search
from src.infrastructure.keyword_store import KeywordStore
from src.infrastructure.qdrant_vector_store import QdrantVectorStore


class SearchUseCase:
    """Pipeline de RAG orquestrado com LangGraph: retrieve -> rerank -> generate.

    As dependências são injetadas no construtor (uma vez) e o grafo é compilado
    uma única vez. Cada nó é um passo async do StateGraph."""

    def __init__(
        self,
        embedding_service: EmbeddingServiceProtocol,
        vector_store: QdrantVectorStore,
        keyword_store: KeywordStore,
        reranker_service: RerankerServiceProtocol,
        llm_service: LLMServiceProtocol,
        retrieve_top_k: int = 10,
        rerank_top_k: int = 5,
    ) -> None:
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._keyword_store = keyword_store
        self._reranker_service = reranker_service
        self._llm_service = llm_service
        self._retrieve_top_k = retrieve_top_k
        self._rerank_top_k = rerank_top_k
        self._graph = self._build_graph()

    @staticmethod
    def _merge_docs(dense_docs: list[dict], keyword_docs: list[dict]) -> list[dict]:
        """União dense ∪ keyword por id (dense primeiro; keyword só entra se faltar)."""
        merged: dict[str, dict] = {doc["id"]: doc for doc in dense_docs}
        for doc in keyword_docs:
            merged.setdefault(doc["id"], doc)
        return list(merged.values())

    async def _retrieve(self, state: GraphState) -> dict:
        query = state["query"]
        embedding = await asyncio.to_thread(self._embedding_service.generate, query)
        dense_docs, keyword_docs = await asyncio.gather(
            self._vector_store.search(embedding, top_k=self._retrieve_top_k),
            asyncio.to_thread(self._keyword_store.search, query),
        )
        return {"retrieved_docs": self._merge_docs(dense_docs, keyword_docs)}

    async def _rerank(self, state: GraphState) -> dict:
        docs = await asyncio.to_thread(
            self._reranker_service.rerank,
            state["query"],
            state["retrieved_docs"],
            self._rerank_top_k,
        )
        return {"reranked_docs": docs}

    async def _generate(self, state: GraphState) -> dict:
        answer = await self._llm_service.generate(state["query"], state["reranked_docs"])
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

    async def execute(self, query: str) -> Search:
        result = await self._graph.ainvoke({"query": query})
        return Search(results=result["reranked_docs"], response=result["answer"])

    async def retrieve(self, query: str) -> list[dict]:
        """Só retrieve + rerank — usado para hidratar citações em mensagens antigas."""
        embedding = await asyncio.to_thread(self._embedding_service.generate, query)
        dense_docs, keyword_docs = await asyncio.gather(
            self._vector_store.search(embedding, top_k=self._retrieve_top_k),
            asyncio.to_thread(self._keyword_store.search, query),
        )
        merged = self._merge_docs(dense_docs, keyword_docs)
        return await asyncio.to_thread(
            self._reranker_service.rerank,
            query,
            merged,
            self._rerank_top_k,
        )
