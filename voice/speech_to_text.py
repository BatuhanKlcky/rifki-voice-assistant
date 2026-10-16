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
_recognizer.pause_threshold = 0.8
_recognizer.non_speaking_duration = 0.4
_recognizer.energy_threshold = 200
_recognizer.dynamic_energy_threshold = True
_calibrated = False


def listen_and_transcribe(timeout: int = 5, phrase_time_limit: int = 20) -> str:
    """
    Mikrofondan bir cümle dinler ve metne çevirir.
    Başarısız olursa boş string döner (çağıran taraf bunu "anlaşılamadı" sayar).
    """
    try:
        with sr.Microphone() as source:
            global _calibrated
            if not _calibrated:
                _recognizer.adjust_for_ambient_noise(source, duration=0.3)
                if _recognizer.energy_threshold > 400:
                    _recognizer.energy_threshold = 250
                _calibrated = True
            log.info("Komut dinleniyor...")
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
        log.info("Komut: ses algılandı ama metne çevrilemedi.")
        return ""
    except sr.RequestError as e:
        log.error(f"STT servis hatası: {e}")
        raise SpeechServiceError("Konuşma tanıma servisine ulaşılamıyor.") from e


class MicrophoneError(Exception):
    pass


class SpeechServiceError(Exception):
    pass