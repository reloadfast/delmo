# ── Stage 1: Build the React frontend ───────────────────────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci --frozen-lockfile

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime + built frontend ─────────────────────────────────
FROM python:3.14-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/reloadfast/delmo"
LABEL org.opencontainers.image.description="Automatic torrent data mover via Deluge RPC"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# System deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml + backend source so setuptools can find the package
COPY pyproject.toml ./
COPY backend/ ./backend/
RUN pip install --no-cache-dir .

# Copy alembic (env.py uses sys.path insertion pointing to /app/backend/)
COPY alembic ./alembic
COPY alembic.ini ./

# Copy built React SPA
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Data directory (override via volume mount)
ENV DELMO_DATA_DIR=/data
# Tell main.py where the built SPA lives (absolute path inside this image)
ENV DELMO_FRONTEND_DIR=/app/frontend/dist

RUN mkdir -p /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
