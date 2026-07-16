# Agentic RAG

RAG agnóstico com LangGraph e reranker (cross-encoder), usando Clean Architecture e obras de Machado de Assis como corpus.

## Como funciona

```
Query → [retrieve] → [rerank] → [generate] → Resposta
```

1. **Retrieve**: embedda a query, busca top-10 no corpus por similaridade cosseno
2. **Rerank**: cross-encoder re-ordena os 10 documentos, fica com os top-5
3. **Generate**: envia os 5 documentos + query pro LLM gerar a resposta

O LangGraph orquestra esse fluxo como um StateGraph com 3 nós sequenciais.

## Arquitetura

```
agentic-rag/
├── app.py                          # Entry point FastAPI + lifespan (load modelos + corpus)
├── .env                            # OPENROUTER_API_KEY
├── data/
│   └── corpus.jsonl                # Corpus de obras de Machado de Assis (497 capítulos)
└── src/
    ├── domain/                     # Camada de domínio (entidades e protocolos)
    │   ├── search.py               # Search (dataclass) + SearchQueryParamsInput (Pydantic)
    │   ├── graph_state.py          # GraphState (TypedDict) — estado do LangGraph
    │   ├── embedding.py            # EmbeddingServiceProtocol (interface)
    │   ├── reranker.py             # RerankerServiceProtocol (interface)
    │   └── llm.py                  # LLMServiceProtocol (interface)
    ├── infrastructure/
    │   └── corpus_vector_store.py  # Singleton: carrega corpus, vetoriza e faz busca por similaridade cosseno
    ├── services/                   # Camada de serviços (implementações concretas)
    │   ├── sentence_transformer_service.py  # Embedding com sentence-transformers (singleton)
    │   ├── reranker_service.py              # Cross-encoder reranker (singleton)
    │   ├── openrouter_service.py            # LLM via OpenRouter API (httpx)
    │   └── search_service.py                # Orquestra SearchUseCase
    ├── use_cases/                  # Camada de casos de uso (regras de negócio)
    │   └── search_use_case.py      # Constrói e executa o StateGraph (retrieve → rerank → generate)
    └── controllers/                # Camada de controllers (FastAPI routers)
        └── search_controller.py    # GET /search?query=...
```

### Fluxo da arquitetura

```
Controller → Service → UseCase (LangGraph) → Infrastructure/Domain
```

- **Domain**: entidades e protocolos (interfaces) — sem dependências externas
- **Infrastructure**: persistência e vetorização do corpus em memória
- **Services**: implementações concretas (embedding, reranker, LLM, orquestração)
- **UseCases**: constrói o StateGraph do LangGraph com os nós retrieve → rerank → generate
- **Controllers**: rotas FastAPI, única camada que usa `Depends()`

## Corpus

O corpus contém 497 capítulos extraídos de 3 obras de Machado de Assis, obtidas via Project Gutenberg:

- **Memórias Póstumas de Brás Cubas**
- **Dom Casmurro**
- **Quincas Borba**

Cada entrada no `data/corpus.jsonl` segue o formato:

```json
{
  "id": "machado-dom-casmurro-cap-045",
  "source": "project_gutenberg",
  "title": "Dom Casmurro - Capítulo XLV",
  "text": "conteúdo do capítulo...",
  "metadata": {
    "autor": "Machado de Assis",
    "ano": 1899,
    "genero": "romance",
    "livro": "Dom Casmurro",
    "capitulo": 45,
    "gutenberg_id": 385
  }
}
```

## Como Executar

### Pré-requisitos

- Python 3.12+
- WSL (recomendado) ou Python nativo compatível com wheels do PyPI

### Instalação

```bash
python3 -m venv venv
source venv/bin/activate
pip install torch sentence-transformers fastapi uvicorn httpx python-dotenv numpy langgraph
```

### Configuração

Crie um arquivo `.env` na raiz do projeto:

```
OPENROUTER_API_KEY=sua_chave_aqui
```

### Executar

```bash
uvicorn app:app --host 0.0.0.0 --reload
```

No startup, os modelos de embedding e reranker são carregados e todo o corpus é vetorizado e mantido em memória. No shutdown, a memória é limpa.

## Endpoints

### `GET /search?query=...`

Busca semântica no corpus + reranking + geração de resposta via LLM.

**Parâmetros:**
- `query` (string, obrigatório): pergunta ou termo de busca

**Resposta:**
```json
{
  "response": "Resposta gerada pelo LLM baseada no contexto rerankeado...",
  "results": [
    {
      "id": "machado-dom-casmurro-cap-042",
      "title": "Dom Casmurro - Capítulo XLIV",
      "source": "project_gutenberg",
      "score": 0.5752,
      "rerank_score": 8.123,
      "text": "trecho do capítulo..."
    }
  ]
}
```

## Tecnologias

- **LangGraph** — orquestração do fluxo (StateGraph: retrieve → rerank → generate)
- **FastAPI** — framework web
- **sentence-transformers** — embeddings (`paraphrase-multilingual-MiniLM-L12-v2`) + reranker (`cross-encoder/stsb-distilbert-multilingual`)
- **OpenRouter** — API de LLM (default: `openai/gpt-4o-mini`)
- **NumPy** — similaridade cosseno entre vetores
- **httpx** — cliente HTTP para OpenRouter
- **python-dotenv** — variáveis de ambiente
