from __future__ import annotations

from typing import Any


class DistributedMoEOrchestrator:
    def __init__(self) -> None:
        self.experts: list[str] = ["expert-a", "expert-b"]

    def route(self, prompt: str) -> dict[str, Any]:
        return {"prompt": prompt, "experts": self.experts, "strategy": "fallback-round-robin"}
