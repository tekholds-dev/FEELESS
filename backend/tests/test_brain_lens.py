import asyncio
import trench_brain as tb


def test_brain_lens_ranks_safe_coins_by_learned_play_and_engine_waits_for_proof(monkeypatch):
    import reputation_service as rs
    good = dict(top10=10, site='s', x='x')
    done = [{'mint': 'm%d' % i, 'at': i, 'play': 50.0 if i % 3 == 0 else -30.0, 'how': 'hit' if i % 3 == 0 else 'cut',
             'f': tb.feats({'ageH': 0.5, 'safe': True, **(good if i % 3 == 0 else {'top10': 40})})} for i in range(120)]
    st = {'done': done, 'open': {}}
    rs._brain.update(tbl=tb.table(done), sum={**tb.summary(st)})
    board = [{'mint': 'A', 'symbol': 'A', 'price': 1.0, 'ageH': 0.5, 'safe': True, 'top10': 22, 'liq': 9e3},
             {'mint': 'B', 'symbol': 'B', 'price': 1.0, 'ageH': 0.5, 'safe': True, **good, 'liq': 9e3},
             {'mint': 'C', 'symbol': 'C', 'price': 1.0, 'ageH': 0.5, 'safe': False, **good}]
    monkeypatch.setattr(rs, '_open_board', lambda: [dict(x) for x in board])
    monkeypatch.setattr(rs, '_clean_rows', lambda rows: rows)
    out = asyncio.run(rs._fuses_discover_raw('brain', 'solana'))['pools']
    assert [r['symbol'] for r in out] == ['B', 'A']                     # unsafe C never listed; the learned look first
    assert out[0]['brain']['est'] > 0 > out[1]['brain']['est'] and '🧠 learned play' in out[0]['divisionLabel']
    assert rs._brain_ready()                                           # synthetic record proves itself walk-forward
    rs._brain.update(sum={**tb.summary({'done': done[:30], 'open': {}})})
    assert not rs._brain_ready()                                       # too few unseen coins → a list only, never an engine buy
    rs._brain.update(at=0.0, tbl={}, sum=None)


def test_live_movers_are_real_5_minute_moves_and_best_now_is_never_empty(monkeypatch):
    import reputation_service as rs
    board = [{'mint': 'M', 'symbol': 'M', 'price': 1.0, 'safe': True, 'vol5m': 8000, 'chg5m': 12, 'txns1h': 400, 'buyShare': 60},
             {'mint': 'F', 'symbol': 'F', 'price': 1.0, 'safe': False, 'vol5m': 9000, 'chg5m': 30, 'txns1h': 400, 'buyShare': 60},   # failed scan
             {'mint': 'T', 'symbol': 'T', 'price': 1.0, 'safe': None, 'vol5m': 500, 'chg5m': 40, 'txns1h': 400, 'buyShare': 60},     # $500 = not a mover
             {'mint': 'S', 'symbol': 'S', 'price': 1.0, 'safe': None, 'vol5m': 6000, 'chg5m': 5, 'txns1h': 90, 'buyShare': 40}]      # sellers lead
    monkeypatch.setattr(rs, '_open_board', lambda: [dict(x) for x in board])
    monkeypatch.setattr(rs, '_clean_rows', lambda rows: rows)
    out = rs._live_movers()
    assert [r['symbol'] for r in out] == ['M'] and '+12% in 5m on $8.0K traded' in out[0]['divisionLabel']
    monkeypatch.setattr(rs, '_best_rows', [])
    monkeypatch.setattr(rs, '_edge_cache', {'rows': [{'mint': 'E', 'symbol': 'E', 'priceUsd': 1.0, 'edge': {'edge': 2.2}}]})
    monkeypatch.setattr(rs, '_cand_map', lambda: {'E': {'liq': 60000, 'chg1h': 4}})
    best = asyncio.run(rs._fuses_discover_raw('best', 'solana'))['pools']
    assert best[0]['symbol'] == 'E' and best[0]['liquidityUsd'] == 60000 and 'evidence +2.2%/1h' in best[0]['divisionLabel']


def test_hand_swap_takes_best_list_first_then_only_clean_coins(monkeypatch):
    import reputation_service as rs
    reads = {'W': 'WASH TRADED', 'B': 'BLOW-OFF TOP', 'C': 'COOLING', 'R': 'RUG BAIT', 'H': 'WATCH'}
    monkeypatch.setattr(rs, '_with_tv', lambda x: {**x, 'tv': {'call': ['', reads.get(x['mint'], 'WATCH')], 'rug': 70 if x['mint'] == 'H' else 10}})
    monkeypatch.setattr(rs, '_best_rows', [{'mint': 'Z'}])
    row = lambda m, **k: {'mint': m, 'symbol': m, 'vol1h': 100_000, 'vol5m': 5000, 'txns1h': 500, 'buyShare': 60, 'chg1h': 20, 'chg5m': 1, 'liq': 80_000, **k}
    rows = [row('W', chg1h=300), row('B'), row('C', vol1h=60_000), row('R'), row('H'), row('P', chg5m=9), row('OK'), row('Z')]
    out = [x['mint'] for x in rs._swap_clean(rows)]
    assert out == ['Z', 'OK', 'C']          # 🏆 Best first · wash / blow-off / rug bait / rug meter 70 / mid-candle chase all out · busiest first
