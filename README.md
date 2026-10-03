# IMesh

> **Local-first intelligent mesh network for OpenClaw AI agents.**

IMesh provides a lightweight, modular Python mesh that lets autonomous AI agents discover each other, execute tasks remotely, share capabilities, and coordinate securely — all without a central server.

---

## Table of contents

- [Quick start](#quick-start)
- [CLI reference](#cli-reference)
- [Gateway & portal](#gateway--portal)
- [API compatibility](#api-compatibility)
- [Authentication](#authentication)
- [Skill registry](#skill-registry)
- [ClawHub skill](#clawhub-skill)
- [Configuration reference](#configuration-reference)
- [Feature overview](#feature-overview)
- [Architecture overview](#architecture-overview)
- [License](#license)

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Verify installation
IMesh version
IMesh --help
```

> The package is named `IMesh`. The `openclaw-mesh` command is available as a backward-compatible alias.

---

## CLI reference

### Start a local mesh node

```bash
IMesh start --host 127.0.0.1 --port 8765
# or equivalently
IMesh node --host 127.0.0.1 --port 8765 --no-wan
```

The node starts an async WebSocket server, registers itself on the local mDNS service (`_openclawmesh._tcp`) and publishes its available remote skills.

### Discover peers on the LAN

```bash
IMesh discover
```

Returns a JSON list of discovered peers with their name, host, port, skills, and reachability status.

### Call a skill on a peer

```bash
IMesh call local echo \
  --url ws://127.0.0.1:8765 \
  --payload '{"message": "hello"}'
```

### Start the HTTP gateway

```bash
IMesh gateway --host 127.0.0.1 --port 8000
```

### Identity management

```bash
# Generate a new Ed25519 identity key
IMesh keygen
IMesh keygen --output /path/to/identity.pem

# Show the current node identity
IMesh identity
IMesh identity --key /path/to/identity.pem
```

### Other commands

```bash
IMesh health    # Local health check (JSON)
IMesh version   # Display version string
IMesh peers     # Hint: use 'discover' for mDNS-based discovery
```

---

## Gateway & portal

Start the gateway, then open `http://127.0.0.1:8000/` in your browser.

```bash
IMesh gateway --host 127.0.0.1 --port 8000
```

### Portal features

| Section | Description |
|---|---|
| **Dashboard** | Real-time summary: peer count, reachable peers, skill count, log count |
| **Peers** | Searchable table with status/skill filters and reachability indicators |
| **Diagnostics** | Gateway settings, feature flags, and live skill list |
| **Logs** | Recent events with text and level filtering, JSON export |
| **Skill tester** | Interactive form to call any registered skill from the browser |

The portal auto-refreshes every 5 seconds.

### REST endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health probe |
| `GET` | `/api/v1/skills` | List exposed skills |
| `GET` | `/api/v1/peers` | List discovered peers |
| `GET` | `/api/v1/models` | List available models |
| `GET` | `/api/v1/portal-data` | Full portal data (summary, peers, diagnostics, logs) |
| `POST` | `/api/v1/execute` | Execute a skill by name |
| `POST` | `/api/v1/test-skill` | Same as execute (for portal) |
| `POST` | `/api/v1/checkout/free-key` | Issue a new API key |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat endpoint |
| `POST` | `/v1/messages` | Anthropic-compatible messages endpoint |

---

## API compatibility

### OpenAI

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw-mesh","messages":[{"role":"user","content":"hello"}]}'
```

You can target a specific skill by adding `"skill": "skill_name"` to the body, or by prefixing the message content with `skill: skill_name` or `call skill_name`.

### Anthropic

```bash
curl -X POST http://127.0.0.1:8000/v1/messages \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw-mesh","messages":[{"role":"user","content":"hello"}]}'
```

---

## Authentication

By default the gateway runs without authentication (suitable for local development). To require API keys on all execution endpoints:

```bash
export OPENCLAW_AUTH_REQUIRED=true
IMesh gateway --host 127.0.0.1 --port 8000
```

**Issue an API key:**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/checkout/free-key
# → {"api_key": "imesh_..."}
```

**Use the key:**

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer imesh_..." \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw-mesh","messages":[{"role":"user","content":"hello"}]}'
```

Endpoints protected by authentication: `/api/v1/execute`, `/v1/chat/completions`, `/v1/messages`.
Keys are stored in the SQLite database at `OPENCLAW_GATEWAY_DB_PATH`.

---

## Skill registry

### Built-in skills

| Skill | Description |
|---|---|
| `echo` | Returns the input payload unchanged |
| `openclaw_info` | Returns mesh name and version |
| `system_info` | Returns platform and Python version |
| `_health` | Health check — returns `{"status": "ok"}` |
| `_describe_skills` | Lists all skills in OpenAI tool format |

### Register a custom skill

```python
from openclaw_mesh.registry import SkillRegistry

registry = SkillRegistry()

# Synchronous skill
@registry.register(name="add", description="Add two numbers")
def add(x: int, y: int) -> dict:
    return {"sum": x + y}

# Asynchronous skill
@registry.register(name="fetch", description="Fetch a URL")
async def fetch(url: str) -> dict:
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return {"status": r.status_code}

# Streaming skill (generator)
@registry.register(name="count", description="Stream numbers")
def count(n: int = 5):
    for i in range(n):
        yield i

# Private skill (not accessible remotely)
@registry.register(name="secret", expose_remote=False)
def secret():
    return {"value": "only local"}
```

### Call a skill programmatically

```python
import asyncio
from openclaw_mesh.registry import get_default_registry

registry = get_default_registry()

# Sync call (safe inside or outside an event loop)
result = registry.call("echo", {"hello": "world"})

# Async call (preferred in async contexts)
async def main():
    result = await registry.acall("echo", {"hello": "world"})
```

### Use the WebSocket client

```python
import asyncio
from openclaw_mesh.client import MeshClient, MeshTaskError

async def main():
    client = MeshClient(secret="my-psk")
    client.add_peer("node-a", "ws://192.168.1.10:8765")
    try:
        result = await client.call("node-a", "echo", {"ping": True})
        print(result)
    except MeshTaskError as e:
        print(f"Task failed: {e}")
    finally:
        await client.stop()

asyncio.run(main())
```

### Stream chunks from a generator skill

```python
async def main():
    client = MeshClient(secret="my-psk")
    client.add_peer("node-a", "ws://127.0.0.1:8765")

    chunks = []
    result = await client.stream_call(
        "node-a",
        "count",
        {"n": 5},
        on_chunk=lambda c: chunks.append(c["chunk"]),
    )
    print(chunks)   # ["0", "1", "2", "3", "4"]
    print(result)   # {"items": ["0", "1", "2", "3", "4"]}
```

---

## ClawHub skill

The agent skill package is available at [`skills/imesh/SKILL.md`](skills/imesh/SKILL.md) and described by [`clawhub.json`](clawhub.json).

It provides safe commands for starting a node, discovering trusted peers, calling skills, checking the gateway, and managing identities.

---

## Configuration reference

All settings use the `OPENCLAW_` environment prefix and can also be defined in a `.env` file.

| Variable | Default | Description |
|---|---|---|
| `OPENCLAW_NODE_NAME` | `openclaw-node` | Identifier advertised on mDNS |
| `OPENCLAW_CLIENT_NAME` | `openclaw-client` | Identifier used in task requests |
| `OPENCLAW_DEFAULT_HOST` | `127.0.0.1` | Node bind address |
| `OPENCLAW_DEFAULT_PORT` | `8765` | Node WebSocket port |
| `OPENCLAW_PSK` | *(none)* | Pre-shared secret for HMAC signing |
| `OPENCLAW_MDNS_ENABLED` | `true` | Enable mDNS peer discovery |
| `OPENCLAW_WAN_ENABLED` | `false` | Enable WAN transport (opt-in) |
| `OPENCLAW_DHT_ENABLED` | `false` | Enable DHT routing (opt-in) |
| `OPENCLAW_QUIC_ENABLED` | `false` | Enable QUIC transport (opt-in) |
| `OPENCLAW_GOSSIPSUB_ENABLED` | `false` | Enable GossipSub (opt-in) |
| `OPENCLAW_E2EE_ENABLED` | `false` | Enable end-to-end encryption |
| `OPENCLAW_IDENTITY_KEY_PATH` | `./.openclaw_identity.pem` | Ed25519 private key file |
| `OPENCLAW_TRUST_STORE_PATH` | `./.openclaw_trust_store.json` | Peer trust store |
| `OPENCLAW_MAX_ACTIVE_TASKS` | `32` | Max concurrent tasks per node |
| `OPENCLAW_MAX_QUEUED_TASKS` | `128` | Max queued tasks |
| `OPENCLAW_TASK_TIMEOUT` | `30.0` | Task execution timeout (seconds) |
| `OPENCLAW_MAX_OUTPUT_BYTES` | `1000000` | Max response payload size |
| `OPENCLAW_GATEWAY_HOST` | `127.0.0.1` | Gateway bind address |
| `OPENCLAW_GATEWAY_PORT` | `8000` | Gateway HTTP port |
| `OPENCLAW_GATEWAY_DB_PATH` | `./openclaw_gateway.db` | SQLite database path |
| `OPENCLAW_PEER_TTL_SECONDS` | `120` | Peer expiry after last seen (seconds) |
| `OPENCLAW_AUTH_REQUIRED` | `false` | Require Bearer token on execution endpoints |
| `OPENCLAW_LOG_LEVEL` | `INFO` | Log level |

> **WAN, DHT, QUIC, and GossipSub** are opt-in. Do not expose a node publicly without a strong `OPENCLAW_PSK`, a trust policy, and a TLS reverse proxy.

---

## Feature overview

- **Async WebSocket node** — non-blocking, concurrent task handling with configurable limits
- **HMAC-signed task protocol** — canonical request signing with replay protection
- **Skill registry** — sync, async and generator skills; `expose_remote` access control enforced at protocol level
- **Real-time streaming** — generator skills stream `TaskChunk` frames over WebSocket
- **mDNS discovery** — zero-config LAN peer discovery with TTL-based expiry and service unregistration
- **Ed25519 identity** — persistent keypair per node; trust store for peer authorisation
- **E2EE payloads** — X25519 key exchange + ChaCha20-Poly1305 encryption with replay guard
- **FastAPI gateway** — REST API, web portal, JSON export
- **OpenAI & Anthropic compatibility** — drop-in endpoints for LLM clients
- **Bearer token authentication** — optional API key protection stored in SQLite
- **Hardware-aware engines** — CUDA / ROCm / OpenVINO / MLX / CPU fallback detection
- **Distributed primitives** — DHT, gossip, relay, vector store (cosine similarity), RAG, MoE (opt-in stubs, ready for WAN)
- **Docker-ready** — minimal `Dockerfile` included

---

## Architecture overview

```
┌────────────────────────────────────────────────────────────────┐
│                    OpenClaw Agent / LLM Client                 │
│         (OpenAI SDK · Anthropic SDK · ClawHub skill)           │
└────────────────────────┬───────────────────────────────────────┘
                         │ HTTP / Bearer token
          ┌──────────────▼───────────────┐
          │        IMesh Gateway          │
          │  FastAPI · Portal · REST API  │
          └──────────┬───────────────────┘
                     │ SkillRegistry.acall()
          ┌──────────▼──────────┐
          │  Local SkillRegistry │   ◄── expose_remote guard
          └──────────┬──────────┘
                     │ WebSocket (HMAC-signed TaskRequest)
     ┌───────────────┼────────────────────┐
     │               │                    │
┌────▼────┐    ┌─────▼────┐    ┌──────────▼───┐
│  Node A  │   │  Node B  │   │    Node C     │
│  (CPU)   │   │  (CUDA)  │   │  (Apple MLX)  │
└──────────┘   └──────────┘   └───────────────┘
     │               │                    │
     └───── mDNS _openclawmesh._tcp ──────┘
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the detailed staged architecture and runtime flows.

---

## License

MIT — see [`LICENSE`](LICENSE).
