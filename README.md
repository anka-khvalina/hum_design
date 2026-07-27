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

In **production** (Render) one Web Service serves:
- Mini App at `/`
- API at `/api/v1/*`
- Telegram webhook at `/webhooks/telegram`
- health at `/health` and `/ready`

---

## Environment variables

Используются только переменные, которые реально читает код (`app/core/config.py`):

| Variable | Required | Description |
| --- | --- | --- |
| `APP_ENV` | yes (prod) | `development` локально, `production` на Render |
| `PUBLIC_BASE_URL` | yes (prod) | Публичный HTTPS URL сервиса (backend + webhook), например `https://human-design-bot.onrender.com` |
| `MINI_APP_URL` | yes (prod) | HTTPS URL Mini App. На Render = тот же URL, что и `PUBLIC_BASE_URL` |
| `SESSION_SECRET` | yes | Секрет подписи JWT Mini App |
| `TELEGRAM_BOT_TOKEN` | yes (prod) | Токен бота от @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | yes (prod) | Secret token для заголовка `X-Telegram-Bot-Api-Secret-Token` |
| `TELEGRAM_WEBHOOK_AUTO_SETUP` | no | `true` (по умолчанию) — зарегистрировать webhook при старте в production |
| `HD_HUB_API_KEY` | yes | Ключ Human Design Hub (`X-API-KEY`) |
| `HD_HUB_BASE_URL` | no | По умолчанию `https://api.humandesignhub.app` |
| `HD_HUB_TIMEOUT_SECONDS` | no | Таймаут Hub (по умолчанию `15`) |
| `DEMO_MODE` | no | `auto` (рекомендуется) \| `live` \| `fixture` |
| `LLM_API_KEY` | no | OpenAI-compatible ключ; без него работают шаблонные интерпретации |
| `LLM_BASE_URL` | no | По умолчанию `https://api.openai.com/v1` |
| `LLM_MODEL` | no | По умолчанию `gpt-4o-mini` |
| `LLM_ENABLED` | no | `true` / `false` |
| `LLM_TIMEOUT_SECONDS` | no | По умолчанию `30` |
| `CORS_ORIGINS` | no | По умолчанию `*` |
| `SESSION_TTL_SECONDS` | no | По умолчанию `3600` |
| `AUTH_TOKEN_TTL_SECONDS` | no | По умолчанию `3600` |
| `INIT_DATA_MAX_AGE_SECONDS` | no | По умолчанию `86400` |
| `PORT` | Render | Render задаёт сам; приложение слушает `0.0.0.0:$PORT` |

Секреты передаются только через environment variables. Не коммитьте `.env`.

---

## Local development

### Backend

```bash
cd human-design-service
cp .env.example .env
# заполните HD_HUB_API_KEY (и при необходимости TELEGRAM_BOT_TOKEN, LLM_API_KEY)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Mini App

```bash
cd mini-app
npm install
npm run dev
```

Откройте `http://localhost:5173`. Без Telegram используется `initData: "demo:local"`.

В dev Mini App ходит на `http://localhost:8000`. В production build API base пустой (same-origin).

### Docker (один контейнер, как на Render)

```bash
docker build -t human-design-bot .
docker run --rm -p 8000:8000 \
  -e APP_ENV=production \
  -e PORT=8000 \
  -e PUBLIC_BASE_URL=https://your-service.onrender.com \
  -e MINI_APP_URL=https://your-service.onrender.com \
  -e SESSION_SECRET=... \
  -e TELEGRAM_BOT_TOKEN=... \
  -e TELEGRAM_WEBHOOK_SECRET=... \
  -e HD_HUB_API_KEY=... \
  -e DEMO_MODE=auto \
  human-design-bot
```

Или `docker compose up --build` для раздельного локального запуска backend + nginx Mini App.

---

## Deploy on Render

### Вариант A — Blueprint (`render.yaml`)

1. Запушьте ветку в GitHub.
2. Render Dashboard → **New** → **Blueprint**.
3. Выберите репозиторий `hum_design`.
4. Render прочитает `render.yaml` и создаст один Web Service (`runtime: docker`).
5. Заполните sync:false переменные (см. список ниже).
6. После первого деплоя скопируйте URL сервиса (например `https://human-design-bot.onrender.com`) и задайте:
   - `PUBLIC_BASE_URL=https://human-design-bot.onrender.com`
   - `MINI_APP_URL=https://human-design-bot.onrender.com`
7. Redeploy. При `APP_ENV=production` и `TELEGRAM_WEBHOOK_AUTO_SETUP=true` сервис сам вызовет `setWebhook`.

### Вариант B — вручную один Web Service

1. **New** → **Web Service** → подключите GitHub repo.
2. Settings:
   - **Runtime:** Docker
   - **Dockerfile Path:** `./Dockerfile`
   - **Docker Context:** `.`
   - **Health Check Path:** `/health`
3. Build / Start (Docker):
   - **Build Command:** *(не нужен — собирает Dockerfile)*
   - **Start Command:** *(из Dockerfile)* `sh -c "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"`
4. Добавьте Environment Variables (полный список выше).
5. Deploy.

### Регистрация Telegram webhook

**Автоматически:** при `APP_ENV=production`, непустых `TELEGRAM_BOT_TOKEN` + `PUBLIC_BASE_URL` (не localhost) и `TELEGRAM_WEBHOOK_AUTO_SETUP=true` webhook регистрируется на старте:

```text
POST {PUBLIC_BASE_URL}/webhooks/telegram
```

с `secret_token = TELEGRAM_WEBHOOK_SECRET`. Backend проверяет заголовок `X-Telegram-Bot-Api-Secret-Token`.

**Вручную (безопасно, без печати токена в Dockerfile):**

```bash
# локально, с production env
cd human-design-service
export APP_ENV=production
export PUBLIC_BASE_URL=https://your-service.onrender.com
export MINI_APP_URL=https://your-service.onrender.com
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_WEBHOOK_SECRET=...
python -m app.telegram.set_webhook
```

### BotFather

1. `/setmenubutton` или Configure Mini App → URL = `MINI_APP_URL` (корневой HTTPS URL Render).
2. Команды: `/start`, `/bodygraph`, `/help`, `/about`.

---

## Webhook path

```text
POST /webhooks/telegram
```

Полный URL: `{PUBLIC_BASE_URL}/webhooks/telegram`

---

## Post-deploy checklist

1. Открыть `https://<service>.onrender.com/health` → `{"status":"ok"}`
2. Открыть `https://<service>.onrender.com/ready` → `"ready": true`
3. Открыть корень `https://<service>.onrender.com/` → загружается Mini App
4. В BotFather указать Mini App URL = корневой URL сервиса
5. Проверить webhook: `getWebhookInfo` или логи старта (`setWebhook status=ok`)
6. В Telegram: `/start` → кнопка «Построить мой BodyGraph» → форма → расчёт
7. Проверить badge режима для презентующего: `LIVE` или `DEMO FALLBACK`
8. «Отправить результат в Telegram» → фото + текст в личный чат

---

## Demo mode

| Value | Behavior |
| --- | --- |
| `live` | только Human Design Hub |
| `fixture` | только fixtures |
| `auto` | Hub + fallback на fixtures (рекомендуется) |

Free Hub plan: locations / timezone / `simple-bodygraph`. `/v2/bodygraph` и image — Standard+; сервис сам переключается на simple + локальный PNG.

## Scope

**In:** Telegram auth, birth form, Hub calculation, bodygraph image, summary, Q&A, send-to-chat, in-memory sessions, fixture fallback.

**Out:** persistent DB, payments, history, multi-profile, admin panel.
