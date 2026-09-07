from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from typing import Any

from .client import MeshClient
from .config import get_settings, reload_settings
from .discovery import MeshDiscovery
from .node import IMeshNode


async def _start_node(host: str | None, port: int | None, no_wan: bool) -> None:
    settings = get_settings()
    if no_wan:
        settings.wan_enabled = False
    node = IMeshNode(host=host or settings.default_host, port=port or settings.default_port)
    await node.start()
    print(f"IMesh node listening on ws://{node.host}:{node.port}")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await node.stop()


async def _call_peer(peer_name: str, url: str, skill: str, payload: dict[str, Any]) -> None:
    client = MeshClient()
    client.add_peer(peer_name, url)
    await client.start()
    try:
        result = await client.call(peer_name, skill, payload)
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        await client.stop()


async def _discover() -> None:
    settings = get_settings()
    discovery = MeshDiscovery(
        settings.node_name, settings.default_port, enabled=settings.mdns_enabled
    )
    await discovery.start()
    try:
        print(json.dumps([asdict(peer) for peer in discovery.discover_now()], indent=2))
    finally:
        await discovery.stop()


async def _gateway(host: str, port: int) -> None:
    import uvicorn

    from .gateway.server import create_app

    app = create_app()
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openclaw-mesh")
    subparsers = parser.add_subparsers(dest="command")

    start_cmd = subparsers.add_parser("start", help="start a local mesh node")
    start_cmd.add_argument("--host", default=None)
    start_cmd.add_argument("--port", type=int, default=None)
    start_cmd.add_argument("--no-wan", action="store_true")

    node_cmd = subparsers.add_parser("node", help="run the node")
    node_cmd.add_argument("--host", default=None)
    node_cmd.add_argument("--port", type=int, default=None)
    node_cmd.add_argument("--no-wan", action="store_true")

    discover_cmd = subparsers.add_parser("discover", help="discover peers")
    discover_cmd.add_argument("--host", default=None)
    discover_cmd.add_argument("--port", type=int, default=None)

    subparsers.add_parser("peers", help="show configured peers")
    call_cmd = subparsers.add_parser("call", help="call a skill")
    call_cmd.add_argument("peer", default="local")
    call_cmd.add_argument("skill", default="echo")
    call_cmd.add_argument("--url", default="ws://127.0.0.1:8765")
    call_cmd.add_argument("--payload", default="{}")

    gateway_cmd = subparsers.add_parser("gateway", help="launch the FastAPI gateway")
    gateway_cmd.add_argument("--host", default="127.0.0.1")
    gateway_cmd.add_argument("--port", type=int, default=8000)

    subparsers.add_parser("keygen", help="generate a local identity")
    subparsers.add_parser("identity", help="show local identity")
    subparsers.add_parser("health", help="show local health")
    subparsers.add_parser("version", help="show version")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    reload_settings()

    if args.command in {"start", "node"}:
        asyncio.run(_start_node(args.host, args.port, getattr(args, "no_wan", False)))
        return 0
    if args.command == "call":
        payload = json.loads(args.payload)
        asyncio.run(_call_peer(args.peer, args.url, args.skill, payload))
        return 0
    if args.command == "gateway":
        asyncio.run(_gateway(args.host, args.port))
        return 0
    if args.command == "version":
        print("openclaw-mesh 0.1.0")
        return 0
    if args.command == "health":
        print(json.dumps({"status": "ok"}, indent=2))
        return 0
    if args.command == "discover":
        asyncio.run(_discover())
        return 0
    if args.command == "peers":
        print(json.dumps({"peers": [], "discovery": "use 'discover' for mDNS"}, indent=2))
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
