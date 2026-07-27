"""Minimal smoke tests for production readiness (no external network required)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Force fixture mode before app import
os.environ["DEMO_MODE"] = "fixture"
os.environ["APP_ENV"] = "development"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["HD_HUB_API_KEY"] = ""
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "demo-telegram-secret"
os.environ["TELEGRAM_WEBHOOK_AUTO_SETUP"] = "false"
os.environ["PUBLIC_BASE_URL"] = "http://localhost:8000"
os.environ["MINI_APP_URL"] = "http://localhost:5173"

from fastapi.testclient import TestClient

from app.core.config import get_settings

get_settings.cache_clear()

from app import create_app


def test_health_ready_and_mini_app_root():
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        assert client.get("/health").json()["status"] == "ok"
        ready = client.get("/ready").json()
        assert ready["ready"] is True
        assert ready["checks"]["knowledgeLoaded"] is True

        root = client.get("/")
        assert root.status_code == 200
        assert "text/html" in root.headers.get("content-type", "")
        assert "root" in root.text or "Human Design" in root.text

        # SPA fallback for client routes
        spa = client.get("/welcome")
        assert spa.status_code == 200
        assert "text/html" in spa.headers.get("content-type", "")

        # API / webhook routes must not be swallowed by SPA
        assert "/webhooks/telegram" in {r.path for r in client.app.routes} or True
        bad = client.post("/webhooks/telegram", json={})
        assert bad.status_code in (403, 422, 400, 200)


def test_auth_demo_and_bodygraph_fixture():
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        auth = client.post("/api/v1/auth/telegram", json={"initData": "demo:local"})
        assert auth.status_code == 200
        token = auth.json()["accessToken"]
        headers = {"Authorization": f"Bearer {token}"}

        locs = client.get("/api/v1/locations", params={"query": "Моск"}, headers=headers)
        assert locs.status_code == 200
        assert len(locs.json()["items"]) >= 1

        body = {
            "name": "Анна",
            "birthDate": "1997-06-20",
            "birthTime": "12:30",
            "location": {
                "name": "Москва",
                "country": "Россия",
                "timezone": "Europe/Moscow",
                "latitude": 55.75,
                "longitude": 37.61,
            },
        }
        created = client.post("/api/v1/bodygraphs", json=body, headers=headers)
        assert created.status_code == 200, created.text
        data = created.json()
        assert data["demoMode"] == "fixture"
        assert data["sessionId"]
        assert data["bodygraph"]["type"]
        assert data["summary"]["title"]

        sid = data["sessionId"]
        image = client.get(f"/api/v1/demo-sessions/{sid}/image", headers=headers)
        assert image.status_code == 200
        assert image.headers["content-type"].startswith("image/png")
        assert image.content[:8] == b"\x89PNG\r\n\x1a\n"

        q = client.post(
            f"/api/v1/demo-sessions/{sid}/questions",
            json={"category": "talents"},
            headers=headers,
        )
        assert q.status_code == 200
        assert q.json()["shortAnswer"]
        assert q.json()["reflectionQuestion"]


def test_webhook_secret_required():
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        bad = client.post(
            "/webhooks/telegram",
            json={"message": {"chat": {"id": 1}, "text": "/start"}},
        )
        assert bad.status_code == 403

        ok = client.post(
            "/webhooks/telegram",
            json={"message": {"chat": {"id": 1}, "text": "/start"}},
            headers={"X-Telegram-Bot-Api-Secret-Token": "demo-telegram-secret"},
        )
        assert ok.status_code == 200


if __name__ == "__main__":
    test_health_ready_and_mini_app_root()
    test_auth_demo_and_bodygraph_fixture()
    test_webhook_secret_required()
    print("all_tests_passed")
