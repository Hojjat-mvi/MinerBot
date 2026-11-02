"""Shared, admin-maintained closed-trade ledger and Telegram dashboard.

Amounts are net realized P&L, including fees, in a single configured currency.
No deposits, withdrawals, open positions or personal XT accounts are inferred.
"""
from contextlib import closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
import sqlite3

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from .content import TRADE_PERFORMANCE_TEXT
from .handlers import send_text


def connect(context):
    connection = context.bot_data['contacts']._connect()
    connection.row_factory = sqlite3.Row
    with connection:
        connection.execute('''CREATE TABLE IF NOT EXISTS performance_config (
            id INTEGER PRIMARY KEY CHECK(id=1), capital TEXT NOT NULL,
            currency TEXT NOT NULL, starts_at TEXT NOT NULL)''')
        connection.execute('''CREATE TABLE IF NOT EXISTS performance_trades (
            reference TEXT PRIMARY KEY, closed_at TEXT NOT NULL, pnl TEXT NOT NULL,
            symbol TEXT NOT NULL, created_by INTEGER NOT NULL, voided INTEGER NOT NULL DEFAULT 0)''')
    return connection


def number(raw):
    try:
        value = Decimal(raw)
        if not value.is_finite() or abs(value) > Decimal('1000000000000') or value.as_tuple().exponent < -8:
            raise ValueError
        return value
    except (InvalidOperation, ValueError):
        raise ValueError('مبلغ نامعتبر؛ حداکثر ۸ رقم اعشار.') from None


def timestamp(raw):
    try:
        result = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError
        return result.astimezone(timezone.utc)
    except ValueError:
        raise ValueError('تاریخ باید ISO 8601 همراه منطقهٔ زمانی باشد؛ مثال: 2026-11-02T12:00:00Z') from None


def metrics(trades, capital):
    equity = capital
    peak = capital
    max_drawdown = Decimal(0)
    profit = loss = Decimal(0)
    wins = losses = 0
    points = [Decimal(0)]
    valid_equity = capital > 0
    for trade in trades:
        pnl = Decimal(trade['pnl'])
        profit += max(pnl, Decimal(0))
        loss += max(-pnl, Decimal(0))
        wins += pnl > 0
        losses += pnl < 0
        equity += pnl
        points.append(equity - capital)
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - equity) / peak * 100)
        if equity <= 0:
            valid_equity = False
    count = len(trades)
    return dict(count=count, wins=wins, losses=losses, breakeven=count-wins-losses,
                profit=profit, loss=loss, net=profit-loss,
                win_rate=Decimal(wins) * 100 / count if count else None,
                factor=profit/loss if loss else None,
                roi=(profit-loss)/capital*100 if valid_equity else None,
                drawdown=max_drawdown if valid_equity else None, points=points)


def chart_png(points):
    """Small dependency-free PNG of cumulative realized P&L, by trade index."""
    import struct
    import zlib
    width, height = 800, 400
    pixels = bytearray([255]) * (width * height * 3)
    def dot(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 3
            pixels[offset:offset+3] = bytes(color)
    def line(x0, y0, x1, y1, color):
        steps = max(abs(x1-x0), abs(y1-y0), 1)
        for step in range(steps+1):
            x = round(x0 + (x1-x0)*step/steps)
            y = round(y0 + (y1-y0)*step/steps)
            dot(x, y, color)
            dot(x, y+1, color)
    low, high = min(points), max(points)
    span = high-low or Decimal(1)
    def y(value):
        return 360-round(float((value-low)/span)*320)
    line(40, y(Decimal(0)), 760, y(Decimal(0)), (170, 170, 170))
    previous = None
    for index, value in enumerate(points):
        point = (40+round(index*720/max(len(points)-1, 1)), y(value))
        if previous:
            line(*previous, *point, (20, 120, 200))
        previous = point
    raw = b''.join(b'\x00'+pixels[row*width*3:(row+1)*width*3] for row in range(height))
    def chunk(kind, data):
        return struct.pack('!I', len(data))+kind+data+struct.pack('!I', zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0))+chunk(b'IDAT', zlib.compress(raw))+chunk(b'IEND', b'')


def keyboard(period):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data='perf:'+value) for label, value in
         [('۷ روز', '7'), ('۳۰ روز', '30'), ('۹۰ روز', '90'), ('همه', 'all')]],
        [InlineKeyboardButton('📈 نمودار', callback_data='perf:chart:'+period),
         InlineKeyboardButton('📋 گزارش قبلی', callback_data='perf:legacy')],
        [InlineKeyboardButton('🏠 منوی اصلی', callback_data='home')]])


async def show_dashboard(context, user_id, period='all', chart=False):
    if period not in {'7', '30', '90', 'all'}:
        return
    now = datetime.now(timezone.utc)
    with closing(connect(context)) as connection:
        config = connection.execute('SELECT * FROM performance_config WHERE id=1').fetchone()
        trades = connection.execute('SELECT * FROM performance_trades WHERE voided=0 ORDER BY closed_at, reference').fetchall()
    if not config:
        await send_text(context, user_id,
                        '📊 داشبورد عملکرد\n\nهنوز دفتر معاملات تنظیم نشده است. گزارش قبلی از دکمهٔ زیر قابل مشاهده است. '
                        'این بخش عملکرد عمومی معاملات مجموعه را نمایش می‌دهد، نه حساب شخصی شما.', keyboard(period))
        return
    # Whole-ledger opening equity is needed even for a filtered period.
    start = timestamp(config['starts_at']) if period == 'all' else max(timestamp(config['starts_at']), now-timedelta(days=int(period)))
    before = [t for t in trades if timestamp(t['closed_at']) < start]
    selected = [t for t in trades if start <= timestamp(t['closed_at']) <= now]
    capital = Decimal(config['capital'])+sum((Decimal(t['pnl']) for t in before), Decimal(0))
    result = metrics(selected, capital)
    def formatted(value, suffix=''):
        return f'{value:,.2f}{suffix}' if value is not None else 'قابل محاسبه نیست'
    text = (f"📊 داشبورد عملکرد | {config['currency']}\n\n"
            f"بازه (UTC): {start:%Y-%m-%d %H:%M} تا {now:%Y-%m-%d %H:%M}\n"
            f"📊 معاملات بسته‌شده: {result['count']}\n"
            f"🎯 سودده: {result['wins']} | ❌ زیان‌ده: {result['losses']} | بدون سود و زیان: {result['breakeven']}\n"
            f"🟢 وین‌ریت: {formatted(result['win_rate'], '%')}\n"
            f"💰 مجموع سود: {formatted(result['profit'])}\n📉 مجموع ضرر: {formatted(result['loss'])}\n"
            f"🚀 خالص: {formatted(result['net'])}\n📐 ضریب سود: {formatted(result['factor'])}\n"
            f"📈 بازده سرمایه: {formatted(result['roi'], '%')}\n"
            f"📉 بیشترین افت سرمایه در بازه: {formatted(result['drawdown'], '%')}\n\n"
            'منبع: معاملات ثبت‌شده توسط مدیریت؛ به‌روزرسانی با ثبت معامله. مبالغ باید پس از کسر کارمزد باشند. '
            'بازده بر سرمایهٔ ابتدای بازه محاسبه می‌شود؛ واریز و برداشت پشتیبانی نمی‌شود. '
            'افت سرمایه بر اساس معاملات بسته‌شده است، نه نوسان پوزیشن‌های باز. این گزارش حساب شخصی شما نیست.')
    await send_text(context, user_id, text, keyboard(period))
    if chart and selected:
        image = BytesIO(chart_png(result['points']))
        image.name = 'performance.png'
        await context.bot.send_photo(chat_id=user_id, photo=image,
                                     caption=f"نمودار سود و زیان تجمعی ({config['currency']})؛ محور افقی: ترتیب معاملات، از چپ به راست. "
                                             f"آغاز: 0؛ پایان: {result['net']:,.2f}؛ کمینه: {min(result['points']):,.2f}؛ بیشینه: {max(result['points']):,.2f}")


async def performance_callback(update, context):
    query = update.callback_query
    await query.answer()
    if not update.effective_chat or update.effective_chat.type != 'private':
        return
    from .member_services import cancel
    cancel(context)
    args = query.data.split(':')[1:]
    if args == ['legacy']:
        await send_text(context, query.from_user.id, TRADE_PERFORMANCE_TEXT+'\n\nگزارش ثابت قبلی؛ تاریخ و واحد مبالغ مشخص نشده است.', keyboard('all'))
    elif len(args) == 1:
        await show_dashboard(context, query.from_user.id, args[0])
    elif len(args) == 2 and args[0] == 'chart':
        await show_dashboard(context, query.from_user.id, args[1], chart=True)


async def performance_admin(update, context):
    if update.effective_user.id not in context.bot_data['settings'].trade_admin_ids:
        return
    args = (update.effective_message.text or '').split()
    help_text = ('📊 مدیریت عملکرد\n\n'
                 '/perfsetup CAPITAL CURRENCY START_ISO\n'
                 '/addtrade REF CLOSED_ISO NET_PNL SYMBOL\n'
                 '/voidtrade REF\n/perftrades\n\n'
                 'مثال تاریخ: 2026-11-02T12:00:00Z\n'
                 'سرمایه باید موجودی قبل از اولین معامله باشد. مرجع معامله یکتا است؛ برای اصلاح ابتدا ابطال کنید و با مرجع جدید ثبت کنید. '
                 'تنظیمات پس از ثبت اولین معامله قفل می‌شود. سود و زیان خالص پس از کارمزد وارد شود.')
    try:
        command = args[0].split('@')[0]
        with closing(connect(context)) as connection, connection:
            connection.execute('BEGIN IMMEDIATE')
            if command == '/perfsetup' and len(args) == 4:
                capital, starts = number(args[1]), timestamp(args[3])
                if capital <= 0 or not re.fullmatch('[A-Z]{2,10}', args[2]) or starts > datetime.now(timezone.utc):
                    raise ValueError('سرمایه، واحد یا تاریخ آغاز نامعتبر است.')
                if connection.execute('SELECT 1 FROM performance_trades LIMIT 1').fetchone():
                    raise ValueError('پس از ثبت معامله امکان تغییر سرمایه و واحد وجود ندارد.')
                connection.execute('INSERT OR REPLACE INTO performance_config VALUES(1,?,?,?)', (str(capital), args[2], starts.isoformat()))
            elif command == '/addtrade' and len(args) == 5:
                config = connection.execute('SELECT * FROM performance_config WHERE id=1').fetchone()
                if not config:
                    raise ValueError('ابتدا /perfsetup را تنظیم کنید.')
                closed, pnl = timestamp(args[2]), number(args[3])
                if not re.fullmatch('[A-Za-z0-9_.-]{1,64}', args[1]) or not re.fullmatch('[A-Za-z0-9/_-]{1,24}', args[4]):
                    raise ValueError('مرجع یا نماد نامعتبر است.')
                if not timestamp(config['starts_at']) <= closed <= datetime.now(timezone.utc):
                    raise ValueError('تاریخ معامله باید بین آغاز دفتر و اکنون باشد.')
                connection.execute('INSERT INTO performance_trades(reference,closed_at,pnl,symbol,created_by) VALUES(?,?,?,?,?)',
                                   (args[1], closed.isoformat(), str(pnl), args[4], update.effective_user.id))
            elif command == '/voidtrade' and len(args) == 2:
                if connection.execute('UPDATE performance_trades SET voided=1 WHERE reference=? AND voided=0', (args[1],)).rowcount != 1:
                    raise ValueError('معاملهٔ فعال پیدا نشد.')
            elif command == '/perftrades' and len(args) == 1:
                rows = connection.execute('SELECT * FROM performance_trades ORDER BY closed_at DESC,reference DESC LIMIT 15').fetchall()
                await send_text(context, update.effective_user.id, '📋 آخرین ۱۵ معامله\n\n'+('\n'.join(
                    f"{t['reference']} | {t['closed_at']} | {t['symbol']} | {t['pnl']} | {'باطل' if t['voided'] else 'فعال'}" for t in rows) or 'بدون معامله'), None)
                return
            else:
                await send_text(context, update.effective_user.id, help_text, None)
                return
    except sqlite3.IntegrityError:
        await send_text(context, update.effective_user.id, 'مرجع معامله تکراری است؛ ثبت دوباره انجام نشد.', None)
        return
    except ValueError as error:
        await send_text(context, update.effective_user.id, str(error), None)
        return
    await send_text(context, update.effective_user.id, '✅ تغییرات دفتر عملکرد ذخیره شد.', None)
