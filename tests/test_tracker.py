import json
from datetime import date, time
from pathlib import Path

import pytest

from asmesite.models import Event
from asmesite.tracker import TrackerFormatError, parse_term

FIXTURE = json.loads(Path("tests/fixtures/tracker_fall.json").read_text())


def test_published_fall_events():
    names = [e.name for e in parse_term(FIXTURE)]
    assert names == ["3D Pen Workshop", "Fall GBM", "SASE x Temple IEEE x ASME Collab",
                     "Soldering Workshop", "3D Blind Boxes (Smiski)"]


def test_event_fields():
    e = next(e for e in parse_term(FIXTURE) if e.name == "SASE x Temple IEEE x ASME Collab")
    assert e.date == date(2026, 10, 20)
    assert (e.start, e.end) == (time(17, 30), time(19, 30))
    assert e.location == "Bossone Auditorium"
    assert e.rsvp_required is True and e.rsvp_link is None


def test_uses_event_form_approved_not_purchase_request():
    # The fixture's one Purchase Request "Approved" checkmark sits on an event whose
    # Event Form is not approved; that event must stay hidden.
    pr = next(i for i, r in enumerate(FIXTURE) if r[0] == "Purchase Request")
    approved = next(r for r in FIXTURE[pr:] if r[1] == "Approved")
    [col] = [c for c, v in enumerate(approved) if c >= 2 and v is True]
    event_row = next(r for r in FIXTURE if r[1] == "Event")
    assert event_row[col] == "Unpublished Event 1"
    assert "Unpublished Event 1" not in [e.name for e in parse_term(FIXTURE)]


def test_fixture_has_nameless_column_that_is_ignored():
    event_row = next(r for r in FIXTURE if r[1] == "Event")
    width = max(len(r) for r in FIXTURE)
    assert any(not (event_row[c] if c < len(event_row) else None) for c in range(2, width))
    assert len(parse_term(FIXTURE)) == 5


def test_rows_found_by_label_after_shuffle():
    header, rest = FIXTURE[:2], FIXTURE[2:]
    shuffled = header + [["", "Drafted", True, True]] + list(reversed(rest[:7])) + rest[7:]
    # General Info rows reversed + a new row; Event Form block untouched
    assert len(parse_term(shuffled)) == 5


def test_text_in_date_and_time_cells():
    grid = [[None, "Event", "A", "B"], [None, "Date", "TBD", 46315.0],
            [None, "Start Time", None, "6pm"], ["Event Form", "Approved", True, True]]
    [only] = parse_term(grid)
    assert only.name == "B" and only.start is None


def test_rsvp_link_and_cover_image_rows():
    grid = [[None, "Event", "A"], [None, "Date", 46315.0], [None, "RSVP?", "Yes"],
            [None, "RSVP Link", " https://forms.gle/x "],
            [None, "Cover Image", "https://drive.google.com/file/d/1AbC_dEf-123456789/view"],
            ["Event Form", "Approved", True]]
    [e] = parse_term(grid)
    assert e.rsvp_link == "https://forms.gle/x" and e.cover_image_id == "1AbC_dEf-123456789"


def test_location_whitespace_collapsed_and_description_trimmed():
    grid = [[None, "Event", "A"], [None, "Date", 46315.0], [None, "Location", "  Randell   121 "],
            [None, "Event Description", "Line one.\n\n\n\nLine two.\n\n"], ["Event Form", "Approved", True]]
    [e] = parse_term(grid)
    assert e.location == "Randell 121" and e.description == "Line one.\n\nLine two."


def test_approved_as_text_true():
    grid = [[None, "Event", "A"], [None, "Date", 46315.0], ["Event Form", "Approved", "TRUE"]]
    assert len(parse_term(grid)) == 1


def test_no_event_row_raises():
    with pytest.raises(TrackerFormatError):
        parse_term([[None, "Week", 1]])


def test_private_fields_never_reach_event():
    assert set(Event.__dataclass_fields__) == {"name", "description", "date", "start", "end",
        "location", "rsvp_required", "rsvp_link", "cover_image_id"}


@pytest.mark.parametrize("bad", [20261020.0, 1e12, float("inf"), float("nan")])
def test_absurd_date_serial_skips_event_without_raising(bad):
    grid = [[None, "Event", "A", "B"], [None, "Date", bad, 46315.0],
            ["Event Form", "Approved", True, True]]
    assert [e.name for e in parse_term(grid)] == ["B"]


@pytest.mark.parametrize("bad", [float("inf"), float("nan")])
def test_absurd_time_serial_gives_none(bad):
    grid = [[None, "Event", "A"], [None, "Date", 46315.0], [None, "Start Time", bad],
            ["Event Form", "Approved", True]]
    [e] = parse_term(grid)
    assert e.start is None


def test_event_form_header_with_note_still_publishes():
    grid = [[None, "Event", "A"], [None, "Date", 46315.0],
            ["Event Form - due 2 wks before", "Approved", True]]
    assert [e.name for e in parse_term(grid)] == ["A"]


def test_note_row_between_event_form_and_approved_raises():
    grid = [[None, "Event", "A"], [None, "Date", 46315.0], ["Event Form", "Due", None],
            ["remember to submit early", "", None], [None, "Approved", True]]
    with pytest.raises(TrackerFormatError, match="Event Form"):
        parse_term(grid)


def test_no_date_row_raises():
    grid = [[None, "Event", "A"], ["Event Form", "Approved", True]]
    with pytest.raises(TrackerFormatError, match="Date"):
        parse_term(grid)
