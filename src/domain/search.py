from dataclasses import dataclass, field
from pydantic import BaseModel
from typing import Optional, List


@dataclass
class Search:
    results: List[dict] = field(default_factory=list)
    response: str = ""


class SearchQueryParamsInput(BaseModel):
    query: Optional[str] = None