"""
ui/mobile_pairing.py
--------------------
Mobil eşleştirme penceresi: LAN + tunnel QR.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QHBoxLayout,
    QPushButton,
    QFrame,
    QApplication,
)

from bridge.pairing import (
    ensure_bridge_token,
    lan_bridge_url,
    make_qr_pixmap,
    pair_uri,
    tunnel_manager,
)
from core.logger import get_logger

log = get_logger("ui.mobile_pairing")


class MobilePairingWindow(QDialog):
    tunnel_ready = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        # parent=None: masaüstü HUD'unun altında kalmasın / tıklama yutmasın
        super().__init__(None)
        self.setWindowTitle("RIFKI — Mobil bağlantı")
        self.setModal(False)
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowStaysOnTopHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
        )
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        self.setMinimumSize(380, 540)
        self.resize(400, 560)
        self.setStyleSheet(
            """
            QDialog { background: #0A1218; color: #E7F7FF; }
            QLabel { background: transparent; }
            QPushButton {
              background: #1A2A34; color: #E7F7FF;
              border: 1px solid #243442; border-radius: 10px;
              padding: 12px 14px; font-weight: 650; font-size: 14px;
            }
            QPushButton:hover { border-color: #3DF0FF; color: #3DF0FF; }
            QPushButton:pressed { background: #243442; }
            QPushButton:disabled { color: #6D8FA3; border-color: #243442; }
            QPushButton[active="true"] {
              background: #3DF0FF; color: #041018; border: none;
            }
            """
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

        self.mode_label = QLabel("AYNI WI‑FI")
        self.mode_label.setStyleSheet(
            "color: #3DFFB0; font-size: 12px; letter-spacing: 1px; font-weight: 650;"
        )
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
        row.setSpacing(10)
        self.btn_lan = QPushButton("Aynı Wi‑Fi")
        self.btn_lan.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_lan.setMinimumHeight(44)
        self.btn_lan.clicked.connect(self.show_lan_qr)
        self.btn_remote = QPushButton("Uzaktan (internet)")
        self.btn_remote.setCursor(QCursor(Qt.PointingHandCursor))
        self.btn_remote.setMinimumHeight(44)
        self.btn_remote.clicked.connect(self.show_remote_qr)
        row.addWidget(self.btn_lan)
        row.addWidget(self.btn_remote)
        root.addLayout(row)

        self.tunnel_ready.connect(self._on_tunnel_url)
        self._token = ""
        self._current_url = ""
        self._set_active_button("lan")

    def _set_active_button(self, which: str) -> None:
        self.btn_lan.setProperty("active", "true" if which == "lan" else "false")
        self.btn_remote.setProperty("active", "true" if which == "remote" else "false")
        self.btn_lan.style().unpolish(self.btn_lan)
        self.btn_lan.style().polish(self.btn_lan)
        self.btn_remote.style().unpolish(self.btn_remote)
        self.btn_remote.style().polish(self.btn_remote)

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)
        self._token = ensure_bridge_token()
        self.show_lan_qr()

    def closeEvent(self, event):
        event.accept()
        self.closed.emit()

    def hideEvent(self, event):
        super().hideEvent(event)
        if not self.isVisible():
            self.closed.emit()

    def show_lan_qr(self):
        log.info("Mobil bağlantı: Aynı Wi‑Fi tıklandı")
        self._set_active_button("lan")
        self.mode_label.setText("AYNI WI‑FI")
        self.mode_label.setStyleSheet(
            "color: #3DFFB0; font-size: 12px; letter-spacing: 1px; font-weight: 650;"
        )
        self.btn_lan.setEnabled(True)
        self.btn_remote.setEnabled(True)
        url = lan_bridge_url()
        self._set_qr(url, "Telefon ve bilgisayar aynı Wi‑Fi ağında olmalı.")
        QApplication.processEvents()

    def show_remote_qr(self):
        log.info("Mobil bağlantı: Uzaktan tıklandı")
        self._set_active_button("remote")
        self.mode_label.setText("UZAKTAN")
        self.mode_label.setStyleSheet(
            "color: #3DF0FF; font-size: 12px; letter-spacing: 1px; font-weight: 650;"
        )
        self.status.setText("İnternet tüneli açılıyor… Birkaç saniye bekleyin.")
        self.qr_label.clear()
        self.btn_remote.setEnabled(False)
        self.btn_lan.setEnabled(True)
        QApplication.processEvents()

        if tunnel_manager.public_url:
            self._on_tunnel_url(tunnel_manager.public_url)
            self.btn_remote.setEnabled(True)
            return

        ok = tunnel_manager.start(on_url=lambda u: self.tunnel_ready.emit(u))
        if not ok:
            self.status.setText(
                "cloudflared bulunamadı. tools/cloudflared.exe dosyasını kontrol edin."
            )
            self.btn_remote.setEnabled(True)
            self._set_active_button("lan")

    def _on_tunnel_url(self, url: str):
        self.btn_remote.setEnabled(True)
        self._set_active_button("remote")
        self._set_qr(
            url,
            "Bu kod internet üzerinden bağlanır. Tünel açık kaldıkça geçerlidir.",
        )

    def _set_qr(self, base_url: str, note: str):
        self._token = ensure_bridge_token()
        self._current_url = base_url
        uri = pair_uri(base_url, self._token)
        pix = make_qr_pixmap(uri, 280)
        self.qr_label.setPixmap(pix)
        self.status.setText(note)
        log.info(f"Eşleştirme QR hazır: {base_url}")
