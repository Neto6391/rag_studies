import json
import re
import unicodedata
from collections import Counter
from difflib import get_close_matches
from pathlib import Path
from typing import Collection, List

from src.infrastructure.qdrant_vector_store import QdrantVectorStore

_QUOTE_RE = re.compile(r"[\"'“”‘’«»](.+?)[\"'“”‘’«»]")
_TOKEN_RE = re.compile(r"[a-zà-ü0-9]+", re.IGNORECASE)

# Tokens presentes em pelo menos esta fração dos documentos = stopwords.
_STOPWORD_DOC_FREQ = 0.35


def _normalize(text: str) -> str:
    text = text.lower().replace("\r\n", "\n")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text


def _token_find(norm_text: str, token: str, start: int = 0) -> int:
    """Índice do token como palavra inteira (evita 'capitu' dentro de 'capitulo')."""
    pattern = re.compile(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])")
    match = pattern.search(norm_text, start)
    return match.start() if match else -1


def _phrase_matches(norm_text: str, phrase: str) -> bool:
    """Match por palavras inteiras, na mesma ordem (com gap permitido)."""
    needle = _normalize(phrase)
    tokens = [t for t in needle.split() if t]
    if not tokens or any(len(t) < 3 for t in tokens):
        return False

    exact = (
        r"(?<![a-z0-9])"
        + r"\s+".join(re.escape(token) for token in tokens)
        + r"(?![a-z0-9])"
    )
    if re.search(exact, norm_text):
        return True

    cursor = 0
    for token in tokens:
        index = _token_find(norm_text, token, cursor)
        if index < 0:
            return False
        cursor = index + len(token)
    return True


def _build_stopwords(normalized_texts: list[str], min_doc_freq: float = _STOPWORD_DOC_FREQ) -> frozenset[str]:
    """Stopwords = tokens que aparecem em muitos documentos do corpus."""
    if not normalized_texts:
        return frozenset()

    doc_freq: Counter[str] = Counter()
    for text in normalized_texts:
        unique_tokens = {
            token
            for token in _TOKEN_RE.findall(text)
            if len(token) >= 2
        }
        doc_freq.update(unique_tokens)

    threshold = max(2, int(len(normalized_texts) * min_doc_freq))
    return frozenset(token for token, count in doc_freq.items() if count >= threshold)


def _content_tokens(query: str, stopwords: Collection[str]) -> list[str]:
    return [
        token
        for token in _TOKEN_RE.findall(_normalize(query))
        if token not in stopwords and len(token) >= 3
    ]


def _expand_with_corpus_vocabulary(
    tokens: list[str], vocabulary: Collection[str] | None
) -> list[str]:
    if not vocabulary:
        return tokens

    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if len(token) < 5 or token in vocabulary:
            continue
        matches = get_close_matches(token, vocabulary, n=1, cutoff=0.84)
        if matches and matches[0] not in expanded:
            expanded.append(matches[0])
    return expanded


def extract_keyword_phrases(
    query: str,
    vocabulary: Collection[str] | None = None,
    stopwords: Collection[str] | None = None,
) -> List[str]:
    """Extrai frases citadas, n-gramas (2–3) e unigramas relevantes da query."""
    stopwords = stopwords or frozenset()
    phrases: list[str] = []
    for match in _QUOTE_RE.findall(query):
        phrase = match.strip()
        if len(phrase) >= 3:
            phrases.append(phrase)

    tokens = _content_tokens(query, stopwords)
    expanded = _expand_with_corpus_vocabulary(tokens, vocabulary)

    for size in (3, 2):
        for index in range(len(tokens) - size + 1):
            chunk = tokens[index : index + size]
            phrases.append(" ".join(chunk))
            expanded_chunk = [
                _expand_with_corpus_vocabulary([token], vocabulary)[-1] for token in chunk
            ]
            if expanded_chunk != chunk:
                phrases.append(" ".join(expanded_chunk))

    for token in expanded:
        if len(token) < 5:
            continue
        if vocabulary is None or token in vocabulary:
            phrases.append(token)

    seen: set[str] = set()
    unique: list[str] = []
    for phrase in phrases:
        key = _normalize(phrase)
        if key in seen:
            continue
        seen.add(key)
        unique.append(phrase)
    return unique


class KeywordStore:
    """Busca lexical simples (substring) sobre o corpus.jsonl — sem BM25.

    Complementa o retrieve denso: se a query cita uma expressão literal, os
    capítulos certos entram no candidato mesmo quando o embedding os ranqueia mal.
    """

    def __init__(self, corpus_path: Path) -> None:
        self._documents: list[dict] = []
        self._normalized_texts: list[str] = []
        self._stopwords: frozenset[str] = frozenset()
        self._vocabulary: set[str] = set()
        self._load(corpus_path)

    def _load(self, corpus_path: Path) -> None:
        with open(corpus_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                doc = json.loads(line)
                normalized_text = _normalize(doc["text"])
                self._documents.append(doc)
                self._normalized_texts.append(normalized_text)

        self._stopwords = _build_stopwords(self._normalized_texts)
        self._vocabulary = {
            token
            for text in self._normalized_texts
            for token in _TOKEN_RE.findall(text)
            if len(token) >= 5 and token not in self._stopwords
        }

    def _to_hit(self, doc: dict) -> dict:
        return {
            "id": doc["id"],
            "title": doc["title"],
            "source": doc["source"],
            "score": 1.0,
            "text": doc["text"][: QdrantVectorStore.TEXT_PREVIEW_CHARS],
        }

    def search(self, query: str, limit: int = 20) -> List[dict]:
        phrases = extract_keyword_phrases(query, self._vocabulary, self._stopwords)
        if not phrases:
            return []

        phrases_sorted = sorted(phrases, key=lambda p: len(_normalize(p)), reverse=True)
        hits: dict[str, dict] = {}

        for phrase in phrases_sorted:
            for doc, norm_text in zip(self._documents, self._normalized_texts):
                if doc["id"] in hits:
                    continue
                if _phrase_matches(norm_text, phrase):
                    hits[doc["id"]] = self._to_hit(doc)
                if len(hits) >= limit:
                    return list(hits.values())

        return list(hits.values())
