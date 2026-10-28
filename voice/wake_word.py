"""
voice/wake_word.py
-------------------
«Rıfkı» uyandırma kelimesi.

Notlar:
- .env'de Türkçe karakter bozulabiliyor (rÄ±fkÄ±); her zaman rifki ailesine normalize et.
- Google sık sık yalnızca «rıf» / «Rıfkı» döndürür — kısa önekleri de kabul et.
- dynamic_energy_threshold KAPALI (kısa kelimeyi yutuyordu).
"""

from __future__ import annotations

import audioop
import speech_recognition as sr

from config.settings import settings
from core.logger import get_logger
from voice.audio_device import get_best_microphone_index

log = get_logger("voice.wake_word")

_recognizer = sr.Recognizer()
_recognizer.energy_threshold = 100
_recognizer.dynamic_energy_threshold = False
_recognizer.pause_threshold = 0.55
_recognizer.non_speaking_duration = 0.35
_recognizer.phrase_threshold = 0.15

_FOLD = str.maketrans({
    "ı": "i", "İ": "i", "I": "i",
    "ş": "s", "Ş": "s",
    "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u",
    "ö": "o", "Ö": "o",
    "ç": "c", "Ç": "c",
    # Mojibake kalıntıları
    "±": "i", "Ä": "", "Å": "",
})

# Tam / yakın yazımlar ve Google STT alternatifleri
_RIFKI_ALIASES = frozenset({
    "rifki", "refki", "rivki", "rifky", "rifkey", "riffki", "riffkey",
    "rifke", "rifku", "ricki", "ricky", "rikki", "rikky",
    "reefki", "reefkey", "risky", "riski", "ripki", "arifki",
    "heyrifki", "yarifki", "merhabarifki", "eyrifki",
    # Google STT'nin Türkçe ses tonlamasında "Rıfkı" için en sık ürettiği varyasyonlar:
    "tipki", "tipk", "tıpkı", "tıpki", "refik", "rifat", "rızkı", "rizki", "rızk", "rizk",
    "rufi", "ruski", "rifkim", "rıfkım", "kirki", "kırkı", "fistik", "fıstık",
})

# Google'ın kestiği kısa parçalar (tek başına kabul)
_RIFKI_PREFIXES = frozenset({
    "rif", "rifk", "ref", "refk", "riv", "rivk", "riff",
})


def _fold(text: str) -> str:
    return (text or "").lower().translate(_FOLD)


def _compact(text: str) -> str:
    return "".join(ch for ch in _fold(text) if ch.isalnum())


def _normalize_wake_setting(raw: str) -> str:
    """Bozuk encoding / jarvis → her zaman rifki ailesi."""
    t = _compact(raw)
    if not t or t in ("jarvis", "alexa"):
        return "rifki"
    if "rifk" in t or "refk" in t or (t.startswith("r") and "fk" in t):
        return "rifki"
    # rÄ±fkÄ± gibi: harfler arasından r..f..k çıkar
    letters = "".join(ch for ch in t if ch.isalpha())
    if "rifk" in letters or letters.startswith("rif"):
        return "rifki"
    return t or "rifki"


def matches_wake_word(text: str) -> bool:
    heard = _fold(text)
    compact = _compact(text)
    if not compact:
        return False

    # Ürün adı her zaman rifki — .env bozuk olsa bile
    if "rifki" in compact or "refki" in compact:
        return True
    if any(a in compact for a in _RIFKI_ALIASES):
        return True
    if any(a in heard for a in _RIFKI_ALIASES):
        return True

    # Sessiz harf analizi: r-f-k veya r-z-k iceren her seslenis
    cons = "".join(c for c in heard if c in "bcdfghjklmnprstvyz")
    if "rfk" in cons or "rzk" in cons:
        return True

    # Tek token: Rıfkı / rıf / rifk...
    for token in heard.replace(",", " ").replace(".", " ").split():
        t = _compact(token)
        if not t:
            continue
        if t in _RIFKI_ALIASES or t in _RIFKI_PREFIXES:
            return True
        if len(t) >= 3 and (
            t.startswith("rif")
            or t.startswith("ref")
            or t.startswith("riv")
            or t.startswith("riff")
        ):
            return True

    # Tüm cümle kompakt önek
    if compact in _RIFKI_PREFIXES:
        return True
    if len(compact) >= 3 and compact.startswith(("rif", "ref", "riv")):
        return True

    target = _normalize_wake_setting(settings.WAKE_WORD)
    if target and target in compact:
        return True
    return False


def _transcripts_from_google(audio, language: str) -> list[str]:
    out: list[str] = []
    try:
        result = _recognizer.recognize_google(
            audio, language=language, show_all=True
        )
    except sr.UnknownValueError:
        return out
    except sr.RequestError as e:
        log.error(f"Wake-word STT hatası [{language}]: {e}")
        raise

    if not result:
        return out
    if isinstance(result, str):
        return [result]
    if isinstance(result, dict):
        for alt in result.get("alternative") or []:
            t = (alt.get("transcript") or "").strip()
            if t and t not in out:
                out.append(t)
    return out


def _wake_languages() -> list[str]:
    primary = (settings.WAKE_WORD_LANGUAGE or "tr-TR").strip() or "tr-TR"
    langs = [primary]
    if primary.lower().startswith("tr"):
        langs.extend(["tr-TR", "en-US"])
    else:
        langs.extend(["tr-TR", "en-US"])
    out = []
    for lang in langs:
        if lang and lang not in out:
            out.append(lang)
    return out


def _audio_rms(audio) -> int:
    try:
        return audioop.rms(audio.frame_data, audio.sample_width)
    except Exception:
        return 0


def wait_for_wake_word(stop_flag_check=lambda: False) -> bool:
    try:
        mic_idx = get_best_microphone_index()
        with sr.Microphone(device_index=mic_idx) as source:
            norm = _normalize_wake_setting(settings.WAKE_WORD)
            log.info(
                f"Wake-word dinleme (kelime={settings.WAKE_WORD!r}→{norm!r}, "
                f"diller={_wake_languages()}, energy={_recognizer.energy_threshold}, "
                f"mic={source.device_index})"
            )
            try:
                _recognizer.adjust_for_ambient_noise(source, duration=0.6)
            except Exception:
                pass
            # Ortam gürültüsüne göre dinamik eşik: 150'ye sabitleme (gürültülü kulaklıklarda sonsuz döngüyü engeller)
            measured_energy = _recognizer.energy_threshold
            _recognizer.energy_threshold = max(measured_energy * 1.15, 300)
            _recognizer.dynamic_energy_threshold = True
            _recognizer.dynamic_energy_adjustment_damping = 0.15
            _recognizer.dynamic_energy_ratio = 1.4
            _recognizer.pause_threshold = 0.5
            _recognizer.phrase_threshold = 0.15
            _recognizer.non_speaking_duration = 0.35

            while not stop_flag_check():
                try:
                    # Biraz daha uzun: «rıfkı» kesilmesin
                    audio = _recognizer.listen(
                        source, timeout=3.0, phrase_time_limit=4.0
                    )
                except sr.WaitTimeoutError:
                    continue

                rms = _audio_rms(audio)
                log.info(f"Wake-word: ses parçası RMS={rms}")

                any_text = False
                for lang in _wake_languages():
                    try:
                        texts = _transcripts_from_google(audio, lang)
                    except sr.RequestError:
                        break
                    for text in texts:
                        any_text = True
                        hit = matches_wake_word(text)
                        log.info(
                            f"Wake-word [{lang}]: '{text}' → "
                            f"{'ESLESTI' if hit else 'yok'}"
                        )
                        if hit:
                            log.info(f"Wake word algılandı: {text}")
                            return True

                if not any_text and rms > 200:
                    log.info(
                        f"Wake-word: ses var ama metin yok (RMS={rms}). "
                        "Daha net «rıfkı» deyin."
                    )
    except OSError as e:
        log.error(f"Mikrofon erişim hatası (wake word): {e}")
        raise

    return False
