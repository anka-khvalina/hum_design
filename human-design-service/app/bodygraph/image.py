from __future__ import annotations

import io
import math
from typing import Any

from PIL import Image, ImageDraw, ImageFont


# Approximate center positions for a stylized bodygraph
CENTER_COORDS = {
    "Head": (400, 70),
    "Ajna": (400, 160),
    "Throat": (400, 260),
    "G": (400, 390),
    "Heart": (300, 390),
    "Ego": (300, 390),
    "Sacral": (400, 540),
    "Solar Plexus": (520, 480),
    "Spleen": (280, 480),
    "Root": (400, 680),
}

CENTER_SHAPES = {
    "Head": "triangle_up",
    "Ajna": "triangle_down",
    "Throat": "square",
    "G": "diamond",
    "Heart": "triangle_up",
    "Ego": "triangle_up",
    "Sacral": "square",
    "Solar Plexus": "triangle_down",
    "Spleen": "triangle_up",
    "Root": "square",
}


def _draw_shape(draw: ImageDraw.ImageDraw, shape: str, xy: tuple[int, int], size: int, fill, outline):
    x, y = xy
    s = size
    if shape == "square":
        draw.rounded_rectangle([x - s, y - s, x + s, y + s], radius=8, fill=fill, outline=outline, width=2)
    elif shape == "diamond":
        pts = [(x, y - s), (x + s, y), (x, y + s), (x - s, y)]
        draw.polygon(pts, fill=fill, outline=outline)
    elif shape == "triangle_up":
        pts = [(x, y - s), (x + s, y + s), (x - s, y + s)]
        draw.polygon(pts, fill=fill, outline=outline)
    else:
        pts = [(x - s, y - s), (x + s, y - s), (x, y + s)]
        draw.polygon(pts, fill=fill, outline=outline)


def generate_bodygraph_png(chart: dict[str, Any], name: str = "") -> bytes:
    """Generate a premium-looking bodygraph PNG when Hub image API is unavailable."""
    width, height = 800, 1000
    img = Image.new("RGB", (width, height), "#0B0618")
    draw = ImageDraw.Draw(img)

    # Atmosphere gradients via concentric ellipses
    for i in range(18, 0, -1):
        alpha_shade = 12 + i * 2
        color = (18 + alpha_shade, 10 + i, 40 + i * 3)
        pad = i * 18
        draw.ellipse([pad, pad + 40, width - pad, height - pad - 20], outline=color, width=2)

    defined = set(chart.get("centers") or [])
    # Normalize ego/heart
    if "Ego" in defined:
        defined.add("Heart")
    if "Heart" in defined:
        defined.add("Ego")

    # Draw channels as soft lines between related centers (heuristic by channel ids)
    channel_center_map = {
        "1-8": ("G", "Throat"),
        "2-14": ("G", "Sacral"),
        "3-60": ("Sacral", "Root"),
        "5-15": ("Sacral", "G"),
        "6-59": ("Solar Plexus", "Sacral"),
        "7-31": ("G", "Throat"),
        "9-52": ("Sacral", "Root"),
        "10-20": ("G", "Throat"),
        "10-34": ("G", "Sacral"),
        "10-57": ("G", "Spleen"),
        "11-56": ("Ajna", "Throat"),
        "12-22": ("Throat", "Solar Plexus"),
        "13-33": ("G", "Throat"),
        "16-48": ("Throat", "Spleen"),
        "17-62": ("Ajna", "Throat"),
        "18-58": ("Spleen", "Root"),
        "19-49": ("Root", "Solar Plexus"),
        "20-34": ("Throat", "Sacral"),
        "20-57": ("Throat", "Spleen"),
        "21-45": ("Heart", "Throat"),
        "23-43": ("Throat", "Ajna"),
        "24-61": ("Ajna", "Head"),
        "25-51": ("G", "Heart"),
        "26-44": ("Heart", "Spleen"),
        "27-50": ("Sacral", "Spleen"),
        "28-38": ("Spleen", "Root"),
        "29-46": ("Sacral", "G"),
        "30-41": ("Solar Plexus", "Root"),
        "32-54": ("Spleen", "Root"),
        "34-57": ("Sacral", "Spleen"),
        "35-36": ("Throat", "Solar Plexus"),
        "37-40": ("Solar Plexus", "Heart"),
        "39-55": ("Root", "Solar Plexus"),
        "42-53": ("Sacral", "Root"),
        "47-64": ("Ajna", "Head"),
        "63-4": ("Head", "Ajna"),
    }

    for ch in chart.get("channels") or []:
        key = str(ch).replace("–", "-").replace("—", "-")
        pair = channel_center_map.get(key)
        if not pair:
            # try reversed
            parts = key.split("-")
            if len(parts) == 2:
                pair = channel_center_map.get(f"{parts[1]}-{parts[0]}")
        if not pair:
            continue
        a, b = pair
        if a not in CENTER_COORDS or b not in CENTER_COORDS:
            continue
        draw.line([CENTER_COORDS[a], CENTER_COORDS[b]], fill="#C9A24A", width=5)

    for center, xy in CENTER_COORDS.items():
        if center == "Heart" and "Ego" in CENTER_COORDS:
            # drawn as Ego
            if center == "Heart":
                pass
        shape = CENTER_SHAPES.get(center, "square")
        is_defined = center in defined
        fill = "#8B5CF6" if is_defined else "#1A1228"
        outline = "#F5D78E" if is_defined else "#4A3A66"
        _draw_shape(draw, shape, xy, 36 if center != "G" else 40, fill, outline)

    try:
        font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    except Exception:
        font_lg = ImageFont.load_default()
        font_md = font_lg
        font_sm = font_lg

    title = name or "BodyGraph"
    draw.text((40, 30), title, fill="#F8F1E3", font=font_lg)
    meta = f"{chart.get('type') or '—'} · {chart.get('profile') or '—'} · {chart.get('authority') or '—'}"
    draw.text((40, 70), meta, fill="#C9A24A", font=font_md)

    # Active gates ribbon
    gates = [str(g) for g in (chart.get("gates") or [])[:18]]
    if gates:
        draw.text((40, 920), "Ворота: " + ", ".join(gates), fill="#B8A9D9", font=font_sm)

    draw.text((40, 960), "Human Design: предназначение", fill="#6E5A8F", font=font_sm)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
