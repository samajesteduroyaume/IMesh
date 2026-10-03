import sqlite3
import threading
from pathlib import Path
from typing import Any


class GatewayDB:
    def __init__(self, db_path: str | Path = "./openclaw_gateway.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    key TEXT PRIMARY KEY,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    enabled INTEGER DEFAULT 1
                )
                """
            )
            self._conn.commit()

    def add_key(self, key: str) -> None:
        with self._lock:
            self._conn.execute("INSERT OR REPLACE INTO api_keys(key, enabled) VALUES (?, 1)", (key,))
            self._conn.commit()

    def revoke_key(self, key: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE api_keys SET enabled = 0 WHERE key = ?", (key,))
            self._conn.commit()

    def is_valid_key(self, key: str) -> bool:
        with self._lock:
            row = self._conn.execute("SELECT 1 FROM api_keys WHERE key = ? AND enabled = 1", (key,)).fetchone()
            return row is not None

    def list_keys(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT key, created_at, enabled FROM api_keys").fetchall()
            return [{"key": r[0], "created_at": r[1], "enabled": bool(r[2])} for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
