from dataclasses import dataclass, field
from typing import List


@dataclass
class EvaluationResult:
    retrieval_accuracy: float
    hallucination_rate: float
    n: int
    details: List[dict] = field(default_factory=list)
