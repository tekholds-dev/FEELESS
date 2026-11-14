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
    sent = []
    async def market(h, t): return {'ticker': t, 'status': 'active', 'close_time': '2099-01-01T00:00:00Z', 'yes_ask': 40}
    async def balance(h, k, p): return 10.0
    async def place(h, k, p, body): sent.append(body); return {'order_id': 'o1', 'status': 'resting'}
    async def order_status(h, k, p, oid): return {'order_id': oid, 'status': 'executed', 'fill_count': 2}
    monkeypatch.setattr(kb, 'market', market); monkeypatch.setattr(kb, 'balance', balance)
    monkeypatch.setattr(kb, 'place', place); monkeypatch.setattr(kb, 'order_status', order_status)
    monkeypatch.setattr(kb, 'split_key', lambda s: ('kid', 'pem'))
    monkeypatch.setattr(fs._ck, 'key_for', lambda *a, **k: 'x')
    cat = {'id': 'c1', 'kalshiCfg': {'on': True}, 'chat': []}
    tk = {'id': 'kb1', 'ticker': 'KXNBAGAME-X', 'side': 'yes', 'title': 'Lakers win', 'conf': [80, 70], 'price': 0.4, 'status': 'waiting'}
    asyncio.run(fs._kalshi_send(cat, tk))
    assert len(sent) == 1 and sent[0]['type'] == 'limit'                  # one limit order, never re-sent
    assert tk['status'] == 'filled' and tk['filled'] == 2 and tk['confirmedAt']
    assert cat['kalshiBids'][-1]['status'] == 'filled' and cat['kalshiBids'][-1]['confirmedAt']
    assert 'Kalshi confirmed' in cat['chat'][-1]['text']


def test_a_failed_read_back_never_resends(monkeypatch):
    async def boom(h, k, p, oid): raise RuntimeError('Kalshi said 503')
    monkeypatch.setattr(kb, 'order_status', boom)
    row = {'orderId': 'o2', 'count': 1, 'price': 0.5, 'status': 'resting'}
    asyncio.run(fs._kalshi_confirm(None, 'k', 'p', row))
    assert row['status'] == 'resting' and '503' in row['confirmErr']
