"""Human Design Service — investor demo backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.knowledge.loader import KnowledgePackage
from app.monitoring.health import router as health_router
from app.sessions.store import SessionStore
from app.telegram.client import TelegramClient
from app.telegram.webhook import router as telegram_router

logger = logging.getLogger(__name__)

_SPA_BLOCKED = (
    "api",
    "api/",
    "webhooks",
    "webhooks/",
    "health",
    "ready",
    "docs",
    "openapi.json",
    "redoc",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    app.state.settings = settings
    app.state.sessions = SessionStore(ttl_seconds=settings.session_ttl_seconds)
    app.state.knowledge = KnowledgePackage.load(settings.knowledge_dir)
    logger.info(
        "service_started demo_mode=%s app_env=%s knowledge_gates=%s public_base_url=%s mini_app_url=%s",
        settings.demo_mode,
        settings.app_env,
        len(app.state.knowledge.gates),
        settings.public_base_url,
        settings.resolved_mini_app_url(),
    )

    if (
        settings.is_production
        and settings.telegram_webhook_auto_setup
        and settings.telegram_bot_token
        and settings.public_base_url
        and "localhost" not in settings.public_base_url
        and "127.0.0.1" not in settings.public_base_url
    ):
        try:
            client = TelegramClient(settings)
            await client.set_webhook()
        except Exception as exc:
            logger.error(
                '"provider=telegram operation=setWebhook status=error error=%s"',
                type(exc).__name__,
            )

    yield
    app.state.sessions.clear()
    logger.info("service_stopped")


def _mount_static(app: FastAPI, static_dir: Path) -> None:
    if not static_dir.exists():
        logger.info('"static_dir missing path=%s — Mini App assets not mounted"', static_dir)
        return

    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    index_file = static_dir / "index.html"

    @app.get("/")
    async def serve_index():
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="Mini App build not found")
        return FileResponse(index_file)

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path in _SPA_BLOCKED or full_path.startswith(("api/", "webhooks/")):
            raise HTTPException(status_code=404, detail="Not found")

        candidate = (static_dir / full_path).resolve()
        try:
            candidate.relative_to(static_dir.resolve())
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="Not found") from exc

        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        if not index_file.exists():
            raise HTTPException(status_code=404, detail="Mini App build not found")
        return FileResponse(index_file)

    logger.info('"static_mounted path=%s"', static_dir)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Human Design Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(telegram_router)
    app.include_router(api_router, prefix="/api/v1")
    _mount_static(app, settings.static_dir)
    return app


app = create_app()
