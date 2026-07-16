"""Índice Node2Vec: similaridade estrutural entre nós do KG."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class Node2VecIndex:
    """Vetores de nós treinados offline; lookup por cosine similarity."""

    def __init__(self, vectors_path: Path, ids_path: Path) -> None:
        self._vectors_path = vectors_path
        self._ids_path = ids_path
        self._vectors: np.ndarray | None = None
        self._ids: list[str] | None = None
        self._id_to_idx: dict[str, int] | None = None

    def load(self) -> None:
        if self._vectors is not None:
            return
        if not self._vectors_path.exists() or not self._ids_path.exists():
            raise FileNotFoundError(
                f"Node2Vec não encontrado ({self._vectors_path}). Rode scripts/build_graph.py"
            )
        self._vectors = np.load(self._vectors_path)
        with open(self._ids_path, encoding="utf-8") as f:
            self._ids = json.load(f)
        # L2-normaliza para cosine = dot.
        norms = np.linalg.norm(self._vectors, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        self._vectors = self._vectors / norms
        self._id_to_idx = {node_id: i for i, node_id in enumerate(self._ids)}

    def similar_to(self, seed_ids: list[str], top_k: int = 20) -> list[tuple[str, float]]:
        """Vizinhos por média dos seeds no espaço Node2Vec."""
        self.load()
        assert self._vectors is not None and self._ids is not None and self._id_to_idx is not None

        idxs = [self._id_to_idx[sid] for sid in seed_ids if sid in self._id_to_idx]
        if not idxs:
            return []

        query = self._vectors[idxs].mean(axis=0)
        query = query / max(float(np.linalg.norm(query)), 1e-12)
        scores = self._vectors @ query
        # Exclui os próprios seeds.
        seed_set = set(idxs)
        ranked = np.argsort(-scores)
        results: list[tuple[str, float]] = []
        for i in ranked:
            if int(i) in seed_set:
                continue
            results.append((self._ids[int(i)], float(scores[int(i)])))
            if len(results) >= top_k:
                break
        return results

    def save(self, vectors: np.ndarray, ids: list[str]) -> None:
        self._vectors_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(self._vectors_path, vectors)
        with open(self._ids_path, "w", encoding="utf-8") as f:
            json.dump(ids, f, ensure_ascii=False, indent=2)
        self._vectors = None
        self._ids = None
        self._id_to_idx = None
