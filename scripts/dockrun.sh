#!/usr/bin/env bash
# scripts/dockrun.sh
# Run the local Docker container for development.
#
# Usage:
#   ./scripts/dockrun.sh            # run in foreground on localhost:8000
#   ./scripts/dockrun.sh -b         # run in background on localhost:8000
#   ./scripts/dockrun.sh -p 80      # run on localhost:80
#   ./scripts/dockrun.sh -b -p 80   # run in background on localhost:80

set -euo pipefail
cd "$(dirname "$0")/.."          # always run from project root

# Parse command line arguments
BACKGROUND=false
HOST_PORT=8000
while [[ $# -gt 0 ]]; do
  case $1 in
    -b|--background)
      BACKGROUND=true
      shift
      ;;
    -p|--port)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Missing port after -p"
        echo "Usage: $0 [-b|--background] [-p PORT]"
        exit 1
      fi
      HOST_PORT="$1"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [-b|--background] [-p PORT]"
      exit 1
      ;;
  esac
done

if [[ "$BACKGROUND" == true ]]; then
  echo "Starting local Docker container in background..."
  echo "   Server will be at: http://localhost:${HOST_PORT}"
  echo "   Container is running in the background"
  echo "   To stop: docker stop \$(docker ps -q --filter ancestor=mabuhive:local)"
  echo ""

  docker run --rm -v "$PWD":/app -p ${HOST_PORT}:8000 --env-file configs/local/.env mabuhive:local &
else
  echo "Starting local Docker container..."
  echo "   Server will be at: http://localhost:${HOST_PORT}"
  echo "   Press Ctrl-C to stop"
  echo ""

  docker run --rm -v "$PWD":/app -p ${HOST_PORT}:8000 --env-file configs/local/.env mabuhive:local
fi