from __future__ import annotations

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

    async def _post(self, method: str, json_body: dict[str, Any] | None = None, files=None, data=None) -> dict[str, Any]:
        if not self.configured:
            logger.warning('"provider=telegram operation=%s status=skipped"', method)
            return {"ok": True, "skipped": True}
        async with httpx.AsyncClient(timeout=20.0) as client:
            if files:
                response = await client.post(f"{self.base}/{method}", data=data, files=files)
            else:
                response = await client.post(f"{self.base}/{method}", json=json_body)
        if response.status_code >= 400:
            logger.error('"provider=telegram operation=%s status=%s"', method, response.status_code)
            raise RuntimeError(f"Telegram API error: {response.status_code}")
        return response.json()

    async def send_message(self, chat_id: int, text: str, reply_markup: dict | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            body["reply_markup"] = reply_markup
        return await self._post("sendMessage", body)

    async def send_photo(self, chat_id: int, photo: bytes, caption: str | None = None) -> dict[str, Any]:
        data = {"chat_id": str(chat_id)}
        if caption:
            data["caption"] = caption[:1024]
            data["parse_mode"] = "HTML"
        files = {"photo": ("bodygraph.png", photo, "image/png")}
        return await self._post("sendPhoto", files=files, data=data)

    def mini_app_keyboard(self) -> dict[str, Any]:
        return {
            "inline_keyboard": [
                [
                    {
                        "text": "✨ Построить мой BodyGraph",
                        "web_app": {"url": self.settings.mini_app_url},
                    }
                ]
            ]
        }
