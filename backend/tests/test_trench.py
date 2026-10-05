"""🗑 Trench cycle: fresh breakouts with a real crowd, strict gate, 1–2 per card, never in a normal slot."""
import arena_prime as ap
import fuse_wallet as fw
import trench as tr

GOOD = {'mint': 'T1', 'pairAddress': 'PT1', 'symbol': 'TRN', 'price': 0.00003, 'liq': 12_000.0, 'ageH': 1.5, 'mcap': 28_000.0, 'txns1h': 900,
        'vol1h': 40_000.0, 'buyShare': 63.0, 'chg5m': 9.0, 'chg1h': 35.0, 'scanned': True, 'top10': 18.0, 'insiders': 3.0, 'bundled': 0,
        'dev': 2.0, 'devSold': False, 'top10Jump': 0.0, 'flaggedFunders': 0, 'mayhem': False, 'creatorFlagged': False, 'creatorRep': None, 'snipersOut': True}
SAFE = {'mintAuthority': None, 'freezeAuthority': None}


def test_trench_gate_is_strict_fails_closed_and_cites_every_reason():
    ok, fails = tr.gate(GOOD, 520, SAFE)
    assert ok and not fails
    for bad, why in (({'mcap': 14_000.0}, 'market cap'), ({'ageH': 30.0}, 'fresh'), ({'buyShare': 48.0}, 'buyers'), ({'chg5m': -2.0}, 'green'),
                     ({'top10': 31.0}, 'top-10'), ({'scanned': False}, 'top-10'), ({'bundled': 3}, 'bundled'), ({'devSold': True}, 'dev'),
                     ({'creatorRep': 'suspect'}, 'creator'), ({'creatorFlagged': True}, 'creator'), ({'ageH': None}, 'fresh')):
        ok, fails = tr.gate({**GOOD, **bad}, 520, SAFE)
        assert not ok and any(why in f for f in fails), (bad, fails)
    assert not tr.gate(GOOD, 310, SAFE)[0]                                              # under 400 holders
    assert not tr.gate(GOOD, None, SAFE)[0]                                             # holder count unknown = out
    assert not tr.gate(GOOD, 520, {'mintAuthority': 'X', 'freezeAuthority': None})[0]   # someone can still print
    assert not tr.gate(GOOD, 520, None)[0]                                              # authority unknown = out
    sc, parts = tr.score(GOOD, 520)
    assert 0 < sc <= 100 and {p['part'] for p in parts} >= {'crowd', 'flow', 'momentum', 'spread'}


def _cands():
    C = lambda m, px, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m.upper(), 'price': px, 'liquidityUsd': 2e6, 'volume24h': 2e6, 'liq': 2e6, **k}
    anchors = [C('sol', 100.0), C('btc', 100.0)]
    pools = [C('pool1', 1.0), C('pool2', 1.0)]
    runners = [C('run1', 1.0, score=90, ageH=20), C('run2', 1.0, score=88, ageH=20), C('run3', 1.0, score=80, ageH=20)]
    trench = [C(f'tr{i}', 0.00003, score=70, ageH=1, trenchOnly=True, liq=12_000) for i in range(3)]
    return anchors, pools, runners + trench


def test_trench_cycle_deals_one_or_two_trench_coins_and_other_shapes_never_take_one():
    anchors, pools, runners = _cands()
    one = ap.deal('degen', pools, runners, ap.clean_cfg({'trenchCoins': 1}), 0.0, anchors, shape='trench')
    two = ap.deal('degen', pools, runners, ap.clean_cfg({'trenchCoins': 2}), 0.0, anchors, shape='trench')
    t1 = [l for l in one['legs'] if l.get('trench')]; t2 = [l for l in two['legs'] if l.get('trench')]
    assert len(t1) == 1 and len(t2) == 2 and len(one['legs']) == len(two['legs']) == 4   # 1 major + 1 pool + 2 runner slots
    assert ap.clean_cfg({'trenchCoins': 5})['trenchCoins'] == 1                       # never more than 2 (high risk)
    for shape in ('degen', 'mixed', 'breakeven', None):
        c = ap.deal('degen', pools, runners, ap.clean_cfg({'coins': 6}), 0.0, anchors, shape=shape)
        assert c and not any(l.get('trench') for l in c['legs']), shape                   # trench coins only ever fill a trench slot
    assert ap.next_phase('trench', 3, 0.0) == 'trench' and ap.valid_cycle('trench')


def test_a_trench_leg_is_replaced_by_a_trench_coin_and_a_normal_leg_never_is():
    anchors, pools, runners = _cands()
    cfg = ap.clean_cfg({'trenchCoins': 1, 'instantSwapPct': 15, 'cycles': {t: 'off' for t in ap.DEFAULT_CYCLES}, 'rescuePct': 0, 'cycleEvery': 0})
    card = ap.deal('degen', pools, runners, cfg, 0.0, anchors, shape='trench')
    t_leg = next(l for l in card['legs'] if l.get('trench')); r_leg = next(l for l in card['legs'] if l['role'] == 'runner' and not l.get('trench'))
    px = {l['pairAddress']: l['entry'] for l in card['legs']}
    px[t_leg['pairAddress']] *= 0.8; px[r_leg['pairAddress']] *= 0.8                    # both drop 20% → instant swap
    for x in runners:
        px.setdefault(x['pairAddress'], x['price'])
    out = ap.tick(card, px, pools, runners, cfg, 60.0, anchors, {}, {})
    trench_now = [l for l in out['legs'] if l.get('trench')]
    assert len(trench_now) == 1 and trench_now[0]['mint'] != t_leg['mint']              # trench slot → another trench coin
    assert sum(1 for l in out['legs'] if l['role'] == 'runner' and not l.get('trench')) == 1   # normal slot → a normal runner


def test_real_money_trench_buys_have_their_own_floor_and_every_other_check():
    cfg = fw.clean_cfg({'minLiqUsd': 20_000, 'trenchMinLiqUsd': 8_000})
    assert fw.liq_floor(cfg) == 20_000 and fw.liq_floor(cfg, trench=True) == 8_000
    assert fw.clean_cfg({'trenchMinLiqUsd': 100})['trenchMinLiqUsd'] == 3_000             # never under $3K
    book = {'legs': {}, 'sol': 1.0}
    card = {'legs': [{'mint': 'T1', 'pairAddress': 'PT1', 'symbol': 'TRN', 'units': 1000.0, 'trench': True, 'role': 'runner'}]}
    orders = fw.orders('degen', card, book, {'PT1': 0.01}, 100.0, {**cfg, 'maxSwapUsd': 50, 'minOrderUsd': 0.1}, 0.0)
    buy = next(o for o in orders if o['side'] == 'buy')
    assert buy.get('trench') is True
    ok, why = fw.check({**buy, 'liq': 9_000}, {**cfg, 'armed': True, 'paused': False, 'walletId': 'w', 'address': 'a', 'maxSwapUsd': 50, 'dailyUsd': 300}, [], 0.0, 0.1)
    assert ok, why
    ok, why = fw.check({**buy, 'liq': 6_000}, {**cfg, 'armed': True, 'paused': False, 'walletId': 'w', 'address': 'a', 'maxSwapUsd': 50, 'dailyUsd': 300}, [], 0.0, 0.1)
    assert not ok and 'too thin' in why


def test_trench_rows_carry_their_reasons():
    import pytest
    rs = pytest.importorskip('reputation_service')
    good = rs._trench_row(GOOD, 520, SAFE); bad = rs._trench_row({**GOOD, 'top10': 40.0}, 520, SAFE)
    assert good['ok'] and good['trenchOnly'] and good['score'] >= 60 and good['division'] == 'trench'
    assert not bad['ok'] and any('top-10' in f for f in bad['fails'])


def test_trench_endpoint_lists_finalists_and_the_rules():
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    rs._trench_cache.update(checked=[rs._trench_row(GOOD, 520, SAFE), rs._trench_row({**GOOD, 'mint': 'X', 'top10': 40.0}, 520, SAFE)], rows=[rs._trench_row(GOOD, 520, SAFE)])
    out = asyncio.run(rs.fuse_trench())
    assert out['pass'] == 1 and len(out['checked']) == 2 and '400 holders' in out['rules'] and 'revoked' in out['rules']
    # 🗑 pickable rows (only passing coins) + the trench pool floor, for the swap picker's Trench list
    assert [r['mint'] for r in out['rows']] == [GOOD['mint']] and out['rows'][0]['trench'] and out['floor'] == 8000
    rs._trench_cache.update(checked=[], rows=[])
