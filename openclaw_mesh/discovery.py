from __future__ import annotations

import socket
import time
from dataclasses import dataclass, field
from ipaddress import ip_address
from typing import Any

try:
    from zeroconf import ServiceBrowser, ServiceInfo, Zeroconf
except ImportError:  # pragma: no cover
    Zeroconf = None
    ServiceBrowser = None
    ServiceInfo = None


@dataclass(slots=True)
class PeerInfo:
    name: str
    host: str
    port: int
    skills: list[str] = field(default_factory=list)
    protocol_version: str = "0.1.0"
    last_seen: int = field(default_factory=lambda: int(time.time()))
    reachable: bool = True


class MeshDiscovery:
    def __init__(self, node_name: str, port: int, enabled: bool = True, peer_ttl_seconds: int = 120) -> None:
        self.node_name = node_name
        self.port = port
        self.enabled = enabled
        self.peer_ttl_seconds = peer_ttl_seconds
        self.peers: dict[str, PeerInfo] = {}
        self.zc: Zeroconf | None = None
        self.browser: Any | None = None

    def add_service(self, zc: Any, type_: str, name: str) -> None:
        if self.zc is None:
            return
        info = self.zc.get_service_info(type_, name)
        if info is None or not info.addresses:
            return
        host = str(ip_address(info.addresses[0]))
        peer_name = name.removesuffix(f".{type_}")
        if peer_name == self.node_name:
            return
        self.add_peer(
            PeerInfo(
                name=peer_name,
                host=host,
                port=info.port,
                skills=self._decode_skills(info.properties),
            )
        )

    def remove_service(self, zc: Any, type_: str, name: str) -> None:
        return None

    def update_service(self, zc: Any, type_: str, name: str) -> None:
        self.add_service(zc, type_, name)

    async def start(self) -> None:
        if not self.enabled or Zeroconf is None or ServiceBrowser is None:
            return
        try:
            self.zc = Zeroconf()
            self.browser = ServiceBrowser(self.zc, "_openclawmesh._tcp.local.", listener=self)
        except TypeError:
            self.browser = None
            if self.zc is not None:
                self.zc.close()
                self.zc = None

    async def stop(self) -> None:
        if self.zc is not None:
            self.zc.close()
            self.zc = None
        self.browser = None

    def add_peer(self, peer: PeerInfo) -> None:
        now = int(time.time())
        peer.last_seen = getattr(peer, "last_seen", now)
        peer.reachable = True
        self.peers[peer.name] = peer

    def discover_now(self) -> list[PeerInfo]:
        now = int(time.time())
        all_peers: list[PeerInfo] = []
        for peer in self.peers.values():
            peer.last_seen = getattr(peer, "last_seen", now)
            peer.reachable = (now - int(peer.last_seen)) <= self.peer_ttl_seconds
            all_peers.append(peer)
        return all_peers

    def publish(self, skills: list[str] | None = None) -> None:
        if self.zc is None or ServiceInfo is None:
            return
        service_type = "_openclawmesh._tcp.local."
        service_name = f"{self.node_name}.{service_type}"
        info = ServiceInfo(
            service_type,
            service_name,
            addresses=[socket.inet_aton(self.get_local_ip())],
            port=self.port,
            properties={"skills": ",".join(skills or [])},
        )
        self.zc.register_service(info)

    @staticmethod
    def _decode_skills(properties: dict[Any, Any]) -> list[str]:
        value = properties.get("skills", b"")
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="ignore")
        return [item for item in str(value).split(",") if item]

    def get_local_ip(self) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"

    def register_manual_peer(
        self, name: str, host: str, port: int, skills: list[str] | None = None
    ) -> PeerInfo:
        peer = PeerInfo(name=name, host=host, port=port, skills=skills or [])
        peer.last_seen = int(time.time())
        peer.reachable = True
        self.add_peer(peer)
        return peer
