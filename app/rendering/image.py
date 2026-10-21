import pymupdf
from PIL import Image, ImageChops

# The print template puts a "Page X of Y" footer in the bottom margin; it
# means nothing in a single stacked image, so that band is cut off.
FOOTER_BAND = 0.06
MARGIN_INCHES = 0.35


def _content_box(img):
    body = img.crop((0, 0, img.width, int(img.height * (1 - FOOTER_BAND))))
    diff = ImageChops.difference(body, Image.new("RGB", body.size, "white"))
    # Ignore faint anti-aliasing/specks when finding where content ends.
    return diff.convert("L").point(lambda v: 255 if v > 24 else 0).getbbox()


def render_recipe_png(pdf_path, output_path, dpi=150):
    """Rasterizes the recipe PDF into one tall PNG trimmed to its content --
    PNG because it's the only image format browsers can put on the
    clipboard."""
    doc = pymupdf.open(str(pdf_path))
    zoom = dpi / 72
    matrix = pymupdf.Matrix(zoom, zoom)

    pages = []
    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        box = _content_box(img)
        if box:
            pages.append((img, box))
    doc.close()

    if not pages:
        Image.new("RGB", (10, 10), "white").save(str(output_path), "PNG")
        return output_path

    pad = int(MARGIN_INCHES * dpi)
    left = max(min(box[0] for _, box in pages) - pad, 0)
    right = min(max(box[2] for _, box in pages) + pad, pages[0][0].width)
    pieces = []
    for i, (img, (_, top, _, bottom)) in enumerate(pages):
        top = max(top - pad, 0) if i == 0 else max(top - pad // 2, 0)
        bottom = min(bottom + (pad if i == len(pages) - 1 else pad // 2), img.height)
        pieces.append(img.crop((left, top, right, bottom)))

    stacked = Image.new("RGB", (right - left, sum(p.height for p in pieces)), "white")
    y = 0
    for p in pieces:
        stacked.paste(p, (0, y))
        y += p.height

    stacked.save(str(output_path), "PNG", optimize=True)
    return output_path
