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


def test_candle_store_dump_is_the_same_json_written_pair_by_pair():
    import json
    import candles_service as cs
    store = {'solana:A': [{'t': 1.5, 'p': 3.4e-06, 'v': None}], 'solana:B "q"': [], 'c': [{'t': 2, 'p': 1.0, 'v': 12.5}]}
    assert cs._dump_store(store) == json.dumps(store) and cs._dump_store({}) == '{}'


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
