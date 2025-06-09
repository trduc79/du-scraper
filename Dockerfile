# Build stage
FROM python:3.13-slim@sha256:21e39cf1815802d4c6f89a0d3a166cc67ce58f95b6d1639e68a394c99310d2e5 AS builder

# Set working directory
WORKDIR /build

ENV XDG_BIN_HOME=/build/.local 
# Install dependencies for uv
RUN apt-get update && \
    apt-get install -y curl musl-dev gcc g++ && \
    curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy project files
COPY pyproject.toml . 

# Install dependencies using uv
RUN $XDG_BIN_HOME/uv venv && $XDG_BIN_HOME/uv sync --no-group dev

# Final stage
FROM builder

# Set working directory
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /build/.venv /app/.venv

# Copy source code
COPY src/ /app/

# Set the correct environment for uv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Default command
CMD ["python", "main.py"]