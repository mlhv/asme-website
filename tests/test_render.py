from dataclasses import replace
from datetime import date, datetime, time

import pytest
from bs4 import BeautifulSoup

from asmesite.events import TZ
from asmesite.models import BoardMember, Competition, Event, Project, Settings
from asmesite.render import SiteData, render_site

JOIN = "No sign-up needed — join the Discord, follow us on Instagram, and come to any event."
EMPTY = "New events coming soon — follow us on Instagram."

SETTINGS = Settings("trk", None, "https://discord.gg/x", "https://instagram.com/x", "asme@example.edu",
                    "https://drive.google.com/drive/folders/f", None, "Build things with us", "We are ASME.")


def ev(name="Workshop", description="Learn things.", rsvp_required=False, rsvp_link=None):
    return Event(name, description, date(2026, 10, 20), time(17, 30), time(19, 30), "Randell 121",
                 rsvp_required, rsvp_link, None)


def site(**kw):
    data = SiteData(
        settings=SETTINGS,
        upcoming=[ev()],
        past=[ev("Fall GBM")],
        photos=["photos/a.webp"],
        hero=None,
        competitions=[Competition("SAE Baja", 2026, "Car", "Fast.", None, "3rd", "Team A")],
        projects=[Project("Arm", "A robot arm.", "In progress", None, "Team B")],
        board=[BoardMember("Minh Le", "President", "MEM", "2027", None, 1)],
        images={},
        built_at=datetime(2026, 10, 18, 16, 0, tzinfo=TZ),
    )
    return replace(data, **kw)


@pytest.fixture
def render(tmp_path):
    def go(data):
        render_site(data, tmp_path)
        return BeautifulSoup((tmp_path / "index.html").read_text(), "html.parser")
    return go


def test_nav_anchors_resolve(render):
    soup = render(site())
    links = [a["href"] for a in soup.select("header nav a")]
    assert links == ["#events", "#photos", "#competitions", "#projects", "#board", "#join"]
    for href in links:
        assert soup.find(id=href[1:]) is not None


def test_rsvp_link_only_when_required_and_present(render):
    soup = render(site(upcoming=[ev("A", rsvp_required=True), ev("B", rsvp_required=True, rsvp_link="https://forms.gle/r")]))
    assert soup.select_one('button.event-card[data-dialog="ev-0"]') is not None
    assert not soup.find(id="ev-0").find("a", string=lambda s: s and "RSVP" in s)
    rsvp = soup.find(id="ev-1").find("a", string=lambda s: s and "RSVP" in s)
    assert rsvp["href"] == "https://forms.gle/r" and rsvp["rel"] == ["noopener"]
    assert soup.find(id="ev-1").find("a", string=lambda s: s and "Google Calendar" in s)


def test_empty_upcoming_shows_copy(render):
    soup = render(site(upcoming=[]))
    p = soup.find(string=EMPTY)
    assert p is not None
    assert p.find_parent("a")["href"] == SETTINGS.instagram_url


def test_empty_sections_hidden_with_nav(render):
    soup = render(site(competitions=[], past=[], photos=[]))
    assert soup.find(id="competitions") is None and soup.find(id="earlier") is None and soup.find(id="photos") is None
    hrefs = [a["href"] for a in soup.select("header nav a")]
    assert "#competitions" not in hrefs and "#photos" not in hrefs


def test_board_member_without_headshot_gets_initials(render):
    soup = render(site())
    assert soup.select_one("#board .initials").get_text(strip=True) == "ML"


def test_join_copy_verbatim(render):
    soup = render(site())
    assert soup.find(id="join").find(string=JOIN) is not None
    assert soup.select_one('#join a[href="mailto:asme@example.edu"]') is not None


def test_description_is_escaped(render):
    soup = render(site(upcoming=[ev(description="<script>alert(1)</script>")]))
    dialog = soup.find(id="ev-0")
    assert dialog.find("script") is None
    assert "<script>alert(1)</script>" in dialog.get_text()


def test_description_paragraphs(render):
    soup = render(site(upcoming=[ev(description="One\nline two\n\nPara two")]))
    paras = soup.select("#ev-0 .desc p")
    assert [p.get_text() for p in paras] == ["Oneline two", "Para two"]
    assert paras[0].find("br") is not None


def test_images_used_when_present(render):
    e = replace(ev(), cover_image_id="cov")
    soup = render(site(upcoming=[e], board=[replace(site().board[0], headshot_id="hs")],
                       images={"cov": "img/cov.webp", "hs": "img/hs.webp"}))
    assert soup.select_one('#events img[src="img/cov.webp"]') is not None
    assert soup.select_one('#board img[src="img/hs.webp"]') is not None


def test_external_links_open_new_tab(render):
    soup = render(site())
    for a in soup.select('a[href^="http"]'):
        assert a.get("target") == "_blank" and a.get("rel") == ["noopener"]


def test_updated_stamp(render):
    soup = render(site())
    assert "Updated Oct 18, 2026, 4:00 PM" in soup.find(id="join").get_text()


def test_static_copied(render, tmp_path):
    render(site())
    assert (tmp_path / "static" / "style.css").exists()
    assert (tmp_path / "static" / "app.js").exists()
    assert (tmp_path / "static" / "hero-fallback.jpg").exists()


def test_javascript_rsvp_link_dropped(render):
    soup = render(site(upcoming=[ev(rsvp_required=True, rsvp_link="javascript:alert(1)")]))
    assert not soup.find(id="ev-0").find("a", string=lambda s: s and "RSVP" in s)
    assert "javascript:" not in str(soup).lower()


def test_unsafe_settings_links_omitted(render):
    bad = replace(SETTINGS, discord_url=" JavaScript:alert(1)", photos_folder_url="data:text/html,x",
                  contact_email="javascript:alert(1)//@x.com")
    soup = render(site(settings=bad))
    assert not soup.find("a", string="Join our Discord")
    assert not soup.find("a", string=lambda s: s and "See all photos" in s)
    assert not soup.select('a[href^="mailto:"]')
    assert len(soup.find_all("a", string="Instagram")) == 2
    assert "javascript:" not in str(soup).lower() and "data:" not in str(soup)


def test_plain_https_urls_render(render):
    soup = render(site(upcoming=[ev(rsvp_required=True, rsvp_link="HTTPS://forms.gle/r ")]))
    assert soup.find(id="ev-0").find("a", string="RSVP")["href"] == "HTTPS://forms.gle/r"
    assert [a["href"] for a in soup.find_all("a", string="Join our Discord")] == [SETTINGS.discord_url] * 2
    assert soup.find("a", string=lambda s: s and "See all photos" in s)["href"] == SETTINGS.photos_folder_url
