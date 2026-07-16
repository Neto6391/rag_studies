import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from scripts.ingest import ingest
from src.config import get_settings
from src.controllers.chat_controller import router as chat_router
from src.controllers.dashboard_controller import router as dashboard_router
from src.controllers.evaluate_controller import router as evaluate_router
from src.controllers.search_controller import router as search_router
from src.infrastructure.conversation_repository import ConversationRepository
from src.infrastructure.corpus_stats import CorpusStats
from src.infrastructure.keyword_store import KeywordStore
from src.infrastructure.qdrant_vector_store import QdrantVectorStore
from src.infrastructure.redis_cache import CacheService
from src.services.chat_service import ChatService
from src.services.dashboard_service import DashboardService
from src.services.evaluation_service import EvaluationService
from src.services.openrouter_service import OpenRouterService
from src.services.search_service import SearchService
from src.services.sentence_transformer_service import SentenceTransformerService
from src.use_cases.evaluate_use_case import EvaluateUseCase
from src.use_cases.search_use_case import SearchUseCase

load_dotenv()
logger = logging.getLogger("simple-rag")

DATA_DIR = Path(__file__).parent / "data"
EVAL_PATH = DATA_DIR / "eval.jsonl"
CORPUS_PATH = DATA_DIR / "corpus.jsonl"
CHAT_DB_PATH = DATA_DIR / "chat.db"

CORS_ORIGINS = ["http://localhost:5173", "http://localhost:5174"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Infra + services criados UMA vez e reaproveitados (singletons via app.state).
    embedding_service = SentenceTransformerService(settings.embedding_model)
    llm_service = OpenRouterService(settings.openrouter_api_key, settings.openrouter_model)
    vector_store = QdrantVectorStore(settings.qdrant_url, settings.qdrant_collection)
    cache_service = CacheService(
        settings.redis_url, settings.qdrant_collection, settings.cache_ttl_seconds
    )
    repository = ConversationRepository(CHAT_DB_PATH)
    await repository.init()
    corpus_stats = CorpusStats(CORPUS_PATH)
    keyword_store = KeywordStore(CORPUS_PATH)

    # Popula o Qdrant só se ainda estiver vazio (não re-vetoriza a cada startup).
    if await vector_store.count() == 0:
        logger.info("Coleção vazia — ingerindo corpus no Qdrant...")
        await asyncio.to_thread(ingest, settings, embedding_service)
    else:
        logger.info("Coleção já populada — pulando ingestão.")

    search_use_case = SearchUseCase(
        embedding_service,
        vector_store,
        keyword_store,
        llm_service,
        top_k=settings.top_k,
    )
    evaluate_use_case = EvaluateUseCase(search_use_case, llm_service, EVAL_PATH)
    search_service = SearchService(search_use_case, cache_service)

    app.state.search_service = search_service
    app.state.evaluation_service = EvaluationService(evaluate_use_case)
    app.state.chat_service = ChatService(search_service, llm_service, repository)
    app.state.dashboard_service = DashboardService(vector_store, corpus_stats, repository)

    yield

    await llm_service.close()
    await cache_service.close()
    await vector_store.close()
    await repository.close()


app = FastAPI(title="Simple RAG", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(search_router)
app.include_router(evaluate_router)
app.include_router(chat_router)
app.include_router(dashboard_router)


@app.get("/sessions")
async def list_sessions_alias(request: Request):
    """Alias estável para listar sessões (evita conflito com /chat/{session_id})."""
    service = request.app.state.chat_service
    return {"sessions": await service.list_sessions()}


@app.delete("/sessions/{session_id}")
async def delete_session_alias(session_id: str, request: Request):
    """Alias estável para excluir sessão."""
    service = request.app.state.chat_service
    deleted = await service.delete_session(session_id)
    return {"session_id": session_id, "deleted": deleted}
