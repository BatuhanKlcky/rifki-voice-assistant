"""
tools/media.py
---------------
Medya tuşları (oynat/duraklat, sonraki, önceki) — Windows sanal tuşları.
Spotify/YouTube doğrudan API yok; sistem medya oturumunu kontrol eder.
"""

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


def media_play_pause() -> str:
    try:
        _media_key(VK_MEDIA_PLAY_PAUSE)
        return "Medya: oynat / duraklat."
    except Exception as e:
        log.error(f"Medya play/pause: {e}")
        return "Medya kontrolü gönderilemedi."


def media_next() -> str:
    try:
        _media_key(VK_MEDIA_NEXT_TRACK)
        return "Medya: sonraki parça."
    except Exception as e:
        log.error(f"Medya next: {e}")
        return "Sonraki parça gönderilemedi."


def media_prev() -> str:
    try:
        _media_key(VK_MEDIA_PREV_TRACK)
        return "Medya: önceki parça."
    except Exception as e:
        log.error(f"Medya prev: {e}")
        return "Önceki parça gönderilemedi."


def media_stop() -> str:
    try:
        _media_key(VK_MEDIA_STOP)
        return "Medya: durdur."
    except Exception as e:
        log.error(f"Medya stop: {e}")
        return "Durdur gönderilemedi."


def play_media(query: str) -> str:
    log.info(f"play_media çağrıldı ama henüz desteklenmiyor: {query}")
    return (
        "Doğrudan müzik/video arama çalma henüz yok. "
        "Telefondaki medya tuşlarıyla oynat/duraklat kullanabilirsin "
        "veya YouTube'da aratabilirim."
    )
