"""
ui/main_window.py
------------------
RIFKI'nın ana masaüstü penceresi. Iron Man / arc-reactor ilhamlı bir HUD
(heads-up display) görünümü: ince arka plan ızgarası, köşe aksanlı paneller,
merkezde animasyonlu "arc reactor" çekirdeği (ui/animations.CoreWidget),
CPU/RAM/Disk için dairesel göstergeler (ui/animations.RadialGauge), sohbet
paneli, saat/tarih ve mikrofon durumu.

Mimari not: Ses döngüsü (wake word bekleme -> dinleme -> AI -> TTS) ayrı bir
QThread (VoiceWorker) içinde çalışır ki UI donmasın. Kritik işlem onayları
(ör. "bilgisayarı kapat") worker thread'den ana thread'e bir Qt sinyali ile
iletilir; kullanıcı QMessageBox'ta cevap verene kadar worker thread bir
threading.Event ile bloklanır.
"""

import datetime
import threading

import psutil
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QRectF, QPoint
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QMessageBox, QFrame, QSystemTrayIcon, QMenu, QAction,
)
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QPen, QPixmap, QIcon

from ui.animations import CoreWidget, RadialGauge
from core.ai import rifki_brain
from core.logger import get_logger
from voice.wake_word import wait_for_wake_word
from voice.speech_to_text import listen_and_transcribe, MicrophoneError, SpeechServiceError
from voice.text_to_speech import speak

log = get_logger("ui.main_window")

NEON_CYAN = "#00E5FF"
BG_DARK = "#050B14"
BG_PANEL = "#0A1626"
GRID_COLOR = QColor(0, 180, 255, 14)
BRACKET_COLOR = QColor(0, 210, 255, 170)
# Paneller artık tam opak değil, yarı saydam: masaüstü arkadan hafifçe görünür
# ("Rainmeter tarzı" masaüstüne yapışık widget hissi için).
PANEL_BG_RGBA = "rgba(6, 16, 28, 165)"


def _build_tray_icon_pixmap() -> QPixmap:
    """Harici bir ikon dosyasına ihtiyaç duymadan, basit bir cyan halka
    ikonu çizip QIcon/QPixmap olarak döndürür (sistem tepsisi için)."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(0, 220, 255))
    pen.setWidth(6)
    painter.setPen(pen)
    painter.setBrush(QColor(0, 60, 80))
    painter.drawEllipse(6, 6, size - 12, size - 12)
    painter.setBrush(QColor(255, 255, 255))
    painter.setPen(Qt.NoPen)
    r = 8
    painter.drawEllipse(size // 2 - r, size // 2 - r, r * 2, r * 2)
    painter.end()
    return pixmap


class HudPanel(QFrame):
    """Köşelerinde sci-fi HUD tarzı ince 'L' aksanları olan, yarı saydam
    (masaüstü arkadan hafifçe görünen) panel çerçevesi."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {PANEL_BG_RGBA}; border-radius: 4px;")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(BRACKET_COLOR)
        pen.setWidthF(1.6)
        painter.setPen(pen)
        w, h = self.width(), self.height()
        L = 14  # köşe aksan uzunluğu
        corners = [
            [(0, L), (0, 0), (L, 0)],
            [(w - L, 0), (w, 0), (w, L)],
            [(0, h - L), (0, h), (L, h)],
            [(w - L, h), (w, h), (w, h - L)],
        ]
        for pts in corners:
            for i in range(len(pts) - 1):
                painter.drawLine(*pts[i], *pts[i + 1])


class ConfirmBridge:
    """Worker thread'in ana thread'e onay sorusu sorup cevabını beklemesini sağlar."""

    def __init__(self):
        self._event = threading.Event()
        self._answer = ""
        self.request_signal = None  # MainWindow tarafından bağlanacak

    def ask(self, prompt: str) -> str:
        self._event.clear()
        if self.request_signal:
            self.request_signal.emit(prompt)
        self._event.wait(timeout=60)
        return self._answer

    def provide_answer(self, answer: str):
        self._answer = answer
        self._event.set()


class VoiceWorker(QThread):
    status_changed = pyqtSignal(str)
    user_message = pyqtSignal(str)
    assistant_message = pyqtSignal(str)
    error_message = pyqtSignal(str)
    confirmation_requested = pyqtSignal(str)

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

            # Wake word bir kez duyulduktan sonra, RIFKI cevap verdikçe
            # birkaç tur boyunca "Asistan" demeden devam edebilmek için
            # bir "sohbet oturumu" döngüsüne giriyoruz. Kullanıcı bir süre
            # sessiz kalırsa (follow-up duyulmazsa) sessizce wake-word
            # bekleme moduna geri dönülür.
            in_conversation = True
            while in_conversation and self._running:
                self.status_changed.emit("LISTENING")
                try:
                    command_text = listen_and_transcribe(timeout=5, phrase_time_limit=10)
                except (MicrophoneError, SpeechServiceError) as e:
                    self.error_message.emit(str(e))
                    break

                if not command_text:
                    # Follow-up penceresinde hiçbir şey duyulmadı;
                    # sessizce wake-word beklemeye geri dön.
                    log.info("Follow-up penceresinde ses algılanmadı, wake-word beklemeye dönülüyor.")
                    break

                self.user_message.emit(command_text)
                self.status_changed.emit("THINKING")

                log.info("core/ai.py -> rifki_brain.process() çağrılıyor...")
                try:
                    response_text = rifki_brain.process(
                        command_text,
                        ask_fn=self.confirm_bridge.ask,
                        status_callback=self.status_changed.emit,
                    )
                except Exception as e:
                    log.error(f"AI işleme hatası: {e}")
                    response_text = "Yapay zekâ servisine şu anda ulaşamıyorum."

                log.info(f"rifki_brain.process() döndü: '{response_text}'")
                self.assistant_message.emit(response_text)
                self.status_changed.emit("SPEAKING")
                log.info("TTS (speak) çağrılıyor...")
                try:
                    speak(response_text)
                    log.info("TTS (speak) tamamlandı.")
                except Exception as e:
                    log.error(f"TTS hatası: {e}")
                # Döngü devam ediyor: RIFKI konuşmayı bitirir bitirmez
                # tekrar LISTENING'e geçip follow-up bekleyecek.


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RIFKI")

        # --- "Masaüstü widget'ı" davranışı ---
        # Çerçevesiz + şeffaf arka plan + her zaman en üstte. Bu, RIFKI'nın
        # normal bir uygulama penceresi gibi değil, ekranda sürekli duran bir
        # HUD widget'ı gibi hissettirmesini sağlar. Not: bu, masaüstü
        # simgelerinin ARKASINA gömülmez (bkz. sohbet notu) — simgelerin
        # ÖNÜNDE, her zaman görünür şekilde durur.
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.resize(1180, 760)
        self._drag_offset = None
        self._build_ui()
        self._apply_theme()
        self._setup_tray_icon()

        self.confirm_bridge = ConfirmBridge()
        self.voice_worker = VoiceWorker(self.confirm_bridge)
        self.voice_worker.status_changed.connect(self.on_status_changed)
        self.voice_worker.user_message.connect(self.on_user_message)
        self.voice_worker.assistant_message.connect(self.on_assistant_message)
        self.voice_worker.error_message.connect(self.on_error_message)
        self.voice_worker.confirmation_requested.connect(self.on_confirmation_requested)

        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._update_stats)
        self._stats_timer.start(2000)
        self._update_stats()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

    # ---------- Sistem tepsisi (tray) ----------

    def _setup_tray_icon(self):
        icon = QIcon(_build_tray_icon_pixmap())
        self.setWindowIcon(icon)

        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("RIFKI")

        menu = QMenu()
        show_action = QAction("Göster", self)
        show_action.triggered.connect(self._show_from_tray)
        hide_action = QAction("Gizle", self)
        hide_action.triggered.connect(self.hide)
        quit_action = QAction("Çıkış", self)
        quit_action.triggered.connect(self._quit_app)

        menu.addAction(show_action)
        menu.addAction(hide_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # tek tık
            if self.isVisible():
                self.hide()
            else:
                self._show_from_tray()

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        self.voice_worker.stop()
        self.voice_worker.wait(2000)
        QApplication.quit()

    # ---------- Pencereyi sürükleme (çerçeve olmadığı için elle yapılır) ----------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_offset = None

    # ---------- Arka plan (ince HUD ızgarası, TAM DOLGU YOK) ----------

    def paintEvent(self, event):
        # NOT: Burada bilerek tam pencereyi dolduran opak bir arka plan
        # ÇİZİLMİYOR — pencere şeffaf olduğu için masaüstü arkadan görünür.
        # Sadece çok hafif bir HUD ızgarası çiziliyor.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(GRID_COLOR)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        step = 42
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)
        super().paintEvent(event)

    # ---------- UI kurulumu ----------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        root.setSpacing(14)

        # Üst bar: başlık + tarih + saat + bağlantı durumu
        top_bar = QHBoxLayout()
        title = QLabel("R . I . F . K . I .")
        title.setFont(QFont("Consolas", 22, QFont.Bold))
        title.setStyleSheet(f"color: {NEON_CYAN}; letter-spacing: 6px;")
        top_bar.addWidget(title)

        self.connection_dot = QLabel("●")
        self.connection_dot.setStyleSheet("color: #00FF9C; font-size: 14px;")
        top_bar.addWidget(self.connection_dot)
        self.connection_label = QLabel("BAĞLI")
        self.connection_label.setStyleSheet("color: #7FEFC7; font-family: Consolas; font-size: 11px;")
        top_bar.addWidget(self.connection_label)

        top_bar.addStretch()

        self.date_label = QLabel("--.--.----")
        self.date_label.setFont(QFont("Consolas", 12))
        self.date_label.setStyleSheet("color: #7FD8FF;")
        top_bar.addWidget(self.date_label)

        self.clock_label = QLabel("--:--:--")
        self.clock_label.setFont(QFont("Consolas", 16, QFont.Bold))
        self.clock_label.setStyleSheet(f"color: {NEON_CYAN}; margin-left: 12px;")
        top_bar.addWidget(self.clock_label)

        # Pencere çerçevesiz olduğu için Windows'un varsayılan
        # simge durumuna küçültme / kapatma düğmeleri yok; elle ekliyoruz.
        minimize_btn = QLabel("—")
        minimize_btn.setStyleSheet(
            f"color: {NEON_CYAN}; font-family: Consolas; font-size: 16px; "
            "padding: 2px 10px; margin-left: 14px;"
        )
        minimize_btn.setCursor(Qt.PointingHandCursor)
        minimize_btn.mousePressEvent = lambda e: self.hide()
        top_bar.addWidget(minimize_btn)

        close_btn = QLabel("✕")
        close_btn.setStyleSheet(
            "color: #FF6B6B; font-family: Consolas; font-size: 14px; "
            "padding: 2px 10px;"
        )
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self._quit_app()
        top_bar.addWidget(close_btn)

        root.addLayout(top_bar)

        # Orta bölge: sol gösterge paneli + merkez çekirdek + sağ durum paneli
        middle = QHBoxLayout()
        middle.setSpacing(14)

        # --- Sol panel: CPU / RAM / Disk göstergeleri ---
        left_panel = HudPanel()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_title = QLabel("SİSTEM")
        left_title.setStyleSheet(f"color: {NEON_CYAN}; font-weight: bold; font-family: Consolas; letter-spacing: 2px;")
        left_layout.addWidget(left_title)

        self.cpu_gauge = RadialGauge("CPU", QColor(0, 220, 255))
        self.ram_gauge = RadialGauge("RAM", QColor(0, 255, 170))
        self.disk_gauge = RadialGauge("DİSK", QColor(255, 170, 0))
        for gauge in (self.cpu_gauge, self.ram_gauge, self.disk_gauge):
            left_layout.addWidget(gauge, alignment=Qt.AlignCenter)
        left_layout.addStretch()
        middle.addWidget(left_panel, stretch=2)

        # --- Orta: arc reactor çekirdek + durum yazısı ---
        center_col = QVBoxLayout()
        self.core_widget = CoreWidget()
        center_col.addWidget(self.core_widget, alignment=Qt.AlignCenter)

        self.status_label = QLabel("HAZIRIM")
        self.status_label.setFont(QFont("Consolas", 14, QFont.Bold))
        self.status_label.setStyleSheet(f"color: {NEON_CYAN}; letter-spacing: 3px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        center_col.addWidget(self.status_label)
        middle.addLayout(center_col, stretch=3)

        # --- Sağ panel: mikrofon / oturum bilgisi ---
        right_panel = HudPanel()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_title = QLabel("DURUM")
        right_title.setStyleSheet(f"color: {NEON_CYAN}; font-weight: bold; font-family: Consolas; letter-spacing: 2px;")
        right_layout.addWidget(right_title)

        self.mic_label = QLabel("MİKROFON: pasif")
        self.wake_label = QLabel(f"Uyandırma: bekleniyor")
        self.model_label = QLabel("Model: Gemini")
        for lbl in (self.mic_label, self.wake_label, self.model_label):
            lbl.setStyleSheet("color: #C7F5FF; font-family: Consolas; font-size: 12px;")
            lbl.setWordWrap(True)
            right_layout.addWidget(lbl)

        right_layout.addStretch()
        middle.addWidget(right_panel, stretch=2)

        root.addLayout(middle, stretch=3)

        # Alt bölge: sohbet geçmişi
        chat_panel = HudPanel()
        chat_layout = QVBoxLayout(chat_panel)
        chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet(
            "background-color: transparent; color: #DFF9FF; "
            "font-family: Consolas; border: none;"
        )
        chat_layout.addWidget(self.chat_log)
        root.addWidget(chat_panel, stretch=2)

        # Kontrol butonu (mikrofon aç/kapat)
        bottom_bar = QHBoxLayout()
        self.toggle_button = QPushButton("DİNLEMEYİ BAŞLAT")
        self.toggle_button.clicked.connect(self.toggle_listening)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.toggle_button)
        root.addLayout(bottom_bar)

        self._listening_active = False

    def _apply_theme(self):
        self.setAutoFillBackground(False)
        self.toggle_button.setStyleSheet(
            f"QPushButton {{ background-color: {BG_PANEL}; color: {NEON_CYAN}; "
            f"border: 1px solid {NEON_CYAN}; border-radius: 4px; padding: 10px 22px; "
            f"font-family: Consolas; font-weight: bold; letter-spacing: 2px; }}"
            f"QPushButton:hover {{ background-color: #103049; }}"
        )

    # ---------- Olaylar ----------

    def toggle_listening(self):
        if not self._listening_active:
            self.voice_worker.start()
            self.toggle_button.setText("DİNLEMEYİ DURDUR")
            self.mic_label.setText("MİKROFON: aktif")
            self.wake_label.setText("Uyandırma: bekleniyor")
        else:
            self.voice_worker.stop()
            self.toggle_button.setText("DİNLEMEYİ BAŞLAT")
            self.mic_label.setText("MİKROFON: pasif")
        self._listening_active = not self._listening_active

    def on_status_changed(self, state: str):
        self.core_widget.set_state(state)
        messages = {
            "IDLE": "HAZIRIM",
            "LISTENING": "DİNLİYORUM...",
            "THINKING": "DÜŞÜNÜYORUM...",
            "PROCESSING": "İŞLEM GERÇEKLEŞTİRİLİYOR...",
            "SPEAKING": "YANIT VERİYORUM...",
        }
        self.status_label.setText(messages.get(state, state))

    def on_user_message(self, text: str):
        self.chat_log.append(f"<span style='color:#7FD8FF'><b>Sen:</b> {text}</span>")

    def on_assistant_message(self, text: str):
        self.chat_log.append(f"<span style='color:#00FFC8'><b>RIFKI:</b> {text}</span>")

    def on_error_message(self, text: str):
        self.chat_log.append(f"<span style='color:#FF6B6B'><b>Hata:</b> {text}</span>")

    def on_confirmation_requested(self, prompt: str):
        reply = QMessageBox.question(
            self, "Onay Gerekli", prompt,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        answer = "evet" if reply == QMessageBox.Yes else "hayır"
        self.confirm_bridge.provide_answer(answer)

    # ---------- Periyodik güncellemeler ----------

    def _update_stats(self):
        self.cpu_gauge.set_value(psutil.cpu_percent())
        self.ram_gauge.set_value(psutil.virtual_memory().percent)
        try:
            import os as _os
            disk_path = "C:\\" if _os.name == "nt" else "/"
            self.disk_gauge.set_value(psutil.disk_usage(disk_path).percent)
        except Exception:
            pass

    def _update_clock(self):
        now = datetime.datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(now.strftime("%d.%m.%Y"))

    def closeEvent(self, event):
        self.voice_worker.stop()
        self.voice_worker.wait(2000)
        event.accept()


def run_app():
    import sys

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # tray'e gizlenince uygulama kapanmasın
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())