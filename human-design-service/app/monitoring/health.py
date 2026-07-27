from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["monitoring"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/ready")
async def ready(request: Request):
    settings = request.app.state.settings
    knowledge = request.app.state.knowledge
    checks = {
        "knowledgeLoaded": bool(knowledge.gates),
        "sessionSecret": bool(settings.session_secret),
        "demoMode": settings.demo_mode,
        "telegramConfigured": bool(settings.telegram_bot_token),
        "hdHubKeyConfigured": bool(settings.hd_hub_api_key),
        "llmConfigured": bool(settings.llm_api_key),
    }
    ready_ok = checks["knowledgeLoaded"] and checks["sessionSecret"]
    return {"ready": ready_ok, "checks": checks}
