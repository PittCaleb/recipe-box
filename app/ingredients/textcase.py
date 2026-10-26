import re

SMALL_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into", "nor",
    "of", "on", "or", "per", "the", "to", "with",
}
# Measurement abbreviations stay lowercase ("12 oz.", "9 in.").
ABBREVIATIONS = {"oz", "lb", "lbs", "g", "kg", "ml", "l", "tsp", "tbsp", "c", "pkg", "pt", "qt"}

_WORD = re.compile(r"[A-Za-z][A-Za-z']*")


def _cap_word(word, first):
    lower = word.lower()
    if any(c.isupper() for c in word[1:]):
        return word  # PAM, MB's, OK, Jell-O: deliberate capitals stay
    if lower in ABBREVIATIONS:
        return lower
    if lower in SMALL_WORDS and not first:
        return lower
    return word[0].upper() + word[1:]


def _title_segment(text, start_first=True):
    out = []
    first = start_first
    pos = 0
    for m in _WORD.finditer(text):
        out.append(text[pos:m.start()])
        between = text[pos:m.start()]
        # A comma, semicolon, or colon starts a new phrase: "Flour, Sifted".
        if any(ch in between for ch in ",;:"):
            first = True
        # Hyphen-joined parts each get a capital: "All-Purpose", "Jell-O".
        joined = m.start() > 0 and text[m.start() - 1] == "-"
        if m.start() > 0 and not (text[m.start() - 1].isspace() or text[m.start() - 1] in "(-/"):
            out.append(m.group(0))  # "2nd", "185g", 2"x3": glued to a number, not a word
        else:
            out.append(_cap_word(m.group(0), first or joined))
        first = False
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def title_case_ingredient(kind, raw_text):
    """An imported ingredient line in Title Case, leaving the amount and unit
    as written: "2 cups flour, sifted" -> "2 cups Flour, Sifted"."""
    from app.ingredients.parser import parse_ingredient

    if kind == "heading":
        return title_case(raw_text)
    parsed = parse_ingredient(raw_text)
    line = raw_text.rstrip()
    if parsed["item"]:
        # The parser moves a size note like "(14-ounce)" into the item, so
        # also try the item without it: "1 (14-ounce) can chicken broth".
        for item in (parsed["item"], re.sub(r"^\([^)]*\)\s*", "", parsed["item"])):
            if item and line.endswith(item):
                return line[: -len(item)] + title_case(item)
    if parsed["quantity"] is None:
        return title_case(raw_text)
    return raw_text  # unusual layout; leave it rather than capitalize the unit


def title_case(text, include_parentheticals=False):
    """Title Case for ingredient names and headings: "confectioners' sugar,
    sifted" -> "Confectioners' Sugar, Sifted", "butter or margarine" ->
    "Butter or Margarine". Words with deliberate capitals (PAM, Jell-O) are
    left alone. Parenthetical notes are left as written unless
    include_parentheticals is set."""
    if not text:
        return text
    if include_parentheticals:
        return _title_segment(text)
    parts = re.split(r"(\([^)]*\))", text)
    out = []
    first = True
    for part in parts:
        if part.startswith("(") and part.endswith(")"):
            out.append(part)
        else:
            out.append(_title_segment(part, start_first=first or not "".join(out).strip()))
            first = False
    return "".join(out)
