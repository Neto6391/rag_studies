"""Ingestão do corpus no Qdrant.

Lê data/corpus.jsonl, gera os embeddings em batch e faz upsert na coleção do
Qdrant. Roda uma vez — depois a aplicação apenas consulta o banco, sem
re-vetorizar a cada startup.

Uso:
    python -m scripts.ingest
"""
import json
from pathlib import Path

from qdrant_client import QdrantClient, models

from src.config import Settings, get_settings
from src.domain.embedding import EmbeddingServiceProtocol
from src.services.sentence_transformer_service import SentenceTransformerService

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "data" / "corpus.jsonl"


def _load_documents() -> list[dict]:
    with open(CORPUS_PATH, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def ingest(
    settings: Settings,
    embedding_service: EmbeddingServiceProtocol | None = None,
) -> int:
    embedding_service = embedding_service or SentenceTransformerService(settings.embedding_model)
    documents = _load_documents()
    vectors = embedding_service.generate_batch([doc["text"] for doc in documents])

    client = QdrantClient(url=settings.qdrant_url)
    if client.collection_exists(settings.qdrant_collection):
        client.delete_collection(settings.qdrant_collection)
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=models.VectorParams(
            size=len(vectors[0]),
            distance=models.Distance.COSINE,
        ),
    )

    points = [
        models.PointStruct(
            id=index,
            vector=vectors[index],
            payload={
                "id": doc["id"],
                "title": doc["title"],
                "source": doc["source"],
                "text": doc["text"],
            },
        )
        for index, doc in enumerate(documents)
    ]
    client.upsert(collection_name=settings.qdrant_collection, points=points)
    client.close()
    return len(points)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT))
    from dotenv import load_dotenv

    load_dotenv()
    total = ingest(get_settings())
    print(f"Ingeridos {total} documentos na coleção.")
