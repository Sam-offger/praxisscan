from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str

class BaseSearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        ...
