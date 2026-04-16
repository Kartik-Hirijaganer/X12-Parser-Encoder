# syntax=docker/dockerfile:1.7

FROM node:20-bookworm-slim AS web-builder

WORKDIR /workspace/apps/web

COPY VERSION /workspace/VERSION
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

COPY apps/web/ ./
RUN npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/srv/app/apps/api:/srv/app/packages/x12-edi-tools/src \
    PORT=8000 \
    X12_API_ENVIRONMENT=production \
    X12_API_FRONTEND_DIST_DIR=/srv/app/apps/web/dist

WORKDIR /srv/app

RUN adduser --disabled-password --gecos "" appuser

COPY VERSION README.md LICENSE /srv/app/
COPY packages/x12-edi-tools/pyproject.toml packages/x12-edi-tools/README.md /srv/app/packages/x12-edi-tools/
COPY packages/x12-edi-tools/src /srv/app/packages/x12-edi-tools/src
COPY apps/api/pyproject.toml apps/api/README.md /srv/app/apps/api/
COPY apps/api/app /srv/app/apps/api/app
COPY apps/api/templates /srv/app/apps/api/templates
COPY --from=web-builder /workspace/apps/web/dist /srv/app/apps/web/dist

RUN pip install --upgrade pip \
    && pip install --no-cache-dir /srv/app/packages/x12-edi-tools[all] \
    && pip install --no-cache-dir /srv/app/apps/api

RUN chown -R appuser:appuser /srv/app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{port}/api/v1/health', timeout=4)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
