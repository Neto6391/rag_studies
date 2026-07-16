import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from scripts.build_graph import build_artifacts
from src.config import get_settings
from src.controllers.chat_controller import router as chat_router
from src.controllers.dashboard_controller import router as dashboard_router
from src.controllers.evaluate_controller import router as evaluate_router
from src.controllers.search_controller import router as search_router
from src.infrastructure.conversation_repository import ConversationRepository
from src.infrastructure.corpus_stats import CorpusStats
from src.infrastructure.knowledge_graph_store import KnowledgeGraphStore
from src.infrastructure.keyword_store import KeywordStore
from src.infrastructure.node2vec_index import Node2VecIndex
from src.infrastructure.redis_cache import CacheService
from src.services.chat_service import ChatService
from src.services.dashboard_service import DashboardService
from src.services.evaluation_service import EvaluationService
from src.services.llm_reranker_service import LLMReranker
from src.services.openrouter_service import OpenRouterService
from src.services.reranker_service import CrossEncoderService
from src.services.a2a_agents import A2APipeline
from src.services.search_service import SearchService
from src.use_cases.evaluate_use_case import EvaluateUseCase
from src.use_cases.search_use_case import SearchUseCase

load_dotenv()
logger = logging.getLogger("mangaba-rag")

DATA_DIR = Path(__file__).parent / "data"
EVAL_PATH = DATA_DIR / "eval.jsonl"
CORPUS_PATH = DATA_DIR / "corpus.jsonl"
CHAT_DB_PATH = DATA_DIR / "chat.db"

CORS_ORIGINS = ["http://localhost:5173", "http://localhost:5174"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    if not (
        settings.graph_path.exists()
        and settings.node2vec_path.exists()
        and settings.node2vec_map_path.exists()
    ):
        logger.info("Artefatos GraphRAG ausentes — construindo grafo e Node2Vec...")
        await asyncio.to_thread(
            build_artifacts,
            dimensions=settings.node2vec_dimensions,
            walk_length=settings.node2vec_walk_length,
            num_walks=settings.node2vec_num_walks,
            p=settings.node2vec_p,
            q=settings.node2vec_q,
            graph_path=settings.graph_path,
            node2vec_path=settings.node2vec_path,
            node2vec_map_path=settings.node2vec_map_path,
        )

    cross_encoder = CrossEncoderService(settings.reranker_model)
    if settings.rerank_strategy == "llm":
        logger.info("Reranker: LLM-as-reranker (fallback cross-encoder).")
        reranker_service = LLMReranker(
            settings.openrouter_api_key,
            settings.openrouter_model,
            fallback=cross_encoder,
        )
    else:
        reranker_service = cross_encoder
    llm_service = OpenRouterService(settings.openrouter_api_key, settings.openrouter_model)
    cache_service = CacheService(
        settings.redis_url, settings.cache_namespace, settings.cache_ttl_seconds
    )
    repository = ConversationRepository(CHAT_DB_PATH)
    await repository.init()
    corpus_stats = CorpusStats(CORPUS_PATH)
    keyword_store = KeywordStore(CORPUS_PATH)
    graph_store = KnowledgeGraphStore(settings.graph_path)
    node2vec = Node2VecIndex(settings.node2vec_path, settings.node2vec_map_path)
    graph_store.load()
    node2vec.load()

    pipeline = A2APipeline(
        graph_store,
        node2vec,
        keyword_store,
        reranker_service,
        llm_service,
        retrieve_top_k=settings.retrieve_top_k,
        rerank_top_k=settings.rerank_top_k,
        use_rrf=(settings.rerank_strategy != "llm"),
    )
    search_use_case = SearchUseCase(pipeline)
    evaluate_use_case = EvaluateUseCase(search_use_case, llm_service, EVAL_PATH)
    search_service = SearchService(search_use_case, cache_service)

    app.state.search_service = search_service
    app.state.evaluation_service = EvaluationService(evaluate_use_case)
    app.state.chat_service = ChatService(search_service, llm_service, repository)
    app.state.dashboard_service = DashboardService(graph_store, corpus_stats, repository)

    yield

    await llm_service.close()
    await cache_service.close()
    await repository.close()
    if hasattr(reranker_service, "close"):
        reranker_service.close()


app = FastAPI(title="Mangaba GraphRAG", lifespan=lifespan)
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
