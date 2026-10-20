import nexa

B = {'hardStop': (-40, -10), 'maxPositions': (1, 8), 'takeProfit1': (20, 150)}
R = {'hardStop': -25.0, 'maxPositions': 4, 'takeProfit1': 60.0}


def test_tune_stays_in_bounds_moves_one_step_and_two_keys_max():
    t = nexa.clamp_tune({'hardStop': -80, 'maxPositions': 8, 'takeProfit1': 61, 'unknown': 5}, R, B)
    assert t['hardStop'] == -29.5           # −80 asked: one 15% step of a 30-pt range from −25
    assert t['maxPositions'] == 5 and isinstance(t['maxPositions'], int)
    assert 'takeProfit1' not in t and 'unknown' not in t   # two keys max, unknown refused


def test_parse_keeps_only_packet_pairs_and_sourced_discoveries():
    d = nexa.parse('blah {"avoid":["P1","ZZ"],"exit":["P2"],"favor":["P1"],"tune":{"hardStop":-20},"lesson":"chasers lose","discovery":"no link here","why":"x"}', ['P1', 'P2'], R, B)
    assert d['avoid'] == ['P1'] and d['exit'] == ['P2'] and d['tune'] == {'hardStop': -20.5} and d['discovery'] == ''
    assert nexa.parse('no json', [], R, B) is None


def test_memory_is_capped_deduped_and_recalled():
    m = []
    for i in range(nexa.MEM_MAX + 30):
        m = nexa.remember(m, 'lesson', f'note {i}', i)
    m = nexa.remember(m, 'lesson', f'note {nexa.MEM_MAX + 29}', 999)
    assert len(m) == nexa.MEM_MAX and m[-1]['at'] == 999
    assert len(nexa.recall(m)) <= 12


def test_calls_are_graded_an_hour_later():
    g = nexa.note_calls([], {'favor': ['A'], 'avoid': ['B']}, {'A': 1.0, 'B': 1.0}, 0)
    g, done = nexa.settle(g, {'A': 1.2, 'B': 0.9}, nexa.GRADE_SEC + 1)
    assert len(done) == 2
    r = nexa.record(g)
    assert r['favor']['rightPct'] == 100 and r['avoid']['rightPct'] == 100
    assert nexa.tune_due({}, 5000, True) and not nexa.tune_due({'tunedAt': 4000}, 5000, True) and not nexa.tune_due({}, 5000, False)
