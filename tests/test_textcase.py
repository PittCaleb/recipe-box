import pytest

from app.ingredients.textcase import title_case, title_case_ingredient


@pytest.mark.parametrize("text, expected", [
    ("confectioners' sugar, sifted", "Confectioners' Sugar, Sifted"),
    ("butter or margarine", "Butter or Margarine"),
    ("cream of tartar", "Cream of Tartar"),
    ("all-purpose flour", "All-Purpose Flour"),
    ("2nd bowl", "2nd Bowl"),
    ("(185g) confectioners' sugar", "(185g) Confectioners' Sugar"),
    ('chicken, cut into 2"x3" pieces', 'Chicken, Cut into 2"x3" Pieces'),
    ("Jell-O pudding", "Jell-O Pudding"),
    ("MB's Grandma Cele's Filling", "MB's Grandma Cele's Filling"),
    ("egg whites, room temp. (about 12)", "Egg Whites, Room Temp. (about 12)"),
    ("beer (12 oz.)", "Beer (12 oz.)"),
    ("salt/pepper", "Salt/Pepper"),
    ("", ""),
])
def test_title_case(text, expected):
    assert title_case(text) == expected


def test_parentheticals_can_be_included():
    assert title_case("salt (optional)", include_parentheticals=True) == "Salt (Optional)"


@pytest.mark.parametrize("kind, raw, expected", [
    ("item", "2 cups flour, sifted", "2 cups Flour, Sifted"),
    ("item", "1 1/2 tsp. vanilla extract", "1 1/2 tsp. Vanilla Extract"),
    ("item", "3 eggs", "3 Eggs"),
    ("item", "salt to taste", "Salt to Taste"),
    ("item", "1 (14-ounce) can chicken broth", "1 (14-ounce) can Chicken Broth"),
    ("heading", "for the crust", "For the Crust"),
])
def test_title_case_imported_ingredient(kind, raw, expected):
    assert title_case_ingredient(kind, raw) == expected
