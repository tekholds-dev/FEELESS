"""
FEELESS Reputation Graph — a standalone, chain-agnostic creator/wallet trust engine.

Every token observation the frontend already makes (from DexScreener/GeckoTerminal/
Pump.fun market data it fetches anyway) gets recorded here against the token's
on-chain creator identity. On Solana that identity is the mint authority, resolved
once per mint via public RPC and cached. The ledger persists to disk, so the dataset
— and the moat — compounds every day this service keeps running, independent of
which launchpad or chain happens to be the current meta.

This intentionally has zero dependency on the rest of the monorepo backend (no Mongo,
no provider API keys) so it can run standalone.
"""
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
STORE_PATH = DATA_DIR / 'reputation.json'

# RPC pool: a dedicated key (Helius/QuickNode/Alchemy/Triton) goes first via SOLANA_RPC_URL
# and takes almost all traffic; public endpoints are fallback-only so a rate-limited public
# node never blocks resolution. Each endpoint gets its own failure budget — one bad node
# gets skipped for a cooldown window instead of failing every request that hits it.
_dedicated = os.environ.get('SOLANA_RPC_URL', '').strip()
RPC_POOL = ([_dedicated] if _dedicated else []) + [
    'https://api.mainnet-beta.solana.com',
    'https://solana-rpc.publicnode.com',
    'https://rpc.ankr.com/solana',
]
_rpc_cooldown_until: dict[str, float] = {}
_rpc_cursor = 0
RPC_COOLDOWN_SECONDS = 30
RPC_MAX_RETRIES = len(RPC_POOL)

RUG_LIQUIDITY_DROP_PCT = 80          # % drop from peak liquidity counted as a rug signal
RUG_MIN_AGE_SECONDS = 60 * 30        # token must have existed >=30min to be eligible to be flagged
SUSTAINED_AGE_SECONDS = 60 * 60 * 24 * 3   # 3 days of surviving liquidity counts as "sustained"

_lock = asyncio.Lock()
_mint_authority_cache: dict[str, Optional[str]] = {}


def _empty_store():
    return {'creators': {}, 'mints': {}, 'watchlists': {}, 'feed': [], 'funding': {}}


def _load() -> dict:
    if STORE_PATH.exists():
        try:
            store = json.loads(STORE_PATH.read_text())
            store.setdefault('watchlists', {})
            store.setdefault('feed', [])
            store.setdefault('funding', {})
            return store
        except Exception:
            pass
    return _empty_store()


def _save(store: dict):
    STORE_PATH.write_text(json.dumps(store, indent=2))


def _next_rpc_endpoint() -> Optional[str]:
    """Round-robins the pool, skipping any endpoint still in its cooldown window."""
    global _rpc_cursor
    now = time.time()
    for _ in range(len(RPC_POOL)):
        endpoint = RPC_POOL[_rpc_cursor % len(RPC_POOL)]
        _rpc_cursor += 1
        if _rpc_cooldown_until.get(endpoint, 0) <= now:
            return endpoint
    return RPC_POOL[0] if RPC_POOL else None


async def _rpc(http: httpx.AsyncClient, method: str, params: list):
    """Calls the RPC pool with retry + per-endpoint cooldown on failure or rate-limit."""
    last_error = None
    for _ in range(RPC_MAX_RETRIES):
        endpoint = _next_rpc_endpoint()
        if not endpoint:
            break
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


async def resolve_creator(chain: str, mint_address: str) -> Optional[str]:
    """Resolve a Solana mint's deployer identity. Cached.

    Most pump.fun-style launches renounce mint authority immediately, so it's null
    for the vast majority of new coins and useless as an identity key. Instead we
    fall back to the fee payer of the mint's earliest known transaction — the
    standard on-chain proxy for "who deployed this" used by rug-detection tooling.
    """
    if chain != 'solana':
        return None
    if mint_address in _mint_authority_cache:
        return _mint_authority_cache[mint_address]
    identity = None
    renounced = False
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            info_result = await _rpc(http, 'getAccountInfo', [mint_address, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}])
            info = (((info_result or {}).get('value') or {}).get('data') or {}).get('parsed', {}).get('info', {})
            identity = info.get('mintAuthority')
            renounced = identity is None and info.get('isInitialized', True)

            if not identity:
                signatures = await _rpc(http, 'getSignaturesForAddress', [mint_address, {'limit': 1000}])
                if signatures:
                    oldest = signatures[-1].get('signature')
                    tx = await _rpc(http, 'getTransaction', [oldest, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}])
                    keys = (((tx or {}).get('transaction') or {}).get('message') or {}).get('accountKeys', [])
                    if keys:
                        identity = keys[0].get('pubkey') if isinstance(keys[0], dict) else keys[0]
    except Exception:
        identity = None
    result = {'identity': identity, 'renounced': renounced}
    _mint_authority_cache[mint_address] = result
    return result


def _creator_key(chain: str, address: str) -> str:
    return f'{chain}:{address}'


async def resolve_funding_source(chain: str, wallet_address: str) -> Optional[str]:
    """Resolves who funded a wallet's very first transaction — the standard on-chain
    signal real analytics tools (Arkham, Nansen-style) use to cluster wallets that
    look independent but are actually operated by the same person. If two "different"
    creator wallets were both funded from the same upstream wallet, that's a real,
    verifiable link — not a guess.
    """
    if chain != 'solana':
        return None
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            signatures = await _rpc(http, 'getSignaturesForAddress', [wallet_address, {'limit': 1000}])
            if not signatures:
                return None
            oldest = signatures[-1].get('signature')
            tx = await _rpc(http, 'getTransaction', [oldest, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}])
            keys = (((tx or {}).get('transaction') or {}).get('message') or {}).get('accountKeys', [])
            if not keys:
                return None
            fee_payer = keys[0].get('pubkey') if isinstance(keys[0], dict) else keys[0]
            # The fee payer of this wallet's first-ever transaction is the funding source,
            # unless this wallet WAS the fee payer (it funded itself / was the first mover).
            return fee_payer if fee_payer != wallet_address else None
    except Exception:
        return None


def _push_feed(store: dict, chain: str, address: str, kind: str, detail: str):
    store.setdefault('feed', []).insert(0, {
        'id': uuid.uuid4().hex, 'chain': chain, 'address': address,
        'type': kind, 'detail': detail, 'ts': time.time(),
    })
    store['feed'] = store['feed'][:500]


def score_creator(entry: dict) -> dict:
    tokens = entry.get('tokens', {})
    total = len(tokens)
    rugged = sum(1 for t in tokens.values() if t.get('status') == 'rugged')
    sustained = sum(1 for t in tokens.values() if t.get('status') == 'sustained')
    renounced = sum(1 for t in tokens.values() if t.get('authorityRenounced'))
    symbols = [(t.get('symbol') or '').strip().upper() for t in tokens.values()]
    distinct = len({s for s in symbols if s}) or (1 if total else 0)
    # Re-launching the same ticker over and over is spam/clone behavior, not a track record.
    clones = max(0, total - distinct)

    score = 50
    score += min(distinct, 10) * 3
    score += min(sustained, 6) * 8
    score += min(renounced, 6) * 2
    score -= min(clones, 6) * 6
    score -= min(rugged, 6) * 40
    score = max(0, min(100, score))

    if rugged > 0:
        badge = 'flagged'
    elif total == 0:
        badge = 'unproven'
    elif sustained > 0 or (distinct >= 3 and clones == 0):
        badge = 'trusted'
    else:
        badge = 'building'

    return {
        'score': score, 'badge': badge, 'tokenCount': total, 'distinctTickers': distinct, 'cloneCount': clones,
        'ruggedCount': rugged, 'sustainedCount': sustained, 'renouncedCount': renounced,
    }


class ObservePayload(BaseModel):
    chain: str
    pairAddress: str
    baseTokenAddress: str
    symbol: Optional[str] = None
    dexId: Optional[str] = None
    liquidityUsd: Optional[float] = None
    marketCap: Optional[float] = None
    pairCreatedAt: Optional[int] = None


app = FastAPI(title='FEELESS Reputation Graph')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


@app.post('/api/reputation/observe')
async def observe(payload: ObservePayload):
    async with _lock:
        store = _load()
        now = time.time()
        mint_key = f'{payload.chain}:{payload.baseTokenAddress}'
        mint_state = store['mints'].get(mint_key, {})
        if 'creator' not in mint_state:
            resolved = await resolve_creator(payload.chain, payload.baseTokenAddress)
            mint_state['creator'] = resolved['identity']
            mint_state['renounced'] = resolved['renounced']
            store['mints'][mint_key] = mint_state
        creator_address = mint_state.get('creator')
        authority_renounced = bool(mint_state.get('renounced'))

        if not creator_address:
            _save(store)
            return {'creator': None, 'reason': 'Creator identity unavailable for this chain or mint.', 'score': None}

        ckey = _creator_key(payload.chain, creator_address)
        creator_entry = store['creators'].setdefault(ckey, {
            'chain': payload.chain, 'address': creator_address,
            'firstSeen': now, 'lastSeen': now, 'tokens': {},
        })
        creator_entry['lastSeen'] = now

        is_new_token = payload.pairAddress not in creator_entry['tokens']
        token = creator_entry['tokens'].setdefault(payload.pairAddress, {
            'pairAddress': payload.pairAddress, 'baseTokenAddress': payload.baseTokenAddress,
            'symbol': payload.symbol, 'dexId': payload.dexId,
            'firstSeenAt': now, 'firstLiquidityUsd': payload.liquidityUsd,
            'peakLiquidityUsd': payload.liquidityUsd or 0, 'lastLiquidityUsd': payload.liquidityUsd,
            'lastCheckedAt': now, 'status': 'active', 'authorityRenounced': authority_renounced,
        })
        if is_new_token and len(creator_entry['tokens']) > 1:
            # Only worth notifying once this creator has a track record — the very first
            # token observed for a brand-new creator isn't "news," it's just onboarding.
            _push_feed(store, payload.chain, creator_address, 'new_token', f'Launched a new token: {payload.symbol or "unnamed"}.')
        token['lastCheckedAt'] = now
        token['symbol'] = payload.symbol or token.get('symbol')
        if payload.liquidityUsd is not None:
            token['lastLiquidityUsd'] = payload.liquidityUsd
            token['peakLiquidityUsd'] = max(token.get('peakLiquidityUsd') or 0, payload.liquidityUsd)

        age = now - token['firstSeenAt']
        peak = token.get('peakLiquidityUsd') or 0
        last = token.get('lastLiquidityUsd')
        if token['status'] == 'active' and age >= RUG_MIN_AGE_SECONDS and peak > 0 and last is not None:
            drop_pct = (1 - (last / peak)) * 100
            if drop_pct >= RUG_LIQUIDITY_DROP_PCT:
                token['status'] = 'rugged'
                token['ruggedAt'] = now
                _push_feed(store, payload.chain, creator_address, 'flagged', f'{token.get("symbol") or "A token"} lost {drop_pct:.0f}% of peak liquidity — flagged as rugged.')
        if token['status'] == 'active' and age >= SUSTAINED_AGE_SECONDS:
            token['status'] = 'sustained'

        scoring = score_creator(creator_entry)
        creator_entry['scoring'] = scoring
        _save(store)
        return {'creator': creator_address, **scoring}


@app.get('/api/reputation/token/{chain}/{address}')
async def token_reputation(chain: str, address: str):
    store = _load()
    mint_key = f'{chain}:{address}'
    mint_state = store['mints'].get(mint_key)
    if not mint_state or not mint_state.get('creator'):
        return {'creator': None, 'score': None, 'badge': 'unproven'}
    ckey = _creator_key(chain, mint_state['creator'])
    entry = store['creators'].get(ckey)
    if not entry:
        return {'creator': mint_state['creator'], 'score': None, 'badge': 'unproven'}
    return {'creator': entry['address'], **score_creator(entry)}



_market_cache: dict = {}
MARKET_TTL = 60


async def fetch_token_markets(chain: str, mints: list) -> dict:
    """Live market state per token mint from DexScreener's token endpoint (batched, 30 max).
    A mint with no pairs isn't listed on any DEX yet — for pump.fun that usually means it
    never left the bonding curve."""
    now = time.time()
    out, missing = {}, []
    for m in mints:
        hit = _market_cache.get(m)
        if hit and now - hit[0] < MARKET_TTL:
            out[m] = hit[1]
        else:
            missing.append(m)
    async with httpx.AsyncClient(timeout=8) as http:
        for i in range(0, len(missing), 30):
            batch = missing[i:i + 30]
            try:
                res = await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{",".join(batch)}')
                pairs = (res.json() or {}).get('pairs') or [] if res.status_code == 200 else None
            except Exception:
                pairs = None
            if pairs is None:
                continue
            best = {}
            for p in pairs:
                if p.get('chainId') != chain:
                    continue
                mint = (p.get('baseToken') or {}).get('address')
                liq = ((p.get('liquidity') or {}).get('usd')) or 0
                if mint in batch and (mint not in best or liq > (((best[mint].get('liquidity') or {}).get('usd')) or 0)):
                    best[mint] = p
            for mint in batch:
                p = best.get(mint)
                info = {'listed': False} if not p else {
                    'listed': True, 'url': p.get('url'), 'pairAddress': p.get('pairAddress'), 'dexId': p.get('dexId'),
                    'priceUsd': p.get('priceUsd'), 'marketCap': p.get('marketCap') or p.get('fdv'),
                    'liquidityUsd': (p.get('liquidity') or {}).get('usd'), 'volume24h': (p.get('volume') or {}).get('h24'),
                    'change24h': (p.get('priceChange') or {}).get('h24'), 'imageUrl': (p.get('info') or {}).get('imageUrl'),
                }
                _market_cache[mint] = (now, info)
                out[mint] = info
    return out


def trust_verdict(scoring: dict, tokens: list, linked: list) -> dict:
    """Plain-language verdict with every reason spelled out, so a user can see WHY."""
    reasons = []
    good = bad = 0
    if scoring['ruggedCount']:
        reasons.append(('bad', f"{scoring['ruggedCount']} token(s) lost 80%+ of peak liquidity after launch (confirmed rug pattern)."))
        bad += 3
    if scoring['cloneCount'] >= 2:
        reasons.append(('bad', f"Relaunched the same ticker {scoring['cloneCount']} extra times — clone/spam behavior."))
        bad += 2
    listed = [t for t in tokens if (t.get('market') or {}).get('listed')]
    known = [t for t in tokens if t.get('market') is not None]
    if known:
        dead = len(known) - len(listed)
        if dead and dead / len(known) >= 0.7 and len(known) >= 3:
            reasons.append(('bad', f"{dead} of {len(known)} launches never reached a DEX listing — most launches went nowhere."))
            bad += 1
        alive = [t for t in listed if ((t['market'].get('liquidityUsd') or 0) >= 10000)]
        if alive:
            reasons.append(('good', f"{len(alive)} launch(es) currently hold $10K+ liquidity on a DEX."))
            good += 1
    if scoring['sustainedCount']:
        reasons.append(('good', f"{scoring['sustainedCount']} token(s) survived 3+ days with liquidity intact."))
        good += 2
    if scoring['renouncedCount'] == scoring['tokenCount'] and scoring['tokenCount']:
        reasons.append(('neutral', 'Mint authority renounced on every launch (standard on pump.fun — not a trust signal on its own).'))
    flagged_links = [l for l in linked if l.get('ruggedCount') or l.get('cloneCount', 0) >= 2]
    if flagged_links:
        reasons.append(('bad', f"Shares a funding wallet with {len(flagged_links)} flagged/clone-farming wallet(s)."))
        bad += 2
    elif linked:
        reasons.append(('neutral', f"Shares a funding wallet with {len(linked)} other tracked creator(s) — likely one operator."))
    if scoring['tokenCount'] < 3 and not scoring['sustainedCount']:
        reasons.append(('neutral', 'Short history — not enough launches yet to judge reliably.'))
    if bad >= 3 or scoring['ruggedCount']:
        level, label = 'avoid', 'High risk — avoid'
    elif bad:
        level, label = 'caution', 'Caution'
    elif good >= 2:
        level, label = 'trusted', 'Looks trustworthy'
    else:
        level, label = 'unknown', 'Not enough evidence'
    return {'level': level, 'label': label, 'reasons': [{'tone': t, 'text': x} for t, x in reasons]}


@app.get('/api/reputation/creator/{chain}/{address}')
async def creator_profile(chain: str, address: str):
    store = _load()
    ckey = _creator_key(chain, address)
    entry = store['creators'].get(ckey)
    if not entry:
        raise HTTPException(404, 'No observations recorded for this creator yet.')

    wallet = {'solBalance': None, 'recentSignatures': []}
    if chain == 'solana':
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                balance_result = await _rpc(http, 'getBalance', [address, {'commitment': 'confirmed'}])
                if balance_result is not None:
                    wallet['solBalance'] = (balance_result.get('value') or 0) / 1_000_000_000
                signatures = await _rpc(http, 'getSignaturesForAddress', [address, {'limit': 8}])
                wallet['recentSignatures'] = [{
                    'signature': s.get('signature'), 'blockTime': s.get('blockTime'), 'err': s.get('err') is not None,
                } for s in (signatures or [])]
        except Exception:
            pass

    fkey = _creator_key(chain, address)
    async with _lock:
        store2 = _load()
        if fkey not in store2['funding']:
            store2['funding'][fkey] = await resolve_funding_source(chain, address)
            _save(store2)
        funding_source = store2['funding'][fkey]
    linked = []
    if funding_source:
        for other_ckey, other_entry in store2['creators'].items():
            if other_ckey == ckey:
                continue
            other_fkey = _creator_key(other_entry['chain'], other_entry['address'])
            if store2['funding'].get(other_fkey) == funding_source:
                linked.append({'address': other_entry['address'], 'chain': other_entry['chain'], **score_creator(other_entry)})

    tokens = sorted(entry['tokens'].values(), key=lambda t: -(t.get('firstSeenAt') or 0))
    mints = [t['baseTokenAddress'] for t in tokens if t.get('baseTokenAddress')]
    markets = await fetch_token_markets(chain, mints) if mints else {}
    enriched = [{**t, 'market': markets.get(t.get('baseTokenAddress'))} for t in tokens]
    scoring = score_creator(entry)
    return {**entry, 'tokens': {t['pairAddress']: t for t in enriched}, 'tokenList': enriched, 'scoring': scoring,
            'verdict': trust_verdict(scoring, enriched, linked),
            'wallet': wallet, 'fundingSource': funding_source, 'linkedWallets': linked}


LEADERBOARD_VIEWS = ('trusted', 'flagged', 'serial', 'rising', 'active')
RISING_WINDOW_SECONDS = 60 * 60 * 24 * 2   # first observed within the last 2 days


@app.get('/api/reputation/leaderboard')
async def leaderboard(chain: Optional[str] = Query(None), view: str = Query('trusted')):
    if view not in LEADERBOARD_VIEWS:
        view = 'trusted'
    store = _load()
    now = time.time()
    rows = []
    for entry in store['creators'].values():
        if chain and entry['chain'] != chain:
            continue
        scoring = score_creator(entry)
        rows.append({
            'chain': entry['chain'], 'address': entry['address'],
            'firstSeen': entry['firstSeen'], 'lastSeen': entry['lastSeen'],
            **scoring,
        })

    if view == 'flagged':
        rows = [r for r in rows if r['ruggedCount'] > 0]
        rows.sort(key=lambda r: (-r['ruggedCount'], -r['tokenCount']))
    elif view == 'serial':
        # Highest launch volume, regardless of outcome — the wallets flooding the market.
        rows = [r for r in rows if r['tokenCount'] >= 2]
        rows.sort(key=lambda r: (-r['tokenCount'], -r['ruggedCount']))
    elif view == 'rising':
        # New creators (first seen recently) already showing a clean, decent score.
        rows = [r for r in rows if r['ruggedCount'] == 0 and (now - r['firstSeen']) <= RISING_WINDOW_SECONDS]
        rows.sort(key=lambda r: (-r['score'], r['firstSeen']))
    elif view == 'active':
        rows = [r for r in rows if r['ruggedCount'] == 0]
        rows.sort(key=lambda r: -r['lastSeen'])
    else:
        rows = [r for r in rows if r['ruggedCount'] == 0]
        rows.sort(key=lambda r: (-r['score'], -r['tokenCount']))

    return {
        'rows': rows[:50], 'view': view,
        'totalCreators': len(store['creators']),
        'totalTokensTracked': sum(len(e['tokens']) for e in store['creators'].values()),
    }


class WatchPayload(BaseModel):
    ownerWallet: str
    chain: str
    address: str
    notifyNewToken: bool = True
    notifyFlag: bool = True
    botEnabled: bool = False
    botBrain: Optional[str] = None


@app.post('/api/reputation/watch')
async def watch_creator(payload: WatchPayload):
    async with _lock:
        store = _load()
        bucket = store['watchlists'].setdefault(payload.ownerWallet, {})
        wkey = _creator_key(payload.chain, payload.address)
        existing = bucket.get(wkey, {})
        bucket[wkey] = {
            'chain': payload.chain, 'address': payload.address,
            'notifyNewToken': payload.notifyNewToken, 'notifyFlag': payload.notifyFlag,
            'botEnabled': payload.botEnabled, 'botBrain': payload.botBrain,
            'addedAt': existing.get('addedAt', time.time()),
        }
        _save(store)
        return {'ok': True, 'watch': bucket[wkey]}


class UnwatchPayload(BaseModel):
    ownerWallet: str
    chain: str
    address: str


@app.post('/api/reputation/unwatch')
async def unwatch_creator(payload: UnwatchPayload):
    async with _lock:
        store = _load()
        bucket = store['watchlists'].get(payload.ownerWallet, {})
        bucket.pop(_creator_key(payload.chain, payload.address), None)
        _save(store)
        return {'ok': True}


@app.get('/api/reputation/watchlist')
async def get_watchlist(ownerWallet: str):
    store = _load()
    bucket = store['watchlists'].get(ownerWallet, {})
    rows = []
    for watch in bucket.values():
        ckey = _creator_key(watch['chain'], watch['address'])
        entry = store['creators'].get(ckey)
        scoring = score_creator(entry) if entry else {'score': None, 'badge': 'unproven', 'tokenCount': 0, 'ruggedCount': 0, 'sustainedCount': 0, 'renouncedCount': 0}
        rows.append({**watch, **scoring})
    rows.sort(key=lambda r: -r['addedAt'])
    return {'rows': rows}


@app.get('/api/reputation/watchlist/feed')
async def get_watchlist_feed(ownerWallet: str, limit: int = Query(50, le=200)):
    store = _load()
    bucket = store['watchlists'].get(ownerWallet, {})
    if not bucket:
        return {'events': []}
    events = []
    for event in store.get('feed', []):
        wkey = _creator_key(event['chain'], event['address'])
        watch = bucket.get(wkey)
        if not watch:
            continue
        if event['type'] == 'new_token' and not watch.get('notifyNewToken', True):
            continue
        if event['type'] == 'flagged' and not watch.get('notifyFlag', True):
            continue
        events.append(event)
        if len(events) >= limit:
            break
    return {'events': events}


CLUSTER_RESOLVE_BATCH = 8   # cap RPC calls per request so this stays fast


@app.get('/api/reputation/clusters')
async def get_clusters(chain: Optional[str] = Query('solana')):
    """Groups tracked creators by shared on-chain funding source. A cluster of 2+
    creator wallets funded by the same upstream wallet is a real signal that they're
    the same operator running multiple "clean" identities — this is the analysis no
    other launchpad terminal surfaces."""
    async with _lock:
        store = _load()
        creators = [e for e in store['creators'].values() if not chain or e['chain'] == chain]
        resolved_this_call = 0
        for entry in creators:
            fkey = _creator_key(entry['chain'], entry['address'])
            if fkey not in store['funding']:
                if resolved_this_call >= CLUSTER_RESOLVE_BATCH:
                    continue
                store['funding'][fkey] = await resolve_funding_source(entry['chain'], entry['address'])
                resolved_this_call += 1
        if resolved_this_call:
            _save(store)

        groups: dict[str, list] = {}
        for entry in creators:
            fkey = _creator_key(entry['chain'], entry['address'])
            source = store['funding'].get(fkey)
            if not source:
                continue
            groups.setdefault(source, []).append(entry)

        clusters = []
        for source, members in groups.items():
            if len(members) < 2:
                continue
            scored = [{'address': m['address'], 'chain': m['chain'], **score_creator(m)} for m in members]
            clusters.append({
                'fundingSource': source,
                'members': sorted(scored, key=lambda r: -r['score']),
                'totalTokens': sum(m['tokenCount'] for m in scored),
                'totalFlags': sum(m['ruggedCount'] for m in scored),
            })
        clusters.sort(key=lambda c: (-c['totalFlags'], -len(c['members'])))

    pending = sum(1 for e in creators if _creator_key(e['chain'], e['address']) not in store['funding'])
    return {'clusters': clusters, 'creatorsScanned': len(creators), 'pendingResolution': pending}


@app.get('/api/reputation/feed')
async def global_feed(limit: int = Query(40, ge=1, le=200)):
    """Site-wide trust signals: known creators launching again, and fresh rug flags."""
    store = _load()
    events = []
    for ev in store.get('feed', [])[:limit]:
        entry = store['creators'].get(_creator_key(ev['chain'], ev['address']))
        events.append({**ev, **(score_creator(entry) if entry else {})})
    return {'events': events}


@app.get('/api/reputation/case-studies')
async def case_studies(limit: int = Query(6, ge=1, le=20)):
    """Real flagged creators with the tokens that collapsed — teaching material from live data."""
    store = _load()
    cases = []
    for entry in store['creators'].values():
        rugged = [t for t in entry['tokens'].values() if t.get('status') == 'rugged']
        scoring = score_creator(entry)
        if not rugged and scoring['cloneCount'] < 3:
            continue
        cases.append({
            'chain': entry['chain'], 'address': entry['address'], **scoring,
            'kind': 'rug' if rugged else 'clone-farm',
            'tickers': sorted({(t.get('symbol') or '?') for t in entry['tokens'].values()}),
            'rugged': [{'symbol': t.get('symbol'), 'pairAddress': t['pairAddress'], 'peakLiquidityUsd': t.get('peakLiquidityUsd'),
                        'lastLiquidityUsd': t.get('lastLiquidityUsd'), 'firstSeenAt': t.get('firstSeenAt'), 'lastCheckedAt': t.get('lastCheckedAt')} for t in rugged],
        })
    cases.sort(key=lambda c: (-c['ruggedCount'], -c['cloneCount'], -c['tokenCount']))
    return {'cases': cases[:limit], 'total': len(cases)}


class VotePayload(BaseModel):
    wallet: str
    itemId: str


@app.get('/api/reputation/roadmap/votes')
async def roadmap_votes(wallet: Optional[str] = None):
    store = _load()
    votes = store.setdefault('votes', {})
    return {'counts': {k: len(v) for k, v in votes.items()}, 'mine': [k for k, v in votes.items() if wallet and wallet in v]}


@app.post('/api/reputation/roadmap/vote')
async def roadmap_vote(payload: VotePayload):
    if len(payload.wallet) < 20 or len(payload.itemId) > 64:
        raise HTTPException(400, 'Invalid vote.')
    async with _lock:
        store = _load()
        voters = store.setdefault('votes', {}).setdefault(payload.itemId, [])
        if payload.wallet in voters:
            voters.remove(payload.wallet)
        else:
            voters.append(payload.wallet)
        _save(store)
        return {'itemId': payload.itemId, 'count': len(voters), 'voted': payload.wallet in voters}


@app.get('/api/reputation/health')
async def health():
    store = _load()
    now = time.time()
    rpc_status = [{
        'endpoint': endpoint, 'dedicated': endpoint == _dedicated,
        'cooling_down': _rpc_cooldown_until.get(endpoint, 0) > now,
    } for endpoint in RPC_POOL]
    return {
        'ok': True, 'creators': len(store['creators']), 'mints': len(store['mints']),
        'rpcPool': rpc_status, 'usingDedicatedRpc': bool(_dedicated),
    }
