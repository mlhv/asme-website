"""Build the site: read the sheets and Drive, render into a temp dir, swap it in on success."""
import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from googleapiclient.errors import HttpError

from asmesite.content import (ContentError, parse_board, parse_competitions, parse_projects,
                              parse_settings)
from asmesite.events import TZ, split_events
from asmesite.google_source import GoogleSource
from asmesite.images import CARD_W, GRID_W, HEADSHOT_W, HERO_W, is_landscape, to_webp
from asmesite.render import SiteData, render_site
from asmesite.tracker import TrackerFormatError, parse_term

log = logging.getLogger(__name__)

PHOTO_COUNT = 12
TERMS = ("Fall", "Winter", "Spring")


def _tab(source, sheet_id: str, name: str) -> list[list] | None:
    """The tab's values, or None if the sheet has no such tab (API errors propagate)."""
    for tab in source.tab_names(sheet_id):
        if tab.strip().lower() == name.lower():
            return source.values(sheet_id, tab)
    return None


def _optional(source, sheet_id: str, name: str, parse) -> list:
    values = _tab(source, sheet_id, name)
    if values is None:
        log.warning("Tab %r not found; leaving that section empty", name)
        return []
    return parse(values)


def _read_events(source, tracker_id: str) -> list:
    tabs = source.tab_names(tracker_id)
    events, parsed = [], 0
    for term in TERMS:
        tab = next((t for t in tabs if t.strip().lower().startswith(term.lower())), None)
        if tab is None:
            log.warning("No tracker tab for %s; skipping", term)
            continue
        try:
            events += parse_term(source.values(tracker_id, tab))
            parsed += 1
        except TrackerFormatError as e:
            log.warning("Tracker tab for %s is unreadable (%s); skipping", term, e)
    if not parsed:
        raise TrackerFormatError("no usable Fall/Winter/Spring tab in the event tracker")
    return events


class _Images:
    """Downloads each Drive ID once and writes it to out/img/<id>-<width>.webp."""

    def __init__(self, source, out: Path):
        self.source, self.out = source, out
        self._bytes: dict[str, bytes | None] = {}
        self._done: dict[tuple[str, int], str | None] = {}

    def get(self, image_id: str | None, width: int) -> str | None:
        if not image_id:
            return None
        key = (image_id, width)
        if key not in self._done:
            self._done[key] = self._make(image_id, width)
        return self._done[key]

    def _make(self, image_id: str, width: int) -> str | None:
        if image_id not in self._bytes:
            self._bytes[image_id] = self.source.download(image_id)
        data = self._bytes[image_id]
        webp = to_webp(data, width) if data is not None else None
        if webp is None:
            log.warning("Image %s could not be used; leaving it out", image_id)
            return None
        rel = f"img/{image_id}-{width}.webp"
        (self.out / "img").mkdir(parents=True, exist_ok=True)
        (self.out / rel).write_bytes(webp)
        return rel


def _collect(source, content_sheet_id: str, out: Path, now: datetime) -> SiteData:
    settings_values = _tab(source, content_sheet_id, "Settings")
    if settings_values is None:
        raise ContentError("The content sheet has no 'Settings' tab")
    settings = parse_settings(settings_values)
    board = _optional(source, content_sheet_id, "Board", parse_board)
    competitions = _optional(source, content_sheet_id, "Competitions", parse_competitions)
    events = _read_events(source, settings.tracker_id)
    projects = []
    if settings.robotics_sheet_id:
        projects = _optional(source, settings.robotics_sheet_id, "Projects", parse_projects)
    upcoming, past = split_events(events, now)

    imgs = _Images(source, out)
    photos, hero, images = [], None, {}
    if settings.photos_folder_id:
        drive = source.recent_images(settings.photos_folder_id, PHOTO_COUNT)
        if not drive:
            log.warning("Photo folder has no images; check it is shared with the service account")
        for d in drive:
            path = imgs.get(d.id, GRID_W)
            if path:
                photos.append(path)
                if hero is None and is_landscape(d):
                    hero = imgs.get(d.id, HERO_W)
    else:
        log.warning("No photo folder configured; skipping photos")

    def add(image_id, width):
        path = imgs.get(image_id, width)
        if path:
            images.setdefault(image_id, path)

    for e in upcoming + past:
        add(e.cover_image_id, CARD_W)
    for c in competitions:
        add(c.photo_id, CARD_W)
    for p in projects:
        add(p.photo_id, CARD_W)
    for m in board:
        add(m.headshot_id, HEADSHOT_W)
    return SiteData(settings, upcoming, past, photos, hero, competitions, projects, board, images, now)


def _check_replaceable(out_dir: Path) -> None:
    """Refuse to delete a directory that doesn't look like a previous build."""
    if not out_dir.exists():
        return
    if (out_dir / ".git").exists():
        raise ValueError(f"Refusing to replace {out_dir}: it contains .git")
    if any(out_dir.iterdir()) and not (out_dir / "index.html").exists():
        raise ValueError(f"Refusing to replace {out_dir}: it is not empty and has no index.html")


def build(source, content_sheet_id: str, out_dir: Path, now: datetime) -> None:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    out_dir = Path(out_dir)
    _check_replaceable(out_dir)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".build-", dir=out_dir.parent))
    try:
        os.chmod(tmp, 0o755)
        render_site(_collect(source, content_sheet_id, tmp, now), tmp)
        if out_dir.exists():
            shutil.rmtree(out_dir)
        os.replace(tmp, out_dir)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Build the ASME site.")
    parser.add_argument("--out", type=Path, default=Path("dist"))
    try:
        args = parser.parse_args()
        info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        sheet_id = os.environ["CONTENT_SHEET_ID"]
        build(GoogleSource.from_service_account_info(info), sheet_id, args.out, datetime.now(TZ))
    except HttpError as e:
        # no traceback or repr: both include the request URI, which holds the sheet ID
        log.error("Build failed; the previous site stays live (Google API error %s %s)",
                  e.status_code, e.reason)
        return 1
    except Exception as e:
        log.exception("Build failed; the previous site stays live (%s: %s)", type(e).__name__, e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
