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
import os
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
GECKO_NET = {'solana': 'solana', 'ethereum': 'eth', 'base': 'base', 'bsc': 'bsc', 'arbitrum': 'arbitrum', 'avalanche': 'avax', 'polygon': 'polygon_pos', 'sui': 'sui-network',
             'optimism': 'optimism', 'zksync': 'zksync', 'zora': 'zora-network', 'cronos': 'cro', 'unichain': 'unichain', 'worldchain': 'world-chain', 'tron': 'tron'}
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
    elif not stored and key not in _retry:
        _retry.add(key)
        asyncio.create_task(_retry_later(chain, pair, interval, key))
    return stored or None


_retry = set()


async def _retry_later(chain, pair, interval, key):
    """A chart that missed its first fetch (rate-limit pause) is fetched the moment the pause ends."""
    try:
        for _ in range(6):
            await asyncio.sleep(max(3.0, gecko_budget.blocked_for() + 1))
            _gecko_cache.pop(key, None)
            if await gecko_candles(chain, pair, interval):
                return
    finally:
        _retry.discard(key)


_hot_pairs: dict = {}
HOT_TTL = 30 * 60
DEX_CHAIN = {'solana': 'solana', 'ethereum': 'ethereum', 'base': 'base', 'bsc': 'bsc', 'arbitrum': 'arbitrum', 'avalanche': 'avalanche', 'polygon': 'polygon', 'sui': 'sui',
             'optimism': 'optimism', 'zksync': 'zksync', 'zora': 'zora', 'cronos': 'cronos', 'unichain': 'unichain', 'worldchain': 'worldchain', 'tron': 'tron'}


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
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in (os.environ.get('ALLOWED_ORIGINS') or '*').split(',') if o.strip()], allow_methods=['*'], allow_headers=['*'])


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


# ---- Alchemy Prices: the primary history source (one key, Solana + every EVM chain we run) ----
ALCHEMY_NET = {'solana': 'solana-mainnet', 'ethereum': 'eth-mainnet', 'base': 'base-mainnet', 'bsc': 'bnb-mainnet', 'arbitrum': 'arb-mainnet',
               'avalanche': 'avax-mainnet', 'polygon': 'polygon-mainnet', 'optimism': 'opt-mainnet', 'zksync': 'zksync-mainnet',
               'zora': 'zora-mainnet', 'unichain': 'unichain-mainnet', 'worldchain': 'worldchain-mainnet', 'cronos': 'cronos-mainnet'}
# interval -> (Alchemy point spacing, lookback seconds)
ALCHEMY_PLAN = {'1m': ('5m', 86400), '5m': ('5m', 2 * 86400), '15m': ('5m', 5 * 86400), '1h': ('1h', 21 * 86400),
                '4h': ('1h', 60 * 86400), '1d': ('1d', 365 * 86400)}
_base_token: dict = {}
_alchemy_cache: dict = {}


async def _pair_base_token(chain, pair):
    key = f'{chain}:{pair}'
    if key in _base_token:
        return _base_token[key]
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            p = ((await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{pair}')).json().get('pairs') or [None])[0]
        addr = (p or {}).get('baseToken', {}).get('address')
    except Exception:
        addr = None
    if addr:
        _base_token[key] = addr
    return addr


async def alchemy_candles(chain, pair, interval):
    """Real historical prices from Alchemy, bucketed into candles. Each bucket opens at the previous
    close so bars connect; high/low come from every price point inside the bucket."""
    net = ALCHEMY_NET.get(chain); key_ = os.environ.get('ALCHEMY_API_KEY')
    if not net or not key_:
        return []
    ck = f'{chain}:{pair}:{interval}'
    hit = _alchemy_cache.get(ck)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    token = await _pair_base_token(chain, pair)
    if not token:
        return []
    spacing, lookback = ALCHEMY_PLAN.get(interval, ('1h', 21 * 86400))
    end = time.time(); fmt = lambda t: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(t))
    try:
        async with httpx.AsyncClient(timeout=12) as http:
            r = await http.post(f'https://api.g.alchemy.com/prices/v1/{key_}/tokens/historical',
                                json={'network': net, 'address': token, 'startTime': fmt(end - lookback), 'endTime': fmt(end), 'interval': spacing})
        pts = [(time.mktime(time.strptime(x['timestamp'], '%Y-%m-%dT%H:%M:%SZ')) - time.timezone, float(x['value'])) for x in (r.json().get('data') or []) if x.get('value')]
    except Exception:
        pts = []
    step = INTERVAL_SECONDS.get(interval, 3600)
    buckets = {}
    for t, v in sorted(pts):
        b = int(t // step * step)
        c = buckets.get(b)
        if c:
            c[2] = max(c[2], v); c[3] = min(c[3], v); c[4] = v
        else:
            buckets[b] = [b, v, v, v, v, 0.0]
    out = [buckets[k] for k in sorted(buckets)]
    for i in range(1, len(out)):  # connect bars: open = previous close
        out[i][1] = out[i - 1][4]; out[i][2] = max(out[i][2], out[i][1]); out[i][3] = min(out[i][3], out[i][1])
    _alchemy_cache[ck] = (time.time(), out)
    return out


# ---- Codex (codex.io): primary OHLCV for every chain when CODEX_API_KEY is set ----------------
CODEX_NET = {'solana': 1399811149, 'ethereum': 1, 'base': 8453, 'bsc': 56, 'arbitrum': 42161, 'avalanche': 43114, 'polygon': 137,
             'optimism': 10, 'zksync': 324, 'zora': 7777777, 'cronos': 25, 'unichain': 130, 'worldchain': 480}
CODEX_RES = {'1m': ('1', 86400), '5m': ('5', 3 * 86400), '15m': ('15', 7 * 86400), '1h': ('60', 30 * 86400), '4h': ('240', 120 * 86400), '1d': ('1D', 730 * 86400)}
_codex_cache: dict = {}


async def codex_candles(chain, pair, interval):
    key_ = os.environ.get('CODEX_API_KEY', '').strip(); net = CODEX_NET.get(chain)
    if not key_ or not net:
        return []
    ck = f'{chain}:{pair}:{interval}'
    hit = _codex_cache.get(ck)
    if hit and time.time() - hit[0] < 10:
        return hit[1]
    res, back = CODEX_RES.get(interval, ('60', 30 * 86400))
    now = int(time.time())
    q = 'query($s:String!,$f:Int!,$t:Int!,$r:String!){getBars(symbol:$s,from:$f,to:$t,resolution:$r,removeLeadingNullValues:true){t o h l c volume}}'
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.post('https://graph.codex.io/graphql', headers={'Authorization': key_, 'Content-Type': 'application/json'},
                                json={'query': q, 'variables': {'s': f'{pair}:{net}', 'f': now - back, 't': now, 'r': res}})
        b = ((r.json() or {}).get('data') or {}).get('getBars') or {}
    except Exception:
        return hit[1] if hit else []
    out = []
    for i, t in enumerate(b.get('t') or []):
        o, h, l, c = b['o'][i], b['h'][i], b['l'][i], b['c'][i]
        if c is None:
            continue
        v = (b.get('volume') or [0] * (i + 1))[i]
        out.append([int(t), float(o if o is not None else c), float(h if h is not None else c), float(l if l is not None else c), float(c), float(v or 0)])
    _codex_cache[ck] = (time.time(), out)
    return out


async def codex_trades(chain, pool):
    """Latest swaps for a pool on any Codex-indexed chain. None = Codex unavailable (caller falls back)."""
    key_ = os.environ.get('CODEX_API_KEY', '').strip(); net = CODEX_NET.get(chain)
    if not key_ or not net:
        return None
    q = ('query($a:String!,$n:Int!){getTokenEvents(query:{address:$a,networkId:$n},limit:50){items{timestamp transactionHash maker '
         'eventDisplayType data{... on SwapEventData{priceUsd priceUsdTotal}}}}}')
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.post('https://graph.codex.io/graphql', headers={'Authorization': key_},
                                json={'query': q, 'variables': {'a': pool, 'n': net}})
        items = ((((r.json() or {}).get('data') or {}).get('getTokenEvents') or {}).get('items'))
    except Exception:
        return None
    if items is None:
        return None
    out = []
    for e in items:
        kind = (e.get('eventDisplayType') or '').lower()
        d = e.get('data') or {}
        if kind not in ('buy', 'sell') or not d.get('priceUsdTotal'):
            continue
        out.append({'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(e.get('timestamp') or 0)), 'kind': kind,
                    'usd': round(float(d['priceUsdTotal']), 2), 'price': float(d.get('priceUsd') or 0), 'wallet': e.get('maker'), 'tx': e.get('transactionHash')})
    return out


_helius_hist: dict = {}


async def helius_candles(chain, pair, interval):
    """Solana coins no provider indexes yet (bonding-curve launches like $FEE): rebuild real candles
    from the pool's own swap history via Helius. Price per swap = SOL paid / tokens moved, priced in
    USD at the live SOL rate; outliers (multi-hop routes) are dropped against the rolling median."""
    if chain != 'solana':
        return []
    k = _helius_key()
    if not k:
        return []
    ck = f'{pair}:{interval}'
    hit = _helius_hist.get(ck)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    mint = await _pair_base_token(chain, pair) or (pair if pair.endswith('pump') else None)
    if not mint:
        return []
    rows, before = [], None
    try:
        async with httpx.AsyncClient(timeout=12) as http:
            for _ in range(5):
                params = {'api-key': k, 'type': 'SWAP', 'limit': 100}
                if before:
                    params['before'] = before
                r = await http.get(f'https://api.helius.xyz/v0/addresses/{pair}/transactions', params=params)
                page = r.json() if r.status_code == 200 else []
                if not isinstance(page, list) or not page:
                    break
                rows += page; before = page[-1].get('signature')
                if len(page) < 100:
                    break
            jr = await http.get('https://api.jup.ag/price/v3', params={'ids': WSOL}, headers={'x-api-key': os.environ.get('JUPITER_API_KEY', '')})
            sol_usd = float(((jr.json() or {}).get(WSOL) or {}).get('usdPrice') or 0)
    except Exception:
        return hit[1] if hit else []
    if not sol_usd:
        return []
    pts = []
    for tx in rows:
        who = tx.get('feePayer'); amt = 0.0; sol = 0.0
        for t in tx.get('tokenTransfers') or []:
            if who in (t.get('toUserAccount'), t.get('fromUserAccount')):
                if t.get('mint') == mint:
                    amt += float(t.get('tokenAmount') or 0)
                elif t.get('mint') == WSOL:
                    sol += float(t.get('tokenAmount') or 0)
        if not sol:
            # The signer's net SOL change is the real amount paid/received (transfers alone can surface only the fee leg).
            acct = next((a for a in tx.get('accountData') or [] if a.get('account') == who), None)
            if acct:
                sol = max(0.0, abs(acct.get('nativeBalanceChange') or 0) - (tx.get('fee') or 0)) / 1e9
        if amt > 0 and sol > 0 and tx.get('timestamp'):
            pts.append((tx['timestamp'], sol / amt * sol_usd, sol * sol_usd))
    pts.sort()
    clean = []
    for i, (t, px, usd) in enumerate(pts):
        window = sorted(p[1] for p in pts[max(0, i - 7): i + 8])
        med = window[len(window) // 2]
        if med and 0.4 < px / med < 2.5:
            clean.append((t, px, usd))
    step = INTERVAL_SECONDS.get(interval, 3600)
    buckets = {}
    for t, px, usd in clean:
        b = int(t // step * step); c = buckets.get(b)
        if c:
            c[2] = max(c[2], px); c[3] = min(c[3], px); c[4] = px; c[5] += usd
        else:
            buckets[b] = [b, px, px, px, px, usd]
    out = [buckets[x] for x in sorted(buckets)]
    for i in range(1, len(out)):
        out[i][1] = out[i - 1][4]; out[i][2] = max(out[i][2], out[i][1]); out[i][3] = min(out[i][3], out[i][1])
    _helius_hist[ck] = (time.time(), out)
    return out


@app.get('/api/candles/{chain}/{pair_address}')
async def get_candles(chain: str, pair_address: str, interval: str = Query('1h'), before: Optional[int] = None):
    if before:
        older = [c for c in await alchemy_candles(chain, pair_address, interval) if c[0] < before]
        return {'candles': _fill_gaps(older, INTERVAL_SECONDS.get(interval, 3600)), 'provider': 'Alchemy' if older else 'none', 'interval': interval, 'before': before}
    _hot_pairs[_pair_key(chain, pair_address)] = time.time()
    key = (chain, pair_address, interval)
    hit = _resp_cache.get(key)
    if hit and time.time() - hit[0] < 20:
        return hit[1]
    task = _history_tasks.get(key)
    if not task or task.done():
        task = _history_tasks[key] = asyncio.create_task(_build_candles(chain, pair_address, interval))
    # Speed budget: charts must paint in ~1s. If providers are slow, answer with FEELESS's own
    # recorded bars now; the full history finishes in the background and is served on the next poll.
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=1.2)
    except asyncio.TimeoutError:
        interval_seconds = INTERVAL_SECONDS.get(interval, 3600)
        ticks = _load().get(_pair_key(chain, pair_address), [])
        own = _bucket_candles(ticks, interval_seconds)
        if len(own) >= 2:
            return {'candles': _fill_gaps(own, interval_seconds), 'provider': 'FEELESS', 'interval': interval, 'tickCount': len(ticks), 'partial': True,
                    'source': 'FEELESS-recorded prices; full provider history is loading.'}
        return await task


_resp_cache: dict = {}
_history_tasks: dict = {}


async def _build_candles(chain, pair_address, interval):
    interval_seconds = INTERVAL_SECONDS.get(interval, 3600)
    store = _load()
    ticks = store.get(_pair_key(chain, pair_address), [])
    own = _bucket_candles(ticks, interval_seconds)
    hist = await codex_candles(chain, pair_address, interval)
    provider = 'Codex'
    if not hist or len(hist) < 2:
        hist = await alchemy_candles(chain, pair_address, interval)
        provider = 'Alchemy'
    if not hist or len(hist) < 2:
        hist = await helius_candles(chain, pair_address, interval)
        provider = 'Helius swaps'
    if hist and len(hist) >= 2:
        # FEELESS's own 15s ticks override/extend the provider bars, so the newest candle is live.
        own_by_t = {c[0]: c for c in own}
        merged = [own_by_t.pop(c[0], c) for c in hist] + [c for c in own if c[0] > hist[-1][0]]
        out = {'candles': _fill_gaps(merged, interval_seconds, own), 'provider': provider, 'interval': interval, 'tickCount': len(ticks),
               'source': f'{provider} price history, sharpened with FEELESS-recorded live ticks.'}
    else:
        out = {'candles': _fill_gaps(own, interval_seconds), 'provider': 'FEELESS', 'interval': interval, 'tickCount': len(ticks),
               'source': 'Real prices observed across FEELESS sessions — provider has no history for this pool yet.'}
    _resp_cache[(chain, pair_address, interval)] = (time.time(), out)
    if len(_resp_cache) > 2000:
        for k in sorted(_resp_cache, key=lambda k: _resp_cache[k][0])[:500]:
            _resp_cache.pop(k, None)
    return out


_trade_cache: dict = {}


WSOL = 'So11111111111111111111111111111111111111112'
USD_MINTS = {'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'}
_pair_info: dict = {}


def _helius_key():
    import re as _re2
    m = _re2.search(r'api-key=([A-Za-z0-9-]+)', os.environ.get('SOLANA_RPC_URL', ''))
    return m.group(1) if m else None


async def _pair_snapshot(chain, pool):
    hit = _pair_info.get(pool)
    if hit and time.time() - hit[0] < 30:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            p = ((await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{pool}')).json().get('pairs') or [None])[0]
    except Exception:
        p = None
    if p:
        _pair_info[pool] = (time.time(), p)
    return p


@app.get('/api/candles/trades/{chain}/{pool}')
async def pool_trades(chain: str, pool: str):
    """Latest real swaps for a pool, parsed from the transactions themselves (Helius) — shared
    15s cache so many viewers cost one call. No GeckoTerminal anywhere."""
    key = f'{chain}:{pool}'
    hit = _trade_cache.get(key)
    now = time.time()
    if hit and now - hit[0] < 15:
        return hit[1]
    codex = await codex_trades(chain, pool)
    if codex is not None:
        data = {'trades': codex, 'at': now, 'source': 'Codex'}
        _trade_cache[key] = (now, data)
        return data
    if chain != 'solana':
        return hit[1] if hit else {'trades': [], 'error': 'provider unavailable'}
    k = _helius_key(); pair = await _pair_snapshot(chain, pool)
    if not k or not pair:
        return hit[1] if hit else {'trades': [], 'error': 'provider unavailable'}
    base = (pair.get('baseToken') or {}).get('address')
    price_usd = float(pair.get('priceUsd') or 0); price_native = float(pair.get('priceNative') or 0)
    sol_usd = price_usd / price_native if price_native and (pair.get('quoteToken') or {}).get('address') == WSOL else None
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            r = await http.get(f'https://api.helius.xyz/v0/addresses/{pool}/transactions', params={'api-key': k, 'type': 'SWAP', 'limit': 40})
        rows = r.json() if r.status_code == 200 else None
    except Exception:
        rows = None
    if not isinstance(rows, list):
        return hit[1] if hit else {'trades': [], 'error': 'provider unavailable'}
    trades = []
    for tx in rows:
        who = tx.get('feePayer'); got = sent = 0.0; quote_usd = 0.0
        for t in tx.get('tokenTransfers') or []:
            amt = float(t.get('tokenAmount') or 0)
            if t.get('mint') == base:
                if t.get('toUserAccount') == who: got += amt
                elif t.get('fromUserAccount') == who: sent += amt
            elif t.get('mint') in USD_MINTS and who in (t.get('toUserAccount'), t.get('fromUserAccount')):
                quote_usd += amt
            elif t.get('mint') == WSOL and sol_usd and who in (t.get('toUserAccount'), t.get('fromUserAccount')):
                quote_usd += amt * sol_usd
        if not quote_usd and sol_usd:
            lam = sum(abs(n.get('amount') or 0) for n in tx.get('nativeTransfers') or [] if who in (n.get('fromUserAccount'), n.get('toUserAccount')))
            quote_usd = lam / 1e9 * sol_usd
        amt = got or sent
        if not amt:
            continue
        usd = quote_usd or amt * price_usd
        if price_usd and not (0.5 < (usd / amt) / price_usd < 1.5):  # multi-hop route double-counted the quote leg
            usd = amt * price_usd
        trades.append({'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(tx.get('timestamp') or now)), 'kind': 'buy' if got else 'sell',
                       'usd': round(usd, 2), 'price': usd / amt if amt else price_usd, 'wallet': who, 'tx': tx.get('signature')})
    data = {'trades': trades, 'at': now, 'source': 'Helius (parsed swaps)'}
    _trade_cache[key] = (now, data)
    return data


@app.get('/api/candles/health')
async def health():
    store = _load()
    return {'ok': True, 'pairsTracked': len(store), 'totalTicks': sum(len(v) for v in store.values())}


# ---- Live price stream: one upstream per pool, fanned out to every viewer ----------------------
# Helius logsSubscribe on the token mint fires the instant a swap lands (processed commitment); we then pull
# one fresh price (Jupiter, ~100ms) at most every STREAM_MIN_GAP per pool and push it to all viewers.
# Cost scales with pools being watched, not with users: 10 or 100,000 viewers on a coin = 1 upstream.
import json as _json
from fastapi import WebSocket, WebSocketDisconnect

STREAM_MIN_GAP = 0.35
_streams: dict = {}   # key -> {'clients': set(), 'task': Task, 'last': 0.0, 'price': None}


async def _stream_price(mint):
    # Codex tracks every trade (~120ms); Jupiter as fallback (its price is cached a few seconds).
    key_ = os.environ.get('CODEX_API_KEY', '').strip()
    try:
        async with httpx.AsyncClient(timeout=4) as http:
            if key_:
                r = await http.post('https://graph.codex.io/graphql', headers={'Authorization': key_},
                                    json={'query': 'query($a:String!,$n:Int!){getTokenPrices(inputs:[{address:$a,networkId:$n}]){priceUsd}}', 'variables': {'a': mint, 'n': CODEX_NET['solana']}})
                px = float((((r.json() or {}).get('data') or {}).get('getTokenPrices') or [{}])[0].get('priceUsd') or 0)
                if px:
                    return px
            r = await http.get('https://api.jup.ag/price/v3', params={'ids': mint}, headers={'x-api-key': os.environ.get('JUPITER_API_KEY', '')})
            return float(((r.json() or {}).get(mint) or {}).get('usdPrice') or 0) or None
    except Exception:
        return None


async def _broadcast(key, msg):
    st = _streams.get(key)
    if not st:
        return
    dead = []
    for ws in list(st['clients']):
        try:
            await ws.send_text(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        st['clients'].discard(ws)


async def _push_price(key, chain, pair, mint):
    st = _streams.get(key)
    if not st or time.time() - st['last'] < STREAM_MIN_GAP:
        return
    st['last'] = time.time()
    px = await _stream_price(mint)
    # Sanity gate: a tick 20x away from the last accepted price is a bad read (wrong token, quote-side
    # price), never a real move inside one second. Dropping it keeps charts and stored bars clean.
    prev = st['price']
    if px and prev and not (prev / 20 < px < prev * 20):
        return
    if px and px != st['price']:
        st['price'] = px
        await _broadcast(key, _json.dumps({'p': px, 't': time.time()}))
        # Persist ticks at most every 15s per pool — never block the live push on disk writes.
        if time.time() - st.get('saved', 0) > 15:
            st['saved'] = time.time()
            try:
                store = _load(); _record_tick(store, chain, pair, px, None); _save(store)
            except Exception:
                pass


async def _upstream(key, chain, pair):
    import websockets
    mint = await _pair_base_token(chain, pair)
    if not mint or mint == 'So11111111111111111111111111111111111111112':
        return  # unknown base token: clients keep their polling path rather than risk a wrong price
    url = os.environ.get('PRICE_STREAM_WS_URL', '').strip()
    await _push_price(key, chain, pair, mint)
    backoff = 1
    while key in _streams:
        try:
            if not url:
                raise RuntimeError('no stream url')
            async with websockets.connect(url, ping_interval=20) as ws:
                await ws.send(_json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'logsSubscribe', 'params': [{'mentions': [mint]}, {'commitment': 'processed'}]}))
                backoff = 1
                while key in _streams:
                    try:
                        await asyncio.wait_for(ws.recv(), timeout=1)
                    except asyncio.TimeoutError:
                        pass   # no swap event this second: refresh anyway (≤1s freshness guaranteed)
                    await _push_price(key, chain, pair, mint)
        except Exception:
            # Stream down: keep viewers live by polling every second until it reconnects.
            until = time.time() + min(30, backoff); backoff *= 2
            while key in _streams and time.time() < until:
                await _push_price(key, chain, pair, mint); await asyncio.sleep(1)


@app.websocket('/api/candles/stream/{chain}/{pair}')
async def price_stream(ws: WebSocket, chain: str, pair: str):
    if chain != 'solana' or not (32 <= len(pair) <= 44) or not pair.isalnum():
        await ws.close(code=1008); return
    await ws.accept()
    key = f'{chain}:{pair}'
    st = _streams.get(key)
    if not st:
        st = _streams[key] = {'clients': set(), 'task': None, 'last': 0.0, 'price': None}
        st['task'] = asyncio.create_task(_upstream(key, chain, pair))
    st['clients'].add(ws)
    if st['price']:
        await ws.send_text(_json.dumps({'p': st['price'], 't': time.time()}))
    try:
        while True:
            await ws.receive_text()   # clients only listen; this detects disconnects
    except WebSocketDisconnect:
        pass
    finally:
        st['clients'].discard(ws)
        if not st['clients']:
            _streams.pop(key, None)
            st['task'].cancel()


@app.get('/api/candles/stream-stats')
async def stream_stats():
    return {'pools': len(_streams), 'viewers': sum(len(s['clients']) for s in _streams.values())}
