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
    assert [r['mint'] for r in out['rows'] if not r.get('open')] == [GOOD['mint']] and out['rows'][0]['trench'] and out['floor'] == 8000
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
    assert any('trench drop' in (e.get('why') or '') for e in out['events'])
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
    fills = lambda c: sum(1 for e in c['events'] if 'trench drop' in (e.get('why') or ''))
    n1 = fills(out); assert n1 >= 1 and out.get('trenchFillAt') == 30.0
    # a trench coin is replaced by a NORMAL runner (as an instant swap / stop does) seconds later …
    tl = next(l for l in out['legs'] if l.get('trench'))
    normal = next(x for x in runners if not x.get('trenchOnly') and x['mint'] not in {l['mint'] for l in out['legs']})
    out['legs'][out['legs'].index(tl)] = ap._leg(normal, 10.0, 40.0, 'runner')
    px[normal['pairAddress']] = normal['price']
    again = ap.tick(out, px, pools, runners, cfg, 50.0, anchors, {}, {})         # … and the fill must NOT sell it straight back out
    assert fills(again) == n1 and normal['mint'] in {l['mint'] for l in again['legs']}


def test_a_card_switched_off_trench_takes_no_trench_coin_while_it_waits_for_its_next_reshape():
    anchors, pools, runners = _cands()
    mk = lambda cyc: ap.clean_cfg({'trenchCoins': 2, 'rotateHours': 0.08, 'cycles': {**{t: 'off' for t in ap.DEFAULT_CYCLES}, 'degen': cyc}, 'rescuePct': 0, 'cycleEvery': 0})
    card = {**ap.deal('degen', pools, [x for x in runners if not x.get('trenchOnly')], mk('press'), 0.0, anchors, shape='degen'), 'phase': 'trench'}
    px = {l['pairAddress']: l['entry'] for l in card['legs']}
    for x in runners:
        px.setdefault(x['pairAddress'], x['price'])
    out = ap.tick(card, px, pools, runners, mk('press'), 30.0, anchors, {}, {})       # still in its trench SHAPE, but the owner's cycle is Press now
    assert not any(l.get('trench') for l in out['legs']) and not any('trench drop' in (e.get('why') or '') for e in out['events'])
    on = ap.tick(card, px, pools, runners, mk('trench'), 30.0, anchors, {}, {})       # the same card with Trench still picked does fill
    assert any(l.get('trench') for l in on['legs'])


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
        soft = {k: v for k, v in cfg.items() if k != 'needSocials'}   # 🎯 Launch also REQUIRES a website + X (stricter, never looser)
        assert set(soft) == set(tr.OWN_OPTIONS) and all(soft[k] in tr.OWN_OPTIONS[k] for k in soft), key   # soft checks, fixed lists
        g = tr.meta_gate(key)
        assert all(g[k] == tr.TRENCH[k] for k in ('maxTop10', 'maxInsiders', 'maxBundled', 'maxDev', 'maxTop10Jump', 'minBuyShare'))   # safety never moves
    assert tr.meta_gate('nope') is None
    lo = tr.loosest()
    assert lo['minHolders'] == 100 and lo['maxMcap'] == 1_000_000 and lo['minMcap'] == 10_000
    own = tr.clean_own({'mode': 'meta', 'meta': 'baby'})
    assert own['mode'] == 'meta' and tr.own_gate(own)['minVol1h'] == 5_000 and tr.own_gate(own)['maxTop10'] == tr.TRENCH['maxTop10']
    assert tr.clean_own({'mode': 'meta', 'meta': 'x'})['meta'] == 'breakout' and tr.clean_own({})['mode'] == 'auto'
    board = tr.meta_board([{'h': 1200}, {'h': 200}], lambda r, g: (r['h'] >= g['minHolders'], []))
    assert {b['key']: b['pass'] for b in board} == {'baby': 2, 'breakout': 1} and list(tr.METAS) == ['baby', 'breakout']   # two metas, not seven


def test_meta_proof_settles_after_an_hour_counts_a_vanished_coin_as_a_loss_and_uses_the_median():
    import trench as tr
    st = tr.meta_track({}, {'breakout': [('A', 1.0), ('B', 2.0), ('G', 1.0)]}, lambda m: 0, 0.0)
    assert set(st['breakout']['open']) == {'A', 'B', 'G'} and st['baby'] == {'open': {}, 'done': []}
    st = tr.meta_track(st, {'breakout': [('A', 5.0)]}, lambda m: 0, 1800.0)                       # still open: not noted twice, not settled
    assert st['breakout']['open']['A']['px'] == 1.0 and not st['breakout']['done']
    st = tr.meta_track(st, {'breakout': [('A', 1.2)]}, {'A': 1.2, 'B': 1.0}.get, 3700.0)          # settled: A +20%, B −50%, G vanished
    assert sorted(d['pct'] for d in st['breakout']['done']) == [-100.0, -50.0, 20.0] and not st['breakout']['open']   # A not re-opened for 6h
    p = tr.meta_proof(st)['breakout']
    assert (p['n'], p['medPct'], p['wonPct'], p['proven']) == (3, -50.0, 33, False)
    good = {'breakout': {'done': [{'pct': x} for x in (4, 6, 8, -3, 900)]}}
    assert tr.meta_proof(good)['breakout'] == {'n': 5, 'medPct': 6.0, 'wonPct': 80, 'open': 0, 'proven': True}   # median: the 900% doesn't carry it
    assert tr.meta_proof({})['baby'] == {'n': 0, 'medPct': None, 'wonPct': None, 'open': 0, 'proven': False}


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


def test_closest_lists_only_safe_coins_that_miss_soft_checks_busiest_first():
    import trench as tr
    base = {'mint': 'A', 'pairAddress': 'pa', 'ageH': 2.0, 'mcap': 60_000, 'txns1h': 500, 'vol1h': 30_000, 'buyShare': 60, 'chg5m': -2, 'chg1h': 20, 'scanned': True, 'top10': 15.0,
            'top10Jump': 0.2, 'insiders': 1.0, 'bundled': 0, 'dev': 1.0, 'devSold': False, 'flaggedFunders': 0, 'creatorRep': 'clean', 'creatorFlagged': False}
    rows = tr.closest([base, {**base, 'mint': 'B', 'pairAddress': 'pb', 'vol1h': 90_000, 'chg5m': 4}, {**base, 'mint': 'C', 'pairAddress': 'pc', 'top10': 60.0},
                       {**base, 'mint': 'D', 'pairAddress': 'pd', 'scanned': False, 'top10': None}, {**base, 'mint': 'E', 'pairAddress': 'pe', 'creatorRep': 'high'}])
    assert [c['mint'] for c, _ in rows] == ['B', 'A']                                   # unsafe / unscanned / bad creator never listed
    assert rows[0][1] == ['holder count pending'] and any('green' in f for f in rows[1][1])


def test_the_paper_record_works_for_any_named_read_not_only_metas():
    import trench
    keys = {'sweep': 1, 'breakout': 1}
    st = trench.meta_track({}, {'sweep': [('A', 1.0)], 'breakout': [('B', 2.0)], 'sprout': [('Z', 1.0)]}, lambda m: 0, 1000, keys=keys)
    assert set(st) == {'sweep', 'breakout'} and st['sweep']['open']['A']['px'] == 1.0          # only the asked keys are tracked
    st = trench.meta_track(st, {}, lambda m: {'A': 1.2}.get(m), 1000 + trench.PROOF_SEC, keys=keys)
    assert st['sweep']['done'][0]['pct'] == 20.0 and st['breakout']['done'][0]['pct'] == -100.0   # no price an hour later = a loss
    pr = trench.meta_proof(st, keys=keys)
    assert pr['sweep'] == {'n': 1, 'medPct': 20.0, 'wonPct': 100, 'open': 0, 'proven': False} and set(pr) == {'sweep', 'breakout'}


def test_band_miss_says_in_numbers_why_a_coin_is_outside_the_owners_filter():
    import trench
    g = trench.own_gate(trench.clean_own({'mode': 'own', 'maxAgeH': 1, 'minMcap': 10000, 'maxMcap': 100000}))
    assert trench.band_miss({'ageH': 0.4, 'mcap': 42000}, g) == []
    assert trench.band_miss({'ageH': 6.28, 'mcap': 2_429_929}, g) == ['6.3h old — filter ≤ 1h', 'cap $2.4M — filter up to $100K']
    assert trench.band_miss({'ageH': 0.2, 'mcap': 4000}, g) == ['cap $4K — filter from $10K'] and trench.band_miss({'mcap': 50000}, g) == ['age unknown']
    # the owner's own filter widens which coins get the holder count (a $10K floor is under every meta's)
    assert trench.loosest({**g, 'maxAgeH': 72})['maxAgeH'] == 72 and trench.loosest()['maxAgeH'] < 72


def test_a_gate_that_needs_socials_wants_a_website_and_x_set_at_launch():
    g = {**tr.meta_gate('baby'), 'maxAgeH': 1, 'needSocials': 1}   # the retired 🎯 Launch meta's gate: the check itself is kept
    assert g['maxAgeH'] == 1 and g['needSocials'] and g['maxTop10'] == tr.TRENCH['maxTop10']        # safety checks unchanged
    coin = {'ageH': 0.4, 'mcap': 60000, 'txns1h': 300, 'vol1h': 40000, 'buyShare': 62, 'chg5m': 4, 'chg1h': 30, 'scanned': True, 'top10': 15, 'insiders': 2,
            'bundled': 0, 'dev': 1, 'top10Jump': 0, 'creatorRep': 'clean', 'site': True, 'x': True}
    auth = {'mintAuthority': None, 'freezeAuthority': None}
    assert tr.gate(coin, 300, auth, g)[0]
    for bad in ({'site': False}, {'x': False}, {'ageH': 1.5}):
        ok, fails = tr.gate({**coin, **bad}, 300, auth, g)
        assert not ok
    assert 'website + X account set at launch' in tr.gate({**coin, 'x': False}, 300, auth, g)[1]
    assert 'website + X account set at launch' not in tr.gate({**coin, 'x': False}, 300, auth, tr.meta_gate('baby'))[1]   # a plain meta never asks for it


def _pair(mint, sym, vol1h, vol5m, m5, h1, buys, sells, age_h, now_ms=10_000_000_000.0, px=0.001):
    return {'baseToken': {'address': mint, 'symbol': sym}, 'pairAddress': 'p' + mint, 'priceUsd': px, 'marketCap': 50_000, 'liquidity': {'usd': 12_000},
            'pairCreatedAt': now_ms - age_h * 3.6e6, 'volume': {'h1': vol1h, 'm5': vol5m}, 'priceChange': {'m5': m5, 'h1': h1}, 'txns': {'h1': {'buys': buys, 'sells': sells}}}


def test_open_gates_lists_every_feed_coin_front_runners_first_and_says_what_each_has_not_passed():
    now = 10_000_000_000.0
    pairs = [_pair('A', 'QUIET', 2_000, 100, 0.2, 1, 10, 10, 30), _pair('B', 'RUN', 180_000, 30_000, 9, 60, 700, 300, 0.5), _pair('C', 'OLD', 90_000, 6_000, 1, 12, 300, 250, 400),
             _pair('B', 'RUN', 1, 1, 0, 0, 1, 1, 1), {'baseToken': {}, 'priceUsd': 1}]
    board = tr.open_board(pairs, {'B': (True, []), 'C': (False, ['top-10 < 20%'])}, now)
    assert [r['symbol'] for r in board] == ['RUN', 'OLD', 'QUIET'] and [r['rank'] for r in board] == [1, 2, 3]      # nothing filtered, one row a coin, 400h-old coin included
    run, old, quiet = board
    assert run['safe'] is True and run['fails'] == [] and run['soft'] and run['open'] and run['front'] > old['front'] > quiet['front']
    assert old['safe'] is False and old['fails'] == ['top-10 < 20%']
    assert quiet['safe'] is None and 'not scanned' in quiet['fails'][0]                                              # unknown is SAID, never hidden
    assert run['buyShare'] == 70.0 and run['txns1h'] == 1000 and run['ageH'] == 0.5


def test_callouts_note_a_leader_once_settle_it_an_hour_later_and_feed_reads_newest_first():
    now = 10_000_000_000.0
    board = tr.open_board([_pair('B', 'RUN', 180_000, 30_000, 9, 60, 700, 300, 0.5), _pair('C', 'OLD', 90_000, 6_000, 1, 12, 300, 250, 400),
                               _pair('A', 'QUIET', 2_000, 100, 0.2, 1, 10, 10, 30)], {}, now)
    calls = tr.callouts(board)
    assert [r['symbol'] for r in calls['leader']] == ['RUN', 'OLD', 'QUIET'] and [r['symbol'] for r in calls['mover']] == ['RUN', 'OLD'] and [r['symbol'] for r in calls['fresh']] == ['RUN']
    passing = {k: [(r['mint'], r['price']) for r in v] for k, v in calls.items()}
    st = tr.meta_track({}, passing, lambda m: None, 1000.0, keys=tr.CALLOUTS)
    assert set(st['fresh']['open']) == {'B'} and st['leader']['open']['B']['px'] == 0.001
    st2 = tr.meta_track(st, passing, lambda m: None, 1210.0, keys=tr.CALLOUTS)                               # 3.5 min later: the same call is not noted twice
    assert st2['fresh']['open']['B']['at'] == 1000.0
    feed = tr.callout_feed(st2, {'B': {'symbol': 'RUN', 'pairAddress': 'pB'}}, {'B': 0.0013}, 1300.0)
    b = next(x for x in feed if x['mint'] == 'B' and x['kind'] == 'fresh')
    assert b['live'] and b['pct'] == 30.0 and b['symbol'] == 'RUN' and b['mins'] == 5
    st3 = tr.meta_track(st2, {}, lambda m: {'B': 0.0015}.get(m), 1000.0 + tr.PROOF_SEC, keys=tr.CALLOUTS)   # settled: B +50%, the others vanished = −100%
    assert st3['fresh']['done'][0]['pct'] == 50.0 and st3['fresh']['open'] == {}
    assert {d['mint']: d['pct'] for d in st3['leader']['done']} == {'B': 50.0, 'C': -100.0, 'A': -100.0}
    pr = tr.meta_proof(st3, keys=tr.CALLOUTS)
    assert pr['fresh']['n'] == 1 and pr['leader']['n'] == 3 and pr['leader']['proven'] is False
    assert tr.CALLOUT_SEC == 210 and set(tr.CALLOUTS) == {'leader', 'mover', 'fresh'}


def test_baby_meta_is_the_loosest_crowd_check_and_keeps_every_safety_check():
    g, base = tr.meta_gate('baby'), tr.TRENCH
    assert list(tr.METAS)[0] == 'baby'
    for k in ('minHolders', 'minTxns1h', 'minMcap'):
        assert g[k] == min(tr.OWN_OPTIONS[k])                                   # nothing looser exists
    assert g['maxMcap'] == max(tr.OWN_OPTIONS['maxMcap']) and g['maxAgeH'] == 3
    for k in ('minBuyShare', 'maxTop10', 'maxInsiders', 'maxBundled', 'maxDev', 'maxTop10Jump'):
        assert g[k] == base[k]                                                  # anti-snipe / anti-rug: identical to every other meta


def test_every_30_minutes_one_trench_coin_takes_the_weakest_seat_or_waits_until_a_coin_makes_10c_or_less():
    anchors, pools, runners = _cands()
    cfg = ap.clean_cfg({'trenchCoins': 1, 'rotateHours': 0.25, 'minHoldMins': 10, 'cycles': {**{t: 'off' for t in ap.DEFAULT_CYCLES}, 'degen': 'trench'}, 'rescuePct': 0, 'cycleEvery': 0,
                        'rideAt': 0, 'tp': 0, 'lockBankPct': 0, 'tpStakeUsd': 0, 'skimAt': 0})
    card = ap.deal('degen', pools, [x for x in runners if not x.get('trenchOnly')], cfg, 0.0, anchors, shape='degen')
    px = {l['pairAddress']: l['entry'] for l in card['legs']}
    for x in runners:
        px.setdefault(x['pairAddress'], x['price'])
    drops = lambda c: sum(1 for e in c['events'] if 'trench drop' in (e.get('why') or ''))
    out = ap.tick(card, px, pools, runners, cfg, 30.0, anchors, {}, {})
    assert drops(out) == 1
    mid = ap.tick(out, px, pools, runners, cfg, 30.0 + 900, anchors, {}, {})      # 15 min later: not yet
    assert drops(mid) == 1
    # 30 min: every runner seat is winning more than 10c → the drop WAITS in the queue (nothing is sold for it)
    up = {**px, **{l['pairAddress']: l['entry'] * 1.2 for l in mid['legs'] if l.get('role') == 'runner'}}
    t1 = 30.0 + ap.TRENCH_DROP_SEC + 5
    wait = ap.tick(mid, up, pools, runners, cfg, t1, anchors, {}, {})
    assert drops(wait) == 1 and all(l['units'] * (up[l['pairAddress']] - l['entry']) > ap.TRENCH_VICTIM_USD for l in wait['legs'] if l.get('role') == 'runner')
    # … one coin slips back to +0 → it is the weakest link: the queued trench coin takes ITS seat on the next tick
    weak = next(l for l in wait['legs'] if l.get('role') == 'runner')
    slip = {**up, weak['pairAddress']: weak['entry']}
    late = ap.tick(wait, slip, pools, runners, cfg, t1 + 30, anchors, {}, {})
    assert drops(late) == 2 and weak['mint'] not in {l['mint'] for l in late['legs']} and late['trenchFillAt'] == t1 + 30
    assert drops(ap.tick(late, slip, pools, runners, cfg, t1 + 60, anchors, {}, {})) == 2   # the next one is 30 min away


def test_trench_smart_entry_not_falling_not_mid_spike_buyers_at_least_55():
    ok = {'pairAddress': 'P', 'chg5m': 1.0, 'chg1h': 40.0, 'buyShare': 60}
    assert ap.trench_entry(ok) and ap.trench_entry({'pairAddress': 'P'})            # no reading = not judged
    assert not ap.trench_entry({**ok, 'chg5m': 6.0}) and not ap.trench_entry({**ok, 'chg5m': -4.0})
    assert not ap.trench_entry({**ok, 'buyShare': 48}) and not ap.trench_entry({**ok, 'chg1h': -12.0})
    assert not ap.trench_entry({'pairAddress': 'P'}, {'P': {'chg5m': 9.0}})        # the momentum feed counts when the row has none


def test_every_picker_list_shows_its_own_record_or_says_whose_it_borrows():
    import trench
    mine = {'n': 6, 'medPct': -4.0, 'wonPct': 40, 'proven': False}
    few = {'n': 2, 'medPct': 10.0, 'wonPct': 100}
    calls = {'leader': {'n': 60, 'medPct': -1.1, 'wonPct': 48}, 'mover': {'n': 60, 'medPct': -74.9, 'wonPct': 10}, 'fresh': {'n': 3}}
    out = trench.list_records({'ptrend': few, 'movers': mine, 'volume': few, 'pump': few}, calls, {'n': 38, 'medPct': -5.8}, {'n': 22, 'medPct': -70.2}, 'baby')
    assert out['movers'] == {**mine, 'src': 'this list'}                                   # own record once it has 5 settled
    assert out['volume']['medPct'] == -1.1 and out['volume']['src'] == 'volume-leader callout'   # too few → the nearest callout
    assert out['pump']['src'] == 'this list' and out['pump']['n'] == 2                     # nothing to borrow either → its own few
    assert out['ptrend']['src'] == 'this list'                                             # Pump trending never borrows
    assert out['bottom']['medPct'] == -5.8 and out['trench']['src'] == 'trench meta baby'


def test_rush_mode_drops_every_10_min_into_a_losing_unfrozen_pick_and_never_a_frozen_one():
    anchors, pools, runners = _cands()
    base = {'trenchCoins': 1, 'rotateHours': 0.25, 'minHoldMins': 10, 'cycles': {**{t: 'off' for t in ap.DEFAULT_CYCLES}, 'degen': 'trench'}, 'rescuePct': 0, 'cycleEvery': 0,
            'rideAt': 0, 'tp': 0, 'lockBankPct': 0, 'tpStakeUsd': 0, 'skimAt': 0}
    cfg = ap.clean_cfg({**base, 'trenchRush': True, 'trenchEvery': 10})
    assert cfg['trenchRush'] and cfg['trenchEvery'] == 10 and ap.clean_cfg({'trenchEvery': 7})['trenchEvery'] == 30
    card = ap.deal('degen', pools, [x for x in runners if not x.get('trenchOnly')], cfg, 0.0, anchors, shape='degen')
    for l in card['legs']:                                                   # every seat is the OWNER's pick; one frozen
        l['picked'] = True
    frozen = card['legs'][0]; frozen['frozen'] = True
    px = {l['pairAddress']: l['entry'] * 0.8 for l in card['legs']}           # all losing
    for x in runners:
        px.setdefault(x['pairAddress'], x['price'])
    drops = lambda c: sum(1 for e in c['events'] if 'trench drop' in (e.get('why') or ''))
    t0 = 10_000.0
    card['at'] = 0.0
    out = ap.tick({**card, 'trenchFillAt': t0 - 601}, px, pools, runners, cfg, t0, anchors, {}, {})
    assert drops(out) == 1 and frozen['mint'] in {l['mint'] for l in out['legs']}   # a losing pick gave its seat; ❄ frozen never
    plain = ap.tick({**card, 'trenchFillAt': t0 - 601}, px, pools, runners, ap.clean_cfg(base), t0, anchors, {}, {})
    assert drops(plain) == 0                                                  # no rush: your picks are never the engine's to swap, and 30 min


def test_rush_score_mirrors_the_board():
    row = lambda **k: {'safe': True, 'chg5m': 4, 'buyShare': 60, 'site': 's', 'x': 'x', 'tv': {'heat': 60, 'rug': 20, 'call': ['🔥', 'SEND IT']}, **k}
    assert ap.rush_score(row()) == 20 + 18 - 8 + 4 + 5
    assert ap.rush_score(row(safe=None)) is None and ap.rush_score(row(safe=False)) is None   # the engine never buys an unscanned coin
    assert ap.rush_score(row(tv={'heat': 90, 'rug': 10, 'call': ['🧪', 'WASH TRADED']})) is None
    assert ap.rush_score(row(chg5m=20)) is None and ap.rush_score(row(rug=55)) is None and ap.rush_score(row(chg5m=-28)) is None
    assert ap.rush_score(row(brain={'est': 12})) == ap.rush_score(row()) + 12
