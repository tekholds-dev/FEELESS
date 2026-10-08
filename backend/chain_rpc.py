"""Solana RPC: the endpoint pool and the retrying JSON-RPC client every FEELESS service uses.

A dedicated key (Helius / QuickNode / Alchemy / Triton) goes first via SOLANA_RPC_URL and takes almost all traffic; public endpoints
are fallback-only, so a rate-limited public node never blocks resolution. Each endpoint has its own failure budget — a bad node is
skipped for a cooldown window instead of failing every request that hits it.
"""
import asyncio
import os
import time
from typing import Optional

import env_loader  # noqa: F401  (must run before reading os.environ)
import httpx

_dedicated = os.environ.get('SOLANA_RPC_URL', '').strip()
_backup = os.environ.get('SOLANA_RPC_URL_2', '').strip()   # a second keyed endpoint (any provider): the keeper's other lane
_alchemy = os.environ.get('ALCHEMY_API_KEY', '').strip()
_alchemy_url = f'https://solana-mainnet.g.alchemy.com/v2/{_alchemy}' if _alchemy else ''
# lanes 3–6: more keyed endpoints (free plans from different providers add up — each has its own quota the keeper falls through)
_more = {n: os.environ.get(f'SOLANA_RPC_URL_{n}', '').strip() for n in (3, 4, 5, 6)}
KEEPER_LANES = [e for e in dict.fromkeys([_dedicated, _backup, *_more.values(), _alchemy_url]) if e]   # keyed endpoints, in the keeper's order
PUBLIC = ['https://api.mainnet-beta.solana.com', 'https://solana-rpc.publicnode.com']
KEEPER_PUBLIC = PUBLIC[0]   # while no keyed lane works, this public node is the keeper's alone (scanners use the others)
RPC_POOL = KEEPER_LANES + PUBLIC
_rpc_cooldown_until: dict[str, float] = {}
RPC_COOLDOWN_SECONDS = 30
RPC_BURST_COOLDOWN = 4   # a plain burst 429 (not a spent plan) only rests that node a few seconds — at 30s the scanners' bursts cooled EVERY lane at once and holder scans came back empty
SCAN_CONCURRENCY = 4     # holder / launch scans in flight at once across all scanners (the free plans' burst limits are low)
_scan_gate = asyncio.Semaphore(SCAN_CONCURRENCY)
RPC_MAX_RETRIES = len(RPC_POOL)


def _next_rpc_endpoint() -> Optional[str]:
    """Priority order (dedicated key, then Alchemy, then public nodes), skipping any endpoint in its cooldown window.
    Public nodes are fallback-only: they lag and rate-limit, so balances read right after a trade came back stale."""
    now = time.time()
    for endpoint in RPC_POOL:
        if max(_rpc_cooldown_until.get(endpoint, 0), _quota_until.get(endpoint, 0)) <= now:
            return endpoint
    return min(RPC_POOL, key=lambda e: _rpc_cooldown_until.get(e, 0)) if RPC_POOL else None


# The scanners' share of the dedicated endpoint, in calls a second (fractions allowed). A free plan is a DAILY budget (QuickNode
# 50,000 requests a day ≈ 0.58 a second): at 5 a second the holder scans spent all of it by late morning and the keeper fell back to
# public nodes; at 0 the scans starve (public nodes refuse most holder lookups) and the trench / volume lists go empty. Default 0.3 a
# second ≈ 26K a day for scans, the rest for the keeper. A paid plan can raise it with RPC_SCAN_RPS.
try:
    SCAN_RPS = max(0.0, float(os.environ.get('RPC_SCAN_RPS', '1.0') or 0))
except ValueError:
    SCAN_RPS = 1.0
SCAN_BURST = 6.0
QUOTA_WORDS = ('daily request limit', 'capacity limit', 'monthly', 'quota', 'credits')
_quota_until: dict[str, float] = {}   # endpoint → when its plan's quota comes back (never retried before that)


def out_of_quota(status, text, headers=None, now=None):
    """A 429 that is the PLAN's quota (day / month used up), not a burst → seconds until it resets (0 = an ordinary rate limit).
    Retrying a spent plan only wastes time: each keeper call used to wait ~7s on it before reaching a node that works."""
    if status != 429:
        return 0
    low = str(text or '').lower()
    h = {str(k).lower(): v for k, v in dict(headers or {}).items()}
    spent = any(w in low for w in QUOTA_WORDS) or str(h.get('x-ratelimit-remaining', '')).strip() == '0'
    if not spent:
        return 0
    try:
        reset = float(str(h.get('x-ratelimit-reset', '')).split(',')[0])
    except ValueError:
        reset = 0.0
    return min(86400.0, reset) if reset > 0 else 900.0   # no reset told → look again in 15 min


def quota_state(now=None):
    """For HQ: which keyed lanes are out of quota and for how long. Never the URL — only its position and the minutes left."""
    now = now or time.time()
    return [{'lane': i + 1, 'provider': provider_of(e), 'slot': slot_of(e),
             'spent': _quota_until.get(e, 0) > now, 'backInMin': max(0, round((_quota_until.get(e, 0) - now) / 60))} for i, e in enumerate(KEEPER_LANES)]

_scan_stamps: list = []   # [tokens, last refill] — a token bucket (kept under the old name for the tests that reset it)


def _scan_slot() -> bool:
    """A token from the scanners' bucket on the dedicated endpoint? Refills at SCAN_RPS a second, holds at most a small burst."""
    now = time.time()
    if len(_scan_stamps) != 2:
        _scan_stamps[:] = [min(SCAN_BURST, max(1.0, SCAN_RPS)) if SCAN_RPS > 0 else 0.0, now]
    tokens = min(max(SCAN_BURST, SCAN_RPS), _scan_stamps[0] + (now - _scan_stamps[1]) * SCAN_RPS)
    _scan_stamps[1] = now
    if tokens < 1.0:
        _scan_stamps[0] = tokens
        return False
    _scan_stamps[0] = tokens - 1.0
    return True


async def _rpc(http: httpx.AsyncClient, method: str, params: list, scan: bool = True):
    """Calls the RPC pool with retry + per-endpoint cooldown on failure or rate-limit."""
    last_error = None
    now = time.time()
    order = [e for e in RPC_POOL if max(_rpc_cooldown_until.get(e, 0), _quota_until.get(e, 0)) <= now] or ([_next_rpc_endpoint()] if RPC_POOL else [])
    if scan and not any(_quota_until.get(e, 0) <= now for e in KEEPER_LANES) and len([e for e in RPC_POOL if e not in KEEPER_LANES]) > 1:
        order = [e for e in order if e != KEEPER_PUBLIC] or order   # every keyed plan is spent → the keeper lives on this node; scanners stay off it
    for endpoint in order[:RPC_MAX_RETRIES]:
        if scan and endpoint == _dedicated and len(RPC_POOL) > 1 and not _scan_slot():   # scan=False = the keeper falling back: never budgeted
            last_error = last_error or 'scan_budget'   # over the scanners' share → try the next endpoint, leave the plan to the keeper
            continue
        try:
            if scan:
                async with _scan_gate:
                    res = await http.post(endpoint, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
            else:
                res = await http.post(endpoint, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
            if res.status_code == 429:
                spent = out_of_quota(429, res.text, res.headers)
                if spent:
                    _quota_until[endpoint] = time.time() + spent
                _rpc_cooldown_until[endpoint] = time.time() + (RPC_COOLDOWN_SECONDS if spent else RPC_BURST_COOLDOWN)
                last_error = 'rate_limited'
                continue
            res.raise_for_status()
            body = res.json()
            if 'error' in body:
                last_error = body['error']
                continue
            return body.get('result')
        except (httpx.HTTPError, ValueError):
            _rpc_cooldown_until[endpoint] = time.time() + RPC_COOLDOWN_SECONDS
            last_error = 'request_failed'
            continue
    if last_error:
        raise RuntimeError(f'RPC pool exhausted: {last_error}')
    return None


async def broadcast(http: httpx.AsyncClient, signed_b64: str) -> int:
    """📡 Re-send ONE already-signed transaction to EVERY endpoint at once (same signature = idempotent, it can only land once).
    A single send through one busy node was why real buys/sells "expired": the tx never reached a leader. No preflight, no node-side
    retries — the keeper re-sends every ~2s until the chain confirms it or its blockhash expires. Returns how many nodes took it."""
    import asyncio

    async def one(endpoint):
        try:
            res = await http.post(endpoint, json={'jsonrpc': '2.0', 'id': 1, 'method': 'sendTransaction',
                                                  'params': [signed_b64, {'encoding': 'base64', 'skipPreflight': True, 'maxRetries': 0}]})
            return res.status_code == 200 and 'error' not in res.json()
        except (httpx.HTTPError, ValueError):
            return False
    live = [e for e in RPC_POOL if _quota_until.get(e, 0) <= time.time()] or RPC_POOL
    return sum(1 for ok in await asyncio.gather(*[one(e) for e in live]) if ok)


async def rpc_priority(http: httpx.AsyncClient, method: str, params: list, tries: int = 4):
    """💵 The KEEPER's lanes. Real-money calls (balances, sends, confirmations) go to the keyed endpoints FIRST — the dedicated one,
    then the backup (`SOLANA_RPC_URL_2`), then Alchemy — and ignore the shared cooldown the scanners trip. A burst 429 moves to the
    next lane at once (waiting only when there is no other lane); a lane whose PLAN is used up is skipped until it resets. Only
    then the public pool."""
    import asyncio
    now = time.time()
    lanes = [e for e in KEEPER_LANES if _quota_until.get(e, 0) <= now]
    i = 0   # which lane is next; a lane dropped as spent never shifts the order of the ones after it
    for attempt in range(max(tries, len(lanes) + 2) if lanes else 0):
        if not lanes:
            break
        endpoint = lanes[i % len(lanes)]
        try:
            res = await http.post(endpoint, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
        except httpx.HTTPError:
            if len(lanes) == 1:
                break
            i += 1
            continue
        if res.status_code == 429:
            spent = out_of_quota(429, res.text, res.headers)
            if spent:
                _quota_until[endpoint] = time.time() + spent
                i = lanes.index(endpoint)
                lanes.remove(endpoint)   # the next lane slides into this position
                continue
            if len(lanes) == 1:
                await asyncio.sleep(0.35 * (attempt + 1))
            i += 1
            continue
        if res.status_code != 200:
            if len(lanes) == 1:
                break
            i += 1
            continue
        try:
            body = res.json()
        except ValueError:
            break
        if 'error' not in body:
            return body.get('result')
        break   # a real RPC error (bad params, simulation failed, …) is the caller's to see — the pool reports it the same way
    # no keyed lane left: public nodes, paced — a busy public node is asked again after a breath instead of failing a real-money call
    pub = [e for e in RPC_POOL if e not in KEEPER_LANES]
    for attempt in range(3 if pub else 0):
        for endpoint in pub:
            try:
                res = await http.post(endpoint, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
            except httpx.HTTPError:
                continue
            if res.status_code != 200:
                continue
            try:
                body = res.json()
            except ValueError:
                continue
            if 'error' not in body:
                return body.get('result')
            raise RuntimeError(f"RPC pool exhausted: {body['error']}")
        await asyncio.sleep(0.8 * (attempt + 1))
    return await _rpc(http, method, params, scan=False)


# 🔑 The owner can change a keyed lane from HQ without opening a file. Pure helpers (tested) + a live swap of the lanes.
LANE_KEYS = {1: 'SOLANA_RPC_URL', 2: 'SOLANA_RPC_URL_2', **{n: f'SOLANA_RPC_URL_{n}' for n in (3, 4, 5, 6)}}


def slot_of(url):
    return 1 if url == _dedicated else 2 if url == _backup else next((n for n, u in _more.items() if u == url), 0)


def clean_rpc_url(url):
    """A lane URL must be https, a public host name (never an IP, localhost or a private name), ≤ 300 chars. → url or raises ValueError."""
    import re
    u = str(url or '').strip()
    m = re.match(r'^https://([A-Za-z0-9.-]+)(:\d+)?(/[^\s]*)?$', u)
    if not m or len(u) > 300:
        raise ValueError('Paste the full https:// RPC URL from your provider (it includes your key).')
    host = m.group(1).lower()
    if '.' not in host or re.match(r'^[\d.]+$', host) or host.endswith(('.local', '.internal', '.localhost', '.lan')) or host.startswith('localhost'):
        raise ValueError('That is not a public RPC host.')
    return u


def provider_of(url):
    """What HQ may show for a lane: the provider's domain only (never the path, key or sub-domain)."""
    import re
    m = re.match(r'^https?://([^/:?]+)', str(url or ''))
    return '.'.join(m.group(1).lower().split('.')[-2:]) if m else ''


def env_with_key(text, key, value):
    """The .env text with ONE active `key=value` line: the first active line of that key is replaced (else appended) and every other
    active line of that key is commented out (the loader keeps the FIRST value — a stale line above the new one once won for hours)."""
    out, done = [], False
    for raw in str(text or '').split('\n'):
        if raw.strip().startswith(key + '='):
            out.append(raw if done is None else f'{key}={value}' if not done else '# ' + raw)
            done = True
        else:
            out.append(raw)
    if not done:
        out += [f'{key}={value}']
    return '\n'.join(out)


def set_lane(slot, url):
    """Swap a keeper lane in THIS process (lists are changed in place, so every importer sees it). Its quota / cooldown marks reset."""
    global _dedicated, _backup
    old = _dedicated if slot == 1 else _backup if slot == 2 else _more.get(slot, '')
    if slot == 1:
        _dedicated = url
    elif slot == 2:
        _backup = url
    else:
        _more[slot] = url
    lanes = [e for e in dict.fromkeys([_dedicated, _backup, *_more.values(), _alchemy_url]) if e]
    KEEPER_LANES[:] = lanes
    RPC_POOL[:] = lanes + [e for e in PUBLIC if e not in lanes]
    for e in (old, url):
        _quota_until.pop(e, None); _rpc_cooldown_until.pop(e, None)
    os.environ[LANE_KEYS[slot]] = url


async def probe(http, url):
    """Does this endpoint answer, and can it do the holder lookup the scanners need? → {ok, slot, holders, ms, err}"""
    t = time.time()
    try:
        r = await http.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'getSlot', 'params': []})
        body = r.json() if r.status_code == 200 else {}
        if r.status_code != 200 or 'result' not in body:
            spent = out_of_quota(r.status_code, r.text, r.headers)
            return {'ok': False, 'err': 'this key is out of quota' if spent else f'the endpoint refused the test call (HTTP {r.status_code})'}
        h = await http.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'getTokenLargestAccounts', 'params': ['DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263']})
        return {'ok': True, 'slot': body['result'], 'holders': h.status_code == 200 and 'result' in (h.json() or {}), 'ms': int((time.time() - t) * 1000)}
    except (httpx.HTTPError, ValueError):
        return {'ok': False, 'err': 'could not reach that endpoint'}
