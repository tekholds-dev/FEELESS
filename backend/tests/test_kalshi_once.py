"""🔒 Real Kalshi bids: one send per ticket, a failed send never blocks or counts, and a sent bid is never forgotten (owner 2026-11-15:
'no bugs where multiple filings get made and no … real money kalshi trade go'). Network faked; nothing reaches Kalshi."""
import asyncio
import time

import kalshi_bid as kb

NOW = time.time()
CFG = {'on': True, 'bidUsd': 1, 'dayUsd': 2, 'floorUsd': 2, 'minConf': 65}
MKT = {'ticker': 'KXNBAGAME-26NOV15OKCSAC-OKC', 'status': 'active', 'close_time': '2099-01-01T00:00:00Z', 'yes_ask_dollars': '0.81', 'yes_ask': 81}
PICK = {'ticker': MKT['ticker'], 'side': 'yes', 'conf': [81, 72]}


def test_a_send_kalshi_refused_never_blocks_the_next_bid_or_counts_in_todays_cap():
    failed = [{'ticker': MKT['ticker'], 'status': 'failed', 'orderId': None, 'usd': None, 'at': NOW - 60}]   # PoB #16: the 410
    ok, why, n, px = kb.check(CFG, MKT, PICK, failed, 10.0, NOW)
    assert ok and n == 1 and px == 0.81, why
    assert kb.spent_today(failed, NOW) == 0


def test_a_placed_order_whose_read_back_failed_still_blocks_and_counts():
    placed = [{'ticker': MKT['ticker'], 'status': 'failed', 'orderId': 'o1', 'usd': 0.81, 'at': NOW - 60}]
    assert kb.spent_today(placed, NOW) == 0.81
    ok, why, _n, _p = kb.check(CFG, MKT, PICK, placed, 10.0, NOW)
    assert not ok and 'already bid on this market' in why


def test_two_approve_taps_at_once_send_exactly_one_order(monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, '_KB_SENT', {})
    sent = []

    async def slow_send(cat, tk):
        sent.append(tk['id']); await asyncio.sleep(0.05); tk['status'] = 'filled'; return tk
    once = fs._kb_once(slow_send)
    cat = {'id': 'c', 'kalshiBids': []}; tk = {'id': 'kbTAP', 'status': 'waiting'}

    async def both():
        return await asyncio.gather(once(cat, tk), once(cat, tk), return_exceptions=True)
    out = asyncio.run(both())
    assert sent == ['kbTAP']
    assert sum(isinstance(x, fs.AlreadySent) for x in out) == 1
    try:   # later, from a copy that already has its ledger row: still refused
        asyncio.run(fs._kb_once(slow_send)({'id': 'c', 'kalshiBids': [{'id': 'kbOLD'}]}, {'id': 'kbOLD'}))
        assert False
    except fs.AlreadySent:
        pass


def test_an_older_copy_saving_over_a_sent_bid_never_loses_it(monkeypatch):
    import feecat_service as fs
    monkeypatch.setattr(fs, '_KB_LEDGER', {})
    cat = {'id': 'c', 'kalshiBids': []}
    row = {'id': 'kb1', 'ticker': MKT['ticker'], 'status': 'filled', 'orderId': 'o1', 'usd': 0.81, 'count': 1, 'price': 0.81, 'at': NOW}
    fs._kb_remember(cat, row)
    stale = {'cats': {'c': {'id': 'c', 'kalshiBids': [], 'pobFolders': [{'id': 'f', 'kalshi': {'id': 'kb1', 'status': 'waiting'}}]}}}
    fs._kb_merge(stale)
    c = stale['cats']['c']
    assert [b['id'] for b in c['kalshiBids']] == ['kb1'] and c['pobFolders'][0]['kalshi']['status'] == 'filled' and c['pobFolders'][0]['kalshi']['orderId'] == 'o1'
    fs._kb_merge(stale)
    assert len(c['kalshiBids']) == 1   # added once, never twice
