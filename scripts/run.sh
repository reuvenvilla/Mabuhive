#!/usr/bin/env bash
# scripts/run.sh
# Start the Django development server directly on the host (no Docker).
#
# Usage:
#   ./scripts/run.sh           # runs on 0.0.0.0:8000
#   ./scripts/run.sh 9000      # custom port

set -euo pipefail
cd "$(dirname "$0")/.."          # always run from project root

PORT="${1:-8000}"

# ── Resolve python binary (macOS uses python3) ────────────────────────────────
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
if [[ -z "$PYTHON" ]]; then
  echo "ERR:python3 not found. Install Python 3 and try again."
  exit 1
fi

# ── Check Django is installed ─────────────────────────────────────────────────
if ! "$PYTHON" -c "import django" &>/dev/null; then
  echo "WARNING: Django not found. Installing requirements..."
  "$PYTHON" -m pip install -r requirements.txt
fi

# ── Load env vars ─────────────────────────────────────────────────────────────
# Manually parse instead of `source` — avoids bash treating space-separated
# values like ALLOWED_HOSTS="a b c" as shell commands.
while IFS='=' read -r key value; do
  [[ -z "$key" || "$key" == \#* ]] && continue   # skip blanks and comments
  value="${value%\"}"                              # strip trailing quote
  value="${value#\"}"                              # strip leading quote
  export "$key=$value"
done < configs/local/.env

mkdir -p mnt

echo "   Dev server -> http://localhost:${PORT}"
echo "    Stop with Ctrl-C"
echo ""

"$PYTHON" -m server.server runserver "0.0.0.0:${PORT}"
