"""SITE-8: the shared doc store keeps every write when several worker PROCESSES hit the same key at once (the old whole-file JSON pattern
loses most of them), moves the old JSON in once and leaves it read-only, and its cached all() sees another process's write."""
import json
import multiprocessing as mp
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sql_store as ss   # noqa: E402

N_PROC, N_EACH = 4, 150


def _bump_sql(path, n):
    d = ss.Docs(path)
    for _ in range(n):
        d.update('w', lambda cur: {'n': (cur or {}).get('n', 0) + 1})


def _bump_json(path, n):
    p = Path(path)
    for _ in range(n):
        try:
            cur = json.loads(p.read_text() or '{}')
        except ValueError:
            cur = {}
        cur['n'] = cur.get('n', 0) + 1
        tmp = p.with_suffix(f'.{os.getpid()}.tmp'); tmp.write_text(json.dumps(cur)); tmp.replace(p)


def _run(target, path):
    ctx = mp.get_context('spawn')
    ps = [ctx.Process(target=target, args=(str(path), N_EACH)) for _ in range(N_PROC)]
    [p.start() for p in ps]; [p.join(60) for p in ps]
    assert all(p.exitcode == 0 for p in ps)


def test_four_processes_on_one_key_lose_nothing_where_the_json_file_loses_writes(tmp_path):
    _run(_bump_sql, tmp_path / 'store.json')
    assert ss.Docs(tmp_path / 'store.json').get('w') == {'n': N_PROC * N_EACH}
    j = tmp_path / 'old.json'; j.write_text('{}')
    _run(_bump_json, j)
    assert json.loads(j.read_text())['n'] < N_PROC * N_EACH   # the pattern being replaced: whole-file read → write races


def test_the_old_json_moves_in_once_and_stays_read_only(tmp_path):
    src = tmp_path / 'quest_state.json'; src.write_text(json.dumps({'A': {'days': ['2026-11-01']}, 'B': {'days': []}}))
    d = ss.Docs(src)
    assert d.all() == {'A': {'days': ['2026-11-01']}, 'B': {'days': []}} and oct(src.stat().st_mode & 0o777) == '0o400'
    d.put('A', {'days': []})
    assert ss.Docs(src).get('A') == {'days': []}   # a second opener never re-imports the old file over newer rows


def test_update_returns_an_answer_and_all_sees_another_writer(tmp_path):
    a, b = ss.Docs(tmp_path / 's.json'), ss.Docs(tmp_path / 's.json')
    got = a.update('k', lambda cur: ss.Result({'v': 1}, 'counted'), default={})
    assert got == 'counted' and b.all() == {'k': {'v': 1}}
    a.put('k2', [1]); assert b.all() == {'k': {'v': 1}, 'k2': [1]}   # cached per data_version: the other connection's write is seen
    a.update('k', lambda cur: None); assert b.get('k') is None
    a.replace_all({'z': 1}); assert b.all() == {'z': 1}
