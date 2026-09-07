from fastapi.testclient import TestClient

from openclaw_mesh.gateway.server import create_app


def test_gateway_endpoints():
    app = create_app()
    client = TestClient(app)

    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    resp = client.get("/api/v1/models")
    assert resp.status_code == 200
    assert "openclaw-mesh" in resp.json()["data"]

    resp = client.post("/api/v1/execute", json={"skill": "echo", "payload": {"hello": "world"}})
    assert resp.status_code == 200
    assert resp.json()["skill"] == "echo"
    assert resp.json()["payload"] == {"hello": "world"}

    resp = client.post("/v1/chat/completions", json={"messages": []})
    assert resp.status_code == 200
