"""Telegram Bot API client and webhook helpers."""

from __future__ import annotations

import html
import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.token = settings.telegram_bot_token
        self.base = f"https://api.telegram.org/bot{self.token}" if self.token else ""

    @property
    def configured(self) -> bool:
        return bool(self.token)

    async def _post(
        self,
        method: str,
        json_body: dict[str, Any] | None = None,
        files=None,
        data=None,
    ) -> dict[str, Any]:
        if not self.configured:
            logger.warning('"provider=telegram operation=%s status=skipped"', method)
            return {"ok": True, "skipped": True}
        async with httpx.AsyncClient(timeout=15.0) as client:
            if files:
                response = await client.post(f"{self.base}/{method}", data=data, files=files)
            else:
                response = await client.post(f"{self.base}/{method}", json=json_body)

        try:
            payload = response.json()
        except Exception:
            payload = {"ok": False, "description": response.text[:300]}

        if response.status_code >= 400 or not payload.get("ok", False):
            description = str(payload.get("description") or response.text[:200])
            logger.error(
                '"provider=telegram operation=%s status=%s description=%s"',
                method,
                response.status_code,
                description.replace('"', "'"),
            )
            raise RuntimeError(f"Telegram API error: {description}")
        return payload

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_markup: dict | None = None,
        *,
        parse_mode: str | None = "HTML",
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text[:4096],
            "disable_web_page_preview": True,
        }
        if parse_mode:
            body["parse_mode"] = parse_mode
        if reply_markup:
            body["reply_markup"] = reply_markup
        try:
            return await self._post("sendMessage", body)
        except RuntimeError:
            # Fast fallback: plain text only (no second keyboard attempt).
            plain = {
                "chat_id": chat_id,
                "text": html.unescape(text)[:4096],
                "disable_web_page_preview": True,
            }
            return await self._post("sendMessage", plain)

    async def send_photo(
        self,
        chat_id: int,
        photo: bytes,
        caption: str | None = None,
        *,
        parse_mode: str | None = "HTML",
    ) -> dict[str, Any]:
        data: dict[str, str] = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption[:1024]
            if parse_mode:
                data["parse_mode"] = parse_mode
        files = {"photo": ("bodygraph.png", photo, "image/png")}
        try:
            return await self._post("sendPhoto", files=files, data=data)
        except RuntimeError:
            if caption and parse_mode:
                data_plain = {"chat_id": str(chat_id), "caption": html.unescape(caption)[:1024]}
                return await self._post("sendPhoto", files=files, data=data_plain)
            raise

    def mini_app_keyboard(self) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "✨ Построить мой BodyGraph",
                        "web_app": {"url": self.settings.resolved_mini_app_url()},
                    }
                ]
            ]
        }

    def open_app_keyboard(self) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "Открыть полный разбор",
                        "url": self.settings.resolved_mini_app_url(),
                    }
                ]
            ]
        }

    def questions_keyboard(self) -> dict[str, Any]:
        """Category buttons for post-bodygraph Q&A in Telegram chat."""
        rows = [
            [("✨ Мои главные таланты", "q:talents")],
            [("🧭 Мое направление", "q:direction")],
            [("💼 Работа и реализация", "q:work")],
            [("💰 Деньги и ресурсы", "q:money")],
            [("💬 Мой характер и общение", "q:character")],
            [("❤️ Я в отношениях", "q:relationships")],
            [("⚡ Моя энергия и восстановление", "q:energy")],
            [("✍️ Задать свой вопрос", "q:custom")],
            [("Открыть полный разбор", "url")],
        ]
        keyboard: list[list[dict[str, str]]] = []
        for row in rows:
            buttons: list[dict[str, str]] = []
            for text, action in row:
                if action == "url":
                    buttons.append({"text": text, "url": self.settings.resolved_mini_app_url()})
                else:
                    buttons.append({"text": text, "callback_data": action})
            keyboard.append(buttons)
        return {"inline_keyboard": keyboard}

    async def answer_callback_query(
        self, callback_query_id: str, text: str | None = None, show_alert: bool = False
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            body["text"] = text[:200]
            body["show_alert"] = show_alert
        return await self._post("answerCallbackQuery", body)

    def webhook_url(self) -> str:
        base = self.settings.public_base_url.rstrip("/")
        return f"{base}/webhooks/telegram"

    async def set_webhook(self) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        if not self.settings.public_base_url:
            raise RuntimeError("PUBLIC_BASE_URL is not configured")
        if (
            "localhost" in self.settings.public_base_url
            or "127.0.0.1" in self.settings.public_base_url
        ):
            raise RuntimeError("PUBLIC_BASE_URL must be a public HTTPS URL in production")

        payload: dict[str, Any] = {
            "url": self.webhook_url(),
            "allowed_updates": ["message", "callback_query"],
            "drop_pending_updates": False,
        }
        if self.settings.telegram_webhook_secret:
            payload["secret_token"] = self.settings.telegram_webhook_secret

        result = await self._post("setWebhook", payload)
        logger.info(
            '"provider=telegram operation=setWebhook status=ok url=%s"',
            self.webhook_url(),
        )
        return result

    async def get_webhook_info(self) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.base}/getWebhookInfo")
        if response.status_code >= 400:
            raise RuntimeError(f"Telegram API error: {response.status_code}")
        return response.json()


def html_escape(value: str) -> str:
    return html.escape(value or "", quote=False)
