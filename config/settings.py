"""
config/settings.py
-------------------
Tüm ortam değişkenlerini (.env) tek bir yerden okuyup uygulamaya sunar.
Hiçbir modül doğrudan os.environ okumamalı; hepsi buradan Settings kullanmalı.
"""

import os
import platform
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
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
