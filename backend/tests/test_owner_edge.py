import owner_edge as oe


def _pick(i, f, ret, hold=10):
    return ({'mint': f'M{i}', 'symbol': f'S{i}', 'at': 1000.0 * i, 'f': f},
            {'mint': f'M{i}', 'bat': 1000.0 * i + 30, 'cost': 1.0, 'usd': ret, 'ret': ret, 'hold': hold})


def test_join_matches_a_pick_to_the_pieces_opened_right_after_it():
    log, pcs = zip(*[_pick(1, {'chg5m': 5, 'vol1h': 90000}, -0.1)])
    pcs = list(pcs) + [{'mint': 'M1', 'bat': 1000.0 + 5000, 'cost': 9.0, 'usd': 9.0, 'ret': 1.0, 'hold': 5}]   # a much later buy of the same coin is not this pick
    js = oe.join(list(log), pcs)
    assert len(js) == 1 and js[0]['cost'] == 1.0 and round(js[0]['ret'], 2) == -0.1


def test_the_rules_find_chasing_thin_and_the_dip_setup_from_the_owners_numbers():
    assert oe.matches({'chg5m': 8, 'vol1h': 60000}) == ['chase']
    assert oe.matches({'chg5m': 1, 'vol1h': 5000}) == ['thin']
    assert oe.matches({'chg5m': -5, 'vol1h': 120000}) == ['setup']
    assert oe.matches({'chg5m': None, 'vol1h': None}) == []                     # unknown numbers = not judged


def test_warnings_quote_the_owners_record_only_when_that_entry_lost_and_has_a_sample():
    pairs = [_pick(i, {'chg5m': 6, 'vol1h': 80000}, -0.08) for i in range(1, 11)] + [_pick(i, {'chg5m': -5, 'vol1h': 90000}, 0.1) for i in range(11, 21)]
    rec = oe.records([p for p, _ in pairs], [q for _, q in pairs])
    assert rec['rules']['chase']['n'] == 10 and rec['rules']['chase']['wonPct'] == 0 and rec['rules']['setup']['wonPct'] == 100
    w = oe.warnings({'chg5m': 6, 'vol1h': 80000}, rec)
    assert len(w) == 1 and 'mid-pump' in w[0] and '10 picks' in w[0] and '-8%' in w[0]
    assert oe.warnings({'chg5m': -5, 'vol1h': 90000}, rec) == []               # the setup that paid never warns
    assert oe.warnings({'chg5m': 6}, oe.records([], [])) == []                  # no record → no sentence
