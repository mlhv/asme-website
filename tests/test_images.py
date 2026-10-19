import io
import logging
import struct
import zlib
from datetime import datetime

import pytest

import pillow_heif
from PIL import Image

from asmesite.images import is_landscape, to_webp
from asmesite.models import DriveImage


def _jpeg(size, exif_orientation=None):
    buf = io.BytesIO()
    img = Image.new("RGB", size, (200, 30, 30))
    kwargs = {}
    if exif_orientation:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        kwargs["exif"] = exif
    img.save(buf, format="JPEG", **kwargs)
    return buf.getvalue()


def _open(data):
    return Image.open(io.BytesIO(data))


def test_large_image_downsized_keeping_aspect():
    out = to_webp(_jpeg((3000, 2000)), 1800)
    img = _open(out)
    assert img.format == "WEBP"
    assert img.size == (1800, 1200)


def test_small_image_not_upscaled():
    img = _open(to_webp(_jpeg((400, 300)), 1800))
    assert img.size == (400, 300)


def test_exif_orientation_applied():
    img = _open(to_webp(_jpeg((600, 400), exif_orientation=6), 1800))
    assert img.height > img.width


def test_heic_converts():
    buf = io.BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (64, 48), (10, 120, 200))).save(buf, format="HEIF")
    out = to_webp(buf.getvalue(), 1800)
    assert out is not None
    assert out.startswith(b"RIFF")


def test_garbage_returns_none():
    assert to_webp(b"not an image at all", 800) is None


def _broken_png():
    """Valid header; the image data chunk is followed by a chunk with a garbage type."""
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (1, 2, 3)).save(buf, format="PNG")
    png = buf.getvalue()
    i = png.index(b"IDAT")
    data = png[i + 4:i + 14]
    idat = struct.pack(">I", 10) + b"IDAT" + data + struct.pack(">I", zlib.crc32(b"IDAT" + data))
    return png[:i - 4] + idat + struct.pack(">I", 10) + b"\x00\x01\x02\x03" + b"\0" * 14


def _truncated_jpeg():
    data = _jpeg((640, 480))
    return data[:len(data) // 2]


@pytest.mark.parametrize("make", [_broken_png, _truncated_jpeg])
def test_corrupted_image_returns_none_and_warns(make, caplog):
    with caplog.at_level(logging.WARNING, logger="asmesite.images"):
        assert to_webp(make(), 800) is None
    assert "could not decode image" in caplog.text


def _drive(w, h, rotation):
    return DriveImage("x", datetime(2026, 1, 1), w, h, rotation)


def test_is_landscape_swaps_on_odd_rotation():
    assert is_landscape(_drive(4000, 3000, 0)) is True
    assert is_landscape(_drive(4000, 3000, 1)) is False
    assert is_landscape(_drive(3000, 4000, 3)) is True
    assert is_landscape(_drive(4000, 3000, 2)) is True


def test_is_landscape_unknown_size():
    assert is_landscape(_drive(None, None, 0)) is False
