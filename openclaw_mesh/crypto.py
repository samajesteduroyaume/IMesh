from __future__ import annotations

import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography import x509
from cryptography.x509.oid import NameOID


class NodeIdentity:
    def __init__(self, private_key: ed25519.Ed25519PrivateKey | None = None, public_key: ed25519.Ed25519PublicKey | None = None) -> None:
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = public_key or self.private_key.public_key()

    @classmethod
    def generate(cls) -> "NodeIdentity":
        return cls()

    @classmethod
    def load(cls, path: str | Path) -> "NodeIdentity":
        path = Path(path)
        pem = path.read_bytes()
        private_key = serialization.load_pem_private_key(pem, password=None)
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise TypeError("private key is not Ed25519")
        return cls(private_key=private_key)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        path.write_bytes(pem)
        path.chmod(0o600)

    def sign(self, payload: bytes) -> bytes:
        return self.private_key.sign(payload)

    def verify(self, payload: bytes, signature: bytes) -> bool:
        try:
            self.public_key.verify(signature, payload)
            return True
        except InvalidSignature:
            return False

    def public_pem(self) -> bytes:
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )


class TrustStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else Path("./trust_store.json")
        self.entries: dict[str, dict[str, str | bool]] = {}
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.entries = {}
            return
        try:
            raw = json.loads(self.path.read_text())
            self.entries = raw if isinstance(raw, dict) else {}
        except json.JSONDecodeError:
            self.entries = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.entries, indent=2, sort_keys=True))

    def add(self, node_name: str, pubkey_pem: str, trusted: bool = True) -> None:
        self.entries[node_name] = {"pubkey": pubkey_pem, "trusted": bool(trusted)}
        self.save()

    def revoke(self, node_name: str) -> None:
        self.entries[node_name] = {"pubkey": "", "trusted": False}
        self.save()

    def is_trusted(self, node_name: str) -> bool:
        entry = self.entries.get(node_name)
        return bool(entry and entry.get("trusted"))


def generate_ephemeral_tls_cert(common_name: str = "localhost") -> tuple[str, str]:
    key = ed25519.Ed25519PrivateKey.generate()
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(__import__("datetime").datetime.utcnow())
        .not_valid_after(__import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(days=1))
    )
    cert = builder.sign(key, hashes.SHA256())
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return cert_pem.decode("utf-8"), key_pem.decode("utf-8")
