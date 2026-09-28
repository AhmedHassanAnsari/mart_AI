FROM python:3.12-slim

# Install curl and basic tools
RUN apt-get update && apt-get install -y --no-install-recommends     curl     ca-certificates     && rm -rf /var/lib/apt/lists/*

# Install uv directly into /usr/local/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/usr/local/bin" sh

WORKDIR /app

# Copy dependency files and install system-wide
COPY pyproject.toml uv.lock ./
RUN uv pip install --system .

# Copy app code
COPY . .

CMD ["python", "workflow_worker.py"]
