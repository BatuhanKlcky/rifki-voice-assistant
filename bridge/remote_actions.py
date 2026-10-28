"""
bridge/remote_actions.py
------------------------
Mobil uzaktan kontrol aksiyonları (ses, medya, kilit, güç, URL, telemetri, pano, klavye).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from core.logger import get_logger

log = get_logger("bridge.remote")

# Onay (confirm=true) olmadan çalışmaz
_DANGEROUS = frozenset({"shutdown", "restart", "sleep"})


def run_remote_action(action: str, body: dict | None = None) -> dict[str, Any]:
    """Aksiyon çalıştırır. Başarıda {ok, reply, ...}; hata dict + ok=False."""
    body = body or {}
    action = (action or "").strip().lower()
    confirm = bool(body.get("confirm"))

    if action in _DANGEROUS and not confirm:
        return {
            "ok": False,
            "error": "Bu işlem onay ister (confirm: true).",
            "needs_confirm": True,
            "action": action,
        }

    try:
        reply, extra = _dispatch(action, body)
    except ValueError as e:
        return {"ok": False, "error": str(e), "action": action}
    except Exception as e:
        log.error(f"Uzaktan aksiyon hatası ({action}): {e}")
        return {"ok": False, "error": str(e), "action": action}

    result: dict[str, Any] = {"ok": True, "reply": reply, "action": action}
    if extra:
        result.update(extra)
    return result


def _dispatch(action: str, body: dict) -> tuple[str, dict]:
    from tools import browser, media, system

    # Ses kontrolleri
    if action == "volume_up":
        reply = system.adjust_volume(int(body.get("delta") or 10))
        return reply, {"volume": system.get_volume_info()}
    if action == "volume_down":
        reply = system.adjust_volume(-int(body.get("delta") or 10))
        return reply, {"volume": system.get_volume_info()}
    if action == "set_volume":
        level = int(body.get("level") if body.get("level") is not None else 50)
        reply = system.set_volume(level)
        return reply, {"volume": system.get_volume_info()}
    if action == "mute":
        return system.mute_volume(), {"volume": system.get_volume_info()}
    if action == "unmute":
        return system.unmute_volume(), {"volume": system.get_volume_info()}
    if action == "toggle_mute":
        return system.toggle_mute(), {"volume": system.get_volume_info()}
    if action == "volume_info":
        info = system.get_volume_info()
        level = info.get("level")
        muted = info.get("muted")
        reply = f"Ses %{level}" + (" (sessiz)" if muted else "")
        return reply, {"volume": info}

    # Medya kontrolleri
    if action == "media_play_pause":
        return media.media_play_pause(), {}
    if action == "media_next":
        return media.media_next(), {}
    if action == "media_prev":
        return media.media_prev(), {}
    if action == "media_stop":
        return media.media_stop(), {}

    # Güç ve Ekran
    if action == "lock":
        return system.lock_screen(), {}
    if action == "sleep":
        return system.sleep_pc(), {}
    if action == "shutdown":
        return system.shutdown_computer(), {}
    if action == "restart":
        return system.restart_computer(), {}
    if action == "cancel_shutdown":
        return system.cancel_shutdown(), {}
    if action in ("display_off", "turn_off_display", "screen_off"):
        return system.turn_off_display(), {}

    # Canlı Telemetri
    if action in ("telemetry", "system_status"):
        data = system.get_telemetry_dict()
        reply = f"CPU: %{data.get('cpu')} | RAM: %{data.get('ram')} | Disk: %{data.get('disk')}"
        return reply, {"telemetry": data}

    # Klasör açma
    if action == "open_folder":
        folder = body.get("folder") or "downloads"
        return system.open_special_folder(folder), {}

    # Pano (Clipboard)
    if action == "set_clipboard":
        text = str(body.get("text") or "")
        return system.set_clipboard_text(text), {}
    if action == "get_clipboard":
        clip = system.get_clipboard_text()
        return f"Panodaki metin alındı ({len(clip)} karakter).", {"clipboard": clip}

    # Klavye tuşları & Metin yazma
    if action == "press_key":
        key = str(body.get("key") or "")
        return system.send_key_stroke(key), {}
    if action == "type_text":
        text = str(body.get("text") or "")
        return system.type_text_to_pc(text), {}

    # Arama ve URL
    if action == "search_google":
        q = (body.get("query") or "").strip()
        return browser.open_google_search(q), {}
    if action == "search_youtube":
        q = (body.get("query") or "").strip()
        return browser.open_youtube_search(q), {}

    if action == "open_url":
        url = (body.get("url") or "").strip()
        if not url:
            raise ValueError("url gerekli")
        if len(url) > 2048:
            raise ValueError("url çok uzun")
        parsed = urlparse(url if "://" in url else "https://" + url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("yalnızca http/https")
        return browser.open_url(url), {}

    # Wake-on-LAN
    if action == "wol_info":
        from tools import wake_on_lan
        return wake_on_lan.get_wake_on_lan_info(), {}
    if action == "wake_device":
        from tools import wake_on_lan
        target = body.get("target") or "pc"
        return wake_on_lan.wake_device(target), {}

    # Masaüstü, Pencere ve Sekme Otomasyonu
    if action == "control_window":
        from tools import desktop_automation
        param = body.get("cmd") or body.get("param") or "show_desktop"
        return desktop_automation.control_active_window(param), {}
    if action == "browser_tab":
        from tools import desktop_automation
        param = body.get("cmd") or body.get("param") or "new_tab"
        return desktop_automation.browser_tab_action(param), {}
    if action == "organize_folder":
        from tools import desktop_automation
        folder = body.get("folder") or "downloads"
        return desktop_automation.organize_folder(folder), {}
    if action == "empty_recycle_bin":
        from tools import desktop_automation
        return desktop_automation.empty_recycle_bin(), {}

    # Müzik (YouTube Music)
    if action == "play_youtube_music":
        from tools import media
        q = body.get("query") or "lofi beats"
        return media.play_youtube_music(q), {}

    # Ekran Analizi (Vision AI) ve Görüntü
    if action in ("analyze_screen", "vision"):
        from tools import vision
        q = body.get("question") or "Ekranda ne var? Detaylı incele."
        return vision.analyze_screen(q), {}

    if action in ("take_screenshot", "screenshot"):
        from tools import system
        return system.take_screenshot(), {}

    raise ValueError(f"bilinmeyen aksiyon: {action}")
