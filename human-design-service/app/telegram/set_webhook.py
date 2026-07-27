"""CLI: register Telegram webhook using PUBLIC_BASE_URL and secrets from env."""

from __future__ import annotations

import asyncio
import json
import sys

from app.core.config import get_settings
from app.telegram.client import TelegramClient


async def main() -> int:
    settings = get_settings()
    client = TelegramClient(settings)
    try:
        result = await client.set_webhook()
    except Exception as exc:
        print(f"Webhook registration failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    info = await client.get_webhook_info()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
