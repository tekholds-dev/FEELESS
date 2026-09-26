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
import env_loader  # noqa: F401  (must run before reading os.environ)
import asyncio
import json
import time

import httpx
import gecko_budget
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


GECKO_DISK = Path(__file__).parent / 'data' / 'gecko_candles'


def _disk_get(key):
    try:
        return json.loads((GECKO_DISK / f"{key.replace(':', '_')}.json").read_text())
    except Exception:
        return None


def _disk_put(key, candles):
    GECKO_DISK.mkdir(parents=True, exist_ok=True)
    (GECKO_DISK / f"{key.replace(':', '_')}.json").write_text(json.dumps(candles[-3000:]))


def _merge(a, b):
    by = {int(c[0]): c for c in (a or [])}
    for c in b or []:
        by[int(c[0])] = c
    return [by[t] for t in sorted(by)]


async def _gecko_fetch(net, pair, tf, before=None):
    if not gecko_budget.take('chart'):
        return None
    params = {'aggregate': tf[1], 'limit': 1000, 'currency': 'usd'}
    if before:
        params['before_timestamp'] = int(before)
    try:
        async with httpx.AsyncClient(timeout=12) as http:
            res = await http.get(f'https://api.geckoterminal.com/api/v2/networks/{net}/pools/{pair}/ohlcv/{tf[0]}', params=params, headers={'accept': 'application/json'})
    except Exception:
        return None
    if res.status_code == 429:
        gecko_budget.throttled()
        return None
    if res.status_code != 200:
        return None
    rows = (((res.json() or {}).get('data') or {}).get('attributes') or {}).get('ohlcv_list') or []
    return sorted([[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5] or 0)] for r in rows if len(r) >= 6], key=lambda r: r[0])


async def gecko_candles(chain: str, pair: str, interval: str, before=None):
    """Real OHLCV from GeckoTerminal. Every bar ever fetched is kept on disk, so a rate limit
    never wipes history; `before` pages further back for zoom-out."""
    net = GECKO_NET.get(chain)
    tf = GECKO_TF.get(interval)
    if not net or not tf:
        return None
    key = f'{net}:{pair}:{interval}'
    now = time.time()
    stored = _disk_get(key) or []
    if before:
        older = [c for c in stored if c[0] < before]
        if len(older) >= 200:
            return older
        fresh = await _gecko_fetch(net, pair, tf, before)
        if fresh:
            stored = _merge(stored, fresh)
            _disk_put(key, stored)
        return [c for c in stored if c[0] < before]
    hit = _gecko_cache.get(key)
    if hit and now - hit[0] < GECKO_TTL:
        return hit[1]
    fresh = await _gecko_fetch(net, pair, tf)
    if fresh:
        stored = _merge(stored, fresh)
        _disk_put(key, stored)
        _gecko_cache[key] = (now, stored)
    return stored or None


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


def _fill_gaps(candles, step, own=None, limit=5000):
    """No skipped candles: quiet intervals become flat bars at the last close (zero volume);
    if FEELESS recorded its own tick in that gap, the real observed price is used instead."""
    if not candles:
        return candles
    by_own = {int(c[0]): c for c in (own or [])}
    out = [candles[0]]
    for c in candles[1:]:
        t = out[-1][0] + step
        while t < c[0] and len(out) < limit:
            o = by_own.get(int(t))
            prev = out[-1][4]
            out.append(o if o else [t, prev, prev, prev, prev, 0.0])
            t += step
        out.append(c)
    now_bucket = int(time.time() // step * step)
    while out[-1][0] + step <= now_bucket and len(out) < limit:
        t = out[-1][0] + step
        o = by_own.get(int(t)); prev = out[-1][4]
        out.append(o if o else [t, prev, prev, prev, prev, 0.0])
    return out[-limit:]


@app.get('/api/candles/{chain}/{pair_address}')
async def get_candles(chain: str, pair_address: str, interval: str = Query('1h'), before: Optional[int] = None):
    if before:
        older = await gecko_candles(chain, pair_address, interval, before) or []
        older = _fill_gaps(older, INTERVAL_SECONDS.get(interval, 3600))
        return {'candles': older, 'provider': 'GeckoTerminal' if older else 'none', 'interval': interval, 'before': before}
    _hot_pairs[_pair_key(chain, pair_address)] = time.time()
    interval_seconds = INTERVAL_SECONDS.get(interval, 3600)
    store = _load()
    ticks = store.get(_pair_key(chain, pair_address), [])
    own = _bucket_candles(ticks, interval_seconds)
    gecko = await gecko_candles(chain, pair_address, interval)
    if gecko and len(gecko) >= 2:
        # Extend provider history with any newer self-recorded bars so the latest candle is live.
        last = gecko[-1][0]
        merged = _fill_gaps(gecko + [c for c in own if c[0] > last], interval_seconds, own)
        return {'candles': merged, 'provider': 'GeckoTerminal', 'interval': interval, 'tickCount': len(ticks),
                'source': 'GeckoTerminal OHLCV, extended with FEELESS-recorded ticks.'}
    return {'candles': _fill_gaps(own, interval_seconds), 'provider': 'FEELESS', 'interval': interval, 'tickCount': len(ticks),
            'source': 'Real prices observed across FEELESS sessions — provider has no history for this pool yet.'}


_trade_cache: dict = {}


@app.get('/api/candles/trades/{chain}/{pool}')
async def pool_trades(chain: str, pool: str):
    """Latest real swaps for a pool (GeckoTerminal), shared 5s cache so many viewers cost one call."""
    net = GECKO_NET.get(chain)
    if not net:
        return {'trades': [], 'error': 'unsupported chain'}
    key = f'{net}:{pool}'
    hit = _trade_cache.get(key)
    now = time.time()
    if hit and now - hit[0] < 15:
        return hit[1]
    throttled = not gecko_budget.take('trades')
    if throttled:
        return hit[1] if hit else {'trades': [], 'throttled': True}
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f'https://api.geckoterminal.com/api/v2/networks/{net}/pools/{pool}/trades', headers={'accept': 'application/json'})
        rows = (r.json() or {}).get('data') or [] if r.status_code == 200 else None
    except Exception:
        rows = None
    if rows is None:
        return hit[1] if hit else {'trades': [], 'error': 'provider unavailable'}
    trades = []
    for row in rows:
        a = row.get('attributes') or {}
        trades.append({'ts': a.get('block_timestamp'), 'kind': a.get('kind'), 'usd': float(a.get('volume_in_usd') or 0),
                       'price': float(a.get('price_to_in_usd') if a.get('kind') == 'buy' else a.get('price_from_in_usd') or 0),
                       'wallet': a.get('tx_from_address'), 'tx': a.get('tx_hash')})
    data = {'trades': trades, 'at': now, 'source': 'GeckoTerminal'}
    _trade_cache[key] = (now, data)
    return data


@app.get('/api/candles/health')
async def health():
    store = _load()
    return {'ok': True, 'pairsTracked': len(store), 'totalTicks': sum(len(v) for v in store.values())}
