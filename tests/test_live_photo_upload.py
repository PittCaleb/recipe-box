"""A Live Photo shared as just its movie (QuickTime, often still named .HEIC)
uploads as the still photo."""
import io
from fractions import Fraction

import av
from PIL import Image

from app.live_photo import _still_image_time, is_movie, still_from_movie
from tests.conftest import seed_recipe

RED, BLUE = (220, 30, 30), (30, 30, 220)


def _movie(rotation=None, frames=30, size=(64, 48)):
    """One second of video: red for the first half, blue for the second."""
    buf = io.BytesIO()
    with av.open(buf, "w", format="mov") as container:
        stream = container.add_stream("mpeg4", rate=30)
        stream.width, stream.height = size
        stream.pix_fmt = "yuv420p"
        if rotation is not None:
            stream.set_display_rotation(rotation)
        for i in range(frames):
            frame = av.VideoFrame.from_image(Image.new("RGB", size, RED if i < frames // 2 else BLUE))
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return buf.getvalue()


def _close(pixel, color, tolerance=40):
    return all(abs(a - b) <= tolerance for a, b in zip(pixel, color))


def _upload(client, rid, data, filename="IMG_0052.HEIC", content_type="image/heic"):
    return client.post(f"/recipes/{rid}/image", data={"image": (io.BytesIO(data), filename, content_type)},
                       content_type="multipart/form-data", follow_redirects=True)


def test_live_photo_movie_named_heic_uploads_as_its_still(client, db, cfg):
    rid = seed_recipe(db, title="Live Photo")
    resp = _upload(client, rid, _movie())
    assert b"File is not a readable image." not in resp.data
    name = db.execute("SELECT image_filename FROM recipes WHERE id = ?", (rid,)).fetchone()[0]
    with Image.open(cfg.IMAGES_DIR / name) as im:
        assert im.format == "JPEG"
        assert im.size == (64, 48)
        assert _close(im.getpixel((32, 24)), BLUE)  # the middle frame, with no still-image mark


def test_sideways_movie_is_turned_upright(client, db, cfg):
    rid = seed_recipe(db, title="Portrait Live Photo")
    _upload(client, rid, _movie(rotation=-90))
    name = db.execute("SELECT image_filename FROM recipes WHERE id = ?", (rid,)).fetchone()[0]
    with Image.open(cfg.IMAGES_DIR / name) as im:
        assert im.size == (48, 64)


def test_movie_sent_as_quicktime_or_octet_stream(client, db, cfg):
    for content_type in ("video/quicktime", "application/octet-stream"):
        rid = seed_recipe(db, title=f"Sent as {content_type}")
        _upload(client, rid, _movie(), filename="IMG_0052.MOV", content_type=content_type)
        assert db.execute("SELECT image_filename FROM recipes WHERE id = ?", (rid,)).fetchone()[0]


def test_not_a_movie_is_still_refused(client, db):
    rid = seed_recipe(db, title="Junk")
    junk = b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 200  # looks like a movie, isn't one
    resp = _upload(client, rid, junk)
    assert b"File is not a readable image." in resp.data
    assert db.execute("SELECT image_filename FROM recipes WHERE id = ?", (rid,)).fetchone()[0] is None


def test_is_movie():
    assert is_movie(_movie())
    assert not is_movie(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
    assert not is_movie(b"\x00\x00\x00\x18ftypheic" + b"\x00" * 20)  # a real HEIC still


class _Packet:
    def __init__(self, pts, payload):
        self.pts, self._payload = pts, payload

    def __bytes__(self):
        return self._payload


class _Stream:
    def __init__(self, kind, frames, packets):
        self.type, self.frames, self.time_base, self.packets = kind, frames, Fraction(1, 600), packets


class _Container:
    def __init__(self, *streams):
        self.streams = list(streams)

    def seek(self, offset):
        pass

    def demux(self, stream):
        return iter(stream.packets)


def test_still_image_time_is_read_from_the_marker_track():
    # As in a real iPhone Live Photo: another one-sample track first, then the marker.
    other = _Stream("data", 1, [_Packet(0, b"\x00\x00\x00\n\x00\x00\x00\x01\x00\x06")])
    marker = _Stream("data", 1, [_Packet(760, b"\x00\x00\x00\x09\x00\x00\x00\x01\xff" + b"\x00\x00\x00\x10" + bytes(12))])
    assert _still_image_time(_Container(_Stream("video", 61, []), other, marker)) == 760 / 600
    assert _still_image_time(_Container(other)) is None


def test_still_from_movie_ignores_pictures():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "PNG")
    assert still_from_movie(buf.getvalue()) is None
