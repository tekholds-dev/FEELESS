"""🪟 A cat assigned to NEXA trades PAPER on her fresh desk read: buys only her favored coins (after every guard), sells her exits."""
import asyncio
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cat_model as cm  # noqa: E402

NOW = 1_000_000.0


def test_her_read_is_acted_on_only_while_fresh():
    nx = {'favor': ['A'], 'exit': ['B'], 'avoid': ['C'], 'why': 'A has buyers', 'at': NOW - 600}
    r = cm.read_of(nx, NOW)
    assert r['favor'] == {'A'} and r['age'] == 600
    assert cm.read_of({**nx, 'at': NOW - cm.FRESH_SEC - 1}, NOW) is None and cm.read_of(None, NOW) is None
    assert cm.buy_ok(r, 'A')[0] and not cm.buy_ok(r, 'C')[0] and not cm.buy_ok(r, 'Z')[0] and not cm.buy_ok(None, 'A')[0]
    assert cm.sell_now(r, 'B').startswith('🪟 NEXA said exit') and cm.sell_now(r, 'A') is None and cm.sell_now(None, 'B') is None
    assert cm.status(nx, NOW)['state'] == 'live' and cm.status({**nx, 'at': 1}, NOW)['state'] == 'waiting'
    assert cm.model_of({'modelBrain': 'nexa'})['name'] == 'NEXA' and cm.model_of({}) is None


def _pair(pa, sym, px=1.0):
    return {'pairAddress': pa, 'chainId': 'solana', 'baseToken': {'address': 'M' + pa, 'symbol': sym}, 'priceNative': px, 'priceUsd': px * 150,
            'liquidity': {'usd': 80_000}, 'marketCap': 500_000, 'volume': {'h1': 50_000}, 'txns': {'h1': {'buys': 300, 'sells': 100}}}


def test_nexa_cat_buys_her_pick_through_the_guards_and_sells_her_exit(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    now = time.time()
    nexa = {'favor': ['PB'], 'exit': ['PH'], 'avoid': ['PA'], 'why': 'B has real buyers', 'at': now - 300}
    pairs = [_pair('PA', 'AAA'), _pair('PB', 'BBB'), _pair('PC', 'CCC')]
    held = {'pairAddress': 'PH', 'symbol': 'HHH', 'mint': 'MPH', 'costSol': 0.5, 'notionalSol': 0.495, 'entryPriceNative': 1.0, 'openedAt': now - 3600,
            'peakChange': 0, 'firstEntryPriceNative': 1.0, 'entryLiq': 80_000, 'solUsdAtEntry': 150}

    async def a_(v):
        return v
    monkeypatch.setattr(fs, '_pair_prices', lambda http, pas: a_({'PH': {'priceNative': 1.02, 'priceUsd': 153}}))
    monkeypatch.setattr(fs, '_market_candidates', lambda http: a_(pairs))
    monkeypatch.setattr(fs, '_fuse_discover', lambda http: a_({}))
    monkeypatch.setattr(fs, '_crowd_feed', lambda http: a_({}))
    monkeypatch.setattr(fs, '_duo_read', lambda http: a_({'nexa': nexa}))
    monkeypatch.setattr(fs, '_creator_check', lambda ranked, rej: a_(ranked))
    monkeypatch.setattr(fs, '_safety', lambda http, p: a_((True, 'holders spread', 1.0)))
    monkeypatch.setattr(fs, '_fvg', lambda http, pa, px: a_(None))
    monkeypatch.setattr(fs, '_qualifies', lambda p, n: (1.0, 'momentum'))
    monkeypatch.setattr(fs, 'setup_gate', lambda p: (True, '', 1.0, []))
    monkeypatch.setattr(fs, '_post_as_fee', lambda *a, **k: None)
    monkeypatch.setattr(fs, '_duo_learn', lambda *a, **k: None)
    store = {'cats': {}, 'events': []}
    cat = {'id': 'c1', 'ownerId': 'o', 'name': 'Nexie', 'status': 'running', 'balanceSol': 10.0, 'startingBalanceSol': 10.0, 'positions': [dict(held)],
           'exits': [], 'risk': {'maxPositionSol': 0.25, 'maxDailyLossSol': 0.5}, 'realizedPnlSol': 0, 'wins': 0, 'losses': 0, 'pnlHistory': [{'value': 0}]}
    fs._set_model_brain(cat, 'nexa')
    store['cats']['c1'] = cat
    asyncio.run(fs.run_engine(store, [cat]))
    syms = {p['symbol'] for p in cat['positions']}
    assert 'HHH' not in syms                                 # her EXIT sold it (paper, live price)
    assert syms == {'BBB'}                                   # only her favored coin — not the avoided AAA, not the unpicked CCC
    assert cat['positions'][0]['reason'].startswith('🪟 NEXA favored it')
    fs._set_model_brain(cat, 'rules')
    assert 'modelBrain' not in cat
