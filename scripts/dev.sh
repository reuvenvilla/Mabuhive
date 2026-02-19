#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="mabuhive-dev"
CONTAINER_NAME="mabuhive-dev"

DOCKERFILE_PATH="$ROOT_DIR/dev/Dockerfile"

if [[ ! -f "$DOCKERFILE_PATH" ]]; then
  echo "Error: Dockerfile not found at: $DOCKERFILE_PATH" >&2
  echo "Expected: Mabuhive/dev/Dockerfile" >&2
  exit 1
fi

# Build dev image
docker build -f "$DOCKERFILE_PATH" -t "$IMAGE_NAME" "$ROOT_DIR"

# Run container if not already running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  # Optional: allow docker commands inside dev container (controls host docker)
  SOCK_ARGS=()
  if [[ -S /var/run/docker.sock ]]; then
    SOCK_ARGS=(-v /var/run/docker.sock:/var/run/docker.sock)
  fi

  # Workspace mount
  WS_ARGS=(-v "$ROOT_DIR:/workspace:delegated" -w /workspace)

  # Prefer ssh-agent forwarding when possible; fallback to mounting ~/.ssh read-only
  SSH_ARGS=()

  # Test whether Docker can mount a given path on this host
  can_mount_path() {
    local p="$1"
    docker run --rm \
      -v "$p:$p:ro" \
      alpine:3.19 \
      sh -lc "test -S '$p' || test -e '$p'" >/dev/null 2>&1
  }

  if [[ -n "${SSH_AUTH_SOCK:-}" && -S "${SSH_AUTH_SOCK}" ]]; then
    if can_mount_path "${SSH_AUTH_SOCK}"; then
      SSH_ARGS=(-v "${SSH_AUTH_SOCK}:/ssh-agent" -e SSH_AUTH_SOCK=/ssh-agent)
    else
      echo "Info: SSH agent socket is not mountable by Docker on this host; using ~/.ssh fallback."
    fi
  fi

  if [[ ${#SSH_ARGS[@]} -eq 0 ]]; then
    if [[ -d "${HOME}/.ssh" ]]; then
      SSH_ARGS=(-v "${HOME}/.ssh:/root/.ssh:ro")
    else
      echo "Warning: ${HOME}/.ssh not found; GitHub SSH may not work inside the container." >&2
    fi
  fi

  docker run -dit --rm \
  --name "$CONTAINER_NAME" \
  -v "$ROOT_DIR:/workspace:delegated" \
  -v "${HOME}/.gitconfig:/root/.gitconfig:ro" \
  "${SOCK_ARGS[@]}" \
  "${SSH_ARGS[@]}" \
  -w /workspace \
  "$IMAGE_NAME"
fi

# Attach shell
docker exec -it "$CONTAINER_NAME" bash
