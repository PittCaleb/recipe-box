"""Suggests {quantity, quantity_max, unit, item} from an ingredient's raw text.

The raw text is never modified. When no quantity can be found at all (e.g.
"salt to taste"), quantity is None and the caller should suggest "Don't scale"
instead of showing a broken split.
"""
import re

UNICODE_FRACTIONS = {
    "¼": (1, 4), "½": (1, 2), "¾": (3, 4),
    "⅓": (1, 3), "⅔": (2, 3),
    "⅛": (1, 8), "⅜": (3, 8), "⅝": (5, 8), "⅞": (7, 8),
}
_UNICODE_FRACTION_CHARS = "".join(UNICODE_FRACTIONS)

_MIXED_UNICODE_RE = re.compile(rf"(\d+)\s*([{_UNICODE_FRACTION_CHARS}])")
_BARE_UNICODE_RE = re.compile(rf"[{_UNICODE_FRACTION_CHARS}]")
_MIXED_ASCII_RE = re.compile(r"(\d+)\s+(\d+)/(\d+)\b")
_SIMPLE_FRACTION_RE = re.compile(r"(\d+)/(\d+)\b")
_DECIMAL_RE = re.compile(r"\d+\.\d+")
_INTEGER_RE = re.compile(r"\d+\b")

# A unit word ends at whitespace, end-of-string, or light punctuation -- never
# require a \b word boundary right after an optional trailing period, since
# "." followed by a space has no word boundary between them (both non-word).
_END = r"\.?(?=\s|$|[,;:)])"


def _unit(core, case_sensitive=False):
    flags = 0 if case_sensitive else re.I
    return re.compile(f"(?:{core}){_END}", flags)


# (canonical unit key, compiled regex matched at the start of the remaining text)
# Order matters: more specific/longer word forms are tried before bare single
# letter abbreviations, so "Tbsp" matches tablespoon before the bare-"T" rule.
UNIT_PATTERNS = [
    ("fl_oz", _unit(r"fl\.?\s*oz|fluid\s+ounces?")),
    ("tbsp", _unit(r"tablespoons?|tbsps?|tbs")),
    ("tsp", _unit(r"teaspoons?|tsps?")),
    ("tbsp", _unit(r"T", case_sensitive=True)),  # capital T alone = tablespoon
    ("tsp", _unit(r"t", case_sensitive=True)),  # lowercase t alone = teaspoon
    ("oz", _unit(r"ounces?|oz")),
    ("lb", _unit(r"pounds?|lbs?|#")),
    ("cup", _unit(r"cups?|c")),
    ("pt", _unit(r"pints?|pt")),
    ("qt", _unit(r"quarts?|qt")),
    ("gal", _unit(r"gallons?|gal")),
    ("ml", _unit(r"milliliters?|millilitres?|ml")),
    ("l", _unit(r"liters?|litres?|l")),
    ("kg", _unit(r"kilograms?|kg")),
    ("g", _unit(r"grams?|g")),
    ("stick", _unit(r"sticks?")),
    ("can", _unit(r"cans?")),
    ("package", _unit(r"packages?|pkgs?")),
    ("clove", _unit(r"cloves?")),
    ("pinch", _unit(r"pinch(?:es)?")),
    ("dash", _unit(r"dash(?:es)?")),
]


def _take_leading_number(text):
    """Returns (value, remainder) for the number at the start of `text`,
    or (None, text) if it doesn't start with one."""
    stripped = text.lstrip()
    skipped = len(text) - len(stripped)

    m = _MIXED_UNICODE_RE.match(stripped)
    if m:
        whole = int(m.group(1))
        num, den = UNICODE_FRACTIONS[m.group(2)]
        return whole + num / den, text[skipped + m.end():]

    m = _BARE_UNICODE_RE.match(stripped)
    if m:
        num, den = UNICODE_FRACTIONS[m.group(0)]
        return num / den, text[skipped + m.end():]

    m = _MIXED_ASCII_RE.match(stripped)
    if m:
        value = int(m.group(1)) + int(m.group(2)) / int(m.group(3))
        return value, text[skipped + m.end():]

    m = _SIMPLE_FRACTION_RE.match(stripped)
    if m:
        value = int(m.group(1)) / int(m.group(2))
        return value, text[skipped + m.end():]

    m = _DECIMAL_RE.match(stripped)
    if m:
        return float(m.group(0)), text[skipped + m.end():]

    m = _INTEGER_RE.match(stripped)
    if m:
        return int(m.group(0)), text[skipped + m.end():]

    return None, text


def _take_range_max(text, first_value):
    """If `text` continues with "-N" or "to N", returns (max_value, remainder)."""
    stripped = text.lstrip()

    if stripped.startswith("-"):
        candidate = stripped[1:]
        value, remainder = _take_leading_number(candidate)
        if value is not None:
            return value, remainder

    if stripped[:3].lower() == "to " or stripped[:3].lower() == "to\t":
        candidate = stripped[3:]
        value, remainder = _take_leading_number(candidate)
        if value is not None:
            return value, remainder

    return None, text


def _take_unit(text):
    """Returns (canonical_unit, remainder) if `text` starts with a known unit word."""
    stripped = text.lstrip()
    for unit, pattern in UNIT_PATTERNS:
        m = pattern.match(stripped)
        if m:
            return unit, stripped[m.end():]
    return None, text


_PAREN_RE = re.compile(r"\(([^)]*)\)")


def parse_ingredient(raw_text):
    """Returns {"quantity", "quantity_max", "unit", "item"}.

    quantity is None when no leading number is found at all (e.g. "salt to
    taste") -- callers should suggest "Don't scale" in that situation.
    """
    text = (raw_text or "").strip()

    quantity, rest = _take_leading_number(text)
    if quantity is None:
        return {"quantity": None, "quantity_max": None, "unit": None, "item": None}

    quantity_max, rest = _take_range_max(rest, quantity)

    rest = rest.lstrip()
    paren_match = _PAREN_RE.match(rest)
    parenthetical = None
    after_paren = rest
    if paren_match:
        parenthetical = paren_match.group(0)
        after_paren = rest[paren_match.end():].lstrip()

    unit, remainder = _take_unit(after_paren)
    remainder = remainder.lstrip()

    if parenthetical:
        item = f"{parenthetical} {remainder}".strip()
    else:
        item = remainder.strip()

    if not item:
        item = None

    return {
        "quantity": quantity,
        "quantity_max": quantity_max,
        "unit": unit,
        "item": item,
    }
