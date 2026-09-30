"""Server-side confirmations + position backfill: a trade lands in positions/P&L even if the trader closed the page.
The RPC and database are faked; nothing leaves the process."""
import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('JUPITER_API_KEY', 'test'); os.environ.setdefault('SOLANA_RPC_URL', 'http://rpc.test')
pytest.importorskip('solders')
import trading  # noqa: E402

SOL = 'So11111111111111111111111111111111111111112'
USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
MEME = '49MmWE8sgNjuw342Eu7tB9thsVFtvTfKigUw9KSppump'


def order(i, state='confirmed', **kw):
    base = {'order_id': f'o{i}', 'wallet': 'W', 'state': state, 'signature': f'sig{i}', 'created_at': '2026-09-30T12:00:00+00:00',
            'input_mint': SOL, 'output_mint': MEME, 'in_atoms': '100000000', 'in_decimals': 9, 'out_decimals': 6,
            'quote': {'outAmount': '5000000000'}, 'in_usd': 12.0}
    return {**base, **kw}


def test_buy_and_sell_become_position_rows_with_entry_price():
    rows = trading.fills_from_orders([
        order(1),
        order(2, input_mint=MEME, output_mint=SOL, in_atoms='2500000000', in_decimals=6, out_decimals=9, quote={'outAmount': '60000000'}, in_usd=None),
    ], sol_usd=150)
    buy, sell = rows
    assert buy['side'] == 'buy' and buy['token'] == MEME and buy['usd'] == 12.0 and abs(buy['price'] - 12 / 5000) < 1e-12
    assert sell['side'] == 'sell' and sell['token'] == MEME and sell['usd'] == 9.0   # 0.06 SOL × $150 when the quote had no USD
    assert abs(sell['price'] - 9 / 2500) < 1e-12 and sell['tx'] == 'sig2'


def test_only_confirmed_cash_leg_trades_count():
    rows = trading.fills_from_orders([order(1, state='submitted'), order(2, state='failed'), order(3, signature=None),
                                      order(4, input_mint=MEME, output_mint='OtherCoin1111111111111111111111111111111111'),
                                      order(5, input_mint=USDC, in_decimals=6, in_atoms='20000000', in_usd=None)])
    assert [r['tx'] for r in rows] == ['sig5'] and rows[0]['usd'] == 20.0


class Orders:
    def __init__(self, rows):
        self.rows = {r['order_id']: r for r in rows}

    def find(self, q, proj=None):
        hits = [dict(r) for r in self.rows.values() if r['state'] == q['state'] and r.get('signature')]
        class Cur:
            def sort(self, *a): return self
            def limit(self, n): return self
            async def to_list(self, n): return hits[:n]
        return Cur()

    async def update_one(self, q, u):
        r = self.rows[q['order_id']]
        ok = r['state'] == q['state']
        if ok:
            r.update(u['$set'])
        return type('R', (), {'modified_count': int(ok)})()


def test_sweep_confirms_orders_nobody_is_polling_and_reports_each_once():
    db = type('DB', (), {})(); db.swap_orders = Orders([order(1, state='submitted'), order(2, state='submitted'), order(3, state='submitted')])
    svc = trading.TradingService(db)
    statuses = {'sig1': {'confirmationStatus': 'finalized', 'err': None}, 'sig2': {'confirmationStatus': 'processed', 'err': None}, 'sig3': {'err': {'x': 1}}}
    landed = []

    async def rpc(method, params):
        assert method == 'getSignatureStatuses'
        return {'value': [statuses.get(s) for s in params[0]]}

    async def trade_landed(o):
        landed.append(o['signature'])
    svc.rpc, svc.trade_landed = rpc, trade_landed
    assert asyncio.run(svc.confirm_sweep()) == 1
    assert landed == ['sig1']
    assert [db.swap_orders.rows[k]['state'] for k in ('o1', 'o2', 'o3')] == ['confirmed', 'submitted', 'failed']
    assert asyncio.run(svc.confirm_sweep()) == 0 and landed == ['sig1']   # never reported twice
