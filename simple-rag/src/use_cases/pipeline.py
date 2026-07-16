from typing import Awaitable, Callable, Dict, List

Step = Callable[[Dict], Awaitable[Dict]]


class Pipeline:
    """Executa uma sequência de steps assíncronos sobre um contexto (dict)
    compartilhado. Cada step recebe o contexto e devolve o contexto atualizado,
    deixando o fluxo legível de cima para baixo."""

    def __init__(self, steps: List[Step]) -> None:
        self._steps = steps

    async def run(self, context: Dict) -> Dict:
        for step in self._steps:
            context = await step(context)
        return context
