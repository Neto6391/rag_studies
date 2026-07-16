"""Agentes Mangaba A2A do pipeline GraphRAG.

Um agente `coordinator` orquestra os quatro trabalhadores via REQUEST→RESPONSE:
coordinator → ner → graph → rerank → answer. Os trabalhadores não conversam
entre si; quem conduz o fluxo é sempre o coordinator (A2A honesto e legível).
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Callable

from protocols.a2a import A2AAgent, A2AMessage

from src.domain.llm import LLMServiceProtocol
from src.domain.reranker import RerankerServiceProtocol
from src.infrastructure.knowledge_graph_store import KnowledgeGraphStore
from src.infrastructure.keyword_store import KeywordStore
from src.infrastructure.ner import extract_entities
from src.infrastructure.node2vec_index import Node2VecIndex

_RRF_K = 60


class PipelineAgent(A2AAgent):
    """Agente A2A síncrono. Trabalhadores recebem um `handler`; o coordinator
    não tem handler (só emite requisições e captura respostas)."""

    def __init__(self, agent_id: str, handler: Callable[[dict], Any] | None = None) -> None:
        super().__init__(agent_id)
        self._handler = handler
        self._last_response: dict | None = None

    def handle_request(self, message: A2AMessage) -> None:
        params = message.content.get("params", {})
        try:
            if self._handler is None:
                raise RuntimeError(f"Agente {self.agent_id} não processa requisições")
            result = self._handler(params)
            response = self.a2a_protocol.create_response(message, result, success=True)
        except Exception as exc:
            response = self.a2a_protocol.create_response(
                message, {"error": str(exc)}, success=False
            )
        self.a2a_protocol.send_message(response)

    def handle_response(self, message: A2AMessage) -> None:
        self._last_response = message.content

    def request(self, receiver_id: str, action: str, params: dict) -> Any:
        self._last_response = None
        if not self.send_request(receiver_id, action, params):
            raise RuntimeError(f"Agente A2A não conectado: {receiver_id}")
        if self._last_response is None:
            raise RuntimeError(f"Agente A2A não respondeu: {receiver_id}")
        if not self._last_response.get("success", False):
            result = self._last_response.get("result", {})
            raise RuntimeError(result.get("error", f"Falha no agente {receiver_id}"))
        return self._last_response.get("result")


class A2APipeline:
    """Orquestra o GraphRAG via um agente coordinator sobre quatro trabalhadores."""

    def __init__(
        self,
        graph_store: KnowledgeGraphStore,
        node2vec: Node2VecIndex,
        keyword_store: KeywordStore,
        reranker: RerankerServiceProtocol,
        llm: LLMServiceProtocol,
        retrieve_top_k: int,
        rerank_top_k: int,
        use_rrf: bool = True,
    ) -> None:
        self._retrieve_top_k = retrieve_top_k
        self._rerank_top_k = rerank_top_k
        self._lock = threading.RLock()
        self._llm = llm

        def extract(params: dict) -> dict:
            entities = extract_entities(params["query"])
            return {
                "entities": [
                    {"id": item.id, "label": item.label, "type": item.type}
                    for item in entities
                ]
            }

        def retrieve(params: dict) -> dict:
            query = params["query"]
            entity_ids = [item["id"] for item in params.get("entities", [])]

            direct_docs = graph_store.chapters_for_entities(
                entity_ids, limit=retrieve_top_k * 2
            )


            chapter_hits: list[tuple[str, float]] = []
            entity_hits: list[str] = []
            for node_id, score in node2vec.similar_to(
                entity_ids, top_k=retrieve_top_k * 2
            ):
                if node_id in entity_ids:
                    continue
                if node_id.startswith(("person:", "work:", "phrase:")):
                    entity_hits.append(node_id)
                else:
                    chapter_hits.append((node_id, score))

            neighbor_docs = graph_store.chapters_for_entities(
                entity_hits, limit=retrieve_top_k * 2
            )

            node2vec_docs = graph_store.chapters_by_ids(
                chapter_hits, limit=max(2, retrieve_top_k // 3)
            )

            lexical_docs = keyword_store.search(query, limit=retrieve_top_k)

            merged = {doc["id"]: doc for doc in direct_docs}
            for doc in (*lexical_docs, *neighbor_docs, *node2vec_docs):
                merged.setdefault(doc["id"], doc)
            pool = list(merged.values())[: retrieve_top_k * 3]
            pool_ids = {doc["id"] for doc in pool}

            def _channel(docs: list[dict]) -> list[str]:
                seen: list[str] = []
                for doc in docs:
                    if doc["id"] in pool_ids and doc["id"] not in seen:
                        seen.append(doc["id"])
                return seen

            channels = {
                "entity": _channel(direct_docs),
                "expansion": _channel([*neighbor_docs, *node2vec_docs]),
                "lexical": _channel(lexical_docs),
            }

            anchors: list[str] = []
            for entity_id in entity_ids:
                if not entity_id.startswith("phrase:"):
                    continue
                earliest = graph_store.earliest_chapter(entity_id)
                if earliest and earliest in pool_ids and earliest not in anchors:
                    anchors.append(earliest)

            return {"docs": pool, "channels": channels, "anchors": anchors}

        def rerank(params: dict) -> dict:
            query = params["query"]
            docs = params.get("docs", [])
            if not docs:
                return {"docs": []}

            if use_rrf:
                neural_sorted = reranker.rerank(query, docs, top_k=len(docs))
                channels = dict(params.get("channels", {}))
                channels["neural"] = [doc["id"] for doc in neural_sorted]
                fused: dict[str, float] = {}
                for ranking in channels.values():
                    for rank, doc_id in enumerate(ranking):
                        fused[doc_id] = fused.get(doc_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
                ranked_ids = sorted(fused, key=lambda doc_id: fused[doc_id], reverse=True)
            else:
                ranked_ids = [
                    doc["id"] for doc in reranker.rerank(query, docs, top_k=len(docs))
                ]

            anchors = [a for a in params.get("anchors", []) if a in {d["id"] for d in docs}]
            final_ids = list(dict.fromkeys([*anchors, *ranked_ids]))[:rerank_top_k]

            by_id = {doc["id"]: doc for doc in docs}
            result = []
            for position, doc_id in enumerate(final_ids):
                doc = by_id[doc_id]
                doc["rerank_score"] = float(rerank_top_k - position)
                result.append(doc)
            return {"docs": result}

        def answer(params: dict) -> dict:
            return {"query": params["query"], "docs": params.get("docs", [])}

        self.ner_agent = PipelineAgent("ner_agent", extract)
        self.graph_agent = PipelineAgent("graph_agent", retrieve)
        self.rerank_agent = PipelineAgent("rerank_agent", rerank)
        self.answer_agent = PipelineAgent("answer_agent", answer)

        # Coordinator conduz o fluxo: conecta-se a cada trabalhador.
        self.coordinator = PipelineAgent("coordinator")
        for worker in (self.ner_agent, self.graph_agent, self.rerank_agent, self.answer_agent):
            self.coordinator.connect_to(worker)

    def retrieve(self, query: str) -> list[dict]:
        with self._lock:
            ner_result = self.coordinator.request(
                "ner_agent", "extract", {"query": query}
            )
            graph_result = self.coordinator.request(
                "graph_agent",
                "retrieve",
                {"query": query, "entities": ner_result["entities"]},
            )
            rerank_result = self.coordinator.request(
                "rerank_agent",
                "rerank",
                {
                    "query": query,
                    "docs": graph_result["docs"],
                    "channels": graph_result.get("channels", {}),
                    "anchors": graph_result.get("anchors", []),
                },
            )
            return rerank_result["docs"]

    async def generate(self, query: str, docs: list[dict]) -> str:
        answer_request = await asyncio.to_thread(
            self._prepare_answer, query, docs
        )
        return await self._llm.generate(
            answer_request["query"], answer_request["docs"]
        )

    def _prepare_answer(self, query: str, docs: list[dict]) -> dict:
        with self._lock:
            return self.coordinator.request(
                "answer_agent", "generate", {"query": query, "docs": docs}
            )
