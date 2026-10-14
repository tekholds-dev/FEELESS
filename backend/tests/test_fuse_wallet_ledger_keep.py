import fuse_wallet as fw


def test_the_doc_keeps_a_day_of_rows_bounded_both_ways():
    now = 1_000_000.0
    rows = [{'id': i, 'at': now - (3000 - i) * 120} for i in range(3000)]   # one row every 2 min for 100h
    kept = fw.recent_rows(rows, now)
    assert kept[-1]['id'] == 2999 and all(now - r['at'] <= fw.LEDGER_KEEP_SEC for r in kept) and len(kept) == 780
    quiet = [{'id': i, 'at': now - (400 - i) * 3600} for i in range(400)]   # one an hour: still ≥ 300 rows
    assert len(fw.recent_rows(quiet, now)) == 300
    busy = [{'id': i, 'at': now - (5000 - i)} for i in range(5000)]           # a row a second: ≤ 2000
    assert len(fw.recent_rows(busy, now)) == 2000
