"""
tools/memory_tool.py
---------------------
core/memory.py'deki LongTermMemory'yi LLM'in tool-calling ile çağırabileceği
basit fonksiyonlara sarar (ince bir "adapter" katmanı).
"""

from core.memory import long_term_memory


def remember_fact(key: str, value: str) -> str:
    return long_term_memory.remember(key, value)


def recall_fact(key: str) -> str:
    value = long_term_memory.recall(key)
    if value is None:
        return f"'{key}' ile ilgili hafızamda bir kayıt bulamadım."
    return value


def forget_fact(key: str) -> str:
    return long_term_memory.forget(key)
