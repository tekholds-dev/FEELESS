import pytest
import limit_orders as lo


def test_limits_fire_once_on_the_cross_and_expire():
    b = lo.make('buy', 1.0, now=0, mint='M', pair='P', symbol='M', target='__seat__', cand={'mint': 'M', 'pairAddress': 'P'})
    s = lo.make('sell', 2.0, now=0, mint='H', pair='PH', symbol='H', pct=50)
    st = lo.make('sell', 0.5, now=0, mint='H2', pair='PH2', symbol='H2', stop=True)
    assert b['cand']['ack'] and s['pct'] == 50 and st['stop']
    card = lo.add(lo.add(lo.add({'legs': []}, b), s), st)
    hit, keep, gone = lo.due(card, {'M': 1.1, 'H': 1.9, 'H2': 0.6}, 10)
    assert not hit and len(keep) == 3
    hit, keep, gone = lo.due(card, {'M': 0.99, 'H': 2.1, 'H2': 0.49}, 10)
    assert {x['symbol'] for x in hit} == {'M', 'H', 'H2'} and not keep
    _, keep, gone = lo.due(card, {}, 25 * 3600)
    assert len(gone) == 3                                    # 24h default
    assert 'BUY $M' in lo.word(b) and '50% $H' in lo.word(s) and '🛑' in lo.word(st)
    assert lo.cancel(card, b['id'])['limits'][0]['id'] != b['id']


def test_bad_limits_are_refused_in_words():
    with pytest.raises(ValueError):
        lo.make('buy', 0, mint='M')
    with pytest.raises(ValueError):
        lo.make('buy', 1, mint='M')                           # no seat / coin
    with pytest.raises(ValueError):
        lo.make('hold', 1)
