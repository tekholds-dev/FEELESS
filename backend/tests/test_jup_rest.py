"""📡 a refused Jupiter read lane rests instead of being asked again every half second."""
import jup_rest as jr


def test_only_jupiter_reads_are_lanes_and_each_key_and_family_is_its_own():
    assert jr.lane_of('api.dexscreener.com', '/tokens/v1/solana/x') is None
    assert jr.lane_of('api.jup.ag', '/swap/v1/quote', 'k' * 20) is None            # the keeper's quotes are never touched
    a, b = jr.lane_of('api.jup.ag', '/tokens/v2/search', 'a' * 20), jr.lane_of('api.jup.ag', '/tokens/v2/search', 'b' * 20)
    assert a and b and a != b and jr.lane_of('api.jup.ag', '/price/v3', 'a' * 20) != a and jr.lane_of('lite-api.jup.ag', '/tokens/v2/recent')


def test_a_429_rests_the_lane_for_its_retry_after_and_a_good_answer_does_not():
    jr._rest.clear()
    lane = jr.lane_of('lite-api.jup.ag', '/tokens/v2/search')
    jr.note(lane, 200, None, 100.0)
    assert not jr.resting(lane, 100.5)
    jr.note(lane, 429, '4', 101.0)
    assert jr.resting(lane, 104.9) and not jr.resting(lane, 105.1)
    jr.note(lane, 429, None, 200.0)
    assert jr.resting(lane, 200.0 + jr.REST_SEC - 0.1) and not jr.resting(lane, 200.0 + jr.REST_SEC + 0.1)
    assert jr.rest_sec('900') == jr.REST_SEC and jr.rest_sec('x') == jr.REST_SEC and not jr.resting(jr.lane_of('api.jup.ag', '/price/v3', 'z' * 9), 200.0)
    jr._rest.clear()
