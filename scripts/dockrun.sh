#!/usr/bin/env bash
# scripts/dockrun.sh
# Run the local Docker container for development.
#
# Usage:
#   ./scripts/dockrun.sh

set -euo pipefail
cd "$(dirname "$0")/.."          # always run from project root

echo "Starting local Docker container..."
echo "   Server will be at: http://localhost:8000"
echo "   Press Ctrl-C to stop"
echo ""

docker run --rm -v "$PWD":/app -p 8000:8000 --env-file configs/local/.env mabuhive:local