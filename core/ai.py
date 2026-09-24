"""
core/ai.py
----------
RIFKI'nın "beyni". Google Gemini API'sini (google-genai SDK) tool-calling
(function calling) mantığıyla kullanır:

1) Kullanıcı mesajı Gemini'ye gönderilir (konuşma geçmişi, Gemini'nin kendi
   "Chat" nesnesi tarafından oturum boyunca otomatik tutulur).
2) Gemini ya doğrudan metin döner, ya da bir/birden çok fonksiyon çağırmak
   ister (response.function_calls doluysa).
3) İstenen tool'lar core/router.py üzerinden çalıştırılır, sonuçları
   FunctionResponse olarak tekrar Gemini'ye gönderilir.
4) Gemini nihai, doğal Türkçe cevabı üretene kadar bu döngü devam eder
   (maks. MAX_TOOL_ITERATIONS kez; sonsuz döngüyü önlemek için).

NOT: tools/router.py içindeki TOOL_SCHEMAS, sağlayıcıdan bağımsız (düz JSON
şema) formatta tutuluyor; bu dosya sadece onu Gemini'nin beklediği
FunctionDeclaration/Schema nesnelerine çevirir (_build_gemini_tools).
Yarın başka bir LLM'e geçmek istersen sadece bu dosyayı değiştirmen yeterli,
core/router.py ve tools/ klasörüne dokunmana gerek kalmaz.
"""

from typing import Callable, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError, ClientError

from config.settings import settings
from core.logger import get_logger
from core.memory import short_term_memory
from core.router import TOOL_SCHEMAS, execute_tool

log = get_logger("ai")

MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = """Senin adın RIFKI. Kullanıcının Türkçe konuşan, bilgisayarında \
güvenli işlemler yapabilen kişisel yapay zekâ asistanısın. Google Gemini \
tarafından güçlendiriliyorsun.

ÇOK ÖNEMLİ: HER ZAMAN Türkçe cevap ver. Kullanıcının mesajı başka bir dilde \
yazılmış/algılanmış olsa bile, düşünmen İngilizce olsa bile, kullanıcıya \
verdiğin NİHAİ cevap her zaman Türkçe olmalı. Asla İngilizce (veya başka bir \
dilde) cevap verme.

Konuşma tarzın: doğal, kısa, profesyonel, akıllı, hafif esprili ve yardımsever. \
Gereksiz uzun cevaplar verme; gerektiğinde tek cümlelik net cevaplar yeterlidir.

Kurallar:
- Bir işlem yapmak için gereken bilgi eksikse, fonksiyon çağırmadan ÖNCE \
kullanıcıya kısa bir soru sor.
- Kritik/geri dönüşü zor işlemler (bilgisayarı kapatma, dosya silme, sistem \
ayarlarını değiştirme vb.) zaten sistem tarafından onay istenerek korunuyor; \
sen yine de kullanıcıya ne yapacağını net şekilde söyle.
- Bir fonksiyon sonucu hata veya "sorun oluştu" içeriyorsa, bunu kullanıcıya \
teknik jargon olmadan, anlaşılır şekilde ilet.
- Uydurma bilgi verme; güncel/bilmediğin bir şey sorulursa search_web \
aracını kullan.
"""

_JSON_TO_GEMINI_TYPE = {
    "string": "STRING",
    "integer": "INTEGER",
    "number": "NUMBER",
    "boolean": "BOOLEAN",
    "object": "OBJECT",
    "array": "ARRAY",
}


def _json_schema_to_gemini_schema(schema: dict) -> types.Schema:
    """core/router.py'deki düz JSON-şema sözlüklerini Gemini'nin
    types.Schema nesnesine çevirir. Sadece bizim tool şemalarımızın
    ihtiyaç duyduğu kadarını (object/properties/required, basit tipler)
    destekler; genel amaçlı tam bir JSON-Schema dönüştürücü değildir."""
    gemini_type = _JSON_TO_GEMINI_TYPE.get(schema.get("type", "object"), "OBJECT")

    if gemini_type == "OBJECT":
        properties = {
            key: _json_schema_to_gemini_schema(value)
            for key, value in schema.get("properties", {}).items()
        }
        return types.Schema(
            type=gemini_type,
            properties=properties,
            required=schema.get("required", []),
        )

    if gemini_type == "ARRAY":
        items_schema = schema.get("items", {"type": "string"})
        return types.Schema(type=gemini_type, items=_json_schema_to_gemini_schema(items_schema))

    kwargs = {"type": gemini_type}
    if "description" in schema:
        kwargs["description"] = schema["description"]
    return types.Schema(**kwargs)


def _build_gemini_tools() -> list:
    declarations = []
    for schema in TOOL_SCHEMAS:
        declarations.append(
            types.FunctionDeclaration(
                name=schema["name"],
                description=schema.get("description", ""),
                parameters=_json_schema_to_gemini_schema(schema.get("input_schema", {"type": "object", "properties": {}})),
            )
        )
    return [types.Tool(function_declarations=declarations)]


class RifkiBrain:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            log.warning("GEMINI_API_KEY tanımlı değil; AI çağrıları başarısız olacak.")
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._gemini_tools = _build_gemini_tools()
        self.chat = self._new_chat()

    def _new_chat(self):
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=self._gemini_tools,
        )
        return self.client.chats.create(model=settings.GEMINI_MODEL, config=config)

    def reset_conversation(self):
        """Kısa süreli hafızayı ve Gemini sohbet oturumunu sıfırlar."""
        short_term_memory.clear()
        self.chat = self._new_chat()

    def process(
        self,
        user_text: str,
        ask_fn: Optional[Callable[[str], str]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        user_text: kullanıcının söylediği/yazdığı şey.
        ask_fn: kritik onaylar için kullanıcıya soru sormayı sağlayan callback.
        status_callback: UI'a "THINKING", "PROCESSING" gibi durum bildirmek için.
        Döner: RIFKI'nın nihai doğal dil cevabı (TTS ile okunacak).

        NOT: Konuşma bağlamı Gemini'nin kendi Chat nesnesi tarafından oturum
        boyunca otomatik tutulur; short_term_memory burada ayrıca bir
        transkript/log kaydı olarak tutulur (ör. ileride UI geçmişini
        yeniden yüklemek istersen kullanılabilir).
        """
        short_term_memory.add("user", user_text)

        if status_callback:
            status_callback("THINKING")

        log.info(f"Gemini'ye gönderiliyor: '{user_text}'")
        try:
            response = self.chat.send_message(user_text)
            log.info("Gemini'den ilk yanıt alındı.")
        except ClientError as e:
            log.error(f"Gemini istemci hatası: {e}")
            if getattr(e, "code", None) == 404:
                return (
                    f"Kullanmaya çalıştığım model ('{settings.GEMINI_MODEL}') artık mevcut değil. "
                    ".env dosyasındaki GEMINI_MODEL değerini güncel bir modelle değiştirmen gerekiyor "
                    "(https://ai.google.dev/gemini-api/docs/models adresinden kontrol edebilirsin)."
                )
            if getattr(e, "code", None) == 429:
                return (
                    "Google'ın ücretsiz kotasını aştım (günlük istek sınırına ulaştım). "
                    "Biraz bekleyip tekrar deneyebilirsin, ya da Google AI Studio'dan "
                    "faturalandırmayı etkinleştirip kotanı artırabilirsin "
                    "(https://ai.google.dev/gemini-api/docs/rate-limits)."
                )
            if getattr(e, "code", None) in (401, 403):
                return "API anahtarım geçersiz görünüyor. Lütfen .env dosyasındaki GEMINI_API_KEY değerini kontrol et."
            return "Yapay zekâ servisinden beklenmeyen bir yanıt aldım."
        except APIError as e:
            log.error(f"Gemini API hatası: {e}")
            return "Yapay zekâ servisine şu anda ulaşamıyorum."
        except Exception as e:
            log.error(f"Beklenmeyen AI bağlantı hatası: {e}")
            return "Yapay zekâ servisine şu anda ulaşamıyorum. İnternet bağlantını kontrol eder misin?"

        iterations = 0
        while response.function_calls and iterations < MAX_TOOL_ITERATIONS:
            iterations += 1
            if status_callback:
                status_callback("PROCESSING")

            function_response_parts = []
            for call in response.function_calls:
                args = dict(call.args) if call.args else {}
                log.info(f"Fonksiyon çağrısı: {call.name}({args})")
                result_text = execute_tool(call.name, args, ask_fn=ask_fn)
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={"result": result_text},
                    )
                )

            try:
                response = self.chat.send_message(function_response_parts)
            except Exception as e:
                log.error(f"Fonksiyon-sonrası AI çağrısı hatası: {e}")
                return "İşlemi gerçekleştirdim ama sonucu senle paylaşırken bir sorunla karşılaştım."

        final_text = (response.text or "").strip()
        if not final_text:
            final_text = "İşlemi tamamladım."

        log.info(f"Nihai cevap üretildi: '{final_text}'")
        short_term_memory.add("assistant", final_text)
        if status_callback:
            status_callback("SPEAKING")

        return final_text


rifki_brain = RifkiBrain()