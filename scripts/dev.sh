#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="mabuhive-dev"
CONTAINER_NAME="mabuhive-dev"

# Build dev image
docker build -f "$ROOT_DIR/dev/Dockerfile" -t "$IMAGE_NAME" "$ROOT_DIR"

# Run container if not already running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  # Optional: allow docker commands inside dev container (controls host docker)
  SOCK_ARGS=()
  if [[ -S /var/run/docker.sock ]]; then
    SOCK_ARGS=(-v /var/run/docker.sock:/var/run/docker.sock)
  fi

  docker run -dit --rm \
    --name "$CONTAINER_NAME" \
    -v "$ROOT_DIR:/workspace:delegated" \
    -w /workspace \
    "${SOCK_ARGS[@]}" \
    "$IMAGE_NAME"
fi

# Attach shell
docker exec -it "$CONTAINER_NAME" bash
