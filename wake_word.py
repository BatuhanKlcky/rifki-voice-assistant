"""
voice/wake_word.py
-------------------
"Jarvis" uyandırma kelimesini algılar.

DÜRÜST NOT (mimari tercih): Gerçek, düşük gecikmeli, sürekli-dinleyen bir
wake-word motoru (ör. Picovoice Porcupine) offline çalışır ve çok az CPU
harcar. Bu MVP'de böyle özel bir motor YOK; bunun yerine mevcut STT
(Google recognizer) ile kısa ses parçaları sürekli dinlenip metne çevrilir
ve içinde WAKE_WORD var mı diye bakılır.

Bunun dezavantajı: internet bağlantısı gerektirir ve gerçek wake-word
motorlarına göre biraz daha yüksek gecikme/CPU kullanımı olur. Avantajı:
ek bir API anahtarı/ücretli servis gerektirmeden hemen çalışır.

İleride performans kritikse: bu dosyayı Porcupine ile değiştirmen,
sistemin geri kalanını (main.py, core/ai.py) HİÇ etkilemez — sadece
`wait_for_wake_word()` fonksiyonunun içini değiştirmen yeterli.
"""

import speech_recognition as sr

from config.settings import settings
from core.logger import get_logger

log = get_logger("voice.wake_word")

_recognizer = sr.Recognizer()


def wait_for_wake_word(stop_flag_check=lambda: False) -> bool:
    """
    Uyandırma kelimesi duyulana kadar bloklar. stop_flag_check() True
    dönerse döngüden çıkar (UI'dan "dinlemeyi durdur" gibi bir kontrol
    için kullanılabilir). Uyandırma kelimesi duyulursa True döner.
    """
    try:
        with sr.Microphone() as source:
            log.info(f"Wake-word dinleme başladı. Kullanılan mikrofon: {source.device_index}")
            _recognizer.adjust_for_ambient_noise(source, duration=0.4)
            while not stop_flag_check():
                try:
                    audio = _recognizer.listen(source, timeout=3, phrase_time_limit=4)
                except sr.WaitTimeoutError:
                    log.debug("Wake-word: 3 saniyede ses algılanmadı (sessizlik).")
                    continue

                try:
                    text = _recognizer.recognize_google(audio, language=settings.STT_LANGUAGE)
                except sr.UnknownValueError:
                    # TEŞHİS AMAÇLI: ses geldi ama hiçbir kelimeye çözülemedi.
                    log.info("Wake-word: ses algılandı ama metne çevrilemedi (UnknownValueError).")
                    continue
                except sr.RequestError as e:
                    log.error(f"Wake-word: STT servis hatası: {e}")
                    continue

                # TEŞHİS AMAÇLI: algılanan HER metni logla (wake word olsun olmasın).
                log.info(f"Wake-word: algılanan metin = '{text}'")

                if settings.WAKE_WORD in text.lower():
                    log.info(f"Wake word algılandı: {text}")
                    return True
    except OSError as e:
        log.error(f"Mikrofon erişim hatası (wake word): {e}")
        raise

    return False
