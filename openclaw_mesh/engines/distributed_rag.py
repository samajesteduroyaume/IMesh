from __future__ import annotations

from typing import Any


class DistributedRAG:
    def __init__(self) -> None:
        self.chunks: list[str] = []

    def add(self, text: str) -> None:
        self.chunks.append(text)

    def query(self, text: str) -> list[str]:
        return [chunk for chunk in self.chunks if text.lower() in chunk.lower()][:5]
