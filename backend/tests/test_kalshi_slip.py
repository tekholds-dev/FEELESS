"""🧩 Kalshi parlay slip (owner 2026-11-15 'build a parlay for team and players in one slip'). Kalshi is faked: nothing here reaches it."""
import asyncio

import feecat_service as fs
import kalshi_bid as kb

FUT = '2099-01-01T00:00:00Z'


def _m(t, yes, no=None, ev=None):
    return {'ticker': t, 'event_ticker': ev or '-'.join(t.split('-')[:2]), 'status': 'active', 'close_time': FUT,
            'yes_ask_dollars': str(yes), 'no_ask_dollars': str(no if no is not None else round(1.02 - yes, 2)), 'title': t, 'yes_sub_title': t.split('-')[-1]}


HOU = _m('KXNBAGAME-26NOV15HOUWAS-HOU', 0.75)
WAS = _m('KXNBAGAME-26NOV15HOUWAS-WAS', 0.26)
SEN = _m('KXNBAPTS-26NOV15HOUWAS-HOUASENGUN-20', 0.55)
AMN = _m('KXNBAPTS-26NOV15HOUWAS-HOUATHOMPSON-15', 0.60)
MENU = [HOU, WAS, SEN, AMN]


def _call(name, legs, mind=0):
    return {'name': name, 'mind': mind, 'picks': [{'pick': t, 'confidence': c, 'why': 'w', 'kalshi': {'ticker': t, 'side': s}} for t, s, c in legs]}


def test_mode_of_reads_team_or_parlay():
    assert kb.mode_of('Rockets vs Wizards parlay slip') == 'parlay' and kb.mode_of('3 leg rockets') == 'parlay'
    assert kb.mode_of('Rockets vs Wizards team to win') == 'team' and kb.mode_of('rockets moneyline') == 'team'
    assert kb.mode_of('Rockets vs Wizards') is None


def test_both_minds_same_legs_make_the_slip_and_a_split_gives_his_tap():
    a = _call('A', [(HOU['ticker'], 'yes', 80), (SEN['ticker'], 'yes', 70), (AMN['ticker'], 'yes', 66)])
    b = _call('B', [(SEN['ticker'], 'yes', 72), (HOU['ticker'], 'yes', 75)], 1)
    s = kb.slip_of([a, b], MENU, 65)
    assert s['by'] is None and {g['ticker'] for g in s['legs']} == {HOU['ticker'], SEN['ticker']}
    b2 = _call('B', [(WAS['ticker'], 'yes', 70)], 1)   # B backs the other team: no shared legs → A's slip is the offer
    s2 = kb.slip_of([a, b2], MENU, 65)
    assert s2['by'] == 'A' and len(s2['legs']) == 3
    assert kb.slip_of([_call('A', [(HOU['ticker'], 'yes', 80), (SEN['ticker'], 'yes', 50)]), b2], MENU, 65) is None   # a weak leg: no slip at all


def test_one_winner_per_game_and_ticket_prices():
    a = _call('A', [(HOU['ticker'], 'yes', 80), (WAS['ticker'], 'yes', 80), (SEN['ticker'], 'yes', 70)])
    assert set(kb._legs(a, {m['ticker']: m for m in MENU})) == {HOU['ticker'], SEN['ticker']}   # both teams to win never sit in one slip
    tk = kb.slip_ticket(kb.slip_of([a], MENU, 65), MENU, 'pob1')
    assert tk['kind'] == 'parlay' and tk['status'] == 'waiting' and tk['offer'] == 'A'
    assert tk['price'] == round(0.75 * 0.55, 4) and tk['maxPx'] == round(0.4125 * 1.25 + 0.02, 3)
    assert tk['legs'][0]['event'] == 'KXNBAGAME-26NOV15HOUWAS'


def test_slip_guards():
    tk = kb.slip_ticket({'legs': [{'ticker': HOU['ticker'], 'side': 'yes', 'conf': [80, 75]}, {'ticker': SEN['ticker'], 'side': 'yes', 'conf': [70, 72]}]}, MENU, 'f')
    fresh = {HOU['ticker']: HOU, SEN['ticker']: SEN}
    c = {'bidUsd': 1, 'dayUsd': 2, 'floorUsd': 2, 'minConf': 65}
    ok, why, budget = kb.slip_check(c, fresh, tk, [], 10.0)
    assert ok and budget == 1.0
    assert not kb.slip_check(c, fresh, tk, [], 2.5)[0]   # under his floor
    assert not kb.slip_check(c, {**fresh, SEN['ticker']: {**SEN, 'yes_ask_dollars': '0.70'}}, tk, [], 10.0)[0]   # a leg moved
    assert not kb.slip_check(c, {HOU['ticker']: HOU}, tk, [], 10.0)[0]   # a leg closed
    assert not kb.slip_check(c, fresh, tk, [{'legs': tk['legs'], 'at': tk['at'], 'status': 'filled', 'usd': 1}], 10.0)[0]   # the same slip twice
    assert not kb.slip_check({**c, 'minConf': 75}, fresh, tk, [], 10.0)[0]


def test_pick_quote_takes_the_cheapest_under_the_ticket_and_budget():
    qs = [{'id': 'q1', 'status': 'open', 'no_bid_dollars': '0.50', 'yes_contracts_fp': '2.00'},    # YES at 0.50: over the max
          {'id': 'q2', 'status': 'open', 'no_bid_dollars': '0.58', 'yes_contracts_fp': '2.00'},    # YES at 0.42
          {'id': 'q3', 'status': 'open', 'no_bid_dollars': '0.60', 'yes_contracts_fp': '9.00'},    # cheaper but over budget
          {'id': 'q4', 'status': 'cancelled', 'no_bid_dollars': '0.90', 'yes_contracts_fp': '1.00'}]
    q, px, n = kb.pick_quote(qs, 0.45, 1.0)
    assert q['id'] == 'q2' and px == 0.42 and n == 2.0
    assert kb.pick_quote(qs[:1], 0.45, 1.0) is None


def _fake(monkeypatch, quotes, final='executed'):
    calls = []
    async def market(h, t): return {m['ticker']: m for m in MENU}.get(t)
    async def balance(h, k, p, m=None): return 10.0
    async def unstarted(h, m): return True
    async def combo(h, k, p, legs): calls.append(('combo', [g['ticker'] for g in legs])); return 'KXMVECROSSCATEGORY-S1-ABC'
    async def rfq(h, k, p, t, b): calls.append(('rfq', t, b)); return 'r1'
    seen = {'n': 0}
    async def rq(h, k, p, rid):
        seen['n'] += 1
        return quotes if seen['n'] == 1 else [{**q, 'status': final, 'rfq_creator_order_id': 'ord9'} for q in quotes]
    async def accept(h, k, p, rid, qid): calls.append(('accept', rid, qid))
    async def delete(h, k, p, rid): calls.append(('delete', rid))
    async def nap(*a): return None
    for n, f in (('market', market), ('balance', balance), ('unstarted', unstarted), ('combo_create', combo), ('rfq_create', rfq), ('rfq_quotes', rq), ('quote_accept', accept), ('rfq_delete', delete)):
        monkeypatch.setattr(kb, n, f)
    monkeypatch.setattr(kb, 'split_key', lambda s: ('kid', 'pem')); monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: 'x')
    monkeypatch.setattr(fs.asyncio, 'sleep', nap); monkeypatch.setattr(kb, 'QUOTE_WAIT_S', 0.05); monkeypatch.setattr(kb, 'FILL_WAIT_S', 0.05)
    async def no_feed(*a): return None
    async def quick(wake, s): return None
    monkeypatch.setattr(kb, 'quote_feed', no_feed); monkeypatch.setattr(kb, 'nap', quick)
    return calls


def _tk():
    return kb.slip_ticket({'legs': [{'ticker': HOU['ticker'], 'side': 'yes', 'conf': [80, 75]}, {'ticker': SEN['ticker'], 'side': 'yes', 'conf': [70, 72]}]}, MENU, 'f')


def test_slip_send_one_rfq_one_accept_then_filled(monkeypatch):
    calls = _fake(monkeypatch, [{'id': 'q2', 'status': 'open', 'no_bid_dollars': '0.58', 'yes_contracts_fp': '2.00'}])
    cat = {'id': 'c', 'kalshiCfg': {'bidUsd': 1, 'dayUsd': 2, 'floorUsd': 2, 'minConf': 65}}
    tk = asyncio.run(fs._kalshi_slip_send(cat, _tk()))
    assert tk['status'] == 'filled' and tk['orderId'] == 'ord9' and tk['usd'] == 0.84 and tk['ticker'].startswith('KXMVE')
    assert [c[0] for c in calls] == ['combo', 'rfq', 'accept'] and calls[1][2] == 1.0   # never a second RFQ or accept, nothing left to delete
    assert cat['kalshiBids'][-1]['kind'] == 'parlay' and 'filled my slip' in cat['chat'][-1]['text']


def test_no_cheap_quote_buys_nothing_and_closes_the_rfq(monkeypatch):
    calls = _fake(monkeypatch, [{'id': 'q1', 'status': 'open', 'no_bid_dollars': '0.40', 'yes_contracts_fp': '1.00'}])   # YES 0.60 > max
    tk = asyncio.run(fs._kalshi_slip_send({'id': 'c', 'kalshiCfg': {'minConf': 65}}, _tk()))
    assert tk['status'] == 'refused' and 'No market maker' in tk['why'] and not tk.get('orderId')
    assert ('accept' not in [c[0] for c in calls]) and calls[-1] == ('delete', 'r1')


def test_maker_never_confirms_is_not_bought(monkeypatch):
    calls = _fake(monkeypatch, [{'id': 'q2', 'status': 'open', 'no_bid_dollars': '0.58', 'yes_contracts_fp': '2.00'}], final='cancelled')
    tk = asyncio.run(fs._kalshi_slip_send({'id': 'c', 'kalshiCfg': {'minConf': 65}}, _tk()))
    assert tk['status'] == 'refused' and not tk.get('orderId') and calls[-1] == ('delete', 'r1')


def test_started_game_refuses_before_kalshi_is_asked(monkeypatch):
    calls = _fake(monkeypatch, [])
    async def started(h, m): return False
    monkeypatch.setattr(kb, 'unstarted', started)
    tk = asyncio.run(fs._kalshi_slip_send({'id': 'c', 'kalshiCfg': {'minConf': 65}}, _tk()))
    assert tk['status'] == 'refused' and 'already started' in tk['why'] and calls == []


def test_the_ticket_door_routes_a_slip(monkeypatch):
    hit = []
    async def slip(cat, tk): hit.append('slip'); return tk
    async def one(cat, tk): hit.append('one'); return tk
    monkeypatch.setattr(fs, '_kalshi_slip_send', slip); monkeypatch.setattr(fs, '_kalshi_send', one)
    asyncio.run(fs._kalshi_go({}, {'kind': 'parlay'})); asyncio.run(fs._kalshi_go({}, {'ticker': 'T'}))
    assert hit == ['slip', 'one']


def test_legs_menu_reads_the_game_and_its_props(monkeypatch):
    class R:
        def __init__(self, j): self.status_code, self._j = 200, j
        def json(self): return self._j
    class H:
        async def get(self, url, params=None):
            if 'multivariate' in url:
                return R({'multivariate_contract': {'associated_events': [{'ticker': 'KXNBAGAME-26NOV15HOUWAS'}, {'ticker': 'KXNBAPTS-26NOV15HOUWAS'}]}})
            return R({'markets': [SEN, AMN, _m('KXNBAPTS-26NOV15HOUWAS-X-40', 0.03)]} if params['event_ticker'] == 'KXNBAPTS-26NOV15HOUWAS' else {'markets': []})
    kb._COMBO_EVENTS.update(at=0, set=set())
    menu = asyncio.run(kb.legs_menu(H(), [HOU, WAS]))
    assert [m['ticker'] for m in menu] == [HOU['ticker'], WAS['ticker'], SEN['ticker'], AMN['ticker']]   # a 3¢ long shot is not a leg
    assert 'KALSHI PARLAY LEGS' in kb.slip_brief(menu, 3) and kb.room_view({**_tk(), 'orderId': 'o', 'filled': 2, 'price': 0.42})['legs'][0]['title']


def test_a_pob_with_teams_asks_team_or_parlay_then_files_the_answer(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'ownerId': 'me', 'revoked': False, 'cloud': {'pool': 'feeless'}, 'brainsCfg': {'kind': 'general', 'brains': ['m/a', 'm/b'], 'credit': 5}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_work_live', lambda *_a: True); monkeypatch.setattr(fs._lc, 'can_ask', lambda b: True)
    monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: 'x'); monkeypatch.setattr(fs._POW_WAKE, 'set', lambda: None)
    c = TestClient(fs.app); cat = store['cats']['g']
    r = c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'ask', 'text': 'file a pob rockets vs wizards'})
    assert r.status_code == 200, r.text
    assert cat['chat'][-1]['ask']['chips'] == ['Team to win', 'Parlay slip'] and not cat.get('pobAsk')   # nothing starts before he answers
    c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'ask', 'text': 'Parlay slip'})
    assert not cat.get('pobAsk') and not cat.get('pobModeAsk') and cat['chat'][-1]['ask']['chips'] == kb.LEG_CHIPS   # then: how many legs
    c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'ask', 'text': 'Max legs (4)'})
    assert cat['pobAsk'] == 'rockets vs wizards parlay slip 4 legs' and 'One parlay slip' in cat['chat'][-1]['text'] and not cat.get('pobLegsAsk')
    cat.pop('pobAsk'); fs._POB_WANT.pop('g', None)
    # 🧩 its team to win already bid on this game today: the refile offers only the parlay slip
    cat['pobFolders'] = [{'id': 'f1', 'at': __import__('time').time(), 'topic': 'Rockets vs Wizards team to win', 'kalshi': {'id': 'kb1', 'title': 'Houston wins', 'status': 'filled', 'orderId': 'o1'}}]
    c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'ask', 'text': 'file a pob rockets vs wizards'})
    assert cat['chat'][-1]['ask']['chips'] == ['Parlay slip'] and 'Houston wins' in cat['chat'][-1]['text']
    c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'ask', 'text': 'Parlay slip'})
    c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'ask', 'text': '3 legs'})
    assert cat['pobAsk'] == 'rockets vs wizards parlay slip 3 legs'
    cat.pop('pobAsk'); fs._POB_WANT.pop('g', None)
    c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'ask', 'text': 'file a pob rockets vs wizards team to win'})
    assert cat['pobAsk'] == 'rockets vs wizards team to win'   # he already said which: no question
    fs._POB_WANT.pop('g', None)


def test_extras_warning_record_notes_and_worth_line():
    """Owner 2026-11-15 'build it all': ⚠ Kalshi already disagrees, 🏅 each mind's real record breaks a tie, 🧠 its own after-payout notes, 📈 worth-now line."""
    assert kb.fights(0.12) and 'already disagrees' in kb.fights(0.12) and kb.fights(0.45) is None
    tk = kb.ticket({'ticker': WAS['ticker'], 'side': 'yes', 'conf': [70]}, {**WAS, 'yes_ask_dollars': '0.15'}, 'f')
    assert tk['warn'] and kb.outcome_line({**tk, 'offer': 'A'}, True).startswith(' ⚠ Kalshi already disagrees')
    won = {'topic': 'Rockets vs Wizards', 'kalshi': {'ticker': HOU['ticker'], 'side': 'yes', 'outcome': 'won'}, 'final': [{'name': 'B', 'text': 'Sengun ate inside.'}],
           'calls': [_call('A', [(WAS['ticker'], 'yes', 70)]), _call('B', [(HOU['ticker'], 'yes', 70)], 1)]}
    rec = kb.mind_record([won])
    assert rec == {'B': {'won': 1, 'lost': 0}}
    tie = [_call('A', [(HOU['ticker'], 'yes', 70)]), _call('B', [(SEN['ticker'], 'yes', 70)], 1)]
    assert kb.offer(tie, {HOU['ticker'], SEN['ticker']}, 65)['by'] == 'A' and kb.offer(tie, {HOU['ticker'], SEN['ticker']}, 65, rec)['by'] == 'B'
    notes = kb.past_notes([won], 'Rockets at Wizards tonight')
    assert 'Sengun ate inside.' in notes and 'WON' in notes and kb.past_notes([won], 'Lakers vs Suns') == ''
    v = kb.room_view({'orderId': 'o', 'ticker': 'T', 'side': 'yes', 'filled': 2, 'price': 0.4, 'pxHist': [[1, 0.4], [2, 0.55]]})
    assert v['hist'] == [[1, 0.8], [2, 1.1]]


def test_feed_only_wakes_for_our_request_and_nap_returns_early():
    assert kb.feed_hit('{"type": "quote_created", "msg": {"rfq_id": "r1"}}', 'r1')
    assert not kb.feed_hit('{"type": "quote_created", "msg": {"rfq_id": "r2"}}', 'r1') and not kb.feed_hit('nope', 'r1') and not kb.feed_hit('{"type": "ticker"}', 'r1')
    async def go():
        w = asyncio.Event(); w.set(); t0 = asyncio.get_event_loop().time()
        await kb.nap(w, 5)
        return asyncio.get_event_loop().time() - t0, w.is_set()
    took, still = asyncio.run(go())
    assert took < 0.5 and not still


def test_slip_send_starts_and_ends_the_feed(monkeypatch):
    _fake(monkeypatch, [{'id': 'q2', 'status': 'open', 'no_bid_dollars': '0.58', 'yes_contracts_fp': '2.00'}])
    seen = {}
    async def feed(k, p, rid, wake, stop): seen['rfq'] = rid; seen['stop'] = stop
    async def yield_once(wake, s):   # one real turn of the loop, so the feed task gets to start
        f = asyncio.get_running_loop().create_future(); asyncio.get_running_loop().call_soon(f.set_result, None); await f
    monkeypatch.setattr(kb, 'quote_feed', feed); monkeypatch.setattr(kb, 'nap', yield_once)
    asyncio.run(fs._kalshi_slip_send({'id': 'c', 'kalshiCfg': {'minConf': 65}}, _tk()))
    assert seen['rfq'] == 'r1' and seen['stop'].is_set()


def test_same_slip_smaller_only_after_no_quote_and_once():
    c = {'bidUsd': 2, 'minConf': 65}
    tk = {**_tk(), 'status': 'refused', 'why': 'No market maker quoted the slip at 0.536 or less within 25 s, so nothing was bought.'}
    new, _ = kb.smaller(tk, c)
    assert new['status'] == 'waiting' and new['budgetUsd'] == 1.0 and new['retryOf'] == tk['id'] and new['legs'] == tk['legs'] and new['id'] != tk['id']
    assert kb.smaller(new, c)[0] is None   # waiting, not refused
    assert kb.smaller({**new, 'status': 'refused', 'why': tk['why']}, c)[1] == 'It was already tried smaller once.'
    assert kb.smaller({**tk, 'why': 'Your Kalshi balance would fall under your floor.'}, c)[0] is None
    fresh = {HOU['ticker']: HOU, SEN['ticker']: SEN}
    assert kb.slip_check({**c, 'dayUsd': 5, 'floorUsd': 0}, fresh, {**new, 'conf': [80, 75]}, [], 10.0)[2] == 1.0   # the guard spends the smaller budget


def test_the_collective_shows_minds_not_agents():
    won = {'topic': 'Rockets vs Wizards', 'kalshi': {'ticker': HOU['ticker'], 'side': 'yes', 'outcome': 'won', 'settledAt': 5}, 'final': [{'name': 'openrouter/hy4', 'text': 'Sengun ate inside.'}],
           'calls': [_call('openrouter/hy4', [(HOU['ticker'], 'yes', 70)]), _call('x/terra', [(WAS['ticker'], 'yes', 70)], 1)]}
    cats = [{'id': 'secret-agent', 'name': 'Happy Assistant', 'pobFolders': [won, {'kalshi': {'status': 'waiting'}}]}]
    b = kb.public_board(cats)
    assert b['minds'] == [{'mind': 'hy4', 'won': 1, 'lost': 0, 'n': 1}] and b['notes'][0]['text'] == 'Sengun ate inside.' and b['notes'][0]['mind'] == 'hy4'
    flat = str(b)
    assert 'Happy Assistant' not in flat and 'secret-agent' not in flat and HOU['ticker'] not in flat


def test_public_kalshi_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_load', lambda: {'cats': {}}); fs._KB_PUBLIC['at'] = 0
    r = TestClient(fs.app).get('/api/cats/collective/kalshi')
    assert r.status_code == 200 and r.json() == {'minds': [], 'notes': []}
    fs._KB_PUBLIC['at'] = 0


def test_try_smaller_tap_sends_once_through_the_slip_door(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    tk = {**_tk(), 'status': 'refused', 'why': 'No market maker quoted the slip at 0.536 or less within 25 s, so nothing was bought.'}
    store = {'cats': {'g': {'id': 'g', 'ownerId': 'me', 'revoked': False, 'kalshiCfg': {'bidUsd': 1}, 'pobFolders': [{'id': 'pob1', 'kalshi': tk}]}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: None)
    sent = []
    async def slip(cat, t): sent.append(t['budgetUsd']); t.update(status='refused', why='No market maker quoted again.'); return t
    monkeypatch.setattr(fs, '_kalshi_slip_send', slip)
    c = TestClient(fs.app)
    r = c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'kalshi_smaller', 'job': tk['id']})
    assert r.status_code == 200, r.text
    f = store['cats']['g']['pobFolders'][0]
    assert sent == [0.5] and f['kalshi']['retryOf'] == tk['id'] and f['kalshiTries'][0]['id'] == tk['id']
    assert c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'kalshi_smaller', 'job': f['kalshi']['id']}).status_code == 409 and sent == [0.5]   # once only


GONE = {'id': 'g1', 'at': '2026-11-18T01:00Z', 'state': 'in', 'status': '11:29 - 1st', 'teams': [{'short': 'Pistons', 'abbr': 'DET'}, {'short': 'Spurs', 'abbr': 'SA'}]}
OPEN = [{'id': 'g2', 'at': '2026-11-18T03:30Z', 'state': 'pre', 'teams': [{'short': 'Jazz', 'abbr': 'UTAH'}, {'short': 'Clippers', 'abbr': 'LAC'}]},
        {'id': 'g3', 'at': '2026-11-18T04:00Z', 'state': 'pre', 'teams': [{'short': 'Hornets', 'abbr': 'CHA'}, {'short': 'Lakers', 'abbr': 'LAL'}]}]


def test_a_started_game_is_said_before_any_question_and_never_filed(monkeypatch):
    """🏁 owner 2026-11-17 ("FILED A POB, LET ME GUESS, ANOTHER FUCKING BUG"): Pistons vs Spurs, 12 min after tip-off. It asked team-or-parlay, then
    filed the refusal as PoB #20, scored it 26 and put it in the pot. Now: one line, the games still open as chips, no folder."""
    from fastapi.testclient import TestClient
    monkeypatch.setattr(fs, '_session_wallet', lambda s: str(s or '')); monkeypatch.setattr(fs, '_fresh_session_wallet', lambda s, now=None: str(s or ''))
    store = {'cats': {'g': {'id': 'g', 'ownerId': 'me', 'revoked': False, 'cloud': {'pool': 'feeless'}, 'brainsCfg': {'kind': 'general', 'brains': ['m/a', 'm/b'], 'credit': 5}}}, 'events': []}
    monkeypatch.setattr(fs, '_load', lambda: store); monkeypatch.setattr(fs, '_save', lambda s: None); monkeypatch.setattr(fs, '_work_live', lambda *_a: True); monkeypatch.setattr(fs._lc, 'can_ask', lambda b: True)
    monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: 'x'); monkeypatch.setattr(fs._POW_WAKE, 'set', lambda: None)
    asked = []
    async def gone(topic, now=None):
        asked.append(topic); return GONE, OPEN
    monkeypatch.setattr(fs, '_pob_gone', gone)
    c = TestClient(fs.app); cat = store['cats']['g']
    assert c.post('/api/cats/g/work', json={'ownerId': 'me', 'session': 'me', 'op': 'ask', 'text': 'file a pob Pistons vs Spurs'}).status_code == 200
    last = cat['chat'][-1]
    assert asked == ['Pistons vs Spurs'] and not cat.get('pobModeAsk') and not cat.get('pobAsk') and not cat.get('pobFolders')
    assert last['text'].startswith('🎲 Not filed, nothing spent: Pistons vs Spurs reached its start time') and '11:29 - 1st' in last['text']
    assert 'Jazz vs Clippers' in last['text'] and last['ask']['chips'] == ['file a pob Jazz vs Clippers', 'file a pob Hornets vs Lakers']
    assert cat['chat'][-2] == {'by': 'you', 'text': 'file a pob Pistons vs Spurs', 'at': cat['chat'][-2]['at']}


def test_the_filer_never_numbers_a_started_game(monkeypatch):
    cat = {'id': 'g', 'pobFolders': [{'id': 'p1', 'n': 19}], 'chat': []}
    fs._pob_gone_say(cat, 'Pistons vs Spurs team to win', GONE, [])
    assert len(cat['pobFolders']) == 1 and 'Pick a game that has not started' in cat['chat'][-1]['text'] and 'ask' not in cat['chat'][-1]
    t0 = kb._start('2026-11-18T03:00Z')
    assert [g['id'] for g in kb.upcoming([*OPEN[::-1], GONE], t0)] == ['g2', 'g3'] and kb.upcoming(OPEN, kb._start('2026-11-18T05:00Z')) == []
