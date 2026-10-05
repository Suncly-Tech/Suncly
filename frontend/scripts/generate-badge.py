"""Generate the Suncly Certified badge as vector and raster files.

Circular, the words "suncly certified" on a circular path converted to outlines (so the
badge needs no font), the badge's circular sun mark (design/badge/mark.svg) untouched at the centre, a fine
ring, and one notch at the brand angle (18.4 degrees from vertical, from the two cuts in
the mark). Three versions: paper, dusk and mono. No laurels, shields, stars, ribbons,
ticks, medal colours or tiers; nothing that resembles the CE mark or a regulator's seal.

Usage, from frontend/:  python scripts/generate-badge.py
Needs fontTools (pip install fonttools) and the draft Figtree TTF in
design/directions/fonts/ (SIL OFL 1.1).
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "design/directions/fonts/Figtree[wght].ttf"
MARK = ROOT / "design/badge/mark.svg"  # the badge's own circular mark, kept apart from the brand mark
OUT = ROOT / "public/brand/badge"

SIZE = 512.0
CENTRE = SIZE / 2
RING_OUTER = 244.0  # fine outer ring
TEXT_RADIUS = 206.0  # baseline circle of the lettering
RING_INNER = 162.0  # fine inner ring
MARK_RADIUS = 112.0  # the mark's circle (r=44 of 120 in design/badge/mark.svg) scaled to this radius
ANGLE = 18.4  # brand angle, degrees from vertical
TEXT = "suncly certified"
FONT_SIZE = 40.0
LETTER_SPACING = 0.16  # em
WEIGHT = 500

PALETTES = {
    "paper": {"ink": "#1B1814", "sun": "#F2C14E", "bg": None},
    "dusk": {"ink": "#FAF7F0", "sun": "#F2C14E", "bg": "#17130F"},
    "mono": {"ink": "#1B1814", "sun": "#1B1814", "bg": None},
}


def glyph_paths(font: TTFont, text: str, size: float) -> list[tuple[str, float]]:
    """Each glyph as (svg path at `size` px with y down, advance in px)."""
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    upem = font["head"].unitsPerEm
    scale = size / upem
    out = []
    for ch in text:
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyph_set)
        # flip y, scale to px
        tpen = TransformPen(pen, (scale, 0, 0, -scale, 0, 0))
        glyph_set[name].draw(tpen)
        out.append((pen.getCommands(), glyph_set[name].width * scale))
    return out


def text_on_circle(
    font: TTFont, text: str, radius: float, start_deg: float, size: float, spacing_em: float
) -> str:
    """Place glyph outlines along a circle, reading clockwise from `start_deg` (0 = top)."""
    glyphs = glyph_paths(font, text, size)
    spacing = spacing_em * size
    advances = [adv + spacing for _, adv in glyphs]
    total = sum(advances) - spacing
    # arc length -> angle
    start = math.radians(start_deg) - (total / radius) / 2
    paths = []
    pos = start
    for (d, adv), step in zip(glyphs, advances, strict=True):
        if d:
            centre_angle = pos + (adv / radius) / 2
            deg = math.degrees(centre_angle)
            x = CENTRE + radius * math.sin(centre_angle)
            y = CENTRE - radius * math.cos(centre_angle)
            # glyph origin at its advance centre; baseline tangent to the circle
            transform = f"translate({x:.2f} {y:.2f}) rotate({deg:.2f}) translate({-adv / 2:.2f} 0)"
            paths.append(f'<path transform="{transform}" d="{d}"/>')
        pos += step / radius
    return "\n".join(paths)


def mark_svg() -> str:
    """The badge's sun mark exactly as drawn in design/badge/mark.svg, scaled so its circle has MARK_RADIUS."""
    src = MARK.read_text()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", src, re.S).group(1).strip()
    scale = MARK_RADIUS / 44.0
    offset = CENTRE - 60 * scale
    return f'<g transform="translate({offset:.3f} {offset:.3f}) scale({scale:.5f})">{inner}</g>'


def badge(palette: dict[str, str | None], font: TTFont) -> str:
    ink = palette["ink"]
    sun = palette["sun"]
    bg = palette["bg"]
    bg_rect = ""
    if bg:
        bg_rect = f'<circle cx="{CENTRE}" cy="{CENTRE}" r="{SIZE / 2}" fill="{bg}"/>'
    mark = mark_svg()
    if sun != "#F2C14E":
        mark = mark.replace("#F2C14E", sun)
    # unique mask ids per file are not needed: one badge per file
    lettering = text_on_circle(font, TEXT, TEXT_RADIUS, 0.0, FONT_SIZE, LETTER_SPACING)
    # the notch: a short radial stroke at the brand angle, through the outer ring
    a = math.radians(ANGLE)
    x1, y1 = CENTRE + (RING_OUTER - 10) * math.sin(a), CENTRE - (RING_OUTER - 10) * math.cos(a)
    x2, y2 = CENTRE + (RING_OUTER + 10) * math.sin(a), CENTRE - (RING_OUTER + 10) * math.cos(a)
    view_box = f"0 0 {SIZE:.0f} {SIZE:.0f}"
    xmlns = "http://www.w3.org/2000/svg"
    head = f'<svg xmlns="{xmlns}" viewBox="{view_box}" role="img" aria-labelledby="t d">'
    return f"""{head}
<title id="t">Suncly Certified badge</title>
<desc id="d">A circular badge: the words suncly certified around the Suncly sun mark,
with a fine ring and one notch at the brand angle.</desc>
{bg_rect}
<circle cx="{CENTRE}" cy="{CENTRE}" r="{RING_OUTER}" fill="none" stroke="{ink}" stroke-width="2"/>
<circle cx="{CENTRE}" cy="{CENTRE}" r="{RING_INNER}" fill="none" stroke="{ink}" stroke-width="1.5"/>
<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{ink}" stroke-width="2"/>
<g fill="{ink}">
{lettering}
</g>
{mark}
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    var = TTFont(FONT)
    font = instantiateVariableFont(var, {"wght": WEIGHT})
    for name, palette in PALETTES.items():
        (OUT / f"suncly-certified-{name}.svg").write_text(badge(palette, font))
        sys.stdout.write(f"wrote {OUT / f'suncly-certified-{name}.svg'}\n")


if __name__ == "__main__":
    main()
