"""
config/settings.py
-------------------
Tüm ortam değişkenlerini (.env) tek bir yerden okuyup uygulamaya sunar.
Hiçbir modül doğrudan os.environ okumamalı; hepsi buradan Settings kullanmalı.
"""

import os
import platform
import sys
from pathlib import Path
from dotenv import load_dotenv


def _app_dir() -> Path:
    """Kaynak kodda proje klasörü, exe'de ise RIFKI.exe'nin durduğu klasör."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _app_dir()
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


class Settings:
    # --- AI (Google Gemini) ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    # --- Ses ---
    WAKE_WORD: str = os.getenv("WAKE_WORD", "jarvis").lower()
    STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "tr-TR")
    # Uyandırma kelimesi ("Jarvis") İngilizce telaffuzlu bir kelime olduğu için,
    # Türkçe tanıma motoru bunu çoğu zaman yanlış anlıyor (ör. "Alo Care").
    # Bu yüzden SADECE wake-word aşamasında ayrı bir dil kullanılabilir;
    # normal komutlar yine STT_LANGUAGE (Türkçe) ile tanınmaya devam eder.
    WAKE_WORD_LANGUAGE: str = os.getenv("WAKE_WORD_LANGUAGE", "en-US")
    # TTS_ENGINE: "edge" (varsayılan, ücretsiz nöral ses, önerilen),
    # "piper" (tamamen yerel/offline, farklı sesler), "gtts" (Google, orta
    # kalite) veya "pyttsx3" (offline, robotik).
    TTS_ENGINE: str = os.getenv("TTS_ENGINE", "edge").lower()
    # "edge" motoru için ses seçimi. Kadın: tr-TR-EmelNeural (varsayılan).
    # Erkek: tr-TR-AhmetNeural. Diğer diller/sesler için:
    # `edge-tts --list-voices` komutuyla tüm listeyi görebilirsin.
    EDGE_TTS_VOICE: str = os.getenv("EDGE_TTS_VOICE", "tr-TR-EmelNeural")
    # "piper" motoru: tamamen ücretsiz, açık kaynak, YEREL (offline) çalışan
    # nöral TTS. Edge/gTTS'ten farklı bir ses sunar. Model dosyaları önceden
    # indirilmiş olmalı (bkz. README -> Piper kurulumu).
    # NOT: "fahrettin" ve "fettah" sesleri katkıda bulunanların talebiyle
    # depodan kaldırıldı (Eylül 2026 itibarıyla); şu an sadece "dfki" mevcut.
    PIPER_VOICE: str = os.getenv("PIPER_VOICE", "tr_TR-dfki-medium")
    PIPER_MODEL_DIR: Path = BASE_DIR / "voice" / "piper_models"

    # --- Log ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # --- Mobil köprü (telefon PWA) ---
    # Token boşsa köprü açılmaz. Dışarıdan erişim için Cloudflare Tunnel kullan.
    MOBILE_BRIDGE_ENABLED: bool = os.getenv("MOBILE_BRIDGE_ENABLED", "true").lower() in (
        "1", "true", "yes", "on",
    )
    # 0.0.0.0: aynı Wi‑Fi'deki telefon LAN ile bağlanabilsin (token zorunlu).
    MOBILE_BRIDGE_HOST: str = os.getenv("MOBILE_BRIDGE_HOST", "0.0.0.0")
    MOBILE_BRIDGE_PORT: int = int(os.getenv("MOBILE_BRIDGE_PORT", "8765"))
    MOBILE_BRIDGE_TOKEN: str = os.getenv("MOBILE_BRIDGE_TOKEN", "")

    # --- Yollar ---
    BASE_DIR: Path = BASE_DIR
    LOG_DIR: Path = BASE_DIR / "logs"
    DB_PATH: Path = BASE_DIR / "database" / "memory.db"

    # --- Platform ---
    IS_WINDOWS: bool = platform.system() == "Windows"

    @classmethod
    def validate(cls) -> list:
        """Eksik / hatalı ayarları döndürür. Boş liste = her şey tamam."""
        problems = []
        if not cls.GEMINI_API_KEY or cls.GEMINI_API_KEY.startswith("AIzaSyXXXX"):
            problems.append(
                "GEMINI_API_KEY tanımlı değil. .env dosyasına gerçek bir "
                "Google Gemini API anahtarı girmelisin (https://aistudio.google.com/apikey)."
            )
        if not cls.IS_WINDOWS:
            problems.append(
                "Bu sistem Windows'a göre optimize edildi. Şu an Windows dışında "
                "bir işletim sisteminde çalışıyorsun; uygulama açma, ses seviyesi "
                "ve bildirim modülleri sınırlı/çalışmayabilir."
            )
        return problems


settings = Settings()
