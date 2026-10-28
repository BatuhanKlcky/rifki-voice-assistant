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

ÖNEMLİ (Windows + Piper): onnxruntime'ın native DLL'i, bir QThread içinde
İLK kez import edildiğinde Windows'ta "access violation" ile çöküyor (native
başlatma thread-context'e duyarlı). Bu yüzden preload_piper() fonksiyonu
main.py'de, herhangi bir arka plan thread'i başlamadan ÖNCE, ana thread'den
çağrılmalıdır. Bu, onnxruntime'ı sys.modules'a güvenle önceden yükler;
sonrasında VoiceWorker içindeki speak() çağrıları zaten önbellekteki
kopyayı kullanır ve tekrar native init tetiklenmez.
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


def preload_piper():
    """Piper/onnxruntime'ı ANA thread'de önceden yükler. Bu import bir
    QThread içinde ilk kez yapılırsa Windows'ta onnxruntime'ın native DLL'i
    access violation ile çöküyor (thread-context'e duyarlı native init).
    Bu fonksiyon main.py'de, VoiceWorker başlamadan ÖNCE çağrılmalı."""
    if settings.TTS_ENGINE == "piper":
        try:
            _get_piper_voice()
            log.info("Piper ses modeli ana thread'de önceden yüklendi.")
        except Exception as e:
            log.error(f"Piper ön yükleme hatası: {e}")


def _play_wav_windows(path: str):
    """Windows'ta winsound ile çalar; playsound'un dosya kilitleme
    sorunlarına (WinError 32) takılmaz, çalma bitince dosyayı serbest bırakır."""
    import winsound
    winsound.PlaySound(path, winsound.SND_FILENAME)


def _speak_piper(text: str):
    voice = _get_piper_voice()
    tmp_path = os.path.join(tempfile.gettempdir(), f"rifki_tts_{int(time.time()*1000)}.wav")
    try:
        with wave.open(tmp_path, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)

        if settings.IS_WINDOWS:
            _play_wav_windows(tmp_path)
        else:
            from playsound import playsound
            playsound(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except PermissionError:
                # Dosya hâlâ kilitliyse sessizce geç; bir sonraki çağrıda
                # farklı zaman damgalı yeni bir dosya oluşturulacağı için sorun olmaz.
                pass


def _play_mp3_windows(path: str):
    """MP3 dosyaları winsound ile doğrudan çalınamaz (yalnızca WAV destekler),
    bu yüzden MCI komutlarıyla çalıp kapatıyoruz."""
    import ctypes
    alias = "rifki_tts_mp3"
    ctypes.windll.winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
    ctypes.windll.winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
    ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, None)


def _speak_edge(text: str):
    import asyncio
    import edge_tts

    tmp_path = os.path.join(tempfile.gettempdir(), f"rifki_tts_{int(time.time()*1000)}.mp3")

    async def _generate():
        communicate = edge_tts.Communicate(text, settings.EDGE_TTS_VOICE)
        await communicate.save(tmp_path)

    try:
        asyncio.run(_generate())
        if settings.IS_WINDOWS:
            _play_mp3_windows(tmp_path)
        else:
            from playsound import playsound
            playsound(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except PermissionError:
                pass


def _speak_gtts(text: str):
    from gtts import gTTS

    tmp_path = os.path.join(tempfile.gettempdir(), f"rifki_tts_{int(time.time()*1000)}.mp3")
    try:
        gTTS(text=text, lang="tr").save(tmp_path)
        if settings.IS_WINDOWS:
            _play_mp3_windows(tmp_path)
        else:
            from playsound import playsound
            playsound(tmp_path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except PermissionError:
                pass


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


def clean_text_for_speech(text: str) -> str:
    """Metindeki markdown sembollerini (*, #, _, vb.), kod bloklarını ve
    gereksiz teknik işaretleri temizleyerek TTS'in akıcı, doğal Türkçe okumasını sağlar."""
    import re
    if not text:
        return ""
    # 1. Kod bloklarını ve teknik etiketleri kaldır
    text = re.sub(r"```[\s\S]*?```", " kod bloğu ", text)
    text = re.sub(r"`([^`]+)`", r"", text)
    # 2. Markdown linklerini temizle: [Başlık](http://...) -> Başlık
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"", text)
    # 3. Kalın ve italik işaretlerini kaldır: **metin**, *metin*, __metin__, _metin_
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"", text)
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"", text)
    # Kalan tekil veya çift yıldız/alt çizgileri tamamen sil
    text = text.replace("*", "").replace("_", "")
    # 4. Başlıkları temizle: ### Başlık -> Başlık
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    # 5. Liste ve madde işaretlerini temizle: - madde, + madde, 1. madde
    text = re.sub(r"^\s*[-+•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s*", "", text, flags=re.MULTILINE)
    # 6. Parantez içi teknik işaretleri ve gereksiz sembolleri temizle
    text = re.sub(r"[#~|><\[\]{}^@/\=]+", " ", text)
    # 7. Emojileri temizle
    text = re.sub(r"[𐀀-􏿿]", "", text)
    # 8. Boşlukları ve noktalama işaretlerini düzelt
    text = re.sub(r"\s+", " ", text).strip()
    return text


def speak(text: str):
    if not text:
        return
    text = clean_text_for_speech(text)
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

def synthesize_wav_bytes(text: str) -> bytes:
    """Metni yerel Piper veya gTTS ile WAV baytlarına dönüştürür (mobil yayın)."""
    import io
    import wave
    clean = clean_text_for_speech(text or "").strip()
    if not clean:
        return b""
    try:
        voice = _get_piper_voice()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            voice.synthesize_wav(clean, wav_file)
        return buf.getvalue()
    except Exception as e:
        log.warning(f"Piper wav sentez hatası ({e}), gTTS deneniyor...")
        try:
            from gtts import gTTS
            buf = io.BytesIO()
            tts = gTTS(text=clean, lang="tr", slow=False)
            tts.write_to_fp(buf)
            return buf.getvalue()
        except Exception as err:
            log.error(f"TTS genel ses dönüştürme hatası: {err}")
            return b""
