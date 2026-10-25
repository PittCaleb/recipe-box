from app.ingredients.inflect import set_noun_number
from app.ingredients.units import (
    format_quantity, format_scaled, format_scaled_range, round_kitchen_fraction,
    rounded_count, unit_label,
)

# Discrete slider stops, left to right, per SPEC.md 6.5.
MULTIPLIER_STOPS = [0.25, 1 / 3, 0.5, 2 / 3, 0.75, 1, 1.5, 2, 3, 4]
MULTIPLIER_LABELS = ["¼", "⅓", "½", "⅔", "¾", "1", "1½", "2", "3", "4"]
DEFAULT_MULTIPLIER = 1.0


def format_amount(value):
    """A stored quantity as kitchen text: 1.5 -> "1 ½", 0.333 -> "⅓"."""
    return format_quantity(round_kitchen_fraction(value))


def format_ingredient_line(quantity, quantity_max, unit, item):
    """The display line for a split ingredient, in the units it was entered
    in -- "2 oz semisweet chocolate", "1–2 cups water", "3 eggs". This is the
    only source of a split ingredient's text; nothing typed separately
    overrides it."""
    item = (item or "").strip()
    if quantity is None:
        return item
    amount = format_amount(quantity)
    if quantity_max:
        amount = f"{amount}–{format_amount(quantity_max)}"
    parts = [amount]
    if unit:
        parts.append(unit_label(unit, quantity_max or quantity))
    if item:
        parts.append(item)
    return " ".join(parts)


def scale_ingredient_line(ingredient, multiplier):
    """Returns the display text for one ingredient row at the given
    multiplier. Headings and non-split/no-scale rows pass through unchanged."""
    if ingredient["kind"] == "heading":
        return ingredient["raw_text"]

    if ingredient["no_scale"] or not ingredient["is_split"] or ingredient["quantity"] is None:
        return ingredient["raw_text"]

    unit = ingredient["unit"] or None
    item = ingredient["item"] or ""

    if multiplier == DEFAULT_MULTIPLIER:
        # Unscaled, show it exactly as entered rather than re-choosing units
        # (3 tsp stays 3 tsp instead of becoming 1 tbsp).
        return format_ingredient_line(ingredient["quantity"], ingredient["quantity_max"], unit, item)

    low = ingredient["quantity"] * multiplier
    high = ingredient["quantity_max"] * multiplier if ingredient["quantity_max"] else None

    if high is not None:
        qty_text = format_scaled_range(low, high, unit)
    else:
        qty_text = format_scaled(low, unit)

    if unit is None and item:
        # Plain counts carry their noun in the item text ("3 eggs"). Only
        # re-inflect when scaling crosses the singular/plural line, so the
        # source wording is kept whenever it's already right.
        original = ingredient["quantity_max"] or ingredient["quantity"]
        scaled = rounded_count(high if high is not None else low)
        if (original > 1) != (scaled > 1):
            item = set_noun_number(item, plural=scaled > 1)

    return f"{qty_text} {item}".strip()
