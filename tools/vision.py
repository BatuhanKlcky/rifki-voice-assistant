"""
tools/vision.py
---------------
Multimodal Vision Motoru.
Bilgisayar ekranının anlık görüntüsünü yakalar ve Vision AI (Gemini / OmniRoute)
üzerinden ekrandaki kodları, hata pencerelerini, metinleri ve görselleri analiz eder.
"""

import base64
import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

from core.logger import get_logger
from tools.system import capture_screenshot_for_mobile

log = get_logger("tools.vision")

# .env yükle
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


def get_screen_base64(max_width: int = 1600, quality: int = 80) -> str:
    """Ekran görüntüsünü alıp base64 string olarak döner."""
    jpeg_bytes = capture_screenshot_for_mobile(max_width=max_width, quality=quality)
    return base64.b64encode(jpeg_bytes).decode("ascii")


def _analyze_with_omniroute(prompt: str, b64_img: str) -> str:
    """OmniRoute / OpenAI uyumlu vision endpoint'i çağırır."""
    url = os.getenv("OMNIROUTE_URL", "http://127.0.0.1:20128/v1/chat/completions").replace("://localhost", "://127.0.0.1")
    api_key = os.getenv("OMNIROUTE_API_KEY", "")
    model = os.getenv("OMNIROUTE_MODEL", "antigravity/gemini-2.5-flash")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Kullanıcının isteği: {prompt}\n\n"
                            "Bu bilgisayar ekranının anlık görüntüsüdür. "
                            "Görüntüyü dikkatlice incele; açık pencereler, hata mesajları, "
                            "kodlar veya arayüzdeki önemli unsurlar hakkında net, Türkçe ve özet bilgi ver."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_img}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        "stream": False,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=25)
    if not resp.ok:
        raise RuntimeError(f"OmniRoute HTTP {resp.status_code}: {resp.text[:150]}")

    data = resp.json()
    choices = data.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content") or ""
        if content:
            return content.strip()
    return "Ekran analiz edilemedi (boş yanıt)."


def _analyze_with_gemini(prompt: str, b64_img: str, api_key: str) -> str:
    """Doğrudan Google Gemini Vision REST API çağırır."""
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"Kullanıcının isteği: {prompt}\n\n"
                            "Ekteki ekran görüntüsünü incele. Açık uygulamaları, metinleri, "
                            "hata pencerelerini veya kullanıcının sorduğu detayları Türkçe, açık ve net bir şekilde açıkla."
                        )
                    },
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": b64_img,
                        }
                    },
                ]
            }
        ]
    }

    resp = requests.post(url, json=payload, timeout=25)
    if not resp.ok:
        raise RuntimeError(f"Gemini API HTTP {resp.status_code}: {resp.text[:150]}")

    data = resp.json()
    candidates = data.get("candidates") or []
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if p.get("text")]
        if texts:
            return "".join(texts).strip()

    return "Ekran analiz edilemedi (Gemini boş içerik döndürdü)."


def _offline_fallback(prompt: str) -> str:
    """Vision API'leri kapalıyken yerel pencere ve sistem durumunu özetler."""
    try:
        from tools.desktop_automation import get_active_window_title
        active = get_active_window_title()
    except Exception:
        active = "Bilinmiyor"

    return (
        f"Görsel analiz API'sine erişilemedi. Ancak sistem tespitine göre şu an ön planda "
        f"aktif olan pencere: '{active}'. "
        f"(Tam AI Vision analizi için OmniRoute veya GEMINI_API_KEY bağlantısının aktif olması gerekir.)"
    )


def analyze_screen(question: str = "Ekranda ne görüyorsun? Özetle.") -> str:
    """
    Mevcut masaüstünün ekran görüntüsünü alır ve Multimodal Vision AI ile inceler.
    Ekrandaki pencereleri, hataları, kodları veya metinleri analiz eder.
    """
    log.info(f"Ekran analizi başlatılıyor: {question}")
    try:
        b64_img = get_screen_base64(max_width=1600, quality=80)
    except Exception as e:
        log.error(f"Ekran görüntüsü alınamadı: {e}")
        return f"Ekran görüntüsü alınamadı: {e}"

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    # 1. Önce OmniRoute dene
    try:
        res = _analyze_with_omniroute(question, b64_img)
        if res:
            log.info("Ekran analizi OmniRoute üzerinden tamamlandı.")
            return res
    except Exception as e:
        log.warning(f"OmniRoute Vision başarısız oldu: {e}")

    # 2. Gemini API Key varsa Gemini dene
    if gemini_key and not gemini_key.startswith("AIzaSyXXXX"):
        try:
            res = _analyze_with_gemini(question, b64_img, gemini_key)
            if res:
                log.info("Ekran analizi Gemini üzerinden tamamlandı.")
                return res
        except Exception as e:
            log.warning(f"Gemini Vision başarısız oldu: {e}")

    # 3. Çevrimdışı / fallback raporu
    return _offline_fallback(question)
