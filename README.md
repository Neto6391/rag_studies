# RAG Studies

Estudo de RAG (Retrieval-Augmented Generation) com corpus de obras de Machado de Assis.

## Projetos

### `simple-rag/`

RAG básico com Clean Architecture. Busca semântica + geração de resposta via LLM.

- **Embedding**: `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers)
- **LLM**: OpenRouter (`openai/gpt-4o-mini`)
- **Busca**: similaridade cosseno direta no corpus vetorial (top-5)
- **Sem reranker**

```bash
cd simple-rag/simple-rag
uvicorn app:app --host 0.0.0.0 --reload
# GET /search?query=Quem é Capitu?
```

### `agentic-rag/`

RAG agnóstico com LangGraph + reranker (cross-encoder). Mesma Clean Architecture, mas com orquestração via StateGraph.

- **Embedding**: `paraphrase-multilingual-MiniLM-L12-v2` (sentence-transformers)
- **Reranker**: `cross-encoder/stsb-distilbert-multilingual` (sentence-transformers)
- **LLM**: OpenRouter (`openai/gpt-4o-mini`)
- **Fluxo**: retrieve (top-10) → rerank (top-5) → generate

```bash
cd agentic-rag
uvicorn app:app --host 0.0.0.0 --reload
# GET /search?query=Quem é Capitu?
```

## Diferenças

| | simple-rag | agentic-rag |
|---|---|---|
| Orquestração | Chamada direta | LangGraph StateGraph |
| Reranker | Não | Cross-encoder multilíngue |
| Retrieval | Top-5 direto | Top-10 → rerank → top-5 |
| Arquitetura | Clean Architecture | Clean Architecture |

## Corpus

Ambos usam o mesmo corpus: 497 capítulos de 3 obras de Machado de Assis (Memórias Póstumas, Dom Casmurro, Quincas Borba), extraídos do Project Gutenberg.

## Setup

### Pré-requisitos

- Python 3.11+
- `pip install fastapi uvicorn httpx python-dotenv numpy sentence-transformers`
- Para agentic-rag, adicionalmente: `pip install langgraph`

### Configuração

Cada projeto tem um `.env-example`. Copie para `.env` e preencha sua chave do OpenRouter:

```
OPENROUTER_API_KEY=sk-or-v1-...
```
