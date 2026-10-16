"""
core/tts_piper.py
------------------
Piper TTS (yerel, ücretsiz, offline) motoru.
.env dosyasındaki PIPER_VOICE değişkenine göre ses modelini seçer.
"""

import os
import subprocess
import tempfile
import wave

import pyaudio
from dotenv import load_dotenv

from core.logger import get_logger

load_dotenv()
log = get_logger("core.tts_piper")

# .env'de PIPER_VOICE=tr_TR-fahrettin-medium şeklinde tanımlı
# Model dosyalarının bulunduğu klasörü burada belirtin
PIPER_MODELS_DIR = os.getenv("PIPER_MODELS_DIR", r"D:\R.I.F.K.I\voice\piper_models")
PIPER_VOICE = os.getenv("PIPER_VOICE", "tr_TR-fahrettin-medium")


class PiperTTS:
    def __init__(self):
        self.model_path = os.path.join(PIPER_MODELS_DIR, f"{PIPER_VOICE}.onnx")

        if not os.path.exists(self.model_path):
            log.error(f"Piper ses modeli bulunamadı: {self.model_path}")
        else:
            log.info(f"Piper TTS hazır. Ses modeli: {self.model_path}")

    def speak(self, text: str):
        """Metni Piper ile sese çevirip doğrudan çalar."""
        if not text or not text.strip():
            return

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            log.info(f"Piper ile sentezleniyor: {text[:50]}...")

            result = subprocess.run(
                ["piper", "--model", self.model_path, "--output_file", tmp_path],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if result.returncode != 0:
                log.error(f"Piper hata verdi: {result.stderr.decode('utf-8', errors='ignore')}")
                return

            self._play_wav(tmp_path)

        except subprocess.TimeoutExpired:
            log.error("Piper sentezleme zaman aşımına uğradı.")
        except Exception as e:
            log.error(f"Piper TTS hatası: {e}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _play_wav(self, path: str):
        wf = wave.open(path, "rb")
        p = pyaudio.PyAudio()
        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True,
        )
        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)
        stream.stop_stream()
        stream.close()
        p.terminate()
        wf.close()


# Diğer motorlarla (gtts, edge_tts) aynı desende tekil örnek
piper_tts = PiperTTS()