from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class KnowledgePackage:
    gates: dict[str, Any]
    types: dict[str, Any]
    authorities: dict[str, Any]
    profiles: dict[str, Any]
    definitions: dict[str, Any]
    centers: dict[str, Any]
    channels: dict[str, Any]
    question_rules: dict[str, Any]

    @classmethod
    def load(cls, directory: Path) -> "KnowledgePackage":
        def load_json(name: str) -> dict[str, Any]:
            path = directory / name
            if not path.exists():
                return {}
            return json.loads(path.read_text(encoding="utf-8"))

        return cls(
            gates=load_json("gates.json"),
            types=load_json("types.json"),
            authorities=load_json("authorities.json"),
            profiles=load_json("profiles.json"),
            definitions=load_json("definitions.json"),
            centers=load_json("centers.json"),
            channels=load_json("channels.json"),
            question_rules=load_json("question-rules.json"),
        )

    def fragments_for_chart(self, chart: dict[str, Any], focus: list[str] | None = None) -> list[dict[str, Any]]:
        focus = focus or ["type", "authority", "profile", "gates", "channels"]
        fragments: list[dict[str, Any]] = []

        if "type" in focus and chart.get("type"):
            t = self.types.get(chart["type"])
            if t:
                fragments.append({"kind": "type", "key": chart["type"], **t})

        if "authority" in focus and chart.get("authority"):
            a = self.authorities.get(chart["authority"])
            if a:
                fragments.append({"kind": "authority", "key": chart["authority"], **a})

        if "profile" in focus and chart.get("profile"):
            p = self.profiles.get(chart["profile"])
            if p:
                fragments.append({"kind": "profile", "key": chart["profile"], **p})

        if "definition" in focus and chart.get("definition"):
            d = self.definitions.get(chart["definition"])
            if d:
                fragments.append({"kind": "definition", "key": chart["definition"], **d})

        if "centers" in focus:
            for center in chart.get("centers") or []:
                c = self.centers.get(center)
                if c:
                    fragments.append({"kind": "center", "key": center, **c})

        if "gates" in focus:
            for activation in (chart.get("activations") or [])[:8]:
                gate_no, _, line = str(activation).partition(".")
                gate = self.gates.get(str(int(gate_no)) if gate_no.isdigit() else gate_no)
                if not gate:
                    continue
                line_data = (gate.get("lines") or {}).get(str(line)) if line else None
                fragments.append(
                    {
                        "kind": "gate",
                        "gate": gate.get("gate"),
                        "title": gate.get("title"),
                        "theme": gate.get("theme"),
                        "talent": gate.get("talent"),
                        "possibleRealization": gate.get("possibleRealization"),
                        "line": line,
                        "lineTitle": (line_data or {}).get("title"),
                        "lineDescription": (line_data or {}).get("description"),
                        "source": gate.get("source"),
                        "usageStatus": gate.get("usageStatus"),
                        "authorApproved": gate.get("authorApproved"),
                        "version": gate.get("version"),
                    }
                )

        if "channels" in focus:
            for ch in (chart.get("channels") or [])[:6]:
                key = str(ch).replace("–", "-").replace("—", "-")
                meta = self.channels.get(key) or {}
                fragments.append(
                    {
                        "kind": "channel",
                        "key": key,
                        "title": meta.get("title") or f"Канал {key}",
                        "theme": meta.get("theme"),
                        "source": meta.get("source"),
                        "usageStatus": meta.get("usageStatus"),
                        "authorApproved": meta.get("authorApproved"),
                        "version": meta.get("version"),
                    }
                )

        return fragments
