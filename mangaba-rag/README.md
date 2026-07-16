# Mangaba GraphRAG

GraphRAG sobre 497 capítulos de Machado de Assis. **Sem embedding denso de
capítulos e sem Qdrant** — o retrieval é 100% estrutural (grafo + Node2Vec) +
lexical, e o rerank pode ser neural (cross-encoder) ou um **LLM-as-reranker**.

```text
query → NER (gazetteer) → grafo (entidades→capítulos) ┐
                          Node2Vec (expansão estrutural) ├→ pool → rerank → OpenRouter
                          keyword lexical               ┘
```

Um agente **coordinator** do `protocols.a2a` do Mangaba conduz o fluxo sobre
quatro trabalhadores: `ner_agent → graph_agent → rerank_agent → answer_agent`.

## Como rodar (passo a passo)

Pré-requisito: o **Redis** compartilhado no ar (na raiz do repo: `docker compose up -d`).
Qdrant **não** é necessário para este backend.

```bash
cd mangaba-rag
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env-example .env          # preencha OPENROUTER_API_KEY (o resto tem default)

uvicorn app:app --port 8002   # 1º start constrói o grafo + Node2Vec automaticamente
```

- No **primeiro start**, se os artefatos do grafo não existirem, o `lifespan` roda
  o `build_graph` sozinho (pode levar ~1 min). Nos próximos starts é instantâneo.
- Para reconstruir o grafo manualmente (ex.: depois de mexer no gazetteer):
  `python -m scripts.build_graph`.
- O frontend (`../frontend`) já aponta para este backend em `:8002` (seletor
  "Mangaba RAG").

### Teste rápido

```bash
curl "http://localhost:8002/dashboard/"
curl "http://localhost:8002/search/?query=Quem é Rubião?"
curl "http://localhost:8002/evaluate/"     # roda o gold set: retrieval_accuracy + hallucination_rate
```

## Estratégia de rerank (`RERANK_STRATEGY`)

Um flag no `.env` escolhe o "cérebro" do rerank:

| Valor | O que faz | Quando usar |
|---|---|---|
| `cross_encoder` (**default**) | cross-encoder `mmarco-mMiniLMv2` + **RRF** (funde grafo+lexical+neural) | rápido, **grátis**, determinístico (**6/6** no gold) |
| `llm` | **LLM-as-reranker** via OpenRouter, com fallback automático pro cross-encoder | entende o PT de 1881; fecha **7/7** determinístico; custa +1 chamada LLM por busca |

Troca sem código: `RERANK_STRATEGY=llm` no `.env` e reiniciar.

## Técnicas de retrieval (o que faz o retrieval ser "afiado")

1. **NER gazetteer com grafia arcaica** — o corpus é de 1881 ("Braz", "Sophia",
   "Marcella"); o gazetteer tem tanto a grafia moderna (para a query do usuário)
   quanto a arcaica (para ligar as entidades ao texto do corpus). Sem isso,
   personagens principais ficam **desconectados do grafo**.
2. **Composição do pool** — sinais precisos (entidade direta + lexical) entram no
   pool **antes** da expansão estrutural fuzzy, para uma entidade ampla (ex.: Brás
   Cubas, 19 caps) não truncar o capítulo lexical certo antes do corte.
3. **RRF** (modo `cross_encoder`) — Reciprocal Rank Fusion de grafo + lexical +
   neural. Documentos em que vários canais concordam sobem; compensa o
   cross-encoder sozinho, **sem banco vetorial**.
4. **LLM-as-reranker** (modo `llm`) — o cross-encoder foi treinado em texto web
   moderno e erra o português arcaico; o LLM relê os candidatos e acerta.
   Determinismo: **provider pinning** + `seed` + `top_p=0..1` + **cache em memória**
   (mesma query+candidatos → mesma ordem, e não gasta LLM à toa).
5. **Tie-break de frase** — se a query cita uma expressão, o capítulo que a
   **introduz** (menor número entre os ligados à frase no grafo) é garantido no
   top-k, de forma determinística. Crava casos como "ao vencedor as batatas"→cap-18.

## Artefatos do grafo

- `data/knowledge_graph.gpickle` — nós PERSON/WORK/PHRASE/CHAPTER e relações.
- `data/graph_edges.jsonl` — export legível das arestas.
- `data/node2vec.npy` / `data/node2vec_ids.json` — vetores estruturais (biased
  walks + PPMI/SVD, sem gensim) e o mapa nó→índice. Configuráveis via `NODE2VEC_*`.

## Endpoints

- `GET /search/?query=...` — busca + resposta (com cache).
- `POST /chat/` `{session_id, message}` · `GET /chat/{session_id}` — chat com sessão.
- `GET /sessions` · `DELETE /sessions/{session_id}` — gestão de sessões.
- `GET /dashboard/` — estatísticas (corpus, alucinações, conversas).
- `GET /evaluate/` — gold set → `retrieval_accuracy` (hit@k) + `hallucination_rate`.

Respostas preservam o contrato dos outros backends: `Search(results, response)`,
com fontes por capítulo e `rerank_score`.

## Arquitetura

```text
controllers → services → use_cases → infrastructure/domain
```

Chat, sessões, fontes, avaliação, Redis e SQLite seguem os mesmos contratos do
`agentic-rag`; só o retrieve/orquestrador é o GraphRAG A2A.

## Variáveis de ambiente (`.env`)

```
OPENROUTER_API_KEY=sk-...
OPENROUTER_MODEL=openai/gpt-4o-mini
RERANK_STRATEGY=cross_encoder      # ou "llm"
REDIS_URL=redis://localhost:6379/0
CACHE_NAMESPACE=machado_mangaba
RETRIEVE_TOP_K=10
RERANK_TOP_K=5
# GRAPH_PATH / NODE2VEC_* têm defaults; ver .env-example
```
