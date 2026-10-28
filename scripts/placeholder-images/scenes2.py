"""The rest of the recipes, sharing scenes.py's table and pieces.

    python scripts/placeholder-images/scenes2.py OUT_DIR [RECIPE_ID ...]
"""
import math
import random
import sys

import scenes
from scenes import SCENES, SHADOW, WOOD, board, butter, cylinder, dots, napkin, plate, scene, shadow


# ---- more shared pieces ----------------------------------------------------

def bowl(cx, rim, rx, ry, depth, color="#f4efe8", body=None, band=None, inside="#e2dacd"):
    body = body or color
    out = shadow(cx, rim + depth * 0.55, rx * 0.95, ry * 1.2, dx=24, dy=20)
    out += f'<path d="M{cx - rx} {rim} A{rx} {depth} 0 0 0 {cx + rx} {rim} Z" fill="{body}"/>'
    if band:
        out += f'<path d="M{cx - rx * 0.86} {rim + depth * 0.45} A{rx * 0.86} {depth * 0.55} 0 0 0 {cx + rx * 0.86} {rim + depth * 0.45}" stroke="{band}" stroke-width="16" fill="none"/>'
    out += f'<ellipse cx="{cx}" cy="{rim}" rx="{rx}" ry="{ry}" fill="{color}"/>'
    out += f'<ellipse cx="{cx}" cy="{rim}" rx="{rx * 0.93}" ry="{ry * 0.86}" fill="{inside}"/>'
    return out


def pot(cx, rim, rx, ry, height, color="#c8442f", rimc="#a83625"):
    out = shadow(cx, rim + height, rx, ry, dx=24, dy=10)
    for side in (-1, 1):
        x = cx + side * (rx + 40)
        out += f'<rect x="{x - 50}" y="{rim + 40}" width="100" height="44" rx="22" fill="{rimc}"/>'
    out += f'<path d="M{cx - rx} {rim} L{cx - rx} {rim + height} A{rx} {ry} 0 0 0 {cx + rx} {rim + height} L{cx + rx} {rim} Z" fill="{color}"/>'
    out += f'<path d="M{cx + rx * 0.5} {rim + ry * 0.85} L{cx + rx * 0.5} {rim + height + ry * 0.85} A{rx} {ry} 0 0 0 {cx + rx} {rim + height} L{cx + rx} {rim} Z" fill="{rimc}" opacity="0.5"/>'
    out += f'<ellipse cx="{cx}" cy="{rim}" rx="{rx}" ry="{ry}" fill="{rimc}"/>'
    out += f'<ellipse cx="{cx}" cy="{rim}" rx="{rx - 22}" ry="{ry - 14}" fill="#3a2a22"/>'
    return out


def cookie(x, y, r, edge, top, spots=(), seed=0, tilt=0.78):
    out = (f'<ellipse cx="{x + 10}" cy="{y + r * tilt * 0.4 + 14}" rx="{r}" ry="{r * tilt}" fill="{SHADOW}" opacity="0.6"/>'
           f'<ellipse cx="{x}" cy="{y + r * 0.18}" rx="{r}" ry="{r * tilt}" fill="{edge}"/>'
           f'<ellipse cx="{x}" cy="{y}" rx="{r * 0.97}" ry="{r * tilt * 0.95}" fill="{top}"/>')
    for i, (color, n, size) in enumerate(spots):
        out += dots(x, y, r * 0.72, r * tilt * 0.68, n, color, r=size, seed=seed * 7 + i)
    return out


def strands(cx, cy, rx, ry, n, color, edge, width=16, seed=1, length=160):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        a, d = rng.uniform(0, 2 * math.pi), math.sqrt(rng.random())
        x, y = cx + math.cos(a) * rx * d * 0.85, cy + math.sin(a) * ry * d * 0.85
        b = rng.uniform(0, 2 * math.pi)
        dx, dy = math.cos(b) * length / 2, math.sin(b) * length / 2 * ry / rx
        bend = rng.uniform(-60, 60)
        out.append(f'M{x - dx:.0f} {y - dy:.0f} Q{x + bend:.0f} {y - bend * 0.5:.0f} {x + dx:.0f} {y + dy:.0f}')
    paths = " ".join(out)
    return (f'<path d="{paths}" stroke="{edge}" stroke-width="{width + 6}" fill="none" stroke-linecap="round"/>'
            f'<path d="{paths}" stroke="{color}" stroke-width="{width}" fill="none" stroke-linecap="round"/>')


def bits(cx, cy, rx, ry, n, shape, seed=1):
    """Scatters shape(x, y, angle, rng) inside an ellipse, back to front."""
    rng = random.Random(seed)
    pts = []
    while len(pts) < n:
        x, y = rng.uniform(-1, 1), rng.uniform(-1, 1)
        if x * x + y * y <= 1:
            pts.append((cy + y * ry, cx + x * rx, rng.uniform(0, 360)))
    return "".join(shape(x, y, a, rng) for y, x, a in sorted(pts))


def leaf(x, y, a, s=1.0, c1="#5e9a42", c2="#7cb85a"):
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f}) scale({s})">'
            f'<path d="M-40 0 C -20 -26, 20 -26, 40 0 C 20 26, -20 26, -40 0 Z" fill="{c1}"/>'
            f'<path d="M-34 0 C -18 -18, 18 -18, 34 0 Z" fill="{c2}"/><path d="M-36 0 L36 0" stroke="#4a7d32" stroke-width="3"/></g>')


def parsley(cx, cy, rx, ry, n=12, seed=3):
    return bits(cx, cy, rx, ry, n, lambda x, y, a, r: leaf(x, y, a, 0.35), seed=seed)


def lemon_wedge(x, y, a=0, s=1.0):
    return (f'<g transform="translate({x} {y}) rotate({a}) scale({s})">'
            '<path d="M-70 0 A70 70 0 0 0 70 0 Z" fill="#e8c93a"/><path d="M-58 0 A58 58 0 0 0 58 0 Z" fill="#f7e27a"/>'
            '<g stroke="#e8c93a" stroke-width="4"><line x1="0" y1="0" x2="0" y2="56"/><line x1="0" y1="0" x2="-40" y2="40"/><line x1="0" y1="0" x2="40" y2="40"/></g></g>')


def lemon_slice(x, y, r=60):
    spokes = "".join(f'<line x1="{x}" y1="{y}" x2="{x + r * 0.78 * math.cos(math.radians(d)):.0f}" y2="{y + r * 0.62 * math.sin(math.radians(d)):.0f}"/>' for d in range(0, 360, 45))
    return (f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r * 0.8}" fill="#e8c93a"/><ellipse cx="{x}" cy="{y}" rx="{r * 0.84}" ry="{r * 0.66}" fill="#f7e27a"/>'
            f'<g stroke="#ecd055" stroke-width="5">{spokes}</g>')


def bar(x, y, w, h, d, top, front, side):
    """A box seen from the front and a little above: top face, front face, right side."""
    return (f'<polygon points="{x},{y} {x + w},{y} {x + w + d},{y - d * 0.6} {x + d},{y - d * 0.6}" fill="{top}"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{front}"/>'
            f'<polygon points="{x + w},{y} {x + w + d},{y - d * 0.6} {x + w + d},{y + h - d * 0.6} {x + w},{y + h}" fill="{side}"/>')


def pie(cx, cy, rx, ry, filling, crust="#d39a5c", flute="#e6b071", rim="#b57a45", gap=True, gap_fill=None):
    out = (shadow(cx, cy, rx + 100, ry + 75) +
           f'<ellipse cx="{cx}" cy="{cy}" rx="{rx + 100}" ry="{ry + 75}" fill="#f6f1ea"/>'
           f'<ellipse cx="{cx}" cy="{cy}" rx="{rx + 60}" ry="{ry + 45}" fill="#e9e1d6"/>'
           f'<ellipse cx="{cx}" cy="{cy}" rx="{rx + 30}" ry="{ry + 22}" fill="{rim}"/>'
           f'<ellipse cx="{cx}" cy="{cy - 4}" rx="{rx + 18}" ry="{ry + 12}" fill="{crust}"/>')
    if flute:
        out += "".join(f'<circle cx="{cx + (rx + 18) * math.cos(t):.0f}" cy="{cy - 4 + (ry + 12) * math.sin(t):.0f}" r="30" fill="{flute}"/>'
                       for t in (i * 2 * math.pi / 30 for i in range(30)))
    out += f'<ellipse cx="{cx}" cy="{cy - 15}" rx="{rx - 15}" ry="{ry - 15}" fill="{filling}"/>'
    if gap:
        ex, ey = cx + (rx - 15), cy - 15
        sx, sy = cx + (rx - 15) * math.cos(0.75), cy - 15 + (ry - 15) * math.sin(0.75)
        out += f'<path d="M{cx} {cy - 15} L{ex} {ey} A{rx - 15} {ry - 15} 0 0 1 {sx:.0f} {sy:.0f} Z" fill="{gap_fill or "#00000033"}"/>'
    return out


def pecan(x, y, a, s=1.0):
    return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f}) scale({s})">'
            '<ellipse rx="58" ry="30" fill="#7a3d18"/><ellipse rx="50" ry="23" fill="#9a5226"/>'
            '<path d="M-44 0 L44 0" stroke="#6a3212" stroke-width="5"/>'
            '<path d="M-30 -12 C -20 -4, -10 -16, 0 -8 C 10 -16, 20 -4, 30 -12" stroke="#6a3212" stroke-width="4" fill="none"/>'
            '<path d="M-30 12 C -20 4, -10 16, 0 8 C 10 16, 20 4, 30 12" stroke="#6a3212" stroke-width="4" fill="none"/></g>')


def glass_of_milk(x, y):
    return ('<ellipse cx="%d" cy="%d" rx="110" ry="34" fill="%s"/>' % (x + 16, y + 330, SHADOW)
            + cylinder(x, y, y + 320, 100, 30, "#f7f7f4", "#ffffff", side_dark="#dcdcd6")
            + f'<rect x="{x - 70}" y="{y + 40}" width="18" height="240" rx="9" fill="#ffffff"/>')


def whisk(x, y, a):
    wires = "".join(f'<path d="M0 0 C {s * 30} 60, {s * 40} 140, 0 190" stroke="#c7ccd1" stroke-width="7" fill="none"/>' for s in (-1, -0.5, 0.5, 1))
    return (f'<g transform="translate({x} {y}) rotate({a})">{wires}'
            '<rect x="-16" y="-240" width="32" height="250" rx="16" fill="#3a3a3a"/></g>')


def spatula(x, y, a):
    return (f'<g transform="translate({x} {y}) rotate({a})">'
            '<rect x="-12" y="-300" width="24" height="300" rx="12" fill="#c69060"/>'
            '<path d="M-50 0 L50 0 L44 110 C 30 130, -30 130, -44 110 Z" fill="#e05f5f"/></g>')


def rolling_pin(x, y, a, length=620):
    return (f'<g transform="rotate({a} {x} {y})">'
            f'<rect x="{x - length / 2 + 16}" y="{y - 40 + 24}" width="{length}" height="80" rx="40" fill="{SHADOW}"/>'
            f'<rect x="{x - length / 2 - 90}" y="{y - 18}" width="{length + 180}" height="36" rx="18" fill="#b07a48"/>'
            f'<rect x="{x - length / 2}" y="{y - 40}" width="{length}" height="80" rx="40" fill="#d9a873"/>'
            f'<rect x="{x - length / 2 + 20}" y="{y - 28}" width="{length - 40}" height="14" rx="7" fill="#e8c196"/></g>')


def ladle(x, y, a):
    return (f'<g transform="translate({x} {y}) rotate({a})">'
            '<rect x="-14" y="-420" width="28" height="420" rx="14" fill="#c7ccd1"/>'
            '<rect x="-6" y="-410" width="8" height="400" rx="4" fill="#e8ebee"/></g>')


def flour(cx, cy, rx, ry, seed=2):
    return dots(cx, cy, rx, ry, 70, "#f8f4ec", r=6, seed=seed, opacity=0.7)


# ---- cakes ------------------------------------------------------------------

@scene(24)  # Great Vanilla Cupcake
def cupcakes():
    def cupcake(x, y, liner, liner_dark, frost, sprinkles):
        pleats = "".join(f'<line x1="{x - 110 + i * 22}" y1="{y}" x2="{x - 90 + i * 18}" y2="{y + 170}"/>' for i in range(11))
        swirl = "".join(f'<ellipse cx="{x}" cy="{y - 20 - i * 52}" rx="{150 - i * 34}" ry="{60 - i * 9}" fill="{c}"/>'
                        for i, c in enumerate((frost[1], frost[0], frost[1], frost[0])))
        spr = "".join(f'<rect x="{x + dx}" y="{y + dy}" width="22" height="8" rx="4" fill="{c}" transform="rotate({a} {x + dx} {y + dy})"/>'
                      for dx, dy, a, c in sprinkles)
        return (f'<ellipse cx="{x + 14}" cy="{y + 180}" rx="110" ry="30" fill="{SHADOW}"/>'
                f'<path d="M{x - 120} {y} L{x + 120} {y} L{x + 90} {y + 175} L{x - 90} {y + 175} Z" fill="{liner}"/>'
                f'<g stroke="{liner_dark}" stroke-width="6">{pleats}</g>'
                f'<ellipse cx="{x}" cy="{y}" rx="125" ry="34" fill="#e7b46a"/>' + swirl
                + f'<path d="M{x} {y - 210} C {x + 20} {y - 230}, {x + 8} {y - 250}, {x - 6} {y - 258}" stroke="{frost[0]}" stroke-width="22" stroke-linecap="round" fill="none"/>'
                + spr)
    spr = [(-60, -60, 20, "#e05f8a"), (40, -90, -30, "#5fa8e0"), (-20, -140, 60, "#f2c94c"), (70, -30, 10, "#6fcf97"),
           (-90, -20, -40, "#5fa8e0"), (10, -40, 80, "#e05f8a"), (30, -170, -10, "#6fcf97")]
    return (board(170, 640, 1260, 380)
            + cupcake(470, 700, "#f4b6c2", "#e391a3", ("#fffaf2", "#f3e9d8"), spr)
            + cupcake(1130, 700, "#a9cfee", "#80b2dc", ("#fffaf2", "#f3e9d8"), spr[::-1])
            + cupcake(800, 790, "#f6dd8a", "#e5c35c", ("#fde3ec", "#f7cad9"), spr))


@scene(14)  # Venetians
def venetians():
    out = plate(780, 700, 600, 380)
    layers = (("#3e2217", 22), ("#5fa463", 54), ("#e3913a", 8), ("#f6efd9", 54), ("#e3913a", 8), ("#d9566a", 54), ("#3e2217", 18))

    def piece(x, y):
        o = ""
        top_y = y
        o += f'<polygon points="{x},{y} {x + 200},{y} {x + 250},{y - 40} {x + 50},{y - 40}" fill="#4a2a1c"/>'
        o += f'<path d="M{x + 30} {y - 20} C {x + 80} {y - 35}, {x + 140} {y - 5}, {x + 210} {y - 22}" stroke="#5d3526" stroke-width="6" fill="none"/>'
        for color, h in layers:
            o += f'<rect x="{x}" y="{top_y}" width="200" height="{h}" fill="{color}"/>'
            o += f'<polygon points="{x + 200},{top_y} {x + 250},{top_y - 40} {x + 250},{top_y - 40 + h} {x + 200},{top_y + h}" fill="{color}" opacity="0.8"/>'
            top_y += h
        return o
    for x, y in ((420, 470), (700, 450), (980, 470), (520, 700), (820, 690)):
        out += piece(x, y)
    return out


# ---- cookies and bars -------------------------------------------------------

def brownie(x, y, w=220, h=70, d=60, top="#4a2a1c", front="#3a1f14", side="#2e180f", crackle="#6b4130"):
    return (bar(x, y, w, h, d, top, front, side)
            + f'<path d="M{x + 30} {y - 15} C {x + 80} {y - 30}, {x + 130} {y - 5}, {x + w} {y - 25}" stroke="{crackle}" stroke-width="6" fill="none"/>')


@scene(74)  # Brownies
def brownies():
    out = board(200, 360, 1180, 640) + '<rect x="270" y="420" width="1040" height="520" rx="10" fill="#efe6d6"/>'
    for x, y in ((360, 560), (650, 560), (940, 560), (480, 800), (790, 800)):
        out += brownie(x, y)
    out += brownie(1040, 790, 220, 70, 60)
    out += brownie(1060, 700, 200, 70, 60)  # a stacked one
    return out


@scene(52)  # Final Exam Brownies
def final_exam():
    out = (f'<polygon points="262,312 1262,312 1352,892 172,892" fill="{SHADOW}" transform="translate(18 28)"/>'
           '<polygon points="262,312 1262,312 1352,892 172,892" fill="#a3a9ae"/>'
           '<polygon points="292,340 1232,340 1316,866 208,866" fill="#3e2217"/>')
    rng = random.Random(8)

    def mallow(x, y, a, r):
        return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><rect x="-22" y="-16" width="44" height="34" rx="12" fill="#e9e2d6"/>'
                '<rect x="-22" y="-20" width="44" height="30" rx="12" fill="#fffbf4"/></g>')

    def nut(x, y, a, r):
        return f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><path d="M-18 -10 L16 -14 L20 10 L-14 14 Z" fill="#c89a62"/></g>'
    out += bits(762, 603, 470, 230, 70, mallow, seed=8)
    out += bits(762, 603, 480, 240, 50, nut, seed=9)
    out += dots(762, 603, 470, 230, 40, "#2a160d", r=9, seed=10)
    out += '<g stroke="#2a160d" stroke-width="8">' + "".join(
        f'<line x1="{292 + i * 235 - (0) * 0}" y1="340" x2="{208 + i * 277}" y2="866"/>' for i in range(1, 4)) + \
        '<line x1="252" y1="603" x2="1274" y2="603"/></g>'
    return out


@scene(73)  # Gooey Brownies (a single-serving mug brownie)
def mug_brownie():
    cx, top = 720, 420
    mug = (f'<ellipse cx="{cx + 20}" cy="{top + 470}" rx="270" ry="70" fill="{SHADOW}"/>'
           f'<path d="M{cx + 230} {top + 120} C {cx + 400} {top + 110}, {cx + 400} {top + 350}, {cx + 220} {top + 340}" stroke="#d65c4c" stroke-width="56" fill="none"/>'
           + cylinder(cx, top, top + 430, 250, 70, "#e46a59", "#f0e8de", side_dark="#b84a3c")
           + f'<ellipse cx="{cx}" cy="{top}" rx="226" ry="58" fill="#3a1f14"/>'
           f'<path d="M{cx - 226} {top} C {cx - 150} {top - 90}, {cx + 150} {top - 90}, {cx + 226} {top} C {cx + 150} {top + 50}, {cx - 150} {top + 50}, {cx - 226} {top} Z" fill="#4a2a1c"/>'
           f'<path d="M{cx - 160} {top - 30} C {cx - 80} {top - 70}, {cx + 40} {top - 40}, {cx + 140} {top - 50}" stroke="#6b4130" stroke-width="8" fill="none"/>'
           + dots(cx, top - 20, 150, 30, 10, "#2a160d", r=14, seed=4)
           + f'<path d="M{cx - 120} {top + 20} C {cx - 130} {top + 80}, {cx - 100} {top + 90}, {cx - 95} {top + 40}" fill="#4a2a1c"/>'
           f'<path d="M{cx + 60} {top + 30} C {cx + 55} {top + 110}, {cx + 90} {top + 110}, {cx + 95} {top + 35}" fill="#4a2a1c"/>')
    spoon = (f'<g transform="rotate(30 {cx + 40} {top - 40})"><rect x="{cx + 25}" y="{top - 380}" width="30" height="360" rx="15" fill="#c7ccd1"/>'
             f'<ellipse cx="{cx + 40}" cy="{top - 30}" rx="50" ry="70" fill="#c7ccd1"/></g>')
    chips = "".join(f'<path d="M{x} {y} L{x - 22} {y + 30} L{x + 22} {y + 30} Z" fill="#3a1f14"/>' for x, y in ((300, 900), (360, 960), (1180, 920), (1250, 860), (1120, 990)))
    return napkin(1050, 760, 400, 300, angle=10, stripe="#c8442f") + mug + spoon + chips


def cc_cookie(x, y, r, seed, extra=()):
    return cookie(x, y, r, "#b8732f", "#d9a05e", spots=(("#4a2a1c", 9, r * 0.11),) + tuple(extra), seed=seed)


@scene(55)  # Chocolate Chip Cookie Recipe
def cc_recipe():
    out = plate(780, 660, 600, 380)
    for i, (x, y) in enumerate(((560, 520), (860, 480), (1080, 600), (480, 720), (760, 730), (1000, 820))):
        out += cc_cookie(x, y, 150, i)
    return out


@scene(35)  # Just Right Chocolate Chip Cookies
def cc_just_right():
    out = plate(640, 720, 460, 300)
    for i in range(5):
        out += cookie(640, 760 - i * 48, 210, "#b8732f", "#d9a05e", seed=i)
    out += dots(640, 760 - 4 * 48, 150, 110, 12, "#4a2a1c", r=18, seed=3)
    out += cc_cookie(1180, 960, 120, 9) + cc_cookie(1390, 1010, 110, 11)
    return out + glass_of_milk(1260, 300)


@scene(61)  # The Ultimate Chocolate Chip Cookie
def cc_ultimate():
    rack = ('<rect x="186" y="296" width="1260" height="720" rx="20" fill="' + SHADOW + '"/>'
            '<rect x="170" y="270" width="1260" height="720" rx="20" fill="none" stroke="#2f2f2f" stroke-width="14"/>'
            + "".join(f'<line x1="{x}" y1="270" x2="{x}" y2="990" stroke="#3a3a3a" stroke-width="6"/>' for x in range(230, 1420, 60))
            + "".join(f'<line x1="170" y1="{y}" x2="1430" y2="{y}" stroke="#3a3a3a" stroke-width="6"/>' for y in (450, 630, 810)))
    out = rack
    for i, (x, y) in enumerate(((380, 440), (720, 420), (1070, 450), (380, 800), (720, 780), (1070, 810))):
        out += cookie(x, y, 160, "#a8622a", "#c98a45", spots=(("#3a1f14", 9, 17), ("#e2b07a", 5, 14)), seed=i)
    out += pecan(1380, 1100, 30, 0.9) + pecan(1500, 1040, -40, 0.8) + pecan(130, 1100, 70, 0.8)
    return out


@scene(56)  # Chocolate Covered Cherry Cookies
def cherry_cookies():
    out = plate(780, 660, 600, 380)
    for i, (x, y) in enumerate(((560, 520), (860, 480), (1080, 600), (480, 720), (760, 730), (1000, 820))):
        out += cookie(x, y, 130, "#2e180f", "#4a2a1c", seed=i)
        out += f'<ellipse cx="{x}" cy="{y - 10}" rx="62" ry="50" fill="#3a1f14"/>'
        out += f'<circle cx="{x}" cy="{y - 26}" r="30" fill="#c8102e"/><circle cx="{x - 9}" cy="{y - 35}" r="9" fill="#f07c8c"/>'
        out += f'<path d="M{x - 62} {y - 10} C {x - 40} {y - 20}, {x - 20} {y + 6}, {x} {y - 4} C {x + 20} {y + 6}, {x + 40} {y - 20}, {x + 62} {y - 10}" stroke="#3a1f14" stroke-width="12" fill="none"/>'
    for x, y in ((1330, 1000), (1420, 960)):
        out += (f'<circle cx="{x}" cy="{y}" r="34" fill="#c8102e"/><circle cx="{x - 10}" cy="{y - 10}" r="10" fill="#f07c8c"/>'
                f'<path d="M{x} {y - 30} C {x + 10} {y - 90}, {x + 50} {y - 110}, {x + 60} {y - 120}" stroke="#5a7a2e" stroke-width="6" fill="none"/>')
    return out


@scene(15)  # Chocolate Crinkles
def crinkles():
    out = board(170, 330, 1260, 680, fill="#d9b48a", line="#c9a276")
    rng = random.Random(15)
    for i, (x, y) in enumerate(((400, 520), (700, 500), (1000, 520), (1260, 560), (520, 790), (830, 800), (1130, 820))):
        out += cookie(x, y, 125, "#2e180f", "#3e2217", seed=i, tilt=0.85)
        for _ in range(7):
            px, py = x + rng.uniform(-80, 80), y + rng.uniform(-70, 60)
            out += f'<path d="M{px:.0f} {py:.0f} l{rng.uniform(20, 40):.0f} {rng.uniform(-14, 14):.0f} l{rng.uniform(-8, 8):.0f} {rng.uniform(18, 30):.0f} l{rng.uniform(-40, -20):.0f} {rng.uniform(-6, 6):.0f} Z" fill="#fbf7f0"/>'
    return out + dots(800, 680, 620, 320, 60, "#fbf7f0", r=4, seed=11, opacity=0.6)


@scene(57)  # Ladylocks
def ladylocks():
    out = plate(780, 680, 620, 380)

    def lock(x, y, a):
        bands = "".join(f'<path d="M{-170 + i * 46} -{40 - i * 3} L{-150 + i * 46} {40 - i * 3}" stroke="#c98d4b" stroke-width="10"/>' for i in range(7))
        return (f'<g transform="translate({x} {y}) rotate({a})">'
                '<path d="M-200 -50 L150 -12 L150 12 L-200 50 Z" fill="#e8bd7e"/>' + bands
                + '<ellipse cx="-200" cy="0" rx="34" ry="52" fill="#fffaf2"/><ellipse cx="-222" cy="0" rx="30" ry="44" fill="#fffdf8"/></g>')
    for x, y, a in ((800, 480, -8), (840, 600, -4), (760, 720, 4), (820, 840, 8), (1080, 660, 160)):
        out += lock(x, y, a)
    return out + dots(780, 660, 450, 260, 80, "#ffffff", r=4, seed=12, opacity=0.8)


@scene(4)  # Nut Cups
def nut_cups():
    out = plate(780, 680, 620, 380)

    def cup(x, y):
        flutes = "".join(f'<line x1="{x - 80 + i * 20}" y1="{y}" x2="{x - 60 + i * 15}" y2="{y + 90}"/>' for i in range(9))
        return (f'<ellipse cx="{x + 10}" cy="{y + 98}" rx="76" ry="22" fill="#cfc3ad"/>'
                f'<path d="M{x - 92} {y} L{x + 92} {y} L{x + 64} {y + 95} L{x - 64} {y + 95} Z" fill="#d39a5c"/>'
                f'<g stroke="#b57a45" stroke-width="5">{flutes}</g>'
                f'<ellipse cx="{x}" cy="{y}" rx="96" ry="34" fill="#e6b071"/><ellipse cx="{x}" cy="{y - 2}" rx="74" ry="24" fill="#7a3d18"/>'
                + dots(x, y - 4, 60, 16, 8, "#a8602c", r=8, seed=x))
    for x, y in ((540, 500), (780, 470), (1020, 500), (440, 680), (680, 660), (920, 660), (1140, 690), (560, 850), (800, 840), (1040, 850)):
        out += cup(x, y)
    return out


@scene(5)  # Peanut Blossom Cookies
def peanut_blossoms():
    out = plate(780, 660, 600, 380)
    for i, (x, y) in enumerate(((560, 520), (860, 480), (1080, 600), (480, 720), (760, 730), (1000, 820))):
        out += cookie(x, y, 135, "#b5793c", "#d6a060", spots=(("#fff4dc", 18, 4),), seed=i)
        out += (f'<path d="M{x - 52} {y + 10} C {x - 50} {y - 40}, {x - 10} {y - 70}, {x} {y - 100} C {x + 10} {y - 70}, {x + 50} {y - 40}, {x + 52} {y + 10} Z" fill="#4a2a1c"/>'
                f'<path d="M{x - 20} {y - 20} C {x - 18} {y - 45}, {x - 8} {y - 65}, {x - 2} {y - 80}" stroke="#7a4a33" stroke-width="8" fill="none" stroke-linecap="round"/>'
                f'<ellipse cx="{x}" cy="{y + 10}" rx="52" ry="16" fill="#3a1f14"/>')
    return out


@scene(59)  # Pizzelles, Vanilla
def pizzelles():
    out = plate(760, 680, 600, 380)

    def pizzelle(x, y, r):
        ry = r * 0.78
        spokes = "".join(f'<line x1="{x}" y1="{y}" x2="{x + r * 0.9 * math.cos(math.radians(d)):.0f}" y2="{y + ry * 0.9 * math.sin(math.radians(d)):.0f}"/>' for d in range(0, 360, 30))
        rings = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{r * f:.0f}" ry="{ry * f:.0f}" fill="none"/>' for f in (0.3, 0.6, 0.88))
        return (f'<ellipse cx="{x}" cy="{y + 12}" rx="{r}" ry="{ry}" fill="#d8b277"/>'
                f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{ry}" fill="#f1d9a4"/>'
                f'<g stroke="#ddb877" stroke-width="7">{spokes}{rings}</g>')
    for i in range(4):
        out += pizzelle(700, 720 - i * 18, 300)
    out += pizzelle(1180, 600, 220)
    return out + dots(760, 640, 420, 260, 90, "#ffffff", r=4, seed=13, opacity=0.85)


@scene(17)  # Snowballs
def snowballs():
    out = plate(780, 700, 600, 380)

    def ball(x, y, r=78):
        return (f'<ellipse cx="{x + 10}" cy="{y + r * 0.8}" rx="{r}" ry="{r * 0.3}" fill="#cfc6b8"/>'
                f'<circle cx="{x}" cy="{y}" r="{r}" fill="#ebe5da"/><circle cx="{x - 8}" cy="{y - 8}" r="{r * 0.88}" fill="#fbf8f2"/>'
                f'<circle cx="{x - r * 0.35:.0f}" cy="{y - r * 0.35:.0f}" r="{r * 0.18:.0f}" fill="#ffffff"/>')
    pos = [(x, y) for y in (820, 700, 580) for x in range(500 if y == 820 else 560 if y == 700 else 640, 1120 if y == 820 else 1060 if y == 700 else 980, 150)]
    pos += [(780, 480)]
    for x, y in sorted(pos, key=lambda p: p[1]):
        out += ball(x, y)
    return out + dots(780, 900, 480, 100, 60, "#ffffff", r=5, seed=14)


@scene(76)  # The Best Rolled Sugar Cookies
def sugar_cookies():
    out = board(150, 260, 1300, 760, fill="#efe6d6", line="#e2d6c2")

    def star(x, y, r, fill, edge):
        pts = " ".join(f"{x + (r if i % 2 == 0 else r * 0.45) * math.sin(i * math.pi / 5):.0f},{y - (r if i % 2 == 0 else r * 0.45) * math.cos(i * math.pi / 5) * 0.85:.0f}" for i in range(10))
        pts2 = " ".join(f"{x + (r - 16 if i % 2 == 0 else r * 0.45 - 8) * math.sin(i * math.pi / 5):.0f},{y - 4 - (r - 16 if i % 2 == 0 else r * 0.45 - 8) * math.cos(i * math.pi / 5) * 0.85:.0f}" for i in range(10))
        return (f'<polygon points="{pts}" fill="#d9a05e" transform="translate(0 14)"/><polygon points="{pts}" fill="#f0cf96"/>'
                f'<polygon points="{pts2}" fill="{fill}"/>')

    def heart(x, y, s, fill):
        return (f'<g transform="translate({x} {y}) scale({s})">'
                '<path d="M0 90 C -150 0, -100 -90, 0 -30 C 100 -90, 150 0, 0 90 Z" fill="#d9a05e" transform="translate(0 14)"/>'
                '<path d="M0 90 C -150 0, -100 -90, 0 -30 C 100 -90, 150 0, 0 90 Z" fill="#f0cf96"/>'
                f'<path d="M0 72 C -120 0, -82 -70, 0 -18 C 82 -70, 120 0, 0 72 Z" fill="{fill}"/></g>')
    out += star(420, 480, 140, "#7fb3e0", 0) + heart(760, 470, 1.2, "#f2a7bb") + star(1110, 500, 130, "#f6dd8a", 0)
    out += cookie(470, 800, 120, "#d9a05e", "#f0cf96", seed=1) + f'<ellipse cx="470" cy="796" rx="96" ry="72" fill="#a8d5a2"/>'
    out += heart(800, 800, 1.0, "#ffffff") + star(1120, 810, 120, "#f2a7bb", 0)
    out += dots(800, 640, 560, 300, 40, "#f2c94c", r=5, seed=16) + dots(800, 640, 560, 300, 30, "#e05f8a", r=5, seed=17)
    return out + rolling_pin(800, 1080, -4, 700)


@scene(62)  # Thumbprint Cookies
def thumbprints():
    out = plate(780, 660, 600, 380)
    jams = ("#b3122e", "#e8913a", "#b3122e", "#e8913a", "#b3122e", "#e8913a", "#b3122e")
    for i, (x, y) in enumerate(((540, 500), (800, 470), (1060, 510), (440, 690), (700, 680), (960, 690), (1180, 700), (600, 860), (880, 860))):
        out += cookie(x, y, 105, "#b8732f", "#d39a5c", spots=(("#a8602c", 22, 7),), seed=i, tilt=0.8)
        out += f'<ellipse cx="{x}" cy="{y + 4}" rx="44" ry="32" fill="#7a3d18"/><ellipse cx="{x}" cy="{y}" rx="40" ry="28" fill="{jams[i % 7]}"/>'
        out += f'<ellipse cx="{x - 14}" cy="{y - 10}" rx="12" ry="6" fill="#ffffff" opacity="0.5"/>'
    return out


# ---- pies -------------------------------------------------------------------

@scene(29)  # Chocolate Ribbon Pie
def ribbon_pie():
    out = pie(680, 530, 420, 290, "#fbf7f0", crust="#3e2217", flute=None, rim="#2e180f", gap=False)
    out += f'<path d="M300 500 C 400 400, 500 640, 620 480 C 720 360, 820 650, 920 470 C 980 380, 1040 560, 1080 500" stroke="#4a2a1c" stroke-width="22" fill="none" stroke-linecap="round"/>'
    out += f'<path d="M340 600 C 440 520, 560 700, 680 600 C 800 500, 900 700, 1020 600" stroke="#4a2a1c" stroke-width="16" fill="none" stroke-linecap="round"/>'
    out += dots(680, 500, 360, 220, 40, "#3e2217", r=6, seed=29)
    out += plate(1300, 960, 260, 150)
    out += ('<polygon points="1120,980 1440,890 1450,960 1130,1050" fill="#2e180f"/>'
            '<polygon points="1120,950 1440,860 1440,895 1120,985" fill="#5a3424"/>'
            '<polygon points="1120,920 1440,830 1440,865 1120,955" fill="#fbf7f0"/>'
            '<polygon points="1120,920 1440,830 1390,805 Z" fill="#ffffff"/>'
            '<path d="M1160 905 C 1220 880, 1270 900, 1330 860" stroke="#4a2a1c" stroke-width="10" fill="none"/>')
    return out


@scene(12)  # Spiced Pecan Pie
def pecan_pie():
    out = pie(680, 530, 430, 300, "#8a3f14", gap=False)
    for ring, (rx, ry, n) in enumerate(((330, 220, 16), (200, 130, 10), (70, 45, 4))):
        for i in range(n):
            t = i * 2 * math.pi / n + ring * 0.2
            out += pecan(680 + rx * math.cos(t), 515 + ry * math.sin(t), math.degrees(t) + 90, 0.95)
    out += dots(680, 515, 400, 270, 30, "#c46a2a", r=5, seed=12, opacity=0.6)
    sticks = "".join(f'<g transform="rotate(-25 1300 {950 + i * 40})"><rect x="1150" y="{930 + i * 44}" width="320" height="44" rx="22" fill="#9a5530"/>'
                     f'<rect x="1150" y="{940 + i * 44}" width="320" height="10" fill="#b8703f"/></g>' for i in range(2))
    return out + sticks


# ---- puddings and custards ---------------------------------------------------

def blintz(x, y, a, s=1.0):
    return (f'<g transform="translate({x} {y}) rotate({a}) scale({s})">'
            '<rect x="-170" y="-50" width="340" height="120" rx="40" fill="#cf9440"/>'
            '<rect x="-170" y="-70" width="340" height="120" rx="40" fill="#f0cf8a"/>'
            '<path d="M-150 -40 C -60 -70, 60 -10, 150 -40" stroke="#e2b367" stroke-width="10" fill="none"/>'
            '<ellipse cx="-60" cy="-20" rx="50" ry="16" fill="#d9a04f" opacity="0.7"/></g>')


@scene(45)  # Blintzes (Bette Galcik version)
def blintzes_bette():
    out = plate(760, 660, 600, 380)
    for x, y, a in ((660, 500, -8), (860, 600, -8), (620, 720, -8), (900, 800, -8)):
        out += blintz(x, y, a)
    out += ('<ellipse cx="1180" cy="520" rx="110" ry="60" fill="#f4efe6"/><ellipse cx="1180" cy="500" rx="80" ry="40" fill="#ffffff"/>'
            '<ellipse cx="1180" cy="480" rx="40" ry="22" fill="#ffffff"/>')
    return out + parsley(760, 620, 420, 260, 6, seed=45)


@scene(44)  # Blintzes (J Crozier version)
def blintzes_crozier():
    out = plate(760, 660, 600, 380)
    out = out.replace("#e9e1d6", "#b9cde0")
    for x, y, a in ((700, 540, 12), (720, 700, 12), (760, 860, 12)):
        out += blintz(x, y, a, 1.05)
    rng = random.Random(44)
    for _ in range(18):
        x, y = 720 + rng.uniform(-260, 260), 680 + rng.uniform(-160, 160)
        out += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="24" fill="#8c1028"/><circle cx="{x - 7:.0f}" cy="{y - 7:.0f}" r="7" fill="#d9475e"/>'
    out += '<path d="M480 600 C 600 640, 820 560, 980 660 C 900 720, 600 760, 480 600 Z" fill="#a8102a" opacity="0.6"/>'
    return out + dots(760, 660, 420, 260, 80, "#ffffff", r=4, seed=45, opacity=0.9)


@scene(11)  # Chocolate Mousse (Magazine)
def mousse_magazine():
    def glass(x, y):
        return (f'<ellipse cx="{x + 16}" cy="{y + 470}" rx="150" ry="40" fill="{SHADOW}"/>'
                f'<ellipse cx="{x}" cy="{y + 450}" rx="140" ry="36" fill="#dfe7ec"/>'
                f'<rect x="{x - 18}" y="{y + 250}" width="36" height="200" fill="#dfe7ec"/>'
                f'<path d="M{x - 200} {y} C {x - 200} {y + 200}, {x - 60} {y + 270}, {x} {y + 270} C {x + 60} {y + 270}, {x + 200} {y + 200}, {x + 200} {y} Z" fill="#e7eef2"/>'
                f'<path d="M{x - 186} {y + 40} C {x - 180} {y + 200}, {x - 60} {y + 255}, {x} {y + 255} C {x + 60} {y + 255}, {x + 180} {y + 200}, {x + 186} {y + 40} Z" fill="#4a2a1c"/>'
                f'<ellipse cx="{x}" cy="{y + 40}" rx="186" ry="44" fill="#5d3526"/>'
                f'<ellipse cx="{x}" cy="{y + 10}" rx="100" ry="40" fill="#fbf6ee"/><ellipse cx="{x}" cy="{y - 15}" rx="66" ry="30" fill="#ffffff"/>'
                f'<ellipse cx="{x}" cy="{y - 38}" rx="30" ry="18" fill="#ffffff"/>'
                + dots(x, y + 40, 140, 30, 14, "#2a160d", r=6, seed=x)
                + f'<rect x="{x - 170}" y="{y + 60}" width="16" height="150" rx="8" fill="#ffffff" opacity="0.5"/>')
    return glass(520, 380) + glass(1060, 440) + '<g fill="#3e2217"><rect x="230" y="960" width="120" height="70" rx="6"/><rect x="370" y="990" width="120" height="70" rx="6"/></g>'


@scene(51)  # Dirt Cake
def dirt_cake():
    cx, top = 760, 520
    out = (f'<ellipse cx="{cx + 30}" cy="{top + 470}" rx="300" ry="70" fill="{SHADOW}"/>'
           f'<path d="M{cx - 320} {top} L{cx - 230} {top + 450} A230 60 0 0 0 {cx + 230} {top + 450} L{cx + 320} {top} Z" fill="#c4643a"/>'
           f'<path d="M{cx + 100} {top + 60} L{cx + 120} {top + 470} A230 60 0 0 0 {cx + 230} {top + 450} L{cx + 320} {top} Z" fill="#a8502c"/>'
           f'<rect x="{cx - 350}" y="{top - 30}" width="700" height="110" rx="14" fill="#d4734a"/>'
           f'<ellipse cx="{cx}" cy="{top - 30}" rx="350" ry="80" fill="#d4734a"/><ellipse cx="{cx}" cy="{top - 30}" rx="310" ry="62" fill="#2a1a12"/>'
           + dots(cx, top - 40, 290, 50, 60, "#1a0f0a", r=12, seed=51) + dots(cx, top - 40, 290, 50, 20, "#f4ede2", r=6, seed=52))
    worm = (f'<path d="M{cx - 160} {top - 30} C {cx - 120} {top - 120}, {cx - 40} {top - 20}, {cx} {top - 90}" stroke="#f08a3a" stroke-width="34" fill="none" stroke-linecap="round"/>'
            f'<path d="M{cx - 160} {top - 30} C {cx - 140} {top - 70}, {cx - 120} {top - 80}, {cx - 100} {top - 70}" stroke="#7fd06b" stroke-width="34" fill="none" stroke-linecap="round"/>')
    flower = (f'<path d="M{cx + 120} {top - 40} C {cx + 140} {top - 200}, {cx + 110} {top - 300}, {cx + 130} {top - 380}" stroke="#4e8a3e" stroke-width="16" fill="none"/>'
              + leaf(cx + 170, top - 180, -30, 1.2)
              + "".join(f'<ellipse cx="{cx + 130 + 60 * math.cos(math.radians(d)):.0f}" cy="{top - 400 + 60 * math.sin(math.radians(d)):.0f}" rx="44" ry="30" '
                        f'transform="rotate({d} {cx + 130 + 60 * math.cos(math.radians(d)):.0f} {top - 400 + 60 * math.sin(math.radians(d)):.0f})" fill="#f2a7bb"/>' for d in range(0, 360, 60))
              + f'<circle cx="{cx + 130}" cy="{top - 400}" r="34" fill="#f2c94c"/>')
    cookies = "".join(f'<circle cx="{x}" cy="{y}" r="60" fill="#1f1410"/><circle cx="{x}" cy="{y}" r="44" fill="#2a1c16"/>' for x, y in ((260, 960), (1270, 980)))
    return out + flower + worm + cookies


# ---- frostings ----------------------------------------------------------------

def peaks(cx, cy, rx, ry, color, shade, n=9, seed=1):
    rng = random.Random(seed)
    out = f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{color}"/>'
    for _ in range(n):
        x, y = cx + rng.uniform(-0.7, 0.7) * rx, cy + rng.uniform(-0.5, 0.5) * ry
        h = rng.uniform(50, 100)
        out += (f'<path d="M{x - 70:.0f} {y + 20:.0f} C {x - 40:.0f} {y - h * 0.3:.0f}, {x - 10:.0f} {y - h:.0f}, {x + 10:.0f} {y - h - 10:.0f} '
                f'C {x + 10:.0f} {y - h * 0.5:.0f}, {x + 50:.0f} {y - 10:.0f}, {x + 70:.0f} {y + 20:.0f} Z" fill="{color}"/>'
                f'<path d="M{x + 10:.0f} {y - h - 6:.0f} C {x + 14:.0f} {y - h * 0.5:.0f}, {x + 40:.0f} {y - 10:.0f}, {x + 64:.0f} {y + 16:.0f}" stroke="{shade}" stroke-width="8" fill="none"/>')
    return out


@scene(53)  # Fluffy White Frosting
def fluffy_frosting():
    out = bowl(720, 520, 470, 150, 380, color="#f4efe8", body="#7fa8c9", band="#9cc0dc")
    out += peaks(720, 500, 400, 120, "#ffffff", "#e9e3da", n=11, seed=53)
    return out + whisk(1180, 560, 35)


@scene(23)  # Icing
def icing():
    out = board(160, 640, 860, 400, fill="#efe6d6", line="#e2d6c2")
    for x, y in ((300, 820), (460, 860), (620, 820), (780, 860), (380, 960), (700, 960)):
        out += (f'<ellipse cx="{x}" cy="{y}" rx="60" ry="30" fill="#e9e3da"/>'
                f'<ellipse cx="{x}" cy="{y - 18}" rx="48" ry="24" fill="#ffffff"/><ellipse cx="{x}" cy="{y - 36}" rx="30" ry="16" fill="#ffffff"/>'
                f'<path d="M{x} {y - 52} l6 -14" stroke="#ffffff" stroke-width="10" stroke-linecap="round"/>')
    bag = ('<g transform="rotate(-30 1180 520)">'
           '<path d="M1040 260 L1320 260 L1200 640 L1160 640 Z" fill="#f4efe8"/><path d="M1040 260 L1320 260 L1300 320 L1060 320 Z" fill="#e3d8c8"/>'
           '<path d="M1160 640 L1200 640 L1192 700 L1168 700 Z" fill="#c7ccd1"/><path d="M1080 340 L1280 340 L1210 560 L1150 560 Z" fill="#ffffff"/></g>')
    out += bowl(1240, 860, 220, 70, 200, color="#f4efe8", body="#e8b4b4")
    out += peaks(1240, 850, 180, 54, "#ffffff", "#ece6dc", n=3, seed=23)
    return out + bag


@scene(36)  # Marshmallow Frosting
def marshmallow_frosting():
    out = bowl(680, 560, 460, 150, 360, color="#f4efe8", body="#f2b8c6", band="#f8d3dc")
    out += f'<ellipse cx="680" cy="545" rx="400" ry="115" fill="#fbf4ea"/>'
    out += f'<path d="M380 540 C 480 480, 600 600, 700 520 C 800 450, 900 590, 980 530" stroke="#efe2d0" stroke-width="16" fill="none" stroke-linecap="round"/>'
    out += spatula(940, 470, 40)

    def mallow(x, y, a=0):
        return (f'<g transform="translate({x} {y}) rotate({a})"><rect x="-46" y="-30" width="92" height="74" rx="24" fill="#e6ded2"/>'
                '<rect x="-46" y="-44" width="92" height="70" rx="24" fill="#fffbf4"/><ellipse cx="0" cy="-36" rx="40" ry="14" fill="#ffffff"/></g>')
    return out + mallow(1260, 900) + mallow(1390, 980, 20) + mallow(1200, 1040, -15) + mallow(260, 1030, 10)


# ---- mains ---------------------------------------------------------------------

@scene(6)  # Apple Cider-Brined Turkey with Savory Herb Gravy
def turkey():
    out = (shadow(760, 640, 640, 360) + '<ellipse cx="760" cy="640" rx="640" ry="360" fill="#f6f1ea"/>'
           '<ellipse cx="760" cy="640" rx="560" ry="300" fill="#e9e1d6"/>')
    out += "".join(leaf(760 + 480 * math.cos(t), 640 + 250 * math.sin(t), math.degrees(t) + 90, 1.0) for t in (i * 2 * math.pi / 14 for i in range(14)))
    for t in (0.3, 1.6, 2.9, 4.3, 5.5):
        out += lemon_slice(760 + 440 * math.cos(t), 640 + 230 * math.sin(t), 52).replace("#e8c93a", "#e8892a").replace("#f7e27a", "#f6b04f").replace("#ecd055", "#e89a3a")
    out += ('<ellipse cx="760" cy="640" rx="360" ry="230" fill="#9a5226"/>'
            '<ellipse cx="760" cy="610" rx="340" ry="205" fill="#c27a3a"/>'
            '<ellipse cx="740" cy="560" rx="230" ry="120" fill="#d99550"/>'
            '<ellipse cx="700" cy="520" rx="110" ry="50" fill="#e8b070"/>'
            '<path d="M760 420 L760 800" stroke="#a8622a" stroke-width="8"/>')
    for side in (-1, 1):
        x = 760 + side * 300
        out += (f'<ellipse cx="{x}" cy="760" rx="120" ry="80" fill="#b06a30" transform="rotate({side * -25} {x} 760)"/>'
                f'<ellipse cx="{x + side * 20}" cy="740" rx="90" ry="58" fill="#c98444" transform="rotate({side * -25} {x} 760)"/>'
                f'<rect x="{x + side * 60 - 18}" y="820" width="36" height="70" rx="12" fill="#f3e6cc" transform="rotate({side * -25} {x} 760)"/>'
                f'<circle cx="{x + side * 60 - 10}" cy="890" r="20" fill="#fbf3e2" transform="rotate({side * -25} {x} 760)"/>'
                f'<circle cx="{x + side * 60 + 10}" cy="890" r="20" fill="#fbf3e2" transform="rotate({side * -25} {x} 760)"/>')
    gravy = (f'<ellipse cx="1390" cy="1050" rx="170" ry="60" fill="{SHADOW}"/>'
             '<path d="M1240 980 C 1240 1060, 1520 1060, 1520 980 Z" fill="#f6f1ea"/>'
             '<ellipse cx="1380" cy="980" rx="140" ry="44" fill="#f6f1ea"/><ellipse cx="1380" cy="980" rx="118" ry="34" fill="#8a4a1e"/>'
             '<path d="M1500 975 L1580 945 L1510 1000 Z" fill="#f6f1ea"/>')
    return out + gravy


@scene(66)  # Chicken & Rice
def chicken_rice():
    dish = ('<rect x="222" y="322" width="1160" height="660" rx="90" fill="' + SHADOW + '"/>'
            '<rect x="200" y="290" width="1160" height="660" rx="90" fill="#f4efe8"/>'
            '<rect x="120" y="560" width="120" height="120" rx="40" fill="#f4efe8"/><rect x="1320" y="560" width="120" height="120" rx="40" fill="#f4efe8"/>'
            '<rect x="250" y="340" width="1060" height="560" rx="70" fill="#ddd4c7"/>'
            '<rect x="270" y="360" width="1020" height="520" rx="60" fill="#efe0bd"/>')

    def grain(x, y, a, r):
        return f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="16" ry="7" fill="#fbf6ea" transform="rotate({a:.0f} {x:.0f} {y:.0f})"/>'

    def chunk(x, y, a, r):
        return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><path d="M-40 -20 L30 -30 L44 18 L-30 30 Z" fill="#d9b27a"/>'
                '<path d="M-34 -14 L24 -22 L34 10 L-24 20 Z" fill="#f0d6a6"/></g>')
    return dish + bits(780, 620, 470, 230, 260, grain, seed=66) + bits(780, 620, 440, 220, 20, chunk, seed=67) + parsley(780, 620, 440, 220, 14, seed=68)


@scene(37)  # Chicken Cordon Bleu
def cordon_bleu():
    out = plate(760, 680, 600, 380)

    def roll(x, y, cut):
        if not cut:
            return (f'<rect x="{x - 210}" y="{y - 60}" width="420" height="170" rx="85" fill="#a8622a"/>'
                    f'<rect x="{x - 210}" y="{y - 80}" width="420" height="160" rx="80" fill="#cf8a42"/>'
                    + dots(x, y - 10, 180, 50, 30, "#e2a660", r=7, seed=x) + dots(x, y - 10, 180, 50, 12, "#b8482a", r=4, seed=x + 1))
        return (f'<ellipse cx="{x}" cy="{y}" rx="110" ry="100" fill="#cf8a42"/><ellipse cx="{x}" cy="{y}" rx="92" ry="84" fill="#fbf1e0"/>'
                f'<path d="M{x - 70} {y} C {x - 70} {y - 60}, {x + 60} {y - 60}, {x + 60} {y} C {x + 60} {y + 40}, {x - 30} {y + 40}, {x - 30} {y}" stroke="#e8909a" stroke-width="20" fill="none"/>'
                f'<path d="M{x - 50} {y} C {x - 50} {y - 36}, {x + 36} {y - 36}, {x + 36} {y}" stroke="#f6d36b" stroke-width="14" fill="none"/>')
    out += roll(620, 520, False) + roll(1000, 700, True) + roll(780, 760, True) + roll(560, 760, False).replace("#cf8a42", "#c98444")
    return out + parsley(760, 640, 400, 240, 8, seed=37)


@scene(42)  # Hard To Believe Brisket
def brisket():
    out = board(140, 300, 1320, 720)
    out += '<path d="M260 650 C 300 520, 820 480, 1000 560 L1000 760 C 820 820, 300 840, 260 760 Z" fill="#7a2f1a"/>'
    out += '<path d="M280 650 C 320 540, 800 510, 980 580 L980 620 C 800 560, 340 580, 280 680 Z" fill="#9a4426"/>'
    for i in range(6):
        x = 1000 + i * 70
        out += (f'<g transform="rotate(8 {x} 660)"><rect x="{x}" y="520" width="90" height="280" rx="24" fill="#5a2212"/>'
                f'<rect x="{x + 10}" y="532" width="70" height="256" rx="18" fill="#b86a50"/>'
                f'<g stroke="#a45a40" stroke-width="5"><line x1="{x + 14}" y1="600" x2="{x + 76}" y2="610"/><line x1="{x + 14}" y1="700" x2="{x + 76}" y2="712"/></g></g>')
    out += '<path d="M300 800 C 500 860, 900 850, 1200 830 C 1300 840, 1350 880, 1200 900 C 900 930, 400 910, 300 800 Z" fill="#8a1f12" opacity="0.8"/>'
    out += dots(620, 620, 300, 80, 20, "#c25a2a", r=8, seed=42)
    return out


@scene(77)  # Homemade Shake and Bake Mixture
def shake_and_bake():
    out = '<rect x="182" y="292" width="900" height="720" rx="30" fill="' + SHADOW + '"/><rect x="160" y="260" width="900" height="720" rx="30" fill="#9aa0a6"/>'
    out += '<rect x="190" y="290" width="840" height="660" rx="20" fill="#7d848b"/>'

    def drum(x, y, a):
        return (f'<g transform="translate({x} {y}) rotate({a})">'
                '<path d="M-130 0 C -130 -90, 60 -80, 90 -20 L170 -10 L170 10 L90 20 C 60 80, -130 90, -130 0 Z" fill="#a8622a"/>'
                '<path d="M-118 -6 C -118 -76, 50 -66, 80 -18 L90 0 C 40 -30, -60 -40, -118 -6 Z" fill="#d9944a"/>'
                + dots(-30, 0, 90, 50, 18, "#e8b46a", r=6, seed=x)
                + '<circle cx="180" cy="-14" r="18" fill="#fbf3e2"/><circle cx="180" cy="14" r="18" fill="#fbf3e2"/></g>')
    out += drum(450, 440, 10) + drum(780, 480, -10) + drum(460, 700, -6) + drum(780, 760, 12)
    out += bowl(1290, 640, 230, 76, 240, color="#f4efe8", body="#5b7fa6")
    out += f'<ellipse cx="1290" cy="636" rx="200" ry="62" fill="#e0a85a"/>' + dots(1290, 630, 180, 50, 60, "#b8732f", r=6, seed=77) + dots(1290, 630, 180, 50, 30, "#c2421e", r=4, seed=78)
    return out + dots(1300, 1020, 160, 50, 30, "#e0a85a", r=6, seed=79)


@scene(79)  # Sous Vide Times
def sous_vide():
    out = pot(700, 380, 450, 140, 480, color="#c7ccd1", rimc="#9aa0a6")
    out = out.replace('fill="#3a2a22"', 'fill="#8fc3dc"')
    out += '<ellipse cx="700" cy="380" rx="420" ry="122" fill="#a6d3e8" opacity="0.7"/>'
    out += '<g transform="rotate(-10 700 400)"><rect x="520" y="330" width="320" height="110" rx="20" fill="#e8f2f6" opacity="0.8"/><rect x="540" y="345" width="280" height="80" rx="16" fill="#b55b4a"/></g>'
    out += dots(700, 380, 360, 90, 16, "#ffffff", r=6, seed=79, opacity=0.8)
    out += ('<rect x="1030" y="120" width="110" height="520" rx="40" fill="#2f2f2f"/>'
            '<rect x="1046" y="160" width="78" height="120" rx="14" fill="#5fa8e0"/>'
            '<text x="1085" y="235" font-family="Helvetica, Arial, sans-serif" font-size="44" font-weight="bold" fill="#ffffff" text-anchor="middle">57°</text>'
            '<rect x="1010" y="360" width="150" height="40" rx="10" fill="#555"/>'
            '<circle cx="1085" cy="320" r="18" fill="#6fcf97"/>')
    return out + leaf(240, 960, 20, 1.2) + leaf(320, 1000, -30, 1.0)


def cutlet(x, y, a, s=1.0, crust="#c98444", light="#e2a660"):
    return (f'<g transform="translate({x} {y}) rotate({a}) scale({s})">'
            '<path d="M-240 0 C -240 -130, -60 -150, 60 -120 C 200 -90, 260 -40, 250 30 C 240 120, 60 150, -80 130 C -200 110, -240 70, -240 0 Z" fill="#a8622a"/>'
            f'<path d="M-225 -10 C -225 -120, -60 -138, 60 -108 C 190 -80, 240 -40, 232 20 C 220 100, 60 128, -80 112 C -190 94, -225 60, -225 -10 Z" fill="{crust}"/>'
            + dots(0, -10, 200, 100, 50, light, r=7, seed=int(x)) + '</g>')


@scene(70)  # Veal
def veal():
    out = (shadow(700, 600, 500, 340) + '<rect x="1150" y="555" width="380" height="80" rx="40" fill="#2b2624"/>'
           '<ellipse cx="700" cy="600" rx="500" ry="340" fill="#2b2624"/><ellipse cx="700" cy="592" rx="460" ry="305" fill="#3d3633"/>'
           '<ellipse cx="700" cy="600" rx="430" ry="285" fill="#b5873a" opacity="0.5"/>')
    out += cutlet(560, 520, -10, 0.75) + cutlet(850, 560, 15, 0.75, crust="#d0904a") + cutlet(660, 740, 5, 0.7)
    out += lemon_wedge(1000, 760, -20, 0.8) + parsley(700, 600, 380, 240, 10, seed=70)
    return out + lemon_slice(1350, 960, 70) + lemon_wedge(1220, 1020, 30)


@scene(71)  # Wienerschnitzel
def schnitzel():
    out = plate(760, 660, 620, 400)
    out += cutlet(700, 640, -6, 1.45, crust="#d9944a", light="#eab56e")
    out += lemon_slice(1020, 520, 70) + lemon_slice(1120, 600, 64)
    out += leaf(480, 820, 30, 0.8) + leaf(530, 850, -10, 0.7) + leaf(500, 870, 60, 0.6)
    return out


# ---- pastas ----------------------------------------------------------------------

@scene(68)  # Alfredo Sauce
def alfredo():
    out = bowl(760, 560, 520, 210, 330, color="#f4efe8", body="#2f5d8a", band="#4a7bab", inside="#f3e6c8")
    out += strands(760, 540, 440, 170, 60, "#f6dc93", "#e3c06c", width=22, seed=68, length=220)
    out += '<path d="M480 520 C 560 470, 700 600, 820 520 C 920 460, 1000 580, 1040 520" stroke="#fffaf0" stroke-width="40" fill="none" stroke-linecap="round" opacity="0.85"/>'
    out += dots(760, 540, 400, 150, 50, "#ffffff", r=6, seed=69) + parsley(760, 540, 380, 140, 12, seed=70)
    cheese = ('<polygon points="1240,940 1460,880 1480,1000 1260,1060" fill="#f6dc80"/>'
              '<polygon points="1240,940 1460,880 1430,850 1220,905" fill="#fbe9a8"/>'
              + dots(1350, 960, 80, 40, 8, "#e5c35c", r=8, seed=71))
    return out + cheese + '<g fill="#fbf3e2"><ellipse cx="240" cy="980" rx="40" ry="30"/><ellipse cx="300" cy="1010" rx="36" ry="28"/></g>'


@scene(41)  # Fettuccine Carbonara
def fettuccine_carbonara():
    out = plate(760, 660, 600, 380)
    out += strands(760, 640, 380, 230, 70, "#f2d27a", "#d9b257", width=22, seed=41, length=260)

    def bacon(x, y, a, r):
        return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><rect x="-30" y="-14" width="60" height="28" rx="8" fill="#a8322a"/>'
                '<rect x="-30" y="-4" width="60" height="8" fill="#f2c9a8"/></g>')
    out += bits(760, 620, 330, 190, 22, bacon, seed=42)
    out += dots(760, 620, 340, 200, 70, "#2a2a2a", r=3, seed=43) + dots(760, 620, 330, 190, 40, "#fff8e0", r=6, seed=44)
    return out + parsley(760, 620, 320, 180, 8, seed=45) + '<circle cx="1330" cy="330" r="90" fill="#8a9096"/><circle cx="1330" cy="320" r="80" fill="#d7dadd"/>' + dots(1330, 320, 60, 60, 25, "#2a2a2a", r=5, seed=46)


@scene(67)  # Pasta Carbonara (fun 3D shapes)
def pasta_carbonara():
    out = bowl(740, 540, 500, 200, 330, color="#f4efe8", body="#d9534a", band="#f08a7f", inside="#f3e3b8")

    def rotini(x, y, a, r):
        return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})">'
                '<rect x="-46" y="-16" width="92" height="32" rx="14" fill="#e2b85c"/>'
                + "".join(f'<path d="M{-40 + i * 20} -16 L{-26 + i * 20} 16" stroke="#c89a3c" stroke-width="7"/>' for i in range(5)) + '</g>')
    out += bits(740, 520, 420, 160, 70, rotini, seed=67)
    out += dots(740, 520, 400, 150, 60, "#fffaea", r=5, seed=68)
    shaker = (f'<ellipse cx="1340" cy="930" rx="110" ry="30" fill="{SHADOW}"/>'
              + cylinder(1330, 560, 900, 100, 30, "#f0e9dd", "#e05f5f", side_dark="#d2cabb")
              + '<rect x="1230" y="660" width="200" height="140" fill="#2f7a46"/>'
              '<text x="1330" y="748" font-family="Helvetica, Arial, sans-serif" font-size="46" font-weight="bold" fill="#ffffff" text-anchor="middle">PARM</text>'
              + dots(1330, 560, 60, 14, 8, "#9c2f2f", r=6, seed=69))
    return out + shaker


@scene(69)  # Ravoli Recipe
def ravioli():
    out = board(140, 300, 1320, 720)

    def rav(x, y):
        teeth = "".join(f'<circle cx="{x + i * 26}" cy="{y}" r="9"/><circle cx="{x + i * 26}" cy="{y + 156}" r="9"/>'
                        f'<circle cx="{x}" cy="{y + i * 26}" r="9"/><circle cx="{x + 156}" cy="{y + i * 26}" r="9"/>' for i in range(7))
        return (f'<rect x="{x + 6}" y="{y + 12}" width="156" height="156" rx="10" fill="#b57f50"/>'
                f'<g fill="#e9c98a">{teeth}</g><rect x="{x}" y="{y}" width="156" height="156" rx="10" fill="#f2d79e"/>'
                f'<ellipse cx="{x + 78}" cy="{y + 74}" rx="52" ry="46" fill="#f8e4b8"/><ellipse cx="{x + 66}" cy="{y + 60}" rx="18" ry="10" fill="#fff4d6"/>')
    for r in range(3):
        for c in range(5):
            out += rav(260 + c * 200, 380 + r * 200)
    out += flour(780, 640, 560, 280)
    return out + rolling_pin(800, 1100, -3, 760)


# ---- salads ------------------------------------------------------------------------

@scene(9)  # Caesar Salad
def caesar():
    out = bowl(740, 540, 540, 210, 320, color="#f4efe8", body="#c9a46a", band="#b48c50", inside="#5e9a42")

    def romaine(x, y, a, r):
        return leaf(x, y, a, r.uniform(1.6, 2.2), c1="#5e9a42" if r.random() < 0.5 else "#7cb85a", c2="#a8d47e")
    out += bits(740, 500, 440, 160, 40, romaine, seed=9)

    def crouton(x, y, a, r):
        return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><rect x="-26" y="-22" width="52" height="48" rx="10" fill="#b8732f"/>'
                '<rect x="-24" y="-24" width="48" height="40" rx="10" fill="#e2ac6a"/></g>')

    def shaving(x, y, a, r):
        return f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><path d="M-36 -8 L34 -14 L30 12 L-30 10 Z" fill="#fbf0c8"/></g>'
    out += bits(740, 490, 380, 140, 14, crouton, seed=10) + bits(740, 490, 380, 140, 16, shaving, seed=11)
    out += dots(740, 490, 380, 140, 40, "#2a2a2a", r=3, seed=12)
    return out + lemon_wedge(1350, 960, -10, 1.1) + lemon_wedge(1200, 1020, 40, 0.9)


# ---- side dishes ---------------------------------------------------------------------

def blobs(cx, cy, rx, ry, n, edge, fill, hi, size=(40, 60), seed=1):
    def blob(x, y, a, r):
        w, h = r.uniform(*size), r.uniform(size[0] * 0.6, size[1] * 0.7)
        return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><ellipse cx="0" cy="6" rx="{w:.0f}" ry="{h:.0f}" fill="{edge}"/>'
                f'<ellipse cx="0" cy="0" rx="{w:.0f}" ry="{h:.0f}" fill="{fill}"/><ellipse cx="{-w * 0.3:.0f}" cy="{-h * 0.3:.0f}" rx="{w * 0.3:.0f}" ry="{h * 0.25:.0f}" fill="{hi}"/></g>')
    return bits(cx, cy, rx, ry, n, blob, seed=seed)


@scene(28)  # Dumplings
def dumplings():
    out = bowl(760, 540, 520, 200, 330, color="#f4efe8", body="#5b8a6a", band="#7fae8c", inside="#e9c46a")
    out += blobs(760, 520, 420, 150, 55, "#d9a84a", "#f2d68a", "#fbecc0", size=(36, 56), seed=28)
    out += butter(780, 470, 0.8) + parsley(760, 520, 400, 140, 14, seed=29)
    return out + napkin(1200, 820, 300, 220, angle=12, stripe="#5b8a6a")


@scene(81)  # Mashed Potatoes
def mashed():
    out = bowl(760, 560, 520, 200, 330, color="#f4efe8", body="#e8d9b8", band="#d6c094", inside="#fbf3e2")
    out += ('<path d="M320 560 C 360 380, 560 300, 760 300 C 960 300, 1160 380, 1200 560 C 1000 640, 520 640, 320 560 Z" fill="#fbf3e2"/>'
            '<path d="M420 520 C 520 440, 640 480, 700 420 C 760 370, 880 400, 960 460 C 1020 500, 1100 500, 1120 540" stroke="#efe2c8" stroke-width="16" fill="none" stroke-linecap="round"/>'
            '<path d="M520 400 C 600 360, 700 380, 760 340" stroke="#efe2c8" stroke-width="14" fill="none" stroke-linecap="round"/>')
    out += '<path d="M690 340 C 700 400, 840 410, 860 350 C 840 420, 780 450, 720 430 Z" fill="#f2d16a" opacity="0.9"/>' + butter(770, 330, 0.8)
    out += dots(760, 460, 380, 140, 40, "#3a3a3a", r=3, seed=81) + dots(760, 470, 340, 120, 20, "#f2c14c", r=6, seed=82)
    return out + parsley(760, 460, 300, 100, 6, seed=83)


@scene(1)  # Rice Pilaf
def rice_pilaf():
    out = bowl(760, 540, 520, 200, 330, color="#f4efe8", body="#b56b3a", band="#cf8a58", inside="#f0e2c0")

    def grain(x, y, a, r):
        return f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="17" ry="7" fill="{"#f2e2b8" if r.random() < 0.6 else "#e5cc92"}" transform="rotate({a:.0f} {x:.0f} {y:.0f})"/>'

    def pine(x, y, a, r):
        return f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="14" ry="9" fill="#f6e2a8" stroke="#d9b46a" stroke-width="3" transform="rotate({a:.0f} {x:.0f} {y:.0f})"/>'
    out += bits(760, 520, 450, 170, 400, grain, seed=1) + bits(760, 510, 420, 150, 40, pine, seed=2)
    out += dots(760, 510, 420, 150, 30, "#d9a35a", r=6, seed=3) + parsley(760, 510, 400, 140, 12, seed=4)
    return out + leaf(1320, 980, 20, 1.1) + leaf(1400, 1020, -20, 0.9)


@scene(75)  # Sesame Green Beans
def green_beans():
    out = plate(760, 660, 600, 380)

    def bean(x, y, a, r):
        return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><rect x="-90" y="-14" width="180" height="32" rx="16" fill="#3f7a2e"/>'
                '<rect x="-90" y="-18" width="180" height="28" rx="14" fill="#5fa043"/><rect x="-80" y="-12" width="140" height="8" rx="4" fill="#86c066"/></g>')
    out += bits(760, 640, 380, 230, 55, bean, seed=75)
    out += dots(760, 630, 380, 230, 120, "#f6ecd0", r=4, seed=76) + dots(760, 630, 380, 230, 30, "#2a2a2a", r=3, seed=77)
    return out


def spaetzle(cx, cy, rx, ry, n, seed):
    def noodle(x, y, a, r):
        return (f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})">'
                '<path d="M-34 0 C -20 -18, 0 14, 14 -6 C 22 -14, 30 -6, 34 0" stroke="#d9a84a" stroke-width="20" fill="none" stroke-linecap="round"/>'
                '<path d="M-34 -4 C -20 -22, 0 10, 14 -10 C 22 -18, 30 -10, 34 -4" stroke="#f2d27a" stroke-width="14" fill="none" stroke-linecap="round"/></g>')
    return bits(cx, cy, rx, ry, n, noodle, seed=seed)


@scene(72)  # Spatzel
def spatzel():
    out = (shadow(700, 600, 500, 340) + '<rect x="1150" y="555" width="380" height="80" rx="40" fill="#2b2624"/>'
           '<ellipse cx="700" cy="600" rx="500" ry="340" fill="#2b2624"/><ellipse cx="700" cy="592" rx="460" ry="305" fill="#3d3633"/>')
    out += spaetzle(700, 590, 400, 250, 140, seed=72)
    out += dots(700, 590, 380, 240, 30, "#b8732f", r=7, seed=73) + parsley(700, 590, 380, 230, 14, seed=74)
    return out


@scene(46)  # Spatzle
def spatzle():
    out = bowl(760, 560, 520, 200, 330, color="#f4efe8", body="#7a8fa6", band="#9db0c4", inside="#f2d27a")
    out += spaetzle(760, 540, 430, 160, 110, seed=46)
    out += butter(760, 490, 0.7) + dots(760, 540, 400, 150, 30, "#3a3a3a", r=3, seed=47)
    grater = ('<g transform="rotate(-20 1300 960)"><rect x="1100" y="920" width="420" height="80" rx="20" fill="#c7ccd1"/>'
              + "".join(f'<circle cx="{1140 + i * 34}" cy="960" r="9" fill="#8a9096"/>' for i in range(11)) + '</g>')
    return out + grater


@scene(80)  # Twice Baked Potatoes
def twice_baked():
    out = '<rect x="182" y="312" width="1240" height="700" rx="30" fill="' + SHADOW + '"/><rect x="160" y="280" width="1240" height="700" rx="30" fill="#9aa0a6"/>'
    out += '<rect x="190" y="310" width="1180" height="640" rx="20" fill="#efe6d6"/>'

    def potato(x, y, a):
        return (f'<g transform="translate({x} {y}) rotate({a})">'
                '<ellipse cx="0" cy="30" rx="230" ry="120" fill="#7a4a2a"/><ellipse cx="0" cy="10" rx="220" ry="110" fill="#9a6038"/>'
                '<ellipse cx="0" cy="0" rx="190" ry="88" fill="#fbf0d4"/>'
                '<path d="M-140 -10 C -90 -70, -20 30, 30 -40 C 70 -80, 120 -20, 150 -20" stroke="#efe0b8" stroke-width="22" fill="none" stroke-linecap="round"/>'
                '<path d="M-120 10 C -60 -40, 20 50, 120 0" stroke="#f2b84a" stroke-width="18" fill="none" stroke-linecap="round" opacity="0.9"/>'
                + dots(0, -10, 150, 60, 14, "#5e9a42", r=6, seed=x) + '</g>')
    out += potato(470, 480, -6) + potato(1060, 500, 6) + potato(480, 790, 4) + potato(1070, 800, -4)
    return out + bowl(1430, 1060, 120, 40, 90, color="#f4efe8").replace('fill="#e2dacd"', 'fill="#fffaf0"')


# ---- soups -----------------------------------------------------------------------------

def soup_bits(cx, cy, rx, ry, seed):
    def carrot(x, y, a, r):
        return f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="26" ry="18" fill="#e8762a"/><ellipse cx="{x:.0f}" cy="{y:.0f}" rx="14" ry="9" fill="#f29a52"/>'

    def celery(x, y, a, r):
        return f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><path d="M-22 -10 L22 -10 L18 12 L-18 12 Z" fill="#9cc96a"/></g>'
    return bits(cx, cy, rx, ry, 20, carrot, seed=seed) + bits(cx, cy, rx, ry, 14, celery, seed=seed + 1)


@scene(40)  # Chicken Soup
def chicken_soup():
    out = pot(720, 420, 480, 150, 440)
    out += '<ellipse cx="720" cy="425" rx="452" ry="134" fill="#e8b84a"/>'
    out += soup_bits(720, 425, 400, 110, seed=40)
    out += strands(720, 425, 380, 100, 14, "#f6dc93", "#e3c06c", width=12, seed=41, length=120)

    def chunk(x, y, a, r):
        return f'<g transform="translate({x:.0f} {y:.0f}) rotate({a:.0f})"><path d="M-30 -16 L24 -22 L32 14 L-22 20 Z" fill="#f0d6a6"/></g>'
    out += bits(720, 425, 380, 100, 10, chunk, seed=42) + parsley(720, 425, 380, 100, 14, seed=43)
    return out + ladle(1050, 430, 40) + '<ellipse cx="1000" cy="400" rx="80" ry="34" fill="#c7ccd1"/>'


@scene(78)  # Matzo Balls
def matzo_balls():
    out = bowl(760, 540, 520, 200, 330, color="#f4efe8", body="#3f6f9a", band="#6a95bd", inside="#e8b84a")
    out += soup_bits(760, 540, 430, 160, seed=78)

    def ball(x, y):
        return (f'<ellipse cx="{x}" cy="{y + 50}" rx="120" ry="40" fill="#c99a3a"/>'
                f'<circle cx="{x}" cy="{y}" r="120" fill="#e6cf9a"/><circle cx="{x - 14}" cy="{y - 14}" r="100" fill="#f2e0b0"/>'
                + dots(x, y, 80, 80, 20, "#d9bd80", r=6, seed=x))
    out += ball(600, 520) + ball(900, 500) + ball(760, 600)
    dill = "".join(f'<path d="M{x} {y} l{dx} {dy}" stroke="#4e8a3e" stroke-width="5" stroke-linecap="round"/>'
                   for x, y, dx, dy in ((700, 420, 20, -30), (720, 400, -20, -20), (860, 640, 30, -10), (880, 620, 10, -30), (520, 640, -20, -20)))
    return out + dill + parsley(760, 540, 400, 150, 8, seed=79)


if __name__ == "__main__":
    scenes.main()
