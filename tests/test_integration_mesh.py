import asyncio

import pytest

from openclaw_mesh.client import MeshClient
from openclaw_mesh.node import IMeshNode
from openclaw_mesh.registry import SkillRegistry


@pytest.mark.asyncio
async def test_node_client_roundtrip():
    registry = SkillRegistry()

    @registry.register("echo")
    def echo(payload=None):
        return {"payload": payload or {}}

    node = IMeshNode(host="127.0.0.1", port=8766, registry=registry, secret="integration-secret")
    await node.start()
    try:
        client = MeshClient(client_name="client-a", secret="integration-secret")
        client.add_peer("node-a", "ws://127.0.0.1:8766")
        result = await client.call("node-a", "echo", {"message": "hello"})
        assert result == {"payload": {"message": "hello"}}
        health = await client.check_health("node-a")
        assert health["status"] == "ok"
    finally:
        await node.stop()
        await client.stop()
