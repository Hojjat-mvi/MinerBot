"""Admin-authorized channel discovery using synthetic Telegram updates."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.constants import ChatMemberStatus

from minerbot.channel_setup import PREFIX, channel_id_command, discover_channel_id
from minerbot.config import Settings


class ChannelSetupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = SimpleNamespace(send_message=AsyncMock(),
            get_chat_member=AsyncMock(return_value=SimpleNamespace(status=ChatMemberStatus.ADMINISTRATOR)))
        self.context = SimpleNamespace(bot=self.bot, bot_data={"settings": Settings(token="fake", trade_admin_ids=(42,))})

    async def create_code(self):
        await channel_id_command(SimpleNamespace(effective_user=SimpleNamespace(id=42)), self.context)
        return self.bot.send_message.call_args.kwargs["text"].split("\n\n")[-1]

    def post(self, code):
        return SimpleNamespace(channel_post=SimpleNamespace(text=code,
            chat=SimpleNamespace(id=-1001234567890, type="channel"), delete=AsyncMock()))

    async def test_only_allowed_admin_can_request_setup(self):
        await channel_id_command(SimpleNamespace(effective_user=SimpleNamespace(id=99)), self.context)
        self.bot.send_message.assert_not_awaited()
        self.assertNotIn("channel_setup_requests", self.context.bot_data)

    async def test_valid_post_sends_channel_id_privately_and_consumes_code(self):
        code = await self.create_code()
        self.assertTrue(code.startswith(PREFIX))
        update = self.post(code)
        await discover_channel_id(update, self.context)
        sent = self.bot.send_message.call_args.kwargs
        self.assertEqual(sent["chat_id"], 42)
        self.assertIn("XT_REWARD_CHANNEL_ID=-1001234567890", sent["text"])
        self.assertEqual(self.context.bot_data["channel_setup_requests"], {})
        update.channel_post.delete.assert_awaited_once()
        count = self.bot.send_message.await_count
        await discover_channel_id(update, self.context)
        self.assertEqual(self.bot.send_message.await_count, count)

    async def test_unknown_expired_and_nonadmin_posts_are_ignored(self):
        await discover_channel_id(self.post(PREFIX + "unknown"), self.context)
        self.bot.send_message.assert_not_awaited()
        with patch("minerbot.channel_setup.time.time", return_value=100):
            code = await self.create_code()
        with patch("minerbot.channel_setup.time.time", return_value=701):
            await discover_channel_id(self.post(code), self.context)
        self.assertEqual(self.bot.send_message.await_count, 1)
        code = await self.create_code()
        self.bot.get_chat_member.return_value = SimpleNamespace(status=ChatMemberStatus.MEMBER)
        await discover_channel_id(self.post(code), self.context)
        self.assertEqual(self.bot.send_message.await_count, 2)

    async def test_new_request_invalidates_previous_code(self):
        await self.create_code()
        old = set(self.context.bot_data["channel_setup_requests"])
        await self.create_code()
        self.assertEqual(len(self.context.bot_data["channel_setup_requests"]), 1)
        self.assertTrue(old.isdisjoint(self.context.bot_data["channel_setup_requests"]))

