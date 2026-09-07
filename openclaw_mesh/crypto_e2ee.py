from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from collections.abc import Sequence
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class ReplayError(RuntimeError):
    pass


class E2EEChannel:
    def __init__(self, local_priv: x25519.X25519PrivateKey | None = None, remote_pub: x25519.X25519PublicKey | None = None) -> None:
        self.local_priv = local_priv or x25519.X25519PrivateKey.generate()
        self.remote_pub = remote_pub
        self._shared_key: bytes | None = None
        self._replay_cache: dict[str, int] = {}
        self._max_replay = 256
        self.aead = None
        if remote_pub is not None:
            self._shared_key = self.local_priv.exchange(remote_pub)
            self.aead = ChaCha20Poly1305(self._shared_key)

    def _shared_secret(self) -> bytes:
        if self._shared_key is None:
            if self.remote_pub is None:
                raise ValueError("remote public key required")
            self._shared_key = self.local_priv.exchange(self.remote_pub)
            self.aead = ChaCha20Poly1305(self._shared_key)
        return self._shared_key

    @classmethod
    def generate_pair(cls) -> tuple["E2EEChannel", x25519.X25519PublicKey, bytes]:
        local = cls()
        return local, local.local_priv.public_key(), local._shared_secret()

    def set_remote_public_key(self, public_key: x25519.X25519PublicKey) -> None:
        self.remote_pub = public_key
        self._shared_key = self.local_priv.exchange(public_key)
        self.aead = ChaCha20Poly1305(self._shared_key)

    def encrypt(self, payload: Any, associated_data: bytes | None = None, nonce: bytes | None = None) -> bytes:
        if self.aead is None:
            raise ValueError("remote public key required before encryption")
        if nonce is None:
            nonce = os.urandom(12)
        if associated_data is None:
            associated_data = b""
        if isinstance(payload, (dict, list)):
            plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        elif isinstance(payload, str):
            plaintext = payload.encode("utf-8")
        elif isinstance(payload, bytes):
            plaintext = payload
        else:
            raise TypeError("unsupported payload type")
        return self.aead.encrypt(nonce, plaintext, associated_data)

    def decrypt(self, ciphertext: bytes, associated_data: bytes | None = None, nonce: bytes | None = None) -> Any:
        if self.aead is None:
            raise ValueError("remote public key required before decryption")
        if nonce is None:
            raise ValueError("nonce required")
        if associated_data is None:
            associated_data = b""
        plaintext = self.aead.decrypt(nonce, ciphertext, associated_data)
        try:
            return json.loads(plaintext.decode("utf-8"))
        except Exception:
            return plaintext

    def validate_and_record(self, nonce: bytes, timestamp: float | None = None, max_skew: float = 30.0) -> None:
        nonce_key = nonce.hex()
        now = time.time()
        if timestamp is not None and abs(now - float(timestamp)) > max_skew:
            raise ValueError("timestamp outside allowed skew")
        if nonce_key in self._replay_cache:
            raise ReplayError("replay detected")
        self._replay_cache[nonce_key] = int(now)
        if len(self._replay_cache) > self._max_replay:
            self._replay_cache = dict(list(self._replay_cache.items())[-self._max_replay :])


def derive_shared_key(private_key: x25519.X25519PrivateKey, public_key: x25519.X25519PublicKey) -> bytes:
    secret = private_key.exchange(public_key)
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"openclaw-mesh").derive(secret)
