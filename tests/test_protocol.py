import json

import pytest

from openclaw_mesh.protocol import TaskChunk, TaskRequest, TaskResponse, parse_message


def test_protocol_serialization_roundtrip():
    req = TaskRequest(skill="echo", payload={"hello": "world"}, origin="alpha")
    req.sig = "deadbeef"
    payload = req.to_dict()
    assert payload["type"] == "task_request"
    assert TaskRequest.from_dict(payload).to_dict() == payload

    chunk = TaskChunk(request_id=req.request_id, index=0, chunk="hello")
    assert TaskChunk.from_dict(chunk.to_dict()).to_dict() == chunk.to_dict()

    response = TaskResponse(request_id=req.request_id, ok=True, result={"ok": True}, handled_by="beta")
    assert TaskResponse.from_dict(response.to_dict()).to_dict() == response.to_dict()


def test_parse_message_invalid_type():
    with pytest.raises(ValueError):
        parse_message(json.dumps({"type": "bogus"}))


def test_hmac_canonicalization():
    req = TaskRequest(skill="sum", payload={"x": 1, "y": 2}, origin="node-a")
    secret = "supersecret"
    req.sign(secret)
    assert req.verify_signature(secret)
    req.payload["x"] = 99
    assert not req.verify_signature(secret)
