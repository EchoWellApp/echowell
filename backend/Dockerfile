# Backend image (TRD 15 DEP-020..DEP-022, DEP-111; FEAT-077). Build context: repository root
#   docker build -f backend/Dockerfile -t echowell-backend .
# The same image runs unchanged on Docker Compose, Render and AWS App Runner (ARC-090, NFR-090).
# The root .dockerignore keeps .env files, tests/, specs/, docs/ and frontend/ out of the context (DEP-021).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

# Runtime pins only (backend/requirements.txt, psycopg[binary] 3.x, D-53); never requirements-dev.txt.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

# Non-root runtime user (DEP-021, CIC-023): fixed UID/GID 10001, no home directory, no login shell.
RUN groupadd --system --gid 10001 echowell \
    && useradd --system --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin echowell

# Application code stays root-owned and read-only for the runtime user; nothing is written to local disk
# between requests (DEP-111). database/ carries the seed files and role scripts (DEP-020).
COPY alembic.ini ./
COPY analytics/ analytics/
COPY backend/ backend/
COPY database/ database/

USER 10001:10001

EXPOSE 8000

# No migration step here: Alembic runs as a separate pre-deploy step (DEP-040, DEP-060). The sh -c
# wrapper expands ${PORT:-8000} injected by Render / App Runner (TRD 15 §8).
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
