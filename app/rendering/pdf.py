import weasyprint
from flask import render_template


def render_recipe_pdf(recipe, ingredients, notes, image_path, output_path):
    html = render_template(
        "print/recipe_pdf.html",
        recipe=recipe, ingredients=ingredients, notes=notes,
        image_path=str(image_path) if image_path else None,
    )
    weasyprint.HTML(string=html).write_pdf(str(output_path))
    return output_path
