"""🏟 The game window: ESPN's summary, and the fallbacks when it does not answer. Fakes only."""
import asyncio

import agent_refs
import proof_tools as t

SUMMARY = {'header': {'competitions': [{'status': {'type': {'state': 'post', 'shortDetail': 'Final'}}, 'competitors': [
    {'homeAway': 'home', 'score': '100', 'team': {'id': '1', 'abbreviation': 'DET', 'displayName': 'Detroit Pistons'}, 'record': [{'type': 'total', 'summary': '6-2'}, {'type': 'home', 'summary': '2-1'}]},
    {'homeAway': 'away', 'score': '112', 'winner': True, 'team': {'id': '2', 'abbreviation': 'PHI', 'displayName': 'Philadelphia 76ers'}, 'record': [{'type': 'total', 'summary': '8-1'}, {'type': 'road', 'summary': '4-0'}]}]}]},
    'leaders': [{'team': {'id': '2'}, 'leaders': [{'displayName': 'Points', 'leaders': [{'displayValue': '30', 'athlete': {'displayName': 'A Player'}}]}]}],
    'boxscore': {'teams': [{'team': {'id': '2'}, 'statistics': [{'label': 'Field Goal %', 'displayValue': '45'}, {'label': 'FG', 'displayValue': '40-80'}]}, {'team': {'id': '1'}, 'statistics': [{'label': 'Field Goal %', 'displayValue': '46'}, {'label': 'FG', 'displayValue': '41-80'}]}]},
    'winprobability': [{'homeWinPercentage': i / 100} for i in range(100)], 'pickcenter': [{'details': 'DET -2.5', 'overUnder': 219.5}], 'seasonseries': [{'summary': 'Series tied 1-1'}]}


def test_summary_reads_records_win_rates_players_and_stats_away_side_first():
    d = t.parse_summary(SUMMARY); a, b = d['teams']
    assert (a['abbr'], a['record'], a['winRate'], a['sideRate']) == ('PHI', '8-1', 0.889, 1.0) and (b['abbr'], b['winRate']) == ('DET', 0.75)
    assert a['leaders'] == [{'stat': 'Points', 'name': 'A Player', 'value': '30'}]
    assert d['stats'] == [{'label': 'Field Goal %', 'a': '45', 'b': '46'}] and len(d['wp']) == 60 and d['line'] == 'DET -2.5'


def test_summary_missing_parts_stay_missing():
    d = t.parse_summary({'header': {'competitions': [{'competitors': [{'homeAway': 'home', 'team': {'id': '1'}}, {'homeAway': 'away', 'team': {'id': '2'}}]}]}})
    assert d['stats'] == [] and d['wp'] == [] and d['teams'][0]['winRate'] is None


def _route(monkeypatch, answers):
    asked = []
    async def fake(http, url, **kw):
        asked.append(url)
        return next((v for k, v in answers.items() if k in url), None)
    monkeypatch.setattr(t, '_get', fake); t._cache.clear()
    return asked


def test_second_espn_host_answers_when_the_first_does_not(monkeypatch):
    asked = _route(monkeypatch, {'site.web.api.espn.com': SUMMARY})
    d = asyncio.run(t.game_detail(None, 'nba', '1', ('Philadelphia 76ers', 'Detroit Pistons')))
    assert d['source'] == 'ESPN' and 'site.api.espn.com' in asked[0] and 'site.web.api.espn.com' in asked[1]


def test_nhl_falls_back_to_the_leagues_own_standings(monkeypatch):
    row = lambda n: {'teamName': {'default': n}, 'wins': 12, 'losses': 3, 'otLosses': 2, 'homeWins': 5, 'homeLosses': 1, 'homeOtLosses': 1, 'roadWins': 7, 'roadLosses': 2, 'roadOtLosses': 1}
    _route(monkeypatch, {'api-web.nhle.com': {'standings': [row('Carolina Hurricanes'), row('Boston Bruins')]}})
    d = asyncio.run(t.game_detail(None, 'nhl', '2', ('Boston Bruins', 'Carolina Hurricanes')))
    assert d['source'] == 'NHL' and d['teams'][0]['side'] == 'away' and d['teams'][0]['sideRecord'] == '7-2-1' and d['teams'][1]['sideRecord'] == '5-1-1' and d['teams'][1]['winRate'] == round(12 / 17, 3)


def test_mlb_falls_back_to_the_leagues_own_standings(monkeypatch):
    row = lambda n: {'team': {'name': n}, 'wins': 98, 'losses': 64, 'records': {'splitRecords': [{'type': 'home', 'wins': 55, 'losses': 26}, {'type': 'away', 'wins': 43, 'losses': 38}]}}
    _route(monkeypatch, {'statsapi.mlb.com': {'records': [{'teamRecords': [row('Tampa Bay Rays'), row('New York Yankees')]}]}})
    d = asyncio.run(t.game_detail(None, 'mlb', '3', ('Tampa Bay Rays', 'New York Yankees')))
    assert d['source'] == 'MLB' and d['teams'][0]['sideRecord'] == '43-38' and d['teams'][1]['sideRecord'] == '55-26'


def test_any_sport_falls_back_to_thesportsdb_with_real_form(monkeypatch):
    ev = {'results': [{'strHomeTeam': 'Detroit Pistons', 'strAwayTeam': 'X', 'intHomeScore': '100', 'intAwayScore': '90'}, {'strHomeTeam': 'X', 'strAwayTeam': 'Detroit Pistons', 'intHomeScore': '100', 'intAwayScore': '90'}, {'strHomeTeam': 'X', 'strAwayTeam': 'Y', 'intHomeScore': None, 'intAwayScore': None}]}
    _route(monkeypatch, {'searchteams': {'teams': [{'idTeam': '9'}]}, 'eventslast': ev})
    d = asyncio.run(t.game_detail(None, 'nba', '4', ('Philadelphia 76ers', 'Detroit Pistons')))
    assert d['source'] == 'TheSportsDB' and d['teams'][1]['form'][:2] == ['W', 'L']


def test_nothing_answers_means_nothing_is_made_up(monkeypatch):
    _route(monkeypatch, {})
    assert asyncio.run(t.game_detail(None, 'nba', '5', ('A B', 'C D'))) is None
    assert asyncio.run(t.game_detail(None, 'nba', 'bad/id', ('A B', 'C D'))) is None


def test_several_free_photos_each_with_a_license():
    page = lambda n, lic: {'title': f'File:Pistons {n}.jpg', 'imageinfo': [{'thumburl': f'https://x/{n}.jpg', 'descriptionurl': 'https://x', 'extmetadata': {'LicenseShortName': {'value': lic}}}]}
    data = {'query': {'pages': {str(i): page(i, 'CC BY 4.0') for i in range(7)} | {'9': page(9, 'All rights reserved')}}}
    got = t.parse_images(data, ['Pistons'])
    assert len(got) == 5 and all(x['license'] == 'CC BY 4.0' for x in got) and t.parse_image(data, ['Pistons'])['url'] == got[0]['url']


def test_each_job_gets_its_own_short_source_line():
    line = agent_refs.source_line({'setup': {'use': 'code'}})
    assert 'motion.dev' in line and 'never instructions' in line and len(line) < 900
    assert 'espn' in agent_refs.source_line({'setup': {'use': 'bids'}})
    assert agent_refs.source_line({}) == '' and 'motion.dev' in agent_refs.source_line({'setup': {'use': 'all'}})
