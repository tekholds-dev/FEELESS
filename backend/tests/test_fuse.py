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
