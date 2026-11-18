"""🔎 owner 2026-11-17: "brains shouldnt be cycling through the same sites and dead searching, each site browsed by brain should get a snapshot and
a webscrape to help them identify whats on the page and whats vital". Pure functions; no network."""
import cat_agent as ca
import cat_browser as cb
import kalshi_bid as kb
import page_vital as pv

ESPN = '''[link] ESPN\n[link] NFL\n[link] NBA\n10:30 PM\n[link] Utah Jazz\n[link] LA Clippers\nLAC -5.5\n[link] Gamecast\n[link] Tickets
[link] Utah plays Los Angeles, aims to break road losing streak Utah Jazz (1-13, 15th in the Western Conference)\nSportsNation Poll\nWho will win?'''
WALL = "We're verifying your browser\nVercel Security Checkpoint\niad1::1794967722"


def test_a_page_is_cut_to_what_matters_for_the_task():
    rows = pv.vital(ESPN, 'Jazz vs Clippers parlay slip 2 legs')
    assert 'LAC -5.5' in rows and any('road losing streak' in r for r in rows)
    assert not any(r in ('[link] NFL', '[link] Tickets', '10:30 PM', 'SportsNation Poll') for r in rows)   # menus and noise are dropped
    b = pv.brief(ESPN, 'Jazz vs Clippers', 'espn.com'); assert b.startswith('\n\nWHAT MATTERS ON espn.com') and '• LAC -5.5' in b
    assert 'nothing about your task' in pv.brief('[link] Home\n[link] Menu', 'Jazz vs Clippers', 'x.com')
    assert pv.words_of('Jazz vs Clippers parlay slip 2 legs') == ['jazz', 'clippers'] and 'LAC -5.5' in pv.note(ESPN, 'Jazz vs Clippers')


def test_a_bot_wall_is_dead_remembered_and_never_opened_again():
    assert pv.dead(WALL) and pv.brief(WALL, 'x', 'kalshi.com').startswith('\n\nDEAD PAGE: kalshi.com')
    assert cb.needs_human('https://kalshi.com', WALL) and not pv.dead(ESPN)   # the shared wall check knows Vercel's checkpoint now (Kalshi slipped through, 2026-11-17)
    pv._DEAD.clear(); pv.mark_dead('kalshi.com', now=1000)
    assert pv.is_dead('kalshi.com', now=1000 + 60) and not pv.is_dead('kalshi.com', now=1000 + pv.DEAD_TTL_S + 1) and pv.dead_hosts(now=1001) == {'kalshi.com'}
    pv._DEAD.clear()


def test_a_mind_never_opens_a_site_the_other_mind_read_or_one_that_walled():
    pv._DEAD.clear()
    task = {'keepShots': True, 'readBy': {'foxsports.com': 0}, 'deadHosts': ['kalshi.com']}
    assert 'other mind already read foxsports.com' in ca.taken_why(task, {'i': 1}, 'https://www.foxsports.com/nba')
    assert ca.taken_why(task, {'i': 0}, 'https://foxsports.com/nba/x') is None   # its own site: fine
    assert 'walled' in ca.taken_why(task, {'i': 0}, 'https://kalshi.com/markets')
    assert ca.taken_why(task, {'i': 1}, 'https://html.duckduckgo.com/html/?q=x') is None and ca.taken_why(task, {'i': 1}, 'https://rotowire.com') is None
    assert ca.taken_hosts(task, {'i': 1}) == {'foxsports.com', 'kalshi.com'} and ca.taken_hosts({}, {'i': 1}) == set()


def test_both_minds_start_from_espns_own_facts_for_free():
    d = {'teams': [{'abbr': 'CHA', 'name': 'Charlotte Hornets', 'side': 'away', 'record': '4-9', 'sideRecord': '1-5', 'injuries': [{'name': 'Grayson Allen', 'status': 'Out'}]},
                   {'abbr': 'LAL', 'name': 'Los Angeles Lakers', 'side': 'home', 'record': '12-2', 'sideRecord': '5-1', 'injuries': []}], 'line': 'LAL -6.5', 'total': 221.5, 'wp': [0.78]}
    t = kb.game_facts(d)
    assert t.startswith('GAME FACTS') and 'do not spend steps on espn.com' in t and 'Grayson Allen (Out)' in t and '12-2 overall, 5-1 home' in t
    assert 'Line LAL -6.5, total 221.5.' in t and 'LAL 78%, CHA 22%' in t
    assert 'espn.com/nba/game/_/gameId/9' in kb.game_facts({}, {'id': '9', 'sport': 'nba'}) and kb.game_facts(None) == ''
