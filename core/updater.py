"""
core/updater.py
---------------
GitHub Releases üzerinden PC Setup güncellemesi.

Akış: latest release → semver karşılaştır → Setup.exe indir → sessiz kurulum başlat.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.request import Request, urlopen

from core.logger import get_logger
from core.version import (
    APP_VERSION,
    GITHUB_OWNER,
    GITHUB_RELEASES_API,
    GITHUB_REPO,
)

log = get_logger("core.updater")

_UA = f"RIFKI-Updater/{APP_VERSION} (+https://github.com/{GITHUB_OWNER}/{GITHUB_REPO})"
_SETUP_RE = re.compile(r"^RIFKI-Setup-[\d.]+\.exe$", re.IGNORECASE)


@dataclass
class ReleaseInfo:
    tag: str
    version: str
    name: str
    body: str
    setup_url: str
    setup_name: str
    html_url: str


def parse_version(text: str) -> tuple:
    """'v2.1.0' / '2.1.0' → (2, 1, 0). Eksik parçalar 0."""
    raw = (text or "").strip().lstrip("vV")
    parts = []
    for chunk in raw.split("."):
        m = re.match(r"(\d+)", chunk)
        parts.append(int(m.group(1)) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:4])


def is_newer(remote: str, local: str = APP_VERSION) -> bool:
    return parse_version(remote) > parse_version(local)


def _http_json(url: str, timeout: float = 20.0) -> dict:
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=timeout) as resp:
        import json

        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_latest_release() -> ReleaseInfo:
    data = _http_json(GITHUB_RELEASES_API)
    tag = str(data.get("tag_name") or "").strip()
    version = tag.lstrip("vV")
    assets = data.get("assets") or []
    setup_url = ""
    setup_name = ""
    for asset in assets:
        name = str(asset.get("name") or "")
        if _SETUP_RE.match(name):
            setup_url = str(asset.get("browser_download_url") or "")
            setup_name = name
            break
    if not setup_url:
        # Fallback: klasik adlandırma
        guess = f"RIFKI-Setup-{version}.exe"
        setup_url = (
            f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/"
            f"{tag}/{guess}"
        )
        setup_name = guess
    return ReleaseInfo(
        tag=tag,
        version=version,
        name=str(data.get("name") or tag),
        body=str(data.get("body") or ""),
        setup_url=setup_url,
        setup_name=setup_name,
        html_url=str(data.get("html_url") or ""),
    )


def check_for_update() -> Optional[ReleaseInfo]:
    """Yeni sürüm yoksa None."""
    try:
        info = fetch_latest_release()
    except Exception as e:
        log.warning(f"Güncelleme kontrolü başarısız: {e}")
        raise
    if not info.version:
        return None
    if is_newer(info.version, APP_VERSION):
        log.info(f"Yeni sürüm: {info.version} (şu an {APP_VERSION})")
        return info
    log.info(f"Güncel ({APP_VERSION}); uzak {info.version}")
    return None


def download_setup(
    info: ReleaseInfo,
    dest: Optional[Path] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """Setup.exe indirir. on_progress(downloaded, total)."""
    if dest is None:
        dest = Path(tempfile.gettempdir()) / (info.setup_name or "RIFKI-Setup-update.exe")
    dest = Path(dest)
    req = Request(info.setup_url, headers={"User-Agent": _UA})
    with urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        chunk = 256 * 1024
        with open(dest, "wb") as out:
            while True:
                block = resp.read(chunk)
                if not block:
                    break
                out.write(block)
                downloaded += len(block)
                if on_progress:
                    on_progress(downloaded, total)
    if dest.stat().st_size < 100_000:
        raise RuntimeError("İndirilen Setup çok küçük veya bozuk.")
    log.info(f"Setup indirildi: {dest} ({dest.stat().st_size} bayt)")
    return dest


def launch_installer(setup_path: Path) -> None:
    """Kurulumu başlatır; mevcut RIFKI kapanmalı (CLOSEAPPLICATIONS)."""
    setup_path = Path(setup_path)
    if not setup_path.is_file():
        raise FileNotFoundError(str(setup_path))
    # PrivilegesRequired=lowest kurulum; sessiz + uygulamayı kapat
    args = [
        str(setup_path),
        "/SILENT",
        "/CLOSEAPPLICATIONS",
        "/NORESTART",
        "/SUPPRESSMSGBOXES",
    ]
    creation = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
    subprocess.Popen(
        args,
        close_fds=True,
        creationflags=creation | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        cwd=str(setup_path.parent),
    )
    log.info(f"Kurulum başlatıldı: {setup_path}")


def updates_enabled() -> bool:
    raw = os.getenv("RIFKI_AUTO_UPDATE", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")
