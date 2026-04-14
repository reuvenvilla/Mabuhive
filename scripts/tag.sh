#!/usr/bin/env bash
# scripts/tag.sh
# Tag the mabuhive:local image for deployment.
#
# Usage:
#   ./scripts/tag.sh --latest    # tag as mabuhive:latest
#   ./scripts/tag.sh --release   # tag as mabuhive:latest and mabuhive:release

set -euo pipefail
cd "$(dirname "$0")/.."          # always run from project root

SOURCE_IMAGE="mabuhive:local"

# Check if source image exists
if ! docker image inspect "$SOURCE_IMAGE" &>/dev/null; then
  echo "Error: Source image '$SOURCE_IMAGE' not found. Build it first with ./scripts/build.sh local"
  exit 1
fi

case "${1:-}" in
  --latest)
    echo "Tagging $SOURCE_IMAGE as mabuhive:latest..."
    docker tag "$SOURCE_IMAGE" mabuhive:latest
    echo "Done."
    ;;
  --release)
    echo "Tagging $SOURCE_IMAGE as mabuhive:latest and mabuhive:release..."
    docker tag "$SOURCE_IMAGE" mabuhive:latest
    docker tag "$SOURCE_IMAGE" mabuhive:release
    echo "Done."
    ;;
  *)
    echo "Usage: $0 [--latest|--release]"
    echo "  --latest   Tag as mabuhive:latest"
    echo "  --release  Tag as mabuhive:latest and mabuhive:release"
    exit 1
    ;;
esac