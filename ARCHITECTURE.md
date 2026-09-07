# Architecture IMesh

This repository follows a staged architecture:

1. Core transport and protocol
   - message model for task requests, chunks and responses
   - registry of skills
   - secure configuration and singleton settings
2. Node runtime
   - WebSocket task server
   - multi-request orchestration and timeout handling
   - local execution with sync/async/generator support
3. Local discovery and client access
   - peer registry
   - mDNS discovery with graceful fallback
4. Gateway and portal
   - FastAPI exposure
   - API keys and local portal
5. Optional AI and distributed features
   - hardware detection and model manager
   - distributed routing, DHT and gossip modules

## Runtime flows

1. A client creates and HMAC-signs a `TaskRequest`.
2. The node validates the signature, rejects duplicate request IDs, and checks
   the skill registry before executing it under a timeout.
3. The gateway reuses the same registry for local HTTP execution; it does not
   maintain a second implementation of skills.
4. LAN discovery advertises `_openclawmesh._tcp` services when mDNS is enabled,
   while manual peer registration remains available for controlled networks.

The DHT and gossip objects currently provide deterministic local primitives. A
future WAN transport can build on them without changing the public task API.

## Design notes

- All modules are loaded lazily and are optional when dependencies are absent.
- The default runtime remains a local WebSocket mesh; WAN and advanced transports are disabled by default.
- Security standards are enforced by default; they must not be silently disabled.
