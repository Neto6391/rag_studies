from dataclasses import dataclass, field
from typing import List


@dataclass
class DashboardStats:
    corpus_total: int
    predominant_corpus: str
    corpus_breakdown: List[dict] = field(default_factory=list)  # [{"name": str, "count": int}]
    total_messages: int = 0
    total_sessions: int = 0
    hallucination_count: int = 0
