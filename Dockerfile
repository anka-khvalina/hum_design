# Multi-stage production image: Mini App + Human Design Service in one container.
# Secrets are injected at runtime via environment variables — never bake them in.

# ---- Stage 1: build Telegram Mini App ----
FROM node:22-alpine AS frontend
WORKDIR /frontend

COPY mini-app/package.json mini-app/package-lock.json ./
RUN npm ci

COPY mini-app/ ./
# Empty base URL → relative /api calls to the same Render service
ENV VITE_API_BASE_URL=
RUN npm run build

# ---- Stage 2: Python backend + static Mini App ----
FROM python:3.12-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY human-design-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY human-design-service/app ./app
COPY human-design-service/knowledge ./knowledge
COPY human-design-service/fixtures ./fixtures
COPY human-design-service/prompts ./prompts
COPY --from=frontend /frontend/dist ./app/static

ENV APP_ENV=production \
    PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

# Render injects PORT; default 8000 for local docker runs
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
