# docker/Dockerfile
### Base environment container ###
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=settings

# Install system dependencies if needed (e.g., for Django)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY . /usr/src/project
WORKDIR /usr/src/project

### Build/test container ###
# Define builder stage
FROM base AS builder

# Share work directory
WORKDIR /usr/src/project

# Run tests
RUN python -m pytest tests/ -v --tb=short

### Deploy container ###
# Define deploy stage
FROM python:3.12-slim AS deploy

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=settings

# Install runtime dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project source from builder
COPY --from=builder /usr/src/project /app
WORKDIR /app

# Create build directory
RUN mkdir -p build/posts

# Expose port
EXPOSE 8000

# Use ENTRYPOINT to specify the binary name
ENTRYPOINT ["gunicorn"]

# Use CMD to specify arguments to ENTRYPOINT
CMD ["server.server:application", "--bind", "0.0.0.0:8000", "--workers", "2"]

### Local development stage ###
FROM deploy AS local

# Install additional tools for development
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Override for development
ENV DEBUG=True

# Override ENTRYPOINT inherited from deploy so local stage runs python directly
ENTRYPOINT ["python"]

# Use Django runserver for hot reload
CMD ["-m", "server.server", "runserver", "0.0.0.0:8000"]
