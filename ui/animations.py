"""
ui/animations.py
-----------------
RIFKI'nın görsel HUD (heads-up display) bileşenleri:

- CoreWidget: merkezdeki "arc reactor" tarzı animasyonlu çekirdek.
  Durum bazlı (IDLE / LISTENING / THINKING / PROCESSING / SPEAKING) renk
  ve birden fazla katmanlı, farklı hızlarda dönen segmentli halkalarla
  Iron Man / JARVIS ilhamlı, ama doğrudan kopya olmayan bir görünüm.
- RadialGauge: CPU/RAM/Disk gibi tekil bir yüzde değerini dairesel bir
  gösterge (dial) olarak çizen hafif widget.

Performans için ağır efektler yerine basit QPainter çizimleri + 30 FPS
timer kullanılır (gereksiz CPU tüketmeyecek şekilde).
"""

import math

from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QRadialGradient, QFont
from PyQt5.QtWidgets import QWidget

STATE_COLORS = {
    "IDLE": QColor(0, 200, 255),
    "LISTENING": QColor(0, 255, 170),
    "THINKING": QColor(255, 200, 0),
    "PROCESSING": QColor(255, 140, 0),
    "SPEAKING": QColor(0, 255, 255),
}


class CoreWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self._state = "IDLE"
        self._angle = 0.0
        self._pulse = 0.0
        self._audio_level = 0.0  # 0..1, konuşurken dışarıdan güncellenebilir

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30 FPS

    def set_state(self, state: str):
        if state in STATE_COLORS:
            self._state = state

    def set_audio_level(self, level: float):
        self._audio_level = max(0.0, min(1.0, level))

    def _tick(self):
        self._angle = (self._angle + 1.4) % 360
        self._pulse = (math.sin(self._angle * math.pi / 60) + 1) / 2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base_radius = min(w, h) / 2 - 14

        color = STATE_COLORS.get(self._state, STATE_COLORS["IDLE"])

        extra = self._audio_level * 15 if self._state in ("LISTENING", "SPEAKING") else 0
        pulse_radius = base_radius * 0.34 + self._pulse * 6 + extra

        # Dış parlama (glow)
        glow_radius = base_radius + 10
        gradient = QRadialGradient(cx, cy, glow_radius)
        glow_color = QColor(color)
        glow_color.setAlpha(50)
        gradient.setColorAt(0.0, glow_color)
        transparent = QColor(color)
        transparent.setAlpha(0)
        gradient.setColorAt(1.0, transparent)
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - glow_radius, cy - glow_radius, glow_radius * 2, glow_radius * 2))

        # Sabit ince dış çember (blueprint hissi)
        outer_pen = QPen(QColor(color.red(), color.green(), color.blue(), 60))
        outer_pen.setWidthF(1.0)
        painter.setPen(outer_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(cx - base_radius, cy - base_radius, base_radius * 2, base_radius * 2))

        # Katmanlı, farklı hız/uzunlukta dönen segmentli halkalar
        ring_specs = [
            # (radius_factor, width, speed_mult, num_segments, span_deg)
            (1.00, 2.4, 1.0, 3, 70),
            (0.82, 1.8, -1.6, 5, 40),
            (0.64, 3.0, 2.2, 2, 110),
            (0.48, 1.4, -0.7, 8, 20),
        ]
        for radius_factor, pen_width, speed_mult, num_segments, span_deg in ring_specs:
            radius = base_radius * radius_factor
            pen = QPen(color)
            pen.setWidthF(pen_width)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            gap = 360 / num_segments
            for i in range(num_segments):
                start = (self._angle * speed_mult + i * gap) % 360
                painter.drawArc(
                    QRectF(cx - radius, cy - radius, radius * 2, radius * 2).toRect(),
                    int(start * 16), int(span_deg * 16),
                )

        # Merkez "arc reactor" halkası: içi koyu, kenarı parlak bir halka
        # (dolu bir top yerine tam bir reaktör çekirdeği hissi verir)
        ring_outer = pulse_radius
        ring_inner = pulse_radius * 0.62

        core_gradient = QRadialGradient(cx, cy, ring_outer)
        core_gradient.setColorAt(0.0, QColor(6, 14, 20))
        core_gradient.setColorAt(0.55, QColor(6, 14, 20))
        bright = QColor(255, 255, 255)
        core_gradient.setColorAt(0.72, bright)
        core_gradient.setColorAt(0.85, color)
        core_edge = QColor(color)
        core_edge.setAlpha(140)
        core_gradient.setColorAt(1.0, core_edge)
        painter.setBrush(core_gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - ring_outer, cy - ring_outer, ring_outer * 2, ring_outer * 2))

        # İç göbek: küçük, sabit parlak bir nokta (reaktörün merkezi)
        hub_r = ring_inner * 0.32
        hub_gradient = QRadialGradient(cx, cy, hub_r)
        hub_gradient.setColorAt(0.0, QColor(255, 255, 255))
        hub_gradient.setColorAt(1.0, color)
        painter.setBrush(hub_gradient)
        painter.drawEllipse(QRectF(cx - hub_r, cy - hub_r, hub_r * 2, hub_r * 2))

        # İnce iç halka çizgisi (detay)
        inner_ring_pen = QPen(QColor(color.red(), color.green(), color.blue(), 200))
        inner_ring_pen.setWidthF(1.2)
        painter.setPen(inner_ring_pen)
        painter.setBrush(Qt.NoBrush)
        mid_r = ring_inner * 0.68
        painter.drawEllipse(QRectF(cx - mid_r, cy - mid_r, mid_r * 2, mid_r * 2))


class RadialGauge(QWidget):
    """CPU/RAM/Disk gibi tekil bir 0-100 yüzde değerini dairesel bir
    gösterge olarak çizer. Ortada büyük yüzde yazısı, altında küçük etiket."""

    def __init__(self, label: str, color: QColor = None, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 130)
        self._label = label
        self._value = 0.0  # 0-100
        self._display_value = 0.0  # yumuşak geçiş için
        self._color = color or QColor(0, 220, 255)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_step)
        self._timer.start(33)

    def set_value(self, value: float):
        self._value = max(0.0, min(100.0, value))

    def _animate_step(self):
        diff = self._value - self._display_value
        if abs(diff) > 0.1:
            self._display_value += diff * 0.15
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        gauge_h = w  # kare alan, altta etiket için ayrı yer bırakılır
        cx, cy = w / 2, gauge_h / 2
        radius = min(w, gauge_h) / 2 - 8

        start_angle = 90  # 12 yönünden başla (Qt: 0=3 yönü, saat yönü tersi)
        span_full = 360

        # Arka plan track
        track_pen = QPen(QColor(255, 255, 255, 30))
        track_pen.setWidthF(6)
        track_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(track_pen)
        painter.drawArc(
            QRectF(cx - radius, cy - radius, radius * 2, radius * 2).toRect(),
            0, span_full * 16,
        )

        # Değer arc'ı
        value_pen = QPen(self._color)
        value_pen.setWidthF(6)
        value_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(value_pen)
        span = int(-(self._display_value / 100.0) * span_full * 16)
        painter.drawArc(
            QRectF(cx - radius, cy - radius, radius * 2, radius * 2).toRect(),
            start_angle * 16, span,
        )

        # Yüzde metni
        painter.setPen(QColor(220, 250, 255))
        font = QFont("Consolas", int(radius * 0.32))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(cx - radius, cy - radius, radius * 2, radius * 2),
            Qt.AlignCenter, f"{int(self._display_value)}%",
        )

        # Etiket (alt kısım)
        label_font = QFont("Consolas", 9)
        painter.setFont(label_font)
        painter.setPen(QColor(140, 220, 255))
        painter.drawText(
            QRectF(0, gauge_h - 6, w, 24),
            Qt.AlignHCenter | Qt.AlignTop, self._label,
        )