"""
tools/memory_tool.py
---------------------
core/memory.py'deki LongTermMemory katmanını LLM araçlarına (Tool Calling) bağlar.
"""

from __future__ import annotations

from core.memory import long_term_memory


def remember_fact(key: str, value: str, *args, **kwargs) -> str:
    """Kullanıcının 'bunu hatırla' dediği bir bilgiyi uzun süreli hafızaya kaydeder."""
    return long_term_memory.remember(key, value)


def recall_fact(key: str, *args, **kwargs) -> str:
    """Uzun süreli hafızadan daha önce kaydedilmiş bir bilgiyi getirir."""
    value = long_term_memory.recall(key)
    if value is None:
        # Doğrudan eşleşmezse anlamsal aramayı dene
        results = long_term_memory.search_facts(key)
        if results:
            lines = [f"{k}: {v}" for k, v in results[:3]]
            return "Hafızamda bunlara rastladım:\n" + "\n".join(lines)
        return f"'{key}' ile ilgili hafızamda bir kayıt bulamadım."
    return value


def forget_fact(key: str, *args, **kwargs) -> str:
    """Uzun süreli hafızadan bir bilgiyi siler."""
    return long_term_memory.forget(key)


def search_memories(query: str, *args, **kwargs) -> str:
    """Hafızadaki tüm kaydedilmiş bilgi ve notlarda arama yapar."""
    facts = long_term_memory.search_facts(query)
    notes = long_term_memory.search_notes(query, limit=3)

    out = []
    if facts:
        out.append("Bilinen Gerçekler:")
        out.extend(f"• {k}: {v}" for k, v in facts)
    if notes:
        out.append("İlgili Notlar:")
        out.extend(f"• [{n['title']}]: {n['content']}" for n in notes)

    if not out:
        return f"'{query}' konusunda hafızamda hiçbir kayıt veya not bulamadım."
    return "\n".join(out)


def save_note(title: str, content: str, tags: str = "", *args, **kwargs) -> str:
    """Kullanıcının söylediği bir notu veya fikri not defterine kaydeder."""
    return long_term_memory.add_note(title, content, tags)


def search_notes(query: str, *args, **kwargs) -> str:
    """Not defterinde arama yapar."""
    notes = long_term_memory.search_notes(query)
    if not notes:
        return f"'{query}' içeren bir not bulunamadı."
    lines = [f"• [{n['title']}]: {n['content']} (Tarih: {n['created_at']})" for n in notes]
    return "\n".join(lines)


def list_all_memories(*args, **kwargs) -> str:
    """Hafızada kullanıcı hakkında kayıtlı olan tüm bilgileri listeler."""
    facts = long_term_memory.list_all()
    if not facts:
        return "Şu anda hafızamda kayıtlı herhangi bir kişisel bilgi bulunmuyor."
    lines = [f"• {k}: {v}" for k, v in facts]
    return "Hafızamda seninle ilgili kayıtlı olan bilgiler:\n" + "\n".join(lines)
