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
import env_loader  # noqa: F401  (must run before reading os.environ)
import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
import gecko_budget
from fastapi import FastAPI, HTTPException, Query, Request
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
        key = f'{chain}:{mint_address}'
        if key not in _mint_authority_cache:
            creator = await resolve_evm_creator(chain, mint_address)
            _mint_authority_cache[key] = {'identity': creator, 'renounced': False} if creator else None
        return _mint_authority_cache[key]
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


DUMP_MIN_AGE = 2 * 3600


def token_outcome(t: dict, now: float = None) -> str:
    """Outcome from live market snapshots: 'dumped', 'dead', or 'alive'. Pump.fun curve coins
    have no liquidity figure, so market-cap collapse is the reliable signal there."""
    now = now or time.time()
    if t.get('status') == 'rugged':
        return 'dumped'
    m = t.get('market') or {}
    age = now - (t.get('firstSeenAt') or now)
    if not m.get('checkedAt'):
        return 'unknown'
    if not m.get('listed'):
        return 'dead' if age > 24 * 3600 else 'unknown'
    mc, peak, ch = m.get('marketCap') or 0, m.get('peakMarketCap') or 0, m.get('change24h')
    if age >= DUMP_MIN_AGE and ((peak > 0 and mc <= peak * 0.3) or (ch is not None and ch <= -70) or (mc and mc < 2000 and age > 6 * 3600)):
        return 'dumped'
    return 'alive'


def score_creator(entry: dict) -> dict:
    tokens = entry.get('tokens', {})
    total = len(tokens)
    rugged = sum(1 for t in tokens.values() if t.get('status') == 'rugged')
    sustained = sum(1 for t in tokens.values() if t.get('status') == 'sustained')
    renounced = sum(1 for t in tokens.values() if t.get('authorityRenounced'))
    symbols = [(t.get('symbol') or '').strip().upper() for t in tokens.values()]
    distinct = len({s for s in symbols if s}) or (1 if total else 0)
    clones = max(0, total - distinct)
    now = time.time()
    outcomes = [token_outcome(t, now) for t in tokens.values()]
    dumped = outcomes.count('dumped')
    dead = outcomes.count('dead')
    judged = sum(1 for o in outcomes if o != 'unknown')
    alive_big = sum(1 for t in tokens.values() if token_outcome(t, now) == 'alive' and ((t.get('market') or {}).get('marketCap') or 0) >= 100_000)

    score = 50
    score += min(distinct, 10) * 3
    score += min(sustained, 6) * 8
    score += min(alive_big, 5) * 6
    score += min(renounced, 6) * 1
    score -= min(clones, 6) * 6
    score -= min(dumped, 8) * 12
    score -= min(dead, 6) * 4
    score -= min(rugged, 6) * 40
    score = max(0, min(100, score))

    serial_dumper = dumped >= 3 and judged and dumped / judged >= 0.5
    if rugged > 0 or serial_dumper:
        badge = 'flagged'
    elif total == 0:
        badge = 'unproven'
    elif dumped == 0 and clones == 0 and (sustained > 0 or alive_big > 0 or (distinct >= 3 and judged >= 3 and dead == 0)):
        badge = 'trusted'
    else:
        badge = 'building'

    return {
        'score': score, 'badge': badge, 'tokenCount': total, 'distinctTickers': distinct, 'cloneCount': clones,
        'ruggedCount': rugged, 'dumpedCount': dumped, 'deadCount': dead, 'judgedCount': judged, 'bigWinners': alive_big,
        'serialDumper': bool(serial_dumper), 'sustainedCount': sustained, 'renouncedCount': renounced,
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
    if scoring.get('serialDumper'):
        reasons.append(('bad', f"Serial dumper: {scoring['dumpedCount']} of {scoring['judgedCount']} launches collapsed 70%+ from their peak or died under $2K market cap."))
        bad += 4
    elif scoring.get('dumpedCount'):
        reasons.append(('bad', f"{scoring['dumpedCount']} launch(es) collapsed 70%+ after launch."))
        bad += 1 + scoring['dumpedCount']
    if scoring.get('bigWinners'):
        reasons.append(('good', f"{scoring['bigWinners']} launch(es) are alive above $100K market cap right now."))
        good += 2
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
    if bad >= 3 or scoring['ruggedCount'] or scoring.get('serialDumper'):
        level, label = 'avoid', 'High risk — avoid'
    elif bad:
        level, label = 'caution', 'Caution'
    elif good >= 2:
        level, label = 'trusted', 'Looks trustworthy'
    else:
        level, label = 'unknown', 'Not enough evidence'
    return {'level': level, 'label': label, 'reasons': [{'tone': t, 'text': x} for t, x in reasons]}


def _apply_markets(entry: dict, markets: dict):
    now = time.time()
    for t in entry.get('tokens', {}).values():
        info = markets.get(t.get('baseTokenAddress'))
        if info is None:
            continue
        prev = t.get('market') or {}
        mc = info.get('marketCap') or 0
        t['market'] = {**info, 'checkedAt': now, 'peakMarketCap': max(prev.get('peakMarketCap') or 0, mc)}


async def _refresh_all_markets():
    """Background: keep every tracked launch's market outcome fresh so scores reflect reality."""
    while True:
        try:
            store = _load()
            by_chain = {}
            for entry in store['creators'].values():
                for t in entry['tokens'].values():
                    if t.get('baseTokenAddress'):
                        by_chain.setdefault(entry['chain'], []).append(t['baseTokenAddress'])
            for chain, mints in by_chain.items():
                for i in range(0, len(mints), 300):
                    markets = await fetch_token_markets(chain, mints[i:i + 300])
                    async with _lock:
                        st = _load()
                        for entry in st['creators'].values():
                            if entry['chain'] == chain:
                                _apply_markets(entry, markets)
                        _save(st)
                    await asyncio.sleep(2)
        except Exception:
            pass
        await asyncio.sleep(300)


@app.on_event('startup')
async def _start_background():
    asyncio.create_task(_refresh_all_markets())


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
    async with _lock:
        store3 = _load()
        live = store3['creators'].get(ckey) or entry
        _apply_markets(live, markets)
        _save(store3)
        entry = live
    tokens = sorted(entry['tokens'].values(), key=lambda t: -(t.get('firstSeenAt') or 0))
    enriched = [{**t, 'outcome': token_outcome(t)} for t in tokens]
    scoring = score_creator(entry)
    return {**entry, 'tokens': {t['pairAddress']: t for t in enriched}, 'tokenList': enriched, 'scoring': scoring,
            'verdict': trust_verdict(scoring, enriched, linked),
            'feelessLaunches': [l for l in (_load().get('feelessLaunches') or {}).values() if l['wallet'] == address],
            'wallet': wallet, 'fundingSource': funding_source, 'linkedWallets': linked}


LEADERBOARD_VIEWS = ('trusted', 'flagged', 'serial', 'rising', 'active', 'feeless')
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

    if view == 'feeless':
        launches = store.get('feelessLaunches', {})
        by_creator = {}
        for l in launches.values():
            by_creator.setdefault(_creator_key(l['chain'], l['wallet']), []).append(l)
        rows = [{**r, 'feelessLaunches': len(by_creator[_creator_key(r['chain'], r['address'])])} for r in rows if _creator_key(r['chain'], r['address']) in by_creator]
        rows.sort(key=lambda r: (-r['bigWinners'], r['dumpedCount'], -r['score']))
    elif view == 'flagged':
        rows = [r for r in rows if r['badge'] == 'flagged' or r['dumpedCount'] >= 2]
        rows.sort(key=lambda r: (-r['ruggedCount'], -r['dumpedCount'], -r['tokenCount']))
    elif view == 'serial':
        # Highest launch volume, regardless of outcome — the wallets flooding the market.
        rows = [r for r in rows if r['tokenCount'] >= 2]
        rows.sort(key=lambda r: (-r['tokenCount'], -r['ruggedCount']))
    elif view == 'rising':
        # New creators (first seen recently) already showing a clean, decent score.
        rows = [r for r in rows if r['badge'] != 'flagged' and r['dumpedCount'] == 0 and (now - r['firstSeen']) <= RISING_WINDOW_SECONDS]
        rows.sort(key=lambda r: (-r['score'], r['firstSeen']))
    elif view == 'active':
        rows = [r for r in rows if r['badge'] != 'flagged']
        rows.sort(key=lambda r: -r['lastSeen'])
    else:
        rows = [r for r in rows if r['badge'] != 'flagged' and r['dumpedCount'] == 0]
        rows.sort(key=lambda r: (r['badge'] != 'trusted', -r['score'], -r['tokenCount']))

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
        if not rugged and scoring['cloneCount'] < 3 and not scoring.get('serialDumper'):
            continue
        cases.append({
            'chain': entry['chain'], 'address': entry['address'], **scoring,
            'kind': 'rug' if rugged else 'dumper' if scoring.get('serialDumper') else 'clone-farm',
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


UPLOAD_DIR = DATA_DIR / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_TYPES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif'}


class UploadPayload(BaseModel):
    dataUrl: str


@app.post('/api/reputation/uploads')
async def upload_image(payload: UploadPayload):
    """Token images for launches. Browser resizes first; we only accept small real images."""
    import base64
    import re
    m = re.match(r'^data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/=]+)$', payload.dataUrl or '')
    if not m:
        raise HTTPException(400, 'Only PNG, JPG, WEBP or GIF images are supported.')
    raw = base64.b64decode(m.group(2))
    if len(raw) > 2_000_000:
        raise HTTPException(413, 'Image must be under 2 MB.')
    sig = raw[:12]
    if not (sig.startswith(b'\x89PNG') or sig.startswith(b'\xff\xd8') or sig[:4] == b'RIFF' or sig[:3] == b'GIF'):
        raise HTTPException(400, 'File is not a valid image.')
    name = f"{uuid.uuid4().hex}.{UPLOAD_TYPES[m.group(1)]}"
    (UPLOAD_DIR / name).write_bytes(raw)
    return {'url': f'/api/reputation/uploads/{name}'}


@app.get('/api/reputation/uploads/{name}')
async def get_upload(name: str):
    from fastapi.responses import FileResponse
    import re
    if not re.match(r'^[a-f0-9]{32}\.(png|jpg|webp|gif)$', name):
        raise HTTPException(404, 'Not found')
    path = UPLOAD_DIR / name
    if not path.exists():
        raise HTTPException(404, 'Not found')
    return FileResponse(path, headers={'Cache-Control': 'public, max-age=31536000, immutable'})


_intel_cache: dict = {}
INTEL_TTL = 180
SYSTEM_PROGRAM = '11111111111111111111111111111111'


@app.get('/api/reputation/intel/{chain}/{mint}')
async def token_intel(chain: str, mint: str):
    """On-chain launch forensics for a token: bundles, snipers, holder concentration, dev bag.
    Bundled = distinct wallets (not the creator) buying in the mint's creation slot.
    Snipers  = distinct wallets buying within the next 3 slots (~1.2s)."""
    if chain != 'solana':
        raise HTTPException(400, 'On-chain forensics currently cover Solana.')
    hit = _intel_cache.get(mint)
    if hit and time.time() - hit[0] < INTEL_TTL:
        return hit[1]
    out = {'mint': mint, 'checkedAt': time.time()}
    async with httpx.AsyncClient(timeout=12) as http:
        supply_res, largest = await asyncio.gather(
            _rpc(http, 'getTokenSupply', [mint]), _rpc(http, 'getTokenLargestAccounts', [mint]), return_exceptions=True)
        supply = float(((supply_res or {}).get('value') or {}).get('uiAmount') or 0) if isinstance(supply_res, dict) else 0
        holders = ((largest or {}).get('value') or []) if isinstance(largest, dict) else []
        owners = {}
        if holders:
            accs = await _rpc(http, 'getMultipleAccounts', [[h['address'] for h in holders], {'encoding': 'jsonParsed'}])
            for h, a in zip(holders, (accs or {}).get('value') or []):
                info = (((a or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
                owners[h['address']] = info.get('owner')
            owner_list = [o for o in owners.values() if o]
            kinds = {}
            if owner_list:
                oaccs = await _rpc(http, 'getMultipleAccounts', [owner_list, {'encoding': 'base64'}])
                for o, a in zip(owner_list, (oaccs or {}).get('value') or []):
                    # Wallets are system-owned (or don't exist yet); pools/curves are program-owned PDAs.
                    kinds[o] = 'wallet' if (a is None or a.get('owner') == SYSTEM_PROGRAM) else 'program'
        rows = []
        for h in holders:
            owner = owners.get(h['address'])
            amt = float(h.get('uiAmount') or 0)
            rows.append({'owner': owner, 'amount': amt, 'pct': (amt / supply * 100) if supply else None,
                         'kind': kinds.get(owner, 'wallet') if owner else 'unknown'})
        wallets = [r for r in rows if r['kind'] == 'wallet']
        out['supply'] = supply
        out['topHolders'] = rows[:12]
        out['top10Pct'] = round(sum(r['pct'] or 0 for r in wallets[:10]), 2) if supply else None
        out['poolPct'] = round(sum(r['pct'] or 0 for r in rows if r['kind'] == 'program'), 2) if supply else None

        sigs = await _rpc(http, 'getSignaturesForAddress', [mint, {'limit': 1000}]) or []
        creator, bundled, snipers = None, set(), set()
        if sigs:
            oldest = sorted(sigs, key=lambda x: (x.get('slot') or 0))[:40]
            create_slot = oldest[0].get('slot')
            early = [x for x in oldest if (x.get('slot') or 0) <= create_slot + 3 and not x.get('err')][:25]
            sem = asyncio.Semaphore(6)

            async def fetch(sig):
                async with sem:
                    try:
                        return await _rpc(http, 'getTransaction', [sig['signature'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}])
                    except Exception:
                        return None
            txs = await asyncio.gather(*(fetch(x) for x in early))
            for tx in sorted([t for t in txs if t], key=lambda t: t.get('slot') or 0):
                keys = ((tx.get('transaction') or {}).get('message') or {}).get('accountKeys') or []
                payer = keys[0].get('pubkey') if keys and isinstance(keys[0], dict) else (keys[0] if keys else None)
                if not payer:
                    continue
                if creator is None:
                    creator = payer
                    continue
                if payer == creator:
                    continue
                (bundled if tx.get('slot') == create_slot else snipers).add(payer)
            snipers -= bundled
            out['createSlot'] = create_slot
            out['historyComplete'] = len(sigs) < 1000
        out['creator'] = creator
        out['bundledWallets'] = sorted(bundled)
        out['sniperWallets'] = sorted(snipers)
        insiders = bundled | snipers
        out['insidersHoldingPct'] = round(sum(r['pct'] or 0 for r in wallets if r['owner'] in insiders), 2) if supply else None
        out['devHoldingPct'] = round(sum(r['pct'] or 0 for r in wallets if r['owner'] == creator), 2) if supply and creator else None
    flags = []
    if len(out['bundledWallets']) >= 3:
        flags.append(f"{len(out['bundledWallets'])} wallets bought in the same block as the mint — a bundled launch.")
    if len(out['sniperWallets']) >= 5:
        flags.append(f"{len(out['sniperWallets'])} wallets sniped within ~1 second of launch.")
    if (out.get('insidersHoldingPct') or 0) >= 10:
        flags.append(f"Bundlers/snipers still hold {out['insidersHoldingPct']}% of supply among the top holders.")
    if (out.get('top10Pct') or 0) >= 35:
        flags.append(f"Top 10 wallets hold {out['top10Pct']}% of supply (excluding pools).")
    if (out.get('devHoldingPct') or 0) >= 5:
        flags.append(f"Creator still holds {out['devHoldingPct']}% of supply.")
    out['flags'] = flags
    await _record_offenders(mint, out.get('bundledWallets', []), out.get('sniperWallets', []))
    bl = _block_load()
    out['walletRecords'] = {w: {'strikes': len(bl['wallets'].get(w, {}).get('mints', {})), 'blocked': _is_blocked(bl['wallets'].get(w))}
                            for w in out.get('bundledWallets', []) + out.get('sniperWallets', [])}
    _intel_cache[mint] = (time.time(), out)
    return out


# ---- Multi-network RPC layer ------------------------------------------------
# Public defaults work out of the box; set <CHAIN>_RPC_URL in backend/.env to use a
# dedicated provider (Alchemy/QuickNode/Infura) for higher limits.
CHAIN_RPC_DEFAULTS = {
    'ethereum': 'https://ethereum-rpc.publicnode.com', 'base': 'https://base-rpc.publicnode.com',
    'bsc': 'https://bsc-rpc.publicnode.com', 'arbitrum': 'https://arbitrum-one-rpc.publicnode.com',
    'avalanche': 'https://avalanche-c-chain-rpc.publicnode.com', 'polygon': 'https://polygon-bor-rpc.publicnode.com',
    'sui': 'https://sui-rpc.publicnode.com',
}
EVM_CHAIN_IDS = {'ethereum': 1, 'base': 8453, 'bsc': 56, 'arbitrum': 42161, 'avalanche': 43114, 'polygon': 137}


def chain_rpc_url(chain: str) -> Optional[str]:
    if chain == 'solana':
        return RPC_POOL[0] if RPC_POOL else None
    return os.environ.get(f'{chain.upper()}_RPC_URL') or CHAIN_RPC_DEFAULTS.get(chain)


async def _ping_chain(http, chain):
    url = chain_rpc_url(chain)
    if not url:
        return {'chain': chain, 'ok': False, 'error': 'no endpoint'}
    method = 'getSlot' if chain == 'solana' else 'sui_getLatestCheckpointSequenceNumber' if chain == 'sui' else 'eth_blockNumber'
    started = time.time()
    try:
        r = await http.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': []})
        body = r.json()
        result = body.get('result')
        head = int(result, 16) if isinstance(result, str) and result.startswith('0x') else int(result) if result is not None else None
        return {'chain': chain, 'ok': head is not None, 'head': head, 'latencyMs': round((time.time() - started) * 1000),
                'dedicated': bool(os.environ.get('SOLANA_RPC_URL' if chain == 'solana' else f'{chain.upper()}_RPC_URL')),
                'host': url.split('/')[2].split('?')[0]}
    except Exception as exc:
        return {'chain': chain, 'ok': False, 'error': type(exc).__name__, 'host': url.split('/')[2].split('?')[0]}


@app.get('/api/reputation/rpc/health')
async def rpc_health():
    async with httpx.AsyncClient(timeout=6) as http:
        rows = await asyncio.gather(*(_ping_chain(http, c) for c in ['solana', *CHAIN_RPC_DEFAULTS]))
    return {'chains': rows, 'explorerKey': bool(os.environ.get('ETHERSCAN_API_KEY'))}


async def resolve_evm_creator(chain: str, token: str) -> Optional[str]:
    """Contract deployer via Etherscan API v2 (one key covers every EVM chain we support)."""
    key = os.environ.get('ETHERSCAN_API_KEY')
    cid = EVM_CHAIN_IDS.get(chain)
    if not key or not cid:
        return None
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.get('https://api.etherscan.io/v2/api', params={'chainid': cid, 'module': 'contract', 'action': 'getcontractcreation', 'contractaddresses': token, 'apikey': key})
            rows = (r.json() or {}).get('result') or []
            return rows[0].get('contractCreator') if isinstance(rows, list) and rows else None
    except Exception:
        return None


GLOBE_NETS = {'solana': 'solana', 'ethereum': 'eth', 'base': 'base', 'bsc': 'bsc', 'arbitrum': 'arbitrum', 'avalanche': 'avax', 'polygon': 'polygon_pos', 'sui': 'sui-network'}
GLOBE_MIN_MC = 10_000_000
_globe_cache = {'at': 0, 'data': None}


GLOBE_SKIP = {'USDT', 'USDC', 'USDC.E', 'USDBC', 'DAI', 'USDE', 'USDS', 'FDUSD', 'PYUSD', 'USD1', 'TUSD', 'BUSD', 'USDD', 'FRAX', 'LUSD',
              'WETH', 'WSOL', 'SOL', 'ETH', 'WBNB', 'BNB', 'WBTC', 'CBBTC', 'BTCB', 'WAVAX', 'AVAX', 'WMATIC', 'WPOL', 'POL', 'SUI', 'STETH', 'WSTETH', 'CBETH', 'RETH', 'WEETH'}


def _globe_row(chain, pool, images):
    a = pool.get('attributes') or {}
    base_id = (((pool.get('relationships') or {}).get('base_token') or {}).get('data') or {}).get('id')
    bt = images.get(base_id, {})
    symbol = (bt.get('symbol') or (a.get('name') or '?').split(' / ')[0]).strip()
    if symbol.upper() in GLOBE_SKIP or symbol.upper().startswith('USD') or symbol.upper().endswith('USD'):
        return None
    def f(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
    mc, fdv, liq = f(a.get('market_cap_usd')), f(a.get('fdv_usd')), f(a.get('reserve_in_usd'))
    if GLOBE_MIN_MC <= mc <= 5e12:
        value, kind = mc, 'market cap'
    elif GLOBE_MIN_MC <= fdv <= 1e11 and liq >= 200_000 and fdv <= liq * 500:
        value, kind = fdv, 'FDV'
    else:
        return None
    return {
        'chain': chain, 'address': bt.get('address') or (base_id or '').split('_', 1)[-1], 'symbol': symbol, 'name': bt.get('name'),
        'imageUrl': bt.get('image_url') if (bt.get('image_url') or '').startswith('http') else None,
        'marketCap': value, 'mcKind': kind, 'liquidityUsd': liq, 'priceUsd': a.get('base_token_price_usd'),
        'change24h': (a.get('price_change_percentage') or {}).get('h24'), 'volume24h': f((a.get('volume_usd') or {}).get('h24')),
        'pairAddress': a.get('address'),
    }


async def _refresh_globe():
    await asyncio.sleep(120)  # let charts claim GeckoTerminal first after a restart
    while True:
        tokens, ok_chains = {}, set()
        async with httpx.AsyncClient(timeout=12, headers={'accept': 'application/json'}) as http:
            for chain, net in GLOBE_NETS.items():
                for path in (f'/networks/{net}/pools?sort=h24_volume_usd_desc&include=base_token', f'/networks/{net}/trending_pools?include=base_token'):
                    r = None
                    for _ in range(2):
                        if not gecko_budget.take('globe'):
                            await asyncio.sleep(20)
                            continue
                        try:
                            r = await http.get(f'https://api.geckoterminal.com/api/v2{path}')
                            if r.status_code == 429:
                                gecko_budget.throttled()
                        except Exception:
                            r = None
                        if r is not None and r.status_code == 200:
                            break
                        await asyncio.sleep(8)
                    await asyncio.sleep(2.5)
                    if r is None or r.status_code != 200:
                        continue
                    ok_chains.add(chain)
                    body = r.json()
                    images = {i['id']: (i.get('attributes') or {}) for i in body.get('included') or []}
                    for pool in body.get('data') or []:
                        row = _globe_row(chain, pool, images)
                        if row:
                            key = f"{chain}:{row['address']}"
                            if key not in tokens or tokens[key]['volume24h'] < row['volume24h']:
                                tokens[key] = row
        if tokens:
            prev = (_globe_cache['data'] or {}).get('tokens') or []
            kept = [t for t in prev if t['chain'] not in ok_chains]
            _globe_cache.update(at=time.time(), data={'tokens': sorted(list(tokens.values()) + kept, key=lambda t: -t['marketCap']),
                                                      'minMarketCap': GLOBE_MIN_MC, 'source': 'GeckoTerminal top-volume + trending pools',
                                                      'chains': sorted(ok_chains | {t['chain'] for t in kept}), 'at': time.time()})
        await asyncio.sleep(900)


@app.on_event('startup')
async def _start_globe():
    asyncio.create_task(_refresh_globe())


@app.get('/api/reputation/globe-tokens')
async def globe_tokens():
    return _globe_cache['data'] or {'tokens': [], 'minMarketCap': GLOBE_MIN_MC, 'warming': True}


class FeelessLaunchPayload(BaseModel):
    chain: str = 'solana'
    wallet: str
    mint: str
    symbol: Optional[str] = None
    signature: Optional[str] = None


@app.post('/api/reputation/feeless-launch')
async def register_feeless_launch(payload: FeelessLaunchPayload):
    """Tag a token as launched on FEELESS — only after the chain confirms this wallet created it."""
    resolved = await resolve_creator(payload.chain, payload.mint)
    creator = (resolved or {}).get('identity') if isinstance(resolved, dict) else None
    if not creator:
        raise HTTPException(409, 'Mint not yet visible on-chain — retry after confirmation.')
    if creator != payload.wallet:
        raise HTTPException(403, 'This wallet did not create that mint.')
    async with _lock:
        store = _load()
        store.setdefault('feelessLaunches', {})[payload.mint] = {
            'chain': payload.chain, 'wallet': payload.wallet, 'mint': payload.mint, 'symbol': payload.symbol,
            'signature': payload.signature, 'at': time.time(),
        }
        ckey = _creator_key(payload.chain, payload.wallet)
        entry = store['creators'].setdefault(ckey, {'chain': payload.chain, 'address': payload.wallet, 'firstSeen': time.time(), 'lastSeen': time.time(), 'tokens': {}})
        entry['lastSeen'] = time.time()
        entry['tokens'].setdefault(payload.mint, {'pairAddress': payload.mint, 'baseTokenAddress': payload.mint, 'symbol': payload.symbol,
                                                  'dexId': 'feeless', 'firstSeenAt': time.time(), 'status': 'active', 'launchedOnFeeless': True})
        entry['tokens'][payload.mint]['launchedOnFeeless'] = True
        _push_feed(store, payload.chain, payload.wallet, 'new_token', f'Launched {payload.symbol or "a token"} on FEELESS.')
        _save(store)
    return {'ok': True, 'creator': creator}


# ---- Web push alerts ---------------------------------------------------------
import base64
import hashlib

PUSH_PATH = DATA_DIR / 'push.json'
VAPID_PATH = DATA_DIR / 'vapid.json'
_push_lock = asyncio.Lock()
DEFAULT_RULES = {'up': 20, 'down': 15, 'move24h': 0, 'liqDrain': 30, 'volSpike': 4, 'feeRead': True, 'creatorFlag': True}
DEFAULT_PREFS = {'cooldownMin': 30, 'minLiquidity': 0, 'quietStart': None, 'quietEnd': None}


def _vapid():
    if VAPID_PATH.exists():
        return json.loads(VAPID_PATH.read_text())
    from py_vapid import Vapid01
    from cryptography.hazmat.primitives import serialization
    v = Vapid01()
    v.generate_keys()
    priv = v.private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    pub_raw = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    data = {'private': priv, 'public': base64.urlsafe_b64encode(pub_raw).decode().rstrip('=')}
    VAPID_PATH.write_text(json.dumps(data))
    try:
        os.chmod(VAPID_PATH, 0o600)
    except OSError:
        pass
    return data


def _push_load():
    if PUSH_PATH.exists():
        try:
            return json.loads(PUSH_PATH.read_text())
        except Exception:
            pass
    return {'subs': {}}


def _push_save(d):
    PUSH_PATH.write_text(json.dumps(d))


def _sub_id(sub):
    return hashlib.sha256((sub.get('endpoint') or '').encode()).hexdigest()[:24]


class PushSubscribe(BaseModel):
    subscription: dict
    watch: list = []
    prefs: dict = {}


@app.get('/api/reputation/push/vapid')
async def push_vapid():
    return {'publicKey': _vapid()['public']}


@app.post('/api/reputation/push/subscribe')
async def push_subscribe(payload: PushSubscribe):
    sub = payload.subscription
    if not str(sub.get('endpoint', '')).startswith('https://') or not (sub.get('keys') or {}).get('p256dh'):
        raise HTTPException(400, 'Invalid push subscription.')
    sid = _sub_id(sub)
    async with _push_lock:
        d = _push_load()
        prev = d['subs'].get(sid, {})
        watch = []
        for w in payload.watch[:100]:
            if not isinstance(w, dict) or not w.get('pairAddress') or not w.get('chainId'):
                continue
            key = f"{w['chainId']}:{w['pairAddress']}"
            old = next((x for x in prev.get('watch', []) if f"{x['chainId']}:{x['pairAddress']}" == key), {})
            watch.append({'chainId': w['chainId'], 'pairAddress': w['pairAddress'], 'mint': w.get('mint'), 'symbol': w.get('symbol'),
                          'watchedPrice': w.get('watchedPrice'), 'watchedLiq': w.get('watchedLiq') or old.get('watchedLiq'),
                          'rules': {**DEFAULT_RULES, **(w.get('rules') or {})}, 'state': old.get('state', {})})
        d['subs'][sid] = {'subscription': sub, 'watch': watch, 'prefs': {**DEFAULT_PREFS, **(payload.prefs or {})},
                          'createdAt': prev.get('createdAt', time.time()), 'updatedAt': time.time(), 'sent': prev.get('sent', [])[-50:]}
        _push_save(d)
    return {'ok': True, 'id': sid, 'watching': len(watch)}


class PushUnsubscribe(BaseModel):
    endpoint: str


@app.post('/api/reputation/push/unsubscribe')
async def push_unsubscribe(payload: PushUnsubscribe):
    async with _push_lock:
        d = _push_load()
        d['subs'].pop(_sub_id({'endpoint': payload.endpoint}), None)
        _push_save(d)
    return {'ok': True}


def _send_push(sub, title, body, url='/terminal/watchlist', tag=None):
    from pywebpush import webpush, WebPushException
    from py_vapid import Vapid01
    v = _vapid()
    try:
        webpush(subscription_info=sub, data=json.dumps({'title': title, 'body': body, 'url': url, 'tag': tag}),
                vapid_private_key=Vapid01.from_pem(v['private'].encode()), vapid_claims={'sub': 'mailto:alerts@feeless.app'}, ttl=600)
        return 'ok'
    except WebPushException as exc:
        code = getattr(getattr(exc, 'response', None), 'status_code', None)
        return 'gone' if code in (404, 410) else f'error {code}'
    except Exception as exc:
        return f'error {type(exc).__name__}'


class PushTest(BaseModel):
    endpoint: str


@app.post('/api/reputation/push/test')
async def push_test(payload: PushTest):
    d = _push_load()
    entry = d['subs'].get(_sub_id({'endpoint': payload.endpoint}))
    if not entry:
        raise HTTPException(404, 'Subscription not found — enable push first.')
    result = await asyncio.to_thread(_send_push, entry['subscription'], 'FEELESS alerts are on', f"Watching {len(entry['watch'])} coin(s). You'll hear from us even with the site closed.", '/terminal/watchlist', 'feeless-test')
    return {'result': result}


def _in_quiet(prefs):
    qs, qe = prefs.get('quietStart'), prefs.get('quietEnd')
    if qs is None or qe is None:
        return False
    h = time.localtime().tm_hour
    return (qs <= h < qe) if qs < qe else (h >= qs or h < qe)


async def _evaluate_alerts():
    """Server-side watcher: every 30s, evaluate every subscriber's rules against live data."""
    while True:
        try:
            d = _push_load()
            watched = {}
            for entry in d['subs'].values():
                for w in entry['watch']:
                    watched.setdefault(w['chainId'], set()).add(w['pairAddress'])
            live = {}
            async with httpx.AsyncClient(timeout=10) as http:
                for chain, pairs in watched.items():
                    pairs = sorted(pairs)
                    for i in range(0, len(pairs), 30):
                        try:
                            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{",".join(pairs[i:i + 30])}')
                            for p in (r.json() or {}).get('pairs') or []:
                                live[f"{chain}:{p.get('pairAddress')}"] = p
                        except Exception:
                            pass
                sol_mints = sorted({w['mint'] for e in d['subs'].values() for w in e['watch'] if w['chainId'] == 'solana' and w.get('mint')})
                jup = {}
                for i in range(0, len(sol_mints), 50):
                    try:
                        r = await http.get(f'https://lite-api.jup.ag/price/v3?ids={",".join(sol_mints[i:i + 50])}')
                        jup.update({k: float(v.get('usdPrice') or 0) for k, v in (r.json() or {}).items()})
                    except Exception:
                        pass
                fee_reads = {}
                sol_pairs = [{'chainId': 'solana', 'pairAddress': a} for a in sorted(watched.get('solana', set()))]
                if sol_pairs:
                    try:
                        r = await http.post('http://127.0.0.1:5088/api/cats/evaluate', json={'pairs': sol_pairs})
                        fee_reads = (r.json() or {}).get('reads') or {}
                    except Exception:
                        pass
            rep = _load()
            creator_of = {}
            for c in rep['creators'].values():
                for t in c['tokens'].values():
                    if t.get('baseTokenAddress'):
                        creator_of[t['baseTokenAddress']] = c
            now = time.time()
            dead = []
            for sid, entry in d['subs'].items():
                prefs = entry['prefs']
                cooldown = max(5, int(prefs.get('cooldownMin') or 30)) * 60
                quiet = _in_quiet(prefs)
                for w in entry['watch']:
                    p = live.get(f"{w['chainId']}:{w['pairAddress']}")
                    if not p:
                        continue
                    rules, state = w['rules'], w.setdefault('state', {})
                    sym = w.get('symbol') or (p.get('baseToken') or {}).get('symbol') or 'coin'
                    price = jup.get(w.get('mint')) or float(p.get('priceUsd') or 0)
                    liq = float((p.get('liquidity') or {}).get('usd') or 0)
                    if not w.get('watchedLiq') and liq:
                        w['watchedLiq'] = liq
                    if prefs.get('minLiquidity') and liq < float(prefs['minLiquidity']):
                        continue
                    fired = []
                    base = float(w.get('watchedPrice') or 0)
                    if base and price:
                        move = (price / base - 1) * 100
                        if rules.get('up') and move >= rules['up']:
                            fired.append(('up', f'{sym} is up {move:+.1f}% since you starred it'))
                        elif rules.get('down') and move <= -rules['down']:
                            fired.append(('down', f'{sym} is down {move:+.1f}% since you starred it'))
                        elif abs(move) < min(rules.get('up') or 999, rules.get('down') or 999) / 2:
                            state.pop('up', None); state.pop('down', None)
                    h24 = float((p.get('priceChange') or {}).get('h24') or 0)
                    if rules.get('move24h') and abs(h24) >= rules['move24h']:
                        fired.append(('move24h', f'{sym} moved {h24:+.1f}% in 24h'))
                    if rules.get('liqDrain') and w.get('watchedLiq') and liq and liq <= w['watchedLiq'] * (1 - rules['liqDrain'] / 100):
                        fired.append(('liqDrain', f'{sym} liquidity drained {(1 - liq / w["watchedLiq"]) * 100:.0f}% — possible exit'))
                    vol = p.get('volume') or {}
                    m5, h24v = float(vol.get('m5') or 0), float(vol.get('h24') or 0)
                    if rules.get('volSpike') and h24v > 0 and m5 * 288 >= rules['volSpike'] * h24v and m5 > 500:
                        fired.append(('volSpike', f'{sym} volume spike: last 5m running {m5 * 288 / h24v:.1f}× its daily pace'))
                    read = fee_reads.get(w['pairAddress'])
                    if rules.get('feeRead') and read and read.get('passes') and not state.get('feeWasPass'):
                        fired.append(('feeRead', f"Fee would buy {sym} now — it just passed every entry rule"))
                    if read:
                        state['feeWasPass'] = bool(read.get('passes'))
                    creator = creator_of.get(w.get('mint'))
                    if rules.get('creatorFlag') and creator and score_creator(creator)['badge'] == 'flagged' and not state.get('flagSent'):
                        fired.append(('creatorFlag', f'{sym} creator is now flagged on FEELESS reputation'))
                        state['flagSent'] = True
                    for kind, text in fired:
                        last = state.get(kind)
                        if last and now - last < cooldown and kind not in ('up', 'down'):
                            continue
                        if kind in ('up', 'down') and last:
                            continue
                        state[kind] = now
                        if quiet:
                            continue
                        res = await asyncio.to_thread(_send_push, entry['subscription'], f'FEELESS · {sym}', text,
                                                      f"/?coin={w['chainId']}:{w['pairAddress']}", f"{w['pairAddress']}-{kind}")
                        entry.setdefault('sent', []).append({'at': now, 'kind': kind, 'text': text, 'result': res})
                        entry['sent'] = entry['sent'][-50:]
                        if res == 'gone':
                            dead.append(sid)
                            break
            async with _push_lock:
                fresh = _push_load()
                for sid, entry in d['subs'].items():
                    if sid in fresh['subs'] and sid not in dead:
                        fresh['subs'][sid]['watch'] = entry['watch']
                        fresh['subs'][sid]['sent'] = entry.get('sent', [])
                for sid in dead:
                    fresh['subs'].pop(sid, None)
                _push_save(fresh)
        except Exception as exc:
            print('push watcher error', exc)
        await asyncio.sleep(30)


@app.on_event('startup')
async def _start_push_watcher():
    _vapid()
    asyncio.create_task(_evaluate_alerts())


@app.get('/api/reputation/push/status')
async def push_status(endpoint: str):
    entry = _push_load()['subs'].get(_sub_id({'endpoint': endpoint}))
    if not entry:
        return {'subscribed': False}
    return {'subscribed': True, 'watching': len(entry['watch']), 'prefs': entry['prefs'], 'recent': entry.get('sent', [])[-10:][::-1]}


# ---- Call Ledger: every coin posted in the Trenches, priced at the moment and tracked forever
CALLS_PATH = DATA_DIR / 'calls.json'
_calls_lock = asyncio.Lock()


def _calls_load():
    if CALLS_PATH.exists():
        try:
            return json.loads(CALLS_PATH.read_text())
        except Exception:
            pass
    return {'calls': {}}


def _calls_save(d):
    CALLS_PATH.write_text(json.dumps(d))


class CallPayload(BaseModel):
    room: str
    messageId: str
    caller: str
    callerAddress: Optional[str] = None
    chain: str
    pairAddress: str
    ts: Optional[float] = None


@app.post('/api/reputation/calls')
async def register_call(payload: CallPayload):
    """Price is taken by the server at registration — never trusted from the client."""
    cid = hashlib.sha256(f'{payload.messageId}:{payload.pairAddress}'.encode()).hexdigest()[:20]
    d = _calls_load()
    if cid in d['calls']:
        return {'ok': True, 'id': cid, 'existing': True}
    msg_ts = (payload.ts or time.time() * 1000) / 1000 if (payload.ts or 0) > 1e11 else (payload.ts or time.time())
    if time.time() - msg_ts > 600:
        raise HTTPException(409, 'Call is too old to price honestly.')
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{payload.chain}/{payload.pairAddress}')
            p = ((r.json() or {}).get('pairs') or [None])[0]
    except Exception:
        p = None
    price = float((p or {}).get('priceUsd') or 0)
    if not p or price <= 0:
        raise HTTPException(404, 'No live market for that pair.')
    call = {'id': cid, 'messageId': payload.messageId[:80], 'room': payload.room[:80], 'caller': payload.caller[:40], 'callerAddress': (payload.callerAddress or '')[:64],
            'chain': payload.chain, 'pairAddress': payload.pairAddress, 'mint': (p.get('baseToken') or {}).get('address'),
            'symbol': (p.get('baseToken') or {}).get('symbol'), 'imageUrl': (p.get('info') or {}).get('imageUrl'),
            'priceAtCall': price, 'mcAtCall': p.get('marketCap') or p.get('fdv'), 'at': time.time(),
            'lastPrice': price, 'peakPrice': price, 'checkedAt': time.time()}
    async with _calls_lock:
        d = _calls_load()
        d['calls'].setdefault(cid, call)
        _calls_save(d)
    return {'ok': True, 'id': cid}


def _call_view(c):
    return {**c, 'x': c['lastPrice'] / c['priceAtCall'] if c['priceAtCall'] else None,
            'peakX': c['peakPrice'] / c['priceAtCall'] if c['priceAtCall'] else None}


async def _refresh_calls():
    while True:
        try:
            d = _calls_load()
            by_chain = {}
            for c in d['calls'].values():
                if time.time() - c['at'] < 30 * 86400:
                    by_chain.setdefault(c['chain'], set()).add(c['pairAddress'])
            live = {}
            async with httpx.AsyncClient(timeout=10) as http:
                for chain, pairs in by_chain.items():
                    pairs = sorted(pairs)
                    for i in range(0, len(pairs), 30):
                        try:
                            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{",".join(pairs[i:i + 30])}')
                            for p in (r.json() or {}).get('pairs') or []:
                                live[p.get('pairAddress')] = float(p.get('priceUsd') or 0)
                        except Exception:
                            pass
            async with _calls_lock:
                d = _calls_load()
                for c in d['calls'].values():
                    px = live.get(c['pairAddress'])
                    if px:
                        c['lastPrice'] = px
                        c['peakPrice'] = max(c['peakPrice'], px)
                        c['checkedAt'] = time.time()
                _calls_save(d)
        except Exception as exc:
            print('calls refresh error', exc)
        await asyncio.sleep(60)


@app.on_event('startup')
async def _start_calls():
    asyncio.create_task(_refresh_calls())


@app.get('/api/reputation/calls/recent')
async def recent_calls(room: Optional[str] = None, pair: Optional[str] = None, limit: int = Query(30, ge=1, le=100)):
    calls = [_call_view(c) for c in _calls_load()['calls'].values() if (not room or c['room'].startswith(room)) and (not pair or c['pairAddress'] == pair)]
    calls.sort(key=lambda c: -c['at'])
    return {'calls': calls[:limit]}


@app.get('/api/reputation/calls/leaderboard')
async def caller_board(days: int = Query(7, ge=1, le=90)):
    since = time.time() - days * 86400
    by = {}
    for c in _calls_load()['calls'].values():
        if c['at'] < since:
            continue
        v = _call_view(c)
        b = by.setdefault(c['caller'], {'caller': c['caller'], 'callerAddress': c.get('callerAddress'), 'calls': 0, 'hits': 0, 'rugs': 0, 'sumPeak': 0.0, 'best': None})
        b['calls'] += 1
        b['sumPeak'] += v['peakX'] or 1
        if (v['peakX'] or 0) >= 2:
            b['hits'] += 1
        if (v['x'] or 1) <= 0.3:
            b['rugs'] += 1
        if not b['best'] or (v['peakX'] or 0) > (b['best']['peakX'] or 0):
            b['best'] = {'symbol': v['symbol'], 'peakX': v['peakX'], 'pairAddress': v['pairAddress'], 'chain': v['chain']}
    rows = [{**b, 'hitRate': b['hits'] / b['calls'], 'avgPeakX': b['sumPeak'] / b['calls']} for b in by.values()]
    rows.sort(key=lambda r: (-r['hitRate'], -r['avgPeakX'], -r['calls']))
    return {'rows': rows[:50], 'days': days}


@app.get('/api/reputation/calls/hot')
async def hot_calls(minutes: int = Query(60, ge=5, le=1440)):
    since = time.time() - minutes * 60
    agg = {}
    for c in _calls_load()['calls'].values():
        if c['at'] < since:
            continue
        v = _call_view(c)
        a = agg.setdefault(c['pairAddress'], {'symbol': c['symbol'], 'imageUrl': c.get('imageUrl'), 'chain': c['chain'], 'pairAddress': c['pairAddress'], 'callers': set(), 'calls': 0, 'firstX': v['x']})
        a['calls'] += 1
        a['callers'].add(c['caller'])
        a['x'] = v['x']
    rows = [{**{k: v for k, v in a.items() if k != 'callers'}, 'callers': len(a['callers'])} for a in agg.values()]
    rows.sort(key=lambda r: (-r['callers'], -r['calls']))
    return {'rows': rows[:12], 'minutes': minutes}


# ---- Chat reactions ------------------------------------------------------------
REACT_PATH = DATA_DIR / 'reactions.json'
REACTIONS = ['🔥', '🚀', '💎', '💀']
_react_lock = asyncio.Lock()


def _react_load():
    if REACT_PATH.exists():
        try:
            return json.loads(REACT_PATH.read_text())
        except Exception:
            pass
    return {'rooms': {}}


class ReactPayload(BaseModel):
    room: str
    messageId: str
    emoji: str
    voter: str


@app.post('/api/reputation/reactions')
async def react(payload: ReactPayload):
    if payload.emoji not in REACTIONS or not (6 <= len(payload.voter) <= 80):
        raise HTTPException(400, 'Invalid reaction.')
    async with _react_lock:
        d = _react_load()
        msg = d['rooms'].setdefault(payload.room[:120], {}).setdefault(payload.messageId[:80], {})
        voters = msg.setdefault(payload.emoji, [])
        if payload.voter in voters:
            voters.remove(payload.voter)
        else:
            voters.append(payload.voter)
        REACT_PATH.write_text(json.dumps(d))
    return {'ok': True}


@app.get('/api/reputation/reactions')
async def reactions(room: str, voter: Optional[str] = None):
    msgs = _react_load()['rooms'].get(room[:120], {})
    return {'reactions': {mid: {e: {'count': len(v), 'mine': bool(voter and voter in v)} for e, v in em.items() if v} for mid, em in msgs.items()},
            'emojis': REACTIONS}


@app.get('/api/reputation/calls/by-room')
async def calls_by_room(room: str):
    out = {}
    for c in _calls_load()['calls'].values():
        if c['room'] == room[:80] and c.get('messageId'):
            v = _call_view(c)
            out.setdefault(c['messageId'], []).append({'symbol': v['symbol'], 'x': v['x'], 'peakX': v['peakX'], 'mcAtCall': v['mcAtCall'], 'pairAddress': v['pairAddress']})
    return {'calls': out}


@app.get('/api/reputation/balance/{owner}/{mint}')
async def token_balance(owner: str, mint: str):
    """UI-unit balance of a token for a wallet (Solana), used for quick sells."""
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            if mint == 'So11111111111111111111111111111111111111112':
                r = await _rpc(http, 'getBalance', [owner])
                return {'amount': ((r or {}).get('value') or 0) / 1e9, 'decimals': 9}
            r = await _rpc(http, 'getTokenAccountsByOwner', [owner, {'mint': mint}, {'encoding': 'jsonParsed'}])
    except Exception:
        raise HTTPException(502, 'Balance unavailable right now.')
    total, decimals = 0.0, None
    for acc in (r or {}).get('value') or []:
        info = (((acc.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
        amt = (info.get('tokenAmount') or {})
        total += float(amt.get('uiAmount') or 0)
        decimals = amt.get('decimals', decimals)
    return {'amount': total, 'decimals': decimals}


# ---- Wallet profiles (customizable, wallet-signed) ------------------------------
PROFILE_PATH = DATA_DIR / 'profiles.json'
_profile_lock = asyncio.Lock()
HEX = set('0123456789abcdefABCDEF')


def _profiles_load():
    if PROFILE_PATH.exists():
        try:
            return json.loads(PROFILE_PATH.read_text())
        except Exception:
            pass
    return {'profiles': {}}


def _safe_url(v, max_len=400):
    v = (v or '').strip()
    return v if v.startswith('https://') or v.startswith('/api/reputation/uploads/') and len(v) <= max_len else ''


def _clean_profile(p: dict) -> dict:
    accent = str(p.get('accent') or '#00e9a0')
    accent = accent if accent.startswith('#') and len(accent) in (4, 7) and set(accent[1:]) <= HEX else '#00e9a0'
    links = p.get('links') or {}
    top8 = []
    for t in (p.get('top8') or [])[:8]:
        if isinstance(t, dict) and t.get('pairAddress') and t.get('chain'):
            top8.append({'chain': str(t['chain'])[:20], 'pairAddress': str(t['pairAddress'])[:64], 'mint': str(t.get('mint') or '')[:64],
                         'symbol': str(t.get('symbol') or '')[:16], 'imageUrl': _safe_url(t.get('imageUrl'))})
    return {
        'displayName': str(p.get('displayName') or '')[:32], 'bio': str(p.get('bio') or '')[:280],
        'avatarUrl': _safe_url(p.get('avatarUrl')), 'bannerUrl': _safe_url(p.get('bannerUrl')), 'accent': accent,
        'mood': str(p.get('mood') or '')[:40],
        'links': {k: _safe_url(links.get(k)) for k in ('x', 'website', 'telegram') if _safe_url(links.get(k))},
        'top8': top8,
        'theme': p.get('theme') if p.get('theme') in ('grid', 'glitter', 'matrix', 'sunset', 'vapor', 'goldrush', 'neoncat') else 'grid',
        'friends': [str(f)[:44] for f in (p.get('friends') or [])[:8] if _re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', str(f))],
        'ring': p.get('ring') if p.get('ring') in RING_TIERS else 'none',
        'nameFx': p.get('nameFx') if p.get('nameFx') in NAMEFX_TIERS else 'none',
        'featuredBadges': list(dict.fromkeys(str(b)[:40] for b in (p.get('featuredBadges') or []) if _re.match(r'^[a-z0-9-]{2,40}$', str(b))))[:3],
    }


class ProfileSave(BaseModel):
    address: str
    message: str
    signature: str
    profile: dict


def _verify_evm(address: str, message: str, signature_hex: str) -> bool:
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        return Account.recover_message(encode_defunct(text=message), signature=signature_hex).lower() == address.lower()
    except Exception:
        return False


def _verify_wallet(address: str, message: str, signature: str) -> bool:
    if _re.match(r'^0x[0-9a-fA-F]{40}$', address or ''):
        return _verify_evm(address, message, signature)
    return _verify_solana(address, message, signature)


def _verify_solana(address: str, message: str, signature_b64: str) -> bool:
    try:
        import base58
        from nacl.signing import VerifyKey
        VerifyKey(base58.b58decode(address)).verify(message.encode(), base64.b64decode(signature_b64))
        return True
    except Exception:
        return False


@app.post('/api/reputation/profile')
async def save_profile(payload: ProfileSave):
    expected_prefix = f'FEELESS profile update\naddress:{payload.address}\nts:'
    if not payload.message.startswith(expected_prefix):
        raise HTTPException(400, 'Unexpected message.')
    try:
        ts = int(payload.message[len(expected_prefix):])
    except ValueError:
        raise HTTPException(400, 'Bad timestamp.')
    if abs(time.time() - ts) > 300:
        raise HTTPException(401, 'Signature expired — sign again.')
    if not _verify_wallet(payload.address, payload.message, payload.signature):
        raise HTTPException(401, 'Signature does not match this wallet.')
    tier = (await _perk_tier(payload.address))[0]
    async with _profile_lock:
        d = _profiles_load()
        prev = d['profiles'].get(payload.address, {})
        if prev.get('lastTs', 0) >= ts:
            raise HTTPException(409, 'Replay rejected — sign a fresh update.')
        clean = _clean_profile(payload.profile)
        if clean['featuredBadges']:
            earned = {b['id'] for b in (await wallet_badges(payload.address))['badges']}
            clean['featuredBadges'] = [b for b in clean['featuredBadges'] if b in earned]
        if RING_TIERS[clean['ring']] > tier or NAMEFX_TIERS[clean['nameFx']] > tier:
            raise HTTPException(403, 'That style is a $FEE holder perk — hold more $FEE to unlock it.')
        if TIER_THEMES.get(clean['theme'], 0) > tier:
            raise HTTPException(403, 'That theme is a Fee Friend perk — hold $10+ of $FEE.')
        d['profiles'][payload.address] = {**clean, 'lastTs': ts, 'updatedAt': time.time()}
        PROFILE_PATH.write_text(json.dumps(d))
    return {'ok': True, 'profile': d['profiles'][payload.address]}


@app.get('/api/reputation/profile/{address}')
async def get_profile(address: str):
    p = _profiles_load()['profiles'].get(address)
    board = await caller_board(days=30)
    caller = next((r for r in board['rows'] if r.get('callerAddress') == address), None)
    return {'address': address, 'profile': p, 'caller': caller}


@app.get('/api/reputation/profiles')
async def get_profiles(addresses: str):
    d = _profiles_load()['profiles']
    return {'profiles': {a: {k: d[a].get(k) for k in ('displayName', 'avatarUrl', 'accent', 'mood', 'featuredBadges', 'ring', 'nameFx')} for a in addresses.split(',')[:100] if a in d}}



# ---- Evidence-based blocklist of snipers and bundlers ----------------------------
BLOCK_PATH = DATA_DIR / 'blocklist.json'
_block_lock = asyncio.Lock()
AUTO_BLOCK_STRIKES = 3


def _block_load():
    if BLOCK_PATH.exists():
        try:
            return json.loads(BLOCK_PATH.read_text())
        except Exception:
            pass
    return {'wallets': {}}


def _is_blocked(rec):
    if not rec:
        return False
    return bool(rec.get('reported')) or len(rec.get('mints', {})) >= AUTO_BLOCK_STRIKES


async def _record_offenders(mint, bundled, snipers):
    if not bundled and not snipers:
        return
    async with _block_lock:
        d = _block_load()
        for role, wallets in (('bundler', bundled), ('sniper', snipers)):
            for w in wallets:
                rec = d['wallets'].setdefault(w, {'mints': {}, 'firstSeen': time.time()})
                rec['mints'].setdefault(mint, role)
                rec['lastSeen'] = time.time()
        BLOCK_PATH.write_text(json.dumps(d))


class BlockPayload(BaseModel):
    mint: str
    wallets: list
    reporter: Optional[str] = None


@app.post('/api/reputation/blocklist')
async def add_to_blocklist(payload: BlockPayload):
    """Only wallets proven by FEELESS's own forensics to have bundled/sniped that mint are accepted."""
    intel = await token_intel('solana', payload.mint)
    evidence = {w: 'bundler' for w in intel.get('bundledWallets', [])}
    evidence.update({w: 'sniper' for w in intel.get('sniperWallets', []) if w not in evidence})
    accepted, rejected = [], []
    async with _block_lock:
        d = _block_load()
        for w in [str(x) for x in payload.wallets[:200]]:
            if w not in evidence:
                rejected.append(w)
                continue
            rec = d['wallets'].setdefault(w, {'mints': {}, 'firstSeen': time.time()})
            rec['mints'].setdefault(payload.mint, evidence[w])
            rec['reported'] = True
            rec.setdefault('reports', []).append({'mint': payload.mint, 'role': evidence[w], 'by': (payload.reporter or 'anon')[:64], 'at': time.time()})
            rec['reports'] = rec['reports'][-20:]
            accepted.append(w)
        BLOCK_PATH.write_text(json.dumps(d))
    _intel_cache.pop(payload.mint, None)
    return {'accepted': accepted, 'rejected': rejected}


@app.get('/api/reputation/blocklist')
async def get_blocklist(limit: int = Query(200, ge=1, le=5000)):
    rows = []
    for w, rec in _block_load()['wallets'].items():
        if not _is_blocked(rec):
            continue
        roles = list(rec['mints'].values())
        rows.append({'wallet': w, 'strikes': len(rec['mints']), 'bundles': roles.count('bundler'), 'snipes': roles.count('sniper'),
                     'reported': bool(rec.get('reported')), 'auto': len(rec['mints']) >= AUTO_BLOCK_STRIKES, 'lastSeen': rec.get('lastSeen')})
    rows.sort(key=lambda r: (-r['strikes'], -(r['lastSeen'] or 0)))
    return {'wallets': rows[:limit], 'total': len(rows), 'autoThreshold': AUTO_BLOCK_STRIKES}


# ---- FEELESS chat: wallet-signed, holder-gated coin rooms ---------------------------
import re as _re
CHAT_PATH = DATA_DIR / 'chat.json'
_chat_lock = asyncio.Lock()
_room_mint_cache: dict = {}
_holder_cache: dict = {}
CA_RE = _re.compile(r'\b(?:0x[0-9a-fA-F]{40}|[1-9A-HJ-NP-Za-km-z]{32,44})\b')
MENTION_RE = _re.compile(r'@([A-Za-z0-9_.-]{2,32})')
MIN_HOLD_USD = 1.0


def _chat_load():
    if CHAT_PATH.exists():
        try:
            return json.loads(CHAT_PATH.read_text())
        except Exception:
            pass
    return {'rooms': {}, 'lastTs': {}}


def _display_name(address):
    p = _profiles_load()['profiles'].get(address) or {}
    return p.get('displayName') or f'{address[:4]}…{address[-4:]}'


async def _room_mint(room: str):
    """coin-solana-<pairOrMint>-<side> → (mint, symbol); None for non-coin rooms."""
    m = _re.match(r'^coin-solana-([1-9A-HJ-NP-Za-km-z]{32,44})-(bulls|bears|trenches)$', room)
    if not m:
        return None
    key = m.group(1)
    if key in _room_mint_cache:
        return _room_mint_cache[key]
    info = None
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/solana/{key}')
            p = ((r.json() or {}).get('pairs') or [None])[0]
            if not p:
                r = await http.get(f'https://api.dexscreener.com/tokens/v1/solana/{key}')
                arr = r.json() if r.status_code == 200 else []
                p = arr[0] if isinstance(arr, list) and arr else None
            if p:
                info = ((p.get('baseToken') or {}).get('address'), (p.get('baseToken') or {}).get('symbol'))
    except Exception:
        info = None
    if info:
        _room_mint_cache[key] = info
    return info


async def _holding_usd(owner: str, mint: str):
    key = f'{owner}:{mint}'
    hit = _holder_cache.get(key)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    bal = await token_balance(owner, mint)
    amount = float(bal.get('amount') or 0)
    price = 0.0
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f'https://lite-api.jup.ag/price/v3?ids={mint}')
            price = float(((r.json() or {}).get(mint) or {}).get('usdPrice') or 0)
    except Exception:
        pass
    value = amount * price
    _holder_cache[key] = (time.time(), value)
    return value


@app.get('/api/reputation/chat/gate')
async def chat_gate(room: str, address: Optional[str] = None):
    coin = await _room_mint(room)
    if not coin:
        return {'gated': False, 'allowed': True}
    mint, symbol = coin
    if not address:
        return {'gated': True, 'allowed': False, 'symbol': symbol, 'minUsd': MIN_HOLD_USD, 'holdingUsd': None}
    if address.startswith('0x'):
        return {'gated': True, 'allowed': False, 'symbol': symbol, 'minUsd': MIN_HOLD_USD, 'holdingUsd': None, 'needsChain': 'solana'}
    value = await _holding_usd(address, mint)
    return {'gated': True, 'allowed': value >= MIN_HOLD_USD, 'symbol': symbol, 'minUsd': MIN_HOLD_USD, 'holdingUsd': round(value, 4)}


class ChatPost(BaseModel):
    room: str
    address: str
    text: str
    ts: int
    signature: str
    parentId: Optional[str] = None
    boost: bool = False


_boost_last = {}


def _chat_message_to_sign(room, address, ts, text):
    return f'FEELESS chat\nroom:{room}\naddress:{address}\nts:{ts}\nhash:{hashlib.sha256(text.encode()).hexdigest()[:16]}'


@app.post('/api/reputation/chat')
async def chat_post(payload: ChatPost):
    text = payload.text.strip()
    if not text or len(text) > 500:
        raise HTTPException(400, 'Messages must be 1–500 characters.')
    if not _re.match(r'^[a-z0-9-]{3,120}$', payload.room) and not payload.room.startswith('coin-') and not _re.match(r'^wall-([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', payload.room):
        raise HTTPException(400, 'Unknown room.')
    if abs(time.time() - payload.ts) > 120:
        raise HTTPException(401, 'Signature expired — try again.')
    if not _verify_wallet(payload.address, _chat_message_to_sign(payload.room, payload.address, payload.ts, text), payload.signature):
        raise HTTPException(401, 'Signature does not match this wallet.')
    coin = await _room_mint(payload.room)
    if coin and payload.address.startswith('0x'):
        raise HTTPException(403, f'{coin[1]} lives on Solana — switch your wallet to its Solana account to chat here.')
    if coin:
        value = await _holding_usd(payload.address, coin[0])
        if value < MIN_HOLD_USD:
            raise HTTPException(403, f'Hold at least ${MIN_HOLD_USD:.0f} of {coin[1]} to chat here (you hold ${value:.2f}).')
    tokens = []
    for ca in CA_RE.findall(text)[:2]:
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                r = await http.get(f'https://api.dexscreener.com/latest/dex/search?q={ca}')
                pairs = sorted((r.json() or {}).get('pairs') or [], key=lambda p: -(((p.get('liquidity') or {}).get('usd')) or 0))
            if pairs:
                tokens.append({'address': ca, 'chainId': pairs[0].get('chainId'), 'pairAddress': pairs[0].get('pairAddress'),
                               'symbol': (pairs[0].get('baseToken') or {}).get('symbol'), 'pair': pairs[0], 'fetched_at': time.time()})
        except Exception:
            pass
    tier = (await _perk_tier(payload.address))[0]
    boosted = False
    if payload.boost:
        if tier < 2:
            raise HTTPException(403, 'Boosting is a Fee Insider perk — hold $100+ of $FEE.')
        if time.time() - _boost_last.get(payload.address, 0) < 600:
            raise HTTPException(429, 'One boost every 10 minutes.')
        boosted = True
    async with _chat_lock:
        d = _chat_load()
        last = d['lastTs'].get(payload.address, 0)
        if payload.ts <= last:
            raise HTTPException(409, 'Replay rejected — sign a fresh message.')
        if time.time() - d.get('lastAt', {}).get(payload.address, 0) < 3:
            raise HTTPException(429, 'Slow down — one message every 3 seconds.')
        d['lastTs'][payload.address] = payload.ts
        d.setdefault('lastAt', {})[payload.address] = time.time()
        if boosted:
            _boost_last[payload.address] = time.time()
        msg = {'id': uuid.uuid4().hex[:16], 'room': payload.room, 'address': payload.address, 'chain': 'evm' if payload.address.startswith('0x') else 'solana',
               'tier': tier, 'boosted': boosted,
               'username': _display_name(primary_of(payload.address)), 'identity': primary_of(payload.address), 'text': text, 'ts': int(time.time() * 1000),
               'parentId': payload.parentId, 'mentions': sorted(set(MENTION_RE.findall(text)))[:10], 'tokens': tokens,
               'profile': {'address': primary_of(payload.address), 'chain': 'solana' if not primary_of(payload.address).startswith('0x') else 'evm'}}
        room = d['rooms'].setdefault(payload.room, [])
        room.append(msg)
        d['rooms'][payload.room] = room[-300:]
        CHAT_PATH.write_text(json.dumps(d))
    return {'ok': True, 'message': msg}


def chat_system_post(room: str, username: str, address: str, text: str, tokens=None):
    """Server-authored message (e.g. Fee's calls). Not user-signed; flagged as system."""
    d = _chat_load()
    msg = {'id': uuid.uuid4().hex[:16], 'room': room, 'address': address, 'chain': 'solana', 'username': username, 'text': text,
           'ts': int(time.time() * 1000), 'parentId': None, 'mentions': [], 'tokens': tokens or [], 'system': True,
           'profile': {'address': address, 'chain': 'solana'}}
    d['rooms'].setdefault(room, []).append(msg)
    d['rooms'][room] = d['rooms'][room][-300:]
    CHAT_PATH.write_text(json.dumps(d))
    return msg


@app.get('/api/reputation/chat/{room}')
async def chat_room(room: str):
    msgs = _chat_load()['rooms'].get(room, [])[-120:]
    return {'room': room, 'messages': msgs}


FEE_ADDRESS = 'FEE-LEADER-CAT'


class FeeCallPayload(BaseModel):
    chain: str = 'solana'
    pairAddress: str
    text: str
    registerCall: bool = False


INTERNAL_KEY_PATH = DATA_DIR / 'internal.key'


def _internal_key():
    if not INTERNAL_KEY_PATH.exists():
        INTERNAL_KEY_PATH.write_text(uuid.uuid4().hex + uuid.uuid4().hex)
        try:
            os.chmod(INTERNAL_KEY_PATH, 0o600)
        except OSError:
            pass
    return INTERNAL_KEY_PATH.read_text().strip()


@app.post('/api/reputation/internal/fee-post')
async def fee_post(payload: FeeCallPayload, request: Request):
    """Only the local Fee engine (holder of the on-disk shared secret) may post as Fee."""
    import hmac
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), _internal_key()):
        raise HTTPException(403, 'Internal endpoint.')
    room = f'coin-{payload.chain}-{payload.pairAddress}-trenches'
    msg = chat_system_post(room, 'Fee 🐱', FEE_ADDRESS, payload.text[:2000])
    call_id = None
    if payload.registerCall:
        res = await register_call(CallPayload(room=room, messageId=msg['id'], caller='Fee 🐱', callerAddress=FEE_ADDRESS,
                                               chain=payload.chain, pairAddress=payload.pairAddress, ts=time.time()))
        call_id = res.get('id')
    return {'ok': True, 'messageId': msg['id'], 'callId': call_id}


_badge_cache: dict = {}
_fee_assets = {'at': 0, 'mints': {}}


async def _ecosystem_mints():
    if time.time() - _fee_assets['at'] < 600 and _fee_assets['mints']:
        return _fee_assets['mints']
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.get('http://127.0.0.1:5001/api/market/assets')
            _fee_assets['mints'] = {a['id']: a['mint'] for a in (r.json() or {}).get('assets') or [] if a.get('mint')}
            _fee_assets['at'] = time.time()
    except Exception:
        pass
    return _fee_assets['mints']


@app.get('/api/reputation/badges/catalog')
async def badge_catalog():
    return {'catalog': BADGE_CATALOG}


@app.get('/api/reputation/badges/{address}')
async def wallet_badges(address: str):
    """Automatic, data-backed badges. Every badge states the evidence behind it."""
    hit = _badge_cache.get(address)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    badges = []
    mints = await _ecosystem_mints()
    labels = {'fee': '$FEE', 'feecat': 'FEECAT', 'rfee': 'rFEE'}
    fee_usd = 0.0
    for aid, mint in mints.items():
        try:
            value = await _holding_usd(address, mint)
        except Exception:
            continue
        if aid == 'fee':
            fee_usd = value
        if value >= 1:
            label = labels.get(aid, aid.upper())
            if aid == 'fee' and value >= 1000:
                badges.append({'id': 'fee-whale', 'label': '$FEE Whale', 'icon': '🐋', 'tone': 'gold', 'why': f'Holds ${value:,.0f} of $FEE'})
            badges.append({'id': f'{aid}-holder', 'label': f'{label} Holder', 'icon': '🌿' if aid == 'fee' else '🐱' if aid == 'feecat' else '💠', 'tone': 'mint', 'why': f'Holds ${value:,.2f} of {label}'})
    try:
        async with httpx.AsyncClient(timeout=6) as http:
            leader = (await http.get('http://127.0.0.1:5088/api/cats/leader')).json().get('cat') or {}
        for pos in leader.get('positions', []):
            if pos.get('mint') and await _holding_usd(address, pos['mint']) >= 1:
                badges.append({'id': 'rides-with-fee', 'label': 'Rides with Fee', 'icon': '🐾', 'tone': 'mint', 'why': f"Holds {pos['symbol']}, which Fee is in right now"})
                break
    except Exception:
        pass
    board = await caller_board(days=30)
    me = next((r for r in board['rows'] if r.get('callerAddress') == address), None)
    if me:
        sharp = me['calls'] >= 5 and me['hitRate'] >= 0.5
        badges.append({'id': 'sharp-caller' if sharp else 'caller', 'label': 'Sharp Caller' if sharp else 'Caller', 'icon': '🎯', 'tone': 'gold' if sharp else 'plain',
                       'why': f"{me['calls']} calls, {round(me['hitRate'] * 100)}% hit 2× (30d)"})
    creator = _load()['creators'].get(_creator_key('solana', address))
    if creator:
        sc = score_creator(creator)
        if sc['badge'] == 'trusted':
            badges.append({'id': 'trusted-creator', 'label': 'Trusted Creator', 'icon': '🛡️', 'tone': 'mint', 'why': f"{sc['tokenCount']} launches, none dumped"})
        elif sc['badge'] == 'flagged':
            badges.append({'id': 'flagged-creator', 'label': 'Flagged Creator', 'icon': '⚠️', 'tone': 'bad', 'why': f"{sc['dumpedCount'] + sc['ruggedCount']} launches dumped or rugged"})
    if any(l['wallet'] == address for l in (_load().get('feelessLaunches') or {}).values()):
        badges.append({'id': 'feeless-launcher', 'label': 'FEELESS Launcher', 'icon': '🚀', 'tone': 'mint', 'why': 'Launched a token on FEELESS (verified on-chain)'})
    rec = _block_load()['wallets'].get(address)
    if _is_blocked(rec):
        badges.append({'id': 'blocklisted', 'label': 'Blocklisted', 'icon': '⛔', 'tone': 'bad', 'why': f"Caught bundling/sniping {len(rec['mints'])} launch(es)"})
    badges.extend(_admin_load()['badges'].get(address, {}).values())
    if address in _admin_wallets():
        badges.insert(0, {'id': 'feeless-hq', 'label': 'FEELESS HQ', 'icon': '👑', 'tone': 'gold', 'why': 'Created $FEE — runs the FEELESS command center'})
    progress = {'feeUsd': round(fee_usd, 2), 'calls': me['calls'] if me else 0, 'hitRate': me['hitRate'] if me else 0}
    out = {'address': address, 'badges': badges, 'progress': progress, 'at': time.time()}
    _badge_cache[address] = (time.time(), out)
    return out


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


# ---- FEELESS Command Center: creator-wallet admin tools ------------------------------
# $FEE's creator wallet (fee payer of the mint's first transaction on-chain) is the default
# admin; FEELESS_ADMIN_WALLETS in backend/.env (comma separated) overrides it.
FEE_CREATOR_WALLET = 'ANwSewb5AaKv4DarsDQ4NSEQ9APNtTGVxygPzn9u5K8P'
ADMIN_PATH = DATA_DIR / 'admin.json'
BUGS_PATH = ADMIN_PATH.parent / 'bugs.json'
_admin_lock = asyncio.Lock()
_status_log = []          # rolling (ts, method, path, status) for the security monitor
_holder_cache = {}
_bug_ip_hits = {}


def _admin_wallets():
    env = [a.strip() for a in os.environ.get('FEELESS_ADMIN_WALLETS', '').split(',') if a.strip()]
    return env or [FEE_CREATOR_WALLET]


def _admin_load():
    try:
        d = json.loads(ADMIN_PATH.read_text())
    except Exception:
        d = {}
    d.setdefault('badges', {}); d.setdefault('airdrops', []); d.setdefault('audit', [])
    return d


def _admin_save(d):
    ADMIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = ADMIN_PATH.with_suffix('.tmp'); tmp.write_text(json.dumps(d)); tmp.replace(ADMIN_PATH)


def _json_load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _json_save(path, d):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(d)); tmp.replace(path)


@app.middleware('http')
async def _record_status(request: Request, call_next):
    resp = await call_next(request)
    if resp.status_code >= 400:
        _status_log.append((time.time(), request.method, request.url.path[:120], resp.status_code))
        del _status_log[:-600]
    return resp


def _require_admin(request: Request) -> str:
    """Session proof: the admin wallet signs `FEELESS command center\\naddress:{a}\\nts:{ts}` (valid 1h)."""
    addr = request.headers.get('x-admin-address', '')
    ts = request.headers.get('x-admin-ts', '')
    sig = request.headers.get('x-admin-sig', '')
    if addr not in _admin_wallets():
        raise HTTPException(403, 'This wallet is not a FEELESS command center wallet.')
    try:
        ts_i = int(ts)
    except ValueError:
        raise HTTPException(401, 'Missing command center signature.')
    if abs(time.time() - ts_i) > 3600:
        raise HTTPException(401, 'Command center session expired — sign in again.')
    if not _verify_wallet(addr, f'FEELESS command center\naddress:{addr}\nts:{ts_i}', sig):
        raise HTTPException(401, 'Command center signature does not match.')
    return addr


def _audit(d, admin, action, detail):
    d['audit'].append({'at': time.time(), 'admin': admin, 'action': action, 'detail': detail})
    d['audit'] = d['audit'][-300:]


@app.get('/api/reputation/admin/whoami')
async def admin_whoami(address: str = ''):
    return {'isAdmin': address in _admin_wallets(),
            'source': 'env' if os.environ.get('FEELESS_ADMIN_WALLETS') else 'fee-creator-onchain'}


async def _token_holders(mint: str):
    hit = _holder_cache.get(mint)
    if hit and time.time() - hit[0] < 120:
        return hit[1]
    owners = {}
    accounts = {}
    async with httpx.AsyncClient(timeout=40) as http:
        for program in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
            filters = [{'memcmp': {'offset': 0, 'bytes': mint}}]
            if program.startswith('Tokenkeg'):
                filters.insert(0, {'dataSize': 165})
            try:
                accts = await _rpc(http, 'getProgramAccounts', [program, {'encoding': 'jsonParsed', 'filters': filters}])
            except Exception:
                accts = None
            for a in accts or []:
                info = (((a.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
                amt = float(((info.get('tokenAmount') or {}).get('uiAmount')) or 0)
                if amt > 0 and info.get('owner'):
                    owners[info['owner']] = owners.get(info['owner'], 0) + amt
                    if amt > accounts.get(info['owner'], ('', 0))[1]:
                        accounts[info['owner']] = (a.get('pubkey'), amt)
            if owners:
                break
    price = None
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            price = float(((await http.get(f'https://lite-api.jup.ag/price/v3?ids={mint}')).json().get(mint) or {}).get('usdPrice') or 0) or None
    except Exception:
        pass
    total = sum(owners.values()) or 1
    rows = sorted(({'owner': o, 'amount': v, 'pct': v / total * 100, 'usd': v * price if price else None, 'tokenAccount': accounts.get(o, (None,))[0]} for o, v in owners.items()), key=lambda r: -r['amount'])
    out = {'mint': mint, 'price': price, 'holders': len(rows), 'rows': rows, 'at': time.time()}
    _holder_cache[mint] = (time.time(), out)
    return out


@app.get('/api/reputation/admin/holders')
async def admin_holders(request: Request, asset: str = 'fee'):
    _require_admin(request)
    mints = await _ecosystem_mints()
    mint = mints.get(asset) or (asset if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', asset) else None)
    if not mint:
        raise HTTPException(404, 'Unknown asset.')
    data = await _token_holders(mint)
    d = _admin_load(); bl = _block_load()['wallets']
    lp_like = set()
    for r in data['rows'][:3]:
        if r['pct'] > 20:
            lp_like.add(r['owner'])  # bonding curve / pool vaults usually dominate the top
    rows = [{**r, 'customBadges': list(d['badges'].get(r['owner'], {}).values()), 'blocked': _is_blocked(bl.get(r['owner'])),
             'likelyPool': r['owner'] in lp_like, 'isAdmin': r['owner'] in _admin_wallets()} for r in data['rows'][:2000]]
    return {**data, 'rows': rows, 'assets': list(mints.keys())}


class AdminBadge(BaseModel):
    addresses: list
    label: str = Field(min_length=2, max_length=32)
    icon: str = Field(default='⭐', max_length=8)
    tone: str = 'gold'
    why: str = Field(default='', max_length=140)


@app.post('/api/reputation/admin/badges')
async def admin_award(request: Request, payload: AdminBadge):
    admin = _require_admin(request)
    addrs = [a for a in payload.addresses[:500] if _re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', str(a))]
    if not addrs:
        raise HTTPException(400, 'No valid addresses.')
    bid = 'custom-' + _re.sub(r'[^a-z0-9]+', '-', payload.label.lower()).strip('-')[:28]
    tone = payload.tone if payload.tone in ('mint', 'gold', 'plain', 'bad') else 'gold'
    async with _admin_lock:
        d = _admin_load()
        for a in addrs:
            d['badges'].setdefault(a, {})[bid] = {'id': bid, 'label': payload.label, 'icon': payload.icon, 'tone': tone,
                                                  'why': payload.why or 'Awarded by FEELESS', 'awardedBy': 'FEELESS', 'at': time.time()}
            _badge_cache.pop(a, None)
        _audit(d, admin, 'award-badge', f'{payload.label} → {len(addrs)} wallet(s)')
        _admin_save(d)
    return {'ok': True, 'awarded': len(addrs), 'id': bid}


@app.delete('/api/reputation/admin/badges/{address}/{bid}')
async def admin_revoke(request: Request, address: str, bid: str):
    admin = _require_admin(request)
    async with _admin_lock:
        d = _admin_load()
        removed = d['badges'].get(address, {}).pop(bid, None)
        _badge_cache.pop(address, None)
        _audit(d, admin, 'revoke-badge', f'{bid} ✕ {address[:6]}…')
        _admin_save(d)
    return {'ok': bool(removed)}


class Airdrop(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    asset: str = 'fee'
    recipients: list
    scheduledAt: float
    note: str = Field(default='', max_length=280)


@app.get('/api/reputation/admin/airdrops')
async def admin_airdrops(request: Request):
    _require_admin(request)
    return {'airdrops': sorted(_admin_load()['airdrops'], key=lambda a: -a['scheduledAt'])}


@app.post('/api/reputation/admin/airdrops')
async def admin_schedule(request: Request, payload: Airdrop):
    admin = _require_admin(request)
    recips = []
    for r in payload.recipients[:1000]:
        a = str((r or {}).get('address', ''))
        try:
            amt = float((r or {}).get('amount'))
        except (TypeError, ValueError):
            continue
        if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a) and amt > 0:
            recips.append({'address': a, 'amount': amt})
    if not recips:
        raise HTTPException(400, 'Add at least one valid Solana recipient with an amount.')
    drop = {'id': uuid.uuid4().hex[:12], 'name': payload.name, 'asset': payload.asset, 'recipients': recips,
            'total': sum(r['amount'] for r in recips), 'scheduledAt': payload.scheduledAt, 'note': payload.note,
            'status': 'scheduled', 'createdAt': time.time(), 'createdBy': admin, 'txs': []}
    async with _admin_lock:
        d = _admin_load(); d['airdrops'].append(drop)
        _audit(d, admin, 'schedule-airdrop', f"{payload.name}: {len(recips)} wallets, {drop['total']:,.2f} {payload.asset.upper()}")
        _admin_save(d)
    return {'ok': True, 'airdrop': drop}


class AirdropStatus(BaseModel):
    status: str
    txSig: Optional[str] = None


@app.post('/api/reputation/admin/airdrops/{drop_id}')
async def admin_airdrop_status(request: Request, drop_id: str, payload: AirdropStatus):
    admin = _require_admin(request)
    if payload.status not in ('sent', 'cancelled', 'scheduled'):
        raise HTTPException(400, 'Bad status.')
    verified = None
    if payload.status == 'sent':
        if not payload.txSig or not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', payload.txSig):
            raise HTTPException(400, 'Paste the on-chain transaction signature to mark an airdrop sent.')
        async with httpx.AsyncClient(timeout=20) as http:
            tx = await _rpc(http, 'getTransaction', [payload.txSig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}])
        if not tx:
            raise HTTPException(404, 'That transaction is not on-chain (yet).')
        if (tx.get('meta') or {}).get('err'):
            raise HTTPException(400, 'That transaction failed on-chain.')
        signers = [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]
        if admin not in signers:
            raise HTTPException(400, 'That transaction was not signed by your command center wallet.')
        verified = {'sig': payload.txSig, 'slot': tx.get('slot'), 'blockTime': tx.get('blockTime')}
    async with _admin_lock:
        d = _admin_load()
        drop = next((x for x in d['airdrops'] if x['id'] == drop_id), None)
        if not drop:
            raise HTTPException(404, 'Airdrop not found.')
        drop['status'] = payload.status
        if verified:
            drop['txs'].append(verified)
            for r in drop['recipients']:
                d['badges'].setdefault(r['address'], {})['airdrop-recipient'] = {
                    'id': 'airdrop-recipient', 'label': 'Airdropped', 'icon': '🪂', 'tone': 'gold',
                    'why': f"Received the {drop['name']} airdrop", 'awardedBy': 'FEELESS', 'at': time.time()}
                _badge_cache.pop(r['address'], None)
        _audit(d, admin, f'airdrop-{payload.status}', drop['name'])
        _admin_save(d)
    return {'ok': True, 'airdrop': drop}


class BugReport(BaseModel):
    text: str = Field(min_length=5, max_length=2000)
    page: str = Field(default='', max_length=300)
    kind: str = 'bug'
    address: Optional[str] = None


@app.post('/api/reputation/bugs')
async def report_bug(request: Request, payload: BugReport):
    ip = request.headers.get('x-forwarded-for', request.client.host if request.client else '?').split(',')[0]
    hits = [t for t in _bug_ip_hits.get(ip, []) if time.time() - t < 60]
    if len(hits) >= 3:
        raise HTTPException(429, 'Slow down — 3 reports a minute.')
    _bug_ip_hits[ip] = hits + [time.time()]
    kind = payload.kind if payload.kind in ('bug', 'security', 'idea') else 'bug'
    async with _admin_lock:
        d = _json_load(BUGS_PATH, {'bugs': []})
        d['bugs'].append({'id': uuid.uuid4().hex[:10], 'text': payload.text.strip(), 'page': payload.page, 'kind': kind,
                          'address': (payload.address or '')[:44] or None, 'status': 'open', 'at': time.time()})
        d['bugs'] = d['bugs'][-1000:]
        _json_save(BUGS_PATH, d)
    return {'ok': True}


@app.get('/api/reputation/admin/bugs')
async def admin_bugs(request: Request):
    _require_admin(request)
    return _json_load(BUGS_PATH, {'bugs': []})


@app.post('/api/reputation/admin/bugs/{bug_id}')
async def admin_bug_status(request: Request, bug_id: str, status: str = Query(...)):
    admin = _require_admin(request)
    if status not in ('open', 'fixing', 'fixed', 'wontfix'):
        raise HTTPException(400, 'Bad status.')
    async with _admin_lock:
        d = _json_load(BUGS_PATH, {'bugs': []})
        for b in d['bugs']:
            if b['id'] == bug_id:
                b['status'] = status; b['updatedAt'] = time.time()
        _json_save(BUGS_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'bug-status', f'{bug_id} → {status}'); _admin_save(ad)
    return {'ok': True}


@app.get('/api/reputation/admin/security')
async def admin_security(request: Request):
    _require_admin(request)
    root = Path(__file__).parent
    checks = []

    def check(name, ok, detail, sev='high'):
        checks.append({'name': name, 'ok': bool(ok), 'detail': detail, 'severity': 'ok' if ok else sev})

    for f, label in ((root / 'data' / 'internal.key', 'Internal service key'), (root / '.env', 'Backend .env secrets')):
        if f.exists():
            mode = oct(f.stat().st_mode & 0o777)
            check(f'{label} permissions', (f.stat().st_mode & 0o077) == 0, f'{f.name} is {mode} (should be 0o600)', 'high')
    gi = (root.parent / '.gitignore')
    gtxt = gi.read_text() if gi.exists() else ''
    check('Secrets kept out of git', all(x in gtxt for x in ('.env', 'data/')), '.gitignore covers .env and backend/data/' if gtxt else 'No .gitignore found')
    fe_env = root.parent / 'frontend' / '.env'
    leak = fe_env.exists() and _re.search(r'REACT_APP_[A-Z_]*=.*(api-key|apikey|secret)', fe_env.read_text(), _re.I)
    check('No API keys shipped to the browser', not leak, 'A REACT_APP_ variable contains a key — it is public in the bundle.' if leak else 'No REACT_APP_ secrets found')
    check('RPC key stays server-side', bool(os.environ.get('SOLANA_RPC_URL')), 'Helius RPC is read from backend/.env only', 'medium')
    check('CORS scope', False, "Services allow any origin ('*'). Lock to your domain before launch.", 'medium')
    services = []
    async with httpx.AsyncClient(timeout=4) as http:
        for name, url in (('Market API', 'http://127.0.0.1:5001/api/market/assets'), ('Reputation', 'http://127.0.0.1:5077/api/reputation/health'),
                          ('FeeCats', 'http://127.0.0.1:5088/api/cats/leader'), ('Candles', 'http://127.0.0.1:5099/api/candles/health')):
            t0 = time.time()
            try:
                r = await http.get(url); up = r.status_code < 500
            except Exception:
                up = False
            services.append({'name': name, 'up': up, 'ms': round((time.time() - t0) * 1000)})
    now = time.time()
    recent = [s for s in _status_log if now - s[0] < 3600]
    by = {}
    for _, m, p, st in recent:
        k = f'{st} {m} {_re.sub(r"/[1-9A-HJ-NP-Za-km-z]{32,}|/0x[0-9a-fA-F]{40}", "/:addr", p)}'
        by[k] = by.get(k, 0) + 1
    signals = {'forgedSignatures': sum(1 for s in recent if s[3] == 401), 'replays': sum(1 for s in recent if s[3] == 409),
               'rateLimited': sum(1 for s in recent if s[3] == 429), 'forbidden': sum(1 for s in recent if s[3] == 403),
               'serverErrors': sum(1 for s in recent if s[3] >= 500)}
    chat = _json_load(CHAT_PATH, {})
    rooms = chat.get('rooms', chat) if isinstance(chat, dict) else {}
    msgs24 = sum(1 for msgs in rooms.values() if isinstance(msgs, list) for m in msgs if isinstance(m, dict) and now - (m.get('ts', 0) / (1000 if m.get('ts', 0) > 1e12 else 1)) < 86400)
    bl = _block_load()['wallets']
    bugs = _json_load(BUGS_PATH, {'bugs': []})['bugs']
    score = max(0, 100 - sum(25 if c['severity'] == 'high' else 8 for c in checks if not c['ok']) - (10 if signals['serverErrors'] else 0) - 10 * sum(1 for s in services if not s['up']))
    return {'score': score, 'checks': checks, 'services': services, 'signals': signals,
            'topErrors': sorted(({'key': k, 'count': v} for k, v in by.items()), key=lambda x: -x['count'])[:12],
            'stats': {'chat24h': msgs24, 'chatRooms': len(rooms), 'blocklisted': sum(1 for r in bl.values() if _is_blocked(r)),
                      'openBugs': sum(1 for b in bugs if b['status'] in ('open', 'fixing')), 'customBadges': sum(len(v) for v in _admin_load()['badges'].values())},
            'audit': _admin_load()['audit'][-25:][::-1], 'at': now}


BADGE_CATALOG = [
    {'id': 'fee-holder', 'label': '$FEE Holder', 'icon': '🌿', 'tone': 'mint', 'tier': 1, 'how': 'Hold at least $1 of $FEE in your wallet.'},
    {'id': 'feecat-holder', 'label': 'FEECAT Holder', 'icon': '🐱', 'tone': 'mint', 'tier': 1, 'how': 'Hold at least $1 of FEECAT.'},
    {'id': 'rfee-holder', 'label': 'rFEE Holder', 'icon': '💠', 'tone': 'mint', 'tier': 1, 'how': 'Hold at least $1 of rFEE.'},
    {'id': 'rides-with-fee', 'label': 'Rides with Fee', 'icon': '🐾', 'tone': 'mint', 'tier': 2, 'how': 'Hold a coin the Leader cat is currently in (see FeeCats).'},
    {'id': 'caller', 'label': 'Caller', 'icon': '🎯', 'tone': 'plain', 'tier': 2, 'how': 'Drop a CA in chat — it lands on the Call Ledger and is tracked live.'},
    {'id': 'sharp-caller', 'label': 'Sharp Caller', 'icon': '🎯', 'tone': 'gold', 'tier': 3, 'how': '5+ calls in 30 days with at least half reaching 2×.'},
    {'id': 'feeless-launcher', 'label': 'FEELESS Launcher', 'icon': '🚀', 'tone': 'mint', 'tier': 3, 'how': 'Launch a token through FEELESS (verified on-chain).'},
    {'id': 'trusted-creator', 'label': 'Trusted Creator', 'icon': '🛡️', 'tone': 'mint', 'tier': 3, 'how': 'Have launches tracked by FEELESS with none dumped or rugged.'},
    {'id': 'airdrop-recipient', 'label': 'Airdropped', 'icon': '🪂', 'tone': 'gold', 'tier': 3, 'how': 'Receive a FEELESS airdrop — verified by its on-chain transaction.'},
    {'id': 'fee-whale', 'label': '$FEE Whale', 'icon': '🐋', 'tone': 'gold', 'tier': 4, 'how': 'Hold $1,000 or more of $FEE.'},
    {'id': 'custom', 'label': 'FEELESS Special', 'icon': '⭐', 'tone': 'gold', 'tier': 4, 'how': 'Hand-awarded by the FEELESS team for building, finding bugs or legendary calls.'},
]


# ---- Receipts: every trade/airdrop kept forever, in the smallest verifiable form -------
# One JSON array per line in data/receipts.jsonl (append-only, never rewritten):
#   [blockTime, signature, wallet, kind, [[mint, delta], ...], solDelta, slot]
# The signature is the proof — anything else can be re-derived from the chain.
RECEIPTS_PATH = DATA_DIR / 'receipts.jsonl'
_receipt_lock = asyncio.Lock()
_receipt_sigs = None
WSOL = 'So11111111111111111111111111111111111111112'


def _receipt_rows():
    if not RECEIPTS_PATH.exists():
        return []
    rows = []
    for line in RECEIPTS_PATH.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


class ReceiptIn(BaseModel):
    sig: str
    wallet: str
    kind: str = 'swap'


@app.post('/api/reputation/receipts')
async def store_receipt(payload: ReceiptIn):
    global _receipt_sigs
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', payload.sig) or not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', payload.wallet):
        raise HTTPException(400, 'Bad signature or wallet.')
    kind = payload.kind if payload.kind in ('swap', 'buy', 'sell', 'airdrop', 'launch', 'transfer') else 'swap'
    if _receipt_sigs is None:
        _receipt_sigs = {r[1]: r[2] for r in _receipt_rows()}
    if payload.sig in _receipt_sigs:
        if _receipt_sigs[payload.sig] != payload.wallet:
            raise HTTPException(400, 'That wallet did not sign this transaction.')
        return {'ok': True, 'duplicate': True}
    tx = None
    async with httpx.AsyncClient(timeout=20) as http:
        for _ in range(6):  # freshly-sent txs can take a few seconds to be queryable
            tx = await _rpc(http, 'getTransaction', [payload.sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
            if tx:
                break
            await asyncio.sleep(2)
    if not tx:
        raise HTTPException(404, 'Transaction not found on-chain yet — retry shortly.')
    meta = tx.get('meta') or {}
    if meta.get('err'):
        raise HTTPException(400, 'Transaction failed on-chain; no receipt stored.')
    keys = [k['pubkey'] for k in tx['transaction']['message']['accountKeys']]
    signers = [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]
    if payload.wallet not in signers:
        raise HTTPException(400, 'That wallet did not sign this transaction.')
    deltas = {}
    for side, sign in (('preTokenBalances', -1), ('postTokenBalances', 1)):
        for b in meta.get(side) or []:
            if b.get('owner') == payload.wallet:
                amt = float((b.get('uiTokenAmount') or {}).get('uiAmount') or 0)
                deltas[b['mint']] = deltas.get(b['mint'], 0) + sign * amt
    idx = keys.index(payload.wallet)
    sol = ((meta.get('postBalances') or [0])[idx] - (meta.get('preBalances') or [0])[idx]) / 1e9
    row = [tx.get('blockTime'), payload.sig, payload.wallet, kind,
           [[m, float(f'{d:.9g}')] for m, d in deltas.items() if abs(d) > 0], float(f'{sol:.9g}'), tx.get('slot')]
    async with _receipt_lock:
        if payload.sig not in _receipt_sigs:
            with RECEIPTS_PATH.open('a') as f:
                f.write(json.dumps(row, separators=(',', ':')) + '\n')
            _receipt_sigs[payload.sig] = payload.wallet
    return {'ok': True, 'receipt': row}


@app.get('/api/reputation/receipts/{wallet}')
async def list_receipts(wallet: str, limit: int = 200):
    rows = [r for r in _receipt_rows() if r[2] == wallet]
    rows.sort(key=lambda r: -(r[0] or 0))
    keys = ['t', 'sig', 'wallet', 'kind', 'tokens', 'sol', 'slot']
    return {'wallet': wallet, 'count': len(rows), 'receipts': [dict(zip(keys, r)) for r in rows[:max(1, min(limit, 1000))]]}


# ---- Airdrop engine: hold duration + holder snapshots ------------------------------------
_age_cache = {}
SNAP_PATH = DATA_DIR / 'snapshots.json'


async def _first_active(http, account: str):
    """Oldest on-chain activity of a token account = when this wallet started holding."""
    hit = _age_cache.get(account)
    if hit and time.time() - hit[0] < 6 * 3600:
        return hit[1]
    before, oldest = None, None
    for _ in range(8):
        opts = {'limit': 1000}
        if before:
            opts['before'] = before
        try:
            sigs = await _rpc(http, 'getSignaturesForAddress', [account, opts])
        except Exception:
            break
        if not sigs:
            break
        oldest = sigs[-1].get('blockTime') or oldest
        before = sigs[-1]['signature']
        if len(sigs) < 1000:
            break
    _age_cache[account] = (time.time(), oldest)
    return oldest


@app.get('/api/reputation/admin/holders/ages')
async def admin_holder_ages(request: Request, asset: str = 'fee', limit: int = 150):
    _require_admin(request)
    mints = await _ecosystem_mints()
    mint = mints.get(asset)
    if not mint:
        raise HTTPException(404, 'Unknown asset.')
    data = await _token_holders(mint)
    rows = [r for r in data['rows'] if r.get('tokenAccount')][:max(1, min(limit, 300))]
    sem = asyncio.Semaphore(6)
    out = {}
    async with httpx.AsyncClient(timeout=30) as http:
        async def one(r):
            async with sem:
                out[r['owner']] = await _first_active(http, r['tokenAccount'])
        await asyncio.gather(*(one(r) for r in rows))
    return {'asset': asset, 'since': out, 'note': 'Earliest on-chain activity of each holder\'s token account.'}


def _snaps():
    return _json_load(SNAP_PATH, {'snaps': []})


@app.post('/api/reputation/admin/snapshots')
async def admin_snapshot(request: Request, asset: str = 'fee', label: str = ''):
    admin = _require_admin(request)
    mints = await _ecosystem_mints()
    mint = mints.get(asset)
    if not mint:
        raise HTTPException(404, 'Unknown asset.')
    _holder_cache.pop(mint, None)
    data = await _token_holders(mint)
    snap = {'id': uuid.uuid4().hex[:10], 'asset': asset, 'label': label[:60], 'at': time.time(), 'price': data['price'],
            'rows': [[r['owner'], float(f"{r['amount']:.9g}")] for r in data['rows']]}
    async with _admin_lock:
        d = _snaps(); d['snaps'].append(snap); d['snaps'] = d['snaps'][-60:]; _json_save(SNAP_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'snapshot', f"{asset.upper()} · {len(snap['rows'])} holders"); _admin_save(ad)
    return {'ok': True, 'id': snap['id'], 'holders': len(snap['rows'])}


@app.get('/api/reputation/admin/snapshots')
async def admin_snapshots(request: Request):
    _require_admin(request)
    return {'snaps': [{k: v for k, v in s.items() if k != 'rows'} | {'holders': len(s['rows'])} for s in _snaps()['snaps']][::-1]}


@app.get('/api/reputation/admin/snapshots/{snap_id}/diff')
async def admin_snapshot_diff(request: Request, snap_id: str):
    _require_admin(request)
    snap = next((s for s in _snaps()['snaps'] if s['id'] == snap_id), None)
    if not snap:
        raise HTTPException(404, 'Snapshot not found.')
    mints = await _ecosystem_mints()
    now = {r['owner']: r['amount'] for r in (await _token_holders(mints[snap['asset']]))['rows']}
    then = dict((o, a) for o, a in snap['rows'])
    rows = []
    for o in set(now) | set(then):
        a, b = then.get(o, 0), now.get(o, 0)
        kind = 'new' if not a else 'exited' if not b else 'grew' if b > a * 1.01 else 'shrank' if b < a * 0.99 else 'held'
        rows.append({'owner': o, 'then': a, 'now': b, 'delta': b - a, 'kind': kind})
    rows.sort(key=lambda r: -abs(r['delta']))
    counts = {k: sum(1 for r in rows if r['kind'] == k) for k in ('new', 'exited', 'grew', 'shrank', 'held')}
    return {'snap': {k: v for k, v in snap.items() if k != 'rows'}, 'counts': counts, 'rows': rows[:500],
            'diamondHands': [r['owner'] for r in rows if r['kind'] in ('held', 'grew')]}


# ---- Holder perks: hold $FEE, unlock more FEELESS (no subscriptions) ----------------------
PERK_TIERS = [
    {'tier': 0, 'name': 'Trencher', 'minUsd': 0, 'icon': '🪖', 'perks': ['Chat, profile, / commands', 'Call Ledger + badges', 'Fee live chart mode']},
    {'tier': 1, 'name': 'Fee Friend', 'minUsd': 10, 'icon': '🌿', 'perks': ['/scan any CA (holders, snipers, risk)', 'Glowing name in chat', 'Gold Rush + Neon Cat profile themes']},
    {'tier': 2, 'name': 'Fee Insider', 'minUsd': 100, 'icon': '💎', 'perks': ['/alpha — Fee\'s live read in chat', 'Boost a message (1 per 10 min)', 'Aurora animated profile frame']},
    {'tier': 3, 'name': 'Fee Whale', 'minUsd': 1000, 'icon': '🐋', 'perks': ['/whales — who is accumulating', 'Gold animated profile frame + crown', 'Priority line to FEELESS HQ']},
]
TIER_THEMES = {'goldrush': 1, 'neoncat': 1}
# Avatar rings + name effects. 0 = free for everyone; higher = $FEE holder tier required.
RING_TIERS = {'none': 0, 'mint': 0, 'sunset': 0, 'ocean': 0, 'candy': 0, 'neon': 0, 'ghost': 0,
              'emerald': 1, 'plasma': 1, 'diamond': 2, 'aurora': 2, 'gold': 3, 'royal': 3}
NAMEFX_TIERS = {'none': 0, 'glow': 0, 'gradient': 0, 'rainbow': 1, 'diamond': 2, 'gold': 3}
_perk_cache = {}


async def _perk_tier(address: str):
    address = primary_of(address)
    hit = _perk_cache.get(address)
    if hit and time.time() - hit[0] < 120:
        return hit[1]
    usd = 0.0
    if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address or ''):
        mint = (await _ecosystem_mints()).get('fee')
        if mint:
            try:
                usd = await _holding_usd(address, mint)
            except Exception:
                usd = 0.0
    tier = max(t['tier'] for t in PERK_TIERS if usd >= t['minUsd'])
    if address in _admin_wallets():
        tier = 3
    _perk_cache[address] = (time.time(), (tier, usd))
    return tier, usd


@app.get('/api/reputation/perks/{address}')
async def perks(address: str):
    tier, usd = await _perk_tier(address)
    nxt = next((t for t in PERK_TIERS if t['tier'] == tier + 1), None)
    return {'address': address, 'tier': tier, 'feeUsd': round(usd, 2), 'tiers': PERK_TIERS,
            'next': {'name': nxt['name'], 'needUsd': round(max(0, nxt['minUsd'] - usd), 2)} if nxt else None}


# ---- Click tracking for $TICKERS, CAs and @mentions in chat -------------------------------
CLICKS_PATH = DATA_DIR / 'clicks.json'
_click_ip = {}


class ClickIn(BaseModel):
    kind: str
    value: str = Field(min_length=1, max_length=64)
    room: str = Field(default='', max_length=140)


@app.post('/api/reputation/clicks')
async def track_click(request: Request, payload: ClickIn):
    if payload.kind not in ('ticker', 'ca', 'mention', 'command'):
        raise HTTPException(400, 'Bad kind.')
    ip = request.headers.get('x-forwarded-for', request.client.host if request.client else '?').split(',')[0]
    hits = [t for t in _click_ip.get(ip, []) if time.time() - t < 60]
    if len(hits) >= 60:
        raise HTTPException(429, 'Too many clicks.')
    _click_ip[ip] = hits + [time.time()]
    value = payload.value.strip()
    if payload.kind == 'ticker':
        value = value.upper().lstrip('$')[:12]
    async with _admin_lock:
        d = _json_load(CLICKS_PATH, {})
        key = f'{payload.kind}:{value}'
        rec = d.get(key) or [0, 0, 0]  # [total, last-at, 24h-bucket-start]
        rec[0] += 1
        rec[1] = time.time()
        d[key] = rec
        _json_save(CLICKS_PATH, d)
    return {'ok': True, 'count': rec[0]}


@app.get('/api/reputation/clicks/top')
async def top_clicks(kind: str = '', limit: int = 10):
    d = _json_load(CLICKS_PATH, {})
    rows = [{'kind': k.split(':', 1)[0], 'value': k.split(':', 1)[1], 'count': v[0], 'lastAt': v[1]} for k, v in d.items() if not kind or k.startswith(kind + ':')]
    rows.sort(key=lambda r: -r['count'])
    return {'rows': rows[:max(1, min(limit, 50))]}


# ---- Auto profile: every wallet gets real on-chain stats before it ever sets up ------------
_wstats_cache = {}


@app.get('/api/reputation/wallet-stats/{address}')
async def wallet_stats(address: str):
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        return {'address': address, 'chain': 'evm' if address.startswith('0x') else None, 'supported': False}
    hit = _wstats_cache.get(address)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    out = {'address': address, 'chain': 'solana', 'supported': True}
    async with httpx.AsyncClient(timeout=25) as http:
        try:
            out['sol'] = ((await _rpc(http, 'getBalance', [address])) or {}).get('value', 0) / 1e9
        except Exception:
            out['sol'] = None
        try:
            toks = []
            for prog in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
                r = await _rpc(http, 'getTokenAccountsByOwner', [address, {'programId': prog}, {'encoding': 'jsonParsed'}])
                toks += (r or {}).get('value', [])
            held = [t for t in toks if float(((t['account']['data']['parsed']['info'].get('tokenAmount') or {}).get('uiAmount')) or 0) > 0]
            out['tokensHeld'] = len(held)
        except Exception:
            out['tokensHeld'] = None
        before, oldest, count = None, None, 0
        for _ in range(5):
            opts = {'limit': 1000}
            if before:
                opts['before'] = before
            try:
                sigs = await _rpc(http, 'getSignaturesForAddress', [address, opts])
            except Exception:
                break
            if not sigs:
                break
            count += len(sigs)
            oldest = sigs[-1].get('blockTime') or oldest
            before = sigs[-1]['signature']
            if len(sigs) < 1000:
                break
        out['txCount'] = count
        out['txCountCapped'] = count >= 5000
        out['firstSeen'] = oldest if not out['txCountCapped'] else None
    _wstats_cache[address] = (time.time(), out)
    return out


# ---- Linked identities: one person, every network ------------------------------------------
IDENTITY_PATH = DATA_DIR / 'identities.json'


def _ids():
    return _json_load(IDENTITY_PATH, {'links': {}})


def primary_of(address: str) -> str:
    """Solana account is the primary identity; a linked 0x account resolves to it."""
    return _ids()['links'].get(address, {}).get('primary', address)


def linked_of(address: str):
    p = primary_of(address)
    return sorted({p, *[a for a, v in _ids()['links'].items() if v.get('primary') == p]})


class LinkIn(BaseModel):
    solana: str
    evm: str
    ts: int
    solanaSig: str
    evmSig: str


@app.post('/api/reputation/identity/link')
async def identity_link(payload: LinkIn):
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', payload.solana) or not _re.match(r'^0x[0-9a-fA-F]{40}$', payload.evm):
        raise HTTPException(400, 'Need one Solana and one 0x address.')
    if abs(time.time() - payload.ts) > 300:
        raise HTTPException(401, 'Link expired — try again.')
    msg = f'FEELESS link wallets\nsolana:{payload.solana}\nevm:{payload.evm}\nts:{payload.ts}'
    if not _verify_solana(payload.solana, msg, payload.solanaSig) or not _verify_evm(payload.evm, msg, payload.evmSig):
        raise HTTPException(401, 'Both accounts must sign the link.')
    async with _admin_lock:
        d = _ids()
        d['links'][payload.evm] = {'primary': payload.solana, 'at': time.time()}
        d['links'][payload.solana] = {'primary': payload.solana, 'at': time.time()}
        _json_save(IDENTITY_PATH, d)
    _badge_cache.pop(payload.evm, None); _perk_cache.pop(payload.evm, None)
    return {'ok': True, 'primary': payload.solana, 'linked': linked_of(payload.solana)}


@app.get('/api/reputation/identity/{address}')
async def identity(address: str):
    return {'address': address, 'primary': primary_of(address), 'linked': linked_of(address)}


class ChatDelete(BaseModel):
    room: str
    id: str
    address: str
    ts: int
    signature: str


@app.post('/api/reputation/chat/delete')
async def chat_delete(payload: ChatDelete):
    """Posts can only be deleted on profile walls: by the wall owner (any network they've linked) or by the poster."""
    m = _re.match(r'^wall-(.+)$', payload.room)
    if not m:
        raise HTTPException(403, 'Posts can only be deleted on profile walls.')
    if abs(time.time() - payload.ts) > 120:
        raise HTTPException(401, 'Signature expired.')
    if not _verify_wallet(payload.address, f'FEELESS delete\nroom:{payload.room}\nid:{payload.id}\nts:{payload.ts}', payload.signature):
        raise HTTPException(401, 'Signature does not match this wallet.')
    me = set(linked_of(payload.address))
    async with _chat_lock:
        d = _chat_load()
        msgs = d['rooms'].get(payload.room, [])
        msg = next((x for x in msgs if x['id'] == payload.id), None)
        if not msg:
            raise HTTPException(404, 'Post not found.')
        if primary_of(m.group(1)) not in me and msg.get('address') not in me:
            raise HTTPException(403, 'Only the wall owner or the poster can delete this.')
        d['rooms'][payload.room] = [x for x in msgs if x['id'] != payload.id]
        CHAT_PATH.write_text(json.dumps(d))
    return {'ok': True}
