"""
ui/animations.py
-----------------
RIFKI komuta ekranının çizilen parçaları.

- CoreWidget: durum rengiyle değişen, katmanlı reaktör çekirdeği.
- WaveformWidget: dinleme / konuşma enerjisini gösteren ses izi.
- RadialGauge: CPU, RAM ve disk için kokpit kadranı.
- paint_command_deck: pencerenin radar alanı, köşe nişangâhları ve kenar taraması.
- AsciiBackdrop: tüm ekranı kaplayan hareketli ASCII karakter alanı ve ortadaki
  ASCII göz (göz kırpar, etrafa bakar, duruma göre renk/tempo değiştirir).
- AsciiEyeAnchor: düzende gözün yerini tutan görünmez yer tutucu.
"""

import math
import random
import time

import numpy as np
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QRadialGradient, QFont, QFontMetricsF, QPolygonF
from PyQt5.QtWidgets import QWidget


STATE_COLORS = {
    "IDLE": QColor(0, 210, 255),
    "LISTENING": QColor(61, 255, 176),
    "THINKING": QColor(255, 176, 32),
    "PROCESSING": QColor(255, 122, 46),
    "SPEAKING": QColor(120, 236, 255),
}

_SPIN = {
    "IDLE": 0.55,
    "LISTENING": 2.4,
    "THINKING": 1.35,
    "PROCESSING": 1.9,
    "SPEAKING": 1.7,
}


def _polygon(cx, cy, radius, sides, rotation_deg):
    poly = QPolygonF()
    for i in range(sides):
        angle = math.radians(rotation_deg + i * (360.0 / sides) - 90)
        poly.append(QPointF(cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return poly


def paint_brackets(painter, x, y, w, h, length=22, color=None, width=1.7):
    """Dört köşeye HUD 'L' nişangâhı çizer."""
    pen = QPen(color or QColor(0, 229, 255, 190))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.FlatCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    right, bottom = x + w, y + h
    painter.drawLine(x, y, x + length, y)
    painter.drawLine(x, y, x, y + length)
    painter.drawLine(right, y, right - length, y)
    painter.drawLine(right, y, right, y + length)
    painter.drawLine(x, bottom, x + length, bottom)
    painter.drawLine(x, bottom, x, bottom - length)
    painter.drawLine(right, bottom, right - length, bottom)
    painter.drawLine(right, bottom, right, bottom - length)


def paint_command_deck(painter, rect, glass=False):
    """Pencere arkasındaki radar alanı. Çocuk widget'ların altında kalır.

    glass=True iken zemin boyanmaz; masaüstü görünür, yalnızca halkalar kalır.
    """
    painter.setRenderHint(QPainter.Antialiasing)
    w, h = rect.width(), rect.height()
    if glass:
        _paint_glass_radar(painter, w, h)
        return

    painter.fillRect(rect, QColor(2, 6, 12))

    cx, cy = w / 2.0, h * 0.46
    bloom = QRadialGradient(cx, cy, 340)
    bloom.setColorAt(0.0, QColor(0, 120, 160, 55))
    bloom.setColorAt(0.55, QColor(0, 40, 70, 18))
    bloom.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.fillRect(rect, bloom)

    painter.setBrush(Qt.NoBrush)
    ring_pen = QPen(QColor(0, 190, 220, 26))
    ring_pen.setWidthF(1.0)
    painter.setPen(ring_pen)
    for radius in (80, 150, 230, 320, 430):
        painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

    spoke_pen = QPen(QColor(0, 190, 220, 16))
    spoke_pen.setWidthF(1.0)
    painter.setPen(spoke_pen)
    for deg in range(0, 360, 30):
        rad = math.radians(deg - 90)
        painter.drawLine(
            QPointF(cx, cy),
            QPointF(cx + math.cos(rad) * 460, cy + math.sin(rad) * 460),
        )

    vignette = QRadialGradient(cx, cy, max(w, h) * 0.72)
    vignette.setColorAt(0.35, QColor(0, 0, 0, 0))
    vignette.setColorAt(1.0, QColor(0, 0, 0, 190))
    painter.fillRect(rect, vignette)

    scan = QPen(QColor(0, 0, 0, 22))
    painter.setPen(scan)
    for y in range(0, h, 4):
        painter.drawLine(0, y, w, y)

    paint_brackets(painter, 10, 10, w - 20, h - 20, length=34, color=QColor(0, 229, 255, 170), width=1.8)

    tick_pen = QPen(QColor(0, 229, 255, 80))
    tick_pen.setWidthF(1.0)
    painter.setPen(tick_pen)
    for x in range(36, w - 36, 16):
        height = 9 if x % 80 < 16 else 4
        painter.drawLine(x, 10, x, 10 + height)
        painter.drawLine(x, h - 10, x, h - 10 - height)


def _paint_glass_radar(painter, w, h):
    """Masaüstünün üstüne binen şeffaf HUD: dolgu yok, sadece ince radar."""
    cx, cy = w / 2.0, h * 0.48
    painter.setBrush(Qt.NoBrush)
    ring_pen = QPen(QColor(0, 210, 255, 42))
    ring_pen.setWidthF(1.0)
    painter.setPen(ring_pen)
    for radius in (70, 130, 200, 280):
        painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

    spoke_pen = QPen(QColor(0, 210, 255, 22))
    spoke_pen.setWidthF(1.0)
    painter.setPen(spoke_pen)
    for deg in range(0, 360, 45):
        rad = math.radians(deg - 90)
        painter.drawLine(
            QPointF(cx, cy),
            QPointF(cx + math.cos(rad) * 300, cy + math.sin(rad) * 300),
        )

    paint_brackets(
        painter, 10, 10, w - 20, h - 20,
        length=28, color=QColor(0, 229, 255, 140), width=1.6,
    )


def _prepare_glass(widget):
    widget.setAttribute(Qt.WA_TranslucentBackground, True)
    widget.setAttribute(Qt.WA_NoSystemBackground, True)
    widget.setAutoFillBackground(False)
    widget.setStyleSheet("background: transparent;")


_ACTIVE_FPS_MS = 33
_IDLE_FPS_MS = 250


class CoreWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        _prepare_glass(self)
        self.setFixedSize(360, 360)
        self._state = "IDLE"
        self._angle = 0.0
        self._pulse = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(_IDLE_FPS_MS)

    def set_state(self, state: str):
        if state not in STATE_COLORS:
            return
        prev = self._state
        self._state = state
        if state == "IDLE":
            self._timer.setInterval(_IDLE_FPS_MS)
        else:
            self._timer.setInterval(_ACTIVE_FPS_MS)
        if prev != state and not self._timer.isActive():
            self._timer.start()

    def _tick(self):
        self._angle = (self._angle + _SPIN.get(self._state, 0.8)) % 360
        self._pulse = (math.sin(self._angle * math.pi / 48) + 1) / 2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base = min(w, h) / 2 - 18
        color = STATE_COLORS.get(self._state, STATE_COLORS["IDLE"])

        glow_alpha = {
            "IDLE": 36,
            "LISTENING": 80,
            "THINKING": 64,
            "PROCESSING": 70,
            "SPEAKING": 92,
        }.get(self._state, 40)
        glow_r = base + 16 + self._pulse * 6
        glow = QRadialGradient(cx, cy, glow_r)
        glow_color = QColor(color)
        glow_color.setAlpha(glow_alpha)
        glow.setColorAt(0.0, glow_color)
        fade = QColor(color)
        fade.setAlpha(0)
        glow.setColorAt(1.0, fade)
        painter.setPen(Qt.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))

        # Dış açı taraması
        tick_color = QColor(color)
        tick_color.setAlpha(150)
        major = QColor(color)
        major.setAlpha(220)
        for i in range(72):
            angle = math.radians(i * 5 - 90)
            outer = base
            inner = base - (11 if i % 6 == 0 else 5)
            pen = QPen(major if i % 6 == 0 else tick_color)
            pen.setWidthF(1.6 if i % 6 == 0 else 1.0)
            painter.setPen(pen)
            painter.drawLine(
                QPointF(cx + math.cos(angle) * inner, cy + math.sin(angle) * inner),
                QPointF(cx + math.cos(angle) * outer, cy + math.sin(angle) * outer),
            )

        dash = QPen(color)
        dash.setWidthF(1.15)
        dash.setDashPattern([1.4, 5.5])
        dash.setDashOffset(-self._angle / 8)
        painter.setPen(dash)
        painter.setBrush(Qt.NoBrush)
        r = base * 0.90
        painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        ring_specs = [
            (0.78, 2.6, 1.0, 3, 62),
            (0.64, 1.7, -1.55, 4, 36),
            (0.50, 3.1, 2.05, 2, 100),
        ]
        for factor, pen_width, speed, count, span in ring_specs:
            radius = base * factor
            pen = QPen(color)
            pen.setWidthF(pen_width)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            gap = 360 / count
            rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            for i in range(count):
                start = (self._angle * speed + i * gap) % 360
                painter.drawArc(rect, int(start * 16), int(span * 16))

        hex_pen = QPen(QColor(color.red(), color.green(), color.blue(), 170))
        hex_pen.setWidthF(1.3)
        painter.setPen(hex_pen)
        painter.drawPolygon(_polygon(cx, cy, base * 0.40, 6, self._angle * 0.35))
        inner_hex = QPen(QColor(color.red(), color.green(), color.blue(), 90))
        inner_hex.setWidthF(1.0)
        painter.setPen(inner_hex)
        painter.drawPolygon(_polygon(cx, cy, base * 0.31, 6, -self._angle * 0.5))

        # Artı nişangah, merkezin içinden geçmeden
        cross = QPen(QColor(color.red(), color.green(), color.blue(), 130))
        cross.setWidthF(1.0)
        painter.setPen(cross)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            painter.drawLine(
                QPointF(cx + dx * base * 0.16, cy + dy * base * 0.16),
                QPointF(cx + dx * base * 0.27, cy + dy * base * 0.27),
            )

        pulse_r = base * 0.16 + self._pulse * 5
        core = QRadialGradient(cx, cy, pulse_r)
        core.setColorAt(0.0, QColor(8, 16, 24))
        core.setColorAt(0.45, QColor(8, 16, 24))
        core.setColorAt(0.62, QColor(255, 255, 255))
        core.setColorAt(0.78, color)
        edge = QColor(color)
        edge.setAlpha(150)
        core.setColorAt(1.0, edge)
        painter.setPen(Qt.NoPen)
        painter.setBrush(core)
        painter.drawEllipse(QRectF(cx - pulse_r, cy - pulse_r, pulse_r * 2, pulse_r * 2))

        hub_r = pulse_r * 0.28
        hub = QRadialGradient(cx, cy, hub_r)
        hub.setColorAt(0.0, QColor(255, 255, 255))
        hub.setColorAt(1.0, color)
        painter.setBrush(hub)
        painter.drawEllipse(QRectF(cx - hub_r, cy - hub_r, hub_r * 2, hub_r * 2))

        for i, (speed, orbit, radius_px) in enumerate((
            (1.0, 0.90, 3.4),
            (-0.72, 0.64, 2.4),
            (1.65, 0.50, 2.2),
        )):
            angle = math.radians(self._angle * speed + i * 120)
            orbit_r = base * orbit
            x = cx + math.cos(angle) * orbit_r
            y = cy + math.sin(angle) * orbit_r
            painter.setBrush(color)
            painter.drawEllipse(QRectF(x - radius_px, y - radius_px, radius_px * 2, radius_px * 2))


class WaveformWidget(QWidget):
    """Duruma göre yükselen ses izi. Gerçek genlik yok; ritim durumu anlatır."""

    def __init__(self, parent=None):
        super().__init__(parent)
        _prepare_glass(self)
        self.setMinimumHeight(54)
        self.setMaximumHeight(64)
        self._phase = 0.0
        self._state = "IDLE"
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(_IDLE_FPS_MS)

    def set_state(self, state: str):
        self._state = state if state in STATE_COLORS else "IDLE"
        if self._state == "IDLE":
            self._timer.setInterval(_IDLE_FPS_MS)
        else:
            self._timer.setInterval(_ACTIVE_FPS_MS)
        if not self._timer.isActive():
            self._timer.start()

    def _tick(self):
        speed = {
            "IDLE": 0.05,
            "LISTENING": 0.34,
            "THINKING": 0.14,
            "PROCESSING": 0.2,
            "SPEAKING": 0.28,
        }.get(self._state, 0.08)
        self._phase += speed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        count = 48
        gap = 3.0
        bar_w = max(2.0, (w - gap * (count - 1)) / count)
        mid = h / 2
        color = STATE_COLORS.get(self._state, STATE_COLORS["IDLE"])
        energy = {
            "IDLE": 0.16,
            "LISTENING": 1.0,
            "THINKING": 0.42,
            "PROCESSING": 0.6,
            "SPEAKING": 0.86,
        }.get(self._state, 0.2)

        base_pen = QPen(QColor(color.red(), color.green(), color.blue(), 40))
        base_pen.setWidthF(1.0)
        painter.setPen(base_pen)
        painter.drawLine(0, int(mid), w, int(mid))

        painter.setPen(Qt.NoPen)
        for i in range(count):
            primary = math.sin(self._phase * 2.1 + i * 0.42)
            secondary = math.sin(self._phase * 3.4 + i * 0.17)
            amp = (0.18 + 0.82 * abs(primary * 0.72 + secondary * 0.28)) * energy
            bar_h = max(2.0, amp * (h - 8))
            shade = QColor(color)
            shade.setAlpha(70 + int(170 * amp))
            painter.setBrush(shade)
            x = i * (bar_w + gap)
            painter.drawRoundedRect(QRectF(x, mid - bar_h / 2, bar_w, bar_h), 1.2, 1.2)


class RadialGauge(QWidget):
    """0-100 değerini altı açık kokpit kadranı olarak çizer."""

    def __init__(self, label: str, color: QColor = None, parent=None):
        super().__init__(parent)
        _prepare_glass(self)
        self.setFixedSize(112, 132)
        self._label = label
        self._value = 0.0
        self._display_value = 0.0
        self._color = color or QColor(0, 220, 255)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_step)
        # Sadece değer değişirken çalışır (boşta CPU yok)

    def set_value(self, value: float):
        self._value = max(0.0, min(100.0, value))
        if abs(self._value - self._display_value) > 0.15 and not self._timer.isActive():
            self._timer.start(_ACTIVE_FPS_MS)

    def _animate_step(self):
        diff = self._value - self._display_value
        if abs(diff) > 0.15:
            self._display_value += diff * 0.18
            self.update()
        else:
            self._display_value = self._value
            self._timer.stop()
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx = w / 2
        cy = (h - 18) / 2
        radius = min(w, h - 22) / 2 - 6

        # 8 yönünden 4 yönüne, 12'den geçen 240 derecelik yay.
        start = 210 * 16
        full = -240 * 16

        track = QPen(QColor(180, 230, 255, 28))
        track.setWidthF(7)
        track.setCapStyle(Qt.RoundCap)
        painter.setPen(track)
        painter.setBrush(Qt.NoBrush)
        arc = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.drawArc(arc, start, full)

        glow = QPen(self._color)
        glow.setWidthF(11)
        glow.setCapStyle(Qt.RoundCap)
        glow_color = QColor(self._color)
        glow_color.setAlpha(50)
        glow.setColor(glow_color)
        painter.setPen(glow)
        span = int(full * (self._display_value / 100.0))
        painter.drawArc(arc, start, span)

        value_pen = QPen(self._color)
        value_pen.setWidthF(6)
        value_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(value_pen)
        painter.drawArc(arc, start, span)

        painter.setPen(QColor(232, 252, 255))
        font = QFont("Consolas", max(10, int(radius * 0.34)))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(cx - radius, cy - radius * 0.55, radius * 2, radius), Qt.AlignCenter, f"{int(self._display_value)}")

        label_font = QFont("Consolas", 8)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(QColor(140, 210, 230))
        painter.drawText(QRectF(0, h - 18, w, 16), Qt.AlignHCenter | Qt.AlignVCenter, self._label)


# ---------------------------------------------------------------------------
# ASCII arka plan + göz (Siber / Neon Cyan Teması & Konuşma Morf Animasyonu)
# ---------------------------------------------------------------------------

WORDS_SCLERA = (
    r"XCQ0ZmwwqqddbbkklktkklddpqmZ0Q0U*|"
    r"\CQ0Zxqpcblbkhhaaae0CQVxbhhlcsbdpqxZ0Q0U*//"
    r"tCUQ0mwqpdbkhhaoc0t*fqahhkhbdpqmCQCIE*"
    r"rcYJLC0Zmwqpdbkhhaoo0*//\\ahhkbdpqmZ0LU*"
    r"xvX3LC0QZmwqpddbkhhaoo0t\\GahhkbddpqmZ00L"
    r"fncXUCL00Zmwqpddbkhhaoo0*//\2ahhkbddpqmZ00LCUKcx"
    r"fmuxuvLQ0Zmwqpddbkhhaoo0*||\YhhhkbddpqmZ0QLCUxmf"
    r"fmuvUYQ00Zmwqpddbkhhaoo0t//OahhkbddpqmZ00QCJYzent"
    r"fmuvYQ00Zmwqpddbkhhaoo0*|\tpahhkbddpqmZ00YX"
    r"tffftfnXQmpddbkhhaoo*df///\deahkp2cxn"
    r"ttjn0C2pkhaoo*bn\\//xJJfxvxrjt"
)
_CHARS_SCLERA = np.array(list(WORDS_SCLERA), dtype="<U1")

WORDS_IRIS = (
    "mwcVzpNoxiou*00"
    "nvvdolle*0a"
    "fOdfd  0x"
    "uqdbw1  c000Xxsni"
    "nmfQjktHtezh0Tn"
    "ahhkbdpqmZ00L"
)
_CHARS_IRIS = np.array(list(WORDS_IRIS), dtype="<U1")

BG_STREAMS = (
    r"/t/t/t/ttttttjrjjffffjfttffffffjtttt///ttttt"
    r"\\\\\\t/t/tttttttjrjjjfftt/tft///ff/t///tttt"
    r"(((((((())))))))[[[[[[[]]]]]]]]{{{{{{{}}}}}}}"
    r"trxxrrxxjjrrjrjjffttffjxxrfjjffffjffttft/t/t"
)
_CHARS_BG = np.array(list(BG_STREAMS), dtype="<U1")

# Mevcut HUD arayüzü ile birebir uyumlu Neon Cyan / Sci-Fi renk paleti
ASCII_STATE_TINT = {
    "OFF": QColor(50, 85, 110),          # Sönük çelik mavisi
    "IDLE": QColor(61, 240, 255),        # Neon Cyan (#3DF0FF) - HUD ile birebir
    "LISTENING": QColor(61, 255, 176),   # Sinyal Zümrütü (#3DFFB0)
    "THINKING": QColor(255, 176, 32),    # Altın Kehribar (#FFB020)
    "PROCESSING": QColor(255, 122, 46),  # Canlı Turuncu (#FF7A2E)
    "SPEAKING": QColor(120, 245, 255),   # Parlak Elektrik Cyan (#78ECFF)
}

_ASCII_STATE_PARAMS = {
    "OFF": (0.35, 0.40, 0.35, 0.3),
    "IDLE": (0.70, 0.95, 0.36, 1.0),
    "LISTENING": (1.30, 1.12, 0.48, 0.6),
    "THINKING": (1.80, 0.85, 0.28, 2.0),
    "PROCESSING": (2.20, 0.90, 0.32, 1.5),
    "SPEAKING": (1.35, 1.08, 0.45, 1.2),
}


class AsciiBackdrop:
    """Tüm ekranı kaplayan hareketli ASCII karakter alanı, siber göz ve konuşma morfları."""

    def __init__(self, pixel_size: int = 11):
        self.font = QFont("Consolas")
        self.font.setStyleHint(QFont.Monospace)
        self.font.setPixelSize(pixel_size)
        self.font.setKerning(False)
        metrics = QFontMetricsF(self.font)
        self.char_w = max(4.0, metrics.horizontalAdvance("M"))
        self.char_h = max(6.0, metrics.height())
        self.ascent = metrics.ascent()

        self._state = "OFF"
        self._grid_key = None
        self._X = None
        self._Y = None
        self._cols = 0
        self._rows = 0

        now = time.perf_counter()
        self._last = now
        self._phase = 0.0
        tempo, opening, pupil, wander = _ASCII_STATE_PARAMS["OFF"]
        self._tempo = tempo
        self._open = opening
        self._pupil = pupil
        self._wander = wander

        # Konuşma sırasında geometrik şekillere geçiş ağırlığı (0.0 -> 1.0)
        self._morph_weight = 0.0

        self._next_blink = now + random.uniform(2.5, 5.0)
        self._blink_start = None
        self._gaze = np.zeros(2, dtype=np.float32)
        self._gaze_target = np.zeros(2, dtype=np.float32)
        self._next_saccade = now + 1.0

        # HUD renkleriyle tam uyumlu palet
        self._c_bg = QColor(26, 78, 112, 160)       # Siber cyan matris akışı
        self._c_sclera = QColor(220, 248, 255, 255) # Buz beyazı / parlak elektrik cyan
        self._c_crease = QColor(61, 240, 255, 190)  # Neon Cyan
        self._c_glint = QColor(255, 255, 255, 255)  # Saf Beyaz
        self._c_pupil = QColor(2, 8, 16, 250)       # Derin Uzay Laciverti
        self._c_lash = QColor(3, 10, 20, 250)
        self._c_morph = QColor(120, 245, 255, 255)  # Konuşma geometrisi parlak cyan
        self._c_core = QColor(255, 255, 255, 255)   # Odak parlaması beyaz

    def set_state(self, state: str):
        state = state if state in _ASCII_STATE_PARAMS else "OFF"
        if state != self._state:
            self._state = state
            self._next_saccade = time.perf_counter()

    @property
    def state(self) -> str:
        return self._state

    def _ensure_grid(self, W: int, H: int):
        key = (W, H)
        if key == self._grid_key:
            return
        self._cols = int(W / self.char_w) + 1
        self._rows = int(H / self.char_h) + 1
        xs = (np.arange(self._cols, dtype=np.float32) + 0.5) * self.char_w
        ys = (np.arange(self._rows, dtype=np.float32) + 0.5) * self.char_h
        self._X, self._Y = np.meshgrid(xs, ys)
        self._grid_key = key

    def _advance(self, now: float):
        dt = min(0.2, max(0.0, now - self._last))
        self._last = now
        tempo, opening, pupil, wander = _ASCII_STATE_PARAMS[self._state]
        k = min(1.0, dt * 3.5)
        self._tempo += (tempo - self._tempo) * k
        self._open += (opening - self._open) * k
        self._pupil += (pupil - self._pupil) * k
        self._wander += (wander - self._wander) * k
        self._phase += dt * self._tempo

        # Konuşurken geometrik şekillere yumuşak geçiş
        if self._state == "SPEAKING":
            self._morph_weight = min(1.0, self._morph_weight + dt * 4.5)
        else:
            self._morph_weight = max(0.0, self._morph_weight - dt * 3.0)

        # Göz hareketleri (saccades)
        if now >= self._next_saccade:
            spread = min(1.0, 0.45 * self._wander)
            self._gaze_target[:] = (
                random.uniform(-1, 1) * spread,
                random.uniform(-1, 1) * spread * 0.55,
            )
            self._next_saccade = now + random.uniform(0.7, 3.0) / max(0.3, self._wander)
        self._gaze += (self._gaze_target - self._gaze) * min(1.0, dt * 8.5)

        # Kırpma (blink) - konuşurken kırpma seyrelir ve konuşma atımı öne çıkar
        blink = 1.0
        if self._state != "SPEAKING" and self._state != "OFF":
            if self._blink_start is None and now >= self._next_blink:
                self._blink_start = now
            if self._blink_start is not None:
                p = (now - self._blink_start) / 0.24
                if p >= 1.0:
                    self._blink_start = None
                    self._next_blink = now + random.uniform(2.6, 6.0)
                    if random.random() < 0.16:
                        self._next_blink = now + 0.32
                else:
                    blink = abs(1.0 - 2.0 * p) ** 1.3
        return max(0.01, blink * self._open)

    def paint(self, painter: QPainter, W: int, H: int, eye_center: QPointF, scale: float = 1.0):
        if W <= 0 or H <= 0:
            return
        self._ensure_grid(W, H)
        blink = self._advance(time.perf_counter())

        rows, cols = self._rows, self._cols
        X, Y = self._X, self._Y

        cx, cy = eye_center.x(), eye_center.y()
        dx = X - cx
        dy = Y - cy
        dist = np.sqrt(dx * dx + dy * dy)
        angle = np.arctan2(dy, dx)

        # Göz geometrisi
        A_left = 390.0 * scale
        A_right = 490.0 * scale
        A = np.where(dx < 0, A_left, A_right)

        # Konuşurken göz ritmik olarak açılır ve ses dalgasıyla nabız atar
        speak_pulse = (0.16 * math.sin(self._phase * 8.5)) if self._morph_weight > 0.05 else 0.0
        B_top = 155.0 * scale * (blink + speak_pulse * self._morph_weight)
        B_bot = 125.0 * scale * (blink + speak_pulse * self._morph_weight)

        u = dx / A
        inside_x = np.abs(u) < 1.0

        y_top = -B_top * np.power(np.clip(1.0 - u * u, 0.0, 1.0), 0.70)
        y_bot = B_bot * np.power(np.clip(1.0 - u * u, 0.0, 1.0), 0.85)
        taper = np.clip((u - 0.35) / 0.65, 0.0, 1.0)
        y_top = y_top * (1.0 - taper * 0.3)
        y_bot = y_bot * (1.0 - taper * 0.5)

        inside_eye = inside_x & (dy >= y_top) & (dy <= y_bot)

        # Bounding satırları
        eye_rows_mask = inside_eye.any(axis=1)
        r_min = np.argmax(eye_rows_mask) if eye_rows_mask.any() else 0
        r_max = (rows - np.argmax(eye_rows_mask[::-1])) if eye_rows_mask.any() else 0

        # Kirpik ve kıvrım
        d_top = np.abs(dy - y_top)
        d_bot = np.abs(dy - y_bot)
        is_lash = inside_x & ((d_top < 5.0) | (d_bot < 4.5))
        crease_y = y_top - 24.0 * scale
        is_crease = inside_x & (np.abs(dy - crease_y) < 5.0) & (dy < y_top)

        # İris ve göz bebeği konumu
        iris_cx = cx + self._gaze[0] * 125.0 * scale
        iris_cy = cy + self._gaze[1] * 42.0 * scale
        idx = X - iris_cx
        idy = Y - iris_cy
        iris_r = np.sqrt(idx * idx + idy * idy)

        pulse_iris = (1.0 + 0.10 * math.sin(self._phase * 9.0)) if self._morph_weight > 0.05 else 1.0
        IRIS_R = 100.0 * scale * pulse_iris
        pupil_factor = self._pupil
        if self._morph_weight > 0.05:
            pupil_factor += 0.20 * math.sin(self._phase * 11.0)
        PUPIL_R = 36.0 * scale * pupil_factor

        inside_iris = inside_eye & (iris_r <= IRIS_R)
        inside_pupil = inside_iris & (iris_r <= PUPIL_R)

        # Işık parıltısı
        glint_x = idx + 28.0 * scale
        glint_y = idy + 26.0 * scale
        is_glint = inside_eye & ((glint_x * glint_x + glint_y * glint_y) < (11.0 * scale) ** 2)

        inside_sclera = inside_eye & (~inside_iris) & (~is_lash)

        # --- KONUŞMA GEOMETRİK ŞEKİLLERİ (ŞEKİLLERE GİRME) ---
        is_morph_shape = np.zeros_like(inside_eye, dtype=bool)
        is_morph_core = np.zeros_like(inside_eye, dtype=bool)

        if self._morph_weight > 0.02:
            # 1. Ses dalgası halkaları (Göz bebeğinden dışa yayılan sonar halkaları)
            wave_dist = (dist - self._phase * 150.0) % (80.0 * scale)
            sonic_rings = (wave_dist < (14.0 * scale)) & (dist < 340.0 * scale)

            # 2. Dönen Sibernetik Altıgen / Diyafram Bıçakları
            rot = self._phase * 1.6
            theta_hex = (angle - rot) % (math.pi / 3.0) - (math.pi / 6.0)
            hex_dist = dist * np.cos(theta_hex)
            hex_aperture = (
                (np.abs(hex_dist - 145.0 * scale) < (14.0 * scale)) |
                (np.abs(hex_dist - 80.0 * scale) < (10.0 * scale))
            ) & (dist < 320.0 * scale)

            # 3. Radyal Ses Frekansı Ekolayzır Işınları
            spike_amp = (
                np.abs(np.sin(angle * 6.0 + self._phase * 4.0)) * 75.0 * scale +
                np.abs(np.cos(angle * 12.0 - self._phase * 6.0)) * 30.0 * scale
            )
            freq_spikes = (dist < (85.0 * scale + spike_amp)) & (dist > 40.0 * scale)

            # 4. Harmonik Frekans Kafesi (Lissajous Dalgaları)
            harm_wave = np.abs(np.sin(dx * 0.04 + self._phase * 5.0) * np.cos(dy * 0.04 - self._phase * 4.0))
            harm_grid = (harm_wave > 0.65) & (dist < 280.0 * scale)

            # Şekiller arasında periyodik geçiş (Ses tonu modülasyonu)
            cycle = (self._phase * 0.55) % 3.0
            if cycle < 1.0:
                active_shape = sonic_rings | freq_spikes
            elif cycle < 2.0:
                active_shape = hex_aperture | harm_grid
            else:
                active_shape = sonic_rings | hex_aperture | freq_spikes

            is_morph_shape = active_shape & inside_eye
            is_morph_core = (dist < PUPIL_R)

        # Karakter matrisleri
        bg_idx = ((X * 0.15 + Y * 0.35 + self._phase * 40.0).astype(np.int32)) % len(_CHARS_BG)
        char_matrix = _CHARS_BG[bg_idx]

        sclera_idx = ((X * 0.23 + Y * 0.51).astype(np.int32)) % len(_CHARS_SCLERA)
        char_matrix = np.where(inside_sclera, _CHARS_SCLERA[sclera_idx], char_matrix)

        iris_idx = ((X * 0.37 + Y * 0.63).astype(np.int32)) % len(_CHARS_IRIS)
        char_matrix = np.where(inside_iris, _CHARS_IRIS[iris_idx], char_matrix)
        char_matrix = np.where(inside_pupil, "#", char_matrix)
        char_matrix = np.where(is_glint, "*", char_matrix)
        char_matrix = np.where(is_lash, "=", char_matrix)

        # Konuşurken şekilleri çizen özel semboller
        if self._morph_weight > 0.02:
            morph_chars = np.array(list("0O*#%X+@<>{}[]"), dtype="<U1")
            m_idx = ((dist * 0.2 + self._phase * 22.0).astype(np.int32)) % len(morph_chars)
            char_matrix = np.where(is_morph_shape, morph_chars[m_idx], char_matrix)
            char_matrix = np.where(is_morph_core, "*", char_matrix)

        # Gruplar: 0=bg, 1=sclera, 2=iris, 3=glint, 4=pupil, 5=lash, 6=crease, 7=morph_shape, 8=morph_core
        group_matrix = np.zeros((rows, cols), dtype=np.int8)
        group_matrix[inside_sclera] = 1
        group_matrix[inside_iris] = 2
        group_matrix[inside_pupil] = 4
        group_matrix[is_glint] = 3
        group_matrix[is_lash] = 5
        group_matrix[is_crease] = 6
        if self._morph_weight > 0.02:
            group_matrix[is_morph_shape] = 7
            group_matrix[is_morph_core] = 8

        # Çizim
        painter.save()
        painter.setFont(self.font)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        c_iris = ASCII_STATE_TINT.get(self._state, ASCII_STATE_TINT["IDLE"])

        # 1. Arka plan
        painter.setPen(self._c_bg)
        for r in range(rows):
            y_pos = r * self.char_h + self.ascent
            if r < r_min or r >= r_max:
                painter.drawText(QPointF(0, y_pos), "".join(char_matrix[r]))
            else:
                bg_mask = (group_matrix[r] == 0)
                if bg_mask.any():
                    line = "".join(np.where(bg_mask, char_matrix[r], " "))
                    painter.drawText(QPointF(0, y_pos), line)

        # 2. Göz öğeleri ve konuşma şekilleri
        for r in range(r_min, r_max):
            y_pos = r * self.char_h + self.ascent
            grp = group_matrix[r]
            ch = char_matrix[r]

            # Göz akı (sclera)
            m1 = (grp == 1)
            if m1.any():
                painter.setPen(self._c_sclera)
                painter.drawText(QPointF(0, y_pos), "".join(np.where(m1, ch, " ")))

            # İris
            m2 = (grp == 2)
            if m2.any():
                painter.setPen(c_iris)
                painter.drawText(QPointF(0, y_pos), "".join(np.where(m2, ch, " ")))

            # Konuşma şekilleri (morph shape)
            m7 = (grp == 7)
            if m7.any():
                painter.setPen(self._c_morph)
                painter.drawText(QPointF(0, y_pos), "".join(np.where(m7, ch, " ")))

            # Konuşma odak çekirdeği (morph core)
            m8 = (grp == 8)
            if m8.any():
                painter.setPen(self._c_core)
                painter.drawText(QPointF(0, y_pos), "".join(np.where(m8, ch, " ")))

            # Göz bebeği (pupil)
            m4 = (grp == 4)
            if m4.any():
                painter.setPen(self._c_pupil)
                painter.drawText(QPointF(0, y_pos), "".join(np.where(m4, ch, " ")))

            # Işık parıltısı (glint)
            m3 = (grp == 3)
            if m3.any():
                painter.setPen(self._c_glint)
                painter.drawText(QPointF(0, y_pos), "".join(np.where(m3, ch, " ")))

            # Kıvrım (crease)
            m6 = (grp == 6)
            if m6.any():
                painter.setPen(self._c_crease)
                painter.drawText(QPointF(0, y_pos), "".join(np.where(m6, ch, " ")))

            # Kirpik (lash)
            m5 = (grp == 5)
            if m5.any():
                painter.setPen(self._c_lash)
                painter.drawText(QPointF(0, y_pos), "".join(np.where(m5, ch, " ")))

        painter.restore()


class AsciiEyeAnchor(QWidget):
    """Gözün düzendeki yerini tutar; çizimi ana pencere yapar."""

    def __init__(self, backdrop: AsciiBackdrop, parent=None):
        super().__init__(parent)
        _prepare_glass(self)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedSize(520, 320)
        self._backdrop = backdrop

    def set_state(self, state: str):
        self._backdrop.set_state(state)

