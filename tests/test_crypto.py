import json
import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import x25519

from openclaw_mesh.crypto import NodeIdentity, TrustStore
from openclaw_mesh.crypto_e2ee import E2EEChannel, ReplayError, derive_shared_key


def test_ed25519_identity_roundtrip(tmp_path: Path):
    key_path = tmp_path / "identity.pem"
    identity = NodeIdentity.generate()
    identity.save(key_path)
    assert key_path.stat().st_mode & 0o777 == 0o600

    loaded = NodeIdentity.load(key_path)
    payload = b"hello mesh"
    sig = loaded.sign(payload)
    assert loaded.verify(payload, sig)


def test_trust_store_persistence(tmp_path: Path):
    trust_store = TrustStore(path=tmp_path / "trust.json")
    trust_store.add("node-a", "pubkey-value")
    assert trust_store.is_trusted("node-a")
    trust_store.revoke("node-a")
    assert not trust_store.is_trusted("node-a")


def test_e2ee_encrypt_decrypt_and_replay_detection():
    alice = E2EEChannel()
    bob = E2EEChannel()
    alice.set_remote_public_key(bob.local_priv.public_key())
    bob.set_remote_public_key(alice.local_priv.public_key())

    nonce = b"\x01" * 12
    ctxt = alice.encrypt({"hello": "world"}, associated_data=b"ad", nonce=nonce)
    assert bob.decrypt(ctxt, associated_data=b"ad", nonce=nonce) == {"hello": "world"}

    now = time.time()
    alice.validate_and_record(nonce, timestamp=now)
    with pytest.raises(ReplayError):
        alice.validate_and_record(nonce)


def test_x25519_derive_key():
    a = x25519.X25519PrivateKey.generate()
    b = x25519.X25519PrivateKey.generate()
    key = derive_shared_key(a, b.public_key())
    assert len(key) == 32
    assert key == derive_shared_key(b, a.public_key())
