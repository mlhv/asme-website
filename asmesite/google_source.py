"""Thin wrapper over the Sheets v4 and Drive v3 APIs (read-only)."""
import io
import logging
from collections import deque
from datetime import datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from asmesite.models import DriveImage

log = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
_RETRIES = 3  # retries transient errors (5xx, 429, connection) with backoff
_FOLDER = "application/vnd.google-apps.folder"
_FIELDS = ("nextPageToken, files(id, mimeType, createdTime, "
           "imageMediaMetadata(width,height,rotation))")


_LIMIT_REASONS = {"rateLimitExceeded", "userRateLimitExceeded", "dailyLimitExceeded",
                  "quotaExceeded"}


def _is_limit_error(e: HttpError) -> bool:
    details = e.error_details if isinstance(e.error_details, list) else []
    return any(isinstance(d, dict) and d.get("reason") in _LIMIT_REASONS for d in details)


def _parse_time(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


class GoogleSource:
    def __init__(self, sheets, drive):
        self._sheets = sheets
        self._drive = drive

    @classmethod
    def from_service_account_info(cls, info: dict) -> "GoogleSource":
        creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
        return cls(
            build("sheets", "v4", credentials=creds, cache_discovery=False),
            build("drive", "v3", credentials=creds, cache_discovery=False),
        )

    def tab_names(self, spreadsheet_id: str) -> list[str]:
        meta = self._sheets.spreadsheets().get(
            spreadsheetId=spreadsheet_id, fields="sheets.properties.title",
        ).execute(num_retries=_RETRIES)
        return [s["properties"]["title"] for s in meta.get("sheets", [])]

    def values(self, spreadsheet_id: str, tab: str) -> list[list[object]]:
        quoted = tab.replace("'", "''")  # A1 notation escapes ' inside a quoted name as ''
        resp = self._sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{quoted}'",
            valueRenderOption="UNFORMATTED_VALUE",
            dateTimeRenderOption="SERIAL_NUMBER",
        ).execute(num_retries=_RETRIES)
        return resp.get("values", [])

    def recent_images(self, folder_id: str, limit: int) -> list[DriveImage]:
        images: list[DriveImage] = []
        seen = {folder_id}
        queue = deque([folder_id])
        while queue:
            current = queue.popleft()
            token = None
            while True:
                resp = self._drive.files().list(
                    q=(f"(mimeType contains 'image/' or mimeType = '{_FOLDER}') "
                       f"and '{current}' in parents and trashed = false"),
                    fields=_FIELDS,
                    pageSize=1000,
                    pageToken=token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                ).execute(num_retries=_RETRIES)
                for f in resp.get("files", []):
                    if f["mimeType"] == _FOLDER:
                        if f["id"] not in seen:
                            seen.add(f["id"])
                            queue.append(f["id"])
                        continue
                    meta = f.get("imageMediaMetadata") or {}
                    images.append(DriveImage(
                        id=f["id"],
                        created=_parse_time(f["createdTime"]),
                        width=meta.get("width"),
                        height=meta.get("height"),
                        rotation=meta.get("rotation", 0),
                    ))
                token = resp.get("nextPageToken")
                if not token:
                    break
        images.sort(key=lambda i: i.created, reverse=True)
        return images[:limit]

    def download(self, file_id: str) -> bytes | None:
        buf = io.BytesIO()
        try:
            request = self._drive.files().get_media(fileId=file_id, supportsAllDrives=True)
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk(num_retries=_RETRIES)
        except HttpError as e:
            if e.resp.status in (403, 404) and not _is_limit_error(e):
                log.warning("Could not download Drive file %s (HTTP %s)", file_id, e.resp.status)
                return None
            raise
        return buf.getvalue()
