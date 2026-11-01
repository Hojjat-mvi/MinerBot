"""Minimal contact storage: Telegram ID, phone, and consent timestamps only."""

import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


def normalize_phone(value: str) -> str | None:
    value = value.strip()
    if not re.fullmatch(r"\+?[1-9][0-9]{6,14}", value):
        return None
    return "+" + value.lstrip("+")


class ContactStore:
    def __init__(self, path: Path):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            self.path.chmod(0o600)
            connection.execute("PRAGMA secure_delete=ON")
            connection.execute("""CREATE TABLE IF NOT EXISTS contacts (
                telegram_user_id INTEGER PRIMARY KEY,
                phone_number TEXT NOT NULL,
                consent_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            connection.commit()
            return connection
        except Exception:
            connection.close()
            raise

    def has_contact(self, user_id: int) -> bool:
        with closing(self._connect()) as connection:
            return connection.execute("SELECT 1 FROM contacts WHERE telegram_user_id = ?", (user_id,)).fetchone() is not None

    def save(self, user_id: int, phone: str) -> None:
        phone = normalize_phone(phone)
        if phone is None:
            raise ValueError("Invalid contact phone format")
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection, connection:
            connection.execute("""INSERT INTO contacts VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    phone_number=excluded.phone_number, consent_at=excluded.consent_at,
                    updated_at=excluded.updated_at""", (user_id, phone, now, now))

    def delete(self, user_id: int) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM contacts WHERE telegram_user_id = ?", (user_id,))
