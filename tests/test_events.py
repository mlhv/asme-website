from datetime import date, datetime, time
from urllib.parse import parse_qs, urlparse

from asmesite.events import TZ, gcal_url, split_events, when_text
from asmesite.models import Event


def ev(d, s=None, en=None, name="X", description=""):
    return Event(name, description, d, s, en, "Randell 121", False, None, None)


NOW = datetime(2026, 10, 20, 18, 0, tzinfo=TZ)


def test_event_today_stays_upcoming_until_it_ends():
    up, past = split_events([ev(date(2026, 10, 20), time(17, 30), time(19, 30)),
                             ev(date(2026, 10, 20), time(9), time(10), name="morning"),
                             ev(date(2026, 10, 20), name="allday")], NOW)
    assert [e.name for e in up] == ["X", "allday"] and [e.name for e in past] == ["morning"]


def test_ordering():
    a, b, c = ev(date(2026, 9, 19), name="a"), ev(date(2026, 11, 5), name="b"), ev(date(2026, 10, 30), name="c")
    up, past = split_events([a, b, c], NOW)
    assert [e.name for e in up] == ["c", "b"] and [e.name for e in past] == ["a"]


def test_when_text():
    assert when_text(ev(date(2026, 10, 20), time(17, 30), time(19, 30))) == "Tue, Oct 20 · 5:30–7:30 PM"
    assert when_text(ev(date(2026, 12, 8), time(10), time(13))) == "Tue, Dec 8 · 10:00 AM–1:00 PM"
    assert when_text(ev(date(2026, 9, 19), time(18))) == "Sat, Sep 19 · 6:00 PM"
    assert when_text(ev(date(2026, 10, 20))) == "Tue, Oct 20"


def test_gcal_url_timed_and_all_day():
    q = parse_qs(urlparse(gcal_url(ev(date(2026, 10, 20), time(17, 30), time(19, 30), name="Collab"))).query)
    assert q["action"] == ["TEMPLATE"] and q["text"] == ["Collab"]
    assert q["dates"] == ["20261020T173000/20261020T193000"] and q["ctz"] == ["America/New_York"]
    assert q["location"] == ["Randell 121"]
    q2 = parse_qs(urlparse(gcal_url(ev(date(2026, 10, 20)))).query)
    assert q2["dates"] == ["20261020/20261021"]


def test_gcal_url_start_only_is_one_hour_and_details_optional():
    q = parse_qs(urlparse(gcal_url(ev(date(2026, 10, 20), time(23, 30)))).query)
    assert q["dates"] == ["20261020T233000/20261021T003000"]
    assert "details" not in q
    q2 = parse_qs(urlparse(gcal_url(ev(date(2026, 10, 20), description="Pizza"))).query)
    assert q2["details"] == ["Pizza"]
