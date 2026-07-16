from fastapi import APIRouter, HTTPException, status, Depends

from src.services.search_service import SearchService
from src.services.sentence_transformer_service import SentenceTransformerService
from src.services.openrouter_service import OpenRouterService
from src.services.reranker_service import CrossEncoderService
from src.domain.search import SearchQueryParamsInput

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/")
def get_search(params: SearchQueryParamsInput = Depends()):
    try:
        if params.query is None or params.query.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="O parâmetro de busca 'query' é obrigatório e não pode estar vazio."
            )
        embedding_service = SentenceTransformerService()
        llm_service = OpenRouterService()
        reranker_service = CrossEncoderService()
        search_service = SearchService()
        result = search_service.get_search(
            query=params.query,
            embedding_service=embedding_service,
            llm_service=llm_service,
            reranker_service=reranker_service,
        )
        return {"response": result.response, "results": result.results}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ocorreu um erro interno inesperado no servidor.")
