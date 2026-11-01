"""Phone consent, ownership, persistence, and trade access regression tests."""

import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError

from minerbot.contacts import ContactStore, normalize_phone
from minerbot.config import Settings
from minerbot.handlers import callback_handler, delete_phone, handle_contact, handle_messages
from minerbot.keyboards import TRADE_LABEL, FREE_LABEL, MONTHLY_LABEL, TRAINING_LABEL, SUBSCRIPTIONS_LABEL, RESULTS_LABEL


class ContactStoreTests(unittest.TestCase):
    def test_persistence_upsert_and_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "contacts.sqlite3"
            store = ContactStore(path)
            self.assertFalse(store.has_contact(42))
            store.save(42, "15551234567")
            self.assertTrue(ContactStore(path).has_contact(42))
            store.save(42, "+15557654321")
            with sqlite3.connect(path) as connection:
                rows = connection.execute("SELECT phone_number, consent_at FROM contacts WHERE telegram_user_id=42").fetchall()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "+15557654321")
            self.assertTrue(rows[0][1])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            store.delete(42)
            self.assertFalse(ContactStore(path).has_contact(42))

    def test_old_phone_database_migrates_and_uid_survives_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.sqlite3"
            with sqlite3.connect(path) as connection:
                connection.execute("CREATE TABLE contacts (telegram_user_id INTEGER PRIMARY KEY, phone_number TEXT NOT NULL, consent_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
                connection.execute("INSERT INTO contacts VALUES (42, '+15551234567', 'original-consent', 'original-time')")
            store = ContactStore(path)
            self.assertTrue(store.has_contact(42))
            store.save_uid(42, "123456", status="submitted")
            store.save_uid(42, "123456", status="below_threshold")
            self.assertTrue(ContactStore(path).has_contact(42))
            with sqlite3.connect(path) as connection:
                row = connection.execute("SELECT phone_number, consent_at, xt_uid, xt_status, xt_checked_at FROM contacts WHERE telegram_user_id=42").fetchone()
            self.assertEqual(row[:4], ('+15551234567', 'original-consent', '123456', 'below_threshold'))
            self.assertTrue(row[4])
            store.save(42, '+15557654321')
            store.delete(42)
            self.assertFalse(store.has_contact(42))

    def test_uid_cannot_create_an_orphan_user(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ContactStore(Path(directory) / "contacts.sqlite3")
            with self.assertRaises(ValueError):
                store.save_uid(42, "123456", status="submitted")
            self.assertFalse(store.has_contact(42))

    def test_invalid_phone_is_not_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ContactStore(Path(directory) / "contacts.sqlite3")
            for phone in ["abc", "123", "+1;DROP TABLE contacts", "0" * 12, "+" + "1" * 16]:
                self.assertIsNone(normalize_phone(phone))
                with self.assertRaises(ValueError):
                    store.save(42, phone)
            self.assertFalse(store.has_contact(42))


class PhoneFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ContactStore(Path(self.temp.name) / "contacts.sqlite3")
        self.bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock(),
            get_chat_member=AsyncMock(return_value=SimpleNamespace(status=ChatMemberStatus.MEMBER)))
        self.context = SimpleNamespace(bot=self.bot, user_data={}, bot_data={
            "settings": Settings(token="fake"), "contacts": self.store,
            "xt_verifier": SimpleNamespace(verify=AsyncMock())})
        self.user = SimpleNamespace(id=42)

    async def text(self, text):
        await handle_messages(SimpleNamespace(effective_user=self.user, effective_message=SimpleNamespace(text=text)), self.context)

    def update(self, owner=42, phone="+15551234567"):
        return SimpleNamespace(effective_user=self.user, effective_chat=SimpleNamespace(type="private"),
            effective_message=SimpleNamespace(contact=SimpleNamespace(user_id=owner, phone_number=phone), delete=AsyncMock()))

    async def test_every_trade_button_is_gated(self):
        for label in [TRADE_LABEL, FREE_LABEL, TRAINING_LABEL, MONTHLY_LABEL, SUBSCRIPTIONS_LABEL, RESULTS_LABEL]:
            await self.text(label)
            markup = self.bot.send_message.call_args.kwargs["reply_markup"]
            self.assertTrue(markup.keyboard[0][0].request_contact)
        for data in ["trade", "trade:free", "trade:check", "trade:training", "trade:monthly", "trade:subscriptions", "trade:results"]:
            await callback_handler(SimpleNamespace(callback_query=SimpleNamespace(data=data, from_user=self.user, answer=AsyncMock())), self.context)
            self.assertTrue(self.bot.send_message.call_args.kwargs["reply_markup"].keyboard[0][0].request_contact)
        self.context.bot_data["xt_verifier"].verify.assert_not_awaited()

    async def test_own_contact_is_saved_then_room_opens(self):
        await self.text(TRADE_LABEL)
        update = self.update()
        await handle_contact(update, self.context)
        self.assertTrue(self.store.has_contact(42))
        update.effective_message.delete.assert_awaited_once()
        labels = {b.text for row in self.bot.send_message.call_args.kwargs["reply_markup"].keyboard for b in row}
        self.assertIn(SUBSCRIPTIONS_LABEL, labels)
        self.assertNotIn("phone_requested_until", self.context.user_data)
        self.assertNotIn("+15551234567", str(self.bot.send_message.call_args_list))

    async def test_other_or_missing_contact_owner_is_rejected(self):
        await self.text(TRADE_LABEL)
        for owner in [None, 99]:
            await handle_contact(self.update(owner=owner), self.context)
            self.assertFalse(self.store.has_contact(42))

    async def test_unsolicited_and_expired_contacts_are_not_saved(self):
        await handle_contact(self.update(), self.context)
        self.assertFalse(self.store.has_contact(42))
        self.context.user_data["phone_requested_until"] = time.monotonic() - 1
        await handle_contact(self.update(), self.context)
        self.assertFalse(self.store.has_contact(42))

    async def test_typed_phone_does_not_register(self):
        await self.text(TRADE_LABEL)
        await self.text("+15551234567")
        self.assertFalse(self.store.has_contact(42))
        self.assertTrue(self.bot.send_message.call_args.kwargs["reply_markup"].keyboard[0][0].request_contact)

    async def test_home_cancels_registration(self):
        await self.text(TRADE_LABEL)
        await self.text("🏠 منوی اصلی")
        await handle_contact(self.update(), self.context)
        self.assertFalse(self.store.has_contact(42))

    async def test_member_requirement_still_applies(self):
        await self.text(TRADE_LABEL)
        self.bot.get_chat_member.return_value = SimpleNamespace(status=ChatMemberStatus.LEFT)
        await handle_contact(self.update(), self.context)
        self.assertFalse(self.store.has_contact(42))

    async def test_registered_users_are_not_prompted_again(self):
        self.store.save(42, "+15551234567")
        await self.text(TRADE_LABEL)
        self.assertNotIn("phone_requested_until", self.context.user_data)
        labels = {b.text for row in self.bot.send_message.call_args.kwargs["reply_markup"].keyboard for b in row}
        self.assertIn(SUBSCRIPTIONS_LABEL, labels)

    async def test_delete_phone_revokes_trade_entry(self):
        self.store.save(42, "+15551234567")
        await delete_phone(SimpleNamespace(effective_user=self.user), self.context)
        self.assertFalse(self.store.has_contact(42))
        await self.text(TRADE_LABEL)
        self.assertIn("phone_requested_until", self.context.user_data)

    async def test_contact_message_delete_failure_does_not_lose_registration(self):
        await self.text(TRADE_LABEL)
        update = self.update()
        update.effective_message.delete.side_effect = TelegramError("cannot delete")
        await handle_contact(update, self.context)
        self.assertTrue(self.store.has_contact(42))

    async def test_database_failure_does_not_unlock_room(self):
        await self.text(TRADE_LABEL)
        with patch.object(self.store, "save", side_effect=sqlite3.OperationalError("disk full")):
            with self.assertRaises(sqlite3.OperationalError):
                await handle_contact(self.update(), self.context)
        self.assertFalse(self.store.has_contact(42))

    async def test_group_contact_is_not_saved(self):
        await self.text(TRADE_LABEL)
        update = self.update()
        update.effective_chat.type = "group"
        await handle_contact(update, self.context)
        self.assertFalse(self.store.has_contact(42))


if __name__ == "__main__":
    unittest.main()
