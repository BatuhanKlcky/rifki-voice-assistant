"""
tools/system.py
----------------
İşletim sistemi kontrol araçları (kapanma, yeniden başlatma, sistem durumu, ses, tarih ve ekran görüntüsü).
"""

import os
import platform
import subprocess
import datetime
from pathlib import Path
from core.logger import get_logger

log = get_logger("tools.system")


def get_system_status() -> str:
    """Sistem kaynaklarının anlık durumunu özetler."""
    import psutil
    # Blocking interval=0.5 kaldırıldı; non-blocking ölçüm + tek ısıtma
    psutil.cpu_percent(interval=None)
    cpu = psutil.cpu_percent(interval=0.05)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/").percent
    return f"Sistem Durumu -> CPU: %{cpu}, RAM: %{ram}, Disk: %{disk}"


def get_datetime() -> str:
    """Anlık tarih ve saat bilgisini döndürür."""
    now = datetime.datetime.now()
    return now.strftime("%d Eylül %Y, %H:%M:%S")


def _grab_screenshot_image():
    """Ekranı PIL Image olarak alır (ImageGrab → pyautogui)."""
    errors: list[str] = []
    try:
        from PIL import ImageGrab

        image = ImageGrab.grab(all_screens=True)
        if image is not None:
            return image
    except Exception as e:
        errors.append(f"ImageGrab: {e}")

    try:
        import pyautogui

        image = pyautogui.screenshot()
        if image is not None:
            return image
    except Exception as e:
        errors.append(f"pyautogui: {e}")

    raise RuntimeError("; ".join(errors) or "ekran görüntüsü alınamadı")


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


def capture_screenshot_for_mobile(max_width: int = 1280, quality: int = 72) -> bytes:
    """Mobil için ölçeklenmiş JPEG (daha küçük / hızlı)."""
    import io

    image = _grab_screenshot_image()
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    w, h = image.size
    if w > max_width and w > 0:
        new_h = max(1, int(h * (max_width / float(w))))
        try:
            from PIL import Image as _PILImage

            resample = getattr(_PILImage, "Resampling", _PILImage).LANCZOS
        except Exception:
            resample = 1  # LANCZOS
        image = image.resize((max_width, new_h), resample)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=max(40, min(95, int(quality))), optimize=True)
    data = buf.getvalue()
    if not data or len(data) < 100:
        raise RuntimeError("ekran görüntüsü alınamadı")
    return data


def take_screenshot() -> str:
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
    # Yeni pycaw: EndpointVolume özelliği; eski: Activate(...)
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
            import ctypes

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