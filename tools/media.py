"""
tools/media.py
---------------
Medya kontrolleri ve YouTube Music entegrasyonu.
Windows sanal medya tuşları + YouTube Music doğrudan parça/arama çalma.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
import webbrowser

from core.logger import get_logger

log = get_logger("tools.media")

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _media_key(vk: int) -> None:
    import ctypes
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


def media_play_pause(*args, **kwargs) -> str:
    try:
        _media_key(VK_MEDIA_PLAY_PAUSE)
        return "Medya: oynat / duraklat."
    except Exception as e:
        log.error(f"Medya play/pause hatası: {e}")
        return "Medya kontrolü gönderilemedi."


def media_next(*args, **kwargs) -> str:
    try:
        _media_key(VK_MEDIA_NEXT_TRACK)
        return "Medya: sonraki parça."
    except Exception as e:
        log.error(f"Medya next hatası: {e}")
        return "Sonraki parça gönderilemedi."


def media_prev(*args, **kwargs) -> str:
    try:
        _media_key(VK_MEDIA_PREV_TRACK)
        return "Medya: önceki parça."
    except Exception as e:
        log.error(f"Medya prev hatası: {e}")
        return "Önceki parça gönderilemedi."


def media_stop(*args, **kwargs) -> str:
    try:
        _media_key(VK_MEDIA_STOP)
        return "Medya: durdur."
    except Exception as e:
        log.error(f"Medya stop hatası: {e}")
        return "Durdur gönderilemedi."


def play_youtube_music(query: str, *args, **kwargs) -> str:
    """
    YouTube Music üzerinde arama yapar ve ilk bulunan şarkıyı doğrudan başlatır.
    """
    cleaned = (query or "").strip()
    if not cleaned:
        cleaned = "lo-fi chill beats"

    target_url = None
    try:
        # YouTube üzerinden en iyi video/parça ID'sini çek
        search_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(cleaned)}"
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            html_text = resp.read().decode("utf-8", errors="ignore")

        # videoId eşleşmesi
        matches = re.findall(r'\"videoId\":\"([a-zA-Z0-9_-]{11})\"', html_text)
        if matches:
            vid = matches[0]
            target_url = f"https://music.youtube.com/watch?v={vid}"
            log.info(f"YouTube Music parçası bulundu: {vid} (sorgu: '{cleaned}')")
    except Exception as e:
        log.warning(f"YouTube Music parça arama hatası, aramaya düşülüyor: {e}")

    if not target_url:
        target_url = f"https://music.youtube.com/search?q={urllib.parse.quote_plus(cleaned)}"

    try:
        webbrowser.open(target_url, new=2)
        return f"YouTube Music'te '{cleaned}' açılıyor."
    except Exception as e:
        log.error(f"YouTube Music tarayıcı hatası: {e}")
        return "YouTube Music açılamadı."


def play_media(query: str, *args, **kwargs) -> str:
    """Müzik çalma isteğini doğrudan YouTube Music motoruna yönlendirir."""
    return play_youtube_music(query, *args, **kwargs)
