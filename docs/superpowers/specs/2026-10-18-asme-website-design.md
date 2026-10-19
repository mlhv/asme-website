# Drexel ASME Website — Design

## Intent

Drexel's ASME chapter (American Society of Mechanical Engineers) needs a public website. Its main readers are **new and prospective students** who want to see what the club does and how to get involved. Anyone else who's curious (faculty, sponsors, other students) should be able to browse it too.

Success looks like this: a freshman scans a QR code at the involvement fair, sees an active club with real events, photos, competition projects, and robotics work, and leaves knowing to join the Discord, follow the Instagram, and show up to an event.

The real risk is staleness, not the build. Most of the e-board is non-technical and turns over every year. The site has to update itself from the Google tools the board already uses, so that **no one ever edits code to change content**. One technical owner (currently the e-board member who requested this) maintains the code and writes documentation for future technical members.

## Goals

- One long, scrolling, mobile-first page that looks clean and inviting.
- Content flows automatically from Google Sheets and Google Drive.
- Joining is obvious: Discord and Instagram buttons, plus "just show up to any event."
- It survives e-board turnover. Ownership sits with club accounts, not personal ones, and there is documentation for both non-technical and technical successors.
- It costs nothing to run.

## Non-goals

- Instagram feed integration. Instagram is a link/button only. (Meta API tokens expire about every 60 days, which would quietly break after the owner graduates.)
- Reading the Drexel OneDrive (CAD/.STEP/.SLDPRT competition files). That stays internal.
- Membership sign-up forms, dues, logins, or member-only areas.
- A custom domain (a free subdomain is fine for now; adding one later should be easy).
- Instant updates. A delay of a few hours between a sheet edit and the site is acceptable.

## Anti-goals (failure even if it "works")

- **Exposing private data.** The event tracker holds budgets, actual spend, approval status, event leads/teams, and a member's Discord handle. None of that may ever appear on the site or in any public file, repo, or build artifact.
- **Breaking silently or visibly.** A malformed sheet must never take the site down or show garbage. The last good version stays live.
- **Depending on a person.** If something relies on one student's personal Google/GitHub account or a credential that expires, it will die at graduation.
- **Making the board change its habits.** The existing tracker workflow stays as-is. Only small additive rows/columns are allowed.

## Constraints

- Free hosting, free address (e.g. GitHub Pages or Netlify subdomain).
- No always-on server for anyone to maintain.
- Google Sheets and Drive stay **private**. The site reads them with a club-owned service account that the files are shared with (read-only).
- Times are shown in America/New_York.

## Architecture (decided)

- **Static site, rebuilt on a schedule.** A scheduled job (e.g. GitHub Actions cron, every ~3 hours, plus a manual "rebuild now" trigger) does three things: reads the sheets and Drive through the Google APIs using the service account, generates the static site, and deploys it.
- **Only public fields are extracted.** The build reads the tracker but emits only the whitelisted public fields listed below. Nothing else from the tracker is written to disk in the output or committed.
- **Fail safe.** If Google can't be reached, or a whole sheet can't be parsed, the build fails and the previous deploy stays live. Problems with a single event or row are skipped with a logged warning, and the rest of the site still builds. A failed scheduled build must notify the technical owner(s); GitHub's built-in failed-workflow email is enough.
- **Photos are copied, not hotlinked.** Drive image URLs aren't reliable for embedding. The build downloads the selected photos, resizes and compresses them (and converts HEIC to JPEG/WebP), and serves them from the site.
- **Ownership.** The club already has per-role board email accounts (secretary, treasurer, etc.) that pass from officer to officer. These are not under Drexel's Google Workspace.
  - **Owner: the Technical Coordinator role account** (`drexelasme.technical@gmail.com`, held by the current Technical Coordinator) owns everything website-related: the Google Cloud project and service account, the GitHub account/org and repo, the hosting, and the website's Drive files and sheets.
  - **Backup admin: the President's role account** (`drexelasme@gmail.com`) gets full access to all of the above, so the site survives even if the Technical Coordinator role is vacant.
  - On turnover, the role account's password passes to the next Technical Coordinator. No transfers are needed.
  - The event tracker, photo dump folder, Website Content sheet, Robotics Projects sheet, and Website Images folder currently live (or would be created) in **members' personal Drives**. **Step one of setup** is transferring ownership of each to a role account, or creating them there, so nothing depends on one student. Photos that members upload into the dump folder stay owned by whoever uploaded them. That's acceptable: if one disappears, the site just shows the next most recent photo.
  - The service-account key is stored as a CI secret and never committed.
- **Sharing recommendation.** The tracker is currently shared with "anyone with the link," which means the budget and other private fields are already readable by anyone who has the URL. *Recommendation, the board's decision:* restrict the tracker to board role accounts plus the service account. The site doesn't need it public.

## Content sources

### 1. Event tracker (existing Google Sheet, one file per school year)

Example: "Event Tracking Sheet 26-27". The layout is **transposed**:

- One tab per term: `Fall`, `Winter`, `Spring`. The `Event Form Check List` tab is ignored.
- Column A holds section headers (`General Info`, `Event Form`, `Purchase Request`, `Advertise`, `Marketing…`). Column B holds row labels. **Each event is a column**, starting at column C.
- Rows must be found **by label, not by position**, because the board may insert rows. Labels such as `Due`, `Submitted`, and `Approved` repeat across sections. **`Approved` means the one in the `Event Form` section** (the first `Approved` after the `Event Form` header in column A).
- Some columns contain totals (e.g. the cost sum after the last Fall event). A column with no `Event` name is not an event.

**Publish rule:** an event appears on the site **only when it has a Date and its Event Form "Approved" box is checked.**

**Public fields (whitelist):** Event name, Event Description, Date, Start Time, End Time, Location, RSVP? and two **new rows to add** in `General Info`:
- `RSVP Link`: a URL. An RSVP button shows only when `RSVP?` = Yes and a link is present.
- `Cover Image` (optional): a Drive file link for the event card/modal.

Everything else (Week, Event Level, Day, PR, Food, attendance, costs, leads/teams, forms, purchase requests, advertising, marketing notes) is **never** emitted.

**Data is messy; handle it gracefully:**
- Location spelling and case varies ("Randell 121" / "RANDEL 121"). Trim whitespace. *Builder's call* on any light normalization, but never invent information.
- Missing times mean the event shows the date only. A missing description shows the card without the "more" text.
- Descriptions contain line breaks and trailing whitespace. Keep the paragraphs and trim the rest.
- Week values mix numbers and text ("Welcome Week", "Finals"). They aren't used.

**Cell formats (verified from the 26-27 file):** `Approved`, `Submitted`, and the other boxes are real checkboxes (TRUE/FALSE). `Date` is a real date value with the year. `Start Time` and `End Time` are real time values. `Event Level` is numeric. Some blank cells are empty and others are `None`. A copy of the 26-27 tracker exists as an .xlsx. Because it contains private budget data, test fixtures must be a **sanitized** copy (costs, leads, teams, and handles removed), never the raw file.

**Which tracker file:** a new file is made each school year. The current tracker's URL lives in the Website Content sheet's `Settings` tab (below), so the board switches years by pasting a link. No code change needed.

### 2. Photo dump folder (existing shared Google Drive folder)

- Members upload event photos freely. There's no curation step.
- The site shows the **most recent** photos (by Drive creation/upload time), images only, including subfolders. *Builder's call* on the exact count; around 8–12 fits a phone-friendly grid.
- A **"See all photos"** link opens the full folder. That means the folder must be viewable by anyone with the link. The board has accepted that the whole dump is effectively public.
- The hero background uses the most recent landscape photo, with a fallback to a static image if none is suitable.

### Linked images (headshots, cover images, competition/robotics photos)

*Design call (not yet confirmed by the board):* All images linked from the sheets must be uploaded to one club-owned **"Website Images"** Drive folder that is shared with the service account. A link to a file the service account can't read falls back to a placeholder (initials for headshots, a plain blue card otherwise), and the build logs a warning. The board guide says this plainly: "upload the photo to Website Images first, then paste its link."

### 3. Website Content sheet (new, owned by the board)

A new Google Sheet that the board edits. Proposed tabs (*column names are the builder's call*, but they must be plain-English headers a non-technical member understands):

- **Settings:** current event tracker URL, Discord invite URL, Instagram URL, contact email, photo folder URL, hero tagline/intro sentence.
- **Board:** Name, Role, Major, Year, Headshot (Drive link), Display order.
- **Competitions:** one row per competition project. Competition (e.g. ASME Student Design Competition), Year, Project name, Short description (about 2 lines), Photo (Drive link), Placement (optional), Team members, Show (Yes/No).

### 4. Robotics Projects sheet (new, owned by the robotics team)

A separate spreadsheet the robotics team maintains with more detail for its own use. The site reads only the basic fields: Project name, Short description, Status (e.g. In progress / Completed), Photo (Drive link), Team, Show (Yes/No). The robotics team may add extra columns, which the site ignores.

## The page (decided)

One long scrolling page in the **"Bright & airy"** style: mostly white, light blue-tinted section backgrounds alternating with white, and one bright engineering blue (around `#1565d8`) for buttons, dates, and links over dark navy text. Friendly, clean, generous whitespace, rounded cards with soft shadows. It must look good on a phone first.

Top to bottom:

1. **Header:** "ASME · Drexel" with links that jump to each section. It stays pinned while scrolling.
2. **Hero:** a short pitch line, one sentence about the club, and **Join our Discord** and **Instagram** buttons over a recent photo.
3. **Upcoming events:** cards for published events that haven't ended yet, soonest first. Each shows date, time, name, and location. Tapping a card opens the full description, an RSVP button (if applicable), and "Add to Google Calendar." If there are no upcoming events, it shows "New events coming soon — follow us on Instagram."
4. **Earlier this year:** a compact list of published events from the current tracker that already happened, newest first.
5. **Recent photos:** the photo grid plus "See all photos →".
6. **Competitions:** cards from the Competitions tab, newest year first.
7. **Robotics projects:** cards from the Robotics Projects sheet, in the same card style as Competitions.
8. **Meet the board:** headshots, names, and roles, in display order. A missing headshot gets a tasteful placeholder (e.g. initials).
9. **Join / footer:** "No sign-up needed — join the Discord, follow us on Instagram, and come to any event." The two buttons again, plus the contact email.

Any section with no data hides itself, except Upcoming events, which shows its "coming soon" message.

## Documentation (required deliverable)

- **Board guide (non-technical, short):** how to get an event on the site (fill in the date, check Approved, optionally add an RSVP link or cover image); how photos appear; how to update the board after elections; how to add a competition project; how to switch to next year's tracker; "copy the tab, don't rearrange it"; how long changes take to show (within about 3 hours). *Design call:* only technical members trigger a manual "rebuild now," so the board needs no GitHub access, and the board guide says to ask a technical member if something is urgent.
- **Technical handoff:** architecture, where every account and secret lives and who owns it, how to rotate the service-account key, how to run locally, and what to do when a scheduled build fails.

## Left to the builder

- Static site tooling, language, and libraries.
- Exact rebuild frequency (within "every few hours"), photo count, image sizes.
- Hosting choice between free static hosts.
- Exact column names in the new sheets, and creating template copies of them.
- Fonts, icons, and the finer visual details within the decided style.
- Whether past events link to photos (nice-to-have, not required).
