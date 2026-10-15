import candle_clock as cc


def test_the_candle_clock_waits_only_in_the_first_100s_of_a_5m_candle():
    assert cc.clock(1000) == {'s1': 40, 'left1': 20, 's5': 100, 'left5': 200}
    assert cc.wait_why(900 + 30) and '30s old' in cc.wait_why(930)
    assert cc.wait_why(900 + 150) is None
    assert cc.wait_why(930, {'candleClock': False}) is None
    assert 'EARLY' in cc.line(930) and 'EARLY' not in cc.line(1050)
