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


def test_nexa_desk_asks_held_coins_first_then_fresh_candidates_and_reads_one_word():
    import nexa_desk as nd
    held = [{'pair': 'PH', 'mint': 'MH', 'symbol': 'HHH', 'pct': 12.3, 'peak': 20, 'mins': 25, 'mcap': 150_000, 'd5': -3, 'buy': 41}]
    cands = [{'pair': 'PH', 'symbol': 'HHH'}, {'pair': 'PA', 'mint': 'MA', 'symbol': 'AAA', 'mcap': 120_000, 'ageMin': 45, 'd5': 4.2, 'c1': 30, 'buy': 62, 'liq': 40_000, 'top10': 22},
             {'pair': 'PB', 'symbol': 'BBB'}, {'pair': 'PC', 'symbol': 'CCC'}]
    jobs = nd.pick(held, cands, [{'pair': 'PB', 'at': NOW - 60}], NOW)
    assert [(j['kind'], j['pair']) for j in jobs] == [('hold', 'PH'), ('buy', 'PA'), ('buy', 'PC')]   # held first · never a held coin as a buy · PB asked 1 min ago
    assert jobs[0]['line'].startswith('$HHH · you +12.3% (peak +20.0%) held 25m · MC 150K')
    assert jobs[1]['line'] == '$AAA · MC 120K · age 45m · 5m +4.2% · 1h +30.0% · buyers 62% · pool 40K · top10 22%'
    assert nd.parse('YES — buyers lead, pool deep', 'buy') == ('YES', 'buyers lead, pool deep')
    assert nd.parse('<think>hmm</think> sell: momentum died', 'hold') == ('SELL', 'momentum died')
    assert nd.parse('maybe later', 'buy') == (None, '')
    calls = nd.note([], jobs[1], 'YES', 'clean', 900, NOW - 100)
    calls = nd.note(calls, jobs[0], 'SELL', 'dying', 900, NOW - 50)
    calls = nd.note(calls, {'pair': 'PZ', 'kind': 'buy', 'line': 'x'}, 'YES', '', 900, NOW - nd.FRESH - 5)   # stale
    m = nd.merge(calls, NOW)
    assert m['favor'] == ['PA'] and m['exit'] == ['PH'] and m['at'] == NOW - 50
    assert nd.due({'deskAt': NOW - 100}, NOW) is False and nd.due({}, NOW) is True


def test_only_the_owner_switch_hands_feecat_to_nexa(monkeypatch, tmp_path):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    store = {'cats': {'leader': {'id': 'leader', 'name': 'FeeCat', 'isLeader': True, 'positions': []}, 'u1': {'id': 'u1', 'name': 'Mine', 'positions': [], 'risk': {}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_log_event', lambda *a, **k: None)
    fs.DATA_DIR.mkdir(parents=True, exist_ok=True); (fs.DATA_DIR / 'internal.key').write_text('secret')
    c = TestClient(fs.app)
    assert c.post('/api/cats/internal/brain', json={'model': 'nexa'}).status_code == 403                # no internal key → refused
    assert c.post('/api/cats/u1/action', json={'action': 'brain', 'text': 'nexa'}).status_code == 400   # a user's cat can't take NEXA
    monkeypatch.setattr(fs, '_internal', lambda request: None)
    assert c.post('/api/cats/internal/brain', json={'model': 'nexa'}).json() == {'model': 'nexa'}
    assert store['cats']['leader']['modelBrain'] == 'nexa' and 'modelBrain' not in store['cats']['u1']
    assert c.post('/api/cats/internal/brain', json={'model': 'rules'}).json() == {'model': 'rules'}


def test_feecat_reads_nexas_desk_words_only_while_the_owner_switch_is_on():
    rs = pytest.importorskip('reputation_service')
    now = time.time()
    desk = [{'pair': 'PA', 'word': 'YES', 'at': now - 30}, {'pair': 'PH', 'word': 'SELL', 'at': now - 20}, {'pair': 'PN', 'word': 'NO', 'at': now - 10}]
    rs._nexa_mem.put({'cfg': {'trade': True}, 'desk': desk}, now)
    nx = asyncio.run(rs.cats_ai())['nexa']
    assert nx['favor'] == ['PA'] and nx['exit'] == ['PH'] and nx['trades'] is True and cm.read_of(nx, now)['favor'] == {'PA'}
    rs._nexa_mem.put({'cfg': {'trade': False}, 'desk': desk}, now)
    assert asyncio.run(rs.cats_ai())['nexa'] is None                     # switch off: her desk words never reach FeeCat


def test_a_user_runs_at_most_two_agents_and_a_retired_one_frees_its_slot(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    from fastapi.testclient import TestClient
    store = {'cats': {'a': {'id': 'a', 'ownerId': 'u', 'revoked': False}, 'b': {'id': 'b', 'ownerId': 'u', 'revoked': False}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    c = TestClient(fs.app)
    r = c.post('/api/cats', json={'ownerId': 'u', 'name': 'Third', 'handle': 'third'})
    assert r.status_code == 400 and 'retire one' in r.json()['detail']
    store['cats']['b']['revoked'] = True
    assert c.post('/api/cats', json={'ownerId': 'u', 'name': 'Third', 'handle': 'third'}).status_code == 200
