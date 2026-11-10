"""COL-7 (found 2026-11-10): a PoB filed before its game was played kept 'none' in the stash forever (9 of 10 real PoBs). It now takes
its result once, when it settles. A settled result never flips, and the stored copy never changes."""
import collective_stash as st


def test_a_proof_settles_once_in_the_stash(tmp_path):
    f = {'id': 'b1', 'status': 'closed', 'at': 1, 'sites': ['espn.com', 'kalshi.com']}
    cat = {'id': 'c1', 'pobFolders': [f]}
    assert st.ingest_cat(tmp_path, cat, lambda x: x, lambda *a: None) == 2
    out = lambda: dict(st._db(tmp_path).execute("select key, outcome from items").fetchall())
    assert set(out().values()) == {'none'}
    sha = st._db(tmp_path).execute("select sha from items where key='pobFolders:b1'").fetchone()[0]
    f['graded'] = 'right'
    assert st.ingest_cat(tmp_path, cat, lambda x: x, lambda *a: None) == 0   # nothing new stored
    assert set(out().values()) == {'won'}   # the folder and its source rows
    assert st._db(tmp_path).execute("select sha from items where key='pobFolders:b1'").fetchone()[0] == sha   # the kept copy is the same
    f['graded'] = 'wrong'
    st.ingest_cat(tmp_path, cat, lambda x: x, lambda *a: None)
    assert set(out().values()) == {'won'}   # a settled result never flips
