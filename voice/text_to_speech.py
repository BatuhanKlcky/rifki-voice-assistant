"""
voice/text_to_speech.py
-------------------------
RIFKI'in Türkçe sesli yanıt vermesini sağlar. Dört motor desteklenir
(TTS_ENGINE ayarıyla seçilir):

- "edge"    : Microsoft Edge'in ücretsiz nöral (neural) sesleri
              (edge-tts kütüphanesi). API anahtarı GEREKMEZ, internet
              gerektirir. Türkçe'de sadece 2 ses vardır: Emel (kadın),
              Ahmet (erkek).
- "piper"   : Tamamen ücretsiz, açık kaynak, YEREL (offline) çalışan nöral
              TTS motoru. İnternet GEREKMEZ (ilk model indirmesi hariç),
              kota/limit yoktur. Edge'den farklı 3 Türkçe erkek sesi sunar
              (fahrettin, fettah, dfki). Kullanmadan önce model dosyalarını
              indirmen gerekir — bkz. README -> "Piper kurulumu".
- "gtts"    : Google Text-to-Speech (internet gerektirir, orta kalite).
- "pyttsx3" : Tamamen offline çalışan sistem TTS motoru (SAPI5/Windows).
              Türkçe ses kalitesi işletim sistemine kurulu Türkçe sese
              bağlıdır; bazı Windows kurulumlarında Türkçe ses paketi
              yüklü olmayabilir — bu durumda İngilizce aksanla okuyabilir.
              Bu, kütüphanenin değil işletim sisteminin bir sınırlamasıdır.
"""

import os
import tempfile
import time
import wave

from config.settings import settings
from core.logger import get_logger

log = get_logger("voice.tts")

_piper_voice_cache = None  # PiperVoice nesnesini bir kez yükleyip önbelleğe alır


def _get_piper_voice():
    """Piper ses modelini (ilk çağrıda) yükler ve önbelleğe alır."""
    global _piper_voice_cache
    if _piper_voice_cache is not None:
        return _piper_voice_cache

    from piper import PiperVoice

    model_path = settings.PIPER_MODEL_DIR / f"{settings.PIPER_VOICE}.onnx"
    config_path = settings.PIPER_MODEL_DIR / f"{settings.PIPER_VOICE}.onnx.json"

    if not model_path.exists() or not config_path.exists():
        raise FileNotFoundError(
            f"Piper ses modeli bulunamadı: {model_path}\n"
            f"Önce şu komutu çalıştırman gerekiyor:\n"
            f"python -m piper.download_voices {settings.PIPER_VOICE} "
            f"--download-dir \"{settings.PIPER_MODEL_DIR}\""
        )

    _piper_voice_cache = PiperVoice.load(str(model_path), str(config_path))
    return _piper_voice_cache


def _speak_piper(text: str):
    from playsound import playsound

    voice = _get_piper_voice()
    tmp_path = os.path.join(tempfile.gettempdir(), f"rifki_tts_{int(time.time()*1000)}.wav")
    try:
        with wave.open(tmp_path, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
        playsound(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _speak_edge(text: str):
    import asyncio
    import edge_tts
    from playsound import playsound

    tmp_path = os.path.join(tempfile.gettempdir(), f"rifki_tts_{int(time.time()*1000)}.mp3")

    async def _generate():
        communicate = edge_tts.Communicate(text, settings.EDGE_TTS_VOICE)
        await communicate.save(tmp_path)

    try:
        asyncio.run(_generate())
        playsound(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _speak_gtts(text: str):
    from gtts import gTTS
    from playsound import playsound

    tmp_path = os.path.join(tempfile.gettempdir(), f"rifki_tts_{int(time.time()*1000)}.mp3")
    try:
        gTTS(text=text, lang="tr").save(tmp_path)
        playsound(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _speak_pyttsx3(text: str):
    import pyttsx3

    engine = pyttsx3.init()
    # Mümkünse Türkçe bir ses seç
    for voice in engine.getProperty("voices"):
        if "tr" in (voice.id or "").lower() or "turkish" in (voice.name or "").lower():
            engine.setProperty("voice", voice.id)
            break
    engine.say(text)
    engine.runAndWait()


def speak(text: str):
    if not text:
        return
    try:
        if settings.TTS_ENGINE == "pyttsx3":
            _speak_pyttsx3(text)
        elif settings.TTS_ENGINE == "gtts":
            _speak_gtts(text)
        elif settings.TTS_ENGINE == "piper":
            _speak_piper(text)
        else:
            _speak_edge(text)
    except FileNotFoundError as e:
        log.error(f"Piper model dosyası eksik: {e}")
        print(f"[RIFKI - Piper model eksik]: {e}")
    except Exception as e:
        log.error(f"TTS hatası ({settings.TTS_ENGINE}): {e}")
        # Sessiz başarısızlık yerine en azından konsola yaz:
        print(f"[Rıfkı - sesli okunamadı]: {text}")