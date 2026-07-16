from fastapi import Request

from src.services.chat_service import ChatService
from src.services.dashboard_service import DashboardService
from src.services.evaluation_service import EvaluationService
from src.services.search_service import SearchService


def get_search_service(request: Request) -> SearchService:
    return request.app.state.search_service


def get_evaluation_service(request: Request) -> EvaluationService:
    return request.app.state.evaluation_service


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def get_dashboard_service(request: Request) -> DashboardService:
    return request.app.state.dashboard_service
