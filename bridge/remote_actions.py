"""
bridge/remote_actions.py
------------------------
Mobil uzaktan kontrol aksiyonları (ses, medya, kilit, güç, URL).
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

    if action == "media_play_pause":
        return media.media_play_pause(), {}
    if action == "media_next":
        return media.media_next(), {}
    if action == "media_prev":
        return media.media_prev(), {}
    if action == "media_stop":
        return media.media_stop(), {}

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

    raise ValueError(f"bilinmeyen aksiyon: {action}")
