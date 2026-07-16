import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.deps import get_evaluation_service
from src.domain.errors import LLMServiceError
from src.services.evaluation_service import EvaluationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evaluate", tags=["evaluate"])


@router.get("/")
async def get_evaluate(
    service: EvaluationService = Depends(get_evaluation_service),
):
    try:
        result = await service.evaluate()
        return {
            "retrieval_accuracy": result.retrieval_accuracy,
            "hallucination_rate": result.hallucination_rate,
            "n": result.n,
            "details": result.details,
        }
    except LLMServiceError:
        logger.exception("Falha ao chamar o serviço de LLM durante a avaliação")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível avaliar: o serviço de LLM está indisponível ou a chave de API é inválida.",
        )
    except Exception:
        logger.exception("Erro interno inesperado em /evaluate")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocorreu um erro interno inesperado no servidor.",
        )
