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
