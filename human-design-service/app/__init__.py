"""Human Design Service — investor demo backend."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.knowledge.loader import KnowledgePackage
from app.monitoring.health import router as health_router
from app.sessions.store import SessionStore
from app.telegram.webhook import router as telegram_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    app.state.settings = settings
    app.state.sessions = SessionStore(ttl_seconds=settings.session_ttl_seconds)
    app.state.knowledge = KnowledgePackage.load(settings.knowledge_dir)
    logger.info(
        "service_started demo_mode=%s knowledge_gates=%s",
        settings.demo_mode,
        len(app.state.knowledge.gates),
    )
    yield
    app.state.sessions.clear()
    logger.info("service_stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Human Design Service",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(telegram_router)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
