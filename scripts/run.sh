#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="mabuhive-prod"
CONTAINER_NAME="mabuhive-prod"

docker build -f "$ROOT_DIR/docker/Dockerfile" -t "$IMAGE_NAME" "$ROOT_DIR"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
docker run -d --rm \
  --name "$CONTAINER_NAME" \
  -p 8080:8080 \
  "$IMAGE_NAME"

echo "Prod container running at http://localhost:8080"
