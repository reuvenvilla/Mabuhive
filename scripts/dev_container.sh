#!/usr/bin/env bash
set -euo pipefail

# Run from repo root (works even if called elsewhere)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"
REQ_FILE="src/backend/requirements.txt"
MANAGE="src/backend/manage.py"

echo "========================================"
echo "Mabuhive: init_dev_env.sh"
echo "Repo: $ROOT_DIR"
echo "Venv: $VENV_DIR"
echo "========================================"

if [[ ! -f "$REQ_FILE" ]]; then
  echo "ERROR: requirements file not found: $REQ_FILE"
  exit 1
fi

if [[ ! -f "$MANAGE" ]]; then
  echo "ERROR: Django manage.py not found: $MANAGE"
  exit 1
fi

# Ensure python exists
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. If you're inside the dev container, rebuild it."
  exit 1
fi

# Create venv if missing
if [[ ! -d "$VENV_DIR" ]]; then
  echo "[init] Creating virtualenv at $VENV_DIR ..."
  python3 -m venv "$VENV_DIR"
else
  echo "[init] Virtualenv already exists at $VENV_DIR"
fi

# Activate venv
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

echo "[init] Upgrading pip/setuptools/wheel..."
python -m pip install --upgrade pip setuptools wheel

echo "[init] Installing backend requirements from $REQ_FILE ..."
pip install -r "$REQ_FILE"

# Optional: run Django setup steps unless skipped
SKIP_DJANGO_SETUP="${SKIP_DJANGO_SETUP:-0}"
if [[ "$SKIP_DJANGO_SETUP" != "1" ]]; then
  echo "[init] Running migrations..."
  python "$MANAGE" migrate --noinput

  echo "[init] Collecting static (safe even if not configured)..."
  python "$MANAGE" collectstatic --noinput || true
else
  echo "[init] Skipping Django migrate/collectstatic (SKIP_DJANGO_SETUP=1)"
fi

echo "----------------------------------------"
echo "Dev environment ready."
echo
echo "To start the Django dev server:"
echo "  source $VENV_DIR/bin/activate"
echo "  python $MANAGE runserver 0.0.0.0:8080"
echo
echo "Then open:"
echo "  http://localhost:8080"
echo "----------------------------------------"
