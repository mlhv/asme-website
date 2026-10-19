import re

_PATTERNS = [
    re.compile(r"/d/([A-Za-z0-9_-]+)"),
    re.compile(r"/folders/([A-Za-z0-9_-]+)"),
    re.compile(r"[?&]id=([A-Za-z0-9_-]+)"),
]
_BARE = re.compile(r"^[A-Za-z0-9_-]{15,}$")


def drive_id(url_or_id: str | None) -> str | None:
    """Extract a Google Drive/Sheets ID from a URL or bare ID; None if not found."""
    if not url_or_id:
        return None
    text = url_or_id.strip()
    for pattern in _PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    if _BARE.match(text):
        return text
    return None
