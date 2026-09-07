from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DHTRecord:
    key: str
    value: Any
    ttl: int = 300
    created_at: float = field(default_factory=time.monotonic)


class DHTNode:
    def __init__(self, node_id: str = "dht-node") -> None:
        self.node_id = node_id
        self.records: dict[str, DHTRecord] = {}

    def put(self, key: str, value: Any, ttl: int = 300) -> None:
        self.records[key] = DHTRecord(key=key, value=value, ttl=ttl)

    def get(self, key: str) -> Any:
        self.refresh()
        record = self.records.get(key)
        if record is None:
            raise KeyError(key)
        return record.value

    def delete(self, key: str) -> None:
        self.records.pop(key, None)

    def refresh(self) -> None:
        now = time.monotonic()
        expired = [
            key for key, record in self.records.items() if now - record.created_at >= record.ttl
        ]
        for key in expired:
            self.records.pop(key, None)
