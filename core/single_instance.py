"""Tek RIFKI kopyası. İkincisi çalıştığında var olan RIFKI penceresini öne getirir."""

import ctypes
from ctypes import wintypes
import socket
import threading
from typing import Callable, Optional

_MUTEX_NAME = "Local\\RIFKI.SingleInstance"
_IPC_PORT = 49277
_handle = None
_server_socket: Optional[socket.socket] = None
_show_callback: Optional[Callable[[], None]] = None


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


def notify_already_running() -> bool:
    """Zaten çalışan RIFKI'ye 'pencereyi öne getir' sinyali gönderir.

    Sinyal başarıyla iletilirse True döner; iletişim kurulamazsa False.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(1.5)
            client.connect(("127.0.0.1", _IPC_PORT))
            client.sendall(b"SHOW\n")
            return True
    except Exception:
        pass

    # Yedek: Win32 pencere arayıp öne çıkarmayı dene
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "RIFKI")
    if hwnd:
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
        return True
    return False


def start_single_instance_listener(on_show_requested: Callable[[], None]) -> None:
    """İlk kopya bu soket dinleyicisini başlatır; ikinci tıklamada pencere öne gelir."""
    global _server_socket, _show_callback
    _show_callback = on_show_requested

    def _listen():
        global _server_socket
        try:
            _server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            _server_socket.bind(("127.0.0.1", _IPC_PORT))
            _server_socket.listen(5)
            while True:
                conn, _ = _server_socket.accept()
                with conn:
                    data = conn.recv(64)
                    if data and b"SHOW" in data and _show_callback:
                        _show_callback()
        except Exception:
            pass

    t = threading.Thread(target=_listen, daemon=True, name="SingleInstanceIPC")
    t.start()
