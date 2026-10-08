"""
FEELESS Candles — a self-hosted OHLCV aggregator that never depends on a third
party's uptime.

Every time anyone's browser has a pair's live price on screen (a chart open, a
Pump Radar card rendered, a Discover row visible), it fires a tiny tick here.
This service buckets those real observed ticks into real OHLC candles on
request. It's deliberately not trying to replace a real market data provider
for pairs nobody's looked at yet — it's the fallback that makes sure a chart
never just dies when a provider fails, and it gets *better* the more the
site is used, permanently, because every tick is kept.

File-backed JSON, zero external dependencies, standalone FastAPI app.
"""
import env_loader  # noqa: F401  (must run before reading os.environ)
import asyncio
import json
import os
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


_hot_pairs: dict = {}
HOT_TTL = 30 * 60
DEX_CHAIN = {'solana': 'solana', 'ethereum': 'ethereum', 'base': 'base', 'bsc': 'bsc', 'arbitrum': 'arbitrum', 'avalanche': 'avalanche', 'polygon': 'polygon', 'sui': 'sui',
             'optimism': 'optimism', 'zksync': 'zksync', 'zora': 'zora', 'cronos': 'cronos', 'unichain': 'unichain', 'worldchain': 'worldchain', 'tron': 'tron'}


import re as _re_mod
_re_pair = _re_mod.compile(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$')
_tick_pending: dict = {}


def _record_tick(store: dict, chain: str, pair: str, price: float, volume):
    key = _pair_key(chain, pair)
    ticks = store.setdefault(key, [])
    now = time.time()
    if ticks and now - ticks[-1]['t'] < 14:
        return
    # One bad read must never draw a spike for every viewer: a tick >4x away from the recent median
    # is held until 3 consecutive reads agree on the new level (a real move), then accepted.
    recent = sorted(t['p'] for t in ticks[-10:])
    if recent:
        med = recent[len(recent) // 2]
        if not (med / 4 <= price <= med * 4):
            pend = [x for x in _tick_pending.get(key, []) if abs(x / price - 1) < 0.2] + [price]
            _tick_pending[key] = pend
            if len(pend) < 3:
                return
        _tick_pending.pop(key, None)
    ticks.append({'t': now, 'p': price, 'v': volume})
    cutoff = now - MAX_AGE_SECONDS
    store[key] = [t for t in ticks if t['t'] >= cutoff][-MAX_TICKS_PER_PAIR:]


# 📈 ALWAYS LIVE: every major and stock token is recorded all the time (pair → mint), not only after someone opens its chart.
# A chart opened cold used to show flat minutes — the history provider prints a candle only when a trade lands, and the live
# 15s ticks that sharpen it started at the click ("stocks charts don't move ever", "make sure stocks and all major coins move").
_always_hot: dict = {'at': 0.0, 'pairs': {}}
ALWAYS_REFRESH = 600
ALWAYS_GAP, ALWAYS_KEEP = 55, 3000


def always_pairs(lists):
    """Discover rows (majors / stocks) → {pairAddress: mint}. Pure."""
    out = {}
    for rows in lists or []:
        for r in rows or []:
            if r.get('pairAddress') and (r.get('baseAddress') or r.get('mint')):
                out[r['pairAddress']] = r.get('baseAddress') or r.get('mint')
    return out


async def _refresh_always(http, now):
    if now - _always_hot['at'] < ALWAYS_REFRESH and _always_hot['pairs']:
        return
    _always_hot['at'] = now
    got = []
    for lens in ('majors', 'stocks'):
        try:
            got.append((await http.get(f'http://127.0.0.1:5077/api/reputation/fuses/discover?lens={lens}&chain=solana')).json().get('pools') or [])
        except Exception:
            pass
    pairs = always_pairs(got)
    if pairs:
        _always_hot['pairs'] = pairs


async def _poll_hot_pairs():
    """Server-side price recorder: every pair anyone opened in the last 30 min gets a
    price tick every 15s, so candles build even while providers throttle us."""
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
            if True:   # majors + stocks tick even when nobody has a chart open
                store = _load()
                async with httpx.AsyncClient(timeout=8) as http:
                    await _refresh_always(http, now)
                    always = _always_hot['pairs']
                    sol_pairs = sorted(set(by_chain.pop('solana', [])) | set(always))
                    if sol_pairs:
                        mints = {p: always.get(p) or await _pair_base_token('solana', p) for p in sol_pairs}
                        ids = sorted({m for m in mints.values() if m})
                        prices = {}
                        for i in range(0, len(ids), 50):
                            try:
                                r = await http.get(f'https://lite-api.jup.ag/price/v3?ids={",".join(ids[i:i + 50])}')
                                prices.update({k: float(v.get('usdPrice') or 0) for k, v in (r.json() or {}).items()})
                            except Exception:
                                pass
                        hot_now = {k.split(':', 1)[1] for k in _hot_pairs if k.startswith('solana:')}
                        for p, m in mints.items():
                            if prices.get(m, 0) > 0:
                                if p not in hot_now:   # nobody is watching: one tick a minute is enough to keep every 1-min candle moving,
                                    tk = store.get(_pair_key('solana', p)) or []   # and only ~2 days are kept (the store is rewritten every pass)
                                    if tk and now - tk[-1]['t'] < ALWAYS_GAP:
                                        continue
                                _record_tick(store, 'solana', p, prices[m], None)
                                if p not in hot_now and len(store.get(_pair_key('solana', p)) or []) > ALWAYS_KEEP:
                                    store[_pair_key('solana', p)] = store[_pair_key('solana', p)][-ALWAYS_KEEP:]
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
from starlette.middleware.gzip import GZipMiddleware as _GZip
app.add_middleware(_GZip, minimum_size=1024)   # ⚡ every list over 1KB goes compressed (a 287KB trench list was sent raw)


@app.on_event('startup')
async def _start_poller():
    asyncio.create_task(_poll_hot_pairs())
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in (os.environ.get('ALLOWED_ORIGINS') or '*').split(',') if o.strip()], allow_methods=['*'], allow_headers=['*'])


@app.post('/api/candles/observe')
async def observe(payload: TickPayload):
    """Browsers only say "someone is watching this pair"; the price itself is always fetched by the
    server. A client-supplied price is never stored — otherwise one user could draw on everyone's chart."""
    if not _re_pair.match(payload.pairAddress or '') or payload.chain not in DEX_CHAIN:
        return {'ok': False}
    _hot_pairs[_pair_key(payload.chain, payload.pairAddress)] = time.time()
    return {'ok': True}


def _sanitize(candles, step):
    """Secure candles: drop non-finite/non-positive prices, snap every bar to its interval bucket, merge duplicates
    (first open, max high, min low, last close, summed volume), keep high >= max(o,c) and low <= min(o,c), sort by time."""
    import math
    by = {}
    for c in sorted((c for c in candles or [] if c and len(c) >= 5), key=lambda c: c[0]):
        try:
            t, o, h, l, cl = int(c[0]) // step * step, float(c[1]), float(c[2]), float(c[3]), float(c[4])
            v = float(c[5]) if len(c) > 5 and c[5] is not None else 0.0
        except (TypeError, ValueError):
            continue
        if not all(math.isfinite(x) and x > 0 for x in (o, h, l, cl)) or not math.isfinite(v) or v < 0:
            continue
        h, l = max(o, h, l, cl), min(o, h, l, cl)
        if t in by:
            b = by[t]; b[2] = max(b[2], h); b[3] = min(b[3], l); b[4] = cl; b[5] += v
        else:
            by[t] = [t, o, h, l, cl, v]
    return [by[t] for t in sorted(by)]


def _fill_gaps(candles, step, own=None, limit=5000):
    """No skipped candles: quiet intervals become flat bars at the last close (zero volume);
    if FEELESS recorded its own tick in that gap, the real observed price is used instead."""
    candles = _sanitize(candles, step)
    if not candles:
        return candles
    by_own = {int(c[0]): c for c in _sanitize(own or [], step)}
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
    # Continuous market: each bar opens at the previous close (high/low widened to include it), so the chart
    # never shows detached one-price dashes or gaps between consecutive candles.
    for k in range(1, len(out)):
        pc = out[k - 1][4]
        bar = list(out[k]); bar[1] = pc; bar[2] = max(bar[2], pc, bar[4]); bar[3] = min(bar[3], pc, bar[4]); out[k] = bar
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


PUMP_PROGRAM = '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'
_B58_ALPH = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def _b58decode(v: str) -> bytes:
    n = 0
    for ch in v:
        n = n * 58 + _B58_ALPH.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, 'big')
    return b'\x00' * (len(v) - len(v.lstrip('1'))) + raw


async def _accept_mint_hint(chain, pair, mint):
    """A browser may tell us which coin a pool trades (DexScreener hasn't indexed brand-new pools).
    Trusted only if the pool account's on-chain data actually contains that mint, so one client can't
    point everyone's chart at a different coin."""
    key = f'{chain}:{pair}'
    if chain != 'solana' or key in _base_token or not mint or not (32 <= len(mint) <= 44) or not all(c in _B58_ALPH for c in mint + pair):
        return
    if mint == pair:
        _base_token[key] = mint; return
    rpc = os.environ.get('SOLANA_RPC_URL', '').strip()
    if not rpc:
        return
    try:
        from solders.pubkey import Pubkey
        # pump.fun bonding curve: the pool address is derived from the mint.
        if str(Pubkey.find_program_address([b'bonding-curve', bytes(Pubkey.from_string(mint))], Pubkey.from_string(PUMP_PROGRAM))[0]) == pair:
            _base_token[key] = mint; return
        async with httpx.AsyncClient(timeout=6) as http:
            r = await http.post(rpc, json={'jsonrpc': '2.0', 'id': 1, 'method': 'getAccountInfo', 'params': [pair, {'encoding': 'jsonParsed'}]})
        v = ((r.json() or {}).get('result') or {}).get('value') or {}
        d = v.get('data')
        if isinstance(d, dict):  # a token account (e.g. a curve vault) states its own mint
            if ((d.get('parsed') or {}).get('info') or {}).get('mint') == mint:
                _base_token[key] = mint
        elif isinstance(d, list) and d:
            import base64
            if _b58decode(mint) in base64.b64decode(d[0]):  # AMM pool accounts embed their mints
                _base_token[key] = mint
    except Exception:
        pass


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


_jup_hist: dict = {}
JUP_IV = {'1m': '1_MINUTE', '5m': '5_MINUTE', '15m': '15_MINUTE', '1h': '1_HOUR', '4h': '4_HOUR', '1d': '1_DAY'}


async def jupiter_candles(chain, pair, interval):
    """Token-level USD candles from Jupiter's chart data (the same price basis as the header and
    swaps), from launch onward. Cached 30s per token+interval so viewer count never multiplies calls."""
    if chain != 'solana' or interval not in JUP_IV:
        return []
    mint = await _pair_base_token(chain, pair) or pair  # a bare mint (bonding-curve coin) charts directly
    ck = f'{mint}:{interval}'
    hit = _jup_hist.get(ck)
    if hit and time.time() - hit[0] < 30:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=6) as http:
            r = await http.get(f'https://datapi.jup.ag/v2/charts/{mint}', params={'interval': JUP_IV[interval], 'to': int(time.time() * 1000), 'candles': 300, 'type': 'price', 'quote': 'usd'})
        rows = (r.json() or {}).get('candles') or [] if r.status_code == 200 else []
    except Exception:
        return hit[1] if hit else []
    out = [[int(c['time']), float(c['open']), float(c['high']), float(c['low']), float(c['close']), float(c.get('volume') or 0)] for c in rows if c.get('close')]
    _jup_hist[ck] = (time.time(), out)
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
            # Page back until the history spans ~150 bars (busy coins fill a page in seconds; Helius'
            # SWAP filter returns short pages, so page length is not an end-of-history signal).
            want_from = time.time() - 150 * INTERVAL_SECONDS.get(interval, 3600)
            for _ in range(20):
                params = {'api-key': k, 'type': 'SWAP', 'limit': 100}
                if before:
                    params['before'] = before
                r = await http.get(f'https://api.helius.xyz/v0/addresses/{pair}/transactions', params=params)
                page = r.json() if r.status_code == 200 else []
                if not isinstance(page, list) or not page:
                    break
                rows += page; before = page[-1].get('signature')
                if (page[-1].get('timestamp') or 0) < want_from:
                    break
            sol_usd = await _jup_price(WSOL) or 0
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
async def get_candles(chain: str, pair_address: str, interval: str = Query('1h'), before: Optional[int] = None, mint: Optional[str] = None):
    await _accept_mint_hint(chain, pair_address, mint)
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


FULL_HISTORY = 120   # bars: enough to fill a chart at any interval


async def _build_candles(chain, pair_address, interval):
    interval_seconds = INTERVAL_SECONDS.get(interval, 3600)
    store = _load()
    ticks = store.get(_pair_key(chain, pair_address), [])
    own = _bucket_candles(ticks, interval_seconds)
    # Anchor: the live token price (same number the header and swaps use). Provider history that
    # ends far from it is priced off a different pool/quote and must not be drawn.
    anchor = None
    if chain == 'solana':
        mint = await _pair_base_token(chain, pair_address) or pair_address
        anchor = await _stream_price(mint)
    agrees = lambda h: bool(h) and len(h) >= 1 and (not anchor or anchor / 3 <= h[-1][4] <= anchor * 3)
    # Charts must be ready: take the first provider with a full history (FULL_HISTORY bars); if each is thin, keep the
    # longest one that agrees with the live price instead of the first short answer.
    hist, provider = [], None
    for name, fn in (('Jupiter', jupiter_candles), ('Alchemy', alchemy_candles), ('Helius swaps', helius_candles)):
        try:
            h = await fn(chain, pair_address, interval)
        except Exception:
            h = None
        if agrees(h) and len(h) > len(hist):
            hist, provider = h, name
        if len(hist) >= FULL_HISTORY:
            break
    if hist and len(hist) >= 2:
        # FEELESS's own 15s ticks override/extend the provider bars, so the newest candle is live.
        own_by_t = {c[0]: c for c in own}
        merged = [own_by_t.pop(c[0], c) for c in hist] + [c for c in own if c[0] > hist[-1][0]]
        out = {'candles': _fill_gaps(merged, interval_seconds, own), 'provider': provider, 'interval': interval, 'tickCount': len(ticks),
               'source': f'{provider} price history, sharpened with FEELESS-recorded live ticks.'}
    else:
        out = {'candles': _fill_gaps(own, interval_seconds), 'provider': 'FEELESS', 'interval': interval, 'tickCount': len(ticks),
               'source': 'Real prices observed across FEELESS sessions — provider has no history for this pool yet.'}
    if out['candles']:  # never cache an empty answer — a brand-new coin must fill in on the next poll
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
    """HELIUS_API_KEY, else the api-key in HELIUS_RPC_URL, else in SOLANA_RPC_URL (which may point at another RPC)."""
    import re as _re2
    if os.environ.get('HELIUS_API_KEY'):
        return os.environ['HELIUS_API_KEY'].strip()
    for var in ('HELIUS_RPC_URL', 'SOLANA_RPC_URL'):
        m = _re2.search(r'helius[^?]*\?(?:.*&)?api-key=([A-Za-z0-9-]{20,})', os.environ.get(var, ''))
        if m:
            return m.group(1)
    return None


async def _pair_snapshot(chain, pool):
    hit = _pair_info.get(pool)
    if hit and time.time() - hit[0] < 30:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            p = ((await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{pool}')).json().get('pairs') or [None])[0]
            if not p and chain == 'solana':   # 📡 DexScreener silent → Jupiter's data for the same pool (the tape needs the coin + price)
                import launchpad_board as _lb
                p = await _lb.jup_lookup(http, pool)
                if p:   # the tape converts SOL legs to $ with priceUsd / priceNative — Jupiter's row has no native price, so derive it
                    try:
                        sol = float((((await http.get('https://lite-api.jup.ag/price/v3', params={'ids': 'So11111111111111111111111111111111111111112'})).json() or {})
                                     .get('So11111111111111111111111111111111111111112') or {}).get('usdPrice') or 0)
                    except Exception:
                        sol = 0.0
                    if sol > 0:
                        p = {**p, 'priceNative': str(float(p.get('priceUsd') or 0) / sol)}
    except Exception:
        p = None
    if p:
        _pair_info[pool] = (time.time(), p)
    return p


@app.get('/api/candles/trades/{chain}/{pool}')
async def pool_trades(chain: str, pool: str):
    """Latest real swaps for a pool, parsed from the transactions themselves (Helius) — shared
    15s cache so many viewers cost one call."""
    key = f'{chain}:{pool}'
    hit = _trade_cache.get(key)
    now = time.time()
    if hit and now - hit[0] < 15:
        return hit[1]
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
        # Helius out of quota / down: read the pool's latest swaps straight from Solana RPC (Alchemy).
        rpc = await _rpc_trades(pool, base, price_usd, sol_usd)
        if rpc is None:
            return hit[1] if hit else {'trades': [], 'error': 'provider unavailable'}
        data = {'trades': rpc, 'at': now, 'source': 'Solana RPC (parsed swaps)'}
        _trade_cache[key] = (now, data)
        return data
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


def parse_rpc_swap(tx, base, price_usd, sol_usd, pool=None):
    """One jsonParsed Solana transaction -> a tape row. The trader is the owner (not the pool) whose balance of the coin
    moved most — bots and routers often pay fees from another key. Priced by their SOL/USDC leg; no leg + under 1¢ = spam."""
    meta, msg = (tx or {}).get('meta') or {}, ((tx or {}).get('transaction') or {}).get('message') or {}
    keys = [k.get('pubkey') if isinstance(k, dict) else k for k in msg.get('accountKeys') or []]
    if meta.get('err') or not keys:
        return None
    def bal(rows, mint, owner):
        return sum(float((r.get('uiTokenAmount') or {}).get('uiAmount') or 0) for r in rows or [] if r.get('mint') == mint and r.get('owner') == owner)
    pre_t, post_t = meta.get('preTokenBalances'), meta.get('postTokenBalances')
    owners = {r.get('owner') for r in (pre_t or []) + (post_t or []) if r.get('mint') == base and r.get('owner') and r.get('owner') != pool}
    deltas = {o: bal(post_t, base, o) - bal(pre_t, base, o) for o in owners}
    who = max(deltas, key=lambda o: abs(deltas[o]), default=None)
    if not who or not deltas[who]:
        return None
    delta = deltas[who]; amt = abs(delta)
    usd = sum(abs(bal(post_t, m, who) - bal(pre_t, m, who)) for m in USD_MINTS)
    if not usd and sol_usd:
        lamports = 0
        if who in keys:
            k = keys.index(who); pre, post = (meta.get('preBalances') or []), (meta.get('postBalances') or [])
            if k < len(pre) and k < len(post):
                lamports = abs(post[k] - pre[k] + (meta.get('fee') or 0 if k == 0 else 0))
        wsol = abs(bal(post_t, WSOL, who) - bal(pre_t, WSOL, who))
        usd = ((lamports / 1e9 if lamports > 100_000 else 0) + wsol) * sol_usd  # < 0.0001 SOL = fees, not a leg
    if not usd or (price_usd and not (0.5 < (usd / amt) / price_usd < 1.5)):
        usd = amt * price_usd  # routed through accounts we can't see: value it at the live price
    if usd < 0.01:
        return None  # dust transfer / bot spam, not a swap
    sig = ((tx.get('transaction') or {}).get('signatures') or [None])[0]
    return {'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(tx.get('blockTime') or time.time())), 'kind': 'buy' if delta > 0 else 'sell',
            'usd': round(usd, 2), 'price': usd / amt if amt else price_usd, 'wallet': who, 'tx': sig}


_tape_rows: dict = {}   # signature -> parsed row (None = not a swap): a transaction is read ONCE, later refreshes fetch only new ones
_tape_bad: dict = {}    # rpc url -> skip until (it refused / is out of quota)
TAPE_NEW = 25           # new transactions read per refresh


def tape_lanes(pool_urls, keeper_lanes):
    """RPC order for the trade tape: every other keyed lane, then the public nodes, the keeper's own first lane LAST (its quota
    is for real swaps)."""
    first = list(keeper_lanes[:1])
    return [u for u in pool_urls if u not in first] + first


async def _rpc_trades(pool, base, price_usd, sol_usd, limit=40):
    """The pool's latest swaps straight from Solana RPC, walking EVERY lane (it used one fixed Alchemy key: when that plan ran out
    the tape read "waiting for trades…" on every coin)."""
    import chain_rpc
    if not base:
        return None
    now = time.time()
    async with httpx.AsyncClient(timeout=10) as http:
        for url in tape_lanes(list(chain_rpc.RPC_POOL), list(chain_rpc.KEEPER_LANES)):
            if _tape_bad.get(url, 0) > now:
                continue
            try:
                r = await http.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'getSignaturesForAddress', 'params': [pool, {'limit': limit}]})
                sigs = r.json().get('result') if r.status_code == 200 else None
                if not isinstance(sigs, list):
                    raise ValueError('no signatures')
                ok = [x['signature'] for x in sigs if not x.get('err')]
                new = [x for x in ok if x not in _tape_rows][:TAPE_NEW]
                if new:
                    batch = [{'jsonrpc': '2.0', 'id': i, 'method': 'getTransaction', 'params': [x, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}]}
                             for i, x in enumerate(new)]
                    rr = await http.post(url, json=batch)
                    txs = rr.json() if rr.status_code == 200 else None
                    if not isinstance(txs, list) or not any(isinstance(t, dict) and t.get('result') for t in txs):
                        raise ValueError('no transactions')
                    for t in txs:
                        if isinstance(t, dict) and t.get('result') and isinstance(t.get('id'), int) and t['id'] < len(new):
                            _tape_rows[new[t['id']]] = parse_rpc_swap(t['result'], base, price_usd, sol_usd, pool)
                if len(_tape_rows) > 20000:
                    for k in list(_tape_rows)[:5000]:
                        _tape_rows.pop(k, None)
                return [_tape_rows[x] for x in ok if _tape_rows.get(x)]
            except Exception:
                _tape_bad[url] = now + 60
    return None


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


_px_cache: dict = {}


async def _jup_price(mint):
    """USD price with fallbacks (keyed Jupiter → free Jupiter → DexScreener), cached 5s per mint so
    thousands of viewers never multiply upstream calls. A 429 on one source never blanks a chart."""
    hit = _px_cache.get(mint)
    if hit and time.time() - hit[0] < 5:
        return hit[1]
    key_ = os.environ.get('JUPITER_API_KEY', '')
    async with httpx.AsyncClient(timeout=5) as http:
        for url, hdr in (('https://api.jup.ag/price/v3', {'x-api-key': key_}), ('https://lite-api.jup.ag/price/v3', {})):
            try:
                r = await http.get(url, params={'ids': mint}, headers=hdr)
                if r.status_code == 200:
                    px = float(((r.json() or {}).get(mint) or {}).get('usdPrice') or 0)
                    if px:
                        _px_cache[mint] = (time.time(), px)
                        return px
            except Exception:
                pass
        try:
            r = await http.get(f'https://api.dexscreener.com/tokens/v1/solana/{mint}')
            pairs = sorted(r.json() or [], key=lambda p: -float((p.get('liquidity') or {}).get('usd') or 0))
            px = float((pairs[0] if pairs else {}).get('priceUsd') or 0)
            if px:
                _px_cache[mint] = (time.time(), px)
                return px
        except Exception:
            pass
    return hit[1] if hit else None


async def _stream_price(mint):
    try:
        return await _jup_price(mint)
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
    mint = await _pair_base_token(chain, pair) or pair  # bonding-curve coins are addressed by mint
    if mint == 'So11111111111111111111111111111111111111112':
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
    await _accept_mint_hint(chain, pair, ws.query_params.get('mint'))
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
