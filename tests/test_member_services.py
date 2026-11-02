"""Persistence, isolation, and privacy regressions for member services."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from minerbot.contacts import ContactStore
from minerbot.member_services import account_command, ticket_callback, reply_ticket


class TicketStorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'contacts.sqlite3'
        self.store = ContactStore(self.path)

    def test_ticket_survives_restart_and_other_users_cannot_read_or_close(self):
        ticket = self.store.create_ticket(42, 'Help', 1000)
        reopened = ContactStore(self.path)
        self.assertEqual(reopened.ticket(ticket, 42)['body'], 'Help')
        self.assertIsNone(reopened.ticket(ticket, 43))
        self.assertFalse(reopened.close_ticket(ticket, 43))
        self.assertTrue(reopened.reply_ticket(ticket, 'Answer', 2000))
        self.assertFalse(reopened.reply_ticket(ticket, 'Duplicate', 2001))
        self.assertEqual(reopened.ticket(ticket, 42)['reply'], 'Answer')
        self.assertTrue(reopened.close_ticket(ticket, 42))

    def test_persistent_creation_limits(self):
        self.store.create_ticket(42, 'One', 1000)
        with self.assertRaises(ValueError):
            ContactStore(self.path).create_ticket(42, 'Too soon', 1001)
        self.store.create_ticket(42, 'Two', 1060)
        self.store.create_ticket(42, 'Three', 1120)
        with self.assertRaises(ValueError):
            self.store.create_ticket(42, 'Four', 1180)
        with self.assertRaises(ValueError):
            self.store.create_ticket(43, 'x' * 2001, 1180)


class MemberHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = ContactStore(Path(directory.name) / 'contacts.sqlite3')
        self.context = SimpleNamespace(user_data={}, bot_data={
            'contacts': self.store, 'settings': SimpleNamespace(trade_admin_ids=(99,))})
        self.update = SimpleNamespace(effective_user=SimpleNamespace(id=42))

    async def test_account_masks_phone_and_displays_cached_result(self):
        self.store.save(42, '+15551234567')
        self.store.save_uid(42, '12345', status='eligible')
        with patch('minerbot.member_services.send_text', new_callable=AsyncMock) as send:
            await account_command(self.update, self.context)
        text = send.call_args.args[2]
        self.assertIn('***4567', text)
        self.assertNotIn('+15551234567', text)
        self.assertIn('12345', text)
        self.assertIn('ذخیره‌شده', text)

    async def test_forged_ticket_callback_cannot_read_another_users_text(self):
        ticket = self.store.create_ticket(99, 'private ticket body', 1000)
        self.update.effective_chat = SimpleNamespace(type='private')
        self.update.callback_query = SimpleNamespace(answer=AsyncMock(), from_user=SimpleNamespace(id=42), data=f'ticket:view:{ticket}')
        with patch('minerbot.member_services.send_text', new_callable=AsyncMock) as send:
            await ticket_callback(self.update, self.context)
        self.assertNotIn('private ticket body', send.call_args.args[2])

    async def test_non_admin_cannot_reply(self):
        ticket = self.store.create_ticket(42, 'Question', 1000)
        self.update.effective_message = SimpleNamespace(text=f'/replyticket {ticket} fake')
        await reply_ticket(self.update, self.context)
        self.assertIsNone(self.store.ticket(ticket, 42)['reply'])
