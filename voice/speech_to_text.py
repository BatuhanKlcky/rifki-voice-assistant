"""
voice/speech_to_text.py
------------------------
RIFKI'nın mikrofon üzerinden Türkçe konuşmayı metne çevirmesini sağlar.

Kullanılan kütüphane: SpeechRecognition (mikrofon + ses yakalama) +
Google Web Speech API (recognizer.recognize_google, dil="tr-TR").

DÜRÜST NOT: recognize_google, Google'ın ücretsiz/anahtar gerektirmeyen
web servisini kullanır; internet bağlantısı gerektirir ve resmi/production
kullanım için garanti edilmez. Daha kurumsal bir çözüm istersen ileride
Google Cloud Speech-to-Text (API anahtarlı) veya OpenAI Whisper (yerel,
offline) ile değiştirebilirsin — kod bu değişikliğe izin verecek şekilde
tek bir fonksiyon (listen_and_transcribe) arkasında izole edildi.
"""

import speech_recognition as sr

from config.settings import settings
from core.logger import get_logger

log = get_logger("voice.stt")

_recognizer = sr.Recognizer()


def listen_and_transcribe(timeout: int = 5, phrase_time_limit: int = 10) -> str:
    """
    Mikrofondan bir cümle dinler ve metne çevirir.
    Başarısız olursa boş string döner (çağıran taraf bunu "anlaşılamadı" sayar).
    """
    try:
        with sr.Microphone() as source:
            _recognizer.adjust_for_ambient_noise(source, duration=0.4)
            log.debug("Dinleniyor...")
            audio = _recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
    except sr.WaitTimeoutError:
        return ""
    except OSError as e:
        log.error(f"Mikrofon erişim hatası: {e}")
        raise MicrophoneError("Mikrofon erişiminde bir sorun oluştu.") from e

    try:
        text = _recognizer.recognize_google(audio, language=settings.STT_LANGUAGE)
        log.info(f"Algılanan konuşma: {text}")
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        log.error(f"STT servis hatası: {e}")
        raise SpeechServiceError("Konuşma tanıma servisine ulaşılamıyor.") from e


class MicrophoneError(Exception):
    pass


class SpeechServiceError(Exception):
    pass