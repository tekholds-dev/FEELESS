import sys

import loop_lag


def test_culprit_names_project_frames_only():
    key = loop_lag.culprit(sys._getframe(), root=loop_lag.ROOT)
    assert 'test_culprit_names_project_frames_only' in key
    assert loop_lag.culprit(sys._getframe(), root='/nowhere') == ''


def test_watch_is_bounded_and_ranks_the_worst():
    w = loop_lag.Watch(keep=5, last=3)
    for i in range(40):
        w.charge(f'fn{i}', i * 0.1)
        w.stall(0.5, {f'fn{i}': 2}, now=1000 + i)
    assert len(w.where) <= 5 and len(w.recent) == 3
    v = w.view(now=w.since + 100)
    assert v['stalls'] == 40 and v['top'][0]['where'] == 'fn39' and v['recent'][-1]['where'] == 'fn39'
    assert v['blockedPct'] == 20.0
    w.reset()
    assert w.view()['stalls'] == 0


def test_blocklist_view_is_built_once_per_file_version_and_pump_callers_stay_in_memory(monkeypatch):
    import json
    import reputation_service as rs
    rs.BLOCK_PATH.write_text(json.dumps({'wallets': {'A': {'mints': {'m': 'sniper'}}, 'SAFE': {'mints': {}}}}))
    monkeypatch.setattr(rs, '_protected_wallets', lambda: {'SAFE'})
    rs._block_view.update(key=None, d=None)
    a, b = rs._block_load(), rs._block_load()
    assert a is b and 'SAFE' not in a['wallets'] and 'A' in a['wallets']
    rs.BLOCK_PATH.write_text(json.dumps({'wallets': {'A': {'mints': {}}, 'B': {'mints': {}}, 'pad': {'mints': {'x': 'y'}}}}))
    assert 'B' in rs._block_load()['wallets']          # a new file version → a new view
    monkeypatch.setattr(rs, '_protected_wallets', lambda: {'B'})
    assert 'B' not in rs._block_load()['wallets']      # a new protected set → a new view

    rs._pump_callers.update(st=None, saved=0.0)
    calls = [{'user': 'u', 'id': 'c1', 'at': 1_000_000, 'mult': 2.0, 'mint': 'M'}]
    board = rs._pump_callers_pass(calls, 1_000_000 / 1000 + 2 * 3600)
    assert board['u']['n'] == 1 and not rs.PUMP_CALLERS_PATH.exists()   # judged in memory, not written every pass
    rs._pump_callers_pass(calls, 1_000_000 / 1000 + 2 * 3600 + rs.PUMP_CALLERS_SAVE_SEC + 1)
    assert json.loads(rs.PUMP_CALLERS_PATH.read_text())['u']['calls']['c1']['res'] == 2.0


def test_scanner_strikes_are_debounced_but_never_lost(monkeypatch):
    import asyncio
    import json
    import reputation_service as rs
    monkeypatch.setattr(rs, '_protected_wallets', lambda: set())
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    rs.BLOCK_PATH.write_text(json.dumps({'wallets': {'A': {'mints': {'m0': 'sniper'}}}}))
    rs._block_view.update(key=None, d=None); rs._block_dirty.update(on=False, at=rs.time.time())
    d = rs._block_load()
    d['wallets']['B'] = {'mints': {'m1': 'bundler'}}
    rs._block_save(d)                                   # inside the minute: memory only
    assert 'B' not in json.loads(rs.BLOCK_PATH.read_text())['wallets'] and 'B' in rs._block_load()['wallets']
    monkeypatch.setattr(rs, '_protected_wallets', lambda: {'ZZ'})   # the view is replaced → what it learned is written first
    assert 'B' in rs._block_load()['wallets'] and 'B' in json.loads(rs.BLOCK_PATH.read_text())['wallets']
    d = rs._block_load(); d['wallets']['C'] = {'mints': {}}
    rs._block_save(d, now=True)                         # a person's report is written at once, and the view survives the write
    assert 'C' in json.loads(rs.BLOCK_PATH.read_text())['wallets'] and rs._block_load() is d

    rs._hygiene_mem.update(d=None, dirty=False, at=0.0)
    rs._absorb_intel('M1', {'creator': 'CR', 'sniperWallets': ['x'], 'bundledWallets': []})
    hp = rs.DATA_DIR / 'hygiene.json'
    first = hp.stat().st_mtime_ns
    rs._absorb_intel('M1', {'creator': 'CR', 'sniperWallets': ['x'], 'bundledWallets': []})   # same counts: nothing written
    rs._absorb_intel('M2', {'creator': 'CR', 'sniperWallets': [], 'bundledWallets': ['y', 'z']})   # new, inside the minute: memory
    assert hp.stat().st_mtime_ns == first and rs._hygiene('CR', {'score': 50})['hygiene']['launches'] == 2
    rs._hygiene_flush()
    assert json.loads(hp.read_text())['CR']['launches']['M2'] == {'snipers': 0, 'bundled': 2}
    rs._hygiene_mem.update(d=None, dirty=False, at=0.0)
    assert asyncio.run(rs._desk_get())['snap'] is not None   # the intel desk is built once, in a worker thread


def test_candle_store_is_streamed_to_disk_as_valid_json():
    import json
    import candles_service as cs
    store = {'solana:A': [{'t': 1.5, 'p': 3.4e-06, 'v': None}], 'b': [], 'c': [{'t': 2, 'p': 1.0, 'v': 12.5}]}
    cs._stream_store(store)
    assert json.loads(cs.STORE_PATH.read_text()) == store
    cs._stream_store({})
    assert json.loads(cs.STORE_PATH.read_text()) == {}


def test_every_async_client_shares_one_tls_context_unless_it_brings_its_own():
    import httpx
    import http_ctx
    http_ctx.install(); http_ctx.install()
    a, b = httpx.AsyncClient(timeout=3), httpx.AsyncClient()
    ctx = http_ctx.context()
    pool = lambda c: c._transport._pool._ssl_context   # noqa: E731
    assert pool(a) is ctx and pool(b) is ctx
    assert pool(httpx.AsyncClient(verify=False)) is not ctx          # a caller's own choice is kept
    assert isinstance(httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200)))._transport, httpx.MockTransport)


def test_full_ledger_reads_only_new_rows_and_matches_a_full_read():
    import reputation_service as rs
    import store
    lg = store.Ledger(rs.FUSE_WALLET_PATH)
    rs._fw_full_cache.update(n=-1, rows=[], db=None, last=0)
    for i in range(3):
        lg.append({'at': 100 + i, 'card': 'degen', 'id': f'o{i}'})
    first = rs._fw_full_ledger()
    assert [r['id'] for r in first] == ['o0', 'o1', 'o2']
    calls = []
    real = store.Ledger.since
    store.Ledger.since = lambda self, after_id=0: (calls.append(after_id), real(self, after_id))[1]
    try:
        lg.append({'at': 200, 'card': 'degen', 'id': 'o3'})
        again = rs._fw_full_ledger()
        assert rs._fw_full_ledger() is again and len(calls) == 1 and calls[0] > 0     # one incremental read, then the cache
    finally:
        store.Ledger.since = real
    assert [r['id'] for r in again] == ['o0', 'o1', 'o2', 'o3'] == [r['id'] for r in lg.rows(limit=10)[::-1]]
    assert [r['id'] for r in first] == ['o0', 'o1', 'o2']                              # a list handed out earlier is never changed


def test_the_agents_page_gets_a_trimmed_snapshot_serialized_once(monkeypatch):
    import json
    import reputation_service as rs
    office = {'at': 5, 'mission': {'x': 1}, 'index': [1] * 50, 'social': {'big': 'x' * 500}, 'cycleLog': [1], 'kernel': {'candidates': []}}
    monkeypatch.setattr(rs, '_agents', {'view': {'agents': [{'key': 'tally'}], 'table': [{'mint': 'M', 'symbol': 'S', 'social': {'packet': 'y' * 900}, 'k': {'rank': 1}}]}, 'card': None})
    monkeypatch.setattr(rs, '_office', {'payload': office})
    rs._agents_page.update(key=None, body=b'{}')
    body = rs._agents_page_body(now=100.0)
    page = json.loads(body)
    assert page['office'] == {'at': 5, 'mission': {'x': 1}, 'kernel': {'candidates': []}} and page['table'] == [{'mint': 'M', 'symbol': 'S', 'k': {'rank': 1}}]
    assert rs._agents_page_body(now=100.5) is body                      # every reader inside the window shares the same bytes
    assert rs._agents_snapshot()['office'] is office and 'social' in office and 'social' in rs._agents['view']['table'][0]   # memory is untouched


def test_a_built_chart_answers_at_once_and_refreshes_behind(monkeypatch):
    import asyncio
    import time
    import candles_service as cs
    built = []

    async def build(chain, pair, interval):
        built.append(pair); await asyncio.sleep(0.3)
        out = {'candles': [[1, 1, 1, 1, 1]], 'provider': 'new'}
        cs._resp_cache[(chain, pair, interval)] = (time.time(), out)
        return out

    async def hint(*a, **k):
        raise AssertionError('a chart that is already built never waits on a pool lookup')
    monkeypatch.setattr(cs, '_build_candles', build); monkeypatch.setattr(cs, '_accept_mint_hint', hint)
    cs._history_tasks.clear()
    old = {'candles': [[0, 1, 1, 1, 1]], 'provider': 'old'}

    async def go():
        cs._resp_cache[('solana', 'P', '1m')] = (time.time() - 5, old)            # fresh: the answer, nothing started
        assert await cs.get_candles('solana', 'P', '1m', None, 'MINT') is old and built == []
        cs._resp_cache[('solana', 'P', '1m')] = (time.time() - 40, old)           # 40s old: the same answer NOW, one rebuild behind it
        t0 = time.time()
        assert await cs.get_candles('solana', 'P', '1m', None, 'MINT') is old and time.time() - t0 < 0.1
        assert await cs.get_candles('solana', 'P', '1m', None, 'MINT') is old     # a second poll shares the rebuild in flight
        await asyncio.sleep(0.4)
        assert built == ['P'] and (await cs.get_candles('solana', 'P', '1m', None, 'MINT'))['provider'] == 'new'
    asyncio.run(go())


def test_a_stale_list_answers_at_once_while_one_rebuild_runs(monkeypatch):
    import asyncio
    import time
    import reputation_service as rs
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    rs._disc_cache.clear(); rs._list_flight.clear()
    n = {'b': 0}

    async def rebuild():
        n['b'] += 1
        assert rs._list_now(('k', ''), 10, rebuild) is None       # inside the rebuild the route really builds
        await asyncio.sleep(0.05)
        rs._disc_cache[('k', '')] = (time.time(), 'new')

    async def go():
        assert rs._list_now(('k', ''), 10, rebuild) is None       # nothing cached: the caller builds
        rs._disc_cache[('k', '')] = (time.time() - 2, 'old')
        assert rs._list_now(('k', ''), 10, rebuild) == 'old' and n['b'] == 0          # fresh
        rs._disc_cache[('k', '')] = (time.time() - 30, 'old')
        assert rs._list_now(('k', ''), 10, rebuild) == 'old' and rs._list_now(('k', ''), 10, rebuild) == 'old'   # stale: served, ONE rebuild
        await asyncio.sleep(0.15)
        assert n['b'] == 1 and rs._list_now(('k', ''), 10, rebuild) == 'new'
        rs._disc_cache[('k', '')] = (time.time() - rs.LIST_STALE_SEC - 1, 'ancient')
        assert rs._list_now(('k', ''), 10, rebuild) is None       # too old to show: built now
    asyncio.run(go())
