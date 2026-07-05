from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


class AuditStore:
    def __init__(self, path: Path):
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def record_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        created_at: Optional[datetime] = None,
    ) -> int:
        self.initialize()
        timestamp = (created_at or datetime.utcnow()).isoformat()
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO audit_events (created_at, event_type, payload_json)
                VALUES (?, ?, ?)
                """,
                (timestamp, event_type, json.dumps(payload, sort_keys=True)),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def list_events(self, limit: int = 100) -> Iterable[Tuple[int, str, str, Dict[str, Any]]]:
        self.initialize()
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, event_type, payload_json
                FROM audit_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        for event_id, created_at, event_type, payload_json in rows:
            yield event_id, created_at, event_type, json.loads(payload_json)
