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
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("C:\\" if os.name == "nt" else "/").percent
    return f"Sistem Durumu -> CPU: %{cpu}, RAM: %{ram}, Disk: %{disk}"


def get_datetime() -> str:
    """Anlık tarih ve saat bilgisini döndürür."""
    now = datetime.datetime.now()
    return now.strftime("%d Eylül %Y, %H:%M:%S")


def take_screenshot() -> str:
    """Ekran görüntüsü alır ve masaüstüne kaydeder."""
    try:
        import pyautogui
        desktop = Path(os.path.expanduser("~")) / "Desktop"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = desktop / f"rifki_screenshot_{timestamp}.png"
        
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        log.info(f"Ekran görüntüsü kaydedildi: {filepath}")
        return f"Ekran görüntüsü başarıyla masaüstüne kaydedildi."
    except Exception as e:
        log.error(f"Ekran görüntüsü alma hatası: {e}")
        return "Ekran görüntüsü alınamadı (pyautogui kütüphanesi gerekebilir)."


def set_volume(level: int) -> str:
    """Sistem ses seviyesini belirtilen yüzdeye (0-100) ayarlar."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        scalar = max(0.0, min(100.0, float(level))) / 100.0
        volume.SetMasterVolumeLevelScalar(scalar, None)
        return f"Ses seviyesi %{level} olarak ayarlandı."
    except Exception as e:
        log.error(f"Ses ayarlama hatası: {e}")
        return "Ses seviyesi değiştirilemedi."


def mute_volume() -> str:
    """Sistem sesini tamamen kapatır (Mute)."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        volume.SetMute(1, None)
        return "Sistem sesi kapatıldı."
    except Exception as e:
        log.error(f"Sesi kapatma hatası: {e}")
        return "Ses kapatılamadı."


def unmute_volume() -> str:
    """Sistem sesini açar (Unmute)."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        volume.SetMute(0, None)
        return "Sistem sesi açıldı."
    except Exception as e:
        log.error(f"Sesi açma hatası: {e}")
        return "Ses açılamadı."


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
