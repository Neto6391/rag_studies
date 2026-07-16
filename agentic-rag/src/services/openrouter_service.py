import os
from typing import List

import httpx

from src.domain.llm import LLMServiceProtocol


class OpenRouterService(LLMServiceProtocol):
    def __init__(
        self,
        model: str = "openai/gpt-4o-mini",
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ) -> None:
        self._model = model
        self._api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self._base_url = base_url

        if not self._api_key:
            raise ValueError("OPENROUTER_API_KEY não definida no .env")

    def generate(self, prompt: str, context: List[dict]) -> str:
        context_text = "\n\n".join(
            f"[{item['title']}]\n{item['text']}" for item in context
        )

        system_message = (
            "Você é um assistente que responde perguntas com base em trechos de obras "
            "literárias de Machado de Assis. Use o contexto fornecido para formular sua resposta. "
            "Responda em português. Se o contexto contiver informações relevantes, use-as. "
            "Só diga que não possui informação suficiente se o contexto for totalmente irrelevante."
        )

        user_message = f"Contexto:\n{context_text}\n\nPergunta: {prompt}"

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
