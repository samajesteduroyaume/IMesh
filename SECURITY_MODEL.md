# Security model

## Principles

1. **Explicit mutual trust.** Peers are only trusted after explicit registration in the `TrustStore`. No peer is implicitly trusted by virtue of sharing the network.
2. **Signed messages.** Every `TaskRequest` carries an HMAC-SHA256 canonical signature. A node will reject any request whose signature does not match its pre-shared key.
3. **Replay protection.** Request IDs are tracked per-node for 60 seconds. A replayed request ID is rejected immediately.
4. **Remote access control.** Each skill carries an `expose_remote` flag. Skills with `expose_remote=False` are silently registered locally but raise a `PermissionError` if called over WebSocket.
5. **Opt-in WAN.** The node operates on the LAN by default. WAN, DHT, QUIC and GossipSub require explicit environment variables.
6. **Secure key storage.** Identity private keys are written with `0600` permissions. They are never logged or transmitted.
7. **Optional E2EE.** Payload-level encryption is available via `E2EEChannel` (X25519 + HKDF-SHA256 + ChaCha20-Poly1305). It is disabled by default and must not be applied to message metadata visible to relays.

---

## Current implementation

### Transport layer

| Mechanism | Status | Detail |
|---|---|---|
| HMAC-SHA256 request signing | ✅ Active | Canonical string: `request_id\|origin\|skill\|ts\|payload` |
| Replay detection | ✅ Active | Per-node TTL-based `_seen_requests` dict (60 s window) |
| `expose_remote` enforcement | ✅ Active | Checked in `IMeshNode._handle_request` before execution |
| WAN disabled by default | ✅ Active | `OPENCLAW_WAN_ENABLED=false` |
| mDNS isolation | ✅ Active | Nodes ignore themselves in `add_service` |

### Identity and trust

| Mechanism | Status | Detail |
|---|---|---|
| Ed25519 keypair | ✅ Active | `NodeIdentity.generate()` / `.save()` / `.load()` |
| `0600` file permissions | ✅ Active | Set on `.save()` |
| TrustStore | ✅ Active | JSON file; `add` / `revoke` / `is_trusted` |
| E2EE channel | ✅ Available | X25519 + HKDF-SHA256 + ChaCha20-Poly1305; disabled by default |
| Ephemeral TLS cert generation | ✅ Fixed | Ed25519 with `algorithm=None` as required by the spec |

### Gateway

| Mechanism | Status | Detail |
|---|---|---|
| API key issuance | ✅ Active | `POST /api/v1/checkout/free-key` → `imesh_<24-byte-token>` |
| Bearer token validation | ✅ Active | `check_auth` reads from `app.state.gateway_db` |
| SQLite thread safety | ✅ Active | `check_same_thread=False` + `threading.Lock` |
| Key revocation | ✅ Active | `GatewayDB.revoke_key()` sets `enabled=0` |
| Auth enforcement (optional) | ✅ Active | `OPENCLAW_AUTH_REQUIRED=true` |
| CORS | ✅ Active | Open by default (suitable for local dev); restrict in production |

---

## Threat model

### In scope

- **Unauthorised skill invocation** — prevented by HMAC signature + `expose_remote` enforcement.
- **Replay attacks** — prevented by request ID deduplication.
- **Rogue peer impersonation** — mitigated by TrustStore; peers not in the store are not trusted.
- **Payload interception** — mitigated by optional E2EE on the WebSocket layer.
- **Unauthorised gateway access** — mitigated by Bearer token authentication when `OPENCLAW_AUTH_REQUIRED=true`.

### Out of scope (not hardened for production)

- **Transport-level TLS** — WebSocket traffic is unencrypted by default. Put the node and gateway behind a TLS terminator (nginx, Caddy) before any non-local exposure.
- **Distributed trust / PKI** — the current TrustStore is local and manual. Automated certificate issuance and revocation are future work.
- **Post-quantum cryptography** — Ed25519 and X25519 are classical algorithms. PQC is a planned optional upgrade.
- **Trusted Execution Environments (TEE)** — not implemented.

---

## Deployment checklist

Before exposing IMesh outside `localhost`:

- [ ] Set `OPENCLAW_PSK` to a high-entropy random secret (≥ 32 bytes, base64 or hex).
- [ ] Generate a node identity: `IMesh keygen`.
- [ ] Register expected peers in the TrustStore.
- [ ] Keep `OPENCLAW_WAN_ENABLED=false` unless WAN authentication and firewall rules are deliberately configured.
- [ ] Place the gateway behind TLS (nginx, Caddy, or similar) before external exposure.
- [ ] Set `OPENCLAW_AUTH_REQUIRED=true` and issue API keys for all gateway clients.
- [ ] Restrict the gateway database (`OPENCLAW_GATEWAY_DB_PATH`) and identity key (`OPENCLAW_IDENTITY_KEY_PATH`) to the service account user.
- [ ] Register only skills with `expose_remote=True` when they are safe for remote execution. Local-only skills must use `expose_remote=False`.
- [ ] Never commit `.env` files, identity keys, or the gateway SQLite database.
- [ ] Configure CORS to allow only known origins in production.

---

## Key lifecycle

```
IMesh keygen [--output path]
  → generate Ed25519 PrivateKey
  → save PEM to identity_key_path (chmod 0600)
  → print public key (JSON)

IMesh identity [--key path]
  → load existing PEM
  → print node_name + key_path + public_key (JSON)

TrustStore.add(node_name, pubkey_pem)
  → persisted to trust_store_path

TrustStore.revoke(node_name)
  → sets trusted=false in trust_store_path
```

---

## E2EE channel lifecycle

```python
# Alice initiates
alice = E2EEChannel()
alice_pubkey, alice_pub_bytes = alice.local_priv.public_key(), ...

# Bob receives Alice's public key
bob = E2EEChannel()
bob.set_remote_public_key(alice.local_priv.public_key())
alice.set_remote_public_key(bob.local_priv.public_key())

# Encrypt / decrypt
nonce = os.urandom(12)
ciphertext = alice.encrypt({"hello": "world"}, nonce=nonce)
plaintext  = bob.decrypt(ciphertext, nonce=nonce)   # → {"hello": "world"}

# Replay guard
alice.validate_and_record(nonce)          # OK first time
alice.validate_and_record(nonce)          # → ReplayError
```

Shared key derivation always uses **HKDF-SHA256** (via `derive_shared_key`) rather than the raw X25519 output, ensuring the key is properly domain-separated.
