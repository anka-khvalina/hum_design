from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.telegram.client import TelegramClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["telegram"])

WELCOME = (
    "Привет! Я помогу тебе построить персональный BodyGraph и посмотреть на свои "
    "сильные стороны, таланты и естественные способы принимать решения.\n\n"
    "Это не предсказание будущего, а инструмент для знакомства с собой."
)

HELP = (
    "Команды:\n"
    "/start — начать работу\n"
    "/bodygraph — построить карту\n"
    "/help — помощь\n"
    "/about — о проекте"
)

ABOUT = (
    "<b>Human Design: предназначение</b>\n"
    "Демонстрационная версия инструмента самопознания. "
    "Через карту ты изучаешь качества, таланты и способы принятия решений."
)


@router.post("/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    settings = request.app.state.settings
    expected = settings.telegram_webhook_secret
    if expected and x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    update: dict[str, Any] = await request.json()
    client = TelegramClient(settings)

    message = update.get("message") or update.get("edited_message")
    callback = update.get("callback_query")

    if callback:
        data = callback.get("data") or ""
        chat_id = callback.get("message", {}).get("chat", {}).get("id")
        if chat_id and data == "open_bodygraph":
            await client.send_message(chat_id, "Открываю Mini App…", client.mini_app_keyboard())
        return {"ok": True}

    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    web_app_data = message.get("web_app_data")

    if web_app_data:
        await client.send_message(chat_id, "Получил данные из Mini App. Открой карту снова, если нужно продолжить.")
        return {"ok": True}

    if text.startswith("/start") or text.startswith("/bodygraph"):
        await client.send_message(chat_id, WELCOME, client.mini_app_keyboard())
    elif text.startswith("/help"):
        await client.send_message(chat_id, HELP)
    elif text.startswith("/about"):
        await client.send_message(chat_id, ABOUT)
    else:
        await client.send_message(
            chat_id,
            "Нажми кнопку ниже, чтобы построить BodyGraph.",
            client.mini_app_keyboard(),
        )
    return {"ok": True}
