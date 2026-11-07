import proof_weights as pw

WON = {'status': 'closed', 'real': True, 'pnlPct': 80, 'tp': 50, 'sl': 30, 'boughtAt': 1000, 'soldAt': 1000 + 3600, 'shots': [1, 2, 3], 'vitals': {'a': 1}, 'whys': {'0': 'x', '1': 'y'}}
LOST = {**WON, 'pnlPct': -19, 'real': False, 'soldAt': 1000 + 300, 'shots': [], 'vitals': None, 'tp': None, 'sl': None}


def test_two_proofs_from_one_agent_no_longer_score_the_same():
    a, b = pw.view('PoW', WON), pw.view('PoW', LOST)
    assert a['rank'] == 'S' and a['score'] == 300 and a['known']
    assert b['rank'] == 'D' and b['score'] < 60 and b['frac'] < a['frac']


def test_every_kind_has_its_own_parts_and_weights_add_to_100():
    seen = set()
    for k, rows in pw.RUBRIC.items():
        assert sum(w for _, _, w, _r in rows) == 100, k
        seen.add(tuple(key for key, _, _, _r in rows))
    assert len(seen) == len(pw.RUBRIC)


def test_what_is_not_known_scores_nothing_and_cannot_top_the_board():
    f = {'status': 'closed', 'version': 5, 'plan': 'p', 'steps': [1, 2, 3], 'refs': [{'open': True}] * 3}   # a page nobody marked
    v = pw.view('PoStatic', f)
    assert v['parts'][0]['value'] is None and v['frac'] == 0.6 and not v['known'] and v['rank'] == 'B'
    assert pw.rank_of(0.95, False) == 'A' and pw.rank_of(0.95, True) == 'S'


def test_a_no_trade_is_not_scored_as_a_win_and_bad_data_never_crashes():
    v = pw.view('PoP', {'status': 'closed', 'noTrade': True, 'calls': [], 'reads': [1]})
    assert v['parts'][0]['value'] is None and v['rank'] == 'D'
    assert pw.view('nonsense', {}) is None and pw.view('PoW', None) is None
    assert pw.view('PoW', {'coins': 'bad', 'shots': 7, 'pnlPct': 'x', 'status': 'closed'})['rank'] == 'D'


def test_the_minds_can_correct_but_cannot_talk_up_an_empty_record():
    assert pw.blend(0.1, 300, 300) == round(0.1 * 300 + 0.15 * 300, 1)   # a thin proof stays near its record, however they liked it
    assert pw.blend(0.9, 0, 300) == round(0.6 * 270, 1)                  # they can pull a good-looking record down
    assert pw.blend(0.85, 5, 300, both_reject=True) == 5   # two rejections stand, one does not
    assert pw.blend(1.0, 300, 300) == 300 and pw.blend(0.94, 300, 300) < 300   # flawless takes a full record


def test_the_minds_read_the_facts_with_todays_record():
    line = pw.facts_line(pw.view('PoW', WON))
    assert 'FACTS CHECKED BY CODE' in line and 'Real result (weight 30): 100%' in line and 'rank S' in line and pw.facts_line(None) == ''


def _samples():
    # the minds care about evidence far more than the start weights do
    rows = []
    for i in range(16):
        ev = (i % 4) / 3; res = ((i * 3) % 5) / 4
        rows.append({'kind': 'pow', 'parts': {'result': res, 'real': 1.0, 'hold': 1.0, 'evidence': ev, 'exits': 1.0, 'minds': 1.0}, 'label': 0.3 + 0.6 * ev})
    return rows


def test_learning_waits_for_enough_and_only_counts_what_beats_unseen_proofs():
    rows = pw.learn(_samples()[:5])
    assert not next(r for r in rows if r['kind'] == 'pow')['ready'] and next(r for r in rows if r['kind'] == 'pow')['weights'] is None
    got = next(r for r in pw.learn(_samples()) if r['kind'] == 'pow')
    assert got['n'] == 16 and got['ready'] and got['learnedMae'] < got['mae']
    assert got['weights']['evidence'] > 15 and got['weights']['evidence'] <= 22.5   # moved toward the minds, inside its limit


def test_the_owners_apply_stays_inside_the_limits_and_changes_the_score(tmp_path):
    d = pw.apply(tmp_path, 'pow', {'result': 999, 'real': 1, 'hold': 15, 'evidence': 22, 'exits': 10, 'minds': 10})
    assert d['pow']['result'] == 45 and d['pow']['real'] == 10 and pw.load(tmp_path) == d
    assert pw.view('PoW', LOST, weights=d)['parts'][0]['weight'] == 45
    try:
        pw.apply(tmp_path, 'nope', {})
        assert False
    except ValueError:
        pass


def test_one_right_pick_is_not_flawless():
    f = {'graded': 'right', 'shots': [1, 2, 3, 4], 'browsed': {'a': 1, 'b': 2}, 'games': [1], 'calls': [{}, {}]}
    first = pw.view('PoB', f); run = pw.view('PoB', {**f, 'loop': {'wins': 5, 'losses': 0}})
    assert first['rank'] == 'A' and first['score'] == 255 and not first['known'] and run['rank'] == 'S' and run['score'] == 300
    assert pw.at_top(first, 500)['score'] == 425 and pw.at_top(None, 500) is None

