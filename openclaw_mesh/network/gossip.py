from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any


class GossipNode:
    def __init__(self, node_id: str = "gossip") -> None:
        self.node_id = node_id
        self.topics: set[str] = set()
        self.messages: dict[str, list[Any]] = defaultdict(list)
        self.seen: set[str] = set()

    def subscribe(self, topic: str) -> None:
        self.topics.add(topic)

    def publish(self, topic: str, message: Any) -> None:
        message_id = hashlib.sha256(
            f"{topic}:".encode() + json.dumps(message, sort_keys=True, default=str).encode()
        ).hexdigest()
        if message_id in self.seen:
            return
        self.messages[topic].append(message)
        self.seen.add(message_id)

    def get_messages(self, topic: str) -> list[Any]:
        return list(self.messages.get(topic, []))
