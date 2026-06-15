FROM python:3.11-slim

# Install uv inside container
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies using uv sync
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

EXPOSE 8501

# Place the virtual environment's bin on the PATH
ENV PATH="/app/.venv/bin:$PATH"
