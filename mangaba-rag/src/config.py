import os
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PROJECT_DIR = _DATA_DIR.parent


def _project_path(name: str, default: Path) -> Path:
    path = Path(os.getenv(name, str(default)))
    return path if path.is_absolute() else _PROJECT_DIR / path


class Settings:
    """Configuração lida do ambiente (.env). Uma instância por processo."""

    def __init__(self) -> None:
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        self.reranker_model = os.getenv(
            "RERANKER_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
        )
     
        self.rerank_strategy = os.getenv("RERANK_STRATEGY", "cross_encoder")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.cache_namespace = os.getenv("CACHE_NAMESPACE", "machado_mangaba")
        self.cache_ttl_seconds = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        self.retrieve_top_k = int(os.getenv("RETRIEVE_TOP_K", "10"))
        self.rerank_top_k = int(os.getenv("RERANK_TOP_K", "5"))
        self.graph_path = _project_path(
            "GRAPH_PATH", _DATA_DIR / "knowledge_graph.gpickle"
        )
        self.node2vec_path = _project_path(
            "NODE2VEC_PATH", _DATA_DIR / "node2vec.npy"
        )
        self.node2vec_map_path = _project_path(
            "NODE2VEC_MAP_PATH", _DATA_DIR / "node2vec_ids.json"
        )
        self.node2vec_dimensions = int(os.getenv("NODE2VEC_DIMENSIONS", "64"))
        self.node2vec_walk_length = int(os.getenv("NODE2VEC_WALK_LENGTH", "20"))
        self.node2vec_num_walks = int(os.getenv("NODE2VEC_NUM_WALKS", "10"))
        self.node2vec_p = float(os.getenv("NODE2VEC_P", "1.0"))
        self.node2vec_q = float(os.getenv("NODE2VEC_Q", "0.5"))


def get_settings() -> Settings:
    return Settings()
