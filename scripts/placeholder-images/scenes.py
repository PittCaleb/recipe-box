"""Flat illustrated placeholder pictures for recipes, all on the same wooden
table. These drew the 59 placeholders added on 2026-10-28; scenes2.py holds most
of the recipes, and 16.svg (Chocolate Chess Pie) was drawn by hand.

    python scripts/placeholder-images/scenes2.py OUT_DIR [RECIPE_ID ...]
    python scripts/placeholder-images/sheet.py OUT_DIR data/recipes.db SHEET.png RECIPE_ID ...

Writes OUT_DIR/<id>.svg, <id>.png (1600x1200) and <id>-thumb.png (400x300).
Needs rsvg-convert (brew install librsvg). Each scene is keyed by recipe id.
"""
import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image

W, H = 1600, 1200
WOOD, GRAIN, SHADOW = "#8c5a3c", "#7a4c31", "#6e4329"
PLATE, PLATE_IN = "#f6f1ea", "#e9e1d6"
SCENES = {}


def scene(rid):
    def wrap(fn):
        SCENES[rid] = fn
        return fn
    return wrap


# ---- shared pieces -------------------------------------------------------

def table():
    grain = "".join(
        f'<path d="M0 {y} C 450 {y - 20 + 15 * (i % 2)}, 1000 {y + 25}, 1600 {y - 5}"/>'
        for i, y in enumerate((140, 330, 560, 800, 1010)))
    return (f'<rect width="{W}" height="{H}" fill="{WOOD}"/>'
            f'<g stroke="{GRAIN}" stroke-width="5" fill="none" stroke-linecap="round">{grain}</g>')


def shadow(cx, cy, rx, ry, dx=20, dy=30):
    return f'<ellipse cx="{cx + dx}" cy="{cy + dy}" rx="{rx}" ry="{ry}" fill="{SHADOW}"/>'


def plate(cx, cy, rx, ry, inner=0.8):
    return (shadow(cx, cy, rx, ry)
            + f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{PLATE}"/>'
            + f'<ellipse cx="{cx}" cy="{cy}" rx="{rx * inner}" ry="{ry * inner}" fill="{PLATE_IN}"/>')


def board(x, y, w, h, fill="#c69060", line="#b57f50"):
    lines = "".join(f'<path d="M{x + 30} {y + h * f} C {x + w * 0.4} {y + h * f - 12}, {x + w * 0.7} {y + h * f + 12}, {x + w - 30} {y + h * f}"/>'
                    for f in (0.25, 0.5, 0.75))
    return (f'<rect x="{x + 22}" y="{y + 30}" width="{w}" height="{h}" rx="40" fill="{SHADOW}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="40" fill="{fill}"/>'
            f'<g stroke="{line}" stroke-width="5" fill="none" stroke-linecap="round">{lines}</g>')


def napkin(x, y, w, h, angle=-8, color="#fbf6ee", stripe="#5b7fa6"):
    stripes = "".join(f'<rect x="{x}" y="{y + h * f}" width="{w}" height="10" fill="{stripe}"/>' for f in (0.15, 0.22, 0.78, 0.85))
    return (f'<g transform="rotate({angle} {x + w / 2} {y + h / 2})">'
            f'<rect x="{x + 14}" y="{y + 20}" width="{w}" height="{h}" rx="8" fill="{SHADOW}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{color}"/>{stripes}</g>')


def cylinder(cx, top, bottom, rx, ry, side, top_fill, side_dark=None):
    """An upright round thing (cake, glass) seen from a little above."""
    out = (f'<path d="M{cx - rx} {top} L{cx - rx} {bottom} A{rx} {ry} 0 0 0 {cx + rx} {bottom} L{cx + rx} {top} Z" fill="{side}"/>')
    if side_dark:
        out += (f'<path d="M{cx + rx * 0.45} {top + ry * 0.9} L{cx + rx * 0.45} {bottom + ry * 0.9} '
                f'A{rx} {ry} 0 0 0 {cx + rx} {bottom} L{cx + rx} {top} Z" fill="{side_dark}" opacity="0.5"/>')
    return out + f'<ellipse cx="{cx}" cy="{top}" rx="{rx}" ry="{ry}" fill="{top_fill}"/>'


def dots(cx, cy, rx, ry, n, fill, r=5, seed=1, opacity=1):
    rng = random.Random(seed)
    out = []
    while len(out) < n:
        x, y = rng.uniform(-1, 1), rng.uniform(-1, 1)
        if x * x + y * y <= 1:
            out.append(f'<circle cx="{cx + x * rx:.0f}" cy="{cy + y * ry:.0f}" r="{r}"/>')
    return f'<g fill="{fill}" opacity="{opacity}">{"".join(out)}</g>'


def butter(x, y, s=1.0):
    return (f'<g transform="translate({x} {y}) scale({s})">'
            '<path d="M-60 -10 L0 -40 L60 -10 L0 20 Z" fill="#fff1b8"/>'
            '<path d="M-60 -10 L0 20 L0 40 L-60 10 Z" fill="#f2d980"/>'
            '<path d="M60 -10 L0 20 L0 40 L60 10 Z" fill="#e8cb6a"/></g>')


def svg(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{table()}{body}</svg>'


# ---- scenes ----------------------------------------------------------------

@scene(43)  # Beer Bread
def beer_bread():
    loaf = ('<path d="M260 820 L260 600 C260 430, 860 430, 860 600 L860 820 Z" fill="#b8732f"/>'
            '<path d="M290 600 C300 470, 820 470, 830 600 L830 640 C700 600, 420 600, 290 640 Z" fill="#d49450"/>'
            '<g stroke="#9a5a22" stroke-width="10" fill="none" stroke-linecap="round">'
            '<path d="M400 520 C 450 500, 520 500, 560 520"/><path d="M560 500 C 610 480, 680 480, 720 500"/></g>'
            '<rect x="260" y="790" width="600" height="30" fill="#9a5a22"/>')

    def slice_(x, y, a):
        return (f'<g transform="rotate({a} {x + 110} {y + 160})">'
                f'<path d="M{x + 12} {y + 330} L{x + 12} {y + 90} C{x + 12} {y - 20}, {x + 232} {y - 20}, {x + 232} {y + 90} L{x + 232} {y + 330} Z" fill="{SHADOW}"/>'
                f'<path d="M{x} {y + 320} L{x} {y + 80} C{x} {y - 30}, {x + 220} {y - 30}, {x + 220} {y + 80} L{x + 220} {y + 320} Z" fill="#f3dfb3" stroke="#b8732f" stroke-width="18"/>'
                + dots(x + 110, y + 170, 70, 110, 14, "#e2c78f", r=6, seed=x) + '</g>')

    bottle = ('<ellipse cx="1330" cy="905" rx="110" ry="30" fill="' + SHADOW + '"/>'
              '<path d="M1250 900 L1250 520 C1250 450, 1295 430, 1300 380 L1300 250 L1360 250 L1360 380 C1365 430, 1410 450, 1410 520 L1410 900 Z" fill="#7a3f0e"/>'
              '<rect x="1272" y="480" width="22" height="400" rx="11" fill="#a85f22"/>'
              '<rect x="1250" y="600" width="160" height="170" fill="#f3e6c4"/>'
              '<rect x="1250" y="640" width="160" height="30" fill="#b3362b"/>'
              '<rect x="1292" y="225" width="76" height="34" rx="6" fill="#c9a227"/>')
    return board(160, 360, 1000, 600) + loaf + slice_(880, 520, 8) + slice_(960, 560, 14) + bottle


@scene(39)  # Christiana Campbell's Tavern Spoon Bread
def spoon_bread():
    dish = (shadow(760, 610, 600, 360)
            + '<ellipse cx="180" cy="600" rx="90" ry="50" fill="#f4efe8"/><ellipse cx="1340" cy="600" rx="90" ry="50" fill="#f4efe8"/>'
            '<ellipse cx="760" cy="600" rx="560" ry="340" fill="#f4efe8"/>'
            '<ellipse cx="760" cy="590" rx="500" ry="295" fill="#ddd4c7"/>'
            '<ellipse cx="760" cy="600" rx="480" ry="280" fill="#e6b45a"/>')
    top = ('<g fill="#cf923c"><ellipse cx="560" cy="520" rx="120" ry="50"/><ellipse cx="760" cy="720" rx="150" ry="55"/>'
           '<ellipse cx="1010" cy="660" rx="90" ry="40"/><ellipse cx="460" cy="680" rx="70" ry="30"/></g>'
           '<g fill="#f0c977"><ellipse cx="680" cy="610" rx="90" ry="30"/><ellipse cx="880" cy="520" rx="70" ry="24"/></g>')
    scoop = ('<ellipse cx="980" cy="500" rx="150" ry="80" fill="#b67d2c"/>'
             '<ellipse cx="985" cy="510" rx="130" ry="65" fill="#f5d98f"/>')
    spoon = ('<path d="M1050 470 L1470 230" stroke="' + SHADOW + '" stroke-width="40" stroke-linecap="round" transform="translate(16 26)"/>'
             '<path d="M1050 470 L1470 230" stroke="#c7ccd1" stroke-width="40" stroke-linecap="round"/>'
             '<path d="M1060 455 L1460 228" stroke="#e8ebee" stroke-width="10" stroke-linecap="round"/>'
             '<ellipse cx="985" cy="505" rx="105" ry="62" fill="#c7ccd1"/><ellipse cx="985" cy="500" rx="85" ry="46" fill="#f2cf78"/>'
             '<ellipse cx="960" cy="490" rx="30" ry="12" fill="#f9e3a6"/>')
    return dish + top + scoop + spoon + butter(640, 560, 0.9)


@scene(31)  # Cornbread
def cornbread():
    cx, cy = 700, 600
    skillet = (shadow(cx, cy, 480, 340)
               + '<rect x="1120" y="555" width="380" height="80" rx="40" fill="' + SHADOW + '" transform="translate(16 26)"/>'
               '<rect x="1120" y="555" width="380" height="80" rx="40" fill="#2b2624"/>'
               '<circle cx="1450" cy="595" r="18" fill="' + WOOD + '"/>'
               f'<ellipse cx="{cx}" cy="{cy}" rx="480" ry="340" fill="#2b2624"/>'
               f'<ellipse cx="{cx}" cy="{cy - 8}" rx="440" ry="305" fill="#3d3633"/>'
               f'<ellipse cx="{cx}" cy="{cy}" rx="420" ry="290" fill="#d79b34"/>'
               f'<ellipse cx="{cx}" cy="{cy}" rx="390" ry="265" fill="#eab94a"/>')
    cuts = "".join(
        f'<line x1="{cx}" y1="{cy}" x2="{cx + 420 * math.cos(a):.0f}" y2="{cy + 290 * math.sin(a):.0f}"/>'
        for a in (math.radians(d) for d in range(0, 360, 45)))
    crumbs = dots(cx, cy, 340, 220, 40, "#d9a13a", r=7, seed=3)
    side = plate(1260, 960, 260, 140)
    wedge = ('<path d="M1100 980 L1400 900 C1430 960, 1410 1010, 1380 1030 Z" fill="#c98a2a"/>'
             '<path d="M1100 960 L1400 880 C1430 940, 1410 990, 1380 1010 Z" fill="#eab94a"/>')
    return (skillet + f'<g stroke="#c4892a" stroke-width="7">{cuts}</g>' + crumbs
            + butter(cx, cy - 10) + side + wedge + butter(1300, 940, 0.55))


@scene(30)  # Passover Rolls
def passover_rolls():
    basket = (shadow(780, 640, 580, 360)
              + '<ellipse cx="780" cy="640" rx="580" ry="360" fill="#b9874b"/>'
              + "".join(f'<ellipse cx="780" cy="640" rx="{580 - i * 14}" ry="{360 - i * 9}" fill="none" stroke="#a07038" stroke-width="4"/>' for i in range(1, 5))
              + '<ellipse cx="780" cy="630" rx="500" ry="300" fill="#8d5f2f"/>')
    cloth = ('<path d="M330 560 L420 330 L780 360 L1150 320 L1240 560 L1180 860 L780 900 L380 860 Z" fill="#fbf6ee"/>'
             '<g stroke="#5b7fa6" stroke-width="12" fill="none"><path d="M400 400 L1170 380"/><path d="M380 430 L1190 410"/>'
             '<path d="M390 820 L1180 830"/></g>')

    def roll(x, y, s=1.0):
        return (f'<g transform="translate({x} {y}) scale({s})">'
                '<ellipse cx="10" cy="20" rx="150" ry="105" fill="#7a4c31" opacity="0.35"/>'
                '<ellipse cx="0" cy="0" rx="150" ry="105" fill="#b9773a"/>'
                '<ellipse cx="-5" cy="-15" rx="130" ry="85" fill="#d79c5a"/>'
                '<ellipse cx="-40" cy="-45" rx="50" ry="22" fill="#e9bd80"/>'
                '<path d="M-70 -5 C -30 -30, 20 10, 70 -20" stroke="#a5642c" stroke-width="10" fill="none" stroke-linecap="round"/>'
                '<path d="M-20 30 C 10 15, 40 35, 60 20" stroke="#a5642c" stroke-width="8" fill="none" stroke-linecap="round"/></g>')
    rolls = roll(560, 560) + roll(830, 520) + roll(1060, 590, 0.95) + roll(640, 760) + roll(920, 750)
    return basket + cloth + rolls


@scene(20)  # Perfect Pancakes
def pancakes():
    out = plate(700, 760, 540, 330)
    cx, rx, ry = 700, 340, 190
    for i in range(6):
        y = 790 - i * 56
        out += f'<ellipse cx="{cx}" cy="{y + 26}" rx="{rx}" ry="{ry}" fill="#a8622a"/>'
        out += f'<ellipse cx="{cx}" cy="{y}" rx="{rx}" ry="{ry}" fill="#e2ab6a"/>'
    top = 790 - 5 * 56
    out += f'<ellipse cx="{cx}" cy="{top}" rx="{rx - 30}" ry="{ry - 20}" fill="#c98a45"/>'
    out += f'<ellipse cx="{cx}" cy="{top}" rx="{rx - 70}" ry="{ry - 50}" fill="#d49a56"/>'
    syrup = (f'<path d="M480 {top - 30} C 520 {top - 140}, 900 {top - 150}, 930 {top - 20} C 960 {top + 60}, 880 {top + 130}, 760 {top + 140} '
             f'C 600 {top + 150}, 450 {top + 80}, 480 {top - 30} Z" fill="#8f4510" opacity="0.92"/>'
             f'<path d="M470 {top + 20} L470 {top + 180} C470 {top + 210}, 500 {top + 210}, 500 {top + 180} L500 {top + 60} Z" fill="#8f4510"/>'
             f'<path d="M900 {top + 90} L905 {top + 240} C905 {top + 270}, 935 {top + 270}, 935 {top + 240} L930 {top + 60} Z" fill="#8f4510"/>'
             f'<path d="M640 {top + 140} L645 {top + 290} C645 {top + 320}, 675 {top + 320}, 675 {top + 290} L670 {top + 140} Z" fill="#8f4510"/>'
             f'<ellipse cx="620" cy="{top - 40}" rx="70" ry="18" fill="#b8692a"/>')
    sugar = dots(cx, top + 10, 320, 170, 45, "#ffffff", r=4, seed=9, opacity=0.85)
    pitcher = ('<ellipse cx="1360" cy="520" rx="130" ry="36" fill="' + SHADOW + '"/>'
               '<path d="M1460 340 C1540 340, 1540 460, 1450 470" stroke="#d9e4ea" stroke-width="22" fill="none"/>'
               + cylinder(1350, 260, 500, 110, 34, "#cfdde5", "#e7eef2")
               + '<path d="M1240 330 L1240 500 A110 34 0 0 0 1460 500 L1460 330 A110 34 0 0 1 1240 330 Z" fill="#8f4510" opacity="0.85"/>'
               '<path d="M1238 260 L1215 240 L1250 252 Z" fill="#cfdde5"/>')
    return out + syrup + butter(700, top - 50, 0.9) + sugar + pitcher


@scene(64)  # Chocolate Fudge
def fudge():
    out = board(160, 260, 1280, 720) + '<rect x="230" y="320" width="1140" height="600" rx="12" fill="#efe6d6"/>'
    choc = ("#4a2a1c", "#5d3526", "#6d4130")
    pb = ("#b37a3e", "#cf9a5b", "#ddb075")
    for row in range(3):
        for col in range(5):
            x, y = 290 + col * 212 + (row % 2) * 30, 360 + row * 185
            side, top, hi = choc if (row + col) % 3 else pb
            out += (f'<rect x="{x + 10}" y="{y + 20}" width="170" height="150" rx="14" fill="#cfc3ad"/>'
                    f'<rect x="{x}" y="{y + 28}" width="170" height="120" rx="14" fill="{side}"/>'
                    f'<rect x="{x}" y="{y}" width="170" height="120" rx="14" fill="{top}"/>'
                    f'<path d="M{x + 30} {y + 70} C {x + 60} {y + 40}, {x + 110} {y + 90}, {x + 140} {y + 55}" stroke="{hi}" stroke-width="9" fill="none" stroke-linecap="round"/>')
    return out


@scene(13)  # Sugared Pecans
def sugared_pecans():
    cx, rim = 760, 520
    out = shadow(cx, 700, 470, 170)
    out += f'<path d="M{cx - 440} {rim} A440 300 0 0 0 {cx + 440} {rim} Z" fill="#4f6f94"/>'
    out += f'<path d="M{cx - 380} {rim + 120} A380 200 0 0 0 {cx + 380} {rim + 120}" stroke="#6b8bb0" stroke-width="14" fill="none"/>'
    out += f'<ellipse cx="{cx}" cy="{rim}" rx="440" ry="150" fill="#f3efe7"/><ellipse cx="{cx}" cy="{rim}" rx="410" ry="130" fill="#3f5c7e"/>'

    def pecan(x, y, a, s=1.0):
        return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f}) scale({s})">'
                '<ellipse rx="58" ry="30" fill="#7a3d18"/><ellipse rx="50" ry="23" fill="#9a5226"/>'
                '<path d="M-44 0 L44 0" stroke="#6a3212" stroke-width="5"/>'
                '<path d="M-30 -12 C -20 -4, -10 -16, 0 -8 C 10 -16, 20 -4, 30 -12" stroke="#6a3212" stroke-width="4" fill="none"/>'
                '<path d="M-30 12 C -20 4, -10 16, 0 8 C 10 16, 20 4, 30 12" stroke="#6a3212" stroke-width="4" fill="none"/></g>')
    rng = random.Random(4)
    nuts = []
    for _ in range(90):
        x, y = rng.uniform(-1, 1), rng.uniform(-1, 0.6)
        if x * x + y * y <= 1:
            nuts.append((rim + y * 170 - (1 - x * x) * 60, cx + x * 380, rng.uniform(0, 360)))
    for y, x, a in sorted(nuts):
        out += pecan(x, y, a)
    out += dots(cx, rim - 60, 380, 150, 120, "#fff8ec", r=4, seed=5, opacity=0.9)
    for x, y, a in ((1300, 900, 20), (1380, 820, 70), (260, 900, -30), (1240, 1000, 110)):
        out += pecan(x, y, a)
    sticks = "".join(f'<g transform="rotate(-18 {300 + i * 30} {300 + i * 40})">'
                     f'<rect x="{180 + i * 30}" y="{280 + i * 40}" width="300" height="46" rx="23" fill="{SHADOW}" transform="translate(10 16)"/>'
                     f'<rect x="{180 + i * 30}" y="{280 + i * 40}" width="300" height="46" rx="23" fill="#9a5530"/>'
                     f'<rect x="{180 + i * 30}" y="{290 + i * 40}" width="300" height="10" fill="#b8703f"/></g>' for i in range(2))
    return sticks + out


@scene(47)  # Angel Food Cake
def angel_food():
    cx = 680
    stand = (shadow(cx, 700, 480, 170)
             + f'<path d="M{cx - 120} 900 L{cx - 60} 720 L{cx + 60} 720 L{cx + 120} 900 Z" fill="#e6ded2"/>'
             f'<ellipse cx="{cx}" cy="905" rx="200" ry="50" fill="#e6ded2"/>'
             f'<ellipse cx="{cx}" cy="690" rx="480" ry="170" fill="#f6f1ea"/><ellipse cx="{cx}" cy="680" rx="440" ry="150" fill="#ece5da"/>')
    cake = cylinder(cx, 380, 640, 340, 120, "#c98d4b", "#e2ac6a", side_dark="#a8702f")
    cake += f'<ellipse cx="{cx}" cy="380" rx="300" ry="100" fill="#d9a05e"/>'
    cake += f'<ellipse cx="{cx}" cy="380" rx="95" ry="34" fill="#8d5a30"/><ellipse cx="{cx}" cy="388" rx="80" ry="24" fill="#5e3a1e"/>'
    cake += dots(cx, 380, 280, 90, 40, "#fff8ec", r=5, seed=6, opacity=0.8)
    side = plate(1290, 920, 270, 150)
    slice_ = ('<path d="M1110 960 L1410 880 L1420 960 L1120 1040 Z" fill="#fbf3e0"/>'
              '<path d="M1110 960 L1410 880 L1420 960" stroke="#c98d4b" stroke-width="12" fill="none"/>'
              '<path d="M1110 960 L1410 880 L1370 850 L1110 935 Z" fill="#d9a05e"/>')

    def berry(x, y, s=1.0):
        return (f'<g transform="translate({x} {y}) scale({s})">'
                '<path d="M0 40 C -40 10, -40 -30, 0 -30 C 40 -30, 40 10, 0 40 Z" fill="#c8263a"/>'
                '<path d="M-22 -30 L0 -44 L22 -30 L0 -22 Z" fill="#4e8a3e"/>'
                '<g fill="#f6d36b"><circle cx="-10" cy="-6" r="3"/><circle cx="10" cy="4" r="3"/><circle cx="0" cy="20" r="3"/></g></g>')
    return stand + cake + side + slice_ + berry(1200, 1000) + berry(1260, 1020, 0.9) + berry(1440, 1000, 0.85)


@scene(49)  # Chocolate Cherry Cake
def choc_cherry():
    pan = (f'<polygon points="262,332 1162,332 1272,872 152,872" fill="{SHADOW}" transform="translate(18 28)"/>'
           '<polygon points="262,332 1162,332 1272,872 152,872" fill="#a3a9ae"/>'
           '<polygon points="292,358 1132,358 1232,846 192,846" fill="#7d848b"/>')
    out = pan
    # 4 x 3 squares of frosted cake, one missing.
    for r in range(3):
        for c in range(4):
            if (r, c) == (2, 0):
                continue
            y0, y1 = 368 + r * 158, 368 + (r + 1) * 158 - 10
            def xl(y, c):
                left = 292 - (y - 358) * 100 / 488
                right = 1132 + (y - 358) * 100 / 488
                return left + (right - left) * c / 4
            pts = f"{xl(y0, c) + 6:.0f},{y0} {xl(y0, c + 1) - 6:.0f},{y0} {xl(y1, c + 1) - 6:.0f},{y1} {xl(y1, c) + 6:.0f},{y1}"
            out += f'<polygon points="{pts}" fill="#3e2217"/>'
            mx, my = (xl(y0, c) + xl(y1, c + 1)) / 2, (y0 + y1) / 2
            out += f'<path d="M{mx - 70:.0f} {my + 20:.0f} C {mx - 30:.0f} {my - 10:.0f}, {mx + 20:.0f} {my + 30:.0f}, {mx + 70:.0f} {my:.0f}" stroke="#55301f" stroke-width="8" fill="none" stroke-linecap="round"/>'
            out += (f'<circle cx="{mx:.0f}" cy="{my - 10:.0f}" r="30" fill="#a8102a"/><circle cx="{mx - 9:.0f}" cy="{my - 20:.0f}" r="9" fill="#e45a6e"/>'
                    f'<path d="M{mx:.0f} {my - 38:.0f} C {mx + 10:.0f} {my - 80:.0f}, {mx + 40:.0f} {my - 90:.0f}, {mx + 50:.0f} {my - 95:.0f}" stroke="#5a7a2e" stroke-width="6" fill="none"/>')
    side = plate(1300, 960, 260, 150)
    piece = ('<polygon points="1160,930 1380,900 1440,960 1220,1000" fill="#3e2217"/>'
             '<polygon points="1220,1000 1440,960 1440,1040 1220,1080" fill="#5a3424"/>'
             '<polygon points="1160,930 1220,1000 1220,1080 1160,1010" fill="#4a2a1c"/>'
             '<g fill="#b3122e"><ellipse cx="1280" cy="1030" rx="22" ry="12"/><ellipse cx="1370" cy="1010" rx="18" ry="10"/><ellipse cx="1190" cy="990" rx="12" ry="14"/></g>'
             '<circle cx="1300" cy="930" r="26" fill="#a8102a"/><circle cx="1292" cy="922" r="8" fill="#e45a6e"/>')
    return out + side + piece


@scene(50)  # Chocolate Marshmallow Cake
def choc_marshmallow():
    cx = 680
    stand = (shadow(cx, 760, 500, 170)
             + f'<path d="M{cx - 120} 960 L{cx - 60} 790 L{cx + 60} 790 L{cx + 120} 960 Z" fill="#e6ded2"/>'
             f'<ellipse cx="{cx}" cy="965" rx="200" ry="50" fill="#e6ded2"/>'
             f'<ellipse cx="{cx}" cy="760" rx="500" ry="170" fill="#f6f1ea"/><ellipse cx="{cx}" cy="750" rx="460" ry="150" fill="#ece5da"/>')
    cake = cylinder(cx, 390, 700, 370, 130, "#f4ede2", "#fffbf5", side_dark="#d9cdbb")
    swirls = "".join(
        f'<path d="M{x - 40} {y} C {x - 20} {y - 30}, {x + 20} {y - 30}, {x + 40} {y} C {x + 20} {y + 20}, {x - 10} {y + 10}, {x} {y - 5}" stroke="#e3d8c8" stroke-width="8" fill="none" stroke-linecap="round"/>'
        for x, y in ((520, 360), (690, 330), (850, 380), (600, 440), (780, 450), (440, 420), (920, 430)))
    side_swirls = "".join(f'<path d="M{x} 500 C {x + 30} 560, {x - 30} 620, {x} 690" stroke="#e3d8c8" stroke-width="8" fill="none"/>'
                          for x in (380, 480, 600, 720, 840, 960))
    def edge(x):  # front edge of the cake's top
        return 390 + 130 * math.sqrt(max(0, 1 - ((x - cx) / 370) ** 2))
    dribble = (f'<path d="M{cx - 370} 390 A370 130 0 0 0 {cx + 370} 390" stroke="#4a2a1c" stroke-width="20" fill="none"/>'
               + "".join(f'<path d="M{x} {edge(x):.0f} L{x} {edge(x) + 50 + (i % 3) * 35:.0f}" stroke="#4a2a1c" stroke-width="18" stroke-linecap="round"/>'
                         for i, x in enumerate(range(360, 1010, 65))))
    side = plate(1300, 1000, 250, 130)
    piece = ''
    for i, (fill, h) in enumerate((("#3e2217", 50), ("#fbf6ee", 22), ("#3e2217", 50), ("#fbf6ee", 30))):
        y = 1010 - sum(hh for _, hh in ((("#3e2217", 50), ("#fbf6ee", 22), ("#3e2217", 50), ("#fbf6ee", 30))[:i])) - h
        piece += f'<polygon points="1130,{y + 40} 1420,{y - 30} 1420,{y - 30 + h} 1130,{y + 40 + h}" fill="{fill}"/>'
    piece += '<path d="M1130 898 L1420 828 L1370 800 Z" fill="#fffbf5"/>'
    return stand + cake + side_swirls + dribble + swirls + side + piece


# ---- render ---------------------------------------------------------------

def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    drawn = Path(__file__).parent
    ids = [int(a) for a in sys.argv[2:]] or sorted(set(SCENES) | {int(p.stem) for p in drawn.glob("*.svg")})
    for rid in ids:
        path = out / f"{rid}.svg"
        if rid in SCENES:
            path.write_text(svg(SCENES[rid]()))
        else:
            path.write_text((drawn / f"{rid}.svg").read_text())
        subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), str(path), "-o", str(out / f"{rid}.png")], check=True)
        Image.open(out / f"{rid}.png").convert("RGB").resize((400, 300), Image.LANCZOS).save(out / f"{rid}-thumb.png")
        print(rid)


if __name__ == "__main__":
    main()
