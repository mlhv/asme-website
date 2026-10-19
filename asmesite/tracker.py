"""Turn the transposed event tracker tab into public Events.

Only whitelisted rows are ever read, so private columns (costs, leads, etc.)
cannot reach an Event.
"""
import logging
import re
from datetime import date, time, timedelta

from asmesite.ids import drive_id
from asmesite.models import Event

log = logging.getLogger(__name__)

_EPOCH = date(1899, 12, 30)
_FIRST_EVENT_COL = 2
_WANTED = {"event", "event description", "date", "start time", "end time", "location",
           "rsvp?", "rsvp link", "cover image"}


class TrackerFormatError(Exception):
    pass


def _is_number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def serial_to_date(v: object) -> date | None:
    if not _is_number(v):
        return None
    try:
        return _EPOCH + timedelta(days=int(v))
    except (OverflowError, ValueError):
        return None


def serial_to_time(v: object) -> time | None:
    if not _is_number(v):
        return None
    try:
        minutes = round((v % 1) * 1440) % 1440
    except (OverflowError, ValueError):
        return None
    return time(minutes // 60, minutes % 60)


def _truthy(v: object) -> bool:
    if v is True:
        return True
    return isinstance(v, str) and v.strip().lower() in {"true", "yes", "x"}


def _text(v: object) -> str:
    return "" if v is None else str(v).strip()


def _cell(row: list[object] | None, col: int) -> object:
    return row[col] if row is not None and col < len(row) else None


def _description(v: object) -> str:
    lines = [line.rstrip() for line in _text(v).splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines))


def _index_rows(grid: list[list[object]]) -> dict[str, list[object]]:
    rows: dict[str, list[object]] = {}
    section = ""
    for row in grid:
        a = _text(row[0]) if row else ""
        if a:
            section = a
        label = _text(row[1]).lower() if len(row) > 1 else ""
        if label == "approved":
            if not section.lower().startswith("event form"):
                continue
        elif label not in _WANTED:
            continue
        rows.setdefault(label, row)
    return rows


def parse_term(grid: list[list[object]]) -> list[Event]:
    rows = _index_rows(grid)
    if "event" not in rows:
        raise TrackerFormatError("no row labeled 'Event' in tracker tab")
    if "date" not in rows:
        raise TrackerFormatError("no row labeled 'Date' in tracker tab")
    if "approved" not in rows:
        raise TrackerFormatError("no 'Approved' row in the 'Event Form' section of tracker tab")

    events = []
    for col in range(_FIRST_EVENT_COL, len(rows["event"])):
        name = _text(rows["event"][col])
        if not name:
            continue

        def get(label: str) -> object:
            return _cell(rows.get(label), col)

        if not _truthy(get("approved")):
            continue
        event_date = serial_to_date(get("date"))
        if event_date is None:
            if _text(get("date")):
                log.warning("Unparseable date for event %r", name)
            continue
        times = []
        for label in ("start time", "end time"):
            t = serial_to_time(get(label))
            if t is None and _text(get(label)):
                log.warning("Unparseable %s for event %r", label, name)
            times.append(t)
        events.append(Event(
            name=name,
            description=_description(get("event description")),
            date=event_date,
            start=times[0],
            end=times[1],
            location=" ".join(_text(get("location")).split()),
            rsvp_required=_truthy(get("rsvp?")),
            rsvp_link=_text(get("rsvp link")) or None,
            cover_image_id=drive_id(_text(get("cover image"))),
        ))
    return events
