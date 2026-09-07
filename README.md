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

## Configuration

Configuration uses the `OPENCLAW_` environment prefix:

```bash
export OPENCLAW_PSK='a-long-shared-secret'
export OPENCLAW_DEFAULT_PORT=8765
export OPENCLAW_MDNS_ENABLED=true
export OPENCLAW_WAN_ENABLED=false
```

WAN, DHT, QUIC, and gossip are opt-in. Do not expose a node publicly without a
strong secret, identity trust policy, and transport-level protection.

## Features

- Async WebSocket node runtime
- Signed task protocol
- Skill registry
- Encrypted E2EE payload support
- Local peer discovery with mDNS
- FastAPI gateway and local portal
- Optional hardware-aware inference backends with CPU fallback

## License

MIT
