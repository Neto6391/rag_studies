import json
from pathlib import Path
from typing import List


class CorpusStats:
    """Lê o corpus.jsonl uma única vez e expõe o total e o breakdown por livro
    (para o 'corpus predominante' do dashboard)."""

    def __init__(self, corpus_path: Path) -> None:
        self._breakdown: List[dict] = []
        self._total = 0
        self._load(corpus_path)

    def _load(self, corpus_path: Path) -> None:
        counts: dict[str, int] = {}
        with open(corpus_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                doc = json.loads(line)
                livro = doc.get("metadata", {}).get("livro", "Desconhecido")
                counts[livro] = counts.get(livro, 0) + 1
        self._total = sum(counts.values())
        self._breakdown = sorted(
            ({"name": name, "count": count} for name, count in counts.items()),
            key=lambda item: item["count"],
            reverse=True,
        )

    @property
    def total(self) -> int:
        return self._total

    @property
    def breakdown(self) -> List[dict]:
        return self._breakdown

    @property
    def predominant(self) -> str:
        return self._breakdown[0]["name"] if self._breakdown else "Desconhecido"
