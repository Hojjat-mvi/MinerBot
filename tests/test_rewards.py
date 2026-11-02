"""VIP claim and admission regression coverage, with no live Telegram requests."""

import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from telegram.constants import ChatMemberStatus

from minerbot.config import Settings
from minerbot.contacts import ContactStore
from minerbot.rewards import RewardConflict, approve_uid, invite_digest, issue_reward, reward_join_request
from minerbot.xt import Eligibility, XTUnavailable


class RewardStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "contacts.sqlite3"
        self.store = ContactStore(self.path)
        self.register(42)

    def register(self, user):
        self.store.save(user, "+15551234567")
        self.store.save_uid(user, "123456", status="eligible")
        self.store.request_ownership(user, "123456")

    def test_uid_cannot_be_assigned_to_two_telegram_accounts(self):
        self.store.approve_binding(42, "123456", 1)
        self.register(99)
        with self.assertRaises(RewardConflict):
            self.store.approve_binding(99, "123456", 1)
        self.assertTrue(ContactStore(self.path).binding_matches(42, "123456"))

    def test_phone_deletion_does_not_release_used_uid(self):
        self.store.approve_binding(42, "123456", 1)
        self.store.delete(42)
        self.assertFalse(self.store.has_contact(42))
        self.assertTrue(ContactStore(self.path).binding_conflicts(99, "123456"))

    def test_stale_approval_does_not_bind_a_changed_uid(self):
        self.store.save_uid(42, "654321", status="eligible")
        with self.assertRaises(RewardConflict):
            self.store.approve_binding(42, "123456", 1)

    def test_invite_consumption_and_reissue_are_atomic(self):
        self.store.approve_binding(42, "123456", 1)
        self.store.save_admission(42, "123456", -100123, "first", int(time.time()) + 600)
        self.assertFalse(self.store.consume_admission("first", 99, time.time()))
        self.assertTrue(self.store.consume_admission("first", 42, time.time()))
        self.assertFalse(self.store.consume_admission("first", 42, time.time()))
        self.store.save_admission(42, "123456", -100123, "second", int(time.time()) + 600)
        self.store.save_admission(42, "123456", -100123, "third", int(time.time()) + 600)
        self.assertFalse(self.store.consume_admission("second", 42, time.time()))
        self.assertTrue(self.store.consume_admission("third", 42, time.time()))

    def test_expired_invites_and_deleted_contacts_cannot_be_used(self):
        self.store.approve_binding(42, "123456", 1)
        self.store.save_admission(42, "123456", -100123, "expired", int(time.time()) - 1)
        self.assertFalse(self.store.consume_admission("expired", 42, time.time()))
        self.store.save_admission(42, "123456", -100123, "active", int(time.time()) + 600)
        self.store.delete(42)
        self.assertFalse(self.store.consume_admission("active", 42, time.time()))

    def test_cooldown_survives_restart_and_phone_deletion(self):
        self.assertTrue(self.store.take_xt_slot(42, 100))
        self.store.delete(42)
        self.assertFalse(ContactStore(self.path).take_xt_slot(42, 101))
        self.assertTrue(ContactStore(self.path).take_xt_slot(42, 116))


class RewardAdmissionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ContactStore(Path(self.temp.name) / "contacts.sqlite3")
        self.store.save(42, "+15551234567")
        self.store.save_uid(42, "123456", status="eligible")
        self.settings = Settings(token="fake", xt_reward_channel_id=-100123, trade_admin_ids=(1,))
        self.link = "https://t.me/+synthetic_join_request"
        self.bot = SimpleNamespace(
            send_message=AsyncMock(),
            get_chat=AsyncMock(return_value=SimpleNamespace(type="channel", username=None)),
            create_chat_invite_link=AsyncMock(return_value=SimpleNamespace(invite_link=self.link)),
            revoke_chat_invite_link=AsyncMock(),
            approve_chat_join_request=AsyncMock(), decline_chat_join_request=AsyncMock(),
            get_chat_member=AsyncMock(return_value=SimpleNamespace(status=ChatMemberStatus.MEMBER)),
        )
        self.verifier = SimpleNamespace(verify=AsyncMock(return_value=Eligibility(True, True)))
        self.context = SimpleNamespace(bot=self.bot, args=[], user_data={},
            bot_data={"settings": self.settings, "contacts": self.store, "xt_verifier": self.verifier})

    def bind(self):
        self.store.request_ownership(42, "123456")
        self.store.approve_binding(42, "123456", 1)

    def join(self, user=42, link=None, channel=-100123):
        return SimpleNamespace(chat_join_request=SimpleNamespace(
            chat=SimpleNamespace(id=channel), from_user=SimpleNamespace(id=user),
            invite_link=SimpleNamespace(invite_link=link or self.link)))

    async def test_first_eligible_submit_requires_owner_review(self):
        state, link = await issue_reward(self.context, 42, "123456")
        self.assertEqual(state, "review")
        self.assertIsNone(link)
        self.assertTrue(self.store.ownership_pending(42, "123456"))
        self.bot.create_chat_invite_link.assert_not_awaited()

    async def test_legacy_shared_url_is_never_used(self):
        self.bind()
        self.context.bot_data["settings"] = replace(self.settings, xt_reward_channel_id=None,
                                                   xt_reward_channel_url="https://t.me/+old_shared_invite")
        self.assertEqual(await issue_reward(self.context, 42, "123456"), ("unconfigured", None))
        self.bot.create_chat_invite_link.assert_not_awaited()

    async def test_public_channel_never_generates_a_reward_invite(self):
        self.bind()
        self.bot.get_chat.return_value = SimpleNamespace(type="channel", username="public_channel")
        self.assertEqual(await issue_reward(self.context, 42, "123456"), ("unconfigured", None))
        self.bot.create_chat_invite_link.assert_not_awaited()

    async def test_forwarded_link_cannot_approve_or_consume_owner_invite(self):
        self.bind()
        await issue_reward(self.context, 42, "123456")
        await reward_join_request(self.join(user=99), self.context)
        self.bot.decline_chat_join_request.assert_awaited_with(-100123, 99)
        self.bot.approve_chat_join_request.assert_not_awaited()
        self.assertEqual(self.store.admission_for(invite_digest(self.link))["consumed"], 0)

    async def test_owner_is_rechecked_and_approved_once(self):
        self.bind()
        await issue_reward(self.context, 42, "123456")
        kwargs = self.bot.create_chat_invite_link.call_args.kwargs
        self.assertTrue(kwargs["creates_join_request"])
        self.assertNotIn("member_limit", kwargs)
        await reward_join_request(self.join(), self.context)
        self.verifier.verify.assert_awaited_once_with("123456")
        self.bot.approve_chat_join_request.assert_awaited_once_with(-100123, 42)
        await reward_join_request(self.join(), self.context)
        self.bot.approve_chat_join_request.assert_awaited_once()

    async def test_api_error_and_failed_conditions_never_approve(self):
        self.bind()
        await issue_reward(self.context, 42, "123456")
        self.verifier.verify.side_effect = XTUnavailable()
        await reward_join_request(self.join(), self.context)
        self.bot.approve_chat_join_request.assert_not_awaited()
        self.bot.decline_chat_join_request.assert_awaited_once()

    async def test_unknown_and_expired_links_are_declined(self):
        self.bind()
        await reward_join_request(self.join(link="https://t.me/+unknown"), self.context)
        self.store.save_admission(42, "123456", -100123, invite_digest(self.link), int(time.time()) - 1)
        await reward_join_request(self.join(), self.context)
        self.bot.approve_chat_join_request.assert_not_awaited()
        self.assertEqual(self.bot.decline_chat_join_request.await_count, 2)

    async def test_lost_public_membership_never_approves(self):
        self.bind()
        await issue_reward(self.context, 42, "123456")
        self.bot.get_chat_member.return_value = SimpleNamespace(status=ChatMemberStatus.LEFT)
        await reward_join_request(self.join(), self.context)
        self.bot.approve_chat_join_request.assert_not_awaited()
        self.verifier.verify.assert_not_awaited()

    async def test_admin_command_requires_allowed_identity_and_pending_request(self):
        self.context.args = ["42", "123456"]
        await approve_uid(SimpleNamespace(effective_user=SimpleNamespace(id=99)), self.context)
        self.verifier.verify.assert_not_awaited()
        self.store.request_ownership(42, "123456")
        await approve_uid(SimpleNamespace(effective_user=SimpleNamespace(id=1)), self.context)
        self.assertTrue(self.store.binding_matches(42, "123456"))
        self.bot.create_chat_invite_link.assert_not_awaited()

    async def test_foreign_channel_requests_are_untouched(self):
        await reward_join_request(self.join(channel=-100999), self.context)
        self.bot.approve_chat_join_request.assert_not_awaited()
        self.bot.decline_chat_join_request.assert_not_awaited()
