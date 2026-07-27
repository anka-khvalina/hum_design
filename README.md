# Human Design: предназначение

Investor Demo / MVP 0.1 — Telegram Mini App + backend for personal BodyGraph calculation and interpretation.

## Architecture

```text
Telegram Bot → Telegram Mini App → Human Design Service
                                      ├── Human Design Hub API
                                      ├── LLM Provider (optional)
                                      ├── Knowledge Package
                                      └── In-memory sessions (TTL 60m)
```

Mini App never talks to Human Design Hub directly. API keys stay on the backend.

## Quick start

### 1. Backend

```bash
cd human-design-service
cp .env.example .env   # fill secrets
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

### 2. Mini App

```bash
cd mini-app
npm install
npm run dev
```

Open `http://localhost:5173` — in browser demo mode auth uses `initData: "demo:local"` (works without Telegram bot token).

### 3. Docker

```bash
cp human-design-service/.env.example human-design-service/.env
docker compose up --build
```

## Environment

| Variable | Purpose |
| --- | --- |
| `HD_HUB_API_KEY` | Human Design Hub `X-API-KEY` |
| `TELEGRAM_BOT_TOKEN` | Bot token |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook `secret_token` |
| `SESSION_SECRET` | JWT signing for Mini App sessions |
| `DEMO_MODE` | `live` \| `fixture` \| `auto` |
| `LLM_API_KEY` | Optional OpenAI-compatible key |
| `MINI_APP_URL` | Public Mini App URL for bot button |

## Demo mode

- `live` — only real Human Design Hub
- `fixture` — only prepared fixtures
- `auto` — live with fixture fallback (recommended for investor demos)

Free Hub plan supports locations, timezone resolve, and `simple-bodygraph`. Full `/v2/bodygraph` and image endpoints require Standard+; the service automatically falls back to `simple-bodygraph` and a locally rendered PNG.

## Telegram setup

1. Create a bot via @BotFather, set Mini App URL.
2. Set webhook:

```bash
curl -X POST "https://api.telegram.org/bot$TOKEN/setWebhook" \
  -d "url=$PUBLIC_BASE_URL/webhooks/telegram" \
  -d "secret_token=$TELEGRAM_WEBHOOK_SECRET"
```

## API surface

- `POST /api/v1/auth/telegram`
- `GET /api/v1/locations?query=`
- `POST /api/v1/bodygraphs`
- `GET /api/v1/demo-sessions/{id}/image`
- `POST /api/v1/demo-sessions/{id}/questions`
- `POST /api/v1/demo-sessions/{id}/send-to-telegram`
- `POST /webhooks/telegram`
- `GET /health`, `GET /ready`

## Knowledge package

Author methodology for all 64 gates (from «Справочник Дело Жизни и Линия») plus types, authorities, profiles, definitions, centers, and question rules lives in `human-design-service/knowledge/`.

## Scope of this demo

In scope: Telegram auth, birth form, Hub calculation, bodygraph image, summary, Q&A, send-to-chat, in-memory sessions, fixture fallback.

Out of scope: persistent DB, payments, history, multi-profile, admin panel.
