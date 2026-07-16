import asyncio
import logging
from typing import List

from src.domain.chat import ChatMessage
from src.domain.llm import LLMServiceProtocol
from src.infrastructure.conversation_repository import ConversationRepository
from src.services.search_service import SearchService

logger = logging.getLogger(__name__)


class ChatService:
    """Orquestra o chat com sessão: persiste as mensagens, reusa o SearchService
    (cache + pipeline) e dispara em background o juiz de grounding para marcar se
    a resposta alucinou (sem travar o retorno para o usuário)."""

    def __init__(
        self,
        search_service: SearchService,
        llm_service: LLMServiceProtocol,
        repository: ConversationRepository,
    ) -> None:
        self._search_service = search_service
        self._llm_service = llm_service
        self._repository = repository
        self._background_tasks: set[asyncio.Task] = set()

    async def send(self, session_id: str, message: str) -> dict:
        await self._repository.add_message(session_id, "user", message)

        result = await self._search_service.search(message)

        assistant_id = await self._repository.add_message(
            session_id, "assistant", result.response, sources=result.results
        )
        self._schedule_grounding_check(
            assistant_id, message, result.response, result.results
        )

        return {
            "message_id": assistant_id,
            "response": result.response,
            "results": result.results,
        }

    async def history(self, session_id: str) -> List[ChatMessage]:
        messages = await self._repository.get_by_session(session_id)
        return await self._hydrate_missing_sources(messages)

    async def list_sessions(self) -> List[dict]:
        return await self._repository.list_sessions()

    async def delete_session(self, session_id: str) -> int:
        return await self._repository.delete_session(session_id)

    async def _hydrate_missing_sources(
        self, messages: List[ChatMessage]
    ) -> List[ChatMessage]:
        """Para mensagens antigas sem sources, reexecuta só o retrieve e persiste."""
        last_user: str | None = None
        for message in messages:
            if message.role == "user":
                last_user = message.content
                continue
            if message.role != "assistant" or message.sources or not last_user:
                continue
            try:
                sources = await self._search_service.retrieve(last_user)
                if not sources:
                    continue
                await self._repository.set_sources(message.id, sources)
                # Flags antigos do juiz rígido eram falso-positivo nestas msgs.
                if message.hallucinated:
                    await self._repository.set_hallucinated(message.id, False)
                    message.hallucinated = False
                message.sources = sources
            except Exception:
                logger.exception(
                    "Falha ao hidratar sources da mensagem %s", message.id
                )
        return messages

    def _schedule_grounding_check(
        self, message_id: int, question: str, response: str, context: List[dict]
    ) -> None:
        task = asyncio.create_task(
            self._check_grounding(message_id, question, response, context)
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    async def _check_grounding(
        self, message_id: int, question: str, response: str, context: List[dict]
    ) -> None:
        try:
            grounded = await self._llm_service.is_grounded(
                response, context, question=question
            )
            await self._repository.set_hallucinated(message_id, not grounded)
        except Exception:
            logger.exception("Falha no check de grounding em background")
