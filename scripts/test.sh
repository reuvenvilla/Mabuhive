#!/usr/bin/env bash
# scripts/test.sh
# Run the test suite.
#
# Usage:
#   ./scripts/test.sh            # run locally with host Python
#   ./scripts/test.sh --docker   # build test image and run inside container

set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)

if [[ "${1:-}" == "--docker" ]]; then
  echo "   Building test image..."
  docker build --target test --tag mabuhive:test --file docker/Dockerfile .
  echo ""
  echo "   Running tests in container..."
  docker run --rm --env-file configs/test/.env mabuhive:test
else
  echo "   Running tests locally..."
  # Safe env loading (avoids source breaking on space-separated values)
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" == \#* ]] && continue
    value="${value%\"}"; value="${value#\"}"
    export "$key=$value"
  done < configs/test/.env
  "$PYTHON" -m pytest tests/ -v --tb=short
fi
