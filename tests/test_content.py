import logging

import pytest

from asmesite.content import (ContentError, parse_board, parse_competitions,
                              parse_projects, parse_settings, rows_to_dicts)

TRACKER = "1AbCdEfGhIjKlMnOpQrStUvWxYz"
ROBOTICS = "9ZyXwVuTsRqPoNmLkJiHgFeDcBa"


def test_rows_to_dicts_basics():
    rows = rows_to_dicts([[" Name ", "Year"], ["Ann", 2025.0], [], ["", " "], ["Bob"]])
    assert rows == [{"name": "Ann", "year": "2025"}, {"name": "Bob", "year": ""}]


def test_settings_full():
    s = parse_settings([
        ["Setting", "Value"],
        [" event tracker link ", f"https://docs.google.com/spreadsheets/d/{TRACKER}/edit"],
        ["Robotics Sheet Link", ROBOTICS],
        ["Discord  Invite Link", "https://discord.gg/x"],
        ["Instagram Link", "https://instagram.com/x"],
        ["Contact Email", "a@b.c"],
        ["Photo Folder Link", f"https://drive.google.com/drive/folders/{TRACKER}"],
        ["Tagline", "Hi"],
        ["Intro", "Yo"],
    ])
    assert s.tracker_id == TRACKER
    assert s.robotics_sheet_id == ROBOTICS
    assert s.discord_url == "https://discord.gg/x"
    assert s.photos_folder_id == TRACKER
    assert s.photos_folder_url.endswith(TRACKER)
    assert (s.tagline, s.intro) == ("Hi", "Yo")


def test_settings_defaults_and_optional():
    s = parse_settings([["Setting", "Value"], ["Event Tracker Link", TRACKER], ["Tagline", ""]])
    assert s.tagline == "Build things. Meet engineers."
    assert s.intro.startswith("Drexel's chapter")
    assert s.robotics_sheet_id is None
    assert s.photos_folder_id is None


def test_settings_missing_tracker_raises():
    with pytest.raises(ContentError):
        parse_settings([["Setting", "Value"], ["Event Tracker Link", "nope"]])
    with pytest.raises(ContentError):
        parse_settings([["Setting", "Value"]])


def test_board_sort_and_headshot():
    members = parse_board([
        ["Name", "Role", "Major", "Year", "Headshot", "Order"],
        ["Zed", "VP", "ME", "2027", "", ""],
        ["Amy", "Pres", "ME", "2026", f"https://drive.google.com/file/d/{TRACKER}/view", 2.0],
        ["Bo", "Treas", "ME", "2026", "", "1.0"],
        ["", "Ghost", "", "", "", 0],
    ])
    assert [m.name for m in members] == ["Bo", "Amy", "Zed"]
    assert members[1].headshot_id == TRACKER
    assert members[0].order == 1.0
    assert members[2].headshot_id is None


def test_competitions_show_year_sort():
    comps = parse_competitions([
        ["Competition", "Year", "Project", "Description", "Photo", "Placement", "Team", "Show"],
        ["A", "TBD", "p", "d", "", "1st", "t", "yes"],
        ["B", 2025.0, "p", "d", "", "", "", True],
        ["C", 2026, "p", "d", "", "", "", "TRUE"],
        ["D", 2026, "p", "d", "", "", "", "No"],
        ["E", 2026, "p", "d", "", "", "", ""],
        ["F", 2024, "p", "d", "", "", "", "x"],
    ])
    assert [c.competition for c in comps] == ["C", "B", "F", "A"]
    assert [c.year for c in comps] == [2026, 2025, 2024, None]


def test_projects_ignore_extra_and_ragged():
    projects = parse_projects([
        ["Project", "Description", "Status", "Photo", "Team", "Show", "CAD Link"],
        ["Rover", "d", "Active", "", "t", "yes", "http://x"],
        ["Hidden", "d", "Active", "", "t", "no", "http://x"],
        ["Short", "d", "Done"],
        ["Ragged", "d", "Done", "", "t", "x"],
    ])
    assert [p.name for p in projects] == ["Rover", "Ragged"]
    assert projects[0].photo_id is None


def test_float_cells_normalized():
    members = parse_board([["Name", "Year"], ["Ann", 2027.0]])
    assert members[0].year == "2027"
    assert rows_to_dicts([["a"], [True], [2.5]]) == [{"a": "True"}, {"a": "2.5"}]


def test_warnings_for_skipped_and_bad_rows(caplog):
    with caplog.at_level(logging.WARNING):
        parse_board([["Name", "Role", "Headshot"], ["", "VP", ""], ["Ann", "P", "not a link!"]])
        parse_competitions([["Competition", "Project", "Show"], ["", "", "yes"], ["", "", "no"]])
        parse_projects([["Project", "Show"], ["", "yes"]])
    text = caplog.text
    assert "Board: skipping row" in text
    assert "Headshot link" in text and "Ann" in text
    assert "Competitions: skipping" in text
    assert "Projects: skipping" in text
    assert len(caplog.records) == 4
