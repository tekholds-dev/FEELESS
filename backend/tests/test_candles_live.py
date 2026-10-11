"""👁 The agents watch the LIVE chart (2026-10-11): one batched call returns the war room's chart for every desk coin — provider history
kept from the last build + FEELESS's live 15s ticks — and marks each pool watched. Mint hints only from this machine."""
import asyncio
import time
from types import SimpleNamespace

import candles_service as cs

P1 = 'A' * 43
P2 = 'B' * 43
M1 = 'C' * 43


def _req(host):
    return SimpleNamespace(client=SimpleNamespace(host=host))


def _setup(monkeypatch, ticks):
    built = []
    async def build(chain, pair, interval):
        built.append(pair)
    monkeypatch.setattr(cs, '_build_candles', build)
    monkeypatch.setattr(cs, '_load', lambda: ticks)
    cs._live_hist.clear(); cs._live_builds.clear(); cs._hot_pairs.clear(); cs._base_token.pop(f'solana:{P1}', None); cs._base_token.pop(f'solana:{P2}', None)
    return built


def test_live_chart_is_history_plus_newest_live_ticks(monkeypatch):
    now = time.time()
    t0 = int(now // 60) * 60 - 600
    hist = [[t0 + i * 60, 1.0, 1.1, 0.9, 1.0, 50.0] for i in range(8)]
    ticks = {cs._pair_key('solana', P1): [{'t': now - 30, 'p': 1.5, 'v': None}, {'t': now - 5, 'p': 1.6, 'v': None}]}
    built = _setup(monkeypatch, ticks)
    cs._live_hist[('solana', P1, '1m')] = (now - 30, hist, 'Jupiter')

    async def run():
        out = await cs.live_charts(cs.LivePayload(pairs={P1: M1}), _req('127.0.0.1'))
        await asyncio.sleep(0)
        return out
    out = asyncio.run(run())
    ch = out['charts'][P1]
    assert ch['provider'] == 'Jupiter' and ch['candles'][0][0] == t0
    assert ch['candles'][-1][4] == 1.6                  # the newest candle is the live tick, not the old snapshot
    assert ch['liveAt'] == ticks[cs._pair_key('solana', P1)][-1]['t']
    assert cs._pair_key('solana', P1) in cs._hot_pairs  # watched: the recorder ticks it every 15s
    assert built == []                                   # fresh history: no provider call
    assert cs._base_token[f'solana:{P1}'] == M1          # mint hint taken from this machine


def test_no_history_starts_a_background_build_and_answers_with_live_ticks(monkeypatch):
    now = time.time()
    ticks = {cs._pair_key('solana', P2): [{'t': now - 200, 'p': 2.0, 'v': None}, {'t': now - 100, 'p': 2.2, 'v': None}, {'t': now - 5, 'p': 2.4, 'v': None}]}
    built = _setup(monkeypatch, ticks)

    async def run():
        out = await cs.live_charts(cs.LivePayload(pairs={P2: M1}), _req('203.0.113.9'))
        await asyncio.sleep(0.01)
        return out
    out = asyncio.run(run())
    assert out['started'] == 1 and built == [P2]
    assert out['charts'][P2]['provider'] == 'FEELESS' and out['charts'][P2]['partial'] is True
    assert f'solana:{P2}' not in cs._base_token          # a remote caller can never point a pool at another coin


def test_history_builds_are_capped_per_call(monkeypatch):
    built = _setup(monkeypatch, {})
    pairs = {'EFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'[i] + 'D' * 42: None for i in range(cs.LIVE_NEW_BUILDS + 10)}

    async def run():
        out = await cs.live_charts(cs.LivePayload(pairs=pairs), _req('127.0.0.1'))
        await asyncio.sleep(0.01)
        return out
    assert asyncio.run(run())['started'] == cs.LIVE_NEW_BUILDS
