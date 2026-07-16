from typing import TypedDict


class GraphState(TypedDict):
    query: str
    retrieved_docs: list
    reranked_docs: list
    answer: str
