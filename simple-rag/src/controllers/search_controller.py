import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.deps import get_search_service
from src.domain.errors import LLMServiceError
from src.domain.search import SearchQueryParamsInput
from src.services.search_service import SearchService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])


@router.get("/")
async def get_search(
    params: SearchQueryParamsInput = Depends(),
    service: SearchService = Depends(get_search_service),
):
    if params.query is None or params.query.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O parâmetro de busca 'query' é obrigatório e não pode estar vazio.",
        )
    try:
        result = await service.search(params.query)
        return {"response": result.response, "results": result.results}
    except HTTPException:
        raise
    except LLMServiceError:
        logger.exception("Falha ao chamar o serviço de LLM")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível gerar a resposta: o serviço de LLM está indisponível ou a chave de API é inválida.",
        )
    except Exception:
        logger.exception("Erro interno inesperado em /search")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocorreu um erro interno inesperado no servidor.",
        )
