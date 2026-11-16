"""Owner 2026-11-14: "they should check and confirm the bid on kalshi works" — after sending, the agent reads the order back from Kalshi."""
import asyncio
import time

import feecat_service as fs
import kalshi_bid as kb


def test_settle_reads_kalshis_own_record():
    assert kb.settle({'status': 'executed', 'fill_count': 2}, 2, 0.4) == {'status': 'filled', 'filled': 2, 'usd': 0.8, 'kalshiStatus': 'executed'}
    assert kb.settle({'status': 'resting', 'fill_count': 0}, 2, 0.4)['status'] == 'resting'
    assert kb.settle({'status': 'resting', 'remaining_count': 1, 'initial_count': 2}, 2, 0.4)['filled'] == 1
    gone = kb.settle({'status': 'canceled', 'fill_count': 0}, 2, 0.4)
    assert gone['status'] == 'canceled' and gone['usd'] == 0          # a canceled, unfilled order frees today's cap
    assert kb.spent_today([{'status': 'canceled', 'usd': 0, 'at': time.time()}]) == 0
    part = kb.settle({'status': 'canceled', 'fill_count': 1}, 2, 0.4)
    assert part['status'] == 'filled' and part['usd'] == 0.4


def test_send_then_confirm_and_say_it_in_chat(monkeypatch):
    monkeypatch.setattr(fs, "_KB_SENT", {})   # the one-send claim set is per process: another test in this worker may have claimed the same ticket id
    sent = []
    async def market(h, t): return {'ticker': t, 'status': 'active', 'close_time': '2099-01-01T00:00:00Z', 'yes_ask': 40}
    async def balance(h, k, p, m=None): return 10.0
    async def place(h, k, p, body): sent.append(body); return {'order_id': 'o1', 'status': 'resting'}
    async def order_status(h, k, p, oid): return {'order_id': oid, 'status': 'executed', 'fill_count': 2}
    monkeypatch.setattr(kb, 'market', market); monkeypatch.setattr(kb, 'balance', balance)
    monkeypatch.setattr(kb, 'place', place); monkeypatch.setattr(kb, 'order_status', order_status)
    monkeypatch.setattr(kb, 'split_key', lambda s: ('kid', 'pem'))
    monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: 'x')
    started = [False]
    async def unstarted(h, m): return not started[0]
    monkeypatch.setattr(kb, 'unstarted', unstarted)
    cat = {'id': 'c1', 'kalshiCfg': {}, 'chat': []}
    tk = {'id': 'kb1', 'ticker': 'KXNBAGAME-X', 'side': 'yes', 'title': 'Lakers win', 'conf': [80, 70], 'price': 0.4, 'status': 'waiting'}
    asyncio.run(fs._kalshi_send(cat, tk))
    assert len(sent) == 1 and sent[0]['side'] == 'bid'                  # one limit order, never re-sent
    assert tk['status'] == 'filled' and tk['filled'] == 2 and tk['confirmedAt']
    assert cat['kalshiBids'][-1]['status'] == 'filled' and cat['kalshiBids'][-1]['confirmedAt']
    assert 'Kalshi confirmed' in cat['chat'][-1]['text']
    started[0] = True   # ⏱ the game began between the pick and the send: refused, nothing sent (owner 2026-11-15)
    tk2 = {**tk, 'id': 'kb2', 'ticker': 'KXNBAGAME-Y', 'status': 'waiting'}; tk2.pop('orderId', None)
    asyncio.run(fs._kalshi_send(cat, tk2))
    assert len(sent) == 1 and tk2['status'] == 'refused' and 'already started' in tk2['why']


def test_a_failed_read_back_never_resends(monkeypatch):
    async def boom(h, k, p, oid): raise RuntimeError('Kalshi said 503')
    monkeypatch.setattr(kb, 'order_status', boom)
    row = {'orderId': 'o2', 'count': 1, 'price': 0.5, 'status': 'resting'}
    asyncio.run(fs._kalshi_confirm(None, 'k', 'p', row))
    assert row['status'] == 'resting' and '503' in row['confirmErr']


def test_after_the_payout_both_minds_write_their_final_word_once(monkeypatch):
    asked = []
    async def ask(cat, i, sys_, user_, n=180, box=None, kind=None): asked.append((i, user_)); return f'mind {i}: the rest edge held.'
    monkeypatch.setattr(fs, '_pow2_ask', ask)
    f = {'id': 'pob9', 'topic': 'Mavericks vs Celtics', 'kalshi': {'orderId': 'o9', 'ticker': 'T', 'side': 'yes', 'title': 'Dallas wins', 'price': 0.4, 'count': 2},
         'calls': [{'mind': 0, 'name': 'hy4', 'picks': [{'pick': 'Mavericks', 'confidence': 70, 'why': 'rest'}]}, {'mind': 1, 'name': 'glm', 'picks': [], 'pass': 'no odds'}]}
    cat = {'id': 'c', 'pobFolders': [f], 'chat': []}
    b = {'orderId': 'o9', 'filled': 2, 'outcome': 'won'}
    rows = asyncio.run(fs._pob_final(cat, b))
    assert [r['name'] for r in rows] == ['hy4', 'glm'] and f['final'] == rows and 'After the payout' in cat['chat'][-1]['text']
    assert 'WON, paid out $2.0, P&L $1.2 (fees not counted)' in asked[0][1] and 'no pick: no odds' in asked[1][1]
    assert asyncio.run(fs._pob_final(cat, b)) == [] and len(asked) == 2   # once only
