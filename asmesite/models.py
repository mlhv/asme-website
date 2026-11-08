from dataclasses import dataclass
from datetime import date, datetime, time


@dataclass(frozen=True)
class Event:
    name: str
    description: str
    date: date
    start: time | None
    end: time | None
    location: str
    rsvp_required: bool
    rsvp_link: str | None
    cover_image_id: str | None


@dataclass(frozen=True)
class BoardMember:
    name: str
    role: str
    major: str
    year: str
    headshot_id: str | None
    order: float


@dataclass(frozen=True)
class Competition:
    competition: str
    year: int | None
    project: str
    description: str
    photo_id: str | None
    placement: str
    team: str


@dataclass(frozen=True)
class Project:
    name: str
    description: str
    status: str
    photo_id: str | None
    team: str


@dataclass(frozen=True)
class Settings:
    tracker_id: str
    robotics_sheet_id: str | None
    discord_url: str
    instagram_url: str
    contact_email: str
    photos_folder_url: str
    photos_folder_id: str | None
    tagline: str
    intro: str
    dragonlink_url: str = ""


@dataclass(frozen=True)
class DriveImage:
    id: str
    created: datetime
    width: int | None
    height: int | None
    rotation: int
