"""
core/memory.py
---------------
İki katmanlı hafıza:

1) Kısa süreli hafıza (ShortTermMemory): sadece RAM'de, mevcut konuşmanın
   bağlamını (son N mesaj) tutar. Uygulama kapanınca silinir.

2) Uzun süreli hafıza (LongTermMemory): SQLite tabanlı basit key-value store.
   Kullanıcı "bunu hatırla" dediğinde LLM, remember_fact tool'unu çağırır ve
   burada kalıcı olarak saklanır. "Bunu unut" dediğinde forget_fact ile silinir.

Depolama katmanı bilinçli olarak SQLite ile sınırlı tutuldu; ileride bunu
başka bir veritabanına (ör. PostgreSQL, vektör DB) taşımak istersen sadece bu
dosyayı değiştirmen yeterli — geri kalan sistem LongTermMemory arayüzünü kullanıyor.
"""

import sqlite3
from collections import deque
from pathlib import Path
from typing import Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger("memory")


class ShortTermMemory:
    def __init__(self, max_turns: int = 12):
        self._buffer = deque(maxlen=max_turns)

    def add(self, role: str, content: str):
        self._buffer.append({"role": role, "content": content})

    def get_history(self) -> list:
        return list(self._buffer)

    def clear(self):
        self._buffer.clear()


class LongTermMemory:
    def __init__(self, db_path: Path = settings.DB_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def remember(self, key: str, value: str) -> str:
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO facts (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key.strip().lower(), value.strip()),
                )
                conn.commit()
            log.info(f"Hafızaya kaydedildi: {key} = {value}")
            return f"'{key}' bilgisini hafızama kaydettim."
        except Exception as e:
            log.error(f"Hafızaya yazma hatası: {e}")
            return "Bunu hafızama kaydederken bir sorun oluştu."

    def recall(self, key: str) -> Optional[str]:
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "SELECT value FROM facts WHERE key = ?", (key.strip().lower(),)
                )
                row = cur.fetchone()
                return row[0] if row else None
        except Exception as e:
            log.error(f"Hafıza okuma hatası: {e}")
            return None

    def forget(self, key: str) -> str:
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "DELETE FROM facts WHERE key = ?", (key.strip().lower(),)
                )
                conn.commit()
                if cur.rowcount:
                    return f"'{key}' bilgisini hafızamdan sildim."
                return f"'{key}' diye bir kayıt bulamadım."
        except Exception as e:
            log.error(f"Hafıza silme hatası: {e}")
            return "Bunu hafızamdan silerken bir sorun oluştu."

    def list_all(self) -> list:
        with self._connect() as conn:
            cur = conn.execute("SELECT key, value FROM facts ORDER BY created_at DESC")
            return cur.fetchall()


short_term_memory = ShortTermMemory()
long_term_memory = LongTermMemory()
