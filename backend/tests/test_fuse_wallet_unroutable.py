import fuse_wallet as fw


def test_a_coin_jupiter_cannot_route_is_benched_at_once_not_retried_forever():
    b, benched = fw.note_miss({}, 'M', 1000.0, 'The token M is not tradable (HTTP 400)')
    assert benched and 'M' in fw.benched(b, 1001.0)
    b2, benched2 = fw.note_miss({}, 'M', 1000.0, 'slippage exceeded')
    assert not benched2
