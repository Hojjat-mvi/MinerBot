"""Ledger calculations and admin isolation. No external services required."""
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import tempfile
import unittest

from minerbot.contacts import ContactStore
from minerbot.performance import metrics, number, timestamp, chart_png, performance_admin, connect
from contextlib import closing


class CalculationTests(unittest.TestCase):
    def test_results_and_closed_equity_drawdown(self):
        result = metrics([{'pnl': '100'}, {'pnl': '-50'}, {'pnl': '0'}], Decimal(1000))
        self.assertEqual(result['net'], Decimal(50))
        self.assertEqual(result['factor'], Decimal(2))
        self.assertEqual(result['roi'], Decimal(5))
        self.assertEqual(result['drawdown'], Decimal(50)/1100*100)
        self.assertEqual(result['breakeven'], 1)
        self.assertEqual(result['win_rate'], Decimal(100)/3)

    def test_empty_no_losses_and_insolvency(self):
        self.assertIsNone(metrics([], Decimal(100))['win_rate'])
        self.assertIsNone(metrics([{'pnl': '1'}], Decimal(100))['factor'])
        self.assertIsNone(metrics([{'pnl': '-100'}], Decimal(100))['roi'])
        self.assertIsNone(metrics([], Decimal(0))['drawdown'])

    def test_validation_and_png(self):
        for raw in ('NaN', 'Infinity', '1e30', '0.000000001'):
            with self.assertRaises(ValueError):
                number(raw)
        with self.assertRaises(ValueError):
            timestamp('2026-01-01')
        self.assertEqual(timestamp('2026-01-01T03:30:00+03:30').hour, 0)
        self.assertTrue(chart_png([Decimal(0), Decimal(5)]).startswith(b'\x89PNG\r\n\x1a\n'))


class AdminTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.context = SimpleNamespace(bot_data={
            'contacts': ContactStore(Path(directory.name)/'db.sqlite3'),
            'settings': SimpleNamespace(trade_admin_ids=(99,))})

    async def command(self, text, user=99):
        update = SimpleNamespace(effective_user=SimpleNamespace(id=user), effective_message=SimpleNamespace(text=text))
        with patch('minerbot.performance.send_text', new_callable=AsyncMock):
            await performance_admin(update, self.context)

    async def test_admin_permissions_duplicates_void_and_locked_setup(self):
        await self.command('/perfsetup 1000 USDT 2020-01-01T00:00:00Z', user=42)
        with closing(connect(self.context)) as connection:
            self.assertIsNone(connection.execute('SELECT * FROM performance_config').fetchone())
        await self.command('/perfsetup 1000 USDT 2020-01-01T00:00:00Z')
        await self.command('/addtrade ref1 2020-01-02T00:00:00Z 10 BTC/USDT')
        await self.command('/addtrade ref1 2020-01-02T00:00:00Z 99 BTC/USDT')
        await self.command('/perfsetup 999 EUR 2020-01-01T00:00:00Z')
        await self.command('/voidtrade ref1')
        with closing(connect(self.context)) as connection:
            self.assertEqual(connection.execute('SELECT capital FROM performance_config').fetchone()[0], '1000')
            rows = connection.execute('SELECT pnl,voided FROM performance_trades').fetchall()
            self.assertEqual([(r['pnl'], r['voided']) for r in rows], [('10', 1)])
