"""
ui/spotlight.py
---------------
Mac Spotlight / Raycast benzeri, klavye kısayoluyla (Ctrl+Space veya Ctrl+Shift+R)
ekranın ortasında açılan hızlı RIFKI komut ve soru çubuğu.
"""

from __future__ import annotations

import ctypes
from typing import Optional

from PyQt5.QtCore import QEvent, QPoint, QSize, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QIcon, QKeySequence, QPainter, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QShortcut,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config.settings import settings
from core.logger import get_logger

log = get_logger("ui.spotlight")


class VoiceWorkerThread(QThread):
    transcription_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            from voice.speech_to_text import listen_and_transcribe
            text = listen_and_transcribe(timeout=4, phrase_time_limit=12)
            self.transcription_ready.emit(text)
        except Exception as e:
            self.error_occurred.emit(str(e))


class CommandWorkerThread(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, command_text: str, parent=None):
        super().__init__(parent)
        self.command_text = command_text

    def run(self):
        try:
            from core.ai import rifki_brain
            reply = rifki_brain.process(self.command_text)
            self.response_ready.emit(reply)
        except Exception as e:
            self.error_occurred.emit(f"Hata: {e}")


class SpotlightWindow(QWidget):
    command_executed = pyqtSignal(str, str)  # (user_text, assistant_reply)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RIFKI Spotlight")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)

        self._voice_thread: Optional[VoiceWorkerThread] = None
        self._cmd_thread: Optional[CommandWorkerThread] = None
        self._is_listening = False

        self._build_ui()
        self._setup_shortcuts()

    def _build_ui(self):
        self.setFixedWidth(680)

        # Main container with border and neon background
        self.container = QWidget(self)
        self.container.setObjectName("spotlightContainer")
        self.container.setStyleSheet("""
            QWidget#spotlightContainer {
                background-color: #070D18;
                border: 1px solid #00E5FF;
                border-radius: 12px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 229, 255, 60))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 14, 16, 14)
        container_layout.setSpacing(10)

        # Header bar
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #00E5FF; font-size: 11px;")
        header_layout.addWidget(self.status_dot)

        self.header_title = QLabel("RIFKI // HIZLI KOMUT")
        self.header_title.setStyleSheet("color: #7FD8FF; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        header_layout.addWidget(self.header_title)

        header_layout.addStretch(1)

        hint_label = QLabel("Esc: Kapat  |  Enter: Gönder")
        hint_label.setStyleSheet("color: #4A677D; font-size: 10px;")
        header_layout.addWidget(hint_label)

        container_layout.addLayout(header_layout)

        # Input Row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        # Mic Button
        self.btn_mic = QPushButton("🎙️")
        self.btn_mic.setFixedSize(36, 36)
        self.btn_mic.setCursor(Qt.PointingHandCursor)
        self.btn_mic.setToolTip("Bas ve Konuş (Mikrofon)")
        self.btn_mic.setStyleSheet("""
            QPushButton {
                background-color: #0D1A2A;
                border: 1px solid #1C3854;
                border-radius: 18px;
                font-size: 14px;
                color: #A5C4D4;
            }
            QPushButton:hover {
                background-color: #122840;
                border-color: #00E5FF;
                color: #FFFFFF;
            }
        """)
        self.btn_mic.clicked.connect(self._toggle_voice_input)
        input_row.addWidget(self.btn_mic)

        # Text Line Edit
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("Rıfkı'ya sor veya komut ver... (örn: 'Spotify aç', 'sesi %40 yap')")
        self.input_edit.setFixedHeight(36)
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background-color: #0B1626;
                border: 1px solid #162E47;
                border-radius: 8px;
                padding: 0 12px;
                color: #FFFFFF;
                font-size: 14px;
                selection-background-color: #00E5FF;
                selection-color: #000000;
            }
            QLineEdit:focus {
                border: 1px solid #00E5FF;
                background-color: #0D1C30;
            }
        """)
        self.input_edit.returnPressed.connect(self._submit_command)
        input_row.addWidget(self.input_edit)

        # Send Button
        self.btn_send = QPushButton("➔")
        self.btn_send.setFixedSize(36, 36)
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.setToolTip("Komutu Çalıştır (Enter)")
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #00E5FF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                color: #03060C;
            }
            QPushButton:hover {
                background-color: #3DFFB0;
            }
        """)
        self.btn_send.clicked.connect(self._submit_command)
        input_row.addWidget(self.btn_send)

        container_layout.addLayout(input_row)

        # Response Card Area (hidden by default)
        self.response_area = QTextEdit()
        self.response_area.setReadOnly(True)
        self.response_area.setFixedHeight(120)
        self.response_area.setStyleSheet("""
            QTextEdit {
                background-color: #0A1424;
                border: 1px solid #183350;
                border-radius: 8px;
                padding: 10px;
                color: #D7FFF0;
                font-size: 13px;
                line-height: 1.4;
            }
        """)
        self.response_area.hide()
        container_layout.addWidget(self.response_area)

    def _setup_shortcuts(self):
        esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        esc_shortcut.activated.connect(self.hide)

    def show_spotlight(self):
        # Ortaya konumlandır
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = (geo.width() - self.width()) // 2
            y = geo.height() // 4  # Ekranın üst-orta üçte birinde Spotlight pozisyonu
            self.move(x, y)

        self.input_edit.clear()
        self.response_area.hide()
        self._set_status("HAZIR", "#00E5FF")
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_edit.setFocus()

    def _set_status(self, text: str, color: str = "#00E5FF"):
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 11px;")
        self.header_title.setText(f"RIFKI // {text.upper()}")
        self.header_title.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")

    def _toggle_voice_input(self):
        if self._is_listening:
            return

        self._is_listening = True
        self.btn_mic.setStyleSheet("""
            QPushButton {
                background-color: #FF4757;
                border: 1px solid #FF6B81;
                border-radius: 18px;
                font-size: 14px;
                color: #FFFFFF;
            }
        """)
        self._set_status("DİNLİYOR (KONUŞUN...)", "#FF4757")

        self._voice_thread = VoiceWorkerThread(self)
        self._voice_thread.transcription_ready.connect(self._on_voice_transcribed)
        self._voice_thread.error_occurred.connect(self._on_voice_error)
        self._voice_thread.start()

    def _on_voice_transcribed(self, text: str):
        self._is_listening = False
        self.btn_mic.setStyleSheet("""
            QPushButton {
                background-color: #0D1A2A;
                border: 1px solid #1C3854;
                border-radius: 18px;
                font-size: 14px;
                color: #A5C4D4;
            }
        """)
        if text.strip():
            self.input_edit.setText(text.strip())
            self._submit_command()
        else:
            self._set_status("SES DUYULMADI", "#FFBD2E")

    def _on_voice_error(self, err: str):
        self._is_listening = False
        self._set_status("MİKROFON HATASI", "#FF4757")

    def _submit_command(self):
        text = self.input_edit.text().strip()
        if not text:
            return

        self._set_status("DÜŞÜNÜLÜYOR...", "#FFBD2E")
        self.input_edit.setEnabled(False)
        self.btn_send.setEnabled(False)
        self.response_area.show()
        self.response_area.setText("Komut işleniyor...")

        self._cmd_thread = CommandWorkerThread(text, self)
        self._cmd_thread.response_ready.connect(lambda reply: self._on_command_finished(text, reply))
        self._cmd_thread.error_occurred.connect(lambda err: self._on_command_finished(text, err))
        self._cmd_thread.start()

    def _on_command_finished(self, text: str, reply: str):
        self.input_edit.setEnabled(True)
        self.btn_send.setEnabled(True)
        self._set_status("TAMAMLANDI", "#3DFFB0")
        self.response_area.setText(reply)
        self.command_executed.emit(text, reply)

        # İsteğe bağlı yerel sesli yanıt
        try:
            from voice.text_to_speech import speak
            speak(reply)
        except Exception:
            pass
