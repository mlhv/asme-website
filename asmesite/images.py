"""Convert downloaded Drive photos (JPEG, PNG, iPhone HEIC) to resized WebP."""
import io
import logging

import pillow_heif
from PIL import Image, ImageOps

from asmesite.models import DriveImage

log = logging.getLogger(__name__)

pillow_heif.register_heif_opener()

HERO_W = 1800
GRID_W = 800
CARD_W = 800
HEADSHOT_W = 320

_QUALITY = 80


def to_webp(data: bytes, max_width: int) -> bytes | None:
    """Return WebP bytes no wider than max_width, or None if the bytes can't be read."""
    try:
        with Image.open(io.BytesIO(data)) as src:
            img = ImageOps.exif_transpose(src).convert("RGB")
    except Exception as e:
        # A damaged file can raise almost anything (OSError, SyntaxError, ValueError, ...)
        log.warning("could not decode image (%s)", type(e).__name__)
        return None
    if img.width > max_width:
        height = max(1, round(img.height * max_width / img.width))
        img = img.resize((max_width, height), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=_QUALITY)
    return out.getvalue()


def is_landscape(img: DriveImage) -> bool:
    if img.width is None or img.height is None:
        return False
    w, h = (img.height, img.width) if img.rotation in (1, 3) else (img.width, img.height)
    return w > h
