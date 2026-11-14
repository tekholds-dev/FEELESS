"""🔒 SITE-8 slice 4: sql_store.ProcLock — a whole-document JSON store (crews.json) keeps every write when 4 worker processes change it at once."""
import asyncio
import json
import multiprocessing as mp
import sys
from pathlib import Path


def _bump(path, n, locked):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import sql_store

    async def run():
        lock = sql_store.ProcLock(path) if locked else asyncio.Lock()
        for _ in range(n):
            async with lock:
                d = json.loads(Path(path).read_text() or '{}')     # load → change → save, exactly like the crews routes
                await asyncio.sleep(0)                             # an await inside the section (the on-chain payment read)
                d['n'] = d.get('n', 0) + 1
                tmp = Path(path).with_suffix('.tmp'); tmp.write_text(json.dumps(d)); tmp.replace(path)
    asyncio.run(run())


def _race(tmp_path, locked):
    path = tmp_path / 'crews.json'; path.write_text('{}')
    ctx = mp.get_context('spawn')
    ps = [ctx.Process(target=_bump, args=(str(path), 60, locked)) for _ in range(4)]
    [p.start() for p in ps]; [p.join(120) for p in ps]
    assert all(p.exitcode == 0 for p in ps)
    return json.loads(path.read_text())['n']


def test_four_processes_lose_nothing_under_the_proc_lock(tmp_path):
    assert _race(tmp_path, True) == 240


def test_inside_one_process_it_is_still_a_plain_async_lock(tmp_path):
    import sql_store
    lock = sql_store.ProcLock(tmp_path / 'x.json'); order = []

    async def one(i):
        async with lock:
            order.append(('in', i)); await asyncio.sleep(0.01); order.append(('out', i))
    async def main():
        await asyncio.gather(*(one(i) for i in range(3)))
        return lock.locked()
    assert asyncio.run(main()) is False
    assert all(order[k][0] == 'in' and order[k + 1] == ('out', order[k][1]) for k in range(0, 6, 2))   # never two holders


def test_crews_routes_use_the_proc_lock():
    src = (Path(__file__).resolve().parents[1] / 'reputation_service.py').read_text()
    assert '_crews_lock = _sqls_proc.ProcLock(lambda: CREWS_PATH)' in src


def test_every_fuse_hq_and_runners_save_holds_the_cross_process_admin_lock():
    import ast
    src = (Path(__file__).resolve().parents[1] / 'reputation_service.py').read_text()
    assert '_admin_lock = _sqls_proc.ProcLock(lambda: FUSE_HQ_PATH)' in src
    t = ast.parse(src); par = {c: n for n in ast.walk(t) for c in ast.iter_child_nodes(n)}
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and getattr(n.func, 'id', None) in ('_json_save', '_json_save_soft') and n.args \
                and any(k in ast.unparse(n.args[0]) for k in ('FUSE_HQ_PATH', 'RUNNERS_PATH')):
            p, held = n, set()
            while p in par:
                p = par[p]
                if isinstance(p, ast.AsyncWith):
                    held |= {ast.unparse(i.context_expr) for i in p.items}
            assert '_admin_lock' in held, f'line {n.lineno} saves without the admin lock'


def test_tests_never_touch_the_real_lock_files_or_payment_holds():
    import reputation_service as rs
    real = (Path(__file__).resolve().parents[1] / 'data').resolve()
    for p in (rs._crews_lock.path, rs._admin_lock.path, Path(rs._PAY_HELD.docs.path)):
        assert real not in p.resolve().parents, p


def test_one_payment_is_claimed_once_across_processes(tmp_path):
    import sql_store
    s = sql_store.SharedSet(tmp_path / 'held.json')
    ctx = mp.get_context('spawn'); q = ctx.Queue()
    ps = [ctx.Process(target=_claim, args=(str(tmp_path / 'held.json'), q)) for _ in range(6)]
    [p.start() for p in ps]; [p.join(60) for p in ps]
    wins = [q.get(timeout=5) for _ in ps]
    assert sum(wins) == 1 and 'SIG' in s                                   # six workers, one payment: exactly one gets it
    s.discard('SIG'); assert 'SIG' not in s and s.claim('SIG') is True       # released (it failed) → spendable again
    old = sql_store.SharedSet(tmp_path / 'held.json', ttl=0); assert old.claim('SIG') is True   # a hold past its time never blocks forever


def _claim(path, q):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import sql_store
    q.put(sql_store.SharedSet(path).claim('SIG'))


def test_a_cancelled_wait_never_closes_a_descriptor_a_thread_still_uses(tmp_path):
    import sql_store
    lock = sql_store.ProcLock(tmp_path / 'c.json')

    async def main():
        holder = sql_store.ProcLock(tmp_path / 'c.json')   # a second holder in this process stands in for another worker
        await holder.__aenter__()
        t = asyncio.ensure_future(lock.__aenter__())
        await asyncio.sleep(0.1); t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
        await holder.__aexit__(None, None, None)
        await asyncio.sleep(0.2)                             # the late thread gets the lock, then lets it go
        async with lock:                                     # and the lock is still usable
            return True
    assert asyncio.run(main()) is True


def test_old_holds_are_pruned(tmp_path):
    import sql_store
    s = sql_store.SharedSet(tmp_path / 'h.json', ttl=0.01)
    s.add('A'); import time; time.sleep(0.02); s.prune()
    assert s.docs.all() == {}


def _hits(path, q):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import sql_store
    h = sql_store.SharedHits(path, 'rpc')
    q.put(sum(h.hit('9.9.9.9', 50, 3600) for _ in range(20)))


def test_a_device_limit_holds_across_worker_processes(tmp_path):
    """🚦 SITE-8: 6 workers × 20 calls from one device, limit 50 → exactly 50 pass (an in-memory dict would let 120 through)."""
    import sql_store
    ctx = mp.get_context('spawn'); q = ctx.Queue()
    ps = [ctx.Process(target=_hits, args=(str(tmp_path / 'hits.json'), q)) for _ in range(6)]
    [p.start() for p in ps]; [p.join(60) for p in ps]
    assert sum(q.get(timeout=5) for _ in ps) == 50
    h = sql_store.SharedHits(tmp_path / 'hits.json', 'rpc'); other = sql_store.SharedHits(tmp_path / 'hits.json', 'bug')
    assert not h.hit('9.9.9.9', 50, 3600) and h.hit('8.8.8.8', 50, 3600)   # another device is not locked out
    assert other.hit('9.9.9.9', 3, 60)                                       # limiters are separate namespaces
    h.clear(); assert h.hit('9.9.9.9', 50, 3600) and not other.docs.get('rpc:x')
    assert other.docs.get('bug:9.9.9.9')                                     # clear() empties only its own limiter
    assert h.hit('7.7.7.7', 1, 0.01) and not h.hit('7.7.7.7', 1, 0.01)
    import time
    time.sleep(0.02); h.prune(); assert h.docs.get('rpc:7.7.7.7') is None    # a passed window is pruned
    assert h.hit('7.7.7.7', 1, 0.01)


def test_every_per_device_limiter_is_shared_by_all_workers():
    """No per-IP limiter is a plain dict any more (each worker would hold its own count)."""
    import reputation_service as rs
    import sql_store
    names = ['_upload_ip', '_fle_hits', '_flv_hits', '_fjp_hits', '_fjx_hits', '_hqp_ip', '_bug_ip_hits', '_appr_hits', '_receipt_hits',
             '_click_ip', '_ad_ev_ip', '_edge_ip', '_tr_ip', '_rpc_hits']
    assert all(isinstance(getattr(rs, n), sql_store.SharedHits) for n in names)
    assert len({getattr(rs, n).ns for n in names}) == len(names)
    real = (Path(__file__).resolve().parents[1] / 'data').resolve()
    assert real not in Path(rs._rpc_hits.docs.path).resolve().parents
    src = ''.join(f.read_text() for f in [Path(rs.__file__), *sorted(Path(rs.__file__).parent.glob('rep_*.py'))])
    import re
    assert not re.search(r'for t_? in (?:rs\.)?_\w+\.get\(ip_?, \[\]\) if', src)   # no hand-rolled in-memory limiter left


def test_a_broken_shared_limiter_still_limits_in_process():
    import reputation_service as rs

    class Broken:
        ns = 'x'

        def hit(self, *a):
            raise OSError('locked')
    req = type('R', (), {'headers': {}, 'client': type('C', (), {'host': '5.5.5.5'})()})()
    assert all(asyncio.run(rs._ip_hit(Broken(), req, 2, 60)) for _ in range(2)) and not asyncio.run(rs._ip_hit(Broken(), req, 2, 60))
