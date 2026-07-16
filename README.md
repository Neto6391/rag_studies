# RAG Studies

Estudo de RAG (Retrieval-Augmented Generation) com corpus de obras de Machado de Assis.
Dois backends independentes, com a mesma Clean Architecture, mostrando a evolução de um
RAG simples para um RAG orquestrado e "production-ready", mais um **frontend React**
(backoffice) com dashboard de métricas e um chat estilo Instagram DM.

```
┌────────────┐        ┌──────────────┐        ┌──────────────────────┐
│  frontend  │ ─────▶ │  simple-rag  │        │  Qdrant  (vetorial)  │
│ React+antd │  ⇄     │   :8001      │ ─────▶ │  Redis   (cache)     │
│  :5173     │ ─────▶ │  agentic-rag │        │  SQLite  (conversas) │
└────────────┘        │   :8000      │        └──────────────────────┘
   seletor de backend └──────────────┘
```

## Infra compartilhada (Docker)

Os dois projetos usam **Redis** (cache) e **Qdrant** (banco vetorial). Suba os dois com:

```bash
docker compose up -d
# Redis  -> localhost:6379
# Qdrant -> localhost:6333
```

- **Qdrant**: guarda os embeddings do corpus. Ingerido uma vez; a aplicação não
  re-vetoriza o corpus a cada startup (era o maior gargalo antes).
- **Redis**: cache das buscas com TTL, para não repetir embedding + retrieval + LLM em
  queries iguais.

## Projetos

### `simple-rag/`

Pipeline direto: **retrieve → generate**. Sem framework de orquestração.

- **Embedding**: `paraphrase-multilingual-MiniLM-L12-v2`
- **Retrieval**: Qdrant (cosseno), top-5
- **LLM**: OpenRouter (`openai/gpt-4o-mini`)

### `agentic-rag/`

Mesma arquitetura, com **reranker** e orquestração via **LangGraph**:
**retrieve (top-10) → rerank (top-5) → generate**.

- **Reranker**: `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
- **Orquestração**: LangGraph `StateGraph`

## Diferenças

| | simple-rag | agentic-rag |
|---|---|---|
| Orquestração | Pipeline plano (steps async) | LangGraph `StateGraph` |
| Reranker | Não | Cross-encoder multilíngue |
| Retrieval | Top-5 direto | Top-10 → rerank → top-5 |
| Banco vetorial | Qdrant | Qdrant |
| Cache | Redis (TTL) | Redis (TTL) |
| Arquitetura | Clean Architecture | Clean Architecture |

## O que os dois têm em comum

- **Clean Architecture**: Controller → Service → UseCase → Infra/Domain. O controller
  nunca chama o use case direto — sempre passa pelo service.
- **Services singletons**: criados uma vez no `lifespan` e guardados em `app.state`,
  injetados via `Depends`. Nenhum service é recriado por request.
- **Async**: endpoints, LLM (httpx async) e I/O do Redis/Qdrant são assíncronos;
  embedding/reranker (CPU) rodam em `asyncio.to_thread`.
- **Métricas** (`GET /evaluate`): retrieval accuracy (hit@k) e hallucination rate
  (LLM-as-judge) sobre um gold set pequeno (`data/eval.jsonl`).

- **Persistência de conversas** (SQLite): cada mensagem do chat é gravada; a cada
  resposta, um juiz de grounding roda em **background** e marca se ela alucinou.

## Endpoints (nos dois projetos)

- `GET /search/?query=...` — busca + resposta do LLM (com cache).
- `GET /evaluate/` — roda o gold set e retorna `retrieval_accuracy` e `hallucination_rate`.
- `POST /chat/` `{session_id, message}` — chat com sessão; persiste a conversa.
- `GET /chat/{session_id}` — histórico da sessão.
- `GET /dashboard/` — estatísticas: total do corpus, obra predominante, nº de
  alucinações detectadas, mensagens e sessões.

## Frontend (`frontend/`)

React + TypeScript + Vite + Ant Design, em clean architecture
(`domain / infrastructure / services / application / presentation`). Layout de
backoffice (usuário "logado") com:

- **Dashboard**: cards de estatística + gráfico de pizza da composição do corpus.
- **Chat** estilo Instagram DM com o "Machado de Assis" respondendo pelo RAG.
- **Seletor de backend** no header: alterna ao vivo entre Simple e Agentic.
- **Toasts** de erro (antd) reaproveitando as mensagens de erro do backend (ex.: 502).

## Setup

```bash
docker compose up -d                 # sobe Redis + Qdrant

# --- backends (um terminal cada) ---
cd agentic-rag                       # e, em outro terminal, cd simple-rag
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env-example .env                 # preencha OPENROUTER_API_KEY
uvicorn app:app --port 8000          # agentic :8000 · simple use --port 8001
# 1º start popula o Qdrant; próximos são rápidos

# --- frontend ---
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

O frontend lê `VITE_AGENTIC_URL` / `VITE_SIMPLE_URL` do `.env` (default :8000 / :8001).

## Corpus

Ambos usam o mesmo corpus: 497 capítulos de 3 obras de Machado de Assis (Memórias
Póstumas, Dom Casmurro, Quincas Borba), extraídos do Project Gutenberg.
