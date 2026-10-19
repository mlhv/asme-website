# Drexel ASME Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A single-page, white-and-blue static site for Drexel ASME. It is rebuilt every 3 hours from private Google Sheets and Drive, so the board never touches code.

**Architecture:** A Python build script (`asmesite`) reads the event tracker, the Website Content sheet, the Robotics Projects sheet, and the photo folder through a club-owned Google service account. It extracts only whitelisted public fields, processes images to WebP, and renders one Jinja template to `dist/`. A GitHub Actions cron job runs tests and then the build, and deploys `dist/` to GitHub Pages. A failed build never deploys, so the last good site stays live.

**Tech Stack:** Python ≥3.12, `google-api-python-client` + `google-auth`, Jinja2, Pillow + `pillow-heif`, pytest + BeautifulSoup4 (tests), vanilla HTML/CSS/JS, GitHub Actions + GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-10-18-asme-website-design.md`

## Global Constraints

- **Never emit private tracker fields.** Only these may leave the parser: Event, Event Description, Date, Start Time, End Time, Location, RSVP?, RSVP Link, Cover Image. Costs, spend, leads, teams, forms, purchase requests, advertising, and marketing rows (including Discord handles) must never reach models, `dist/`, logs, or the repo.
- **Publish rule:** an event is shown only when it has a Date **and** the `Approved` row inside the `Event Form` section is checked.
- Find tracker rows by the label in column B, never by position. The section is the most recent non-empty column A value.
- Display timezone is `America/New_York`.
- The raw tracker `.xlsx` is never committed. Test fixtures are sanitized.
- A Google error or an unparseable sheet fails the build (no deploy). A single bad row or event is skipped with a `logging` warning.
- Visual style is "Bright & airy": white plus a `#f6f9fe` tint for alternating sections, accent `#1565d8`, ink `#0f1f3a`, muted `#4a5b78`, border `#e1e9f5`, rounded cards with a soft shadow, and mobile first.
- The free host address is `https://drexel-asme.github.io` (GitHub org `drexel-asme`, owned by `drexelasme.technical@gmail.com`, with `drexelasme@gmail.com` as a second owner).
- Board-facing column and setting names are plain English, exactly as listed in Task 4.
- Join copy (verbatim): "No sign-up needed — join the Discord, follow us on Instagram, and come to any event."
- Empty upcoming copy (verbatim): "New events coming soon — follow us on Instagram."

## Review Focus

1. **The board inserts, deletes, or reorders tracker rows**, or a new year's tracker adds a `Drafted` row. Parsing must be unaffected (Task 2: `test_rows_found_by_label_after_shuffle`).
2. **Text typed into a Date or Time cell** ("TBD", "6pm") **or a whole term tab missing** (e.g. no `Winter` tab yet). The event is treated as having no date or time, and the term is skipped with a warning (Task 2: `test_text_in_date_and_time_cells`; Task 8: `test_missing_term_tab_is_skipped`).
3. **An event happening today.** It stays in "Upcoming" until its end time passes, and an event with no times stays until the end of its day (Task 3: `test_event_today_stays_upcoming_until_it_ends`).
4. **A linked image the service account can't read, or an iPhone HEIC photo.** The first falls back to a placeholder without failing the build, and the second converts to WebP (Task 6: `test_heic_converts`; Task 8: `test_unreadable_image_uses_placeholder`).
5. **GitHub disables cron workflows after 60 days with no repo activity**, which would silently freeze the site over summer. A keepalive step resets the timer (Task 9 verification). Also: **HTML or script typed into a description** must be escaped (Task 7: `test_description_is_escaped`).

---

## File Structure

```
asmesite/
  __init__.py
  ids.py            drive_id(): pull a file/folder/sheet ID out of any Google URL
  models.py         frozen dataclasses: Event, BoardMember, Competition, Project, Settings, DriveImage
  tracker.py        parse the transposed tracker grid -> list[Event] (pure)
  events.py         split upcoming/past, Google Calendar link, display formatting (pure)
  content.py        parse Website Content + Robotics sheets -> Settings / lists (pure)
  google_source.py  thin wrapper over Sheets + Drive APIs
  images.py         bytes -> resized WebP; landscape check
  render.py         SiteData + Jinja -> dist/index.html + static assets
  build.py          orchestrate, fail-safe, CLI entry point
  templates/index.html.j2
  static/style.css, static/app.js, static/hero-fallback.jpg
scripts/make_fixture.py       one-off: xlsx -> sanitized JSON fixture
sheet-templates/*.csv         importable starter tabs for the new sheets
tests/fixtures/tracker_fall.json
tests/test_*.py
.github/workflows/build.yml
docs/BOARD_GUIDE.md, docs/TECHNICAL.md
pyproject.toml, .gitignore, README.md
```

---

### Task 1: Scaffold, models, and ID parsing

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `README.md`, `asmesite/__init__.py`, `asmesite/models.py`, `asmesite/ids.py`
- Test: `tests/test_ids.py`

**Interfaces:**
- Produces:
  - `drive_id(url_or_id: str | None) -> str | None`
  - Dataclasses in `asmesite/models.py`, all `@dataclass(frozen=True)`:
    - `Event(name: str, description: str, date: date, start: time | None, end: time | None, location: str, rsvp_required: bool, rsvp_link: str | None, cover_image_id: str | None)`
    - `BoardMember(name: str, role: str, major: str, year: str, headshot_id: str | None, order: float)`
    - `Competition(competition: str, year: int | None, project: str, description: str, photo_id: str | None, placement: str, team: str)`
    - `Project(name: str, description: str, status: str, photo_id: str | None, team: str)`
    - `Settings(tracker_id: str, robotics_sheet_id: str | None, discord_url: str, instagram_url: str, contact_email: str, photos_folder_url: str, photos_folder_id: str | None, tagline: str, intro: str)`
    - `DriveImage(id: str, created: datetime, width: int | None, height: int | None, rotation: int)`

- [ ] **Step 1: Initialize the repo.** Run `git init -b main`. In `.gitignore`, ignore `.superpowers/`, `dist/`, `.venv/`, `__pycache__/`, `*.xlsx`, `service-account*.json`, and `.env`. In `pyproject.toml`, declare the package `asmesite`, `requires-python = ">=3.12"`, and the runtime deps `google-api-python-client`, `google-auth`, `jinja2`, `pillow`, `pillow-heif`, with the `dev` extra `pytest` and `beautifulsoup4`. Set `[tool.pytest.ini_options] testpaths = ["tests"]` and package data to include `templates/*` and `static/*`. Run `python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'`. It should install with no errors.

- [ ] **Step 2: Write failing tests** in `tests/test_ids.py`:

```python
from asmesite.ids import drive_id

ID = "1AbC_dEf-123456789"

def test_file_url():        assert drive_id(f"https://drive.google.com/file/d/{ID}/view?usp=sharing") == ID
def test_open_id_url():     assert drive_id(f"https://drive.google.com/open?id={ID}") == ID
def test_folder_url():      assert drive_id(f"https://drive.google.com/drive/folders/{ID}?usp=drive_link") == ID
def test_sheet_url():       assert drive_id(f"https://docs.google.com/spreadsheets/d/{ID}/edit#gid=0") == ID
def test_bare_id():         assert drive_id(f"  {ID} ") == ID
def test_blank_and_none():  assert drive_id("") is None and drive_id(None) is None
def test_non_google_text(): assert drive_id("see instagram") is None
```

- [ ] **Step 3: Run** `.venv/bin/pytest tests/test_ids.py -v`. Expected: FAIL (`ModuleNotFoundError`).

- [ ] **Step 4: Implement** `models.py` (the dataclasses above, no behavior) and `drive_id` in `ids.py`. Use regexes for `/d/<id>`, `/folders/<id>`, and `[?&]id=<id>`. A bare token matching `^[A-Za-z0-9_-]{15,}$` is an ID. Anything else returns `None`.

- [ ] **Step 5: Run** `.venv/bin/pytest -v`. Expected: all PASS.

- [ ] **Step 6: Commit.** Run `git add -A && git commit -m "chore: scaffold asmesite package, models, drive_id"`. The spec and plan docs are included in this first commit.

---

### Task 2: Tracker parser

**Files:**
- Create: `scripts/make_fixture.py`, `tests/fixtures/tracker_fall.json`, `asmesite/tracker.py`
- Test: `tests/test_tracker.py`

**Interfaces:**
- Consumes: `Event`, `drive_id`
- Produces:
  - `serial_to_date(v: object) -> date | None`: Sheets serial (days since 1899-12-30); `bool`/str/None → None
  - `serial_to_time(v: object) -> time | None`: fractional day (0.75 → 18:00), rounded to the minute
  - `parse_term(grid: list[list[object]]) -> list[Event]`: grid is the raw `UNFORMATTED_VALUE`/`SERIAL_NUMBER` values of one tab (ragged rows allowed). Returns published events only.
  - `class TrackerFormatError(Exception)`: raised by `parse_term` when no row labeled `Event` exists.

Fixture facts (from the real 26-27 Fall tab): event columns start at column C (index 2). Column L has no Event name but has a cost total, so it must be ignored. In Fall, these five are published (dated and Event-Form-Approved): **3D Pen Workshop (2026-09-19), Fall GBM (09-29), SASE x Temple IEEE x ASME Collab (10-20), Soldering Workshop (11-05), 3D Blind Boxes (Smiski) (11-10)**. The four other events have Event Form Approved = FALSE (the sanitized fixture renames them "Unpublished Event 1-4"). One unpublished event has Purchase Request Approved = TRUE, which proves it is excluded only if the right `Approved` row is used.

- [ ] **Step 1: Write `scripts/make_fixture.py <xlsx> <out.json>`.** Using `openpyxl` (a dev-only import inside the script), read the `Fall` sheet and keep only rows whose column-B label is in {Week, Event, Event Description, Event Level, Date, Start Time, End Time, Location, RSVP?, Due, Submitted, Approved}. Keep column A on kept rows so the section headers stay. Convert `datetime` → serial float and `time` → day fraction. Write a JSON list of rows. Run it on `~/Downloads/Event Tracking Sheet 26-27.xlsx`, then grep `tests/fixtures/tracker_fall.json` for known private values from the sheet (a cost, a lead's name, a Discord handle). Expected: no output (the fixture is sanitized).

- [ ] **Step 2: Write failing tests** in `tests/test_tracker.py`:

```python
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
    assert "Unpublished Event 1" not in [e.name for e in parse_term(FIXTURE)]

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
```

- [ ] **Step 3: Run** `.venv/bin/pytest tests/test_tracker.py -v`. Expected: FAIL (`ImportError`).

- [ ] **Step 4: Implement** `tracker.py`. Walk the rows tracking `section` (the last non-blank, stripped column A). Key each row by `label.strip().lower()`, except `approved`, which is captured only while `section.lower() == "event form"`. The first occurrence of each label wins. An event column is any index ≥2 with a non-blank `Event` cell. Booleans accept `True` or the case-insensitive strings `"true"`, `"yes"`, `"x"`. For descriptions, strip, collapse 3+ newlines to 2, and rstrip each line. For locations, collapse internal whitespace. Log a warning (event name only, never other cells) when a non-blank Date or Time cell can't be parsed.

- [ ] **Step 5: Run** `.venv/bin/pytest tests/test_tracker.py -v`. Expected: all PASS.

- [ ] **Step 6: Commit.** Run `git add asmesite/tracker.py scripts tests && git commit -m "feat: parse event tracker with publish rule and field whitelist"`

---

### Task 3: Event helpers

**Files:**
- Create: `asmesite/events.py`
- Test: `tests/test_events.py`

**Interfaces:**
- Consumes: `Event`
- Produces:
  - `TZ = ZoneInfo("America/New_York")`
  - `ends_at(e: Event) -> datetime`: aware datetime. Uses the end time, else the start time, else 23:59 on the event's date.
  - `split_events(events: list[Event], now: datetime) -> tuple[list[Event], list[Event]]`: (upcoming soonest-first, past newest-first). Upcoming means `ends_at(e) >= now`.
  - `when_text(e: Event) -> str`: `"Tue, Oct 20 · 5:30–7:30 PM"`, `"Sat, Sep 19 · 6:00 PM"` (start only), `"Tue, Oct 20"` (no times). Uses `10:00 AM–1:00 PM` when the meridiem differs.
  - `gcal_url(e: Event) -> str`

- [ ] **Step 1: Write failing tests:**

```python
def ev(d, s=None, en=None, name="X"):
    return Event(name, "", d, s, en, "Randell 121", False, None, None)

NOW = datetime(2026, 10, 20, 18, 0, tzinfo=TZ)

def test_event_today_stays_upcoming_until_it_ends():
    up, past = split_events([ev(date(2026,10,20), time(17,30), time(19,30)),
                             ev(date(2026,10,20), time(9), time(10), name="morning"),
                             ev(date(2026,10,20), name="allday")], NOW)
    assert [e.name for e in up] == ["X", "allday"] and [e.name for e in past] == ["morning"]

def test_ordering():
    a, b, c = ev(date(2026,9,19), name="a"), ev(date(2026,11,5), name="b"), ev(date(2026,10,30), name="c")
    up, past = split_events([a, b, c], NOW)
    assert [e.name for e in up] == ["c", "b"] and [e.name for e in past] == ["a"]

def test_when_text():
    assert when_text(ev(date(2026,10,20), time(17,30), time(19,30))) == "Tue, Oct 20 · 5:30–7:30 PM"
    assert when_text(ev(date(2026,12,8), time(10), time(13))) == "Tue, Dec 8 · 10:00 AM–1:00 PM"
    assert when_text(ev(date(2026,9,19), time(18))) == "Sat, Sep 19 · 6:00 PM"
    assert when_text(ev(date(2026,10,20))) == "Tue, Oct 20"

def test_gcal_url_timed_and_all_day():
    q = parse_qs(urlparse(gcal_url(ev(date(2026,10,20), time(17,30), time(19,30), name="Collab"))).query)
    assert q["action"] == ["TEMPLATE"] and q["text"] == ["Collab"]
    assert q["dates"] == ["20261020T173000/20261020T193000"] and q["ctz"] == ["America/New_York"]
    assert q["location"] == ["Randell 121"]
    q2 = parse_qs(urlparse(gcal_url(ev(date(2026,10,20)))).query)
    assert q2["dates"] == ["20261020/20261021"]
```

- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_events.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `events.py`. The base URL is `https://calendar.google.com/calendar/render`. A start-only event defaults to a 1-hour duration in the calendar link. Include `details` only when the description is non-empty.
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_events.py -v`. Expected: PASS.
- [ ] **Step 5: Commit.** Run `git add asmesite/events.py tests/test_events.py && git commit -m "feat: event split, display text, calendar links"`

---

### Task 4: Website Content and Robotics sheet parsers

**Files:**
- Create: `asmesite/content.py`, `sheet-templates/Settings.csv`, `sheet-templates/Board.csv`, `sheet-templates/Competitions.csv`, `sheet-templates/Projects.csv`
- Test: `tests/test_content.py`

**Exact board-facing names (fixed here, used in templates and docs):**
- Website Content sheet, tab **Settings**: columns `Setting | Value`. Rows: `Event Tracker Link`, `Robotics Sheet Link`, `Discord Invite Link`, `Instagram Link`, `Contact Email`, `Photo Folder Link`, `Tagline`, `Intro`.
- Tab **Board**: `Name | Role | Major | Year | Headshot | Order`
- Tab **Competitions**: `Competition | Year | Project | Description | Photo | Placement | Team | Show`
- Robotics sheet, tab **Projects**: `Project | Description | Status | Photo | Team | Show` (other columns are allowed and ignored)

**Interfaces:**
- Consumes: models, `drive_id`
- Produces:
  - `class ContentError(Exception)`
  - `rows_to_dicts(values: list[list[object]]) -> list[dict[str, str]]`: the first row is the header. Keys are lowercased and stripped, values are `str(v).strip()`, blank rows are dropped, and missing cells become `""`.
  - `parse_settings(values) -> Settings`: raises `ContentError` if `Event Tracker Link` has no valid ID. Defaults: `tagline="Build things. Meet engineers."`, `intro="Drexel's chapter of the American Society of Mechanical Engineers: workshops, competitions, robotics, and free food."`
  - `parse_board(values) -> list[BoardMember]`: skips rows with no Name. Sorts by Order (blank → last), then Name.
  - `parse_competitions(values) -> list[Competition]`: keeps only rows with Show = yes/true/x. Sorts by Year descending (blank last). A non-numeric Year becomes `None`.
  - `parse_projects(values) -> list[Project]`: keeps only shown rows, in sheet order.

- [ ] **Step 1: Write failing tests** covering: settings keys are matched case- and space-insensitively (`" event tracker link "`); a missing tracker link raises `ContentError`; tagline and intro defaults apply when blank; board sort with a blank Order and a Headshot URL resolving to an ID; Competitions `Show` blank/`No` hidden while `yes`/`TRUE` is shown; Year `"2025"` → 2025 and `"TBD"` → None, sorted 2026, 2025, None; Projects ignores an extra column `CAD Link`; a ragged row shorter than the header doesn't crash.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_content.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `content.py` and write the four CSVs with headers plus one example row each. Settings.csv lists every setting name with an empty Value.
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_content.py -v`. Expected: PASS.
- [ ] **Step 5: Commit.** Run `git add asmesite/content.py sheet-templates tests/test_content.py && git commit -m "feat: parse website content and robotics sheets"`

---

### Task 5: Google API wrapper

**Files:**
- Create: `asmesite/google_source.py`
- Test: `tests/test_google_source.py`

**Interfaces:**
- Consumes: `DriveImage`
- Produces `class GoogleSource` (the build depends only on these four methods, and the tests in Task 8 use a fake with the same shape):
  - `GoogleSource.from_service_account_info(info: dict) -> GoogleSource`: scopes `spreadsheets.readonly` and `drive.readonly`
  - `tab_names(spreadsheet_id: str) -> list[str]`
  - `values(spreadsheet_id: str, tab: str) -> list[list[object]]`: `valueRenderOption="UNFORMATTED_VALUE"`, `dateTimeRenderOption="SERIAL_NUMBER"`, range `f"'{tab}'"`
  - `recent_images(folder_id: str, limit: int) -> list[DriveImage]`: breadth-first through subfolders, `trashed = false`, `mimeType contains 'image/'`, paginated, newest `createdTime` first, truncated to `limit`
  - `download(file_id: str) -> bytes | None`: returns `None` and logs a warning on `HttpError` 403/404. Other errors propagate.
- The constructor takes the built `sheets` and `drive` service objects, so tests inject `unittest.mock.MagicMock`s.

- [ ] **Step 1: Write failing tests** with mocked services: `recent_images` descends into a subfolder, sorts across folders by `createdTime`, follows `nextPageToken`, maps `imageMediaMetadata.width/height/rotation` (missing → `None`/`0`), and respects `limit`. `download` returns `None` for a mocked `HttpError` with status 404, and raises for status 500. `values` passes `UNFORMATTED_VALUE` and `SERIAL_NUMBER`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_google_source.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** Use `googleapiclient.http.MediaIoBaseDownload` for downloads. Pass `supportsAllDrives=True, includeItemsFromAllDrives=True` on list calls.
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_google_source.py -v`. Expected: PASS.
- [ ] **Step 5: Commit.** Run `git add asmesite/google_source.py tests/test_google_source.py && git commit -m "feat: Google Sheets/Drive source wrapper"`

---

### Task 6: Image processing

**Files:**
- Create: `asmesite/images.py`
- Test: `tests/test_images.py`

**Interfaces:**
- Produces:
  - `to_webp(data: bytes, max_width: int) -> bytes | None`: registers `pillow_heif`, applies `ImageOps.exif_transpose`, converts to RGB, downsizes only (never upscales) to `max_width`, and saves WebP at quality 80. Returns `None` and logs a warning if Pillow can't open the bytes.
  - `is_landscape(img: DriveImage) -> bool`: swaps width and height when `rotation in (1, 3)`. Unknown size → `False`.
  - Size constants: `HERO_W = 1800`, `GRID_W = 800`, `CARD_W = 800`, `HEADSHOT_W = 320`

- [ ] **Step 1: Write failing tests:** a 3000×2000 JPEG → WebP 1800 wide with aspect preserved; a 400 px image stays 400; an EXIF orientation-6 portrait JPEG comes out portrait; `test_heic_converts` builds a HEIC in memory with `pillow_heif.from_pillow(...).save(buf, format="HEIF")` and asserts the output starts with `b"RIFF"`; garbage bytes → `None`; `is_landscape` with rotation 1 on a 4000×3000 image → `False`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_images.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `images.py`.
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_images.py -v`. Expected: PASS.
- [ ] **Step 5: Commit.** Run `git add asmesite/images.py tests/test_images.py && git commit -m "feat: image resize/HEIC to WebP"`

---

### Task 7: Page template and renderer

**Files:**
- Create: `asmesite/render.py`, `asmesite/templates/index.html.j2`, `asmesite/static/style.css`, `asmesite/static/app.js`, `asmesite/static/hero-fallback.jpg` (a plain blue gradient JPEG generated with Pillow, 1800×1000)
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: models, `when_text`, `gcal_url`
- Produces:
  - `@dataclass SiteData(settings: Settings, upcoming: list[Event], past: list[Event], photos: list[str], hero: str | None, competitions: list[Competition], projects: list[Project], board: list[BoardMember], images: dict[str, str], built_at: datetime)`. `photos` and `hero` are site-relative paths. `images` maps a Drive ID → site-relative path for cover images, headshots, and competition/project photos (a missing key means use the placeholder).
  - `render_site(data: SiteData, out_dir: Path) -> None`: writes `out_dir/index.html` and copies `static/` to `out_dir/static/`. Jinja `autoescape=True`. Filters: `when`, `gcal`, `img` (ID → path or `None`), `initials` ("Minh Le" → "ML").

**Page contract (section `id`s are the nav anchors):** the sticky header with "ASME · Drexel" and links Events, Photos, Competitions, Projects, Board, Join. Then:
- `#top` hero with the tagline, intro, and two buttons (Join our Discord → `discord_url`, Instagram → `instagram_url`), with the hero photo or the fallback behind a white-to-transparent overlay for legibility.
- `#events`: upcoming cards, each a `<button class="event-card" data-dialog="ev-N">` opening a `<dialog id="ev-N">` that holds the description paragraphs, an RSVP button (only if `rsvp_required` and `rsvp_link`), and "Add to Google Calendar". If there are no upcoming events, show the verbatim empty copy linked to Instagram.
- `#earlier`: an "Earlier this year" compact list (date · name), shown only if `past` is non-empty.
- `#photos`: a grid plus "See all photos →" linking to `photos_folder_url`, shown only if photos exist.
- `#competitions` and `#projects`: cards with photo-or-blue-placeholder, title, meta line, description, and team. Shown only if non-empty.
- `#board`: circular headshots or an initials placeholder, with name, role, and major/year.
- `#join` footer: the verbatim join copy, both buttons, `mailto:` contact email, and "Updated {built_at}".

All external links use `rel="noopener"`. Fonts come from Google Fonts Inter. `app.js` only opens and closes dialogs (with a backdrop click to close), so the page still reads fine without JS. The layout is one column under 640 px, and event cards are a 3-up grid at ≥900 px.

- [ ] **Step 1: Write failing tests** with BeautifulSoup on rendered output, using a `SiteData` factory: nav anchors all resolve to section `id`s; the dialog for an event with `rsvp_required=True, rsvp_link=None` has no RSVP link, and the one with both has a link; the empty upcoming list shows the exact empty copy; empty competitions → no `#competitions` section and no nav link to it; a board member with no headshot renders initials; the join copy is present verbatim; `test_description_is_escaped` (description `"<script>alert(1)</script>"` → no `<script>` tag inside the dialog, and the escaped text is present); `static/style.css` exists in `out_dir`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_render.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the template, CSS (with the Global Constraints colors as `:root` custom properties), JS, and `render.py`. The navbar hides links to sections that are absent.
- [ ] **Step 4: Run** `.venv/bin/pytest tests/test_render.py -v`. Expected: PASS.
- [ ] **Step 5: Visual check.** Run `.venv/bin/python -m asmesite.render --demo dist` (a `__main__` that renders sample data built from the five real Fall events). Then open `dist/index.html` at 390 px and 1280 px widths. Expected: it matches the approved "Bright & airy" mockup, with no horizontal scroll at 390 px and dialogs that open and close.
- [ ] **Step 6: Commit.** Run `git add asmesite tests/test_render.py && git commit -m "feat: single-page template and renderer"`

---

### Task 8: Build orchestrator and fail-safety

**Files:**
- Create: `asmesite/build.py`
- Test: `tests/test_build.py`, `tests/fakes.py`

**Interfaces:**
- Consumes: everything above. Any object with `tab_names / values / recent_images / download` (the `GoogleSource` shape).
- Produces:
  - `PHOTO_COUNT = 12`, `TERMS = ("Fall", "Winter", "Spring")`
  - `build(source, content_sheet_id: str, out_dir: Path, now: datetime) -> None`
  - `main() -> int`: reads env `GOOGLE_SERVICE_ACCOUNT_JSON` (JSON text) and `CONTENT_SHEET_ID`, plus CLI `--out` (default `dist`). Returns non-zero on any exception, with a log line saying the previous site stays live. Invoked as `python -m asmesite.build`.

**Flow:** Read the content sheet tabs `Settings`, `Board`, and `Competitions` (missing `Settings` → `ContentError`; missing Board/Competitions → empty plus a warning). Then read the tracker. For each term, the tab whose name starts with the term (case-insensitive) is passed to `parse_term`. A missing term tab is skipped with a warning. If no term tab exists or every term raises `TrackerFormatError`, raise. Then the robotics sheet's `Projects` tab, if `robotics_sheet_id` is set. Then split events at `now`. Then `recent_images(photos_folder_id, PHOTO_COUNT)`, where the hero is the first `is_landscape` photo. Download and convert every referenced image ID once to `out_dir/img/<id>-<width>.webp`. If `download` or `to_webp` returns `None`, the ID is left out of `SiteData.images`. Build into a temp dir and move it to `out_dir` only on success.

- [ ] **Step 1: Write `tests/fakes.py`** with a `FakeSource(sheets: dict[str, dict[str, list[list]]], images: list[DriveImage], files: dict[str, bytes])`, where unknown file IDs → `None`.
- [ ] **Step 2: Write failing tests:**
  - `test_end_to_end_with_fixture`: the Fall fixture plus minimal content at `now=2026-10-18 12:00 ET`. Upcoming names are SASE, Soldering, Smiski, and past is Fall GBM, 3D Pen, in that order in the HTML.
  - `test_private_values_never_in_output`: add rows `Estimated Cost`=`98765`, `Event Lead`=`SECRET-LEAD`, and a marketing row `fake-handle-123` to the Fall grid. Then `grep` every file under `out_dir` for those strings and expect none.
  - `test_missing_term_tab_is_skipped`: tracker with only `Fall` → builds.
  - `test_no_term_tabs_raises`.
  - `test_missing_settings_raises_and_out_dir_untouched`: a pre-existing `out_dir/index.html` is left unchanged.
  - `test_unreadable_image_uses_placeholder`: headshot ID not in `files` → build succeeds and initials render.
  - `test_main_returns_nonzero_without_env`.
- [ ] **Step 3: Run** `.venv/bin/pytest tests/test_build.py -v`. Expected: FAIL.
- [ ] **Step 4: Implement** `build.py`.
- [ ] **Step 5: Run** `.venv/bin/pytest -v`. Expected: the whole suite PASSES.
- [ ] **Step 6: Commit.** Run `git add asmesite/build.py tests && git commit -m "feat: build orchestrator with fail-safe output"`

---

### Task 9: Scheduled build and deploy

**Files:**
- Create: `.github/workflows/build.yml`

**Workflow contract:** triggers on `schedule: cron "17 */3 * * *"`, `workflow_dispatch`, and `push` to `main`. Permissions: `contents: write` (keepalive), `pages: write`, `id-token: write`. `concurrency: pages`. The build job runs on `ubuntu-latest` with `actions/setup-python@v5` (3.12) and pip cache. It runs `pip install -e '.[dev]'`, then `pytest`, then `python -m asmesite.build --out dist` with `GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}` and `CONTENT_SHEET_ID: ${{ vars.CONTENT_SHEET_ID }}`, then `actions/upload-pages-artifact@v3` (path `dist`). The deploy job `needs: build` and uses `actions/deploy-pages@v4`. A keepalive step uses `gautamkrishnar/keepalive-workflow@2.0.10` with `use_api: true` so cron isn't disabled after 60 idle days. Any failed step stops the run before deploy, so the previous site stays.

- [ ] **Step 1: Write** `build.yml`.
- [ ] **Step 2: Lint.** Run `pipx run check-jsonschema --builtin-schema vendor.github-workflows .github/workflows/build.yml`. Expected: `ok -- validation done`.
- [ ] **Step 3: Commit.** Run `git add .github && git commit -m "ci: scheduled build and GitHub Pages deploy"`

---

### Task 10: Documentation

**Files:**
- Create: `docs/BOARD_GUIDE.md`, `docs/TECHNICAL.md`; Modify: `README.md`

- [ ] **Step 1: Write `docs/BOARD_GUIDE.md`** in plain language with no code. Cover:
  - How an event gets on the site: fill in the Date and check Event Form → Approved; optionally add an RSVP Link and a Cover Image (upload the image to **Website Images** first).
  - "Copy the tab, don't rearrange it."
  - How to add the two new rows `RSVP Link` and `Cover Image` under General Info, and that row order doesn't matter but the label text does.
  - Photos: drop them in the dump folder, and the newest 12 appear.
  - Updating the board after elections, adding a competition project (Show = Yes), and the robotics team's Projects tab.
  - New school year: paste the new tracker's link into Settings → Event Tracker Link, and share it with the service-account email (written out in full).
  - Changes appear within about 3 hours; ask the Technical Coordinator if it's urgent.
  - Recommendation: share the tracker with board accounts plus the service account only, not "anyone with the link."
- [ ] **Step 2: Write `docs/TECHNICAL.md`.** Cover:
  - The architecture diagram (text).
  - An account table: GitHub org `drexel-asme`, owners `drexelasme.technical@gmail.com` and `drexelasme@gmail.com`; Google Cloud project owned by the technical account with the President as Owner; the service-account email; where `GOOGLE_SERVICE_ACCOUNT_JSON` (secret) and `CONTENT_SHEET_ID` (variable) live.
  - Rotating the key.
  - A local run: put the JSON in `.env`, then `python -m asmesite.build`, then open `dist/index.html`.
  - Running `make_fixture.py` for a new tracker format.
  - "When the scheduled build fails" triage, based on the failed-workflow email and the job log.
  - The turnover checklist: pass the role-account password, remove the old personal admins.
- [ ] **Step 3: Update `README.md`** to a one-paragraph summary that links both guides.
- [ ] **Step 4: Commit.** Run `git add docs README.md && git commit -m "docs: board guide and technical handoff"`

---

### Task 11: Go live (with the Technical Coordinator)

These steps need the club accounts, so the Technical Coordinator performs them with the implementer guiding. Each ends with a check.

- [ ] **Step 1: Accounts.** Signed in as `drexelasme.technical@gmail.com`, create the GitHub org `drexel-asme` (add `drexelasme@gmail.com`'s GitHub user as owner) and a Google Cloud project `drexel-asme-website` (add `drexelasme@gmail.com` as Owner). Enable the Sheets and Drive APIs, create service account `website-builder`, and download its JSON key. Check: `gcloud iam service-accounts list` or the console shows the account.
- [ ] **Step 2: Move and create files.** Transfer ownership of the tracker, the photo dump folder, and the robotics sheet to the technical account. Create the **Website Content** sheet (import the four `sheet-templates/*.csv` as tabs; Projects goes to the robotics sheet) and the **Website Images** folder. Share all five with the service-account email as Viewer. Check: Settings is filled in with real links.
- [ ] **Step 3: Tracker rows.** Add `RSVP Link` and `Cover Image` rows under General Info in the Fall, Winter, and Spring tabs.
- [ ] **Step 4: Local real build.** Run `GOOGLE_SERVICE_ACCOUNT_JSON="$(cat key.json)" CONTENT_SHEET_ID=… .venv/bin/python -m asmesite.build --out dist`. Expected: exit 0, and `dist/index.html` shows the real approved events, the 12 newest photos, and the board. Then delete the local `key.json` after it's stored as a secret.
- [ ] **Step 5: Publish.** Create the public repo `drexel-asme/drexel-asme.github.io` and push `main`. Add the secret `GOOGLE_SERVICE_ACCOUNT_JSON` and the variable `CONTENT_SHEET_ID`. Under Settings → Pages, set the source to GitHub Actions. Check: the workflow run is green and `https://drexel-asme.github.io` loads on a phone.
- [ ] **Step 6: Failure drill.** Temporarily rename the content sheet's `Settings` tab and run the workflow manually. Expected: the run fails before deploy, the live site is unchanged, and a failure email arrives. Then restore the tab name.
