#!/usr/bin/env bash
# scripts/dev.sh
# Launch an interactive Ubuntu container with the project root bind-mounted to /app.
# Any file you edit on your host is instantly visible inside the container, and vice versa.
#
# Usage:
#   ./scripts/dev.sh              # enter bash shell
#   ./scripts/dev.sh --rebuild    # force image rebuild, then enter shell
#   ./scripts/dev.sh --run        # start the Django dev server inside Ubuntu

set -euo pipefail
cd "$(dirname "$0")/.."            # always run from project root

IMAGE="myapp:ubuntu"
REBUILD=false
MODE="shell"

for arg in "$@"; do
  case "$arg" in
    --rebuild) REBUILD=true ;;
    --run)     MODE="run"   ;;
  esac
done

# ── Build image if needed ─────────────────────────────────────────────────────
if [[ "$REBUILD" == true ]] || ! docker image inspect "$IMAGE" &>/dev/null; then
  echo "🔨  Building Ubuntu dev image..."
  docker build \
    --file  docker/Dockerfile.ubuntu \
    --tag   "$IMAGE" \
    .
  echo ""
fi

# ── Common docker run args ────────────────────────────────────────────────────
DOCKER_ARGS=(
  --rm                                    # remove container on exit
  --interactive                           # keep stdin open
  --tty                                   # allocate a pseudo-TTY
  --volume "$(pwd):/app"                  # bind-mount project root → /app
  --workdir /app                          # start in /app
  --env-file configs/local/.env           # load local env vars
  --publish 8000:8000                     # expose Django dev server port
  --name myapp-dev
)

if [[ "$MODE" == "run" ]]; then
  echo "   Starting Django dev server inside Ubuntu container..."
  echo "    http://localhost:8000"
  docker run "${DOCKER_ARGS[@]}" "$IMAGE" \
    bash -c "mkdir -p /app/build/posts && python -m server.server runserver 0.0.0.0:8000"
else
  echo "   Entering Ubuntu dev container  (project root → /app)"
  echo "    Type 'exit' or Ctrl-D to leave."
  echo ""
  docker run "${DOCKER_ARGS[@]}" "$IMAGE"
fi
