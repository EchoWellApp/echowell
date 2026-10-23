# Backend image (TRD 15 DEP-020, DEP-022). Build context: repository root.
# Hardening (non-root UID 10001, image checks) is completed by FEAT-077.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY alembic.ini ./
COPY analytics/ analytics/
COPY backend/ backend/

EXPOSE 8000

# No migration step here: Alembic runs as a separate pre-deploy step (DEP-040, DEP-060).
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
