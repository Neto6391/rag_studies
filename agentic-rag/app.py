from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from dotenv import load_dotenv

from src.controllers.search_controller import router as search_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.services.sentence_transformer_service import SentenceTransformerService
    from src.services.reranker_service import CrossEncoderService
    from src.infrastructure.corpus_vector_store import CorpusVectorStore

    corpus_path = Path(__file__).parent / "data" / "corpus.jsonl"
    embedding_service = SentenceTransformerService()
    CrossEncoderService()
    store = CorpusVectorStore.get_instance()
    store.load(embedding_service, corpus_path)
    yield
    store.clear()


app = FastAPI(title="Agentic RAG", lifespan=lifespan)
app.include_router(search_router)