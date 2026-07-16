import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.deps import get_chat_service
from src.domain.chat import ChatRequest
from src.domain.errors import LLMServiceError
from src.services.chat_service import ChatService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/")
async def post_chat(
    body: ChatRequest,
    service: ChatService = Depends(get_chat_service),
):
    if not body.session_id.strip() or not body.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Os campos 'session_id' e 'message' são obrigatórios.",
        )
    try:
        return await service.send(body.session_id, body.message)
    except LLMServiceError:
        logger.exception("Falha ao chamar o serviço de LLM no chat")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível gerar a resposta: o serviço de LLM está indisponível ou a chave de API é inválida.",
        )
    except Exception:
        logger.exception("Erro interno inesperado em /chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocorreu um erro interno inesperado no servidor.",
        )


@router.get("/sessions")
async def list_sessions(service: ChatService = Depends(get_chat_service)):
    return {"sessions": await service.list_sessions()}


@router.get("/{session_id}")
async def get_history(
    session_id: str,
    service: ChatService = Depends(get_chat_service),
):
    messages = await service.history(session_id)
    return {"session_id": session_id, "messages": [vars(m) for m in messages]}


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    service: ChatService = Depends(get_chat_service),
):
    deleted = await service.delete_session(session_id)
    return {"session_id": session_id, "deleted": deleted}
