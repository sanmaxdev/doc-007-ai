# ======================================================================
# DOC-007-AI API (FastAPI + SQLAlchemy async + Alembic + Celery)
# Production image.
#
# Multi-stage build: a builder stage compiles wheels (build tools + headers)
# into an isolated prefix, and a slim runtime stage copies only what is
# needed to run. Runtime deps only - the [dev] extra (pytest, ruff, mypy,
# aiosqlite) is NOT installed.
#
# Local development still works: docker-compose.yml overrides this image's
# CMD with `uvicorn ... --reload` and bind-mounts the source tree, so the
# production default below does not affect `docker compose up`.
# ======================================================================

# ---- builder: install runtime deps into an isolated prefix ----
FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build tools needed to compile wheels (argon2-cffi, asyncpg, etc.).
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only what hatchling needs to build the wheel (metadata + package src),
# then install the project plus its runtime dependencies into /install.
COPY pyproject.toml ./
COPY src ./src
RUN pip install --upgrade pip \
    && pip install --prefix=/install .

# ---- runtime: slim image with just the installed packages + app ----
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# curl for the container healthcheck only (no build tools in runtime).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Bring in the installed Python packages + console scripts from the builder.
COPY --from=builder /install /usr/local

# Application code, migrations, and Alembic config (needed for `alembic
# upgrade head` at deploy time).
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Make the package importable when running tools (alembic env.py imports it).
ENV PYTHONPATH=/app/src

# Run as a non-root user; give it ownership of the upload volume mountpoint.
RUN useradd --create-home --uid 1001 appuser \
    && mkdir -p /data/uploads \
    && chown -R appuser:appuser /app /data
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

# Production server: gunicorn managing uvicorn workers.
CMD ["gunicorn", "doc007.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000"]
