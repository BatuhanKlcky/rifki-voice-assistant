"""
ui/mobile_pairing.py
--------------------
Mobil eşleştirme penceresi: LAN + tunnel QR.
"""

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QFrame,
)

from bridge.pairing import (
    ensure_bridge_token,
    lan_bridge_url,
    make_qr_pixmap,
    pair_uri,
    tunnel_manager,
)
from config.settings import settings
from core.logger import get_logger

log = get_logger("ui.mobile_pairing")


class MobilePairingWindow(QWidget):
    tunnel_ready = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RIFKI — Mobil bağlantı")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(360, 520)
        self.setStyleSheet(
            "QWidget { background: #0A1218; color: #E7F7FF; }"
            "QLabel { background: transparent; }"
            "QPushButton {"
            "  background: #3DF0FF; color: #041018; border: none;"
            "  border-radius: 8px; padding: 10px 14px; font-weight: 600;"
            "}"
            "QPushButton#secondary {"
            "  background: #1A2A34; color: #E7F7FF; border: 1px solid #243442;"
            "}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("Mobil bağlantı")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        root.addWidget(title)

        hint = QLabel(
            "Telefondaki RIFKI uygulamasında «QR tara» deyin ve "
            "aşağıdaki kodu okutun. Bilgisayarınızın açık kalması gerekir."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #6D8FA3; font-size: 13px;")
        root.addWidget(hint)

        self.mode_label = QLabel("Aynı Wi‑Fi")
        self.mode_label.setStyleSheet("color: #3DFFB0; font-size: 12px; letter-spacing: 1px;")
        root.addWidget(self.mode_label)

        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: #121C24; border: 1px solid #243442; border-radius: 12px; }"
        )
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(16, 16, 16, 16)
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setMinimumSize(280, 280)
        fl.addWidget(self.qr_label)
        root.addWidget(frame, stretch=1)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #6D8FA3; font-size: 12px;")
        root.addWidget(self.status)

        row = QHBoxLayout()
        self.btn_lan = QPushButton("Aynı Wi‑Fi")
        self.btn_lan.setObjectName("secondary")
        self.btn_lan.clicked.connect(self.show_lan_qr)
        self.btn_remote = QPushButton("Uzaktan (internet)")
        self.btn_remote.clicked.connect(self.show_remote_qr)
        row.addWidget(self.btn_lan)
        row.addWidget(self.btn_remote)
        root.addLayout(row)

        self.tunnel_ready.connect(self._on_tunnel_url)
        self._token = ""
        self._current_url = ""

    def showEvent(self, event):
        super().showEvent(event)
        self._token = ensure_bridge_token()
        self.show_lan_qr()

    def closeEvent(self, event):
        # Tunnel'ı açık bırakabiliriz; kullanıcı uzaktan kullanıyorsa lazım.
        event.accept()

    def show_lan_qr(self):
        self.mode_label.setText("AYNI WI‑FI")
        url = lan_bridge_url()
        self._set_qr(url, "Telefon ve bilgisayar aynı Wi‑Fi ağında olmalı.")

    def show_remote_qr(self):
        self.mode_label.setText("UZAKTAN")
        self.status.setText("İnternet tüneli açılıyor… Birkaç saniye bekleyin.")
        self.qr_label.clear()
        if tunnel_manager.public_url:
            self._on_tunnel_url(tunnel_manager.public_url)
            return
        ok = tunnel_manager.start(on_url=lambda u: self.tunnel_ready.emit(u))
        if not ok:
            self.status.setText(
                "cloudflared bulunamadı. tools/cloudflared.exe dosyasını kontrol edin."
            )

    def _on_tunnel_url(self, url: str):
        self._set_qr(url, "Bu kod internet üzerinden bağlanır. Tünel açık kaldıkça geçerlidir.")

    def _set_qr(self, base_url: str, note: str):
        self._token = ensure_bridge_token()
        self._current_url = base_url
        uri = pair_uri(base_url, self._token)
        pix = make_qr_pixmap(uri, 280)
        self.qr_label.setPixmap(pix)
        self.status.setText(note)
        log.info(f"Eşleştirme QR hazır: {base_url}")
