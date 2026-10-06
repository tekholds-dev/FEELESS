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
CFG = ap.clean_cfg({'lockBankPct': 0, 'peakSellPct': 100, 'floorPct': 20, 'rotateMinDrop': 0, 'cycleEvery': 1, 'rotateConfirm': 1, 'minHoldMins': 0, 'cycles': {'safe': 'off', 'balanced': 'off', 'degen': 'classic', 'next': 'classic', 'ever': 'off'},   # the original tier behaviour
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
    assert {'gold', 'blaze', 'ever'} <= {c['tier'] for c in v['cards']} and all(19.8 < c['valueUsd'] <= 20 for c in v['cards'])   # true fills on the $20 paper size
    class Rq:
        async def json(self): return {'cfg': {'rotateHours': 3, 'on': False}}
    out = asyncio.run(rs.fuse_prime_admin(Rq()))
    assert out['cfg']['rotateHours'] == 3 and out['cfg']['on'] is False and asyncio.run(rs._prime_tick(2000)) == 0


def test_cmd_ctr_replaces_one_coin_with_best_same_role():
    card = ap.deal('balanced', [P('a', 1), P('b', 1)], [R('r1', 1), R('r2', 1)], CFG, 0, SOL[:1])
    out = ap.replace_leg(card, 'Pr1', {'Pr1': 2}, [P('a', 1)], [R('r1', 1), R('r9', 1)], SOL, CFG, 10)
    mints = [l['mint'] for l in out['legs']]
    assert 'r9' in mints and 'r1' not in mints and abs(next(l for l in out['legs'] if l['mint'] == 'r9')['costUsd'] - card['legs'][-1]['units'] * 2) < 1e-6
    assert out['events'][-1]['why'] == '⇄ swapped by hand'
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


def test_payout_percentage_applies_to_realized_profit_never_principal():
    cfg = ap.clean_cfg({'payouts': {'degen': 100}, 'compoundStyle': 'smart', 'cycles': {'degen': 'off'}})
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1), R('r2', 1)], cfg, 0, SOL[:1])  # $25 cost per leg
    px = {'Psol': 1, 'Pa': 1, 'Pr1': 2.2, 'Pr2': 1}
    out = ap.tick(card, px, [], [], cfg, 30, SOL)
    sold = [e for e in out['events'] if e['kind'] == 'payout'][-1]
    # TP sells ~$30 of R1, but part of those proceeds is principal. Even at 100% payout only realized profit leaves the card.
    assert 0 < sold['usd'] < 30
    assert out['walletUsd'] == pytest.approx(sold['usd'], abs=1e-4)
    assert out['compoundedUsd'] > 0
    assert abs(ap.value(out, px) - ap.value(card, px)) < 0.1


def test_compound_off_keeps_sold_principal_and_unpaid_profit_as_card_cash():
    cfg = ap.clean_cfg({'payouts': {'degen': 50}, 'compound': False, 'cycles': {'degen': 'off'}})
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1), R('r2', 1)], cfg, 0, SOL[:1])
    out = ap.tick(card, {'Psol': 1, 'Pa': 1, 'Pr1': 2.2, 'Pr2': 1}, [], [], cfg, 30, SOL)
    assert out['walletUsd'] > 0 and out['cash'] > out['walletUsd']
    assert abs(ap.value(out, {'Psol': 1, 'Pa': 1, 'Pr1': 2.2, 'Pr2': 1}) - 130) < 0.1


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
    cfg = ap.clean_cfg({'lockBankPct': 0, 'peakSellPct': 100, 'compound': False, 'trail': False, 'cycles': {'degen': 'off'}})
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
    # 🛟 Rescue OFF = no fix at all: the same −42% day keeps the owner's coins and config (only the coin floor protects it)
    off = ap.clean_cfg({'compound': False, 'trail': False, 'floorPct': 60, 'rescuePct': 0, 'cycles': {'degen': 'press'}})
    c2 = ap.tick({**card, 'legs': [dict(l) for l in legs], 'events': []}, {'PR': 0.15, 'PS': 1.0, 'PB': 1.0, 'PE': 1.0}, [], [], off, 10, anchors, liqs={'PR': 1e12, 'PS': 1e12, 'PB': 1e12, 'PE': 1e12})
    assert not c2.get('cycleFix') and not any(e['kind'] == 'fix' for e in c2['events']) and {l['mint'] for l in c2['legs']} == {'R', 'S'}


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
    cfg = ap.clean_cfg({'lockBankPct': 0, 'peakSellPct': 100, 'compound': False, 'trail': False, 'rotateHours': 99, 'rideAt': 25, 'rideTrail': 10, 'cycles': {'degen': 'off'}})
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
    cfg = ap.clean_cfg({'peakSellPct': 100, 'compound': False, 'trail': False, 'rotateHours': 99, 'rideAt': 25, 'rideTrail': 30, 'cycles': {'degen': 'off'}})
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


def test_reshape_carries_a_coin_dealt_again_instead_of_selling_and_rebuying_it():
    import arena_prime as ap
    old = [{'mint': 'A', 'pairAddress': 'pa', 'symbol': 'A', 'role': 'runner', 'entry': 1.0, 'units': 2.0, 'costUsd': 2.0, 'at': 0},
           {'mint': 'B', 'pairAddress': 'pb', 'symbol': 'B', 'role': 'runner', 'entry': 1.0, 'units': 2.0, 'costUsd': 2.0, 'at': 0}]
    nc = {'legs': [{'mint': 'A', 'pairAddress': 'pa', 'role': 'runner', 'entry': 1.0, 'units': 1.9, 'costUsd': 2.0},
                   {'mint': 'C', 'pairAddress': 'pc', 'role': 'runner', 'entry': 1.0, 'units': 2.0, 'costUsd': 2.0}]}
    out, kept = ap.keep_winners(nc, old, {'pa': 0.97, 'pb': 0.97, 'pc': 1.0}, {}, 5.0, 3.94)
    a = next(l for l in out['legs'] if l['mint'] == 'A')
    assert kept == 1 and a['units'] == 1.9 and a['entry'] == 1.0          # same entry, only trimmed to its new slot (never sold whole + rebought)
    assert {l['mint'] for l in out['legs']} == {'A', 'C'}
    assert abs(sum(l['costUsd'] for l in out['legs'] if l['mint'] == 'C') - (3.94 - 1.9 * 0.97)) < 1e-6   # money stays exact


def test_dropped_coins_cool_down_then_come_back():
    import arena_prime as ap
    before = {'legs': [{'mint': 'A', 'role': 'runner'}, {'mint': 'S', 'role': 'anchor'}]}
    after = ap.note_dropped(before, {'legs': [{'mint': 'B', 'role': 'runner'}, {'mint': 'S', 'role': 'anchor'}]}, 1000.0, 5 / 60)
    assert ap.cooling({**after, 'rounds': 3}, 1000.0 + 901, 5 / 60) == {'A'}   # left in round 0 → out for rounds 1–3, whatever the clock says
    assert ap.cooling({**after, 'rounds': 4}, 1000.0 + 901, 5 / 60) == set()   # back from round 4
    later = ap.note_dropped(after, {**after, 'rounds': 4}, 1000.0 + 2000, 5 / 60)
    assert 'A' not in later['cool']                                   # stale stamps are forgotten
    lost = ap.note_dropped({'legs': [{'mint': 'X', 'pairAddress': 'PX', 'role': 'runner', 'entry': 1.0}]}, {'legs': []}, 0.0, 5 / 60, {'PX': 0.7})
    assert ap.cooling(lost, 5000.0, 5 / 60, {'PX': 0.6}) == {'X'}      # 🩸 sold at a loss and still falling → stays out
    assert ap.cooling(lost, 5000.0, 5 / 60, {'PX': 0.75}) == set()     # back above its exit → may return
    assert ap.cooling(lost, 90000.0, 5 / 60, {'PX': 0.1}) == set()     # max 24h


def test_real_card_config_is_separate_from_hq_paper_config(monkeypatch):
    import reputation_service as rs
    pr = {'cfg': {'rotateHours': 0.08, 'rotateConfirm': 1}, 'realCfg': {'rotateHours': 0.08, 'rotateConfirm': 3, 'minHoldMins': 10}}
    monkeypatch.setattr(rs, '_prime_cfg', lambda: {**ap.clean_cfg(pr['cfg']), 'paperFeeUsd': 0.02})
    r = rs._prime_real_cfg(pr)
    assert r['rotateHours'] == 0.08 and r['rotateConfirm'] == 3 and r['minHoldMins'] == 10   # 5-min real rounds allowed; the real-money guard floors the hold at 10 min (2 rounds)
    pr['cfg']['rotateConfirm'] = 6                                                           # an HQ paper edit…
    assert rs._prime_real_cfg(pr)['rotateConfirm'] == 3                                      # …never reaches the real card
    assert rs._prime_real_cfg({'cfg': pr['cfg']})['paperFeeUsd'] == 0.02                     # unset → starts from paper


def test_real_card_never_bypasses_stop_cooldown_when_candidates_are_thin():
    import reputation_service as rs
    rows = [{'mint': 'STOPPED'}, {'mint': 'FRESH'}]
    assert rs._prime_cool_candidates(rows, {'STOPPED'}, 3, strict=True) == [{'mint': 'FRESH'}]
    assert rs._prime_cool_candidates(rows, {'STOPPED'}, 3, strict=False) == rows  # paper preserves historical sparse-pool fallback


def test_keep_winners_never_changes_a_four_slot_shape_to_three_or_five():
    now = 1000.0
    prices = {'p1': 1.0, 'p2': 1.2, 'p3': 1.0, 'p4': 1.0, 'p5': 1.0}
    old = [
        {'mint':'m1','pairAddress':'p1','symbol':'A','role':'anchor','units':1,'costUsd':1,'entry':1},
        {'mint':'m2','pairAddress':'p2','symbol':'WIN','role':'runner','units':1,'costUsd':1,'entry':1,'frozen':True},
        {'mint':'m3','pairAddress':'p3','symbol':'OLD','role':'runner','units':1,'costUsd':1,'entry':1},
        {'mint':'m4','pairAddress':'p4','symbol':'OLD2','role':'runner','units':1,'costUsd':1,'entry':1},
    ]
    nc = {'legs': [
        {'mint':'m1','pairAddress':'p1','symbol':'A','role':'anchor','units':1,'costUsd':1,'entry':1},
        {'mint':'m3','pairAddress':'p3','symbol':'OLD','role':'runner','units':1,'costUsd':1,'entry':1},
        {'mint':'m4','pairAddress':'p4','symbol':'OLD2','role':'runner','units':1,'costUsd':1,'entry':1},
        {'mint':'m5','pairAddress':'p5','symbol':'NEW','role':'runner','units':1,'costUsd':1,'entry':1},
    ], 'cash':0}
    out, kept = ap.keep_winners(nc, old, prices, {}, 10, 4.2)
    assert out is not None and kept >= 1
    assert len(out['legs']) == 4
    assert 'm2' in {l['mint'] for l in out['legs']}


def test_replace_mode_keeps_slot_when_feed_temporarily_has_no_candidate_then_heals_it():
    now = 1000.0
    cfg = {**ap.DEFAULT_CFG, 'slMode':'replace', 'compound':False}
    card = ap.deal('safe',
        [{'mint':'a','pairAddress':'pa','symbol':'A','price':1,'liquidityUsd':1000000,'stars':5}],
        [{'mint':'r','pairAddress':'pr','symbol':'R','price':1,'liquidityUsd':1000000,'stars':5}],
        cfg, now, anchors=[{'mint':'a','pairAddress':'pa','symbol':'A','price':1,'liquidityUsd':1000000,'stars':5}], usd=6)
    # Build a deterministic four-slot live shape: anchor + stopped runner + two protected runners.
    base = {'entry':1.0,'firstEntry':1.0,'units':1.0,'costUsd':1.0,'at':now-1000,'stars':5,'liq':1000000}
    card['legs'] = [
        {**base,'mint':'a','pairAddress':'pa','symbol':'A','role':'anchor'},
        {**base,'mint':'r1','pairAddress':'p1','symbol':'R1','role':'runner'},
        {**base,'mint':'r2','pairAddress':'p2','symbol':'R2','role':'runner','frozen':True},
        {**base,'mint':'r3','pairAddress':'p3','symbol':'R3','role':'runner','frozen':True},
    ]
    card['cash']=0.0; card['startUsd']=4.0; card['roundStartUsd']=4.0
    prices={'pa':1,'p1':0.1,'p2':1,'p3':1}
    out=ap.tick(card,prices,[],[],cfg,now,anchors=[{'mint':'a','pairAddress':'pa','symbol':'A','price':1,'liquidityUsd':1000000,'stars':5}],liqs={'p1':1000000})
    assert len(out['legs']) == 4
    assert any(l.get('placeholder') for l in out['legs'])
    assert out['cash'] > 0
    candidate={'mint':'r4','pairAddress':'p4','symbol':'R4','price':1,'liquidityUsd':1000000,'score':90}
    healed=ap.tick(out,{**prices,'p4':1},[],[candidate],cfg,now+1,anchors=[{'mint':'a','pairAddress':'pa','symbol':'A','price':1,'liquidityUsd':1000000,'stars':5}])
    assert len(healed['legs']) == 4
    assert 'r4' in {l['mint'] for l in healed['legs']}
    assert not any(l.get('placeholder') for l in healed['legs'])


def test_phase_deal_never_commits_partial_four_slot_shape():
    cfg={**CFG,'cycleEvery':6}
    anchors=[C('sol',1,'SOL')]
    only_two=[R('r1',1),R('r2',1)]
    assert ap.deal('safe',[],only_two,cfg,100,anchors,usd=6,shape='degen') is None
    full=ap.deal('safe',[],only_two+[R('r3',1)],cfg,100,anchors,usd=6,shape='degen')
    assert full is not None and len(full['legs']) == 4


def test_legacy_three_leg_degen_self_heals_to_four_without_topup():
    cfg={**CFG,'cycleEvery':6,'cycles':{**CFG['cycles'],'safe':'press'},'keepWinPct':5}
    now=1000.0
    base={'entry':1.0,'firstEntry':1.0,'units':1.0,'costUsd':1.0,'at':0,'stars':5,'liq':1000000}
    card={'id':'prime-safe','tpl':'safe','label':'Prime Diamond','at':0,'lastRotateAt':900,'cash':0.0,'feesUsd':0.0,'compoundedUsd':0.0,'takenUsd':0.0,
          'events':[],'startUsd':3.0,'dayAt':0,'dayStartUsd':3.0,'days':[],'lowPct':0.0,'rounds':6,'roundStartUsd':3.0,'phase':'degen',
          'legs':[{**base,'mint':'sol','pairAddress':'Psol','symbol':'SOL','role':'anchor'},
                  {**base,'mint':'r1','pairAddress':'Pr1','symbol':'R1','role':'runner'},
                  {**base,'mint':'r2','pairAddress':'Pr2','symbol':'R2','role':'runner'}]}
    out=ap.tick(card,{'Psol':1,'Pr1':1,'Pr2':1,'Pr3':1,'Pr4':1,'Pr5':1},[],[R('r3',1),R('r4',1),R('r5',1)],cfg,now,[C('sol',1,'SOL')])
    assert len(out['legs']) == 4
    assert out['phase'] == 'degen'


def test_real_guard_floors_a_churny_real_config_but_keeps_the_5_min_clock():
    churn = {'rotateHours': 0.08, 'minHoldMins': 0, 'rotateConfirm': 1, 'instantSwapPct': 5, 'cycleEvery': 1}
    out, changed = ap.real_guard(churn)
    assert out['rotateHours'] == 0.08                                    # the clock is the owner's — never touched
    assert out['minHoldMins'] == ap.REAL_MIN_HOLD and out['rotateConfirm'] == ap.REAL_MIN_CONFIRM
    assert out['instantSwapPct'] == ap.REAL_MIN_INSTANT and out['cycleEvery'] == ap.REAL_MAX_RESHAPE
    assert len(changed) == 4 and out['fixEvery'] == ap.REAL_MAX_RESHAPE and 'floorRestMins' not in out   # resting is the owner's switch, never forced
    # off stays off, never stays never, a patient config is left alone, slow clocks keep their own hold time
    calm = {'rotateHours': 1.0, 'minHoldMins': 0, 'rotateConfirm': 4, 'instantSwapPct': 0, 'cycleEvery': 0}
    assert ap.real_guard(calm) == ({**calm, 'fixEvery': 6, 'dealLeadSec': 15.0, 'minCoinUsd': 0.75}, [])


def test_runner_weather_reads_the_freshest_sim_window_and_limits_real_runner_buys():
    assert ap.weather({})['level'] == 'clear'                                              # no sims yet = nothing to judge
    assert ap.weather({'s24': {'n': 200, 'avgPct': -36.5}})['level'] == 'storm'
    assert ap.weather({'s24': {'n': 200, 'avgPct': -36.5}, 's6': {'n': 100, 'avgPct': -8.1}})['level'] == 'rain'   # 6h is fresher
    assert ap.weather({'s24': {'n': 200, 'avgPct': -36.5}, 's6': {'n': 100, 'avgPct': 2.0}})['level'] == 'clear'
    rows = [{'mint': 'a', 'score': 80, 'liq': 90_000, 'ageH': 20}, {'mint': 'b', 'score': 80, 'liq': 30_000, 'ageH': 20}, {'mint': 'c', 'score': 40, 'liq': 500_000, 'ageH': 20},
            {'mint': 'm', 'newMajor': True, 'score': 60, 'liq': 300_000}, {'mint': 'baby', 'score': 99, 'liq': 534_000, 'ageH': 0.3}, {'mint': 'unknown', 'score': 99, 'liq': 534_000}]
    lq = lambda x: x['liq']
    assert [x['mint'] for x in ap.weather_runners(rows, 'clear', 80_000, lq)] == ['a', 'b', 'c', 'm']
    assert [x['mint'] for x in ap.weather_runners(rows, 'rain', 80_000, lq)] == ['a', 'm']   # strong AND deep, or a new major
    assert [x['mint'] for x in ap.weather_runners(rows, 'storm', 80_000, lq)] == ['m']


def test_a_real_card_under_a_fix_does_not_reshape_every_round_and_rests_after_a_floor():
    paper = ap.cycle_peek({'tpl': 'safe', 'cycleFix': 'safe', 'rounds': 7, 'phase': 'anchor'}, {'cycleEvery': 6})
    real = ap.cycle_peek({'tpl': 'safe', 'cycleFix': 'safe', 'rounds': 7, 'phase': 'anchor'}, ap.real_guard({'cycleEvery': 6, 'rotateHours': 0.08})[0])
    assert paper['inRounds'] == 1 and real['inRounds'] == 5      # paper re-shapes next round · real waits for round 12


def test_resting_after_a_floor_is_the_owners_switch_and_off_by_default():
    assert ap.clean_cfg({})['floorRestMins'] == 0.0 and ap.clean_cfg({'floorRestMins': 30})['floorRestMins'] == 30.0 and ap.clean_cfg({'floorRestMins': 7})['floorRestMins'] == 0.0
    card = {'id': 'prime-safe', 'label': 'x', 'at': 0, 'tpl': 'safe', 'startUsd': 10, 'legs': [], 'flooredAt': 1000.0, 'lastRotateAt': 900.0, 'cash': 0, 'compoundedUsd': 0, 'takenUsd': 0, 'feesUsd': 0, 'events': []}
    off = ap.summary(card, {}, ap.clean_cfg({}))
    on = ap.summary(card, {}, ap.clean_cfg({'floorRestMins': 30}))
    assert off['resting'] is False and off['nextRoundAt'] == 1060.0      # no rest set → re-deal on the next tick
    assert on['resting'] is True and on['nextRoundAt'] == 1000.0 + 1800


def test_anchors_cool_like_every_coin_and_rescue_off_ends_a_running_fix():
    before = {'legs': [{'mint': 'btc', 'symbol': 'cbBTC', 'role': 'anchor', 'pairAddress': 'Pbtc', 'entry': 1.0}, {'mint': 'sol', 'symbol': 'SOL', 'role': 'anchor', 'pairAddress': 'Psol', 'entry': 1.0}]}
    after = ap.note_dropped(before, {'legs': []}, 1000.0, 0.08, {'Pbtc': 0.99})
    assert 'btc' in after['cool'] and 'sol' not in after['cool']          # a sold major sits out · SOL is the card's cash, never "dropped"
    assert 'btc' in ap.cooling(after, 1000.0 + 600, 0.08) and 'btc' not in ap.cooling({'cool': {'btc': {'at': 1000.0}}}, 1000.0 + 1200, 0.08)   # old stamps: (3 + 1) rounds of time


def test_small_real_cards_hold_fewer_bigger_coins_and_keep_their_character():
    assert [ap.size_slots(u, 0.75, 4) for u in (1, 1.6, 2.5, 5, 100)] == [1, 2, 3, 4, 4] and ap.size_slots(1, 0, 4) == 4
    picks = [('a1', 'anchor'), ('a2', 'anchor'), ('a3', 'anchor'), ('r1', 'runner')]
    assert ap.fit_size(picks, 1.7, 0.75) == [('a1', 'anchor'), ('r1', 'runner')]        # one anchor + the runner, never 2 majors only
    assert ap.fit_size(picks, 2.5, 0.75) == [('a1', 'anchor'), ('a2', 'anchor'), ('r1', 'runner')]
    assert ap.fit_size(picks, 50, 0.75) == picks and ap.fit_size(picks, 1.7, None) == picks


def test_a_coin_can_carry_its_own_take_profit_and_stop_and_zero_follows_the_tier_again():
    card = {'legs': [{'pairAddress': 'P1', 'symbol': 'A'}]}
    c = ap.set_leg(card, 'P1', tp=50, sl=15)
    assert c['legs'][0]['tp'] == 50 and c['legs'][0]['sl'] == 15 and 'tp' not in card['legs'][0]
    assert ap.leg_tp(c['legs'][0], {'tp': 300, 'sl': 35}) == 50 and ap.leg_sl(c['legs'][0], {'tp': 300, 'sl': 35}) == 15
    back = ap.set_leg(c, 'P1', tp=0)
    assert 'tp' not in back['legs'][0] and ap.leg_tp(back['legs'][0], {'tp': 300, 'sl': 35}) == 300 and back['legs'][0]['sl'] == 15
    with pytest.raises(ValueError):
        ap.set_leg(card, 'P1', sl=7)


def test_fast_clocks_rank_coins_by_what_is_moving_now_and_slow_clocks_keep_their_order():
    rows = [{'mint': 'deep', 'pairAddress': 'P1', 'vol1h': 2_000}, {'mint': 'hot', 'pairAddress': 'P2', 'vol1h': 400_000}, {'mint': 'mid', 'pairAddress': 'P3', 'vol1h': 40_000}]
    mom = {'P1': {'chg1h': -3}, 'P2': {'chg1h': 25}, 'P3': {'chg1h': 4}}
    assert [r['mint'] for r in ap.clock_rank(rows, 0.08, mom)] == ['hot', 'mid', 'deep']     # 5-min card
    assert [r['mint'] for r in ap.clock_rank(rows, 1.0, mom)] == ['deep', 'hot', 'mid']      # 1-hour card: untouched
    assert len(ap.clock_rank(rows, 0.08, mom)) == 3 and ap.clock_rank([], 0.08) == []


def test_the_owner_picks_how_many_coins_a_card_holds_at_any_size():
    assert ap.clean_cfg({'coins': 6})['coins'] == 6 and ap.clean_cfg({'coins': 9})['coins'] == 0 and ap.clean_cfg({})['coins'] == 0
    assert ap.real_guard({'coins': 6, 'rotateHours': 1})[0]['minCoinUsd'] == 0.0            # the owner's count beats the size rule
    assert ap.real_guard({'coins': 0, 'rotateHours': 1})[0]['minCoinUsd'] == ap.REAL_MIN_COIN_USD
    A = lambda m: ({'mint': m, 'price': 1.0, 'liquidityUsd': 5e6, 'volume24h': 5e6}, 'anchor')
    picks = [A('a1'), A('a2')]
    runners = [{'mint': 'r1', 'price': 1.0, 'score': 90}, {'mint': 'a1', 'price': 1.0, 'score': 90}, {'mint': 'r2', 'price': 1.0, 'score': 80}]
    grown = ap.grow_picks(picks, 4, [], runners, [])
    assert [c['mint'] for c, _ in grown] == ['a1', 'a2', 'r1', 'r2']                         # never the same coin twice
    assert len(ap.grow_picks(picks, 6, [], runners, [])) == 4                                # feeds ran out → what exists, no crash
    assert [c['mint'] for c, _ in ap.fit_count(grown, 2)] == ['a1', 'r1']                    # one anchor + one runner kept


def test_the_owner_picks_the_coin_that_comes_in_at_the_next_round():
    card = {'legs': [{'mint': 'a', 'pairAddress': 'Pa', 'symbol': 'AAA', 'role': 'runner', 'units': 10.0, 'entry': 1.0, 'costUsd': 10.0, 'liq': 1e9},
                     {'mint': 'b', 'pairAddress': 'Pb', 'symbol': 'BBB', 'role': 'pool', 'units': 5.0, 'entry': 1.0, 'costUsd': 5.0, 'liq': 1e9}], 'events': [], 'feesUsd': 0}
    pick = {'mint': 'n', 'pairAddress': 'Pn', 'symbol': 'NEW', 'price': 2.0, 'liquidityUsd': 1e9, 'division': 'yield'}
    q = ap.queue_swap(card, 'Pa', pick)
    assert q['legs'][0]['swapTo']['symbol'] == 'NEW' and 'swapTo' not in card['legs'][0]          # queued, nothing traded yet
    with pytest.raises(ValueError):
        ap.queue_swap(card, 'Pa', {**pick, 'mint': 'b'})                                           # already on the card
    with pytest.raises(ValueError):
        ap.queue_swap(q, 'Pb', pick)                                                               # one coin, one seat
    assert 'swapTo' not in ap.queue_swap(q, 'Pa', None)['legs'][0]                                 # cancel
    n = ap.apply_queued(q, {'Pa': 1.2, 'Pn': 2.0}, {}, 99.0)
    leg = q['legs'][0]
    assert n == 1 and leg['mint'] == 'n' and leg['picked'] and leg['division'] == 'yield' and leg['role'] == 'runner'
    # ⚖ the old coin was worth $12 of a $17 card (2 coins → an equal share is $8.50): the pick gets $8.50, the spare $3.50 waits in cash
    assert abs(leg['units'] * leg['entry'] - 8.5) < 0.01 and abs(q['cash'] - 3.5) < 0.01
    assert q['events'][-1]['to'] == ['NEW'] and q['legs'][1]['mint'] == 'b'
    # 🗑 a picked TRENCH coin keeps its trench flag through the queue, so the keeper buys it at the trench pool floor
    t = ap.queue_swap(card, 'Pb', {**pick, 'mint': 't', 'pairAddress': 'Pt', 'trenchOnly': True})
    ap.apply_queued(t, {'Pb': 1.0, 'Pt': 2.0}, {}, 99.0)
    assert t['legs'][1]['trench'] is True and 'trench' not in leg


def test_every_tier_plays_its_own_round_clock():
    cfg = ap.clean_cfg({'rotateHours': 0.25})
    clocks = [ap.tier_cfg(cfg, t)['rotateHours'] for t in ap.DEFAULT_CLOCKS]
    assert len(set(clocks)) == len(clocks) == 5 and ap.tier_cfg(cfg, 'degen')['rotateHours'] == 0.08          # five tiers, five clocks
    assert ap.tier_cfg(ap.clean_cfg({'clocks': {'degen': 1}}), 'degen')['rotateHours'] == 1.0                 # the owner's pick per tier
    assert ap.tier_cfg(cfg, 'nope')['rotateHours'] == 0.25 and cfg['rotateHours'] == 0.25                     # unknown tier → shared · input untouched


def test_fresh_card_dealt_with_an_amount_starts_at_that_amount():
    cfg = ap.clean_cfg({})
    anchors = [C('SOL', 1, 'SOL')]
    c = ap.deal('degen', [], [R('R1', 1), R('R2', 1)], cfg, 0, anchors, usd=10.0)
    assert c['startUsd'] == 10.0 and c['dayStartUsd'] == 10.0     # never the $100 default: that read −90% and tripped the floor
    assert ap.deal('degen', [], [R('R1', 1)], cfg, 0, anchors, usd=10.0, keep={'startUsd': 55.0})['startUsd'] == 55.0


def test_paper_pays_out_only_above_what_was_put_in_even_after_a_restart():
    cfg = ap.clean_cfg({'payouts': {'degen': 100}, 'compoundStyle': 'smart', 'cycles': {'degen': 'off'}})
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1), R('r2', 1)], cfg, 0, SOL[:1])
    assert card['putInUsd'] == 100.0
    # the card restarted after a fall: its run starts at $60, but $100 was PUT IN
    low = {**card, 'startUsd': 60.0, 'roundStartUsd': 60.0, 'legs': [{**l, 'units': l['units'] * 0.6, 'costUsd': l['costUsd'] * 0.6} for l in card['legs']]}
    px = {'Psol': 1, 'Pa': 1, 'Pr1': 2.2, 'Pr2': 1}                         # r1 doubles → the card is ~$76: up on the run, still under $100
    out = ap.tick(low, px, [], [], cfg, 30, SOL)
    assert not out.get('walletUsd') and not [e for e in out['events'] if e['kind'] == 'payout']
    assert ap.summary(out, px)['math']['putIn'] == 100.0                     # what was put in stays on screen
    # a restart keeps the put-in line
    again = ap.deal('degen', [P('a', 1)], [R('r1', 1)], cfg, 1, SOL[:1], usd=40.0, keep={'startUsd': 40.0, 'putInUsd': 100.0})
    assert again['putInUsd'] == 100.0 and ap.payout_line(again) == 100.0


def test_paid_out_money_never_counts_toward_the_line():
    cfg = ap.clean_cfg({'payouts': {'degen': 100}, 'compoundStyle': 'smart', 'cycles': {'degen': 'off'}})
    card = ap.deal('degen', [P('a', 1)], [R('r1', 1), R('r2', 1)], cfg, 0, SOL[:1])
    # $100 in · coins now worth less · $30 already paid out → in-card money is under $100: nothing more may leave
    worn = {**card, 'walletUsd': 30.0, 'legs': [{**l, 'units': l['units'] * 0.75} for l in card['legs']]}
    out = ap.tick(worn, {'Psol': 1, 'Pa': 1, 'Pr1': 2.2, 'Pr2': 1}, [], [], cfg, 30, SOL)
    assert out['walletUsd'] == 30.0


def test_every_tier_card_plays_its_own_unique_exits_and_a_shared_edit_applies_to_all():
    cfg = ap.clean_cfg({})
    own = {t: tuple(ap.tier_cfg(cfg, t)[k] for k in ('rideAt', 'rideTrail', 'rotateConfirm', 'minHoldMins')) for t in ap.TEMPLATES}
    assert len(set(own.values())) == len(ap.TEMPLATES)                                      # no two cards share their exits
    assert ap.tier_cfg(cfg, 'degen')['rideAt'] == 15 and ap.tier_cfg(cfg, 'degen')['rideTrail'] == 8
    c2 = ap.clean_cfg({**cfg, 'tierCfg': {**cfg['tierCfg'], 'degen': {**cfg['tierCfg']['degen'], 'rideAt': 10, 'tp': 50, 'bogus': 1, 'rideTrail': 7}}})
    d = ap.tier_cfg(c2, 'degen')
    assert d['rideAt'] == 10 and d['tp'] == 50 and 'bogus' not in c2['tierCfg']['degen'] and c2['tierCfg']['degen'].get('rideTrail') is None   # 7 isn't an option
    assert ap.card_template('degen', d)['tp'] == 50 and ap.card_template('degen', {})['tp'] == ap.TEMPLATES['degen']['tp']


def test_hq_per_card_exit_edit_and_a_shared_edit_never_flattens_the_cards(monkeypatch):
    import asyncio
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cfg': {}, 'cards': {}}})
    class Rq:
        def __init__(self, b): self.b = b
        async def json(self): return self.b
    asyncio.run(rs.fuse_prime_admin(Rq({'cfg': {'tierCfg': {'degen': {'rideAt': 20}}}})))
    cfg = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']['cfg']
    assert cfg['tierCfg']['degen']['rideAt'] == 20 and cfg['tierCfg']['next']['rideAt'] == 20 and cfg['tierCfg']['safe']['rideAt'] == 50   # only Blaze moved
    asyncio.run(rs.fuse_prime_admin(Rq({'cfg': {'rideAt': 25}})))                         # a shared edit never flattens the cards
    cfg = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']['cfg']
    assert ap.tier_cfg(cfg, 'degen')['rideAt'] == 20 and ap.tier_cfg(cfg, 'safe')['rideAt'] == 50


def test_all_cards_get_their_own_exits_back_and_the_real_card_is_never_touched(monkeypatch):
    import asyncio
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, '_require_owner', lambda r: 'OWNER'); monkeypatch.setattr(rs, '_require_admin', lambda r: 'ADMIN')
    real = {'rotateHours': 0.08, 'rotateConfirm': 2, 'minHoldMins': 10, 'rideAt': 15, 'rideTrail': 8, 'instantSwapPct': 15, 'rescuePct': 0, 'floorPct': 40}
    # the state "Add to all cards" left: every card's own keys cleared, shared TP 300 + trail 8 on every card
    flat = {t: {} for t in ap.TEMPLATES}
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cfg': {'tp': 300, 'rideTrail': 8, 'tierCfg': flat}, 'realCfg': real, 'realOwnerSet': sorted(real), 'cards': {}}})
    assert asyncio.run(rs._prime_unique_fix(0)) and not asyncio.run(rs._prime_unique_fix(1))       # once
    pr = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']
    sigs = {t: tuple(ap.tier_cfg(pr['cfg'], t)[k] for k in ap.TIER_KEYS) for t in ap.TEMPLATES}
    assert len(set(sigs.values())) == len(ap.TEMPLATES) and pr['cfg']['tp'] == 0                       # all unique again, TP back to 'tier'
    assert pr['realCfg'] == real                                                                         # 💵 Blaze real untouched
    r = rs._prime_real_cfg()
    assert (r['rotateConfirm'], r['minHoldMins'], r['rideAt'], r['rideTrail'], r['instantSwapPct']) == (2, 10, 15, 8, 15)
    with pytest.raises(rs.HTTPException):                                                                # no "all cards" action any more
        asyncio.run(rs.fuse_verdict_act(None, rs.VerdictActIn(area='🧠 Sim config', name='take-profit = 300', act='apply')))
    class Rq:
        async def json(self): return {'cfg': {'rideAt': 25, 'rotateConfirm': 1}}
    asyncio.run(rs.fuse_prime_admin(Rq()))                                                               # a shared edit can't flatten the cards
    pr2 = rs._json_load(rs.FUSE_HQ_PATH, {})['prime']
    assert {t: tuple(ap.tier_cfg(pr2['cfg'], t)[k] for k in ap.TIER_KEYS) for t in ap.TEMPLATES} == sigs and pr2['realCfg'] == real


def test_every_real_card_setting_reaches_the_engine(monkeypatch):
    rs = pytest.importorskip('reputation_service')
    real = {'rotateHours': 0.08, 'rotateConfirm': 2, 'minHoldMins': 10, 'rideAt': 15, 'rideTrail': 8, 'instantSwapPct': 15, 'rescuePct': 0,
            'floorPct': 40, 'floorRestMins': 0, 'tp': 300, 'sl': 30, 'slMode': 'replace', 'coins': 4}
    rs._json_save(rs.FUSE_HQ_PATH, {'prime': {'cfg': {}, 'realCfg': real, 'realOwnerSet': sorted(real), 'cards': {}}})
    e = rs._prime_real_cfg()
    for k, v in real.items():
        assert e[k] == v, k                                                          # nothing dropped or silently changed by the guard
    t = ap.card_template('degen', e)
    assert (t['tp'], t['sl']) == (300, 30) and ap.leg_tp({}, t) == 300 and ap.leg_tp({'tp': 50}, t) == 50   # a coin's own TP still wins


def test_a_coin_that_left_in_round_n_cannot_come_back_before_round_n_plus_4():
    before = {'rounds': 5, 'legs': [{'mint': 'HIGGS', 'pairAddress': 'PH', 'symbol': 'HIGGS', 'entry': 1.0}]}
    after = ap.note_dropped(before, {'rounds': 5, 'legs': []}, 1000.0, 5 / 60, {'PH': 0.9})
    assert after['cool']['HIGGS']['round'] == 5
    for r in (6, 7, 8):   # sold mid round 5 → out for rounds 6, 7 and 8, whatever the clock says
        assert 'HIGGS' in ap.cooling({**after, 'rounds': r}, 1000.0 + (r - 5) * 300 + 290, 5 / 60, {'PH': 2.0})
    assert 'HIGGS' not in ap.cooling({**after, 'rounds': 9}, 1000.0 + 4 * 300, 5 / 60, {'PH': 2.0})
    assert 'HIGGS' in ap.cooling({**after, 'rounds': 0}, 1100.0, 5 / 60, {'PH': 2.0})   # a restarted run falls back to the time window


def test_owner_can_switch_round_min_hold_off_on_real_money():
    cfg = {'rotateHours': 5 / 60, 'minHoldMins': 0, 'rotateConfirm': 3}
    assert ap.real_guard(cfg)[0]['minHoldMins'] == ap.REAL_MIN_HOLD                       # nobody chose it → floor applies
    out, changed = ap.real_guard(cfg, ['minHoldMins'])
    assert out['minHoldMins'] == 0 and not any('hold' in c for c in changed)             # the owner's OFF wins
    assert ap.real_guard({**cfg, 'minHoldMins': 5}, ['minHoldMins'])[0]['minHoldMins'] == ap.REAL_MIN_HOLD   # only OFF is honoured below the floor


def test_a_coin_that_went_in_tiny_is_topped_up_to_equal_weight_but_a_loser_is_never_averaged_down():
    legs = [{'mint': 'a', 'pairAddress': 'Pa', 'symbol': 'A', 'role': 'anchor', 'units': 2.0, 'entry': 1.0, 'costUsd': 2.0},
            {'mint': 'b', 'pairAddress': 'Pb', 'symbol': 'B', 'role': 'runner', 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0},
            {'mint': 'c', 'pairAddress': 'Pc', 'symbol': 'C', 'role': 'runner', 'units': 0.05, 'entry': 1.0, 'costUsd': 0.05},   # went in tiny
            {'mint': 'd', 'pairAddress': 'Pd', 'symbol': 'D', 'role': 'runner', 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0}]
    c = {'legs': [dict(l) for l in legs], 'cash': 0.2, 'events': [], 'feesUsd': 0.0}
    px = {'Pa': 1.0, 'Pb': 1.0, 'Pc': 1.0, 'Pd': 0.3}                                          # D lost 70% — it is NOT topped up
    ev = lambda **e: c['events'].append(e)
    ap.balance_small(c, px, {}, 0.0, 0.01, ev)
    by = {l['mint']: l for l in c['legs']}
    assert by['c']['units'] > 0.7 and by['d']['units'] == 1.0 and by['a']['units'] < 2.0 and c['cash'] == 0.0
    assert [e['symbol'] for e in c['events']] == ['C']
    again = len(c['events']); ap.balance_small(c, px, {}, 1.0, 0.01, ev)
    assert len(c['events']) == again                                                       # no churn once balanced


def test_a_coin_is_only_bought_when_its_two_prices_agree_and_a_fresh_gap_is_never_sold_as_a_loss():
    assert ap.price_agrees({'pairAddress': 'P', 'price': 1.0}, {'P': 1.05}) and not ap.price_agrees({'pairAddress': 'P', 'price': 1.0}, {'P': 0.13})
    assert ap.price_agrees({'pairAddress': 'P', 'price': 1.0}, {})                     # no live price yet → allowed
    assert ap.GAP_PCT == 50.0 and ap.GAP_SECS == 90.0


def test_cool_down_survives_a_re_deal_and_tells_the_owner_how_many_rounds_are_left():
    import arena_prime as ap
    leg = lambda m: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'entry': 1.0, 'role': 'runner'}
    c1 = {'rounds': 10, 'legs': [leg('A'), leg('B')]}
    c2 = ap.note_dropped(c1, {'rounds': 10, 'legs': [leg('B'), leg('C')]}, 1000, 0.08, {'PA': 0.8})        # A sold at a loss in round 10
    assert ap.cooling(c2, 1000, 0.08) == {'A'}
    fresh = {'rounds': 11, 'legs': [leg('D'), leg('E')]}                                                   # floor re-deal = a NEW card dict, no 'cool'
    c3 = ap.note_dropped(c2, fresh, 1300, 0.08, {})
    assert {'A', 'B', 'C'} <= ap.cooling(c3, 1300, 0.08)                                                   # A is still out, B and C just left
    assert ap.cool_left(c3, 'A', 1300, 0.08) == 3 and ap.cool_left(c3, 'B', 1300, 0.08) == 4 and ap.cool_left(c3, 'Z', 1300, 0.08) == 0
    c4 = {**c3, 'rounds': 14}
    assert ap.cool_left(c4, 'B', 2500, 0.08) == 1 and ap.cool_left({**c3, 'rounds': 15}, 'B', 2800, 0.08) == 0


def test_stay_or_swap_only_rotates_when_the_next_coin_beats_this_one_by_more_than_the_swap_costs():
    import arena_prime as ap
    cost = ap.swap_cost_pct(1.0, 100_000, 100_000, 0.001)
    assert 0.2 < cost < 1.0                                                              # two fees on a $1 coin + (no spread learned in tests)
    assert ap.swap_cost_pct(1.0, 5_000, 5_000, 0.001) > cost and ap.swap_cost_pct(0, 1, 1) == 0.0
    go, why = ap.swap_edge({'chg1h': -6}, {'chg1h': 9}, 1.0, 0.9)
    assert go and 'edge' in why
    assert not ap.swap_edge({'chg1h': -6}, {'chg1h': 0.5}, 1.0, 0.9)[0]                  # next coin isn't even beating SOL → stay
    assert not ap.swap_edge({'chg1h': 3.0}, {'chg1h': 4.5}, 1.0, 0.9)[0]                 # 1.5% edge < 0.9% cost + 1% margin → stay
    assert ap.swap_edge({'chg1h': 3.0}, {'chg1h': 5.0}, 1.0, 0.9)[0]
    assert ap.swap_edge({'chg1h': -6}, {}, 1.0, 0.9)[0]                                  # no reading = no evidence to block on


def test_hourly_swap_cap_tunes_itself_from_the_cost_explains_itself_and_never_counts_protective_exits():
    import arena_prime as ap
    small = ap.swap_cap({'paperFeeUsd': 0.01}, 5.0, 4)
    cheap = ap.swap_cap({'paperFeeUsd': 0.001}, 5.0, 4)
    assert small['auto'] and cheap['auto'] and 2 <= small['cap'] <= cheap['cap'] <= 12   # dearer swaps → fewer of them an hour
    assert small['costPct'] > cheap['costPct']
    assert 'rotations an hour' in small['why'] and '%' in small['why']
    assert ap.swap_cap({'swapCapHr': 4}, 5.0, 4)['cap'] == 4 and not ap.swap_cap({'swapCapHr': 4}, 5.0, 4)['auto']
    assert ap.swap_cap({'swapCapHr': -1}, 5.0, 4)['cap'] == 0
    assert ap.clean_cfg({'swapCapHr': 7})['swapCapHr'] == 0 and ap.clean_cfg({'swapCapHr': 6})['swapCapHr'] == 6 and ap.clean_cfg({})['swapEdge'] is True
    ev = [{'kind': 'rotate', 'at': 990, 'why': 'weakest after 0.08h'}, {'kind': 'rotate', 'at': 995, 'why': '🗑 trench cycle — -1% runner swapped'},
          {'kind': 'rotate', 'at': 996, 'why': '🎯 your pick — swapped in at the round'}, {'kind': 'rotate', 'at': 997, 'why': '⇄ swapped by hand'},
          {'kind': 'sl', 'at': 998, 'why': 'stop'}, {'kind': 'instant-swap', 'at': 999, 'why': '-18%'}, {'kind': 'rotate', 'at': -5000, 'why': 'weakest after 0.08h'}]
    assert ap.swaps_last_hour({'events': ev}, 1000) == 2                                 # only engine rotations count


def test_a_cycle_into_the_same_shape_leaves_a_full_card_alone_and_idle_cash_logs_one_line():
    import arena_prime as ap
    now = 1_000_000.0
    cfg = ap.clean_cfg({'rotateHours': 0.08, 'cycleEvery': 3, 'cycles': {'degen': 'trench'}, 'coins': 4, 'rescuePct': 0, 'rotateMinDrop': 15, 'swapEdge': False})
    row = lambda m, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'price': 1.0, 'liquidityUsd': 500000, 'liq': 500000, 'score': 80, 'vol1h': 50000, 'buyShare': 60, 'ageH': 30, **k}
    anchors, pools = [row('SOL'), row('MAJ')], [row('PL1'), row('PL2')]
    runners = [row('R1'), row('R2'), row('R3'), row('R4')]
    card = ap.deal('degen', pools, runners, cfg, now, anchors, shape='trench')
    assert card and card['phase'] == 'trench'
    held = {l['mint'] for l in card['legs']}
    px = {l['pairAddress']: 1.0 for l in card['legs']}                                   # every coin flat: none is a "winner" a re-shape would protect
    fresh = [row('N1', score=99), row('N2', score=99), row('N3', score=99)]             # better-ranked coins show up
    c = card
    for i in range(1, 8):                                                               # 7 round bells → two re-shape boundaries (rounds 3 and 6)
        c = ap.tick(c, px, pools, fresh + runners, cfg, now + i * (0.08 * 3600 + ap.BELL_SEC + 1), anchors, {}, {})
    assert {l['mint'] for l in c['legs']} == held and c['phase'] == 'trench'             # trench → trench: not one coin sold
    assert not any(e.get('kind') == 'phase' for e in c['events'][len(card['events']):])
    # idle cash put back to work reads as ONE line, not one a tick
    c2 = {**card, 'cash': 0.5, 'events': list(card['events'])}
    for i in range(4):
        c2 = ap.tick({**c2, 'cash': 0.5}, px, pools, runners, cfg, now + 30 + i * 50, anchors, {}, {})
    lines = [e for e in c2['events'] if e.get('kind') == 'compound']
    assert len(lines) == 1 and lines[0]['n'] == 4 and lines[0]['usd'] == 2.0


def test_money_trail_adds_back_route_rent_that_was_repaired():
    import fuse_wallet as fw
    rows = [{'id': 'a', 'side': 'sell', 'status': 'filled', 'usd': 0.05, 'costUsd': 0.42, 'realizedPnlUsd': -0.37, 'at': 10, 'mint': 'M'},
            {'id': 'routefix:t', 'side': 'fix', 'status': 'done', 'usd': 0.36, 'sol': 0.003, 'at': 20}]
    t = fw.money_trail(rows, {'sol': 0.0, 'legs': {}, 'fundedUsd': 0.42}, 0, 100, 120.0)
    assert t['routeRentBackUsd'] == 0.36 and t['realizedAllUsd'] == -0.01


def test_hands_off_lock_times_out_by_itself_and_only_takes_listed_lengths():
    import arena_prime as ap
    c = ap.set_hands_off({'events': []}, 3, 1000)
    assert c['handsOffUntil'] == 1000 + 3 * 3600 and ap.hands_off_left(c, 1000) == 10800 and 'hands-off for 3h' in c['events'][-1]['why']
    assert ap.hands_off_left(c, 1000 + 3 * 3600 + 1) == 0                                # over → picks work again, nothing to press
    assert 'handsOffUntil' not in ap.set_hands_off({'events': []}, 5, 1000)              # 5h is not an option → no lock
    off = ap.set_hands_off(c, 0, 2000)
    assert 'handsOffUntil' not in off and 'released' in off['events'][-1]['why'] and ap.hands_off_left(off, 2000) == 0


def test_real_money_does_not_buy_a_coin_that_is_falling_right_now():
    import arena_prime as ap
    assert ap.entry_ok({'pairAddress': 'P', 'chg5m': 2, 'chg1h': 10})
    assert not ap.entry_ok({'pairAddress': 'P', 'chg5m': -3.0, 'chg1h': 10})             # dropping this minute
    assert not ap.entry_ok({'pairAddress': 'P', 'chg5m': 1, 'chg1h': -8.0})              # down hard over the hour
    assert ap.entry_ok({'pairAddress': 'P', 'chg5m': -2.9, 'chg1h': -7.9})
    assert ap.entry_ok({'pairAddress': 'P'})                                             # no reading → not judged here
    assert not ap.entry_ok({'pairAddress': 'P'}, {'P': {'chg1h': -12}})                  # the live feed's reading counts too
    assert ap.entry_ok({'pairAddress': 'P', 'chg1h': 5}, {'P': {'chg1h': -12}})          # the candidate's own (fresher) reading wins


def test_floor_never_parks_the_card_in_a_pick_and_a_real_card_with_rest_off_goes_to_cash():
    import arena_prime as ap
    now = 1_000_000.0
    leg = lambda m, role, units, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': role, 'units': units, 'entry': 1.0, 'costUsd': units, 'at': now - 9999, 'liq': 5e6, **k}
    base = {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': now, 'cash': 0.0, 'startUsd': 4.0, 'roundStartUsd': 4.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'feesUsd': 0.0, 'events': [], 'rounds': 3}
    px = {'PKURA': 0.5, 'PR1': 0.5, 'PR2': 0.5, 'PMAJ': 0.5}                              # everything halved → −50% ≤ the −40% floor
    cfg = ap.clean_cfg({'rotateHours': 0.08, 'floorPct': 40, 'rescuePct': 0, 'compound': False})
    assert not ap.safe_anchor(leg('KURA', 'anchor', 1, picked=True)) and not ap.safe_anchor(leg('N', 'anchor', 1, newMajor=True)) and ap.safe_anchor(leg('MAJ', 'anchor', 1))
    # the owner's pick sits in the anchor seat → it is sold with the rest, the money waits in cash (never piled into the pick)
    c = ap.tick({**base, 'legs': [leg('KURA', 'anchor', 2, picked=True), leg('R1', 'runner', 1), leg('R2', 'runner', 1)]}, px, [], [], cfg, now + 30, [], {}, {})
    assert c.get('flooredAt') and c['legs'] == [] and round(c['cash'], 2) == 2.0 and c['events'][-1]['to'] == ['cash']
    # an established major still takes the floor money on a paper card …
    c2 = ap.tick({**base, 'legs': [leg('MAJ', 'anchor', 2), leg('R1', 'runner', 1), leg('R2', 'runner', 1)]}, px, [], [], cfg, now + 30, [], {}, {})
    assert [l['mint'] for l in c2['legs']] == ['MAJ'] and c2['events'][-1]['to'] == ['MAJ']
    # … but a REAL card with rest off re-deals on the next tick, so it goes straight to cash (no buy-then-sell of the anchor)
    real_cfg = {**cfg, 'dealLeadSec': 15.0, 'floorRestMins': 0.0}
    c3 = ap.tick({**base, 'legs': [leg('MAJ', 'anchor', 2), leg('R1', 'runner', 1), leg('R2', 'runner', 1)]}, px, [], [], real_cfg, now + 30, [], {}, {})
    assert c3['legs'] == [] and round(c3['cash'], 2) == 2.0
    c4 = ap.tick({**base, 'legs': [leg('MAJ', 'anchor', 2), leg('R1', 'runner', 1), leg('R2', 'runner', 1)]}, px, [], [], {**real_cfg, 'floorRestMins': 30.0}, now + 30, [], {}, {})
    assert [l['mint'] for l in c4['legs']] == ['MAJ']                                    # resting on purpose → it rests in the major


def test_idle_cash_never_piles_into_one_coin_and_the_stack_reads_in_one_line():
    import arena_prime as ap
    leg = lambda m, units, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'units': units, 'entry': 1.0, 'costUsd': units, **k}
    legs = [leg('A', 0.6), leg('B', 0.6), leg('C', 0.6), leg('NEW', 0.0, buying=True, wantUnits=0.0)]
    fills = ap.spread_cash(legs, 1.2, {})
    assert [round(f, 2) for f in fills] == [0.15, 0.15, 0.15, 0.75]                       # the waiting coin is filled to an equal share — not handed all $1.20
    after = [0.6 + fills[0], 0.6 + fills[1], 0.6 + fills[2], fills[3]]
    assert max(after) - min(after) < 1e-9 and round(sum(fills), 6) == 1.2                # every coin ends on the same share
    assert [round(f, 2) for f in ap.spread_cash([leg('A', 2.0), leg('B', 0.5), leg('C', 0.5)], 0.6, {})] == [0.0, 0.3, 0.3]   # an overweight coin gets nothing
    assert ap.spread_cash([leg('A', 1.0), leg('B', 1.0)], 0.0, {}) == [0.0, 0.0] and ap.spread_cash([], 1.0, {}) == []
    card = {'legs': [leg('W', 1, ride=True), leg('F', 1, frozen=True), leg('UP', 1), leg('FLAT', 1), {**leg('E', 0), 'placeholder': True}]}
    st = ap.stack(card, {'PUP': 1.08, 'PFLAT': 1.0}, {'keepWinPct': 5.0})
    assert st == {'seats': 4, 'locked': 2, 'winning': 1, 'proving': 1, 'full': False}
    assert ap.stack({'legs': [leg('W', 1, ride=True), leg('F', 1, frozen=True)]}, {}, {})['full'] and not ap.stack({'legs': []}, {}, {})['full']


def test_a_winner_banks_part_as_it_locks_and_is_not_bought_straight_back():
    import arena_prime as ap
    now = 1_000_000.0
    assert ap.clean_cfg({})['lockBankPct'] == 33.0 and ap.clean_cfg({'lockBankPct': 40})['lockBankPct'] == 33.0 and ap.clean_cfg({'lockBankPct': 0})['lockBankPct'] == 0.0
    cfg = ap.clean_cfg({'rotateHours': 99, 'rideAt': 20, 'rideTrail': 10, 'compound': True, 'cycles': {'degen': 'off'}, 'rescuePct': 0})
    leg = lambda m, role, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': role, 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0, 'at': now - 9999, 'liq': 1e12, **k}
    card = {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': now, 'cash': 0.0, 'startUsd': 3.0, 'roundStartUsd': 3.0, 'compoundedUsd': 0.0,
            'takenUsd': 0.0, 'feesUsd': 0.0, 'events': [], 'rounds': 1, 'legs': [leg('WIN', 'runner'), leg('B', 'runner'), leg('C', 'pool')]}
    c = ap.tick(card, {'PWIN': 1.3, 'PB': 1.0, 'PC': 1.0}, [], [], cfg, now + 30, [], {}, {'PWIN': 1e12, 'PB': 1e12, 'PC': 1e12})
    win = next(l for l in c['legs'] if l['mint'] == 'WIN')
    assert win['ride'] and abs(win['units'] - 0.67) < 1e-6 and abs(win['costUsd'] - 0.67) < 1e-6 and win['trimAt'] == now + 30   # 33% sold at the lock
    kinds = [e['kind'] for e in c['events']]
    assert kinds.index('ride') < kinds.index('lock-bank') and '33%' in next(e['why'] for e in c['events'] if e['kind'] == 'lock-bank')
    others = [l for l in c['legs'] if l['mint'] != 'WIN']
    assert all(l['units'] > 1.0 for l in others) and abs(sum(l['units'] for l in others) - (2.0 + 0.33 * 1.3)) < 0.01     # the banked $ went to the OTHER coins
    assert c['takenUsd'] > 0.09                                                          # the gain on the part sold is booked as taken


def test_the_keeper_sells_an_engine_trim_even_inside_the_rebalance_band():
    import fuse_wallet as fw
    cfg = {**fw.DEFAULT_CFG, 'walletId': 'w', 'address': 'O', 'armed': True, 'minOrderUsd': 0.1}
    book = {'sol': 0.0, 'legs': {'W': {'atoms': 1_000_000, 'decimals': 6, 'pair': 'PW', 'symbol': 'WIN', 'costUsd': 1.0, 'entryPx': 1.0}}}
    leg = {'mint': 'W', 'pairAddress': 'PW', 'symbol': 'WIN', 'units': 0.67, 'entry': 1.0}
    plain = fw.orders('t', {'legs': [leg]}, book, {'PW': 1.3}, 100.0, cfg, 1000)
    assert not [o for o in plain if o['side'] == 'sell']                                 # 33% over target is inside the 50% band → left alone
    banked = fw.orders('t', {'legs': [{**leg, 'trimAt': 900}]}, book, {'PW': 1.3}, 100.0, cfg, 1000)
    sells = [o for o in banked if o['side'] == 'sell']
    assert len(sells) == 1 and abs(sells[0]['atoms'] - 330000) <= 1 and sells[0]['why'] == 'trimmed to the card'
    assert not [o for o in fw.orders('t', {'legs': [{**leg, 'trimAt': 100}]}, book, {'PW': 1.3}, 100.0, cfg, 1000) if o['side'] == 'sell']   # only for 10 min


def test_no_list_sits_empty_trench_shows_its_closest_misses_as_watch_only():
    import contenders as ct
    miss = {'mint': 'T1', 'pairAddress': 'PT1', 'symbol': 'ALMOST', 'price': 0.001, 'liq': 30000, 'vol1h': 40000, 'ageH': 3, 'buyShare': 58, 'chg1h': 12, 'chg5m': 4}
    lg = ct.league({'trench': [], 'trench_watch': [miss, {**miss, 'mint': 'OLD', 'pairAddress': 'PO', 'ageH': 90}]})
    tr = next(d for d in lg['divisions'] if d['key'] == 'trench')
    assert [r['symbol'] for r in tr['rows']] == ['ALMOST'] and tr['rows'][0]['watch'] and tr['rows'][0]['chg5m'] == 4.0   # shown, with its 5-minute move
    assert not tr.get('nextUp') and 'T1' not in lg['nextUp']                             # a watch coin is never seated
    ok = ct.league({'trench': [{**miss, 'trenchOnly': True, 'trenchScore': 70}], 'trench_watch': [miss]})
    assert not next(d for d in ok['divisions'] if d['key'] == 'trench')['rows'][0].get('watch')   # a passing coin replaces the watch rows


def test_a_coin_the_owner_swapped_out_stays_off_the_card_for_hours():
    import arena_prime as ap
    card = {'rounds': 10, 'legs': [{'mint': 'PENGU', 'pairAddress': 'Pp', 'symbol': 'PENGU', 'role': 'pool', 'units': 5.0, 'entry': 1.0, 'costUsd': 5.0, 'liq': 1e9},
                                   {'mint': 'b', 'pairAddress': 'Pb', 'symbol': 'B', 'role': 'runner', 'units': 5.0, 'entry': 1.0, 'costUsd': 5.0, 'liq': 1e9}], 'events': [], 'feesUsd': 0, 'cash': 0.0}
    q = ap.queue_swap(card, 'Pp', {'mint': 'n', 'pairAddress': 'Pn', 'symbol': 'NEW', 'price': 2.0, 'liquidityUsd': 1e9})
    ap.apply_queued(q, {'Pp': 1.0, 'Pn': 2.0}, {}, 1000.0)
    assert 'PENGU' in ap.cooling(q, 1000.0 + 60, 0.08)
    later = {**q, 'rounds': 40}                                                          # 30 rounds on: the normal 3-round cool-down is long over …
    assert 'PENGU' in ap.cooling(later, 1000.0 + 3 * 3600, 0.08)                         # … but the owner took it off → still out
    assert 'PENGU' not in ap.cooling(later, 1000.0 + ap.OWNER_OUT_SEC + 1, 0.08)         # free again after 6h
    assert ap.cool_left(later, 'PENGU', 1000.0 + 3600, 0.08) == 0                        # … the 6h rule is for the ENGINE: the owner may pick it back
    q2 = ap.queue_swap({**later, 'legs': [dict(x) for x in later['legs']]}, 'Pn', {'mint': 'PENGU', 'pairAddress': 'Pp', 'symbol': 'PENGU', 'price': 1.0, 'liquidityUsd': 1e9})
    ap.apply_queued(q2, {'Pp': 1.0, 'Pn': 2.0}, {}, 1000.0 + 3 * 3600)
    assert 'PENGU' not in (q2.get('ownerOut') or {})                                     # picked back in → no longer "removed by you"


def test_skim_takes_only_the_profit_keeps_the_stake_and_sends_it_where_the_owner_says():
    import arena_prime as ap
    now = 1_000_000.0
    leg = lambda m, units, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': 'runner', 'units': units, 'entry': 1.0, 'costUsd': units, 'at': now - 9999, 'liq': 1e12, **k}
    card = {'legs': [leg('UP', 1.0), leg('DOWN', 1.0)], 'cash': 0.0, 'events': [], 'takenUsd': 0.0, 'feesUsd': 0.0}
    px = {'PUP': 1.5, 'PDOWN': 0.7}
    c = ap.skim_leg(card, 'PUP', px, {}, now)
    up = c['legs'][0]
    assert abs(up['units'] * 1.5 - 1.0) < 1e-6                                           # what stays is worth exactly the stake ($1.00)
    assert abs(c['cash'] - 0.5) < 1e-6 and not c.get('holdCashUsd')                      # the $0.50 profit is card cash, free to go into the other coins
    assert up['trimAt'] == now and up['skimPx'] == 1.5 and c['events'][-1]['kind'] == 'skim' and 'other coins' in c['events'][-1]['why']
    assert card['legs'][0]['units'] == 1.0                                               # pure: the input card is untouched
    tax = ap.skim_leg(card, 'PUP', px, {}, now, to='cash')
    assert abs(tax['holdCashUsd'] - 0.5) < 1e-6 and 'held as cash' in tax['events'][-1]['why']               # held for the owner, never re-spent
    for bad in ('PDOWN', 'PNOPE'):
        try:
            ap.skim_leg(card, bad, px, {}, now); assert False
        except ValueError:
            pass
    # the skimmed profit goes to the OTHER coin, not back into the one it came from
    fills = [l for l in c['legs'] if now - (l.get('trimAt') or 0) > 600]
    assert [l['mint'] for l in fills] == ['DOWN']
    # auto: every +20% since the entry / the last skim
    cfg = ap.clean_cfg({'skimAt': 20, 'skimTo': 'card', 'rotateHours': 99, 'rideAt': 0, 'compound': False, 'cycles': {'degen': 'off'}, 'rescuePct': 0, 'lockBankPct': 0, 'peakSellPct': 100, 'tp': 0})
    assert cfg['skimAt'] == 20.0 and ap.clean_cfg({'skimAt': 15})['skimAt'] == 0.0 and ap.clean_cfg({'skimTo': 'x'})['skimTo'] == 'card'
    base = {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': now, 'cash': 0.0, 'startUsd': 2.0, 'roundStartUsd': 2.0, 'compoundedUsd': 0.0,
            'takenUsd': 0.0, 'feesUsd': 0.0, 'events': [], 'rounds': 1, 'legs': [leg('UP', 1.0, tp=900), leg('FLAT', 1.0)]}
    c1 = ap.tick(base, {'PUP': 1.15, 'PFLAT': 1.0}, [], [], cfg, now + 10, [], {}, {})
    assert not any(e['kind'] == 'skim' for e in c1['events'])                            # +15% < +20%: nothing yet
    c2 = ap.tick(c1, {'PUP': 1.25, 'PFLAT': 1.0}, [], [], cfg, now + 20, [], {}, {})
    assert [e['kind'] for e in c2['events']].count('skim') == 1 and abs(c2['cash'] - 0.25) < 0.01
    c3 = ap.tick(c2, {'PUP': 1.30, 'PFLAT': 1.0}, [], [], cfg, now + 30, [], {}, {})
    assert [e['kind'] for e in c3['events']].count('skim') == 1                          # +4% since the last skim: not again
    c4 = ap.tick(c3, {'PUP': 1.52, 'PFLAT': 1.0}, [], [], cfg, now + 40, [], {}, {})
    assert [e['kind'] for e in c4['events']].count('skim') == 2                          # another +20% from the last skim price → skimmed again


def test_a_partial_sell_to_cash_is_flagged_so_the_keeper_really_sells_it():
    import arena_prime as ap
    import fuse_wallet as fw
    card = {'legs': [{'mint': 'W', 'pairAddress': 'PW', 'symbol': 'W', 'role': 'runner', 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0}], 'cash': 0.0, 'events': []}
    c = ap.sell_leg_to_cash(card, 'PW', {'PW': 1.0}, 1000.0, 25)
    assert c['legs'][0]['trimAt'] == 1000.0 and abs(c['legs'][0]['units'] - 0.75) < 1e-9
    cfg = {**fw.DEFAULT_CFG, 'walletId': 'w', 'address': 'O', 'armed': True, 'minOrderUsd': 0.1}
    book = {'sol': 0.0, 'legs': {'W': {'atoms': 1_000_000, 'decimals': 6, 'pair': 'PW', 'symbol': 'W', 'costUsd': 1.0, 'entryPx': 1.0}}}
    assert [o['atoms'] for o in fw.orders('t', c, book, {'PW': 1.0}, 100.0, cfg, 1010) if o['side'] == 'sell'] == [250000]   # 25% really goes


def test_a_riding_coin_that_never_banked_banks_once_and_only_once():
    import arena_prime as ap
    now = 1_000_000.0
    cfg = ap.clean_cfg({'rotateHours': 99, 'rideAt': 100, 'rideTrail': 30, 'compound': False, 'cycles': {'degen': 'off'}, 'rescuePct': 0, 'tp': 0})
    leg = lambda m, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': 'runner', 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0, 'at': now - 9999, 'liq': 1e12, **k}
    card = {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': now, 'cash': 0.0, 'startUsd': 2.0, 'roundStartUsd': 2.0, 'compoundedUsd': 0.0,
            'takenUsd': 0.0, 'feesUsd': 0.0, 'events': [], 'rounds': 1,
            'legs': [leg('SPACE', ride=True, high=5.0, rideFrom=1.0, rideAt=now - 600, trimAt=now - 600), leg('B')]}   # locked earlier, its bank never sold
    px = {'PSPACE': 5.0, 'PB': 1.0}
    c = ap.tick(card, px, [], [], cfg, now + 10, [], {}, {})
    sp = c['legs'][0]
    assert abs(sp['units'] - 0.67) < 1e-6 and sp['bankedAt'] == now + 10 and sp['ride'] and [e['kind'] for e in c['events']].count('lock-bank') == 1
    c2 = ap.tick(c, px, [], [], cfg, now + 60, [], {}, {})
    assert abs(c2['legs'][0]['units'] - 0.67) < 1e-6 and [e['kind'] for e in c2['events']].count('lock-bank') == 1   # never twice
    off = ap.tick(card, px, [], [], {**cfg, 'lockBankPct': 0.0}, now + 10, [], {}, {})
    assert off['legs'][0]['units'] == 1.0                                                # setting off → nothing sold


def test_equal_weight_never_buys_back_a_coin_whose_profit_was_just_taken():
    import arena_prime as ap
    now = 1_000_000.0
    leg = lambda m, units, cost, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': 'runner', 'units': units, 'entry': 1.0, 'costUsd': cost, 'at': now - 9999, **k}
    evs = []
    ev = lambda **e: evs.append(e)
    for flag in ({'skimPx': 5.0}, {'bankedAt': now - 5}, {'ride': True}, {'frozen': True}, {'trimAt': now - 30}):
        c = {'cash': 1.5, 'legs': [leg('SPACE', 0.08, 0.08, **flag), leg('A', 1.1, 1.1), leg('B', 1.1, 1.1)]}
        ap.balance_small(c, {'PSPACE': 5.0, 'PA': 1.0, 'PB': 1.0}, {}, now, 0.0, ev)
        assert c['legs'][0]['units'] == 0.08 and c['cash'] == 1.5, flag                  # left alone: it is small on purpose
    c = {'cash': 1.5, 'legs': [leg('TINY', 0.08, 0.08), leg('A', 1.1, 1.1), leg('B', 1.1, 1.1)]}
    ap.balance_small(c, {'PTINY': 1.0, 'PA': 1.0, 'PB': 1.0}, {}, now, 0.0, ev)
    assert c['legs'][0]['units'] > 0.08                                                  # a coin that really went in tiny is still topped up


def test_off_its_peak_only_part_of_the_profit_is_sold_and_the_coin_keeps_riding():
    import arena_prime as ap
    now = 1_000_000.0
    assert ap.clean_cfg({})['peakSellPct'] == 50.0 and ap.clean_cfg({'peakSellPct': 60})['peakSellPct'] == 50.0 and ap.clean_cfg({'peakSellPct': 100})['peakSellPct'] == 100.0
    cfg = ap.clean_cfg({'rotateHours': 99, 'rideAt': 100, 'rideTrail': 30, 'compound': False, 'cycles': {'degen': 'off'}, 'rescuePct': 0, 'tp': 0, 'lockBankPct': 0})
    leg = lambda m, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': 'runner', 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0, 'at': now - 9999, 'liq': 1e12, **k}
    card = {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': now, 'cash': 0.0, 'startUsd': 2.0, 'roundStartUsd': 2.0, 'compoundedUsd': 0.0,
            'takenUsd': 0.0, 'feesUsd': 0.0, 'events': [], 'rounds': 1, 'legs': [leg('BIG', ride=True, high=10.0, rideFrom=1.0, rideAt=now - 600, bankedAt=now - 600), leg('B')]}
    nxt = [{'mint': 'N', 'pairAddress': 'PN', 'symbol': 'N', 'price': 1.0, 'liquidityUsd': 1e9, 'score': 90, 'vol1h': 9e4, 'buyShare': 60, 'ageH': 30}]
    c = ap.tick(card, {'PBIG': 7.0, 'PB': 1.0}, [], nxt, cfg, now + 10, [], {}, {})      # 10 → 7 = 30% off its peak, still +600%
    big = next(l for l in c['legs'] if l['mint'] == 'BIG')
    assert big['ride'] and big['high'] == 7.0                                            # still on the card, still riding, trail re-armed from here
    assert abs(big['units'] * 7.0 - (7.0 - 3.0)) < 0.01                                  # profit was $6 → half of it ($3) sold
    other = next(l for l in c['legs'] if l['mint'] == 'B')
    assert abs(other['units'] - 4.0) < 0.01 and c['cash'] < 0.01                         # … and put to work in the OTHER coin (never back into BIG)
    assert [e['kind'] for e in c['events']].count('peak-sell') == 1 and '50% of its profit' in next(e['why'] for e in c['events'] if e['kind'] == 'peak-sell')
    c2 = ap.tick(c, {'PBIG': 6.5, 'PB': 1.0}, [], nxt, cfg, now + 60, [], {}, {})       # −7% from the new mark: nothing more is sold
    assert [e['kind'] for e in c2['events']].count('peak-sell') == 1
    c3 = ap.tick(c2, {'PBIG': 0.4, 'PB': 1.0}, [], nxt, cfg, now + 120, [], {}, {})     # under its floor → the ride is over, swapped as before
    assert 'BIG' not in {l['mint'] for l in c3['legs']} and any(e['kind'] == 'ride-end' for e in c3['events'])


def test_an_empty_seat_is_refilled_with_an_equal_share_when_the_card_has_cash():
    import arena_prime as ap
    now = 1_000_000.0
    cfg = ap.clean_cfg({'rotateHours': 99, 'coins': 4, 'compound': True, 'cycles': {'degen': 'off'}, 'rescuePct': 0, 'rideAt': 0, 'tp': 0, 'cycleEvery': 0})
    leg = lambda m, role='runner': {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': role, 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0, 'at': now - 9999, 'liq': 1e12}
    card = {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': now, 'cash': 1.0, 'startUsd': 4.0, 'roundStartUsd': 4.0, 'compoundedUsd': 0.0,
            'takenUsd': 0.0, 'feesUsd': 0.0, 'events': [], 'rounds': 1, 'phase': 'degen', 'legs': [leg('A', 'anchor'), leg('B'), leg('C')]}
    px = {'PA': 1.0, 'PB': 1.0, 'PC': 1.0}
    cand = [{'mint': 'N', 'pairAddress': 'PN', 'symbol': 'NEW', 'price': 2.0, 'liquidityUsd': 1e9, 'score': 90, 'vol1h': 9e4, 'buyShare': 60, 'ageH': 30}]
    c = ap.tick(card, px, [], cand, cfg, now + 10, [], {}, {})
    assert [l['mint'] for l in c['legs']] == ['A', 'B', 'C', 'N'] and any(e['kind'] == 'seat' for e in c['events'])
    assert abs(c['legs'][3]['units'] * 2.0 - 1.0) < 0.01                                 # an equal share of a $4 card
    # no cash at all (a rugged coin left nothing): the three coins above the new equal share each give up their extra
    broke = ap.tick({**card, 'cash': 0.0}, px, [], cand, cfg, now + 10, [], {}, {})
    assert [l['mint'] for l in broke['legs']] == ['A', 'B', 'C', 'N']
    vals = [l['units'] * (2.0 if l['mint'] == 'N' else 1.0) for l in broke['legs']]
    assert all(abs(v - 0.75) < 0.02 for v in vals)                                       # 3 × $1.00 → 4 × $0.75
    locked = {**card, 'cash': 0.0, 'legs': [{**l, 'ride': True, 'high': 1.0, 'rideFrom': 1.0, 'bankedAt': 1} for l in card['legs']]}
    assert len(ap.tick(locked, px, [], cand, cfg, now + 10, [], {}, {})['legs']) == 3    # locked coins never give anything up
    assert len(ap.tick(card, px, [], [], cfg, now + 10, [], {}, {})['legs']) == 3        # no coin to seat → the cash is spread as before
    held = ap.tick({**card, 'holdAll': True}, px, [], cand, cfg, now + 10, [], {}, {})
    assert len(held['legs']) == 3


def test_the_owner_is_only_blocked_by_the_short_no_back_to_back_rule():
    import arena_prime as ap
    card = {'rounds': 20, 'cool': {'RECENT': {'at': 1.0, 'round': 19, 'loss': True, 'px': 2.0, 'pair': 'Pr'},
                                   'OLDLOSS': {'at': 1.0, 'round': 5, 'loss': True, 'px': 2.0, 'pair': 'Po'}, 'LEGACY': 123.0}}
    assert ap.pick_cool(card) == {'RECENT': 3}                                           # left a round ago → 3 more rounds
    assert ap.cool_left(card, 'OLDLOSS') == 0 and ap.cool_left(card, 'LEGACY') == 0 and ap.cool_left(card, 'NEVER') == 0
    assert 'OLDLOSS' in ap.cooling(card, 100.0, 0.08, {'Po': 1.0})                       # the ENGINE still won't deal back a coin under its exit price


def test_an_owner_write_during_a_tick_beats_the_ticks_save():
    a0 = {'tpl': 'degen', 'legs': [{'mint': 'A', 'pairAddress': 'pa'}], 'cash': 1.0}
    b0 = {'tpl': 'gold', 'legs': [{'mint': 'B', 'pairAddress': 'pb'}]}
    snap = ap.card_snap({'degen': a0, 'gold': b0})
    ticked = {'degen': {**a0, 'cash': 0.5}, 'gold': {**b0, 'rounds': 1}}
    assert ap.merge_tick(snap, ticked, {'degen': a0, 'gold': b0}) == ticked                      # nobody wrote: the tick saves
    picked = {**a0, 'legs': [{'mint': 'A', 'pairAddress': 'pa', 'swapTo': {'mint': 'Z'}}]}        # the owner queued a pick meanwhile
    out = ap.merge_tick(snap, ticked, {'degen': picked, 'gold': b0})
    assert out['degen'] == picked and out['gold'] == ticked['gold']                             # the pick survives; the other card ticks
    assert 'gold' not in ap.merge_tick(snap, ticked, {'degen': a0})                             # deleted meanwhile stays deleted
    assert ap.merge_tick(snap, ticked, {'degen': a0, 'gold': b0, 'next': {'tpl': 'next'}})['next'] == {'tpl': 'next'}


def test_forecast_reads_weather_trend_and_breadth_and_never_guesses():
    sim = {'s6': {'n': 60, 'avgPct': 1.0}, 's24': {'n': 200, 'avgPct': -4.0}}
    up = [{'chg1h': 5, 'buyShare': 60}] * 7 + [{'chg1h': -3, 'buyShare': 40}] * 3
    f = ap.forecast(sim, up)
    assert (f['level'], f['trend'], f['breadthPct'], f['buyersPct'], f['outlook']) == ('clear', 'clearing', 70, 54, 'tailwind')
    down = [{'chg1h': -5, 'buyShare': 40}] * 8 + [{'chg1h': 2, 'buyShare': 60}] * 2
    assert ap.forecast(sim, down)['outlook'] == 'headwind'
    storm = ap.forecast({'s6': {'n': 60, 'avgPct': -30.0}, 's24': {'n': 200, 'avgPct': -10.0}}, up)
    assert storm['level'] == 'storm' and storm['trend'] == 'worsening' and storm['outlook'] == 'headwind' and 'new majors' in storm['buys']
    none = ap.forecast({}, [])
    assert none['breadthPct'] is None and none['outlook'] == 'mixed' and none['trend'] == 'steady'   # no reading = no call


def test_idle_cash_never_lifts_the_one_eligible_coin_above_the_cards_equal_share():
    legs = [{'pairAddress': p, 'units': u, 'entry': 1.0} for p, u in (('a', 0.38), ('b', 0.29), ('c', 0.43), ('d', 0.74))]
    px = {l['pairAddress']: 1.0 for l in legs}
    fills = ap.spread_cash([legs[3]], 0.92, px, legs)                  # only the fresh pick may be topped up (the others were just cut)
    assert fills == [0.0]                                              # it already holds more than an equal share ($0.69): cash waits
    fills = ap.spread_cash([legs[1]], 0.92, px, legs)
    assert abs(fills[0] - (0.69 - 0.29)) < 1e-9                        # filled to the card's equal share, the rest stays cash
    assert abs(sum(ap.spread_cash(legs, 0.92, px, legs)) - 0.92) < 1e-9 and ap.spread_cash(legs, 0.92, px, legs)[3] == 0.0


def test_profit_recycle_every_n_rounds_takes_only_profit_and_spreads_it_for_balance():
    now = 1_000_000.0
    assert ap.clean_cfg({})['recyclePct'] == 0 and ap.clean_cfg({'recyclePct': 70, 'recycleEvery': 2})['recycleEvery'] == 2 and ap.clean_cfg({'recyclePct': 33})['recyclePct'] == 0
    base = {'rotateHours': 0.1, 'compound': True, 'cycles': {'degen': 'off'}, 'rescuePct': 0, 'lockBankPct': 0, 'peakSellPct': 100, 'rideAt': 150, 'swapCapHr': -1}
    leg = lambda m, role, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': role, 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0, 'at': now - 9999, 'liq': 1e12, **k}
    mk = lambda rounds: {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': now - 9999, 'cash': 0.0, 'startUsd': 3.0, 'roundStartUsd': 3.0, 'compoundedUsd': 0.0,
                         'takenUsd': 0.0, 'feesUsd': 0.0, 'events': [], 'rounds': rounds, 'legs': [leg('WIN', 'runner'), leg('B', 'runner'), leg('C', 'pool')]}
    px = {'PWIN': 1.5, 'PB': 0.9, 'PC': 1.0}; liq = {k: 1e12 for k in px}
    c = ap.tick(mk(1), px, [], [], ap.clean_cfg({**base, 'recyclePct': 70, 'recycleEvery': 2}), now, [], {}, liq)      # round 2 = a recycle round
    win = next(l for l in c['legs'] if l['mint'] == 'WIN')
    assert abs(win['units'] * 1.5 - (1.5 - 0.35)) < 0.01                        # 70% of the $0.50 profit left the coin, stake + 30% stay
    others = {l['mint']: l['units'] for l in c['legs'] if l['mint'] != 'WIN'}
    assert others['B'] > 1.0 and others['C'] > 1.0 and others['B'] * 0.9 < others['C'] * 1.0 + 0.2   # spread over the other coins
    assert c['cash'] < 0.01 and any('recycled' in e.get('why', '') for e in c['events'])
    assert all(l['units'] == 1.0 for l in ap.tick(mk(2), px, [], [], ap.clean_cfg({**base, 'recyclePct': 70, 'recycleEvery': 2}), now, [], {}, liq)['legs'])   # round 3: not due
    assert all(l['units'] == 1.0 for l in ap.tick(mk(1), px, [], [], ap.clean_cfg(base), now, [], {}, liq)['legs'])                                              # off by default


def test_idle_card_cash_goes_back_into_the_coins_at_the_round_even_after_a_recent_cut():
    now = 1_000_000.0
    cfg = ap.clean_cfg({'rotateHours': 0.1, 'compound': True, 'cycles': {'degen': 'off'}, 'rescuePct': 0, 'lockBankPct': 0, 'peakSellPct': 100, 'swapCapHr': -1})
    leg = lambda m, role, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': role, 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0, 'at': now - 9999, 'liq': 1e12, **k}
    card = lambda last: {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': last, 'cash': 0.6, 'startUsd': 3.6, 'roundStartUsd': 3.6, 'compoundedUsd': 0.0,
                         'takenUsd': 0.0, 'feesUsd': 0.0, 'events': [], 'rounds': 1,
                         'legs': [leg('A', 'runner', units=0.5, costUsd=0.5, trimAt=now - 120), leg('B', 'runner', units=0.5, costUsd=0.5, trimAt=now - 120), leg('C', 'pool', units=2.0, costUsd=2.0)]}
    px = {'PA': 1.0, 'PB': 1.0, 'PC': 1.0}; liq = {k: 1e12 for k in px}
    mid = ap.tick(card(now), px, [], [], cfg, now + 30, [], {}, liq)             # mid-round: A and B were cut 2 min ago, C is over its share
    assert abs(mid['cash'] - 0.6) < 1e-6                                         # the cash waits (it must not all go into C)
    bell = ap.tick(card(now - 9999), px, [], [], cfg, now + 30, [], {}, liq)     # the round bell
    assert bell['cash'] < 0.01 and all(abs(l['units'] - 0.8) < 0.01 for l in bell['legs'] if l['mint'] in 'AB')   # back into the coins under their share


def test_a_reserved_seat_with_no_coin_for_a_round_gives_its_money_back_to_the_cards_coins():
    now = 1_000_000.0
    cfg = ap.clean_cfg({'rotateHours': 0.1, 'compound': True, 'cycles': {'degen': 'off'}, 'rescuePct': 0, 'lockBankPct': 0, 'peakSellPct': 100, 'swapCapHr': -1})
    leg = lambda m, role, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': role, 'units': 1.0, 'entry': 1.0, 'costUsd': 1.0, 'at': now - 9999, 'liq': 1e12, **k}
    card = lambda age: {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': now, 'cash': 0.6, 'startUsd': 2.6, 'roundStartUsd': 2.6, 'compoundedUsd': 0.0,
                        'takenUsd': 0.0, 'feesUsd': 0.0, 'events': [], 'rounds': 1,
                        'legs': [leg('A', 'runner'), leg('B', 'runner'), leg('S', 'pool', units=0.0, costUsd=0.0, placeholder=True, reserveUsd=0.6, at=now - age)]}
    px = {'PA': 1.0, 'PB': 1.0, 'PS': 1.0}; liq = {k: 1e12 for k in px}
    young = ap.tick(card(60), px, [], [], cfg, now + 1, [], {}, liq)
    assert any(l.get('placeholder') for l in young['legs']) and abs(young['cash'] - 0.6) < 1e-6        # inside the round: still reserved
    old = ap.tick(card(900), px, [], [], cfg, now + 1, [], {}, liq)
    assert not any(l.get('placeholder') for l in old['legs']) and old['cash'] < 0.01                   # a round with no coin: released …
    assert all(abs(l['units'] - 1.3) < 0.01 for l in old['legs']) and any(e['kind'] == 'slot' for e in old['events'])   # … into the card's coins
    run = {'mint': 'R', 'pairAddress': 'PR', 'symbol': 'R', 'price': 1.0, 'liquidityUsd': 1e12, 'score': 80, 'ageH': 20}
    heal = ap.tick(card(60), {**px, 'PR': 1.0}, [], [run], cfg, now + 1, [], {}, {**liq, 'PR': 1e12})
    assert any(l['mint'] == 'R' for l in heal['legs'])                                                # no pool to take a pool seat → a runner takes it

def test_recycle_every_takes_2_4_and_6_rounds():
    assert [ap.clean_cfg({'recyclePct': 70, 'recycleEvery': n})['recycleEvery'] for n in (2, 4, 6, 5)] == [2, 4, 6, 3]


def test_a_real_card_with_money_in_transit_is_never_floored_on_the_engines_estimate():
    import arena_prime as ap
    now = 1_000_000.0
    leg = lambda m, role, units, **k: {'mint': m, 'pairAddress': 'P' + m, 'symbol': m, 'role': role, 'units': units, 'entry': 1.0, 'costUsd': units, 'at': now - 9999, 'liq': 5e6, **k}
    # two picks are mid-swap: their money is in the wallet as SOL the engine can't see yet → the estimate reads $2.2 of a $4 card
    card = {'tpl': 'degen', 'id': 'x', 'label': 'B', 'at': now - 9999, 'lastRotateAt': now, 'cash': 0.0, 'startUsd': 4.0, 'roundStartUsd': 4.0, 'compoundedUsd': 0.0,
            'takenUsd': 0.0, 'feesUsd': 0.0, 'events': [], 'rounds': 3, 'real': True,
            'legs': [leg('MAJ', 'anchor', 1.2), leg('R1', 'runner', 1.0), leg('N1', 'runner', 0.0, buying=True, wantUnits=0.9), leg('N2', 'runner', 0.0, buying=True, wantUnits=0.9)]}
    px = {'PMAJ': 1.0, 'PR1': 1.0, 'PN1': 1.0, 'PN2': 1.0}
    cfg = ap.clean_cfg({'rotateHours': 0.08, 'floorPct': 40, 'rescuePct': 50, 'compound': False})
    blind = ap.tick(card, px, [], [], cfg, now + 30, [], {}, {}, blind=True)
    assert not blind.get('flooredAt') and not blind.get('cycleFix') and {'MAJ', 'R1'} <= {l['mint'] for l in blind['legs']}
    assert not [e for e in blind['events'] if e['kind'] in ('floor', 'fix')]
    # the same card read from its TRUE book: $4 → nothing fires; a true −45% → the floor still protects it
    assert not ap.tick(card, px, [], [], cfg, now + 30, [], {}, {}, true_usd=4.0, blind=True).get('flooredAt')
    assert ap.tick(card, px, [], [], cfg, now + 30, [], {}, {}, true_usd=2.2).get('flooredAt')
    # paper cards (and the old call) are judged as before
    assert ap.tick({**card, 'real': False}, px, [], [], cfg, now + 30, [], {}, {}).get('flooredAt')
    # a floored real card is not re-dealt on a blind tick either: its new run must start from the TRUE value, not from the part
    # of its sale money the engine can see (the false floor's re-deal set a $1.07 baseline on a $2.39 card → "+129% this run")
    fl = {**card, 'legs': [], 'cash': 1.0, 'flooredAt': now - 120}
    assert ap.tick(fl, px, [], [], cfg, now + 30, [], {}, {}, blind=True).get('flooredAt') == now - 120


def test_best_entries_now_reads_three_setups_from_live_numbers_and_ranks_by_strength():
    import arena_prime as ap
    c = lambda m, m5, h1, buy, v5=1000, v1=12000: {'mint': m, 'symbol': m, 'pairAddress': 'P' + m, 'chg5m': m5, 'chg1h': h1, 'buyShare': buy, 'vol5m': v5, 'vol1h': v1, 'liq': 50000}
    assert ap.entry_setup(c('S', 4, -20, 65))[0] == 'sweep'                               # flushed on the hour, taken back now
    assert ap.entry_setup(c('B', 5, 30, 62, v5=3000))[0] == 'breakout'                    # up, still pushing, volume speeding up
    assert ap.entry_setup(c('B2', 5, 30, 62, v5=500)) is None                             # … not without the volume
    assert ap.entry_setup(c('P', -3, 40, 55))[0] == 'pullback'                            # strong hour, small dip, buyers in charge
    assert ap.entry_setup(c('K', -9, -20, 40)) is None and ap.entry_setup(c('F', -3, 40, 45)) is None   # a falling knife / sellers in charge = no setup
    assert ap.entry_setup({**c('N', 4, -20, 65), 'chg5m': None}) is None and ap.entry_setup(c('T', 4, -20, 65, v1=900)) is None   # no reading / no volume = not judged
    rows = ap.entries([c('S', 4, -20, 65), c('S', 4, -20, 65), c('B', 9, 30, 70, v5=4000), c('P', -3, 40, 55), c('X', 3, -9, 59), c('H', 4, -20, 65)], skip={'H'})
    assert len(rows) == 3 and [r['mint'] for r in rows].count('S') == 1 and 'H' not in [r['mint'] for r in rows]
    assert rows == sorted(rows, key=lambda r: -r['strength']) and all(r['name'] and r['why'] and 0 < r['strength'] <= 100 for r in rows)
    assert ap.entry_setup(c('G', 17, 839, 73, v5=9000)) is None                           # +839% on the hour already ran: not an entry
