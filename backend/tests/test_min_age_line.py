"""🐣 The owner's youngest-coin line is ENFORCED (it was shown on screen and checked nowhere after the 2026-10-12 refactor)."""
import time

import opportunity as opp
from trench_kernel import universe as uni


def _row(age_h, cap=50_000):
    return {'mint': 'M', 'px': 1.0, 'nums': {'liq': 30_000, 'v5': 5_000, 'tx': 300},
            'vitals': {'safe': True, 'mcap': cap, 'ageH': age_h, 'liq': 30_000, 'vol1h': 20_000}, 'chart': {}}


def teardown_function(_):
    uni.set_band({})


def test_youngest_coin_line_blocks_every_door():
    uni.set_band({'agentMinAgeH': 1, 'agentMcMin': 12_000, 'agentMcMax': 300_000})
    assert uni.min_age() == 1.0
    young = _row(0.05)   # 3 minutes old — where every rug of the night of 10-13 lived
    assert 'youngest-coin line' in (uni.too_young(young['vitals']) or '')
    assert 'youngest-coin line' in (opp.hard_fail(young) or '')
    assert 'youngest-coin line' in (opp.open_ok(young) or '')
    assert not uni.in_lane({'mint': 'M', 'mcap': 50_000, 'vol1h': 20_000, 'ageH': 0.05})
    assert uni.in_lane({'mint': 'M', 'mcap': 50_000, 'vol1h': 20_000, 'ageH': 2})


def test_pump_trending_does_not_waive_the_youngest_line():
    uni.set_band({'agentMinAgeH': 1, 'agentPumpTrend': 'first'})
    uni.set_trending(['M'])
    assert not uni.in_lane({'mint': 'M', 'mcap': 50_000, 'vol1h': 20_000, 'ageH': 0.1})
    uni.set_trending([])


def test_off_means_any_age_and_unlisted_values_are_ignored():
    uni.set_band({'agentMinAgeH': 0})
    assert uni.too_young({'ageH': 0.01}) is None
    uni.set_band({'agentMinAgeH': 0.7})   # not an option → any age, never a made-up line
    assert uni.min_age() == 0.0
    assert time.time() > 0
