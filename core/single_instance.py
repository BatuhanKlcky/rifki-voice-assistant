"""Tek RIFKI kopyası. İkincisi pencere açmadan çıkar, kullanıcıya haber verir."""

import ctypes
from ctypes import wintypes

_MUTEX_NAME = "Local\\RIFKI.SingleInstance"
_handle = None


class _FLASHWINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("hwnd", wintypes.HWND),
        ("dwFlags", wintypes.DWORD),
        ("uCount", wintypes.UINT),
        ("dwTimeout", wintypes.DWORD),
    ]


def acquire_single_instance() -> bool:
    """İlk kopya True döner. Mutex tutamacı süreç bitene kadar açık kalır."""
    global _handle
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if not handle:
        return True
    _handle = handle
    return kernel32.GetLastError() != 183


def notify_already_running() -> None:
    """Görev çubuğundaki RIFKI'yi yakıp neden pencere açılmadığını söyler."""
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "RIFKI")
    if hwnd:
        info = _FLASHWINFO()
        info.cbSize = ctypes.sizeof(info)
        info.hwnd = hwnd
        info.dwFlags = 0x00000003 | 0x0000000C  # FLASHW_ALL | FLASHW_TIMERNOFG
        info.uCount = 6
        info.dwTimeout = 0
        user32.FlashWindowEx(ctypes.byref(info))
    user32.MessageBoxW(
        None,
        "RIFKI zaten açık.\n\n"
        "Arayüz masaüstünde, diğer pencerelerin arkasında duruyor. "
        "Görmek için masaüstünü göster (Win+D).\n\n"
        "Kapatmak için görev çubuğundaki RIFKI simgesine sağ tık → Çıkış.",
        "RIFKI",
        0x00000040 | 0x00040000,  # MB_ICONINFORMATION | MB_TOPMOST
    )
