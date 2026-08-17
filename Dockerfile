FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# ─── Production ───────────────────────────────────────────────────────
FROM base AS production

# Install only production dependencies
RUN pip install --no-cache-dir "azure-core==1.29.7" && \
    pip install --no-cache-dir -e . uvicorn[standard] httpx aiohttp

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ─── Development ──────────────────────────────────────────────────────
FROM base AS development

# Install all dependencies including dev (pytest, hypothesis)
RUN pip install --no-cache-dir "azure-core==1.29.7" && \
    pip install --no-cache-dir -e ".[dev]" uvicorn[standard] httpx aiohttp

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
