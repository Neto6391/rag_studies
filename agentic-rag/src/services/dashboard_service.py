from src.domain.dashboard import DashboardStats
from src.infrastructure.conversation_repository import ConversationRepository
from src.infrastructure.corpus_stats import CorpusStats
from src.infrastructure.qdrant_vector_store import QdrantVectorStore


class DashboardService:
    """Monta as estatísticas do dashboard: tamanho do corpus (Qdrant), livro
    predominante (corpus.jsonl) e métricas de uso/alucinação (SQLite)."""

    def __init__(
        self,
        vector_store: QdrantVectorStore,
        corpus_stats: CorpusStats,
        repository: ConversationRepository,
    ) -> None:
        self._vector_store = vector_store
        self._corpus_stats = corpus_stats
        self._repository = repository

    async def get_stats(self) -> DashboardStats:
        corpus_total = await self._vector_store.count()
        return DashboardStats(
            corpus_total=corpus_total or self._corpus_stats.total,
            predominant_corpus=self._corpus_stats.predominant,
            corpus_breakdown=self._corpus_stats.breakdown,
            total_messages=await self._repository.count_messages(),
            total_sessions=await self._repository.count_sessions(),
            hallucination_count=await self._repository.count_hallucinations(),
        )
