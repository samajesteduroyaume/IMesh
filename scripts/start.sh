#!/usr/bin/env bash
set -eu

cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-$(which python3.10 || which python3 || echo "python")}"
exec "$PYTHON_BIN" -m openclaw_mesh.cli start --host "${1:-127.0.0.1}" --port "${2:-8765}"
