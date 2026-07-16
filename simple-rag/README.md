# Simple RAG

RAG em Python com Clean Architecture sobre obras de Machado de Assis.
Pipeline direto: **retrieve → generate**, com Qdrant (banco vetorial), Redis (cache) e
métricas de avaliação.

## Como funciona

```
Query → [retrieve: dense ∪ keyword] → [generate] → Resposta
```

1. **retrieve**: busca densa (top-5 no Qdrant) **unida** a hits lexicais
   (substring no `corpus.jsonl` — frases citadas / n-gramas; sem BM25).
   Sem reranker, os hits de keyword entram primeiro no top-k.
2. **generate**: envia os documentos + query ao LLM (OpenRouter) para gerar a resposta.

O `SearchService` consulta o **cache Redis** antes de rodar o pipeline; em cache miss,
executa e guarda o resultado com TTL.

## Arquitetura

```
simple-rag/
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
    │   ├── evaluation.py               # EvaluationResult
    │   ├── embedding.py / llm.py       # protocolos dos services
    ├── infrastructure/
    │   ├── qdrant_vector_store.py      # busca vetorial no Qdrant (async)
    │   ├── keyword_store.py            # busca lexical simples (substring, sem BM25)
    │   └── redis_cache.py              # cache de busca com TTL (async)
    ├── services/                       # implementações concretas
    │   ├── sentence_transformer_service.py  # embeddings (modelo singleton)
    │   ├── openrouter_service.py            # LLM async + juiz de grounding
    │   ├── search_service.py                # cache + orquestra o use case
    │   └── evaluation_service.py            # orquestra o use case de avaliação
    ├── use_cases/                      # regras de negócio
    │   ├── pipeline.py                 # runner minúsculo de steps async
    │   ├── search_use_case.py          # pipeline retrieve → generate
    │   └── evaluate_use_case.py        # calcula as métricas
    └── controllers/                    # rotas FastAPI
        ├── deps.py                     # providers dos services singleton (Depends)
        ├── search_controller.py        # GET /search
        └── evaluate_controller.py      # GET /evaluate
```

### Princípios

- **Controller → Service → UseCase → Infra/Domain**. O controller só recebe o service
  singleton via `Depends` e chama `await service.search(query)` — nunca o use case direto.
- **Singletons**: services criados uma vez no `lifespan` (em `app.state`), nunca por request.
- **Async**: endpoints e I/O (LLM, Redis, Qdrant) assíncronos; embedding roda em thread.

## Como executar

```bash
# na raiz do repo:
docker compose up -d

cd simple-rag
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env-example .env            # preencha OPENROUTER_API_KEY
uvicorn app:app --reload
```

No **primeiro** start, o corpus é vetorizado e gravado no Qdrant (`scripts/ingest.py`).
Nos próximos starts a ingestão é pulada (a coleção já existe) — startup rápido.

Para reingerir manualmente: `python -m scripts.ingest`.

## Endpoints

### `GET /search/?query=...`

Busca semântica + resposta do LLM (com cache Redis).

```json
{
  "response": "Resposta gerada pelo LLM...",
  "results": [
    { "id": "machado-dom-casmurro-cap-031", "title": "...", "source": "...",
      "score": 0.57, "text": "trecho..." }
  ]
}
```

### `GET /evaluate/`

Roda o gold set (`data/eval.jsonl`) pelo pipeline e retorna as métricas:

```json
{
  "retrieval_accuracy": 0.83,
  "hallucination_rate": 0.17,
  "n": 6,
  "details": [ { "query": "...", "hit": true, "grounded": true, "retrieved_ids": ["..."] } ]
}
```

- **retrieval_accuracy** (hit@k): fração de perguntas em que algum documento relevante
  esperado aparece no top-k.
- **hallucination_rate**: fração de respostas que o LLM-juiz considera não fundamentadas
  no contexto recuperado.

## Configuração (`.env`)

```
OPENROUTER_API_KEY=sk-...
OPENROUTER_MODEL=openai/gpt-4o-mini
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=machado_simple
CACHE_TTL_SECONDS=3600
TOP_K=5
```
