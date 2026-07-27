from __future__ import annotations

from typing import Any


def normalize_bodygraph(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert Human Design Hub response into internal DTO v1."""

    def pick(*keys: str, default=None):
        for key in keys:
            if key in raw and raw[key] is not None:
                return raw[key]
        return default

    channels = pick("channels_short", "channels", default=[]) or []
    if channels and isinstance(channels[0], dict):
        channels = [c.get("name") or c.get("id") or str(c) for c in channels]

    centers = pick("centers", default=[]) or []
    if centers and isinstance(centers[0], dict):
        centers = [c.get("name") or c.get("id") or str(c) for c in centers]

    gates = pick("gates", default=[]) or []
    if gates and isinstance(gates[0], dict):
        gates = [str(g.get("id") or g.get("gate") or g) for g in gates]
    else:
        gates = [str(g) for g in gates]

    activations = pick("activations", "gate_activations", default=[]) or []
    activations = [str(a) for a in activations]

    cognition = pick("cognition")
    if isinstance(cognition, dict):
        cognition = cognition.get("name") or cognition.get("label")
    determination = pick("determination")
    if isinstance(determination, dict):
        determination = determination.get("label") or determination.get("name")
    variables = pick("variables")
    if isinstance(variables, dict):
        variables = variables.get("label") or variables.get("name")
    motivation = pick("motivation")
    if isinstance(motivation, dict):
        motivation = motivation.get("label") or motivation.get("name")
    transference = pick("transference")
    if isinstance(transference, dict):
        transference = transference.get("label") or transference.get("name")
    perspective = pick("perspective")
    if isinstance(perspective, dict):
        perspective = perspective.get("label") or perspective.get("name")
    distraction = pick("distraction")
    if isinstance(distraction, dict):
        distraction = distraction.get("label") or distraction.get("name")
    environment = pick("environment")
    if isinstance(environment, dict):
        environment = environment.get("label") or environment.get("name")

    return {
        "type": pick("type"),
        "strategy": pick("strategy"),
        "authority": pick("authority"),
        "profile": pick("profile"),
        "definition": pick("definition"),
        "signature": pick("signature"),
        "notSelfTheme": pick("not_self_theme", "notSelfTheme"),
        "incarnationCross": pick("incarnation_cross", "incarnationCross"),
        "cognition": cognition,
        "determination": determination,
        "variables": variables,
        "motivation": motivation,
        "transference": transference,
        "perspective": perspective,
        "distraction": distraction,
        "environment": environment,
        "centers": centers,
        "channels": channels,
        "gates": gates,
        "activations": activations,
        "rawSource": "human_design_hub",
    }
