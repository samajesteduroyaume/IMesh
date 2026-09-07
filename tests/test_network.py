from openclaw_mesh.network import DHTNode, GossipNode, RelayNode


def test_network_basics():
    dht = DHTNode("node-1")
    dht.put("abc", {"value": 42})
    assert dht.get("abc") == {"value": 42}

    relay = RelayNode("relay-1")
    relay.add_peer("node-2")
    assert relay.relay({"ok": True})["relay"] == "relay-1"

    gossip = GossipNode("node-1")
    gossip.subscribe("mesh")
    gossip.publish("mesh", {"hello": "world"})
    assert gossip.get_messages("mesh") == [{"hello": "world"}]
