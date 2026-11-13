"""🗄 SITE-8 · wallet profiles live one row per wallet (profiles.db). The old store rewrote the whole file per save, so two workers saving two
different wallets at once wiped one of them. Here 4 processes each save their own wallets 40 times while also touching one shared wallet."""
import json
import multiprocessing as mp
import sys
from pathlib import Path

import pytest

B = Path(__file__).resolve().parents[1]


def _worker(path, i, n):
    sys.path.insert(0, str(B))
    import sql_store
    d = sql_store.Docs(path, inner='profiles')
    for k in range(n):
        d.update(f'w{i}-{k}', lambda cur: {'displayName': f'p{i}', 'lastTs': k})
        d.update('shared', lambda cur: {**(cur or {}), 'saves': (cur or {}).get('saves', 0) + 1})


def test_old_profiles_file_moves_in_once_and_stays_read_only(tmp_path):
    sys.path.insert(0, str(B)); import sql_store
    f = tmp_path / 'profiles.json'; f.write_text(json.dumps({'profiles': {'A': {'displayName': 'degen'}, 'B': {'handle': 'bob'}}}))
    d = sql_store.Docs(f, inner='profiles')
    assert d.all() == {'A': {'displayName': 'degen'}, 'B': {'handle': 'bob'}} and (f.stat().st_mode & 0o777) == 0o400
    d.update('A', lambda cur: {**cur, 'bio': 'gm'})
    assert sql_store.Docs(f, inner='profiles').get('A') == {'displayName': 'degen', 'bio': 'gm'}   # a second worker sees it, no re-migration


@pytest.mark.skipif(sys.platform == 'win32', reason='fork')
def test_four_workers_saving_profiles_at_once_lose_nothing(tmp_path):
    f = tmp_path / 'profiles.json'; f.write_text('{"profiles": {}}')
    ps = [mp.get_context('spawn').Process(target=_worker, args=(str(f), i, 40)) for i in range(4)]
    [p.start() for p in ps]; [p.join(60) for p in ps]
    assert all(p.exitcode == 0 for p in ps)
    sys.path.insert(0, str(B)); import sql_store
    got = sql_store.Docs(f, inner='profiles').all()
    assert len([k for k in got if k.startswith('w')]) == 160 and got['shared']['saves'] == 160


def test_the_profile_read_view_sees_a_write_at_once(monkeypatch, tmp_path):
    rs = pytest.importorskip('reputation_service')
    monkeypatch.setattr(rs, 'PROFILE_PATH', tmp_path / 'profiles.json')
    (tmp_path / 'profiles.json').write_text('{"profiles": {"Z": {"lastTs": 100}}}')
    assert rs._profiles_load()['profiles'] == {'Z': {'lastTs': 100}}
    rs._prof().update('Y', lambda cur: {'handle': 'yy'})
    assert set(rs._profiles_load()['profiles']) == {'Y', 'Z'}            # the read view sees a write at once (cache keyed on the db version)
