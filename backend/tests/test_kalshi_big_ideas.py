"""Owner 2026-11-14 "do all of the big ideas": hedge card, Kalshi results → COMP lessons + live price, streak offer, rivals. Network faked."""
import asyncio
import time

import comp_v2
import feecat_service as fs
import kalshi_bid as kb

MK = [{'ticker': 'T1', 'title': 'Lakers win', 'yes_ask': 40, 'no_ask': 62}, {'ticker': 'T2', 'title': 'Suns win', 'yes_ask': 55, 'no_ask': 47}]


def _call(mind, t, side, conf):
    return {'mind': mind, 'name': 'AB'[mind], 'picks': [{'confidence': conf, 'why': 'r', 'kalshi': {'ticker': t, 'side': side}}]}


def test_hedge_shows_each_side_only_when_they_split():
    split = kb.split_view([_call(0, 'T1', 'yes', 70), _call(1, 'T1', 'no', 66)], MK)
    assert [(r['side'], r['price']) for r in split] == [('yes', 0.4), ('no', 0.62)]
    assert kb.split_view([_call(0, 'T1', 'yes', 70), _call(1, 'T1', 'yes', 66)], MK) == []   # they agreed → a ticket, not a hedge


def test_lesson_streak_and_an_offer_never_over_the_caps():
    now = time.time()
    won = [{'outcome': 'won', 'settledAt': now - i} for i in range(3)]
    assert kb.streak(won) == 3 and kb.streak([{'outcome': 'lost', 'settledAt': now}] + won) == 0
    assert kb.raise_offer({'bidUsd': 1, 'dayUsd': 2}, won) == {'streak': 3, 'from': 1.0, 'to': 2.0}
    assert kb.raise_offer({'bidUsd': 1, 'dayUsd': 2}, won[:2]) is None
    assert kb.raise_offer({'bidUsd': 5, 'dayUsd': 20}, won) is None                      # already at the hard max
    row = kb.lesson({'orderId': 'o1', 'title': 'Lakers win', 'side': 'yes', 'price': 0.4, 'minds': ['A: pace', 'B: injuries'], 'outcome': 'won'})
    assert row['kind'] == 'PoB · Kalshi' and row['outcome'] == 'won' and 'pace' in row['plan'] and 'won' not in row['plan']


def test_rivals_name_the_winner_and_loser():
    rows = [{'agent': 'a', 'name': 'Happy', 'ticker': 'T1', 'side': 'yes', 'result': 'no', 'at': 2},
            {'agent': 'b', 'name': 'Fee', 'ticker': 'T1', 'side': 'no', 'at': 1},
            {'agent': 'a', 'name': 'Happy', 'ticker': 'T2', 'side': 'yes', 'at': 1}, {'agent': 'a', 'name': 'Happy', 'ticker': 'T2', 'side': 'no', 'at': 1}]
    r = kb.rivals(rows)
    assert len(r) == 1 and r[0]['winner'] == 'Fee' and r[0]['loser'] == 'Happy'


def test_settle_pass_grades_a_filled_bid_and_files_one_lesson(monkeypatch, tmp_path):
    monkeypatch.setattr(comp_v2, 'DATA', tmp_path)
    async def market(h, t): return {'ticker': t, 'yes_ask': 99, 'result': 'yes'}
    monkeypatch.setattr(kb, 'market', market); monkeypatch.setattr(fs, '_save', lambda s: None)
    bid = {'ticker': 'T1', 'title': 'Lakers win', 'side': 'yes', 'price': 0.4, 'status': 'filled', 'orderId': 'o1', 'at': time.time(), 'minds': ['pace']}
    rest = {'ticker': 'T1', 'side': 'no', 'status': 'resting', 'orderId': 'o2', 'at': time.time()}
    cat = {'id': 'c', 'chat': [], 'kalshiBids': [bid, rest], 'pobFolders': [{'kalshi': {'orderId': 'o1'}}]}
    store = {'cats': {'c': cat}}
    asyncio.run(fs._kalshi_settle_pass(None, store, time.time())); asyncio.run(fs._kalshi_settle_pass(None, store, time.time()))
    assert bid['outcome'] == 'won' and cat['pobFolders'][0]['kalshi']['outcome'] == 'won'
    assert 'outcome' not in rest and 'livePx' in rest                           # an unfilled order neither won nor lost
    assert len(comp_v2.kalshi_rows(tmp_path)) == 1 and 'COMP lesson' in cat['chat'][0]['text'] and len(cat['chat']) == 1


def test_dataset_takes_the_kalshi_lessons(tmp_path, monkeypatch):
    monkeypatch.setattr(comp_v2._market, 'rows', lambda f, n: [])
    comp_v2.add_kalshi_row({'id': 'kalshi:o1', 'kind': 'PoB · Kalshi', 'title': 'x', 'outcome': 'won'}, tmp_path)
    assert comp_v2.add_kalshi_row({'id': 'kalshi:o1', 'kind': 'PoB · Kalshi', 'title': 'x', 'outcome': 'won'}, tmp_path) is False
    counts = comp_v2.write_dataset([{'id': f'p{i}', 'kind': 'PoW', 'title': 't', 'outcome': 'lost'} for i in range(9)], tmp_path)
    assert counts['won'] == 1 and 'PoB · Kalshi' in counts['kinds']
