from __future__ import annotations

from typing import Any


class MultiModalEngine:
    def __init__(self) -> None:
        self.supported = ["text", "vision"]

    def process(self, modality: str, payload: Any) -> dict[str, Any]:
        return {"modality": modality, "status": "ok", "payload": payload}
