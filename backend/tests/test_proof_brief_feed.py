"""📰 + 🔔 (owner 2026-11-10): the daily proofs brief and the desk bell read the proof record only; real filing time wins over a backfill."""
import time
import proof_events as pev


def test_brief_ranks_by_review_and_grades_and_counts_real_filing_time(tmp_path):
    db = tmp_path / 'ev.db'; now = time.time()
    pev.append(db, 'pob', 'b1', 'file', {'filedAt': now - 3600, 'status': 'filed'}, cat='c1')
    pev.append(db, 'pob', 'b1', 'review', {'score': 80, 'verdict': 'pass'}, cat='c1')
    pev.append(db, 'pob', 'b1', 'grade', {'graded': 'right'}, cat='c1')
    pev.append(db, 'pos', 's1', 'file', {'filedAt': now - 3 * 86400, 'status': 'filed'}, cat='c1')   # backfilled today, filed 3 days ago
    pev.append(db, 'pos', 's1', 'review', {'score': 20, 'verdict': 'fail'}, cat='c1')
    pev.append(db, 'pow', 'w1', 'file', {'filedAt': now - 30 * 86400}, cat='c1')                     # older than a week: not counted
    b = pev.brief(db, now)
    by = {r['kind']: r for r in b['rows']}
    assert b['best'] == 'pob' and by['pob']['avgScore'] == 80 and by['pob']['passPct'] == 100 and by['pob']['rightPct'] == 100
    assert (by['pos']['filed24'], by['pos']['filed7']) == (0, 1) and by['pow']['filed7'] == 0
    assert by['poc']['heat'] == 0   # nothing reviewed: can't top the brief


def test_bell_reads_one_agents_newest_steps_with_verdicts(tmp_path):
    db = tmp_path / 'ev.db'
    pev.append(db, 'pow', 'w1', 'review', {'score': 0, 'verdict': 'fail'}, cat='c1', at=100)
    pev.append(db, 'pos', 's1', 'grade', {'graded': 'right'}, cat='c1', at=200)
    pev.append(db, 'pos', 's2', 'grade', {'graded': 'right'}, cat='other', at=300)
    rows = pev.recent(db, 'c1')
    assert [(r['kind'], r['event'], r['detail'], r['bad']) for r in rows] == [('pos', 'grade', 'right', False), ('pow', 'review', 'fail 0/100', True)]
    assert pev.recent(db, 'c1', since=150)[0]['ref'] == 's1' and len(pev.recent(db, 'c1', since=150)) == 1
