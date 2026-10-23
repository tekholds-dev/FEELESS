"""🪟 NEXA's lane: her fresh YES is FeeCat's lane (2026-10-23: FeeCat's own lanes passed 0 of 42 coins, so NEXA never traded) — but a pool
she can't exit (under $5K) never passes, and her YES is never a lane for a cat that isn't hers (cat_model.buy_ok still gates the buy)."""
import feecat_service as fs
import cat_model as cm


def test_nexa_yes_is_the_lane_but_never_past_the_pool_floor():
    assert fs.nexa_lane({'liquidity': {'usd': 42000}}) == (1.0, '🪟 NEXA said YES')
    score, why = fs.nexa_lane({'liquidity': {'usd': 3000}})
    assert score is None and 'no exit' in why
    assert fs.nexa_lane({})[0] is None


def test_only_her_fresh_picks_pass_her_gate():
    read = cm.read_of({'favor': ['P1'], 'avoid': ['P2'], 'at': 1000.0}, now=1100.0)
    assert cm.buy_ok(read, 'P1')[0] is True and cm.buy_ok(read, 'P2')[0] is False and cm.buy_ok(read, 'P3')[0] is False
    assert cm.read_of({'favor': ['P1'], 'at': 1000.0}, now=1000.0 + cm.FRESH_SEC + 1) is None   # stale → her cat waits
