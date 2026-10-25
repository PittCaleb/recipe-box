import re

# Words that name the counted thing even when they aren't last:
# "3 cubes chicken bouillon", "2 slices bread", "4 sprigs thyme".
COUNT_NOUNS = {
    "bag", "bar", "bottle", "box", "bulb", "bunch", "carton", "container",
    "cube", "drop", "ear", "envelope", "fillet", "head", "jar", "leaf",
    "link", "loaf", "packet", "piece", "pouch", "rib", "scoop", "sheet",
    "slice", "sprig", "square", "stalk", "strip", "wedge",
}
IRREGULAR_PLURALS = {
    "leaf": "leaves", "loaf": "loaves", "half": "halves", "knife": "knives",
    "potato": "potatoes", "tomato": "tomatoes", "mango": "mangoes",
}
IRREGULAR_SINGULARS = {v: k for k, v in IRREGULAR_PLURALS.items()}
# End in "s" but aren't plurals.
NOT_PLURAL = {"molasses", "asparagus", "hummus", "couscous", "swiss", "citrus", "bass"}


def pluralize(word):
    lower = word.lower()
    if lower in IRREGULAR_PLURALS:
        return _match_case(word, IRREGULAR_PLURALS[lower])
    if lower.endswith("s") or lower in NOT_PLURAL:
        return word
    if re.search(r"(x|z|ch|sh)$", lower):
        return word + "es"
    if re.search(r"[^aeiou]y$", lower):
        return word[:-1] + "ies"
    return word + "s"


def singularize(word):
    lower = word.lower()
    if lower in IRREGULAR_SINGULARS:
        return _match_case(word, IRREGULAR_SINGULARS[lower])
    if lower in NOT_PLURAL or lower.endswith("ss") or not lower.endswith("s"):
        return word
    if lower.endswith("ies") and len(lower) > 4:
        return word[:-3] + "y"
    if re.search(r"(x|z|ch|sh)es$", lower):
        return word[:-2]
    return word[:-1]


def _match_case(original, replacement):
    return replacement.capitalize() if original[:1].isupper() else replacement


def set_noun_number(item, plural):
    """Makes the counted noun in an ingredient's item text singular or
    plural: "eggs" -> "egg", "small onion, diced" -> "small onions, diced",
    "cubes chicken bouillon" -> "cube chicken bouillon". The noun is a known
    counting word if present, else the last word before any comma or
    parenthetical. Anything that isn't a plain word is left alone."""
    match = re.search(r"\s*[,;(]", item)
    head, rest = (item[: match.start()], item[match.start():]) if match else (item, "")
    words = head.split(" ")

    index = next(
        (i for i, w in enumerate(words) if singularize(w).lower() in COUNT_NOUNS),
        len(words) - 1,
    )
    word = words[index]
    if not word.isalpha():
        return item
    words[index] = pluralize(word) if plural else singularize(word)
    return " ".join(words) + rest
