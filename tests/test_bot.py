"""Offline regression checks for the async migration; no Telegram requests."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from telegram.constants import ChatMemberStatus

from minerbot.application import build_application
from minerbot.config import ASSET_DIR, Settings, load_settings
from minerbot.catalog import catalog_summary, financial_details, product_card
from minerbot.content import CALLBACK_TEXTS, MENU_TEXTS, PRODUCTS, SETUP_VIDEOS
from minerbot.handlers import HOME_TEXT, UNKNOWN_TEXT, callback_handler, handle_messages, start
from minerbot.presentation import rtl_html
from minerbot.keyboards import product_keyboard, lightning_menu_keyboard


class ConfigurationTests(unittest.TestCase):
    def test_missing_token_has_actionable_error(self):
        with patch.dict(os.environ, {}, clear=True), patch("minerbot.config.load_dotenv"):
            with self.assertRaisesRegex(ValueError, "BOT_TOKEN"):
                load_settings()

    def test_environment_settings_and_secret_repr(self):
        with patch.dict(os.environ, {
            "BOT_TOKEN": "123:fake-token", "REQUIRED_CHANNEL_ID": "@test", "CHANNEL_URL": "https://t.me/test",
        }, clear=True), patch("minerbot.config.load_dotenv"):
            settings = load_settings()
        self.assertEqual(settings.required_channel_id, "@test")
        self.assertEqual(settings.channel_url, "https://t.me/test")
        self.assertNotIn(settings.token, repr(settings))

    def test_application_builds_without_network(self):
        application = build_application(Settings(token="123:fake-token"))
        self.assertEqual(len(application.handlers[0]), 6)
        self.assertTrue(application.error_handlers)


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = SimpleNamespace(
            send_message=AsyncMock(), send_photo=AsyncMock(), send_video=AsyncMock(),
            get_chat_member=AsyncMock(),
        )
        self.bot.get_chat_member.return_value = SimpleNamespace(status=ChatMemberStatus.MEMBER)
        self.context = SimpleNamespace(bot=self.bot, user_data={}, bot_data={"contacts": SimpleNamespace(has_contact=Mock(return_value=True), save_uid=Mock()), "settings": Settings(token="123:fake-token")})
        self.user = SimpleNamespace(id=42)

    def callback_update(self, data):
        return SimpleNamespace(callback_query=SimpleNamespace(data=data, from_user=self.user, answer=AsyncMock()))

    async def test_start_shows_membership_keyboard(self):
        await start(SimpleNamespace(effective_user=self.user), self.context)
        markup = self.bot.send_message.call_args.kwargs["reply_markup"]
        self.assertEqual(markup.inline_keyboard[-1][0].callback_data, "check_channel")

    async def test_membership_statuses(self):
        for status, accepted in [
            (ChatMemberStatus.OWNER, True), (ChatMemberStatus.ADMINISTRATOR, True),
            (ChatMemberStatus.MEMBER, True), (ChatMemberStatus.LEFT, False),
        ]:
            with self.subTest(status=status):
                self.bot.get_chat_member.return_value = SimpleNamespace(status=status)
                update = self.callback_update("check_channel")
                await callback_handler(update, self.context)
                update.callback_query.answer.assert_awaited_once()
                text = self.bot.send_message.call_args.kwargs["text"]
                self.assertEqual(text == rtl_html(HOME_TEXT), accepted)

    async def test_all_faq_callbacks_preserve_content(self):
        for data, text in CALLBACK_TEXTS.items():
            update = self.callback_update(data)
            await callback_handler(update, self.context)
            update.callback_query.answer.assert_awaited_once()
            self.assertEqual(self.bot.send_message.call_args.kwargs["text"], rtl_html(text))

    async def test_all_products_have_working_buttons_and_assets(self):
        for label, product in PRODUCTS.items():
            with self.subTest(product=label):
                update = SimpleNamespace(effective_user=self.user, effective_message=SimpleNamespace(text=label))
                await handle_messages(update, self.context)
                if product["image"]:
                    self.assertTrue((ASSET_DIR / product["image"]).is_file())
                    sent = self.bot.send_photo.call_args.kwargs
                    self.assertEqual(sent["caption"], rtl_html(product_card(product)))
                else:
                    self.assertEqual(self.bot.send_message.call_args.kwargs["text"], rtl_html(product_card(product)))
                for row in product_keyboard(product).inline_keyboard:
                    for button in row:
                        if button.callback_data.startswith("info:"):
                            self.assertIn(button.callback_data.split(":", 2)[2], CALLBACK_TEXTS.keys() | SETUP_VIDEOS.keys() | {p[key] for p in PRODUCTS.values() for key in ("order_callback", "income_callback")})
                        else:
                            self.assertIn(button.callback_data, {"home", "contact", "lightning"})
                        self.assertLessEqual(len(button.callback_data.encode()), 64)

    async def test_video_routes_and_local_file_closure(self):
        for data in SETUP_VIDEOS:
            await callback_handler(self.callback_update(data), self.context)
            video = self.bot.send_video.call_args.kwargs["video"]
            if not isinstance(video, str):
                self.assertTrue(video.closed)

    async def test_contact_agency_and_unknown_message(self):
        for text in [*MENU_TEXTS, "unknown"]:
            update = SimpleNamespace(effective_user=self.user, effective_message=SimpleNamespace(text=text))
            await handle_messages(update, self.context)
            self.assertEqual(
                self.bot.send_message.call_args.kwargs["text"], rtl_html(MENU_TEXTS.get(text, UNKNOWN_TEXT)),
            )


class PresentationTests(unittest.TestCase):
    def test_rtl_html_escapes_markup_and_isolates_latin(self):
        rendered = rtl_html("راهنما\n  اتصال HDMI و BTC <test> & کیف پول  ")
        self.assertTrue(rendered.startswith("<b>\u200f"))
        self.assertIn("\u2066HDMI\u2069", rendered)
        self.assertIn("&lt;", rendered)
        self.assertIn("&amp;", rendered)
        self.assertNotIn("<test>", rendered)
        self.assertTrue(rendered.splitlines()[1].startswith("\u200f"))

    def test_signed_performance_amounts_keep_sign_inside_ltr_isolate(self):
        rendered = rtl_html("گزارش\nسود: +4,325.73\nضرر: -850")
        self.assertIn("\u2066+4,325.73\u2069", rendered)
        self.assertIn("\u2066-850\u2069", rendered)

    def test_source_url_is_not_split_by_direction_marks(self):
        url = "https://ahuraminer.com/products/lightning-nodes"
        self.assertIn("\u2066" + url + "\u2069", rtl_html("منبع\n" + url))

    def test_buttons_have_native_styles_and_fit_callback_limits(self):
        from minerbot.keyboards import channel_keyboard, main_keyboard
        keyboards = [main_keyboard(), channel_keyboard(Settings(token="fake"))]
        keyboards.extend(product_keyboard(product) for product in PRODUCTS.values())
        styles = set()
        for keyboard in keyboards:
            for row in keyboard.inline_keyboard:
                self.assertLessEqual(len(row), 2)
                for button in row:
                    styles.add(button.to_dict().get("style"))
                    if button.callback_data:
                        self.assertLessEqual(len(button.callback_data.encode()), 64)
        self.assertIn("primary", styles)
        self.assertIn("success", styles)

    def test_product_captions_fit_telegram_limit(self):
        for product in PRODUCTS.values():
            self.assertLessEqual(len(rtl_html(product_card(product))), 1024)


class NavigationTests(unittest.IsolatedAsyncioTestCase):
    setUp = HandlerTests.setUp
    callback_update = HandlerTests.callback_update

    async def test_new_inline_product_routes(self):
        from minerbot.keyboards import PRODUCT_IDS
        for product_id, label in PRODUCT_IDS.items():
            await callback_handler(self.callback_update(f"product:{product_id}"), self.context)
            product = PRODUCTS[label]
            sent = self.bot.send_photo.call_args.kwargs if product["image"] else self.bot.send_message.call_args.kwargs
            self.assertEqual(sent["caption" if product["image"] else "text"], rtl_html(product_card(product)))

    async def test_detail_returns_to_same_product(self):
        for product in PRODUCTS.values():
            for row in product_keyboard(product).inline_keyboard:
                for button in row:
                    if not button.callback_data.startswith("info:"):
                        continue
                    _, product_id, topic = button.callback_data.split(":", 2)
                    await callback_handler(self.callback_update(button.callback_data), self.context)
                    sender = self.bot.send_video if topic in SETUP_VIDEOS else self.bot.send_message
                    markup = sender.call_args.kwargs["reply_markup"]
                    self.assertEqual(markup.inline_keyboard[0][0].callback_data, f"product:{product_id}")
                    self.assertEqual(markup.inline_keyboard[-1][0].callback_data, "home")

    async def test_main_contact_and_agency_routes(self):
        for data in ["home", "contact", "agency", "info:invalid", "product:invalid", "unknown"]:
            await callback_handler(self.callback_update(data), self.context)
            self.assertIsNotNone(self.bot.send_message.call_args.kwargs["reply_markup"])





class CatalogMenuTests(unittest.IsolatedAsyncioTestCase):
    setUp = HandlerTests.setUp
    callback_update = HandlerTests.callback_update

    async def test_start_installs_dismissible_bottom_keyboard(self):
        from telegram import ReplyKeyboardMarkup
        await start(SimpleNamespace(effective_user=self.user), self.context)
        markup = self.bot.send_message.call_args_list[0].kwargs["reply_markup"]
        self.assertIsInstance(markup, ReplyKeyboardMarkup)
        self.assertFalse(markup.is_persistent)
        self.assertFalse(lightning_menu_keyboard().is_persistent)
        labels = {button.text for row in markup.keyboard for button in row}
        self.assertEqual(len(labels), 2)
        lightning_labels = {button.text for row in lightning_menu_keyboard().keyboard for button in row}
        self.assertTrue(set(PRODUCTS).issubset(lightning_labels))

    async def test_home_and_menu_restore_bottom_keyboard(self):
        from telegram import ReplyKeyboardMarkup
        from minerbot.handlers import menu
        await menu(SimpleNamespace(effective_user=self.user), self.context)
        self.assertIsInstance(self.bot.send_message.call_args.kwargs["reply_markup"], ReplyKeyboardMarkup)
        await callback_handler(self.callback_update("home"), self.context)
        self.assertIsInstance(self.bot.send_message.call_args.kwargs["reply_markup"], ReplyKeyboardMarkup)

    async def test_price_and_income_routes_use_single_catalog(self):
        for product in PRODUCTS.values():
            for key in ["order_callback", "income_callback"]:
                await callback_handler(self.callback_update(product[key]), self.context)
                self.assertEqual(self.bot.send_message.call_args.kwargs["text"],
                                 rtl_html(financial_details(product, income=key == "income_callback")))

    async def test_price_summary_from_both_menus(self):
        await callback_handler(self.callback_update("prices"), self.context)
        self.assertEqual(self.bot.send_message.call_args.kwargs["text"], rtl_html(catalog_summary()))
        update = SimpleNamespace(effective_user=self.user,
                                 effective_message=SimpleNamespace(text="💵 قیمت و درآمد دستگاه‌ها"))
        await handle_messages(update, self.context)
        self.assertEqual(self.bot.send_message.call_args.kwargs["text"], rtl_html(catalog_summary()))

    def test_catalog_matches_source_snapshot_and_currency_disclosure(self):
        expected = {"1": (1020, 50), "2": (1400, 75), "3": (4050, 250), "4": (6750, 410)}
        for product in PRODUCTS.values():
            product_id = product["order_callback"].removeprefix("order_delivery")
            self.assertEqual((product["price_usdt"], product["monthly_income_usd"]), expected[product_id])
            card = product_card(product)
            self.assertIn("۱ دلار ≈ ۱ USDT", card)
            self.assertIn("ارقام موقت", card)
            self.assertEqual(card.count("USDT"), 3)


class AccessTests(unittest.IsolatedAsyncioTestCase):
    setUp = HandlerTests.setUp
    callback_update = HandlerTests.callback_update

    async def test_nonmember_cannot_open_device_or_old_callback(self):
        self.bot.get_chat_member.return_value = SimpleNamespace(status=ChatMemberStatus.LEFT)
        for data in ["product:4", "income3", "info:1:order_delivery1", "prices", "home"]:
            await callback_handler(self.callback_update(data), self.context)
            markup = self.bot.send_message.call_args.kwargs["reply_markup"]
            self.assertEqual(markup.inline_keyboard[-1][0].callback_data, "check_channel")
        self.bot.send_photo.assert_not_awaited()
        self.bot.send_video.assert_not_awaited()

    async def test_nonmember_cannot_bypass_gate_with_keyboard_text_or_menu(self):
        from minerbot.handlers import menu
        self.bot.get_chat_member.return_value = SimpleNamespace(status=ChatMemberStatus.LEFT)
        for label in PRODUCTS:
            await handle_messages(SimpleNamespace(effective_user=self.user,
                                  effective_message=SimpleNamespace(text=label)), self.context)
        await menu(SimpleNamespace(effective_user=self.user), self.context)
        self.bot.send_photo.assert_not_awaited()
        self.assertIn("عضویت", self.bot.send_message.call_args.kwargs["text"])

    async def test_mismatched_device_callback_is_rejected(self):
        await callback_handler(self.callback_update("info:1:order_delivery4"), self.context)
        self.assertEqual(self.bot.send_message.call_args.kwargs["text"], rtl_html(UNKNOWN_TEXT))


class MultipleChannelTests(unittest.IsolatedAsyncioTestCase):
    setUp = HandlerTests.setUp
    callback_update = HandlerTests.callback_update

    async def test_second_channel_is_required(self):
        self.bot.get_chat_member.side_effect = [
            SimpleNamespace(status=ChatMemberStatus.MEMBER),
            SimpleNamespace(status=ChatMemberStatus.LEFT),
        ]
        await callback_handler(self.callback_update("product:1"), self.context)
        self.bot.send_photo.assert_not_awaited()
        self.assertEqual(self.bot.get_chat_member.call_args.args[0], "@ahuramine")
        markup = self.bot.send_message.call_args.kwargs["reply_markup"]
        self.assertEqual([row[0].url for row in markup.inline_keyboard[:-1]],
                         ["https://t.me/Ahuraminenode", "https://t.me/ahuramine"])

    async def test_member_of_both_can_open_device(self):
        await callback_handler(self.callback_update("product:1"), self.context)
        self.assertEqual(self.bot.get_chat_member.await_count, 2)
        self.bot.send_photo.assert_awaited_once()

    def test_channels_are_deduplicated(self):
        settings = Settings(token="fake", additional_channel_ids=("@ahuraminenode", "@ahuramine", "@AHURAMINE"))
        self.assertEqual(len(settings.required_channels), 2)


class LoggingTests(unittest.TestCase):
    def test_credentials_are_redacted_in_messages_and_tracebacks(self):
        import io
        import logging
        from minerbot.logging_setup import SecretFilter
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        settings = Settings(token="123:fake-sensitive-token", xt_api_key="test-api-key", xt_api_secret="test-api-secret")
        handler.addFilter(SecretFilter(settings))
        logger = logging.getLogger("test.secret-redaction")
        logger.addHandler(handler)
        logger.propagate = False
        try:
            try:
                raise RuntimeError(settings.token)
            except RuntimeError:
                logger.error("%s %s", settings.xt_api_key, settings.xt_api_secret, exc_info=True)
            output = stream.getvalue()
            for secret in [settings.token, settings.xt_api_key, settings.xt_api_secret]:
                self.assertNotIn(secret, output)
            self.assertIn("RuntimeError", output)
            self.assertIn("[REDACTED]", output)
        finally:
            logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
