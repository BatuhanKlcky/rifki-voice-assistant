"""
tools/web.py
------------
Güncel bilgi arama. DuckDuckGo'nun resmi olmayan ama yaygın kullanılan
"duckduckgo-search" kütüphanesi ile metin araması yapılır (API anahtarı
gerektirmez). Sonuçlar ham metin olarak döner; bunları doğal Türkçe cümleye
çeviren adım core/ai.py içinde LLM tarafından yapılır (bu fonksiyon sadece
ham veriyi getirir, yorumlamaz).

NOT (dürüst sınırlama): Bu, "gerçek zamanlı borsa/kripto API'si" değildir;
genel amaçlı bir metin arama sonucudur. Bitcoin fiyatı gibi çok hassas /
anlık veriler için ileride özel bir finans API'si (ör. CoinGecko) eklemen
daha güvenilir olur — bu MVP'de o entegrasyon YOK, TODO olarak bırakıldı.
"""

from core.logger import get_logger

log = get_logger("tools.web")


def search_web(query: str, max_results: int = 5) -> str:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "Web arama kütüphanesi (duckduckgo-search) kurulu değil."

    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, region="tr-tr", max_results=max_results):
                title = r.get("title", "")
                body = r.get("body", "")
                href = r.get("href", "")
                results.append(f"- {title}: {body} ({href})")

        if not results:
            return f"'{query}' için sonuç bulunamadı."

        return "\n".join(results)
    except Exception as e:
        log.error(f"Web arama hatası: {e}")
        return "İnternette arama yaparken bir sorun oluştu. İnternet bağlantısını kontrol et."
