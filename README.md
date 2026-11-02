# Drexel ASME website

Live at https://mlhv.github.io/asme-website/ (moving to https://drexel-asme.github.io when the club takes over; see [TECHNICAL.md](docs/TECHNICAL.md#moving-to-the-club-accounts)).

Static-site builder for the Drexel ASME club website. A scheduled GitHub Actions job reads the club's Google Sheets and Drive folders through a read-only service account, generates a static site, and deploys it to GitHub Pages every few hours. Board members edit the sheets only; see the [board guide](docs/BOARD_GUIDE.md). Future Technical Coordinators should read the [technical handoff](docs/TECHNICAL.md) for architecture, accounts, key rotation, local runs, and failure triage.
