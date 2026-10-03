# IMesh Architecture

IMesh follows a layered, staged architecture. Each layer is independently testable and can be replaced or extended without breaking the others.

---

## Layers

### 1 · Protocol and core transport

**Module:** `openclaw_mesh/protocol.py`, `openclaw_mesh/crypto.py`, `openclaw_mesh/crypto_e2ee.py`

- **`TaskRequest`** — signed task envelope with skill name, payload, origin, timestamp and HMAC signature.
- **`TaskChunk`** — streaming chunk frame sent by a node before the final `TaskResponse`.
- **`TaskResponse`** — result or error envelope with an `ok` flag and `handled_by` field.
- **`parse_message`** — deserialises and validates any incoming JSON frame into one of the three types.
- **HMAC signing** — canonical string (`request_id|origin|skill|ts|payload`) signed with SHA-256 and the pre-shared key.
- **Replay protection** — per-node `_seen_requests` dict; request IDs expire after 60 seconds.
- **Ed25519 identity** (`NodeIdentity`) — persistent keypair, PEM serialisation with `0600` file permissions.
- **TrustStore** — JSON-backed per-peer trust entries with `add` / `revoke` / `is_trusted`.
- **E2EE** (`E2EEChannel`) — X25519 ephemeral key exchange + HKDF (SHA-256) key derivation + ChaCha20-Poly1305 AEAD. Nonce-based replay guard per channel.

### 2 · Skill registry

**Module:** `openclaw_mesh/registry.py`

- `SkillDefinition` — name, description, callable, optional Pydantic schema, `expose_remote` flag.
- `SkillRegistry.register()` — decorator for sync, async and generator skills.
- `SkillRegistry.call()` — synchronous dispatch; safe inside or outside an active event loop (uses `ThreadPoolExecutor` if needed).
- `SkillRegistry.acall()` — native async dispatch; awaits coroutines, iterates async generators.
- `expose_remote=False` — skill-level access control enforced both in `IMeshNode._handle_request` and by convention in the gateway.
- Built-in skills: `echo`, `openclaw_info`, `system_info`, `_health`, `_describe_skills`.

### 3 · Node runtime

**Module:** `openclaw_mesh/node.py`

- `IMeshNode` — async WebSocket server wrapping `websockets.serve`.
- On `start()`: bind server → start mDNS discovery → **publish remote skills via mDNS**.
- Per-connection handler `_handle_connection` — receives `TaskRequest` frames and dispatches them.
- `_handle_request` — validates replay, signature, skill existence and `expose_remote` before acquiring the active-task slot.
- `_execute_skill` — detects function type before dispatching:
  - `asyncio.iscoroutinefunction` → `await func(**payload)`
  - `inspect.isgeneratorfunction` → iterate synchronously, send `TaskChunk` over WebSocket per item
  - `inspect.isasyncgenfunction` → async iteration, send `TaskChunk` per item
  - otherwise → `asyncio.to_thread(invoke)`
- Streaming: `TaskChunk` frames are sent to the WebSocket before the final `TaskResponse(streamed=True)`.
- `MeshServer` — backward-compatible alias for `IMeshNode`.

### 4 · Client

**Module:** `openclaw_mesh/client.py`

- `MeshClient` — manages peer endpoints and WebSocket connections.
- Connection reuse: returns an existing open socket when available.
- `call()` — send a signed `TaskRequest`, receive a `TaskResponse`; raises `MeshTaskError` if `ok=False`.
- `stream_call()` — collects `TaskChunk` frames via an optional `on_chunk` callback, then returns the final result.
- `MeshTaskError` — typed exception carrying `request_id` for traceability.
- `discover_skills()` / `check_health()` — convenience wrappers around `_describe_skills` and `_health`.
- `find_best_peer_for_skill()` — selects the first peer advertising a given skill.

### 5 · Discovery

**Module:** `openclaw_mesh/discovery.py`

- `MeshDiscovery` — Zeroconf/mDNS service browser and advertiser.
- Service type: `_openclawmesh._tcp.local.`
- `start()` — creates `Zeroconf()` and `ServiceBrowser` (skipped gracefully if Zeroconf is absent).
- `publish(skills)` — runs `zc.register_service()` via `asyncio.to_thread` to avoid `EventLoopBlocked`.
- `stop()` — unregisters the published service and closes Zeroconf via `asyncio.to_thread`.
- `add_service()` — adds or updates a peer on discovery.
- `remove_service()` — marks the peer `reachable=False` (does not delete from the registry).
- `discover_now()` — returns all peers with up-to-date TTL-based reachability.
- `register_manual_peer()` — adds a peer without mDNS.

### 6 · Gateway and portal

**Module:** `openclaw_mesh/gateway/`

- `create_app()` — factory that builds the FastAPI application with all routes, CORS middleware, and shared state.
- `app.state.gateway_db` — `GatewayDB` instance accessible to all routes (including `check_auth`).
- `app.state.discovery` — `MeshDiscovery` instance providing peer data.
- `app.state.logs` — in-memory log ring buffer (max 200 entries).
- **`check_auth(request)`** — reads Bearer token from `Authorization` header, validates against `app.state.gateway_db`. Raises `401` on invalid tokens; no-op when `OPENCLAW_AUTH_REQUIRED=false` and no token provided.
- **`invoke_skill()`** — calls `skill_registry.acall()` (fully async, no blocking).
- `/` (HTML) — self-contained portal with embedded CSS and JavaScript; auto-refresh every 5 s.

**`GatewayDB`** (`openclaw_mesh/gateway/db.py`):
- SQLite backend with `check_same_thread=False` and `threading.Lock` for multi-thread safety.
- `add_key()`, `revoke_key()`, `is_valid_key()`, `list_keys()`.

### 7 · Optional AI engines

**Module:** `openclaw_mesh/engines/`

All engines are lazily loaded. Missing optional dependencies (torch, mlx, openvino) are caught silently and fall back to CPU or stubs.

| Class | Role |
|---|---|
| `HardwareDetector` | Probes CUDA → ROCm → OpenVINO → MLX → CPU |
| `UniversalInferenceEngine` | Stub inference with hardware-aware device selection |
| `UniversalEmbeddingEngine` | Stub text encoder |
| `AutoModelManager` | Model selection from an allowlist |
| `ModelCache` | LRU cache for loaded models |
| `SemanticKVCache` | LRU key-value cache for semantic results |
| `DistributedVectorStore` | In-memory vector store with **cosine similarity** ranking |
| `DistributedRAG` | Substring-based retrieval over ingested text chunks |
| `DistributedMoEOrchestrator` | Round-robin expert routing stub |
| `MultiModalEngine` | Stub multi-modal processing |

### 8 · Network primitives (opt-in)

**Module:** `openclaw_mesh/network/`

| Class | Role |
|---|---|
| `DHTNode` | Local DHT with TTL-based record expiry |
| `GossipNode` | Pub-sub with SHA-256 message deduplication |
| `RelayNode` | Simple relay registry |

These provide deterministic local primitives. A future WAN transport can build on them without changing the public task API.

---

## Runtime flows

### 1 · Inbound task execution (WebSocket)

```
Client                          IMeshNode
  │                               │
  │── TaskRequest (signed JSON) ──►│
  │                               │ validate replay
  │                               │ verify HMAC signature
  │                               │ check skill exists + expose_remote
  │                               │ acquire active task slot
  │                               │ execute skill
  │                             [if generator]
  │◄── TaskChunk (index 0) ───────│
  │◄── TaskChunk (index 1) ───────│
  │                               │
  │◄── TaskResponse (ok=True) ────│
```

### 2 · Local gateway execution

```
HTTP Client ──► FastAPI endpoint
                    │ check_auth (Bearer token → GatewayDB)
                    │ skill_registry.acall(skill_name, payload)
                    │   → await coroutine / run sync in thread
                    └──► JSON response
```

### 3 · mDNS peer discovery

```
Node starts
  │
  ├── discovery.start()  → Zeroconf browser on _openclawmesh._tcp
  │
  └── discovery.publish(skills)  → register_service via to_thread
                                     (prevents EventLoopBlocked)

Remote peer appears
  │
  └── add_service() → PeerInfo added to discovery.peers

Remote peer disappears
  │
  └── remove_service() → peer.reachable = False
```

---

## Design principles

1. **Optional dependencies** — all advanced modules are imported lazily; the core WebSocket mesh works with only the declared `pyproject.toml` dependencies.
2. **Local-first** — default runtime is a local mesh; WAN, DHT, QUIC and GossipSub require explicit opt-in.
3. **Security by default** — HMAC signing, replay protection and `expose_remote` access control are enforced unconditionally; they cannot be silently disabled.
4. **Async-safe dispatch** — `SkillRegistry.acall` is used in all async contexts; `call` uses `ThreadPoolExecutor` if called from inside a running event loop.
5. **Thread safety** — `GatewayDB` uses `threading.Lock` and `check_same_thread=False` for safe multi-threaded gateway access.
