"""Plain-text backup export (SPEC.md section 7) — a portable, human-readable
dump of every recipe, plus a parser so the round-trip can be tested against
the database it came from."""
import re
from datetime import datetime
from html.parser import HTMLParser

APP_NAME = "Recipes"
SEPARATOR = "=" * 50


def _fmt_num(value):
    if value is None:
        return ""
    if float(value) == int(value):
        return str(int(value))
    return str(value)


def _fmt_note_date(iso_timestamp):
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso_timestamp or ""


class _HtmlToText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paragraphs = []
        self._buf = []
        self._list_stack = []  # list of ['ul'] or ['ol', counter]
        self._in_li = False

    def _flush_para(self):
        text = "".join(self._buf).strip()
        if text:
            self.paragraphs.append(text)
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self._flush_para()
        elif tag == "br":
            self._buf.append("\n")
        elif tag == "strong":
            self._buf.append("**")
        elif tag == "em":
            self._buf.append("*")
        elif tag == "ul":
            self._list_stack.append(["ul", 0])
        elif tag == "ol":
            self._list_stack.append(["ol", 0])
        elif tag == "li":
            self._in_li = True
            if self._list_stack:
                self._list_stack[-1][1] += 1
                kind, n = self._list_stack[-1]
                prefix = "- " if kind == "ul" else f"{n}. "
            else:
                prefix = "- "
            if self._buf:
                self._flush_para()
            self._buf.append(prefix)

    def handle_endtag(self, tag):
        if tag == "p":
            self._flush_para()
        elif tag in ("strong", "em"):
            marker = "**" if tag == "strong" else "*"
            self._buf.append(marker)
        elif tag == "li":
            self._flush_para()
            self._in_li = False
        elif tag in ("ul", "ol"):
            if self._list_stack:
                self._list_stack.pop()

    def handle_data(self, data):
        self._buf.append(data)

    def get_text(self):
        self._flush_para()
        return "\n\n".join(self.paragraphs)


def html_to_text(html):
    parser = _HtmlToText()
    parser.feed(html or "")
    return parser.get_text()


def _text_to_html_fallback(text):
    """Best-effort reverse of html_to_text, used only by tests to sanity
    check round-tripping -- not used by the app itself."""
    paragraphs = text.split("\n\n")
    out = []
    for para in paragraphs:
        if para.startswith("- "):
            items = [line[2:] for line in para.split("\n")]
            out.append("<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>")
        elif re.match(r"^\d+\. ", para):
            items = [re.sub(r"^\d+\. ", "", line) for line in para.split("\n")]
            out.append("<ol>" + "".join(f"<li>{i}</li>" for i in items) + "</ol>")
        else:
            out.append(f"<p>{para}</p>")
    return "".join(out)


def _ingredient_line(ing):
    if ing["kind"] == "heading":
        return f"## {ing['raw_text']}"

    if ing["no_scale"]:
        return f"- {ing['raw_text']}   [no-scale]"

    if ing["is_split"] and ing["quantity"] is not None:
        parts = [f"qty={_fmt_num(ing['quantity'])}"]
        if ing["quantity_max"] is not None:
            parts.append(f"qty_max={_fmt_num(ing['quantity_max'])}")
        parts.append(f"unit={ing['unit'] or ''}")
        parts.append(f'item="{ing["item"] or ""}"')
        return f"- {ing['raw_text']}   [{' '.join(parts)}]"

    return f"- {ing['raw_text']}"


def _personal_summary(conn, recipe_id):
    """Everyone's own favorite / rating / last made, on one line:
    "a@x.com (favorite, 5 stars, made 2026-09-14); b@y.com (favorite)"."""
    rows = conn.execute(
        """SELECT u.email, ur.favorite, ur.rating, ur.last_made
           FROM user_recipes ur JOIN users u ON u.id = ur.user_id
           WHERE ur.recipe_id = ? ORDER BY u.id""",
        (recipe_id,),
    ).fetchall()
    people = []
    for r in rows:
        parts = []
        if r["favorite"]:
            parts.append("favorite")
        if r["rating"]:
            parts.append(f"{r['rating']} star{'s' if r['rating'] != 1 else ''}")
        if r["last_made"]:
            parts.append(f"made {r['last_made']}")
        if parts:
            people.append(f"{r['email']} ({', '.join(parts)})")
    return "; ".join(people)


def _recipe_block(conn, recipe):
    ingredients = conn.execute(
        "SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY position", (recipe["id"],)
    ).fetchall()
    notes = conn.execute(
        "SELECT * FROM notes WHERE recipe_id = ? ORDER BY created_at, id", (recipe["id"],)
    ).fetchall()

    category_name = recipe["category_name"] or ""
    origin = ""
    if recipe["source_pdf"]:
        origin = f"{recipe['source_pdf']} page {recipe['source_page']}"

    lines = [
        SEPARATOR,
        f"RECIPE: {recipe['title']}",
        f"ID: {recipe['id']}",
        f"CATEGORY: {category_name}",
        f"CONTRIBUTOR: {recipe['contributor'] or ''}",
        f"SOURCE: {recipe['source'] or ''}",
        f"SERVINGS: {recipe['servings'] or ''}",
        f"PREP TIME: {recipe['prep_time'] or ''}",
        f"COOK TIME: {recipe['cook_time'] or ''}",
        f"OWNER: {recipe['owner_email'] or ''}",
        f"PERSONAL: {_personal_summary(conn, recipe['id'])}",
        f"NEEDS REVIEW: {'yes' if recipe['needs_review'] else 'no'}",
        f"IMAGE FILE: {recipe['image_filename'] or ''}",
        f"SCAN FILE: {recipe['scan_filename'] or ''}",
        f"ORIGIN: {origin}",
        f"CREATED: {recipe['created_at']}",
        f"UPDATED: {recipe['updated_at']}",
        "",
        "INGREDIENTS:",
    ]
    for ing in ingredients:
        lines.append(_ingredient_line(ing))

    lines += ["", "INSTRUCTIONS:", html_to_text(recipe["instructions_html"])]

    lines += ["", "NOTES:"]
    for note in notes:
        lines.append(f"[{_fmt_note_date(note['created_at'])}] {note['body']}")

    lines.append("")
    return "\n".join(lines)


def build_backup_text(conn):
    recipes = conn.execute(
        """SELECT r.*, c.name AS category_name, u.email AS owner_email
           FROM recipes r
           LEFT JOIN categories c ON c.id = r.category_id
           LEFT JOIN users u ON u.id = r.owner_id
           ORDER BY COALESCE(c.name, '~'), r.title COLLATE NOCASE"""
    ).fetchall()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"{APP_NAME} backup — exported {now} — {len(recipes)} recipes"

    blocks = [_recipe_block(conn, r) for r in recipes]
    return header + "\n\n" + "\n".join(blocks)


# --- Parsing, for the round-trip test ---

_FIELD_RE = re.compile(r"^([A-Z ]+): (.*)$")


def parse_backup_text(text):
    """Returns (header, [recipe_dict, ...]) reconstructed from backup text."""
    parts = text.split(SEPARATOR)
    header = parts[0].strip()
    recipes = []

    for block in parts[1:]:
        block = block.strip("\n")
        if not block.strip():
            continue
        lines = block.split("\n")

        fields = {}
        i = 0
        while i < len(lines) and lines[i].strip() != "":
            m = _FIELD_RE.match(lines[i])
            if m:
                fields[m.group(1)] = m.group(2)
            i += 1

        # skip blank line
        i += 1
        assert lines[i] == "INGREDIENTS:"
        i += 1
        ingredients = []
        while i < len(lines) and lines[i].strip() != "":
            ingredients.append(_parse_ingredient_line(lines[i]))
            i += 1

        i += 1  # blank line
        assert lines[i] == "INSTRUCTIONS:"
        i += 1
        instr_lines = []
        while i < len(lines) and lines[i] != "NOTES:":
            instr_lines.append(lines[i])
            i += 1
        # Drop the single trailing blank line that separates instructions from "NOTES:"
        while instr_lines and instr_lines[-1] == "":
            instr_lines.pop()
        instructions_text = "\n".join(instr_lines)

        assert lines[i] == "NOTES:"
        i += 1
        notes = []
        while i < len(lines):
            if lines[i].strip():
                nm = re.match(r"^\[(.*?)\] (.*)$", lines[i])
                if nm:
                    notes.append({"date": nm.group(1), "body": nm.group(2)})
            i += 1

        recipes.append({
            "fields": fields,
            "ingredients": ingredients,
            "instructions_text": instructions_text,
            "notes": notes,
        })

    return header, recipes


_BRACKET_RE = re.compile(r"^- (.*?)   \[(.*)\]$")


def _parse_ingredient_line(line):
    if line.startswith("## "):
        return {"kind": "heading", "raw_text": line[3:]}

    m = _BRACKET_RE.match(line)
    if m:
        raw_text, bracket = m.group(1), m.group(2)
        if bracket == "no-scale":
            return {"kind": "item", "raw_text": raw_text, "no_scale": True}
        attrs = {}
        for key in ("qty", "qty_max", "unit"):
            am = re.search(rf"{key}=(\S*)", bracket)
            if am:
                attrs[key] = am.group(1)
        item_m = re.search(r'item="([^"]*)"', bracket)
        if item_m:
            attrs["item"] = item_m.group(1)
        return {"kind": "item", "raw_text": raw_text, "split": attrs}

    return {"kind": "item", "raw_text": line[2:] if line.startswith("- ") else line}
