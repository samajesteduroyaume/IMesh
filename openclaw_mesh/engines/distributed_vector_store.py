from __future__ import annotations

from typing import Any


class DistributedVectorStore:
    def __init__(self) -> None:
        self.documents: dict[str, list[float]] = {}

    def add(self, key: str, vector: list[float]) -> None:
        self.documents[key] = vector

    def search(self, query: list[float], k: int = 5) -> list[str]:
        return list(self.documents.keys())[:k]
