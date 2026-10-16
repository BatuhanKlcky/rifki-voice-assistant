"""
bridge/pairing.py
-----------------
Mobil eşleştirme: otomatik token, LAN adresi, cloudflared tunnel, QR verisi.
"""

from __future__ import annotations

import os
import re
import secrets
import socket
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from config.settings import BASE_DIR, ENV_PATH, settings
from core.logger import get_logger

log = get_logger("bridge.pairing")

_URL_RE = re.compile(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com")


def ensure_bridge_token() -> str:
    """Token yoksa üretir, settings ve .env dosyasına yazar."""
    token = (settings.MOBILE_BRIDGE_TOKEN or "").strip()
    if token:
        return token
    token = secrets.token_urlsafe(18)
    settings.MOBILE_BRIDGE_TOKEN = token
    _upsert_env("MOBILE_BRIDGE_TOKEN", token)
    _upsert_env("MOBILE_BRIDGE_ENABLED", "true")
    if not os.getenv("MOBILE_BRIDGE_HOST"):
        _upsert_env("MOBILE_BRIDGE_HOST", "0.0.0.0")
        settings.MOBILE_BRIDGE_HOST = "0.0.0.0"
    log.info("Mobil köprü tokeni otomatik üretildi.")
    return token


def _upsert_env(key: str, value: str) -> None:
    path = ENV_PATH
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
    found = False
    out: list[str] = []
    for line in lines:
        if line.startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.environ[key] = value


def lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return "127.0.0.1"


def lan_bridge_url() -> str:
    return f"http://{lan_ip()}:{settings.MOBILE_BRIDGE_PORT}"


def pair_uri(base_url: str, token: str) -> str:
    return f"rifki://pair?u={quote(base_url, safe='')}&t={quote(token, safe='')}"


def cloudflared_path() -> Optional[Path]:
    candidates = [
        BASE_DIR / "tools" / "cloudflared.exe",
        Path(__file__).resolve().parent.parent / "tools" / "cloudflared.exe",
    ]
    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        candidates.insert(0, meipass / "tools" / "cloudflared.exe")
        candidates.insert(0, Path(sys.executable).resolve().parent / "tools" / "cloudflared.exe")
    for p in candidates:
        if p.is_file():
            return p
    return None


def make_qr_pixmap(data: str, size: int = 280):
    """QR kodunu QPixmap olarak üretir. qrcode yoksa Pillow ile basit fallback."""
    from PyQt5.QtGui import QImage, QPixmap

    try:
        import qrcode

        img = qrcode.make(data, border=2)
        img = img.convert("RGB").resize((size, size))
        from io import BytesIO

        buf = BytesIO()
        img.save(buf, format="PNG")
        qimg = QImage.fromData(buf.getvalue())
        return QPixmap.fromImage(qimg)
    except Exception:
        from PIL import Image, ImageDraw

        # Minimal fallback: empty box with text hint (no real QR)
        im = Image.new("RGB", (size, size), (10, 18, 24))
        d = ImageDraw.Draw(im)
        d.rectangle((8, 8, size - 8, size - 8), outline=(61, 240, 255), width=3)
        from io import BytesIO

        buf = BytesIO()
        im.save(buf, format="PNG")
        return QPixmap.fromImage(QImage.fromData(buf.getvalue()))


class TunnelManager:
    """cloudflared quick tunnel; URL hazır olunca callback."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self.public_url: str = ""
        self._on_url = None
        self._lock = threading.Lock()

    def start(self, on_url=None) -> bool:
        self._on_url = on_url
        exe = cloudflared_path()
        if exe is None:
            log.warning("cloudflared.exe bulunamadı (tools/).")
            return False
        self.stop()
        local = f"http://127.0.0.1:{settings.MOBILE_BRIDGE_PORT}"
        try:
            self._proc = subprocess.Popen(
                [str(exe), "tunnel", "--url", local],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError as e:
            log.error(f"cloudflared başlatılamadı: {e}")
            return False
        self._thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._thread.start()
        log.info("cloudflared tunnel başlatıldı.")
        return True

    def _read_stdout(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        for line in proc.stdout:
            m = _URL_RE.search(line)
            if not m:
                continue
            url = m.group(0)
            with self._lock:
                self.public_url = url
            log.info(f"Tunnel URL: {url}")
            if self._on_url:
                try:
                    self._on_url(url)
                except Exception as e:
                    log.error(f"Tunnel URL callback hatası: {e}")
            break

    def stop(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        with self._lock:
            self.public_url = ""


tunnel_manager = TunnelManager()
