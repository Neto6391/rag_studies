import asyncio
from typing import List

from mangaba.core.llm import create_llm_client

from src.domain.errors import LLMServiceError
from src.domain.llm import LLMServiceProtocol

_SYSTEM_ANSWER = (
    "Você é um assistente que responde perguntas com base em trechos de obras "
    "literárias de Machado de Assis. Use o contexto fornecido para formular sua resposta. "
    "Responda em português. Se o contexto contiver informações relevantes, use-as. "
    "Só diga que não possui informação suficiente se o contexto for totalmente irrelevante."
)

_SYSTEM_JUDGE = (
    "Você é um avaliador de fundamentação em RAG literário.\n"
    "Dada uma PERGUNTA, um CONTEXTO (trechos recuperados) e uma RESPOSTA, decida se a resposta "
    "é aceitável.\n\n"
    "Marque SIM quando:\n"
    "- Fatos sobre personagens, tramas e obras estão sustentados pelo contexto; OU\n"
    "- A resposta é inferência, opinião, conselho ou paralelo contemporâneo pedido na pergunta "
    "e coerente com o contexto (mesmo sem estar literalmente no texto).\n\n"
    "Marque NAO somente quando:\n"
    "- Inventa fatos concretos sobre a obra (personagens, eventos, citações) que contradizem "
    "ou não aparecem no contexto; OU\n"
    "- Responde sobre a obra ignorando completamente o contexto.\n\n"
    "Responda somente com uma palavra: SIM ou NAO."
)


class OpenRouterService(LLMServiceProtocol):
    """Adapter assíncrono para o cliente OpenRouter oficial do Mangaba."""

    def __init__(
        self,
        api_key: str | None,
        model: str = "openai/gpt-4o-mini",
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY não definida no .env")
        self._client = create_llm_client(
            provider="openrouter",
            api_key=api_key,
            model=model,
            base_url=base_url,
            max_output_tokens=1024,
        )

    @staticmethod
    def _format_context(context: List[dict]) -> str:
        return "\n\n".join(f"[{item['title']}]\n{item['text']}" for item in context)

    async def _chat(self, system: str, user: str) -> str:
        try:
            return await asyncio.to_thread(
                self._client.generate_text,
                user,
                system_prompt=system,
            )
        except Exception as exc:
            raise LLMServiceError(f"Falha no OpenRouter via Mangaba: {exc}") from exc

    @staticmethod
    def _parse_grounded_verdict(verdict: str) -> bool:
        text = verdict.strip().lower()
        if text.startswith("sim"):
            return True
        if text.startswith("nao") or text.startswith("não"):
            return False
        return text.split()[0] == "sim" if text.split() else False

    async def generate(self, prompt: str, context: List[dict]) -> str:
        user = f"Contexto:\n{self._format_context(context)}\n\nPergunta: {prompt}"
        return await self._chat(_SYSTEM_ANSWER, user)

    async def is_grounded(
        self, answer: str, context: List[dict], question: str = ""
    ) -> bool:
        user = (
            f"PERGUNTA:\n{question or '(não informada)'}\n\n"
            f"CONTEXTO:\n{self._format_context(context)}\n\n"
            f"RESPOSTA:\n{answer}"
        )
        verdict = await self._chat(_SYSTEM_JUDGE, user)
        return self._parse_grounded_verdict(verdict)

    async def close(self) -> None:
        return None
