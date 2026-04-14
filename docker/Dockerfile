# docker/Dockerfile
#
# Three build targets — select with --target flag:
#
#   docker build --target local  -t myapp:local  -f docker/Dockerfile .
#   docker build --target test   -t myapp:test   -f docker/Dockerfile .
#   docker build --target deploy -t myapp:deploy -f docker/Dockerfile .
#
# Or via scripts/:
#   ./scripts/build.sh local
#   ./scripts/build.sh test
#   ./scripts/build.sh deploy


# ══════════════════════════════════════════════════════════════════════════════
# Stage 1 — base
# Shared foundation: installs dependencies, copies source.
# No CMD — not meant to be run directly.
# ══════════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Project root is the WORKDIR, so `import settings` resolves correctly
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=settings

WORKDIR /app

# Install Python dependencies (cached layer — only rebuilds if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full project source
COPY . .

# Create the build output directory (git-ignored on host)
RUN mkdir -p /app/build/posts


# Testing Sage (No tests for now, so ignore)
# Runs the test suite. 
# Tests ran before CI builds project
#
# Usage:  docker build --target test -t myapp:test -f docker/Dockerfile .
#         docker run --rm myapp:test
FROM base AS test

ENV DEBUG=True

# pytest + pytest-django already in requirements.txt
CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]


# ══════════════════════════════════════════════════════════════════════════════
# Build Stage (Local)
# Django development server with DEBUG=True.
# Source should be bind-mounted for hot-reload:
#   docker run -v $(pwd):/app -p 8000:8000 myapp:local
#
# Usage:  docker build --target local -t myapp:local -f docker/Dockerfile .
#         docker run -v $(pwd):/app -p 8000:8000 --env-file configs/local/.env myapp:local
# ══════════════════════════════════════════════════════════════════════════════
FROM base AS local

# curl needed for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV DEBUG=True

EXPOSE 8000

CMD ["python", "-m", "server.server", "runserver", "0.0.0.0:8000"]


# ══════════════════════════════════════════════════════════════════════════════
# Deploy Stage
# Production image: Gunicorn, DEBUG=False, minimal footprint.
#
# Usage:  docker build --target deploy -t myapp:deploy -f docker/Dockerfile .
#         docker run -p 8000:8000 --env-file configs/deploy/.env myapp:deploy
# ══════════════════════════════════════════════════════════════════════════════
FROM base AS deploy

RUN pip install --no-cache-dir gunicorn

ENV DEBUG=False

EXPOSE 8000

# 2 workers is a safe default; tune with WEB_CONCURRENCY env var if needed
CMD ["gunicorn", "server.server:application", \
     "--bind",            "0.0.0.0:8000", \
     "--workers",         "2", \
     "--timeout",         "60", \
     "--access-logfile",  "-", \
     "--error-logfile",   "-"]
