from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class LLMAdapter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def available(self) -> bool:
        return bool(self.settings.llm_enabled and self.settings.llm_api_key)

    async def generate_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
        if not self.available:
            return None

        payload = {
            "model": self.settings.llm_model,
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.settings.llm_timeout_seconds) as client:
                    response = await client.post(
                        f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.settings.llm_api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                if response.status_code >= 400:
                    logger.error('"provider=llm status=%s attempt=%s"', response.status_code, attempt + 1)
                    continue
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed
            except Exception as exc:
                logger.error('"provider=llm error=%s attempt=%s"', type(exc).__name__, attempt + 1)
        return None
