"""Crop recipe scans out of rendered page PNGs, using boxes recorded in crops.json.

Usage: python -m importer.crop_scans
"""
import json

from PIL import Image

from config import config

MAX_LONG_SIDE = 2000


def crop_one(pages_dir, scans_dir, entry):
    src = pages_dir / f"{entry['source_pdf'].removesuffix('.pdf')}-p{entry['source_page']:03d}.png"
    im = Image.open(src)
    w, h = im.size
    left, top, right, bottom = entry["box"]
    box = (int(left * w), int(top * h), int(right * w), int(bottom * h))
    cropped = im.crop(box).convert("RGB")

    cw, ch = cropped.size
    long_side = max(cw, ch)
    if long_side > MAX_LONG_SIDE:
        scale = MAX_LONG_SIDE / long_side
        cropped = cropped.resize((int(cw * scale), int(ch * scale)), Image.LANCZOS)

    out_path = scans_dir / entry["scan_filename"]
    cropped.save(out_path, "JPEG", quality=90)
    return out_path


def main():
    config.ensure_data_dirs()
    pages_dir = config.IMPORT_DIR / "pages"
    scans_dir = config.SCANS_DIR
    crops_path = config.IMPORT_DIR / "crops.json"
    crops = json.loads(crops_path.read_text())

    count = 0
    for entry in crops:
        crop_one(pages_dir, scans_dir, entry)
        count += 1
    print(f"Cropped {count} scans -> {scans_dir}")


if __name__ == "__main__":
    main()
