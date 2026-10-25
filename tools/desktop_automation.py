"""
tools/desktop_automation.py
----------------------------
Gelişmiş Windows masaüstü otomasyonu ve dosya düzenleyici:
- İndirilenler ve Masaüstü klasörünü dosya türlerine göre otomatik düzenleme
- Geri Dönüşüm Kutusunu (Recycle Bin) boşaltma
- Aktif pencere ve sekme yönetimi (kapat, küçült, tam ekran, masaüstünü göster)
"""

from __future__ import annotations

import ctypes
import os
import shutil
import time
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger("tools.automation")

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

VK_LWIN = 0x5B
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_SHIFT = 0x10
VK_TAB = 0x09
VK_F4 = 0x73
VK_F5 = 0x74
VK_F11 = 0x7A
VK_D = 0x44
VK_T = 0x54
VK_W = 0x57
VK_UP = 0x26
VK_DOWN = 0x28

SHERB_NOCONFIRMATION = 0x00000001
SHERB_NOPROGRESSUI = 0x00000002
SHERB_NOSOUND = 0x00000004

FILE_CATEGORIES = {
    "Resimler": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff"},
    "Belgeler": {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".txt", ".csv", ".epub", ".md"},
    "Arşivler": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "Kurulumlar": {".exe", ".msi", ".iso", ".bat", ".cmd", ".apk"},
    "Ses_ve_Video": {".mp3", ".wav", ".flac", ".m4a", ".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "Kod_ve_Projeler": {".py", ".js", ".html", ".css", ".json", ".sql", ".cpp", ".cs", ".java"},
}


def _key_combo(*vks: int):
    """Tuş kombinasyonunu basar ve sırayla bırakır."""
    for vk in vks:
        user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    for vk in reversed(vks):
        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


def empty_recycle_bin(*args, **kwargs) -> str:
    """Windows Geri Dönüşüm Kutusunu (Çöp Kutusu) tamamen boşaltır."""
    try:
        res = shell32.SHEmptyRecycleBinW(
            None, None, SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI
        )
        if res == 0:
            log.info("Geri dönüşüm kutusu boşaltıldı.")
            return "Geri Dönüşüm Kutusu başarıyla boşaltıldı."
        elif res == -2147418113:  # S_FALSE (zaten boş)
            return "Geri Dönüşüm Kutusu zaten boş."
        return "Geri Dönüşüm Kutusu boşaltıldı."
    except Exception as e:
        log.error(f"Geri dönüşüm kutusu boşaltma hatası: {e}")
        return f"Çöp kutusu boşaltılırken bir hata oluştu: {e}"


def organize_folder(folder_name: str = "downloads", *args, **kwargs) -> str:
    """
    İndirilenler (downloads) veya Masaüstü (desktop) klasöründeki dağınık dosyaları
    türlerine göre (Resimler, Belgeler, Arşivler, Kurulumlar) alt klasörlere taşır.
    """
    user_home = Path(os.path.expanduser("~"))
    target_dir = None

    low_name = folder_name.lower().strip()
    if any(k in low_name for k in ("indir", "download")):
        target_dir = user_home / "Downloads"
    elif any(k in low_name for k in ("masaüstü", "desktop")):
        target_dir = user_home / "Desktop"
    elif os.path.isdir(folder_name):
        target_dir = Path(folder_name)
    else:
        target_dir = user_home / "Downloads"

    if not target_dir.is_dir():
        return f"Hedef klasör bulunamadı: {target_dir}"

    moved_counts: dict[str, int] = {}
    skipped = 0

    try:
        for item in list(target_dir.iterdir()):
            # Klasörleri, gizli dosyaları ve kısayolları atla
            if item.is_dir() or item.name.startswith(".") or item.suffix.lower() == ".lnk":
                continue

            ext = item.suffix.lower()
            if not ext:
                continue

            matched_category = None
            for category, ext_set in FILE_CATEGORIES.items():
                if ext in ext_set:
                    matched_category = category
                    break

            if not matched_category:
                matched_category = "Diğer"

            category_dir = target_dir / matched_category
            category_dir.mkdir(parents=True, exist_ok=True)

            dest_path = category_dir / item.name
            # İsim çakışması varsa numaralandır
            counter = 1
            stem = item.stem
            while dest_path.exists():
                dest_path = category_dir / f"{stem}_{counter}{ext}"
                counter += 1

            shutil.move(str(item), str(dest_path))
            moved_counts[matched_category] = moved_counts.get(matched_category, 0) + 1

        total_moved = sum(moved_counts.values())
        if total_moved == 0:
            return f"'{target_dir.name}' klasöründe düzenlenecek dağınık dosya bulunamadı, her şey tertemiz!"

        summary_parts = [f"{count} {cat}" for cat, count in moved_counts.items()]
        return f"'{target_dir.name}' klasörü düzenlendi: Toplam {total_moved} dosya kategorilerine ayrıldı ({', '.join(summary_parts)})."
    except Exception as e:
        log.error(f"Klasör düzenleme hatası: {e}")
        return f"Klasör düzenlenirken bir hata oluştu: {e}"


def control_active_window(action: str, *args, **kwargs) -> str:
    """
    Aktif pencereyi kontrol eder:
    - 'show_desktop' / 'masaüstü' (Win+D)
    - 'minimize' / 'küçült' (Win+Aşağı Ok)
    - 'maximize' / 'büyüt' (Win+Yukarı Ok)
    - 'close' / 'kapat' (Alt+F4)
    - 'fullscreen' / 'tam_ekran' (F11)
    - 'switch_window' / 'pencere_degis' (Alt+Tab)
    """
    act = action.lower().strip()
    try:
        if any(k in act for k in ("desktop", "masaüstü", "gizle")):
            _key_combo(VK_LWIN, VK_D)
            return "Masaüstü gösterildi."
        elif any(k in act for k in ("close", "kapat")):
            _key_combo(VK_MENU, VK_F4)
            return "Aktif pencere kapatıldı."
        elif any(k in act for k in ("maximize", "büyüt", "ekranı kapla")):
            _key_combo(VK_LWIN, VK_UP)
            return "Pencere büyütüldü."
        elif any(k in act for k in ("minimize", "küçült")):
            _key_combo(VK_LWIN, VK_DOWN)
            return "Pencere küçültüldü."
        elif any(k in act for k in ("fullscreen", "tam ekran")):
            _key_combo(VK_F11)
            return "Tam ekran moduna geçildi."
        elif any(k in act for k in ("switch", "geç", "alt_tab")):
            _key_combo(VK_MENU, VK_TAB)
            return "Pencere değiştirildi."
        else:
            return f"Bilinmeyen pencere eylemi: {action}"
    except Exception as e:
        log.error(f"Pencere kontrol hatası: {e}")
        return "Pencere kontrolü gerçekleştirilemedi."


def browser_tab_action(action: str, *args, **kwargs) -> str:
    """
    Tarayıcı sekmelerini yönetir:
    - 'new_tab' / 'yeni_sekme' (Ctrl+T)
    - 'close_tab' / 'sekmeyi_kapat' (Ctrl+W)
    - 'reopen_tab' / 'kapanan_sekme' (Ctrl+Shift+T)
    - 'refresh' / 'yenile' (F5)
    """
    act = action.lower().strip()
    try:
        if any(k in act for k in ("new", "yeni")):
            _key_combo(VK_CONTROL, VK_T)
            return "Yeni tarayıcı sekmesi açıldı."
        elif any(k in act for k in ("close", "kapat")):
            _key_combo(VK_CONTROL, VK_W)
            return "Mevcut sekme kapatıldı."
        elif any(k in act for k in ("reopen", "geri", "kurtar")):
            _key_combo(VK_CONTROL, VK_SHIFT, VK_T)
            return "Son kapatılan sekme geri açıldı."
        elif any(k in act for k in ("refresh", "yenile")):
            _key_combo(VK_F5)
            return "Sayfa yenilendi."
        else:
            return f"Bilinmeyen sekme eylemi: {action}"
    except Exception as e:
        log.error(f"Sekme eylemi hatası: {e}")
        return "Sekme eylemi gerçekleştirilemedi."
