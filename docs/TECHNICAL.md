# Technical handoff

For the Technical Coordinator. The board-facing guide is [BOARD_GUIDE.md](BOARD_GUIDE.md).

## Architecture

```
Google Sheets (event tracker, Website Content, Robotics)  +  Google Drive (photos, Website Images)
        |  read-only, via service account
        v
GitHub Actions (every 3 hours, on push to main, or manual)
   pip install (pinned by constraints.txt) -> pytest -> python -m asmesite.build --out dist
        |  static HTML + WebP images in dist/
        v
GitHub Pages (deploy job)
```

- A failed build never replaces the live site. The builder renders into a temp directory and swaps it in only on success.
- Event tracker tabs are matched by name prefix (Fall, Winter, Spring). At least one must parse or the build fails.
- Content sheet tabs are `Settings` (required), `Board`, `Competitions`; the Robotics sheet needs a `Projects` tab. Missing optional tabs just leave that section empty.
- Images are fetched from Drive once each and converted to WebP. The newest 12 photos (`PHOTO_COUNT` in `asmesite/build.py`) appear in the grid, and the hero uses the newest landscape one.
- Event publish rule (`asmesite/tracker.py`): Date present and the `Approved` row in the `Event Form` section checked (TRUE, yes, or x). Only whitelisted rows are read: Event, Event Description, Date, Start Time, End Time, Location, RSVP?, RSVP Link, Cover Image.
- Content sheet: `Show` is true when it reads yes, true, or x (any case). Settings names (column Setting): Event Tracker Link (required), Robotics Sheet Link, Discord Invite Link, Instagram Link, Contact Email, Photo Folder Link, Tagline, Intro. Board has no Show column.

## Accounts and secrets

| Thing | Where / who |
| --- | --- |
| GitHub org | `drexel-asme`; owners `drexelasme.technical@gmail.com` and `drexelasme@gmail.com` |
| Google Cloud project | `drexel-asme-website`, owned by the technical account, President added as Owner |
| Service account | `website-builder@drexel-asme-website.iam.gserviceaccount.com` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | GitHub repo **secret** (Settings > Secrets and variables > Actions): the full key JSON |
| `CONTENT_SHEET_ID` | GitHub repo **variable** (same page): the Website Content sheet's ID |

That service-account address is the planned one. Once it exists, confirm the exact address in the Google Cloud console (IAM & Admin > Service accounts) and update this file and the board guide if it differs.

The service account needs Viewer access to: the event tracker, the Website Content sheet, the Robotics sheet, the photo dump folder, and the Website Images folder.

## Rotating the service-account key

1. Cloud console > IAM & Admin > Service accounts > the account > Keys > Add key > JSON.
2. Replace the `GOOGLE_SERVICE_ACCOUNT_JSON` repo secret with the new file's full contents.
3. Run the workflow manually (below) and confirm it succeeds.
4. Delete the old key in the console.

## Rebuild now

Actions tab > "Build and deploy site" > Run workflow. Technical members only.

## Running locally

Needs Python 3.12.

```
python3.12 -m venv .venv && .venv/bin/pip install -c constraints.txt -e '.[dev]'
.venv/bin/pytest
```

### Updating dependency pins

`constraints.txt` pins every package version CI installs, so a new upstream release can't break the scheduled build on its own. To bump: make a fresh Python 3.12 venv, run `pip install -U -e '.[dev]'` (no `-c`), run `pytest`, then re-freeze with `.venv/bin/pip freeze --exclude-editable > constraints.txt` and commit it.

Real data: the build reads two environment variables. `.env` is not auto-loaded. `GOOGLE_SERVICE_ACCOUNT_JSON` holds the JSON text, not a path. Save the key as `service-account.json` (gitignored via `service-account*.json`):

```
GOOGLE_SERVICE_ACCOUNT_JSON="$(cat service-account.json)" CONTENT_SHEET_ID=<sheet id> \
  .venv/bin/python -m asmesite.build --out dist
open dist/index.html
```

No credentials? Preview with sample data:

```
.venv/bin/python -m asmesite.render --demo dist
```

## When the tracker format changes

`scripts/make_fixture.py` builds a sanitized test fixture from a downloaded tracker .xlsx. It is dev-only, so `openpyxl` is not a declared dependency.

```
.venv/bin/pip install openpyxl
.venv/bin/python scripts/make_fixture.py ~/Downloads/tracker.xlsx tests/fixtures/<name>.json
```

It reads the `Fall` sheet and sanitizes it: only the public rows plus the section/label rows the parser needs are kept; Week, Event Level, Due, Submitted, and every Approved outside Event Form are cleared; unapproved events become "Unpublished Event N" with a placeholder description (the first one gets a synthetic Purchase Request Approved checkmark for a test); the totals column is cleared. Never commit the .xlsx (it is gitignored). Before committing the JSON, grep it for any cost figure, person's name, or unpublished event name you know is in the sheet and confirm nothing matches.

## When the scheduled build fails

The live site stays as it was. Two alerts go out:

- The workflow's `notify-failure` job opens an issue titled "Scheduled site build is failing" (or comments on it if it is already open) with a link to the failed run. Owners should **watch the repo** (Watch > All activity, or Custom > Issues) with GitHub notification emails turned on, so they get these. Close the issue once a build succeeds again.
- GitHub's own failure email goes only to whoever last edited the workflow file (for scheduled runs), not to watchers. So commit changes to `.github/workflows/build.yml` from the technical role account (`drexelasme.technical@gmail.com`), not a personal account.

To diagnose:

1. Actions tab > the failed run > the **Build site** step.
2. Find the last `ERROR` line: "Build failed; the previous site stays live (ExceptionType: message)". Google API failures read "(Google API error <status> <reason>)" and deliberately omit the request URL, since it contains the sheet ID.
3. Common causes:
   - Settings tab renamed or missing (`The content sheet has no 'Settings' tab`).
   - Event Tracker Link wrong, or the tracker not shared with the service account.
   - Service-account key revoked or the secret empty (auth error).
   - No Fall/Winter/Spring tab found or readable in the tracker (a tab is unreadable when it has no `Event` row, no `Date` row, or no `Approved` row under a column-A header starting with "Event Form").
   - Output directory refused: `--out` points at a non-empty folder without `index.html`, or one containing `.git`.
4. Fix the sheet or secret, then run the workflow manually.

A **Test** step failure means a code or dependency problem; run `.venv/bin/pytest` locally.

### Scheduled runs pausing

GitHub pauses scheduled workflows after 60 days without repo activity. A "Keep scheduled builds enabled" step in the workflow re-enables it via the API on each scheduled run, which guards against this. Still, at the start of each term check that the Actions tab shows recent scheduled runs, and re-enable the workflow there if it is paused.

## Turnover checklist

- [ ] Hand over the `drexelasme.technical@gmail.com` password (and its recovery phone/email and 2FA) to the new Technical Coordinator.
- [ ] Remove the outgoing person's personal account from the GitHub org, the Cloud project, and any Drive sharing.
- [ ] Confirm the President is still an Owner of the Cloud project and a GitHub org owner.
- [ ] Rotate the service-account key (above).
- [ ] Confirm a recent scheduled run exists in the Actions tab.
- [ ] Make sure the incoming coordinator watches the repo for failure issues, and that the workflow file was last committed from the technical role account.
- [ ] Walk the new coordinator through this file and a manual rebuild.
