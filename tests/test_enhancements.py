import asyncio
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from openclaw_mesh.crypto import generate_ephemeral_tls_cert
from openclaw_mesh.crypto_e2ee import E2EEChannel
from openclaw_mesh.registry import SkillRegistry
from openclaw_mesh.node import IMeshNode
from openclaw_mesh.client import MeshClient, MeshTaskError
from openclaw_mesh.gateway.server import create_app
from openclaw_mesh.gateway.db import GatewayDB
from openclaw_mesh.engines import DistributedVectorStore
from openclaw_mesh.cli import main as cli_main


def test_tls_ephemeral_cert_generation():
    cert_pem, key_pem = generate_ephemeral_tls_cert("mesh-node.local")
    assert "BEGIN CERTIFICATE" in cert_pem
    assert "BEGIN PRIVATE KEY" in key_pem


def test_e2ee_channel_generate_pair():
    channel, pubkey, pub_bytes = E2EEChannel.generate_pair()
    assert channel is not None
    assert pubkey is not None
    assert len(pub_bytes) == 32


@pytest.mark.asyncio
async def test_registry_acall_and_call_async_coroutine():
    registry = SkillRegistry()

    @registry.register("async_calc")
    async def async_calc(x: int = 1, y: int = 2):
        await asyncio.sleep(0.01)
        return {"sum": x + y}

    # test acall
    res_async = await registry.acall("async_calc", {"x": 10, "y": 20})
    assert res_async == {"sum": 30}

    # test call within running event loop
    res_sync = registry.call("async_calc", {"x": 5, "y": 7})
    assert res_sync == {"sum": 12}


@pytest.mark.asyncio
async def test_node_expose_remote_protection():
    registry = SkillRegistry()

    @registry.register("private_skill", expose_remote=False)
    def private_skill():
        return {"secret": "private_data"}

    node = IMeshNode(host="127.0.0.1", port=8768, registry=registry, secret="sec123")
    await node.start()
    try:
        client = MeshClient(client_name="test-client", secret="sec123")
        client.add_peer("node", "ws://127.0.0.1:8768")
        with pytest.raises(MeshTaskError) as exc_info:
            await client.call("node", "private_skill")
        assert "not exposed for remote execution" in str(exc_info.value)
    finally:
        await node.stop()
        await client.stop()


@pytest.mark.asyncio
async def test_node_streaming_chunks():
    registry = SkillRegistry()

    @registry.register("stream_tokens")
    def stream_tokens():
        for i in range(3):
            yield f"token_{i}"

    node = IMeshNode(host="127.0.0.1", port=8769, registry=registry, secret="streamsec")
    await node.start()
    try:
        client = MeshClient(client_name="stream-client", secret="streamsec")
        client.add_peer("node", "ws://127.0.0.1:8769")

        received_chunks = []
        result = await client.stream_call(
            "node",
            "stream_tokens",
            on_chunk=lambda chunk: received_chunks.append(chunk["chunk"]),
        )
        assert received_chunks == ["token_0", "token_1", "token_2"]
        assert result.get("items") == ["token_0", "token_1", "token_2"]
    finally:
        await node.stop()
        await client.stop()


def test_gateway_bearer_auth(tmp_path: Path):
    db_path = tmp_path / "test_gw.db"
    db = GatewayDB(db_path)
    db.add_key("valid_token_123")

    app = create_app()
    app.state.gateway_db = db

    client = TestClient(app)

    # test without auth header when not strictly required: succeeds
    resp = client.post("/api/v1/execute", json={"skill": "echo", "payload": {"foo": "bar"}})
    assert resp.status_code == 200

    # test with valid auth header: succeeds
    resp = client.post(
        "/api/v1/execute",
        headers={"Authorization": "Bearer valid_token_123"},
        json={"skill": "echo", "payload": {"foo": "bar"}},
    )
    assert resp.status_code == 200

    # test with invalid auth header: 401
    resp = client.post(
        "/api/v1/execute",
        headers={"Authorization": "Bearer bad_token"},
        json={"skill": "echo", "payload": {"foo": "bar"}},
    )
    assert resp.status_code == 401

    # revoke key and check that it is now rejected
    db.revoke_key("valid_token_123")
    resp = client.post(
        "/api/v1/execute",
        headers={"Authorization": "Bearer valid_token_123"},
        json={"skill": "echo", "payload": {"foo": "bar"}},
    )
    assert resp.status_code == 401


def test_vector_store_cosine_similarity():
    vs = DistributedVectorStore()
    vs.add("orthogonal", [0.0, 1.0, 0.0])
    vs.add("parallel", [1.0, 0.0, 0.0])
    vs.add("similar", [0.9, 0.1, 0.0])

    results = vs.search([1.0, 0.0, 0.0], k=2)
    assert results[0] == "parallel"
    assert results[1] == "similar"


def test_cli_keygen_and_identity(tmp_path: Path):
    key_file = tmp_path / "ident.pem"
    assert cli_main(["keygen", "--output", str(key_file)]) == 0
    assert key_file.exists()

    assert cli_main(["identity", "--key", str(key_file)]) == 0
