from __future__ import annotations

from collections import OrderedDict
from typing import Any


class SemanticKVCache:
    def __init__(self, max_entries: int = 128) -> None:
        self.max_entries = max_entries
        self._data: OrderedDict[str, Any] = OrderedDict()

    def set(self, key: str, value: Any) -> None:
        if key in self._data:
            self._data.pop(key)
        self._data[key] = value
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)

    def get(self, key: str, default: Any = None) -> Any:
        if key not in self._data:
            return default
        value = self._data.pop(key)
        self._data[key] = value
        return value

    def clear(self) -> None:
        self._data.clear()
