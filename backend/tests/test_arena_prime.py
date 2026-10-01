"""Arena Prime: 3 top-tier paper cards, fully auto — 3★+ coins only, a stable major anchor (never rotated / stopped), auto TP
compounds into the other coins, SL replaced at once, 2 weakest rotate every 6h, a −20% card FLOOR (never −25%), an honest
day record (good day = +10%), fees tracked apart (never in P&L), every action logged with its reason."""
import arena_prime as ap

C = lambda m, px, sym=None, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': sym or m.upper(), 'price': px, **k}
P = lambda m, px: C(m, px, liquidityUsd=2e6, volume24h=2e6)             # 5★ pool
R = lambda m, px, sc=90: C(m, px, score=sc)                                 # 5★ runner by default
SOL = [C('sol', 1, 'SOL'), C('jito', 1, 'JitoSOL')]
CFG = ap.clean_cfg({})


def test_stars_and_only_3_star_coins_get_in():
    assert ap.stars({}, 'anchor') == 5 and ap.stars({'liquidityUsd': 2e6, 'volume24h': 2e6}, 'pool') == 5 and ap.stars({'liquidityUsd': 2e5}, 'pool') == 3
    assert [ap.stars({'score': s}, 'runner') for s in (95, 80, 65, 40)] == [5, 4, 3, 2]
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1, 40), R('r2', 1, 80), R('r3', 1, 65)], CFG, 0, SOL)
    assert [l['mint'] for l in card['legs']] == ['sol', 'a', 'r2', 'r3'] and all(l['stars'] >= 3 for l in card['legs'])   # 2★ runner kept off


def test_tiers_hold_an_anchor_plus_pools_and_runners_equal_dollars():
    card = ap.deal('safe', [P('sol', 1), P('a', 2)], [R('r1', 0.1)], CFG, 0, SOL)            # SOL pool never doubles the SOL anchor
    assert [(l['mint'], l['role']) for l in card['legs']] == [('sol', 'anchor'), ('jito', 'anchor'), ('a', 'pool'), ('r1', 'runner')]
    assert all(abs(l['costUsd'] - 25) < 1e-9 for l in card['legs']) and ap.value(card, {}) == 100 and card['label'] == '💎 Prime Diamond'
    assert {t['tier'] for t in ap.TEMPLATES.values()} == {'diamond', 'gold', 'blaze'}
    assert all(3 <= t['anchors'] + t['pools'] + t['runners'] <= 5 for t in ap.TEMPLATES.values())


def test_auto_tp_compounds_into_the_others_and_pnl_excludes_fees():
    card = ap.deal('balanced', [P('a', 1), P('b', 1)], [R('r1', 1), R('r2', 1)], CFG, 0, SOL[:1])     # 5 coins × $20
    px = {'Psol': 1, 'Pa': 1.6, 'Pb': 1, 'Pr1': 1, 'Pr2': 1}                                         # a +60% ≥ +50% → take the gain
    out = ap.tick(card, px, [], [], CFG, 60, SOL)
    a = next(l for l in out['legs'] if l['mint'] == 'a')
    assert abs(a['units'] * 1.6 - 20) < 1e-6 and abs(out['compoundedUsd'] - 12) < 1e-6
    tp = [e for e in out['events'] if e['kind'] == 'tp'][-1]
    assert tp['to'] == ['SOL', 'B', 'R1', 'R2'] and ap.value(out, px) == 112 and ap.summary(out, px)['pnlPct'] == 12 and out['feesUsd'] > card['feesUsd']


def test_stop_loss_replaced_anchor_never_stopped_or_rotated():
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1), R('r2', 1), R('r3', 1)], CFG, 0, SOL)
    px = {'Psol': 0.5, 'Pa': 1, 'Pr1': 0.5, 'Pr2': 1.1, 'Pr3': 0.9}                # r1 −50% ≤ −40% → out; SOL −50% stays (anchor)
    out = ap.tick(card, px, [], [R('r9', 1)], CFG, 60, SOL)
    mints = [l['mint'] for l in out['legs']]
    assert 'r9' in mints and 'r1' not in mints and 'sol' in mints
    out2 = ap.tick(out, {**px, 'Pr9': 1}, [P('x', 2)], [R('r8', 1), R('r7', 1)], CFG, 6 * 3600 + 61, SOL)
    rot = [e for e in out2['events'] if e['kind'] == 'rotate']
    assert len(rot) == 2 and 'SOL' not in [e['symbol'] for e in rot]


def test_floor_never_lets_a_card_sit_below_minus_25():
    card = ap.deal('balanced', [P('a', 1), P('b', 1)], [R('r1', 1), R('r2', 1)], CFG, 0, SOL[:1])
    px = {'Psol': 1, 'Pa': 0.75, 'Pb': 0.75, 'Pr1': 0.7, 'Pr2': 0.7}             # −22% ≤ −20% floor (a 5-min tick; only a gap could skip it)
    out = ap.tick(card, px, [], [], CFG, 60, SOL)
    assert out.get('flooredAt') == 60 and [l['role'] for l in out['legs']] == ['anchor'] and [e for e in out['events'] if e['kind'] == 'floor']
    s = ap.summary(out, px)
    assert s['floored'] and s['pnlPct'] > -25
    later = ap.tick(out, {'Psol': 1, 'Pc': 1, 'Pr3': 1}, [P('c', 1)], [R('r3', 1)], CFG, 60 + 86401, SOL)   # next day: re-dealt fresh
    assert not later.get('flooredAt') and len(later['legs']) > 1 and later['runs'][-1]['pct'] < 0 and ap.record(later)['runs'][-1]['startUsd'] == 100


def test_day_record_counts_good_days_honestly():
    card = ap.deal('safe', [P('a', 1)], [R('r1', 1)], CFG, 0, SOL)
    up = {'Psol': 1.12, 'Pjito': 1.12, 'Pa': 1.12, 'Pr1': 1.12}
    c1 = ap.tick(card, up, [], [], CFG, 86401, SOL)
    c2 = ap.tick(c1, {k: v * 1.01 for k, v in up.items()}, [], [], CFG, 2 * 86402, SOL)
    r = ap.record(c2)
    assert r['loggedDays'] == 2 and r['goodDays'] == 1


def test_cfg_ranges():
    c = ap.clean_cfg({'rotateHours': 0.2, 'rotateCount': 9, 'sizeUsd': 5, 'compound': False, 'floorPct': 60})
    assert c['rotateHours'] == 1 and c['rotateCount'] == 3 and c['sizeUsd'] == 10 and c['compound'] is False and c['floorPct'] == 25


def test_service_deals_ticks_and_admin_config(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    async def cands(): return ([P('a', 1), P('b', 1), P('c', 1)], [R('r1', 1), R('r2', 1), R('r3', 1)], SOL)
    async def prices(legs): return {l['pairAddress']: 1.0 for l in legs}
    monkeypatch.setattr(rs, '_prime_candidates', cands); monkeypatch.setattr(rs, '_hq_prices', prices); monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    rs._json_save(rs.FUSE_HQ_PATH, {})
    assert asyncio.run(rs._prime_tick(1000)) == 3
    v = asyncio.run(rs.fuse_prime())
    assert {c['tier'] for c in v['cards']} == {'diamond', 'gold', 'blaze'} and all(c['valueUsd'] == 100 for c in v['cards'])
    class Rq:
        async def json(self): return {'cfg': {'rotateHours': 3, 'on': False}}
    out = asyncio.run(rs.fuse_prime_admin(Rq()))
    assert out['cfg']['rotateHours'] == 3 and out['cfg']['on'] is False and asyncio.run(rs._prime_tick(2000)) == 0
