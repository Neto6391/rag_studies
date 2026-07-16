from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional

from src.services.answer_service import AnswerService
from src.services.sentence_transformer_service import SentenceTransformerService
from src.services.openrouter_service import OpenRouterService

router = APIRouter(prefix="/ask", tags=["ask"])


class AskInput(BaseModel):
    question: Optional[str] = None


@router.get("/")
def get_ask(params: AskInput = Depends()):
    try:
        if params.question is None or params.question.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O parâmetro 'question' é obrigatório e não pode estar vazio.",
            )
        embedding_service = SentenceTransformerService()
        llm_service = OpenRouterService()
        answer_service = AnswerService(
            embedding_service=embedding_service,
            llm_service=llm_service,
        )
        result = answer_service.get_answer(question=params.question)
        return {
            "question": result.question,
            "response": result.response,
            "sources": result.sources,
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro interno: {str(e)}",
        )
