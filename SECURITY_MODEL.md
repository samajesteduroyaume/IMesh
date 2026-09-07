# Security model

## Principles

- Mutual trust is explicit and logged.
- WAN exposure requires opt-in and explicit authentication.
- Private keys use restrictive permissions.
- Replayed messages are rejected using request tracking and nonce validation.
- E2EE is optional and never used for message metadata that must stay visible to relays.

## Current implementation

The project includes:

- HMAC canonical signatures for task requests
- per-node replay detection
- private key file permissions with 0600 on write
- TrustStore support for explicit peer trust
- explicit disablement of WAN by default
- generated gateway keys are persisted in SQLite rather than returned as a
	hard-coded demo credential

## Important caveat

This is a production-oriented foundation, not a full hardened production deployment. Advanced TEE, PQC and decentralized trust features are designed as modular placeholders and remain opt-in.

## Deployment checklist

- Set `OPENCLAW_PSK` to a high-entropy secret shared only by trusted peers.
- Keep `OPENCLAW_WAN_ENABLED=false` unless WAN authentication and firewall rules
	are configured deliberately.
- Put the gateway behind TLS or a trusted reverse proxy before exposing it
	outside localhost.
- Restrict the gateway database and identity files to the service account.
- Register only skills with `expose_remote=True` when they are safe for remote
	execution; local-only skills must use `expose_remote=False`.
