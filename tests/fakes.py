from asmesite.models import DriveImage


class FakeSource:
    """Stands in for GoogleSource: sheets maps spreadsheet id -> {tab name: values}."""

    def __init__(self, sheets: dict[str, dict[str, list[list]]], images: list[DriveImage] | None = None,
                 files: dict[str, bytes] | None = None):
        self.sheets = sheets
        self.images = images or []
        self.files = files or {}
        self.downloads: list[str] = []

    def tab_names(self, spreadsheet_id):
        return list(self.sheets[spreadsheet_id])

    def values(self, spreadsheet_id, tab):
        return self.sheets[spreadsheet_id][tab]

    def recent_images(self, folder_id, limit):
        return self.images[:limit]

    def download(self, file_id):
        self.downloads.append(file_id)
        return self.files.get(file_id)
