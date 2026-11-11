"""📺 The watch room's live games (owner 2026-11-10): ESPN's public scoreboard slimmed to what sits beside the stream. No network in tests."""
import game_scores as gs

BOARD = {'events': [
    {'id': '1', 'date': '2026-11-11T03:00Z', 'status': {'type': {'state': 'post', 'shortDetail': 'Final'}}, 'competitions': [{'competitors': [
        {'homeAway': 'home', 'score': '99', 'winner': True, 'team': {'abbreviation': 'AAA', 'shortDisplayName': 'Aces', 'color': '112233'}},
        {'homeAway': 'away', 'score': '90', 'team': {'abbreviation': 'BBB', 'shortDisplayName': 'Bees'}}]}]},
    {'id': '2', 'date': '2026-11-11T01:00Z', 'status': {'type': {'state': 'in', 'shortDetail': '5:54 - 4th'}}, 'competitions': [{'competitors': [
        {'homeAway': 'home', 'score': '106', 'records': [{'summary': '5-4'}], 'team': {'abbreviation': 'NY', 'shortDisplayName': 'Knicks', 'color': '1d428a'}},
        {'homeAway': 'away', 'score': '78', 'team': {'abbreviation': 'MIL', 'shortDisplayName': 'Bucks', 'color': 'zz'}}],
        'situation': {'lastPlay': {'text': 'Knicks timeout', 'probability': {'homeWinPercentage': 0.999}}}, 'broadcasts': [{'names': ['NBA TV']}], 'geoBroadcasts': [{'media': {'shortName': 'MSG'}}]}]},
    {'id': '3', 'status': {'type': {'state': 'pre'}}, 'competitions': [{'competitors': [{'homeAway': 'home', 'team': {}}]}]},   # one side missing: skipped
]}


def test_board_puts_live_games_first_with_win_chance_and_networks():
    rows = gs.slim_board(BOARD)
    assert [r['id'] for r in rows] == ['2', '1']
    live = rows[0]
    assert live['homeWin'] == 99.9 and live['last'] == 'Knicks timeout' and live['tv'] == ['MSG', 'NBA TV']
    assert live['home'] == {'abbr': 'NY', 'name': 'Knicks', 'score': 106, 'color': '#1d428a', 'record': '5-4', 'winner': False}
    assert live['away']['color'] is None   # a bad colour is dropped, never passed on
    assert rows[1]['homeWin'] is None and rows[1]['home']['winner'] is True


def test_game_thins_the_win_line_keeps_the_last_point_and_newest_plays_first():
    raw = {'winprobability': [{'homeWinPercentage': i / 400} for i in range(401)], 'plays': [{'text': f'play {i}', 'clock': {'displayValue': '1:00'}, 'period': {'number': 4}, 'scoringPlay': i % 2 == 0} for i in range(20)],
           'pickcenter': [{'details': 'NY -14.5', 'overUnder': 221.5, 'provider': {'name': 'DraftKings'}}]}
    g = gs.slim_game(raw)
    assert len(g['win']) <= 82 and g['win'][0] == 0.0 and g['win'][-1] == 100.0
    assert [p['text'] for p in g['plays'][:2]] == ['play 19', 'play 18'] and len(g['plays']) == 8
    assert (g['spread'], g['total'], g['by']) == ('NY -14.5', 221.5, 'DraftKings')
    assert gs.slim_game({}) == {'win': [], 'plays': [], 'spread': None, 'total': None, 'by': None}


def test_bad_league_or_event_is_refused_before_any_call():
    import asyncio
    import pytest
    with pytest.raises(ValueError):
        asyncio.run(gs.board(None, 'curling'))
    with pytest.raises(ValueError):
        asyncio.run(gs.game(None, 'nba', '../etc'))
