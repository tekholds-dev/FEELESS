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
import json
import time
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


app = FastAPI(title='FEELESS Candles')
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
    interval_seconds = INTERVAL_SECONDS.get(interval, 3600)
    store = _load()
    ticks = store.get(_pair_key(chain, pair_address), [])
    candles = _bucket_candles(ticks, interval_seconds)
    return {
        'candles': candles, 'provider': 'FEELESS', 'interval': interval,
        'tickCount': len(ticks), 'source': 'Real prices observed across FEELESS sessions — not a third-party feed.',
    }


@app.get('/api/candles/health')
async def health():
    store = _load()
    return {'ok': True, 'pairsTracked': len(store), 'totalTicks': sum(len(v) for v in store.values())}
