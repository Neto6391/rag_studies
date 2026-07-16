"""Persistência e consulta do knowledge graph NetworkX."""

from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Any

import networkx as nx

_CAP_NUM_RE = re.compile(r"cap-(\d+)")


class KnowledgeGraphStore:
    """Grafo de entidades/capítulos: PERSON/WORK/PHRASE ↔ CHAPTER."""

    def __init__(self, graph_path: Path) -> None:
        self._path = graph_path
        self._graph: nx.Graph | None = None

    def load(self) -> nx.Graph:
        if self._graph is not None:
            return self._graph
        if not self._path.exists():
            raise FileNotFoundError(
                f"Grafo não encontrado em {self._path}. Rode scripts/build_graph.py"
            )
        with open(self._path, "rb") as f:
            self._graph = pickle.load(f)
        return self._graph

    def save(self, graph: nx.Graph) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "wb") as f:
            pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)
        self._graph = graph

    @property
    def graph(self) -> nx.Graph:
        return self.load()

    def chapter_count(self) -> int:
        g = self.load()
        return sum(1 for _, data in g.nodes(data=True) if data.get("type") == "CHAPTER")

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        g = self.load()
        if node_id not in g:
            return None
        data = dict(g.nodes[node_id])
        data["id"] = node_id
        return data

    def _chapter_doc(self, chapter_id: str, score: float) -> dict:
        data = self.load().nodes[chapter_id]
        return {
            "id": chapter_id,
            "title": data.get("title", chapter_id),
            "source": data.get("source", "graph"),
            "score": float(score),
            "text": data.get("text", ""),
        }

    @staticmethod
    def _chapter_number(chapter_id: str) -> int:
        match = _CAP_NUM_RE.search(chapter_id)
        return int(match.group(1)) if match else 10**9

    def earliest_chapter(self, entity_id: str) -> str | None:
        """Capítulo que INTRODUZ a entidade = o de menor número entre os ligados
        a ela. Para frases (PHRASE), é onde a expressão é apresentada."""
        g = self.load()
        if entity_id not in g:
            return None
        chapters = [
            n for n in g.neighbors(entity_id) if g.nodes[n].get("type") == "CHAPTER"
        ]
        if not chapters:
            return None
        return min(chapters, key=self._chapter_number)

    def chapters_by_ids(self, scored_ids: list[tuple[str, float]], limit: int = 50) -> list[dict]:
        """Documentos de capítulos diretos (ex.: nós CHAPTER vindos do Node2Vec)."""
        g = self.load()
        docs: list[dict] = []
        for chapter_id, score in scored_ids:
            if chapter_id in g and g.nodes[chapter_id].get("type") == "CHAPTER":
                docs.append(self._chapter_doc(chapter_id, score))
            if len(docs) >= limit:
                break
        return docs

    def chapters_for_entities(self, entity_ids: list[str], limit: int = 50) -> list[dict]:
        """Capítulos ligados a entidades via APPEARS_IN / MENTIONS_IN."""
        g = self.load()
        scored: dict[str, float] = {}
        for eid in entity_ids:
            if eid not in g:
                continue
            for neighbor in g.neighbors(eid):
                ndata = g.nodes[neighbor]
                if ndata.get("type") != "CHAPTER":
                    continue
                edge = g.edges[eid, neighbor]
                weight = float(edge.get("weight", 1.0))
                scored[neighbor] = scored.get(neighbor, 0.0) + weight

        ranked = sorted(scored.items(), key=lambda x: x[1], reverse=True)[:limit]
        docs: list[dict] = []
        for chapter_id, score in ranked:
            data = g.nodes[chapter_id]
            docs.append(
                {
                    "id": chapter_id,
                    "title": data.get("title", chapter_id),
                    "source": data.get("source", "graph"),
                    "score": float(score),
                    "text": data.get("text", ""),
                }
            )
        return docs
