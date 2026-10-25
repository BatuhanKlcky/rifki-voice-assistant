"""
core/memory.py
---------------
İki katmanlı akıllı hafıza sistemi:

1) Kısa süreli hafıza (ShortTermMemory): RAM'de son konuşma bağlamını tutar.
2) Uzun süreli anlamsal hafıza (LongTermMemory): SQLite tabanlı kalıcı bilgi
   ve not defteri. Anahtar-değer gerçekleri (facts) ve yapılandırılmış notları (notes) saklar.
   Anahtar kelime ve anlamsal eşleşmeyle kullanıcının önceki kayıtlarını hatırlar.
"""

from __future__ import annotations

import re
import sqlite3
from collections import deque
from pathlib import Path
from typing import Any, Optional

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
            # 1. Gerçekler / Tercihler (Facts)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS facts (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # 2. Not Defteri / Fikirler (Notes)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def remember(self, key: str, value: str) -> str:
        clean_key = key.strip().lower()
        clean_val = value.strip()
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO facts (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value, created_at=CURRENT_TIMESTAMP",
                    (clean_key, clean_val),
                )
                conn.commit()
            log.info(f"Hafızaya kaydedildi: {clean_key} = {clean_val}")
            return f"'{key}' bilgisini hafızama kaydettim."
        except Exception as e:
            log.error(f"Hafızaya yazma hatası: {e}")
            return "Bunu hafızama kaydederken bir sorun oluştu."

    def recall(self, key: str) -> Optional[str]:
        clean_key = key.strip().lower()
        try:
            with self._connect() as conn:
                # 1. Tam eşleşme
                cur = conn.execute("SELECT value FROM facts WHERE key = ?", (clean_key,))
                row = cur.fetchone()
                if row:
                    return row[0]

                # 2. Kısmi / LIKE eşleşmesi
                cur = conn.execute(
                    "SELECT key, value FROM facts WHERE key LIKE ? OR ? LIKE ('%' || key || '%')",
                    (f"%{clean_key}%", clean_key),
                )
                row = cur.fetchone()
                if row:
                    return row[1]
                return None
        except Exception as e:
            log.error(f"Hafıza okuma hatası: {e}")
            return None

    def forget(self, key: str) -> str:
        clean_key = key.strip().lower()
        try:
            with self._connect() as conn:
                cur = conn.execute("DELETE FROM facts WHERE key = ?", (clean_key,))
                conn.commit()
                if cur.rowcount:
                    return f"'{key}' bilgisini hafızamdan sildim."
                return f"'{key}' diye bir kayıt bulamadım."
        except Exception as e:
            log.error(f"Hafıza silme hatası: {e}")
            return "Bunu hafızamdan silerken bir sorun oluştu."

    def search_facts(self, query: str) -> list[tuple[str, str]]:
        """Sorgu kelimelerine göre tüm kayıtlı gerçekler arasında arama yapar."""
        tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) >= 2]
        if not tokens:
            return self.list_all()[:5]

        results = []
        with self._connect() as conn:
            cur = conn.execute("SELECT key, value FROM facts")
            for k, v in cur.fetchall():
                text = f"{k} {v}".lower()
                score = sum(1 for tok in tokens if tok in text)
                if score > 0:
                    results.append((score, k, v))

        results.sort(key=lambda x: x[0], reverse=True)
        return [(k, v) for _, k, v in results[:6]]

    def list_all(self) -> list[tuple[str, str]]:
        with self._connect() as conn:
            cur = conn.execute("SELECT key, value FROM facts ORDER BY created_at DESC")
            return cur.fetchall()

    def get_known_facts_summary(self, limit: int = 12) -> str:
        """Sistem promptuna doğrudan beslenecek kullanıcı gerçekleri özeti."""
        facts = self.list_all()[:limit]
        if not facts:
            return ""
        lines = [f"- {k}: {v}" for k, v in facts]
        return "\n".join(lines)

    # --- Not Defteri İşlemleri ---
    def add_note(self, title: str, content: str, tags: str = "") -> str:
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO notes (title, content, tags) VALUES (?, ?, ?)",
                    (title.strip(), content.strip(), tags.strip()),
                )
                conn.commit()
            return f"'{title}' başlıklı not başarıyla kaydedildi."
        except Exception as e:
            log.error(f"Not ekleme hatası: {e}")
            return "Not kaydedilirken bir sorun oluştu."

    def search_notes(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        tokens = [t.lower() for t in re.findall(r"\w+", query) if len(t) >= 2]
        notes = []
        with self._connect() as conn:
            cur = conn.execute("SELECT id, title, content, tags, created_at FROM notes ORDER BY id DESC")
            for nid, title, content, tags, created_at in cur.fetchall():
                full_text = f"{title} {content} {tags}".lower()
                score = sum(1 for tok in tokens if tok in full_text) if tokens else 1
                if score > 0 or not tokens:
                    notes.append({
                        "id": nid,
                        "title": title,
                        "content": content,
                        "tags": tags,
                        "created_at": created_at,
                        "_score": score,
                    })
        notes.sort(key=lambda x: x["_score"], reverse=True)
        return notes[:limit]


short_term_memory = ShortTermMemory()
long_term_memory = LongTermMemory()
