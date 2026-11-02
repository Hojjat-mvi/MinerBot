"""Account privacy regressions for member services."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from minerbot.contacts import ContactStore
from minerbot.member_services import account_command


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
