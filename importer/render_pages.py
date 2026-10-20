"""Render every page of the source PDFs to PNG for visual inspection.

Usage: python -m importer.render_pages
"""
import pymupdf

from config import config

DPI = 250
SOURCE_PDFS = ["pdf/recipes.pdf", "pdf/recipes2.pdf"]


def render_pdf(pdf_path, out_dir):
    stem = pdf_path.split("/")[-1].removesuffix(".pdf")
    doc = pymupdf.open(pdf_path)
    zoom = DPI / 72
    matrix = pymupdf.Matrix(zoom, zoom)
    count = 0
    for page_index in range(len(doc)):
        page = doc[page_index]
        pix = page.get_pixmap(matrix=matrix)
        out_path = out_dir / f"{stem}-p{page_index + 1:03d}.png"
        pix.save(out_path)
        count += 1
    doc.close()
    return count


def main():
    config.ensure_data_dirs()
    out_dir = config.IMPORT_DIR / "pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for pdf_path in SOURCE_PDFS:
        n = render_pdf(pdf_path, out_dir)
        print(f"{pdf_path}: rendered {n} pages")
        total += n
    print(f"Total pages rendered: {total} -> {out_dir}")


if __name__ == "__main__":
    main()
