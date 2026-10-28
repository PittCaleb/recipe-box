import io
from datetime import datetime

from PIL import Image, ImageCms, ImageOps

SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
SRGB_ICC = SRGB.tobytes()

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_LONG_SIDE = 1600
THUMB_LONG_SIDE = 400
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


class InvalidImage(ValueError):
    pass


def thumb_filename(filename):
    if filename.endswith(".jpg"):
        return filename[: -len(".jpg")] + "-thumb.jpg"
    return filename + "-thumb.jpg"


def _resized(im, long_side):
    w, h = im.size
    longest = max(w, h)
    if longest <= long_side:
        return im
    scale = long_side / longest
    return im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)


def _to_srgb(im, icc):
    """Converts using the photo's embedded color profile. Phone and Mac
    photos are usually Display P3; dropping that profile without converting
    makes browsers read the pixels as sRGB, which looks washed out."""
    if icc:
        try:
            source = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            if im.mode not in ("RGB", "CMYK", "L"):
                im = im.convert("RGB")
            return ImageCms.profileToProfile(im, source, SRGB, outputMode="RGB")
        except (ImageCms.PyCMSError, OSError, ValueError):
            pass
    return im.convert("RGB")


def save_recipe_image(file_storage, images_dir, recipe_id):
    """Validates and processes an uploaded photo, saving a full-size (max 1600px)
    and a 400px thumbnail JPEG. Returns the main image filename."""
    data = file_storage.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise InvalidImage("Image is larger than 25 MB.")

    content_type = (file_storage.content_type or "").lower()
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise InvalidImage(f"Unsupported image type: {content_type}")

    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception as exc:
        raise InvalidImage("File is not a readable image.") from exc

    icc = im.info.get("icc_profile")
    im = ImageOps.exif_transpose(im)
    return save_image_files(_to_srgb(im, icc), images_dir, recipe_id)


def save_image_files(im, images_dir, recipe_id):
    """Saves an RGB image as the recipe's full-size (max 1600px) and 400px
    thumbnail JPEGs. Returns the main image filename."""
    full = _resized(im, MAX_LONG_SIDE)
    thumb = _resized(im, THUMB_LONG_SIDE)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"recipe-{recipe_id}-{timestamp}.jpg"

    full.save(images_dir / filename, "JPEG", quality=85, icc_profile=SRGB_ICC)
    thumb.save(images_dir / thumb_filename(filename), "JPEG", quality=85, icc_profile=SRGB_ICC)

    return filename


def delete_recipe_image(images_dir, filename):
    if not filename:
        return
    for name in (filename, thumb_filename(filename)):
        path = images_dir / name
        if path.exists():
            path.unlink()
