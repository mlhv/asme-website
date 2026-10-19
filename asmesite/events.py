"""Event display helpers: upcoming/past split, readable times, calendar links."""
from datetime import datetime, time, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from asmesite.models import Event

TZ = ZoneInfo("America/New_York")
_GCAL = "https://calendar.google.com/calendar/render"


def ends_at(e: Event) -> datetime:
    t = e.end or e.start or time(23, 59)
    return datetime.combine(e.date, t, tzinfo=TZ)


def split_events(events: list[Event], now: datetime) -> tuple[list[Event], list[Event]]:
    upcoming = [e for e in events if ends_at(e) >= now]
    past = [e for e in events if ends_at(e) < now]
    upcoming.sort(key=lambda e: (e.date, e.start or time.max))
    past.sort(key=lambda e: (e.date, e.start or time.max), reverse=True)
    return upcoming, past


def _clock(t: time, meridiem: bool = True) -> str:
    text = f"{t.hour % 12 or 12}:{t.minute:02d}"
    return f"{text} {'AM' if t.hour < 12 else 'PM'}" if meridiem else text


def when_text(e: Event) -> str:
    day = f"{e.date:%a, %b} {e.date.day}"
    if e.start is None:
        return day
    if e.end is None:
        return f"{day} · {_clock(e.start)}"
    same = (e.start.hour < 12) == (e.end.hour < 12)
    return f"{day} · {_clock(e.start, not same)}–{_clock(e.end)}"


def gcal_url(e: Event) -> str:
    if e.start is None:
        dates = f"{e.date:%Y%m%d}/{e.date + timedelta(days=1):%Y%m%d}"
    else:
        start = datetime.combine(e.date, e.start)
        end = datetime.combine(e.date, e.end) if e.end else start + timedelta(hours=1)
        dates = f"{start:%Y%m%dT%H%M%S}/{end:%Y%m%dT%H%M%S}"
    params = {"action": "TEMPLATE", "text": e.name, "dates": dates,
              "ctz": TZ.key, "location": e.location}
    if e.description:
        params["details"] = e.description
    return f"{_GCAL}?{urlencode(params)}"
