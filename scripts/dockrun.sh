#!/usr/bin/env bash
# scripts/dockrun.sh
# Run the local Docker container for development.
#
# Usage:
#   ./scripts/dockrun.sh        # run in foreground
#   ./scripts/dockrun.sh -b     # run in background

set -euo pipefail
cd "$(dirname "$0")/.."          # always run from project root

# Parse command line arguments
BACKGROUND=false
while [[ $# -gt 0 ]]; do
  case $1 in
    -b|--background)
      BACKGROUND=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [-b|--background]"
      exit 1
      ;;
  esac
done

if [[ "$BACKGROUND" == true ]]; then
  echo "Starting local Docker container in background..."
  echo "   Server will be at: http://localhost:8000"
  echo "   Container is running in the background"
  echo "   To stop: docker stop \$(docker ps -q --filter ancestor=mabuhive:local)"
  echo ""

  docker run --rm -v "$PWD":/app -p 8000:8000 --env-file configs/local/.env mabuhive:local &
else
  echo "Starting local Docker container..."
  echo "   Server will be at: http://localhost:8000"
  echo "   Press Ctrl-C to stop"
  echo ""

  docker run --rm -v "$PWD":/app -p 8000:8000 --env-file configs/local/.env mabuhive:local
fi