from __future__ import annotations

from typing import Any


class AutoModelManager:
    def __init__(self, allowlist: list[str] | None = None) -> None:
        self.allowlist = allowlist or ["fallback-model"]

    def select_model(self, preferred: str | None = None) -> str:
        if preferred and preferred in self.allowlist:
            return preferred
        return self.allowlist[0]

    def available_models(self) -> list[str]:
        return list(self.allowlist)
