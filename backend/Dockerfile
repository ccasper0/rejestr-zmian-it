# One image for both the API and the arq worker:
#   api:    uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers   (default CMD)
#   worker: arq app.worker.WorkerSettings
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}"

# WeasyPrint runtime: Pango, HarfBuzz, fontconfig + fonts with full Polish glyphs.
# The reports embed IBM Plex Sans/Mono from app/reports/fonts (OFL, copied with the app
# below; ADR 0017) - the system fonts are only a last-resort fallback of Pango.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libharfbuzz-subset0 \
        libfontconfig1 \
        shared-mime-info \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first (layer cache), then project sources.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --extra reports --no-install-project

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN uv sync --frozen --no-dev --extra reports

RUN useradd --system --uid 10001 --home-dir /app appuser \
    && mkdir -p /data/storage \
    && chown appuser /data/storage
ENV STORAGE_PATH=/data/storage
# Fontconfig (WeasyPrint) needs a writable cache directory; /app is not writable.
ENV XDG_CACHE_HOME=/tmp/cache
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4).status == 200 else 1)" || exit 1

# Proxy headers (X-Forwarded-For/-Proto) are honoured ONLY from addresses listed in
# FORWARDED_ALLOW_IPS (read natively by uvicorn; comma-separated IPs/CIDRs). Never "*":
# uvicorn would then trust a client-supplied X-Forwarded-For and the audit log would
# record a spoofed IP. Docker Compose sets it to the compose subnet (nginx).
ENV FORWARDED_ALLOW_IPS=127.0.0.1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
