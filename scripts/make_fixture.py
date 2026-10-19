"""Build a sanitized tracker fixture: python scripts/make_fixture.py <xlsx> <out.json>

Dev-only (needs openpyxl). Sanitizes structurally so private data never reaches the repo:
- keeps only the public rows the parser reads, plus Week/Event Level/Due/Submitted/Approved
  label rows and column-A section headers (text before " - "), so section structure stays;
- clears Week, Event Level, every Due/Submitted, and every Approved outside Event Form;
- renames unapproved events to "Unpublished Event N" with a placeholder description;
- sets Purchase Request Approved on the first unpublished event, so tests can check the
  parser ignores it;
- clears the totals column (no Event name), leaving a 0 in its Date cell so it still exists.
"""
import datetime as dt
import json
import sys

import openpyxl

PUBLIC = {"event", "event description", "date", "start time", "end time", "location",
          "rsvp?", "rsvp link", "cover image"}
CLEARED = {"week", "event level", "due", "submitted", "approved"}
EPOCH = dt.datetime(1899, 12, 30)
FIRST_COL = 2


def cell(v):
    if isinstance(v, dt.datetime):
        return (v - EPOCH).total_seconds() / 86400
    if isinstance(v, dt.date):
        return float((v - EPOCH.date()).days)
    if isinstance(v, dt.time):
        return (v.hour * 3600 + v.minute * 60 + v.second) / 86400
    return v


def _section_name(a):
    return a.split(" - ")[0].strip() if isinstance(a, str) and a.strip() else None


def main(src, out):
    ws = openpyxl.load_workbook(src, data_only=True)["Fall"]
    rows, section = [], ""
    event_form_approved = purchase_approved = None
    for r in ws.iter_rows(values_only=True):
        a = _section_name(r[0] if r else None)
        if a:
            section = a.lower()
        label = str(r[1]).strip() if len(r) > 1 and r[1] is not None else ""
        key = label.lower()
        if key in PUBLIC or key in CLEARED:
            row = [a, label] + [cell(v) for v in r[FIRST_COL:]]
            if key == "approved" and section.startswith("event form"):
                event_form_approved = row
            elif key in CLEARED:
                row[FIRST_COL:] = [None] * (len(row) - FIRST_COL)
                if key == "approved" and section.startswith("purchase request"):
                    purchase_approved = row
            rows.append(row)
        elif a:
            rows.append([a, ""])  # section header on a private row: keep only its name

    by_label = {}
    for row in rows:
        by_label.setdefault(row[1].lower(), row)
    event = by_label["event"]
    unpublished = 0
    for col in range(FIRST_COL, len(event)):
        if event[col] is None or not str(event[col]).strip():  # totals column
            for row in rows:
                if col < len(row):
                    row[col] = None
            by_label["date"][col] = 0
            continue
        if event_form_approved[col] is True:
            continue
        unpublished += 1
        event[col] = f"Unpublished Event {unpublished}"
        by_label["event description"][col] = "Placeholder description."
        if unpublished == 1:
            purchase_approved[col] = True
    with open(out, "w") as f:
        json.dump(rows, f, indent=0, default=str)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
