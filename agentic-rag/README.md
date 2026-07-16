# Agentic RAG

RAG em Python com Clean Architecture sobre obras de Machado de Assis, orquestrado com
**LangGraph** e com **reranker** (cross-encoder). Usa Qdrant (banco vetorial), Redis
(cache) e métricas de avaliação.

## Como funciona

```
Query → [retrieve: dense ∪ keyword] → [rerank] → [generate] → Resposta
```

1. **retrieve**: busca densa (top-10 no Qdrant) **unida** a hits lexicais
   (substring no `corpus.jsonl` — frases citadas / n-gramas; sem BM25).
2. **rerank**: o cross-encoder re-ordena os candidatos e mantém os top-5.
3. **generate**: envia os 5 documentos + query ao LLM (OpenRouter).

O LangGraph orquestra isso como um `StateGraph` de 3 nós assíncronos. O `SearchService`
consulta o **cache Redis** antes de rodar o grafo; em miss, executa e guarda com TTL.

## Arquitetura

```
agentic-rag/
├── app.py                              # FastAPI + lifespan (cria singletons, popula Qdrant)
├── docker-compose.yml                  # (na raiz do repo) Redis + Qdrant
├── requirements.txt
├── data/
│   ├── corpus.jsonl                    # 497 capítulos de Machado de Assis
│   └── eval.jsonl                      # gold set para /evaluate
├── scripts/
│   └── ingest.py                       # ingere o corpus no Qdrant (roda uma vez)
└── src/
    ├── config.py                       # Settings lidas do .env
    ├── domain/                         # entidades + protocolos (interfaces)
    │   ├── search.py                   # Search + SearchQueryParamsInput
    │   ├── graph_state.py              # GraphState (estado do LangGraph)
    │   ├── evaluation.py               # EvaluationResult
    │   ├── embedding.py / llm.py / reranker.py   # protocolos dos services
    ├── infrastructure/
│   ├── qdrant_vector_store.py      # busca vetorial no Qdrant (async)
│   ├── keyword_store.py            # busca lexical simples (substring, sem BM25)
│   └── redis_cache.py              # cache de busca com TTL (async)
    ├── services/                       # implementações concretas
    │   ├── sentence_transformer_service.py  # embeddings (modelo singleton)
    │   ├── reranker_service.py              # cross-encoder (modelo singleton)
    │   ├── openrouter_service.py            # LLM async + juiz de grounding
    │   ├── search_service.py                # cache + orquestra o use case
    │   └── evaluation_service.py            # orquestra o use case de avaliação
    ├── use_cases/                      # regras de negócio
    │   ├── search_use_case.py          # StateGraph retrieve → rerank → generate
    │   └── evaluate_use_case.py        # calcula as métricas
    └── controllers/                    # rotas FastAPI
        ├── deps.py                     # providers dos services singleton (Depends)
        ├── search_controller.py        # GET /search
        └── evaluate_controller.py      # GET /evaluate
```

### Princípios

- **Controller → Service → UseCase → Infra/Domain**. O controller só recebe o service
  singleton via `Depends` e chama `await service.search(query)` — nunca o use case direto.
- **Singletons**: services (incluindo embedding e reranker) criados uma vez no `lifespan`
  (em `app.state`), nunca por request.
- **Async**: endpoints e I/O (LLM, Redis, Qdrant) assíncronos; embedding e reranker (CPU)
  rodam em `asyncio.to_thread` dentro dos nós do grafo.

## Como executar

```bash
# na raiz do repo:
docker compose up -d

cd agentic-rag
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env-example .env            # preencha OPENROUTER_API_KEY
uvicorn app:app --reload
```

No **primeiro** start, o corpus é vetorizado e gravado no Qdrant (`scripts/ingest.py`).
Nos próximos starts a ingestão é pulada — startup rápido.

Para reingerir manualmente: `python -m scripts.ingest`.

## Endpoints

### `GET /search/?query=...`

Busca semântica + reranking + resposta do LLM (com cache Redis).

```json
{
  "response": "Resposta gerada pelo LLM...",
  "results": [
    { "id": "machado-dom-casmurro-cap-031", "title": "...", "source": "...",
      "score": 0.57, "rerank_score": 8.12, "text": "trecho..." }
  ]
}
```

### `GET /evaluate/`

Roda o gold set (`data/eval.jsonl`) pelo pipeline e retorna `retrieval_accuracy`
(hit@k) e `hallucination_rate` (LLM-as-judge). Mesmo formato do simple-rag.

## Configuração (`.env`)

```
OPENROUTER_API_KEY=sk-...
OPENROUTER_MODEL=openai/gpt-4o-mini
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=machado_agentic
CACHE_TTL_SECONDS=3600
RETRIEVE_TOP_K=10
RERANK_TOP_K=5
```
