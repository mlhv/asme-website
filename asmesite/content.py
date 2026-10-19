"""Parse the Website Content and Robotics sheets (raw Sheets values) into models."""
import logging
import math

from asmesite.ids import drive_id
from asmesite.models import BoardMember, Competition, Project, Settings

DEFAULT_TAGLINE = "Build things. Meet engineers."
DEFAULT_INTRO = ("Drexel's chapter of the American Society of Mechanical Engineers: "
                 "workshops, competitions, robotics, and free food.")

log = logging.getLogger(__name__)


class ContentError(Exception):
    pass


def _cell_text(v: object) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _link_id(text: str, what: str, label: str) -> str | None:
    found = drive_id(text)
    if text and found is None:
        log.warning("%s: %s link is not a valid Drive link; ignoring it", label, what)
    return found


def rows_to_dicts(values: list[list[object]]) -> list[dict[str, str]]:
    if not values:
        return []
    header = [str(h).strip().lower() for h in values[0]]
    rows = []
    for raw in values[1:]:
        cells = [_cell_text(v) for v in raw]
        if not any(cells):
            continue
        cells += [""] * (len(header) - len(cells))
        rows.append(dict(zip(header, cells)))
    return rows


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def _shown(row: dict[str, str]) -> bool:
    return row.get("show", "").lower() in {"true", "yes", "x"}


def _number(s: str) -> float | None:
    try:
        n = float(s)
    except ValueError:
        return None
    return n if math.isfinite(n) else None


def _year(s: str) -> int | None:
    n = _number(s)
    return None if n is None else int(n)


def parse_settings(values: list[list[object]]) -> Settings:
    found = {_norm(r.get("setting", "")): r.get("value", "") for r in rows_to_dicts(values)}

    def get(name: str) -> str:
        return found.get(name, "")

    tracker_id = drive_id(get("event tracker link"))
    if tracker_id is None:
        raise ContentError("Settings: 'Event Tracker Link' is missing or not a valid sheet link")
    photos_url = get("photo folder link")
    return Settings(
        tracker_id=tracker_id,
        robotics_sheet_id=_link_id(get("robotics sheet link"), "Robotics Sheet", "Settings"),
        discord_url=get("discord invite link"),
        instagram_url=get("instagram link"),
        contact_email=get("contact email"),
        photos_folder_url=photos_url,
        photos_folder_id=drive_id(photos_url),
        tagline=get("tagline") or DEFAULT_TAGLINE,
        intro=get("intro") or DEFAULT_INTRO,
    )


def parse_board(values: list[list[object]]) -> list[BoardMember]:
    members = []
    for r in rows_to_dicts(values):
        if not r.get("name"):
            log.warning("Board: skipping row with no Name (role %r)", r.get("role", ""))
            continue
        order = _number(r.get("order", ""))
        members.append(BoardMember(
            name=r["name"],
            role=r.get("role", ""),
            major=r.get("major", ""),
            year=r.get("year", ""),
            headshot_id=_link_id(r.get("headshot", ""), "Headshot", f"Board {r['name']!r}"),
            order=math.inf if order is None else order,
        ))
    return sorted(members, key=lambda m: (m.order, m.name))


def parse_competitions(values: list[list[object]]) -> list[Competition]:
    comps = []
    for r in rows_to_dicts(values):
        if not _shown(r):
            continue
        name = r.get("competition", "") or r.get("project", "")
        if not name:
            log.warning("Competitions: skipping shown row with no Competition or Project")
            continue
        comps.append(Competition(
            competition=r.get("competition", ""),
            year=_year(r.get("year", "")),
            project=r.get("project", ""),
            description=r.get("description", ""),
            photo_id=_link_id(r.get("photo", ""), "Photo", f"Competitions {name!r}"),
            placement=r.get("placement", ""),
            team=r.get("team", ""),
        ))
    return sorted(comps, key=lambda c: (c.year is None, -(c.year or 0)))


def parse_projects(values: list[list[object]]) -> list[Project]:
    projects = []
    for r in rows_to_dicts(values):
        if not _shown(r):
            continue
        if not r.get("project"):
            log.warning("Projects: skipping shown row with no Project name")
            continue
        projects.append(Project(
            name=r["project"],
            description=r.get("description", ""),
            status=r.get("status", ""),
            photo_id=_link_id(r.get("photo", ""), "Photo", f"Projects {r['project']!r}"),
            team=r.get("team", ""),
        ))
    return projects
