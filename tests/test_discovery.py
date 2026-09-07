from openclaw_mesh.discovery import MeshDiscovery, PeerInfo


def test_mesh_discovery_manual_registration():
    discovery = MeshDiscovery(node_name="alpha", port=8765, enabled=True)
    peer = discovery.register_manual_peer("beta", "127.0.0.1", 8766, skills=["echo"])
    assert peer.name == "beta"
    assert discovery.discover_now()[0].name == "beta"
