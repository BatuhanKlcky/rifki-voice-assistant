"""
tools/browser.py
-----------------
Tarayıcı açma ve belirli URL/arama sayfalarını açma. Bu modül sadece
tarayıcıyı sistem varsayılan tarayıcısıyla açar; sayfa içeriğini okumaz
(bilgi arama/özetleme için tools/web.py kullanılır).
"""

import webbrowser
from urllib.parse import quote_plus
from core.logger import get_logger

log = get_logger("tools.browser")


def open_browser() -> str:
    try:
        webbrowser.open("https://www.google.com")
        return "Tarayıcı açılıyor."
    except Exception as e:
        log.error(f"Tarayıcı açma hatası: {e}")
        return "Tarayıcı açılırken bir sorun oluştu."


def open_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        webbrowser.open(url)
        log.info(f"URL açıldı: {url}")
        return f"{url} açılıyor."
    except Exception as e:
        log.error(f"URL açma hatası ({url}): {e}")
        return "Bu bağlantıyı açarken bir sorun oluştu."


def open_youtube_search(query: str) -> str:
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    return open_url(url)


def open_google_search(query: str) -> str:
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    return open_url(url)