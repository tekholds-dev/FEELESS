import time
import feecat_service as fs


def _pair(age_h, now):
    return {'quoteToken': {'symbol': 'SOL'}, 'liquidity': {'usd': 90_000}, 'volume': {'h24': 400_000},
            'marketCap': 2_000_000, 'priceChange': {'m5': 1, 'h1': 10, 'h6': 30, 'h24': 40},
            'txns': {'h1': {'buys': 300, 'sells': 150}}, 'pairCreatedAt': (now - age_h * 3600) * 1000}


def test_core_lane_skips_coins_younger_than_three_days():
    now = time.time()
    # her record: under 6h avg -36%, 1-3d avg -60%, 3d+ +16% — pulled pools were all young
    assert fs._qualifies(_pair(30, now), now)[0] is None
    assert fs._qualifies(_pair(30, now), now)[1] == 'too new'
    assert fs._qualifies(_pair(80, now), now)[0] is not None
