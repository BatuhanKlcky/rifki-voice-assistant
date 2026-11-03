"""
tools/filesystem.py
--------------------
Güvenli dosya/klasör işlemleri. Silme gibi geri dönüşü zor işlemler
core/security.py üzerinden onay gerektirir (router bunu kontrol eder).
"""

import os
import shutil
from pathlib import Path
from config.settings import BASE_DIR
from core.logger import get_logger

log = get_logger("tools.filesystem")

_BLOCKED_NAMES = {
    ".env",
    ".env.local",
    "id_rsa",
    "id_ed25519",
    "authorized_keys",
    "known_hosts",
    "keystore.properties",
}
_BLOCKED_EXTENSIONS = {".pem", ".jks", ".keystore", ".pfx", ".p12", ".sys", ".dll"}


def _validate_path(raw_path: str, write_operation: bool = True) -> tuple[Path | None, str | None]:
    """
    Dosya sistemi yollarını güvenlik duvarından geçirir:
    - Hassas dosyalara (.env, anahtarlar, sertifikalar) erişimi engeller.
    - Yazma/taşıma/silme işlemlerinde Windows sistem klasörlerini, AppData'yı
      ve R.I.F.K.I'nin kendi uygulama dizinini (BASE_DIR) koruma altına alır.
    """
    if not raw_path or not str(raw_path).strip():
        return None, "Geçerli bir dosya yolu belirtilmedi."
    try:
        p = Path(raw_path).expanduser().resolve()
    except Exception:
        return None, "Geçersiz dosya yolu formatı."

    name_low = p.name.lower()
    if name_low in _BLOCKED_NAMES or p.suffix.lower() in _BLOCKED_EXTENSIONS:
        log.warning(f"Güvenlik engeli: Hassas dosyaya erişim reddedildi -> {p}")
        return None, "Güvenlik politikası gereği bu dosya türüne erişim engellendi."

    parts_low = {part.lower() for part in p.parts}
    if any(secret_dir in parts_low for secret_dir in (".ssh", ".gnupg", ".git", ".aws")):
        log.warning(f"Güvenlik engeli: Korumalı gizli dizine erişim reddedildi -> {p}")
        return None, "Güvenlik politikası gereği bu dizine erişim engellendi."

    if write_operation:
        app_root = BASE_DIR.resolve()
        if p == app_root or app_root in p.parents:
            log.warning(f"Güvenlik engeli: R.I.F.K.I uygulama dizinine müdahale reddedildi -> {p}")
            return None, "Güvenlik politikası gereği R.I.F.K.I sistem dosyaları değiştirilemez."

        protected_roots = [
            Path(os.environ.get("SystemRoot", "C:\\Windows")).resolve(),
            Path(os.environ.get("ProgramFiles", "C:\\Program Files")).resolve(),
            Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")).resolve(),
            Path(os.environ.get("ProgramData", "C:\\ProgramData")).resolve(),
        ]
        appdata = os.environ.get("APPDATA")
        localappdata = os.environ.get("LOCALAPPDATA")
        if appdata:
            protected_roots.append(Path(appdata).resolve())
        if localappdata:
            protected_roots.append(Path(localappdata).resolve())

        for root in protected_roots:
            if p == root or root in p.parents:
                log.warning(f"Güvenlik engeli: Sistem klasörüne yazma/silme reddedildi -> {p}")
                return None, "Güvenlik politikası gereği sistem klasörlerinde değişiklik yapılamaz."

    return p, None


def search_files(folder: str, keyword: str) -> str:
    folder_path, err = _validate_path(folder, write_operation=False)
    if err or folder_path is None:
        return err or "Geçersiz klasör yolu."
    if not folder_path.exists():
        return f"'{folder}' klasörü bulunamadı."

    matches = []
    try:
        for root, dirs, files in os.walk(folder_path):
            # Gizli / hassas klasörleri aramadan hariç tut
            dirs[:] = [d for d in dirs if d.lower() not in {".git", ".ssh", ".venv", "venv", "__pycache__", "node_modules"}]
            for f in files:
                if f.lower() in _BLOCKED_NAMES:
                    continue
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
        p, err = _validate_path(path, write_operation=True)
        if err or p is None:
            return err or "Dosya yolu doğrulanamadı."
        if p.exists():
            log.warning(f"Üzerine yazma engellendi (dosya zaten var): {p}")
            return f"'{p.name}' adında bir dosya zaten mevcut. Güvenlik nedeniyle mevcut dosyanın üzerine yazılmadı."
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        log.info(f"Dosya oluşturuldu: {p}")
        return f"{p} oluşturuldu."
    except Exception as e:
        log.error(f"Dosya oluşturma hatası: {e}")
        return "Dosya oluşturulurken bir sorun oluştu."


def copy_file(source: str, destination: str) -> str:
    try:
        src, err1 = _validate_path(source, write_operation=False)
        dst, err2 = _validate_path(destination, write_operation=True)
        if err1 or src is None:
            return err1 or "Kaynak dosya yolu geçersiz."
        if err2 or dst is None:
            return err2 or "Hedef dosya yolu geçersiz."
        shutil.copy2(src, dst)
        return f"{source} -> {destination} kopyalandı."
    except Exception as e:
        log.error(f"Kopyalama hatası: {e}")
        return "Dosya kopyalanırken bir sorun oluştu."


def move_file(source: str, destination: str) -> str:
    try:
        src, err1 = _validate_path(source, write_operation=True)
        dst, err2 = _validate_path(destination, write_operation=True)
        if err1 or src is None:
            return err1 or "Kaynak dosya yolu geçersiz."
        if err2 or dst is None:
            return err2 or "Hedef dosya yolu geçersiz."
        shutil.move(src, dst)
        return f"{source} -> {destination} taşındı."
    except Exception as e:
        log.error(f"Taşıma hatası: {e}")
        return "Dosya taşınırken bir sorun oluştu."


def rename_file(source: str, new_name: str) -> str:
    try:
        if any(sep in new_name for sep in ("/", "\\", "..")):
            return "Yeni dosya adı klasör yolu içeremez."
        src, err1 = _validate_path(source, write_operation=True)
        if err1 or src is None:
            return err1 or "Kaynak dosya yolu geçersiz."
        dst, err2 = _validate_path(str(src.parent / new_name), write_operation=True)
        if err2 or dst is None:
            return err2 or "Hedef dosya adı geçersiz."
        src.rename(dst)
        return f"{source} -> {new_name} olarak yeniden adlandırıldı."
    except Exception as e:
        log.error(f"Yeniden adlandırma hatası: {e}")
        return "Dosya yeniden adlandırılırken bir sorun oluştu."


def delete_file(path: str) -> str:
    """Bu fonksiyon router tarafından SADECE kullanıcı onayından sonra çağrılmalı."""
    try:
        p, err = _validate_path(path, write_operation=True)
        if err or p is None:
            return err or "Silinecek dosya yolu geçersiz."
        # Kullanıcı ana klasörlerinin (Desktop, Downloads, Documents, Home) kendisinin silinmesini engelle
        home = Path.home().resolve()
        critical_user_dirs = {
            home,
            (home / "Desktop").resolve(),
            (home / "Downloads").resolve(),
            (home / "Documents").resolve(),
            (home / "Pictures").resolve(),
        }
        if p in critical_user_dirs:
            return "Ana kullanıcı klasörleri tamamen silinemez."
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
    p, err = _validate_path(path, write_operation=False)
    if err or p is None:
        return err or "Dosya yolu doğrulanamadı."
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
