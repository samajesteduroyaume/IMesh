from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Generator
from typing import Any

import websockets

from .config import get_settings
from .discovery import MeshDiscovery, PeerInfo
from .protocol import TaskChunk, TaskRequest, TaskResponse, parse_message
from .registry import SkillRegistry, get_default_registry


class IMeshNode:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        registry: SkillRegistry | None = None,
        secret: str | None = None,
        discovery: MeshDiscovery | None = None,
    ) -> None:
        settings = get_settings()
        self.host = host or settings.default_host
        self.port = port or settings.default_port
        self.registry = registry or get_default_registry()
        self.secret = secret or settings.psk or "openclaw-dev-secret"
        self.server: websockets.WebSocketServer | None = None
        self._lock = asyncio.Lock()
        self._active_tasks: set[str] = set()
        self._seen_requests: dict[str, float] = {}
        self._max_active = settings.max_active_tasks
        self._task_timeout = settings.task_timeout
        self._max_output = settings.max_output_bytes
        self.discovery = discovery or MeshDiscovery(node_name=settings.node_name, port=self.port, enabled=settings.mdns_enabled)

    async def start(self) -> None:
        self.server = await websockets.serve(self._handle_connection, self.host, self.port)
        await self.discovery.start()

    async def stop(self) -> None:
        if self.server is not None:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        await self.discovery.stop()

    async def _handle_connection(self, websocket) -> None:
        async for raw in websocket:
            try:
                message = parse_message(raw)
            except Exception as exc:  # pragma: no cover - defensive
                await websocket.send(json.dumps({"type": "task_response", "request_id": "unknown", "ok": False, "error": str(exc), "handled_by": self.host, "streamed": False}))
                continue

            if isinstance(message, TaskRequest):
                try:
                    response = await self._handle_request(message)
                    if response is not None:
                        await websocket.send(json.dumps(response.to_dict()))
                except Exception as exc:
                    await websocket.send(
                        json.dumps(
                            TaskResponse(
                                request_id=message.request_id,
                                ok=False,
                                error=str(exc),
                                handled_by=self.host,
                            ).to_dict()
                        )
                    )

    async def _handle_request(self, message: TaskRequest) -> TaskResponse | None:
        now = asyncio.get_running_loop().time()
        for request_id, seen_at in list(self._seen_requests.items()):
            if now - seen_at > 60:
                self._seen_requests.pop(request_id, None)
        if message.request_id in self._seen_requests:
            raise ValueError("replay detected")
        self._seen_requests[message.request_id] = now
        if not message.verify_signature(self.secret):
            raise PermissionError("invalid request signature")
        if message.skill not in self.registry and message.skill not in {"_health", "_describe_skills"}:
            raise KeyError(f"unknown skill: {message.skill}")

        async with self._lock:
            if len(self._active_tasks) >= self._max_active:
                raise RuntimeError("task queue saturated")
            self._active_tasks.add(message.request_id)

        try:
            result = await asyncio.wait_for(self._execute_skill(message), timeout=self._task_timeout)
            return TaskResponse(
                request_id=message.request_id,
                ok=True,
                result=result,
                handled_by=self.host,
                streamed=False,
            )
        except Exception as exc:
            return TaskResponse(request_id=message.request_id, ok=False, error=str(exc), handled_by=self.host)
        finally:
            self._active_tasks.discard(message.request_id)

    async def _execute_skill(self, message: TaskRequest) -> dict[str, Any]:
        if message.skill == "_health":
            return {"status": "ok"}
        if message.skill == "_describe_skills":
            return {"skills": [s.to_tool() for s in self.registry.list()]}

        skill_def = self.registry.get(message.skill)
        payload = message.payload or {}
        func = skill_def.func

        def invoke() -> Any:
            try:
                return func(**payload)
            except TypeError:
                try:
                    return func(payload)
                except TypeError:
                    raise

        if asyncio.iscoroutinefunction(func):
            value = await func(**payload)
        elif callable(func):
            value = invoke()
            if asyncio.iscoroutine(value):
                value = await value
        else:
            raise TypeError("unsupported skill callable")

        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return {"items": value}
        if isinstance(value, (str, int, float, bool)):
            return {"value": value}
        if isinstance(value, Generator):
            return {"items": list(value)}
        if isinstance(value, AsyncGenerator):
            chunks: list[Any] = []
            async for item in value:
                chunks.append(item)
            return {"items": chunks}
        return {"value": str(value)}


class MeshServer(IMeshNode):
    pass
