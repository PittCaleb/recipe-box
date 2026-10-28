"""Pulls the still photo out of a Live Photo's movie.

An iPhone Live Photo is a HEIC still plus a short QuickTime movie, and
sharing or saving one sometimes hands over only the movie, still named
.HEIC. Pillow can't read a movie, so for those this decodes the frame at the
moment Apple marked as the photo ("still-image-time"), or the middle frame
when there's no mark, turned the right way up."""
import io

import av

# Movie files start with a box whose type is "ftyp" (QuickTime, MP4, HEIC).
_MOVIE_BRANDS = (b"qt  ", b"isom", b"iso2", b"mp41", b"mp42", b"M4V ", b"avc1")

# A still-image-time sample starts with a 9-byte item: size 9, key 1, value -1
# (other items can follow it in the same sample).
_STILL_IMAGE_TIME = b"\x00\x00\x00\x09\x00\x00\x00\x01\xff"


def is_movie(data):
    return data[4:8] == b"ftyp" and data[8:12] in _MOVIE_BRANDS


def _still_image_time(container):
    """Seconds into the movie where the photo was taken, or None."""
    for stream in container.streams:
        if stream.type != "data" or stream.frames != 1:
            continue
        container.seek(0)
        for packet in container.demux(stream):
            if packet.pts is not None and bytes(packet).startswith(_STILL_IMAGE_TIME):
                return float(packet.pts * stream.time_base)
    return None


def still_from_movie(data):
    """The photo frame as an upright RGB PIL image, or None if this isn't a
    movie with video in it."""
    if not is_movie(data):
        return None
    try:
        with av.open(io.BytesIO(data), format="mov") as container:
            videos = list(container.streams.video)
            if not videos:
                return None
            # Live Photos carry small helper tracks too; the photo is the biggest.
            video = max(videos, key=lambda s: (s.codec_context.width or 0) * (s.codec_context.height or 0))
            target = _still_image_time(container)
            if target is None:
                duration = (video.duration * video.time_base) if video.duration else 0
                target = float(duration) / 2

            container.seek(0)
            best = None
            for frame in container.decode(video):
                if best is None or abs(frame.time - target) < abs(best.time - target):
                    best = frame
                elif frame.time > target:
                    break
            if best is None:
                return None
            # rotation is the display matrix's counterclockwise angle; PIL's
            # rotate() is counterclockwise too.
            return best.to_image().rotate(best.rotation, expand=True) if best.rotation else best.to_image()
    except (av.FFmpegError, ValueError):
        return None
