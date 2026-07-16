# Simple RAG

Sistema RAG (Retrieval-Augmented Generation) em Python com Clean Architecture, usando obras de Machado de Assis como corpus.

## Arquitetura

```
simple-rag/
├── app.py                          # Entry point FastAPI + lifespan (load/clear corpus)
├── .env                            # OPENROUTER_API_KEY
├── data/
│   └── corpus.jsonl                # Corpus de obras de Machado de Assis (497 capítulos)
├── scripts/
│   └── build_corpus.py             # Script para baixar e processar obras do Project Gutenberg
└── src/
    ├── domain/                     # Camada de domínio (entidades e protocolos)
    │   ├── search.py               # Search (dataclass) + SearchQueryParamsInput (Pydantic)
    │   ├── embedding.py            # EmbeddingServiceProtocol (interface)
    │   └── llm.py                  # LLMServiceProtocol (interface)
    ├── infrastructure/
    │   └── corpus_vector_store.py  # Singleton: carrega corpus, vetoriza e faz busca por similaridade cosseno
    ├── services/                   # Camada de serviços (implementações concretas)
    │   ├── sentence_transformer_service.py  # Embedding com sentence-transformers (singleton model)
    │   ├── openrouter_service.py            # LLM via OpenRouter API (httpx)
    │   ├── search_service.py                # Orquestra SearchUseCase
    │   └── answer_service.py                # Orquestra AnswerUseCase (não registrado)
    ├── use_cases/                  # Camada de casos de uso (regras de negócio)
    │   ├── search_use_case.py      # Busca semântica + geração de resposta via LLM
    │   └── answer_use_case.py      # Alternativa isolada de answer (não registrada)
    └── controllers/                # Camada de controllers (FastAPI routers)
        ├── search_controller.py    # GET /search?query=...
        └── ask_controller.py       # GET /ask?question=... (não registrado)
```

### Fluxo da arquitetura

```
Controller → Service → UseCase → Infrastructure/Domain
```

- **Domain**: entidades e protocolos (interfaces) — sem dependências externas
- **Infrastructure**: persistência e vetorização do corpus em memória
- **Services**: implementações concretas (embedding, LLM, orquestração)
- **UseCases**: regras de negócio (busca semântica + geração de resposta)
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
pip install torch sentence-transformers fastapi uvicorn httpx python-dotenv numpy
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

No startup, o modelo de embeddings é carregado e todo o corpus é vetorizado e mantido em memória. No shutdown, a memória é limpa.

## Endpoints

### `GET /search?query=...`

Busca semântica no corpus + geração de resposta via LLM.

**Parâmetros:**
- `query` (string, obrigatório): pergunta ou termo de busca

**Resposta:**
```json
{
  "response": "Resposta gerada pelo LLM baseada no contexto recuperado...",
  "results": [
    {
      "id": "machado-dom-casmurro-cap-042",
      "title": "Dom Casmurro - Capítulo XLIV",
      "source": "project_gutenberg",
      "score": 0.5752,
      "text": "trecho do capítulo..."
    }
  ]
}
```

## Tecnologias

- **FastAPI** — framework web
- **sentence-transformers** — modelo `paraphrase-multilingual-MiniLM-L12-v2` para embeddings
- **OpenRouter** — API de LLM (default: `openai/gpt-4o-mini`)
- **NumPy** — similaridade cosseno entre vetores
- **httpx** — cliente HTTP para OpenRouter
- **python-dotenv** — variáveis de ambiente
