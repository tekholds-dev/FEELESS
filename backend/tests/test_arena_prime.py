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


def test_five_tiers_majors_solid_holds_and_young_coins_for_diamond():
    maj = [C('sol', 1, 'SOL'), C('btc', 1, 'cbBTC'), C('eth', 1, 'WETH'), C('jito', 1, 'JitoSOL')]
    d = ap.deal('safe', [P('pump', 2)], [R('y1', 0.1), R('y2', 0.1), R('y3', 0.1)], CFG, 0, maj)     # 💎 young coins toward 10×
    assert [l['role'] for l in d['legs']] == ['anchor', 'runner', 'runner', 'runner'] and ap.TEMPLATES['safe']['tp'] == 900
    ev = ap.deal('ever', [P('pump', 2)], [R('y1', 0.1)], CFG, 0, maj)                                 # ♾ 4 majors + PUMP, no stops
    assert [l['mint'] for l in ev['legs']] == ['sol', 'btc', 'eth', 'jito', 'pump'] and ap.TEMPLATES['ever']['sl'] == 0
    nx = ap.deal('next', [P('pump', 2)], [R(f'r{i}', 1) for i in range(5)], CFG, 0, maj)              # ⚡ all runners
    assert [l['role'] for l in nx['legs']] == ['runner'] * 4
    assert {t['tier'] for t in ap.TEMPLATES.values()} == {'diamond', 'gold', 'blaze', 'next', 'ever'}
    assert all(3 <= t['anchors'] + t['pools'] + t['runners'] <= 5 and t.get('why') for t in ap.TEMPLATES.values())


def test_stop_modes_replace_park_and_rebuy_or_hold():
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1), R('r2', 1)], CFG, 0, SOL[:1])
    px = {'Psol': 1, 'Pa': 1, 'Pr1': 0.75, 'Pr2': 1}                                       # r1 −25% ≤ −20%
    park = ap.tick(card, px, [], [R('r9', 1)], {**CFG, 'slMode': 'park'}, 60, SOL)
    assert 'r1' not in [l['mint'] for l in park['legs']] and 'Pr1' in park['parked'] and 'r9' not in [l['mint'] for l in park['legs']]
    assert abs(ap.value(park, px) - ap.value(card, px)) < 1e-6                               # parked $ still counts in the card
    back = ap.tick(park, {**px, 'Pr1': 1.0}, [], [], {**CFG, 'slMode': 'park'}, 120, SOL)  # back at entry, no fading → rebuy
    assert 'r1' in [l['mint'] for l in back['legs']] and not back['parked'] and back['events'][-1]['kind'] == 'rebuy'
    stay = ap.tick(park, {**px, 'Pr1': 1.0}, [], [], {**CFG, 'slMode': 'park'}, 120, SOL, {'Pr1': {'chg1h': -5, 'buyShare': 40}})
    assert 'Pr1' in stay['parked']                                                           # back at entry but fading → waits
    hold = ap.tick(card, px, [], [R('r9', 1)], {**CFG, 'slMode': 'hold'}, 60, SOL)
    assert 'r1' in [l['mint'] for l in hold['legs']]
    assert ap.clean_cfg({'slMode': 'nope'})['slMode'] == 'replace' and ap.clean_cfg({'slMode': 'park'})['slMode'] == 'park'


def test_everlasting_majors_are_never_stopped():
    maj = [C('sol', 1, 'SOL'), C('btc', 1, 'cbBTC'), C('eth', 1, 'WETH'), C('jito', 1, 'JitoSOL')]
    card = ap.deal('ever', [P('pump', 1)], [], CFG, 0, maj)
    out = ap.tick(card, {'Psol': 0.85, 'Pbtc': 0.85, 'Peth': 0.85, 'Pjito': 0.85, 'Ppump': 0.7}, [], [], CFG, 60, maj)
    assert len(out['legs']) == 5 and not [e for e in out['events'] if e['kind'] in ('sl', 'park')]


def test_exit_plan_rides_strong_momentum_and_banks_fading():
    strong = {'chg1h': 40, 'buyShare': 65, 'vol5m': 1000, 'vol1h': 10000}
    fade = {'chg1h': -8, 'buyShare': 40, 'vol5m': 100, 'vol1h': 10000}
    mode, frac, _ = ap.exit_plan(300, strong)
    assert mode == 'ride' and abs(frac - 0.25) < 1e-9          # 4× → sell 25% = the original cost; house money rides
    assert ap.exit_plan(60, strong)[0] == 'ride' and ap.exit_plan(60, strong)[1] < 60 / 160
    assert ap.exit_plan(60, fade)[:2] == ('bank', 0.75)
    assert ap.exit_plan(60, {'chg1h': 3, 'buyShare': 52, 'vol5m': 800, 'vol1h': 10000})[0] == 'gain' and ap.exit_plan(60)[0] == 'gain'


def test_auto_tp_compounds_into_the_others_and_pnl_excludes_fees():
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1), R('r2', 1)], CFG, 0, SOL[:1])       # 4 coins × $25
    px = {'Psol': 1, 'Pa': 1, 'Pr1': 2.2, 'Pr2': 1}                                         # r1 +120% ≥ +100% → no momentum → sell the gain
    out = ap.tick(card, px, [], [], CFG, 60, SOL)
    r1 = next(l for l in out['legs'] if l['mint'] == 'r1')
    assert abs(r1['units'] * 2.2 - 25) < 1e-6 and abs(out['compoundedUsd'] - 30) < 1e-6 and r1['firstEntry'] == 1
    tp = [e for e in out['events'] if e['kind'] == 'tp'][-1]
    assert tp['to'] == ['SOL', 'A', 'R2'] and tp['mode'] == 'gain' and ap.value(out, px) == 130 and out['feesUsd'] > card['feesUsd']
    strong = {'Pr1': {'chg1h': 50, 'buyShare': 70, 'vol5m': 2000, 'vol1h': 12000}}
    ride = ap.tick(card, {**px, 'Pr1': 4}, [], [], CFG, 60, SOL, strong)                   # 4× with momentum → only the cost comes out
    r = next(l for l in ride['legs'] if l['mint'] == 'r1')
    assert abs(r['units'] * 4 - 75) < 1e-6 and [e for e in ride['events'] if e['kind'] == 'tp'][-1]['mode'] == 'ride'


def test_stop_loss_replaced_early_cut_when_fading_anchor_never_stopped():
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1), R('r2', 1)], CFG, 0, SOL)
    px = {'Psol': 0.9, 'Pa': 1, 'Pr1': 0.75, 'Pr2': 0.88}                                   # r1 −25% ≤ −20% → out; SOL −10% stays
    out = ap.tick(card, px, [], [R('r9', 1)], CFG, 60, SOL)
    mints = [l['mint'] for l in out['legs']]
    assert 'r9' in mints and 'r1' not in mints and 'sol' in mints and 'r2' in mints          # r2 −12% not fading → kept
    fade = {'Pr2': {'chg1h': -9, 'buyShare': 38}}
    cut = ap.tick(out, {**px, 'Pr9': 1}, [], [R('r8', 1)], CFG, 120, SOL, fade)             # −12% ≥ half the stop + fading → early cut
    assert 'r2' not in [l['mint'] for l in cut['legs']] and 'cut early' in [e for e in cut['events'] if e['kind'] == 'sl'][-1]['why']
    rot = ap.tick(cut, {**px, 'Pr9': 1, 'Pr8': 1}, [P('x', 2)], [R('r7', 1)], CFG, 3600 + 61, SOL)
    assert all(e['symbol'] != 'SOL' for e in rot['events'] if e['kind'] == 'rotate')


def test_floor_never_lets_a_card_sit_below_minus_25():
    card = ap.deal('balanced', [P('a', 1)], [R('r1', 1)], CFG, 0, SOL)                      # SOL, JitoSOL, A, R1
    px = {'Psol': 0.78, 'Pjito': 0.78, 'Pa': 0.78, 'Pr1': 0.78}                              # every coin −22% → card −22% ≤ −20% floor
    out = ap.tick(card, px, [], [], CFG, 60, SOL)
    assert out.get('flooredAt') == 60 and {l['role'] for l in out['legs']} == {'anchor'} and [e for e in out['events'] if e['kind'] == 'floor']
    s = ap.summary(out, px)
    assert s['floored'] and s['pnlPct'] > -25
    later = ap.tick(out, {'Psol': 1, 'Pjito': 1, 'Pc': 1, 'Pr3': 1}, [P('c', 1)], [R('r3', 1)], CFG, 60 + 86401, SOL)
    assert not later.get('flooredAt') and len(later['legs']) > 2 and len(later['runs']) == 1 and later['runs'][0]['startUsd'] == 100


def test_day_record_counts_good_days_honestly():
    card = ap.deal('safe', [P('a', 1)], [R('r1', 1)], CFG, 0, SOL)
    up = {'Psol': 1.12, 'Pjito': 1.12, 'Pa': 1.12, 'Pr1': 1.12}
    c1 = ap.tick(card, up, [], [], CFG, 86401, SOL)
    c2 = ap.tick(c1, {k: v * 1.01 for k, v in up.items()}, [], [], CFG, 2 * 86402, SOL)
    r = ap.record(c2)
    assert r['loggedDays'] == 2 and r['goodDays'] == 1


def test_cfg_ranges():
    c = ap.clean_cfg({'rotateHours': 0.01, 'rotateCount': 9, 'sizeUsd': 5, 'compound': False, 'floorPct': 60})
    assert c['rotateHours'] == 0.08 and c['rotateCount'] == 3 and c['sizeUsd'] == 10 and c['compound'] is False and c['floorPct'] == 25


def test_service_deals_ticks_and_admin_config(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    async def cands(): return ([P('a', 1), P('b', 1), P('c', 1)], [R('r1', 1), R('r2', 1), R('r3', 1)], SOL)
    async def prices(legs): return {l['pairAddress']: 1.0 for l in legs}
    async def pairs(legs): return {l['pairAddress']: {'priceUsd': '1.0', 'priceChange': {'h1': 0}, 'txns': {'h1': {'buys': 5, 'sells': 5}}, 'volume': {'m5': 1, 'h1': 12}} for l in legs}
    monkeypatch.setattr(rs, '_prime_candidates', cands); monkeypatch.setattr(rs, '_hq_prices', prices); monkeypatch.setattr(rs, '_fuse_pairs', pairs); monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    rs._json_save(rs.FUSE_HQ_PATH, {})
    assert asyncio.run(rs._prime_tick(1000)) == 5
    v = asyncio.run(rs.fuse_prime())
    assert {'gold', 'blaze', 'ever'} <= {c['tier'] for c in v['cards']} and all(c['valueUsd'] == 100 for c in v['cards'])
    class Rq:
        async def json(self): return {'cfg': {'rotateHours': 3, 'on': False}}
    out = asyncio.run(rs.fuse_prime_admin(Rq()))
    assert out['cfg']['rotateHours'] == 3 and out['cfg']['on'] is False and asyncio.run(rs._prime_tick(2000)) == 0


def test_cmd_ctr_replaces_one_coin_with_best_same_role():
    card = ap.deal('balanced', [P('a', 1), P('b', 1)], [R('r1', 1), R('r2', 1)], CFG, 0, SOL[:1])
    out = ap.replace_leg(card, 'Pr1', {'Pr1': 2}, [P('a', 1)], [R('r1', 1), R('r9', 1)], SOL, CFG, 10)
    mints = [l['mint'] for l in out['legs']]
    assert 'r9' in mints and 'r1' not in mints and abs(next(l for l in out['legs'] if l['mint'] == 'r9')['costUsd'] - card['legs'][-1]['units'] * 2) < 1e-6
    assert out['events'][-1]['why'] == 'replaced from Cmd Ctr'
    import pytest
    with pytest.raises(ValueError):
        ap.replace_leg(card, 'Pnope', {}, [], [], [], CFG, 10)


def test_floored_card_redeals_on_the_rotation_clock_from_arena_coins_first():
    cfg = ap.clean_cfg({'rotateHours': 1})
    card = ap.deal('balanced', [P('a', 1)], [R('r1', 1)], cfg, 0, SOL)
    out = ap.tick(card, {'Psol': 0.78, 'Pjito': 0.78, 'Pa': 0.78, 'Pr1': 0.78}, [], [], cfg, 60, SOL)
    assert out.get('flooredAt') == 60
    pools = [P('c', 1), {**P('arena', 1), 'arena': True}]
    early = ap.tick(out, {'Psol': 1, 'Pjito': 1, 'Pc': 1, 'Parena': 1}, pools, [], cfg, 60 + 1800, SOL)
    assert early.get('flooredAt')                                                          # 30 min: waits for the rotation clock
    later = ap.tick(out, {'Psol': 1, 'Pjito': 1, 'Pc': 1, 'Parena': 1}, pools, [], cfg, 60 + 3601, SOL)
    assert not later.get('flooredAt') and later['runs'] and 'arena' in [l['mint'] for l in later['legs']]   # arena coin first
    assert [c['mint'] for c in ap.rated([P('x', 1), {**R('y', 1, 61), 'arena': True}, R('z', 1, 95)], 'runner')] == ['y', 'z']


def test_service_tags_arena_coins_for_rotation(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    async def metas(): return {'PA': {'baseAddress': 'A', 'symbol': 'A', 'priceUsd': 1, 'liquidityUsd': 5e5}, 'PB': {'baseAddress': 'B', 'symbol': 'B', 'priceUsd': 1, 'liquidityUsd': 5e5}}
    async def live(): return {'passing': [{'mint': 'R1', 'pairAddress': 'PR1', 'symbol': 'R1', 'price': 1, 'score': 80}, {'mint': 'R2', 'pairAddress': 'PR2', 'symbol': 'R2', 'price': 1, 'score': 90}], 'dropped': []}
    async def majors(): return []
    monkeypatch.setattr(rs, '_fuse_candidates', metas); monkeypatch.setattr(rs, '_runner_live', live); monkeypatch.setattr(rs, '_majors_rows', majors)
    rs._json_save(rs.RUNNERS_PATH, {'rounds': [{'picks': [{'mint': 'R1'}]}], 'litCards': []})
    monkeypatch.setitem(rs._arena_mega_cache, 'data', [{'legs': [{'pairAddress': 'PB'}]}])
    pools, runners, _ = asyncio.run(rs._prime_candidates())
    assert {p['mint']: p.get('arena', False) for p in pools} == {'A': False, 'B': True}            # B is on a stage card
    assert [r['mint'] for r in ap.rated(runners, 'runner')] == ['R1', 'R2']                     # round pick before a higher score
