"""Contact storage with a self-reported XT UID and its latest eligibility result."""

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
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("""CREATE TABLE IF NOT EXISTS contacts (
                telegram_user_id INTEGER PRIMARY KEY,
                phone_number TEXT NOT NULL,
                consent_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(contacts)")}
            for name in ("xt_uid", "xt_status", "xt_checked_at"):
                if name not in columns:
                    connection.execute(f"ALTER TABLE contacts ADD COLUMN {name} TEXT")
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
            connection.execute("""INSERT INTO contacts (telegram_user_id, phone_number, consent_at, updated_at) VALUES (?, ?, ?, ?)
                ON CONFLICT(telegram_user_id) DO UPDATE SET
                    phone_number=excluded.phone_number, consent_at=excluded.consent_at,
                    updated_at=excluded.updated_at""", (user_id, phone, now, now))

    def delete(self, user_id: int) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM contacts WHERE telegram_user_id = ?", (user_id,))

    def save_uid(self, user_id: int, uid: str, *, status: str) -> None:
        if not re.fullmatch(r"[1-9][0-9]{0,18}", uid) or int(uid) > 9223372036854775807:
            raise ValueError("Invalid XT UID")
        if status not in {"submitted", "unavailable", "not_referred", "below_threshold", "eligible"}:
            raise ValueError("Invalid XT check status")
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """UPDATE contacts SET xt_uid=?, xt_status=?, xt_checked_at=?, updated_at=?
                   WHERE telegram_user_id=?""",
                (uid, status, None if status == "submitted" else now, now, user_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Phone registration is required before saving an XT UID")
