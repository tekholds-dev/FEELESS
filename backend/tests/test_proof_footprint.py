import proof_footprint as fp


A = {'id': 'a', 'n': 1, 'at': 10, 'topic': 'Lakers v Suns', 'shots': [{'site': 'www.espn.com'}], 'sites': ['nba.com'], 'calls': [{'pick': 'Lakers -3'}]}
B = {'id': 'b', 'n': 2, 'at': 20, 'topic': 'best lakers suns picks tonight', 'shots': [{'site': 'espn.com'}], 'sites': ['nba.com'], 'calls': [{'pick': 'Lakers -3'}]}
C = {'id': 'c', 'n': 3, 'at': 30, 'topic': 'Masters golf winner', 'shots': [{'site': 'pgatour.com'}], 'calls': [{'pick': 'Scheffler'}]}


def test_a_repeat_scores_as_a_repeat_and_new_work_as_new():
    same = fp.unique('pob', B, [A])
    assert same['pct'] <= 5 and same['nearest'] == 1 and same['shared'] == ['espn.com', 'nba.com']
    assert fp.unique('pob', C, [A, B])['pct'] == 100 and fp.unique('pob', A, [])['pct'] == 100


def test_only_what_came_before_counts():
    assert [x['id'] for x in fp.before([A, B, C], B)] == ['a'] and fp.before(None, A) == []


def test_two_minds_never_share_a_site_or_an_angle():
    p = fp.plan('pob', 'x', ['espn.com', 'nba.com', 'cbssports.com', 'actionnetwork.com'], [])
    assert not set(p['sites'][0]) & set(p['sites'][1]) and p['sites'][0] and p['sites'][1] and p['angles'][0] != p['angles'][1]


def test_the_loop_moves_on_from_what_the_last_proofs_leaned_on():
    p = fp.plan('pob', 'x', ['espn.com', 'nba.com', 'cbssports.com'], [A, B])
    assert p['sites'][0][0] == 'cbssports.com'   # the two it just used wait
    assert fp.plan('pob', 'x', ['espn.com', 'nba.com'], [])['sites'][0][0] == 'espn.com'   # with no history, the best first


def test_the_minds_read_the_last_footprints_and_their_own_angle():
    t = fp.note('pob', [A, B], 0)
    assert 'LAST FOOTPRINTS' in t and 'espn.com' in t and 'never run its search' in t and fp.angle_for('pob', [A, B], 0)[0] in t   # its angle turns every proof (owner 2026-11-07)
    assert fp.angle_for('pob', [A], 1)[0] in fp.note('pob', [A], 1) and fp.angle_for('pob', [A], 1) != fp.angle_for('pob', [A, B], 1)
    assert fp.note('pob', []).strip().startswith('IF A STEP FAILS')


def test_odd_records_never_break_it():
    assert fp.unique('pop', {'calls': 'bad', 'shots': 7, 'sources': {'0': None}}, [{'browsed': {'0': 'x'}}])['pct'] == 100
    assert fp.footprint('pow', None)['words'] == set()
