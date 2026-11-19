"""🛡 Slice 12 · PoB: player-prop parlays + bids that always go through (owner 2026-11-18: "minds need to pick leg parlays as in the best over or
under for players" · "can't afford for bids not to go through or filings to f up").
Every bid or filing failure seen so far ends in ONE of: "sent and confirmed", or a plain-words reason with no money moved (or, when the send
was cut off before Kalshi answered, 'unknown': never re-sent, read back until Kalshi says). Network faked; nothing reaches Kalshi."""
import asyncio
import json
import time

import pytest

import kalshi_bid as kb
import pob as _pob

NOW = time.time()
CFG = {'bidUsd': 1, 'dayUsd': 3, 'floorUsd': 2, 'minConf': 65}
MKT = {'ticker': 'KXNBAGAME-26NOV18HOUIND-HOU', 'event_ticker': 'KXNBAGAME-26NOV18HOUIND', 'status': 'active', 'close_time': '2099-01-01T00:00:00Z',
       'yes_ask_dollars': '0.60', 'no_ask_dollars': '0.42', 'yes_sub_title': 'Houston', 'title': 'Houston at Indiana Winner?'}


def _rung(player, key, n, yes, series='KXNBAPTS'):
    return {'ticker': f'{series}-26NOV18HOUIND-{key}-{n}', 'event_ticker': f'{series}-26NOV18HOUIND', 'status': 'active', 'close_time': '2099-01-01T00:00:00Z',
            'yes_ask_dollars': f'{yes:.2f}', 'no_ask_dollars': f'{1 - yes + 0.02:.2f}', 'floor_strike': n - 0.5, 'yes_sub_title': f'{player}: {n}+', 'title': f'{player}: {n}+ points'}


# the real shape read from Kalshi 2026-11-18 (KXNBAPTS-26NOV18HOUIND): a ladder per player
KD = [_rung('Kevin Durant', 'HOUKDURANT7', 15, 0.90), _rung('Kevin Durant', 'HOUKDURANT7', 20, 0.63), _rung('Kevin Durant', 'HOUKDURANT7', 25, 0.24)]
PS = [_rung('Pascal Siakam', 'INDPSIAKAM43', 15, 0.81), _rung('Pascal Siakam', 'INDPSIAKAM43', 20, 0.51), _rung('Pascal Siakam', 'INDPSIAKAM43', 25, 0.23)]
REB = [_rung('Ivica Zubac', 'INDIZUBAC40', 10, 0.55, 'KXNBAREB')]
MENU = [MKT, KD[1], PS[1], REB[0]]


def _call(name, legs, mind=0):
    return {'name': name, 'mind': mind, 'picks': [{'pick': t, 'confidence': c, 'kalshi': {'ticker': t, 'side': s}, **extra} for t, s, c, extra in legs]}


# ── 1 · player-prop legs ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_menu_shows_each_players_line_nearest_a_coin_flip_as_an_over_or_under():
    rows = kb.prop_rows(KD + PS + [{**_rung('Ghost', 'HOUGHOST1', 30, 0.05)}])   # a 5¢ line adds nothing but risk
    assert [r['ticker'] for r in rows] == [PS[1]['ticker'], KD[1]['ticker']]   # one rung per player, closest to 50¢ first
    ln = kb.leg_line(KD[1])
    assert 'Kevin Durant points' in ln and 'OVER 19.5 = YES 0.63' in ln and 'UNDER 19.5 = NO' in ln
    assert kb.stat_of(REB[0]['ticker']) == 'rebounds' and kb.stat_of(MKT['ticker']) == '' and kb.stat_of('KXNBA3PT-X-Y-3') == 'threes'
    assert kb.leg_title(KD[1], 'no') == 'Kevin Durant UNDER 19.5 points'
    assert kb.mode_of('best nba player props tonight') == 'parlay' and kb.mode_of('Lakers over Jazz') is None   # 'over' alone is not a parlay


def test_legs_menu_reads_every_player_stat_kalshi_lists_and_keeps_room_for_players(monkeypatch):
    class R:
        def __init__(self, j): self.status_code, self._j = 200, j
        def json(self): return self._j

    class H:
        async def get(self, url, params=None, **k):
            ev = (params or {}).get('event_ticker', '')
            if ev.startswith('KXNBAPTS'):
                return R({'markets': KD + PS})
            if ev.startswith('KXNBAREB'):
                return R({'markets': REB})
            return R({'markets': []})

    async def combo_events(h):
        return {'KXNBAGAME-26NOV18HOUIND', 'KXNBAPTS-26NOV18HOUIND', 'KXNBAREB-26NOV18HOUIND'}
    monkeypatch.setattr(kb, 'combo_events', combo_events)
    menu = asyncio.run(kb.legs_menu(H(), [MKT]))
    ids = [m['ticker'] for m in menu]
    assert ids[0] == MKT['ticker'] and KD[1]['ticker'] in ids and PS[1]['ticker'] in ids and REB[0]['ticker'] in ids
    assert KD[0]['ticker'] not in ids and len(ids) == len(set(ids))   # one line per player per stat


def test_each_player_leg_needs_its_own_evidence_and_number_and_a_ticker_kalshi_lists():
    ev = {'evidence': 'espn.com: averages 27.4 points, line 19.5', 'number': 27.4}
    a = _call('ossy', [(KD[1]['ticker'], 'yes', 80, ev), (PS[1]['ticker'], 'no', 72, {'why': 'cbs: 14.8 in his last 5'}),
                       (REB[0]['ticker'], 'yes', 70, {'why': 'he is due'}), ('KXNBAPTS-26NOV18HOUIND-HOUMADEUP1-20', 'yes', 90, ev)])
    b = _call('g4', [(KD[1]['ticker'], 'yes', 75, {'evidence': 'rotowire 26 a night', 'number': '26'}), (PS[1]['ticker'], 'no', 70, {'why': 'covers: 15.1 avg vs IND'})], 1)
    s = kb.slip_of([a, b], MENU, 65)
    assert s['by'] is None and [(g['ticker'], g['side']) for g in s['legs']] == [(KD[1]['ticker'], 'yes'), (PS[1]['ticker'], 'no')]
    assert s['legs'][0]['backing'] == [{'mind': 'ossy', 'evidence': ev['evidence'], 'number': 27.4}, {'mind': 'g4', 'evidence': 'rotowire 26 a night', 'number': 26.0}]
    assert s['legs'][1]['backing'][0]['number'] == 14.8   # the figure in its own words counts as its number
    dropped = kb.dropped_legs([a, b], MENU)
    assert {(d['ticker'].split('-')[2], d['why']) for d in dropped} == {('INDIZUBAC40', 'a player leg with no evidence or no number'), ('HOUMADEUP1', 'not a market Kalshi lists for this game')}
    tk = kb.slip_ticket(s, MENU, 'pob1', NOW)
    assert tk['legs'][0]['title'] == 'Kevin Durant OVER 19.5 points' and tk['legs'][0]['ou'] == 'over' and tk['legs'][0]['line'] == 19.5 and tk['legs'][0]['stat'] == 'points'
    assert tk['legs'][1]['ou'] == 'under' and kb.slip_whole(tk, MENU) == ''
    json.dumps(tk)


def test_a_mind_reply_keeps_each_legs_evidence_and_number():
    raw = '{"picks":[{"pick":"Durant over 19.5","confidence":78,"why":"hot","evidence":"espn: 27.4 a game","number":27.4,"kalshi":{"ticker":"KXNBAPTS-26NOV18HOUIND-HOUKDURANT7-20","side":"yes"}}]}'
    p = _pob.parse_picks(raw)['picks'][0]
    assert p['evidence'] == 'espn: 27.4 a game' and p['number'] == '27.4' and kb.leg_backing(p) == ('espn: 27.4 a game', 27.4)
    assert 'evidence' not in _pob.parse_picks('{"picks":[{"pick":"x","confidence":5}]}')['picks'][0]


def test_a_half_made_slip_is_never_a_ticket():
    good = kb.slip_ticket(kb.slip_of([_call('ossy', [(KD[1]['ticker'], 'yes', 80, {'why': 'espn 27.4 a game'}), (MKT['ticker'], 'yes', 70, {'why': 'x'})])], MENU, 65), MENU, 'f')
    assert kb.slip_whole(good, MENU) == ''
    assert 'missing its market' in kb.slip_whole({**good, 'legs': [{**good['legs'][0], 'event': None}, good['legs'][1]]}, MENU)
    assert 'not a market Kalshi lists' in kb.slip_whole(good, [MKT])
    assert 'no evidence' in kb.slip_whole({**good, 'legs': [{**good['legs'][0], 'backing': [{'mind': 'x', 'evidence': '', 'number': None}]}, good['legs'][1]]}, MENU)
    assert '2 to 4 legs' in kb.slip_whole({**good, 'legs': good['legs'][:1]}, MENU)


# ── 2 · every failure seen so far ends in plain words ─────────────────────────────────────────────────────────────────────────────────────
class _R:
    def __init__(self, code, j=None, text=''):
        self.status_code, self._j, self.text = code, j or {}, text or json.dumps(j or {})

    def json(self):
        return self._j


class _H:
    """A fake Kalshi: the market, his balance, the order route and the order list, each answering what the test says."""
    def __init__(self, place=None, read=None, orders=None, balance=None):
        self.place, self.read, self.orders, self.bal = place, read or [], orders, balance
        self.posts = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None, headers=None, **k):
        if url.endswith('/portfolio/balance'):
            return self.bal or _R(200, {'balance': 1000})
        if '/portfolio/orders/' in url:
            return self.read.pop(0) if self.read else _R(404, text='{"error":{"code":"not_found"}}')
        if url.endswith('/portfolio/orders'):
            if isinstance(self.orders, Exception):
                raise self.orders
            return _R(200, {'orders': self.orders or []})
        if '/markets/' in url:
            return _R(200, {'market': MKT})
        return _R(200, {})

    async def post(self, url, json=None, headers=None, **k):
        self.posts.append(json)
        if isinstance(self.place, Exception):
            raise self.place
        return self.place


@pytest.fixture
def svc(monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, '_KB_SENT', {}); monkeypatch.setattr(fs, '_KB_LEDGER', {})
    monkeypatch.setattr(kb, 'split_key', lambda s: ('kid', 'pem')); monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: 'x')
    monkeypatch.setattr(kb, 'headers', lambda *a, **k: {})

    async def unstarted(h, m):
        return True
    monkeypatch.setattr(kb, 'unstarted', unstarted)

    async def quick(*a, **k):
        return None
    monkeypatch.setattr(fs.asyncio, 'sleep', quick)

    def use(h):
        monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda *a, **k: h)
        return h
    fs._use = use
    return fs


def _ticket():
    return {**kb.ticket({'ticker': MKT['ticker'], 'side': 'yes', 'conf': [80, 72], 'why': ['a', 'b']}, MKT, 'pob1', NOW)}


def _send(fs, h, tk=None):
    fs._use(h)
    cat = {'id': 'c', 'kalshiCfg': CFG, 'kalshiBids': [], 'chat': []}
    return cat, asyncio.run(fs._kalshi_send(cat, tk or _ticket()))


SENT = {'order_id': 'o1', 'fill_count_fp': '0.00', 'remaining_count_fp': '1.00'}
HELD = {'order': {'order_id': 'o1', 'status': 'resting', 'fill_count_fp': '0.00', 'remaining_count_fp': '1.00', 'initial_count_fp': '1.00'}}


def test_sent_and_confirmed(svc):
    cat, tk = _send(svc, _H(place=_R(201, SENT), read=[_R(200, HELD)]))
    assert tk['end']['end'] == 'confirmed' and 'Sent and confirmed on Kalshi' in tk['end']['say'] and cat['kalshiBids'][-1]['end']['end'] == 'confirmed'
    assert 'Kalshi confirmed my bid' in cat['chat'][-1]['text']


@pytest.mark.parametrize('name, reply, words', [
    ('the v1 order route (PoB #16)', _R(410, text='{"error":"gone"}'), 'retired the order route'),
    ('money on another exchange index (PoB #17)', _R(404, text='{"error":{"code":"insufficient_shard_balance"}}'), 'Exchange Indexes'),
    ('a market Kalshi took down', _R(404, text='{"error":{"code":"market_not_found"}}'), 'no longer lists that market'),
    ('a key Kalshi will not take', _R(401, text='{"error":"unauthorized"}'), 'did not accept your API key'),
    ('Kalshi busy', _R(429, text='{"error":"too many"}'), 'slow down'),
    ('Kalshi down', _R(503, text='<html>'), 'Kalshi itself had an error'),
])
def test_a_clear_no_from_kalshi_says_why_in_plain_words_and_nothing_moved(svc, name, reply, words):
    cat, tk = _send(svc, _H(place=reply))
    assert tk['status'] == 'failed' and not tk.get('orderId') and not kb.reached(tk), name
    assert tk['end']['end'] == 'stopped' and words in tk['end']['say'] and kb.NO_MONEY in tk['end']['say'] and '{' not in tk['end']['say'], name
    assert words in cat['chat'][-1]['text'] and kb.spent_today(cat['kalshiBids']) == 0   # never counts in today's cap, never blocks the next bid


def test_a_create_then_read_back_404_is_read_again_never_resent(svc):
    h = _H(place=_R(201, SENT), read=[_R(404, text='not_found'), _R(404, text='not_found'), _R(200, HELD)])
    cat, tk = _send(svc, h)
    assert len(h.posts) == 1 and tk['end']['end'] == 'confirmed'
    h2 = _H(place=_R(201, SENT), read=[_R(404, text='not_found')] * 3)
    cat, tk = _send(svc, h2)
    assert len(h2.posts) == 1 and tk['end']['end'] == 'checking' and kb.reached(tk) and 'Never re-sent' in tk['end']['say']


def test_a_game_already_started_is_refused_before_any_order(svc, monkeypatch):
    async def started(h, m):
        return False
    monkeypatch.setattr(kb, 'unstarted', started)
    h = _H(place=_R(201, SENT))
    cat, tk = _send(svc, h)
    assert h.posts == [] and tk['end']['end'] == 'stopped' and 'already started' in tk['end']['say'] and kb.NO_MONEY in tk['end']['say']


def test_a_send_cut_off_before_kalshi_answered_is_looked_up_never_sent_twice(svc):
    """The money case that was silent: a timeout on the create call. The order may be on Kalshi, so it is looked up by our own client id."""
    h = _H(place=TimeoutError('read timed out'), read=[_R(200, HELD)])
    h.orders = []   # filled in once we know the client id

    async def lookup_finds(http, kid, pem, ticker, cid, since):
        return {'order_id': 'o7', 'client_order_id': cid, 'status': 'resting', 'fill_count_fp': '0.00', 'remaining_count_fp': '1.00'}
    real = kb.find_order
    kb.find_order = lookup_finds
    try:
        cat, tk = _send(svc, h)
    finally:
        kb.find_order = real
    assert len(h.posts) == 1 and tk['orderId'] == 'o7' and tk['end']['end'] == 'confirmed'
    # Kalshi has no such order (yet): unknown — never re-sent, blocks the market, counts in the cap
    cat, tk = _send(svc, _H(place=TimeoutError('read timed out'), orders=[]))
    assert tk['status'] == 'unknown' and kb.reached(tk) and tk['end']['end'] == 'unknown' and 'never be sent again' in tk['end']['say']
    ok, why, *_ = kb.check(CFG, MKT, {'ticker': MKT['ticker'], 'side': 'yes', 'conf': [90, 90]}, cat['kalshiBids'], 10.0)
    assert not ok and 'already bid on this market' in why
    # Kalshi cannot even be read: still unknown, said plainly
    cat, tk = _send(svc, _H(place=ConnectionError('dropped'), orders=RuntimeError('down')))
    assert tk['status'] == 'unknown' and 'could not be read' in tk['why'] and cat['chat'][-1]['text'].startswith('⚠')


def test_the_5_min_pass_settles_an_unknown_send(svc):
    import fc_pob
    row = {'id': 'kb1', 'ticker': MKT['ticker'], 'status': 'unknown', 'clientId': 'cid1', 'sentAt': NOW - 30, 'at': NOW - 30, 'count': 1, 'price': 0.6}
    cat = {'id': 'c', 'kalshiBids': [row], 'pobFolders': [{'id': 'pob1', 'kalshi': {'id': 'kb1', 'status': 'unknown'}}], 'chat': []}
    svc._use(_H(orders=[]))
    asyncio.run(fc_pob._kalshi_refresh(cat, 'kid', 'pem'))
    assert row['status'] == 'unknown'   # under 2 min: Kalshi may still be writing it
    row['sentAt'] = row['at'] = NOW - 600
    asyncio.run(fc_pob._kalshi_refresh(cat, 'kid', 'pem'))
    assert row['status'] == 'failed' and row['end']['end'] == 'stopped' and kb.NO_MONEY in row['end']['say']
    assert cat['pobFolders'][0]['kalshi']['status'] == 'failed' and 'nothing went through' in cat['chat'][-1]['text']
    row2 = {**row, 'id': 'kb2', 'status': 'unknown', 'clientId': 'cid2'}
    cat['kalshiBids'] = [row2]
    svc._use(_H(orders=[{'order_id': 'o9', 'client_order_id': 'cid2', 'status': 'executed', 'fill_count_fp': '1.00'}]))
    asyncio.run(fc_pob._kalshi_refresh(cat, 'kid', 'pem'))
    assert row2['orderId'] == 'o9' and row2['status'] == 'filled' and row2['end']['end'] == 'confirmed'


def test_kalshi_lists_orders_by_ticker_and_we_match_our_client_id():
    seen = {}

    class H:
        async def get(self, url, params=None, headers=None):
            seen.update(url=url, params=params)
            return _R(200, {'orders': [{'order_id': 'a', 'client_order_id': 'other'}, {'order_id': 'b', 'client_order_id': 'mine'}]})
    import kalshi_bid
    orig = kalshi_bid.headers
    kalshi_bid.headers = lambda *a, **k: {}
    try:
        o = asyncio.run(kb.find_order(H(), 'k', 'p', MKT['ticker'], 'mine', 1000))
        none = asyncio.run(kb.find_order(H(), 'k', 'p', MKT['ticker'], 'nobody', 1000))
    finally:
        kalshi_bid.headers = orig
    assert o['order_id'] == 'b' and none is None and seen['url'].endswith('/portfolio/orders') and seen['params']['ticker'] == MKT['ticker'] and seen['params']['min_ts'] == 940


def test_a_test_ticket_never_sends(svc):
    h = _H(place=_R(201, SENT))
    cat, tk = _send(svc, h, {**_ticket(), 'test': True})
    assert h.posts == [] and tk['status'] == 'test' and kb.end_of(tk)['end'] == 'test' and kb.NO_MONEY in kb.end_of(tk)['say']


# ── slips: a refused slip now says so in chat; an accept cut off or never confirmed is never called "nothing bought" ─────────────────────
def _slip_fake(monkeypatch, fs, quotes, final, accept_raises=None):
    calls = []
    by = {m['ticker']: m for m in MENU}

    async def market(h, t): return by.get(t)
    async def balance(h, k, p, m=None): return 10.0
    async def unstarted(h, m): return True
    async def combo(h, k, p, legs): calls.append('combo'); return 'KXMVECROSSCATEGORY-S1'
    async def rfq(h, k, p, t, b): calls.append('rfq'); return 'r1'
    seen = {'n': 0}

    async def rq(h, k, p, rid):
        seen['n'] += 1
        return quotes if seen['n'] == 1 else [{**q, 'status': final, 'rfq_creator_order_id': 'ord9'} for q in quotes]

    async def accept(h, k, p, rid, qid):
        calls.append('accept')
        if accept_raises:
            raise accept_raises
    async def delete(h, k, p, rid): calls.append('delete')
    async def none(*a): return None
    for n, f in (('market', market), ('balance', balance), ('unstarted', unstarted), ('combo_create', combo), ('rfq_create', rfq), ('rfq_quotes', rq),
                 ('quote_accept', accept), ('rfq_delete', delete), ('quote_feed', none), ('nap', none)):
        monkeypatch.setattr(kb, n, f)
    monkeypatch.setattr(kb, 'QUOTE_WAIT_S', 0.05); monkeypatch.setattr(kb, 'FILL_WAIT_S', 0.05)

    class Ctx:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, *a, **k): return _R(200, {'markets': [MKT]})
    monkeypatch.setattr(fs.httpx, 'AsyncClient', lambda *a, **k: Ctx())
    return calls


def _slip():
    s = kb.slip_of([_call('ossy', [(KD[1]['ticker'], 'yes', 80, {'why': 'espn 27.4 a game'}), (MKT['ticker'], 'yes', 70, {'why': 'x'})])], MENU, 65)
    return kb.slip_ticket(s, MENU, 'pob1')


Q = [{'id': 'q2', 'status': 'open', 'no_bid_dollars': '0.62', 'yes_contracts_fp': '2.00'}]


def test_a_filled_slip_is_sent_and_confirmed(svc, monkeypatch):
    calls = _slip_fake(monkeypatch, svc, Q, 'executed')
    cat = {'id': 'c', 'kalshiCfg': CFG, 'chat': []}
    tk = asyncio.run(svc._kalshi_slip_send(cat, _slip()))
    assert calls == ['combo', 'rfq', 'accept'] and tk['end']['end'] == 'confirmed' and tk['rfqId'] == 'r1'


def test_a_slip_no_maker_quoted_says_so_in_chat_with_no_money_moved(svc, monkeypatch):
    _slip_fake(monkeypatch, svc, [], 'executed')
    cat = {'id': 'c', 'kalshiCfg': CFG, 'chat': []}
    tk = asyncio.run(svc._kalshi_slip_send(cat, _slip()))
    assert tk['end']['end'] == 'stopped' and 'No market maker' in cat['chat'][-1]['text'] and kb.NO_MONEY in cat['chat'][-1]['text']


def test_an_accept_cut_off_or_not_yet_confirmed_is_unknown_never_nothing_bought(svc, monkeypatch):
    calls = _slip_fake(monkeypatch, svc, Q, 'executed', accept_raises=TimeoutError('t'))
    tk = asyncio.run(svc._kalshi_slip_send({'id': 'c', 'kalshiCfg': CFG, 'chat': []}, _slip()))
    assert tk['status'] == 'unknown' and kb.reached(tk) and 'delete' not in calls and tk['quoteId'] == 'q2'
    calls = _slip_fake(monkeypatch, svc, Q, 'accepted')   # maker still confirming at the end of the wait
    tk = asyncio.run(svc._kalshi_slip_send({'id': 'c', 'kalshiCfg': CFG, 'chat': []}, _slip()))
    assert tk['status'] == 'unknown' and 'may still fill' in tk['why'] and 'delete' not in calls
    calls = _slip_fake(monkeypatch, svc, Q, 'executed', accept_raises=kb.Refused('Kalshi refused the accept (400): x'))
    tk = asyncio.run(svc._kalshi_slip_send({'id': 'c', 'kalshiCfg': CFG, 'chat': []}, _slip()))
    assert tk['status'] == 'failed' and not tk.get('quoteId') and tk['end']['end'] == 'stopped'   # a clear no: nothing bought


def test_the_5_min_pass_reads_an_unknown_slip_back(svc, monkeypatch):
    import fc_pob
    row = {'id': 'kb5', 'kind': 'parlay', 'status': 'unknown', 'rfqId': 'r1', 'quoteId': 'q2', 'count': 2, 'price': 0.38, 'at': NOW, 'sentAt': NOW}
    cat = {'id': 'c', 'kalshiBids': [row], 'pobFolders': [], 'chat': []}

    async def rq(h, k, p, rid):
        return [{'id': 'q2', 'status': 'executed', 'yes_contracts_fp': '2.00', 'rfq_creator_order_id': 'ord1'}]
    monkeypatch.setattr(kb, 'rfq_quotes', rq); svc._use(_H())
    asyncio.run(fc_pob._kalshi_refresh(cat, 'kid', 'pem'))
    assert row['status'] == 'filled' and row['orderId'] == 'ord1' and row['usd'] == 0.76 and row['end']['end'] == 'confirmed'


# ── 3 · a filing never breaks halfway ──────────────────────────────────────────────────────────────────────────────────────────────────────
def test_a_filing_that_breaks_halfway_stops_cleanly_and_says_why(svc, monkeypatch):
    async def boom(cat, rd, now, notes, why):
        raise KeyError('legs')
    monkeypatch.setattr(svc, '_pob_topic_file', boom)
    cat = {'id': 'c', 'chat': [], 'pobFolders': [], 'kalshiBids': []}
    asyncio.run(svc._pob_file_safe(cat, {'topic': 'Rockets vs Pacers parlay', 'by': 'you'}, 1000.0, {}, ''))
    f = cat['pobFolders'][-1]
    assert f['id'] == 'pob1000' and f['noTrade'] and f['stopped'] and 'broke while filing' in f['why'] and 'pobFiling' not in cat and 'pob1000' not in svc._POB_FILING
    assert 'stopped cleanly' in cat['chat'][-1]['text'] and 'no money moved' in cat['chat'][-1]['text']


def test_a_break_after_a_bid_went_out_keeps_that_bid_on_the_folder(svc, monkeypatch):
    async def boom(cat, rd, now, notes, why):
        cat['kalshiBids'].append({'id': 'kb1', 'folder': 'pob1000', 'status': 'resting', 'orderId': 'o1', 'title': 'Houston', 'at': now})
        raise RuntimeError('scoreboard')
    monkeypatch.setattr(svc, '_pob_topic_file', boom)
    cat = {'id': 'c', 'chat': [], 'pobFolders': [], 'kalshiBids': []}
    asyncio.run(svc._pob_file_safe(cat, {'topic': 'Rockets vs Pacers', 'by': 'you'}, 1000.0, {}, ''))
    f = cat['pobFolders'][-1]
    assert f['kalshi']['orderId'] == 'o1' and not f['noTrade'] and 'already sent stands' in cat['chat'][-1]['text']


def test_a_restart_mid_filing_resumes_once_and_the_refile_waits_for_his_tap(svc):
    svc._POB_WANT.clear()
    cat = {'id': 'c', 'chat': [], 'pobFolders': [], 'kalshiBids': [], 'pobFiling': {'id': 'pob900', 'topic': 'Rockets vs Pacers parlay', 'by': 'you', 'at': 900}}
    svc._pob_cut_off(cat, 1000.0)
    assert cat['pobAsk'] == 'Rockets vs Pacers parlay' and cat['pobBy'] == 'resume' and cat['pobResumeOf'] == 'pob900' and svc._POB_WANT['c'] == 'start'
    assert 'Nothing was sent' in cat['chat'][-1]['text'] and not kb.sends_now({'mode': 'auto'}, 'resume')
    # cut off a second time → it stops cleanly, never loops
    cat2 = {'id': 'c2', 'chat': [], 'pobFolders': [], 'kalshiBids': [], 'pobFiling': {'id': 'pob950', 'topic': 'x', 'by': 'resume', 'at': 950, 'resumeOf': 'pob900'}}
    svc._pob_cut_off(cat2, 1000.0)
    assert cat2['pobFolders'][-1]['stopped'] and 'restarted' in cat2['pobFolders'][-1]['why'] and 'pobAsk' not in cat2
    # a TEST cut off stays a TEST
    cat3 = {'id': 'c3', 'chat': [], 'pobFolders': [], 'kalshiBids': [], 'pobFiling': {'id': 'pob960', 'topic': 'y', 'by': 'test', 'at': 960}}
    svc._pob_cut_off(cat3, 1000.0)
    assert cat3['pobBy'] == 'test'
    svc._POB_WANT.clear()


def test_the_engine_ticks_an_agent_whose_filing_was_cut_off(svc, monkeypatch):
    ticked = []

    async def tick(http, cat, now):
        ticked.append(cat['id'])
    monkeypatch.setattr(svc, '_pob_tick', tick)
    store = {'cats': {'a': {'id': 'a', 'pobFiling': {'id': 'pob1'}}, 'b': {'id': 'b'}}}
    asyncio.run(svc._pob_pass(store))
    assert ticked == ['a']


# ── blank minds and a TEST prop parlay, end to end (faked network) ────────────────────────────────────────────────────────────────────────
@pytest.fixture
def filer(svc, monkeypatch, tmp_path):
    monkeypatch.setattr(svc, 'POWSHOTS_DIR', tmp_path)
    monkeypatch.setattr(svc._ck, 'key_for', lambda *a, **k: None)   # Sicario's agent: no Kalshi key — a TEST still reads Kalshi's public markets

    async def markets_for(h, topic, games=None): return [MKT]
    async def legs_menu(h, games): return MENU
    async def empty(*a, **k): return {}
    async def none(*a, **k): return None
    monkeypatch.setattr(kb, 'markets_for', markets_for); monkeypatch.setattr(kb, 'legs_menu', legs_menu)
    monkeypatch.setattr(svc._tools, 'best_topic', none); monkeypatch.setattr(svc._tools, 'sport_board', empty)

    async def mk(*a, **k): return []
    monkeypatch.setattr(svc._tools, 'markets', mk)
    svc._WORK.clear()
    return svc


def test_both_minds_blank_files_plainly_with_nothing_sent(filer, monkeypatch):
    async def blank(cat, i, sys_, user_, n, box): return ''
    monkeypatch.setattr(filer, '_pow2_ask', blank)
    cat = {'id': 'c', 'chat': [], 'brainsCfg': {'brains': ['local/ossy', 'local/g4']}}
    notes = {'0': {'note': 'x' * 100, 'sites': ['espn.com']}, '1': {'note': 'y' * 100, 'sites': ['cbs.com']}}
    asyncio.run(filer._pob_file_safe(cat, {'topic': 'Rockets vs Pacers player props 2 legs', 'by': 'you'}, 2000.0, notes, ''))
    f = cat['pobFolders'][-1]
    assert f['noTrade'] and f['blank'] == ['ossy', 'g4'] and 'came back blank' in f['why'] and 'kalshi' not in f
    assert 'Nothing was sent; no money moved' in cat['chat'][-1]['text']


def test_one_blank_mind_is_named_and_the_other_minds_slip_waits_for_his_tap(filer, monkeypatch):
    async def ask(cat, i, sys_, user_, n, box):
        if i == 1:
            return '   '
        return json.dumps({'picks': [{'pick': 'Durant over', 'confidence': 80, 'evidence': 'espn: 27.4 a game', 'number': 27.4, 'kalshi': {'ticker': KD[1]['ticker'], 'side': 'yes'}},
                                     {'pick': 'Siakam under', 'confidence': 75, 'why': 'cbs: 14.8 last 5', 'kalshi': {'ticker': PS[1]['ticker'], 'side': 'no'}}]})
    monkeypatch.setattr(filer, '_pow2_ask', ask)
    sent = []

    async def no_send(cat, tk): sent.append(tk)
    monkeypatch.setattr(filer, '_kalshi_slip_send', no_send); monkeypatch.setattr(filer._ck, 'key_for', lambda *a, **k: 'x')   # his key is saved
    cat = {'id': 'c', 'chat': [], 'brainsCfg': {'brains': ['local/ossy', 'local/g4']}}
    notes = {'0': {'note': 'x' * 100}, '1': {'note': 'y' * 100}}
    asyncio.run(filer._pob_file_safe(cat, {'topic': 'Rockets vs Pacers player props 2 legs', 'by': 'you'}, 3000.0, notes, ''))
    f = cat['pobFolders'][-1]
    assert f['blank'] == ['g4'] and f['calls'][1]['pass'].startswith('came back blank') and sent == []   # one mind's slip is an offer, never sent by itself
    assert f['kalshi']['offer'] == 'ossy' and [g['ou'] for g in f['kalshi']['legs']] == ['over', 'under'] and f['kalshi']['end']['end'] == 'waiting'


def test_a_test_prop_parlay_files_its_legs_with_evidence_and_never_bids(filer, monkeypatch):
    asks = []

    async def ask(cat, i, sys_, user_, n, box):
        asks.append(user_)
        return json.dumps({'picks': [{'pick': 'Durant over 19.5', 'confidence': 78, 'evidence': f'mind {i}: espn 27.4 a game', 'number': 27.4, 'kalshi': {'ticker': KD[1]['ticker'], 'side': 'yes'}},
                                     {'pick': 'Siakam under 19.5', 'confidence': 72, 'evidence': f'mind {i}: cbs 14.8 last 5', 'number': 14.8, 'kalshi': {'ticker': PS[1]['ticker'], 'side': 'no'}},
                                     {'pick': 'made up', 'confidence': 90, 'evidence': 'x 1 y z abcdefg', 'kalshi': {'ticker': 'KXNBAPTS-26NOV18HOUIND-NOPE1-20', 'side': 'yes'}}]})
    monkeypatch.setattr(filer, '_pow2_ask', ask)
    sent = []

    async def send(cat, tk): sent.append(tk)
    monkeypatch.setattr(filer, '_kalshi_slip_send_raw', send)   # behind _kb_once: a TEST ticket never reaches it
    cat = {'id': 'c', 'chat': [], 'brainsCfg': {'brains': ['local/ossy', 'local/g4']}, 'kalshiCfg': {'mode': 'auto'}}
    notes = {'0': {'note': 'x' * 100}, '1': {'note': 'y' * 100}}
    asyncio.run(filer._pob_file_safe(cat, {'topic': 'Rockets vs Pacers player props 2 legs', 'by': 'test'}, 4000.0, notes, ''))
    f = cat['pobFolders'][-1]
    assert 'OVER 19.5 = YES' in asks[0] and '"number"' in asks[0]   # the minds saw the over/under lines and were told to give a number
    k = f['kalshi']
    assert f['testRun'] and k['test'] and k['end']['end'] == 'test' and sent == [] and k['status'] == 'waiting'   # both agreed, AUTO on: a TEST still never sends (and no tap can)
    assert [(g['stat'], g['ou'], g['line']) for g in k['legs']] == [('points', 'over', 19.5), ('points', 'under', 19.5)]
    assert all(len(g['backing']) == 2 and all(b['number'] is not None and b['evidence'] for b in g['backing']) for g in k['legs'])
    assert [d['why'] for d in f['legsDropped']] == ['not a market Kalshi lists for this game'] * 2 and len(f['legMenu']) == len(MENU)
    json.dumps(f)


# ── review fixes (code-review high, 2026-11-18) ───────────────────────────────────────────────────────────────────────────────────────────
def test_an_unknown_send_counts_in_todays_cap_and_a_resolved_one_is_saved(svc):
    cat, tk = _send(svc, _H(place=TimeoutError('t'), orders=[]))
    assert tk['usd'] == 0.6 and kb.spent_today(cat['kalshiBids']) == 0.6   # it may be real: counted
    import fc_pob
    row = cat['kalshiBids'][-1]; row['sentAt'] = row['at'] = NOW - 600
    svc._use(_H(orders=[]))
    assert asyncio.run(fc_pob._kalshi_refresh(cat, 'kid', 'pem')) == 1   # a change the caller must save
    assert row['status'] == 'failed' and kb.spent_today(cat['kalshiBids']) == 0


def test_an_empty_quote_read_never_turns_an_unknown_slip_into_nothing_bought(svc, monkeypatch):
    import fc_pob
    row = {'id': 'kb6', 'kind': 'parlay', 'status': 'unknown', 'rfqId': 'r1', 'quoteId': 'q2', 'count': 2, 'price': 0.38, 'usd': 0.76, 'at': NOW - 9999, 'sentAt': NOW - 9999}
    cat = {'id': 'c', 'kalshiBids': [row], 'pobFolders': [], 'chat': []}

    async def empty(h, k, p, rid): return []
    monkeypatch.setattr(kb, 'rfq_quotes', empty); svc._use(_H())
    asyncio.run(fc_pob._kalshi_refresh(cat, 'kid', 'pem'))
    assert row['status'] == 'unknown' and kb.reached(row) and kb.spent_today(cat['kalshiBids']) == 0.76

    async def gone(h, k, p, rid): return [{'id': 'q2', 'status': 'cancelled'}]
    monkeypatch.setattr(kb, 'rfq_quotes', gone)
    asyncio.run(fc_pob._kalshi_refresh(cat, 'kid', 'pem'))
    assert row['status'] == 'refused' and row['end']['end'] == 'stopped'


def test_the_5_min_settle_pass_reads_unknown_sends_back(svc, monkeypatch):
    import fc_pob
    row = {'id': 'kb7', 'ticker': MKT['ticker'], 'status': 'unknown', 'clientId': 'cid7', 'sentAt': NOW - 600, 'at': NOW - 600, 'count': 1, 'price': 0.6}
    store = {'cats': {'c': {'id': 'c', 'kalshiBids': [row], 'pobFolders': [], 'chat': []}}}
    saved = []
    monkeypatch.setattr(svc, '_save', lambda s: saved.append(1))
    svc._use(_H(orders=[{'order_id': 'o3', 'client_order_id': 'cid7', 'status': 'resting', 'fill_count_fp': '0.00', 'remaining_count_fp': '1.00'}]))
    asyncio.run(fc_pob._kalshi_settle_pass(None, store, NOW))
    assert row['orderId'] == 'o3' and row['end']['end'] == 'confirmed' and saved


def test_one_minds_model_error_is_that_mind_blank_not_both_lost(svc):
    async def ok(): return '{"picks": []}'
    async def bad(): raise RuntimeError('LM Studio 500')
    assert asyncio.run(svc._minds_ask([ok(), bad()], 5)) == ['{"picks": []}', '']


def test_a_canceled_order_with_nothing_filled_says_no_money_moved():
    e = kb.end_of({'orderId': 'o1', 'confirmedAt': 1, 'status': 'canceled', 'filled': 0, 'title': 'Houston'})
    assert e['end'] == 'stopped' and kb.NO_MONEY in e['say'] and 'canceled' in e['say']


def test_the_filing_mark_is_saved_before_the_minds_are_asked(svc, monkeypatch):
    saved = []

    async def file_(cat, rd, now, notes, why):
        saved_mark = list(saved)
        assert saved_mark and saved_mark[-1] == 'pob5000'

    def save(store):
        saved.append(store['cats']['c'].get('pobFiling', {}).get('id'))
    monkeypatch.setattr(svc, '_pob_topic_file', file_); monkeypatch.setattr(svc, '_save', save)
    cat = {'id': 'c', 'chat': [], 'pobFolders': []}
    asyncio.run(svc._pob_file_safe(cat, {'topic': 't', 'by': 'you'}, 5000.0, {}, '', store={'cats': {'c': cat}}))
    assert saved == ['pob5000'] and 'pobFiling' not in cat


# ── from the real TEST PoB #5 on Sicario (Jazz vs Lakers, 2026-11-18) ──────────────────────────────────────────────────────────────────────
def test_a_leg_named_in_words_is_tagged_and_kalshis_own_line_is_not_evidence():
    calls = [{'name': 'ossy', 'picks': [
        {'pick': 'HOUKDURANT7-20', 'confidence': 70, 'why': f"Kevin Durant points OVER 19.5 YES 0.63 ({KD[1]['ticker']})"},
        {'pick': 'Siakam under', 'confidence': 70, 'why': f"UNDER: cbs has him at 14.8 a game ({PS[1]['ticker']})"},
        {'pick': 'Houston', 'confidence': 70, 'why': 'no ticker here'}]}]
    kb.tag_legs(calls, MENU)
    p = calls[0]['picks']
    assert p[0]['kalshi'] == {'ticker': KD[1]['ticker'], 'side': 'yes'} and p[1]['kalshi'] == {'ticker': PS[1]['ticker'], 'side': 'no'} and 'kalshi' not in p[2]
    assert kb.leg_backing(p[0], KD[1]) is None   # 19.5 and 0.63 are Kalshi's own line and price: not evidence
    assert kb.leg_backing(p[1], PS[1])[1] == 14.8
    s = kb.mind_slips(calls, MENU)
    assert s[0]['mind'] == 'ossy' and [r['ticker'] for r in s[0]['legs']] == [PS[1]['ticker']] and s[0]['legs'][0]['number'] == 14.8


def test_espn_season_numbers_reach_the_minds_beside_kalshis_line():
    """The real shape of ESPN's /teams/lal/athletes/statistics (read 2026-11-18)."""
    j = {'results': [{'name': 'game', 'leaders': [{'athlete': {'displayName': 'Kevin Durant'}, 'statistics': [{'name': 'general', 'stats': [
        {'name': 'avgRebounds', 'value': 5.1}, {'name': 'avgMinutes', 'value': 34.0}, {'name': 'gamesPlayed', 'value': 13.0}]}, {'name': 'offensive', 'stats': [
        {'name': 'avgPoints', 'value': 27.4}, {'name': 'avgAssists', 'value': 4.2}, {'name': 'avgThreePointFieldGoalsMade', 'value': 2.1}]}]}]}]}
    pl = kb.player_lines(j)
    assert kb.season_avg(KD[1], pl) == 27.4 and kb.season_avg({**KD[1], 'ticker': 'KXNBAPRA-26NOV18HOUIND-HOUKDURANT7-35'}, pl) == 36.7
    assert kb.season_avg(PS[1], pl) is None and kb.season_avg({**KD[1], 'yes_sub_title': 'Kévin Durant: 20+'}, pl) == 27.4   # accents never break the match
    note = kb.player_note(MENU, pl)
    assert 'Kevin Durant: 27.4 pts, 5.1 reb, 4.2 ast, 2.1 threes, 34.0 min a game over 13 games' in note and 'PLAYER NUMBERS' in note and kb.player_note(MENU, {}) == ''


def test_a_named_legs_side_never_flips_on_everyday_words():
    t = KD[1]['ticker']
    calls = [{'name': 'm', 'picks': [{'pick': 'a', 'why': f'{t}: he is not injured, no doubt he plays', 'confidence': 70},
                                     {'pick': 'b', 'why': f'{t} OVER now, maybe UNDER later', 'confidence': 70},
                                     {'pick': 'c', 'why': f'{t} UNDER 19.5, cbs 14.8 avg', 'confidence': 70}]}]
    kb.tag_legs(calls, MENU)
    p = calls[0]['picks']
    assert p[0]['kalshi']['side'] == 'yes' and 'kalshi' not in p[1] and p[2]['kalshi']['side'] == 'no'


def test_test_pob_9_a_jersey_number_or_a_made_up_season_average_is_not_evidence():
    """🧪 Real TEST PoB #9 (Knicks vs Timberwolves): ossy wrote 'backed by his 8.2 season average' for Anunoby (ticker …OANUNOBY8-15) and '27.0'
    for Gobert (…RGOBERT27-10): the ticker's jersey digits, not ESPN's numbers. ESPN's player numbers never arrived (tomorrow's game)."""
    an = {**_rung('OG Anunoby', 'NYKOANUNOBY8', 15, 0.59), 'ticker': 'KXNBAPTS-26NOV19NYKMIN-NYKOANUNOBY8-15'}
    assert kb.leg_backing({'why': f"Kalshi price shows 0.59 for YES (Over) on {an['ticker']}, backed by his 8 season average"}, an) is None   # the jersey
    real = {**an, 'espnAvg': 16.8}
    assert kb.leg_backing({'why': 'espn.com season average 8.2 points a game'}, real) is None   # not what ESPN shows
    assert kb.leg_backing({'why': 'espn.com season average 16.8 points a game'}, real) == ('espn.com season average 16.8 points a game', 16.8)
    assert 'ESPN season avg 16.8' in kb.leg_line(real)
    assert kb.teams_of([{'ticker': 'KXNBAGAME-26NOV19NYKMIN-NYK'}, {'ticker': 'KXNBAGAME-26NOV19NYKMIN-MIN'}]) == ['ny', 'min']
    assert kb.teams_of([{'ticker': 'KXNBAGAME-26NOV18UTALAL-UTA'}, {'ticker': 'KXNBAGAME-26NOV18UTALAL-LAL'}]) == ['utah', 'lal']
