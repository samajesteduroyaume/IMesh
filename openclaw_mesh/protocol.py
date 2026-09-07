from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, TypeAlias

MessageType: TypeAlias = dict[str, Any]

MAX_MESSAGE_BYTES = 1_048_576


@dataclass(slots=True)
class TaskRequest:
    type: str = "task_request"
    skill: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    origin: str = ""
    ts: float = field(default_factory=time.time)
    sig: str | None = None
    pubkey: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "skill": self.skill,
            "payload": self.payload,
            "request_id": self.request_id,
            "origin": self.origin,
            "ts": self.ts,
            "sig": self.sig,
            "pubkey": self.pubkey,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskRequest":
        if not isinstance(data, dict):
            raise TypeError("TaskRequest must be a dict")

        if data.get("type") != "task_request":
            raise ValueError("Invalid TaskRequest type")

        payload = data.get("payload", {})
        if not isinstance(payload, dict):
            raise TypeError("payload must be a dict")

        request_id = data.get("request_id")
        origin = data.get("origin")
        skill = data.get("skill")
        ts = data.get("ts")
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id must be a non-empty string")
        if not isinstance(origin, str) or not origin:
            raise ValueError("origin must be a non-empty string")
        if not isinstance(skill, str) or not skill:
            raise ValueError("skill must be a non-empty string")
        if not isinstance(ts, (int, float)):
            raise TypeError("ts must be a float or int")

        return cls(
            type="task_request",
            skill=skill,
            payload=payload,
            request_id=request_id,
            origin=origin,
            ts=float(ts),
            sig=data.get("sig"),
            pubkey=data.get("pubkey"),
        )

    def sign(self, secret: str) -> "TaskRequest":
        canonical = canonical_request_string(self)
        digest = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        self.sig = digest
        return self

    def verify_signature(self, secret: str) -> bool:
        if not self.sig:
            return False
        canonical = canonical_request_string(self)
        expected = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.sig)


def canonical_request_string(req: TaskRequest) -> str:
    payload = json.dumps(req.payload, sort_keys=True, separators=(",", ":"))
    return f"{req.request_id}|{req.origin}|{req.skill}|{repr(req.ts)}|{payload}"


@dataclass(slots=True)
class TaskChunk:
    type: str = "task_chunk"
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    index: int = 0
    chunk: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "request_id": self.request_id, "index": self.index, "chunk": self.chunk}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskChunk":
        if not isinstance(data, dict):
            raise TypeError("TaskChunk must be a dict")
        if data.get("type") != "task_chunk":
            raise ValueError("Invalid TaskChunk type")
        request_id = data.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id must be a non-empty string")
        index = data.get("index")
        if not isinstance(index, int):
            raise TypeError("index must be an integer")
        chunk = data.get("chunk")
        if not isinstance(chunk, str):
            raise TypeError("chunk must be a string")
        return cls(type="task_chunk", request_id=request_id, index=index, chunk=chunk)


@dataclass(slots=True)
class TaskResponse:
    type: str = "task_response"
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ok: bool = True
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    handled_by: str | None = None
    streamed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "request_id": self.request_id,
            "ok": self.ok,
            "result": self.result,
            "error": self.error,
            "handled_by": self.handled_by,
            "streamed": self.streamed,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskResponse":
        if not isinstance(data, dict):
            raise TypeError("TaskResponse must be a dict")
        if data.get("type") != "task_response":
            raise ValueError("Invalid TaskResponse type")
        request_id = data.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id must be a non-empty string")
        result = data.get("result", {})
        if not isinstance(result, dict):
            raise TypeError("result must be a dict")
        ok = data.get("ok")
        if not isinstance(ok, bool):
            raise TypeError("ok must be a bool")
        error = data.get("error")
        if error is not None and not isinstance(error, str):
            raise TypeError("error must be a string or None")
        handled_by = data.get("handled_by")
        if handled_by is not None and not isinstance(handled_by, str):
            raise TypeError("handled_by must be a string or None")
        streamed = data.get("streamed")
        if not isinstance(streamed, bool):
            raise TypeError("streamed must be a bool")
        return cls(
            type="task_response",
            request_id=request_id,
            ok=ok,
            result=result,
            error=error,
            handled_by=handled_by,
            streamed=streamed,
        )


def parse_message(data: str | bytes | dict[str, Any]) -> TaskRequest | TaskChunk | TaskResponse:
    if isinstance(data, (bytes, bytearray)):
        payload = data.decode("utf-8")
        if len(payload.encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise ValueError("message too large")
        data = json.loads(payload)
    elif isinstance(data, str):
        if len(data.encode("utf-8")) > MAX_MESSAGE_BYTES:
            raise ValueError("message too large")
        data = json.loads(data)

    if not isinstance(data, dict):
        raise TypeError("message must be a dict or JSON string")

    kind = data.get("type")
    if kind == "task_request":
        return TaskRequest.from_dict(data)
    if kind == "task_chunk":
        return TaskChunk.from_dict(data)
    if kind == "task_response":
        return TaskResponse.from_dict(data)
    raise ValueError(f"Unsupported message type: {kind!r}")
