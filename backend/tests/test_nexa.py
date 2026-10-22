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


P1, P2, P3 = 'A' * 44, 'B' * 44, 'C' * 44


def test_fast_read_is_number_lines_without_pair_addresses_and_maps_tags_back():
    txt, ids = nexa.fast_lines([{'pairAddress': P1, 'symbol': 'BONK', 'cap': 45200, 'ageMin': 12, 'move5m': 3.24, 'status': 'riding'}],
                               [{'pairAddress': P2, 'symbol': 'WIF', 'cap': 1_250_000, 'buyers': 40, 'pool': 12000, 'top10': 22.5, 'germ': 0.3},
                                {'symbol': 'NOPAIR'}, {'pairAddress': P3, 'symbol': 'POPCAT', 'move5m': -7}])
    assert ids == {'O1': P1, 'N1': P2, 'N2': P3}
    assert txt.splitlines() == ['O1 $BONK cap 45K age 12 5m +3.2 riding', 'N1 $WIF cap 1.2M buyers 40 pool 12K top10 22 germ 0.3', 'N2 $POPCAT 5m -7.0']
    assert P1 not in txt and '{' not in txt   # no 44-char addresses, no JSON keys in
    d = nexa.parse_fast('sure: {"exit":["O1"],"avoid":["N2", "O1", "N9"],"favor":[1],"why":"WIF 40 buyers, POPCAT -7% 5m"}', ids)
    assert d == {'avoid': [P3], 'exit': [P1], 'favor': [P2], 'tune': {}, 'lesson': '', 'discovery': '', 'why': 'WIF 40 buyers, POPCAT -7% 5m'}
    assert nexa.parse_fast('no json here', ids) is None
    assert len(nexa.ASK_FAST) < 520 and nexa.FAST_TOK <= 64   # the fast prompt stays short


def test_the_full_read_runs_once_an_hour():
    assert nexa.full_due({}, 1000)
    assert not nexa.full_due({'fullAt': 1000}, 1000 + nexa.FULL_EVERY - 1)
    assert nexa.full_due({'fullAt': 1000}, 1000 + nexa.FULL_EVERY)


def test_lean_full_read_fits_and_parses():
    import nexa as nx
    open_ = [{'pairAddress': 'P' * 44, 'symbol': 'AAA', 'cap': 40000, 'ageMin': 50, 'move5m': 3.2}]
    next_ = [{'pairAddress': 'Q' * 44, 'symbol': 'BBB', 'cap': 22000, 'ageMin': 300}, {'pairAddress': 'R' * 44, 'symbol': 'CCC', 'cap': 9e5, 'ageMin': 4}]
    lines, ids = nx.fast_lines(open_, next_)
    txt = nx.full_text(lines, {'stopPct': 20}, {'stopPct': (10, 30)}, nx.record([]), ['[lesson] dips on fresh coins kill'] * 9)
    assert 'P' * 44 not in txt and 'O1 $AAA' in txt and 'stopPct 20 [10 30]' in txt and txt.count('[lesson]') == nx.FULL_NOTES
    assert 'persona' not in nx.ASK_FULL.lower() and len(nx.ASK_FULL) < 900
    d = nx.parse_full('{"exit":["O1"],"avoid":["N2"],"favor":["N1"],"tune":{"stopPct":25},"lesson":"cap < 30K graduated held","why":"x"}', ids, {'stopPct': 20}, {'stopPct': (10, 30)})
    assert d['exit'] == ['P' * 44] and d['avoid'] == ['R' * 44] and d['favor'] == ['Q' * 44] and d['lesson'].startswith('cap')
    assert nx.parse_full('cut off {"exit":["O1"', ids, {}, {}) is None
