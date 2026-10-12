"""Generate the brand images in custom_components/solax_adapter_box_g2/brand/ (spec.md 9).

Motif: sun -> adapter box with four contacts (two active) -> water heater.
An original design; it must not use the SolaX logo or other vendor marks.

Usage (needs Pillow and the Noto Sans font, e.g. from the test venv):

    .venv/bin/python tools/brand_images.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "custom_components" / "solax_adapter_box_g2" / "brand"
FONT_BOLD = "/usr/share/fonts/google-noto/NotoSans-Bold.ttf"
FONT_MEDIUM = "/usr/share/fonts/google-noto/NotoSans-Medium.ttf"
SUPERSAMPLING = 4

ORANGE = (245, 130, 32)
TITLE = "Adapter Box G2"
SUBTITLE = "for Home Assistant"


def palette(dark: bool) -> dict[str, tuple[int, int, int]]:
    """Colors for light or dark backgrounds."""
    return {
        "box": (52, 60, 72) if dark else (236, 239, 243),
        "outline": (150, 160, 175) if dark else (120, 130, 145),
        "off": (95, 105, 120) if dark else (190, 196, 205),
        "text": (240, 242, 245) if dark else (27, 38, 59),
        "sub": (170, 178, 190) if dark else (110, 118, 130),
    }


def draw_sun(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float) -> None:
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ORANGE)
    for i in range(8):
        a = i * math.pi / 4
        d.line(
            [cx + math.cos(a) * r * 1.35, cy + math.sin(a) * r * 1.35,
             cx + math.cos(a) * r * 1.75, cy + math.sin(a) * r * 1.75],
            fill=ORANGE,
            width=max(1, int(r * 0.22)),
        )


def draw_heater(d: ImageDraw.ImageDraw, box: tuple[float, float, float, float],
                p: dict, u: float) -> None:
    """Water heater: rounded tank with a flame."""
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=(x1 - x0) * 0.35, fill=p["box"], outline=p["outline"], width=int(6 * u))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + 8 * u
    r = (x1 - x0) * 0.22
    d.polygon([(cx, cy - r * 2.0), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=ORANGE)
    d.ellipse([cx - r, cy - r * 0.2, cx + r, cy + r * 1.1], fill=ORANGE)


def draw_mark(d: ImageDraw.ImageDraw, x: float, y: float, size: float, dark: bool) -> None:
    """The symbol in a size x size square: sun -> adapter box -> water heater."""
    p = palette(dark)
    u = size / 256
    draw_sun(d, x + 34 * u, y + 128 * u, 20 * u)
    d.line([x + 70 * u, y + 128 * u, x + 88 * u, y + 128 * u], fill=p["outline"], width=int(9 * u))
    d.rounded_rectangle([x + 86 * u, y + 76 * u, x + 172 * u, y + 180 * u], radius=18 * u,
                        fill=p["box"], outline=p["outline"], width=int(7 * u))
    for i, on in enumerate([True, True, False, False]):
        cx = x + (108 + (i % 2) * 42) * u
        cy = y + (106 + (i // 2) * 44) * u
        r = 13 * u
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ORANGE if on else p["off"])
    d.line([x + 170 * u, y + 128 * u, x + 190 * u, y + 128 * u], fill=p["outline"], width=int(9 * u))
    draw_heater(d, (x + 188 * u, y + 68 * u, x + 250 * u, y + 188 * u), p, u)


def render_icon(size: int, dark: bool) -> Image.Image:
    big = size * SUPERSAMPLING
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw_mark(ImageDraw.Draw(image), 0, 0, big, dark)
    return image.resize((size, size), Image.LANCZOS)


def render_logo(height: int, dark: bool) -> Image.Image:
    p = palette(dark)
    h = height * SUPERSAMPLING
    title = ImageFont.truetype(FONT_BOLD, int(h * 0.30))
    subtitle = ImageFont.truetype(FONT_MEDIUM, int(h * 0.15))
    text_width = max(title.getlength(TITLE), subtitle.getlength(SUBTITLE))
    width = int(h + h * 0.10 + text_width + h * 0.06)
    image = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    draw_mark(d, 0, 0, h, dark)
    tx = h + h * 0.10
    d.text((tx, h * 0.20), TITLE, font=title, fill=p["text"])
    d.text((tx, h * 0.58), SUBTITLE, font=subtitle, fill=p["sub"])
    return image.resize((width // SUPERSAMPLING, height), Image.LANCZOS)


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    for dark in (False, True):
        prefix = "dark_" if dark else ""
        render_icon(256, dark).save(BRAND / f"{prefix}icon.png")
        render_icon(512, dark).save(BRAND / f"{prefix}icon@2x.png")
        render_logo(128, dark).save(BRAND / f"{prefix}logo.png")
        render_logo(256, dark).save(BRAND / f"{prefix}logo@2x.png")
    print(f"Brand images written to {BRAND}")


if __name__ == "__main__":
    main()
