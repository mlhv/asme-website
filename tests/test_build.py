import copy
import io
import json
import logging
from datetime import datetime
from pathlib import Path

import pytest
from PIL import Image

from asmesite import build as build_mod
from asmesite.build import build, main
from asmesite.content import ContentError
from asmesite.events import TZ
from asmesite.models import DriveImage
from asmesite.tracker import TrackerFormatError
from fakes import FakeSource

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=TZ)
FALL = json.loads((Path(__file__).parent / "fixtures" / "tracker_fall.json").read_text())
ROBOTICS = "robo-id"
SETTINGS = [
    ["Setting", "Value"],
    ["Event Tracker Link", "https://docs.google.com/spreadsheets/d/trk123/edit"],
    ["Discord Invite Link", "https://discord.gg/x"],
    ["Instagram Link", "https://instagram.com/x"],
    ["Contact Email", "asme@example.edu"],
    ["Photo Folder Link", "https://drive.google.com/drive/folders/photofolder"],
]


def jpeg(w=40, h=20):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), "red").save(buf, format="JPEG")
    return buf.getvalue()


def sheets(tracker=None, settings=SETTINGS, board=None, extra=None):
    content = {"Settings": settings, "Board": board or [["Name", "Role"]],
               "Competitions": [["Competition", "Project"]]}
    if settings is None:
        del content["Settings"]
    content.update(extra or {})
    return {"content": content, "trk123": tracker if tracker is not None else {"Fall 2026": FALL}}


def run(tmp_path, src, **kw):
    out = tmp_path / "dist"
    build(src, "content", out, NOW, **kw)
    return out


def test_end_to_end_with_fixture(tmp_path):
    out = run(tmp_path, FakeSource(sheets()))
    html = (out / "index.html").read_text()
    order = ["SASE x Temple IEEE x ASME Collab", "Soldering Workshop", "3D Blind Boxes (Smiski)",
             "Fall GBM", "3D Pen Workshop"]
    positions = [html.index(n) for n in order]
    assert positions == sorted(positions)
    assert not any(tmp_path.glob(".build-*"))


def test_private_values_never_in_output(tmp_path):
    grid = copy.deepcopy(FALL)
    grid.insert(14, [None, "Estimated Cost", 98765, 98765, 98765, 98765, 98765, 98765])
    grid.insert(3, [None, "Event Lead", "SECRET-LEAD", "SECRET-LEAD", "SECRET-LEAD"])
    grid.insert(13, ["Marketing", "Discord", "fake-handle-123", "fake-handle-123", "fake-handle-123"])
    out = run(tmp_path, FakeSource(sheets({"Fall": grid})))
    files = [p for p in out.rglob("*") if p.is_file()]
    assert files
    for p in files:
        data = p.read_bytes()
        for secret in (b"98765", b"SECRET-LEAD", b"fake-handle-123"):
            assert secret not in data, p


def test_missing_term_tab_is_skipped(tmp_path):
    assert (run(tmp_path, FakeSource(sheets({"Fall 2026": FALL}))) / "index.html").exists()


def test_bad_term_is_skipped_but_good_one_builds(tmp_path):
    out = run(tmp_path, FakeSource(sheets({"Fall": FALL, "Winter": [["nothing"]]})))
    assert "Soldering Workshop" in (out / "index.html").read_text()


def test_no_term_tabs_raises(tmp_path):
    with pytest.raises(TrackerFormatError):
        run(tmp_path, FakeSource(sheets({"Notes": FALL})))


def test_every_term_failing_raises(tmp_path):
    with pytest.raises(TrackerFormatError):
        run(tmp_path, FakeSource(sheets({"Fall": [["nothing"]]})))


def test_missing_settings_raises_and_out_dir_untouched(tmp_path):
    out = tmp_path / "dist"
    out.mkdir()
    (out / "index.html").write_text("old")
    with pytest.raises(ContentError):
        build(FakeSource(sheets(settings=None)), "content", out, NOW)
    assert (out / "index.html").read_text() == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["dist"]


def test_render_failure_leaves_out_dir_untouched(tmp_path, monkeypatch):
    out = tmp_path / "dist"
    out.mkdir()
    (out / "index.html").write_text("old")

    def boom(data, d):
        d.mkdir(exist_ok=True)
        raise RuntimeError("boom")
    monkeypatch.setattr(build_mod, "render_site", boom)
    with pytest.raises(RuntimeError):
        build(FakeSource(sheets()), "content", out, NOW)
    assert (out / "index.html").read_text() == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["dist"]


def test_creates_missing_parent(tmp_path):
    out = tmp_path / "a" / "b" / "dist"
    build(FakeSource(sheets()), "content", out, NOW)
    assert (out / "index.html").exists()


def test_unreadable_image_uses_placeholder(tmp_path):
    board = [["Name", "Role", "Headshot"],
             ["Minh Le", "President", "https://drive.google.com/file/d/missingid1/view"]]
    out = run(tmp_path, FakeSource(sheets(board=board)))
    html = (out / "index.html").read_text()
    assert "Minh Le" in html and "ML" in html
    assert not (out / "img").exists() or not list((out / "img").glob("missingid1*"))


def test_images_written_and_referenced(tmp_path):
    board = [["Name", "Role", "Headshot"],
             ["Minh Le", "President", "https://drive.google.com/file/d/headid12345/view"]]
    photos = [DriveImage("portrait1", NOW, 20, 40, 0), DriveImage("wide1", NOW, 40, 20, 0),
              DriveImage("broken1", NOW, 40, 20, 0)]
    src = FakeSource(sheets(board=board), photos,
                     {"headid12345": jpeg(), "portrait1": jpeg(20, 40), "wide1": jpeg()})
    out = run(tmp_path, src)
    html = (out / "index.html").read_text()
    for name in ("img/wide1-1800.webp", "img/wide1-800.webp", "img/portrait1-800.webp",
                 "img/headid12345-320.webp"):
        assert (out / name).is_file()
        assert name in html
    assert not list((out / "img").glob("broken1*"))
    assert src.downloads.count("wide1") == 1


def test_no_photos_folder_skips_photos(tmp_path):
    settings = [r for r in SETTINGS if r[0] != "Photo Folder Link"]
    out = run(tmp_path, FakeSource(sheets(settings=settings)))
    assert 'id="photos"' not in (out / "index.html").read_text()


def test_robotics_projects_tab(tmp_path):
    settings = SETTINGS + [["Robotics Sheet Link", "https://docs.google.com/spreadsheets/d/robo-id/edit"]]
    s = sheets(settings=settings)
    s["robo-id"] = {"Projects": [["Project", "Description", "Show"], ["Demo Arm", "Moves.", "yes"]]}
    out = run(tmp_path, FakeSource(s))
    assert "Demo Arm" in (out / "index.html").read_text()
    s["robo-id"] = {}
    assert (run(tmp_path, FakeSource(s)) / "index.html").exists()


def test_google_error_propagates(tmp_path):
    settings = SETTINGS + [["Robotics Sheet Link", "https://docs.google.com/spreadsheets/d/robo-id/edit"]]
    with pytest.raises(KeyError):  # FakeSource has no such spreadsheet, like an API error
        run(tmp_path, FakeSource(sheets(settings=settings)))


def test_naive_now_rejected(tmp_path):
    with pytest.raises(ValueError):
        build(FakeSource(sheets()), "content", tmp_path / "dist", datetime(2026, 10, 18))


def test_main_returns_nonzero_without_env(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    monkeypatch.delenv("CONTENT_SHEET_ID", raising=False)
    monkeypatch.setattr("sys.argv", ["build", "--out", str(tmp_path / "dist")])
    assert main() == 1


def test_main_google_error_hides_request_uri(monkeypatch, tmp_path, caplog):
    import httplib2
    from googleapiclient.errors import HttpError

    err = HttpError(httplib2.Response({"status": 403}),
                    b'{"error": {"code": 403, "message": "The caller does not have permission"}}',
                    uri="https://sheets.googleapis.com/v4/spreadsheets/FAKESHEETID42/values")

    def boom(*a, **kw):
        raise err
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("CONTENT_SHEET_ID", "FAKESHEETID42")
    monkeypatch.setattr(build_mod.GoogleSource, "from_service_account_info", lambda info: None)
    monkeypatch.setattr(build_mod, "build", boom)
    monkeypatch.setattr("sys.argv", ["build", "--out", str(tmp_path / "dist")])
    assert main() == 1
    assert "FAKESHEETID42" not in caplog.text
    assert "Google API error 403" in caplog.text
    assert all(r.exc_info is None for r in caplog.records)


def test_refuses_non_site_out_dir(tmp_path):
    out = tmp_path / "docs"
    out.mkdir()
    (out / "notes.txt").write_text("keep me")
    with pytest.raises(ValueError):
        build(FakeSource(sheets()), "content", out, NOW)
    assert (out / "notes.txt").read_text() == "keep me"
    assert [p.name for p in tmp_path.iterdir()] == ["docs"]


def test_refuses_out_dir_with_git(tmp_path):
    out = tmp_path / "repo"
    (out / ".git").mkdir(parents=True)
    (out / "index.html").write_text("old")
    with pytest.raises(ValueError):
        build(FakeSource(sheets()), "content", out, NOW)
    assert (out / ".git").is_dir() and (out / "index.html").read_text() == "old"


def test_empty_existing_out_dir_is_fine(tmp_path):
    out = tmp_path / "dist"
    out.mkdir()
    build(FakeSource(sheets()), "content", out, NOW)
    assert (out / "index.html").exists()


def test_empty_photo_folder_warns(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger="asmesite.build"):
        run(tmp_path, FakeSource(sheets()))
    assert "shared with the service account" in caplog.text
