import json
from pathlib import Path

from src.domain.evaluation import EvaluationResult
from src.domain.llm import LLMServiceProtocol
from src.use_cases.search_use_case import SearchUseCase


class EvaluateUseCase:
    """Roda um gold set pequeno pelo pipeline de busca e calcula duas métricas:

    - retrieval accuracy (hit@k): fração de perguntas em que algum documento
      relevante esperado aparece no top-k recuperado.
    - hallucination rate: fração de respostas que o LLM-juiz considera NÃO
      fundamentadas no contexto recuperado."""

    def __init__(
        self,
        search_use_case: SearchUseCase,
        llm_service: LLMServiceProtocol,
        eval_path: Path,
    ) -> None:
        self._search_use_case = search_use_case
        self._llm_service = llm_service
        self._eval_path = eval_path

    def _load_gold_set(self) -> list[dict]:
        with open(self._eval_path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    async def execute(self) -> EvaluationResult:
        gold_set = self._load_gold_set()
        hits = 0
        hallucinations = 0
        details = []

        for item in gold_set:
            search = await self._search_use_case.execute(item["query"])
            retrieved_ids = [doc["id"] for doc in search.results]
            hit = any(rid in retrieved_ids for rid in item["relevant_ids"])
            grounded = await self._llm_service.is_grounded(
                search.response, search.results, question=item["query"]
            )

            hits += int(hit)
            hallucinations += int(not grounded)
            details.append(
                {
                    "query": item["query"],
                    "hit": hit,
                    "grounded": grounded,
                    "retrieved_ids": retrieved_ids,
                }
            )

        n = len(gold_set)
        return EvaluationResult(
            retrieval_accuracy=round(hits / n, 3) if n else 0.0,
            hallucination_rate=round(hallucinations / n, 3) if n else 0.0,
            n=n,
            details=details,
        )
