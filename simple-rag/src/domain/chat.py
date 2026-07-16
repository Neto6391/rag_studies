from dataclasses import dataclass, field
from typing import List, Optional

from pydantic import BaseModel


@dataclass
class ChatMessage:
    id: int
    session_id: str
    role: str  # "user" | "assistant"
    content: str
    hallucinated: Optional[bool]
    created_at: str
    sources: Optional[List[dict]] = None


class ChatRequest(BaseModel):
    session_id: str
    message: str
