"""Unit conversion, kitchen-fraction rounding, and display formatting for
scaling ingredients (section 6.5 of SPEC.md)."""
import math

VOLUME_UNITS = {"tsp", "tbsp", "cup", "fl_oz", "pt", "qt", "gal"}
WEIGHT_UNITS = {"oz", "lb"}
METRIC_VOLUME_UNITS = {"ml", "l"}
METRIC_WEIGHT_UNITS = {"g", "kg"}
COUNT_LIKE_UNITS = {"stick", "can", "package", "clove"}
NO_CONVERT_UNITS = {"pinch", "dash"}

UNIT_LABELS = {
    "tsp": ("tsp", "tsp"), "tbsp": ("tbsp", "tbsp"), "cup": ("cup", "cups"),
    "fl_oz": ("fl oz", "fl oz"), "pt": ("pt", "pt"), "qt": ("qt", "qt"), "gal": ("gal", "gal"),
    "oz": ("oz", "oz"), "lb": ("lb", "lb"),
    "ml": ("ml", "ml"), "l": ("l", "l"), "g": ("g", "g"), "kg": ("kg", "kg"),
    "stick": ("stick", "sticks"), "can": ("can", "cans"),
    "package": ("package", "packages"), "clove": ("clove", "cloves"),
    "pinch": ("pinch", "pinches"), "dash": ("dash", "dashes"),
}

_FRACTION_GLYPHS = {
    0.125: "⅛", 0.25: "¼", 1 / 3: "⅓", 0.375: "⅜",
    0.5: "½", 0.625: "⅝", 2 / 3: "⅔", 0.75: "¾", 0.875: "⅞",
}
_FRACTION_CANDIDATES = (0.0, *_FRACTION_GLYPHS.keys(), 1.0)


def unit_label(unit, count=1):
    """Singular for zero/fractional/exactly-one amounts ("½ cup", "1 cup"),
    plural once a quantity exceeds one ("1 ½ cups", "2 cups")."""
    singular, plural = UNIT_LABELS.get(unit, (unit, unit))
    return singular if round(count, 4) <= 1 else plural


def round_kitchen_fraction(value):
    """Rounds to the nearest eighth, preferring a third/two-thirds when that's
    closer, per SPEC.md: "nearest ⅛, using ⅓ and ⅔ where closer"."""
    if value < 0:
        return 0.0
    whole = math.floor(value)
    frac = value - whole

    best = min(_FRACTION_CANDIDATES, key=lambda c: abs(c - frac))
    if best >= 1.0:
        whole += 1
        best = 0.0
    return whole + best


def format_quantity(value):
    """Formats a (already kitchen-fraction-rounded) quantity as "1 ½" etc."""
    whole = math.floor(round(value, 6))
    frac = round(value - whole, 6)

    if frac <= 1e-6:
        return str(whole) if whole else "0"

    glyph = None
    for key, g in _FRACTION_GLYPHS.items():
        if abs(key - frac) < 1e-6:
            glyph = g
            break
    if glyph is None:
        glyph = f"{frac:.2f}"

    return f"{whole} {glyph}" if whole else glyph


def round_to_nearest(value, step):
    return round(value / step) * step


def _round_count(value):
    """Rounds to the nearest ½, falling back to the nearest ¼ when that's a
    closer fit, and reports whether that changed the value by more than ~5%."""
    half = round_to_nearest(value, 0.5)
    quarter = round_to_nearest(value, 0.25)
    rounded = half if abs(half - value) <= abs(quarter - value) else quarter
    is_approx = value > 0 and abs(rounded - value) / value > 0.05
    return rounded, is_approx


def rounded_count(value):
    """The amount a plain count actually displays as, after rounding."""
    return round(_round_count(value)[0], 4)


def format_count(value):
    """Plain count items (eggs, candy kisses, ...): round to the nearest ½ or
    ¼, prefixing "about" when that rounding changes the value by more than
    ~5%."""
    rounded, is_approx = _round_count(value)
    text = format_quantity(rounded)
    return f"about {text}" if is_approx else text


def format_pinch_dash(value, unit):
    # A pinch can't be split; scaling down still leaves one.
    whole = max(1, round(value))
    label = unit_label(unit, whole)
    return f"{whole} {label}"


def _format_single(value, unit):
    rounded = round_kitchen_fraction(value)
    text = format_quantity(rounded)
    return f"{text} {unit_label(unit, rounded)}"


def format_volume(total_tsp):
    """Chooses tsp / tbsp / cup (with an optional compound "cup + tbsp" form)
    for a total expressed in teaspoons."""
    total_tbsp = total_tsp / 3
    total_cups = total_tbsp / 16

    if total_tsp < 3:
        return _format_single(total_tsp, "tsp")

    if total_cups < 0.25:
        return _format_single(total_tbsp, "tbsp")

    rounded_cups = round_kitchen_fraction(total_cups)
    error_tbsp = abs(rounded_cups * 16 - total_tbsp)
    if error_tbsp <= 0.5:
        return _format_single(total_cups, "cup")

    whole_cups = math.floor(total_cups)
    remainder_tbsp = round_to_nearest(total_tbsp - whole_cups * 16, 0.5)
    if remainder_tbsp >= 16:
        whole_cups += 1
        remainder_tbsp -= 16

    cup_part = f"{whole_cups} {unit_label('cup', whole_cups)}"
    if remainder_tbsp <= 1e-6:
        return cup_part
    tbsp_part = f"{format_quantity(remainder_tbsp)} {unit_label('tbsp', remainder_tbsp)}"
    return f"{cup_part} + {tbsp_part}"


def format_weight(total_oz):
    if total_oz < 16:
        return _format_single(total_oz, "oz")

    total_lb = total_oz / 16
    rounded_lb = round_kitchen_fraction(total_lb)
    error_oz = abs(rounded_lb * 16 - total_oz)
    if error_oz <= 0.5:
        return _format_single(total_lb, "lb")

    whole_lb = math.floor(total_lb)
    remainder_oz = round_to_nearest(total_oz - whole_lb * 16, 0.5)
    if remainder_oz >= 16:
        whole_lb += 1
        remainder_oz -= 16

    lb_part = f"{whole_lb} {unit_label('lb', whole_lb)}"
    if remainder_oz <= 1e-6:
        return lb_part
    oz_part = f"{format_quantity(remainder_oz)} {unit_label('oz', remainder_oz)}"
    return f"{lb_part} + {oz_part}"


def format_metric_volume(total_ml):
    if total_ml < 1000:
        return _format_single(total_ml, "ml")
    return _format_single(total_ml / 1000, "l")


def format_metric_weight(total_g):
    if total_g < 1000:
        return _format_single(total_g, "g")
    return _format_single(total_g / 1000, "kg")


_TO_TSP = {"tsp": 1, "tbsp": 3, "cup": 48, "fl_oz": 6, "pt": 96, "qt": 192, "gal": 768}
_TO_OZ = {"oz": 1, "lb": 16}
_TO_ML = {"ml": 1, "l": 1000}
_TO_G = {"g": 1, "kg": 1000}


def _volume_tier(total_tsp):
    total_tbsp = total_tsp / 3
    total_cups = total_tbsp / 16
    if total_tsp < 3:
        return "tsp"
    if total_cups < 0.25:
        return "tbsp"
    return "cup"


def _weight_tier(total_oz):
    return "oz" if total_oz < 16 else "lb"


def _metric_volume_tier(total_ml):
    return "ml" if total_ml < 1000 else "l"


def _metric_weight_tier(total_g):
    return "g" if total_g < 1000 else "kg"


def _format_range_in_tier(low_in_tier, high_in_tier, tier):
    lo_r = round_kitchen_fraction(low_in_tier)
    hi_r = round_kitchen_fraction(high_in_tier)
    return f"{format_quantity(lo_r)}–{format_quantity(hi_r)} {unit_label(tier, hi_r)}"


def format_scaled_range(low, high, unit):
    """Like format_scaled, but for a quantity/quantity_max range. Both ends
    are shown in the same unit (chosen from the larger end) rather than each
    picking its own tier, so a range never mixes units."""
    if unit is None:
        lo_r, _ = _round_count(low)
        hi_r, _ = _round_count(high)
        return f"{format_quantity(lo_r)}–{format_quantity(hi_r)}"

    if unit in NO_CONVERT_UNITS:
        lo_w, hi_w = max(1, round(low)), max(1, round(high))
        if lo_w == hi_w:
            return f"{lo_w} {unit_label(unit, hi_w)}"
        return f"{lo_w}–{hi_w} {unit_label(unit, hi_w)}"

    if unit in COUNT_LIKE_UNITS:
        lo_r, _ = _round_count(low)
        hi_r, _ = _round_count(high)
        return f"{format_quantity(lo_r)}–{format_quantity(hi_r)} {unit_label(unit, hi_r)}"

    if unit in VOLUME_UNITS:
        lo_tsp, hi_tsp = low * _TO_TSP[unit], high * _TO_TSP[unit]
        tier = _volume_tier(hi_tsp)
        factor = _TO_TSP[tier]
        return _format_range_in_tier(lo_tsp / factor, hi_tsp / factor, tier)

    if unit in WEIGHT_UNITS:
        lo_oz, hi_oz = low * _TO_OZ[unit], high * _TO_OZ[unit]
        tier = _weight_tier(hi_oz)
        factor = _TO_OZ[tier]
        return _format_range_in_tier(lo_oz / factor, hi_oz / factor, tier)

    if unit in METRIC_VOLUME_UNITS:
        lo_ml, hi_ml = low * _TO_ML[unit], high * _TO_ML[unit]
        tier = _metric_volume_tier(hi_ml)
        factor = _TO_ML[tier]
        return _format_range_in_tier(lo_ml / factor, hi_ml / factor, tier)

    if unit in METRIC_WEIGHT_UNITS:
        lo_g, hi_g = low * _TO_G[unit], high * _TO_G[unit]
        tier = _metric_weight_tier(hi_g)
        factor = _TO_G[tier]
        return _format_range_in_tier(lo_g / factor, hi_g / factor, tier)

    lo_r, _ = _round_count(low)
    hi_r, _ = _round_count(high)
    return f"{format_quantity(lo_r)}–{format_quantity(hi_r)}"


def format_scaled(value, unit):
    """Formats a scaled numeric quantity for display, choosing the most
    readable unit for its category. `unit` is the ingredient's original
    canonical unit (or None for a plain count)."""
    if unit is None:
        return format_count(value)
    if unit in NO_CONVERT_UNITS:
        return format_pinch_dash(value, unit)
    if unit in VOLUME_UNITS:
        return format_volume(value * _TO_TSP[unit])
    if unit in WEIGHT_UNITS:
        return format_weight(value * _TO_OZ[unit])
    if unit in METRIC_VOLUME_UNITS:
        return format_metric_volume(value * _TO_ML[unit])
    if unit in METRIC_WEIGHT_UNITS:
        return format_metric_weight(value * _TO_G[unit])
    if unit in COUNT_LIKE_UNITS:
        rounded, is_approx = _round_count(value)
        text = format_quantity(rounded)
        label = unit_label(unit, rounded)
        return f"about {text} {label}" if is_approx else f"{text} {label}"
    return format_count(value)
