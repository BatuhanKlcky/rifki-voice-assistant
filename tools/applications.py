"""
tools/applications.py
----------------------
Yüklü uygulamaları adıyla açar ve kapatır.

Kaynaklar:
- Başlat menüsü ve masaüstü .lnk kısayolları
- Windows'un Get-StartApps listesi (mağaza uygulamaları dahil)
- Sık söylenen Türkçe adlar için küçük bir takma ad tablosu

Kullanıcının cümlesi kabuğa verilmez. Yalnızca bu katalogda bulunan bir
kısayol veya uygulama kimliği başlatılır.
"""

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import psutil

from config.settings import settings
from core.logger import get_logger

log = get_logger("tools.applications")

_CATALOG_TTL_SECONDS = 10 * 60
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Konuşma dilindeki ad -> katalogda aranacak ek adlar
_SPOKEN_ALIASES = {
    "not defteri": ("notepad",),
    "hesap makinesi": ("calculator", "calc"),
    "hesap makinası": ("calculator", "calc"),
    "dosya gezgini": ("file explorer", "explorer"),
    "gezgin": ("file explorer", "explorer"),
    "tarayici": ("google chrome", "chrome", "microsoft edge"),
    "tarayıcı": ("google chrome", "chrome", "microsoft edge"),
    "notepad": ("not defteri",),
    "chrome": ("google chrome",),
    "krom": ("google chrome", "chrome"),
    "calculator": ("hesap makinesi",),
    "calc": ("hesap makinesi", "calculator"),
    "ayarlar": ("settings",),
    "gorev yoneticisi": ("task manager",),
    "görev yöneticisi": ("task manager",),
    "kod": ("visual studio code", "code"),
    "vscode": ("visual studio code", "code"),
}

# Eski sabit liste: katalogda olmasa da PATH'teki tek kelimelik programlar.
_DIRECT_COMMANDS = {
    "notepad": "notepad",
    "calc": "calc",
    "calculator": "calc",
    "mspaint": "mspaint",
    "paint": "mspaint",
    "explorer": "explorer",
    "cmd": "cmd",
    "powershell": "powershell",
}

# Kabuğu veya oturumu düşüren işlemler kapatılmaz.
_PROTECTED_PROCESSES = {
    "explorer.exe",
    "csrss.exe",
    "winlogon.exe",
    "lsass.exe",
    "services.exe",
    "svchost.exe",
    "smss.exe",
    "dwm.exe",
    "wininit.exe",
    "system",
    "registry",
    "secure system",
}

_catalog_cache = None
_catalog_loaded_at = 0.0


@dataclass(frozen=True)
class AppEntry:
    name: str
    folded: str
    kind: str  # "lnk" veya "app"
    launch: str  # kısayol yolu veya AppID


def fold(text: str) -> str:
    """Türkçe karakterleri ve noktalamayı sadeleştirip karşılaştırılabilir hale getirir."""
    value = (text or "").casefold().replace("\u0307", "")
    value = value.translate(str.maketrans({
        "ı": "i",
        "ğ": "g",
        "ü": "u",
        "ş": "s",
        "ö": "o",
        "ç": "c",
    }))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _score(query: str, name: str) -> int:
    if not query or not name:
        return 0
    if query == name:
        return 100
    query_tokens = query.split()
    name_tokens = name.split()
    if query_tokens == name_tokens:
        return 100
    if all(token in name_tokens for token in query_tokens):
        extra = len(name_tokens) - len(query_tokens)
        if name_tokens[-len(query_tokens):] == query_tokens:
            return 94
        if name_tokens[:len(query_tokens)] == query_tokens:
            return max(50, 82 - extra * 8)
        return max(50, 76 - extra * 6)
    ratio = SequenceMatcher(None, query, name).ratio()
    scale = 50 if abs(len(query) - len(name)) > len(query) + 2 else 68
    return int(ratio * scale)


def _penalty(query: str, name: str) -> int:
    noisy = ("uninstall", "unins", "kaldir", "kaldır")
    folded_name = fold(name)
    if any(word in folded_name for word in ("uninstall", "unins", "kaldir")) and not any(
        word in query for word in noisy
    ):
        return 30
    return 0


def match_entries(query: str, entries: list):
    """En iyi eşleşmeyi veya birbirine yakın adayları döndürür."""
    folded_query = fold(query)
    if not folded_query:
        return None, []

    candidates = [folded_query]
    for key, aliases in _SPOKEN_ALIASES.items():
        if fold(key) != folded_query:
            continue
        for alias in aliases:
            folded_alias = fold(alias)
            if folded_alias and folded_alias not in candidates:
                candidates.append(folded_alias)

    ranked = []
    for entry in entries:
        best = 0
        for candidate in candidates:
            best = max(best, _score(candidate, entry.folded) - _penalty(candidate, entry.name))
        if best > 0:
            ranked.append((best, 1 if entry.kind == "lnk" else 0, entry))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if not ranked or ranked[0][0] < 80:
        close = [entry.name for score, _kind, entry in ranked if score >= 62][:3]
        return None, close

    winner_score, _kind, winner = ranked[0]
    if len(folded_query) < 3 and winner_score < 100:
        close = [entry.name for _score_value, _kind, entry in ranked[:4]]
        return None, close
    if winner_score >= 100:
        return winner, []

    rivals = [
        entry.name
        for score, _kind, entry in ranked[1:4]
        if winner_score - score <= 8 and entry.name != winner.name
    ]
    if rivals and winner_score < 88:
        return None, [winner.name, *rivals]
    return winner, []


def _shortcut_roots():
    roots = []
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")
    if appdata:
        roots.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    if programdata:
        roots.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    home = Path.home()
    roots.append(home / "Desktop")
    roots.append(home / "OneDrive" / "Desktop")
    public = os.environ.get("PUBLIC")
    if public:
        roots.append(Path(public) / "Desktop")
    return roots


def _lnk_entries():
    seen = set()
    for root in _shortcut_roots():
        if not root.is_dir():
            continue
        for path in root.rglob("*.lnk"):
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            yield AppEntry(path.stem, fold(path.stem), "lnk", resolved)


def _start_app_entries():
    script = (
        "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
        "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            timeout=25,
            creationflags=_NO_WINDOW,
            check=False,
        )
    except Exception as e:
        log.warning(f"Başlat menüsü uygulamaları okunamadı: {e}")
        return

    raw = completed.stdout.decode("utf-8", errors="replace").strip()
    if not raw:
        log.warning(f"Get-StartApps boş döndü: {completed.stderr.decode('utf-8', errors='replace')[:200]}")
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning(f"Get-StartApps JSON okunamadı: {e}")
        return
    if isinstance(data, dict):
        data = [data]
    for item in data or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("Name") or "").strip()
        app_id = str(item.get("AppID") or "").strip()
        if name and app_id:
            yield AppEntry(name, fold(name), "app", app_id)


def load_catalog(force: bool = False) -> list:
    global _catalog_cache, _catalog_loaded_at
    now = time.monotonic()
    if not force and _catalog_cache is not None and now - _catalog_loaded_at < _CATALOG_TTL_SECONDS:
        return _catalog_cache

    entries = list(_lnk_entries())
    entries.extend(_start_app_entries())
    _catalog_cache = entries
    _catalog_loaded_at = now
    log.info(f"Uygulama kataloğu yüklendi: {len(entries)} kayıt")
    return entries


def _resolve(name: str):
    return match_entries(name, load_catalog())


def _launch(entry: AppEntry) -> None:
    if entry.kind == "lnk":
        os.startfile(entry.launch)  # noqa: S606 — katalogdaki kısayol, kullanıcı metni değil
        return
    subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{entry.launch}"], shell=False)


def _alias_targets(folded_query: str):
    targets = []
    for key, aliases in _SPOKEN_ALIASES.items():
        if fold(key) == folded_query:
            targets.extend(aliases)
    return targets


def _direct_command(name: str):
    key = fold(name)
    command = _DIRECT_COMMANDS.get(key) or _DIRECT_COMMANDS.get(name.strip().lower())
    if not command or not re.fullmatch(r"[A-Za-z0-9._-]+", command):
        return None
    return command


def _executable_on_path(name: str):
    """Katalogda yoksa, tek kelimelik ve PATH'te duran bir programı döndürür."""
    tokens = []
    command = _direct_command(name)
    if command:
        tokens.append(command)
    folded = fold(name)
    if folded and " " not in folded:
        tokens.append(folded)
    for alias in _alias_targets(folded):
        alias_folded = fold(alias)
        if alias_folded and " " not in alias_folded:
            tokens.append(alias_folded)
    seen = set()
    for token in tokens:
        if token in seen or not re.fullmatch(r"[A-Za-z0-9._-]+", token):
            continue
        seen.add(token)
        found = shutil.which(token)
        if found:
            return found
    return None


def list_applications(query: str = "", limit: int = 400) -> list[dict]:
    """Mobil / API için uygulama kataloğunu (benzersiz adlar) döndürür."""
    q = fold(query or "")
    seen: set[str] = set()
    out: list[dict] = []
    for entry in load_catalog():
        key = entry.folded
        if key in seen:
            continue
        if q:
            tokens = q.split()
            if q not in key and not key.startswith(q) and not all(tok in key for tok in tokens):
                continue
        seen.add(key)
        out.append({"name": entry.name, "kind": entry.kind})
    out.sort(key=lambda row: fold(row["name"]))
    cap = max(1, min(int(limit or 400), 800))
    return out[:cap]


def open_application(name: str) -> str:
    """Yüklü bir uygulamayı adına göre açar."""
    cleaned = (name or "").strip()
    if not cleaned:
        return "Hangi uygulamayı açacağımı söylemen gerekiyor."
    if not settings.IS_WINDOWS:
        return "Uygulama açma özelliği şu an sadece Windows'ta çalışacak şekilde tasarlandı."

    entry, alternatives = _resolve(cleaned)
    if entry is None and alternatives:
        listed = ", ".join(alternatives[:4])
        return f"Birkaç uygulama buldum: {listed}. Hangisini açayım?"
    if entry is not None:
        try:
            _launch(entry)
            log.info(f"Uygulama açıldı: {cleaned} -> {entry.name} ({entry.kind})")
            return f"{entry.name} açılıyor."
        except Exception as e:
            log.error(f"Uygulama açma hatası ({entry.name}): {e}")
            return f"{entry.name} açılırken bir sorun oluştu."

    command = _executable_on_path(cleaned)
    if command is None:
        return f"'{cleaned}' adlı yüklü bir uygulama bulamadım."
    try:
        subprocess.Popen([command], shell=False)
        log.info(f"PATH üzerinden açıldı: {cleaned} -> {command}")
        return f"{cleaned} açılıyor."
    except Exception as e:
        log.error(f"Doğrudan açma hatası ({cleaned}): {e}")
        return f"'{cleaned}' adlı yüklü bir uygulama bulamadım."


def _shortcut_exe(path: str) -> str:
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        target = shell.CreateShortCut(path).Targetpath or ""
    except Exception as e:
        log.warning(f"Kısayol hedefi okunamadı ({path}): {e}")
        return ""
    exe = Path(target).name
    if not exe or exe.lower() in _PROTECTED_PROCESSES:
        return ""
    return exe


def _process_names_for(query: str, entry: AppEntry | None) -> set:
    names = set()
    folded_query = fold(query)
    if folded_query and " " not in folded_query and re.fullmatch(r"[a-z0-9._-]+", folded_query):
        if folded_query not in {"exe", "app"}:
            names.add(f"{folded_query}.exe")
    if entry and entry.kind == "lnk":
        exe = _shortcut_exe(entry.launch)
        if exe:
            names.add(exe)
    return {name for name in names if name.lower() not in _PROTECTED_PROCESSES}


def close_application(name: str) -> str:
    """Çalışan bir uygulamayı, çözülen program adına göre kapatır."""
    cleaned = (name or "").strip()
    if not cleaned:
        return "Hangi uygulamayı kapatacağımı söylemen gerekiyor."

    entry, alternatives = _resolve(cleaned)
    if entry is None and alternatives:
        listed = ", ".join(alternatives[:4])
        return f"Birkaç uygulama buldum: {listed}. Hangisini kapatayım?"

    targets = {item.lower() for item in _process_names_for(cleaned, entry)}
    if not targets:
        return f"'{cleaned}' için kapatılacak çalışan bir program bulamadım."

    closed = False
    try:
        for proc in psutil.process_iter(["name"]):
            proc_name = (proc.info.get("name") or "").lower()
            if proc_name in targets:
                proc.terminate()
                closed = True
        label = entry.name if entry is not None else cleaned
        log.info(f"Uygulama kapatma denendi: {label} hedefler={targets} sonuç={closed}")
        if closed:
            return f"{label} kapatıldı."
        return f"{label} zaten çalışmıyor gibi görünüyor."
    except Exception as e:
        log.error(f"Uygulama kapatma hatası ({cleaned}): {e}")
        return f"{cleaned} kapatılırken bir sorun oluştu."
