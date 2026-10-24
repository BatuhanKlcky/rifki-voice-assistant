"""
ui/main_window.py
------------------
RIFKI komuta ekranı. Masaüstüne sabitlenmiş bir arka plan katmanı:
diğer pencerelerin arkasında durur, boş camdan duvar kâğıdı görünür.
"""

import ctypes
import datetime
import html
import threading
from ctypes import wintypes
from typing import Optional

import psutil
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QPoint, QPointF, QEvent, QMetaObject, Q_ARG,
)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QMessageBox, QFrame, QSystemTrayIcon, QMenu, QAction,
)
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QPixmap, QIcon

from ui.animations import (
    CoreWidget, RadialGauge, WaveformWidget, paint_command_deck, paint_brackets,
    AsciiBackdrop, AsciiEyeAnchor,
)
from bridge.pairing import ensure_bridge_token, tunnel_manager
from bridge.service import mobile_bridge
from config.settings import settings
from core.ai import rifki_brain
from core.logger import get_logger
from core.updater import ReleaseInfo, check_for_update, download_setup, launch_installer
from core.version import APP_VERSION
from ui.first_run import maybe_show_first_run
from ui.mobile_pairing import MobilePairingWindow
from voice.wake_word import wait_for_wake_word, matches_wake_word
from voice.speech_to_text import listen_and_transcribe, MicrophoneError, SpeechServiceError
from voice.text_to_speech import speak

log = get_logger("ui.main_window")

WM_NCHITTEST = 0x0084
WM_MOUSEACTIVATE = 0x0021
WM_SYSCOMMAND = 0x0112
HTTRANSPARENT = -1
MA_NOACTIVATE = 3
SC_MINIMIZE = 0xF020
HWND_BOTTOM = 1
HWND_TOPMOST = -1
SW_SHOWNOACTIVATE = 4
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
SWP_NOOWNERZORDER = 0x0200

_user32 = ctypes.windll.user32

NEON_CYAN = "#3DF0FF"
BG_DARK = "#02060C"
MONTHS_TR = (
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
)

# QThread'lerin Windows'taki varsayılan stack boyutu (~1MB) Piper/onnxruntime
# gibi ağır native kütüphaneler için yetersiz kalıp sessiz bir çökmeye (stack
# overflow) yol açabiliyor. VoiceWorker.start() çağrılmadan ÖNCE ayarlanmalı.
VOICE_WORKER_STACK_SIZE = 16 * 1024 * 1024  # 16 MB

APP_QSS = """
QMessageBox { background-color: #071018; }
QMessageBox QLabel { color: #e7f7ff; font-family: Consolas; font-size: 13px; }
QMessageBox QPushButton {
    background-color: #071018;
    color: #3DF0FF;
    border: 1px solid #3DF0FF;
    border-radius: 0px;
    padding: 6px 16px;
    font-family: Consolas;
    font-weight: bold;
    min-width: 88px;
}
QMessageBox QPushButton:hover { background-color: #103049; }
QMenu {
    background-color: #071018;
    color: #e7f7ff;
    border: 1px solid rgba(61, 240, 255, 160);
    font-family: Consolas;
    padding: 4px;
}
QMenu::item { padding: 6px 22px; }
QMenu::item:selected { background-color: #103049; }
QToolTip {
    background-color: #071018;
    color: #e7f7ff;
    border: 1px solid #3DF0FF;
    font-family: Consolas;
}
"""

STATUS_COPY = {
    "IDLE": ("UYANDIRMA", "Uyandırma kelimesi bekleniyor"),
    "LISTENING": ("DİNLİYOR", "Komut alınıyor"),
    "THINKING": ("ANALİZ", "İstek yorumlanıyor"),
    "PROCESSING": ("İŞLEM", "Araç çalıştırılıyor"),
    "SPEAKING": ("KONUŞUYOR", "Sesli yanıt veriliyor"),
}

PILL_COPY = {
    "OFF": ("SİSTEM  KAPALI", "#6d8fa3"),
    "IDLE": ("SİSTEM  DİNLEMEDE", "#7FD8FF"),
    "LISTENING": ("SİSTEM  SİNYAL", "#3DFFB0"),
    "THINKING": ("SİSTEM  ANALİZ", "#FFB020"),
    "PROCESSING": ("SİSTEM  İŞLEM", "#FF8A3D"),
    "SPEAKING": ("SİSTEM  YAYIN", "#3DF0FF"),
}


def _build_tray_icon_pixmap() -> QPixmap:
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(61, 240, 255))
    pen.setWidth(4)
    painter.setPen(pen)
    painter.setBrush(QColor(4, 18, 28))
    painter.drawEllipse(8, 8, size - 16, size - 16)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(16, 16, size - 32, size - 32)
    painter.setBrush(QColor(61, 240, 255))
    painter.setPen(Qt.NoPen)
    r = 5
    painter.drawEllipse(size // 2 - r, size // 2 - r, r * 2, r * 2)
    painter.end()
    return pixmap


def _pretty_wake(word: str) -> str:
    word = (word or "rıfkı").strip()
    return word[:1].upper() + word[1:]


class HudPanel(QFrame):
    """Köşe nişangâhlı, başlığı çerçevenin üstüne oturan cam plaka."""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self._title = title
        self.setStyleSheet("background-color: rgba(4, 12, 22, 242); border: none;")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        paint_brackets(painter, 1, 1, self.width() - 2, self.height() - 2, length=16, color=QColor(61, 240, 255, 180), width=1.4)
        hairline = QPen(QColor(61, 240, 255, 90))
        hairline.setWidthF(1.0)
        painter.setPen(hairline)
        painter.drawLine(18, 1, self.width() - 18, 1)
        if self._title:
            painter.setFont(QFont("Consolas", 9))
            painter.setPen(QColor(61, 240, 255))
            painter.drawText(18, 20, self._title)


class PipelineStep(QFrame):
    def __init__(self, code: str, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("pipelineStep")
        self.setFixedHeight(34)
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 0, 10, 0)
        row.setSpacing(8)
        self.code = QLabel(code)
        self.code.setObjectName("stepCode")
        self.name = QLabel(title)
        self.name.setObjectName("stepName")
        self.phase = QLabel("—")
        self.phase.setObjectName("stepPhase")
        self.phase.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.code)
        row.addWidget(self.name)
        row.addStretch()
        row.addWidget(self.phase)
        self.set_mode("idle")

    def set_mode(self, mode: str, accent: str = "#3DF0FF"):
        if mode == "active":
            bg, border, text, phase_color, phase = f"rgba(61, 240, 255, 22)", accent, "#F4FDFF", accent, "AKTİF"
        elif mode == "armed":
            bg, border, text, phase_color, phase = "rgba(127, 216, 255, 16)", "#7FD8FF", "#D7F4FF", "#9BDCFF", "ARANIYOR"
        elif mode == "done":
            bg, border, text, phase_color, phase = "transparent", "#1F8A62", "#8EE0C2", "#5DBE9A", "TAMAM"
        else:
            bg, border, text, phase_color, phase = "transparent", "rgba(61, 240, 255, 45)", "#6D8FA3", "#4E7084", "—"
        self.phase.setText(phase)
        self.setStyleSheet(
            f"""
            QFrame#pipelineStep {{
                background: {bg};
                border: none;
                border-left: 3px solid {border};
            }}
            QLabel#stepCode {{
                color: {phase_color};
                font-family: Consolas;
                font-size: 12px;
                font-weight: bold;
                background: transparent;
            }}
            QLabel#stepName {{
                color: {text};
                font-family: Consolas;
                font-size: 12px;
                font-weight: bold;
                background: transparent;
            }}
            QLabel#stepPhase {{
                color: {phase_color};
                font-family: Consolas;
                font-size: 10px;
                letter-spacing: 1px;
                background: transparent;
            }}
            """
        )


class ConfirmBridge:
    def __init__(self):
        self._event = threading.Event()
        self._answer = ""
        self.request_signal = None

    def ask(self, prompt: str) -> str:
        self._event.clear()
        if self.request_signal:
            self.request_signal.emit(prompt)
        self._event.wait(timeout=60)
        return self._answer

    def provide_answer(self, answer: str):
        self._answer = answer
        self._event.set()


# Konuşarak dinlemeyi durdurmak için söylenebilecek ifadeler (küçük harfe
# çevrilip içinde geçip geçmediğine bakılır, tam eşleşme aranmaz).
STOP_LISTENING_PHRASES = ("dinlemeyi durdur", "dinlemeyi kapat", "sustur", "sus artık")


class UpdateWorker(QThread):
    """Arka planda GitHub Releases kontrol / indirme."""

    checked = pyqtSignal(object)  # ReleaseInfo | None
    failed = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    downloaded = pyqtSignal(str)  # setup path

    def __init__(self, mode: str = "check", release: Optional[ReleaseInfo] = None):
        super().__init__()
        self.mode = mode  # "check" | "download"
        self.release = release

    def run(self):
        try:
            if self.mode == "check":
                info = check_for_update()
                self.checked.emit(info)
                return
            if self.mode == "download" and self.release is not None:
                path = download_setup(
                    self.release,
                    on_progress=lambda d, t: self.progress.emit(d, t),
                )
                self.downloaded.emit(str(path))
                return
            self.failed.emit("Geçersiz güncelleme işlemi.")
        except Exception as e:
            log.error(f"Güncelleme işçisi: {e}")
            self.failed.emit(str(e))


class VoiceWorker(QThread):
    status_changed = pyqtSignal(str)
    user_message = pyqtSignal(str)
    assistant_message = pyqtSignal(str)
    error_message = pyqtSignal(str)
    confirmation_requested = pyqtSignal(str)
    # Sesli "dinlemeyi durdur" komutuyla worker kendi kendini durdurduğunda
    # arayüzdeki butonu/metni senkronize etmek için UI'a haber verir.
    stopped_by_voice = pyqtSignal()
    wake_acknowledged = pyqtSignal()

    def __init__(self, confirm_bridge: ConfirmBridge):
        super().__init__()
        self._running = True
        self.confirm_bridge = confirm_bridge
        self.confirm_bridge.request_signal = self.confirmation_requested

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            self.status_changed.emit("IDLE")
            try:
                heard = wait_for_wake_word(stop_flag_check=lambda: not self._running)
            except MicrophoneError as e:
                self.error_message.emit(str(e))
                self.msleep(2000)
                continue
            except Exception as e:
                log.error(f"Wake word döngüsü hatası: {e}")
                self.error_message.emit("Mikrofon erişiminde bir sorun oluştu.")
                self.msleep(2000)
                continue

            if not heard or not self._running:
                continue

            self.wake_acknowledged.emit()
            self.status_changed.emit("SPEAKING")
            try:
                speak("Efendim.")
            except Exception as e:
                log.error(f"Uyandırma yanıtı söylenemedi: {e}")

            # Wake word bir kez söylendikten sonra, kullanıcı "dinlemeyi
            # durdur" demedikçe veya arayüzdeki buton kapatılmadıkça sohbet
            # sürekli devam eder — sessizlikte veya boş algılamada wake
            # word'ü tekrar söylemeye gerek kalmaz.
            in_conversation = True
            consecutive_mic_errors = 0
            while in_conversation and self._running:
                self.status_changed.emit("LISTENING")
                try:
                    command_text = listen_and_transcribe(timeout=8, phrase_time_limit=12)
                    consecutive_mic_errors = 0
                except (MicrophoneError, SpeechServiceError) as e:
                    consecutive_mic_errors += 1
                    self.error_message.emit(str(e))
                    if consecutive_mic_errors >= 5:
                        break
                    continue

                if not command_text:
                    continue

                normalized = command_text.strip().lower()
                if matches_wake_word(normalized) and len(normalized.split()) <= 3:
                    self.wake_acknowledged.emit()
                    self.status_changed.emit("SPEAKING")
                    try:
                        speak("Efendim.")
                    except Exception as e:
                        log.error(f"Uyandırma yanıtı söylenemedi: {e}")
                    continue

                if any(phrase in normalized for phrase in STOP_LISTENING_PHRASES):
                    self.assistant_message.emit("Dinlemeyi durduruyorum.")
                    self.status_changed.emit("SPEAKING")
                    try:
                        speak("Dinlemeyi durduruyorum.")
                    except Exception as e:
                        log.error(f"TTS hatası: {e}")
                    self._running = False
                    self.stopped_by_voice.emit()
                    break

                self.user_message.emit(command_text)
                self.status_changed.emit("THINKING")

                try:
                    response_text = rifki_brain.process(
                        command_text,
                        ask_fn=self.confirm_bridge.ask,
                        status_callback=self.status_changed.emit,
                    )
                except Exception as e:
                    log.error(f"AI işleme hatası: {e}")
                    response_text = "Yapay zekâ servisine şu anda ulaşamıyorum."

                self.assistant_message.emit(response_text)
                self.status_changed.emit("SPEAKING")
                try:
                    speak(response_text)
                except Exception as e:
                    log.error(f"TTS hatası: {e}")
                # Yanıt bittikten sonra tekrar LISTENING'e dön, wake word
                # aranmaz — in_conversation True kaldığı sürece döngü sürer.


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RIFKI")
        self._wake_pretty = _pretty_wake(settings.WAKE_WORD)
        self._dot_color = "#6d8fa3"
        self._dot_on = True

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint
        )
        # Şeffaf arka plan katmanı. Bayraklardan SONRA verilmeli; aksi halde
        # Windows katmanlı pencereyi opak çizer.
        # NOT: Qt.Tool bayrağı kasıtlı olarak KALDIRILDI — o bayrak pencereyi
        # görev çubuğundan ve Alt+Tab listesinden gizliyordu.
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)

        self.setMinimumSize(900, 600)
        self.ascii_backdrop = AsciiBackdrop(pixel_size=11)
        self._build_ui()
        self._apply_theme()
        self._setup_tray_icon()

        self.confirm_bridge = ConfirmBridge()
        self.voice_worker = VoiceWorker(self.confirm_bridge)
        # ÖNEMLİ: start()'tan önce ayarlanmalı. Piper/onnxruntime gibi ağır
        # native kütüphaneler QThread'in küçük varsayılan stack'inde sessizce
        # çöküyordu (bkz. VOICE_WORKER_STACK_SIZE açıklaması yukarıda).
        self.voice_worker.setStackSize(VOICE_WORKER_STACK_SIZE)
        self.voice_worker.status_changed.connect(self.on_status_changed)
        self.voice_worker.user_message.connect(self.on_user_message)
        self.voice_worker.assistant_message.connect(self.on_assistant_message)
        self.voice_worker.error_message.connect(self.on_error_message)
        self.voice_worker.confirmation_requested.connect(self.on_confirmation_requested)
        self.voice_worker.stopped_by_voice.connect(self.on_stopped_by_voice)
        self.voice_worker.wake_acknowledged.connect(self.on_wake_acknowledged)

        self._mobile_busy = False
        self._pairing_window = None
        self._pending_release: Optional[ReleaseInfo] = None
        self._update_worker: Optional[UpdateWorker] = None
        self._update_action = None
        # Mobil QR açıkken HUD tıklamayı yutmasın (pencere camın arkasında kalabiliyor)
        self._pairing_mouse_passthrough = False
        ensure_bridge_token()
        mobile_bridge.set_command_handler(self._handle_mobile_command)
        if mobile_bridge.start():
            log.info(
                f"Mobil köprü dinliyor: {settings.MOBILE_BRIDGE_HOST}:"
                f"{settings.MOBILE_BRIDGE_PORT}"
            )

        self._disk_sample_every = 5  # her N stats tick (2s * 5 = 10s)
        self._stats_tick = 0
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(2000)
        self._update_stats()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink_dot)
        self._blink_timer.start(700)

        self._desktop_timer = QTimer(self)
        self._desktop_timer.timeout.connect(self._keep_behind_windows)
        self._desktop_timer.start(2500)

        self._ascii_timer = QTimer(self)
        self._ascii_timer.timeout.connect(self.update)
        self._ascii_timer.start(45)  # ~22 FPS akıcı ve hafif animasyon

    def _setup_tray_icon(self):
        icon = QIcon(_build_tray_icon_pixmap())
        self.setWindowIcon(icon)
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip(f"RIFKI v{APP_VERSION}")
        menu = QMenu()
        show_action = QAction("Göster", self)
        show_action.triggered.connect(self._show_from_tray)
        hide_action = QAction("Gizle", self)
        hide_action.triggered.connect(self.hide)
        quit_action = QAction("Çıkış", self)
        quit_action.triggered.connect(self._quit_app)
        mobile_action = QAction("Mobil bağlantı", self)
        mobile_action.triggered.connect(self._open_mobile_pairing)
        self._update_action = QAction("Güncellemeleri kontrol et", self)
        self._update_action.triggered.connect(self._manual_update_check)
        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addAction(mobile_action)
        menu.addSeparator()
        menu.addAction(self._update_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()
        QTimer.singleShot(600, self._announce_started)
        if settings.AUTO_UPDATE:
            QTimer.singleShot(12_000, self._silent_update_check)

    def _open_mobile_pairing(self):
        ensure_bridge_token()
        if not mobile_bridge.start():
            mobile_bridge.start()
        if self._pairing_window is None:
            # Ana HUD wallpaper katmanında; pairing ayrı top-level dialog olmalı
            self._pairing_window = MobilePairingWindow(None)
            self._pairing_window.closed.connect(self._on_pairing_closed)
        self._pairing_mouse_passthrough = True
        self._pairing_window.show()
        self._pairing_window.raise_()
        self._pairing_window.activateWindow()
        try:
            hwnd = int(self._pairing_window.winId())
            _user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW | SWP_NOOWNERZORDER,
            )
            _user32.SetForegroundWindow(hwnd)
        except Exception as e:
            log.error(f"Mobil pencere öne alınamadı: {e}")

    def _on_pairing_closed(self):
        self._pairing_mouse_passthrough = False

    def _silent_update_check(self):
        if not settings.AUTO_UPDATE:
            return
        self._start_update_check(silent=True)

    def _manual_update_check(self):
        if self._pending_release is not None:
            self._prompt_install_update(self._pending_release)
            return
        self._start_update_check(silent=False)

    def _start_update_check(self, silent: bool):
        if self._update_worker is not None and self._update_worker.isRunning():
            return
        if self._update_action is not None and not silent:
            self._update_action.setEnabled(False)
            self._update_action.setText("Kontrol ediliyor…")
        worker = UpdateWorker("check")
        self._update_worker = worker
        worker.checked.connect(
            lambda info: self._on_update_checked(info, silent=silent)
        )
        worker.failed.connect(
            lambda err: self._on_update_failed(err, silent=silent)
        )
        worker.start()

    def _on_update_checked(self, info, silent: bool):
        if self._update_action is not None:
            self._update_action.setEnabled(True)
        if info is None:
            if self._update_action is not None:
                self._update_action.setText("Güncellemeleri kontrol et")
            if not silent:
                QMessageBox.information(
                    None,
                    "RIFKI",
                    f"RIFKI güncel (v{APP_VERSION}).",
                )
            return
        self._pending_release = info
        if self._update_action is not None:
            self._update_action.setText(f"Güncellemeyi yükle (v{info.version})")
        if silent and self.tray_icon is not None:
            self.tray_icon.showMessage(
                "RIFKI güncelleme",
                f"v{info.version} hazır. Tepsi → Güncellemeyi yükle.",
                QSystemTrayIcon.Information,
                10000,
            )
            return
        self._prompt_install_update(info)

    def _on_update_failed(self, err: str, silent: bool):
        if self._update_action is not None:
            self._update_action.setEnabled(True)
            self._update_action.setText("Güncellemeleri kontrol et")
        if silent:
            log.warning(f"Otomatik güncelleme kontrolü: {err}")
            return
        QMessageBox.warning(
            None,
            "RIFKI",
            f"Güncelleme kontrol edilemedi:\n{err}",
        )

    def _prompt_install_update(self, info: ReleaseInfo):
        box = QMessageBox(None)
        box.setWindowTitle("RIFKI güncelleme")
        box.setIcon(QMessageBox.Question)
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        box.setText(f"Yeni sürüm: v{info.version}\nŞu an: v{APP_VERSION}")
        box.setInformativeText(
            "Kurulum indirilip sessizce uygulanacak. RIFKI kapanıp yeniden açılır."
        )
        install = box.addButton("Şimdi güncelle", QMessageBox.AcceptRole)
        box.addButton("Sonra", QMessageBox.RejectRole)
        box.exec_()
        if box.clickedButton() is install:
            self._download_and_install(info)

    def _download_and_install(self, info: ReleaseInfo):
        if self._update_worker is not None and self._update_worker.isRunning():
            return
        if self._update_action is not None:
            self._update_action.setEnabled(False)
            self._update_action.setText("İndiriliyor…")
        if self.tray_icon is not None:
            self.tray_icon.showMessage(
                "RIFKI",
                f"v{info.version} indiriliyor…",
                QSystemTrayIcon.Information,
                5000,
            )
        worker = UpdateWorker("download", release=info)
        self._update_worker = worker
        worker.downloaded.connect(self._on_update_downloaded)
        worker.failed.connect(
            lambda err: self._on_update_failed(err, silent=False)
        )
        worker.start()

    def _on_update_downloaded(self, path: str):
        try:
            launch_installer(path)
        except Exception as e:
            self._on_update_failed(str(e), silent=False)
            return
        if self.tray_icon is not None:
            self.tray_icon.showMessage(
                "RIFKI",
                "Kurulum başladı. RIFKI kapanıyor…",
                QSystemTrayIcon.Information,
                4000,
            )
        QTimer.singleShot(800, self._quit_app)

    def _announce_started(self):
        if self.tray_icon is not None:
            self.tray_icon.showMessage(
                "RIFKI",
                "Açık. Arayüz masaüstünde (Win+D). Tepsi → Mobil bağlantı / Çıkış.",
                QSystemTrayIcon.Information,
                8000,
            )
        # OmniRoute kapalı veya anahtar yoksa kurulum formu (TXT yok).
        maybe_show_first_run(self)
        box = QMessageBox(self)
        box.setWindowTitle("RIFKI")
        box.setIcon(QMessageBox.Information)
        box.setWindowFlags(box.windowFlags() | Qt.WindowStaysOnTopHint)
        box.setText("RIFKI açıldı.")
        box.setInformativeText(
            "Arayüz masaüstünde, diğer pencerelerin arkasında (Win+D).\n"
            "Mobil QR: tepsi simgesi → Mobil bağlantı"
        )
        box.setStandardButtons(QMessageBox.Ok)
        box.exec_()


    def _show_from_tray(self):
        self.show()
        self._anchor_to_desktop()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_ascii_timer") and not self._ascii_timer.isActive():
            self._ascii_timer.start(45)
        QTimer.singleShot(0, self._anchor_to_desktop)
        if not self._listening_autostarted:
            self._listening_autostarted = True
            QTimer.singleShot(400, self._arm_listening)

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "_ascii_timer"):
            self._ascii_timer.stop()

    def _arm_listening(self):
        if self._listening_active or self.voice_worker.isRunning():
            return
        self.toggle_listening()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            self.setWindowState(Qt.WindowNoState)
            QTimer.singleShot(0, self._anchor_to_desktop)
        super().changeEvent(event)

    def _anchor_to_desktop(self):
        """Ekranı kaplar ama en arkada kalır; konum sabit."""
        screen = QApplication.primaryScreen()
        if screen is not None:
            self.setGeometry(screen.geometry())
        self._keep_behind_windows()

    def _keep_behind_windows(self):
        if not self.isVisible():
            return
        hwnd = int(self.winId())
        if _user32.IsIconic(hwnd):
            _user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        _user32.SetWindowPos(
            hwnd, HWND_BOTTOM, 0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
        )

    def _quit_app(self):
        tunnel_manager.stop()
        mobile_bridge.stop()
        self.voice_worker.stop()
        self.voice_worker.wait(2000)
        QApplication.quit()

    def _handle_mobile_command(self, text: str) -> str:
        """Telefondan gelen komut. aiohttp thread pool'undan çağrılır."""
        if self._mobile_busy:
            return "Şu an başka bir mobil komut işleniyor."
        self._mobile_busy = True
        try:
            mobile_bridge.publish_user(text)
            QMetaObject.invokeMethod(
                self, "_ui_show_user", Qt.QueuedConnection,
                Q_ARG(str, text),
            )
            mobile_bridge.publish_state("THINKING")
            QMetaObject.invokeMethod(
                self, "_ui_set_status", Qt.QueuedConnection,
                Q_ARG(str, "THINKING"),
            )

            def _status(state: str):
                mobile_bridge.publish_state(state)
                QMetaObject.invokeMethod(
                    self, "_ui_set_status", Qt.QueuedConnection,
                    Q_ARG(str, state),
                )

            # AI'sız kısa yollar (OmniRoute kapalıysa da çalışır)
            folded = (text or "").casefold()
            if any(k in folded for k in ("ekran görüntüsü", "ekran goruntusu", "screenshot", "ekranı al", "ekrani al")):
                try:
                    from tools.system import take_screenshot
                    reply = take_screenshot() + " Mobilde görmek için üstteki «Ekran görüntüsü» düğmesini kullan."
                except Exception as e:
                    log.error(f"Mobil screenshot kısayolu: {e}")
                    reply = "Ekran görüntüsü alınamadı."
            else:
                try:
                    reply = rifki_brain.process(
                        text,
                        ask_fn=self.confirm_bridge.ask,
                        status_callback=_status,
                    )
                except Exception as e:
                    log.error(f"Mobil komut AI hatası: {e}")
                    reply = "Yapay zekâ servisine şu anda ulaşamıyorum."

            mobile_bridge.publish_assistant(reply)
            QMetaObject.invokeMethod(
                self, "_ui_show_assistant", Qt.QueuedConnection,
                Q_ARG(str, reply),
            )
            mobile_bridge.publish_state("SPEAKING")
            QMetaObject.invokeMethod(
                self, "_ui_set_status", Qt.QueuedConnection,
                Q_ARG(str, "SPEAKING"),
            )
            try:
                speak(reply)
            except Exception as e:
                log.error(f"Mobil TTS hatası: {e}")
            idle = "LISTENING" if self._listening_active else "IDLE"
            mobile_bridge.publish_state(idle)
            QMetaObject.invokeMethod(
                self, "_ui_set_status", Qt.QueuedConnection,
                Q_ARG(str, idle),
            )
            return reply
        finally:
            self._mobile_busy = False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(2, 6, 12))

        if hasattr(self, "_eye_anchor") and self._eye_anchor is not None:
            anchor_pos = self._eye_anchor.mapTo(self, QPoint(0, 0))
            eye_cx = anchor_pos.x() + self._eye_anchor.width() / 2.0
            eye_cy = anchor_pos.y() + self._eye_anchor.height() / 2.0
            eye_center = QPointF(eye_cx, eye_cy)
        else:
            eye_center = QPointF(self.width() / 2.0, self.height() * 0.44)

        if hasattr(self, "ascii_backdrop") and self.ascii_backdrop is not None:
            self.ascii_backdrop.paint(painter, self.width(), self.height(), eye_center)
        else:
            paint_command_deck(painter, self.rect(), glass=True)
        painter.end()

    def nativeEvent(self, eventType, message):
        """Arka planda kalır. Boş cam tıklamayı masaüstüne bırakır.
        Paneller ve düğmeler kendi tıklamasını tutar.
        Mobil QR açıkken tüm HUD tıklamayı geçirir (QR arkasında kalabiliyor)."""
        try:
            if eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_MOUSEACTIVATE:
                    return True, MA_NOACTIVATE
                if msg.message == WM_SYSCOMMAND and (int(msg.wParam) & 0xFFF0) == SC_MINIMIZE:
                    return True, 0
                if msg.message == WM_NCHITTEST:
                    if self._pairing_mouse_passthrough or self._point_is_glass(msg.lParam):
                        return True, HTTRANSPARENT
        except Exception as e:
            log.error(f"Masaüstü katmanı hatası: {e}")
        return QWidget.nativeEvent(self, eventType, message)

    def _point_is_glass(self, lparam) -> bool:
        packed = int(lparam) & 0xFFFFFFFF
        x = ctypes.c_short(packed & 0xFFFF).value
        y = ctypes.c_short((packed >> 16) & 0xFFFF).value
        local = self.mapFromGlobal(QPoint(x, y))
        if not self.rect().contains(local):
            return False
        widget = self.childAt(local)
        if widget is None or widget is self._center_host or widget is getattr(self, "_eye_anchor", None):
            return True
        return False

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            "color: #7FD8FF; font-family: Consolas; font-size: 10px; "
            "font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        return label

    def _meta_row(self, key: str, value: str):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        key_label = QLabel(key)
        key_label.setStyleSheet(
            "color: #6D8FA3; font-family: Consolas; font-size: 11px; background: transparent;"
        )
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value_label.setStyleSheet(
            "color: #E7F7FF; font-family: Consolas; font-size: 11px; font-weight: bold; background: transparent;"
        )
        row.addWidget(key_label)
        row.addStretch()
        row.addWidget(value_label)
        return row, value_label

    def _window_button(self, text: str, color: str, slot, tip: str) -> QPushButton:
        button = QPushButton(text)
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedSize(28, 24)
        button.setToolTip(tip)
        button.clicked.connect(slot)
        button.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {color}; border: none; "
            f"font-family: Consolas; font-size: 14px; }}"
            f"QPushButton:hover {{ color: #FFFFFF; }}"
        )
        return button

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 26, 28, 22)
        root.setSpacing(12)

        root.addLayout(self._build_header())

        middle = QHBoxLayout()
        middle.setSpacing(18)
        middle.addStretch(1)
        middle.addWidget(self._build_left_panel(), stretch=0)
        middle.addWidget(self._build_center(), stretch=0)
        middle.addWidget(self._build_right_panel(), stretch=0)
        middle.addStretch(1)
        root.addLayout(middle, stretch=1)

        root.addLayout(self._build_bottom())
        self._listening_active = False
        self._listening_autostarted = False
        self._style_arm_button(False)
        self._set_sys_pill("OFF")
        self._paint_pipeline("OFF")

    def _build_header(self):
        top_bar = QHBoxLayout()
        top_bar.setSpacing(14)

        brand = QVBoxLayout()
        brand.setSpacing(0)
        kicker = QLabel("NEURAL VOICE SYSTEM")
        kicker.setStyleSheet(
            "color: #6D8FA3; font-family: Consolas; font-size: 10px; letter-spacing: 2px; background: transparent;"
        )
        title = QLabel("RIFKI")
        title.setStyleSheet(
            "color: #F4FDFF; font-family: Consolas; font-size: 22px; "
            "font-weight: bold; letter-spacing: 6px; background: transparent;"
        )
        brand.addWidget(kicker)
        brand.addWidget(title)
        top_bar.addLayout(brand)

        top_bar.addStretch()

        self.sys_status_frame = HudPanel()
        sys_layout = QHBoxLayout(self.sys_status_frame)
        sys_layout.setContentsMargins(14, 6, 14, 6)
        self.sys_dot = QLabel("●")
        self.sys_text = QLabel("SİSTEM  KAPALI")
        self.sys_text.setStyleSheet(
            "color: #C7F5FF; font-family: Consolas; font-size: 11px; font-weight: bold; "
            "letter-spacing: 1px; background: transparent;"
        )
        sys_layout.addWidget(self.sys_dot)
        sys_layout.addWidget(self.sys_text)
        top_bar.addWidget(self.sys_status_frame)

        top_bar.addStretch()

        clock_box = QVBoxLayout()
        clock_box.setSpacing(0)
        self.date_label = QLabel("")
        self.date_label.setAlignment(Qt.AlignRight)
        self.date_label.setStyleSheet(
            "color: #7FD8FF; font-family: Consolas; font-size: 11px; background: transparent;"
        )
        self.clock_label = QLabel("00:00:00")
        self.clock_label.setAlignment(Qt.AlignRight)
        self.clock_label.setStyleSheet(
            f"color: {NEON_CYAN}; font-family: Consolas; font-size: 18px; font-weight: bold; "
            "letter-spacing: 1px; background: transparent;"
        )
        clock_box.addWidget(self.date_label)
        clock_box.addWidget(self.clock_label)
        top_bar.addLayout(clock_box)

        top_bar.addWidget(self._window_button("—", NEON_CYAN, self.hide, "Tepsiye küçült"))
        top_bar.addWidget(self._window_button("✕", "#FF6B6B", self._quit_app, "Çıkış"))
        return top_bar

    def _build_left_panel(self):
        panel = HudPanel("01   /   SİNYAL HATTI")
        panel.setFixedWidth(360)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 32, 14, 14)
        layout.setSpacing(8)

        self._steps = [
            PipelineStep("01", "DİNLEME"),
            PipelineStep("02", "ANALİZ"),
            PipelineStep("03", "ÜRETİM"),
            PipelineStep("04", "SES ÇIKIŞI"),
        ]
        for step in self._steps:
            layout.addWidget(step)

        layout.addSpacing(8)
        layout.addWidget(self._section_label("SON İLETİ"))
        self.ai_status_desc = QLabel(
            f"Bağlantı kapalı. Açıldığında «{self._wake_pretty}» ile uyanırım."
        )
        self.ai_status_desc.setWordWrap(True)
        self.ai_status_desc.setTextFormat(Qt.PlainText)
        self.ai_status_desc.setMinimumHeight(72)
        self.ai_status_desc.setStyleSheet(
            "color: #E7F7FF; font-family: Consolas; font-size: 12px; "
            "background: rgba(0, 8, 16, 160); padding: 10px; border-left: 2px solid #3DF0FF;"
        )
        layout.addWidget(self.ai_status_desc)

        layout.addStretch()
        layout.addWidget(self._section_label("ALT SİSTEMLER"))

        engine = {"piper": "PIPER", "edge": "EDGE", "gtts": "GTTS", "pyttsx3": "SAPI"}.get(
            settings.TTS_ENGINE, settings.TTS_ENGINE.upper()
        )
        audio_row, self.audio_value = self._meta_row("SES BAĞLANTISI", "KAPALI")
        tts_row, _tts_value = self._meta_row("SES MOTORU", engine)
        wake_row, _wake_value = self._meta_row("UYANDIRMA", self._wake_pretty.upper())
        lang_row, _lang_value = self._meta_row("KANAL", settings.STT_LANGUAGE.upper())
        for row in (audio_row, tts_row, wake_row, lang_row):
            layout.addLayout(row)
        return panel

    def _build_center(self):
        host = QWidget()
        host.setFixedWidth(540)
        host.setAttribute(Qt.WA_TranslucentBackground, True)
        host.setAutoFillBackground(False)
        host.setStyleSheet("background: transparent;")
        self._center_host = host
        center = QVBoxLayout(host)
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(4)
        center.addStretch(1)

        kicker = QLabel("SİBERNETİK GÖZ")
        kicker.setAlignment(Qt.AlignCenter)
        kicker.setStyleSheet(
            f"color: {NEON_CYAN}; font-family: Consolas; font-size: 10px; letter-spacing: 3px; background: transparent;"
        )
        center.addWidget(kicker)

        self._eye_anchor = AsciiEyeAnchor(self.ascii_backdrop)
        self.core_widget = self._eye_anchor
        center.addWidget(self._eye_anchor, alignment=Qt.AlignHCenter)

        center.addSpacing(16)
        self.status_label = QLabel("BEKLEMEDE")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(
            "color: #F4FDFF; font-family: Consolas; font-size: 18px; "
            "font-weight: bold; letter-spacing: 4px; background: transparent;"
        )
        center.addWidget(self.status_label)

        self.status_detail = QLabel("Ses bağlantısı kapalı")
        self.status_detail.setAlignment(Qt.AlignCenter)
        self.status_detail.setStyleSheet(
            "color: #7FD8FF; font-family: Consolas; font-size: 11px; letter-spacing: 1px; background: transparent;"
        )
        center.addWidget(self.status_detail)

        self.waveform = WaveformWidget()
        self.waveform.setFixedSize(400, 56)
        center.addSpacing(10)
        center.addWidget(self.waveform, alignment=Qt.AlignHCenter)
        center.addStretch(1)
        return host

    def _build_right_panel(self):
        panel = HudPanel("02   /   İLETİŞİM KAYDI")
        panel.setFixedWidth(420)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 32, 14, 14)
        layout.setSpacing(8)

        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet(
            """
            QTextEdit {
                background-color: rgba(0, 8, 16, 150);
                color: #E7F7FF;
                font-family: Consolas;
                font-size: 12px;
                border: 1px solid rgba(61, 240, 255, 35);
                padding: 8px;
            }
            QScrollBar:vertical { background: transparent; width: 8px; margin: 0; }
            QScrollBar::handle:vertical { background: rgba(61, 240, 255, 110); min-height: 24px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar:horizontal { height: 0; }
            """
        )
        self.chat_log.append(
            "<span style='color:#6D8FA3'>// oturum açıldı. ses bağlantısı bekleniyor.</span>"
        )
        layout.addWidget(self.chat_log, stretch=1)

        layout.addWidget(self._section_label("OTURUM"))
        mem_row, _mem = self._meta_row("HAFIZA", "YEREL")
        link_row, _link = self._meta_row("KAYIT", "SES  /  METİN")
        layout.addLayout(mem_row)
        layout.addLayout(link_row)
        return panel

    def _build_bottom(self):
        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self.cpu_gauge = RadialGauge("CPU", QColor(61, 240, 255))
        self.ram_gauge = RadialGauge("RAM", QColor(61, 255, 176))
        self.disk_gauge = RadialGauge("DİSK", QColor(255, 176, 32))
        for gauge in (self.cpu_gauge, self.ram_gauge, self.disk_gauge):
            bottom.addWidget(gauge)

        bottom.addStretch()

        action = QVBoxLayout()
        action.setSpacing(4)
        self.toggle_button = QPushButton("SES BAĞLANTISINI AÇ")
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.setMinimumSize(250, 48)
        self.toggle_button.clicked.connect(self.toggle_listening)
        serial = QLabel("RIFKI-MK1    ·    VOX-TR    ·    NODE LOCAL")
        serial.setAlignment(Qt.AlignRight)
        serial.setStyleSheet(
            "color: #4E7084; font-family: Consolas; font-size: 10px; letter-spacing: 1px; background: transparent;"
        )
        action.addStretch()
        action.addWidget(self.toggle_button)
        action.addWidget(serial)
        bottom.addLayout(action)
        return bottom

    def _apply_theme(self):
        self.setAutoFillBackground(False)

    def _style_arm_button(self, live: bool):
        if live:
            color = "#FFB020"
            text = "SES BAĞLANTISINI KES"
        else:
            color = NEON_CYAN
            text = "SES BAĞLANTISINI AÇ"
        self.toggle_button.setText(text)
        self.toggle_button.setStyleSheet(
            f"QPushButton {{ background-color: rgba(4, 14, 24, 230); color: {color}; "
            f"border: 1px solid {color}; padding: 10px 18px; "
            f"font-family: Consolas; font-weight: bold; letter-spacing: 1px; }}"
            f"QPushButton:hover {{ background-color: rgba(16, 48, 73, 230); }}"
            f"QPushButton:pressed {{ background-color: rgba(8, 28, 44, 230); }}"
        )

    def _set_directive(self, text: str):
        clean = " ".join((text or "").split())
        if len(clean) > 180:
            clean = clean[:177] + "…"
        self.ai_status_desc.setText(clean or "—")

    def _set_sys_pill(self, state: str):
        label, color = PILL_COPY.get(state, PILL_COPY["OFF"])
        self._dot_color = color
        self.sys_text.setText(label)
        self.sys_dot.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")

    def _blink_dot(self):
        if not self._listening_active:
            self.sys_dot.setStyleSheet(
                f"color: {self._dot_color}; font-size: 11px; background: transparent;"
            )
            return
        self._dot_on = not self._dot_on
        color = self._dot_color if self._dot_on else "#1A3A4A"
        self.sys_dot.setStyleSheet(f"color: {color}; font-size: 11px; background: transparent;")

    def _paint_pipeline(self, state: str):
        accents = {
            "LISTENING": "#3DFFB0",
            "THINKING": "#FFB020",
            "PROCESSING": "#FF8A3D",
            "SPEAKING": "#3DF0FF",
        }
        if state == "IDLE":
            modes = ["armed", "idle", "idle", "idle"]
        elif state in accents:
            index = {"LISTENING": 0, "THINKING": 1, "PROCESSING": 2, "SPEAKING": 3}[state]
            modes = []
            for i in range(4):
                if i < index:
                    modes.append("done")
                elif i == index:
                    modes.append("active")
                else:
                    modes.append("idle")
        else:
            modes = ["idle", "idle", "idle", "idle"]
        for step, mode in zip(self._steps, modes):
            step.set_mode(mode, accents.get(state, "#3DF0FF"))

    def _enter_standby_ui(self):
        self._listening_active = False
        self._style_arm_button(False)
        self.audio_value.setText("KAPALI")
        self._set_directive(f"Bağlantı kapalı. Açıldığında «{self._wake_pretty}» ile uyanırım.")
        self.status_label.setText("BEKLEMEDE")
        self.status_detail.setText("Ses bağlantısı kapalı")
        self.core_widget.set_state("OFF")
        self.waveform.set_state("IDLE")
        self._set_sys_pill("OFF")
        self._paint_pipeline("OFF")
        mobile_bridge.set_listening(False)
        mobile_bridge.publish_state("OFF")

    def toggle_listening(self):
        if not self._listening_active:
            self.voice_worker.start()
            self._listening_active = True
            self._style_arm_button(True)
            self.audio_value.setText("AÇIK")
            self._set_directive(
                f"Dinliyorum — netçe «{self._wake_pretty}» deyin "
                "(mikrofon açık, internet gerekli)."
            )
            self.status_label.setText("UYANDIRMA")
            self.status_detail.setText("Uyandırma kelimesi bekleniyor")
            mobile_bridge.set_listening(True)
            mobile_bridge.publish_state("IDLE")
            if self.tray_icon is not None:
                self.tray_icon.showMessage(
                    "RIFKI dinliyor",
                    f"«{self._wake_pretty}» deyin.",
                    QSystemTrayIcon.Information,
                    4000,
                )
        else:
            self.voice_worker.stop()
            self._enter_standby_ui()

    @pyqtSlot(str)
    def _ui_set_status(self, state: str):
        self.on_status_changed(state, from_bridge=True)

    @pyqtSlot(str)
    def _ui_show_user(self, text: str):
        self.on_user_message(text, from_bridge=True)

    @pyqtSlot(str)
    def _ui_show_assistant(self, text: str):
        self.on_assistant_message(text, from_bridge=True)

    def on_status_changed(self, state: str, from_bridge: bool = False):
        self.core_widget.set_state(state)
        self.waveform.set_state(state)
        self._paint_pipeline(state)
        self._set_sys_pill(state)
        title, detail = STATUS_COPY.get(state, (state, ""))
        self.status_label.setText(title)
        self.status_detail.setText(detail)
        if not from_bridge:
            mobile_bridge.publish_state(state)

    def on_user_message(self, text: str, from_bridge: bool = False):
        safe = html.escape(text)
        self.chat_log.append(
            f"<div style='margin-top:8px'><span style='color:#6D8FA3'>KULLANICI</span><br>"
            f"<span style='color:#E7F7FF'>{safe}</span></div>"
        )
        self._set_directive(text)
        if not from_bridge:
            mobile_bridge.publish_user(text)

    def on_assistant_message(self, text: str, from_bridge: bool = False):
        safe = html.escape(text)
        self.chat_log.append(
            f"<div style='margin-top:8px'><span style='color:#3DFFB0'>RIFKI</span><br>"
            f"<span style='color:#D7FFF0'>{safe}</span></div>"
        )
        self._set_directive(text)
        if not from_bridge:
            mobile_bridge.publish_assistant(text)

    def on_error_message(self, text: str):
        safe = html.escape(text)
        self.chat_log.append(
            f"<div style='margin-top:8px'><span style='color:#FF6B6B'>HATA</span><br>"
            f"<span style='color:#FFB4B4'>{safe}</span></div>"
        )
        self._set_directive(text)
        mobile_bridge.publish_error(text)

    def on_wake_acknowledged(self):
        if self.tray_icon is None:
            return
        self.tray_icon.showMessage(
            "RIFKI",
            "Efendim, dinliyorum.",
            QSystemTrayIcon.Information,
            4000,
        )

    def on_stopped_by_voice(self):
        """VoiceWorker sesli 'dinlemeyi durdur' komutuyla kendi kendini
        durdurduğunda butonu ve durumu senkronize eder."""
        self._enter_standby_ui()

    def on_confirmation_requested(self, prompt: str):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        box.setWindowTitle("ONAY GEREKLİ")
        box.setText(prompt)
        yes = box.addButton("ONAYLA", QMessageBox.YesRole)
        no = box.addButton("İPTAL", QMessageBox.NoRole)
        box.setDefaultButton(no)
        box.exec_()
        answer = "evet" if box.clickedButton() is yes else "hayır"
        self.confirm_bridge.provide_answer(answer)

    def _update_stats(self):
        # interval=None: blocking yok (önceki çağrıdan bu yana ölçüm)
        self.cpu_gauge.set_value(psutil.cpu_percent(interval=None))
        self.ram_gauge.set_value(psutil.virtual_memory().percent)
        self._stats_tick += 1
        if self._stats_tick == 1 or self._stats_tick % self._disk_sample_every == 0:
            try:
                import os as _os
                disk_path = "C:\\" if _os.name == "nt" else "/"
                self.disk_gauge.set_value(psutil.disk_usage(disk_path).percent)
            except Exception:
                pass

    def _update_clock(self):
        now = datetime.datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(f"{now.day} {MONTHS_TR[now.month - 1]} {now.year}")

    def closeEvent(self, event):
        tunnel_manager.stop()
        mobile_bridge.stop()
        self.voice_worker.stop()
        self.voice_worker.wait(2000)
        event.accept()


def run_app():
    import sys
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(APP_QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
