import asyncio
import time

import candles_service as cs


def test_providers_are_asked_at_once_and_a_slow_one_fills_in_later(monkeypatch):
    """A new coin: Jupiter answers fast with a short history, Alchemy is slow with a longer one. The chart gets Jupiter's bars inside the
    budget (it used to wait for Alchemy, then Helius, one after another), and Alchemy's longer history becomes the cached answer later."""
    bars = lambda n: [[1000 + i * 60, 1.0, 1.1, 0.9, 1.0, 5.0] for i in range(n)]
    async def jup(*a): await asyncio.sleep(0.05); return bars(10)
    async def alc(*a): await asyncio.sleep(0.6); return bars(80)
    async def hel(*a): await asyncio.sleep(5); return bars(3)
    async def none(*a, **k): return None
    monkeypatch.setattr(cs, 'jupiter_candles', jup); monkeypatch.setattr(cs, 'alchemy_candles', alc); monkeypatch.setattr(cs, 'helius_candles', hel)
    monkeypatch.setattr(cs, '_pair_base_token', none); monkeypatch.setattr(cs, '_stream_price', none)
    monkeypatch.setattr(cs, 'PROVIDER_BUDGET', 0.3); monkeypatch.setattr(cs, '_load', lambda: {})
    cs._resp_cache.clear()

    async def run():
        t0 = time.time()
        out = await cs._build_candles('solana', 'PAIRX', '1m')
        took = time.time() - t0
        await asyncio.sleep(0.8)   # Alchemy lands in the background
        return out, took
    out, took = asyncio.run(run())
    assert out['provider'] == 'Jupiter' and took < 0.5
    assert cs._resp_cache[('solana', 'PAIRX', '1m')][1]['provider'] == 'Alchemy'


def test_a_new_pools_coin_is_looked_up_once_and_a_miss_is_remembered(monkeypatch):
    """Four callers (the build + three providers) each waited 8s on a pool DexScreener had not indexed: one shared lookup, miss kept 45s."""
    calls = []
    async def look(chain, pair, key):
        calls.append(pair); await asyncio.sleep(0.05)
        cs._base_miss[key] = time.time(); cs._base_flight.pop(key, None)
        return None
    monkeypatch.setattr(cs, '_base_lookup', look)
    cs._base_token.pop('solana:NEWPOOL', None); cs._base_miss.pop('solana:NEWPOOL', None); cs._base_flight.clear()

    async def run():
        a = await asyncio.gather(*[cs._pair_base_token('solana', 'NEWPOOL') for _ in range(4)])
        b = await cs._pair_base_token('solana', 'NEWPOOL')   # inside the 45s: not asked again
        return a, b
    a, b = asyncio.run(run())
    assert a == [None] * 4 and b is None and calls == ['NEWPOOL']


def test_the_price_store_is_parsed_once_and_re_read_only_when_the_file_changes(monkeypatch, tmp_path):
    """33 MB of ticks were parsed on every chart request and re-written on every tick: the service froze and keep-alive killed it."""
    import json
    p = tmp_path / 'ticks.json'; p.write_text(json.dumps({'solana:A': [{'t': 1, 'p': 1.0}]}))
    monkeypatch.setattr(cs, 'STORE_PATH', p); monkeypatch.setattr(cs, '_LAZY_SAVE', False)
    reads = []
    real = json.loads
    monkeypatch.setattr(cs.json, 'loads', lambda s, *a, **k: (reads.append(1), real(s, *a, **k))[1])
    a = cs._load(); b = cs._load()
    assert a is b and len(reads) == 1                                  # one parse, the same object
    a['solana:B'] = [{'t': 2, 'p': 2.0}]; cs._save(a)
    assert cs._load() is a and len(reads) == 1 and 'solana:B' in real(p.read_text())   # our own save is not a reason to re-read
    monkeypatch.setattr(cs, '_LAZY_SAVE', True)
    a['solana:C'] = []; cs._save(a)
    assert 'solana:C' not in real(p.read_text()) and cs._mem['dirty']   # the running service: kept in memory, written by the flush
    assert asyncio.run(cs._flush_store()) is True and 'solana:C' in real(p.read_text()) and cs._load() is a
