"""Render the single-page site from collected data."""
import argparse
import re
import shutil
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

from jinja2 import Environment, PackageLoader
from markupsafe import Markup, escape

from asmesite.events import TZ, gcal_url, split_events, when_text
from asmesite.models import BoardMember, Competition, Event, Project, Settings

STATIC = Path(__file__).parent / "static"


@dataclass
class SiteData:
    settings: Settings
    upcoming: list[Event]
    past: list[Event]
    photos: list[str]
    hero: str | None
    competitions: list[Competition]
    projects: list[Project]
    board: list[BoardMember]
    images: dict[str, str]
    built_at: datetime


def initials(name: str) -> str:
    return "".join(w[0] for w in name.split()[:2]).upper()


def paragraphs(text: str) -> list[Markup]:
    """Blank lines split paragraphs; single newlines become <br>. Pieces are escaped."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return [Markup("<br>").join(escape(line.strip()) for line in p.split("\n")) for p in paras]


def safe_url(url: str | None) -> str | None:
    """Allow only http(s) links from the sheets; anything else (e.g. javascript:) is dropped."""
    url = (url or "").strip()
    return url if re.match(r"https?://", url, re.IGNORECASE) else None


def safe_email(email: str | None) -> str | None:
    """A plain address only, so the template's mailto: can't be turned into another scheme."""
    email = (email or "").strip()
    return email if re.fullmatch(r"[^\s:@<>\"]+@[^\s:@<>\"]+\.[^\s:@<>\"]+", email) else None


def stamp(dt: datetime) -> str:
    d = dt.astimezone(TZ)
    return f"{d:%b} {d.day}, {d.year}, {d.hour % 12 or 12}:{d.minute:02d} {'AM' if d.hour < 12 else 'PM'}"


def render_site(data: SiteData, out_dir: Path) -> None:
    env = Environment(loader=PackageLoader("asmesite", "templates"), autoescape=True,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update(when=when_text, gcal=gcal_url, initials=initials, paragraphs=paragraphs,
                       safe_url=safe_url, safe_email=safe_email,
                       stamp=stamp, img=lambda i: data.images.get(i) if i else None)
    html = env.get_template("index.html.j2").render(d=data, s=data.settings)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    shutil.copytree(STATIC, out_dir / "static", dirs_exist_ok=True)


def demo_data() -> SiteData:
    def ev(name, d, start, end, location, rsvp=False):
        return Event(name, f"Placeholder description for {name}.\n\nCome hang out — everyone is welcome.",
                     d, start, end, location, rsvp, "https://example.com/rsvp" if rsvp else None, None)

    events = [
        ev("3D Pen Workshop", date(2026, 9, 19), time(18), time(20), "Randell 121"),
        ev("Fall GBM", date(2026, 9, 29), time(18, 30), time(20, 30), "Randell 121"),
        ev("SASE x Temple IEEE x ASME Collab", date(2026, 10, 20), time(17, 30), time(19, 30),
           "Bossone Auditorium", rsvp=True),
        ev("Soldering Workshop", date(2026, 11, 5), time(19), time(21), "Senior Design Room"),
        ev("3D Blind Boxes (Smiski)", date(2026, 11, 10), time(18), time(20), "Randell 121", rsvp=True),
    ]
    now = datetime(2026, 10, 18, 12, 0, tzinfo=TZ)
    upcoming, past = split_events(events, now)
    settings = Settings("demo", None, "https://discord.gg/example", "https://instagram.com/example",
                        "asme@example.edu", "https://drive.google.com/drive/folders/example", None,
                        "Build, break, and learn with Drexel ASME.",
                        "We're Drexel's mechanical engineering student chapter: workshops, competitions, "
                        "robotics, and free food. Everyone is welcome.",
                        "https://drexel.campuslabs.com/engage/organization/drexelasme")
    return SiteData(
        settings=settings, upcoming=upcoming, past=past, photos=[], hero=None,
        competitions=[
            Competition("Example Design Challenge", 2026, "Demo Rover", "A placeholder competition entry.",
                        None, "2nd place", "Placeholder Team"),
            Competition("Example Student Fest", 2025, "Demo Bridge", "Another placeholder entry.",
                        None, "", "Placeholder Team"),
        ],
        projects=[
            Project("Demo Robot Arm", "A placeholder robotics project.", "In progress", None, "Placeholder Team"),
            Project("Demo Line Follower", "Another placeholder project.", "Complete", None, "Placeholder Team"),
        ],
        board=[BoardMember(n, r, "Mechanical Engineering", "2027", None, i)
               for i, (n, r) in enumerate([("Alex Example", "President"), ("Sam Sample", "Vice President"),
                                           ("Jordan Demo", "Treasurer"), ("Riley Placeholder", "Secretary")])],
        images={}, built_at=now,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render the site with sample data.")
    parser.add_argument("--demo", metavar="OUT_DIR", type=Path, required=True)
    render_site(demo_data(), parser.parse_args().demo)
