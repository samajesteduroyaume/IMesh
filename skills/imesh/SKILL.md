---
name: imesh
description: Operate an IMesh Python mesh for discovering trusted peers, starting a local node, calling remote skills, and checking mesh health.
metadata:
  openclaw:
    requires:
      bins:
        - IMesh
    install:
      - kind: python
        package: IMesh
        command: python -m pip install -e .
---

# IMesh

Use this skill to operate the IMesh local-first AI-agent mesh from a shell.
IMesh uses an asynchronous WebSocket node, signed task requests, optional mDNS
discovery, and a FastAPI gateway.

## Safety rules

- Keep WAN disabled unless the operator explicitly requests it.
- Never expose a remote skill unless it is registered with
  `expose_remote=True` and the peer is trusted.
- Set `OPENCLAW_PSK` to a long random shared secret before connecting peers.
- Do not print, copy, or commit private keys, API keys, `.env` files, or the
  gateway database.
- Prefer `127.0.0.1` while testing. Ask for explicit confirmation before using
  `0.0.0.0` or a public address.

## Common operations

Start a local node:

```bash
IMesh start --host 127.0.0.1 --port 8765
```

Discover peers on the local network:

```bash
IMesh discover
```

Call a skill on a trusted peer:

```bash
IMesh call local echo \
  --url ws://127.0.0.1:8765 \
  --payload '{"message":"hello"}'
```

Start the HTTP gateway locally:

```bash
IMesh gateway --host 127.0.0.1 --port 8000
```

Check the gateway:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## Configuration

Configuration is read from environment variables with the `OPENCLAW_` prefix:

```bash
export OPENCLAW_PSK='replace-with-a-long-random-secret'
export OPENCLAW_DEFAULT_PORT=8765
export OPENCLAW_MDNS_ENABLED=true
export OPENCLAW_WAN_ENABLED=false
```

## Troubleshooting

- If no peers are returned, check that mDNS is enabled and that the local
  firewall permits the service.
- If a call is rejected, check that both peers use the same `OPENCLAW_PSK`.
- If a skill is unknown, inspect `/api/v1/skills` or the node registry.
- Run `python -m pytest -q` after changing the installation or runtime.
