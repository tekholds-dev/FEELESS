"""⏱ Execution reliability (2026-10-12 audit): ONE lifecycle word per order, a quote is never built into a transaction past its TTL
(an urgent exit's TTL is half), duplicate requests on an in-flight card are dropped and counted, the Courier's metrics come from the
ledger only. 🧹 Storage trim: only re-fetchable caches and logs, never a ledger. Fakes only — nothing reaches the chain."""
import asyncio
import os
import time

import fuse_wallet as fw
import storage_trim as stt


def test_one_lifecycle_word_per_order():
    assert fw.exec_state({'status': 'filled'}) == 'FILLED'
    assert fw.exec_state({'status': 'sent', 'sentAt': 100}, now=101) == 'SUBMITTED' and fw.exec_state({'status': 'sent', 'sentAt': 100}, now=130) == 'CONFIRMING'
    assert fw.exec_state({'status': 'failed', 'err': 'transaction expired — never landed'}) == 'EXPIRED'
    assert fw.exec_state({'status': 'failed', 'err': 'slippage exceeded on-chain'}) == 'FAILED'
    assert fw.exec_state({'status': 'skipped', 'err': 'no route'}) == 'FAILED' and fw.exec_state({'status': 'quoted'}) == 'QUOTE_READY'
    assert fw.exec_state({'status': 'fix'}) == 'RECONCILING' and fw.exec_state({}) == 'INTENT'
    assert all(fw.exec_state({'status': s}) in fw.EXEC_STATES for s in ('filled', 'sent', 'failed', 'skipped', 'dry', 'quoted', 'fix', 'x'))


def test_quote_ttl_is_shorter_for_urgent_exits_and_an_unknown_quote_time_is_stale():
    buy, sell, stop = {'side': 'buy'}, {'side': 'sell', 'why': 'take profit'}, {'side': 'sell', 'why': 'R5 stop −30%'}
    assert fw.quote_ttl(buy) == 8.0 and fw.quote_ttl(sell) == 5.0 and fw.quote_ttl(stop) == 2.5
    assert fw.urgent_order(stop) and fw.urgent_order({'side': 'sell', 'why': '🚨 rug shield: pool drained'}) and not fw.urgent_order({'side': 'buy', 'why': 'stop'})
    assert not fw.quote_stale(100, 104, sell) and fw.quote_stale(100, 106, sell) and fw.quote_stale(100, 103, stop) and fw.quote_stale(None, 1, buy)


def test_metrics_come_from_the_ledger_only():
    now = 10_000.0
    led = [{'at': now - 10, 'side': 'buy', 'status': 'filled', 'quoteAgeSec': 1.2, 'landSec': 8, 'delta': 0.9},
           {'at': now - 20, 'side': 'sell', 'status': 'filled', 'why': 'R5 stop', 'quoteAgeSec': 0.6, 'landSec': 4, 'delta': -0.4, 'quoteRefresh': 1},
           {'at': now - 30, 'side': 'sell', 'status': 'failed', 'err': 'transaction expired — never landed'},
           {'at': now - 40, 'side': 'buy', 'status': 'skipped', 'err': 'no route back'},
           {'at': now - 50, 'side': 'buy', 'status': 'failed', 'err': 'slippage exceeded on-chain', 'slipRetry': 1},
           {'at': now - 9999, 'side': 'buy', 'status': 'filled'}]
    m = fw.exec_metrics(led, now, dupes=3)
    assert (m['sends'], m['fills'], m['failed'], m['expired'], m['refused']) == (4, 2, 1, 1, 1)
    assert m['noRoute'] == 1 and m['retries'] == 1 and m['staleRefresh'] == 1 and m['urgentSells'] == 1 and m['dupesDropped'] == 3
    assert m['quoteAgeMed'] == 1.2 and m['landMed'] == 8 and m['sells'] == 2 and m['buys'] == 2


def test_a_quote_gone_stale_during_the_safety_checks_is_refreshed_before_the_build(monkeypatch):
    """An urgent exit: the quote ages past its 2.5s TTL before the build → a FRESH quote is built, its age is recorded, one send."""
    import reputation_service as rs
    clock = {'t': 1000.0, 'jump': 0.0, 'skip': 0}

    def tick():   # time barely moves, except once: after the FIRST quote is stamped, the safety work "took" 3s (> the 2.5s urgent TTL)
        if clock['skip']:
            clock['skip'] -= 1
        else:
            clock['t'] += clock['jump']; clock['jump'] = 0.0
        clock['t'] += 0.01
        return clock['t']
    monkeypatch.setattr(rs.time, 'time', tick)
    quotes, built, sent = [], [], []

    async def quote(order, cfg):
        quotes.append(clock['t'])
        if len(quotes) == 1:
            clock['jump'], clock['skip'] = 3.0, 1
        return {'outAmount': '1000', 'priceImpactPct': '0.001', 'n': len(quotes)}

    async def jup(method, path, json=None, **k):
        built.append(json['quoteResponse']['n'])
        return {'swapTransaction': 'tx', 'lastValidBlockHeight': 9}

    async def sign(cfg, raw, memo):
        return {'signature': 'SIG', 'signedTransaction': 'b64'}

    async def krpc(http, method, params):
        sent.append(method)

    async def resolve(tid, book, cfg, sol_px, wait=0):
        return {**book, 'pending': None}
    store = {'ledger': [], 'books': {}}
    monkeypatch.setattr(rs, '_fw_quote', quote); monkeypatch.setattr(rs, '_fw_jup', jup); monkeypatch.setattr(rs, '_fw_sign', sign)
    monkeypatch.setattr(rs, '_krpc', krpc); monkeypatch.setattr(rs, '_fw_resolve', resolve); monkeypatch.setattr(rs, '_fw_signer_ready', lambda: True)
    monkeypatch.setattr(rs, '_fw_load', lambda: store); monkeypatch.setattr(rs, '_fw_save', lambda d: None); monkeypatch.setattr(rs, '_fw_raw_keep', lambda *a: None)
    monkeypatch.setattr(rs, '_fw_record', lambda d, r: d['ledger'].append(r))
    monkeypatch.setattr(rs, '_fw_keep', lambda d, tid, b: b)
    monkeypatch.setattr(rs._fw, 'check', lambda *a, **k: (True, None)); monkeypatch.setattr(rs._fw, 'landing_boost', lambda *a, **k: 0)
    monkeypatch.setattr(rs._fw, 'note_sell_quote', lambda *a, **k: None)

    class Http:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
    monkeypatch.setattr(rs.httpx, 'AsyncClient', Http)
    order = {'side': 'sell', 'mint': 'M', 'id': 'o1', 'why': '🚨 rug shield: pool drained', 'symbol': 'M'}
    asyncio.run(rs._fw_execute('degen', order, {'legs': {}}, {'slippageBps': 300, 'address': 'W'}, 150.0, 1e5))
    assert len(quotes) == 2 and built == [2] and sent == ['sendTransaction']                                   # the stale quote was never built
    assert store['books']['degen']['pending']['quoteRefresh'] == 1 and store['books']['degen']['pending']['quoteAgeSec'] <= fw.quote_ttl(order)


def test_a_duplicate_request_on_an_in_flight_card_is_dropped_and_counted(monkeypatch):
    import reputation_service as rs

    async def forbidden(*a, **k):
        raise AssertionError('no second order while one is in flight')
    monkeypatch.setattr(rs, '_fw_quote', forbidden)
    n0 = rs._FW_DUPES['n']
    book = {'pending': {'sig': 'first', 'side': 'sell'}}
    for o in ({'side': 'sell', 'mint': 'M', 'why': 'R5 stop'}, {'side': 'buy', 'mint': 'N'}, {'side': 'sell', 'mint': 'M', 'why': 'flow exit'}):
        assert asyncio.run(rs._fw_execute('degen', o, book, {}, 100, 1e6)) is book
    assert rs._FW_DUPES['n'] == n0 + 3


def test_logo_cache_is_capped_oldest_first_and_never_trims_a_fresh_logo(tmp_path):
    now = 1_000_000.0
    files = [('old.png', 400, now - 9 * 86400), ('mid.png', 400, now - 3 * 86400), ('new.png', 400, now - 60)]
    assert stt.plan_logos(files, now, max_bytes=500) == ['old.png', 'mid.png']
    assert stt.plan_logos(files, now, max_bytes=5000) == []
    assert stt.plan_logos([('new.png', 10_000, now - 60)], now, max_bytes=1) == []                             # nothing under a day old
    assert stt.cache_logo_ok(b'x' * 1000) and not stt.cache_logo_ok(b'x' * (stt.LOGO_FILE_MAX + 1)) and not stt.cache_logo_ok(b'')
    d = tmp_path / 'logos'; d.mkdir()
    for n, sz, mt in files:
        p = d / n; p.write_bytes(b'x' * sz); os.utime(p, (mt, mt))
    assert stt.trim_logos(d, now, max_bytes=500) == {'files': 2, 'freed': 800, 'kept': 1}
    assert [f.name for f in d.iterdir()] == ['new.png']

def test_logs_keep_their_newest_tail_and_ledgers_are_never_in_scope(tmp_path):
    assert stt.plan_log(10) is None and stt.plan_log(stt.LOG_MAX_BYTES + 1) == stt.LOG_KEEP_BYTES
    f = tmp_path / 'feeless-api.log'
    f.write_bytes(b'a' * (stt.LOG_MAX_BYTES + 10) + b'\nNEWEST LINE\n')
    (tmp_path / 'fuse_wallet.db').write_bytes(b'L' * (stt.LOG_MAX_BYTES + 10))
    assert stt.trim_logs(tmp_path) == ['feeless-api.log']
    assert f.stat().st_size < stt.LOG_KEEP_BYTES + 100 and f.read_bytes().endswith(b'NEWEST LINE\n')
    assert (tmp_path / 'fuse_wallet.db').stat().st_size == stt.LOG_MAX_BYTES + 10                              # a ledger is never a log
    assert stt.LOG_GLOB == 'feeless-*.log'


def test_prime_view_is_single_flight_and_an_owner_write_clears_it(monkeypatch):
    """⚡ /fuses/prime: concurrent viewers share ONE build; a young answer is served at once; an owner write empties the cache and a
    build that started before the write cannot refill it."""
    import reputation_service as rs
    monkeypatch.delenv('PYTEST_CURRENT_TEST', raising=False)
    calls = {'n': 0}

    async def build():
        calls['n'] += 1
        await asyncio.sleep(0.05)
        return {'n': calls['n']}
    monkeypatch.setattr(rs, '_fuse_prime_build', build)
    rs._prime_resp.update(at=0.0, data=None, task=None, cleared=0.0)

    async def go():
        a = await asyncio.gather(*[rs.fuse_prime() for _ in range(5)])
        b = await rs.fuse_prime()
        t = asyncio.create_task(rs._prime_resp_build()); await asyncio.sleep(0.01)
        rs._prime_resp_clear(); await t
        return a, b
    a, b = asyncio.run(go())
    assert calls['n'] == 2 and all(x == {'n': 1} for x in a) and b == {'n': 1}                                  # 5 viewers → 1 build; young → served
    assert rs._prime_resp['data'] is None                                                                      # the pre-write build did not refill it
