import card_dna as dn


def test_every_card_gets_a_unique_dna_that_fits_its_dial_and_stays_stable():
    cards = [{'id': f'c{i}', 'dial': d} for i, d in enumerate(['safe', 'degen', 'balanced', 'degen', 'safe', None])]
    a = dn.assign(cards)
    assert len({dn.sig(d) for d in a.values()}) == len(cards)                       # no two cards alike
    assert a['c1']['cycle'] in ('press', 'classic', 'adaptive') and a['c1']['clock'] <= 1   # degen leans fast + aggressive
    assert a['c0']['payoutPct'] >= 50                                                # safe takes profit out
    again = dn.assign(cards + [{'id': 'new', 'dial': 'degen'}], known=a)
    assert all(again[k] == a[k] for k in a) and dn.sig(again['new']) not in {dn.sig(d) for d in a.values()}


def test_engine_learns_the_winning_dna():
    dna = {'x': dn.clean({'cycle': 'adaptive', 'compound': 'smart', 'payoutPct': 25}), 'y': dn.clean({'cycle': 'press', 'compound': 'even', 'payoutPct': 75})}
    res = [{'winner': 'x', 'loser': 'y'}] * 3 + [{'winner': 'y', 'loser': 'x'}]
    b = dn.best(dn.learn(res, dna))
    assert b['dna']['cycle'] == 'adaptive' and b['dna']['compound'] == 'smart' and b['dna']['payoutPct'] == 25 and b['why']


def test_profit_split_and_smart_compound_skip_fading_coins():
    assert dn.split_profit(100, {'payoutPct': 25, 'compound': 'smart'}) == (25.0, 75.0)
    assert dn.split_profit(100, {'payoutPct': 50, 'compound': 'off'}) == (50.0, 0.0)
    w = dn.compound_weights([{'pairAddress': 'A'}, {'pairAddress': 'B'}, {'pairAddress': 'C'}],
                            {'A': {'chg1h': 20, 'buyShare': 70}, 'B': {'chg1h': -5, 'buyShare': 40}, 'C': {'chg1h': 0, 'buyShare': 50}})
    assert 'B' not in w and w['A'] > w['C'] and abs(sum(w.values()) - 1) < 1e-9
    assert dn.label(dn.clean({'cycle': 'adaptive', 'clock': 0.25})).startswith('🧠 adaptive')


def test_unique_dna_endpoint_never_repeats_a_live_card(monkeypatch):
    import asyncio
    import pytest
    rs = pytest.importorskip('reputation_service')
    held = dn.clean({'cycle': 'adaptive', 'compound': 'smart', 'payoutPct': 50, 'clock': 1, 'stop': 'sell'})
    rs._json_save(rs.FUSE_HQ_PATH, {'cardDna': {'mega:a': held}, 'positions': []})
    got = [asyncio.run(rs.fuse_dna_unique('degen', f's{i}'))['dna'] for i in range(5)]
    assert all(dn.sig(g) != dn.sig(held) for g in got) and got[0]['clock'] <= 1
