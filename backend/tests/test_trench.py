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
                     ({'top10': 31.0}, 'top-10'), ({'scanned': False}, 'holder scan'), ({'bundled': 3}, 'bundled'), ({'devSold': True}, 'dev'),
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


def test_a_card_switched_to_the_trench_cycle_takes_its_trench_coins_on_the_next_tick():
    anchors, pools, runners = _cands()
    cfg = ap.clean_cfg({'trenchCoins': 2, 'cycles': {**{t: 'off' for t in ap.DEFAULT_CYCLES}, 'degen': 'trench'}, 'rescuePct': 0, 'cycleEvery': 6})
    card = ap.deal('degen', pools, [x for x in runners if not x.get('trenchOnly')], cfg, 0.0, anchors, shape='degen')
    assert not any(l.get('trench') for l in card['legs'])
    px = {l['pairAddress']: l['entry'] for l in card['legs']}
    win = next(l for l in card['legs'] if l['role'] == 'runner')
    px[win['pairAddress']] *= 1.5                                                        # a +50% runner is never sold for a trench coin
    for x in runners:
        px.setdefault(x['pairAddress'], x['price'])
    out = ap.tick(card, px, pools, runners, cfg, 30.0, anchors, {}, {})
    tl = [l for l in out['legs'] if l.get('trench')]
    assert 1 <= len(tl) <= 2 and any(l['mint'] == win['mint'] for l in out['legs'])
    assert any('trench cycle' in (e.get('why') or '') for e in out['events'])
    again = ap.tick(out, {**px, **{l['pairAddress']: l['entry'] for l in out['legs'] if l.get('trench')}}, pools, runners, cfg, 60.0, anchors, {}, {})
    assert len([l for l in again['legs'] if l.get('trench')]) == len(tl)                # stays put — no churn once it holds them
    off = ap.tick(card, px, pools, runners, ap.clean_cfg({**cfg, 'cycles': {t: 'off' for t in ap.DEFAULT_CYCLES}}), 30.0, anchors, {}, {})
    assert not any(l.get('trench') for l in off['legs'])                                 # other cycles never take one


def test_raw_pairs_breaking_out_join_the_holder_scan():
    now = 10 * 3.6e6
    p = {'pairCreatedAt': now - 2 * 3.6e6, 'marketCap': 30_000, 'txns': {'h1': {'buys': 300, 'sells': 150}}, 'volume': {'h1': 15_000},
         'priceChange': {'m5': 4, 'h1': 20}}
    assert tr.market_pair(p, now)
    for bad in ({'marketCap': 9_000}, {'pairCreatedAt': now - 9 * 3.6e6}, {'txns': {'h1': {'buys': 100, 'sells': 100}}}, {'priceChange': {'m5': -1, 'h1': 20}}, {'pairCreatedAt': None}):
        assert not tr.market_pair({**p, **bad}, now), bad


def test_a_runner_still_waiting_on_its_buy_is_the_first_seat_a_trench_coin_takes():
    anchors, pools, runners = _cands()
    cfg = ap.clean_cfg({'trenchCoins': 1, 'cycles': {**{t: 'off' for t in ap.DEFAULT_CYCLES}, 'degen': 'trench'}, 'rescuePct': 0, 'cycleEvery': 0})
    card = ap.deal('degen', pools, [x for x in runners if not x.get('trenchOnly')], cfg, 0.0, anchors, shape='degen')
    rs = [l for l in card['legs'] if l['role'] == 'runner']
    rs[-1].update(units=0.0, buying=True, wantUnits=5.0)                                  # stuck buying (real card)
    px = {l['pairAddress']: l['entry'] for l in card['legs']}
    for x in runners:
        px.setdefault(x['pairAddress'], x['price'])
    out = ap.tick(card, px, pools, runners, cfg, 30.0, anchors, {}, {})
    assert rs[-1]['mint'] not in {l['mint'] for l in out['legs']} and sum(1 for l in out['legs'] if l.get('trench')) == 1


def test_trench_widens_soft_checks_only_when_nothing_passes():
    thin = {**GOOD, 'txns1h': 140, 'vol1h': 6_000.0}                                        # passes only at a wider level
    lvl, res = tr.best_level([(GOOD, 520), (thin, 230)], lambda g, cfg: tr.gate(g[0], g[1], SAFE, cfg))
    assert lvl == 0 and [ok for _, ok, _ in res] == [True, False]                          # strict first: no widening needed
    lvl, res = tr.best_level([(thin, 230)], lambda g, cfg: tr.gate(g[0], g[1], SAFE, cfg))
    assert lvl == 2 and res[0][1]
    for k in ('maxTop10', 'maxInsiders', 'maxBundled', 'maxDev', 'minBuyShare'):              # safety never moves
        assert all(tr.widen(i)[k] == tr.TRENCH[k] for i in range(len(tr.WIDEN))), k
    rug = {**thin, 'top10': 40.0}
    assert tr.best_level([(rug, 900)], lambda g, cfg: tr.gate(g[0], g[1], SAFE, cfg))[0] is None


def test_a_picked_cycle_always_cycles_even_with_reshape_off():
    cfg = ap.clean_cfg({'cycleEvery': 0, 'cycles': {**{t: 'off' for t in ap.DEFAULT_CYCLES}, 'degen': 'trench'}})
    assert ap.reshape_every({'tpl': 'degen'}, cfg) == ap.REAL_MAX_RESHAPE
    assert ap.reshape_every({'tpl': 'safe'}, cfg) == 0                                      # no cycle picked → off stays off
    assert ap.cycle_peek({'tpl': 'degen', 'rounds': 2}, cfg)['next'] == 'trench'


def test_watch_creators_pass_with_a_penalty_and_the_funnel_says_why_coins_failed():
    ok, _ = tr.gate({**GOOD, 'creatorRep': 'watch'}, 520, SAFE)
    assert ok and tr.score({**GOOD, 'creatorRep': 'watch'}, 520)[0] < tr.score(GOOD, 520)[0]
    assert not tr.gate({**GOOD, 'creatorRep': 'high'}, 520, SAFE)[0]
    f = tr.funnel([GOOD, {**GOOD, 'ageH': 30.0}, {**GOOD, 'ageH': 40.0, 'top10': 60.0}])
    assert f[0]['n'] == 2 and 'fresh' in f[0]['why'] and any('top-10' in x['why'] for x in f)


def test_trench_fill_never_loops_one_fill_a_round_and_never_on_a_coin_just_bought():
    anchors, pools, runners = _cands()
    cfg = ap.clean_cfg({'trenchCoins': 2, 'rotateHours': 0.08, 'minHoldMins': 10, 'cycles': {**{t: 'off' for t in ap.DEFAULT_CYCLES}, 'degen': 'trench'}, 'rescuePct': 0, 'cycleEvery': 0})
    card = ap.deal('degen', pools, [x for x in runners if not x.get('trenchOnly')], cfg, 0.0, anchors, shape='degen')
    px = {l['pairAddress']: l['entry'] for l in card['legs']}
    for x in runners:
        px.setdefault(x['pairAddress'], x['price'])
    out = ap.tick(card, px, pools, runners, cfg, 30.0, anchors, {}, {})          # the first fill is immediate
    fills = lambda c: sum(1 for e in c['events'] if 'trench cycle' in (e.get('why') or ''))
    n1 = fills(out); assert n1 >= 1 and out.get('trenchFillAt') == 30.0
    # a trench coin is replaced by a NORMAL runner (as an instant swap / stop does) seconds later …
    tl = next(l for l in out['legs'] if l.get('trench'))
    normal = next(x for x in runners if not x.get('trenchOnly') and x['mint'] not in {l['mint'] for l in out['legs']})
    out['legs'][out['legs'].index(tl)] = ap._leg(normal, 10.0, 40.0, 'runner')
    px[normal['pairAddress']] = normal['price']
    again = ap.tick(out, px, pools, runners, cfg, 50.0, anchors, {}, {})         # … and the fill must NOT sell it straight back out
    assert fills(again) == n1 and normal['mint'] in {l['mint'] for l in again['legs']}


def test_owner_trench_settings_only_move_the_soft_checks_and_snap_to_the_lists():
    own = tr.clean_own({'mode': 'own', 'minHolders': 170, 'minVol1h': 4200, 'maxMcap': 9e9, 'minMcap': 50000, 'maxAgeH': 5, 'maxTop10': 99, 'minBuyShare': 1})
    assert own['mode'] == 'own' and own['minHolders'] in (150, 200) and own['minVol1h'] == 5000 and own['maxMcap'] == 1_000_000 and own['maxAgeH'] == 6
    assert 'maxTop10' not in own and 'minBuyShare' not in own                             # safety checks are not options
    g = tr.own_gate(own)
    assert g['maxTop10'] == tr.TRENCH['maxTop10'] and g['minBuyShare'] == tr.TRENCH['minBuyShare'] and g['maxDev'] == tr.TRENCH['maxDev']
    assert tr.clean_own(None) == {'mode': 'auto', 'meta': 'breakout', **{k: tr.clean_own({})[k] for k in tr.OWN_OPTIONS}} and tr.clean_own({'mode': 'x'})['mode'] == 'auto'
    low = tr.clean_own({'mode': 'own', 'minMcap': 50000, 'maxMcap': 100000})
    assert low['maxMcap'] > low['minMcap']
    coin = {'ageH': 2, 'mcap': 60000, 'txns1h': 130, 'vol1h': 6000, 'buyShare': 60, 'chg5m': 3, 'chg1h': 9, 'scanned': True, 'top10': 18, 'insiders': 2,
            'bundled': 0, 'dev': 1, 'top10Jump': 0, 'creatorRep': 'clean'}
    auth = {'mintAuthority': None, 'freezeAuthority': None}
    assert not tr.gate(coin, 220, auth)[0]                                               # strict default: too small a crowd
    mine = tr.own_gate({'mode': 'own', 'minHolders': 200, 'minTxns1h': 120, 'minVol1h': 5000})
    assert tr.gate(coin, 220, auth, mine)[0]                                             # the owner's numbers let it in …
    assert not tr.gate({**coin, 'top10': 40}, 220, auth, mine)[0]                        # … and a whale-heavy coin is still out
    assert not tr.gate(coin, 220, {'mintAuthority': 'X', 'freezeAuthority': None}, mine)[0]


def test_a_trench_near_miss_is_only_one_that_passed_every_safety_check():
    assert tr.soft_only(['≥ 400 holders', '≥ 250 trades in 1h', 'fresh (≤ 6h old)'])
    assert tr.soft_only(['5m and 1h green (breaking out now)', 'market cap broke $20K (under $150K)'])
    for f in ('top-10 < 25% (scan done)', 'snipers/bundlers < 8% · ≤ 1 bundled', 'dev < 5% and not selling', 'no top-10 spike · no flagged funders',
              'not a mayhem-mode coin', 'creator clean (not flagged · not suspect / high)', 'mint + freeze authority revoked'):
        assert not tr.soft_only(['≥ 400 holders', f]), f
    assert not tr.soft_only([])                                                          # a passing coin is not a "near-miss"


def test_trench_metas_set_only_soft_checks_and_the_finalist_pool_is_wide_enough_for_all():
    import trench as tr
    for key, (_l, _b, cfg) in tr.METAS.items():
        assert set(cfg) == set(tr.OWN_OPTIONS) and all(cfg[k] in tr.OWN_OPTIONS[k] for k in cfg), key   # soft checks, fixed lists
        g = tr.meta_gate(key)
        assert all(g[k] == tr.TRENCH[k] for k in ('maxTop10', 'maxInsiders', 'maxBundled', 'maxDev', 'maxTop10Jump', 'minBuyShare'))   # safety never moves
    assert tr.meta_gate('nope') is None
    lo = tr.loosest()
    assert lo['minHolders'] == 150 and lo['maxAgeH'] == 48 and lo['maxMcap'] == 1_000_000 and lo['minMcap'] == 10_000
    own = tr.clean_own({'mode': 'meta', 'meta': 'flood'})
    assert own['mode'] == 'meta' and tr.own_gate(own)['minVol1h'] == 50_000 and tr.own_gate(own)['maxTop10'] == tr.TRENCH['maxTop10']
    assert tr.clean_own({'mode': 'meta', 'meta': 'x'})['meta'] == 'breakout' and tr.clean_own({})['mode'] == 'auto'
    board = tr.meta_board([{'h': 1200}, {'h': 200}], lambda r, g: (r['h'] >= g['minHolders'], []))
    assert {b['key']: b['pass'] for b in board} == {'sprout': 2, 'breakout': 1, 'flood': 1, 'crowd': 1, 'survivor': 1}


def test_meta_proof_settles_after_an_hour_counts_a_vanished_coin_as_a_loss_and_uses_the_median():
    import trench as tr
    st = tr.meta_track({}, {'flood': [('A', 1.0), ('B', 2.0), ('G', 1.0)]}, lambda m: 0, 0.0)
    assert set(st['flood']['open']) == {'A', 'B', 'G'} and st['sprout'] == {'open': {}, 'done': []}
    st = tr.meta_track(st, {'flood': [('A', 5.0)]}, lambda m: 0, 1800.0)                       # still open: not noted twice, not settled
    assert st['flood']['open']['A']['px'] == 1.0 and not st['flood']['done']
    st = tr.meta_track(st, {'flood': [('A', 1.2)]}, {'A': 1.2, 'B': 1.0}.get, 3700.0)          # settled: A +20%, B −50%, G vanished
    assert sorted(d['pct'] for d in st['flood']['done']) == [-100.0, -50.0, 20.0] and not st['flood']['open']   # A not re-opened for 6h
    p = tr.meta_proof(st)['flood']
    assert (p['n'], p['medPct'], p['wonPct'], p['proven']) == (3, -50.0, 33, False)
    good = {'flood': {'done': [{'pct': x} for x in (4, 6, 8, -3, 900)]}}
    assert tr.meta_proof(good)['flood'] == {'n': 5, 'medPct': 6.0, 'wonPct': 80, 'open': 0, 'proven': True}   # median: the 900% doesn't carry it
    assert tr.meta_proof({})['crowd'] == {'n': 0, 'medPct': None, 'wonPct': None, 'open': 0, 'proven': False}


def test_an_unscanned_coin_is_reported_apart_and_top10_passes_higher_only_while_holders_hold():
    import trench as tr
    base = {'ageH': 2.0, 'mcap': 60_000, 'txns1h': 500, 'vol1h': 30_000, 'buyShare': 60, 'chg5m': 3, 'chg1h': 20, 'scanned': True, 'top10': 31.0, 'top10Jump': 0.2,
            'insiders': 1.0, 'bundled': 0, 'dev': 1.0, 'devSold': False, 'flaggedFunders': 0, 'creatorRep': 'clean', 'creatorFlagged': False, 'x': True, 'site': False}
    assert tr.precheck(base) == []                                                          # 31% but holding, with an X account, 2h old
    assert any('top-10' in f for f in tr.precheck({**base, 'x': False}))                    # nobody behind it → the 25% limit
    assert any('top-10' in f for f in tr.precheck({**base, 'top10': 36.0}))                 # never past 35%
    assert any('top-10' in f for f in tr.precheck({**base, 'top10Jump': 3.0}))              # top holders adding = not holding
    un = tr.precheck({**base, 'scanned': False, 'top10': None})
    assert un == ['holder scan not done yet'] and not tr.soft_only(un)                      # queued, not judged — and never pickable as a near-miss
