import logging
import re
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httplib2
import pytest
from googleapiclient.errors import HttpError

from asmesite.google_source import GoogleSource

FOLDER = "application/vnd.google-apps.folder"


def _img(id, created, meta=None):
    f = {"id": id, "mimeType": "image/jpeg", "createdTime": created}
    if meta is not None:
        f["imageMediaMetadata"] = meta
    return f


def _folder(id):
    return {"id": id, "mimeType": FOLDER, "createdTime": "2026-01-01T00:00:00.000Z"}


def _drive(pages_by_folder):
    """pages_by_folder: folder id -> list of response pages (dicts)."""
    drive = MagicMock()
    executes = drive.executes = []

    def list_(**kw):
        folder = re.search(r"'([^']+)' in parents", kw["q"]).group(1)
        pages = pages_by_folder[folder]
        idx = 0 if kw.get("pageToken") is None else int(kw["pageToken"])
        req = MagicMock()
        req.execute.side_effect = lambda **ekw: (executes.append(ekw), pages[idx])[1]
        return req

    drive.files.return_value.list.side_effect = list_
    return drive


def test_recent_images_descends_sorts_and_limits():
    drive = _drive({
        "root": [{"files": [_img("a", "2026-10-01T00:00:00.000Z"), _folder("sub")]}],
        "sub": [{"files": [_img("b", "2026-10-03T00:00:00.000Z"),
                           _img("c", "2026-09-01T00:00:00.000Z")]}],
    })
    src = GoogleSource(MagicMock(), drive)
    got = src.recent_images("root", 10)
    assert [i.id for i in got] == ["b", "a", "c"]
    assert got[0].created == datetime(2026, 10, 3, tzinfo=timezone.utc)
    assert [i.id for i in src.recent_images("root", 2)] == ["b", "a"]


def test_recent_images_follows_pages_and_maps_metadata():
    drive = _drive({"root": [
        {"files": [_img("a", "2026-10-01T12:34:56.789Z",
                        {"width": 10, "height": 20, "rotation": 3})],
         "nextPageToken": "1"},
        {"files": [_img("b", "2026-10-02T00:00:00Z")]},
    ]})
    got = GoogleSource(MagicMock(), drive).recent_images("root", 10)
    by_id = {i.id: i for i in got}
    assert (by_id["a"].width, by_id["a"].height, by_id["a"].rotation) == (10, 20, 3)
    assert (by_id["b"].width, by_id["b"].height, by_id["b"].rotation) == (None, None, 0)
    assert by_id["a"].created.tzinfo is not None
    kw = drive.files.return_value.list.call_args.kwargs
    assert kw["supportsAllDrives"] and kw["includeItemsFromAllDrives"]
    assert "trashed = false" in kw["q"]
    assert drive.executes == [{"num_retries": 3}] * 2


def test_recent_images_ignores_folder_cycles():
    drive = _drive({
        "root": [{"files": [_folder("sub")]}],
        "sub": [{"files": [_folder("root"), _img("a", "2026-10-01T00:00:00Z")]}],
    })
    got = GoogleSource(MagicMock(), drive).recent_images("root", 10)
    assert [i.id for i in got] == ["a"]


def test_values_render_options():
    sheets = MagicMock()
    get = sheets.spreadsheets.return_value.values.return_value.get
    get.return_value.execute.return_value = {"values": [[1, "x"]]}
    assert GoogleSource(sheets, MagicMock()).values("sid", "Fall") == [[1, "x"]]
    get.assert_called_once_with(
        spreadsheetId="sid", range="'Fall'",
        valueRenderOption="UNFORMATTED_VALUE", dateTimeRenderOption="SERIAL_NUMBER")
    get.return_value.execute.assert_called_once_with(num_retries=3)


def test_values_escapes_apostrophe_in_tab_name():
    sheets = MagicMock()
    get = sheets.spreadsheets.return_value.values.return_value.get
    get.return_value.execute.return_value = {"values": []}
    GoogleSource(sheets, MagicMock()).values("sid", "Fall '26")
    assert get.call_args.kwargs["range"] == "'Fall ''26'"


def test_values_empty():
    sheets = MagicMock()
    sheets.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {}
    assert GoogleSource(sheets, MagicMock()).values("sid", "Fall") == []


def test_tab_names():
    sheets = MagicMock()
    sheets.spreadsheets.return_value.get.return_value.execute.return_value = {
        "sheets": [{"properties": {"title": "A"}}, {"properties": {"title": "B"}}]}
    assert GoogleSource(sheets, MagicMock()).tab_names("sid") == ["A", "B"]
    sheets.spreadsheets.return_value.get.return_value.execute.assert_called_once_with(num_retries=3)


def _http_error(status):
    return HttpError(httplib2.Response({"status": status}), b"")


def test_download_returns_bytes():
    def fake_downloader(buf, request):
        d = MagicMock()
        d.next_chunk.side_effect = lambda **kw: (buf.write(b"data"), (None, True))[1]
        downloaders.append(d)
        return d

    downloaders = []
    with patch("asmesite.google_source.MediaIoBaseDownload", fake_downloader):
        assert GoogleSource(MagicMock(), MagicMock()).download("f") == b"data"
    downloaders[0].next_chunk.assert_called_once_with(num_retries=3)


@pytest.mark.parametrize("status", [403, 404])
def test_download_missing_returns_none_and_logs(status, caplog):
    drive = MagicMock()
    drive.files.return_value.get_media.return_value = MagicMock()
    err = _http_error(status)

    def boom(buf, request):
        d = MagicMock()
        d.next_chunk.side_effect = err
        return d

    with patch("asmesite.google_source.MediaIoBaseDownload", boom):
        with caplog.at_level(logging.WARNING):
            assert GoogleSource(MagicMock(), drive).download("fid") is None
    assert "fid" in caplog.text and str(status) in caplog.text


def test_download_other_errors_propagate():
    def boom(buf, request):
        d = MagicMock()
        d.next_chunk.side_effect = _http_error(500)
        return d

    with patch("asmesite.google_source.MediaIoBaseDownload", boom):
        with pytest.raises(HttpError):
            GoogleSource(MagicMock(), MagicMock()).download("f")


def _forbidden(reason):
    body = ('{"error": {"errors": [{"reason": "%s", "message": "m"}], "code": 403, '
            '"message": "m"}}' % reason).encode()
    return HttpError(httplib2.Response({"status": 403}), body)


def _download_raising(err):
    def boom(buf, request):
        d = MagicMock()
        d.next_chunk.side_effect = err
        return d

    return patch("asmesite.google_source.MediaIoBaseDownload", boom)


@pytest.mark.parametrize("reason", ["rateLimitExceeded", "userRateLimitExceeded",
                                    "dailyLimitExceeded", "quotaExceeded"])
def test_download_rate_limit_403_propagates(reason):
    with _download_raising(_forbidden(reason)):
        with pytest.raises(HttpError):
            GoogleSource(MagicMock(), MagicMock()).download("f")


def test_download_permission_403_returns_none():
    with _download_raising(_forbidden("insufficientFilePermissions")):
        assert GoogleSource(MagicMock(), MagicMock()).download("f") is None
