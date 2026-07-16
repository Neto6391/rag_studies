from src.domain.dashboard import DashboardStats
from src.infrastructure.conversation_repository import ConversationRepository
from src.infrastructure.corpus_stats import CorpusStats
from src.infrastructure.knowledge_graph_store import KnowledgeGraphStore


class DashboardService:
    """Monta estatísticas do grafo, corpus e conversas."""

    def __init__(
        self,
        graph_store: KnowledgeGraphStore,
        corpus_stats: CorpusStats,
        repository: ConversationRepository,
    ) -> None:
        self._graph_store = graph_store
        self._corpus_stats = corpus_stats
        self._repository = repository

    async def get_stats(self) -> DashboardStats:
        return DashboardStats(
            corpus_total=self._graph_store.chapter_count()
            or self._corpus_stats.total,
            predominant_corpus=self._corpus_stats.predominant,
            corpus_breakdown=self._corpus_stats.breakdown,
            total_messages=await self._repository.count_messages(),
            total_sessions=await self._repository.count_sessions(),
            hallucination_count=await self._repository.count_hallucinations(),
        )
