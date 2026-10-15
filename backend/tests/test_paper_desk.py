

def test_floor_hold_is_a_dip_holding_higher_lows_on_volume():
    import paper_desk as pd
    row = {'chart': {'distHigh': 22, 'hl': 3, 'll': 0, 'distLow': 8}}
    n = {'buy': 61, 'pace': 1.2, 'holdD': 2, 'd5': 1}
    assert 'floor_hold' in pd.strats(row, n)
    assert 'floor_hold' not in pd.strats({'chart': {**row['chart'], 'll': 1}}, n)        # a lower low = the floor broke
    assert 'floor_hold' not in pd.strats({'chart': {**row['chart'], 'distHigh': 5}}, n)   # not a dip
    assert 'floor_hold' not in pd.strats(row, {**n, 'd5': -6})                           # falling now
    assert 'floor_hold' not in pd.strats({}, n)                                          # no chart read = not judged
