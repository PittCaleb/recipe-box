"""Turns ingredient lines into shopping-list entries like
"Heavy whipping cream (2 cups)"."""
import re

from app.ingredients.inflect import COUNT_NOUNS, pluralize, set_noun_number, singularize
from app.ingredients.parser import parse_ingredient
from app.ingredients.units import (
    _TO_G, _TO_ML, _TO_OZ, _TO_TSP, COUNT_LIKE_UNITS, NO_CONVERT_UNITS,
    format_scaled, format_scaled_range, rounded_count,
)

# The Apple Shortcut the "Add to shopping list" buttons run; the Help page
# tells people to create it with exactly this name.
SHORTCUT_NAME = "Add to Shopping List"

# Each convertible unit maps to (category, base unit, factor to base).
_CATEGORIES = {}
for _unit, _f in _TO_TSP.items():
    _CATEGORIES[_unit] = ("volume", "tsp", _f)
for _unit, _f in _TO_OZ.items():
    _CATEGORIES[_unit] = ("weight", "oz", _f)
for _unit, _f in _TO_ML.items():
    _CATEGORIES[_unit] = ("metric_volume", "ml", _f)
for _unit, _f in _TO_G.items():
    _CATEGORIES[_unit] = ("metric_weight", "g", _f)


def _amount(ingredient, multiplier):
    """(quantity, quantity_max, unit, item) as shown on screen at this
    multiplier, or None when the line has no amount worth shopping for."""
    if ingredient["kind"] != "item":
        return None
    if ingredient["is_split"] and ingredient["quantity"] is not None:
        q, q_max, unit, item = (ingredient["quantity"], ingredient["quantity_max"],
                                ingredient["unit"], ingredient["item"])
        # Only split, scalable lines change with the slider; everything else
        # is shown as written, so its shopping amount stays as written too.
        if not ingredient["no_scale"]:
            q = q * multiplier
            q_max = q_max * multiplier if q_max else None
    else:
        parsed = parse_ingredient(ingredient["raw_text"])
        q, q_max, unit, item = (parsed["quantity"], parsed["quantity_max"],
                                parsed["unit"], parsed["item"])
    if q is None or not item or unit in NO_CONVERT_UNITS:
        return None
    return q, q_max, unit, item


PREP_STARTERS = {
    "room", "at", "to", "for", "cut", "about", "plus", "optional", "or", "if",
    "as", "into", "in", "such", "see", "cold", "warm", "hot", "minced",
    "torn", "ground", "whole", "halved", "packed", "sifted", "softened",
}


def _is_prep(text):
    first = re.match(r"[a-z]+", text.strip().lower())
    if not first:
        return True
    word = first.group(0)
    return word in PREP_STARTERS or word.endswith(("ed", "ly"))


def shopping_name(item):
    """"(2 sticks) butter, chunked" -> "Butter": leading parentheticals and
    trailing prep notes don't belong on a shopping list. A comma only ends
    the name when prep follows it, so "fat-free, less-sodium chicken broth"
    stays whole."""
    name = re.sub(r"^(\([^)]*\)\s*)+", "", item.strip())
    name = name.split(";", 1)[0]
    parts = name.split(",")
    kept = [parts[0]]
    for part in parts[1:]:
        if _is_prep(part):
            break
        kept.append(part)
    name = re.sub(r"\s+", " ", ",".join(kept)).strip(" ,")
    return name[:1].upper() + name[1:] if name else ""


def _split_count_noun(name):
    """"Slices peeled fresh ginger" -> ("Peeled fresh ginger", "slice")."""
    first, _, rest = name.partition(" ")
    if rest and singularize(first).lower() in COUNT_NOUNS:
        return rest[:1].upper() + rest[1:], singularize(first).lower()
    return name, None


def _merge_key(name):
    words = name.lower().split()
    if words:
        words[-1] = singularize(words[-1])
    return " ".join(words)


def _qty_text(q, q_max, unit):
    if q_max:
        return format_scaled_range(q, q_max, unit)
    return format_scaled(q, unit)


def _entry(name, q, q_max, unit):
    if unit is None:
        shown = rounded_count(q_max if q_max else q)
        name, counter = _split_count_noun(name)
        if counter:
            noun = pluralize(counter) if shown > 1 else counter
            return f"{name} ({_qty_text(q, q_max, None)} {noun})"
        name = set_noun_number(name, plural=shown > 1)
    return f"{name} ({_qty_text(q, q_max, unit)})"


def shopping_entry(ingredient, multiplier=1.0):
    amount = _amount(ingredient, multiplier)
    if amount is None:
        return None
    q, q_max, unit, item = amount
    name = shopping_name(item)
    if not name:
        return None
    return _entry(name, q, q_max, unit)


def shopping_list(ingredients, multiplier=1.0):
    """Entries for every line with an amount, with the same ingredient
    combined when its units can be added up (cups + tbsp, oz + lb, two counts
    of eggs). Ranges and mismatched units stay as separate entries."""
    groups = {}
    order = []
    for ing in ingredients:
        amount = _amount(ing, multiplier)
        if amount is None:
            continue
        q, q_max, unit, item = amount
        name = shopping_name(item)
        if not name:
            continue

        if q_max:
            key = ("separate", len(order))
        elif unit in _CATEGORIES:
            category, _, _ = _CATEGORIES[unit]
            key = (_merge_key(name), category)
        elif unit is None or unit in COUNT_LIKE_UNITS:
            key = (_merge_key(name), unit or "count")
        else:
            key = ("separate", len(order))

        if key not in groups:
            groups[key] = {"name": name, "parts": []}
            order.append(key)
        groups[key]["parts"].append((q, q_max, unit))

    entries = []
    for key in order:
        group = groups[key]
        parts = group["parts"]
        if len(parts) == 1:
            q, q_max, unit = parts[0]
            entries.append(_entry(group["name"], q, q_max, unit))
            continue
        unit = parts[0][2]
        if unit in _CATEGORIES:
            _, base, _ = _CATEGORIES[unit]
            total = sum(q * _CATEGORIES[u][2] for q, _, u in parts)
            entries.append(_entry(group["name"], total, None, base))
        else:
            entries.append(_entry(group["name"], sum(q for q, _, _ in parts), None, unit))
    return entries
