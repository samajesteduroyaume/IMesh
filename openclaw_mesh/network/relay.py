from __future__ import annotations

from typing import Any


class RelayNode:
    def __init__(self, name: str = "relay") -> None:
        self.name = name
        self.peers: list[str] = []

    def add_peer(self, peer: str) -> None:
        if peer not in self.peers:
            self.peers.append(peer)

    def relay(self, payload: Any) -> dict[str, Any]:
        return {"relay": self.name, "payload": payload}
