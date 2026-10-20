import pymupdf
from PIL import Image


def render_recipe_jpg(pdf_path, output_path, dpi=150):
    """Rasterizes every page of the PDF and stacks them into one tall JPG,
    for sharing over iMessage."""
    doc = pymupdf.open(str(pdf_path))
    zoom = dpi / 72
    matrix = pymupdf.Matrix(zoom, zoom)

    page_images = []
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        page_images.append(img)
    doc.close()

    max_width = max(im.width for im in page_images)
    total_height = sum(im.height for im in page_images)
    stacked = Image.new("RGB", (max_width, total_height), "white")

    y = 0
    for im in page_images:
        stacked.paste(im, (0, y))
        y += im.height

    stacked.save(str(output_path), "JPEG", quality=90)
    return output_path
