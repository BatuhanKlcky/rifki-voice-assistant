"""
ui/hotkey_manager.py
--------------------
Windows genelinde (global) kısayol tuşlarını yakalayan yerel yönetici.
Win32 RegisterHotKey ve PyQt5 QAbstractNativeEventFilter kullanır.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Callable, Optional

from PyQt5.QtCore import QAbstractNativeEventFilter, QObject, pyqtSignal
from PyQt5.QtWidgets import QApplication

from core.logger import get_logger

log = get_logger("ui.hotkey")

user32 = ctypes.windll.user32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
VK_SPACE = 0x20
VK_R = 0x52
WM_HOTKEY = 0x0312

HOTKEY_ID_SPOTLIGHT_CTRL_SPACE = 101
HOTKEY_ID_SPOTLIGHT_CTRL_SHIFT_R = 102


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class _WindowsNativeEventFilter(QAbstractNativeEventFilter):
    def __init__(self, callback: Callable[[int], None]):
        super().__init__()
        self._callback = callback

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            try:
                msg = _MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    self._callback(int(msg.wParam))
                    return True, 0
            except Exception:
                pass
        return False, 0


class GlobalHotkeyManager(QObject):
    spotlight_triggered = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter: Optional[_WindowsNativeEventFilter] = None
        self._registered_ids: list[int] = []

    def start(self, hwnd: int) -> bool:
        """Kısayolları kaydeder ve olay dinleyicisini başlatır."""
        self._hwnd = hwnd

        # 1. Ctrl + Space
        ok1 = user32.RegisterHotKey(
            self._hwnd,
            HOTKEY_ID_SPOTLIGHT_CTRL_SPACE,
            MOD_CONTROL | MOD_NOREPEAT,
            VK_SPACE,
        )
        if ok1:
            self._registered_ids.append(HOTKEY_ID_SPOTLIGHT_CTRL_SPACE)
            log.info("Global kısayol kaydedildi: Ctrl + Space")
        else:
            log.warning("Ctrl + Space kısayolu başka bir program tarafından kullanılıyor.")

        # 2. Ctrl + Shift + R (Yedek)
        ok2 = user32.RegisterHotKey(
            self._hwnd,
            HOTKEY_ID_SPOTLIGHT_CTRL_SHIFT_R,
            MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT,
            VK_R,
        )
        if ok2:
            self._registered_ids.append(HOTKEY_ID_SPOTLIGHT_CTRL_SHIFT_R)
            log.info("Global kısayol kaydedildi: Ctrl + Shift + R")

        if not self._registered_ids:
            log.warning("Hiçbir global kısayol kaydedilemedi.")
            return False

        # Native Event Filter yükle
        self._filter = _WindowsNativeEventFilter(self._on_native_hotkey)
        QApplication.instance().installNativeEventFilter(self._filter)
        return True

    def _on_native_hotkey(self, hotkey_id: int):
        if hotkey_id in (HOTKEY_ID_SPOTLIGHT_CTRL_SPACE, HOTKEY_ID_SPOTLIGHT_CTRL_SHIFT_R):
            log.info(f"Spotlight kısayolu tetiklendi (ID: {hotkey_id})")
            self.spotlight_triggered.emit()

    def stop(self):
        """Kayıtlı kısayolları serbest bırakır."""
        if hasattr(self, "_hwnd"):
            for hid in self._registered_ids:
                try:
                    user32.UnregisterHotKey(self._hwnd, hid)
                except Exception:
                    pass
            self._registered_ids.clear()

        if self._filter:
            try:
                QApplication.instance().removeNativeEventFilter(self._filter)
            except Exception:
                pass
            self._filter = None
