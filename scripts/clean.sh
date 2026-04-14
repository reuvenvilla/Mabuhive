#!/usr/bin/env bash
# scripts/clean.sh
# Remove the build/ directory and optionally prune Docker artifacts.
#
# Usage:
#   ./scripts/clean.sh            # remove build/ only
#   ./scripts/clean.sh --docker   # also remove mabuhive Docker images

set -euo pipefail
cd "$(dirname "$0")/.."

echo "Removing build/..."
rm -rf build/
echo "    Done."

if [[ "${1:-}" == "--docker" ]]; then
  echo "   Removing mabuhive Docker images..."
  docker rmi mabuhive:local mabuhive:test mabuhive:deploy mabuhive:base 2>/dev/null && echo "    Done." \
    || echo "    (No mabuhive images found — skipping.)"
fi
