#!/usr/bin/env bash
# scripts/build.sh
# Build the Docker image for a specific target stage.
#
# Usage:
#   ./scripts/build.sh             # defaults to local
#   ./scripts/build.sh local
#   ./scripts/build.sh -p 80 local
#   ./scripts/build.sh test
#   ./scripts/build.sh deploy
#   ./scripts/build.sh base

set -euo pipefail
cd "$(dirname "$0")/.."

HOST_PORT=80
TARGET="local"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--port)
      shift
      if [[ $# -eq 0 ]]; then
        echo "    Missing port after -p"
        echo "    Usage: $0 [-p PORT] [local|test|deploy|base]"
        exit 1
      fi
      HOST_PORT="$1"
      shift
      ;;
    local|test|deploy|base)
      TARGET="$1"
      shift
      ;;
    *)
      echo "    Unknown option: $1"
      echo "    Usage: $0 [-p PORT] [local|test|deploy|base]"
      exit 1
      ;;
  esac
done

case "$TARGET" in
  local|test|deploy|base) ;;
  *)
    echo "    Unknown target: $TARGET"
    echo "    Usage: $0 [-p PORT] [local|test|deploy|base]"
    exit 1
    ;;
esac

IMAGE="mabuhive:${TARGET}"

echo "Building image → ${IMAGE}  (target: ${TARGET})"
docker build \
  --target  "$TARGET" \
  --tag     "$IMAGE" \
  --file    docker/Dockerfile \
  .

echo ""
echo "    Built: ${IMAGE}"
echo ""
echo "Run it:"
case "$TARGET" in
  local)
    echo "  docker run --rm -p ${HOST_PORT}:8000 --env-file configs/local/.env ${IMAGE}"
    ;;
  test)
    echo "  docker run --rm -p ${HOST_PORT}:8000 --env-file configs/test/.env ${IMAGE}"
    ;;
  deploy)
    echo "  docker run --rm -p ${HOST_PORT}:8000 --env-file configs/deploy/.env ${IMAGE}"
    ;;
  base)
    echo "  Note: ${IMAGE} is a build-stage base image and is not directly runnable."
    ;;
esac
