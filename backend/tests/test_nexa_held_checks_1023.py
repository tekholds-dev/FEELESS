"""⏱ While FeeCat holds a coin NEXA re-checks it every 2 min (owner, 2026-10-23: "quick questions to her faster — hold · skim · new SL · new TP")."""
import asyncio
import time

import pytest

import cat_model as cm
import nexa_desk as nd

NOW = 1_800_000_000.0


def test_a_live_trade_gets_a_held_only_round_every_two_minutes():
    assert nd.round_kind({}, NOW, False) == 'full' and nd.round_kind({'deskAt': NOW - 400}, NOW, True) == 'full'
    assert nd.round_kind({'deskAt': NOW - 130}, NOW, True) == 'held' and nd.round_kind({'deskAt': NOW - 130}, NOW, False) is None
    assert nd.round_kind({'deskAt': NOW - 200, 'heldAt': NOW - 60}, NOW, True) is None          # checked a minute ago
    held = [{'pair': 'PH', 'symbol': 'HHH', 'pct': 4}]
    jobs = nd.pick(held, [{'pair': 'PA', 'symbol': 'AAA'}], [], NOW, held_only=True)
    assert [(j['kind'], j['pair']) for j in jobs] == [('hold', 'PH')]                            # no buy questions in the fast check
    assert nd.HELD_EVERY <= 120 < nd.EVERY


def test_her_held_words_skim_and_lines():
    assert nd.parse('SKIM — spike into thin pool', 'hold') == ('SKIM', 'spike into thin pool')
    assert nd.parse('SL 15 buyers thinning', 'hold') == ('HOLD', 'SL 15 buyers thinning')       # a line move alone = keep it, new stop
    assert nd.parse('SL 15', 'buy') == (None, '')
    assert nd.lines_of('HOLD, TP 60 and SL -12%') == {'sl': 12.0, 'tp': 60.0}
    assert nd.lines_of('SL 90 TP 2') == {'sl': 40.0, 'tp': 10.0} and nd.lines_of('HOLD') == {}   # clamped
    calls = nd.note([], {'pair': 'PH', 'kind': 'hold', 'line': 'x'}, 'HOLD', 'law', 900, NOW - 60, lines={'sl': 15.0})
    calls = nd.note(calls, {'pair': 'PH', 'kind': 'hold', 'line': 'x'}, 'HOLD', 'law', 900, NOW - 30, lines={'tp': 60.0})
    calls = nd.note(calls, {'pair': 'PS', 'kind': 'hold', 'line': 'x'}, 'SKIM', 'spike', 900, NOW - 10)
    calls = nd.note(calls, {'pair': 'PB', 'kind': 'buy', 'line': 'x'}, 'YES', '', 900, NOW - 5, lines={'sl': 9.0})   # a buy call never carries lines
    m = nd.merge(calls, NOW)
    assert m['skim'] == {'PS': NOW - 10} and m['lines'] == {'PH': {'sl': 15.0, 'tp': 60.0}}


def test_feecat_skims_once_per_call_and_sells_on_her_lines():
    read = cm.read_of({'at': NOW - 30, 'skim': {'PS': NOW - 30}, 'lines': {'PH': {'sl': 15, 'tp': 60}}}, NOW)
    pos = {'pairAddress': 'PS'}
    assert cm.skim_now(read, pos) == '🪟 NEXA said skim: banked half'
    pos['nxSkimAt'] = NOW - 30
    assert cm.skim_now(read, pos) is None                                                        # that call was already skimmed
    assert cm.line_exit(read, {'pairAddress': 'PH'}, -16.0).startswith("🪟 NEXA's stop −15%")
    assert cm.line_exit(read, {'pairAddress': 'PH'}, 61.0).startswith("🪟 NEXA's take +60%")
    assert cm.line_exit(read, {'pairAddress': 'PH'}, 5.0) is None and cm.line_exit(None, {'pairAddress': 'PH'}, -50) is None


def _pair(pa, sym):
    return {'pairAddress': pa, 'baseToken': {'symbol': sym, 'address': 'M' + pa}, 'priceNative': '1.0', 'priceUsd': '150', 'liquidity': {'usd': 90_000},
            'marketCap': 400_000, 'fdv': 400_000, 'volume': {'h1': 60_000, 'h24': 900_000}, 'txns': {'h1': {'buys': 300, 'sells': 120}, 'm5': {'buys': 30, 'sells': 10}},
            'priceChange': {'m5': 3, 'h1': 25, 'h6': 60, 'h24': 120}, 'pairCreatedAt': (time.time() - 6 * 3600) * 1000, 'dexId': 'raydium'}


def test_feecat_engine_banks_half_on_her_skim_and_sells_on_her_stop(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    now = time.time()
    nexa = {'favor': [], 'exit': [], 'avoid': [], 'why': '', 'at': now - 30, 'skim': {'PS': now - 30}, 'lines': {'PL': {'sl': 10}}}
    base = {'costSol': 0.5, 'notionalSol': 0.495, 'entryPriceNative': 1.0, 'openedAt': now - 3600, 'peakChange': 0, 'firstEntryPriceNative': 1.0,
            'entryLiq': 80_000, 'solUsdAtEntry': 150}

    async def a_(v):
        return v
    monkeypatch.setattr(fs, '_pair_prices', lambda http, pas: a_({'PS': {'priceNative': 1.30, 'priceUsd': 195}, 'PL': {'priceNative': 0.88, 'priceUsd': 132}}))
    for k_, v_ in (('_market_candidates', []), ('_fuse_discover', {}), ('_crowd_feed', {}), ('_duo_read', {'nexa': nexa})):
        monkeypatch.setattr(fs, k_, (lambda v: (lambda http: a_(v)))(v_))
    monkeypatch.setattr(fs, '_creator_check', lambda ranked, rej: a_(ranked))
    monkeypatch.setattr(fs, '_post_as_fee', lambda *a, **k: None)
    monkeypatch.setattr(fs, '_duo_learn', lambda *a, **k: None)
    monkeypatch.setattr(fs, '_thesis', lambda pos, live, R: (None, False, None))
    cat = {'id': 'c1', 'ownerId': 'o', 'name': 'Nexie', 'status': 'running', 'balanceSol': 10.0, 'startingBalanceSol': 10.0,
           'positions': [{**base, 'pairAddress': 'PS', 'symbol': 'SSS', 'mint': 'MS'}, {**base, 'pairAddress': 'PL', 'symbol': 'LLL', 'mint': 'ML'}],
           'exits': [], 'risk': {'maxPositionSol': 0.25, 'maxDailyLossSol': 5}, 'realizedPnlSol': 0, 'wins': 0, 'losses': 0, 'pnlHistory': [{'value': 0}]}
    fs._set_model_brain(cat, 'nexa')
    store = {'cats': {'c1': cat}, 'events': []}
    asyncio.run(fs.run_engine(store, [cat]))
    by = {p['symbol']: p for p in cat['positions']}
    assert 'LLL' not in by                                                       # −12% under her −10% stop → sold
    assert by['SSS']['notionalSol'] == pytest.approx(0.2475) and by['SSS']['nxSkimAt'] == now - 30   # half banked, once
    asyncio.run(fs.run_engine(store, [cat]))
    assert cat['positions'][0]['notionalSol'] == pytest.approx(0.2475)            # the same SKIM call never skims twice


def test_cats_ai_publishes_her_skim_and_lines():
    rs = pytest.importorskip('reputation_service')
    now = time.time()
    desk = [{'pair': 'PS', 'word': 'SKIM', 'at': now - 20, 'kind': 'hold'}, {'pair': 'PL', 'word': 'HOLD', 'at': now - 10, 'kind': 'hold', 'lines': {'sl': 12.0}}]
    rs._nexa_mem.put({'cfg': {'trade': True}, 'desk': desk}, now)
    nx = asyncio.run(rs.cats_ai())['nexa']
    assert nx['skim'] == {'PS': now - 20} and nx['lines'] == {'PL': {'sl': 12.0}}
    r = cm.read_of(nx, now)
    assert r['skim'] == {'PS': now - 20} and r['lines'] == {'PL': {'sl': 12.0}}


def test_her_desk_words_become_public_chart_bubbles_scrubbed():
    jobs = nd.pick([{'pair': 'PH', 'symbol': 'HHH', 'mcap': 41_000}], [{'pair': 'PA', 'symbol': 'AAA', 'mcap': 28_000}], [], NOW)
    assert [j['mc'] for j in jobs] == [41_000, 28_000]                                           # every question knows the coin's cap
    calls = nd.note([], jobs[1], 'YES', 'graduated, buyers lead', 900, NOW - 60)
    calls = nd.note(calls, jobs[0], None, 'no clear word', 900, NOW - 50)                         # silence is no bubble
    calls = nd.note(calls, {'pair': 'PX', 'kind': 'buy', 'line': 'x'}, 'NO', '', 900, NOW - 40)   # no cap → no bubble
    calls = nd.note(calls, jobs[0], 'SKIM', 'spike', 900, NOW - nd.TALK_SEC - 5)                  # older than 3 h
    assert nd.talk(calls, NOW) == [{'pair': 'PA', 'word': 'YES', 'why': 'graduated, buyers lead', 'at': round(NOW - 60), 'mc': 28000}]
    old = [{'pair': 'PB', 'word': 'HOLD', 'why': 'x', 'at': NOW - 30, 'line': '$BBB · you +4.0% (peak +9.0%) held 12m · MC 1.2M · 5m +2.0%'}]
    assert nd.talk(old, NOW)[0]['mc'] == 1_200_000 and nd.line_mc('$X · age 3m') == 0.0                # a call from before 'mc' reads its own line


def test_the_public_leader_carries_her_talk_with_every_name_scrubbed(monkeypatch):
    fs = pytest.importorskip('feecat_service')
    store = {'cats': {'leader': {'id': 'leader', 'name': 'FeeCat', 'positions': []}}, 'events': [],
             'aiTalk': [{'pair': 'PA', 'word': 'YES', 'why': '🪟 NEXA likes it, OSSY agrees: under 15 words', 'at': 1, 'mc': 28000}]}
    monkeypatch.setattr(fs, '_load', lambda: store)
    monkeypatch.setattr(fs, '_migrate', lambda s: None)
    out = asyncio.run(fs.leader())
    assert out['talk'][0]['why'] == '🔮 FeeCat AI likes it, 🔮 FeeCat AI agrees' and out['talk'][0]['mc'] == 28000
    import nexa
    assert nexa.real_why('under 15 words') == '' and nexa.real_why('buyers lead, pool deep') == 'buyers lead, pool deep'
