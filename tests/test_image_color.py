import io
from pathlib import Path

import pytest
from PIL import Image, ImageCms
from werkzeug.datastructures import FileStorage

from app.images import save_recipe_image

P3_PROFILE = Path("/System/Library/ColorSync/Profiles/Display P3.icc")


def _upload(im, **save_kwargs):
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=95, **save_kwargs)
    buf.seek(0)
    return FileStorage(stream=buf, filename="photo.jpg", content_type="image/jpeg")


def _saved(tmp_path, upload):
    name = save_recipe_image(upload, tmp_path, recipe_id=1)
    return Image.open(tmp_path / name)


def _center(im):
    return im.convert("RGB").getpixel((im.width // 2, im.height // 2))


def test_saved_images_embed_srgb_profile(tmp_path):
    out = _saved(tmp_path, _upload(Image.new("RGB", (200, 100), (180, 90, 60))))
    profile = ImageCms.ImageCmsProfile(io.BytesIO(out.info["icc_profile"]))
    assert "sRGB" in ImageCms.getProfileDescription(profile)


def test_untagged_photo_colors_unchanged(tmp_path):
    out = _saved(tmp_path, _upload(Image.new("RGB", (200, 100), (180, 90, 60))))
    assert all(abs(a - b) <= 3 for a, b in zip(_center(out), (180, 90, 60)))


@pytest.mark.skipif(not P3_PROFILE.exists(), reason="needs macOS Display P3 profile")
def test_display_p3_photo_is_converted_not_washed_out(tmp_path):
    # A P3-tagged orange. Read naively as sRGB it's duller than intended;
    # converted properly, the red goes up and the blue goes down.
    p3 = (200, 100, 60)
    upload = _upload(Image.new("RGB", (200, 100), p3), icc_profile=P3_PROFILE.read_bytes())
    r, g, b = _center(_saved(tmp_path, upload))
    assert r > p3[0] + 10
    assert b < p3[2] - 10


def test_rotation_still_applied_with_color_profile(tmp_path):
    im = Image.new("RGB", (300, 100), (180, 90, 60))
    exif = im.getexif()
    exif[0x0112] = 6  # Orientation: rotate 90 CW (how phones store portrait shots)
    kwargs = {"exif": exif.tobytes()}
    if P3_PROFILE.exists():
        kwargs["icc_profile"] = P3_PROFILE.read_bytes()
    out = _saved(tmp_path, _upload(im, **kwargs))
    assert out.size == (100, 300)
