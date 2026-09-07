#!/usr/bin/env bash
set -eu

cd "$(dirname "$0")/.."
exec /opt/homebrew/bin/python3.10 -m openclaw_mesh.cli start --host 127.0.0.1 --port 8765
