from typing import List

import httpx

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
    """Cliente do LLM via OpenRouter. Usa um AsyncClient httpx reaproveitado
    (uma conexão por instância singleton)."""

    def __init__(
        self,
        api_key: str | None,
        model: str = "openai/gpt-4o-mini",
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY não definida no .env")
        self._model = model
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=60,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    @staticmethod
    def _format_context(context: List[dict]) -> str:
        return "\n\n".join(f"[{item['title']}]\n{item['text']}" for item in context)

    async def _chat(self, system: str, user: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise LLMServiceError(
                f"OpenRouter respondeu {e.response.status_code}: {e.response.text[:200]}"
            ) from e
        except httpx.RequestError as e:
            raise LLMServiceError(f"Falha de conexão com o OpenRouter: {e}") from e

        data = response.json()
        return data["choices"][0]["message"]["content"]

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
        await self._client.aclose()
