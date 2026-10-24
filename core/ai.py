"""
core/ai.py
----------
Yerel OmniRoute (localhost:20128) üzerinden çalışan yapay zekâ bağlantısı.

Sohbetin yanında OpenAI uyumlu tool calling kullanır: model bir işlem
isterse core/router.execute_tool ile gerçek aracı çalıştırır, sonucu geri
verir ve sesli okunacak kısa Türkçe cümleyi alır.
"""

import json
import os
import re

import requests
from dotenv import load_dotenv

from config.settings import settings
from core.logger import get_logger
from core.router import TOOL_SCHEMAS, execute_tool

load_dotenv(dotenv_path=settings.BASE_DIR / ".env")
log = get_logger("core.ai")

_MAX_ROUNDS = 4
_MAX_TOOL_CALLS = 6
_HISTORY_LIMIT = 8


def _openai_tools():
    tools = []
    for schema in TOOL_SCHEMAS:
        parameters = schema.get("input_schema") or {"type": "object", "properties": {}}
        tools.append({
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema.get("description", ""),
                "parameters": parameters,
            },
        })
    return tools


def _parse_arguments(raw):
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except json.JSONDecodeError:
            return {}
    return parsed if isinstance(parsed, dict) else {}


def _strip_think(text: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return cleaned or text.strip()


def _message_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get("text") or ""))
        content = "\n".join(part for part in parts if part)
    if content is None:
        return ""
    return _strip_think(str(content))


def _tool_calls_of(message: dict):
    calls = message.get("tool_calls") or []
    if calls:
        return calls
    legacy = message.get("function_call")
    if isinstance(legacy, dict) and legacy.get("name"):
        return [{
            "id": "legacy-call",
            "type": "function",
            "function": {
                "name": legacy.get("name"),
                "arguments": legacy.get("arguments") or {},
            },
        }]
    return []


class OmniRouteAI:
    def __init__(self):
        self.api_key = os.getenv("OMNIROUTE_API_KEY", "")
        self.model_name = os.getenv("OMNIROUTE_MODEL", "antigravity/gemini-3.6-flash-high")
        raw_url = os.getenv("OMNIROUTE_URL", "http://127.0.0.1:20128/v1/chat/completions")
        # Windows: localhost çoğu zaman ::1; OmniRoute genelde yalnız IPv4 dinler.
        self.api_url = (raw_url or "").replace("://localhost", "://127.0.0.1")
        self._tools = _openai_tools()
        self._history = []
        self.system_prompt = (
            "Sen RIFKI adlı masaüstü sesli asistanısın. Yanıtların sesli okunur: "
            "kısa, net, günlük Türkçe kur. "
            "Kullanıcı bilgisayarda bir işlem istiyorsa ilgili aracı çağır ve "
            "işlemi yapmadan yaptığını söyleme. Araç sonucunu aldıktan sonra "
            "ne olduğunu bir veya iki cümleyle anlat. "
            "Sohbet, açıklama ve fikir sorularında araç çağırma. "
            "Birden fazla işlem varsa araçları sırayla çağır."
        )

    def process(self, prompt: str, ask_fn=None, status_callback=None) -> str:
        try:
            if status_callback:
                status_callback("THINKING")

            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self._history)
            messages.append({"role": "user", "content": prompt})

            use_tools = True
            tool_runs = 0
            last_tool_text = ""

            for _round in range(_MAX_ROUNDS):
                try:
                    data = self._complete(messages, use_tools=use_tools)
                except _ToolsUnsupported:
                    if not use_tools:
                        raise
                    log.warning("Sunucu araç çağrısını kabul etmedi; düz sohbet kullanılıyor.")
                    use_tools = False
                    messages = [
                        item for item in messages
                        if item.get("role") != "tool" and "tool_calls" not in item
                    ]
                    continue

                choice = (data.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                calls = _tool_calls_of(message) if use_tools else []
                if not calls:
                    text = _message_text(message) or last_tool_text or "Tamam."
                    self._remember(prompt, text)
                    log.info(f"Rıfkı Yanıtı Hazır: {text[:50]}...")
                    return text

                if status_callback:
                    status_callback("PROCESSING")

                messages.append({
                    "role": "assistant",
                    "content": message.get("content") or "",
                    "tool_calls": calls,
                })
                for call in calls:
                    if tool_runs >= _MAX_TOOL_CALLS:
                        break
                    tool_runs += 1
                    function = call.get("function") or {}
                    name = function.get("name") or ""
                    arguments = _parse_arguments(function.get("arguments"))
                    log.info(f"Araç çağrısı: {name} {arguments}")
                    result = execute_tool(name, arguments, ask_fn=ask_fn)
                    last_tool_text = str(result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.get("id") or name or "call",
                        "content": last_tool_text,
                    })

            fallback = last_tool_text or "İşlemi tamamlayamadım."
            self._remember(prompt, fallback)
            return fallback

        except requests.exceptions.ConnectionError as e:
            log.error(f"Kritik İletişim Hatası: {e}")
            return "Yapay zekâ servisine ulaşamıyorum. OmniRoute kapalı olabilir."
        except requests.exceptions.ReadTimeout:
            log.error("İstek zaman aşımına uğradı!")
            return "Bağlantı zaman aşımına uğradı."
        except _OmniHttpError as e:
            return self._http_error_message(e.status, e.detail)
        except Exception as e:
            # _OmniHttpError kaçarsa veya eski sarmalayıcılar
            if isinstance(e, _OmniHttpError):
                return self._http_error_message(e.status, e.detail)
            detail = str(e)
            match = re.search(r"\bHTTP\s+(\d{3})\b", detail, flags=re.IGNORECASE)
            if match:
                return self._http_error_message(int(match.group(1)), detail)
            log.error(f"Kritik İletişim Hatası: {e}", exc_info=True)
            return f"Bir hata oluştu: {detail[:160]}"

    @staticmethod
    def _http_error_message(status: int, detail: str) -> str:
        text = (detail or "").lower()
        log.error(f"OmniRoute HTTP {status}: {(detail or '')[:200]}")
        if status == 429:
            return "Yapay zekâ kotası doldu; biraz sonra tekrar dene."
        if status in (401, 403):
            return (
                "OmniRoute'da yapay zekâ sağlayıcı oturumu yok. "
                "OmniRoute penceresini aç → Antigravity veya Google ile giriş yap → "
                "sonra RIFKI'yi yeniden dene. "
                "(.env içindeki OMNIROUTE_MODEL şu an: antigravity/... olabilir)"
            )
        if status == 404:
            return "Seçili yapay zekâ modeli yok veya kapalı. .env içindeki OMNIROUTE_MODEL değerini değiştir."
        return f"Yapay zekâ servisi hata verdi ({status})."

    def _complete(self, messages, use_tools: bool) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
        }
        if use_tools:
            payload["tools"] = self._tools
            payload["tool_choice"] = "auto"

        log.info(f"OmniRoute'a {self.model_name} ile istek iletiliyor...")
        response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
        # Model/credential hatalarını "tools unsupported" sanma.
        if use_tools and response.status_code in (400, 422):
            body = (response.text or "").lower()
            if "tool" in body or "function" in body or "schema" in body:
                log.error(
                    f"OmniRoute araç isteğini reddetti ({response.status_code}): "
                    f"{response.text[:300]}"
                )
                raise _ToolsUnsupported()
        if not response.ok:
            log.error(f"OmniRoute Hata Detayı ({response.status_code}): {response.text}")
            raise _OmniHttpError(response.status_code, response.text or "")
        try:
            return response.json()
        except ValueError as e:
            log.error(f"JSON İşleme Hatası: {e} | Gelen cevap: {response.text[:200]}")
            raise

    def _remember(self, user_text: str, assistant_text: str):
        self._history.append({"role": "user", "content": user_text})
        self._history.append({"role": "assistant", "content": assistant_text})
        if len(self._history) > _HISTORY_LIMIT:
            self._history = self._history[-_HISTORY_LIMIT:]


class _ToolsUnsupported(Exception):
    pass


class _OmniHttpError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail or ""
        super().__init__(f"HTTP {status}: {self.detail[:180]}")


rifki_brain = OmniRouteAI()
