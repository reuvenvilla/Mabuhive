# Mabuhive/dev/Dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    build-essential \
  && rm -rf /var/lib/apt/lists/*

# Convenience: python -> python3
RUN ln -sf /usr/bin/python3 /usr/bin/python

CMD ["/bin/bash"]
