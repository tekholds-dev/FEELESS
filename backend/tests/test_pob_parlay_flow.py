"""🧩 Refile after a team-to-win bid (owner 2026-11-15 'after the thunder to win bid is in i wona file the same and only see one option for leg
parlay -> max legs -> then they research alil more per kalshi's best odds'). Network faked; nothing reaches Kalshi."""
import time

import kalshi_bid as kb


def test_how_many_legs_answers():
    assert kb.legs_answer('Max legs (4)') == kb.SLIP_MAX == 4
    assert kb.legs_answer('3 legs') == 3 and kb.legs_answer('two') == 2
    assert kb.legs_answer('6 legs') is None and kb.legs_answer('hello') is None
    assert kb.legs_said('Thunder vs Kings parlay slip 4 legs') and kb.legs_said('max legs parlay') and not kb.legs_said('Thunder vs Kings parlay slip')


def test_a_parlay_reads_every_leg_kalshi_will_price_first():
    game = [{'ticker': 'KXNBAGAME-26NOV15OKCSAC-OKC', 'title': 'Oklahoma City wins', 'yes_ask_dollars': '0.81', 'yes_ask': 81, 'status': 'active'}]
    legs = [{'ticker': 'KXNBAPTS-26NOV15OKCSAC-SGA30', 'title': 'SGA 30+ points', 'yes_ask_dollars': '0.48', 'yes_ask': 48, 'no_ask_dollars': '0.54', 'status': 'active'}]
    note = kb.first_note(game, legs)
    assert 'PARLAY LEGS' in note and 'SGA 30+ points' in note and 'Research EACH leg' in note
    assert 'PARLAY LEGS' not in kb.first_note(game)


def _cat(fs, folders):
    return {'id': 'c', 'pobFolders': folders}


def test_after_a_team_to_win_bid_the_refile_offers_only_a_parlay_slip(monkeypatch):
    import feecat_service as fs
    now = time.time()
    bid = {'id': 'f1', 'at': now - 600, 'topic': 'Thunder vs Kings team to win', 'kalshi': {'id': 'kb1', 'title': 'Oklahoma City wins', 'status': 'filled', 'orderId': 'o1'}}
    failed = {'id': 'f0', 'at': now - 900, 'topic': 'Thunder vs Kings team to win', 'kalshi': {'id': 'kb0', 'title': 'Oklahoma City wins', 'status': 'failed', 'orderId': None}}
    assert fs._pob_team_bid(_cat(fs, [bid]), 'Thunder vs Kings', now) == 'Oklahoma City wins'
    assert fs._pob_team_bid(_cat(fs, [failed]), 'Thunder vs Kings', now) == ''          # a refused send never counts as a bid
    assert fs._pob_team_bid(_cat(fs, [bid]), 'Lakers vs Suns', now) == ''               # another game
    assert fs._pob_team_bid(_cat(fs, [{**bid, 'at': now - 3 * 86400}]), 'Thunder vs Kings', now) == ''   # another day
