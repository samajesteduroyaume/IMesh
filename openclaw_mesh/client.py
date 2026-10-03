"""WebSocket client for the IMesh mesh.

Use :class:`MeshClient` to connect to remote :class:`~openclaw_mesh.node.IMeshNode`
peers, sign and dispatch task requests, receive streaming chunk frames, and
collect final responses.

Typical usage::

    import asyncio
    from openclaw_mesh.client import MeshClient, MeshTaskError

    async def main():
        client = MeshClient(secret="my-psk")
        client.add_peer("node-a", "ws://192.168.1.10:8765")
        try:
            result = await client.call("node-a", "echo", {"hello": "world"})
        except MeshTaskError as e:
            print(f"Task failed: {e} (request_id={e.request_id})")
        finally:
            await client.stop()
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

import websockets

from .config import get_settings
from .protocol import TaskChunk, TaskRequest, TaskResponse, parse_message


class MeshTaskError(RuntimeError):
    """Raised when a remote node returns ``ok=False`` in a :class:`~openclaw_mesh.protocol.TaskResponse`.

    Attributes:
        request_id: The request ID of the failed task, for traceability.
    """

    def __init__(self, message: str, request_id: str | None = None) -> None:
        super().__init__(message)
        self.request_id = request_id


class MeshClient:
    """Async WebSocket client for the IMesh peer-to-peer mesh.

    Manages named peer endpoints and connection reuse. Signs every outgoing
    :class:`~openclaw_mesh.protocol.TaskRequest` with the pre-shared HMAC key.

    Args:
        client_name: Origin identifier embedded in task requests.
            Defaults to ``OPENCLAW_CLIENT_NAME``.
        secret: Pre-shared key for HMAC signing.
            Defaults to ``OPENCLAW_PSK`` or ``"openclaw-dev-secret"``.
    """

    def __init__(self, client_name: str | None = None, secret: str | None = None) -> None:
        settings = get_settings()
        self.client_name = client_name or settings.client_name
        self.secret = secret or settings.psk or "openclaw-dev-secret"
        self.peers: dict[str, str] = {}
        self.connections: dict[str, Any] = {}
        self._reader_tasks: dict[str, asyncio.Task[None]] = {}
        self._peer_metadata: dict[str, dict[str, Any]] = {}

    def add_peer(self, name: str, url: str, metadata: dict[str, Any] | None = None) -> None:
        self.peers[name] = url
        if metadata is not None:
            self._peer_metadata[name] = metadata

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        for ws in list(self.connections.values()):
            try:
                await ws.close()
            except Exception:
                pass
        self.connections.clear()
        self._reader_tasks.clear()

    async def _connect(self, endpoint: str):
        existing = self.connections.get(endpoint)
        if existing is not None:
            try:
                if getattr(existing, "open", False) or not getattr(existing, "closed", True):
                    return existing
            except Exception:
                pass
        ws = await websockets.connect(endpoint)
        self.connections[endpoint] = ws
        return ws

    async def call(self, peer: str, skill: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if peer not in self.peers:
            raise KeyError(f"unknown peer: {peer}")
        endpoint = self.peers[peer]
        request = TaskRequest(skill=skill, payload=payload or {}, origin=self.client_name)
        request.sign(self.secret)
        ws = await self._connect(endpoint)
        await ws.send(request.to_json())
        response_json = await ws.recv()
        response = TaskResponse.from_dict(json.loads(response_json))
        if not response.ok:
            raise MeshTaskError(response.error or "task execution failed", request_id=response.request_id)
        return response.result

    async def stream_call(
        self,
        peer: str,
        skill: str,
        payload: dict[str, Any] | None = None,
        on_chunk: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        if peer not in self.peers:
            raise KeyError(f"unknown peer: {peer}")
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
                if not message.ok:
                    raise MeshTaskError(message.error or "streaming task execution failed", request_id=message.request_id)
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
