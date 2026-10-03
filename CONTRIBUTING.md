# Contributing to IMesh

Thank you for contributing to IMesh.

---

## Environment

IMesh supports Python 3.10 and later.

```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Verify the setup:

```bash
IMesh version
pytest -q
```

---

## Project layout

```
IMesh/
├── openclaw_mesh/          # Core library
│   ├── protocol.py         # TaskRequest / TaskChunk / TaskResponse + HMAC signing
│   ├── registry.py         # SkillRegistry (call / acall / register)
│   ├── node.py             # IMeshNode WebSocket server
│   ├── client.py           # MeshClient WebSocket client
│   ├── discovery.py        # MeshDiscovery (mDNS + manual peers)
│   ├── crypto.py           # Ed25519 identity + TrustStore + TLS cert
│   ├── crypto_e2ee.py      # E2EE channel (X25519 + HKDF + ChaCha20-Poly1305)
│   ├── config.py           # Settings (OPENCLAW_* env prefix)
│   ├── cli.py              # Typer CLI (start, discover, call, gateway, keygen, identity, …)
│   ├── gateway/
│   │   ├── server.py       # FastAPI app factory (create_app)
│   │   └── db.py           # GatewayDB (SQLite, thread-safe)
│   ├── engines/            # AI engine stubs (inference, embedding, vector store, …)
│   └── network/            # Optional distributed primitives (DHT, gossip, relay)
├── tests/                  # pytest suite
├── scripts/
│   └── start.sh            # Portable startup script
├── skills/
│   └── imesh/SKILL.md      # ClawHub agent skill
├── clawhub.json            # ClawHub skill descriptor
├── pyproject.toml          # Package metadata and tool config
├── Dockerfile              # Minimal Docker image
├── README.md               # English documentation
├── README.fr.md            # French documentation
├── ARCHITECTURE.md         # Layered architecture reference
├── SECURITY_MODEL.md       # Threat model and deployment checklist
└── CONTRIBUTING.md         # This file
```

---

## Before a pull request

All of the following must pass on the target Python version:

```bash
# Code formatting
python -m black --check --target-version py310 openclaw_mesh tests

# Linting
python -m ruff check openclaw_mesh tests

# Type checking (optional but encouraged)
python -m mypy openclaw_mesh --ignore-missing-imports

# Tests
pytest -q
```

### Checklist

- [ ] The existing public API is preserved or changes are documented.
- [ ] A test is added for every new behaviour.
- [ ] Optional dependencies are imported lazily inside the function or a `try/except ImportError` block; a missing dependency must never break the core mesh.
- [ ] No secret, private key, or local database is committed.
- [ ] Any new `OPENCLAW_*` environment variable is documented in `config.py` and in `README.md` (Configuration reference section).

---

## Adding a skill

Register skills in `openclaw_mesh/registry.py` (for built-in skills) or from user code:

```python
from openclaw_mesh.registry import SkillRegistry

registry = SkillRegistry()

@registry.register(name="my_skill", description="What it does")
def my_skill(x: int) -> dict:
    return {"result": x * 2}
```

Rules for built-in skills:
- Must not import any optional dependency at module level.
- Must default to `expose_remote=True` only if safe for any caller on the LAN.
- Must include a unit test in `tests/`.

---

## Adding an engine

Engines live in `openclaw_mesh/engines/`. They must:
1. Catch `ImportError` for every optional dependency (`torch`, `mlx`, `openvino`, etc.) at the point of import, not at module level.
2. Expose a stable interface matching the existing engines.
3. Register a graceful CPU fallback.
4. Add a test in `tests/test_engines.py`.

---

## Commits and pull requests

- Describe the problem solved and the expected behaviour.
- List the validation commands run.
- Reference the relevant `OPENCLAW_*` variable if configuration changes.
- Use [Conventional Commits](https://www.conventionalcommits.org/) prefixes: `fix:`, `feat:`, `docs:`, `test:`, `refactor:`, `chore:`.

---

## Compatibility

The package name is `IMesh`. The `openclaw-mesh` command remains a backward-compatible CLI alias. Any change to the public CLI interface must be documented in `README.md` and in `ARCHITECTURE.md`.

The minimum supported Python version is **3.10**. Do not use language or stdlib features unavailable in 3.10.
