#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] migrate..."
python src/backend/manage.py migrate --noinput

echo "[entrypoint] collectstatic..."
python src/backend/manage.py collectstatic --noinput || true

exec "$@"