"""Arena Prime: fully-auto paper cards — auto TP compounds into the other coins, SL is replaced at once, 2 weakest rotate every 6h,
fees tracked separately (never in P&L), every action logged with its reason."""
import arena_prime as ap

C = lambda m, px, sym=None: {'mint': m, 'pairAddress': 'P' + m, 'symbol': sym or m.upper(), 'price': px}
CFG = ap.clean_cfg({})


def test_deal_equal_dollars_by_template():
    pools = [C('a', 1), C('b', 2), C('c', 4), C('d', 1)]; runners = [C('r1', 0.1), C('r2', 0.2)]
    card = ap.deal('balanced', pools, runners, CFG, now=0)
    assert [l['mint'] for l in card['legs']] == ['a', 'b', 'c', 'r1', 'r2'] and all(abs(l['costUsd'] - 20) < 1e-9 for l in card['legs'])
    assert ap.value(card, {}) == 100 and card['feesUsd'] == 0.5


def test_auto_tp_compounds_into_the_others_and_pnl_excludes_fees():
    card = ap.deal('safe', [C('a', 1), C('b', 1), C('c', 1)], [C('r', 1)], CFG, now=0)
    px = {'Pa': 1.5, 'Pb': 1, 'Pc': 1, 'Pr': 1}                                  # a +50% ≥ +30% → take the gain
    out = ap.tick(card, px, [], [], CFG, now=60)
    a = out['legs'][0]
    assert abs(a['units'] * 1.5 - 25) < 1e-6 and abs(out['compoundedUsd'] - 12.5) < 1e-6
    assert out['events'][-1]['kind'] == 'tp' and out['events'][-1]['to'] == ['B', 'C', 'R']
    assert ap.value(out, px) == 112.5 and ap.summary(out, px)['pnlPct'] == 12.5 and out['feesUsd'] > card['feesUsd']   # fees separate


def test_stop_loss_replaced_now_and_rotation_every_6h():
    card = ap.deal('degen', [C('a', 1), C('b', 1)], [C('r1', 1), C('r2', 1), C('r3', 1)], CFG, now=0)
    px = {'Pa': 1, 'Pb': 1, 'Pr1': 0.5, 'Pr2': 1.1, 'Pr3': 0.9}                # r1 −50% ≤ −40% → out
    out = ap.tick(card, px, [C('x', 2)], [C('r9', 1)], CFG, now=60)
    assert 'r9' in [l['mint'] for l in out['legs']] and 'r1' not in [l['mint'] for l in out['legs']] and out['events'][-1]['kind'] == 'sl'
    out2 = ap.tick(out, {**px, 'Pr9': 1}, [C('x', 2), C('y', 3)], [C('r8', 1), C('r7', 1)], CFG, now=6 * 3600 + 61)
    rot = [e for e in out2['events'] if e['kind'] == 'rotate']
    assert len(rot) == 2 and out2['lastRotateAt'] == 6 * 3600 + 61
    out3 = ap.tick(out2, px, [C('z', 1)], [C('r6', 1)], CFG, now=6 * 3600 + 120)
    assert not [e for e in out3['events'] if e['kind'] == 'rotate' and e['at'] == 6 * 3600 + 120]      # not again within 6h


def test_cfg_ranges():
    c = ap.clean_cfg({'rotateHours': 0.2, 'rotateCount': 9, 'sizeUsd': 5, 'compound': False})
    assert c['rotateHours'] == 1 and c['rotateCount'] == 3 and c['sizeUsd'] == 10 and c['compound'] is False


def test_service_deals_ticks_and_admin_config(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    async def cands(): return ([C('a', 1), C('b', 1), C('c', 1), C('d', 1)], [C('r1', 1), C('r2', 1), C('r3', 1)])
    async def prices(legs): return {l['pairAddress']: 1.0 for l in legs}
    monkeypatch.setattr(rs, '_prime_candidates', cands); monkeypatch.setattr(rs, '_hq_prices', prices); monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    rs._json_save(rs.FUSE_HQ_PATH, {})
    assert asyncio.run(rs._prime_tick(1000)) == 3
    v = asyncio.run(rs.fuse_prime())
    assert {c['tpl'] for c in v['cards']} == {'safe', 'balanced', 'degen'} and all(c['valueUsd'] == 100 for c in v['cards'])
    class R:
        async def json(self): return {'cfg': {'rotateHours': 3, 'on': False}}
    out = asyncio.run(rs.fuse_prime_admin(R()))
    assert out['cfg']['rotateHours'] == 3 and out['cfg']['on'] is False and asyncio.run(rs._prime_tick(2000)) == 0
