"""Offline broadcast authorization, delivery, opt-out, and restart coverage."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.error import Forbidden, NetworkError

from minerbot.broadcasts import broadcast_command, send_broadcast, stop_broadcasts
from minerbot.contacts import ContactStore
from minerbot.config import Settings


class BroadcastStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "contacts.sqlite3"
        self.store = ContactStore(self.path)
        self.store.remember_user(42)

    def test_opt_out_survives_reopen_and_normal_interaction(self):
        self.store.subscribe_user(42, False)
        reopened = ContactStore(self.path)
        reopened.remember_user(42)
        self.assertFalse(reopened.is_subscribed(42))

    def test_confirmation_is_single_use_and_has_one_active_job(self):
        self.store.draft_broadcast("first", 1, "Hello", 100)
        self.assertFalse(self.store.confirm_broadcast("first", 99, 101))
        self.assertTrue(self.store.confirm_broadcast("first", 1, 101))
        self.assertFalse(self.store.confirm_broadcast("first", 1, 102))
        self.store.draft_broadcast("second", 1, "Other", 103)
        self.assertFalse(self.store.confirm_broadcast("second", 1, 104))

    def test_expired_and_cancelled_drafts_cannot_send(self):
        self.store.draft_broadcast("expired", 1, "Hello", 100)
        self.assertFalse(self.store.confirm_broadcast("expired", 1, 701))
        self.store.draft_broadcast("cancelled", 1, "Hello", 702)
        self.assertTrue(self.store.cancel_broadcast("cancelled", 1))
        self.assertFalse(self.store.confirm_broadcast("cancelled", 1, 703))

    def test_restart_does_not_requeue_uncertain_deliveries(self):
        self.store.draft_broadcast("job", 1, "Hello", 100)
        self.store.confirm_broadcast("job", 1, 101)
        self.assertEqual(self.store.next_broadcast_recipient("job"), 42)
        ContactStore(self.path).interrupt_broadcasts()
        self.assertEqual(self.store.broadcast_info("job", 1)["state"], "interrupted")
        self.assertEqual(self.store.delivery_counts("job"), {"uncertain": 1})
        self.assertIsNone(self.store.next_broadcast_recipient("job"))


class BroadcastFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ContactStore(Path(self.temp.name) / "contacts.sqlite3")
        self.store.remember_user(42)
        self.bot = SimpleNamespace(send_message=AsyncMock())
        self.context = SimpleNamespace(bot=self.bot,
            bot_data={"settings": Settings(token="fake", trade_admin_ids=(1,)), "contacts": self.store})

    def update(self, user=1, text="/broadcast Hello"):
        return SimpleNamespace(effective_user=SimpleNamespace(id=user),
            effective_message=SimpleNamespace(text=text, reply_to_message=None))

    async def test_nonadmin_cannot_preview_or_send(self):
        await broadcast_command(self.update(user=99), self.context)
        self.bot.send_message.assert_not_awaited()
        self.assertIsNone(self.store.latest_broadcast(99))

    async def test_admin_command_only_previews_until_confirmation(self):
        await broadcast_command(self.update(), self.context)
        self.assertTrue(all(call.args[0] == 1 for call in self.bot.send_message.call_args_list))
        job = self.store.broadcast_info(self.store.latest_broadcast(1), 1)
        self.assertEqual(job["state"], "draft")
        self.assertEqual(self.store.delivery_counts(job["id"]), {})

    async def test_stop_preserves_contact_and_disables_broadcasts(self):
        self.store.save(42, "+15551234567")
        await stop_broadcasts(self.update(user=42), self.context)
        self.assertFalse(self.store.is_subscribed(42))
        self.assertTrue(self.store.has_contact(42))

    async def run_job(self):
        self.store.draft_broadcast("job", 1, "Hello", 100)
        self.store.confirm_broadcast("job", 1, 101)
        info = self.store.broadcast_info("job", 1)
        with patch("minerbot.broadcasts.asyncio.sleep", new_callable=AsyncMock):
            await send_broadcast(self.context, info)

    async def test_text_delivery_and_counts(self):
        await self.run_job()
        self.assertEqual(self.store.delivery_counts("job"), {"sent": 1})
        self.assertEqual(self.store.broadcast_info("job", 1)["body"], "")

    async def test_blocked_users_are_unsubscribed(self):
        self.bot.send_message.side_effect = Forbidden("blocked")
        await self.run_job()
        self.assertFalse(self.store.is_subscribed(42))
        self.assertEqual(self.store.delivery_counts("job"), {"failed": 1})

    async def test_ambiguous_network_failure_is_not_retried(self):
        self.bot.send_message.side_effect = NetworkError("timeout")
        await self.run_job()
        self.assertEqual(self.store.delivery_counts("job"), {"uncertain": 1})
        calls_to_user = [call for call in self.bot.send_message.call_args_list if call.args[0] == 42]
        self.assertEqual(len(calls_to_user), 1)
