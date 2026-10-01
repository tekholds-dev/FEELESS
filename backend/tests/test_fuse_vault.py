"""FUSE Vault engine: the rules the on-chain program mirrors."""
import pytest

import fuse_vault as v

P = [{'pairAddress': 'A', 'kind': 'v2', 'weight': 1, 'capPct': 2}, {'pairAddress': 'B', 'kind': 'v3', 'weight': 1, 'capPct': 2, 'rangePct': 15},
     {'pairAddress': 'C', 'kind': 'v2', 'weight': 1, 'capPct': 2}]
META = {'A': {'liquidityUsd': 5_000_000, 'aprEst': 40}, 'B': {'liquidityUsd': 2_000_000, 'aprEst': 120}, 'C': {'liquidityUsd': 100_000, 'aprEst': 900}}


def test_kind_detection_and_three_pool_limit():
    assert v.kind_of({'dexId': 'raydium', 'labels': ['CLMM']}) == 'v3' and v.kind_of({'dexId': 'orca'}) == 'v2'
    assert v.kind_of({'dexId': 'meteora', 'labels': ['DLMM']}) == 'v3' and v.kind_of({'dexId': 'raydium', 'labels': ['CPMM']}) == 'v2'
    assert len(v.clean_pools(P + [{'pairAddress': 'D'}])) == 3


def test_auto_weights_bounded_and_scale_with_yield_and_depth():
    w = v.auto_weights(v.clean_pools(P), META)
    assert abs(sum(w.values()) - 1) < 1e-6 and all(0.1 - 1e-9 <= x <= 0.7 + 1e-9 for x in w.values())
    assert w['B'] > w['A']                                       # higher fee APR on decent depth wins weight
    dead = v.auto_weights(v.clean_pools(P), {**META, 'B': {'liquidityUsd': 2_000_000, 'aprEst': 0}})
    assert dead['B'] < w['B']                                    # yield collapses → scaled down automatically


def test_allocate_respects_caps_spills_and_buffers():
    pools = v.clean_pools(P)
    room = v.caps_sol(pools, META, {}, sol_usd=200)              # caps: A 500, B 200, C 10 SOL
    assert room == {'A': 500.0, 'B': 200.0, 'C': 10.0}
    alloc, buf = v.allocate(1000, {'A': 0.3, 'B': 0.4, 'C': 0.3}, room)
    assert alloc == {'A': 500.0, 'B': 200.0, 'C': 10.0} and buf == 290.0   # everything capped → rest stays buffered
    alloc, buf = v.allocate(100, {'A': 0.3, 'B': 0.4, 'C': 0.3}, room)
    assert alloc['C'] == 10.0 and round(sum(alloc.values()) + buf, 6) == 100 and buf == 0   # C's overflow spills to A/B
    assert v.capacity(pools, META, 200) == 710.0


def test_shares_withdraw_and_rebalance():
    assert v.shares_for_deposit(10, 0, 0) == 10                  # first deposit 1:1
    assert v.shares_for_deposit(10, 10, 20) == 5                 # NAV doubled → half the shares
    out, take, buf = v.withdraw(5, 10, {'A': 8, 'B': 8}, buffer_sol=4)
    assert out == 10 and buf == 0 and take == {'A': 3.0, 'B': 3.0}
    r = v.rebalance({'A': 9, 'B': 1}, 0, {'A': 0.5, 'B': 0.5}, v3_out_of_range=['B'])
    assert r['moves'] == {'A': -4.0, 'B': 4.0} and r['recenter'] == ['B']
    assert v.rebalance({'A': 5.1, 'B': 4.9}, 0, {'A': 0.5, 'B': 0.5})['moves'] == {}   # inside the drift band: leave it


def test_fees_mgmt_by_time_perf_above_high_water_mark_only():
    fee, hwm = v.fees(100, 100, 1.0, mgmt_bps=200, perf_bps=1000, seconds=v.YEAR)   # flat year: 2% mgmt, no perf
    assert fee == pytest.approx(2.0) and hwm == pytest.approx(1.0)
    fee, hwm = v.fees(120, 100, 1.0, mgmt_bps=0, perf_bps=1000, seconds=0)          # +20% → 10% of 20 SOL
    assert fee == pytest.approx(2.0) and hwm == pytest.approx(1.18)
    assert v.fees(110, 100, 1.18, 0, 1000, 0)[0] == 0                              # below the high-water mark: nothing


def test_simulate_reports_where_money_goes_and_the_fee_wallet_take():
    s = v.simulate(v.clean_pools(P), META, 200, 100, mgmt_bps=100, perf_bps=1000)
    assert round(sum(s['allocation'].values()) + s['bufferSol'], 6) == 100 and s['capacitySol'] == 710.0
    assert s['blendedAprPct'] > 0 and s['yearlyFeeSol'] > 1.0
