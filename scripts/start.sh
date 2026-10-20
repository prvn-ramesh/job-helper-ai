#!/usr/bin/env bash
# AutoJob AI — Single Command Launcher
# Usage: ./scripts/start.sh

set -e

cd "$(dirname "$0")/.."

echo "Starting AutoJob AI Mission Control..."
exec uv run python scripts/launch.py "$@"
