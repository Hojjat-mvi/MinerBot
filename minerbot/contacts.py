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
            connection.execute("""CREATE TABLE IF NOT EXISTS reward_bindings (
                xt_uid TEXT PRIMARY KEY, telegram_user_id INTEGER NOT NULL UNIQUE,
                approved_by INTEGER NOT NULL, approved_at TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS ownership_requests (
                telegram_user_id INTEGER PRIMARY KEY, xt_uid TEXT NOT NULL,
                requested_at TEXT NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS reward_admissions (
                invite_hash TEXT PRIMARY KEY, telegram_user_id INTEGER NOT NULL,
                xt_uid TEXT NOT NULL, channel_id INTEGER NOT NULL,
                expires_at INTEGER NOT NULL, consumed INTEGER NOT NULL DEFAULT 0
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS xt_check_limits (
                telegram_user_id INTEGER PRIMARY KEY, next_check_at REAL NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS broadcast_users (
                telegram_user_id INTEGER PRIMARY KEY, subscribed INTEGER NOT NULL DEFAULT 1
            )""")
            connection.execute("CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            if connection.execute("SELECT 1 FROM app_metadata WHERE key='broadcast_users_migrated'").fetchone() is None:
                connection.execute("INSERT OR IGNORE INTO broadcast_users (telegram_user_id) SELECT telegram_user_id FROM contacts")
                connection.execute("INSERT INTO app_metadata VALUES ('broadcast_users_migrated', '1')")
            connection.execute("""CREATE TABLE IF NOT EXISTS broadcasts (
                id TEXT PRIMARY KEY, admin_id INTEGER NOT NULL, body TEXT NOT NULL,
                state TEXT NOT NULL, created_at REAL NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS broadcast_deliveries (
                broadcast_id TEXT NOT NULL, telegram_user_id INTEGER NOT NULL,
                state TEXT NOT NULL DEFAULT 'pending',
                PRIMARY KEY (broadcast_id, telegram_user_id)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                body TEXT NOT NULL, reply TEXT, status TEXT NOT NULL DEFAULT 'open',
                created_at REAL NOT NULL, updated_at REAL NOT NULL
            )""")
            connection.execute("CREATE INDEX IF NOT EXISTS tickets_owner ON support_tickets(user_id, created_at)")
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
            connection.execute("DELETE FROM ownership_requests WHERE telegram_user_id = ?", (user_id,))
            connection.execute("UPDATE reward_admissions SET consumed=1 WHERE telegram_user_id=?", (user_id,))

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


    def binding_matches(self, user_id: int, uid: str) -> bool:
        with closing(self._connect()) as connection:
            return connection.execute("SELECT 1 FROM reward_bindings WHERE telegram_user_id=? AND xt_uid=?", (user_id, uid)).fetchone() is not None

    def binding_conflicts(self, user_id: int, uid: str) -> bool:
        with closing(self._connect()) as connection:
            return connection.execute("SELECT 1 FROM reward_bindings WHERE (xt_uid=? AND telegram_user_id!=?) OR (telegram_user_id=? AND xt_uid!=?)", (uid, user_id, user_id, uid)).fetchone() is not None

    def claim_binding(self, user_id: int, uid: str) -> None:
        """Atomically assign an eligible UID to its first Telegram claimant."""
        from .rewards import RewardConflict
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            contact = connection.execute(
                "SELECT 1 FROM contacts WHERE telegram_user_id=? AND xt_uid=? AND xt_status='eligible'",
                (user_id, uid),
            ).fetchone()
            if contact is None:
                raise RewardConflict()
            existing = connection.execute(
                "SELECT xt_uid, telegram_user_id FROM reward_bindings WHERE xt_uid=? OR telegram_user_id=?",
                (uid, user_id),
            ).fetchall()
            if existing and existing != [(uid, user_id)]:
                raise RewardConflict()
            # Keep the existing schema: approved_by=0 denotes automatic XT qualification.
            connection.execute("INSERT OR IGNORE INTO reward_bindings VALUES (?, ?, 0, ?)",
                               (uid, user_id, datetime.now(timezone.utc).isoformat()))
            connection.execute("DELETE FROM ownership_requests WHERE telegram_user_id=?", (user_id,))

    def save_admission(self, user_id: int, uid: str, channel_id: int, digest: str, expires: int) -> None:
        from .rewards import RewardConflict
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM reward_bindings b JOIN contacts c USING(telegram_user_id) WHERE b.telegram_user_id=? AND b.xt_uid=? AND c.xt_uid=? AND c.xt_status='eligible'", (user_id, uid, uid)).fetchone() is None:
                raise RewardConflict()
            connection.execute("UPDATE reward_admissions SET consumed=1 WHERE telegram_user_id=?", (user_id,))
            connection.execute("INSERT INTO reward_admissions VALUES (?, ?, ?, ?, ?, 0)", (digest, user_id, uid, channel_id, expires))

    def admission_for(self, digest: str) -> dict | None:
        with closing(self._connect()) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT * FROM reward_admissions WHERE invite_hash=?", (digest,)).fetchone()
            return dict(row) if row is not None else None

    def consume_admission(self, digest: str, user_id: int, now: float) -> bool:
        with closing(self._connect()) as connection, connection:
            return connection.execute("UPDATE reward_admissions SET consumed=1 WHERE invite_hash=? AND telegram_user_id=? AND consumed=0 AND expires_at>?", (digest, user_id, now)).rowcount == 1

    def take_xt_slot(self, user_id: int, now: float) -> bool:
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT next_check_at FROM xt_check_limits WHERE telegram_user_id=?", (user_id,)).fetchone()
            if row and row[0] > now:
                return False
            connection.execute("INSERT INTO xt_check_limits VALUES (?, ?) ON CONFLICT(telegram_user_id) DO UPDATE SET next_check_at=excluded.next_check_at", (user_id, now + 15))
            return True


    def remember_user(self, user_id: int) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("INSERT OR IGNORE INTO broadcast_users (telegram_user_id) VALUES (?)", (user_id,))

    def subscribe_user(self, user_id: int, enabled: bool) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("INSERT INTO broadcast_users VALUES (?, ?) ON CONFLICT(telegram_user_id) DO UPDATE SET subscribed=excluded.subscribed", (user_id, int(enabled)))

    def is_subscribed(self, user_id: int) -> bool:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT subscribed FROM broadcast_users WHERE telegram_user_id=?", (user_id,)).fetchone()
            return bool(row and row[0])

    def broadcast_audience(self) -> int:
        with closing(self._connect()) as connection:
            return connection.execute("SELECT COUNT(*) FROM broadcast_users WHERE subscribed=1").fetchone()[0]

    def draft_broadcast(self, draft_id: str, admin_id: int, body: str, now: float) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("UPDATE broadcasts SET state='cancelled', body='' WHERE admin_id=? AND state='draft'", (admin_id,))
            connection.execute("INSERT INTO broadcasts VALUES (?, ?, ?, 'draft', ?)", (draft_id, admin_id, body, now))

    def broadcast_info(self, draft_id: str, admin_id: int) -> dict | None:
        with closing(self._connect()) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT * FROM broadcasts WHERE id=? AND admin_id=?", (draft_id, admin_id)).fetchone()
            return dict(row) if row else None

    def confirm_broadcast(self, draft_id: str, admin_id: int, now: float) -> bool:
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute("SELECT 1 FROM broadcasts WHERE state='running'").fetchone():
                return False
            changed = connection.execute("UPDATE broadcasts SET state='running' WHERE id=? AND admin_id=? AND state='draft' AND created_at>?", (draft_id, admin_id, now - 600)).rowcount
            if not changed:
                return False
            connection.execute("INSERT INTO broadcast_deliveries (broadcast_id, telegram_user_id) SELECT ?, telegram_user_id FROM broadcast_users WHERE subscribed=1", (draft_id,))
            return True

    def cancel_broadcast(self, draft_id: str, admin_id: int) -> bool:
        with closing(self._connect()) as connection, connection:
            return connection.execute("UPDATE broadcasts SET state='cancelled', body='' WHERE id=? AND admin_id=? AND state='draft'", (draft_id, admin_id)).rowcount == 1

    def next_broadcast_recipient(self, draft_id: str) -> int | None:
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT telegram_user_id FROM broadcast_deliveries WHERE broadcast_id=? AND state='pending' ORDER BY telegram_user_id LIMIT 1", (draft_id,)).fetchone()
            if not row:
                return None
            connection.execute("UPDATE broadcast_deliveries SET state='sending' WHERE broadcast_id=? AND telegram_user_id=?", (draft_id, row[0]))
            return row[0]

    def record_delivery(self, draft_id: str, user_id: int, state: str) -> None:
        if state not in {'sent', 'failed', 'uncertain', 'skipped'}:
            raise ValueError("Invalid delivery state")
        with closing(self._connect()) as connection, connection:
            connection.execute("UPDATE broadcast_deliveries SET state=? WHERE broadcast_id=? AND telegram_user_id=?", (state, draft_id, user_id))

    def finish_broadcast(self, draft_id: str, state: str) -> None:
        if state not in {'completed', 'interrupted'}:
            raise ValueError("Invalid broadcast state")
        with closing(self._connect()) as connection, connection:
            connection.execute("UPDATE broadcast_deliveries SET state='uncertain' WHERE broadcast_id=? AND state='sending'", (draft_id,))
            connection.execute("UPDATE broadcasts SET state=?, body='' WHERE id=?", (state, draft_id))

    def interrupt_broadcasts(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("UPDATE broadcast_deliveries SET state='uncertain' WHERE state='sending'")
            connection.execute("UPDATE broadcasts SET state='interrupted', body='' WHERE state='running'")
            connection.execute("UPDATE broadcasts SET state='cancelled', body='' WHERE state='draft'")

    def latest_broadcast(self, admin_id: int) -> str | None:
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT id FROM broadcasts WHERE admin_id=? ORDER BY created_at DESC LIMIT 1", (admin_id,)).fetchone()
            return row[0] if row else None

    def delivery_counts(self, draft_id: str) -> dict[str, int]:
        with closing(self._connect()) as connection:
            return dict(connection.execute("SELECT state, COUNT(*) FROM broadcast_deliveries WHERE broadcast_id=? GROUP BY state", (draft_id,)).fetchall())

    def account(self, user_id: int) -> dict | None:
        with closing(self._connect()) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT * FROM contacts WHERE telegram_user_id=?", (user_id,)).fetchone()
            return dict(row) if row else None

    def create_ticket(self, user_id: int, body: str, now: float) -> int:
        if not body.strip() or len(body.encode("utf-16-le")) > 4000:
            raise ValueError("invalid_body")
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            count, latest = connection.execute(
                "SELECT SUM(CASE WHEN status='open' THEN 1 ELSE 0 END), MAX(created_at) FROM support_tickets WHERE user_id=?",
                (user_id,),
            ).fetchone()
            if (count or 0) >= 3 or (latest is not None and now - latest < 60):
                raise ValueError("ticket_limit")
            return connection.execute(
                "INSERT INTO support_tickets(user_id,body,created_at,updated_at) VALUES(?,?,?,?)",
                (user_id, body.strip(), now, now),
            ).lastrowid

    def tickets(self, user_id: int | None) -> list[dict]:
        with closing(self._connect()) as connection:
            connection.row_factory = sqlite3.Row
            if user_id is None:
                rows = connection.execute("SELECT * FROM support_tickets WHERE status='open' ORDER BY id LIMIT 10")
            else:
                rows = connection.execute("SELECT * FROM support_tickets WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,))
            return [dict(row) for row in rows]

    def ticket(self, ticket_id: int, user_id: int | None) -> dict | None:
        with closing(self._connect()) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute("SELECT * FROM support_tickets WHERE id=? AND (? IS NULL OR user_id=?)",
                                     (ticket_id, user_id, user_id)).fetchone()
            return dict(row) if row else None

    def reply_ticket(self, ticket_id: int, reply: str, now: float) -> bool:
        with closing(self._connect()) as connection, connection:
            return connection.execute("UPDATE support_tickets SET reply=?,status='answered',updated_at=? WHERE id=? AND status='open'",
                                      (reply, now, ticket_id)).rowcount == 1

    def close_ticket(self, ticket_id: int, user_id: int) -> bool:
        with closing(self._connect()) as connection, connection:
            return connection.execute("UPDATE support_tickets SET status='closed' WHERE id=? AND user_id=? AND status!='closed'",
                                      (ticket_id, user_id)).rowcount == 1
