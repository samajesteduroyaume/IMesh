from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

import websockets

from .config import get_settings
from .protocol import TaskChunk, TaskRequest, TaskResponse, parse_message


class MeshClient:
    def __init__(self, client_name: str | None = None, secret: str | None = None) -> None:
        settings = get_settings()
        self.client_name = client_name or settings.client_name
        self.secret = secret or settings.psk or "openclaw-dev-secret"
        self.peers: dict[str, str] = {}
        self.connections: dict[str, websockets.WebSocketClientProtocol] = {}
        self._reader_tasks: dict[str, asyncio.Task[None]] = {}
        self._peer_metadata: dict[str, dict[str, Any]] = {}

    def add_peer(self, name: str, url: str, metadata: dict[str, Any] | None = None) -> None:
        self.peers[name] = url
        if metadata is not None:
            self._peer_metadata[name] = metadata

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        for ws in self.connections.values():
            await ws.close()
        self.connections.clear()
        self._reader_tasks.clear()

    async def _connect(self, endpoint: str):
        ws = await websockets.connect(endpoint)
        self.connections[endpoint] = ws
        return ws

    async def call(self, peer: str, skill: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        endpoint = self.peers[peer]
        request = TaskRequest(skill=skill, payload=payload or {}, origin=self.client_name)
        request.sign(self.secret)
        ws = await self._connect(endpoint)
        await ws.send(request.to_json())
        response_json = await ws.recv()
        response = TaskResponse.from_dict(json.loads(response_json))
        return response.result

    async def stream_call(
        self,
        peer: str,
        skill: str,
        payload: dict[str, Any] | None = None,
        on_chunk: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        endpoint = self.peers[peer]
        request = TaskRequest(skill=skill, payload=payload or {}, origin=self.client_name)
        request.sign(self.secret)
        ws = await self._connect(endpoint)
        await ws.send(request.to_json())
        final_result: dict[str, Any] = {}
        while True:
            raw = await ws.recv()
            message = parse_message(raw)
            if isinstance(message, TaskChunk):
                if on_chunk is not None:
                    on_chunk({"request_id": message.request_id, "index": message.index, "chunk": message.chunk})
            elif isinstance(message, TaskResponse):
                final_result = message.result
                break
        return final_result

    async def discover_skills(self, peer: str) -> list[dict[str, Any]]:
        result = await self.call(peer, "_describe_skills")
        return result.get("skills", [])

    async def check_health(self, peer: str) -> dict[str, Any]:
        return await self.call(peer, "_health")

    def find_best_peer_for_skill(self, skill: str) -> str | None:
        ordered = list(self.peers.items())
        for name, _ in ordered:
            metadata = self._peer_metadata.get(name, {})
            skills = metadata.get("skills", [])
            if skill in skills or skill in {"echo", "_health", "_describe_skills"}:
                return name
        return next(iter(self.peers), None)


class MeshClientSession(MeshClient):
    pass
