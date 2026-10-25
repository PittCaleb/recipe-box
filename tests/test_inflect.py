import pytest

from app.ingredients.inflect import pluralize, set_noun_number, singularize
from app.ingredients.parser import parse_ingredient
from app.ingredients.scaling import scale_ingredient_line
from app.ingredients.units import format_scaled, format_scaled_range


def _scale(raw, m):
    ing = {"kind": "item", "no_scale": 0, "is_split": 1, **parse_ingredient(raw)}
    return scale_ingredient_line(ing, m)


@pytest.mark.parametrize("word, plural", [
    ("egg", "eggs"), ("peach", "peaches"), ("box", "boxes"), ("berry", "berries"),
    ("loaf", "loaves"), ("potato", "potatoes"), ("Onion", "Onions"), ("key", "keys"),
])
def test_pluralize_and_back(word, plural):
    assert pluralize(word) == plural
    assert singularize(plural) == word


@pytest.mark.parametrize("word", ["molasses", "asparagus", "glass"])
def test_words_ending_in_s_that_arent_plural(word):
    assert singularize(word) == word
    assert pluralize(word) == word


@pytest.mark.parametrize("item, plural, expected", [
    ("eggs", False, "egg"),
    ("egg whites", False, "egg white"),
    ("small onion, diced", True, "small onions, diced"),
    ("small onion; diced", True, "small onions; diced"),
    ("cubes chicken bouillon", False, "cube chicken bouillon"),
    ("slice bread (toasted)", True, "slices bread (toasted)"),
    ("fat-free crackers", False, "fat-free cracker"),
    ("Hershey's", False, "Hershey's"),
])
def test_set_noun_number(item, plural, expected):
    assert set_noun_number(item, plural) == expected


@pytest.mark.parametrize("raw, m, expected", [
    ("3 eggs", 1 / 3, "1 egg"),
    ("3 eggs", 0.25, "¾ egg"),
    ("3 eggs", 0.5, "1 ½ eggs"),
    ("1 egg", 1.5, "1 ½ eggs"),
    ("1 egg", 2, "2 eggs"),
    ("1 egg", 0.5, "½ egg"),
    ("2 eggs", 1 / 3, "about ¾ egg"),
    ("4 egg whites", 0.25, "1 egg white"),
    ("3 cubes chicken bouillon", 1 / 3, "1 cube chicken bouillon"),
    ("2-3 apples", 1 / 3, "¾–1 apple"),
    ("2-3 apples", 0.5, "1–1 ½ apples"),
    ("3 eggs", 1, "3 eggs"),
])
def test_scaled_counts_agree_with_quantity(raw, m, expected):
    assert _scale(raw, m) == expected


def test_source_wording_kept_when_not_crossing_one():
    # Wrong in the source, but scaling doesn't cross 1, so it's left as written.
    assert _scale("2 egg", 2) == "4 egg"


def test_units_unaffected():
    assert _scale("2 cups flour", 0.5) == "1 cup flour"
    assert _scale("2 sticks butter", 0.25) == "½ stick butter"


def test_pinch_never_scales_to_zero():
    assert format_scaled(0.25, "pinch") == "1 pinch"
    assert format_scaled_range(0.25, 0.5, "dash") == "1 dash"
    assert format_scaled_range(1, 2, "pinch") == "1–2 pinches"
