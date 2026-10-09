import real_learn as rl
import confluence as cf


def test_a_piece_is_recorded_with_its_buy_features_and_the_table_learns_medians():
    st = {}
    for i, end in enumerate([1.3, 1.2, 1.25, 0.9, 1.4]):   # five old deep-pool coins: mostly winners
        st = rl.note(st, {'mint': f'M{i}', 'entry': 1.0, 'at': 0, 'bought': {'ageH': 30, 'liq': 200e3, 'chg1h': 5, 'buyShare': 60}}, end, 600)
    for i, end in enumerate([0.5, 0.6, 0.7, 0.4, 1.1]):     # five minutes-old pumps: mostly losers
        st = rl.note(st, {'mint': f'Y{i}', 'entry': 1.0, 'at': 0, 'picked': True, 'bought': {'ageH': 0.3, 'liq': 9e3, 'chg1h': 200}}, end, 120)
    t = rl.table(st)
    assert t['age:1-7d']['medPct'] == 25.0 and t['age:<1h']['medPct'] == -40.0 and t['by:you']['n'] == 5
    good, _ = rl.match({'ageH': 40, 'liq': 300e3}, t)
    bad, hits = rl.match({'ageH': 0.2, 'liq': 5e3, 'chg1h': 300}, t)
    assert good > 0 > bad and len(hits) == 3
    assert rl.lessons(t)['best'][0]['medPct'] >= rl.lessons(t)['worst'][0]['medPct']
    assert rl.note({}, {'entry': 0}, 1.0, 0) == {}   # no entry price → no lesson


def test_the_edge_score_reads_your_real_trades():
    t = {'age:<1h': {'n': 9, 'medPct': -40.0}}
    e = cf.edge({'ageH': 0.5}, {}, {}, {}, real_tbl=t)
    assert e['edge'] == -40.0 and any('your real trades' in p[0] for p in e['parts'])


def test_a_leg_with_no_buy_stamp_has_an_unknown_hold_time_not_decades():
    st = rl.note({}, {'entry': 1.0, 'symbol': 'A'}, 1.1, 1_800_000_000)
    assert st['pieces'][0]['holdMin'] is None
    st = rl.note({}, {'entry': 1.0, 'symbol': 'A', 'at': 1_800_000_000 - 600}, 1.1, 1_800_000_000)
    assert st['pieces'][0]['holdMin'] == 10.0


def test_hold_time_is_counted_from_the_buy_time_never_the_entry_price():
    import real_learn as rl
    st = rl.note({}, {'mint': 'm', 'symbol': 'S', 'entry': 1.0, 'firstEntry': 0.0005, 'at': 1000.0, 'bought': {}}, 1.1, 1000.0 + 600)
    assert st['pieces'][-1]['holdMin'] == 10.0
