"""
ui/animations.py
-----------------
RIFKI komuta ekranının çizilen parçaları.

- CoreWidget: durum rengiyle değişen, katmanlı reaktör çekirdeği.
- WaveformWidget: dinleme / konuşma enerjisini gösteren ses izi.
- RadialGauge: CPU, RAM ve disk için kokpit kadranı.
- paint_command_deck: pencerenin radar alanı, köşe nişangâhları ve kenar taraması.
"""

import math

from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QRadialGradient, QFont, QPolygonF
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
        self._timer.start(33)

    def set_state(self, state: str):
        if state in STATE_COLORS:
            self._state = state

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
        self._timer.start(33)

    def set_state(self, state: str):
        self._state = state if state in STATE_COLORS else "IDLE"

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
        self._timer.start(33)

    def set_value(self, value: float):
        self._value = max(0.0, min(100.0, value))

    def _animate_step(self):
        diff = self._value - self._display_value
        if abs(diff) > 0.15:
            self._display_value += diff * 0.18
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
