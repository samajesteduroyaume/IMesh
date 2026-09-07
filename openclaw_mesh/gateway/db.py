from __future__ import annotations

import sqlite3
from pathlib import Path


class GatewayDB:
    def __init__(self, db_path: str | Path = "./openclaw_gateway.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._init_db()

    def _init_db(self) -> None:
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
        self._conn.execute("INSERT OR IGNORE INTO api_keys(key, enabled) VALUES (?, 1)", (key,))
        self._conn.commit()

    def is_valid_key(self, key: str) -> bool:
        row = self._conn.execute("SELECT 1 FROM api_keys WHERE key = ? AND enabled = 1", (key,)).fetchone()
        return row is not None

    def close(self) -> None:
        self._conn.close()
