"""Solana RPC: the endpoint pool and the retrying JSON-RPC client every FEELESS service uses.

A dedicated key (Helius / QuickNode / Alchemy / Triton) goes first via SOLANA_RPC_URL and takes almost all traffic; public endpoints
are fallback-only, so a rate-limited public node never blocks resolution. Each endpoint has its own failure budget — a bad node is
skipped for a cooldown window instead of failing every request that hits it.
"""
import os
import time
from typing import Optional

import env_loader  # noqa: F401  (must run before reading os.environ)
import httpx

_dedicated = os.environ.get('SOLANA_RPC_URL', '').strip()
_alchemy = os.environ.get('ALCHEMY_API_KEY', '').strip()
RPC_POOL = ([_dedicated] if _dedicated else []) + ([f'https://solana-mainnet.g.alchemy.com/v2/{_alchemy}'] if _alchemy else []) + [
    'https://api.mainnet-beta.solana.com',
    'https://solana-rpc.publicnode.com',
    'https://rpc.ankr.com/solana',
]
_rpc_cooldown_until: dict[str, float] = {}
RPC_COOLDOWN_SECONDS = 30
RPC_MAX_RETRIES = len(RPC_POOL)


def _next_rpc_endpoint() -> Optional[str]:
    """Priority order (dedicated key, then Alchemy, then public nodes), skipping any endpoint in its cooldown window.
    Public nodes are fallback-only: they lag and rate-limit, so balances read right after a trade came back stale."""
    now = time.time()
    for endpoint in RPC_POOL:
        if _rpc_cooldown_until.get(endpoint, 0) <= now:
            return endpoint
    return min(RPC_POOL, key=lambda e: _rpc_cooldown_until.get(e, 0)) if RPC_POOL else None


async def _rpc(http: httpx.AsyncClient, method: str, params: list):
    """Calls the RPC pool with retry + per-endpoint cooldown on failure or rate-limit."""
    last_error = None
    now = time.time()
    order = [e for e in RPC_POOL if _rpc_cooldown_until.get(e, 0) <= now] or ([_next_rpc_endpoint()] if RPC_POOL else [])
    for endpoint in order[:RPC_MAX_RETRIES]:
        try:
            res = await http.post(endpoint, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
            if res.status_code == 429:
                _rpc_cooldown_until[endpoint] = time.time() + RPC_COOLDOWN_SECONDS
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
    return sum(1 for ok in await asyncio.gather(*[one(e) for e in RPC_POOL]) if ok)


async def rpc_priority(http: httpx.AsyncClient, method: str, params: list, tries: int = 4):
    """💵 The KEEPER's lane. Real-money calls (balances, sends, confirmations) go to the dedicated endpoint FIRST and ignore the shared
    cooldown: the coin scanners burst past a plan's rate limit, which used to lock the keeper out of its own endpoint for 30s at a
    time ("RPC pool exhausted" on a balance read). A 429 here waits a moment and retries; only then does it fall back to the pool."""
    import asyncio
    if _dedicated:
        for attempt in range(tries):
            try:
                res = await http.post(_dedicated, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
            except httpx.HTTPError:
                break
            if res.status_code == 429:
                await asyncio.sleep(0.35 * (attempt + 1))
                continue
            if res.status_code != 200:
                break
            try:
                body = res.json()
            except ValueError:
                break
            if 'error' not in body:
                return body.get('result')
            break   # a real RPC error (bad params, simulation failed, …) is the caller's to see — the pool reports it the same way
    return await _rpc(http, method, params)
