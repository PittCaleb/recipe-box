"""Draws a placeholder picture for a new recipe that has no photo: Claude
writes a flat SVG illustration in the same style as the hand-drawn set in
scripts/placeholder-images/, rsvg-convert turns it into a JPEG, and it's
linked as the recipe's image with image_is_placeholder set, so a real photo
always replaces it. Runs in a background thread; failures only get logged."""
import io
import re
import subprocess
import threading
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

import anthropic
from PIL import Image

from app.db import get_connection
from app.images import delete_recipe_image, save_image_files
from app.models.recipes import set_placeholder_image

EXAMPLES_DIR = Path(__file__).parent / "placeholder_examples"
WIDTH, HEIGHT = 1600, 1200

# Tests turn this off so the job runs inline.
RUN_IN_BACKGROUND = True

SYSTEM_PROMPT = """You draw placeholder pictures for a family recipe website. Each recipe without a photo gets a flat, friendly illustration of the finished dish, and every picture must look like part of the same set as the examples below.

The style:
- An SVG with viewBox="0 0 1600 1200" width="1600" height="1200". It's shown as a 400x300 thumbnail, so the dish must be recognisable at that size: big simple shapes, not fine detail.
- Flat vector shapes in solid colours: no gradients, filters, blur or outlines around everything. Small accents (crust lines, crumbs, herbs, sugar dots) are drawn as extra shapes on top.
- Seen from the front and a little above, so round things are ellipses (height about 0.6-0.7 of their width) and upright things show their top as an ellipse.
- Always the same wooden table as the background, exactly as the examples start: a full-size rect filled #8c5a3c, then five gently curved grain lines in stroke #7a4c31, stroke-width 5, round caps.
- Shadows are the same shape as the thing they belong to, filled #6e4329, drawn underneath it and offset about 20 right and 30 down.
- Plates and bowls: rim #f6f1ea, inner #e9e1d6 (or a muted coloured bowl body). Wood boards #c69060. Warm, muted, natural food colours.
- Show the dish as it's served, in what it's usually served in (plate, bowl, skillet, baking pan, board, basket, cake stand, glass). Add a serving on a small side plate, or one or two props suggested by the ingredients (a butter pat, lemon wedges, herbs, cinnamon sticks, a jug of syrup) when it helps.
- Keep everything inside x 60-1540 and y 60-1140, with the main dish centred and filling about 60-75% of the width.
- No words, letters, numbers, labels, people, hands or faces anywhere.

Use only these elements: svg, g, rect, circle, ellipse, path, polygon, polyline, line. Use attributes such as fill, stroke, stroke-width, stroke-linecap, opacity, transform and the shape coordinates. No text, image, use, defs, style, script, foreignObject, links, url(...) references or anything loaded from elsewhere.

Reply with only the SVG, starting with <svg and ending with </svg>."""

ALLOWED_TAGS = {"svg", "g", "rect", "circle", "ellipse", "path", "polygon", "polyline", "line"}


class PlaceholderError(Exception):
    pass


def _examples_text():
    parts = []
    for path in sorted(EXAMPLES_DIR.glob("*.svg")):
        parts.append(f"<example recipe=\"{path.stem}\">\n{path.read_text().strip()}\n</example>")
    return "Examples from the set:\n\n" + "\n\n".join(parts)


def _plain_text(html, limit=800):
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def recipe_prompt(title, category, ingredients, instructions_html):
    lines = [f"Recipe: {title}"]
    if category:
        lines.append(f"Category: {category}")
    if ingredients:
        lines.append("Ingredients:\n" + "\n".join(f"- {i}" for i in ingredients))
    instructions = _plain_text(instructions_html)
    if instructions:
        lines.append(f"Instructions (for what the finished dish looks like): {instructions}")
    lines.append("Draw this recipe's placeholder picture.")
    return "\n\n".join(lines)


def extract_svg(text):
    match = re.search(r"<svg\b.*</svg>", text or "", re.DOTALL)
    if not match:
        raise PlaceholderError("The reply had no SVG in it.")
    return match.group(0)


def check_svg(svg):
    """Only plain shapes get through: rsvg-convert never sees anything that
    could load a file or a URL."""
    if "<!" in svg or "<?" in svg:
        raise PlaceholderError("SVG has a doctype, entity or processing instruction.")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise PlaceholderError(f"SVG doesn't parse: {exc}") from exc
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ALLOWED_TAGS:
            raise PlaceholderError(f"SVG uses <{tag}>.")
        for name, value in el.attrib.items():
            if "href" in name.rsplit("}", 1)[-1] or name.startswith("on") or "url(" in value:
                raise PlaceholderError(f"SVG has a {name} attribute that isn't allowed.")
    return svg


def draw_placeholder_svg(title, category, ingredients, instructions_html, api_key, model):
    client = anthropic.Anthropic(api_key=api_key)
    with client.beta.messages.stream(
        model=model,
        max_tokens=32000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "medium"},
        system=[
            {"type": "text", "text": SYSTEM_PROMPT},
            {"type": "text", "text": _examples_text(), "cache_control": {"type": "ephemeral"}},
        ],
        messages=[{"role": "user", "content": recipe_prompt(title, category, ingredients, instructions_html)}],
    ) as stream:
        message = stream.get_final_message()
    if message.stop_reason == "refusal":
        raise PlaceholderError("Claude declined to draw this one.")
    if message.stop_reason == "max_tokens":
        raise PlaceholderError("The drawing was cut off before it finished.")
    text = "".join(block.text for block in message.content if block.type == "text")
    return check_svg(extract_svg(text))


def render_svg(svg, images_dir, recipe_id):
    """SVG text -> the recipe's full-size and thumbnail JPEGs. Returns the
    main image filename."""
    result = subprocess.run(
        ["rsvg-convert", "-w", str(WIDTH), "-h", str(HEIGHT), "-f", "png"],
        input=svg.encode(), capture_output=True, timeout=60, check=False,
    )
    if result.returncode != 0:
        raise PlaceholderError(f"rsvg-convert failed: {result.stderr.decode(errors='replace').strip()}")
    with Image.open(io.BytesIO(result.stdout)) as im:
        return save_image_files(im.convert("RGB"), images_dir, recipe_id)


def make_placeholder(conn, cfg, recipe_id, replacing=None):
    """Draws and links a placeholder for one recipe. With `replacing` (the
    recipe's current picture) it replaces that; otherwise it only draws for a
    recipe with no picture. Nothing changes if the picture is different by the
    time the drawing is done. Returns the new filename, or None."""
    recipe = conn.execute(
        """SELECT r.title, r.instructions_html, r.image_filename, c.name AS category_name
           FROM recipes r LEFT JOIN categories c ON c.id = r.category_id WHERE r.id = ?""",
        (recipe_id,),
    ).fetchone()
    if recipe is None or recipe["image_filename"] != replacing:
        return None
    ingredients = [
        row["raw_text"] for row in conn.execute(
            "SELECT raw_text FROM ingredients WHERE recipe_id = ? ORDER BY position", (recipe_id,)
        )
    ]
    svg = draw_placeholder_svg(
        recipe["title"], recipe["category_name"], ingredients, recipe["instructions_html"],
        api_key=cfg.ANTHROPIC_API_KEY, model=cfg.PLACEHOLDER_MODEL,
    )
    filename = render_svg(svg, cfg.IMAGES_DIR, recipe_id)
    if not set_placeholder_image(conn, recipe_id, filename, replacing):
        delete_recipe_image(cfg.IMAGES_DIR, filename)
        return None
    if replacing and replacing != filename:
        delete_recipe_image(cfg.IMAGES_DIR, replacing)
    return filename


def start_placeholder_job(cfg, recipe_ids, replacing=None):
    """Draws placeholders for these recipes one after another (`replacing`
    is for redrawing one recipe's current picture). Does nothing without an
    API key. Returns True if a job was started."""
    recipe_ids = list(recipe_ids)
    if not cfg.ANTHROPIC_API_KEY or not recipe_ids:
        return False
    if RUN_IN_BACKGROUND:
        threading.Thread(target=_run_job, args=(cfg, recipe_ids, replacing), daemon=True).start()
    else:
        _run_job(cfg, recipe_ids, replacing)
    return True


def _run_job(cfg, recipe_ids, replacing):
    conn = get_connection(cfg.DB_PATH)
    try:
        for recipe_id in recipe_ids:
            try:
                make_placeholder(conn, cfg, recipe_id, replacing)
            except Exception:
                print(f"Couldn't draw a placeholder picture for recipe {recipe_id}:")
                traceback.print_exc()
    finally:
        conn.close()
