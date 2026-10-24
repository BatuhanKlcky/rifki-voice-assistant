"""
voice/audio_device.py
---------------------
Akıllı mikrofon tespiti ve seçimi.

Windows'ta varsayılan kayıt aygıtı "Stereo Karışımı" (Stereo Mix) olabiliyor
ve bu durumda mikrofon RMS değeri 0 (tamamen sessiz) kalarak asistanın
kullanıcıyı duymasını engelliyor.

Bu modül:
1. settings.MICROPHONE_INDEX tanımlıysa doğrudan onu kullanır.
2. Değilse, giriş aygıtlarını filtreler (stereo mix, mapper vb. elenir).
3. Aday cihazları kısa bir sinyal testi (RMS) ile dener.
4. En yüksek canlı sinyal veren veya en uygun mikrofonun indeksini döndürür.
"""

from __future__ import annotations

import math
import struct
from typing import Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger("voice.audio_device")

_cached_device_index: Optional[int] = None

_BLACKLIST_KEYWORDS = (
    "stereo kar",
    "stereo mix",
    "wave",
    "mapper",
    "eslestirici",
    "eşleştirici",
    "birincil",
    "primary",
    "hoparlör",
    "speaker",
    "output",
    "çıkış",
    "cikis",
)

_PRIORITY_KEYWORDS = (
    "razer",
    "blackshark",
    "hyperx",
    "corsair",
    "steelseries",
    "logitech",
    "usb",
    "headset",
    "kulaklık",
    "kulaklik",
)


def calculate_rms(data: bytes) -> int:
    """PCM 16-bit bayt akışından RMS (ses şiddeti) hesaplar."""
    try:
        import audioop
        return audioop.rms(data, 2)
    except Exception:
        count = len(data) // 2
        if count == 0:
            return 0
        try:
            shorts = struct.unpack(f"<{count}h", data[:count * 2])
            sum_squares = sum(s * s for s in shorts)
            return int(math.sqrt(sum_squares / count))
        except Exception:
            return 0


def get_best_microphone_index(force_refresh: bool = False) -> Optional[int]:
    """
    En iyi giriş (mikrofon) aygıtının indeksini döndürür.
    Bulamazsa veya PyAudio yoksa None döner (sr.Microphone varsayılanına düşer).
    """
    global _cached_device_index

    # Kullanıcı elle sabitlemişse
    if settings.MICROPHONE_INDEX is not None:
        return settings.MICROPHONE_INDEX

    if _cached_device_index is not None and not force_refresh:
        return _cached_device_index

    try:
        import pyaudio
    except ImportError:
        log.warning("PyAudio yüklü değil, varsayılan mikrofon kullanılacak.")
        return None

    try:
        p = pyaudio.PyAudio()
    except Exception as e:
        log.error(f"PyAudio başlatılamadı: {e}")
        return None

    candidates: list[tuple[int, str, int]] = []
    try:
        dev_count = p.get_device_count()
        for i in range(dev_count):
            try:
                info = p.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) <= 0:
                    continue
                name = (info.get("name") or "").strip()
                name_low = name.lower()
                if any(b in name_low for b in _BLACKLIST_KEYWORDS):
                    continue
                candidates.append((i, name, info.get("hostApi", 0)))
            except Exception:
                continue

        if not candidates:
            log.warning("Filtre sonrası uygun mikrofon bulunamadı.")
            return None

        best_idx: Optional[int] = None
        best_rms: int = -1
        best_fallback_idx: Optional[int] = None

        # Aday cihazları kısa sinyal testi (1024 sample) ile tara
        for idx, name, host in candidates:
            # Öncelikli fallback: Kulaklık veya USB mikrofon
            name_low = name.lower()
            if best_fallback_idx is None:
                best_fallback_idx = idx
            elif any(pk in name_low for pk in _PRIORITY_KEYWORDS):
                best_fallback_idx = idx

            # Canlı RMS testi
            try:
                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    input_device_index=idx,
                    frames_per_buffer=1024,
                )
                data = stream.read(1024, exception_on_overflow=False)
                data += stream.read(1024, exception_on_overflow=False)
                stream.stop_stream()
                stream.close()
                rms = calculate_rms(data)
                log.debug(f"Mikrofon testi [{idx}] {name}: RMS={rms}")

                # Öncelikli donanım bonusu
                effective_score = rms
                if any(pk in name_low for pk in _PRIORITY_KEYWORDS):
                    effective_score += 1500

                if effective_score > best_rms:
                    best_rms = effective_score
                    best_idx = idx
            except Exception as probe_err:
                log.debug(f"Aygıt {idx} test edilemedi: {probe_err}")

        chosen = best_idx if best_idx is not None else best_fallback_idx
        if chosen is not None:
            dev_info = p.get_device_info_by_index(chosen)
            chosen_name = dev_info.get("name", f"Index {chosen}")
            log.info(f"Seçilen mikrofon: [{chosen}] '{chosen_name}' (RMS skoru: {best_rms})")
            _cached_device_index = chosen
            return chosen

    except Exception as e:
        log.error(f"Mikrofon tespiti sırasında hata: {e}")
    finally:
        try:
            p.terminate()
        except Exception:
            pass

    return None
