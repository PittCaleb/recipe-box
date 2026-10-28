"""Contact sheet of thumbnails with titles: python sheet.py OUT_DIR DB SHEET.png ID ..."""
import sqlite3
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

out, db, dest = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
ids = [int(a) for a in sys.argv[4:]]
conn = sqlite3.connect(db)
font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Georgia.ttf", 18)
cols = 3
rows = (len(ids) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 410 + 10, rows * 340 + 10), "white")
d = ImageDraw.Draw(sheet)
for k, rid in enumerate(ids):
    x, y = 10 + (k % cols) * 410, 10 + (k // cols) * 340
    sheet.paste(Image.open(out / f"{rid}-thumb.png"), (x, y))
    title = conn.execute("SELECT title FROM recipes WHERE id = ?", (rid,)).fetchone()[0]
    d.text((x, y + 306), f"{rid} · {title}"[:40], font=font, fill="#333")
sheet.save(dest)
