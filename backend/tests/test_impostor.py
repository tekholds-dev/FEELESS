import impostor as im


def test_a_small_coin_wearing_a_big_coins_ticker_is_dropped():
    rows = [{'symbol': 'STREAM', 'mint': 'REAL', 'mcap': 20_000_000}, {'symbol': 'STREAM', 'mint': 'FAKE', 'mcap': 40_000},
            {'symbol': 'Stream AI', 'mint': 'FAKE2', 'mcap': 30_000}, {'symbol': 'NEWCOIN', 'mint': 'N', 'mcap': 50_000},
            {'symbol': 'BONK', 'mint': 'B2', 'mcap': 60_000}]
    est = im.established(rows, majors={'BONKREAL': ('BONK', 'Bonk')})
    keep, drop = im.filter_rows(rows, est)
    assert {r['mint'] for r in keep} == {'REAL', 'N'}
    assert {d['mint'] for d in drop} == {'FAKE', 'FAKE2', 'B2'} and 'real $STREAM ($20.0M)' in drop[0]['why']
    # a coin the card holds is established even with no cap reading; a near-size coin is NOT an impostor
    est2 = im.established([], held=[{'symbol': 'MACCA', 'mint': 'M1'}])
    assert im.check({'symbol': 'MACCA', 'mint': 'M2', 'mcap': 20_000}, est2)
    assert im.check({'symbol': 'BIGGY', 'mint': 'X', 'mcap': 900_000}, im.established([{'symbol': 'BIGGY', 'mint': 'Y', 'mcap': 2_000_000}])) is None
