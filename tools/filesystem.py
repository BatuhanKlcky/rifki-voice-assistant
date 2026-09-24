"""
tools/filesystem.py
--------------------
Güvenli dosya/klasör işlemleri. Silme gibi geri dönüşü zor işlemler
core/security.py üzerinden onay gerektirir (router bunu kontrol eder).
"""

import os
import shutil
from pathlib import Path
from core.logger import get_logger

log = get_logger("tools.filesystem")


def search_files(folder: str, keyword: str) -> str:
    folder_path = Path(folder).expanduser()
    if not folder_path.exists():
        return f"'{folder}' klasörü bulunamadı."

    matches = []
    try:
        for root, _, files in os.walk(folder_path):
            for f in files:
                if keyword.lower() in f.lower():
                    matches.append(str(Path(root) / f))
            if len(matches) >= 20:
                break
    except Exception as e:
        log.error(f"Dosya arama hatası: {e}")
        return "Dosya aranırken bir sorun oluştu."

    if not matches:
        return f"'{keyword}' ile eşleşen dosya bulunamadı."
    listing = "\n".join(matches[:20])
    return f"{len(matches)} dosya bulundu:\n{listing}"


def create_file(path: str, content: str = "") -> str:
    try:
        p = Path(path).expanduser()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        log.info(f"Dosya oluşturuldu: {p}")
        return f"{p} oluşturuldu."
    except Exception as e:
        log.error(f"Dosya oluşturma hatası: {e}")
        return "Dosya oluşturulurken bir sorun oluştu."


def copy_file(source: str, destination: str) -> str:
    try:
        shutil.copy2(Path(source).expanduser(), Path(destination).expanduser())
        return f"{source} -> {destination} kopyalandı."
    except Exception as e:
        log.error(f"Kopyalama hatası: {e}")
        return "Dosya kopyalanırken bir sorun oluştu."


def move_file(source: str, destination: str) -> str:
    try:
        shutil.move(Path(source).expanduser(), Path(destination).expanduser())
        return f"{source} -> {destination} taşındı."
    except Exception as e:
        log.error(f"Taşıma hatası: {e}")
        return "Dosya taşınırken bir sorun oluştu."


def rename_file(source: str, new_name: str) -> str:
    try:
        src = Path(source).expanduser()
        dst = src.parent / new_name
        src.rename(dst)
        return f"{source} -> {new_name} olarak yeniden adlandırıldı."
    except Exception as e:
        log.error(f"Yeniden adlandırma hatası: {e}")
        return "Dosya yeniden adlandırılırken bir sorun oluştu."


def delete_file(path: str) -> str:
    """Bu fonksiyon router tarafından SADECE kullanıcı onayından sonra çağrılmalı."""
    try:
        p = Path(path).expanduser()
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
        log.info(f"Silindi: {p}")
        return f"{p} silindi."
    except Exception as e:
        log.error(f"Silme hatası: {e}")
        return "Dosya silinirken bir sorun oluştu."


def open_path(path: str) -> str:
    """Bir dosya/klasörü varsayılan uygulamayla açar."""
    p = Path(path).expanduser()
    if not p.exists():
        return f"'{path}' bulunamadı."
    try:
        os.startfile(str(p))  # Windows-only
        return f"{path} açılıyor."
    except AttributeError:
        return "Dosya/klasör açma şu an sadece Windows'ta destekleniyor."
    except Exception as e:
        log.error(f"Açma hatası: {e}")
        return "Açarken bir sorun oluştu."
