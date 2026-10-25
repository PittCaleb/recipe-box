from app.ingredients.units import format_scaled, format_scaled_range

# Discrete slider stops, left to right, per SPEC.md 6.5.
MULTIPLIER_STOPS = [0.25, 1 / 3, 0.5, 2 / 3, 0.75, 1, 1.5, 2, 3, 4]
MULTIPLIER_LABELS = ["¼", "⅓", "½", "⅔", "¾", "1", "1½", "2", "3", "4"]
DEFAULT_MULTIPLIER = 1.0


def scale_ingredient_line(ingredient, multiplier):
    """Returns the display text for one ingredient row at the given
    multiplier. Headings and non-split/no-scale rows pass through unchanged
    (raw_text is never modified by scaling)."""
    if ingredient["kind"] == "heading":
        return ingredient["raw_text"]

    if ingredient["no_scale"] or not ingredient["is_split"] or ingredient["quantity"] is None:
        return ingredient["raw_text"]

    unit = ingredient["unit"]
    item = ingredient["item"] or ""

    low = ingredient["quantity"] * multiplier
    high = ingredient["quantity_max"] * multiplier if ingredient["quantity_max"] else None

    if high is not None:
        qty_text = format_scaled_range(low, high, unit)
    else:
        qty_text = format_scaled(low, unit)

    return f"{qty_text} {item}".strip()
