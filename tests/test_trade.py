"""Synthetic XT API and Telegram tests. Never uses live credentials or funds."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
from telegram.constants import ChatMemberStatus

from minerbot.config import Settings
from minerbot.handlers import callback_handler, handle_messages, menu, start
from minerbot.keyboards import LIGHTNING_LABEL, TRADE_LABEL
from minerbot.xt import Eligibility, XTUnavailable, XTVerifier, normalize_uid, signed_headers


class XTTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = Settings(token="fake", xt_api_key="example-app-key", xt_api_secret="example-secret", xt_referral_code="AHURA")
        self.requests = []
        self.sleep_patch = patch("minerbot.xt.asyncio.sleep", new_callable=AsyncMock)
        self.sleep_patch.start()
        self.addCleanup(self.sleep_patch.stop)

    def verifier(self, invited=True, code="AHURA", records=None, user_id=123456, response_override=None):
        def handler(request):
            self.requests.append(request)
            if response_override:
                return response_override(request)
            self.assertEqual(request.method, "GET")
            self.assertEqual(str(request.url.host), "api.xt.com")
            self.assertEqual(dict(request.url.params), {"uid": "123456"})
            self.assertEqual(request.headers["validate-algorithms"], "HmacSHA256")
            self.assertEqual(len(request.headers["validate-signature"]), 64)
            path = request.url.path
            if path.endswith("/check"):
                result = invited
            elif path.endswith("/info"):
                result = {"uid": user_id, "registerInviteCode": code}
            else:
                self.assertEqual(path, "/v4/referal/invite/user/data")
                result = {"userId": user_id, "depositDetails": records if records is not None else [{"amountU": "100", "currency": "USDT"}]}
            return httpx.Response(200, json={"rc": 0, "mc": "SUCCESS", "result": result})
        return XTVerifier(self.settings, transport=httpx.MockTransport(handler))

    def test_signature_vector(self):
        headers = signed_headers("example-app-key", "example-secret", "/v4/referal/invite/check", "uid=123456", 1700000000000)
        self.assertEqual(headers["validate-signature"], "23d282c60162270ccded09e02c6c16e5e7916abcb0bf92f59540adb37b3f9387")
        self.assertEqual(headers["validate-recvwindow"], "5000")

    def test_registration_button_uses_configured_link(self):
        from minerbot.keyboards import trade_keyboard
        link = "https://www.xtfarsi.net/ref/7YX74I"
        self.assertEqual(trade_keyboard(link).inline_keyboard[0][0].url, link)
        self.assertEqual(
            {button.url for row in trade_keyboard().inline_keyboard for button in row if button.url},
            {"https://t.me/Ahurasupport_trading"},
        )

    def test_uid_normalization(self):
        self.assertEqual(normalize_uid(" ۱۲۳۴۵۶ "), "123456")
        self.assertEqual(normalize_uid("١٢٣٤٥٦"), "123456")
        for value in ["0", "-1", "1.5", "1e5", "123abc", "", "123&uid=456", "9" * 50]:
            self.assertIsNone(normalize_uid(value))

    def test_settings_hide_secrets_and_require_all_configuration(self):
        self.assertNotIn("example-secret", repr(self.settings))
        self.assertNotIn("example-app-key", repr(self.settings))
        self.assertTrue(self.settings.xt_ready)
        self.assertFalse(Settings(token="fake", xt_api_key="key", xt_api_secret="secret").xt_ready)

    async def test_exact_threshold_passes(self):
        self.assertTrue((await self.verifier().verify("123456")).eligible)
        self.assertEqual(len(self.requests), 3)

    async def test_total_of_multiple_deposits_passes(self):
        result = await self.verifier(records=[{"amountU": "60.01"}, {"amountU": "39.99"}]).verify("123456")
        self.assertTrue(result.eligible)

    async def test_below_threshold_and_empty_records_do_not_pass(self):
        for records in [[{"amountU": "99.999999"}], []]:
            with self.subTest(records=records):
                result = await self.verifier(records=records).verify("123456")
                self.assertTrue(result.referred)
                self.assertFalse(result.eligible)

    async def test_high_precision_value_below_100_cannot_round_up(self):
        result = await self.verifier(records=[{"amountU": "99." + "9" * 40}]).verify("123456")
        self.assertFalse(result.eligible)

    async def test_extreme_exponents_are_rejected(self):
        for value in ["1e999999", "1e-999999"]:
            with self.subTest(value=value), self.assertRaises(XTUnavailable):
                await self.verifier(records=[{"amountU": value}]).verify("123456")

    async def test_uninvited_user_never_queries_financial_data(self):
        self.assertFalse((await self.verifier(invited=False).verify("123456")).eligible)
        self.assertEqual(len(self.requests), 1)

    async def test_wrong_code_never_queries_financial_data(self):
        self.assertFalse((await self.verifier(code="OTHER").verify("123456")).eligible)
        self.assertEqual(len(self.requests), 2)

    async def test_missing_code_or_wrong_user_is_unavailable(self):
        for options in [{"code": None}, {"user_id": 999}]:
            with self.subTest(options=options), self.assertRaises(XTUnavailable):
                await self.verifier(**options).verify("123456")

    async def test_string_boolean_does_not_pass(self):
        with self.assertRaises(XTUnavailable):
            await self.verifier(invited="true").verify("123456")

    async def test_invalid_deposit_values_do_not_pass(self):
        for record in [{}, {"amountU": None}, {"amountU": True}, {"amountU": "NaN"}, {"amountU": "Infinity"}, {"amountU": "-100"}]:
            with self.subTest(record=record), self.assertRaises(XTUnavailable):
                await self.verifier(records=[record]).verify("123456")

    async def test_http_and_exchange_errors_do_not_pass(self):
        for response in [httpx.Response(429), httpx.Response(500), httpx.Response(200, json={"rc": 1, "result": True}),
                         httpx.Response(200, json={"rc": False, "result": True}), httpx.Response(200, text="not-json")]:
            with self.subTest(response=response), self.assertRaises(XTUnavailable):
                await self.verifier(response_override=lambda request: response).verify("123456")

    async def test_timeout_does_not_pass(self):
        def timeout(request):
            raise httpx.ReadTimeout("test timeout")
        with self.assertRaises(XTUnavailable):
            await self.verifier(response_override=timeout).verify("123456")

    async def test_unconfigured_verifier_makes_no_requests(self):
        verifier = XTVerifier(Settings(token="fake"))
        with self.assertRaises(XTUnavailable):
            await verifier.verify("123456")


class TradeFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = Settings(token="fake", xt_api_key="key", xt_api_secret="secret", xt_referral_code="AHURA")
        self.bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock(),
                                   get_chat=AsyncMock(return_value=SimpleNamespace(type="channel", username=None)),
                                   create_chat_invite_link=AsyncMock(return_value=SimpleNamespace(invite_link="https://t.me/+test_bound_invite")),
                                   revoke_chat_invite_link=AsyncMock(), get_chat_member=AsyncMock(return_value=SimpleNamespace(status=ChatMemberStatus.MEMBER)))
        self.verifier = SimpleNamespace(verify=AsyncMock(return_value=Eligibility(True, True)))
        self.context = SimpleNamespace(bot=self.bot, user_data={},
                                       bot_data={"contacts": SimpleNamespace(has_contact=Mock(return_value=True), save_uid=Mock(), binding_conflicts=Mock(return_value=False), binding_matches=Mock(return_value=True), take_xt_slot=Mock(return_value=True), request_ownership=Mock(), claim_binding=Mock(), save_admission=Mock()), "settings": self.settings, "xt_verifier": self.verifier})
        self.user = SimpleNamespace(id=42)

    async def callback(self, data):
        update = SimpleNamespace(callback_query=SimpleNamespace(data=data, from_user=self.user, answer=AsyncMock()))
        await callback_handler(update, self.context)

    async def text(self, value):
        await handle_messages(SimpleNamespace(effective_user=self.user, effective_message=SimpleNamespace(text=value)), self.context)

    async def test_home_has_only_two_sections_and_lightning_has_devices(self):
        await menu(SimpleNamespace(effective_user=self.user), self.context)
        markup = self.bot.send_message.call_args.kwargs["reply_markup"]
        self.assertEqual({b.text for row in markup.keyboard for b in row}, {LIGHTNING_LABEL, TRADE_LABEL})
        await self.text(LIGHTNING_LABEL)
        markup = self.bot.send_message.call_args.kwargs["reply_markup"]
        self.assertIn("مدل ده کانال 🚀", {b.text for row in markup.keyboard for b in row})

    async def test_missing_code_leaves_trade_unavailable(self):
        self.context.bot_data["settings"] = Settings(token="fake")
        await self.callback("trade:check")
        self.assertNotIn("trade_awaiting_uid", self.context.user_data)
        self.verifier.verify.assert_not_awaited()

    async def test_uid_flow_qualifies_but_does_not_persist_ownership(self):
        await self.callback("trade:check")
        await self.text("۱۲۳۴۵۶")
        self.verifier.verify.assert_awaited_once_with("123456")
        self.assertIn("شرایط حساب تأیید شد", self.bot.send_message.call_args.kwargs["text"])
        self.assertNotIn("trade_awaiting_uid", self.context.user_data)
        self.assertNotIn("123456", repr(self.context.user_data))

    async def test_invalid_uid_does_not_query_xt(self):
        await self.callback("trade:check")
        await self.text("not-a-uid")
        self.verifier.verify.assert_not_awaited()
        self.assertIn("trade_awaiting_uid", self.context.user_data)

    async def test_menu_navigation_cancels_pending_uid(self):
        for label in [LIGHTNING_LABEL, TRADE_LABEL, "🏠 منوی اصلی"]:
            await self.callback("trade:check")
            await self.text(label)
            self.assertNotIn("trade_awaiting_uid", self.context.user_data)
        self.verifier.verify.assert_not_awaited()

    async def test_nonmember_cannot_verify(self):
        self.bot.get_chat_member.return_value = SimpleNamespace(status=ChatMemberStatus.LEFT)
        await self.callback("trade:check")
        await self.text("123456")
        self.verifier.verify.assert_not_awaited()

    async def test_unavailable_response_does_not_approve(self):
        self.verifier.verify.side_effect = XTUnavailable()
        await self.callback("trade:check")
        await self.text("123456")
        self.assertIn("بررسی حساب انجام نشد", self.bot.send_message.call_args.kwargs["text"])

    async def test_deposit_failure_and_referral_failure(self):
        for result, expected in [(Eligibility(False), "کد دعوت تأیید نشد"), (Eligibility(True, False), "نرسیده است")]:
            self.context.user_data.clear()
            self.verifier.verify.return_value = result
            await self.callback("trade:check")
            await self.text("123456")
            self.assertIn(expected, self.bot.send_message.call_args.kwargs["text"])

    async def test_repeated_checks_have_cooldown(self):
        await self.callback("trade:check")
        await self.text("123456")
        await self.callback("trade:check")
        await self.text("123456")
        self.verifier.verify.assert_awaited_once()
        self.assertIn("صبر کنید", self.bot.send_message.call_args.kwargs["text"])

    async def test_uid_expires_and_needs_explicit_check_button(self):
        await self.text("123456")
        self.verifier.verify.assert_not_awaited()
        self.context.user_data["trade_awaiting_uid"] = 1
        await self.text("123456")
        self.verifier.verify.assert_not_awaited()
        self.assertNotIn("trade_awaiting_uid", self.context.user_data)



class RewardTests(unittest.IsolatedAsyncioTestCase):
    setUp = TradeFlowTests.setUp
    callback = TradeFlowTests.callback
    text = TradeFlowTests.text

    def test_reward_config_accepts_private_invites_and_rejects_other_urls(self):
        import os
        from minerbot.config import load_settings
        for link, valid in [("https://t.me/+test_private_invite", True),
                            ("https://t.me/joinchat/test_private_invite", True),
                            ("http://t.me/+test", False), ("https://example.com/+test", False),
                            ("https://t.me/public_channel", False)]:
            with self.subTest(link=link), patch.dict(os.environ, {"BOT_TOKEN": "123:fake", "XT_REWARD_CHANNEL_URL": link}, clear=True), patch("minerbot.config.load_dotenv"):
                if valid:
                    settings = load_settings()
                    self.assertEqual(settings.xt_reward_channel_url, link)
                    self.assertNotIn(link, repr(settings))
                else:
                    with self.assertRaises(ValueError):
                        load_settings()

    async def test_qualified_user_gets_reward_link_when_configured(self):
        from dataclasses import replace
        link = "https://t.me/+test_private_invite"
        self.context.bot_data["settings"] = replace(self.settings, xt_reward_channel_url=link, xt_reward_channel_id=-1001234567890)
        await self.callback("trade:check")
        await self.text("123456")
        keyboard = self.bot.send_message.call_args.kwargs["reply_markup"]
        self.assertEqual(keyboard.inline_keyboard[0][0].url, "https://t.me/+test_bound_invite")
        self.bot.create_chat_invite_link.assert_awaited_once()
        self.assertNotIn(link, str(self.bot.send_message.call_args.kwargs))

    async def test_unqualified_or_failed_checks_never_expose_reward(self):
        from dataclasses import replace
        link = "https://t.me/+test_private_invite"
        self.context.bot_data["settings"] = replace(self.settings, xt_reward_channel_url=link)
        for outcome in [Eligibility(False), Eligibility(True, False), XTUnavailable()]:
            self.context.user_data.clear()
            self.verifier.verify.side_effect = outcome if isinstance(outcome, Exception) else None
            self.verifier.verify.return_value = outcome
            await self.callback("trade:check")
            await self.text("123456")
            self.assertNotIn(link, str(self.bot.send_message.call_args.kwargs))

    async def test_missing_link_shows_reward_pending(self):
        await self.callback("trade:check")
        await self.text("123456")
        self.assertIn("عضویت امن کانال هنوز پیکربندی نشده", self.bot.send_message.call_args.kwargs["text"])

    async def test_trade_screen_does_not_expose_configured_reward(self):
        from dataclasses import replace
        link = "https://t.me/+test_private_invite"
        self.context.bot_data["settings"] = replace(self.settings, xt_reward_channel_url=link)
        await self.callback("trade")
        self.assertNotIn(link, str(self.bot.send_message.call_args.kwargs))



class TradeRoomTests(unittest.IsolatedAsyncioTestCase):
    setUp = TradeFlowTests.setUp
    callback = TradeFlowTests.callback
    text = TradeFlowTests.text

    async def test_room_shows_three_sections_from_text_and_callback(self):
        from minerbot.keyboards import TRAINING_LABEL, SUBSCRIPTIONS_LABEL, RESULTS_LABEL
        for entry in ["text", "callback"]:
            if entry == "text":
                await self.text(TRADE_LABEL)
            else:
                await self.callback("trade")
            sent = self.bot.send_message.call_args.kwargs
            labels = [button.text for row in sent["reply_markup"].keyboard for button in row]
            self.assertEqual(labels, [SUBSCRIPTIONS_LABEL, RESULTS_LABEL, TRAINING_LABEL, "🏠 منوی اصلی"])
            self.assertNotIn("vpn", sent["text"])
            self.assertEqual(sent["parse_mode"], "HTML")
            self.verifier.verify.assert_not_awaited()

    async def test_subsection_callbacks_do_not_trigger_verification(self):
        for data in ["trade:free", "trade:training", "trade:monthly"]:
            await self.callback(data)
            self.assertNotIn("گزینه پیدا نشد", self.bot.send_message.call_args.kwargs["text"])
        self.verifier.verify.assert_not_awaited()

    def test_emphasized_lines_are_escaped_without_nested_bold(self):
        from minerbot.presentation import rtl_html
        result = rtl_html("عنوان\n<b>متن</b>", bold_lines=("عنوان", "<b>متن</b>"))
        self.assertNotIn("<b><b>", result)
        self.assertIn("&lt;b&gt;", result.replace("\u2066", "").replace("\u2069", ""))
        self.assertEqual(result.count("<b>"), 2)

    async def test_free_subscription_keeps_existing_uid_check(self):
        from minerbot.keyboards import FREE_LABEL
        await self.text(FREE_LABEL)
        sent = self.bot.send_message.call_args.kwargs
        self.assertIn("<b>\u200fلطفا \u2066vpn\u2069 خود را خاموش کنید</b>", sent["text"])
        self.assertIn("حساب خود را ۱۰۰ دلار شارژ کنید", sent["text"])
        self.assertIn("گزینه بررسی شرایط حساب را بزنید", sent["text"])
        self.assertIn("حساب صرافی خودتان را ارسال کنید", sent["text"])
        markup = sent["reply_markup"]
        self.assertIn("trade:check", {button.callback_data for row in markup.inline_keyboard for button in row})
        await self.callback("trade:check")
        await self.text("123456")
        self.verifier.verify.assert_awaited_once_with("123456")

    async def test_section_buttons_cancel_uid_input(self):
        from minerbot.keyboards import TRAINING_LABEL, MONTHLY_LABEL
        for label in [TRAINING_LABEL, MONTHLY_LABEL]:
            await self.callback("trade:check")
            await self.text(label)
            self.assertNotIn("trade_awaiting_uid", self.context.user_data)
            markup = self.bot.send_message.call_args.kwargs["reply_markup"]
            self.assertIn("trade", {button.callback_data for row in markup.inline_keyboard for button in row})
        self.verifier.verify.assert_not_awaited()

    async def test_legacy_labels_with_whitespace_still_route(self):
        for label in ["🆓 اشتراک رایگان ", "🧑🏻‍🏫 اموزش کار با صرافی", "␚ اشتراک ماهانه"]:
            await self.text(label)
            self.assertNotIn("گزینه پیدا نشد", self.bot.send_message.call_args.kwargs["text"])

    async def test_room_is_available_without_xt_configuration(self):
        self.context.bot_data["settings"] = Settings(token="fake")
        await self.text(TRADE_LABEL)
        self.assertIsNotNone(self.bot.send_message.call_args.kwargs["reply_markup"].keyboard)
        await self.text("اشتراک رایگان")
        self.assertIn("هنوز فعال نشده", self.bot.send_message.call_args.kwargs["text"])



class SubscriptionContactTests(unittest.IsolatedAsyncioTestCase):
    setUp = TradeFlowTests.setUp
    text = TradeFlowTests.text

    async def test_monthly_subscription_prices_and_support_buttons(self):
        from minerbot.content import SUPPORT_CONTACTS, SALES_CONTACTS
        from minerbot.keyboards import MONTHLY_LABEL
        await self.text(MONTHLY_LABEL)
        sent = self.bot.send_message.call_args.kwargs
        for amount in ["۱۰۰", "۲۵۰", "۴۰۰", "۷۰۰"]:
            self.assertIn(amount + " دلار", sent["text"])
        urls = {button.url for row in sent["reply_markup"].inline_keyboard for button in row if button.url}
        self.assertEqual(urls, {"https://t.me/Ahurasupport_trading"})
        self.assertIn("Ahurasupport_trading", sent["text"])
        for username, phone in SUPPORT_CONTACTS:
            self.assertNotIn(username, sent["text"])
            self.assertNotIn(phone, sent["text"])
        for username, _ in SALES_CONTACTS:
            self.assertNotIn("https://t.me/" + username, urls)

    async def test_contact_details_match_buttons(self):
        from minerbot.content import SUPPORT_CONTACTS, SALES_CONTACTS
        await self.text("ارتباط با ما 📧")
        sent = self.bot.send_message.call_args.kwargs
        urls = {button.url for row in sent["reply_markup"].inline_keyboard for button in row if button.url}
        for username, phone in SUPPORT_CONTACTS + SALES_CONTACTS:
            self.assertIn(username, sent["text"])
            self.assertIn(phone, sent["text"])
            self.assertIn("https://t.me/" + username, urls)



class NestedSubscriptionTests(unittest.IsolatedAsyncioTestCase):
    setUp = TradeFlowTests.setUp
    callback = TradeFlowTests.callback
    text = TradeFlowTests.text

    async def test_subscription_menu_contains_both_renamed_options(self):
        from minerbot.keyboards import SUBSCRIPTIONS_LABEL, FREE_LABEL, MONTHLY_LABEL
        for entry in ["text", "callback"]:
            if entry == "text":
                await self.text(SUBSCRIPTIONS_LABEL)
            else:
                await self.callback("trade:subscriptions")
            labels = [b.text for row in self.bot.send_message.call_args.kwargs["reply_markup"].keyboard for b in row]
            self.assertEqual(labels[:2], [FREE_LABEL, MONTHLY_LABEL])

    async def test_results_navigation_cancels_uid_input(self):
        from minerbot.keyboards import RESULTS_LABEL
        await self.callback("trade:check")
        await self.text(RESULTS_LABEL)
        self.assertNotIn("trade_awaiting_uid", self.context.user_data)
        self.assertIn("Trading Performance", self.bot.send_message.call_args.kwargs["text"])
        self.verifier.verify.assert_not_awaited()

    async def test_uid_saved_with_result_status(self):
        await self.callback("trade:check")
        await self.text("۱۲۳۴۵۶")
        saved = self.context.bot_data["contacts"].save_uid
        saved.assert_any_call(42, "123456", status="submitted")
        saved.assert_any_call(42, "123456", status="eligible")

    async def test_api_failure_saves_unavailable_without_eligibility(self):
        self.verifier.verify.side_effect = XTUnavailable()
        await self.callback("trade:check")
        await self.text("123456")
        self.context.bot_data["contacts"].save_uid.assert_called_with(42, "123456", status="unavailable")



class TradeSupportPerformanceTests(unittest.IsolatedAsyncioTestCase):
    setUp = TradeFlowTests.setUp
    callback = TradeFlowTests.callback
    text = TradeFlowTests.text

    async def test_performance_report_has_bold_period_and_supplied_totals(self):
        await self.callback("trade:results")
        sent = self.bot.send_message.call_args.kwargs
        self.assertIn("<b>\u200fبرآیند ۴۵ روز گذشته</b>", sent["text"])
        for value in ["۷۳ معامله", "۵۶ تارگت", "۱۷ استاپ", "4,325.73", "-850", "3,475.73"]:
            self.assertIn(value, sent["text"])

    async def test_legacy_trade_contact_only_shows_trading_support(self):
        await self.callback("trade")
        await self.callback("contact")
        sent = self.bot.send_message.call_args.kwargs
        urls = {b.url for row in sent["reply_markup"].inline_keyboard for b in row if b.url}
        self.assertEqual(urls, {"https://t.me/Ahurasupport_trading"})
        self.assertIn("Ahurasupport_trading", sent["text"])
        self.assertNotIn("091", sent["text"])

    def test_all_trade_support_keyboards_have_only_one_support_destination(self):
        from minerbot.keyboards import trade_keyboard, trade_section_keyboard, subscription_keyboard
        for keyboard in [trade_keyboard(), trade_section_keyboard(), subscription_keyboard()]:
            urls = [b.url for row in keyboard.inline_keyboard for b in row if b.url]
            self.assertEqual(urls, ["https://t.me/Ahurasupport_trading"])
            for row in keyboard.inline_keyboard:
                for button in row:
                    if button.url:
                        self.assertEqual(button.text, "💬 پشتیبانی")


if __name__ == "__main__":
    unittest.main()
