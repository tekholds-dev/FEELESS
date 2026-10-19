import time
import feecat_service as fs


def _p(**k):
    base = {'quoteToken': {'symbol': 'SOL'}, 'pairCreatedAt': (time.time() - 2 * 3600) * 1000, 'marketCap': 80_000, 'liquidity': {'usd': 20_000},
            'volume': {'h1': 30_000}, 'txns': {'m5': {'buys': 20, 'sells': 10}}, 'priceChange': {'m5': 1.0}, '_status': 'READY'}
    return {**base, **k}


LIM = {'mcMin': 12_000, 'mcMax': 300_000, 'minAgeH': 0.25, 'maxAgeH': 6, 'minVol1h': 5_000, 'poolMin': 8_000}


def test_agents_coin_passes_on_the_agents_band():
    s, why = fs._agents_qualifies(_p(), time.time(), LIM)
    assert s and 'agents lane' in why and 'full' in why


def test_contending_is_half_and_band_still_judges():
    assert 'half' in fs._agents_qualifies(_p(_status='CONTENDING'), time.time(), LIM)[1]
    assert fs._agents_qualifies(_p(marketCap=400_000), time.time(), LIM)[0] is None
    assert fs._agents_qualifies(_p(priceChange={'m5': -9}), time.time(), LIM)[0] is None


def test_her_own_override_sits_on_top_of_the_agents_band():
    lim = fs.agent_lane(LIM, {'mcMax': 50_000, 'junk': 1})
    assert lim['mcMax'] == 50_000 and 'junk' not in lim and lim['poolMin'] == 8_000
    assert fs._agents_qualifies(_p(), time.time(), lim)[0] is None


def test_hq_lane_overrides_keep_only_band_keys_and_empty_follows_the_agents():
    assert fs.clean_lane({'mcMax': '50000', 'mcMin': '', 'poolMin': None, 'hack': 9, 'minAgeH': -1}) == {'mcMax': 50000.0}
    assert fs.clean_lane({}) == {}
