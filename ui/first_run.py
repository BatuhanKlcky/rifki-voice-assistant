"""
ui/first_run.py
---------------
İlk açılış / eksik OmniRoute ayarı: ping + anahtar formu, .env güncelleme.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path
from urllib.parse import urlparse

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QDialogButtonBox, QMessageBox,
)

from config.settings import ENV_PATH, settings
from core.logger import get_logger

log = get_logger("ui.first_run")

DEFAULT_MODEL = "antigravity/gemini-2.5-flash"
# localhost Windows'ta önce ::1 dener; OmniRoute çoğu zaman yalnız IPv4 dinler.
DEFAULT_URL = "http://127.0.0.1:20128/v1/chat/completions"


def omniroute_reachable(timeout: float = 1.5) -> bool:
    """TCP + isteğe bağlı HTTP. localhost yerine 127.0.0.1 tercih edilir."""
    url = os.getenv("OMNIROUTE_URL", DEFAULT_URL) or DEFAULT_URL
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 20128
    # IPv6 localhost tuzağı
    if host in ("localhost", "::1"):
        hosts = ("127.0.0.1",)
    else:
        hosts = (host, "127.0.0.1") if host != "127.0.0.1" else ("127.0.0.1",)

    for h in hosts:
        try:
            with socket.create_connection((h, port), timeout=timeout):
                pass
        except OSError:
            continue
        # Port açık; HTTP ile doğrula (daha güvenilir)
        try:
            import urllib.request
            req = urllib.request.Request(
                f"http://{h}:{port}/v1/models",
                headers={"Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if 200 <= getattr(resp, "status", 200) < 500:
                    return True
        except Exception:
            # TCP açıldıysa servis var say (auth/404 yine de ayakta)
            return True
    return False


def api_key_present() -> bool:
    key = (os.getenv("OMNIROUTE_API_KEY") or "").strip()
    return bool(key)


def needs_first_run() -> bool:
    # Anahtar yoksa her zaman form; OmniRoute kapalıysa da uyar.
    return (not api_key_present()) or (not omniroute_reachable())


def _upsert_env(path: Path, updates: dict[str, str]) -> None:
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8").splitlines()
    keys_done = set()
    out: list[str] = []
    for line in lines:
        matched = False
        for key, value in updates.items():
            if line.startswith(f"{key}="):
                out.append(f"{key}={value}")
                keys_done.add(key)
                matched = True
                break
        if not matched:
            out.append(line)
    for key, value in updates.items():
        if key not in keys_done:
            out.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    for key, value in updates.items():
        os.environ[key] = value


def apply_omni_settings(api_key: str, model: str = "", url: str = "") -> None:
    updates = {
        "OMNIROUTE_API_KEY": api_key.strip(),
        "OMNIROUTE_MODEL": (model or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "OMNIROUTE_URL": (url or DEFAULT_URL).strip() or DEFAULT_URL,
    }
    _upsert_env(ENV_PATH, updates)
    # core.ai rifki_brain singleton — runtime'da yeniden oku
    try:
        from core import ai as ai_mod
        ai_mod.rifki_brain.api_key = updates["OMNIROUTE_API_KEY"]
        ai_mod.rifki_brain.model_name = updates["OMNIROUTE_MODEL"]
        ai_mod.rifki_brain.api_url = updates["OMNIROUTE_URL"]
    except Exception as e:
        log.warning(f"AI ayarları canlı güncellenemedi: {e}")
    log.info("OmniRoute ayarları .env dosyasına yazıldı.")


class FirstRunDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RIFKI — OmniRoute ayarı")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        reachable = omniroute_reachable()
        has_key = api_key_present()
        if reachable:
            status = "çalışıyor (127.0.0.1:20128)"
        else:
            status = "kapalı / ulaşılamıyor (127.0.0.1:20128)"
        key_note = "" if has_key else "<br>API anahtarı henüz kayıtlı değil — aşağıya yapıştır."
        tip = QLabel(
            f"OmniRoute durumu: <b>{status}</b>{key_note}<br><br>"
            "RIFKI cevap üretmek için OmniRoute’a bağlanır. "
            "Servis açıksa anahtarı yapıştırıp Kaydet yeter.<br><br>"
            "İndirme (Windows v3.8.51):<br>"
            "<a href='https://github.com/diegosouzapw/OmniRoute/releases/tag/v3.8.51'>"
            "github.com/diegosouzapw/OmniRoute/releases/tag/v3.8.51</a>"
            "<br><br>Elle TXT düzenlemen gerekmez — Kaydet .env’i yazar."
        )
        tip.setOpenExternalLinks(True)
        tip.setWordWrap(True)
        tip.setTextFormat(Qt.RichText)
        layout.addWidget(tip)

        layout.addWidget(QLabel("OMNIROUTE_API_KEY"))
        self.key_edit = QLineEdit()
        self.key_edit.setText(os.getenv("OMNIROUTE_API_KEY", ""))
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("OmniRoute panelindeki anahtar")
        layout.addWidget(self.key_edit)

        layout.addWidget(QLabel("Model"))
        self.model_edit = QLineEdit()
        self.model_edit.setText(
            os.getenv("OMNIROUTE_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL
        )
        layout.addWidget(self.model_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Ignore
        )
        buttons.button(QDialogButtonBox.Save).setText("Kaydet")
        buttons.button(QDialogButtonBox.Ignore).setText("Sonra")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self):
        key = self.key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "RIFKI", "API anahtarı boş olamaz.")
            return
        apply_omni_settings(key, self.model_edit.text().strip())
        self.accept()


def maybe_show_first_run(parent=None) -> None:
    """Eksik ayar veya OmniRoute kapalıysa diyalog aç."""
    if not needs_first_run():
        return
    dlg = FirstRunDialog(parent)
    dlg.exec_()
