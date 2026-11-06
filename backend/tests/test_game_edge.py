"""🏟 The game room reads only what ESPN sent. No network."""
import game_edge as ge


def play(i, a, b, side='1', pts=0, per=1, clock='10:00', kind='JumpShot', **kw):
    return {'id': str(i), 'type': {'text': kind}, 'text': f'p{i}', 'awayScore': a, 'homeScore': b, 'team': {'id': side}, 'scoringPlay': bool(pts), 'scoreValue': pts, 'period': {'number': per}, 'clock': {'displayValue': clock}, **kw}


def test_a_moment_sits_on_the_game_clock():
    assert ge.game_at('cbb', 1, '20:00') == 0 and ge.game_at('cbb', 2, '10:00') == 0.75 and ge.game_at('nba', 5, '3:00') == 1.0 
    assert abs(ge.game_at('mlb', 5, None) - 4 / 9) < 1e-9


def test_plays_drop_the_noise_and_keep_the_score_order():
    data = {'plays': [play(1, 2, 0, pts=2), play(2, 2, 0, kind='Substitution'), play(3, 2, 3, side='2', pts=3)], 'winprobability': [{'playId': '3', 'homeWinPercentage': .6}]}
    rows = ge.plays_of(data, 'cbb', '1')
    assert [r['id'] for r in rows] == ['1', '3'] and rows[0]['side'] == 'a' and rows[1]['side'] == 'b' and rows[1]['wp'] == 0.6 and rows[1]['pts'] == 3


def test_only_the_newest_plays_keep_their_words():
    rows = ge.plays_of({'plays': [play(i, 0, 0) for i in range(5)]}, 'nba', '1', keep_text=2)
    assert 'text' not in rows[0] and rows[-1]['text'] == 'p4'


def test_a_bad_court_spot_is_never_drawn():
    good = ge.plays_of({'plays': [play(1, 0, 0, shootingPlay=True, coordinate={'x': 10, 'y': 5})]}, 'nba', '1')[0]
    bad = ge.plays_of({'plays': [play(1, 0, 0, shootingPlay=True, coordinate={'x': -214748340, 'y': -214748365})]}, 'nba', '1')[0]
    assert good['x'] == 10 and 'x' not in bad


def test_football_plays_come_from_its_drives():
    d = {'drives': {'previous': [{'team': {'id': '1'}, 'plays': [{'id': '9', 'type': {'text': 'Rush'}, 'awayScore': 0, 'homeScore': 0, 'period': {'number': 1}, 'clock': {'displayValue': '15:00'}}]}]}}
    assert ge.plays_of(d, 'nfl', '1')[0]['side'] == 'a'


def test_the_run_counts_back_to_the_other_side():
    assert ge.current_run([{'pts': 2, 'side': 'a'}, {'pts': 0, 'side': 'b'}, {'pts': 3, 'side': 'b'}, {'pts': 2, 'side': 'b'}]) == {'side': 'b', 'pts': 5}
    assert ge.current_run([]) is None


def test_edge_reads_the_line_move_crew_and_pace_and_invents_nothing():
    teams = [{'id': '1', 'abbr': 'WAKE'}, {'id': '2', 'abbr': 'VAN'}]
    data = {'header': {'competitions': [{'status': {'type': {'state': 'in'}}}]}, 'gameInfo': {'officials': [{'displayName': 'Chuck Jones', 'position': {'name': 'Referee'}}]},
            'pickcenter': [{'details': 'VAN -18.5', 'overUnder': 155.5, 'pointSpread': {'home': {'open': {'line': '-16.5'}, 'close': {'line': '-18.5'}}}, 'total': {'over': {'open': {'line': 'o150.5'}, 'close': {'line': 'o155.5'}}}}]}
    plays = ge.plays_of({'plays': [play(1, 40, 46, side='2', pts=3, per=2, clock='10:00')]}, 'cbb', '1')
    e = ge.edge_of(data, 'cbb', teams, plays)
    assert e['crew'][0]['name'] == 'Chuck Jones' and e['moves']['spread'] == {'open': -16.5, 'now': -18.5} and e['pace']['proj'] == round(86 / .75, 1) and 'weather' not in e and 'model' not in e
    says = {r['k']: r for r in ge.reads_of(e, teams)}
    assert 'toward VAN' in says['LINE MOVE']['text'] and says['LINE MOVE']['tone'] == 'b' and 'under the 155.5' in says['PACE']['text']


def test_nothing_sent_means_nothing_read():
    teams = [{'id': '1', 'abbr': 'A'}, {'id': '2', 'abbr': 'B'}]
    e = ge.edge_of({}, 'nba', teams, [])
    assert e == {} and ge.reads_of(e, teams) == []


def test_hot_means_well_off_its_own_season():
    rows = ge.hot_of([{'name': 'H', 'side': 'a', 'stat': 'PTS', 'season': '20', 'recent': 30}, {'name': 'C', 'side': 'b', 'stat': 'PTS', 'season': '10', 'recent': 5}, {'name': 'S', 'side': 'a', 'stat': 'PTS', 'season': '10', 'recent': 11}, {'name': 'Bench', 'side': 'a', 'stat': 'PTS', 'season': '1', 'recent': 9}, {'name': 'None', 'side': 'a', 'stat': 'PTS', 'season': '9', 'recent': None}])
    assert [(r['name'], r['hot']) for r in rows] == [('H', True), ('C', False)]


def test_a_print_ring_ink_counts_less_is_better_the_other_way():
    assert ge.score_change('PTS', 110, 100) == 65 and ge.score_change('TO', 110, 100) == 35 and ge.score_change('PTS', 10, None) == 50


def test_player_print_is_this_season_against_the_one_before():
    rows, season = ge.player_rows({'categories': [{'name': 'averages', 'labels': ['GP', 'FG', 'PTS', '3P%'], 'statistics': [{'season': {'displayName': '2025-26'}, 'stats': ['30', '4-9', '12.0', '30.0']}, {'season': {'displayName': '2026-27'}, 'stats': ['5', '6-9', '18.0', '33.0']}]}]})
    assert season == '2026-27' and [r['abbr'] for r in rows] == ['PTS', '3P%'] and rows[0]['now'] == 18 and rows[0]['last'] == 12 and rows[0]['score'] > 50
    assert ge.player_rows({}) == ([], None)


def test_team_print_keeps_a_stat_with_no_last_season():
    n = {'results': {'stats': {'categories': [{'stats': [{'abbreviation': 'PTS', 'displayName': 'Points', 'displayValue': '80'}, {'abbreviation': 'GP', 'displayValue': '4'}]}]}}}
    rows = ge.team_rows(n, None)
    assert rows == [{'abbr': 'PTS', 'label': 'Points', 'now': 80.0, 'last': None, 'score': 50.0}]
