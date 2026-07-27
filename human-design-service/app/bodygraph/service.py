from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.bodygraph.image import generate_bodygraph_png
from app.bodygraph.normalize import normalize_bodygraph
from app.core.config import Settings
from app.fixtures.loader import load_fixture_chart
from app.integrations.human_design_hub.adapter import HumanDesignHubAdapter, HumanDesignHubError
from app.integrations.llm.adapter import LLMAdapter
from app.interpretation.engine import (
    build_question_fallback,
    build_summary_fallback,
    validate_llm_answer,
)
from app.knowledge.loader import KnowledgePackage
from app.sessions.store import DemoSession, SessionStore

logger = logging.getLogger(__name__)

NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁёІіЇїЄєҐґ'’\- ]{2,50}$")


class BodygraphService:
    def __init__(self, settings: Settings, knowledge: KnowledgePackage, sessions: SessionStore):
        self.settings = settings
        self.knowledge = knowledge
        self.sessions = sessions
        self.hub = HumanDesignHubAdapter(settings)
        self.llm = LLMAdapter(settings)
        self._location_cache: dict[str, list[dict[str, Any]]] = {}

    def validate_birth_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = (payload.get("name") or "").strip()
        if not NAME_RE.match(name):
            raise ValueError("Имя должно содержать 2–50 букв, пробел, дефис или апостроф")
        # Strip potential HTML
        if "<" in name or ">" in name:
            raise ValueError("Недопустимые символы в имени")

        birth_date = payload.get("birthDate") or ""
        birth_time = payload.get("birthTime") or ""
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", birth_date):
            raise ValueError("Некорректная дата рождения")
        if not re.match(r"^\d{2}:\d{2}$", birth_time):
            raise ValueError("Некорректное время рождения")

        from datetime import date, datetime

        try:
            d = date.fromisoformat(birth_date)
        except ValueError as exc:
            raise ValueError("Некорректная дата рождения") from exc
        if d.year < 1900 or d > date.today():
            raise ValueError("Дата рождения вне допустимого диапазона")

        hh, mm = map(int, birth_time.split(":"))
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError("Время рождения вне диапазона")

        location = payload.get("location") or {}
        required_loc = ["name", "country", "timezone", "latitude", "longitude"]
        for key in required_loc:
            if location.get(key) in (None, ""):
                raise ValueError("Необходимо выбрать место рождения из списка")

        return {
            "name": name,
            "birthDate": birth_date,
            "birthTime": birth_time,
            "location": {
                "name": location["name"],
                "region": location.get("region"),
                "country": location["country"],
                "timezone": location["timezone"],
                "latitude": float(location["latitude"]),
                "longitude": float(location["longitude"]),
            },
        }

    async def search_locations(self, query: str) -> list[dict[str, Any]]:
        q = query.strip()
        if len(q) < 2:
            return []
        cache_key = q.lower()
        if cache_key in self._location_cache:
            return self._location_cache[cache_key]

        mode = self.settings.demo_mode
        if mode == "fixture":
            items = self._fixture_locations(q)
            self._location_cache[cache_key] = items
            return items

        try:
            items = await self.hub.search_locations(q)
            self._location_cache[cache_key] = items
            return items
        except HumanDesignHubError:
            if mode == "live":
                raise
            items = self._fixture_locations(q)
            self._location_cache[cache_key] = items
            return items

    def _fixture_locations(self, query: str) -> list[dict[str, Any]]:
        catalog = [
            {
                "id": "nn",
                "name": "Нижний Новгород",
                "region": "Нижегородская область",
                "country": "Россия",
                "timezone": "Europe/Moscow",
                "latitude": 56.3269,
                "longitude": 44.0059,
            },
            {
                "id": "msk",
                "name": "Москва",
                "region": "Москва",
                "country": "Россия",
                "timezone": "Europe/Moscow",
                "latitude": 55.75204,
                "longitude": 37.61781,
            },
            {
                "id": "spb",
                "name": "Санкт-Петербург",
                "region": "Санкт-Петербург",
                "country": "Россия",
                "timezone": "Europe/Moscow",
                "latitude": 59.9386,
                "longitude": 30.3141,
            },
            {
                "id": "ekb",
                "name": "Екатеринбург",
                "region": "Свердловская область",
                "country": "Россия",
                "timezone": "Asia/Yekaterinburg",
                "latitude": 56.8389,
                "longitude": 60.6057,
            },
        ]
        q = query.lower()
        return [c for c in catalog if q in c["name"].lower() or q in c["country"].lower()]

    async def calculate(self, telegram_user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        birth = self.validate_birth_payload(payload)
        mode_used = "live"
        chart_raw: dict[str, Any] | None = None
        image_png: bytes | None = None

        if self.settings.demo_mode == "fixture":
            mode_used = "fixture"
            chart_raw = load_fixture_chart(self.settings.fixtures_dir, birth["name"])
        else:
            try:
                tz = await self.hub.resolve_timezone(
                    birth["location"]["timezone"],
                    birth["birthDate"],
                    birth["birthTime"],
                )
                datetime_iso = tz.get("datetime")
                if not datetime_iso:
                    raise HumanDesignHubError("timezone_resolve", 500, "No datetime", "HDHUB_BAD_RESPONSE")
                chart_raw = await self.hub.calculate_bodygraph(datetime_iso)
                image_png = await self.hub.generate_bodygraph_image(datetime_iso)
            except HumanDesignHubError as exc:
                logger.error(
                    '"operation=calculate provider=human_design_hub status=%s code=%s"',
                    exc.status,
                    exc.code,
                )
                if self.settings.demo_mode == "live":
                    raise
                mode_used = "fixture"
                chart_raw = load_fixture_chart(self.settings.fixtures_dir, birth["name"])

        assert chart_raw is not None
        normalized = normalize_bodygraph(chart_raw)
        if image_png is None:
            image_png = generate_bodygraph_png(normalized, birth["name"])

        summary = await self._build_summary(birth["name"], normalized)
        session = self.sessions.create(
            telegram_user_id=telegram_user_id,
            birth_data=birth,
            normalized_bodygraph=normalized,
            summary=summary,
            image_png=image_png,
            demo_mode=mode_used,
        )
        return self._session_response(session)

    async def _build_summary(self, name: str, chart: dict[str, Any]) -> dict[str, str]:
        fragments = self.knowledge.fragments_for_chart(chart)
        system = (
            "Ты — интерпретатор Human Design по авторской методике самопознания. "
            "Отвечай только валидным JSON с полями title и text. "
            "title — одна эмоциональная фраза. text — 3–5 абзацев. "
            "Без медицины, предсказаний, финансовых советов и давления."
        )
        user = json.dumps(
            {
                "nameAlias": "пользователь",
                "chart": {k: v for k, v in chart.items() if k != "rawSource"},
                "knowledge": fragments[:12],
                "toneRules": self.knowledge.question_rules.get("toneRules", []),
            },
            ensure_ascii=False,
        )
        llm_result = await self.llm.generate_json(system, user)
        if llm_result and llm_result.get("title") and llm_result.get("text"):
            return {"title": str(llm_result["title"]), "text": str(llm_result["text"])}
        return build_summary_fallback(name, chart, self.knowledge)

    async def answer_question(
        self,
        session: DemoSession,
        category: str,
        question: str | None = None,
    ) -> dict[str, Any]:
        cache_key = f"{category}:{question or ''}"
        if cache_key in session.answers:
            return session.answers[cache_key]

        rules = self.knowledge.question_rules.get("categories", {})
        if category not in rules:
            raise ValueError("Неизвестная категория вопроса")
        if category == "custom" and not (question or "").strip():
            raise ValueError("Введите вопрос")
        if category == "custom" and len((question or "").strip()) > 400:
            raise ValueError("Вопрос слишком длинный")

        focus = rules[category].get("focus") or []
        fragments = self.knowledge.fragments_for_chart(session.normalized_bodygraph, focus)
        system = (
            "Ты — интерпретатор Human Design. Верни JSON со схемой: "
            "title, shortAnswer, manifestations[], strength, attentionPoint, "
            "reflectionQuestion, usedChartElements[]. "
            "Это самопознание, не предсказание. Пиши по-русски."
        )
        user = json.dumps(
            {
                "category": category,
                "question": question,
                "promptHint": rules[category].get("promptHint"),
                "chart": {k: v for k, v in session.normalized_bodygraph.items() if k != "rawSource"},
                "knowledge": fragments[:14],
                "toneRules": self.knowledge.question_rules.get("toneRules", []),
            },
            ensure_ascii=False,
        )
        llm_result = await self.llm.generate_json(system, user)
        validated = validate_llm_answer(llm_result) if llm_result else None
        if not validated:
            validated = build_question_fallback(
                category, session.normalized_bodygraph, self.knowledge, question
            )
        self.sessions.save_answer(session.session_id, cache_key, validated)
        return validated

    def _session_response(self, session: DemoSession) -> dict[str, Any]:
        return {
            "sessionId": session.session_id,
            "status": "completed",
            "demoMode": session.demo_mode,
            "bodygraph": session.normalized_bodygraph,
            "summary": session.summary,
            "imageUrl": f"/api/v1/demo-sessions/{session.session_id}/image",
            "birthData": session.birth_data,
            "expiresAt": session.expires_at,
        }
