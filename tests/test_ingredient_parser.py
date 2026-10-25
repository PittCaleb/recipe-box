import pytest

from app.ingredients.parser import parse_ingredient


def parsed(raw):
    return parse_ingredient(raw)


# Real lines pulled from the imported recipe collection (data/recipes.db),
# covering the range of handwriting/typing styles across both source PDFs.
REAL_LINES = [
    ("1 t baking soda", 1, None, "tsp", "baking soda"),
    ("2 egg whites", 2, None, None, "egg whites"),
    ("2 1/2 C. All-purpose Flour", 2.5, None, "cup", "All-purpose Flour"),
    ("1/3 teaspoon salt", 1 / 3, None, "tsp", "salt"),
    ("1 teaspoon vanilla", 1, None, "tsp", "vanilla"),
    ("6 slices pancetta or bacon", 6, None, None, "slices pancetta or bacon"),
    ("3 tablespoon butter; melted", 3, None, "tbsp", "butter; melted"),
    ("1 T. Vanilla", 1, None, "tbsp", "Vanilla"),
    ("1 egg", 1, None, None, "egg"),
    ("4 eggs", 4, None, None, "eggs"),
    ("1/3 cup sugar", 1 / 3, None, "cup", "sugar"),
    ("salt", None, None, None, None),
    ("4 teaspoon baking powder", 4, None, "tsp", "baking powder"),
    ("8 oz almond paste", 8, None, "oz", "almond paste"),
    ("2 Cups Flour", 2, None, "cup", "Flour"),
    ("3 Cups milk", 3, None, "cup", "milk"),
    ("1 envelope dry onion soup mix", 1, None, None, "envelope dry onion soup mix"),
    ("2 C flour", 2, None, "cup", "flour"),
    ("1 C. milk", 1, None, "cup", "milk"),
    ("1/2 t salt", 0.5, None, "tsp", "salt"),
    ("5 Tbs. Margarine", 5, None, "tbsp", "Margarine"),
    ("2 cups pastry flour (can use cake flour too)", 2, None, "cup", "pastry flour (can use cake flour too)"),
    ("1/4 cup Parmesan cheese", 0.25, None, "cup", "Parmesan cheese"),
    ("1 Tbsp. milk", 1, None, "tbsp", "milk"),
    ("1 teaspoon cinnamon", 1, None, "tsp", "cinnamon"),
    ("1 box Pillsbury fudge cake mix", 1, None, None, "box Pillsbury fudge cake mix"),
    ("2 teaspoon vanilla extract", 2, None, "tsp", "vanilla extract"),
    ("1 1/4 C flour", 1.25, None, "cup", "flour"),
    ("1 1/2 C cornmeal", 1.5, None, "cup", "cornmeal"),
    ("2 cup flour; sifted", 2, None, "cup", "flour; sifted"),
    ("1 pinch salt", 1, None, "pinch", "salt"),
    ("3/4 cup walnuts; chopped", 0.75, None, "cup", "walnuts; chopped"),
    ("1 stick margarine", 1, None, "stick", "margarine"),
    ("2 clove garlic; peeled", 2, None, "clove", "garlic; peeled"),
    ("1 12 oz. can Coke (not diet)", 1, None, None, "12 oz. can Coke (not diet)"),
    ("1 bag parsnips (1 lb.)", 1, None, None, "bag parsnips (1 lb.)"),
    ("48 candy kisses", 48, None, None, "candy kisses"),
    ("1.5 cups bread crumbs", 1.5, None, "cup", "bread crumbs"),
    ("10 drops green food coloring", 10, None, None, "drops green food coloring"),
    ("2-3 cup water", 2, 3, "cup", "water"),
]


@pytest.mark.parametrize("raw,qty,qty_max,unit,item", REAL_LINES)
def test_real_card_lines(raw, qty, qty_max, unit, item):
    result = parsed(raw)
    assert result["quantity"] == pytest.approx(qty) if qty is not None else result["quantity"] is None
    if qty_max is not None:
        assert result["quantity_max"] == pytest.approx(qty_max)
    else:
        assert result["quantity_max"] is None
    assert result["unit"] == unit
    assert result["item"] == item


# --- Targeted edge cases from SPEC.md 6.4 ---

def test_mixed_number():
    r = parsed("1 1/2 cups sugar")
    assert r["quantity"] == pytest.approx(1.5)
    assert r["unit"] == "cup"
    assert r["item"] == "sugar"


def test_unicode_fraction_bare():
    r = parsed("½ cup butter")
    assert r["quantity"] == pytest.approx(0.5)
    assert r["unit"] == "cup"
    assert r["item"] == "butter"


def test_unicode_fraction_attached_to_whole():
    r = parsed("1½ cups milk")
    assert r["quantity"] == pytest.approx(1.5)
    assert r["unit"] == "cup"
    assert r["item"] == "milk"


@pytest.mark.parametrize("glyph,value", [
    ("¼", 0.25), ("⅓", 1 / 3), ("¾", 0.75), ("⅔", 2 / 3), ("⅛", 0.125),
])
def test_all_required_unicode_fractions(glyph, value):
    r = parsed(f"{glyph} cup oil")
    assert r["quantity"] == pytest.approx(value)
    assert r["unit"] == "cup"


def test_range_hyphen():
    r = parsed("2-3 tablespoons water")
    assert r["quantity"] == 2
    assert r["quantity_max"] == 3
    assert r["unit"] == "tbsp"
    assert r["item"] == "water"


def test_range_to_word():
    r = parsed("2 to 3 cups flour")
    assert r["quantity"] == 2
    assert r["quantity_max"] == 3
    assert r["unit"] == "cup"
    assert r["item"] == "flour"


def test_parenthetical_size_before_unit():
    r = parsed("1 (8 oz) package cream cheese")
    assert r["quantity"] == 1
    assert r["unit"] == "package"
    assert r["item"] == "(8 oz) cream cheese"


def test_parenthetical_with_no_matching_unit_stays_in_item():
    r = parsed("1 (12-pound) fresh or frozen turkey, thawed")
    assert r["quantity"] == 1
    assert r["unit"] is None
    assert r["item"] == "(12-pound) fresh or frozen turkey, thawed"


def test_capital_t_is_tablespoon():
    r = parsed("1 T butter")
    assert r["unit"] == "tbsp"


def test_lowercase_t_is_teaspoon():
    r = parsed("1 t butter")
    assert r["unit"] == "tsp"


def test_no_quantity_line_suggests_no_scale():
    r = parsed("salt to taste")
    assert r["quantity"] is None
    assert r["quantity_max"] is None
    assert r["unit"] is None


def test_no_quantity_descriptive_line():
    r = parsed("Butter, maple or pancake syrup, confectioners' sugar, for serving")
    assert r["quantity"] is None


def test_pound_sign_unit():
    r = parsed("2# ground beef")
    assert r["quantity"] == 2
    assert r["unit"] == "lb"
    assert r["item"] == "ground beef"


def test_decimal_quantity():
    r = parsed("2.5 cups flour")
    assert r["quantity"] == pytest.approx(2.5)
    assert r["unit"] == "cup"


def test_metric_units():
    r = parsed("250 g flour")
    assert r["quantity"] == 250
    assert r["unit"] == "g"
    assert r["item"] == "flour"

    r2 = parsed("500 ml milk")
    assert r2["unit"] == "ml"


def test_fl_oz_unit():
    r = parsed("8 fl oz heavy cream")
    assert r["unit"] == "fl_oz"
    assert r["item"] == "heavy cream"


def test_dash_unit():
    r = parsed("1 dash cayenne")
    assert r["unit"] == "dash"
    assert r["item"] == "cayenne"


def test_empty_string():
    r = parsed("")
    assert r["quantity"] is None


def test_raw_text_never_mutated():
    raw = "1 1/2 cups sugar"
    parse_ingredient(raw)
    assert raw == "1 1/2 cups sugar"


def test_hyphenated_mixed_number_is_not_a_range():
    from app.ingredients.parser import parse_ingredient
    p = parse_ingredient("1-1/2 cups all-purpose flour")
    assert (p["quantity"], p["quantity_max"], p["unit"], p["item"]) == (1.5, None, "cup", "all-purpose flour")
    r = parse_ingredient("2-3 cups water")
    assert (r["quantity"], r["quantity_max"]) == (2, 3)
