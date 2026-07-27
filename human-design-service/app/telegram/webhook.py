from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request

from app.bodygraph.service import BodygraphService
from app.telegram.client import TelegramClient, html_escape

logger = logging.getLogger(__name__)
router = APIRouter(tags=["telegram"])

WELCOME = (
    "Привет! Я помогу тебе построить персональный BodyGraph и посмотреть на свои "
    "сильные стороны, таланты и естественные способы принимать решения.\n\n"
    "Это не предсказание будущего, а инструмент для знакомства с собой."
)

HELP = (
    "Команды:\n"
    "/start — начать работу\n"
    "/bodygraph — построить карту\n"
    "/help — помощь\n"
    "/about — о проекте"
)

ABOUT = (
    "<b>Human Design: предназначение</b>\n"
    "Демонстрационная версия инструмента самопознания. "
    "Через карту ты изучаешь качества, таланты и способы принятия решений."
)

# telegram_user_id -> waiting for free-text custom question
_pending_custom: dict[int, bool] = {}

QUESTION_CATEGORIES = {
    "talents",
    "direction",
    "work",
    "money",
    "character",
    "relationships",
    "energy",
    "custom",
}


def _format_answer(answer: dict[str, Any]) -> str:
    title = html_escape(str(answer.get("title") or "Ответ по карте"))
    short = html_escape(str(answer.get("shortAnswer") or answer.get("answer") or ""))
    strength = html_escape(str(answer.get("strength") or ""))
    attention = html_escape(str(answer.get("attentionPoint") or ""))
    reflection = html_escape(str(answer.get("reflectionQuestion") or ""))
    based = answer.get("basedOn") or answer.get("usedChartElements") or []
    based_lines = "\n".join(f"• {html_escape(str(item))}" for item in based[:8])

    manifestations = answer.get("manifestations") or []
    manif = "\n".join(f"• {html_escape(str(item))}" for item in manifestations[:5])

    parts = [f"<b>{title}</b>", "", short]
    if manif:
        parts.extend(["", "<b>Как это может проявляться</b>", manif])
    if strength:
        parts.extend(["", "<b>Сильная сторона</b>", strength])
    if attention:
        parts.extend(["", "<b>На что обратить внимание</b>", attention])
    if based_lines:
        parts.extend(["", "<b>На чем основан ответ</b>", based_lines])
    if reflection:
        parts.extend(["", "<b>Вопрос для самонаблюдения</b>", reflection])
    return "\n".join(parts)[:3900]


@router.post("/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    settings = request.app.state.settings
    expected = settings.telegram_webhook_secret
    if expected and x_telegram_bot_api_secret_token != expected:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    update: dict[str, Any] = await request.json()
    client = TelegramClient(settings)
    sessions = request.app.state.sessions
    knowledge = request.app.state.knowledge

    message = update.get("message") or update.get("edited_message")
    callback = update.get("callback_query")

    if callback:
        await _handle_callback(callback, client, sessions, knowledge, settings)
        return {"ok": True}

    if not message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    user_id = int((message.get("from") or {}).get("id") or chat_id)
    text = (message.get("text") or "").strip()
    web_app_data = message.get("web_app_data")

    if web_app_data:
        await client.send_message(
            chat_id,
            "Получил данные из Mini App. Если карта уже построена — выберите вопрос ниже "
            "или откройте полный разбор.",
            client.questions_keyboard(),
        )
        return {"ok": True}

    # Free-text custom question after pressing ✍️
    if _pending_custom.pop(user_id, False) and text and not text.startswith("/"):
        session = sessions.get_latest_for_user(user_id)
        if not session:
            await client.send_message(
                chat_id,
                "Сессия карты завершилась. Постройте BodyGraph ещё раз.",
                client.mini_app_keyboard(),
            )
            return {"ok": True}
        service = BodygraphService(settings=settings, knowledge=knowledge, sessions=sessions)
        try:
            answer = await service.answer_question(session, "custom", text)
            await client.send_message(chat_id, _format_answer(answer), client.questions_keyboard())
        except Exception:
            logger.exception('"operation=telegram_custom_question status=error"')
            await client.send_message(
                chat_id,
                "Не удалось сформировать ответ. Попробуйте ещё раз или откройте Mini App.",
                client.questions_keyboard(),
            )
        return {"ok": True}

    if text.startswith("/start") or text.startswith("/bodygraph"):
        await client.send_message(chat_id, WELCOME, client.mini_app_keyboard())
    elif text.startswith("/help"):
        await client.send_message(chat_id, HELP)
    elif text.startswith("/about"):
        await client.send_message(chat_id, ABOUT)
    else:
        session = sessions.get_latest_for_user(user_id)
        if session:
            await client.send_message(
                chat_id,
                "Выберите, что хотите узнать о себе:",
                client.questions_keyboard(),
            )
        else:
            await client.send_message(
                chat_id,
                "Нажми кнопку ниже, чтобы построить BodyGraph.",
                client.mini_app_keyboard(),
            )
    return {"ok": True}


async def _handle_callback(
    callback: dict[str, Any],
    client: TelegramClient,
    sessions,
    knowledge,
    settings,
) -> None:
    data = callback.get("data") or ""
    callback_id = callback.get("id") or ""
    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    user_id = int((callback.get("from") or {}).get("id") or chat_id or 0)

    if not chat_id:
        return

    if data == "open_bodygraph":
        await client.answer_callback_query(callback_id)
        await client.send_message(chat_id, "Открываю Mini App…", client.mini_app_keyboard())
        return

    if not data.startswith("q:"):
        await client.answer_callback_query(callback_id)
        return

    category = data.split(":", 1)[1].strip()
    if category not in QUESTION_CATEGORIES:
        await client.answer_callback_query(callback_id, "Неизвестная категория")
        return

    session = sessions.get_latest_for_user(user_id)
    if not session:
        await client.answer_callback_query(
            callback_id,
            "Сессия карты завершилась. Постройте карту ещё раз.",
            show_alert=True,
        )
        await client.send_message(chat_id, "Построим карту заново?", client.mini_app_keyboard())
        return

    if category == "custom":
        _pending_custom[user_id] = True
        await client.answer_callback_query(callback_id)
        await client.send_message(
            chat_id,
            "✍️ Напишите свой вопрос следующим сообщением.\n"
            "Например: «Почему мне сложно выбрать одно направление?»",
        )
        return

    await client.answer_callback_query(callback_id, "Готовим ответ…")
    service = BodygraphService(settings=settings, knowledge=knowledge, sessions=sessions)
    try:
        answer = await service.answer_question(session, category)
        await client.send_message(chat_id, _format_answer(answer), client.questions_keyboard())
    except Exception:
        logger.exception('"operation=telegram_question category=%s status=error"', category)
        await client.send_message(
            chat_id,
            "Не удалось сформировать ответ. Попробуйте ещё раз.",
            client.questions_keyboard(),
        )
