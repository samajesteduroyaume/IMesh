from __future__ import annotations

from typing import Any


class UniversalEmbeddingEngine:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or "fallback-embedding-model"

    def encode(self, text: str) -> list[float]:
        return [float(len(text)), 0.0, 1.0]

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.encode(text) for text in texts]
