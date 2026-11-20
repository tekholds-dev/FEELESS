"""🎲 Slice 13 · the PoB folder dashboard (owner: "make PoB a sleek dashboard that views everything beautifully when I / a user opens the PoB
folder: either build their own or see what to have the agent file"). Network faked; nothing reaches Kalshi; a TEST never bids."""
import asyncio
import json
import time

import pytest

import kalshi_bid as kb
import pob as _pob
import pob_dash as pd

NOW = 1795100000.0   # 2026-11-19 ~16:53 UTC
ISO = lambda dt: time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime(NOW + dt))   # noqa: E731


def _bid(outcome, count=2, price=0.68, filled=2, **kw):
    return {'id': 'k1', 'ticker': 'KXNBAGAME-26NOV19MILMIA-MIL', 'side': 'yes', 'title': 'Milwaukee wins', 'orderId': 'o1', 'status': 'filled',
            'count': count, 'filled': filled, 'price': price, 'usd': count * price, 'outcome': outcome, 'settledAt': NOW - 100, **kw}


ROWS = [
    {'id': 'pob1', 'n': 1, 'at': NOW - 9000, 'status': 'closed', 'topic': 'Jazz vs Clippers team to win', 'kalshi': _bid('lost', price=0.68, fees=0.07),
     'review': {'score': 30, 'verdict': 'fail', 'by': {'ossy': {}, 'g4': {}}}},
    {'id': 'pob2', 'n': 2, 'at': NOW - 5000, 'status': 'closed', 'topic': 'Bucks vs Heat team to win', 'kalshi': _bid('won', price=0.85, fees=0.03),
     'review': {'score': 60, 'verdict': 'fail', 'by': {'ossy': {}}}},
    {'id': 'pob3', 'n': 3, 'at': NOW - 4000, 'status': 'closed', 'topic': 'Bucks vs Heat parlay slip 3 legs', 'kalshi': {'kind': 'parlay', 'status': 'refused', 'legs': [{}], 'end': {'say': 'No market maker quoted. Nothing was bought.'}},
     'review': {'score': None, 'why': 'Every judge built this proof, so none may judge it', 'recused': ['ossy', 'g4']}},
    {'id': 'pob4', 'n': 4, 'at': NOW - 3000, 'status': 'closed', 'topic': 'Knicks vs Timberwolves tonight', 'testRun': True, 'kalshi': {'status': 'waiting', 'test': True}},
]


# ── the numbers: P&L without fees, results, judges ─────────────────────────────────────────────────────────────────────────────────────
def test_pnl_is_payout_minus_money_that_reached_kalshi_never_fees():
    d = pd.build(ROWS, {}, [], NOW)
    t = d['totals']
    # lost: 0 − 2×0.68 = −1.36 · won: 2×1.00 − 2×0.85 = +0.30 → −1.06; the 0.07 and 0.03 fees on the receipts are never in it (§1)
    assert t['pnl'] == -1.06 and t['cost'] == 3.06 and (t['won'], t['lost'], t['real'], t['live']) == (1, 1, 2, 0)
    assert [p['pnl'] for p in d['curve']] == [-1.36, -1.06]   # cumulative, oldest settled first
    assert t['judged'] == 2 and t['avg'] == 45 and t['tests'] == 1


def test_each_filing_says_its_result_and_its_judges_in_plain_words():
    rows = {r['id']: r for r in pd.build(ROWS, {}, [], NOW)['rows']}
    assert [rows[i]['result'] for i in ('pob1', 'pob2', 'pob3', 'pob4')] == ['lost', 'won', 'refused', 'test']
    assert rows['pob2']['pnl'] == 0.3 and rows['pob2']['mode'] == 'team' and rows['pob3']['mode'] == 'parlay'
    assert rows['pob1']['judge'] == {'state': 'scored', 'score': 30, 'verdict': 'fail', 'by': ['g4', 'ossy'], 'agree': None}
    assert rows['pob3']['judge']['state'] == 'none' and 'Every judge built' in rows['pob3']['judge']['why']
    assert rows['pob3']['ticket']['say'].startswith('No market maker') and rows['pob4']['judge']['state'] == 'waiting'
    assert [r['id'] for r in pd.build(ROWS, {}, [], NOW)['rows']] == ['pob4', 'pob3', 'pob2', 'pob1']   # newest first


def test_an_open_real_bid_is_at_risk_not_pnl():
    row = {'id': 'pob9', 'at': NOW, 'status': 'closed', 'topic': 'Kings vs Maple Leafs team to win', 'kalshi': {**_bid(None), 'livePx': 0.7}}
    t = pd.build([row], {}, [], NOW)['totals']
    assert t['pnl'] == 0 and t['live'] == 1 and t['atRisk'] == 1.36 and pd.build([row], {}, [], NOW)['rows'][0]['result'] == 'live'


# ── fresh stash odds (COMP's reference), degrading cleanly ─────────────────────────────────────────────────────────────────────────────
REFS = {
    '1': {'id': '1', 'sport': 'nhl', 'label': 'Kings at Maple Leafs', 'start': ISO(3 * 3600), 'teams': ['kings', 'maple leafs'], 'names': ['Los Angeles Kings', 'Toronto Maple Leafs'],
          'abbr': {'kings': 'LA', 'maple leafs': 'TOR'}, 'fav': {'espn.com': 'maple leafs', 'kalshi.com': 'maple leafs'}, 'line': 'TOR -115', 'total': 6.5,
          'chance': {'kings': {'kalshi': 0.48, 'chance': 0.40}, 'maple leafs': {'kalshi': 0.53, 'chance': 0.60}}, 'at': NOW - 600},
    '2': {'id': '2', 'sport': 'nba', 'label': 'Bucks at Heat', 'start': ISO(5 * 3600), 'teams': ['bucks', 'heat'], 'names': ['Milwaukee Bucks', 'Miami Heat'],
          'fav': {'kalshi.com': 'bucks', 'polymarket.com': 'heat'}, 'chance': {'bucks': {'kalshi': 0.55}, 'heat': {'kalshi': 0.46}}, 'at': NOW - 3 * 3600},
    '3': {'id': '3', 'sport': 'nba', 'label': 'Old at Game', 'start': ISO(-3600), 'teams': ['a', 'b'], 'chance': {}, 'at': NOW - 600},
    '4': {'id': '4', 'sport': 'cbb', 'label': 'Florida at West Virginia', 'start': ISO(2 * 3600), 'teams': ['florida gators', 'west virginia mountaineers'],
          'names': ['Florida Gators', 'West Virginia Mountaineers'], 'chance': {'florida gators': {'kalshi': 0.78}, 'west virginia mountaineers': {'kalshi': 0.23}}, 'at': NOW - 600},
}


def test_stash_odds_are_games_not_started_soonest_first_with_their_age():
    od = pd.odds(REFS, NOW)
    assert [o['label'] for o in od] == ['Florida at West Virginia', 'Kings at Maple Leafs', 'Bucks at Heat']   # a started game is gone
    k = od[1]
    assert [(t['short'], t['kalshi'], t['poly']) for t in k['teams']] == [('Kings', 0.48, 0.40), ('Maple Leafs', 0.53, 0.60)]
    assert k['agree'] and not k['stale'] and k['age'] == 600 and od[2]['stale'] and not od[2]['agree']   # 3 h old: stale; sources split


def test_no_stash_still_opens_the_dashboard():
    d = pd.build(ROWS, None, None, NOW)
    assert d['odds'] == [] and d['oddsAt'] is None and d['next'] == [] and d['live'] == [] and d['totals']['filings'] == 4
    json.dumps(d)


# ── what to file next ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_next_files_are_the_exact_words_the_pob_door_reads():
    nx = pd.suggest(pd.odds(REFS, NOW), [], [], NOW)
    assert [n['teams'] for n in nx] == [['Kings', 'Maple Leafs'], ['Bucks', 'Heat']]   # no college side: its words name no Kalshi series
    k = nx[0]
    assert [f['topic'] for f in k['files']] == ['Kings vs Maple Leafs team to win', 'Kings vs Maple Leafs parlay slip 3 legs']
    assert 'differ by 8 pts on Kings' in k['why']   # the markets' own numbers, said so
    for f in k['files']:
        assert kb.mode_of(f['topic']) == ('team' if f['mode'] == 'team' else 'parlay') and kb.series_for(f['topic'])
    assert _pob.legs_of(k['files'][1]['topic']) == 3 and _pob.game_key(k['files'][0]['topic']) == _pob.game_key(k['files'][1]['topic'])


def test_next_skips_games_bid_waiting_or_about_to_start():
    bid = {'id': 'p', 'at': NOW, 'topic': 'Bucks vs Heat team to win', 'kalshi': _bid(None)}
    nx = {n['key']: n for n in pd.suggest(pd.odds(REFS, NOW), [], [bid], NOW)}
    assert [f['mode'] for f in nx['2']['files']] == ['parlay'] and 'already bid' in nx['2']['why']   # its team is bid: the slip is what is left
    wait = {'id': 'w', 'at': NOW, 'topic': 'Kings vs Maple Leafs team to win', 'kalshi': {'status': 'waiting'}}
    assert '1' not in {n['key'] for n in pd.suggest(pd.odds(REFS, NOW), [], [wait], NOW)}   # a ticket waits for his tap there
    soon = {**REFS['1'], 'start': ISO(5 * 60)}
    assert pd.suggest(pd.odds({'1': soon}, NOW), [], [], NOW) == []   # 5 min out: no time for the minds to read
    board = [{'id': '9', 'sport': 'nba', 'state': 'pre', 'at': ISO(2 * 3600), 'teams': [{'short': 'Knicks', 'kalshi': 0.5, 'chance': 0.5}, {'short': 'Timberwolves', 'kalshi': 0.51, 'chance': 0.49}]}]
    assert pd.suggest([], board, [], NOW)[0]['files'][0]['topic'] == 'Knicks vs Timberwolves team to win'   # no stash: the live board still suggests


def test_live_games_flag_the_ones_it_filed_on():
    board = [{'id': '7', 'sport': 'nba', 'state': 'in', 'status': 'Q3 4:10', 'teams': [{'short': 'Bucks', 'score': '70'}, {'short': 'Heat', 'score': '66'}]},
             {'id': '8', 'sport': 'nhl', 'state': 'in', 'status': '2nd', 'teams': [{'short': 'Blues'}, {'short': 'Penguins'}]},
             {'id': '9', 'sport': 'nba', 'state': 'pre', 'teams': [{'short': 'A'}, {'short': 'B'}]}]
    lv = pd.live_games(board, ROWS)
    assert [(g['label'], g['mine']) for g in lv] == [('Bucks vs Heat', True), ('Blues vs Penguins', False)]


# ── his own slip: the same checks ──────────────────────────────────────────────────────────────────────────────────────────────────────
KD = 'KXNBAPTS-26NOV18HOUIND-HOUKDURANT7-20'; PS = 'KXNBAPTS-26NOV18HOUIND-INDPSIAKAM43-20'; WIN = 'KXNBAGAME-26NOV18HOUIND-HOU'


def test_his_slip_is_checked_before_anything_files():
    ok, why = pd.slip_clean([{'ticker': KD, 'side': 'yes', 'title': 'Durant OVER 19.5'}, {'ticker': PS.lower(), 'side': 'NO'}])
    assert not why and [(g['ticker'], g['side']) for g in ok] == [(KD, 'yes'), (PS, 'no')]
    bad = [([{'ticker': KD, 'side': 'yes'}], '2 to 4 legs'),
           ([{'ticker': KD, 'side': 'yes'}] * 2, 'twice'),
           ([{'ticker': 'DROP TABLE', 'side': 'yes'}, {'ticker': PS, 'side': 'no'}], 'Kalshi market'),
           ([{'ticker': KD, 'side': 'maybe'}, {'ticker': PS, 'side': 'no'}], 'side'),
           ([{'ticker': f'{KD[:-2]}{n}', 'side': 'yes'} for n in (15, 20, 25, 30, 35)], '2 to 4 legs'),
           ([{'ticker': KD, 'side': 'yes'}, {'ticker': KD[:-2] + '25', 'side': 'yes'}], 'repeat each other'),
           ([{'ticker': WIN, 'side': 'yes'}, {'ticker': 'KXNBAGAME-26NOV18HOUIND-IND', 'side': 'yes'}], 'fight each other'),
           ([{'ticker': KD, 'side': 'yes'}, {'ticker': 'KXNHLGAME-26NOV19LATOR-TOR', 'side': 'yes'}], 'one game')]   # 🛡 review: a leg on another game
    for legs, want in bad:
        assert pd.slip_clean(legs)[1] and want in pd.slip_clean(legs)[1], legs


@pytest.fixture
def door(monkeypatch):
    import feecat_service as fs
    cat = {'id': 'c1', 'chat': []}; store = {'cats': {'c1': cat}}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None)
    monkeypatch.setattr(fs, '_owner_gate', lambda *a, **k: None); monkeypatch.setattr(fs, '_proof_room', lambda *a, **k: None)
    monkeypatch.setattr(fs, '_POB_WANT', {}); monkeypatch.setattr(fs, '_TEST_ON', {})
    return fs, cat


def test_the_door_files_his_slip_as_a_parlay_of_his_legs(door):
    fs, cat = door
    legs = [{'ticker': KD, 'side': 'yes', 'title': 'Durant OVER 19.5 points'}, {'ticker': PS, 'side': 'no', 'title': 'Siakam UNDER 19.5 points'}]
    out = asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='pob', text='Rockets vs Pacers team to win', tools={'slip': legs}, session='s')))
    assert out['topic'] == 'Rockets vs Pacers parlay slip 2 legs' and cat['pobAsk'] == out['topic'] and cat['pobBy'] == 'you'
    assert [g['ticker'] for g in cat['pobSlip']['legs']] == [KD, PS] and fs._POB_WANT['c1'] == 'start'
    with pytest.raises(fs.HTTPException, match='2 to 4'):
        asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='pob', text='Rockets vs Pacers', tools={'slip': legs[:1]}, session='s')))


def test_a_suggestion_tap_files_through_the_same_door_and_a_test_is_marked(door):
    fs, cat = door
    cat['pobSlip'] = {'topic': 'old', 'legs': []}
    asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='pob', text='Kings vs Maple Leafs team to win', session='s')))
    assert cat['pobAsk'] == 'Kings vs Maple Leafs team to win' and cat['pobBy'] == 'you' and 'pobSlip' not in cat   # an old slip never rides along
    cat.pop('pobAsk'); fs._TEST_ON[('c1', 'pob')] = {'at': time.time()}
    asyncio.run(fs._cat_work('c1', fs.WorkPayload(op='pob', text='Kings vs Maple Leafs team to win', session='s', auto=True)))
    assert cat['pobBy'] == 'test'   # a TEST through the dashboard's door never bids


def test_the_slip_rides_only_with_its_own_game():
    import fc_pob
    cat = {'pobSlip': {'topic': 'Rockets vs Pacers parlay slip 2 legs', 'legs': [{'ticker': KD, 'side': 'yes'}]}}
    assert fc_pob._slip_for(dict(cat), 'Knicks vs Timberwolves parlay slip 2 legs') is None
    assert fc_pob._slip_for(dict(cat), 'Rockets vs Pacers team to win') is None   # 🛡 review: a later chat PoB on the same game never inherits it
    c = dict(cat)
    assert fc_pob._slip_for(c, 'Rockets vs Pacers parlay slip 2 legs') == [{'ticker': KD, 'side': 'yes'}] and 'pobSlip' not in c


# ── his slip end to end through the minds (faked network) ─────────────────────────────────────────────────────────────────────────────
def _rung(player, key, n, yes, series='KXNBAPTS'):
    return {'ticker': f'{series}-26NOV18HOUIND-{key}-{n}', 'event_ticker': f'{series}-26NOV18HOUIND', 'status': 'active', 'close_time': '2099-01-01T00:00:00Z',
            'yes_ask_dollars': f'{yes:.2f}', 'no_ask_dollars': f'{1 - yes + 0.02:.2f}', 'floor_strike': n - 0.5, 'yes_sub_title': f'{player}: {n}+', 'title': f'{player}: {n}+ points'}


MKT = {'ticker': WIN, 'event_ticker': 'KXNBAGAME-26NOV18HOUIND', 'status': 'active', 'close_time': '2099-01-01T00:00:00Z', 'yes_ask_dollars': '0.60', 'no_ask_dollars': '0.42', 'yes_sub_title': 'Houston', 'title': 'Houston at Indiana Winner?'}
MENU = [MKT, _rung('Kevin Durant', 'HOUKDURANT7', 20, 0.63), _rung('Pascal Siakam', 'INDPSIAKAM43', 20, 0.51)]
ZUB = _rung('Ivica Zubac', 'INDIZUBAC40', 10, 0.55, 'KXNBAREB')   # on Kalshi, but not on today's menu any more
SLIP = [{'ticker': KD, 'side': 'yes', 'title': 'Durant OVER 19.5 points'}, {'ticker': PS, 'side': 'no', 'title': 'Siakam UNDER 19.5 points'}]


@pytest.fixture
def filer(monkeypatch, tmp_path):
    import feecat_service as fs
    monkeypatch.setattr(fs, 'POWSHOTS_DIR', tmp_path); monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: 'x')
    monkeypatch.setattr(fs, '_KB_SENT', {}); monkeypatch.setattr(fs, '_KB_LEDGER', {})

    async def markets_for(h, topic, games=None): return [MKT]
    async def legs_menu(h, games): return MENU
    async def market(h, t): return ZUB if t == ZUB['ticker'] else None
    async def empty(*a, **k): return {}
    async def none(*a, **k): return None
    async def nada(*a, **k): return []
    async def players(*a, **k): return []
    monkeypatch.setattr(kb, 'markets_for', markets_for); monkeypatch.setattr(kb, 'legs_menu', legs_menu); monkeypatch.setattr(kb, 'market', market)
    monkeypatch.setattr(kb, 'team_players', players)   # ESPN's season lines: faked, never the network
    monkeypatch.setattr(fs._tools, 'best_topic', none); monkeypatch.setattr(fs._tools, 'sport_board', empty); monkeypatch.setattr(fs._tools, 'markets', nada)
    sent = []

    async def send(cat, tk): sent.append(tk)
    monkeypatch.setattr(fs, '_kalshi_slip_send', send); monkeypatch.setattr(fs, '_kalshi_send', send)
    fs._WORK.clear()
    return fs, sent


def _answer(legs):
    return json.dumps({'picks': [{'pick': t, 'confidence': c, 'evidence': f'espn.com: he averages {n} this season', 'number': n, 'kalshi': {'ticker': t, 'side': s}} for t, s, c, n in legs]})


def _file(fs, monkeypatch, answers, slip=SLIP, by='you'):
    asks = []

    async def ask(cat, i, sys_, user_, n, box):
        asks.append(user_); return answers[i]
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    cat = {'id': 'c', 'chat': [], 'brainsCfg': {'brains': ['local/ossy', 'local/g4']}}
    notes = {'0': {'note': 'x' * 100}, '1': {'note': 'y' * 100}}
    asyncio.run(fs._pob_file_safe(cat, {'topic': 'Rockets vs Pacers parlay slip 2 legs', 'by': by, 'slip': slip}, 5000.0, notes, ''))
    return cat['pobFolders'][-1], asks


def test_both_minds_back_his_whole_slip_so_it_goes_through_as_his(filer, monkeypatch):
    fs, sent = filer
    a = _answer([(KD, 'yes', 80, 27.4), (PS, 'no', 75, 14.8)])
    f, asks = _file(fs, monkeypatch, [a, a])
    assert 'THE OWNER BUILT THIS SLIP HIMSELF' in asks[0] and KD in asks[0] and WIN not in asks[0]   # only his legs are on the minds' menu
    assert f['userSlip']['whole'] and 'Both minds back every leg' in f['userSlip']['say']
    k = f['kalshi']
    assert k['offer'] == 'you' and [(g['ticker'], g['side']) for g in k['legs']] == [(KD, 'yes'), (PS, 'no')] and sent == [k]   # same send path as any agreed slip


def test_a_flipped_or_unbacked_leg_stops_his_slip_and_says_which(filer, monkeypatch):
    fs, sent = filer
    a = _answer([(KD, 'yes', 80, 27.4), (PS, 'no', 75, 14.8)]); b = _answer([(KD, 'yes', 80, 27.4), (PS, 'yes', 70, 21.0)])
    f, _ = _file(fs, monkeypatch, [a, b])
    assert not f['userSlip']['whole'] and 'Siakam UNDER 19.5 points: ossy backs it, g4 flipped it' in f['userSlip']['say']
    assert sent == [] and (f.get('kalshi') or {}).get('kind') != 'parlay' and f['slipDropped'] == f['userSlip']['say']


def test_the_minds_can_never_add_a_leg_or_bid_something_else(filer, monkeypatch):
    fs, sent = filer
    a = _answer([(KD, 'yes', 80, 27.4), (PS, 'no', 75, 14.8), (WIN, 'yes', 90, 3.0)])   # both add the team to win
    f, _ = _file(fs, monkeypatch, [a, a])
    assert [(g['ticker'], g['side']) for g in f['kalshi']['legs']] == [(KD, 'yes'), (PS, 'no')]   # the added leg is not a market on his slip
    assert WIN in {d['ticker'] for d in f['legsDropped']}


def test_a_leg_gone_from_the_menu_is_read_itself_and_a_test_never_bids(filer, monkeypatch):
    fs, sent = filer
    slip = [SLIP[0], {'ticker': ZUB['ticker'], 'side': 'yes', 'title': 'Zubac OVER 9.5 rebounds'}]
    a = _answer([(KD, 'yes', 80, 27.4), (ZUB['ticker'], 'yes', 72, 11.2)])
    f, asks = _file(fs, monkeypatch, [a, a], slip=slip, by='test')
    assert ZUB['ticker'] in asks[0] and f['userSlip']['whole'] and f['kalshi']['test'] and sent == []   # whole, but a TEST never sends
    gone = [SLIP[0], {'ticker': 'KXNBAREB-26NOV18HOUIND-NOBODY0-10', 'side': 'yes', 'title': 'Nobody OVER 9.5'}]
    f, _ = _file(fs, monkeypatch, [a, a], slip=gone)
    assert not f['userSlip']['whole'] and 'Nobody OVER 9.5: Kalshi does not list it open now' in f['userSlip']['say'] and sent == []


def test_a_started_game_never_turns_his_slip_into_a_straight_bid(filer, monkeypatch):
    fs, sent = filer

    async def none_open(h, topic, games=None): return []
    async def board_for(h, topic): return {}
    monkeypatch.setattr(kb, 'markets_for', none_open); monkeypatch.setattr(kb, 'board_for', board_for, raising=False)
    a = _answer([(KD, 'yes', 80, 27.4), (PS, 'no', 75, 14.8)])
    f, _ = _file(fs, monkeypatch, [a, a])
    assert 'kalshi' not in f and not f['userSlip']['whole'] and sent == [] and 'Kalshi does not list it open now' in f['userSlip']['say']


def test_a_restart_refiles_his_slip_as_his_slip():
    import feecat_service as fs
    cat = {'id': 'c9', 'chat': [], 'pobFiling': {'id': 'pob1', 'topic': 'Rockets vs Pacers parlay slip 2 legs', 'by': 'you', 'at': 1, 'slip': SLIP}}
    fs._POB_WANT.pop('c9', None)
    import fc_pob
    fc_pob._pob_cut_off(cat, 10.0)
    assert cat['pobAsk'] == 'Rockets vs Pacers parlay slip 2 legs' and cat['pobSlip']['legs'] == SLIP and cat['pobBy'] == 'resume'
    fs._POB_WANT.pop('c9', None)


def test_menu_rows_say_over_and_under_plainly():
    r = pd.menu_row(MENU[1])
    assert r['kind'] == 'player' and r['stat'] == 'points' and r['line'] == 19.5 and r['over'] == 'Kevin Durant OVER 19.5 points' and r['under'] == 'Kevin Durant UNDER 19.5 points'
    assert pd.menu_row(MKT)['kind'] == 'team' and pd.menu_row(MKT)['yes'] == 0.6
