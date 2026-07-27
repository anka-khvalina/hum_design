from __future__ import annotations

from typing import Any

from app.knowledge.loader import KnowledgePackage


SUMMARY_TITLES = {
    "Generator": "Твоя сила раскрывается через отклик",
    "Manifesting Generator": "Твоя сила в быстром отклике и верном темпе",
    "Projector": "Твоя сила в признании и мудром направлении",
    "Manifestor": "Твоя сила в инициации через информирование",
    "Reflector": "Твоя сила в отражении пространства вокруг",
}


def build_summary_fallback(name: str, chart: dict[str, Any], knowledge: KnowledgePackage) -> dict[str, str]:
    t = chart.get("type") or ""
    type_info = knowledge.types.get(t, {})
    auth = chart.get("authority") or ""
    auth_info = knowledge.authorities.get(auth, {})
    profile = chart.get("profile") or ""
    profile_info = knowledge.profiles.get(profile, {})
    definition = chart.get("definition") or ""
    def_info = knowledge.definitions.get(definition, {})

    title = SUMMARY_TITLES.get(t, "Твоя карта — зеркало природных качеств")

    paragraphs = [
        f"{name}, в твоей карте звучит тип «{type_info.get('ru', t)}». {type_info.get('theme', '')}",
        f"Стратегия «{chart.get('strategy') or '—'}» и авторитет «{auth_info.get('ru', auth)}» "
        f"подсказывают естественный способ принимать решения. {auth_info.get('explanation', '')}",
        f"Профиль {profile_info.get('ru', profile)}: {profile_info.get('theme', '')} "
        f"{profile_info.get('talent', '')}",
    ]
    if definition:
        paragraphs.append(f"Определенность: {def_info.get('ru', definition)}. {def_info.get('explanation', '')}")
    if chart.get("incarnationCross"):
        paragraphs.append(
            f"Дело жизни в карте обозначено как «{chart['incarnationCross']}» — "
            "это направление для наблюдения, а не жёсткий сценарий."
        )
    paragraphs.append(
        "Карта не диктует, кем тебе быть. Она помогает замечать, где ты в потоке, "
        "а где пытаешься жить чужим ритмом."
    )

    return {"title": title, "text": "\n\n".join(p.strip() for p in paragraphs if p.strip())}


def build_question_fallback(
    category: str,
    chart: dict[str, Any],
    knowledge: KnowledgePackage,
    question: str | None = None,
) -> dict[str, Any]:
    rules = knowledge.question_rules.get("categories", {}).get(category, {})
    title = rules.get("title") or "Ответ по твоей карте"
    type_info = knowledge.types.get(chart.get("type") or "", {})
    profile_info = knowledge.profiles.get(chart.get("profile") or "", {})
    auth_info = knowledge.authorities.get(chart.get("authority") or "", {})

    used = []
    if chart.get("profile"):
        used.append(f"Профиль {chart['profile']}")
    if chart.get("authority"):
        used.append(f"{auth_info.get('ru', chart['authority'])} авторитет")
    for ch in (chart.get("channels") or [])[:2]:
        used.append(f"Канал {ch}")
    for act in (chart.get("activations") or [])[:2]:
        used.append(f"Ворота {act}")

    short = {
        "talents": f"Твои природные таланты связаны с типом «{type_info.get('ru', chart.get('type'))}» и профилем {chart.get('profile')}. {type_info.get('talent', '')}",
        "direction": f"Направление проявляется через стратегию «{chart.get('strategy')}» и дело жизни «{chart.get('incarnationCross') or 'наблюдение за резонансом'}».",
        "work": f"В работе тебе важны условия, где стратегия и авторитет соблюдены. {type_info.get('theme', '')}",
        "character": f"Характер и общение окрашены профилем {profile_info.get('ru', chart.get('profile'))}. {profile_info.get('theme', '')}",
        "money": "Отношение к ресурсам связано с тем, как ты обмениваешься ценностью в правильном для себя ритме — без гонки и давления.",
        "relationships": f"В отношениях опора — твой авторитет ({auth_info.get('ru', chart.get('authority'))}). {auth_info.get('explanation', '')}",
        "energy": f"Ритм энергии задаёт тип «{type_info.get('ru', chart.get('type'))}». Восстановление начинается с уважения к стратегии.",
        "custom": f"По вопросу «{question or '…'}»: смотри на ситуацию через стратегию «{chart.get('strategy')}» и авторитет «{auth_info.get('ru', chart.get('authority'))}».",
    }.get(category, "Карта подсказывает качества для наблюдения, а не готовый сценарий.")

    manifestations = [
        "Ты легче входишь в поток, когда действуешь из отклика/приглашения/информации — в зависимости от типа.",
        "Окружающие могут замечать твои сильные стороны раньше, чем ты сам(а).",
        "Сопротивление часто появляется там, где ты игнорируешь свой авторитет.",
    ]
    strength = type_info.get("talent") or profile_info.get("talent") or "Умение быть собой в правильном ритме."
    attention = (
        f"Тема ложного «Я» в карте — «{chart.get('notSelfTheme') or 'напряжение'}». "
        "Это сигнал для наблюдения, а не приговор."
    )
    reflection = {
        "talents": "Где в последнее время ты чувствовал(а) естественную лёгкость, а где — усилие «надо»?",
        "direction": "Какое направление откликается телом/эмоцией, даже если ум ещё спорит?",
        "work": "В каких рабочих задачах у тебя появляется устойчивая энергия, а не только дедлайн?",
        "character": "В каких разговорах ты звучишь как «настоящий(ая) я»?",
        "custom": "Что в этом вопросе уже подсказывает тебе тело или эмоциональная ясность?",
    }.get(category, "Что в тебе уже знает ответ — ещё до того, как ум всё объяснил?")

    return {
        "title": title,
        "shortAnswer": short.strip(),
        "manifestations": manifestations,
        "strength": strength,
        "attentionPoint": attention,
        "reflectionQuestion": reflection,
        "usedChartElements": used,
        "answer": short.strip(),
        "basedOn": used,
    }


def validate_llm_answer(data: dict[str, Any]) -> dict[str, Any] | None:
    required = ["title", "shortAnswer", "manifestations", "strength", "attentionPoint", "reflectionQuestion", "usedChartElements"]
    if not all(k in data for k in required):
        return None
    if not isinstance(data["manifestations"], list) or not data["manifestations"]:
        return None
    return {
        "title": str(data["title"]),
        "shortAnswer": str(data["shortAnswer"]),
        "manifestations": [str(x) for x in data["manifestations"][:5]],
        "strength": str(data["strength"]),
        "attentionPoint": str(data["attentionPoint"]),
        "reflectionQuestion": str(data["reflectionQuestion"]),
        "usedChartElements": [str(x) for x in data["usedChartElements"][:8]],
        "answer": str(data["shortAnswer"]),
        "basedOn": [str(x) for x in data["usedChartElements"][:8]],
    }
