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
    assert any(model["id"] == "openclaw-mesh" for model in resp.json()["data"])

    resp = client.post("/api/v1/execute", json={"skill": "echo", "payload": {"hello": "world"}})
    assert resp.status_code == 200
    assert resp.json()["skill"] == "echo"
    assert resp.json()["payload"] == {"hello": "world"}

    resp = client.post("/v1/chat/completions", json={"model": "openclaw-mesh", "messages": [{"role": "user", "content": "hello"}]})
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"]

    resp = client.get("/api/v1/portal-data")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["models"]
    assert "peers" in payload
    assert "diagnostics" in payload
    assert "logs" in payload
    assert "summary" in payload

    resp = client.post("/api/v1/test-skill", json={"skill": "echo", "payload": {"hello": "world"}})
    assert resp.status_code == 200
    assert resp.json()["result"]["payload"]["hello"] == "world"
