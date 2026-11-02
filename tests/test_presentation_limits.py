"""Telegram command integrity and expanded RTL message limits."""
import re
import unittest
from html import unescape

from minerbot.presentation import rtl_html, telegram_text_parts


class TelegramRenderingTests(unittest.TestCase):
    def test_slash_command_remains_contiguous(self):
        self.assertIn('/deletephone', rtl_html('راهنما\n/deletephone'))

    def test_expanded_long_message_is_split_without_losing_content(self):
        body = 'a ' * 2000 + '<>&' + '😀' * 1000
        parts = telegram_text_parts(body)
        self.assertGreater(len(parts), 1)
        restored = []
        for part in parts:
            text = unescape(part.replace('<b>', '').replace('</b>', ''))
            self.assertLessEqual(len(text.encode('utf-16-le')), 8192)
            restored.append(re.sub('[\u200f\u2066\u2069]', '', text))
        self.assertEqual(''.join(restored).replace(' ', ''), body.replace(' ', ''))
