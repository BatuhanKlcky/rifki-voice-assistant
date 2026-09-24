"""
ui/main_window.py
------------------
RIFKI'nın fütüristik HUD masaüstü penceresi (Şeffaf olmayan, tok sci-fi tema).
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
BG_PANEL = "#071322"
GRID_COLOR = QColor(0, 180, 255, 12)
BRACKET_COLOR = QColor(0, 210, 255, 180)
PANEL_BG_RGBA = "rgba(7, 19, 34, 245)"


def _build_tray_icon_pixmap() -> QPixmap:
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
    """Köşelerinde sci-fi HUD tarzı ince 'L' aksanları olan panel çerçevesi."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {BG_PANEL}; border-radius: 6px; border: 1px solid rgba(0, 229, 255, 50);")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(BRACKET_COLOR)
        pen.setWidthF(1.6)
        painter.setPen(pen)
        w, h = self.width(), self.height()
        L = 12
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

            in_conversation = True
            while in_conversation and self._running:
                self.status_changed.emit("LISTENING")
                try:
                    command_text = listen_and_transcribe(timeout=5, phrase_time_limit=10)
                except (MicrophoneError, SpeechServiceError) as e:
                    self.error_message.emit(str(e))
                    break

                if not command_text:
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


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RIFKI - HUD Interface")

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        # Transparanslık kaldırıldı, tok arka plan aktif edildi.

        self.resize(1320, 800)
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
        self.tray_icon.show()

    def _show_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def _quit_app(self):
        self.voice_worker.stop()
        self.voice_worker.wait(2000)
        QApplication.quit()

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

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(GRID_COLOR)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        step = 45
        for x in range(0, self.width(), step):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), step):
            painter.drawLine(0, y, self.width(), y)
        super().paintEvent(event)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        # --- ÜST BAR ---
        top_bar = QHBoxLayout()
        title = QLabel("SES TANIMA")
        title.setFont(QFont("Consolas", 14, QFont.Bold))
        title.setStyleSheet(f"color: {NEON_CYAN}; letter-spacing: 2px;")
        top_bar.addWidget(title)

        self.accuracy_label = QLabel("%98")
        self.accuracy_label.setStyleSheet("color: #7FEFC7; font-family: Consolas; font-weight: bold; font-size: 13px; margin-left: 10px;")
        top_bar.addWidget(self.accuracy_label)

        top_bar.addStretch()

        sys_status_frame = HudPanel()
        sys_layout = QHBoxLayout(sys_status_frame)
        sys_layout.setContentsMargins(12, 4, 12, 4)
        sys_dot = QLabel("●")
        sys_dot.setStyleSheet("color: #00FF9C; font-size: 11px;")
        sys_text = QLabel("SİSTEM DURUMU: AKTİF")
        sys_text.setStyleSheet("color: #C7F5FF; font-family: Consolas; font-size: 11px; font-weight: bold;")
        sys_layout.addWidget(sys_dot)
        sys_layout.addWidget(sys_text)
        top_bar.addWidget(sys_status_frame)

        top_bar.addStretch()

        self.date_label = QLabel("18 Eylül 2026")
        self.date_label.setFont(QFont("Consolas", 11))
        self.date_label.setStyleSheet("color: #7FD8FF;")
        top_bar.addWidget(self.date_label)

        self.clock_label = QLabel("16:45")
        self.clock_label.setFont(QFont("Consolas", 16, QFont.Bold))
        self.clock_label.setStyleSheet(f"color: {NEON_CYAN}; margin-left: 10px;")
        top_bar.addWidget(self.clock_label)

        minimize_btn = QLabel("—")
        minimize_btn.setStyleSheet(f"color: {NEON_CYAN}; font-family: Consolas; font-size: 14px; padding: 2px 8px; margin-left: 10px;")
        minimize_btn.setCursor(Qt.PointingHandCursor)
        minimize_btn.mousePressEvent = lambda e: self.hide()
        top_bar.addWidget(minimize_btn)

        close_btn = QLabel("✕")
        close_btn.setStyleSheet("color: #FF6B6B; font-family: Consolas; font-size: 13px; padding: 2px 8px;")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.mousePressEvent = lambda e: self._quit_app()
        top_bar.addWidget(close_btn)

        root.addLayout(top_bar)

        # --- ORTA BÖLGE ---
        middle = QHBoxLayout()
        middle.setSpacing(12)

        # 1. SOL KOLON
        left_panel = HudPanel()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        
        l_title = QLabel("DİNLEME & ANALİZ")
        l_title.setStyleSheet(f"color: {NEON_CYAN}; font-weight: bold; font-family: Consolas; font-size: 12px;")
        left_layout.addWidget(l_title)

        self.step1_lbl = QLabel("🎙️ Dinleme Aktif")
        self.step2_lbl = QLabel("⚙️ Analiz Bekleniyor")
        self.step3_lbl = QLabel("🧠 Yanıt Oluşturuluyor")
        self.step4_lbl = QLabel("🔊 Sesli Yanıt")
        for lbl in (self.step1_lbl, self.step2_lbl, self.step3_lbl, self.step4_lbl):
            lbl.setStyleSheet("color: #A0E0FF; font-family: Consolas; font-size: 11px; margin-top: 4px;")
            left_layout.addWidget(lbl)

        left_layout.addSpacing(15)
        ai_box_title = QLabel("YAPAY ZEKA ASİSTANI")
        ai_box_title.setStyleSheet(f"color: {NEON_CYAN}; font-weight: bold; font-family: Consolas; font-size: 12px;")
        left_layout.addWidget(ai_box_title)

        self.ai_status_desc = QLabel("Merhaba! Size nasıl yardımcı olabilirim?")
        self.ai_status_desc.setWordWrap(True)
        self.ai_status_desc.setStyleSheet("color: #DFF9FF; font-family: Consolas; font-size: 11px; background: rgba(0,0,0,120); padding: 8px; border-radius: 4px;")
        left_layout.addWidget(self.ai_status_desc)
        
        left_layout.addStretch()
        middle.addWidget(left_panel, stretch=3)

        # 2. ORTA KOLON (Çekirdek)
        center_col = QVBoxLayout()
        self.core_widget = CoreWidget()
        center_col.addWidget(self.core_widget, alignment=Qt.AlignCenter)

        self.status_label = QLabel("HAZIRIM")
        self.status_label.setFont(QFont("Consolas", 13, QFont.Bold))
        self.status_label.setStyleSheet(f"color: {NEON_CYAN}; letter-spacing: 2px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        center_col.addWidget(self.status_label)
        middle.addLayout(center_col, stretch=4)

        # 3. SAĞ KOLON
        right_panel = HudPanel()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)

        r_title = QLabel("SON KONUŞMA")
        r_title.setStyleSheet(f"color: {NEON_CYAN}; font-weight: bold; font-family: Consolas; font-size: 12px;")
        right_layout.addWidget(r_title)

        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet("background-color: rgba(0,0,0,100); color: #DFF9FF; font-family: Consolas; font-size: 11px; border: none; border-radius: 4px;")
        right_layout.addWidget(self.chat_log, stretch=2)

        shortcut_title = QLabel("KISA YOL TUŞLARI")
        shortcut_title.setStyleSheet(f"color: {NEON_CYAN}; font-weight: bold; font-family: Consolas; font-size: 12px; margin-top: 10px;")
        right_layout.addWidget(shortcut_title)

        shortcuts = [
            "🔍 Bilgi ara        Ctrl + 1",
            "📅 Takvim          Ctrl + 2",
            "⚙️ Sistem ayarları  Ctrl + 3",
            "🎛️ Uygulamalar     Ctrl + 4"
        ]
        for sc in shortcuts:
            sc_lbl = QLabel(sc)
            sc_lbl.setStyleSheet("color: #90D0FF; font-family: Consolas; font-size: 10px;")
            right_layout.addWidget(sc_lbl)

        middle.addWidget(right_panel, stretch=3)

        root.addLayout(middle, stretch=4)

        # --- ALT BAR ---
        bottom_bar = QHBoxLayout()
        
        self.cpu_label = QLabel("CPU: %12")
        self.ram_label = QLabel("RAM: %28")
        self.disk_label = QLabel("DİSK: %35")
        for lbl in (self.cpu_label, self.ram_label, self.disk_label):
            lbl.setStyleSheet("color: #7FEFC7; font-family: Consolas; font-size: 11px; font-weight: bold; margin-right: 15px;")
            bottom_bar.addWidget(lbl)

        bottom_bar.addStretch()

        self.toggle_button = QPushButton("DİNLEMEYİ BAŞLAT")
        self.toggle_button.clicked.connect(self.toggle_listening)
        bottom_bar.addWidget(self.toggle_button)

        root.addLayout(bottom_bar)
        self._listening_active = False

    def _apply_theme(self):
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(5, 11, 20))  # Tok koyu lacivert sci-fi arkaplan
        self.setPalette(palette)

        self.toggle_button.setStyleSheet(
            f"QPushButton {{ background-color: {BG_PANEL}; color: {NEON_CYAN}; "
            f"border: 1px solid {NEON_CYAN}; border-radius: 4px; padding: 8px 18px; "
            f"font-family: Consolas; font-weight: bold; letter-spacing: 1px; }}"
            f"QPushButton:hover {{ background-color: #103049; }}"
        )

    def toggle_listening(self):
        if not self._listening_active:
            self.voice_worker.start()
            self.toggle_button.setText("DİNLEMEYİ DURDUR")
            self.ai_status_desc.setText("Dinleniyor... Rıfkı deyin.")
        else:
            self.voice_worker.stop()
            self.toggle_button.setText("DİNLEMEYİ BAŞLAT")
            self.ai_status_desc.setText("Mikrofon pasif.")
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
        self.ai_status_desc.setText(f"Durum: {messages.get(state, state)}")

    def on_user_message(self, text: str):
        self.chat_log.append(f"<span style='color:#7FD8FF'><b>Kullanıcı:</b> {text}</span>")

    def on_assistant_message(self, text: str):
        self.chat_log.append(f"<span style='color:#00FFC8'><b>Rıfkı:</b> {text}</span>")

    def on_error_message(self, text: str):
        self.chat_log.append(f"<span style='color:#FF6B6B'><b>Hata:</b> {text}</span>")

    def on_confirmation_requested(self, prompt: str):
        reply = QMessageBox.question(
            self, "Onay Gerekli", prompt,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        answer = "evet" if reply == QMessageBox.Yes else "hayır"
        self.confirm_bridge.provide_answer(answer)

    def _update_stats(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.cpu_label.setText(f"CPU: %{int(cpu)}")
        self.ram_label.setText(f"RAM: %{int(ram)}")
        try:
            import os as _os
            disk_path = "C:\\" if _os.name == "nt" else "/"
            disk = psutil.disk_usage(disk_path).percent
            self.disk_label.setText(f"DİSK: %{int(disk)}")
        except Exception:
            pass

    def _update_clock(self):
        now = datetime.datetime.now()
        self.clock_label.setText(now.strftime("%H:%M"))
        self.date_label.setText(now.strftime("%d Eylül %Y"))

    def closeEvent(self, event):
        self.voice_worker.stop()
        self.voice_worker.wait(2000)
        event.accept()


def run_app():
    import sys
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
