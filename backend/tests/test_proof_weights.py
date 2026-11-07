import proof_weights as pw

DEEP = {'scout': [1, 2, 3, 4], 'rounds': 3, 'shots': [{'site': f's{i}.com'} for i in range(5)]}
WON = {'status': 'closed', 'real': True, 'pnlPct': 80, 'tp': 50, 'sl': 30, 'boughtAt': 1000, 'soldAt': 1000 + 3600, 'vitals': {'a': 1}, 'sym': 'WIF', 'at': 5, **DEEP}
FIRST = {'id': 'f', 'at': 1, 'sym': 'BONK', 'shots': [{'site': f's{i}.com'} for i in range(4)]}   # where its line started: the same method, another coin, less work
LOST = {'status': 'closed', 'pnlPct': -19, 'boughtAt': 1000, 'soldAt': 1300}
BIG = {'chars': 60000, 'fns': 80, 'handlers': 12, 'state': 5, 'visuals': 4, 'kits': 3}
TINY = {'chars': 9000, 'fns': 4, 'handlers': 1, 'state': 0, 'visuals': 0, 'kits': 0}
PAGE = {**{'id': 'p', 'at': 9, 'status': 'closed', 'ws': 'w', 'version': 3, 'plan': 'p', 'steps': [1, 2, 3], 'refs': [{'open': True}] * 3, 'graded': 'right', 'topic': 'tool'}}


def test_two_proofs_from_one_agent_no_longer_score_the_same():
    a, b = pw.view('PoW', WON, earlier=[FIRST]), pw.view('PoW', LOST, earlier=[WON])
    assert a['rank'] == 'S' and a['known'] and a['score'] >= 270
    assert b['rank'] == 'D' and b['score'] < 90 and b['frac'] < a['frac']


def test_a_simple_request_done_well_is_not_a_high_score():
    tiny = pw.view('PoStatic', PAGE, earlier=[], page=lambda f: TINY)
    big = pw.view('PoStatic', {**PAGE, 'version': 9}, earlier=[{**PAGE, 'id': 'o', 'at': 1, 'version': 1}], page=lambda f: BIG if f.get('version') == 9 else TINY)
    assert tiny['rank'] in ('C', 'D') and tiny['score'] < 150   # the owner marked it right, it still is simple work
    assert big['rank'] == 'S' and big['score'] > 270            # the same mark on a real build that grew
    assert pw.view('PoStatic', PAGE, earlier=[])['parts'][0]['note'] == 'Page not measured'


def test_more_of_the_same_earns_no_evolution_and_growth_does():
    ev = lambda v: next(p for p in v['parts'] if p['key'] == 'evolve')
    same = pw.view('PoStatic', PAGE, earlier=[{**PAGE, 'id': 'o', 'at': 1}], page=lambda f: BIG)
    grew = pw.view('PoStatic', PAGE, earlier=[{**PAGE, 'id': 'o', 'at': 1, 'version': 1}], page=lambda f: BIG if f['version'] == 3 else TINY)
    first = pw.view('PoStatic', PAGE, earlier=[], page=lambda f: BIG)
    assert ev(same)['value'] == 0 and ev(grew)['value'] == 1 and ev(first)['value'] is None and not first['known']


def test_marked_wrong_or_lost_stays_low_however_much_was_done():
    v = pw.view('PoStatic', {**PAGE, 'graded': 'wrong'}, earlier=[{**PAGE, 'id': 'o', 'at': 1, 'version': 1}], page=lambda f: BIG if f['version'] == 3 else TINY)
    assert v['frac'] == pw.CEIL_FAILED and v['rank'] == 'C' and 'It failed' in v['held']
    assert pw.view('PoW', {**WON, 'pnlPct': -5}, earlier=[FIRST])['frac'] == pw.CEIL_FAILED


def test_no_result_yet_cannot_rank_high():
    v = pw.view('PoStatic', {**PAGE, 'graded': None}, earlier=[{**PAGE, 'id': 'o', 'at': 1, 'version': 1}], page=lambda f: BIG if f['version'] == 3 else TINY)
    assert v['frac'] == pw.CEIL_UNPROVEN and 'Not proven yet' in v['held'] and v['rank'] == 'B'


def test_page_stats_reads_the_code():
    st = pw.page_stats('<script src="k.js"></script><svg></svg><button onclick="a()"></button><script>function a(){setInterval(()=>1,9)}</script>')
    assert st['fns'] == 2 and st['handlers'] == 1 and st['state'] == 1 and st['visuals'] == 1 and st['kits'] == 1 and pw.page_stats('') is None


def test_every_kind_has_its_own_parts_and_weights_add_to_100():
    seen = set()
    for k, rows in pw.RUBRIC.items():
        assert sum(w for _, _, w, _r in rows) == 100, k
        seen.add(tuple(key for key, _, _, _r in rows))
    assert len(seen) == len(pw.RUBRIC)


def test_what_is_not_known_scores_nothing_and_cannot_top_the_board():
    f = {'status': 'closed', 'version': 5, 'plan': 'p', 'steps': [1, 2, 3], 'refs': [{'open': True}] * 3}   # a page nobody marked
    v = pw.view('PoStatic', f)
    assert v['parts'][0]['value'] is None and v['frac'] == 0.2 and not v['known'] and v['rank'] == 'D'
    assert pw.rank_of(0.95, False) == 'A' and pw.rank_of(0.95, True) == 'S'


def test_a_no_trade_is_not_scored_as_a_win_and_bad_data_never_crashes():
    v = pw.view('PoP', {'status': 'closed', 'noTrade': True, 'calls': [], 'reads': [1]})
    assert v['parts'][0]['value'] is None and v['rank'] == 'D'
    assert pw.view('nonsense', {}) is None and pw.view('PoW', None) is None
    assert pw.view('PoW', {'coins': 'bad', 'shots': 7, 'pnlPct': 'x', 'status': 'closed'})['rank'] == 'D'


def test_the_minds_can_correct_but_cannot_talk_up_an_empty_record():
    assert pw.blend(0.1, 300, 300) == round(0.1 * 300 + 0.08 * 300, 1)   # a thin proof stays near its record, however they liked it
    assert pw.blend(0.9, 0, 300) == round(0.6 * 270, 1)                  # they can pull a good-looking record down
    assert pw.blend(0.85, 5, 300, both_reject=True) == 5   # two rejections stand, one does not
    assert pw.blend(1.0, 300, 300) == 300 and pw.blend(0.94, 300, 300) < 300   # flawless takes a full record


def test_the_minds_read_the_facts_with_todays_record():
    line = pw.facts_line(pw.view('PoW', WON, earlier=[FIRST]))
    assert 'FACTS CHECKED BY CODE' in line and 'Real result (weight 25): 100%' in line and 'rank S' in line and pw.facts_line(None) == ''


def _samples():
    # the minds care about evidence far more than the start weights do
    rows = []
    for i in range(16):
        ev = (i % 4) / 3; res = ((i * 3) % 5) / 4
        rows.append({'kind': 'pow', 'parts': {'result': res, 'real': 1.0, 'hold': 1.0, 'unique': 1.0, 'evidence': ev, 'exits': 1.0, 'build': 1.0, 'evolve': 1.0}, 'label': 0.3 + 0.6 * ev})
    return rows


def test_learning_waits_for_enough_and_only_counts_what_beats_unseen_proofs():
    rows = pw.learn(_samples()[:5])
    assert not next(r for r in rows if r['kind'] == 'pow')['ready'] and next(r for r in rows if r['kind'] == 'pow')['weights'] is None
    got = next(r for r in pw.learn(_samples()) if r['kind'] == 'pow')
    assert got['n'] == 16 and got['ready'] and got['learnedMae'] < got['mae']
    assert got['weights']['evidence'] > 5 and got['weights']['evidence'] <= 7.5   # moved toward the minds, inside its limit


def test_the_owners_apply_stays_inside_the_limits_and_changes_the_score(tmp_path):
    d = pw.apply(tmp_path, 'pow', {'result': 999, 'real': 1, 'hold': 10, 'unique': 10, 'evidence': 5, 'exits': 5, 'build': 20, 'evolve': 10})
    assert d['pow']['result'] == 37.5 and d['pow']['real'] == 7.5 and pw.load(tmp_path) == d
    assert pw.view('PoW', LOST, weights=d)['parts'][0]['weight'] == 37.5
    try:
        pw.apply(tmp_path, 'nope', {})
        assert False
    except ValueError:
        pass


def test_one_right_pick_is_not_flawless():
    f = {'id': 'b', 'at': 9, 'topic': 'nba night', 'graded': 'right', 'shots': [{'site': f's{i}.com'} for i in range(6)], 'browsed': {'a': 1, 'b': 2}, 'games': [1, 2, 3], 'calls': [{}, {}], 'agreed': ['a', 'b', 'c']}
    old = {'id': 'o', 'at': 1, 'topic': 'mlb', 'shots': [{'site': f's{i}.com'} for i in range(5)]}
    first = pw.view('PoB', f, earlier=[old]); run = pw.view('PoB', {**f, 'loop': {'wins': 5, 'losses': 0}}, earlier=[old])
    assert first['rank'] == 'A' and not first['known'] and run['rank'] == 'S' and run['frac'] > first['frac']
    assert pw.at_top(first, 500)['score'] == round(first['frac'] * 500, 1) and pw.at_top(None, 500) is None


def test_doing_the_same_thing_again_costs_it():
    f = {**WON, 'id': 'x', 'at': 2, 'sym': 'BONK', 'mint': 'M'}; again = {**f, 'id': 'y', 'at': 3}
    assert pw.view('PoW', f, earlier=[])['score'] > pw.view('PoW', again, earlier=[f])['score']
    assert next(p for p in pw.view('PoW', again)['parts'] if p['key'] == 'unique')['note'] == 'Not compared yet'

