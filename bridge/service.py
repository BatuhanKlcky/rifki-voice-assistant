"""
bridge/service.py
-----------------
Yerel aiohttp sunucusu: mobil PWA, durum API'si, komut POST, WebSocket,
Canlı Touchpad (WS düşük gecikmeli fare kontrolü) ve Kablosuz AirDrop (Telefon ⇄ PC dosya aktarımı).
Dışarıya doğrudan açılmaz (127.0.0.1 / LAN); Cloudflare Tunnel bağlanır.
"""

from __future__ import annotations

import asyncio
from collections import deque
import datetime
import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger("bridge")

CommandHandler = Callable[[str], str]

_AUTH_WINDOW_SECONDS = 60.0
_AUTH_MAX_FAILURES = 10
_AUTH_LOCKOUT_SECONDS = 300.0
_SAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _static_dir() -> Path:
    here = Path(__file__).resolve().parent / "static"
    if here.is_dir():
        return here
    import sys

    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        candidate = meipass / "bridge" / "static"
        if candidate.is_dir():
            return candidate
    return here


def _airdrop_dir() -> Path:
    """Telefondan gelen ve telefona paylaşılacak dosyalar için güvenli klasör."""
    d = Path.home() / "Downloads" / "RIFKI_AirDrop"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sanitize_filename(name: str) -> str:
    clean = Path(name or "dosya").name
    clean = _SAFE_FILENAME_RE.sub("_", clean).strip(". ")
    if not clean:
        clean = f"airdrop_{int(time.time())}.bin"
    return clean[:180]


class MobileBridge:
    def __init__(self) -> None:
        self.state = "OFF"
        self.listening = False
        self.last_user = ""
        self.last_assistant = ""
        self.history: deque[dict[str, str]] = deque(maxlen=100)
        self._clients: set[Any] = set()
        self._command_handler: Optional[CommandHandler] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._runner = None
        self._site = None
        self._stop = threading.Event()
        self._failed_auth: dict[str, list[float]] = {}
        self._locked_ips: dict[str, float] = {}

    def set_command_handler(self, handler: CommandHandler) -> None:
        self._command_handler = handler

    def status_payload(self) -> dict:
        return {
            "state": self.state,
            "listening": self.listening,
            "last_user": self.last_user,
            "last_assistant": self.last_assistant,
            "history": list(self.history)[-40:],
        }

    def _live_payload(self, **extra) -> dict:
        """WS canlı olayları: history yok (hello/status API'sinde kalır)."""
        payload = {
            "state": self.state,
            "listening": self.listening,
            "last_user": self.last_user,
            "last_assistant": self.last_assistant,
        }
        payload.update(extra)
        return payload

    def set_listening(self, active: bool) -> None:
        self.listening = active
        self._broadcast(self._live_payload(type="status"))

    def publish_state(self, state: str) -> None:
        self.state = state or self.state
        self._broadcast(self._live_payload(type="status"))

    def publish_user(self, text: str) -> None:
        self.last_user = text
        self.history.append({"role": "user", "text": text})
        self._broadcast(self._live_payload(type="user", text=text))

    def publish_assistant(self, text: str) -> None:
        self.last_assistant = text
        self.history.append({"role": "assistant", "text": text})
        self._broadcast(self._live_payload(type="assistant", text=text))

    def publish_error(self, text: str) -> None:
        self.history.append({"role": "error", "text": text})
        self._broadcast(self._live_payload(type="error", text=text))

    def _broadcast(self, payload: dict) -> None:
        loop = self._loop
        if loop is None or not self._clients:
            return
        data = json.dumps(payload, ensure_ascii=False)

        def _send_all():
            dead = []
            for ws in list(self._clients):
                try:
                    asyncio.ensure_future(ws.send_str(data), loop=loop)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self._clients.discard(ws)

        try:
            loop.call_soon_threadsafe(_send_all)
        except RuntimeError:
            pass

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return True
        if not settings.MOBILE_BRIDGE_ENABLED:
            log.info("Mobil köprü kapalı (MOBILE_BRIDGE_ENABLED).")
            return False
        if not settings.MOBILE_BRIDGE_TOKEN.strip():
            log.info(
                "Mobil köprü açılmadı: MOBILE_BRIDGE_TOKEN boş. "
                ".env dosyasına bir token yaz."
            )
            return False
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run_thread, name="RIFKI-MobileBridge", daemon=True
        )
        self._thread.start()
        threading.Thread(
            target=self._warmup_apps_catalog,
            name="RIFKI-AppsWarmup",
            daemon=True,
        ).start()
        return True

    @staticmethod
    def _warmup_apps_catalog() -> None:
        try:
            from tools.applications import load_catalog

            load_catalog(force=True)
            log.info("Uygulama kataloğu arka planda ısıtıldı.")
        except Exception as e:
            log.warning(f"Uygulama kataloğu ısınma atlandı: {e}")

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        self._loop = None

    def _run_thread(self) -> None:
        try:
            asyncio.run(self._serve())
        except Exception as e:
            log.error(f"Mobil köprü çöktü: {e}")

    async def _serve(self) -> None:
        from aiohttp import web

        @web.middleware
        async def _security_and_cache_headers(request, handler):
            resp = await handler(request)
            path = request.path or ""
            resp.headers["X-Content-Type-Options"] = "nosniff"
            resp.headers["X-Frame-Options"] = "DENY"
            resp.headers["Referrer-Policy"] = "no-referrer"
            if path.startswith("/static/"):
                resp.headers["Cache-Control"] = "public, max-age=300"
            elif path in ("/", "/index.html") or path.endswith("index.html"):
                resp.headers["Cache-Control"] = "no-cache"
            return resp

        self._loop = asyncio.get_running_loop()
        # 100 MB max upload size for Wireless AirDrop file/photo transfers
        app = web.Application(
            middlewares=[_security_and_cache_headers],
            client_max_size=100 * 1024 * 1024,
        )
        app.router.add_get("/", self._handle_index)
        app.router.add_get("/api/status", self._handle_status)
        app.router.add_post("/api/command", self._handle_command)
        app.router.add_get("/api/screenshot", self._handle_screenshot)
        app.router.add_get("/api/apps", self._handle_apps)
        app.router.add_post("/api/apps/launch", self._handle_apps_launch)
        app.router.add_post("/api/remote", self._handle_remote)
        app.router.add_get("/api/volume", self._handle_volume)
        app.router.add_get("/api/telemetry", self._handle_telemetry)
        app.router.add_get("/api/tts", self._handle_tts)
        app.router.add_post("/api/vision", self._handle_vision)
        app.router.add_get("/api/transfer/list", self._handle_transfer_list)
        app.router.add_post("/api/transfer/upload", self._handle_transfer_upload)
        app.router.add_get("/api/transfer/download", self._handle_transfer_download)
        app.router.add_get("/ws", self._handle_ws)
        static = _static_dir()
        if static.is_dir():
            app.router.add_static("/static/", static, name="static")

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        host = settings.MOBILE_BRIDGE_HOST
        port = settings.MOBILE_BRIDGE_PORT
        self._site = web.TCPSite(self._runner, host, port)
        await self._site.start()
        log.info(f"Mobil köprü dinliyor: http://{host}:{port}")

        while not self._stop.is_set():
            await asyncio.sleep(0.4)

        await self._runner.cleanup()
        log.info("Mobil köprü durdu.")

    @staticmethod
    def _client_ip(request) -> str:
        cf_ip = request.headers.get("CF-Connecting-IP", "").strip()
        if cf_ip:
            return cf_ip
        return request.remote or "unknown"

    def _is_ip_locked(self, ip: str) -> bool:
        now = time.monotonic()
        until = self._locked_ips.get(ip, 0.0)
        if until > now:
            return True
        if ip in self._locked_ips:
            del self._locked_ips[ip]
        return False

    def _record_auth_failure(self, ip: str) -> None:
        now = time.monotonic()
        attempts = [t for t in self._failed_auth.get(ip, []) if now - t < _AUTH_WINDOW_SECONDS]
        attempts.append(now)
        self._failed_auth[ip] = attempts
        if len(attempts) >= _AUTH_MAX_FAILURES:
            self._locked_ips[ip] = now + _AUTH_LOCKOUT_SECONDS
            self._failed_auth.pop(ip, None)
            log.warning(f"Güvenlik uyarısı: Çok fazla hatalı token denemesi nedeniyle IP 5 dk engellendi -> {ip}")

    def _token_ok(self, request, record_failure: bool = True) -> bool:
        ip = self._client_ip(request)
        if self._is_ip_locked(ip):
            return False

        expected = settings.MOBILE_BRIDGE_TOKEN.strip()
        if not expected:
            return False

        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
            if got and secrets.compare_digest(got, expected):
                self._failed_auth.pop(ip, None)
                return True

        cookie_tok = request.cookies.get("rifki_session", "").strip()
        if cookie_tok and secrets.compare_digest(cookie_tok, expected):
            self._failed_auth.pop(ip, None)
            return True

        q = request.rel_url.query.get("token", "").strip()
        if q and secrets.compare_digest(q, expected):
            self._failed_auth.pop(ip, None)
            return True

        if record_failure:
            self._record_auth_failure(ip)
        return False

    async def _handle_index(self, request):
        from aiohttp import web

        authed = self._token_ok(request, record_failure=False)
        index = _static_dir() / "index.html"
        if not index.is_file():
            return web.Response(text="Mobil panel bulunamadı.", status=500)
        resp = web.FileResponse(
            index,
            headers={"Cache-Control": "no-cache"},
        )
        if authed:
            resp.set_cookie(
                "rifki_session",
                settings.MOBILE_BRIDGE_TOKEN.strip(),
                httponly=True,
                samesite="Strict",
                max_age=86400 * 30,
            )
        return resp

    async def _handle_status(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        return web.json_response(self.status_payload())

    async def _handle_command(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "geçersiz json"}, status=400)
        text = (body.get("text") or body.get("command") or "").strip()[:1024]
        if not text:
            return web.json_response({"error": "boş komut"}, status=400)
        handler = self._command_handler
        if handler is None:
            return web.json_response({"error": "köprü hazır değil"}, status=503)
        loop = asyncio.get_running_loop()
        try:
            reply = await loop.run_in_executor(None, handler, text)
        except Exception as e:
            log.error(f"Mobil komut hatası: {e}")
            return web.json_response({"error": str(e)}, status=500)
        return web.json_response({"reply": reply, **self.status_payload()})

    async def _handle_screenshot(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        try:
            max_width = int(request.rel_url.query.get("w") or "1280")
        except ValueError:
            max_width = 1280
        try:
            quality = int(request.rel_url.query.get("q") or "72")
        except ValueError:
            quality = 72
        max_width = max(320, min(1920, max_width))
        quality = max(40, min(90, quality))
        live = (request.rel_url.query.get("live") or "").lower() in ("1", "true", "yes")
        fast = (request.rel_url.query.get("fast") or "").lower() in ("1", "true", "yes") or live
        primary_only = (request.rel_url.query.get("primary") or ("1" if live else "0")).lower() in ("1", "true", "yes")
        if live:
            max_width = min(max_width, 960)
            quality = min(quality, 60)

        loop = asyncio.get_running_loop()
        try:
            from tools.system import capture_screenshot_for_mobile

            jpeg = await loop.run_in_executor(
                None,
                lambda: capture_screenshot_for_mobile(
                    max_width=max_width,
                    quality=quality,
                    fast=fast,
                    all_screens=not primary_only,
                ),
            )
            if not jpeg or len(jpeg) < 100:
                raise RuntimeError("boş görüntü")
        except Exception as e:
            log.error(f"Mobil ekran görüntüsü hatası: {e}", exc_info=True)
            return web.json_response(
                {"error": f"ekran görüntüsü alınamadı ({e})"},
                status=500,
            )
        if not live:
            log.info(f"Mobil ekran görüntüsü gönderildi: {len(jpeg)} bayt (JPEG)")
        return web.Response(
            body=jpeg,
            content_type="image/jpeg",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "Content-Length": str(len(jpeg)),
            },
        )

    async def _handle_volume(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        loop = asyncio.get_running_loop()
        try:
            from tools.system import get_volume_info

            info = await loop.run_in_executor(None, get_volume_info)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
        return web.json_response(info)

    async def _handle_remote(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "geçersiz json"}, status=400)
        action = (body.get("action") or "").strip()
        if not action:
            return web.json_response({"error": "action gerekli"}, status=400)

        from bridge.remote_actions import run_remote_action

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: run_remote_action(action, body)
        )
        if not result.get("ok"):
            return web.json_response(result, status=400)

        reply = result.get("reply") or ""
        label = {
            "volume_up": "Ses +",
            "volume_down": "Ses −",
            "toggle_mute": "Sessiz",
            "mute": "Sessiz",
            "unmute": "Sesi aç",
            "media_play_pause": "Medya ▶/❚❚",
            "media_next": "Sonraki",
            "media_prev": "Önceki",
            "lock": "Kilitle",
            "sleep": "Uyku",
            "shutdown": "Kapat",
            "restart": "Yeniden başlat",
            "open_url": "URL aç",
            "cancel_shutdown": "Kapatmayı iptal",
            "game_mode_toggle": "🎮 Oyun Modu",
            "optimize_ram": "🚀 RAM Optimizasyonu",
        }.get(action, action)
        if action in ("lock", "sleep", "shutdown", "restart", "open_url", "cancel_shutdown", "game_mode_toggle", "optimize_ram"):
            self.publish_user(label)
            if reply:
                self.publish_assistant(reply)
        return web.json_response(result)

    async def _handle_tts(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            return web.Response(text="yetkisiz", status=401)
        text = (request.rel_url.query.get("text") or "").strip()[:1000]
        if not text:
            return web.Response(text="boş metin", status=400)

        from voice.text_to_speech import synthesize_wav_bytes
        loop = asyncio.get_running_loop()
        try:
            data = await loop.run_in_executor(None, lambda: synthesize_wav_bytes(text))
            if not data:
                return web.Response(text="ses üretilemedi", status=500)
            return web.Response(
                body=data,
                content_type="audio/wav",
                headers={"Cache-Control": "public, max-age=120"},
            )
        except Exception as e:
            log.error(f"TTS endpoint hatası: {e}")
            return web.Response(text=str(e), status=500)

    async def _handle_telemetry(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        from tools import system

        loop = asyncio.get_running_loop()
        try:
            data = await loop.run_in_executor(None, system.get_telemetry_dict)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
        return web.json_response(data)

    async def _handle_apps(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        q = (request.rel_url.query.get("q") or "").strip()[:120]
        try:
            limit = int(request.rel_url.query.get("limit") or "400")
        except ValueError:
            limit = 400
        loop = asyncio.get_running_loop()
        try:
            from tools.applications import list_applications

            apps = await loop.run_in_executor(
                None, lambda: list_applications(q, limit)
            )
        except Exception as e:
            log.error(f"Uygulama listesi hatası: {e}")
            return web.json_response({"error": "liste alınamadı"}, status=500)
        return web.json_response({"apps": apps, "count": len(apps)})

    async def _handle_apps_launch(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"error": "geçersiz json"}, status=400)
        name = (body.get("name") or body.get("path") or "").strip()
        if not name:
            return web.json_response({"error": "uygulama adı gerekli"}, status=400)
        if any(ch in name for ch in ("\\", "/", ":", ";", "|")) or len(name) > 120:
            return web.json_response({"error": "geçersiz uygulama adı"}, status=400)
        loop = asyncio.get_running_loop()
        try:
            from tools.applications import open_application

            reply = await loop.run_in_executor(None, open_application, name)
        except Exception as e:
            log.error(f"Mobil uygulama açma hatası: {e}")
            return web.json_response({"error": str(e)}, status=500)
        self.publish_user(f"Uygulama aç: {name}")
        self.publish_assistant(reply)
        return web.json_response({"reply": reply, **self.status_payload()})

    async def _handle_vision(self, request):
        from aiohttp import web
        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        try:
            body = await request.json()
        except Exception:
            body = {}
        question = (body.get("question") or "Ekranda ne görüyorsun? Özetle.").strip()[:512]
        loop = asyncio.get_running_loop()
        try:
            from tools.vision import analyze_screen
            result = await loop.run_in_executor(None, analyze_screen, question)
            return web.json_response({"ok": True, "question": question, "analysis": result})
        except Exception as e:
            log.error(f"Vision API hatası: {e}")
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    # =====================================================================
    # 📲 KABLOSUZ AIRDROP (TELEFON ⇄ PC DOSYA/FOTOĞRAF AKTARIMI)
    # =====================================================================
    @staticmethod
    def _collect_airdrop_files() -> list[dict]:
        folder = _airdrop_dir()
        items: list[dict] = []
        try:
            for f in sorted(folder.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if not f.is_file() or f.name.startswith("."):
                    continue
                st = f.stat()
                items.append({
                    "name": f.name,
                    "size": st.st_size,
                    "mtime": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%d.%m %H:%M"),
                })
                if len(items) >= 30:
                    break
        except Exception as e:
            log.warning(f"AirDrop dosya listeleme hatası: {e}")
        return items

    async def _handle_transfer_list(self, request):
        from aiohttp import web
        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        loop = asyncio.get_running_loop()
        files = await loop.run_in_executor(None, self._collect_airdrop_files)
        return web.json_response({
            "ok": True,
            "folder": str(_airdrop_dir()),
            "files": files,
        })

    async def _handle_transfer_upload(self, request):
        from aiohttp import web
        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)

        folder = _airdrop_dir()
        saved_files: list[str] = []
        try:
            reader = await request.multipart()
            while True:
                part = await reader.next()
                if part is None:
                    break
                if part.filename:
                    safe_name = _sanitize_filename(part.filename)
                    dest = folder / safe_name
                    counter = 1
                    stem = dest.stem
                    ext = dest.suffix
                    while dest.exists():
                        dest = folder / f"{stem}_{counter}{ext}"
                        counter += 1
                    with open(dest, "wb") as out:
                        while True:
                            chunk = await part.read_chunk(256 * 1024)
                            if not chunk:
                                break
                            out.write(chunk)
                    saved_files.append(dest.name)
                    log.info(f"AirDrop ile telefondan dosya alındı: {dest}")
        except Exception as e:
            log.error(f"AirDrop dosya yükleme hatası: {e}")
            return web.json_response({"ok": False, "error": f"Yükleme başarısız: {e}"}, status=400)

        if not saved_files:
            return web.json_response({"ok": False, "error": "Dosya seçilmedi."}, status=400)

        names_str = ", ".join(saved_files)
        msg = f"📲 Telefondan {len(saved_files)} dosya PC'ye aktarıldı ({names_str}) → İndirilenler/RIFKI_AirDrop"
        self.publish_user(f"📲 AirDrop Gönderimi: {names_str}")
        self.publish_assistant(msg)
        try:
            from tools.notifications import send_notification
            send_notification("RIFKI AirDrop", f"Telefondan dosya alındı: {names_str}")
        except Exception:
            pass

        loop = asyncio.get_running_loop()
        files = await loop.run_in_executor(None, self._collect_airdrop_files)
        return web.json_response({
            "ok": True,
            "saved": saved_files,
            "reply": msg,
            "files": files,
        })

    async def _handle_transfer_download(self, request):
        from aiohttp import web
        if not self._token_ok(request):
            return web.Response(text="yetkisiz", status=401)

        raw_name = (request.rel_url.query.get("name") or "").strip()
        if not raw_name or any(sep in raw_name for sep in ("/", "\\", "..")):
            return web.Response(text="geçersiz dosya adı", status=400)

        folder = _airdrop_dir().resolve()
        target = (folder / raw_name).resolve()
        if target.parent != folder or not target.is_file():
            return web.Response(text="dosya bulunamadı", status=404)

        return web.FileResponse(
            target,
            headers={
                "Content-Disposition": f'attachment; filename="{target.name}"',
                "Cache-Control": "no-store",
            },
        )

    async def _handle_ws(self, request):
        from aiohttp import WSMsgType, web
        from tools import system

        if not self._token_ok(request):
            return web.Response(text="yetkisiz", status=401)
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        self._clients.add(ws)
        await ws.send_str(json.dumps({"type": "hello", **self.status_payload()}, ensure_ascii=False))
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except json.JSONDecodeError:
                        continue
                    mtype = data.get("type")
                    if mtype == "ping":
                        await ws.send_str(json.dumps({"type": "pong"}))
                    elif mtype == "mouse_move":
                        system.move_mouse_relative(int(data.get("dx") or 0), int(data.get("dy") or 0))
                    elif mtype == "mouse_click":
                        system.mouse_click(str(data.get("button") or "left"))
                    elif mtype == "mouse_scroll":
                        system.mouse_scroll(int(data.get("dy") or 0))
                    elif mtype == "screen_frame_request":
                        w = int(data.get("w") or 640)
                        q = int(data.get("q") or 45)
                        try:
                            loop = asyncio.get_running_loop()
                            jpeg = await loop.run_in_executor(
                                None,
                                lambda: system.capture_screenshot_for_mobile(
                                    max_width=w, quality=q, fast=True, all_screens=False
                                ),
                            )
                            if jpeg and not ws.closed:
                                await ws.send_bytes(jpeg)
                        except Exception as e:
                            log.debug(f"WS ekran çerçeve hatası: {e}")
                elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
        finally:
            self._clients.discard(ws)
        return ws


mobile_bridge = MobileBridge()
