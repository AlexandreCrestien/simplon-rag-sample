# syntax=docker/dockerfile:1.7

# --- Base stage: Python 3.14 + uv ---
FROM python:3.14-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

# --- Dev stage: full deps, runOnSave for hot reload ---
FROM base AS dev

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --extra dev

COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra dev

EXPOSE 8501
CMD ["streamlit", "run", "src/app/app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.runOnSave=true", \
     "--browser.gatherUsageStats=false"]

# --- Prod stage: minimal deps, headless, source baked in ---
FROM base AS prod

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY src ./src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

EXPOSE 8501
CMD ["streamlit", "run", "src/app/app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
