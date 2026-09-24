"""
tools/applications.py
----------------------
Uygulama açma / kapatma.

ÖNEMLİ (dürüst not): Windows'ta uygulama adları makineden makineye değişir
(kurulum yolu, sürüm vs.). Aşağıdaki KNOWN_APPS sözlüğü en yaygın uygulamalar
için makul varsayılanlar içerir. Kendi bilgisayarındaki bir uygulama burada
yoksa veya farklı bir yola kuruluysa, sözlüğe kendi yolunu eklemen gerekir.
Rastgele/gelişigüzel shell komutu ÇALIŞTIRILMAZ; sadece bu izinli listede
tanımlı uygulamalar açılabilir.
"""

import subprocess
import psutil
from config.settings import settings
from core.logger import get_logger

log = get_logger("tools.applications")

# name -> Windows'ta çalıştırılacak komut (PATH'te olduğu varsayılan yaygın uygulamalar)
KNOWN_APPS = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "notepad": "notepad",
    "not defteri": "notepad",
    "hesap makinesi": "calc",
    "calculator": "calc",
    "explorer": "explorer",
    "dosya gezgini": "explorer",
    "word": "winword",
    "excel": "excel",
    "spotify": "spotify",
    "discord": "discord",
    "vscode": "code",
    "visual studio code": "code",
    "paint": "mspaint",
    "android studio": "studio64",
    "g hub": "lghub",
    "logitech g hub": "lghub",
}

# process adı eşlemesi (kapatma için) - Windows'ta görev yöneticisindeki isim
PROCESS_NAMES = {
    "chrome": "chrome.exe",
    "notepad": "notepad.exe",
    "spotify": "Spotify.exe",
    "discord": "Discord.exe",
    "word": "WINWORD.EXE",
    "excel": "EXCEL.EXE",
    "vscode": "Code.exe",
    "android studio": "studio64.exe",
    "g hub": "lghub.exe",
    "logitech g hub": "lghub.exe",
    "rust": "RustClient.exe",
    "rainbow six siege": "RainbowSix.exe",
}


def open_application(name: str) -> str:
    """Bilinen bir uygulamayı adına göre açar."""
    key = name.strip().lower()
    command = KNOWN_APPS.get(key)

    if command is None:
        log.warning(f"Bilinmeyen uygulama istendi: {name}")
        return (
            f"'{name}' adlı uygulamayı tanımıyorum. "
            f"tools/applications.py içindeki KNOWN_APPS listesine eklemen gerekiyor."
        )

    if not settings.IS_WINDOWS:
        log.warning("Windows dışı ortamda uygulama açma denendi.")
        return "Uygulama açma özelliği şu an sadece Windows'ta çalışacak şekilde tasarlandı."

    try:
        subprocess.Popen(command, shell=True)
        log.info(f"Uygulama açıldı: {name} -> {command}")
        return f"{name} açılıyor."
    except Exception as e:
        log.error(f"Uygulama açma hatası ({name}): {e}")
        return f"{name} açılırken bir sorun oluştu."


def close_application(name: str) -> str:
    """Çalışan bir uygulamayı process adına göre kapatır."""
    key = name.strip().lower()
    process_name = PROCESS_NAMES.get(key)

    if process_name is None:
        return (
            f"'{name}' için kapatılacak process adını bilmiyorum. "
            f"tools/applications.py -> PROCESS_NAMES içine eklemen gerekiyor."
        )

    closed = False
    try:
        for proc in psutil.process_iter(["name"]):
            if proc.info["name"] and proc.info["name"].lower() == process_name.lower():
                proc.terminate()
                closed = True
        log.info(f"Uygulama kapatma denendi: {name} ({process_name}), sonuç={closed}")
        if closed:
            return f"{name} kapatıldı."
        return f"{name} zaten çalışmıyor gibi görünüyor."
    except Exception as e:
        log.error(f"Uygulama kapatma hatası ({name}): {e}")
        return f"{name} kapatılırken bir sorun oluştu."
