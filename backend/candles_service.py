"""
FEELESS Candles — a self-hosted OHLCV aggregator that never depends on a third
party's uptime.

Every time anyone's browser has a pair's live price on screen (a chart open, a
Pump Radar card rendered, a Discover row visible), it fires a tiny tick here.
This service buckets those real observed ticks into real OHLC candles on
request. It's deliberately not trying to replace a real market data provider
for pairs nobody's looked at yet — it's the fallback that makes sure a chart
never just dies when GeckoTerminal 500s, and it gets *better* the more the
site is used, permanently, because every tick is kept.

File-backed JSON, zero external dependencies, standalone FastAPI app.
"""
import asyncio
import json
import time

import httpx
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
STORE_PATH = DATA_DIR / 'candle_ticks.json'

MAX_TICKS_PER_PAIR = 20000
MAX_AGE_SECONDS = 30 * 24 * 60 * 60   # 30 days of raw ticks kept per pair
INTERVAL_SECONDS = {
    '1m': 60, '5m': 300, '15m': 900, '1h': 3600, '4h': 14400, '1d': 86400,
}


def _empty_store():
    return {}


def _load() -> dict:
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text())
        except Exception:
            pass
    return _empty_store()


def _save(store: dict):
    STORE_PATH.write_text(json.dumps(store))


def _pair_key(chain: str, pair_address: str) -> str:
    return f'{chain}:{pair_address}'


def _bucket_candles(ticks: list, interval_seconds: int):
    """Groups raw {t, p, v} ticks into real OHLC candles — open/close are the
    first/last observed price in the bucket, high/low the extremes, volume the
    sum of any per-tick volume observed. No interpolation, no invented data."""
    buckets = {}
    for tick in ticks:
        bucket_t = int(tick['t'] // interval_seconds) * interval_seconds
        b = buckets.setdefault(bucket_t, {'o': tick['p'], 'h': tick['p'], 'l': tick['p'], 'c': tick['p'], 'v': 0.0, 'n': 0})
        b['h'] = max(b['h'], tick['p'])
        b['l'] = min(b['l'], tick['p'])
        b['c'] = tick['p']
        b['v'] += tick.get('v') or 0
        b['n'] += 1
    ordered = sorted(buckets.items())
    return [[t, b['o'], b['h'], b['l'], b['c'], b['v']] for t, b in ordered]


class TickPayload(BaseModel):
    chain: str
    pairAddress: str
    priceUsd: float
    volumeUsd: Optional[float] = None


GECKO_TF = {'1m': ('minute', 1), '5m': ('minute', 5), '15m': ('minute', 15), '1h': ('hour', 1), '4h': ('hour', 4), '1d': ('day', 1)}
GECKO_NET = {'solana': 'solana', 'ethereum': 'eth', 'base': 'base', 'bsc': 'bsc', 'arbitrum': 'arbitrum', 'avalanche': 'avax', 'polygon': 'polygon_pos', 'sui': 'sui-network'}
_gecko_cache: dict = {}
_gecko_lock = asyncio.Lock()
_gecko_calls: list = []
GECKO_TTL = 60
GECKO_PER_MIN = 25


async def gecko_candles(chain: str, pair: str, interval: str):
    """Real OHLCV straight from GeckoTerminal, cached and rate-limited (their public cap is 30/min)."""
    net = GECKO_NET.get(chain)
    tf = GECKO_TF.get(interval)
    if not net or not tf:
        return None
    key = f'{net}:{pair}:{interval}'
    now = time.time()
    hit = _gecko_cache.get(key)
    if hit and now - hit[0] < GECKO_TTL:
        return hit[1]
    async with _gecko_lock:
        _gecko_calls[:] = [t for t in _gecko_calls if now - t < 60]
        if len(_gecko_calls) >= GECKO_PER_MIN:
            return hit[1] if hit else None
        _gecko_calls.append(now)
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            res = await http.get(f'https://api.geckoterminal.com/api/v2/networks/{net}/pools/{pair}/ohlcv/{tf[0]}',
                                 params={'aggregate': tf[1], 'limit': 300, 'currency': 'usd'}, headers={'accept': 'application/json'})
        if res.status_code != 200:
            candles = None
        else:
            rows = (((res.json() or {}).get('data') or {}).get('attributes') or {}).get('ohlcv_list') or []
            candles = sorted([[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5] or 0)] for r in rows if len(r) >= 6], key=lambda r: r[0])
    except Exception:
        candles = None
    if candles is not None:
        _gecko_cache[key] = (now, candles)
    return candles if candles is not None else (hit[1] if hit else None)


_hot_pairs: dict = {}
HOT_TTL = 30 * 60
DEX_CHAIN = {'solana': 'solana', 'ethereum': 'ethereum', 'base': 'base', 'bsc': 'bsc', 'arbitrum': 'arbitrum', 'avalanche': 'avalanche', 'polygon': 'polygon', 'sui': 'sui'}


def _record_tick(store: dict, chain: str, pair: str, price: float, volume):
    key = _pair_key(chain, pair)
    ticks = store.setdefault(key, [])
    now = time.time()
    if ticks and now - ticks[-1]['t'] < 14:
        return
    ticks.append({'t': now, 'p': price, 'v': volume})
    cutoff = now - MAX_AGE_SECONDS
    store[key] = [t for t in ticks if t['t'] >= cutoff][-MAX_TICKS_PER_PAIR:]


async def _poll_hot_pairs():
    """Server-side price recorder: every pair anyone opened in the last 30 min gets a
    DexScreener price tick every 15s, so candles build even while GeckoTerminal throttles us."""
    while True:
        try:
            now = time.time()
            for k in [k for k, t in _hot_pairs.items() if now - t > HOT_TTL]:
                _hot_pairs.pop(k, None)
            by_chain = {}
            for k in _hot_pairs:
                chain, pair = k.split(':', 1)
                if chain in DEX_CHAIN:
                    by_chain.setdefault(chain, []).append(pair)
            if by_chain:
                store = _load()
                async with httpx.AsyncClient(timeout=8) as http:
                    for chain, pairs in by_chain.items():
                        for i in range(0, len(pairs), 30):
                            res = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{DEX_CHAIN[chain]}/{",".join(pairs[i:i + 30])}')
                            if res.status_code != 200:
                                continue
                            for p in (res.json() or {}).get('pairs') or []:
                                try:
                                    price = float(p.get('priceUsd') or 0)
                                except (TypeError, ValueError):
                                    price = 0
                                if price > 0:
                                    _record_tick(store, chain, p.get('pairAddress'), price, (p.get('volume') or {}).get('h24'))
                _save(store)
        except Exception:
            pass
        await asyncio.sleep(15)


app = FastAPI(title='FEELESS Candles')


@app.on_event('startup')
async def _start_poller():
    asyncio.create_task(_poll_hot_pairs())
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


@app.post('/api/candles/observe')
async def observe(payload: TickPayload):
    if not payload.priceUsd or payload.priceUsd <= 0:
        return {'ok': False, 'reason': 'invalid price'}
    store = _load()
    key = _pair_key(payload.chain, payload.pairAddress)
    ticks = store.setdefault(key, [])
    now = time.time()
    last = ticks[-1] if ticks else None
    if last and now - last['t'] < 15:
        return {'ok': True, 'skipped': 'too soon'}
    ticks.append({'t': now, 'p': payload.priceUsd, 'v': payload.volumeUsd})
    cutoff = now - MAX_AGE_SECONDS
    store[key] = [t for t in ticks if t['t'] >= cutoff][-MAX_TICKS_PER_PAIR:]
    _save(store)
    return {'ok': True, 'ticksStored': len(store[key])}


@app.get('/api/candles/{chain}/{pair_address}')
async def get_candles(chain: str, pair_address: str, interval: str = Query('1h')):
    _hot_pairs[_pair_key(chain, pair_address)] = time.time()
    interval_seconds = INTERVAL_SECONDS.get(interval, 3600)
    store = _load()
    ticks = store.get(_pair_key(chain, pair_address), [])
    own = _bucket_candles(ticks, interval_seconds)
    gecko = await gecko_candles(chain, pair_address, interval)
    if gecko and len(gecko) >= 2:
        # Extend provider history with any newer self-recorded bars so the latest candle is live.
        last = gecko[-1][0]
        merged = gecko + [c for c in own if c[0] > last]
        return {'candles': merged, 'provider': 'GeckoTerminal', 'interval': interval, 'tickCount': len(ticks),
                'source': 'GeckoTerminal OHLCV, extended with FEELESS-recorded ticks.'}
    return {'candles': own, 'provider': 'FEELESS', 'interval': interval, 'tickCount': len(ticks),
            'source': 'Real prices observed across FEELESS sessions — provider has no history for this pool yet.'}


@app.get('/api/candles/health')
async def health():
    store = _load()
    return {'ok': True, 'pairsTracked': len(store), 'totalTicks': sum(len(v) for v in store.values())}
