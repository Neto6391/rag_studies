import os


class Settings:
    """Configuração lida do ambiente (.env). Uma instância por processo."""

    def __init__(self) -> None:
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        self.embedding_model = os.getenv(
            "EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.reranker_model = os.getenv(
            "RERANKER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
        )
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_collection = os.getenv("QDRANT_COLLECTION", "machado_agentic")
        self.cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        self.retrieve_top_k = int(os.getenv("RETRIEVE_TOP_K", "10"))
        self.rerank_top_k = int(os.getenv("RERANK_TOP_K", "5"))


def get_settings() -> Settings:
    return Settings()
