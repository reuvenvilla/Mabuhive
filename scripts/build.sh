#!/usr/bin/env bash
# scripts/build.sh
# Build the Docker image for a specific target stage.
#
# Usage:
#   ./scripts/build.sh           # defaults to local
#   ./scripts/build.sh local
#   ./scripts/build.sh test
#   ./scripts/build.sh deploy
#   ./scripts/build.sh base

set -euo pipefail
cd "$(dirname "$0")/.."

TARGET="${1:-local}"

case "$TARGET" in
  local|test|deploy|base) ;;
  *)
    echo "    Unknown target: $TARGET"
    echo "    Usage: $0 [local|test|deploy|base]"
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
    echo "  docker run --rm -p 80:8000 --env-file configs/local/.env ${IMAGE}"
    ;;
  test)
    echo "  docker run --rm --env-file configs/test/.env ${IMAGE}"
    ;;
  deploy)
    echo "  docker run --rm -p 80:8000 --env-file configs/deploy/.env ${IMAGE}"
    ;;
  base)
    echo "  Note: ${IMAGE} is a build-stage base image and is not directly runnable."
    ;;
esac
