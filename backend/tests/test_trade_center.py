import trade_center as tc

CARD = {'seats': [{'kind': 'g4', 'model': 'OSSY', 'symbol': 'AAA', 'pair': 'P1', 'pct': 12.0}, {'kind': 'g4', 'model': 'G4', 'symbol': 'BBB', 'pair': 'P2', 'pct': -4.0},
                  {'kind': 'agent', 'symbol': 'CCC', 'pair': 'P3', 'pct': 3.0, 'action': 'hold', 'why': 'riding'}, {'kind': 'open', 'symbol': None}]}


def test_public_sees_the_aggregate_never_the_coins():
    s = tc.summary(CARD)
    assert s['open'] == 3 and s['green'] == 2 and s['avgPct'] == 3.7 and 'rows' not in s
    assert s['by'] == {'AGENTS': {'n': 1, 'avgPct': 3.0}, 'G4': {'n': 1, 'avgPct': -4.0}, 'OSSY': {'n': 1, 'avgPct': 12.0}}
    assert 'AAA' not in str(s)


def test_staff_see_every_seat_with_its_model():
    s = tc.summary(CARD, staff=True)
    assert [r['who'] for r in s['rows']] == ['OSSY', 'G4', 'agent'] and s['rows'][2]['why'] == 'riding'
    assert tc.summary(None) == {'open': 0, 'green': 0, 'avgPct': None, 'by': {}, 'staff': False}
