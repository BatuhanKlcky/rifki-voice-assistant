"""
tools/media.py
---------------
DURUM: Bu modül Faz 2 kapsamındadır ve MVP'de TAM ÇALIŞMAZ.

Neden: "Müzik/video oynatma" isteği çok belirsiz bir kapsam (Spotify API,
YouTube, yerel dosya, vs. hepsi farklı entegrasyon gerektirir). Sahte bir
"çalıyor" mesajı basıp hiçbir şey yapmamak yerine, burada NET bir şekilde
henüz uygulanmadığını belirtip kullanıcıyı yönlendiriyoruz.

İleride ekleyebileceklerin:
- Spotify: spotipy kütüphanesi + Spotify Web API (OAuth gerekir)
- Yerel dosya: yalnızca varsayılan uygulamayla açmak (tools/filesystem.open_path)
- YouTube: tools/browser.open_youtube_search zaten çalışıyor (arama açar, oynatmaz)
"""

from core.logger import get_logger

log = get_logger("tools.media")


def play_media(query: str) -> str:
    log.info(f"play_media çağrıldı ama henüz desteklenmiyor: {query}")
    return (
        "Doğrudan müzik/video çalma özelliği henüz eklenmedi (Faz 2). "
        "Bunun yerine YouTube'da arayabilirim, ister misin?"
    )
