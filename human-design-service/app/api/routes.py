from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth.telegram import create_access_token, decode_access_token, validate_telegram_init_data
from app.bodygraph.service import BodygraphService
from app.telegram.client import TelegramClient

logger = logging.getLogger(__name__)
api_router = APIRouter()


class AuthRequest(BaseModel):
    initData: str


class LocationOut(BaseModel):
    id: str
    name: str
    region: str | None = None
    country: str
    timezone: str
    latitude: float
    longitude: float


class BirthLocation(BaseModel):
    name: str
    region: str | None = None
    country: str
    timezone: str
    latitude: float
    longitude: float


class BodygraphRequest(BaseModel):
    name: str
    birthDate: str
    birthTime: str
    location: BirthLocation


class QuestionRequest(BaseModel):
    category: str | None = None
    questionType: str | None = None
    question: str | None = Field(default=None, max_length=400)

    def resolved_category(self) -> str:
        return (self.category or self.questionType or "").strip()


def get_service(request: Request) -> BodygraphService:
    return BodygraphService(
        settings=request.app.state.settings,
        knowledge=request.app.state.knowledge,
        sessions=request.app.state.sessions,
    )


def current_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(request.app.state.settings, token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return {
        "telegramUserId": int(payload["telegram_user_id"]),
        "firstName": payload.get("first_name"),
        "languageCode": payload.get("language_code", "ru"),
    }


@api_router.post("/auth/telegram")
async def auth_telegram(body: AuthRequest, request: Request):
    settings = request.app.state.settings
    try:
        validated = validate_telegram_init_data(
            body.initData,
            settings.telegram_bot_token,
            settings.init_data_max_age_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Ошибка авторизации Telegram") from exc

    user = validated["user"]
    token, expires_in = create_access_token(settings, user)
    return {
        "accessToken": token,
        "expiresIn": expires_in,
        "user": {
            "telegramUserId": user.get("id"),
            "firstName": user.get("first_name"),
            "languageCode": user.get("language_code", "ru"),
        },
    }


@api_router.get("/locations")
async def locations(
    query: str,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
    service: BodygraphService = Depends(get_service),
):
    try:
        items = await service.search_locations(query)
    except Exception as exc:
        logger.error('"operation=locations error=%s"', type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="Сейчас не удалось подключиться к сервису расчета. Мы уже знаем о проблеме.",
        ) from exc
    return {"items": items}


@api_router.post("/bodygraphs")
async def create_bodygraph(
    body: BodygraphRequest,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
    service: BodygraphService = Depends(get_service),
):
    try:
        result = await service.calculate(user["telegramUserId"], body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error('"operation=bodygraphs error=%s"', type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail="Сейчас не удалось подключиться к сервису расчета. Мы уже знаем о проблеме.",
        ) from exc
    return result


@api_router.get("/demo-sessions/{session_id}/image")
async def session_image(
    session_id: str,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
):
    session = request.app.state.sessions.get_for_user(session_id, user["telegramUserId"])
    if not session:
        raise HTTPException(
            status_code=404,
            detail="Временная сессия завершилась. Для защиты данных мы не сохраняем карту после закрытия демо.",
        )
    return Response(content=session.image_png, media_type="image/png")


@api_router.get("/demo-sessions/{session_id}")
async def get_session(
    session_id: str,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
    service: BodygraphService = Depends(get_service),
):
    session = request.app.state.sessions.get_for_user(session_id, user["telegramUserId"])
    if not session:
        raise HTTPException(
            status_code=410,
            detail="Временная сессия завершилась. Для защиты данных мы не сохраняем карту после закрытия демо.",
        )
    return service._session_response(session)


@api_router.post("/demo-sessions/{session_id}/questions")
async def ask_question(
    session_id: str,
    body: QuestionRequest,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
    service: BodygraphService = Depends(get_service),
):
    session = request.app.state.sessions.get_for_user(session_id, user["telegramUserId"])
    if not session:
        raise HTTPException(
            status_code=410,
            detail="Временная сессия завершилась. Построй карту еще раз.",
        )
    try:
        category = body.resolved_category()
        if not category:
            raise ValueError("Укажите категорию вопроса")
        return await service.answer_question(session, category, body.question)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@api_router.post("/demo-sessions/{session_id}/send-to-telegram")
async def send_to_telegram(
    session_id: str,
    request: Request,
    user: dict[str, Any] = Depends(current_user),
):
    settings = request.app.state.settings
    session = request.app.state.sessions.get_for_user(session_id, user["telegramUserId"])
    if not session:
        raise HTTPException(status_code=410, detail="Временная сессия завершилась.")

    chart = session.normalized_bodygraph
    name = session.birth_data.get("name", "")
    caption = (
        f"<b>{name}</b>\n"
        f"Тип: {chart.get('type') or '—'}\n"
        f"Стратегия: {chart.get('strategy') or '—'}\n"
        f"Авторитет: {chart.get('authority') or '—'}\n"
        f"Профиль: {chart.get('profile') or '—'}"
    )
    text = (
        f"<b>{session.summary.get('title', '')}</b>\n\n"
        f"{session.summary.get('text', '')}"
    )
    keyboard = {
        "inline_keyboard": [
            [{"text": "Открыть полный разбор", "web_app": {"url": settings.mini_app_url}}]
        ]
    }

    client = TelegramClient(settings)
    await client.send_photo(user["telegramUserId"], session.image_png, caption)
    await client.send_message(user["telegramUserId"], text[:3900], keyboard)
    return {"success": True}
