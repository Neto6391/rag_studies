"""Constrói o knowledge graph + treina Node2Vec a partir do corpus Machado."""

from __future__ import annotations

import argparse
import json
import logging
import pickle
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.infrastructure.ner import (  # noqa: E402
    all_person_aliases,
    all_phrase_aliases,
    all_work_aliases,
    _normalize,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("build_graph")

DATA_DIR = ROOT / "data"
CORPUS_PATH = DATA_DIR / "corpus.jsonl"
GRAPH_PATH = DATA_DIR / "knowledge_graph.gpickle"
EDGES_PATH = DATA_DIR / "graph_edges.jsonl"
NODE2VEC_PATH = DATA_DIR / "node2vec.npy"
NODE2VEC_MAP_PATH = DATA_DIR / "node2vec_ids.json"


def _token_find(norm_text: str, token: str) -> bool:
    pattern = re.compile(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])")
    return pattern.search(norm_text) is not None


def _work_id(livro: str) -> str:
    normalized = _normalize(livro)
    known = {
        "dom casmurro": "work:dom-casmurro",
        "memorias postumas de bras cubas": "work:memorias-postumas",
        "quincas borba": "work:quincas-borba",
        "esau e jaco": "work:esau-e-jaco",
        "memorial de aires": "work:memorial-de-aires",
    }
    return known.get(normalized, f"work:{normalized.replace(' ', '-')}")


def load_corpus(path: Path) -> list[dict]:
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def build_graph(docs: list[dict]) -> nx.Graph:
    g = nx.Graph()
    person_aliases = all_person_aliases()
    phrase_aliases = all_phrase_aliases()
    work_aliases = all_work_aliases()

    # Nós WORK canônicos do gazetteer + dos livros do corpus.
    for _, ent in work_aliases:
        g.add_node(ent.id, type="WORK", label=ent.label)
    for _, ent in [(a, e) for a, e in person_aliases]:
        if ent.id not in g:
            g.add_node(ent.id, type="PERSON", label=ent.label)
    for _, ent in phrase_aliases:
        g.add_node(ent.id, type="PHRASE", label=ent.label)

    chapters_by_work: dict[str, list[str]] = defaultdict(list)

    for doc in docs:
        chapter_id = doc["id"]
        meta = doc.get("metadata") or {}
        livro = meta.get("livro", "Desconhecido")
        wid = _work_id(livro)
        if wid not in g:
            g.add_node(wid, type="WORK", label=livro)

        # Texto truncado no nó para retrieve (payload).
        text = doc.get("text", "")
        g.add_node(
            chapter_id,
            type="CHAPTER",
            label=doc.get("title", chapter_id),
            title=doc.get("title", chapter_id),
            source=doc.get("source", "corpus"),
            text=text,
            livro=livro,
        )
        g.add_edge(chapter_id, wid, relation="PART_OF", weight=1.0)
        chapters_by_work[wid].append(chapter_id)

        norm = _normalize(text)
        # PERSON APPEARS_IN
        seen_persons: list[str] = []
        for alias, ent in person_aliases:
            if ent.id not in g:
                g.add_node(ent.id, type="PERSON", label=ent.label)
            if _token_find(norm, alias):
                if g.has_edge(ent.id, chapter_id):
                    g.edges[ent.id, chapter_id]["weight"] += 1.0
                else:
                    g.add_edge(ent.id, chapter_id, relation="APPEARS_IN", weight=1.0)
                if ent.id not in seen_persons:
                    seen_persons.append(ent.id)

        # PHRASE MENTIONS_IN
        for alias, ent in phrase_aliases:
            if _token_find(norm, alias):
                if g.has_edge(ent.id, chapter_id):
                    g.edges[ent.id, chapter_id]["weight"] += 1.0
                else:
                    g.add_edge(ent.id, chapter_id, relation="MENTIONS_IN", weight=2.0)

        # Co-ocorrência de personagens no mesmo capítulo.
        for i, a in enumerate(seen_persons):
            for b in seen_persons[i + 1 :]:
                if g.has_edge(a, b):
                    g.edges[a, b]["weight"] += 1.0
                else:
                    g.add_edge(a, b, relation="CO_OCCURS", weight=1.0)

    # SAME_WORK_AS entre capítulos vizinhos (ordem do corpus) — estrutura leve.
    for wid, chapter_ids in chapters_by_work.items():
        for i in range(len(chapter_ids) - 1):
            a, b = chapter_ids[i], chapter_ids[i + 1]
            if not g.has_edge(a, b):
                g.add_edge(a, b, relation="SAME_WORK_AS", weight=0.5)

    return g


def _alias_transition(graph: nx.Graph, prev: str | None, curr: str, p: float, q: float) -> str:
    """Amostra próximo nó com bias Node2Vec (p=return, q=in-out)."""
    neighbors = list(graph.neighbors(curr))
    if not neighbors:
        return curr
    if prev is None:
        weights = [float(graph.edges[curr, n].get("weight", 1.0)) for n in neighbors]
        return random.choices(neighbors, weights=weights, k=1)[0]

    weights = []
    for nxt in neighbors:
        w = float(graph.edges[curr, nxt].get("weight", 1.0))
        if nxt == prev:
            weights.append(w / p)
        elif graph.has_edge(prev, nxt):
            weights.append(w)
        else:
            weights.append(w / q)
    return random.choices(neighbors, weights=weights, k=1)[0]


def generate_walks(
    graph: nx.Graph,
    num_walks: int,
    walk_length: int,
    p: float,
    q: float,
) -> list[list[str]]:
    random.seed(42)
    nodes = list(graph.nodes())
    walks: list[list[str]] = []
    for _ in range(num_walks):
        random.shuffle(nodes)
        for start in nodes:
            walk = [start]
            prev = None
            curr = start
            for _ in range(walk_length - 1):
                nxt = _alias_transition(graph, prev, curr, p, q)
                walk.append(nxt)
                prev, curr = curr, nxt
            walks.append(walk)
    return walks


def train_node2vec(
    graph: nx.Graph,
    dimensions: int = 64,
    walk_length: int = 20,
    num_walks: int = 10,
    p: float = 1.0,
    q: float = 0.5,
    window: int = 5,
) -> tuple[np.ndarray, list[str]]:
    """Walks enviesados (Node2Vec) + SVD da matriz de coocorrência (sem gensim)."""
    logger.info(
        "Gerando walks Node2Vec (nodes=%s, walks=%s×%s)...",
        graph.number_of_nodes(),
        num_walks,
        walk_length,
    )
    walks = generate_walks(graph, num_walks, walk_length, p, q)
    ids = list(graph.nodes())
    index = {node_id: i for i, node_id in enumerate(ids)}
    n = len(ids)
    cooc = np.zeros((n, n), dtype=np.float32)

    for walk in walks:
        for i, node in enumerate(walk):
            left = max(0, i - window)
            right = min(len(walk), i + window + 1)
            src = index[node]
            for j in range(left, right):
                if j == i:
                    continue
                dst = index[walk[j]]
                cooc[src, dst] += 1.0

    # PPMI leve + SVD truncado.
    row_sum = cooc.sum(axis=1, keepdims=True)
    col_sum = cooc.sum(axis=0, keepdims=True)
    total = float(cooc.sum()) + 1e-12
    expected = (row_sum @ col_sum) / total
    ppmi = np.log((cooc * total) / np.maximum(expected, 1e-12) + 1e-12)
    ppmi = np.maximum(ppmi, 0.0)

    k = min(dimensions, n - 1)
    logger.info("SVD PPMI → %s dims...", k)
    u, s, _vt = np.linalg.svd(ppmi, full_matrices=False)
    vectors = (u[:, :k] * np.sqrt(s[:k])).astype(np.float32)
    if k < dimensions:
        pad = np.zeros((n, dimensions - k), dtype=np.float32)
        vectors = np.concatenate([vectors, pad], axis=1)
    return vectors, ids


def export_edges(graph: nx.Graph, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for u, v, data in graph.edges(data=True):
            f.write(
                json.dumps(
                    {
                        "source": u,
                        "target": v,
                        "relation": data.get("relation"),
                        "weight": data.get("weight", 1.0),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def build_artifacts(
    dimensions: int = 64,
    walk_length: int = 20,
    num_walks: int = 10,
    p: float = 1.0,
    q: float = 0.5,
    graph_path: Path = GRAPH_PATH,
    edges_path: Path = EDGES_PATH,
    node2vec_path: Path = NODE2VEC_PATH,
    node2vec_map_path: Path = NODE2VEC_MAP_PATH,
) -> None:
    docs = load_corpus(CORPUS_PATH)
    logger.info("Corpus: %s capítulos", len(docs))
    graph = build_graph(docs)
    logger.info(
        "Grafo: %s nós, %s arestas",
        graph.number_of_nodes(),
        graph.number_of_edges(),
    )

    graph_path.parent.mkdir(parents=True, exist_ok=True)
    edges_path.parent.mkdir(parents=True, exist_ok=True)
    node2vec_path.parent.mkdir(parents=True, exist_ok=True)
    node2vec_map_path.parent.mkdir(parents=True, exist_ok=True)
    with open(graph_path, "wb") as f:
        pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)
    export_edges(graph, edges_path)
    logger.info("Salvo %s e %s", graph_path, edges_path)

    vectors, ids = train_node2vec(
        graph,
        dimensions=dimensions,
        walk_length=walk_length,
        num_walks=num_walks,
        p=p,
        q=q,
    )
    np.save(node2vec_path, vectors)
    with open(node2vec_map_path, "w", encoding="utf-8") as f:
        json.dump(ids, f, ensure_ascii=False, indent=2)
    logger.info(
        "Node2Vec salvo: %s (%s×%s)",
        node2vec_path,
        vectors.shape[0],
        vectors.shape[1],
    )

    # Sanity: olhos de ressaca / Capitu
    for probe in ["phrase:olhos-de-ressaca", "person:capitu", "person:bentinho"]:
        if probe in graph:
            chapters = [
                n
                for n in graph.neighbors(probe)
                if graph.nodes[n].get("type") == "CHAPTER"
            ]
            logger.info("%s → %s capítulos (ex: %s)", probe, len(chapters), chapters[:3])


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Machado knowledge graph + Node2Vec")
    parser.add_argument("--dimensions", type=int, default=64)
    parser.add_argument("--walk-length", type=int, default=20)
    parser.add_argument("--num-walks", type=int, default=10)
    parser.add_argument("--p", type=float, default=1.0)
    parser.add_argument("--q", type=float, default=0.5)
    args = parser.parse_args()
    build_artifacts(
        dimensions=args.dimensions,
        walk_length=args.walk_length,
        num_walks=args.num_walks,
        p=args.p,
        q=args.q,
    )


if __name__ == "__main__":
    main()
