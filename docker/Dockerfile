# Mabuhive/docker/Dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    python3 \
    python3-pip \
  && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/bin/python

# Install deps first for caching
COPY src/backend/requirements.txt /app/src/backend/requirements.txt
RUN pip3 install --no-cache-dir -r /app/src/backend/requirements.txt

# Copy source
COPY src/ /app/src/
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--chdir", "src/backend", "--bind", "0.0.0.0:8080", "backend.wsgi:application"]
