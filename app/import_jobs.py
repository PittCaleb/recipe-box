"""Background worker for the "upload a new PDF" import flow: renders pages,
calls the Claude API per page to transcribe recipes, crops a scan image per
recipe, and stages everything in import_batch_recipes for review before
anything touches the real recipes table."""
import json
import threading
import traceback
from datetime import datetime

from app.claude_import import extract_recipes_from_page
from app.db import get_connection
from app.ingredients.textcase import title_case_ingredient
from app.sanitize import sanitize_instructions
from importer.crop_scans import crop_one
from importer.render_pages import render_pdf


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _clamp_box(box):
    if not box or len(box) != 4:
        return [0.0, 0.0, 1.0, 1.0]
    left, top, right, bottom = (max(0.0, min(1.0, v)) for v in box)
    if right <= left:
        right = min(1.0, left + 0.1)
    if bottom <= top:
        bottom = min(1.0, top + 0.1)
    return [left, top, right, bottom]


def _update_batch(conn, batch_id, **fields):
    fields["updated_at"] = _now()
    cols = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE import_batches SET {cols} WHERE id = ?", (*fields.values(), batch_id))
    conn.commit()


def start_import_job(cfg, batch_id, pdf_filename, default_contributor):
    thread = threading.Thread(
        target=_run_import_job, args=(cfg, batch_id, pdf_filename, default_contributor), daemon=True
    )
    thread.start()
    return thread


def _run_import_job(cfg, batch_id, pdf_filename, default_contributor):
    conn = get_connection(cfg.DB_PATH)
    try:
        _run(conn, cfg, batch_id, pdf_filename, default_contributor)
    except Exception as exc:
        traceback.print_exc()
        _update_batch(conn, batch_id, status="error", error_message=str(exc))
    finally:
        conn.close()


def _run(conn, cfg, batch_id, pdf_filename, default_contributor):
    pages_dir = cfg.IMPORT_DIR / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    _update_batch(conn, batch_id, status="rendering")
    pdf_path = str(cfg.PDF_DIR / pdf_filename)
    total_pages = render_pdf(pdf_path, pages_dir)
    _update_batch(conn, batch_id, status="transcribing", total_pages=total_pages)

    existing_categories = [
        r["name"] for r in conn.execute("SELECT DISTINCT name FROM categories ORDER BY name").fetchall()
    ]
    existing_titles = [r["title"] for r in conn.execute("SELECT title FROM recipes").fetchall()]

    page_errors = []
    staged_titles = []

    for page_num in range(1, total_pages + 1):
        stem = pdf_filename.removesuffix(".pdf")
        image_path = pages_dir / f"{stem}-p{page_num:03d}.png"

        try:
            extraction = extract_recipes_from_page(
                image_path,
                api_key=cfg.ANTHROPIC_API_KEY,
                model=cfg.IMPORT_MODEL,
                existing_categories=existing_categories,
                existing_titles=existing_titles + staged_titles,
                default_contributor=default_contributor,
                page_num=page_num,
            )
        except Exception as exc:
            page_errors.append(f"page {page_num}: {exc}")
            _update_batch(conn, batch_id, processed_pages=page_num)
            continue

        for idx, recipe in enumerate(extraction.recipes):
            letter = chr(97 + idx)
            scan_filename = f"batch{batch_id}-p{page_num:03d}-{letter}.jpg"
            box = _clamp_box(recipe.crop_box)
            try:
                crop_one(
                    pages_dir, cfg.SCANS_DIR,
                    {"source_pdf": pdf_filename, "source_page": page_num, "box": box, "scan_filename": scan_filename},
                )
            except Exception as exc:
                page_errors.append(f"page {page_num} recipe '{recipe.title}': crop failed ({exc})")
                scan_filename = None

            review_note = recipe.review_note or ""
            if recipe.instructions_seem_incomplete:
                extra = "Instructions may be cut off and continue on another page."
                review_note = f"{review_note} {extra}".strip()

            conn.execute(
                """INSERT INTO import_batch_recipes
                   (batch_id, source_page, title, contributor, source, servings, prep_time,
                    cook_time, instructions_html, proposed_category, needs_review, review_note,
                    scan_filename, ingredients_json, notes_json, included)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (
                    batch_id, page_num, recipe.title, recipe.contributor, recipe.source,
                    recipe.servings, recipe.prep_time, recipe.cook_time,
                    sanitize_instructions(recipe.instructions_html), recipe.proposed_category,
                    1 if recipe.needs_review else 0, review_note or None, scan_filename,
                    json.dumps([
                        {**i.model_dump(), "raw_text": title_case_ingredient(i.kind, i.raw_text)}
                        for i in recipe.ingredients
                    ]),
                    json.dumps(recipe.notes),
                ),
            )
            staged_titles.append(recipe.title)

        conn.commit()
        _update_batch(conn, batch_id, processed_pages=page_num)

    error_message = "; ".join(page_errors) if page_errors else None
    _update_batch(conn, batch_id, status="ready", error_message=error_message)
