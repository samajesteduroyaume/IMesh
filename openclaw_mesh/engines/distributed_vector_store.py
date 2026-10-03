import math
from typing import Any


class DistributedVectorStore:
    def __init__(self) -> None:
        self.documents: dict[str, list[float]] = {}

    def add(self, key: str, vector: list[float]) -> None:
        self.documents[key] = [float(v) for v in vector]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def search(self, query: list[float], k: int = 5) -> list[str]:
        if not self.documents:
            return []
        scores = []
        for key, vec in self.documents.items():
            sim = self._cosine_similarity(query, vec)
            scores.append((sim, key))
        scores.sort(key=lambda item: item[0], reverse=True)
        return [key for _, key in scores[:k]]
