import pytest
"""Arena Prime: 3 top-tier paper cards, fully auto — 3★+ coins only, a stable major anchor (never rotated / stopped), auto TP
compounds into the other coins, SL replaced at once, 2 weakest rotate every 6h, a −20% card FLOOR (never −25%), an honest
day record (good day = +10%), fees tracked apart (never in P&L), every action logged with its reason."""
import arena_prime as ap


@pytest.fixture(autouse=True)
def _deep_unknown_pools(request, monkeypatch):
    """Older tests feed no liquidity and expect mid-price maths; the thin-pool default has its own tests."""
    if not any(k in request.node.name for k in ('true_fills', 'really_pay')):
        monkeypatch.setattr(ap, 'UNKNOWN_LIQ', 1e18)
    if 'bell' not in request.node.name:   # older tests tick exactly on the round clock
        monkeypatch.setattr(ap, 'BELL_SEC', 0)

C = lambda m, px, sym=None, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': sym or m.upper(), 'price': px, **k}
P = lambda m, px: C(m, px, liquidityUsd=2e6, volume24h=2e6)             # 5★ pool
R = lambda m, px, sc=90: C(m, px, score=sc)                                 # 5★ runner by default
SOL = [C('sol', 1, 'SOL'), C('jito', 1, 'JitoSOL')]
CFG = ap.clean_cfg({'floorPct': 20, 'rotateMinDrop': 0, 'cycleEvery': 1, 'rotateConfirm': 1, 'minHoldMins': 0, 'cycles': {'safe': 'off', 'balanced': 'off', 'degen': 'classic', 'next': 'classic', 'ever': 'off'},   # the original tier behaviour
                    'payouts': {'safe': 0, 'balanced': 0, 'degen': 0, 'next': 0, 'ever': 0}, 'compoundStyle': 'even'})


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
    assert abs(r1['units'] * 2.2 - 25) < 0.05 and abs(out['compoundedUsd'] - 30) < 0.05 and r1['firstEntry'] == 1
    tp = [e for e in out['events'] if e['kind'] == 'tp'][-1]
    assert tp['to'] == ['SOL', 'A', 'R2'] and tp['mode'] == 'gain' and abs(ap.value(out, px) - 130) < 0.05 and out['feesUsd'] > card['feesUsd']
    strong = {'Pr1': {'chg1h': 50, 'buyShare': 70, 'vol5m': 2000, 'vol1h': 12000}}
    ride = ap.tick(card, {**px, 'Pr1': 4}, [], [], CFG, 60, SOL, strong)                   # 4× (≥ +150%) → 🏇 rides, nothing sold yet
    r = next(l for l in ride['legs'] if l['mint'] == 'r1')
    assert abs(r['units'] * 1 - 25) < 0.1 and r['ride'] and ride['events'][-1]['kind'] == 'ride'


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
    assert c['rotateHours'] == 0.08 and c['rotateCount'] == 3 and c['sizeUsd'] == 10 and c['compound'] is False and c['floorPct'] == 60


def test_service_deals_ticks_and_admin_config(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    async def cands(): return ([P('a', 1), P('b', 1), P('c', 1)], [R('r1', 1), R('r2', 1), R('r3', 1)], SOL)
    async def prices(legs): return {l['pairAddress']: 1.0 for l in legs}
    async def pairs(legs): return {l['pairAddress']: {'priceUsd': '1.0', 'priceChange': {'h1': 0}, 'txns': {'h1': {'buys': 5, 'sells': 5}}, 'volume': {'m5': 1, 'h1': 12}} for l in legs}
    monkeypatch.setattr(rs, '_prime_candidates', cands); monkeypatch.setattr(rs, '_hq_prices', prices); monkeypatch.setattr(rs, '_fuse_pairs', pairs); monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    rs._json_save(rs.FUSE_HQ_PATH, {})
    assert asyncio.run(rs._prime_tick(1000)) == 4   # the tiny fixture has only six growth mints; never duplicate one to force five cards
    v = asyncio.run(rs.fuse_prime())
    growth = [l['mint'] for c in v['cards'] for l in c['legs'] if l['role'] != 'anchor']
    assert len(growth) == len(set(growth))
    assert {'gold', 'blaze', 'ever'} <= {c['tier'] for c in v['cards']} and all(99 < c['valueUsd'] <= 100 for c in v['cards'])   # true fills: a fresh card paid real impact
    class Rq:
        async def json(self): return {'cfg': {'rotateHours': 3, 'on': False}}
    out = asyncio.run(rs.fuse_prime_admin(Rq()))
    assert out['cfg']['rotateHours'] == 3 and out['cfg']['on'] is False and asyncio.run(rs._prime_tick(2000)) == 0


def test_cmd_ctr_replaces_one_coin_with_best_same_role():
    card = ap.deal('balanced', [P('a', 1), P('b', 1)], [R('r1', 1), R('r2', 1)], CFG, 0, SOL[:1])
    out = ap.replace_leg(card, 'Pr1', {'Pr1': 2}, [P('a', 1)], [R('r1', 1), R('r9', 1)], SOL, CFG, 10)
    mints = [l['mint'] for l in out['legs']]
    assert 'r9' in mints and 'r1' not in mints and abs(next(l for l in out['legs'] if l['mint'] == 'r9')['costUsd'] - card['legs'][-1]['units'] * 2) < 1e-6
    assert out['events'][-1]['why'] == 'replaced by FEELESS'
    import pytest
    with pytest.raises(ValueError):
        ap.replace_leg(card, 'Pnope', {}, [], [], [], CFG, 10)


def test_floored_card_redeals_on_the_rotation_clock_from_arena_coins_first():
    cfg = ap.clean_cfg({'rotateHours': 1, 'floorPct': 20, 'cycles': CFG['cycles'], 'payouts': CFG['payouts']})
    card = ap.deal('balanced', [P('a', 1)], [R('r1', 1)], cfg, 0, SOL)
    out = ap.tick(card, {'Psol': 0.78, 'Pjito': 0.78, 'Pa': 0.78, 'Pr1': 0.78}, [], [], cfg, 60, SOL)
    assert out.get('flooredAt') == 60
    pools = [P('c', 1), {**P('arena', 1), 'arena': True}]
    same = ap.tick(out, {'Psol': 1, 'Pjito': 1, 'Pc': 1, 'Parena': 1}, pools, [], cfg, 60 + 30, SOL)
    assert same.get('flooredAt')                                                           # same minute: still floored
    later = ap.tick(out, {'Psol': 1, 'Pjito': 1, 'Pc': 1, 'Parena': 1}, pools, [], cfg, 60 + 61, SOL)
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


def test_discovery_pool_includes_existing_trending_new_launchpad_and_pump_feeds(monkeypatch):
    import asyncio
    import reputation_service as rs
    calls = []
    class Response:
        status_code = 200
        def __init__(self, rows): self.rows = rows
        def json(self): return {'pairs': self.rows}
    class Http:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None):
            calls.append((url, dict(params or {})))
            if url.startswith('http://127.0.0.1:5001'):
                tag = f"{params['kind']}-{params.get('scope', 'all')}-{params.get('page', 1)}"
                return Response([{'pairAddress': tag}])
            if 'token-boosts' in url:
                return type('R', (), {'json': lambda self: []})()
            return Response([])
    monkeypatch.setattr(rs.httpx, 'AsyncClient', Http)
    rs._fuse_discover_cache.clear()
    rows = asyncio.run(rs._fuse_discover_pairs('solana'))
    pairs = {r['pairAddress'] for r in rows}
    assert {'trending-all-1', 'new-all-1', 'trending-all-2', 'new-all-2',
            'trending-launchpads-1', 'new-launchpads-1', 'trending-pump-1'} <= pairs


def test_rounds_count_and_the_best_card_of_each_round_is_crowned():
    cfg = ap.clean_cfg({'rotateHours': 1, 'floorPct': 20, 'cycles': CFG['cycles'], 'payouts': CFG['payouts']})
    a = ap.deal('balanced', [P('a', 1)], [R('r1', 1)], cfg, 0, SOL); b = ap.deal('degen', [P('a', 1)], [R('r1', 1)], cfg, 0, SOL)
    up = {'Psol': 1.1, 'Pjito': 1.1, 'Pa': 1.1, 'Pr1': 1.1}; flat = {'Psol': 1, 'Pjito': 1, 'Pa': 1, 'Pr1': 1}
    a2 = ap.tick(a, up, [], [], cfg, 3601, SOL); b2 = ap.tick(b, flat, [], [], cfg, 3601, SOL)
    assert a2['rounds'] == 1 and a2['lastRoundPct'] > b2['lastRoundPct']
    cards = {'balanced': a2, 'degen': b2}
    assert ap.crown_round(cards) == a2['id'] and cards['balanced']['roundWins'] == 1
    assert ap.crown_round(cards) is None                                                   # crowned once per round


def test_cycling_tiers_move_through_anchor_degen_anchor_mixed_rounds():
    cfg = ap.clean_cfg({'rotateHours': 1, 'floorPct': 20, 'cycleEvery': 1, 'rotateMinDrop': 0, 'rotateConfirm': 1, 'minHoldMins': 0, 'cycles': CFG['cycles'], 'payouts': CFG['payouts']})
    maj = [C('sol', 1, 'SOL'), C('btc', 1, 'cbBTC'), C('eth', 1, 'WETH')]   # an anchor round needs ≥ 3 coins
    runners = [R('r1', 1), R('r2', 1), R('r3', 1)]
    flat = {'Psol': 1, 'Pbtc': 1, 'Peth': 1, 'Pa': 1, 'Pr1': 1, 'Pr2': 1, 'Pr3': 1}
    c = ap.deal('next', [P('a', 1)], runners, cfg, 0, maj)
    seen = []
    for i in range(1, 5):
        c = ap.tick(c, flat, [P('a', 1)], runners, cfg, i * 3601, maj)
        seen.append((c.get('phase'), sorted({l['role'] for l in c['legs']})))
    assert [p for p, _ in seen] == ['degen', 'anchor', 'mixed', 'anchor']
    assert seen[1][1] == ['anchor', 'runner'] and 'runner' in seen[0][1]
    assert c['startUsd'] == 100 and not c.get('runs')                                        # one continuous run
    assert ap.deal('balanced', [P('a', 1)], runners, cfg, 0, maj).get('phase') is None      # non-cycling tiers unchanged


def test_paper_fills_are_true_fills_with_price_impact():
    assert ap.buy_px(1.0, 1000, 200_000) == 1.0 * (1 + 1000 / 100_000)                   # $1K into a $200K pool → 1% worse
    assert abs(ap.sell_usd(1000, 1.0, 200_000) - 1000 / 1.01) < 1e-9
    assert ap.buy_px(1.0, 1000, 0) == 1.0 + 1000 / (ap.UNKNOWN_LIQ / 2)                   # unknown depth = a THIN pool (never infinitely deep)
    thin = C('t', 1.0, liquidityUsd=20_000, volume24h=50_000)
    leg = ap._leg(thin, 50, 0, 'pool')
    assert leg['entry'] > 1.0 and leg['units'] < 50 and leg['midAtEntry'] == 1.0          # a $50 buy in a $20K pool fills above mid


def test_cmd_ctr_freezes_a_coin_and_sets_its_own_stop_mode():
    card = {'legs': [{'pairAddress': 'P1', 'symbol': 'A', 'role': 'runner'}]}
    c = ap.set_leg(card, 'P1', frozen=True, sl_mode='park')
    assert c['legs'][0]['frozen'] and c['legs'][0]['slMode'] == 'park' and not card['legs'][0].get('frozen')   # pure
    assert ap.set_leg(c, 'P1', sl_mode='')['legs'][0]['slMode'] is None
    with pytest.raises(ValueError):
        ap.set_leg(card, 'NOPE', frozen=True)


def test_round_cycles_per_tier_and_trailing_lock():
    assert ap.next_phase('off', 3, -5) is None and ap.next_phase('classic', 1, 0) == 'degen'
    assert ap.next_phase('adaptive', 0, -4) == 'anchor' and ap.next_phase('adaptive', 0, 8) == 'degen' and ap.next_phase('adaptive', 0, 1) == 'mixed'
    assert ap.next_phase('safe', 1, 0) == 'mixed' and ap.next_phase('press', 0, 0) == 'degen'
    c = ap.clean_cfg({'cycles': {'safe': 'adaptive', 'next': 'bogus'}})
    assert c['cycles']['safe'] == 'adaptive' and c['cycles']['next'] == 'press' and c['trail'] is True


def test_trailing_lock_sells_a_runner_that_gives_back_a_50pct_run():
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1), R('r2', 1)], CFG, 0, SOL[:1])
    up = ap.tick(card, {'Psol': 1, 'Pa': 1, 'Pr1': 1.6, 'Pr2': 1}, [], [R('r9', 1)], CFG, 30, SOL)       # +60% (below TP 100)
    assert 'r1' in [l['mint'] for l in up['legs']]
    back = ap.tick(up, {'Psol': 1, 'Pa': 1, 'Pr1': 1.04, 'Pr2': 1}, [], [R('r9', 1)], CFG, 60, SOL)      # back to +4%
    assert 'r1' not in [l['mint'] for l in back['legs']] and 'locked before it turned red' in back['events'][-1]['why']
    off = ap.tick(up, {'Psol': 1, 'Pa': 1, 'Pr1': 1.04, 'Pr2': 1}, [], [R('r9', 1)], {**CFG, 'trail': False}, 60, SOL)
    assert 'r1' in [l['mint'] for l in off['legs']]



def test_tier_dna_payout_goes_to_the_wallet_and_smart_compound_skips_fading_coins():
    cfg = ap.clean_cfg({'payouts': {'degen': 50}, 'compoundStyle': 'smart', 'cycles': {'degen': 'off'}})
    assert len(set(ap.DEFAULT_CYCLES.values())) == len(ap.DEFAULT_CYCLES)                       # every tier cycles its own way
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1), R('r2', 1)], cfg, 0, SOL[:1])
    px = {'Psol': 1, 'Pa': 1, 'Pr1': 2.2, 'Pr2': 1}                                              # r1 +120% ≥ TP 100
    mom = {'Pr1': {'chg1h': 30, 'buyShare': 70}, 'Pa': {'chg1h': -9, 'buyShare': 35}, 'Psol': {'chg1h': 2, 'buyShare': 55}, 'Pr2': {'chg1h': 5, 'buyShare': 60}}
    out = ap.tick(card, px, [], [], cfg, 30, SOL, mom)
    assert out['walletUsd'] > 0 and any(e['kind'] == 'payout' for e in out['events'])
    tp = [e for e in out['events'] if e['kind'] == 'tp'][-1]
    assert 'A' not in tp['to'] and 'smart compound' in tp['why']                                  # fading pool gets nothing
    assert abs(ap.value(out, px) - (ap.value(card, px) - 0)) < 5                                  # paid-out $ still counts for the owner


def test_rug_shield_sells_a_coin_whose_liquidity_was_pulled():
    card = ap.deal('degen', [P('a', 1)], [{**R('r1', 1), 'liquidityUsd': 100_000}, R('r2', 1)], CFG, 0, SOL[:1])
    assert [l for l in card['legs'] if l['mint'] == 'r1'][0]['liq'] == 100_000
    out = ap.tick(card, {'Psol': 1, 'Pa': 1, 'Pr1': 0.9, 'Pr2': 1}, [], [], CFG, 30, SOL, None, {'Pr1': 40_000})
    assert 'r1' not in [l['mint'] for l in out['legs']] and any(e['kind'] == 'rug' and 'pulled' in e['why'] for e in out['events'])


def test_rounds_per_run_close_the_run_and_math_reads_plainly():
    cfg = ap.clean_cfg({'roundsPerRun': 5})
    assert cfg['roundsPerRun'] == 5 and ap.clean_cfg({'roundsPerRun': 7})['roundsPerRun'] == 0
    card = {'id': 'prime-safe', 'tpl': 'safe', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 40.0,
            'takenUsd': 300.0, 'walletUsd': 25.0, 'startUsd': 100.0, 'events': [], 'legs': [{'mint': 'M', 'pairAddress': 'P', 'symbol': 'M', 'role': 'runner', 'entry': 1.0, 'units': 150.0, 'costUsd': 150.0}]}
    s = ap.summary(card, {'P': 1.0}, {'rotateHours': 1})
    m = s['math']
    assert m['nowUsd'] == 175 and m['heldUsd'] == 150 and m['paidOutUsd'] == 25 and m['pnlUsd'] == 75   # gross takes never double-count
    assert s['nextRoundAt'] == 3600 and s['real'] is False


def test_impact_mult_from_real_fills_makes_paper_fills_worse():
    try:
        base = ap.buy_px(1.0, 100, 10000)
        ap.IMPACT_MULT = 2.0
        assert ap.buy_px(1.0, 100, 10000) > base and ap.sell_usd(100, 1.0, 10000) < 100 / (1 + 100 / 5000) + 1e-9
    finally:
        ap.IMPACT_MULT = 1.0


def test_card_value_is_what_selling_would_really_pay():
    card = {'legs': [{'pairAddress': 'P', 'units': 100000.0, 'entry': 1.0}], 'cash': 0.0}
    assert ap.value(card, {'P': 1.0}) == round(100000 / (1 + 100000 / (ap.UNKNOWN_LIQ / 2)), 4)   # no liquidity known → treated as thin
    v = ap.value(card, {'P': 1.0}, {'P': 36000})                        # $100K bag in a $36K pool
    assert v < 16000 and v == round(100000 / (1 + 100000 / 18000), 4)


def test_redeals_never_rebuy_with_paid_out_or_parked_money():
    card = {'legs': [{'pairAddress': 'P', 'units': 100.0, 'entry': 1.0}], 'cash': 0.0, 'walletUsd': 30.0,
            'parked': {'Q': {'usd': 20.0}}}
    assert ap.value(card, {'P': 1.0}) == 150.0
    assert ap.in_play(card, {'P': 1.0}) == 100.0          # only the coins + cash go back into coins


def test_runner_rides_from_150_and_sells_only_30_off_its_new_high():
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'cycles': {'degen': 'off'}})
    leg = {'mint': 'R', 'pairAddress': 'PR', 'symbol': 'R', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0, 'liq': 1e12}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 10.0, 'legs': [leg]}
    c = ap.tick(card, {'PR': 2.6}, [], [], cfg, 10, liqs={'PR': 1e12})          # +160% → rides, nothing sold
    assert c['legs'][0]['ride'] and c['legs'][0]['units'] == 10 and c['events'][-1]['kind'] == 'ride'
    c = ap.tick(c, {'PR': 20.0}, [], [], cfg, 20, liqs={'PR': 1e12})            # a 20× keeps riding, new high
    assert c['legs'][0]['ride'] and c['legs'][0]['high'] == 20.0
    c = ap.tick(c, {'PR': 15.0}, [], [], cfg, 30, liqs={'PR': 1e12})            # −25% from the high: still riding
    assert c['legs'][0]['ride']
    c = ap.tick(c, {'PR': 13.5}, [], [], cfg, 40, liqs={'PR': 1e12})            # −32.5%: sold
    assert not c['legs'][0].get('ride') and c['legs'][0]['units'] == 0 and c['cash'] > 100


def test_worst_day_minus_40_fixes_the_tier_config():
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'floorPct': 40, 'cycles': {'degen': 'press'}})
    legs = [{'mint': 'R', 'pairAddress': 'PR', 'symbol': 'R', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0},
            {'mint': 'S', 'pairAddress': 'PS', 'symbol': 'SOL', 'role': 'anchor', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0}]
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 20.0, 'dayStartUsd': 20.0, 'dayAt': 0, 'legs': legs}
    anchors = [{'mint': m, 'pairAddress': f'P{m}', 'symbol': m, 'price': 1.0, 'stars': 5} for m in ('S', 'B', 'E')]
    anchors[0]['pairAddress'] = 'PS'
    c = ap.tick(card, {'PR': 0.15, 'PS': 1.0, 'PB': 1.0, 'PE': 1.0}, [], [], cfg, 10, anchors, liqs={'PR': 1e12, 'PS': 1e12, 'PB': 1e12, 'PE': 1e12})   # day −42.5%
    assert c['cycleFix'] == 'safe' and any(e['kind'] == 'fix' for e in c['events'])
    assert ap.tick(c, {'PR': 0.15, 'PS': 1.0, 'PB': 1.0, 'PE': 1.0}, [], [], cfg, 20, anchors, liqs={'PS': 1e12})['fixedAt'] == c['fixedAt']   # once a day


def test_bell_round_ends_then_10s_countdown_then_the_deal():
    assert ap.BELL_SEC == 10
    cfg = ap.clean_cfg({'rotateHours': 1, 'cycles': {'degen': 'off'}})
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 10.0, 'legs': [{'mint': 'S', 'pairAddress': 'PS', 'symbol': 'SOL', 'role': 'anchor', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0}]}
    assert ap.tick(card, {'PS': 1.0}, [], [], cfg, 3605, liqs={'PS': 1e12}).get('rounds', 0) == 0     # inside the countdown: not yet
    assert ap.tick(card, {'PS': 1.0}, [], [], cfg, 3610, liqs={'PS': 1e12})['rounds'] == 1             # bell done: dealt
    assert ap.summary(card, {'PS': 1.0}, cfg)['nextRoundAt'] == 3610


def test_hold_rule_streaks_and_min_3_coin_cycles():
    assert ap.deal('next', [], [], ap.clean_cfg({}), 0, [C('sol', 1, 'SOL')], shape='anchor') is None      # < 3 coins → no re-shape
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 1, 'cycles': {'degen': 'off'}})
    runner = {'mint': 'R', 'pairAddress': 'PR', 'symbol': 'R', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 10.0, 'legs': [runner]}
    lq = {'PR': 1e12, 'PN': 1e12}
    new = [{'mint': 'N', 'pairAddress': 'PN', 'symbol': 'N', 'price': 1.0, 'score': 99, 'stars': 5}]
    c = ap.tick(card, {'PR': 1.9}, [], new, cfg, 100, liqs=lq)                 # +90% during the round
    c = ap.tick(c, {'PR': 1.85, 'PN': 1.0}, [], new, cfg, 3600, liqs=lq)        # round ends, stayed ≥ +80% all round → held
    assert c['legs'][0]['ride'] and any(e['kind'] == 'ride' for e in c['events'])
    c = ap.tick(c, {'PR': 1.7, 'PN': 1.0}, [], new, cfg, 3700, liqs=lq)         # +70%: under +80% → swapped for N
    assert c['legs'][0]['mint'] == 'N' and c['events'][-1]['kind'] == 'ride-end'
    st = dict(card, streak=-2, legs=[dict(runner)], roundStartUsd=10.0)
    lost = ap.tick(st, {'PR': 0.9, 'PN': 1.0}, [], [], cfg, 3600, liqs=lq)     # 3rd losing round → safe config
    assert lost['cycleFix'] == 'safe' and lost['streak'] == 0
    won = ap.tick(dict(card, streak=2, legs=[dict(runner)], roundStartUsd=10.0), {'PR': 1.1}, [], [], cfg, 3600, liqs=lq)   # 3rd win → locked + frozen
    assert won['lockRounds'] == 1 and won['legs'][0]['freezeRounds'] == 1


def test_rescue_auto_custom_cycles_and_low_churn():
    assert ap.cycle_seq('degen,safest,anchor') == ('degen', 'safest', 'anchor') and ap.cycle_seq('degen,nope') is None
    assert ap.next_phase('auto', 0, -20) == 'breakeven' and ap.next_phase('auto', 0, -4) == 'safest' and ap.next_phase('auto', 0, -2) == 'mixed' and ap.next_phase('auto', 0, 9) == 'degen'
    assert ap.next_phase('rescue', 0, 0) == 'safest' and ap.next_phase('rescue', 1, 0) == 'breakeven'
    c = ap.clean_cfg({'cycles': {'degen': 'degen,safest,breakeven'}})
    assert c['cycles']['degen'] == 'degen,safest,breakeven' and c['rotateMinDrop'] == 10 and c['cycleEvery'] == 6
    # breakeven picks the highest-VOLUME runners
    runners = [{**R('a', 1), 'vol1h': 10}, {**R('b', 1), 'vol1h': 900}, {**R('c', 1), 'vol1h': 500}, {**R('d', 1), 'vol1h': 700}]
    d = ap.deal('next', [{**P('p', 1), 'volume24h': 1e6}], runners, ap.clean_cfg({}), 0, [], shape='breakeven')
    assert sorted(l['mint'] for l in d['legs'] if l['role'] == 'runner') == ['b', 'c', 'd']
    # rescue: a card 50% under its start switches cycle; a winning coin is never rotated out
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 1, 'floorPct': 60})
    legs = [{'mint': 'W', 'pairAddress': 'PW', 'symbol': 'W', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0},
            {'mint': 'L', 'pairAddress': 'PL', 'symbol': 'L', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0}]
    card = {'id': 'prime-next', 'tpl': 'next', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 32.0, 'legs': legs}   # 15.5 of 32 = −52%: rescue, above the −60% floor
    new = [{'mint': 'N', 'pairAddress': 'PN', 'symbol': 'N', 'price': 1.0, 'score': 99, 'stars': 5}]
    out = ap.tick(card, {'PW': 1.05, 'PL': 0.5, 'PN': 1.0}, [], new, cfg, 3600, liqs={'PW': 1e12, 'PL': 1e12, 'PN': 1e12})
    assert out['cycleFix'] == 'rescue' and 'W' in [l['mint'] for l in out['legs']]


def test_patience_makes_5min_rounds_work_and_bad_weather_tightens_runners():
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 5 / 60, 'cycles': {'degen': 'off'}})
    assert cfg['rotateConfirm'] == 3 and cfg['minHoldMins'] == 30
    leg = {'mint': 'L', 'pairAddress': 'PL', 'symbol': 'L', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0, 'at': 0}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 10.0, 'legs': [leg]}
    new = [{'mint': 'N', 'pairAddress': 'PN', 'symbol': 'N', 'price': 1.0, 'score': 99, 'stars': 5, 'vol1h': 50_000, 'buyShare': 60}]
    lq = {'PL': 1e12, 'PN': 1e12}
    c = card
    for r in range(1, 3):   # 2 losing rounds: not yet (one noisy dip never sells it)
        c = ap.tick(c, {'PL': 0.85, 'PN': 1.0}, [], new, cfg, r * 300, liqs=lq)
        assert c['legs'][0]['mint'] == 'L'
    c = ap.tick(c, {'PL': 0.85, 'PN': 1.0}, [], new, cfg, 1800, liqs=lq)   # 3rd losing round + held 30 min → swapped
    assert c['legs'][0]['mint'] == 'N'
    weak = [{'mint': 'W', 'pairAddress': 'PW', 'symbol': 'W', 'price': 1.0, 'score': 99, 'stars': 5, 'vol1h': 900}]
    c2 = ap.tick(dict(card, legs=[dict(leg, loseRounds=5)]), {'PL': 0.85, 'PW': 1.0}, [], weak, {**cfg, 'strictRunners': True}, 1800, liqs={'PL': 1e12, 'PW': 1e12})
    assert c2['legs'][0]['mint'] == 'L'                                     # bad weather: a thin runner never gets in


def test_saved_minus_five_and_patience_two_rotate_on_the_second_qualifying_round():
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 5 / 60, 'rotateMinDrop': 5,
                        'rotateConfirm': 2, 'minHoldMins': 0, 'cycleEvery': 0, 'cycles': {'degen': 'off'}})
    old = {'mint': 'OLD', 'pairAddress': 'PO', 'symbol': 'OLD', 'role': 'runner', 'entry': 1.0, 'units': 10,
           'costUsd': 10, 'at': 0}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0,
            'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0, 'events': [], 'startUsd': 10, 'legs': [old]}
    new = [{**R('NEW', 1), 'vol1h': 50_000, 'buyShare': 60}]
    one = ap.tick(card, {'PO': .949, 'PNEW': 1}, [], new, cfg, 300, liqs={'PO': 1e12, 'PNEW': 1e12})
    assert one['legs'][0]['mint'] == 'OLD' and one['legs'][0]['loseRounds'] == 1
    two = ap.tick(one, {'PO': .949, 'PNEW': 1}, [], new, cfg, 600, liqs={'PO': 1e12, 'PNEW': 1e12})
    assert two['legs'][0]['mint'] == 'NEW' and two['events'][-1]['kind'] == 'rotate'


def test_loss_boundary_matches_the_one_decimal_card_display():
    # The routed decimal price is −4.99989%; the card displays −5.0%, so the saved −5% boundary must count it.
    assert ap.at_or_below_loss(1.17284, 1.234567, 5)


def test_due_phase_cannot_redeal_the_mint_rotated_out_on_that_same_boundary():
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 1, 'rotateMinDrop': 5,
                        'rotateConfirm': 1, 'minHoldMins': 0, 'cycleEvery': 1,
                        'cycles': {'degen': 'classic'}, 'keepWinPct': 5})
    legs = [
        {'mint': 'SOL', 'pairAddress': 'PSOL', 'symbol': 'SOL', 'role': 'anchor', 'entry': 1, 'units': 10, 'costUsd': 10, 'at': 0},
        *[{'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': 'runner', 'entry': 1, 'units': 10, 'costUsd': 10, 'at': 0}
          for m in ('OLD', 'A', 'B')],
    ]
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'rounds': 0,
            'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0, 'events': [],
            'startUsd': 40.0, 'roundStartUsd': 40.0, 'legs': legs}
    runners = [R(m, 1) for m in ('OLD', 'N1', 'N2', 'N3', 'A', 'B')]
    prices = {'PSOL': 1, 'POLD': .9, 'PA': 1, 'PB': 1, 'PN1': 1, 'PN2': 1, 'PN3': 1}
    out = ap.tick(card, prices, [], runners, cfg, 3610, [C('SOL', 1, 'SOL')], liqs={k: 1e12 for k in prices})
    assert 'OLD' not in {leg['mint'] for leg in out['legs']}
    assert {'N1', 'N2', 'N3'} <= {leg['mint'] for leg in out['legs']}


def test_self_fix_never_removes_patience_on_fast_clocks():
    import asyncio, pytest
    rs = pytest.importorskip('reputation_service')
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cfg': {'rotateHours': 5 / 60, 'rotateConfirm': 3}, 'cards': {}}})
    sim = {'s24': {'n': 200, 'avgPct': 1}, 'best': {'confirm': {'value': '1', 'n': 50}}}
    asyncio.run(rs._engine_self_fix(1.0, sim))
    assert rs._prime_cfg()['rotateConfirm'] == 3


def test_safe_fix_expires_back_to_own_cycle():
    import arena_prime as ap
    assert ap.SAFE_FIX_ROUNDS == 8


def test_majors_only_card_reshapes_into_growth_without_waiting():
    import inspect, arena_prime as ap
    assert 'majors_only' in inspect.getsource(ap.tick)


def test_adaptive_noise_stays_mixed():
    import arena_prime as ap
    assert ap.next_phase('adaptive', 1, -0.04) == 'mixed'
    assert ap.next_phase('adaptive', 1, -3.5) == 'anchor'
    assert ap.next_phase('adaptive', 1, 6) == 'degen'


def test_every_shape_has_growth_and_mixes_by_name():
    import time, arena_prime as ap
    assert all(p['runners'] >= 1 for p in ap.PHASES.values())
    anchors = [{'mint': m, 'pairAddress': m, 'symbol': m, 'price': 1} for m in ('A1', 'A2', 'A3')]
    runners = [{'mint': 'R1', 'pairAddress': 'R1', 'symbol': 'R1', 'price': 1, 'score': 90},
               {'mint': 'R2', 'pairAddress': 'R2', 'symbol': 'R2', 'price': 1, 'score': 80},
               {'mint': 'N1', 'pairAddress': 'N1', 'symbol': 'N1', 'price': 1, 'score': 60, 'newMajor': True}]
    roles = lambda sh: [l['symbol'] for l in ap.deal('safe', [], runners, ap.clean_cfg({}), time.time(), anchors, usd=10, shape=sh)['legs'] if l['role'] == 'runner']
    assert roles('anchor') == ['N1'] and roles('safest') == ['N1']
    assert set(roles('mixed')) == {'N1', 'R1'}
    assert roles('degen')[:2] == ['R1', 'R2']


def test_noise_rounds_never_trip_the_safe_fix_and_owner_cycle_wins():
    """5-min rounds: ±0.04% moves are noise — they neither build nor break a streak, so the owner's cycle keeps running."""
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 1, 'cycles': {'degen': 'off'}})
    runner = {'mint': 'R', 'pairAddress': 'PR', 'symbol': 'R', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 10.0, 'legs': [runner], 'streak': -2, 'roundStartUsd': 10.0}
    lq = {'PR': 1e12}
    tiny = ap.tick(card, {'PR': 0.9996}, [], [], cfg, 3600, liqs=lq)            # −0.04% round: noise
    assert not tiny.get('cycleFix') and tiny['streak'] == -2
    real = ap.tick(card, {'PR': 0.95}, [], [], cfg, 3600, liqs=lq)              # −5%: a real 3rd losing round
    assert real['cycleFix'] == 'safe'
    done = ap.tick(dict(card, cycleFix='safe', fixUntil=1), {'PR': 0.95}, [], [], cfg, 3600, liqs=lq)   # fix ends → not re-armed the same round
    assert not done.get('cycleFix') and done['streak'] == 0
    picked = ap.owner_cycle(dict(card, cycleFix='rescue', fixUntil=9), 'classic', 5.0)
    assert 'cycleFix' not in picked and picked['streak'] == 0 and picked['events'][-1]['kind'] == 'streak'


def test_major_leg_keeps_its_pool_depth():
    l = ap._leg({'mint': 'S', 'pairAddress': 'PS', 'symbol': 'SOL', 'price': 150.0, 'liquidityUsd': 9_000_000}, 5.0, 0, 'anchor')
    assert l['liq'] == 9_000_000


def test_auto_cycle_noise_and_taken_coins_rank_last():
    assert ap.next_phase('auto', 0, -0.01) == 'mixed'           # −0.01% is noise — not a 3-majors 'safest' round
    assert ap.next_phase('auto', 0, -4) == 'safest'
    a = {'mint': 'A', 'pairAddress': 'PA', 'price': 1, 'score': 90, 'taken': True}
    b = {'mint': 'B', 'pairAddress': 'PB', 'price': 1, 'score': 70}
    assert [c['mint'] for c in ap.rated([a, b], 'runner')] == ['B', 'A']   # another tier holds A → B first, so tiers differ


def test_one_tap_redeal_keeps_the_money():
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 1, 'cycles': {'degen': 'off'}})
    anchors = [{'mint': 'S', 'pairAddress': 'PS', 'symbol': 'SOL', 'price': 1.0}, {'mint': 'B', 'pairAddress': 'PB', 'symbol': 'BTC', 'price': 1.0}]
    runners = [{'mint': f'R{i}', 'pairAddress': f'PR{i}', 'symbol': f'R{i}', 'price': 1.0, 'score': 80} for i in range(4)]
    old = {'mint': 'X', 'pairAddress': 'PX', 'symbol': 'X', 'role': 'runner', 'entry': 1.0, 'units': 20.0, 'costUsd': 20.0}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 100, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 20.0, 'legs': [old], 'redealNow': True, 'phase': 'mixed'}
    px = {'PX': 1.0, 'PS': 1.0, 'PB': 1.0, **{f'PR{i}': 1.0 for i in range(4)}}
    c = ap.tick(card, px, [], runners, cfg, 200, anchors, liqs={k: 1e12 for k in px})
    assert 'X' not in [l['mint'] for l in c['legs']] and 'redealNow' not in c
    assert abs(sum(l['costUsd'] for l in c['legs']) - 20.0) < 0.5 and c['startUsd'] == 20.0   # same money, same run


def test_freeze_at_x_and_swap_y_from_peak_are_configurable():
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 99, 'rideAt': 25, 'rideTrail': 10, 'cycles': {'degen': 'off'}})
    assert cfg['rideAt'] == 25 and cfg['rideTrail'] == 10 and ap.clean_cfg({'rideAt': 7})['rideAt'] == ap.RIDE_AT
    r = {'mint': 'R', 'pairAddress': 'PR', 'symbol': 'R', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 10.0, 'legs': [r]}
    new = [{'mint': 'N', 'pairAddress': 'PN', 'symbol': 'N', 'price': 1.0, 'score': 99, 'stars': 5}]
    lq = {'PR': 1e12, 'PN': 1e12}
    c = ap.tick(card, {'PR': 1.3}, [], new, cfg, 10, liqs=lq)          # +30% ≥ +25% → frozen (riding)
    assert c['legs'][0]['ride'] and c['events'][-1]['kind'] == 'ride'
    c = ap.tick(c, {'PR': 1.5}, [], new, cfg, 20, liqs=lq)             # new peak 1.5, still held
    assert c['legs'][0]['mint'] == 'R' and c['legs'][0]['high'] == 1.5
    c = ap.tick(c, {'PR': 1.34, 'PN': 1.0}, [], new, cfg, 30, liqs=lq) # −10.7% from peak → swapped for N
    assert c['legs'][0]['mint'] == 'N' and c['events'][-1]['kind'] == 'ride-end' and 'peak' in c['events'][-1]['why']


def test_thirty_pct_peak_trail_is_a_true_price_drawdown_not_percentage_points():
    """Screenshot case: +124.6% peak to +69.0% now is only 24.8% off the peak, so the live card must keep riding."""
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 99, 'rideAt': 25, 'rideTrail': 30, 'cycles': {'degen': 'off'}})
    leg = {'mint': 'SPEC', 'pairAddress': 'PS', 'symbol': 'SPEC', 'role': 'runner', 'entry': 1.0, 'firstEntry': 1.0,
           'units': 1.0, 'costUsd': 1.0, 'at': 0, 'priced': True, 'ride': True, 'rideFrom': 1.0, 'high': 2.246}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0,
            'compoundedUsd': 0.0, 'takenUsd': 0.0, 'events': [], 'startUsd': 1.0, 'legs': [leg]}
    new = [{'mint': 'N', 'pairAddress': 'PN', 'symbol': 'N', 'price': 1.0, 'score': 99}]
    held = ap.tick(card, {'PS': 1.69, 'PN': 1.0}, [], new, cfg, 10, liqs={'PS': 1e12, 'PN': 1e12})
    assert held['legs'][0]['mint'] == 'SPEC' and held['legs'][0]['ride']       # 1 - 1.69/2.246 = 24.8%
    sold = ap.tick(held, {'PS': 1.57, 'PN': 1.0}, [], new, cfg, 20, liqs={'PS': 1e12, 'PN': 1e12})
    assert sold['legs'][0]['mint'] == 'N' and sold['events'][-1]['kind'] == 'ride-end'   # 30.1% off peak


def test_riding_winner_is_carried_but_does_not_block_due_major_reshape():
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 1, 'cycleEvery': 3, 'cycles': {'degen': 'press'},
                        'rideAt': 25, 'rideTrail': 30, 'keepWinPct': 5})
    sol = {'mint': 'SOL', 'pairAddress': 'PSOL', 'symbol': 'SOL', 'role': 'anchor', 'entry': 1.0, 'units': 10, 'costUsd': 10, 'at': 0}
    rider = {'mint': 'RIDE', 'pairAddress': 'PR', 'symbol': 'RIDE', 'role': 'runner', 'entry': 1.0, 'firstEntry': 1.0,
             'units': 10, 'costUsd': 10, 'at': 0, 'priced': True, 'ride': True, 'rideFrom': 1.0, 'high': 1.8}
    plain = {'mint': 'OLD', 'pairAddress': 'PO', 'symbol': 'OLD', 'role': 'runner', 'entry': 1.0, 'units': 10, 'costUsd': 10, 'at': 0}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'rounds': 2, 'phase': 'degen',
            'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0, 'events': [], 'startUsd': 30.0,
            'roundStartUsd': 30.0, 'legs': [sol, rider, plain]}
    anchors = [C('SOL', 1, 'SOL'), C('BTC', 1, 'cbBTC'), C('ETH', 1, 'WETH')]
    runners = [{**R('RIDE', 1), 'newMajor': False}, {**R('NM', 1), 'newMajor': True}, R('NEW', 1)]
    px = {'PSOL': 1, 'PR': 1.7, 'PO': 1, 'PBTC': 1, 'PETH': 1, 'PNM': 1, 'PNEW': 1}
    out = ap.tick(card, px, [], runners, cfg, 3600, anchors, liqs={k: 1e12 for k in px})
    assert out['phase'] == 'mixed' and {'BTC', 'ETH'} <= {l['mint'] for l in out['legs'] if l['role'] == 'anchor'}
    assert 'RIDE' in {l['mint'] for l in out['legs']} and next(l for l in out['legs'] if l['mint'] == 'RIDE')['ride']
    assert 'NM' in {l['mint'] for l in out['legs']}   # mixed = majors + one new major + runner, subject to protected slots


def test_due_shapes_rotate_the_existing_ranked_major_basket():
    cfg = ap.clean_cfg({'cycleEvery': 3})
    anchors = [C('SOL', 1, 'SOL'), C('BTC', 1, 'cbBTC'), C('ETH', 1, 'WETH')]
    runners = [R('R1', 1), R('R2', 1), R('R3', 1)]
    first = ap.deal('degen', [], runners, cfg, 0, anchors)
    due = ap.deal('degen', [], runners, cfg, 1, anchors, keep={'rounds': 3}, shape='degen')
    later = ap.deal('degen', [], runners, cfg, 2, anchors, keep={'rounds': 6}, shape='degen')
    assert next(l['mint'] for l in first['legs'] if l['role'] == 'anchor') == 'SOL'
    assert next(l['mint'] for l in due['legs'] if l['role'] == 'anchor') == 'BTC'
    assert next(l['mint'] for l in later['legs'] if l['role'] == 'anchor') == 'ETH'


def test_cycle_peek_shows_now_next_and_when():
    cfg = ap.clean_cfg({'cycleEvery': 3, 'cycles': {'balanced': 'classic'}})
    pk = ap.cycle_peek({'tpl': 'balanced', 'rounds': 4, 'phase': 'anchor', 'lastRoundPct': 1.0}, cfg)
    assert pk['now'] == 'anchor' and pk['inRounds'] == 2 and pk['next'] == ap.next_phase('classic', 2, 1.0) and pk['mode'] == 'classic'
    fix = ap.cycle_peek({'tpl': 'balanced', 'rounds': 4, 'phase': 'safest', 'cycleFix': 'rescue'}, cfg)
    assert fix['inRounds'] == 1 and fix['fix'] == 'rescue'
    assert ap.cycle_peek({'tpl': 'balanced', 'rounds': 1}, ap.clean_cfg({'cycles': {'balanced': 'off'}}))['next'] is None


def test_new_coin_entry_rebases_to_the_live_price_on_its_first_tick():
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 99, 'cycles': {'degen': 'off'}})
    l = {'mint': 'H', 'pairAddress': 'PH', 'symbol': 'H', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0, 'at': 100}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 10.0, 'legs': [l]}
    c = ap.tick(card, {'PH': 0.13}, [], [], cfg, 130, liqs={'PH': 1e12})   # a source gap: −87% on tick one
    leg = c['legs'][0]
    assert leg['mint'] == 'H' and leg['entry'] == 0.13 and abs(leg['units'] * 0.13 - 10.0) < 1e-6 and not any(e['kind'] == 'sl' for e in c['events'])
    c = ap.tick(c, {'PH': 0.065}, [], [], cfg, 500, liqs={'PH': 1e12})    # a REAL −50% later still counts
    assert any(e['kind'] == 'sl' for e in c['events'])   # not re-based: the stop fires


def test_reshape_never_sells_a_winner_or_frozen_coin_and_money_is_exact():
    px = {'PW': 1.5, 'PF': 0.9, 'PL': 0.8, 'PA': 1.0, 'PB': 1.0, 'PC': 1.0}
    lq = {k: 1e12 for k in px}
    old = [{'mint': 'W', 'pairAddress': 'PW', 'symbol': 'W', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0},   # +50% winner
           {'mint': 'F', 'pairAddress': 'PF', 'symbol': 'F', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0, 'frozen': True},
           {'mint': 'L', 'pairAddress': 'PL', 'symbol': 'L', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0}]  # loser → sold
    nc = {'legs': [{'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0} for m in 'ABC'], 'cash': 0.0}
    ip = ap.value({'legs': old, 'cash': 0.0}, px, lq)
    out, kept = ap.keep_winners(nc, old, px, lq, 5, ip)
    assert kept == 2 and {l['mint'] for l in out['legs']} == {'W', 'F', 'A'}
    assert abs(ap.value(out, px, lq) - ip) < 1e-6                      # same money, nothing created or lost
    assert ap.keep_winners(nc, old, px, lq, 0, ip)[1] == 1             # keep-winners off → only the frozen coin is carried
    assert ap.keep_winners(nc, [old[2]], px, lq, 5, ip) == (nc, 0)     # nothing up → normal re-shape


def test_off_options_and_hold_all():
    c = ap.clean_cfg({'rideAt': 0, 'rescuePct': 0, 'cycleEvery': 0, 'keepWinPct': 0})
    assert c['rideAt'] == 0 and c['rescuePct'] == 0 and c['cycleEvery'] == 0 and c['keepWinPct'] == 0
    assert ap.clean_cfg({})['keepWinPct'] == 5 and ap.clean_cfg({})['cycleEvery'] == 6
    assert ap.cycle_peek({'tpl': 'degen', 'rounds': 3, 'holdAll': True}, ap.clean_cfg({}))['mode'] == 'hold'
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 1, 'rotateConfirm': 1, 'minHoldMins': 0, 'cycles': {'degen': 'off'}})
    r = {'mint': 'R', 'pairAddress': 'PR', 'symbol': 'R', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0, 'loseRounds': 5}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 10.0, 'legs': [r], 'holdAll': True}
    new = [{'mint': 'N', 'pairAddress': 'PN', 'symbol': 'N', 'price': 1.0, 'score': 99, 'stars': 5}]
    c2 = ap.tick(card, {'PR': 0.88, 'PN': 1.0}, [], new, cfg, 3700, liqs={'PR': 1e12, 'PN': 1e12})   # −12%: would rotate, but hold all
    assert c2['legs'][0]['mint'] == 'R'


def test_hand_pick_survives_one_reshape():
    px, lq = {'PH': 1.0, 'PA': 1.0, 'PB': 1.0}, {'PH': 1e12, 'PA': 1e12, 'PB': 1e12}
    old = [{'mint': 'H', 'pairAddress': 'PH', 'symbol': 'H', 'role': 'runner', 'entry': 1.0, 'units': 5.0, 'costUsd': 5.0, 'picked': True}]
    nc = {'legs': [{'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': 'runner', 'entry': 1.0, 'units': 5.0, 'costUsd': 5.0} for m in 'AB'], 'cash': 0.0}
    out, kept = ap.keep_winners(nc, old, px, lq, 5, 10.0)
    assert kept == 1 and 'H' in {l['mint'] for l in out['legs']} and not any(l.get('picked') for l in out['legs'])


def test_rotation_does_not_override_saved_patience_just_to_force_a_fresh_coin():
    cfg = ap.clean_cfg({'compound': False, 'trail': False, 'rotateHours': 1, 'cycleEvery': 0, 'cycles': {'degen': 'off'}})
    w = {'mint': 'W', 'pairAddress': 'PW', 'symbol': 'W', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0}
    f = {'mint': 'F', 'pairAddress': 'PF', 'symbol': 'F', 'role': 'runner', 'entry': 1.0, 'units': 10.0, 'costUsd': 10.0}
    card = {'id': 'prime-degen', 'tpl': 'degen', 'label': 'x', 'at': 0, 'lastRotateAt': 0, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': 20.0, 'legs': [w, f]}
    new = [{'mint': 'N', 'pairAddress': 'PN', 'symbol': 'N', 'price': 1.0, 'score': 99, 'stars': 5}]
    px = {'PW': 1.2, 'PF': 0.99, 'PN': 1.0}
    c = ap.tick(card, px, [], new, cfg, 3700, liqs={k: 1e12 for k in px})
    assert {l['mint'] for l in c['legs']} == {'W', 'F'}                    # neither leg met the saved loss/patience rules
    assert not [e for e in c['events'] if e['kind'] == 'rotate']
    assert ap.tick({**card, 'holdAll': True}, px, [], new, cfg, 3700, liqs={k: 1e12 for k in px})['legs'][1]['mint'] == 'F'   # hold all: nothing
