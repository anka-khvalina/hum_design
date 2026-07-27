from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl

from jose import JWTError, jwt

from app.core.config import Settings


def validate_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int) -> dict[str, Any]:
    if not init_data:
        raise ValueError("initData пуст")
    if not bot_token:
        # Demo / local development without Telegram: allow signed mock
        if init_data.startswith("demo:"):
            return {
                "user": {
                    "id": 100001,
                    "first_name": "Демо",
                    "language_code": "ru",
                },
                "auth_date": int(time.time()),
            }
        raise ValueError("Telegram bot token не настроен")

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("Отсутствует hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated, received_hash):
        raise ValueError("Неверная подпись initData")

    auth_date = int(parsed.get("auth_date", "0"))
    if auth_date <= 0 or int(time.time()) - auth_date > max_age_seconds:
        raise ValueError("initData устарел")

    user_raw = parsed.get("user")
    user = json.loads(user_raw) if user_raw else {}
    return {"user": user, "auth_date": auth_date, "raw": parsed}


def create_access_token(settings: Settings, telegram_user: dict[str, Any]) -> tuple[str, int]:
    expires_in = settings.auth_token_ttl_seconds
    now = int(time.time())
    payload = {
        "sub": str(telegram_user.get("id")),
        "telegram_user_id": telegram_user.get("id"),
        "first_name": telegram_user.get("first_name"),
        "language_code": telegram_user.get("language_code", "ru"),
        "iat": now,
        "exp": now + expires_in,
    }
    token = jwt.encode(payload, settings.session_secret, algorithm="HS256")
    return token, expires_in


def decode_access_token(settings: Settings, token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.session_secret, algorithms=["HS256"])
    except JWTError as exc:
        raise ValueError("Недействительный токен") from exc
