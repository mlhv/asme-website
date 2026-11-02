# Board guide: keeping the ASME website up to date

The website updates itself from our Google Sheets and Drive folders. You never touch the website directly. Edit the sheets as usual and the site follows, usually within about 3 hours.

**In a hurry?** Ask a technical member to re-run the website build. Only they can.

## Getting an event on the site

An event shows up when it has both of these in the event tracker:

1. A **Date**.
2. The **Approved** box checked in the **Event Form** section.

Until both are there, the event stays off the site. The Approved row must sit under the **Event Form** header in column A; don't insert notes in column A between that header and the Approved row, or the site stops reading the tab. Anything else in the tracker (budgets, leads, purchase requests) is never shown.

Optional extras for an event:

- **RSVP Link:** paste the sign-up link. The RSVP button appears only if the **RSVP?** row also says Yes.
- **Cover Image:** first upload the picture to the **Website Images** folder in Drive, then paste that file's link here.

### Adding the two new rows (one time per tracker)

Under **General Info**, add two rows with these exact labels in column B:

- `RSVP Link`
- `Cover Image`

The order of rows doesn't matter, but the label text does. Spelling matters.

### Copy the tab, don't rearrange it

When you start a new term, copy an existing tab instead of building a new one. Don't rename the row labels or move things around in ways that change what a row is called. Tab names must start with **Fall**, **Winter**, or **Spring**.

## New school year

Each year gets a new tracker file. To switch:

1. Open the **Website Content** sheet and go to the **Settings** tab.
2. Paste the new tracker's link next to **Event Tracker Link**. If Sheets offers to replace the link with the file name (a "smart chip"), say no and keep the plain link. A chip hides the link from the website, and the site stops updating.
3. Share the new tracker with the website's service account (our robot reader): `website-builder@drexel-asme-website.iam.gserviceaccount.com`. Viewer access is enough.

If you skip step 3, the site can't read the tracker and won't update.

Tip: share the tracker only with board accounts and the service account, not with "anyone with the link". The website doesn't need it to be public.

## Photos

Drop event photos into the photo dump folder. The site shows the **newest 12** automatically and has a "See all photos" link to the whole folder. Nothing to approve.

The folder must stay shared with the website's service account (`website-builder@drexel-asme-website.iam.gserviceaccount.com`, Viewer), or no photos appear. For the "See all photos" link to work for visitors, the folder's sharing must also be "Anyone with the link" (Viewer).

## Pictures in the sheets (headshots, covers, projects)

1. Upload the picture to the **Website Images** folder in Drive.
2. Right-click it, copy the link, and paste it in the sheet.
3. If Sheets offers to replace the link with the file name (a "smart chip"), say no and keep the plain link. Otherwise the picture won't show.

If the site can't read the picture (for example, it isn't in that folder), the site shows initials (for headshots) or a plain blue card instead. Nothing breaks.

## After elections: update the board

1. Open the **Website Content** sheet, **Board** tab.
2. Edit names, roles, majors, and years. Upload headshots to Website Images and paste the links.
3. Use the **Order** column to set who comes first (1 is first).

The Board tab has no Show column, so every row with a name appears on the site. Delete rows for people who left.

## Adding a competition project

1. Go to the **Competitions** tab and add a row.
2. Fill in Competition, Year, Project, a short Description, Photo, Placement, and Team.
3. Set **Show** to **Yes**. Rows that aren't Yes stay hidden.

## Robotics projects

The robotics team keeps its own **Projects** tab in the Robotics sheet. Set **Show** to **Yes** for a project to appear. Extra columns are fine and ignored. The Robotics sheet link lives in Settings and must be shared with the service account too.

## Setting up the Website Content sheet

The sheet starts from four template files (Settings, Board, Competitions, Projects). Import each as a tab.

**Important:** every template contains one fake example row ("Jane Example" and so on). **Delete or replace it after importing.** In the Board tab there is no Show column, so an unedited example would appear on the live site.

## Quick checklist

- Event not showing? Check Date and the Event Form **Approved** box, and that the tab is named Fall, Winter, or Spring.
- Picture not showing? Is it in Website Images, and is the cell a plain link (not a file-name chip)?
- Whole site stale for a day? Tell the Technical Coordinator.
