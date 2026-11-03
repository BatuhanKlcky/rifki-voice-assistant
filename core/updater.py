"""
core/updater.py
---------------
GitHub Releases üzerinden PC Setup güncellemesi.

Akış: latest release → semver karşılaştır → URL & SHA-256/PE doğrulamasıyla Setup.exe indir → sessiz kurulum başlat.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse
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
_SHA256_RE = re.compile(r"\b([a-fA-F0-9]{64})\b")
_ALLOWED_DOWNLOAD_HOSTS = frozenset({
    "github.com",
    "objects.githubusercontent.com",
    " release-assets.githubusercontent.com".strip(),
})


@dataclass
class ReleaseInfo:
    tag: str
    version: str
    name: str
    body: str
    setup_url: str
    setup_name: str
    html_url: str
    expected_sha256: str = ""


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


def _is_trusted_download_url(url: str) -> bool:
    """İndirme adresinin yalnızca resmi GitHub HTTPS kaynağından geldiğini doğrular."""
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return False
        host = (parsed.hostname or "").lower()
        if host not in _ALLOWED_DOWNLOAD_HOSTS:
            return False
        if host == "github.com":
            expected_prefix = f"/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/".lower()
            if not parsed.path.lower().startswith(expected_prefix):
                return False
        return True
    except Exception:
        return False


def _http_json(url: str, timeout: float = 20.0) -> dict:
    req = Request(url, headers={"User-Agent": _UA, "Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=timeout) as resp:
        import json

        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_latest_release() -> ReleaseInfo:
    data = _http_json(GITHUB_RELEASES_API)
    tag = str(data.get("tag_name") or "").strip()
    version = tag.lstrip("vV")
    body = str(data.get("body") or "")
    assets = data.get("assets") or []
    setup_url = ""
    setup_name = ""
    expected_sha256 = ""
    for asset in assets:
        name = str(asset.get("name") or "")
        if _SETUP_RE.match(name):
            setup_url = str(asset.get("browser_download_url") or "")
            setup_name = name
            digest = str(asset.get("digest") or "").strip()
            if digest.lower().startswith("sha256:"):
                expected_sha256 = digest.split(":", 1)[1].strip().lower()
            break
    if not expected_sha256 and body:
        m = _SHA256_RE.search(body)
        if m:
            expected_sha256 = m.group(1).lower()
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
        body=body,
        setup_url=setup_url,
        setup_name=setup_name,
        html_url=str(data.get("html_url") or ""),
        expected_sha256=expected_sha256,
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
    """Setup.exe indirir, resmi URL, PE imzası ve SHA-256 bütünlüğünü doğrular."""
    if not _is_trusted_download_url(info.setup_url):
        raise RuntimeError(f"Güvenilmeyen güncelleme adresi reddedildi: {info.setup_url}")

    safe_filename = Path(info.setup_name or "RIFKI-Setup-update.exe").name
    if not _SETUP_RE.match(safe_filename):
        safe_filename = "RIFKI-Setup-update.exe"

    if dest is None:
        dest = Path(tempfile.gettempdir()) / safe_filename
    dest = Path(dest)
    req = Request(info.setup_url, headers={"User-Agent": _UA})
    hasher = hashlib.sha256()
    first_bytes = b""

    with urlopen(req, timeout=120) as resp:
        final_url = resp.geturl()
        if final_url and not _is_trusted_download_url(final_url):
            raise RuntimeError(f"Yönlendirilen indirme adresi güvenilir değil: {final_url}")

        total = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        chunk = 256 * 1024
        with open(dest, "wb") as out:
            while True:
                block = resp.read(chunk)
                if not block:
                    break
                if not first_bytes:
                    first_bytes = block[:2]
                out.write(block)
                hasher.update(block)
                downloaded += len(block)
                if on_progress:
                    on_progress(downloaded, total)

    if dest.stat().st_size < 100_000 or first_bytes != b"MZ":
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError("İndirilen Setup geçerli bir Windows kurulum dosyası değil veya bozuk.")

    actual_sha256 = hasher.hexdigest().lower()
    if info.expected_sha256 and actual_sha256 != info.expected_sha256.lower():
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError(
            f"Güncelleme dosyası SHA-256 doğrulamasından geçemedi! "
            f"Beklenen: {info.expected_sha256}, Hesaplanan: {actual_sha256}"
        )

    log.info(f"Setup indirildi ve doğrulandı: {dest} ({dest.stat().st_size} bayt, SHA256={actual_sha256[:16]}...)")
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
