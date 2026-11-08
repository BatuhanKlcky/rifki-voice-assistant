"""
tools/system.py
----------------
İşletim sistemi kontrol araçları (kapanma, yeniden başlatma, sistem durumu, ses, tarih, ekran görüntüsü, fare/touchpad kontrolü, RAM temizliği ve Oyun/Performans Modu).
"""

import ctypes
import datetime
import gc
import os
import threading
import platform
import subprocess
import time
from pathlib import Path
from typing import Callable, Optional
from core.logger import get_logger

log = get_logger("tools.system")

_GAME_MODE_ACTIVE: bool = False
_GAME_MODE_CALLBACK: Optional[Callable[[bool], None]] = None

# Win32 Mouse Event Flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800


def register_game_mode_callback(cb: Optional[Callable[[bool], None]]) -> None:
    """Masaüstü HUD penceresinin Oyun Modu değişimlerini dinlemesi için callback kaydeder."""
    global _GAME_MODE_CALLBACK
    _GAME_MODE_CALLBACK = cb


def is_game_mode_active() -> bool:
    return _GAME_MODE_ACTIVE


def get_system_status(*args, **kwargs) -> str:
    """Sistem kaynaklarının anlık durumunu özetler."""
    import psutil
    # Blocking interval=0.5 kaldırıldı; non-blocking ölçüm + tek ısıtma
    psutil.cpu_percent(interval=None)
    cpu = psutil.cpu_percent(interval=0.05)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/").percent
    gm = "AÇIK (Yüksek Performans)" if _GAME_MODE_ACTIVE else "Kapalı"
    return f"Sistem Durumu -> CPU: %{cpu}, RAM: %{ram}, Disk: %{disk}, Oyun Modu: {gm}"


def get_datetime(*args, **kwargs) -> str:
    """Anlık tarih ve saat bilgisini döndürür."""
    now = datetime.datetime.now()
    return now.strftime("%d Kasım %Y, %H:%M:%S")


def _ensure_input_desktop() -> bool:
    """Windows'ta geçerli iş parçacığını interaktif masaüstüne bağlar."""
    if os.name == "nt":
        try:
            u32 = ctypes.windll.user32
            hdesk = u32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                u32.SetThreadDesktop(hdesk)
                return True
        except Exception:
            pass
    return False


def _get_cursor_position():
    """Windows'ta geçerli fare imlecinin ekran koordinatlarını döndürür."""
    if os.name == "nt":
        try:
            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            u32 = ctypes.windll.user32
            if u32.GetCursorPos(ctypes.byref(pt)):
                return int(pt.x), int(pt.y)
            if _ensure_input_desktop() and u32.GetCursorPos(ctypes.byref(pt)):
                return int(pt.x), int(pt.y)
        except Exception:
            pass
    try:
        import pyautogui
        pos = pyautogui.position()
        if pos and (pos[0] != 0 or pos[1] != 0):
            return int(pos[0]), int(pos[1])
    except Exception:
        pass
    return None


def _draw_mouse_cursor(image, cx: int, cy: int):
    """Ekran görüntüsünün üzerine belirgin, yüksek kontrastlı fare imleci çizer."""
    try:
        from PIL import ImageDraw
        # Standart Windows ok imleci poligonu (cx, cy = uç noktası)
        points = [
            (cx, cy),
            (cx, cy + 20),
            (cx + 5, cy + 16),
            (cx + 9, cy + 25),
            (cx + 13, cy + 23),
            (cx + 9, cy + 14),
            (cx + 15, cy + 14),
        ]
        draw = ImageDraw.Draw(image)
        # 1. Dış siyah kenarlık (her arka planda net görünmesi için)
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                if ox != 0 or oy != 0:
                    draw.polygon([(x + ox, y + oy) for x, y in points], fill="black")
        # 2. İç siber neon dolgu (parlak cyan / beyaz)
        draw.polygon(points, fill=(61, 240, 255))
        # 3. Uç noktası beyaz vurgu
        draw.point((cx, cy), fill="white")
    except Exception as e:
        log.warning(f"İmleç çizme uyarısı: {e}")


def _grab_screenshot_image(include_cursor: bool = True, all_screens: bool = True):
    """Ekranı PIL Image olarak alır ve Windows'ta fare imlecini görüntünün üzerine çizer."""
    hdesk = None
    cursor_pos = None
    if os.name == "nt":
        try:
            user32 = ctypes.windll.user32
            hdesk = user32.OpenInputDesktop(0, False, 0x01FF)
            if hdesk:
                user32.SetThreadDesktop(hdesk)
            if include_cursor:
                cursor_pos = _get_cursor_position()
        except Exception:
            pass

    errors: list[str] = []
    image = None
    try:
        from PIL import ImageGrab
        image = ImageGrab.grab(all_screens=all_screens)
    except Exception as e:
        errors.append(f"ImageGrab: {e}")

    if image is None:
        try:
            import pyautogui
            image = pyautogui.screenshot()
        except Exception as e:
            errors.append(f"pyautogui: {e}")

    if hdesk:
        try:
            ctypes.windll.user32.CloseDesktop(hdesk)
        except Exception:
            pass

    if image is None:
        raise RuntimeError("; ".join(errors) or "ekran görüntüsü alınamadı")

    # Fare imlecini görüntünün üzerine işle
    if include_cursor and cursor_pos is not None:
        cx, cy = cursor_pos
        w, h = image.size
        if 0 <= cx < w and 0 <= cy < h:
            _draw_mouse_cursor(image, cx, cy)

    return image


def capture_screenshot_png() -> bytes:
    """Ekran görüntüsünü PNG baytları olarak döndürür (masaüstü kayıt)."""
    import io

    image = _grab_screenshot_image()
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    data = buf.getvalue()
    if not data:
        raise RuntimeError("ekran görüntüsü alınamadı")
    return data


if os.name == "nt":
    from ctypes import wintypes

    class _BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]


class FastGDIGrabber:
    """Windows DWM / GDI donanımsal doğrudan bellek kopyalama ve StretchBlt motoru (15-20ms, 50+ FPS)."""

    def __init__(self):
        self._lock = threading.Lock()
        self._w = 0
        self._h = 0
        self._hMemDC = None
        self._hDIB = None
        self._raw_buf = None
        self._p_bits = ctypes.c_void_p()

    def _cleanup(self):
        if os.name != "nt":
            return
        gdi32 = ctypes.windll.gdi32
        if self._hDIB:
            gdi32.DeleteObject(self._hDIB)
            self._hDIB = None
        if self._hMemDC:
            gdi32.DeleteDC(self._hMemDC)
            self._hMemDC = None
        self._raw_buf = None
        self._w = 0
        self._h = 0

    def grab_jpeg(self, max_width: int = 640, quality: int = 45, include_cursor: bool = True) -> bytes | None:
        if os.name != "nt":
            return None
        with self._lock:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            hScreenDC = None
            try:
                hScreenDC = user32.GetDC(0)
                if not hScreenDC:
                    return None
                src_w = user32.GetSystemMetrics(0)
                src_h = user32.GetSystemMetrics(1)
                if src_w <= 0 or src_h <= 0:
                    return None

                target_w = min(max_width, src_w)
                target_h = max(1, int(src_h * (target_w / float(src_w))))
                target_w = (target_w // 4) * 4

                if self._w != target_w or self._h != target_h or not self._hDIB:
                    self._cleanup()
                    bmi = _BITMAPINFOHEADER()
                    bmi.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
                    bmi.biWidth = target_w
                    bmi.biHeight = -target_h
                    bmi.biPlanes = 1
                    bmi.biBitCount = 32
                    bmi.biCompression = 0
                    self._hMemDC = gdi32.CreateCompatibleDC(hScreenDC)
                    self._hDIB = gdi32.CreateDIBSection(
                        self._hMemDC, ctypes.byref(bmi), 0, ctypes.byref(self._p_bits), None, 0
                    )
                    if not self._hDIB or not self._p_bits.value:
                        self._cleanup()
                        return None
                    gdi32.SelectObject(self._hMemDC, self._hDIB)
                    gdi32.SetStretchBltMode(self._hMemDC, 3)
                    self._w = target_w
                    self._h = target_h
                    self._raw_buf = (ctypes.c_char * (target_w * target_h * 4)).from_address(self._p_bits.value)

                success = gdi32.StretchBlt(
                    self._hMemDC, 0, 0, target_w, target_h, hScreenDC, 0, 0, src_w, src_h, 0x00CC0020 | 0x40000000
                )
                if not success:
                    return None

                from PIL import Image as _PILImage

                img = _PILImage.frombuffer("RGBA", (target_w, target_h), self._raw_buf, "raw", "BGRA", 0, 1)

                if include_cursor:
                    cpos = _get_cursor_position()
                    if cpos is not None:
                        cx = int(cpos[0] * target_w / float(src_w))
                        cy = int(cpos[1] * target_h / float(src_h))
                        _draw_mouse_cursor(img, cx, cy)

                import io

                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=max(30, min(95, int(quality))), optimize=False)
                return buf.getvalue()
            except Exception as e:
                log.debug(f"Fast GDI hatası: {e}")
                return None
            finally:
                if hScreenDC:
                    user32.ReleaseDC(0, hScreenDC)


_fast_gdi_grabber = FastGDIGrabber()


def capture_screenshot_for_mobile(
    max_width: int = 1280,
    quality: int = 72,
    fast: bool = False,
    all_screens: bool = True,
) -> bytes:
    """Mobil için ölçeklenmiş JPEG (daha küçük / ultra hızlı / minimum gecikmeli)."""
    import io

    # Donanımsal ultra-hızlı GDI motoru (15-20ms)
    if fast and os.name == "nt" and not all_screens:
        try:
            fast_data = _fast_gdi_grabber.grab_jpeg(max_width=max_width, quality=quality, include_cursor=True)
            if fast_data and len(fast_data) > 100:
                return fast_data
        except Exception:
            pass

    image = _grab_screenshot_image(include_cursor=True, all_screens=all_screens)
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    w, h = image.size
    if w > max_width and w > 0:
        new_h = max(1, int(h * (max_width / float(w))))
        try:
            from PIL import Image as _PILImage

            resample = (
                getattr(_PILImage, "Resampling", _PILImage).BILINEAR
                if fast
                else getattr(_PILImage, "Resampling", _PILImage).LANCZOS
            )
        except Exception:
            resample = 2 if fast else 1  # 2: BILINEAR, 1: LANCZOS
        image = image.resize((max_width, new_h), resample)
    buf = io.BytesIO()
    image.save(
        buf,
        format="JPEG",
        quality=max(35, min(95, int(quality))),
        optimize=not fast,
    )
    data = buf.getvalue()
    if not data or len(data) < 100:
        raise RuntimeError("ekran görüntüsü alınamadı")
    return data


def take_screenshot(*args, **kwargs) -> str:
    """Ekran görüntüsü alır ve masaüstüne kaydeder."""
    try:
        desktop = Path(os.path.expanduser("~")) / "Desktop"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = desktop / f"rifki_screenshot_{timestamp}.png"

        png = capture_screenshot_png()
        filepath.write_bytes(png)
        log.info(f"Ekran görüntüsü kaydedildi: {filepath}")
        return "Ekran görüntüsü başarıyla masaüstüne kaydedildi."
    except Exception as e:
        log.error(f"Ekran görüntüsü alma hatası: {e}")
        return "Ekran görüntüsü alınamadı (pyautogui kütüphanesi gerekebilir)."


def _endpoint_volume():
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL

    devices = AudioUtilities.GetSpeakers()
    endpoint = getattr(devices, "EndpointVolume", None)
    if endpoint is not None:
        return endpoint
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(IAudioEndpointVolume)


def get_volume_info() -> dict:
    """Ses yüzdesi ve mute durumu."""
    try:
        vol = _endpoint_volume()
        level = int(round(vol.GetMasterVolumeLevelScalar() * 100))
        muted = bool(vol.GetMute())
        return {"level": level, "muted": muted}
    except Exception as e:
        log.error(f"Ses okuma hatası: {e}")
        return {"level": None, "muted": None, "error": str(e)}


def set_volume(level: int) -> str:
    """Sistem ses seviyesini belirtilen yüzdeye (0-100) ayarlar."""
    try:
        volume = _endpoint_volume()
        scalar = max(0.0, min(100.0, float(level))) / 100.0
        volume.SetMasterVolumeLevelScalar(scalar, None)
        return f"Ses seviyesi %{int(round(scalar * 100))} olarak ayarlandı."
    except Exception as e:
        log.error(f"Ses ayarlama hatası: {e}")
        return "Ses seviyesi değiştirilemedi."


def adjust_volume(delta: int) -> str:
    """Ses seviyesini ±delta yüzde değiştirir."""
    try:
        volume = _endpoint_volume()
        current = volume.GetMasterVolumeLevelScalar()
        scalar = max(0.0, min(1.0, current + (float(delta) / 100.0)))
        volume.SetMasterVolumeLevelScalar(scalar, None)
        if volume.GetMute() and scalar > 0:
            volume.SetMute(0, None)
        return f"Ses seviyesi %{int(round(scalar * 100))}."
    except Exception as e:
        log.error(f"Ses ayarlama hatası: {e}")
        return "Ses seviyesi değiştirilemedi."


def mute_volume() -> str:
    """Sistem sesini tamamen kapatır (Mute)."""
    try:
        volume = _endpoint_volume()
        volume.SetMute(1, None)
        return "Sistem sesi kapatıldı."
    except Exception as e:
        log.error(f"Sesi kapatma hatası: {e}")
        return "Ses kapatılamadı."


def unmute_volume() -> str:
    """Sistem sesini açar (Unmute)."""
    try:
        volume = _endpoint_volume()
        volume.SetMute(0, None)
        return "Sistem sesi açıldı."
    except Exception as e:
        log.error(f"Sesi açma hatası: {e}")
        return "Ses açılamadı."


def toggle_mute() -> str:
    """Mute aç/kapa."""
    try:
        volume = _endpoint_volume()
        muted = bool(volume.GetMute())
        volume.SetMute(0 if muted else 1, None)
        return "Sistem sesi açıldı." if muted else "Sistem sesi kapatıldı."
    except Exception as e:
        log.error(f"Mute değiştirme hatası: {e}")
        return "Ses durumu değiştirilemedi."


def shutdown_pc() -> str:
    """Bilgisayarı kapatır."""
    try:
        if platform.system() == "Windows":
            os.system("shutdown /s /t 5")
        else:
            os.system("shutdown -h now")
        log.warning("Bilgisayar kapatma komutu tetiklendi.")
        return "Bilgisayar 5 saniye içinde kapatılıyor."
    except Exception as e:
        log.error(f"Kapatma hatası: {e}")
        return "Bilgisayar kapatılamadı."


def shutdown_computer() -> str:
    """Bilgisayarı kapatır (Router uyumluluk fonksiyonu)."""
    return shutdown_pc()


def restart_pc() -> str:
    """Bilgisayarı yeniden başlatır."""
    try:
        if platform.system() == "Windows":
            os.system("shutdown /r /t 5")
        else:
            os.system("reboot")
        log.warning("Bilgisayar yeniden başlatma komutu tetiklendi.")
        return "Bilgisayar 5 saniye içinde yeniden başlatılıyor."
    except Exception as e:
        log.error(f"Yeniden başlatma hatası: {e}")
        return "Bilgisayar yeniden başlatılamadı."


def restart_computer() -> str:
    """Bilgisayarı yeniden başlatır (Router uyumluluk fonksiyonu)."""
    return restart_pc()


def lock_screen() -> str:
    """Ekranı kilitler."""
    try:
        if platform.system() == "Windows":
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        else:
            subprocess.run(["xdg-screensaver", "lock"])
        return "Ekran kilitlendi."
    except Exception as e:
        log.error(f"Ekran kilitleme hatası: {e}")
        return "Ekran kilitlenirken bir hata oluştu."


def sleep_pc() -> str:
    """Bilgisayarı uyku moduna alır."""
    try:
        if platform.system() == "Windows":
            # hibernate=False, force=True, wakeupEventsDisabled=False
            ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
        else:
            subprocess.run(["systemctl", "suspend"], check=False)
        log.warning("Uyku komutu tetiklendi.")
        return "Bilgisayar uykuya geçiyor."
    except Exception as e:
        log.error(f"Uyku hatası: {e}")
        return "Uyku moduna geçilemedi."


def cancel_shutdown() -> str:
    """Bekleyen kapatma/yeniden başlatmayı iptal eder."""
    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["shutdown", "/a"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        return "Zamanlanmış kapatma iptal edildi."
    except Exception as e:
        log.error(f"Kapatma iptal hatası: {e}")
        return "Kapatma iptal edilemedi."


def get_telemetry_dict() -> dict:
    """Canlı sistem telemetrisi (CPU, RAM, Disk, Pil, Saat, Oyun Modu)."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk_path = "C:\\" if os.name == "nt" else "/"
        disk = psutil.disk_usage(disk_path).percent
        battery = None
        try:
            b = psutil.sensors_battery()
            if b is not None:
                battery = {"percent": int(b.percent), "plugged": bool(b.power_plugged)}
        except Exception:
            pass

        return {
            "cpu": round(float(cpu), 1),
            "ram": round(float(ram), 1),
            "disk": round(float(disk), 1),
            "battery": battery,
            "game_mode": _GAME_MODE_ACTIVE,
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
        }
    except Exception as e:
        log.error(f"Telemetri okuma hatası: {e}")
        return {"cpu": 0.0, "ram": 0.0, "disk": 0.0, "battery": None, "game_mode": _GAME_MODE_ACTIVE, "error": str(e)}


def turn_off_display() -> str:
    """Monitörü enerji tasarrufu/uyku moduna alır (ekranı karartır)."""
    try:
        if platform.system() == "Windows":
            # HWND_BROADCAST = 0xFFFF, WM_SYSCOMMAND = 0x0112, SC_MONITORPOWER = 0xF170, 2 = power off
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
            return "PC monitörü kapatıldı."
        return "Monitör kapatma bu sistemde desteklenmiyor."
    except Exception as e:
        log.error(f"Monitör kapatma hatası: {e}")
        return f"Monitör kapatılamadı: {e}"


def open_special_folder(folder_name: str) -> str:
    """Özel sistem klasörlerini Dosya Gezgini'nde açar."""
    try:
        name = (folder_name or "").lower().strip()
        user_home = Path.home()
        mapping = {
            "downloads": user_home / "Downloads",
            "indirilenler": user_home / "Downloads",
            "airdrop": user_home / "Downloads" / "RIFKI_AirDrop",
            "documents": user_home / "Documents",
            "belgeler": user_home / "Documents",
            "desktop": user_home / "Desktop",
            "masaustu": user_home / "Desktop",
            "pictures": user_home / "Pictures",
            "resimler": user_home / "Pictures",
            "music": user_home / "Music",
            "muzik": user_home / "Music",
            "home": user_home,
        }
        target = mapping.get(name)
        if name == "airdrop" and target is not None:
            target.mkdir(parents=True, exist_ok=True)
        if target and target.is_dir():
            if platform.system() == "Windows":
                os.startfile(str(target))
            else:
                subprocess.Popen(["xdg-open", str(target)])
            return f"{folder_name.capitalize()} klasörü açıldı."
        return f"Klasör bulunamadı: {folder_name}"
    except Exception as e:
        log.error(f"Klasör açma hatası: {e}")
        return f"Klasör açılamadı: {e}"


def set_clipboard_text(text: str) -> str:
    """Metni PC panosuna kopyalar."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return "Metin PC panosuna kopyalandı."
    except Exception as e:
        log.error(f"Pano yazma hatası: {e}")
        return f"Panoya kopyalanamadı: {e}"


def get_clipboard_text() -> str:
    """PC panosundaki metni döndürür."""
    try:
        import pyperclip
        return pyperclip.paste() or ""
    except Exception as e:
        log.error(f"Pano okuma hatası: {e}")
        return ""


def send_key_stroke(key: str) -> str:
    """Önemli klavye tuşlarını veya kombinasyonlarını tetikler."""
    try:
        import pyautogui
        k = (key or "").lower().strip()
        valid_keys = {
            "enter": "enter",
            "esc": "esc",
            "escape": "esc",
            "space": "space",
            "backspace": "backspace",
            "tab": "tab",
            "win": "win",
            "windows": "win",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
        }
        if k in valid_keys:
            pyautogui.press(valid_keys[k])
            return f"Tuş iletildi: {k}"
        elif k in ("alt_tab", "alttab"):
            pyautogui.hotkey("alt", "tab")
            return "Alt+Tab uygulandı."
        elif k in ("win_d", "wind"):
            pyautogui.hotkey("win", "d")
            return "Masaüstünü göster (Win+D) uygulandı."
        return f"Bilinmeyen tuş: {key}"
    except Exception as e:
        log.error(f"Tuş iletme hatası: {e}")
        return f"Tuş iletilemedi: {e}"


def type_text_to_pc(text: str) -> str:
    """Metni PC'de aktif olan pencereye harf harf yazar."""
    try:
        import pyautogui
        pyautogui.write(text, interval=0.01)
        return "Metin PC'ye yazdırıldı."
    except Exception as e:
        log.error(f"Metin yazdırma hatası: {e}")
        return f"Metin yazılamadı: {e}"


# =========================================================================
# 🖱️ CANLI TOUCHPAD (FARE KONTROLÜ) — Win32 Düşük Gecikmeli API
# =========================================================================
def move_mouse_relative(dx: int, dy: int) -> str:
    """PC fare imlecini göreceli olarak (dx, dy piksel) hareket ettirir."""
    try:
        dx_clamped = max(-1000, min(1000, int(dx)))
        dy_clamped = max(-1000, min(1000, int(dy)))
        if os.name == "nt":
            _ensure_input_desktop()
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, dx_clamped, dy_clamped, 0, 0)
        else:
            import pyautogui
            pyautogui.moveRel(dx_clamped, dy_clamped)
        return "Fare hareket ettirildi."
    except Exception as e:
        log.error(f"Fare hareket hatası: {e}")
        return f"Fare hareket ettirilemedi: {e}"


def mouse_click(button: str = "left") -> str:
    """PC faresine sol, sağ, orta veya çift tıklama yaptırır."""
    btn = (button or "left").lower().strip()
    try:
        if os.name == "nt":
            _ensure_input_desktop()
            u32 = ctypes.windll.user32
            if btn == "right":
                u32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
                u32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
                return "Sağ tık uygulandı."
            elif btn == "middle":
                u32.mouse_event(MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
                u32.mouse_event(MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
                return "Orta tık uygulandı."
            elif btn == "double":
                for _ in range(2):
                    u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                    u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    time.sleep(0.04)
                return "Çift tık uygulandı."
            else:
                u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                return "Sol tık uygulandı."
        else:
            import pyautogui
            if btn == "double":
                pyautogui.doubleClick()
            else:
                pyautogui.click(button=btn if btn in ("left", "right", "middle") else "left")
            return f"Fare tıklandı ({btn})."
    except Exception as e:
        log.error(f"Fare tıklama hatası: {e}")
        return f"Fare tıklanamadı: {e}"


def mouse_scroll(dy: int) -> str:
    """PC fare tekerleğini yukarı (+dy) veya aşağı (-dy) kaydırır."""
    try:
        steps = max(-20, min(20, int(dy)))
        if os.name == "nt":
            _ensure_input_desktop()
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, steps * 120, 0)
        else:
            import pyautogui
            pyautogui.scroll(steps * 100)
        return "Sayfa kaydırıldı."
    except Exception as e:
        log.error(f"Fare kaydırma hatası: {e}")
        return f"Kaydırma yapılamadı: {e}"


# =========================================================================
# 🎮 OYUN & PERFORMANS MODU + RAM OPTİMİZASYONU
# =========================================================================
def optimize_system_ram(*args, **kwargs) -> str:
    """
    Windows EmptyWorkingSet API kullanarak arka planda atıl duran uygulamaların
    RAM çalışma kümelerini (working set) güvenli şekilde temizler ve belleği rahatlatır.
    Hiçbir uygulamayı kapatmaz veya veri kaybına yol açmaz.
    """
    import psutil

    vm_before = psutil.virtual_memory()
    used_before = vm_before.used
    pct_before = vm_before.percent

    gc.collect()

    trimmed_count = 0
    if os.name == "nt":
        try:
            kernel32 = ctypes.windll.kernel32
            psapi = ctypes.windll.psapi
            # PROCESS_QUERY_INFORMATION (0x0400) | PROCESS_SET_QUOTA (0x0100)
            access = 0x0400 | 0x0100
            for proc in psutil.process_iter(["pid", "name"]):
                pid = proc.info.get("pid")
                if not pid or pid <= 4:
                    continue
                hproc = kernel32.OpenProcess(access, False, int(pid))
                if hproc:
                    try:
                        if psapi.EmptyWorkingSet(hproc):
                            trimmed_count += 1
                    finally:
                        kernel32.CloseHandle(hproc)
        except Exception as e:
            log.warning(f"Win32 RAM EmptyWorkingSet uyarısı: {e}")

    time.sleep(0.15)
    vm_after = psutil.virtual_memory()
    used_after = vm_after.used
    pct_after = vm_after.percent
    freed_mb = max(0, int(round((used_before - used_after) / (1024 * 1024))))

    log.info(f"RAM optimize edildi: {trimmed_count} işlem, ~{freed_mb} MB kazanıldı (%{pct_before} -> %{pct_after})")
    if freed_mb > 5:
        return (
            f"🚀 RAM Optimizasyonu tamamlandı! {trimmed_count} arka plan işleminin önbelleği temizlendi, "
            f"yaklaşık {freed_mb} MB RAM boşa çıkarıldı (Bellek kullanımı: %{pct_before} → %{pct_after})."
        )
    return (
        f"🚀 RAM belleği denetlendi ve {trimmed_count} işlemin çalışma kümesi optimize edildi "
        f"(Mevcut bellek kullanımı: %{pct_after})."
    )


def set_game_mode(enabled: bool = True, *args, **kwargs) -> str:
    """
    Oyun ve Yüksek Performans Modunu açar veya kapatır:
    - Açıldığında: Windows Yüksek Performans güç planını devreye alır, RAM önbelleğini temizler
      ve R.I.F.K.I masaüstü HUD animasyonunu Eco (Düşük GPU/CPU) moduna çeker.
    - Kapatıldığında: Windows Dengeli güç planına döner ve HUD animasyonunu tam hıza çıkarır.
    """
    global _GAME_MODE_ACTIVE
    if isinstance(enabled, str):
        enabled = enabled.strip().lower() not in ("0", "false", "no", "off", "kapat", "kapalı", "hayır")
    else:
        enabled = bool(enabled)

    _GAME_MODE_ACTIVE = enabled
    no_win = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    if enabled:
        if os.name == "nt":
            try:
                # High Performance GUID: 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
                subprocess.run(
                    ["powercfg", "/setactive", "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"],
                    creationflags=no_win,
                    timeout=5,
                    check=False,
                )
            except Exception as e:
                log.warning(f"Güç planı değiştirilemedi: {e}")

        ram_msg = optimize_system_ram()
        if _GAME_MODE_CALLBACK:
            try:
                _GAME_MODE_CALLBACK(True)
            except Exception as e:
                log.warning(f"Game mode UI callback hatası: {e}")

        log.info("Oyun & Performans Modu AKTİF edildi.")
        return (
            "🎮 Oyun ve Performans Modu AKTİF! Windows Yüksek Performans güç planı devreye alındı, "
            "R.I.F.K.I arayüzü sıfır yük (Eco HUD) moduna çekildi. " + ram_msg
        )
    else:
        if os.name == "nt":
            try:
                # Balanced GUID: 381b4222-f694-41f0-9685-ff5bb260df2e
                subprocess.run(
                    ["powercfg", "/setactive", "381b4222-f694-41f0-9685-ff5bb260df2e"],
                    creationflags=no_win,
                    timeout=5,
                    check=False,
                )
            except Exception as e:
                log.warning(f"Dengeli güç planına dönülemedi: {e}")

        if _GAME_MODE_CALLBACK:
            try:
                _GAME_MODE_CALLBACK(False)
            except Exception as e:
                log.warning(f"Game mode UI callback hatası: {e}")

        log.info("Oyun & Performans Modu KAPATILDI.")
        return "🎮 Oyun Modu kapatıldı. Sistem standart güç planına ve tam hız HUD animasyonuna geri döndü."


def toggle_game_mode() -> str:
    """Oyun modunu tersine çevirir (Açık <-> Kapalı)."""
    return set_game_mode(not _GAME_MODE_ACTIVE)
