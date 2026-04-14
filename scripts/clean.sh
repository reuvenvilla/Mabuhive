#!/usr/bin/env bash
# scripts/clean.sh
# Remove the build/ directory and optionally prune Docker artifacts.
#
# Usage:
#   ./scripts/clean.sh            # remove build/ only
#   ./scripts/clean.sh --docker   # also remove myapp Docker images

set -euo pipefail
cd "$(dirname "$0")/.."

echo "🧹  Removing build/..."
rm -rf build/
echo "    Done."

if [[ "${1:-}" == "--docker" ]]; then
  echo "🧹  Removing myapp Docker images..."
  docker rmi myapp:local myapp:test myapp:deploy 2>/dev/null && echo "    Done." \
    || echo "    (No myapp images found — skipping.)"
fi
