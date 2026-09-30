"""Every trade's dollars are fixed at its own moment and never re-priced (owner's PAID trade drifted $1.15 → $1.21).
RPC, Mongo and price APIs are faked; nothing leaves the process."""
import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('JUPITER_API_KEY', 'test'); os.environ.setdefault('SOLANA_RPC_URL', 'http://rpc.test')
pytest.importorskip('solders')
import trading  # noqa: E402
from test_trade_confirmations import FakeHttp  # noqa: E402

SOL = trading.SOL_MINT
PAID = 'Paid111111111111111111111111111111111111111'
W = 'Wa11et1111111111111111111111111111111111111'
ATA = 'Ata11111111111111111111111111111111111111111'


def _match(doc, flt):
    for k, v in flt.items():
        if isinstance(v, dict) and '$in' in v:
            if doc.get(k) not in v['$in']:
                return False
        elif doc.get(k) != v:
            return False
    return True


class Coll:
    def __init__(self, rows=()):
        self.rows = [dict(r) for r in rows]

    def find(self, flt, proj=None):
        hits = [dict(r) for r in self.rows if _match(r, flt)]

        class Cur:
            def sort(self, *a): return self
            def limit(self, n): return self
            async def to_list(self, n): return hits[:n]
        return Cur()

    async def update_one(self, flt, upd, upsert=False):
        for r in self.rows:
            if _match(r, flt):
                r.update(upd['$set']); return
        if upsert:
            self.rows.append({**flt, **upd['$set']})


def buy_tx(sig, sol_spent, tokens_atoms, t=1_759_250_000):
    return {'blockTime': t, 'transaction': {'signatures': [sig], 'message': {'accountKeys': [{'pubkey': W}, {'pubkey': ATA}]}},
            'meta': {'err': None, 'fee': 5000, 'preBalances': [10**9, 0], 'postBalances': [10**9 - int(sol_spent * 1e9) - 2_039_280, 2_039_280],
                     'preTokenBalances': [], 'postTokenBalances': [{'accountIndex': 1, 'mint': PAID, 'owner': W, 'uiTokenAmount': {'amount': str(tokens_atoms), 'decimals': 6}}]}}


def service(orders, txs, http):
    db = type('DB', (), {})(); db.swap_orders = Coll(orders); db.wallet_fills = Coll()
    svc = trading.TradingService(db); svc._http = http
    calls = []

    async def rpc(method, params):
        calls.append((method, params[0]))
        if method == 'getTokenAccountsByOwner':
            return {'value': [{'pubkey': ATA, 'account': {'data': {'parsed': {'info': {'tokenAmount': {'amount': '103945500', 'decimals': 6}}}}}}]}
        if method == 'getSignaturesForAddress':
            return [{'signature': s} for s in txs]
        if method == 'getTransaction':
            return txs.get(params[0])
    svc.rpc = rpc
    return svc, calls


def test_old_feeless_order_is_priced_from_its_signed_quote_and_never_drifts():
    # The PAID order predates in_atoms: only the quote the wallet signed says what SOL was worth ($150).
    old_order = {'order_id': 'o1', 'wallet': W, 'signature': 'paid', 'state': 'confirmed', 'input_mint': SOL, 'output_mint': PAID,
                 'in_usd': 1.1505, 'quote': {'inAmount': '7670000', 'outAmount': '103945500', 'swapUsdValue': '1.1505'}}
    svc, calls = service([old_order], {'paid': buy_tx('paid', 0.00767 + 0.000005, 103945500)}, FakeHttp(pyth=161, now=161))
    a = asyncio.run(svc.chain_fills(W, PAID, 161.0))['fills'][0]
    assert a['priced'] == 'signing' and a['locked'] is True and abs(a['solUsd'] - 150) < 0.01
    assert abs(a['usd'] - 0.007675 * 150) < 0.001                                  # $1.15, not today's $1.24
    svc._fills_cache.clear(); svc._http = FakeHttp(pyth=175, now=175)              # a day later, SOL is up 17%
    b = asyncio.run(svc.chain_fills(W, PAID, 175.0))['fills'][0]
    assert b['usd'] == a['usd'] and b['fillPrice'] == a['fillPrice'] and b['price'] == a['price']
    assert [c for c in calls if c[0] == 'getTransaction'] == [('getTransaction', 'paid')]   # read once, stored, never re-fetched


def test_outside_trade_is_priced_at_its_block_time_and_waits_if_history_is_down():
    tx = {'ext': buy_tx('ext', 0.01, 50_000_000)}
    svc, _ = service([], tx, FakeHttp(now=170))          # history sources unreachable
    f = asyncio.run(svc.chain_fills(W, PAID, 170.0))['fills'][0]
    assert f['priced'] == 'now' and f['locked'] is False   # shown with today's price but flagged, not locked
    svc._fills_cache.clear(); svc._http = FakeHttp(coinbase=140.0, now=180)   # Pyth down, Coinbase up
    g = asyncio.run(svc.chain_fills(W, PAID, 180.0))['fills'][0]
    assert g['priced'] == 'block' and g['locked'] is True and abs(g['solUsd'] - 140.0) < 1e-9
    svc._fills_cache.clear(); svc._http = FakeHttp(now=999)
    h = asyncio.run(svc.chain_fills(W, PAID, 999.0))['fills'][0]
    assert h['usd'] == g['usd']                           # locked at its block time from then on


def test_a_locked_price_survives_a_parser_upgrade():
    svc, calls = service([], {'x': buy_tx('x', 0.01, 50_000_000)}, FakeHttp(pyth=150))
    asyncio.run(svc.chain_fills(W, PAID, 0.0))
    for r in svc.db.wallet_fills.rows:
        r['v'] = trading.FILL_VERSION - 1                  # stored by an older parser
    svc._fills_cache.clear(); svc._http = FakeHttp(pyth=999)
    f = asyncio.run(svc.chain_fills(W, PAID, 0.0))['fills'][0]
    assert abs(f['solUsd'] - 150) < 1e-9 and sum(1 for c in calls if c[0] == 'getTransaction') == 2   # re-read, price kept


def test_history_falls_back_to_coingecko_and_caches_per_minute():
    svc = trading.TradingService(None); http = FakeHttp(gecko=145.5); svc._http = http
    assert asyncio.run(svc.sol_usd_at(1_759_249_990)) == 145.5
    n = len(http.urls)
    assert asyncio.run(svc.sol_usd_at(1_759_250_030)) == 145.5 and len(http.urls) == n   # same minute: cached


def test_a_second_caller_never_starts_a_duplicate_scan():
    svc, calls = service([], {'x': buy_tx('x', 0.01, 50_000_000)}, FakeHttp(pyth=150))

    async def race():
        lock = svc._scan_locks.setdefault((W, PAID), asyncio.Lock())
        async with lock:   # a scan is in flight
            return await svc.chain_fills(W, PAID, 150.0)
    out = asyncio.run(race())
    assert out['fills'] == [] and not [c for c in calls if c[0] == 'getTransaction']   # answered from the store, no fetch
