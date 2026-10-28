"""
core/version.py
---------------
Tek kaynak sürüm numarası. Installer (rifki.iss) ile senkron tutulmalı.
"""

APP_NAME = "RIFKI"
APP_VERSION = "2.5.0"

# GitHub Releases: Setup asset adı RIFKI-Setup-{version}.exe
GITHUB_OWNER = "BatuhanKlcky"
GITHUB_REPO = "rifki-voice-assistant"
GITHUB_RELEASES_API = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
GITHUB_RELEASES_PAGE = (
    f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
)
