import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.controllers.deps import get_dashboard_service
from src.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
async def get_dashboard(
    service: DashboardService = Depends(get_dashboard_service),
):
    try:
        stats = await service.get_stats()
        return {
            "corpus_total": stats.corpus_total,
            "predominant_corpus": stats.predominant_corpus,
            "corpus_breakdown": stats.corpus_breakdown,
            "total_messages": stats.total_messages,
            "total_sessions": stats.total_sessions,
            "hallucination_count": stats.hallucination_count,
        }
    except Exception:
        logger.exception("Erro interno inesperado em /dashboard")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocorreu um erro interno inesperado no servidor.",
        )
