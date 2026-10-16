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

    def set_listening(self, active: bool) -> None:
        self.listening = active
        self._broadcast({"type": "status", **self.status_payload()})

    def publish_state(self, state: str) -> None:
        self.state = state or self.state
        self._broadcast({"type": "status", **self.status_payload()})

    def publish_user(self, text: str) -> None:
        self.last_user = text
        self.history.append({"role": "user", "text": text})
        self._broadcast({"type": "user", "text": text, **self.status_payload()})

    def publish_assistant(self, text: str) -> None:
        self.last_assistant = text
        self.history.append({"role": "assistant", "text": text})
        self._broadcast({"type": "assistant", "text": text, **self.status_payload()})

    def publish_error(self, text: str) -> None:
        self.history.append({"role": "error", "text": text})
        self._broadcast({"type": "error", "text": text, **self.status_payload()})

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
        return True

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

        self._loop = asyncio.get_running_loop()
        app = web.Application()
        app.router.add_get("/", self._handle_index)
        app.router.add_get("/api/status", self._handle_status)
        app.router.add_post("/api/command", self._handle_command)
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
        return web.FileResponse(index)

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
