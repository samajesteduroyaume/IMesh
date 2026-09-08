# IMesh

This project provides a lightweight, modular Python mesh for local AI-agent discovery, task execution, and secure peer coordination.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
openclaw-mesh --help
```

The package is named `IMesh`; the `openclaw-mesh` command remains available as a
backwards-compatible alias.

## Usage

```bash
IMesh start --port 8765
IMesh discover
IMesh call local echo --url ws://127.0.0.1:8765 --payload '{"message":"hello"}'
IMesh gateway --port 8000
```

The HTTP gateway provides health, skill listing, local execution, model listing,
and OpenAI/Anthropic-compatible endpoints. Skills are executed through the same
registry used by the WebSocket node.

The web portal available at `http://127.0.0.1:8000/` now includes:

- a supervision dashboard with quick metrics,
- peer listing with search, status/skill filters, and availability indicators,
- gateway diagnostics,
- recent logs with advanced text and level filtering,
- JSON export for diagnostics and logs,
- a manual skill testing form.

Example compatible API calls:

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw-mesh","messages":[{"role":"user","content":"hello"}]}'

curl http://127.0.0.1:8000/api/v1/portal-data
```

## ClawHub skill

The agent skill package is available at [skills/imesh/SKILL.md](skills/imesh/SKILL.md)
and is described by [clawhub.json](clawhub.json). It provides safe commands for
starting a node, discovering trusted peers, calling skills, and checking the
gateway.

## Configuration

Configuration uses the `OPENCLAW_` environment prefix:

```bash
export OPENCLAW_PSK='a-long-shared-secret'
export OPENCLAW_DEFAULT_PORT=8765
export OPENCLAW_MDNS_ENABLED=true
export OPENCLAW_WAN_ENABLED=false
export OPENCLAW_PEER_TTL_SECONDS=120
```

WAN, DHT, QUIC, and gossip are opt-in. Do not expose a node publicly without a
strong secret, identity trust policy, and transport-level protection.

## Features

- Async WebSocket node runtime
- Signed task protocol
- Skill registry
- Encrypted E2EE payload support
- Local peer discovery with mDNS and configurable peer TTL
- FastAPI gateway and enriched local portal
- OpenAI / Anthropic-compatible endpoints
- Portal search, filters, and JSON export support
- Optional hardware-aware inference backends with CPU fallback

## License

MIT
