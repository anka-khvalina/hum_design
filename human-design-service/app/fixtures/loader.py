from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_fixture_chart(fixtures_dir: Path, name: str = "") -> dict[str, Any]:
    # Prefer anna fixture for female-looking names, else male; always have fallback
    anna = fixtures_dir / "anna-bodygraph.json"
    male = fixtures_dir / "male-bodygraph.json"
    choice = anna if anna.exists() else male
    lowered = (name or "").lower()
    male_markers = ("алекс", "иван", "дмитр", "серг", "андрей", "макс", "павел", "никит", "roman", "alex")
    if any(m in lowered for m in male_markers) and male.exists():
        choice = male
    return json.loads(choice.read_text(encoding="utf-8"))
