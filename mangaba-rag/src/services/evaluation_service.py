from src.domain.evaluation import EvaluationResult
from src.use_cases.evaluate_use_case import EvaluateUseCase


class EvaluationService:
    """Orquestra o use case de avaliação. Instância única (singleton via
    app.state)."""

    def __init__(self, use_case: EvaluateUseCase) -> None:
        self._use_case = use_case

    async def evaluate(self) -> EvaluationResult:
        return await self._use_case.execute()
