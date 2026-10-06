"""FUSE math: legs cleaned, index from launch prices, A–F score with reasons, exact splits, capped creator cut."""
import fuse as f
fuse = f


def test_clean_legs_normalises_and_dedupes():
    legs = f.clean_legs([{'chainId': 'solana', 'pairAddress': 'P1', 'weight': 2}, {'chainId': 'solana', 'pairAddress': 'P1', 'weight': 9},
                         {'chainId': 'solana', 'pairAddress': 'P2', 'weight': 2}, {'chainId': 'solana', 'pairAddress': '', 'weight': 5}, {'chainId': 'solana', 'pairAddress': 'P3', 'weight': 0}])
    assert [(x['pairAddress'], x['weight']) for x in legs] == [('P1', 50.0), ('P2', 50.0)]


def test_index_starts_at_100_and_tracks_weighted_moves():
    legs = [{'pairAddress': 'A', 'weight': 50}, {'pairAddress': 'B', 'weight': 50}]
    assert f.index(legs, {'A': 1, 'B': 2}, {'A': 1, 'B': 2}) == 100
    assert f.index(legs, {'A': 1, 'B': 2}, {'A': 1.2, 'B': 1.8}) == 105.0      # +20% and −10% → +5%
    assert f.index(legs, {'A': 1}, {'A': 2}) == 150.0                          # unknown leg counts as unchanged


def test_score_grades_with_reasons():
    deep = {'liquidityUsd': 5_000_000, 'turnover': 1.2, 'change24h': 3}
    s = f.score([deep, deep])
    assert s['grade'] == 'A' and len(s['parts']) == 4 and s['parts'][0]['why'].startswith('$10,000,000')
    thin = {'liquidityUsd': 2_000, 'turnover': 40, 'change24h': 300}
    assert f.score([thin], risky=2)['grade'] == 'F'


def test_split_sums_exactly_and_creator_cut_is_capped():
    legs = [{'pairAddress': 'A', 'chainId': 'solana', 'weight': 33.33}, {'pairAddress': 'B', 'chainId': 'solana', 'weight': 33.33}, {'pairAddress': 'C', 'chainId': 'solana', 'weight': 33.34}]
    parts = f.split(1, legs)
    assert round(sum(p['sol'] for p in parts), 6) == 1.0
    assert f.creator_cut(2.0, 2500) == 0.5 and f.creator_cut(2.0, 99999) == 1.0 and f.creator_cut(2.0, -5) == 0


def test_leg_meta_apr_estimate():
    m = f.leg_meta({'liquidity': {'usd': 100000}, 'volume': {'h24': 50000}, 'priceChange': {'h24': -4}, 'txns': {'h24': {'buys': 30, 'sells': 10}}, 'baseToken': {'symbol': 'FEE'}})
    assert m['aprEst'] == 45.6 and m['turnover'] == 0.5 and m['buyShare'] == 75


def test_pool_picker_drops_parked_pools_and_sorts_by_volume():
    p = lambda liq, vol, n: {'pairAddress': n, 'liquidity': {'usd': liq}, 'volume': {'h24': vol}}
    out = f.real_pools([p(2.5e9, 0, 'fake'), p(2e8, 50, 'parked'), p(7e5, 8e6, 'busy'), p(3e5, 6e5, 'ok')])
    assert [x['pairAddress'] for x in out] == ['busy', 'ok']


def _pair(pa, vol, liq, chain='solana', created=None, sym='X'):
    return {'chainId': chain, 'pairAddress': pa, 'volume': {'h24': vol}, 'liquidity': {'usd': liq}, 'priceUsd': '1', 'pairCreatedAt': created,
            'baseToken': {'symbol': sym}, 'quoteToken': {'symbol': 'SOL'}, 'priceChange': {'h24': 2}}


def test_discover_lenses_filter_chain_fakes_and_rank():
    pairs = [_pair('a', 1_000_000, 500_000), _pair('b', 100_000, 30_000), _pair('c', 10, 9_000_000),   # c parked
             _pair('d', 900_000, 900_000, chain='base'), _pair('e', 200_000, 10_000, created=99_000_000), _pair('a', 1, 1)]
    pop = fuse.discover(pairs, 'popular')
    assert [r['pairAddress'] for r in pop] == ['a', 'e', 'b']
    assert [r['pairAddress'] for r in fuse.discover(pairs, 'yield')] == ['b', 'a']        # e too shallow for yield
    assert fuse.discover(pairs, 'deep')[0]['pairAddress'] == 'a'
    assert [r['pairAddress'] for r in fuse.discover(pairs, 'new', now_ms=300_000_000)] == ['e']


def test_preview_splits_sol_by_auto_weights_and_sums():
    import fuse_vault
    pools = [{'pairAddress': 'a', 'weight': 1}, {'pairAddress': 'b', 'weight': 1}]
    metas = {'a': fuse.leg_meta(_pair('a', 1_000_000, 500_000, sym='A')), 'b': fuse.leg_meta(_pair('b', 50_000, 30_000, sym='B'))}
    w = fuse_vault.auto_weights(pools, metas)
    p = fuse.preview(pools, metas, 1.5, 200, w)
    assert round(sum(x['sol'] for x in p['legs']), 6) == 1.5 and p['usd'] == 300
    assert {x['symbol'] for x in p['legs']} == {'A', 'B'} and p['score']['grade'] in 'ABCDF'
    assert p['dailyUsd'] > 0 and p['blendedAprPct'] > 0


def test_preview_backtest_and_impact_guard():
    import fuse_vault
    pools = [{'pairAddress': 'a', 'weight': 1}, {'pairAddress': 'b', 'weight': 1}]
    metas = {'a': fuse.leg_meta(_pair('a', 1_000_000, 500_000, sym='A')), 'b': fuse.leg_meta(_pair('b', 5_000, 2_000, sym='B'))}
    p = fuse.preview(pools, metas, 10, 200, fuse_vault.auto_weights(pools, metas))
    assert p['backtest24hPct'] == 2.0 and p['impactWarn'] == ['B']   # every leg moved +2%; $ into B ≫ 1% of its $2K
    assert fuse.legs_cap(False) == 3 and fuse.legs_cap(True) == 12
    assert fuse.manual_weights([{'chainId': 's', 'pairAddress': 'a', 'weight': 3}, {'chainId': 's', 'pairAddress': 'b', 'weight': 1}]) == {'a': 0.75, 'b': 0.25}


def _metas(n=10):
    out = {}
    for i in range(n):
        p = _pair(f'p{i}', 50_000 * (i + 1), 100_000 + 40_000 * i, sym=f'S{i}')
        p['priceChange'] = {'h24': (i - 4) * 3}; p['baseToken']['address'] = f'M{i}'
        out[f'p{i}'] = fuse.leg_meta(p)
    return out


def test_evolution_improves_and_is_deterministic():
    m = _metas()
    a = fuse.evolve(m, legs=3, generations=10, population=16, style='yield', sol=1, sol_usd=150, seed=3)
    b = fuse.evolve(m, legs=3, generations=10, population=16, style='yield', sol=1, sol_usd=150, seed=3)
    assert a['champions'] == b['champions']                                     # seeded → reproducible
    best = [h['best'] for h in a['history']]
    assert best == sorted(best) and len(a['history']) == 10                      # elitism: never gets worse
    c = a['champions'][0]
    assert len(set(c['pools'])) == 3 and abs(sum(c['weights'].values()) - 100) < 0.5
    brute = max(fuse.fitness(list(g), m, 'yield', 1, 150)['fitness'] for g in __import__('itertools').combinations(sorted(m), 3))
    assert c['fitness'] >= brute * 0.97                                          # finds (near) the true best basket


def test_styles_and_fee_drag_change_the_winner():
    m = _metas()
    mo = fuse.evolve(m, legs=2, generations=8, style='momentum', sol=1, seed=1)['champions'][0]['parts']
    st = fuse.evolve(m, legs=2, generations=8, style='steady', sol=1, seed=1)['champions'][0]['parts']
    assert mo['momentum24h'] > st['momentum24h']
    tiny = fuse.fitness(['p1', 'p2', 'p3'], m, 'yield', sol=0.001)
    assert tiny['parts']['feeDragPct'] > 20 and tiny['fitness'] < fuse.fitness(['p1', 'p2', 'p3'], m, 'yield', sol=1)['fitness']


def test_big_cmd_ctr_fuse_weights_still_differ():
    m = _metas(10)
    w = fuse._weights_for(sorted(m), m)
    assert abs(sum(w.values()) - 1) < 1e-4 and max(w.values()) - min(w.values()) > 0.02 and min(w.values()) >= 0.05 - 1e-9


def test_replay_window_never_uses_since_launch_moves():
    now = 1_000_000_000_000
    young = {'pairCreatedAt': now - 3 * 3.6e6, 'priceChange': {'h24': 348700, 'h6': 348700, 'h1': 12.5, 'm5': 2}}
    assert fuse.replay_window(young, now) == (12.5, 1)                      # 3h old → last full hour, not "since launch"
    assert fuse.replay_window({'pairCreatedAt': now - 30 * 3.6e6, 'priceChange': {'h24': -8}}, now) == (-8.0, 24)
    assert fuse.replay_window({'priceChange': {'h24': 5}}, now) == (5.0, 24)                # unknown age → 24h
    assert fuse.replay_window({'pairCreatedAt': now - 60000, 'priceChange': {'m5': 9}}, now) == (0.0, 0)   # 1 min old: nothing honest yet


def test_real_majors_first_impostors_flagged():
    rows = [{'symbol': 'BTC', 'baseAddress': 'PumpFakeBTC', 'liquidityUsd': 9e6},
            {'symbol': 'cbBTC', 'baseAddress': 'cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij', 'liquidityUsd': 2e6},
            {'symbol': 'WBTC', 'baseAddress': '3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh', 'liquidityUsd': 5e5},
            {'symbol': 'MOON', 'baseAddress': 'X', 'liquidityUsd': 1e7}]
    out = fuse.mark_real(rows, 'btc')
    assert [r['symbol'] for r in out] == ['cbBTC', 'WBTC', 'MOON', 'BTC'] and out[-1]['impostor'] and out[0]['real']
    M = 'So11111111111111111111111111111111111111112'
    pools = fuse.majors_pools({M: [{'chainId': 'solana', 'pairAddress': 'small', 'baseToken': {'address': M, 'symbol': 'SOL'}, 'liquidity': {'usd': 1e5}, 'volume': {'h24': 1}},
                                  {'chainId': 'solana', 'pairAddress': 'deep', 'baseToken': {'address': M, 'symbol': 'SOL'}, 'liquidity': {'usd': 9e7}, 'volume': {'h24': 1}},
                                  {'chainId': 'base', 'pairAddress': 'evm', 'baseToken': {'address': M}, 'liquidity': {'usd': 1e9}}]})
    assert [p['pairAddress'] for p in pools] == ['deep'] and pools[0]['real'] and pools[0]['name'].startswith('Solana')


def test_new_majors_lens_keeps_young_big_coins_with_real_volume():
    import fuse as f
    now = 1e12
    P = lambda a, mc, vol, liq, age_d, ch=10: {'chainId': 'solana', 'pairAddress': 'P' + a, 'baseToken': {'address': a, 'symbol': a}, 'quoteToken': {'symbol': 'SOL'},
                                                'marketCap': mc, 'volume': {'h24': vol}, 'liquidity': {'usd': liq}, 'pairCreatedAt': now - age_d * 8.64e7, 'priceChange': {'h24': ch}, 'priceUsd': '1'}
    rows = f.risers([P('PAID', 3e6, 2e6, 4e5, 3), P('OLD', 3e6, 2e6, 4e5, 60), P('TINY', 2e5, 2e6, 4e5, 1), P('DEAD', 3e6, 1e4, 4e5, 2), P('HOOK', 6e6, 4e6, 4e5, 3)], now)
    assert [r['symbol'] for r in rows] == ['HOOK', 'PAID']


def test_new_majors_carry_pumps_top_15():
    import fuse as fz
    mk = lambda i, dex='pumpswap', mc=1e6, liq=2e5, vol=None: {'chainId': 'solana', 'dexId': dex, 'pairAddress': f'PP{i}', 'baseToken': {'address': f'M{i}pump', 'symbol': f'P{i}'},
        'quoteToken': {'symbol': 'SOL'}, 'marketCap': mc, 'liquidity': {'usd': liq}, 'volume': {'h24': vol if vol is not None else 1e5 * (i + 1)}, 'txns': {'h24': {'buys': 10, 'sells': 5}}}
    rows = fz.pump_majors([mk(i) for i in range(20)] + [mk(99, dex='pumpfun'), mk(98, mc=1e4)], have={'M19pump'})
    assert len(rows) == 19 and rows[0]['symbol'] == 'P18' and all(r['pump'] for r in rows)       # up to 40 by volume (19 qualify here), listed coin skipped
    assert len(fz.pump_majors([mk(i) for i in range(20)], top=15)) == 15
    assert not any(r['symbol'] in ('P99', 'P98') for r in rows)                                    # pre-bond curve + tiny mcap out


def test_stocks_are_majors_with_their_own_table_and_need_a_real_pool():
    from fuse import STOCKS, MAJORS, ALL_MAJORS, majors_pools, STOCK_MIN_LIQ
    assert len(STOCKS) <= 30 and not set(STOCKS) & set(MAJORS) and set(ALL_MAJORS) == set(STOCKS) | set(MAJORS)
    assert all(m.startswith('Xs') and sym.endswith('x') for m, (sym, _n) in STOCKS.items())           # xStock mints + tickers only
    nv = next(m for m, v in STOCKS.items() if v[0] == 'NVDAx'); sp = next(m for m, v in STOCKS.items() if v[0] == 'SPYx')
    pair = lambda mint, sym, liq: {'chainId': 'solana', 'pairAddress': 'p' + sym, 'baseToken': {'address': mint, 'symbol': sym}, 'priceUsd': '240', 'liquidity': {'usd': liq}, 'volume': {'h24': 9e6}}
    rows = majors_pools({nv: [pair(nv, 'NVDAx', 5e6), pair(nv, 'NVDAx', 1e5)], sp: [pair(sp, 'SPYx', STOCK_MIN_LIQ - 1)]}, STOCKS)
    assert [r['symbol'] for r in rows] == ['NVDAx'] and rows[0]['stock'] and rows[0]['real'] and rows[0]['liquidityUsd'] == 5e6   # deepest pool; thin = not listed
    assert not any(r.get('stock') for r in majors_pools({nv: [pair(nv, 'NVDAx', 5e6)]}))                # the crypto table never lists a stock
    import fuse_wallet as fw
    assert fw.lookalike('NVDAx', 'FakeMint', ALL_MAJORS) and not fw.lookalike('NVDAx', nv, ALL_MAJORS)   # a fake stock ticker can't be bought
