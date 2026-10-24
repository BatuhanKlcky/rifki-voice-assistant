"""
bridge/service.py
-----------------
Yerel aiohttp sunucusu: mobil PWA, durum API'si, komut POST, WebSocket.
Dışarıya doğrudan açılmaz (127.0.0.1); Cloudflare Tunnel bağlanır.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger("bridge")

CommandHandler = Callable[[str], str]


def _static_dir() -> Path:
    here = Path(__file__).resolve().parent / "static"
    if here.is_dir():
        return here
    # PyInstaller: bridge/static _MEIPASS altında
    import sys

    if getattr(sys, "frozen", False):
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        candidate = meipass / "bridge" / "static"
        if candidate.is_dir():
            return candidate
    return here


class MobileBridge:
    def __init__(self) -> None:
        self.state = "OFF"
        self.listening = False
        self.last_user = ""
        self.last_assistant = ""
        self.history: list[dict[str, str]] = []
        self._clients: set[Any] = set()
        self._command_handler: Optional[CommandHandler] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._runner = None
        self._site = None
        self._stop = threading.Event()

    def set_command_handler(self, handler: CommandHandler) -> None:
        self._command_handler = handler

    def status_payload(self) -> dict:
        return {
            "state": self.state,
            "listening": self.listening,
            "last_user": self.last_user,
            "last_assistant": self.last_assistant,
            "history": list(self.history[-40:]),
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
        async def _cache_headers(request, handler):
            resp = await handler(request)
            path = request.path or ""
            if path.startswith("/static/"):
                resp.headers["Cache-Control"] = "public, max-age=300"
            elif path in ("/", "/index.html") or path.endswith("index.html"):
                resp.headers["Cache-Control"] = "no-cache"
            return resp

        self._loop = asyncio.get_running_loop()
        app = web.Application(middlewares=[_cache_headers])
        app.router.add_get("/", self._handle_index)
        app.router.add_get("/api/status", self._handle_status)
        app.router.add_post("/api/command", self._handle_command)
        app.router.add_get("/api/screenshot", self._handle_screenshot)
        app.router.add_get("/api/apps", self._handle_apps)
        app.router.add_post("/api/apps/launch", self._handle_apps_launch)
        app.router.add_post("/api/remote", self._handle_remote)
        app.router.add_get("/api/volume", self._handle_volume)
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

    def _token_ok(self, request) -> bool:
        expected = settings.MOBILE_BRIDGE_TOKEN.strip()
        if not expected:
            return False
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
            if secrets.compare_digest(got, expected):
                return True
        q = request.rel_url.query.get("token", "")
        if q and secrets.compare_digest(q, expected):
            return True
        return False

    async def _handle_index(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            # Sayfa token'ı query veya localStorage ile alacak; ilk girişte
            # token yoksa yine de HTML ver (JS 401 gösterir). Query yoksa da
            # HTML servis edilir — API korumalı kalır.
            pass
        index = _static_dir() / "index.html"
        if not index.is_file():
            return web.Response(text="Mobil panel bulunamadı.", status=500)
        return web.FileResponse(
            index,
            headers={"Cache-Control": "no-cache"},
        )

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
        text = (body.get("text") or "").strip()
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
        if live:
            max_width = min(max_width, 960)
            quality = min(quality, 55)

        loop = asyncio.get_running_loop()
        try:
            from tools.system import capture_screenshot_for_mobile

            jpeg = await loop.run_in_executor(
                None,
                lambda: capture_screenshot_for_mobile(max_width, quality),
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
                "Cache-Control": "no-store",
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
            status = 400 if result.get("needs_confirm") else 400
            if "bilinmeyen" in (result.get("error") or ""):
                status = 400
            return web.json_response(result, status=status)

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
        }.get(action, action)
        # Güç işlemlerini sohbette göster; sık ses/medya spam olmasın
        if action in ("lock", "sleep", "shutdown", "restart", "open_url", "cancel_shutdown"):
            self.publish_user(label)
            if reply:
                self.publish_assistant(reply)
        return web.json_response(result)

    async def _handle_apps(self, request):
        from aiohttp import web

        if not self._token_ok(request):
            return web.json_response({"error": "yetkisiz"}, status=401)
        q = (request.rel_url.query.get("q") or "").strip()
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
        name = (body.get("name") or "").strip()
        if not name:
            return web.json_response({"error": "uygulama adı gerekli"}, status=400)
        # Ham yol / AppID kabul etme — yalnızca katalog adı
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

    async def _handle_ws(self, request):
        from aiohttp import WSMsgType, web

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
                    if data.get("type") == "ping":
                        await ws.send_str(json.dumps({"type": "pong"}))
                elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
        finally:
            self._clients.discard(ws)
        return ws


mobile_bridge = MobileBridge()
