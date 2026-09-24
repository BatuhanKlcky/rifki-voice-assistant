"""
main.py
-------
JARVIS uygulamasının giriş noktası.

Açılışta:
1) Ayarları doğrular (.env kontrolü) ve eksikleri konsola/loga yazar.
2) Bileşen kontrol listesini gösterir (AI bağlantısı, mikrofon, hafıza vb.).
3) PyQt5 arayüzünü başlatır.

Not: Bileşen kontrolleri "en iyi çaba" (best-effort) niteliğindedir; ör.
mikrofon kontrolü gerçek bir donanım testidir ama internet/AI kontrolü
sadece ayarların dolu olup olmadığına bakar (gerçek bir API çağrısı
başlangıçta YAPILMAZ, çünkü bu gereksiz bir maliyet/gecikme olur).
"""

import sys

from config.settings import settings
from core.logger import get_logger
from core.memory import long_term_memory  # noqa: F401 (DB init tetiklenir)

log = get_logger("main")


def print_startup_banner():
    print("=" * 50)
    print("  JARVIS başlatılıyor...")
    print("=" * 50)


def run_component_checks():
    checks = []

    # AI bağlantısı (sadece ayar kontrolü, gerçek network çağrısı yok)
    if settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("AIzaSyXXXX"):
        checks.append(("Yapay zekâ bağlantısı (Gemini API anahtarı)", True))
    else:
        checks.append(("Yapay zekâ bağlantısı (Gemini API anahtarı)", False))

    # Mikrofon
    try:
        import speech_recognition as sr

        mic_list = sr.Microphone.list_microphone_names()
        checks.append(("Mikrofon", len(mic_list) > 0))
    except Exception as e:
        log.error(f"Mikrofon kontrolü hatası: {e}")
        checks.append(("Mikrofon", False))

    # Ses sistemi (TTS motoru importlanabiliyor mu)
    try:
        if settings.TTS_ENGINE == "pyttsx3":
            import pyttsx3  # noqa: F401
        elif settings.TTS_ENGINE == "gtts":
            import gtts  # noqa: F401
            import playsound  # noqa: F401
        else:
            import edge_tts  # noqa: F401
            import playsound  # noqa: F401
        checks.append(("Ses sistemi", True))
    except Exception as e:
        log.error(f"Ses sistemi kontrolü hatası: {e}")
        checks.append(("Ses sistemi", False))

    # Hafıza (DB dosyası oluşturulabiliyor mu)
    checks.append(("Hafıza", settings.DB_PATH.parent.exists()))

    # Tool sistemi
    try:
        from core.router import TOOL_DISPATCH

        checks.append(("Tool sistemi", len(TOOL_DISPATCH) > 0))
    except Exception as e:
        log.error(f"Tool sistemi kontrolü hatası: {e}")
        checks.append(("Tool sistemi", False))

    # İnternet bağlantısı
    try:
        import socket

        socket.create_connection(("8.8.8.8", 53), timeout=2)
        checks.append(("İnternet bağlantısı", True))
    except Exception:
        checks.append(("İnternet bağlantısı", False))

    for name, ok in checks:
        symbol = "✓" if ok else "✗"
        print(f"  {symbol} {name}")

    return all(ok for _, ok in checks)


def main():
    print_startup_banner()

    problems = settings.validate()
    for p in problems:
        print(f"[UYARI] {p}")

    all_ok = run_component_checks()
    if all_ok:
        print("\nJARVIS çevrimiçi. Size nasıl yardımcı olabilirim?\n")
    else:
        print(
            "\nJARVIS bazı eksik bileşenlerle başlatılıyor. "
            "Yukarıdaki ✗ işaretli maddeleri .env / requirements.txt "
            "üzerinden tamamlayabilirsin.\n"
        )

    from ui.main_window import run_app

    run_app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        log.exception(f"Beklenmeyen başlangıç hatası: {e}")
        print(f"[KRİTİK HATA] JARVIS başlatılamadı: {e}")
        sys.exit(1)
