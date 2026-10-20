"""Calls the Claude API (with vision) to transcribe recipes from a scanned
PDF page image, mirroring the manual transcription rules used for the
original Phase 1 import (SPEC.md section 5.4): keep wording as written,
sub-group labels become heading ingredients, uncertain text gets a
[?guess?] marker plus needs_review, a page may hold zero to several
recipes, and margin/handwritten annotations become notes."""
import base64
from typing import Literal, Optional

import anthropic
from pydantic import BaseModel, Field


class ExtractedIngredient(BaseModel):
    kind: Literal["item", "heading"] = "item"
    raw_text: str
    no_scale: bool = False


class ExtractedRecipe(BaseModel):
    title: str
    contributor: Optional[str] = None
    source: Optional[str] = None
    servings: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    instructions_html: str = Field(
        description="Simple <p> paragraphs matching the card's breaks; "
        "<ol>/<ul> only if the card is clearly numbered or bulleted. "
        "Only p, br, strong, em, ul, ol, li tags allowed."
    )
    ingredients: list[ExtractedIngredient] = Field(default_factory=list)
    notes: list[str] = Field(
        default_factory=list,
        description='Margin or handwritten annotations, each prefixed "From original card: ".',
    )
    proposed_category: str
    needs_review: bool = False
    review_note: Optional[str] = Field(
        default=None, description="Why needs_review is set, e.g. uncertain text, no title visible, possible duplicate."
    )
    crop_box: list[float] = Field(
        description="[left, top, right, bottom] as fractions (0-1) of this page image "
        "that tightly crop just this recipe's card/section, with a small margin."
    )
    instructions_seem_incomplete: bool = Field(
        default=False,
        description="True if the instructions appear cut off at the bottom of the page "
        "(the recipe likely continues on another page).",
    )


class PageExtraction(BaseModel):
    recipes: list[ExtractedRecipe] = Field(default_factory=list)


SYSTEM_PROMPT = """You are transcribing scanned recipe cards into structured data for a personal recipe database. Follow these rules exactly:

- Keep the wording, spelling, and abbreviations exactly as written. Don't modernize or "fix" anything.
- A single page may contain zero, one, two, or three separate recipes (cards or clippings can be stacked or side by side). Return one entry per recipe actually present. If the page is blank, a cover page, or pure continuation text with no new recipe title, return an empty recipes list.
- For each recipe, give a crop_box ([left, top, right, bottom], fractions of the page 0-1) that tightly bounds just that recipe, with a small margin. If recipes are stacked vertically, split by top/bottom; include the recipe's own title line.
- Ingredients: one entry per line as written, into raw_text. Sub-group labels like "For the crust:" become kind="heading". Do not split quantity/unit/item out of raw_text yourself.
- Instructions: simple <p> paragraphs matching the card's own paragraph breaks. Use <ol>/<ul> only if the card is clearly numbered or bulleted. Only these tags are allowed: p, br, strong, em, ul, ol, li.
- If any text is illegible or uncertain, write your best guess wrapped as [?guess?] and set needs_review=true with a review_note explaining what's uncertain.
- If no title is visible on a card, invent a short descriptive title and set needs_review=true.
- Margin or handwritten annotations that aren't part of the main recipe become entries in notes, each prefixed "From original card: ".
- If the instructions look cut off at the bottom of the page (likely continuing on another page), set instructions_seem_incomplete=true and needs_review=true, and say so in review_note.
- Fill contributor only if a name is clearly shown on the card; otherwise leave it blank (unless a default contributor is given below, in which case use that only when no other name is shown).
- Fill servings, times, and source only if present on the card.
- For proposed_category, prefer reusing one of the existing categories listed below (match by meaning, not exact words) over inventing a new one. Only propose a new category name if nothing existing fits.
- If a recipe's title closely resembles one of the existing recipe titles listed below, set needs_review=true and mention the likely duplicate by name in review_note."""


def _build_user_text(existing_categories, existing_titles, default_contributor, page_num):
    lines = [f"This is page {page_num} of a scanned recipe collection."]
    if default_contributor:
        lines.append(f'Default contributor (use only when no name is shown on the card): "{default_contributor}"')
    if existing_categories:
        lines.append("Existing categories: " + ", ".join(existing_categories))
    if existing_titles:
        shown = existing_titles[:400]
        lines.append("Existing recipe titles (for duplicate detection): " + "; ".join(shown))
    lines.append("Transcribe every recipe on this page per the rules above.")
    return "\n".join(lines)


def extract_recipes_from_page(
    image_path, api_key, model, existing_categories=None, existing_titles=None,
    default_contributor=None, page_num=1,
):
    client = anthropic.Anthropic(api_key=api_key)

    with open(image_path, "rb") as f:
        image_b64 = base64.standard_b64encode(f.read()).decode("utf-8")

    user_text = _build_user_text(
        existing_categories or [], existing_titles or [], default_contributor, page_num
    )

    response = client.messages.parse(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                {"type": "text", "text": user_text},
            ],
        }],
        output_format=PageExtraction,
    )

    return response.parsed_output
