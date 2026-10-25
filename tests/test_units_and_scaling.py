import pytest

from app.ingredients.scaling import scale_ingredient_line
from app.ingredients.units import (
    format_count,
    format_metric_volume,
    format_metric_weight,
    format_scaled,
    format_scaled_range,
    format_weight,
    round_kitchen_fraction,
)


# --- Kitchen-fraction rounding ---

@pytest.mark.parametrize("value,expected", [
    (0.0, 0.0), (1.0, 1.0),
    (0.12, 0.125), (0.13, 0.125),
    (0.24, 0.25), (0.26, 0.25),
    (0.5, 0.5),
    (0.74, 0.75),
    (1.49, 1.5),
])
def test_round_kitchen_fraction_eighths(value, expected):
    assert round_kitchen_fraction(value) == pytest.approx(expected)


def test_round_kitchen_fraction_prefers_third_when_closer():
    # 1/3 = 0.333..., nearest eighth is 0.375 (diff .0417) vs nearest third
    # 0.333 (diff .0017) -- thirds should win.
    assert round_kitchen_fraction(0.33) == pytest.approx(1 / 3)


def test_round_kitchen_fraction_prefers_two_thirds_when_closer():
    assert round_kitchen_fraction(0.68) == pytest.approx(2 / 3)


def test_round_kitchen_fraction_never_decimal_surprise():
    # A value very close to a whole number rounds to the whole, not 7/8 etc.
    assert round_kitchen_fraction(0.99) == pytest.approx(1.0)


# --- Volume conversion / display ---

def test_volume_under_one_tbsp_displays_as_tsp():
    assert format_scaled(0.5, "tsp") == "½ tsp"


def test_volume_three_tsp_promotes_to_tbsp_equivalent_but_stays_tsp_unit():
    # 1 tbsp of tbsp-unit ingredient stays in tbsp.
    assert format_scaled(1, "tbsp") == "1 tbsp"


def test_volume_under_quarter_cup_displays_as_tbsp():
    # 2 tbsp = 1/8 cup < 1/4 cup -> stays tbsp
    assert format_scaled(2, "tbsp") == "2 tbsp"


def test_volume_quarter_cup_or_more_displays_as_cups():
    assert format_scaled(4, "tbsp") == "¼ cup"


def test_volume_exact_cup_multiple():
    assert format_scaled(2, "cup") == "2 cups"


def test_volume_compound_form_when_not_clean_cups():
    # 1.5 cups + a bit more tbsp that doesn't round cleanly to a cup fraction
    # 1 cup 2 Tbsp = 18 tbsp = 1.125 cups -> nearest eighth cup is 1.125 itself! use a messier case
    # 10 tbsp = 0.625 cup exactly -> clean eighth, should NOT be compound
    assert format_scaled(10, "tbsp") == "⅝ cup"
    # 15 tbsp = 0.9375 cup -- not a clean eighth (nearest eighth 0.875 or 1.0,
    # both > 0.5 tbsp off) -> compound form expected
    text = format_scaled(15, "tbsp")
    assert "+" in text
    assert "tbsp" in text


def test_volume_half_recipe_cup_to_tbsp_plus():
    # 1 1/2 cups scaled by 1/3 = 1/2 cup exactly
    assert format_scaled(1.5 * (1 / 3), "cup") == "½ cup"


def test_volume_range():
    assert format_scaled_range(2, 3, "tbsp") == "2–3 tbsp"


def test_volume_range_crosses_tier_uses_larger_ends_tier():
    # 2 tbsp - 4 tbsp: larger end (4 tbsp = 1/4 cup) picks "cup" tier for both.
    text = format_scaled_range(2, 4, "tbsp")
    assert text.endswith("cup") or "cup" in text


# --- Weight conversion / display ---

def test_weight_under_one_lb_displays_oz():
    assert format_scaled(8, "oz") == "8 oz"


def test_weight_sixteen_oz_is_one_lb():
    assert format_scaled(16, "oz") == "1 lb"


def test_weight_compound_form():
    text = format_weight(19)  # 1.1875 lb -- not a clean eighth, so compound
    assert "1 lb" in text
    assert "oz" in text


def test_weight_lb_stays_lb_when_scaled():
    assert format_scaled(2, "lb") == "2 lb"


# --- Metric ---

def test_metric_volume_under_1000ml():
    assert format_metric_volume(250) == "250 ml"


def test_metric_volume_scales_to_liters():
    assert format_metric_volume(1500) == "1 ½ l"


def test_metric_weight_under_1000g():
    assert format_metric_weight(500) == "500 g"


def test_metric_weight_scales_to_kg():
    assert format_metric_weight(2000) == "2 kg"


# --- Count items (eggs, candy kisses, etc.) ---

def test_count_rounds_to_nearest_half():
    assert format_count(3.4) == "3 ½"


def test_count_rounds_to_nearest_quarter_when_closer():
    # 3.25 is exactly a quarter; nearest half (3.5) is farther (.25 vs .0)
    assert format_count(3.25) == "3 ¼"


def test_count_shows_about_when_rounding_off_by_more_than_5_percent():
    # value 1 scaled by 1/3 = 0.333; nearest half/quarter rounding is 0.5,
    # which is 50% off -> "about"
    text = format_count(1 / 3)
    assert text.startswith("about")


def test_count_no_about_prefix_for_close_rounding():
    # 4 eggs * 1 = 4, rounds exactly -> no "about"
    assert format_count(4) == "4"


# --- Pinch / dash: multiplied, never converted ---

def test_pinch_multiplies_without_conversion():
    assert format_scaled(2, "pinch") == "2 pinches"


def test_dash_singular():
    assert format_scaled(1, "dash") == "1 dash"


# --- Count-like named units (sticks, cans, cloves, packages) ---

def test_count_like_unit_multiplies_and_labels():
    assert format_scaled(2, "stick") == "2 sticks"


def test_count_like_unit_singular():
    assert format_scaled(1, "clove") == "1 clove"


# --- scale_ingredient_line integration ---

def _ing(**kw):
    base = {
        "kind": "item", "raw_text": "2 cups flour", "is_split": 1,
        "quantity": 2, "quantity_max": None, "unit": "cup", "item": "flour", "no_scale": 0,
    }
    base.update(kw)
    return base


def test_scale_ingredient_line_basic():
    assert scale_ingredient_line(_ing(), 2) == "4 cups flour"


def test_scale_ingredient_line_no_scale_passes_through_raw_text():
    ing = _ing(no_scale=1, raw_text="salt to taste")
    assert scale_ingredient_line(ing, 4) == "salt to taste"


def test_scale_ingredient_line_heading_passes_through():
    ing = {"kind": "heading", "raw_text": "For the crust:"}
    assert scale_ingredient_line(ing, 3) == "For the crust:"


def test_scale_ingredient_line_unsplit_passes_through_raw_text():
    ing = _ing(is_split=0, raw_text="a handful of something")
    assert scale_ingredient_line(ing, 2) == "a handful of something"


def test_scale_ingredient_line_range():
    ing = _ing(quantity=2, quantity_max=3, unit="tbsp", item="water", raw_text="2-3 tbsp water")
    assert scale_ingredient_line(ing, 1) == "2–3 tbsp water"


def test_scale_ingredient_line_default_multiplier_matches_original_values():
    ing = _ing(quantity=3, unit=None, item="eggs", raw_text="3 eggs")
    assert scale_ingredient_line(ing, 1) == "3 eggs"


def test_three_quarter_stop_between_two_thirds_and_one():
    from app.ingredients.scaling import MULTIPLIER_LABELS, MULTIPLIER_STOPS
    assert MULTIPLIER_STOPS == sorted(MULTIPLIER_STOPS)
    i = MULTIPLIER_STOPS.index(0.75)
    assert MULTIPLIER_LABELS[i] == "¾"
    assert MULTIPLIER_LABELS[i - 1] == "⅔" and MULTIPLIER_LABELS[i + 1] == "1"
    assert len(MULTIPLIER_STOPS) == len(MULTIPLIER_LABELS)


def test_three_quarter_scaling_of_a_cup():
    from app.ingredients.scaling import scale_ingredient_line
    ing = {"kind": "item", "no_scale": 0, "is_split": 1, "quantity": 1.0,
           "quantity_max": None, "unit": "cup", "item": "flour"}
    assert scale_ingredient_line(ing, 0.75) == "¾ cup flour"
