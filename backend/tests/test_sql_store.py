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


def _try_lead(path, q):
    q.put(ss.Leader(path).try_take())


def test_only_one_process_leads_the_loops_and_a_waiter_takes_over_when_it_dies(tmp_path):
    """👑 SITE-8 slice 8: one worker holds loops.leader for life; another process can't take it; once the leader lets go (dies / reloads),
    a waiting worker leads within `every` seconds and only THEN runs its loop."""
    import asyncio
    where = tmp_path / 'loops.leader'
    a = ss.Leader(where)
    assert a.try_take() and a.leading and a.try_take()          # taken, and asking again keeps it
    ctx = mp.get_context('spawn'); q = ctx.Queue()
    p = ctx.Process(target=_try_lead, args=(str(where), q)); p.start(); p.join(30)
    assert q.get(timeout=5) is False                             # another process can't lead while this one lives

    async def scenario():
        b = ss.Leader(where, every=0.05); ran = []

        async def loop():
            ran.append(1)
        t = b.start(loop)
        await asyncio.sleep(0.2)
        t2 = b.start(loop)
        await asyncio.sleep(0.2)
        assert ran == [] and b._poll is not None and len(b._tasks) == 2 and not b.leading                       # waits: a second worker never starts the loops
        a.release()                                              # the leader dies / reloads
        await asyncio.wait_for(asyncio.gather(t, t2), 2)
        assert ran == [1, 1] and b.leading and not b._tasks   # ONE shared poller woke both; done tasks drop their refs                          # the waiter took over and ran its loop
        b.release()
    asyncio.run(scenario())


def test_every_reputation_startup_loop_goes_through_the_leader():
    """👑 No startup handler in reputation_service starts a background loop on its own — only the per-process flushes of THIS worker's writes
    (store, traffic) and the lag catcher's own dump may; everything else waits for the leader."""
    import re
    src = (Path(__file__).resolve().parents[1] / 'reputation_service.py').read_text().split('\n')
    allowed = {'_store_flush_loop', '_flush_traffic', '_loop_lag_dump'}
    stray = []
    for s, line in enumerate(src):
        if line.strip() == "@app.on_event('startup')":
            i = s + 2
            while i < len(src) and (src[i] == '' or src[i].startswith((' ', '\t'))):
                for name in re.findall(r'(?:create_task|ensure_future)\(([\w.]+)\(', src[i]):
                    if name not in allowed:
                        stray.append((i + 1, name))
                i += 1
    assert stray == []
    assert sum(1 for x in src if '_LEAD.start(' in x) >= 25
