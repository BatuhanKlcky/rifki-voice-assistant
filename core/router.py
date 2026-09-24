"""
core/router.py
---------------
İki şeyi bir arada tutar:

1) TOOL_SCHEMAS: sağlayıcıdan bağımsız, düz JSON şema formatında, LLM'e
   "hangi araçları çağırabilirsin" bilgisini veren şema listesi.
2) TOOL_DISPATCH: tool adını gerçek Python fonksiyonuna eşleyen sözlük.

execute_tool(name, input, ask_fn) fonksiyonu:
- İstenen tool'un kritik olup olmadığını core/security.py ile kontrol eder.
- Kritikse onay ister; onay yoksa işlemi YAPMADAN iptal mesajı döner.
- Değilse doğrudan çalıştırır.
- Her durumda hatanın çıplak traceback olarak kullanıcıya gitmesini engeller.
"""

from typing import Callable, Optional

from core.logger import get_logger
from core.security import is_critical, confirm
from tools import applications, browser, filesystem, system, web, notifications, media
from tools import memory_tool

log = get_logger("router")


TOOL_SCHEMAS = [
    {
        "name": "open_application",
        "description": "Bilgisayarda bilinen bir uygulamayı açar (ör. chrome, notepad, spotify).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Uygulama adı"}},
            "required": ["name"],
        },
    },
    {
        "name": "close_application",
        "description": "Çalışan bir uygulamayı kapatır.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Uygulama adı"}},
            "required": ["name"],
        },
    },
    {
        "name": "open_url",
        "description": "Tarayıcıda belirli bir URL'yi açar.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "name": "open_browser",
        "description": "Varsayılan tarayıcıyı açar.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "open_youtube_search",
        "description": "YouTube'da bir arama sonucu sayfası açar.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "search_files",
        "description": "Belirli bir klasörde, adında bir anahtar kelime geçen dosyaları arar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Aranacak klasör yolu"},
                "keyword": {"type": "string"},
            },
            "required": ["folder", "keyword"],
        },
    },
    {
        "name": "create_file",
        "description": "Belirtilen yolda yeni bir dosya oluşturur.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "copy_file",
        "description": "Bir dosyayı başka bir konuma kopyalar.",
        "input_schema": {
            "type": "object",
            "properties": {"source": {"type": "string"}, "destination": {"type": "string"}},
            "required": ["source", "destination"],
        },
    },
    {
        "name": "move_file",
        "description": "Bir dosyayı başka bir konuma taşır.",
        "input_schema": {
            "type": "object",
            "properties": {"source": {"type": "string"}, "destination": {"type": "string"}},
            "required": ["source", "destination"],
        },
    },
    {
        "name": "rename_file",
        "description": "Bir dosyayı yeniden adlandırır.",
        "input_schema": {
            "type": "object",
            "properties": {"source": {"type": "string"}, "new_name": {"type": "string"}},
            "required": ["source", "new_name"],
        },
    },
    {
        "name": "delete_file",
        "description": "Bir dosyayı veya klasörü siler. GERİ DÖNÜŞÜ YOKTUR, onay gerektirir.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "open_path",
        "description": "Bir dosya veya klasörü varsayılan uygulamayla açar.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "get_system_status",
        "description": "CPU, RAM ve disk kullanımını özetler.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_datetime",
        "description": "Güncel tarih ve saati söyler.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "set_volume",
        "description": "Sistem ses seviyesini 0-100 arası bir değere ayarlar.",
        "input_schema": {
            "type": "object",
            "properties": {"level_percent": {"type": "integer"}},
            "required": ["level_percent"],
        },
    },
    {
        "name": "take_screenshot",
        "description": "Ekran görüntüsü alır ve kaydeder.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "shutdown_computer",
        "description": "Bilgisayarı kapatır. GERİ DÖNÜŞÜ YOKTUR, mutlaka onay gerektirir.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "restart_computer",
        "description": "Bilgisayarı yeniden başlatır. Onay gerektirir.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_web",
        "description": "İnternette güncel bilgi arar (haberler, genel bilgi, güncel gelişmeler).",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "send_notification",
        "description": "Ekranda bir masaüstü bildirimi gösterir.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "message": {"type": "string"}},
            "required": ["title", "message"],
        },
    },
    {
        "name": "set_reminder",
        "description": "Bir hatırlatıcı kurmaya çalışır (NOT: bu özellik henüz tam çalışmıyor).",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}, "when": {"type": "string"}},
            "required": ["message", "when"],
        },
    },
    {
        "name": "play_media",
        "description": "Müzik/video çalmayı dener (NOT: bu özellik henüz tam çalışmıyor).",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "remember_fact",
        "description": "Kullanıcının 'bunu hatırla' dediği bir bilgiyi uzun süreli hafızaya kaydeder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Bilginin kısa etiketi, ör. 'favori_dil'"},
                "value": {"type": "string", "description": "Hatırlanacak bilginin kendisi"},
            },
            "required": ["key", "value"],
        },
    },
    {
        "name": "recall_fact",
        "description": "Uzun süreli hafızadan daha önce kaydedilmiş bir bilgiyi getirir.",
        "input_schema": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
    {
        "name": "forget_fact",
        "description": "Uzun süreli hafızadan bir bilgiyi siler.",
        "input_schema": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
]

TOOL_DISPATCH = {
    "open_application": applications.open_application,
    "close_application": applications.close_application,
    "open_url": browser.open_url,
    "open_browser": browser.open_browser,
    "open_youtube_search": browser.open_youtube_search,
    "search_files": filesystem.search_files,
    "create_file": filesystem.create_file,
    "copy_file": filesystem.copy_file,
    "move_file": filesystem.move_file,
    "rename_file": filesystem.rename_file,
    "delete_file": filesystem.delete_file,
    "open_path": filesystem.open_path,
    "get_system_status": system.get_system_status,
    "get_datetime": system.get_datetime,
    "set_volume": system.set_volume,
    "take_screenshot": system.take_screenshot,
    "shutdown_computer": system.shutdown_computer,
    "restart_computer": system.restart_computer,
    "search_web": web.search_web,
    "send_notification": notifications.send_notification,
    "set_reminder": notifications.set_reminder,
    "play_media": media.play_media,
    "remember_fact": memory_tool.remember_fact,
    "recall_fact": memory_tool.recall_fact,
    "forget_fact": memory_tool.forget_fact,
}


def execute_tool(
    name: str,
    tool_input: dict,
    ask_fn: Optional[Callable[[str], str]] = None,
) -> str:
    fn = TOOL_DISPATCH.get(name)
    if fn is None:
        log.error(f"Bilinmeyen tool çağrıldı: {name}")
        return f"'{name}' adında bir araç tanımlı değil."

    if is_critical(name):
        prompt = f"'{name}' işlemini gerçekleştirmemi onaylıyor musun?"
        if not confirm(prompt, ask_fn=ask_fn):
            log.info(f"Kritik işlem onaylanmadı: {name}")
            return "İşlemi onaylamadığın için gerçekleştirmedim."

    try:
        result = fn(**tool_input)
        log.info(f"Tool çalıştı: {name}({tool_input}) -> {result}")
        return result
    except TypeError as e:
        log.error(f"Tool parametre hatası ({name}): {e}")
        return "Bu işlem için gereken bilgiler eksik ya da hatalı."
    except Exception as e:
        log.error(f"Tool çalıştırma hatası ({name}): {e}")
        return "Bu işlemi gerçekleştirirken beklenmeyen bir sorun oluştu."