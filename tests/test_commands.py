"""Native Menu setup and command entry-point coverage, using mocked API calls."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from telegram.constants import ChatMemberStatus
from telegram.error import TelegramError

from minerbot.commands import USER_COMMANDS, configure_command_menu, help_command, nodes_command, support_command, trade_command
from minerbot.config import Settings


class CommandMenuTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_menu_registers_only_public_user_commands(self):
        bot = SimpleNamespace(set_my_commands=AsyncMock(), set_chat_menu_button=AsyncMock())
        await configure_command_menu(SimpleNamespace(bot=bot))
        self.assertEqual([c.command for c in USER_COMMANDS], ["menu", "trade", "nodes", "support", "help", "stop", "subscribe", "deletephone"])
        self.assertEqual(bot.set_my_commands.await_count, 2)
        self.assertEqual(bot.set_chat_menu_button.call_args.kwargs["menu_button"].type, "commands")
        self.assertNotIn("channelid", [c.command for c in USER_COMMANDS])
        self.assertNotIn("approveuid", [c.command for c in USER_COMMANDS])

    async def test_menu_setup_failure_does_not_stop_polling(self):
        bot = SimpleNamespace(set_my_commands=AsyncMock(side_effect=TelegramError("unavailable")), set_chat_menu_button=AsyncMock())
        await configure_command_menu(SimpleNamespace(bot=bot))


class UserCommandTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = SimpleNamespace(send_message=AsyncMock(),
            get_chat_member=AsyncMock(return_value=SimpleNamespace(status=ChatMemberStatus.MEMBER)))
        self.context = SimpleNamespace(bot=self.bot, user_data={"trade_awaiting_uid": 123},
            bot_data={"settings": Settings(token="fake"), "contacts": SimpleNamespace(has_contact=Mock(return_value=False))})
        self.update = SimpleNamespace(effective_user=SimpleNamespace(id=42))

    async def test_trade_command_preserves_phone_gate(self):
        await trade_command(self.update, self.context)
        self.assertNotIn("trade_awaiting_uid", self.context.user_data)
        keyboard = self.bot.send_message.call_args.kwargs["reply_markup"]
        self.assertTrue(keyboard.keyboard[0][0].request_contact)

    async def test_nodes_command_checks_membership(self):
        self.bot.get_chat_member.return_value = SimpleNamespace(status=ChatMemberStatus.LEFT)
        await nodes_command(self.update, self.context)
        self.assertIn("عضویت", self.bot.send_message.call_args.kwargs["text"])

    async def test_trade_support_has_only_dedicated_contact(self):
        await support_command(self.update, self.context)
        self.assertIn("Ahurasupport_trading", self.bot.send_message.call_args.kwargs["text"])
        self.assertNotIn("trade_awaiting_uid", self.context.user_data)

    async def test_help_replaces_myid_and_lists_user_actions(self):
        await help_command(self.update, self.context)
        text = self.bot.send_message.call_args.kwargs["text"]
        self.assertIn("42", text)
        self.assertIn("/deletephone", text)
        self.assertNotIn("/channelid", text)
        self.assertNotIn("/approveuid", text)
