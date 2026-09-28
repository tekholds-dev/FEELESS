"""
FEELESS Reputation Graph — a standalone, chain-agnostic creator/wallet trust engine.

Every token observation the frontend already makes (from DexScreener/
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
_alchemy = os.environ.get('ALCHEMY_API_KEY', '').strip()
RPC_POOL = ([_dedicated] if _dedicated else []) + ([f'https://solana-mainnet.g.alchemy.com/v2/{_alchemy}'] if _alchemy else []) + [
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
            store = _cached_json(STORE_PATH)
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
                # Jupiter's token index records the deployer ("dev") for Solana coins — exact and fast.
                try:
                    j = (await http.get('https://lite-api.jup.ag/tokens/v2/search', params={'query': mint_address})).json()
                    identity = next((t.get('dev') for t in j if t.get('id') == mint_address and t.get('dev')), None)
                except Exception:
                    identity = None
            if not identity:
                signatures = await _rpc(http, 'getSignaturesForAddress', [mint_address, {'limit': 1000}])
                # Only trust "oldest tx fee payer" when we can actually see the whole history; on a busy
                # coin the 1,000th-newest tx is some random trader, not the creator.
                if signatures and len(signatures) < 1000:
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
    """Brutal, evidence-only scoring. No market evidence → no score. Launch volume alone never earns trust."""
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
    dumped, dead = outcomes.count('dumped'), outcomes.count('dead')
    judged = sum(1 for o in outcomes if o != 'unknown')
    alive = [t for t in tokens.values() if token_outcome(t, now) == 'alive']
    alive_big = sum(1 for t in alive if ((t.get('market') or {}).get('marketCap') or 0) >= 100_000)
    alive_traded = sum(1 for t in alive if ((t.get('market') or {}).get('volume24h') or 0) >= 10_000)
    ghost = sum(1 for t in alive if not ((t.get('market') or {}).get('volume24h') or 0))
    # Serial launching: more than 2 launches inside any 24h window is a farm pattern.
    times = sorted(t.get('firstSeenAt') or 0 for t in tokens.values() if t.get('firstSeenAt'))
    burst = max((sum(1 for u in times if 0 <= u - x <= 86400) for x in times), default=0)
    serial_launcher = burst >= 3
    base = {'tokenCount': total, 'distinctTickers': distinct, 'cloneCount': clones, 'ruggedCount': rugged, 'dumpedCount': dumped, 'deadCount': dead,
            'judgedCount': judged, 'bigWinners': alive_big, 'sustainedCount': sustained, 'renouncedCount': renounced,
            'serialLauncher': serial_launcher, 'launchBurst24h': burst, 'ghostCount': ghost}
    if rugged:
        return {**base, 'score': max(0, 10 - 5 * rugged), 'badge': 'flagged', 'serialDumper': True, 'confidence': 'high', 'reasons': [f'{rugged} rug(s) on record']}
    if judged == 0:
        return {**base, 'score': None, 'badge': 'unproven', 'serialDumper': False, 'confidence': 'none',
                'reasons': ['No market evidence yet — FEELESS will not score a creator on launches alone.'] + (['Rapid-fire launching detected.'] if serial_launcher else [])}
    score = 40
    score += min(sustained, 5) * 10 + min(alive_big, 5) * 8 + min(alive_traded, 5) * 3
    score -= min(dumped, 8) * 15 + min(dead, 8) * 8 + min(clones, 6) * 8 + min(ghost, 6) * 5
    if serial_launcher:
        score -= 10 * (burst - 2)
    # Reputation is a long-lasting asset, not just a risk flag: a clean track record earns a
    # growing tenure bonus the longer it holds up — this is the only way to reach the top tier.
    tenure_days = (now - (entry.get('firstSeen') or now)) / 86400
    clean = not dumped and not rugged and not clones
    tenure_bonus = 0
    if clean:
        if tenure_days >= 365: tenure_bonus = 20
        elif tenure_days >= 180: tenure_bonus = 12
        elif tenure_days >= 90: tenure_bonus = 6
        elif tenure_days >= 30: tenure_bonus = 2
    score += tenure_bonus
    score = max(0, min(100, score))
    dump_rate = dumped / judged if judged else 0
    serial_dumper = dumped >= 2 and dump_rate >= 0.5
    reasons = []
    if dumped: reasons.append(f'{dumped}/{judged} judged launches dumped')
    if dead: reasons.append(f'{dead} launches died')
    if clones: reasons.append(f'{clones} cloned tickers')
    if serial_launcher: reasons.append(f'{burst} launches inside 24h (farm pattern)')
    if ghost: reasons.append(f'{ghost} listed with zero volume')
    if sustained or alive_big: reasons.append(f'{sustained} sustained, {alive_big} over $100K')
    veteran = clean and tenure_days >= 180
    if tenure_bonus: reasons.append(f'{int(tenure_days)}d clean track record (+{tenure_bonus})')
    if serial_dumper or dump_rate >= 0.34 and dumped >= 2:
        badge = 'flagged'
    elif judged >= 2 and not dumped and not clones and not serial_launcher and (sustained or alive_big) and score >= 65:
        badge = 'veteran' if veteran and score >= 80 else 'trusted'
    elif serial_launcher or dumped or clones or ghost:
        badge = 'risky'
    else:
        badge = 'building'
    return {**base, 'score': score, 'badge': badge, 'serialDumper': bool(serial_dumper), 'tenureDays': int(tenure_days), 'veteran': veteran,
            'confidence': 'high' if judged >= 6 else 'medium' if judged >= 3 else 'low', 'reasons': reasons}


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
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in (os.environ.get('ALLOWED_ORIGINS') or '*').split(',') if o.strip()], allow_methods=['*'], allow_headers=['*'])


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


def _hygiene(creator, scored):
    """Launch hygiene from FEELESS intel: snipers + bundled wallets across this creator's launches."""
    h = _json_load(DATA_DIR / 'hygiene.json', {}).get(creator) or {}
    launches = h.get('launches') or {}
    if not launches:
        return {'hygiene': None}
    snip = sum(v.get('snipers', 0) for v in launches.values()); bund = sum(v.get('bundled', 0) for v in launches.values())
    n = len(launches)
    penalty = min(40, round((snip / n) * 1.0 + (bund / n) * 3.0))
    score = scored.get('score')
    adj = max(0, score - penalty) if isinstance(score, (int, float)) else score
    badge = scored.get('badge')
    if n >= 2 and bund / n >= 5:
        badge = 'flagged'
    return {'score': adj, 'badge': badge, 'hygiene': {'launches': n, 'avgSnipers': round(snip / n, 1), 'avgBundled': round(bund / n, 1), 'penalty': penalty}}


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
    out = {'creator': entry['address'], **score_creator(entry)}
    return {**out, **_hygiene(entry['address'], out)}



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
        rows.sort(key=lambda r: (-r['bigWinners'], r['dumpedCount'], -(r['score'] or 0)))
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
        rows.sort(key=lambda r: (-(r['score'] or 0), r['firstSeen']))
    elif view == 'active':
        rows = [r for r in rows if r['badge'] != 'flagged']
        rows.sort(key=lambda r: -(r['lastSeen'] or 0))
    else:
        rows = [r for r in rows if r['badge'] != 'flagged' and r['dumpedCount'] == 0]
        rows.sort(key=lambda r: (r['badge'] != 'trusted', -(r['score'] or 0), -(r['tokenCount'] or 0)))

    return {
        'rows': rows[:50], 'view': view,
        'totalCreators': len(store['creators']),
        'totalTokensTracked': sum(len(e['tokens']) for e in store['creators'].values()),
    }


class WatchPayload(BaseModel):
    ownerWallet: str
    session: str = ''
    chain: str
    address: str
    notifyNewToken: bool = True
    notifyFlag: bool = True
    botEnabled: bool = False
    botBrain: Optional[str] = None


@app.post('/api/reputation/watch')
async def watch_creator(payload: WatchPayload):
    payload.ownerWallet = _session_or_401(payload.ownerWallet, payload.session)
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
    session: str = ''
    chain: str
    address: str


@app.post('/api/reputation/unwatch')
async def unwatch_creator(payload: UnwatchPayload):
    payload.ownerWallet = _session_or_401(payload.ownerWallet, payload.session)
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
                'members': sorted(scored, key=lambda r: -(r['score'] or 0)),
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
    session: str = ''


@app.get('/api/reputation/roadmap/votes')
async def roadmap_votes(wallet: Optional[str] = None):
    store = _load()
    votes = store.setdefault('votes', {})
    return {'counts': {k: len(v) for k, v in votes.items()}, 'mine': [k for k, v in votes.items() if wallet and wallet in v]}


@app.post('/api/reputation/roadmap/vote')
async def roadmap_vote(payload: VotePayload):
    if len(payload.wallet) < 20 or len(payload.itemId) > 64:
        raise HTTPException(400, 'Invalid vote.')
    payload.wallet = _session_or_401(payload.wallet, payload.session)  # one signed wallet, one vote
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
async def upload_image(payload: UploadPayload, request: Request):
    """Images for profiles, launches and seasons. Everyone: 2 MB. A signed-in creator/admin
    (command center session) may upload big GIFs/art up to 25 MB."""
    import base64
    import re
    m = re.match(r'^data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/=]+)$', payload.dataUrl or '')
    if not m:
        raise HTTPException(400, 'Only PNG, JPG, WEBP or GIF images are supported.')
    raw = base64.b64decode(m.group(2))
    try:
        _require_admin(request); cap = 25_000_000
    except HTTPException:
        cap = 2_000_000
    if len(raw) > cap:
        raise HTTPException(413, f'Image must be under {cap // 1_000_000} MB.')
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
        out['snipersHoldingPct'] = round(sum(r['pct'] or 0 for r in wallets if r['owner'] in snipers), 2) if supply else None
        out['bundledHoldingPct'] = round(sum(r['pct'] or 0 for r in wallets if r['owner'] in bundled), 2) if supply else None
        out['devHoldingPct'] = round(sum(r['pct'] or 0 for r in wallets if r['owner'] == creator), 2) if supply and creator else None
        # Live holding of every flagged wallet (not just top holders): 0 = sold out, shown struck through.
        if supply:
            flagged = (sorted(bundled) + [w for w in sorted(snipers) if w not in bundled])[:30]
            sem = asyncio.Semaphore(8)
            async def bal(w):
                async with sem:
                    try:
                        r = await _rpc(http, 'getTokenAccountsByOwner', [w, {'mint': mint}, {'encoding': 'jsonParsed'}])
                        amt = sum(float(((a['account']['data']['parsed']['info'].get('tokenAmount') or {}).get('uiAmount')) or 0) for a in (r or {}).get('value') or [])
                        return w, round(amt / supply * 100, 3)
                    except Exception:
                        return w, None
            out['flaggedHoldings'] = dict(await asyncio.gather(*(bal(w) for w in flagged)))
            fh = out['flaggedHoldings']
            if len(fh) >= 3 and all(v == 0 for v in fh.values()):
                # Every sniper/bundler has sold out: the supply overhang is gone — often the dip entry.
                # Alerts link to the coin's deepest pool so the Trenches chart opens on it.
                try:
                    pools = sorted((await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{mint}')).json().get('pairs') or [], key=lambda p: -((p.get('liquidity') or {}).get('usd') or 0))
                except Exception:
                    pools = []
                pa = pools[0]['pairAddress'] if pools else mint
                sym = ((pools[0].get('baseToken') or {}).get('symbol') if pools else None) or mint[:4]
                if _radar_event('snipers-out', pa, sym, f"All {len(fh)} flagged snipers/bundlers have sold out — no sniper supply left to dump."):
                    asyncio.create_task(_push_snipers_out(mint))
                if creator:
                    notify(creator, 'reward', f"🎯 Every sniper on your coin {sym} has sold out", f'/terminal/chat?chain=solana&pair={pa}&room=bulls')
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
    all_offenders = out.get('bundledWallets', []) + out.get('sniperWallets', [])
    flagged_funders = {w: funder_lookup(w) for w in all_offenders}
    flagged_funders = {w: v for w, v in flagged_funders.items() if v}
    if flagged_funders:
        distinct_funders = {v['funder'] for v in flagged_funders.values()}
        flags.append(f"{len(flagged_funders)} sniper/bundler wallet(s) here were funded by {len(distinct_funders)} wallet(s) already linked to prior rug/snipe launches.")
    out['flags'] = flags
    out['flaggedFunders'] = flagged_funders
    await _record_offenders(mint, out.get('bundledWallets', []), out.get('sniperWallets', []))
    bl = _block_load()
    out['walletRecords'] = {w: {'strikes': len(bl['wallets'].get(w, {}).get('mints', {})), 'blocked': _is_blocked(bl['wallets'].get(w)),
                                 'flaggedFunder': flagged_funders.get(w)}
                            for w in all_offenders}
    _intel_cache[mint] = (time.time(), out)
    try:
        _absorb_intel(mint, out)
    except Exception:
        pass
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


GLOBE_NETS = ['solana', 'ethereum', 'base', 'bsc', 'arbitrum', 'avalanche', 'polygon', 'sui', 'optimism', 'zksync', 'zora', 'cronos', 'unichain', 'worldchain']
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
    """$10M+ coins per chain for the globe, from FEELESS's own DexScreener-backed market feed
    (strictly per chain — a coin only ever orbits the network it actually trades on)."""
    await asyncio.sleep(20)
    while True:
        tokens, ok_chains = {}, set()
        async with httpx.AsyncClient(timeout=20) as http:
            for chain in GLOBE_NETS:
                # page 1 = boosted/trending; page 2 = the chain's main-DEX pools (where the $10M+ coins live)
                for params in ({'kind': 'trending'}, {'kind': 'trending', 'source': 'search'}, {'kind': 'new'}):
                    try:
                        r = await http.get('http://127.0.0.1:5001/api/market/feed', params={'chain': chain, **params})
                        pairs = r.json().get('pairs') or [] if r.status_code == 200 else []
                    except Exception:
                        pairs = []
                    for p in pairs:
                        if p.get('chainId') != chain:
                            continue
                        mc = p.get('marketCap') or p.get('fdv') or 0
                        if not mc or mc < GLOBE_MIN_MC:
                            continue
                        ok_chains.add(chain)
                        bt = p.get('baseToken') or {}
                        row = {'chain': chain, 'address': bt.get('address'), 'symbol': bt.get('symbol'), 'name': bt.get('name'),
                               'imageUrl': (p.get('info') or {}).get('imageUrl'), 'marketCap': mc, 'mcKind': 'market cap' if p.get('marketCap') else 'FDV',
                               'liquidityUsd': (p.get('liquidity') or {}).get('usd'), 'priceUsd': p.get('priceUsd'),
                               'change24h': (p.get('priceChange') or {}).get('h24'), 'volume24h': (p.get('volume') or {}).get('h24') or 0,
                               'pairAddress': p.get('pairAddress')}
                        key = f"{chain}:{row['address']}"
                        if key not in tokens or tokens[key]['volume24h'] < row['volume24h']:
                            tokens[key] = row
                    await asyncio.sleep(0.5)
        if tokens:
            prev = (_globe_cache['data'] or {}).get('tokens') or []
            kept = [t for t in prev if t['chain'] not in ok_chains]
            _globe_cache.update(at=time.time(), data={'tokens': sorted(list(tokens.values()) + kept, key=lambda t: -t['marketCap']),
                                                      'minMarketCap': GLOBE_MIN_MC, 'source': 'DexScreener via FEELESS market feed',
                                                      'chains': sorted(ok_chains | {t['chain'] for t in kept}), 'at': time.time()})
        await asyncio.sleep(300)


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
    rail: Optional[str] = None  # 'feeless' (Meteora DBC config) or 'pump'


@app.post('/api/reputation/feeless-launch')
async def register_feeless_launch(payload: FeelessLaunchPayload):
    """Tag a token as launched on FEELESS — only after the chain confirms this wallet created it."""
    creator = None
    if payload.signature and _re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', payload.signature):
        # Proof from the launch transaction: it succeeded, this wallet signed it, and the new mint signed it.
        async with httpx.AsyncClient(timeout=15) as http:
            tx = await _rpc(http, 'getTransaction', [payload.signature, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
        if tx and not (tx.get('meta') or {}).get('err'):
            signers = [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]
            if payload.wallet in signers and payload.mint in signers:
                creator = payload.wallet
    if not creator:
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
            'signature': payload.signature, 'at': time.time(), 'rail': payload.rail if payload.rail in ('feeless', 'pump') else 'feeless',
            'config': _json_load(LAUNCH_RAIL_PATH, {}).get('config') if payload.rail != 'pump' else None,
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
import hmac

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
                    if rules.get('above') and price >= float(rules['above']):
                        fired.append(('above', f"{sym} hit your target {price:.8g} (≥ {float(rules['above']):.8g})"))
                    if rules.get('below') and price and price <= float(rules['below']):
                        fired.append(('below', f"{sym} fell to {price:.8g} (≤ {float(rules['below']):.8g})"))
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
    # Who called, when, and which coin all come from the signed chat message on the server —
    # a client can't register a call in someone else's name or backdate one.
    src = next((m for m in _chat_load()['rooms'].get(payload.room, []) if m.get('id') == payload.messageId), None)
    if not src or not any(t.get('pairAddress') == payload.pairAddress for t in (src.get('tokens') or [])):
        raise HTTPException(404, 'No matching chat call.')
    payload.callerAddress = src.get('identity') or src.get('address')
    payload.caller = payload.caller if payload.caller == 'anon' else (src.get('username') or 'anon')
    payload.ts = src.get('ts')
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


FEED_CALL_POINTS = ((2, 50), (5, 150), (10, 400))


def _award_feed_call(c):
    # FEEd reputation: a post that turns into a real move pays its author once per milestone.
    if not c['room'].startswith('feed-') or not c.get('callerAddress') or not c['priceAtCall']:
        return
    peak = c['peakPrice'] / c['priceAtCall']
    done = c.setdefault('awarded', [])
    for x, pts in FEED_CALL_POINTS:
        if peak >= x and x not in done:
            done.append(x)
            season_award(primary_of(c['callerAddress']), pts, f"feed-call:{x}x:{c['symbol']}")
            notify(c['callerAddress'], 'reward', f"📈 Your FEEd call on {c['symbol']} hit {x}× — +{pts} season points", f"/terminal/chat?chain={c['chain']}&pair={c['pairAddress']}")


def _record_feed_calls(msg):
    async def run():
        async with _calls_lock:
            d = _calls_load()
            for t in msg['tokens']:
                p = t.get('pair') or {}
                price = float(p.get('priceUsd') or 0)
                if price <= 0:
                    continue
                cid = f"{msg['id']}:{t['pairAddress']}"
                d['calls'].setdefault(cid, {'id': cid, 'messageId': msg['id'], 'room': msg['room'], 'caller': msg['username'][:40], 'callerAddress': msg['address'],
                    'chain': t['chainId'], 'pairAddress': t['pairAddress'], 'mint': t['address'], 'symbol': t.get('symbol'),
                    'imageUrl': (p.get('info') or {}).get('imageUrl'), 'priceAtCall': price, 'mcAtCall': p.get('marketCap') or p.get('fdv'),
                    'at': time.time(), 'lastPrice': price, 'peakPrice': price, 'checkedAt': time.time()})
            _calls_save(d)
    asyncio.create_task(run())


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
                    _award_feed_call(c)
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
async def caller_board(days: int = Query(7, ge=1, le=90), room: Optional[str] = None):
    since = time.time() - days * 86400
    by = {}
    for c in _calls_load()['calls'].values():
        if c['at'] < since or (room and not c['room'].startswith(room)):
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
        'songs': [{'url': str(x.get('url'))[:300], 'title': str(x.get('title') or '')[:60]} for x in (p.get('songs') or [])[:15]
                  if isinstance(x, dict) and _re.match(r'^https://(www\.|m\.|music\.|open\.)?(youtube\.com|youtu\.be|spotify\.com|soundcloud\.com)/', str(x.get('url') or ''))],
        'handle': str(p.get('handle') or '').lower().lstrip('@')[:20] if _re.match(r'^@?[a-z0-9_]{3,20}$', str(p.get('handle') or '').lower()) else '',
        'ring': p.get('ring') if p.get('ring') in RING_TIERS else 'none',
        'nameFx': p.get('nameFx') if p.get('nameFx') in NAMEFX_TIERS else 'none',
        'featuredBadges': list(dict.fromkeys(str(b)[:40] for b in (p.get('featuredBadges') or []) if _re.match(r'^[a-z0-9-]{2,40}$', str(b))))[:3],
    }


class ProfileSave(BaseModel):
    address: str
    message: str
    signature: str
    profile: dict
    target: Optional[str] = None


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
    owner = primary_of(payload.address)
    if payload.target and primary_of(payload.target) != owner:
        raise HTTPException(403, 'This wallet is not linked to that profile.')
    async with _profile_lock:
        d = _profiles_load()
        prev = d['profiles'].get(owner, {})
        if prev.get('lastTs', 0) >= ts:
            raise HTTPException(409, 'Replay rejected — sign a fresh update.')
        clean = _clean_profile(payload.profile)
        if clean['handle'] and any(a != owner and (v or {}).get('handle') == clean['handle'] for a, v in d['profiles'].items()):
            raise HTTPException(409, f"@{clean['handle']} is taken.")
        if clean['featuredBadges']:
            earned = {b['id'] for b in (await wallet_badges(owner))['badges']}
            clean['featuredBadges'] = [b for b in clean['featuredBadges'] if b in earned]
        un, _r = _unlocks(owner)
        if (RING_TIERS[clean['ring']] > tier and f"ring:{clean['ring']}" not in un) or (NAMEFX_TIERS[clean['nameFx']] > tier and f"nameFx:{clean['nameFx']}" not in un):
            raise HTTPException(403, 'That style is a $FEE holder perk — hold more $FEE to unlock it.')
        if TIER_THEMES.get(clean['theme'], 0) > tier:
            raise HTTPException(403, 'That theme is a Fee Friend perk — hold $10+ of $FEE.')
        # Pictures never disappear by accident: an empty avatar/cover keeps the previous one unless
        # the owner explicitly removed it; every image ever set is kept in mediaHistory.
        cleared = set((payload.profile or {}).get('cleared') or [])
        hist = list(prev.get('mediaHistory') or [])
        for k in ('avatarUrl', 'bannerUrl'):
            if not clean.get(k) and prev.get(k) and k not in cleared:
                clean[k] = prev[k]
            if prev.get(k) and prev[k] != clean.get(k):
                hist.append({'field': k, 'url': prev[k], 'at': time.time()})
        d['profiles'][owner] = {**clean, 'mediaHistory': hist[-20:], 'lastTs': ts, 'updatedAt': time.time()}
        tmp = PROFILE_PATH.with_suffix('.tmp'); tmp.write_text(json.dumps(d)); tmp.replace(PROFILE_PATH)  # atomic: no half-written file
    return {'ok': True, 'profile': d['profiles'][owner]}


@app.get('/api/reputation/profile/{address}')
async def get_profile(address: str):
    p = _profiles_load()['profiles'].get(address)
    board = await caller_board(days=30)
    caller = next((r for r in board['rows'] if r.get('callerAddress') == address), None)
    return {'address': address, 'profile': p, 'caller': caller, 'verified': is_verified(address)}


@app.get('/api/reputation/profiles')
async def get_profiles(addresses: str):
    d = _profiles_load()['profiles']
    return {'profiles': {a: {**{k: d[a].get(k) for k in ('displayName', 'avatarUrl', 'accent', 'mood', 'featuredBadges', 'ring', 'nameFx', 'handle')}, 'verified': is_verified(a)} for a in addresses.split(',')[:100] if a in d}}



# ---- Evidence-based blocklist of snipers and bundlers ----------------------------
BLOCK_PATH = DATA_DIR / 'blocklist.json'
_block_lock = asyncio.Lock()
AUTO_BLOCK_STRIKES = 3


def _block_load():
    if BLOCK_PATH.exists():
        try:
            return _cached_json(BLOCK_PATH)
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
    asyncio.create_task(_trace_funders(mint, list(bundled) + list(snipers)))


# ---- Funder graph: who bankrolls sniper/bundler wallets, so a serial funder gets caught even
# before their next puppet wallet snipes anything --------------------------------------------
FUNDERS_PATH = DATA_DIR / 'funders.json'
FUNDER_STRIKE_MINTS = 2   # a funder linked to offenders across 2+ different launches is a pattern
FUNDER_STRIKE_WALLETS = 3  # or has bankrolled 3+ distinct sniper/bundler wallets total
_funder_lock = asyncio.Lock()
_funder_resolved = set()  # offender wallets we've already traced (in-memory, this process)


def _funders_load():
    return _json_load(FUNDERS_PATH, {'funders': {}, 'offenderFunder': {}})


def _is_flagged_funder(rec):
    if not rec:
        return False
    return len(rec.get('mints', {})) >= FUNDER_STRIKE_MINTS or len(rec.get('funded', [])) >= FUNDER_STRIKE_WALLETS


async def _trace_funders(mint, offenders):
    """Best-effort, capped, background: find who funded each new offender wallet's very first
    transaction, and remember it. A funder seen behind offenders on 2+ launches (or 3+ puppet
    wallets) gets flagged — and added to the blocklist itself — so their NEXT batch of fresh
    wallets is already suspect before they've sniped a single thing."""
    todo = [w for w in offenders if w not in _funder_resolved][:8]
    if not todo:
        return
    for w in todo:
        _funder_resolved.add(w)
        try:
            funder = await resolve_funding_source('solana', w)
        except Exception:
            funder = None
        if not funder or funder == w:
            continue
        async with _funder_lock:
            d = _funders_load()
            rec = d['funders'].setdefault(funder, {'mints': {}, 'funded': [], 'firstSeen': time.time()})
            rec['mints'].setdefault(mint, True)
            if w not in rec['funded']:
                rec['funded'].append(w)
            rec['lastSeen'] = time.time()
            d['offenderFunder'][w] = funder
            newly_flagged = _is_flagged_funder(rec) and funder not in (d.get('flagged') or [])
            if newly_flagged:
                d.setdefault('flagged', []).append(funder)
            _json_save(FUNDERS_PATH, d)
        if newly_flagged:
            # The funder becomes a blocklist entry in their own right — 'funder' strikes count
            # exactly like sniping/bundling do, so they auto-block the same way.
            async with _block_lock:
                bl = _block_load()
                brec = bl['wallets'].setdefault(funder, {'mints': {}, 'firstSeen': time.time()})
                for m in d['funders'][funder]['mints']:
                    brec['mints'].setdefault(m, 'funder')
                brec['lastSeen'] = time.time()
                BLOCK_PATH.write_text(json.dumps(bl))


def funder_lookup(wallet: str):
    """Is this wallet's funder already known to have bankrolled other snipe/bundle squads?"""
    d = _funders_load()
    funder = d['offenderFunder'].get(wallet)
    if not funder:
        return None
    rec = d['funders'].get(funder) or {}
    if not _is_flagged_funder(rec):
        return None
    return {'funder': funder, 'otherLaunches': len(rec.get('mints', {})), 'walletsFunded': len(rec.get('funded', []))}


class BlockPayload(BaseModel):
    mint: str
    wallets: list
    reporter: str = ''
    session: str = ''


@app.post('/api/reputation/blocklist')
async def add_to_blocklist(payload: BlockPayload):
    """Only wallets proven by FEELESS's own forensics to have bundled/sniped that mint are accepted.
    The reporter is the signed-in wallet, so every report is attributable. Blocklisting only adds a
    flag and a penalty line; the wallet's full record stays public."""
    payload.reporter = _session_or_401(payload.reporter, payload.session)
    intel = await token_intel('solana', payload.mint)
    evidence = {w: 'bundler' for w in intel.get('bundledWallets', [])}
    evidence.update({w: 'sniper' for w in intel.get('sniperWallets', []) if w not in evidence})
    accepted, rejected, fresh = [], [], []
    async with _block_lock:
        d = _block_load()
        for w in [str(x) for x in payload.wallets[:200]]:
            if w not in evidence:
                rejected.append(w)
                continue
            rec = d['wallets'].setdefault(w, {'mints': {}, 'firstSeen': time.time()})
            if not rec.get('reported'):
                fresh.append(w)
            rec['mints'].setdefault(payload.mint, evidence[w])
            rec['reported'] = True
            rec.setdefault('reports', []).append({'mint': payload.mint, 'role': evidence[w], 'by': (payload.reporter or 'anon')[:64], 'at': time.time()})
            rec['reports'] = rec['reports'][-20:]
            accepted.append(w)
        BLOCK_PATH.write_text(json.dumps(d))
    _intel_cache.pop(payload.mint, None)
    # Season points only for wallets nobody had reported yet: 25 each, capped at 100 per coin.
    if fresh:
        season_award(payload.reporter, min(100, 25 * len(fresh)), f'rug-report:{payload.mint[:8]}')
    return {'accepted': accepted, 'rejected': rejected, 'newlyFlagged': len(fresh)}


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
            return _cached_json(CHAT_PATH)
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
    eg = await evm_gate(room, address or '')
    if eg:
        return eg
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
    signature: str = ''
    session: str = ''
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
    if payload.session:
        if primary_of(session_address(payload.session) or "") != primary_of(payload.address) or not session_address(payload.session):
            raise HTTPException(401, 'Chat session expired — sign in to chat again.')
    elif not _verify_wallet(payload.address, _chat_message_to_sign(payload.room, payload.address, payload.ts, text), payload.signature):
        raise HTTPException(401, 'Signature does not match this wallet.')
    if payload.room == 'feeless-updates' and primary_of(payload.address) not in {primary_of(w) for w in _admin_wallets()}:
        raise HTTPException(403, 'Updates is read-only — only FEELESS admins post here.')
    if payload.room in _ALPHA and not await _alpha_allowed(payload.room, payload.address):
        raise HTTPException(403, f"{_ALPHA[payload.room]['name']} unlocks at ${_ALPHA[payload.room]['minUsd']:,} held in $FEE.")
    eg = await evm_gate(payload.room, payload.address)
    if eg and not eg['allowed']:
        raise HTTPException(403, f"{eg['symbol']} is an EVM coin — link or switch to your 0x account." if eg.get('needsChain') else f"Hold at least ${MIN_HOLD_USD:.0f} of {eg['symbol']} to chat here (you hold ${eg['holdingUsd'] or 0:.2f}).")
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
    if is_muted(payload.address):
        raise HTTPException(403, 'You are muted by FEELESS moderators for now.')
    tier = (await _perk_tier(payload.address))[0]
    boosted = False
    if payload.boost:
        credits = (_pts().get(primary_of(payload.address)) or {}).get('boostCredits', 0)
        if tier < 2 and credits <= 0:
            raise HTTPException(403, 'Boosting is a Fee Insider perk — hold $100+ of $FEE or buy boosts with points.')
        if tier < 2:
            d_ = _pts(); d_[primary_of(payload.address)]['boostCredits'] = credits - 1; _json_save(POINTS_PATH, d_)
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
        verdict = _spam_check(d, payload.room, payload.address, text, tier)
        if verdict:
            CHAT_PATH.write_text(json.dumps(d))
            raise HTTPException(429 if verdict.startswith('Slow') else 403, verdict)
        d['lastTs'][payload.address] = payload.ts
        d.setdefault('lastAt', {})[payload.address] = time.time()
        if boosted:
            _boost_last[payload.address] = time.time()
        msg = {'id': uuid.uuid4().hex[:16], 'handle': handle_of(primary_of(payload.address)), 'room': payload.room, 'address': payload.address, 'chain': 'evm' if payload.address.startswith('0x') else 'solana',
               'tier': tier, 'boosted': boosted,
               'username': _display_name(primary_of(payload.address)), 'identity': primary_of(payload.address), 'text': text, 'ts': int(time.time() * 1000),
               'parentId': payload.parentId, 'mentions': sorted(set(MENTION_RE.findall(text)))[:10], 'tokens': tokens,
               'profile': {'address': primary_of(payload.address), 'chain': 'solana' if not primary_of(payload.address).startswith('0x') else 'evm'}}
        room = d['rooms'].setdefault(payload.room, [])
        room.append(msg)
        _track_pin(d, payload.room, room, payload.parentId)
        try:
            if payload.room.startswith('wall-'):
                notify(payload.room[5:], 'wall', f"@{handle_of(primary_of(payload.address))} wrote on your wall: {text[:80]}", f"/terminal/profile/{primary_of(payload.room[5:])}", payload.address)
            for h in msg['mentions']:
                who = next((a for a, v in _profiles_load()['profiles'].items() if (v or {}).get('handle') == h.lower()), None)
                if who:
                    notify(who, 'mention', f"@{handle_of(primary_of(payload.address))} mentioned you: {text[:80]}", '/terminal/chat', payload.address)
        except Exception:
            pass
        d['rooms'][payload.room] = room[-300:]
        CHAT_PATH.write_text(json.dumps(d))
    if payload.room.startswith('feed-') and tokens:
        _record_feed_calls(msg)
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


ALPHA_ROOMS = [{'id': 'alpha-100', 'name': '$100 Club', 'minUsd': 100, 'icon': '🥉', 'vibe': 'First look at FeeCat calls + early meta chatter'},
               {'id': 'alpha-1k', 'name': '$1K Vault', 'minUsd': 1_000, 'icon': '🥈', 'vibe': 'Deeper calls, Shield intel, launch previews'},
               {'id': 'alpha-10k', 'name': '$10K Council', 'minUsd': 10_000, 'icon': '🥇', 'vibe': 'Council votes, pool-builder strategy, direct line to the team'},
               {'id': 'alpha-1m', 'name': '$1M Throne', 'minUsd': 1_000_000, 'icon': '👑', 'vibe': 'The throne room. Legends only.'}]
_ALPHA = {r['id']: r for r in ALPHA_ROOMS}


async def _fee_usd(address: str) -> float:
    mint = (await _ecosystem_mints()).get('fee')
    if not mint or not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address or ''):
        return 0.0
    try:
        return round(await _holding_usd(address, mint) or 0, 2)
    except Exception:
        return 0.0


async def _alpha_allowed(room: str, address: str) -> bool:
    r = _ALPHA.get(room)
    if not r:
        return True
    a = primary_of(address or '')
    return bool(a) and (a in _admin_wallets() or await _fee_usd(a) >= r['minUsd'])


@app.get('/api/reputation/alpha-rooms')
async def alpha_rooms(address: str = ''):
    held = await _fee_usd(primary_of(address)) if address else 0.0
    admin = primary_of(address) in _admin_wallets() if address else False
    d = _chat_load()
    return {'holdingUsd': held, 'rooms': [{**r, 'unlocked': admin or held >= r['minUsd'], 'messages': len(d['rooms'].get(r['id'], []))} for r in ALPHA_ROOMS]}


@app.get('/api/reputation/chat/{room}')
async def chat_room(room: str, session: str = ''):
    if room in _ALPHA and not await _alpha_allowed(room, session_address(session) or ''):
        raise HTTPException(403, f"{_ALPHA[room]['name']} unlocks at ${_ALPHA[room]['minUsd']:,} held in $FEE.")
    d = _chat_load()
    msgs = d['rooms'].get(room, [])[-120:]
    pin = (d.get('pins') or {}).get(room)
    pinned = None
    if pin and time.time() - pin['at'] < PIN_SECONDS:
        pinned = next((m for m in d['rooms'].get(room, []) if m['id'] == pin['id']), None)
        if pinned:
            pinned = {**pinned, 'pinnedFor': round(PIN_SECONDS - (time.time() - pin['at']))}
    return {'room': room, 'messages': msgs, 'pinned': pinned}


# ---- Chat security: bots, raids, floods, link spam -------------------------------------------
PIN_SECONDS = 30
PIN_REPLIES = 3
_URL_RE = _re.compile(r'https?://([^/\s]+)', _re.I)
SAFE_HOSTS = ('dexscreener.com', 'solscan.io', 'etherscan.io', 'basescan.org', 'x.com', 'twitter.com', 'pump.fun', 'jup.ag', 'birdeye.so', 'youtube.com', 'youtu.be', 'spotify.com')


def _norm(text):
    return _re.sub(r'[^a-z0-9$]+', ' ', text.lower()).strip()[:200]


def _spam_check(d, room, address, text, tier):
    """Returns a user-facing reason to reject, or None. Stateful in the chat store (d['guard']).
    Repeat offenders are auto-muted so bots burn their wallets, not the room."""
    now = time.time(); g = d.setdefault('guard', {}); a = primary_of(address)
    until = (g.get('cool') or {}).get(a, 0)
    if now < until:
        return f'Slow down — cooling off for {int(until - now)}s.'
    hist = [x for x in (g.setdefault('recent', {}).get(a) or []) if now - x[0] < 600]
    n = _norm(text)
    # 1) the same wallet repeating itself
    if n and any(x[1] == n for x in hist):
        g['recent'][a] = hist
        return 'You already posted that — no repeats.'
    # 2) flooding
    if sum(1 for x in hist if now - x[0] < 60) >= 8:
        g.setdefault('cool', {})[a] = now + 600
        _guard_log(g, 'flood', a, room, text)
        return 'Slow down — too many messages; 10 minute cooldown.'
    # 3) link spam from unproven accounts
    hosts = [h.lower().lstrip('www.') for h in _URL_RE.findall(text)]
    if tier < 1 and any(not any(h == s_ or h.endswith('.' + s_) for s_ in SAFE_HOSTS) for h in hosts):
        _guard_log(g, 'link', a, room, text)
        return 'Outside links unlock at Fee Friend tier — only trusted sites (DexScreener, Solscan, X, …) for now.'
    # 4) coordinated raids: the same text from 3+ wallets inside 2 minutes
    raid = g.setdefault('texts', {}).setdefault(room, {})
    wallets = {w: t for w, t in (raid.get(n) or {}).items() if now - t < 120} if n and len(n) > 6 else {}
    wallets[a] = now
    if n and len(n) > 6:
        raid[n] = wallets
        if len(raid) > 500:
            for k in list(raid)[:250]:
                raid.pop(k, None)
    if len(wallets) >= 3:
        for w in wallets:
            g.setdefault('cool', {})[w] = now + 1800
        _guard_log(g, 'raid', a, room, text, wallets=list(wallets))
        return 'Coordinated copy-paste detected — these wallets are muted for 30 minutes.'
    hist.append((now, n)); g['recent'][a] = hist[-20:]
    return None


def _guard_log(g, kind, address, room, text, wallets=None):
    log = g.setdefault('log', [])
    log.insert(0, {'kind': kind, 'address': address, 'room': room, 'text': text[:120], 'wallets': wallets, 'at': time.time()})
    g['log'] = log[:300]


def _track_pin(d, room, msgs, parent_id):
    """The first message in a room to draw PIN_REPLIES replies gets pinned for PIN_SECONDS."""
    if not parent_id:
        return
    replies = sum(1 for m in msgs if m.get('parentId') == parent_id)
    pins = d.setdefault('pins', {})
    cur = pins.get(room)
    if replies >= PIN_REPLIES and (not cur or time.time() - cur['at'] >= PIN_SECONDS) and (not cur or cur['id'] != parent_id):
        pins[room] = {'id': parent_id, 'at': time.time(), 'replies': replies}


@app.get('/api/reputation/admin/chat-guard')
async def admin_chat_guard(request: Request):
    _require_admin(request)
    g = _chat_load().get('guard') or {}
    now = time.time()
    return {'log': g.get('log', [])[:100], 'cooling': sorted(({'address': a, 'secondsLeft': int(t - now)} for a, t in (g.get('cool') or {}).items() if t > now), key=lambda x: -x['secondsLeft'])}


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
    try:
        head = payload.text.split('\n', 1)[0][:120]
        followers = [e for e in _push_load()['subs'].values() if (e.get('prefs') or {}).get('followFee')]
        for e in followers[:500]:
            asyncio.get_running_loop().run_in_executor(None, _send_push, e['subscription'], 'Fee 🐱 just traded', head, f"/terminal/coin/solana/{payload.pairAddress}", 'fee-copy')
    except Exception:
        pass
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
    invited = len(_json_load(REF_PATH, {'by': {}})['by'].get(address, []))
    if invited >= 3:
        badges.append({'id': 'recruiter', 'label': 'Recruiter' if invited < 10 else 'Legendary Recruiter', 'icon': '📣', 'tone': 'gold' if invited >= 10 else 'mint', 'why': f'Invited {invited} wallets to FEELESS'})
    if 'badge:points-og' in _unlocks(address)[0]:
        badges.append({'id': 'points-og', 'label': 'Points OG', 'icon': '💠', 'tone': 'gold', 'why': 'Spent 2,000 earned points on it'})
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
        'endpoint': _re.sub(r'(api[-_]?key=)[^&]+', r'\1•••', endpoint), 'dedicated': endpoint == _dedicated,
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
    owners = env or [FEE_CREATOR_WALLET]
    try:
        granted = [a for a, g in _json_load(DATA_DIR / 'roles.json', {'grants': {}})['grants'].items() if g.get('role') in ('admin', 'moderator', 'marketing')]
    except Exception:
        granted = []
    return owners + granted


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


_parse_cache = {}


def _cached_json(path):
    """Parse a JSON store once per on-disk version (mtime+size). Hot endpoints read these on every
    request; re-parsing multi-MB files each time is what would melt under thousands of users."""
    st = path.stat()
    key = (st.st_mtime_ns, st.st_size)
    hit = _parse_cache.get(str(path))
    if hit and hit[0] == key:
        return hit[1]
    obj = json.loads(path.read_text())
    _parse_cache[str(path)] = (key, obj)
    return obj


def _json_load(path, default):
    try:
        return _cached_json(path)
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
    if abs(time.time() - ts_i) > 86400:
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
    {'id': 'recruiter', 'label': 'Recruiter', 'icon': '📣', 'tone': 'mint', 'tier': 2, 'how': 'Invite 3 wallets with your invite link (10 = Legendary Recruiter).'},
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


_receipt_hits: dict = {}


@app.post('/api/reputation/receipts')
async def store_receipt(payload: ReceiptIn, request: Request):
    global _receipt_sigs
    ip = request.client.host if request.client else '?'
    now = time.time(); hits = [t for t in _receipt_hits.get(ip, []) if now - t < 60]
    if len(hits) >= 20:  # each receipt costs RPC lookups; cap per IP
        raise HTTPException(429, 'Too many receipts — slow down.')
    _receipt_hits[ip] = hits + [now]
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', payload.sig) or not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', payload.wallet):
        raise HTTPException(400, 'Bad signature or wallet.')
    kind = payload.kind if payload.kind in ('swap', 'buy', 'sell', 'airdrop', 'launch', 'transfer', 'pool', 'claim') else 'swap'
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
           [[m, float(f'{d:.9g}')] for m, d in deltas.items() if abs(d) > 0], float(f'{sol:.9g}'), tx.get('slot'), (meta.get('fee') or 0) / 1e9]
    async with _receipt_lock:
        if payload.sig not in _receipt_sigs:
            with RECEIPTS_PATH.open('a') as f:
                f.write(json.dumps(row, separators=(',', ':')) + '\n')
            _receipt_sigs[payload.sig] = payload.wallet
            try:  # confirmed on-chain → a receipt notification (the bell), linking the tx
                label = {'swap': 'Swap', 'buy': 'Buy', 'sell': 'Sell', 'launch': 'Launch', 'pool': 'Pool creation', 'airdrop': 'Airdrop', 'transfer': 'Transfer', 'claim': 'Creator fee claim'}[kind]
                notify(payload.wallet, 'reward', f"✅ {label} confirmed on-chain · {sol:+.4f} SOL", f'https://solscan.io/tx/{payload.sig}')
            except Exception:
                pass
    return {'ok': True, 'receipt': row}


@app.get('/api/reputation/receipts/{wallet}')
async def list_receipts(wallet: str, limit: int = 200):
    rows = [r for r in _receipt_rows() if r[2] == wallet]
    rows.sort(key=lambda r: -(r[0] or 0))
    keys = ['t', 'sig', 'wallet', 'kind', 'tokens', 'sol', 'slot', 'fee']
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
    signature: str = ''
    session: str = ''


@app.post('/api/reputation/chat/delete')
async def chat_delete(payload: ChatDelete):
    """Posts can only be deleted on profile walls: by the wall owner (any network they've linked) or by the poster."""
    m = _re.match(r'^wall-(.+)$', payload.room)
    if not m:
        raise HTTPException(403, 'Posts can only be deleted on profile walls.')
    if abs(time.time() - payload.ts) > 120:
        raise HTTPException(401, 'Signature expired.')
    if payload.session:
        if primary_of(session_address(payload.session) or "") != primary_of(payload.address) or not session_address(payload.session):
            raise HTTPException(401, 'Chat session expired.')
    elif not _verify_wallet(payload.address, f'FEELESS delete\nroom:{payload.room}\nid:{payload.id}\nts:{payload.ts}', payload.signature):
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


# ---- Trading fees & discounts, controlled only by the creator wallet -----------------------
# Jupiter's integrator fee: charged via a referral account the creator owns (50–255 bps allowed).
FEE_DEFAULTS = {'platformFeeBps': 0, 'referralAccount': '', 'tierDiscountPct': {'0': 0, '1': 10, '2': 25, '3': 50},
                'zeroFeeMints': [], 'promo': {'label': '', 'discountPct': 0, 'until': 0}}
JUP_MIN_BPS, JUP_MAX_BPS = 50, 255


def _fee_cfg():
    d = _admin_load()
    cfg = {**FEE_DEFAULTS, **(d.get('fees') or {})}
    cfg['tierDiscountPct'] = {**FEE_DEFAULTS['tierDiscountPct'], **(cfg.get('tierDiscountPct') or {})}
    return cfg


async def effective_fee(wallet: str, input_mint: str = '', output_mint: str = ''):
    cfg = _fee_cfg()
    base = int(cfg['platformFeeBps'] or 0)
    notes = []
    if not base or not cfg['referralAccount']:
        return {'bps': 0, 'baseBps': base, 'notes': ['No FEELESS fee on this trade.'], 'referralAccount': None}
    mints = await _ecosystem_mints()
    if input_mint in cfg['zeroFeeMints'] or output_mint in cfg['zeroFeeMints'] or input_mint in mints.values() or output_mint in mints.values():
        return {'bps': 0, 'baseBps': base, 'notes': ['$FEE ecosystem trades are fee-free.'], 'referralAccount': None}
    tier = (await _perk_tier(wallet))[0] if wallet else 0
    disc = float(cfg['tierDiscountPct'].get(str(tier), 0))
    promo = cfg.get('promo') or {}
    if promo.get('discountPct') and time.time() < float(promo.get('until') or 0):
        disc = max(disc, float(promo['discountPct']))
        notes.append(f"{promo.get('label') or 'Promo'}: {promo['discountPct']:.0f}% off")
    bps = round(base * (1 - disc / 100))
    if disc:
        notes.append(f'{disc:.0f}% holder discount (tier {tier})')
    if bps < JUP_MIN_BPS:
        notes.append('Below Jupiter\'s 0.5% minimum — waived.')
        bps = 0
    return {'bps': min(bps, JUP_MAX_BPS), 'baseBps': base, 'notes': notes, 'referralAccount': cfg['referralAccount'] if bps else None}


@app.get('/api/reputation/fees/quote')
async def fee_quote(wallet: str = '', inputMint: str = '', outputMint: str = ''):
    out = await effective_fee(wallet, inputMint, outputMint)
    return {k: v for k, v in out.items() if k != 'referralAccount'} | {'active': bool(out['bps'])}


@app.get('/api/reputation/internal/fees')
async def internal_fees(request: Request, wallet: str = '', inputMint: str = '', outputMint: str = ''):
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), _internal_key()):
        raise HTTPException(403, 'Internal only.')
    return await effective_fee(wallet, inputMint, outputMint)


class FeeCfg(BaseModel):
    platformFeeBps: int = Field(ge=0, le=JUP_MAX_BPS)
    referralAccount: str = ''
    tierDiscountPct: dict = {}
    zeroFeeMints: list = []
    promo: dict = {}


@app.get('/api/reputation/admin/fees')
async def admin_fees_get(request: Request):
    _require_admin(request)
    return {'fees': _fee_cfg(), 'limits': {'minBps': JUP_MIN_BPS, 'maxBps': JUP_MAX_BPS}}


@app.post('/api/reputation/admin/fees')
async def admin_fees_set(request: Request, payload: FeeCfg):
    admin = _require_admin(request)
    if payload.referralAccount and not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', payload.referralAccount):
        raise HTTPException(400, 'Referral account must be a Solana address.')
    if payload.platformFeeBps and payload.platformFeeBps < JUP_MIN_BPS:
        raise HTTPException(400, f'Jupiter needs at least {JUP_MIN_BPS} bps (0.5%) — or set 0 for no fee.')
    tiers = {str(k): max(0.0, min(100.0, float(v))) for k, v in (payload.tierDiscountPct or {}).items() if str(k) in ('0', '1', '2', '3')}
    zero = [m for m in payload.zeroFeeMints[:50] if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', str(m))]
    promo = {'label': str((payload.promo or {}).get('label') or '')[:40], 'discountPct': max(0.0, min(100.0, float((payload.promo or {}).get('discountPct') or 0))),
             'until': float((payload.promo or {}).get('until') or 0)}
    async with _admin_lock:
        d = _admin_load()
        d['fees'] = {'platformFeeBps': payload.platformFeeBps, 'referralAccount': payload.referralAccount, 'tierDiscountPct': tiers, 'zeroFeeMints': zero, 'promo': promo}
        _audit(d, admin, 'fees', f"{payload.platformFeeBps} bps · discounts {tiers} · promo {promo['discountPct']:.0f}%")
        _admin_save(d)
    return {'ok': True, 'fees': _fee_cfg()}


# ---- Chat sessions: sign once, chat for 7 days --------------------------------------------
import secrets as _secrets
SESSIONS_PATH = DATA_DIR / 'chat_sessions.json'
SESSION_TTL = 7 * 86400


def _sess():
    return _json_load(SESSIONS_PATH, {'s': {}})


def session_address(token: str):
    if not token:
        return None
    rec = _sess()['s'].get(hashlib.sha256(token.encode()).hexdigest())
    if not rec or time.time() > rec['exp']:
        return None
    return rec['address']


class SessionIn(BaseModel):
    address: str
    ts: int
    signature: str


@app.post('/api/reputation/chat/session')
async def chat_session(payload: SessionIn):
    if abs(time.time() - payload.ts) > 300:
        raise HTTPException(401, 'Signature expired — try again.')
    if not _verify_wallet(payload.address, f'FEELESS chat session\naddress:{payload.address}\nts:{payload.ts}', payload.signature):
        raise HTTPException(401, 'Signature does not match this wallet.')
    token = _secrets.token_urlsafe(32)
    async with _admin_lock:
        d = _sess()
        now = time.time()
        d['s'] = {k: v for k, v in d['s'].items() if v['exp'] > now}
        d['s'][hashlib.sha256(token.encode()).hexdigest()] = {'address': payload.address, 'exp': now + SESSION_TTL}
        _json_save(SESSIONS_PATH, d)
    return {'token': token, 'expiresAt': time.time() + SESSION_TTL}


def handle_of(address: str) -> str:
    p = _profiles_load()['profiles'].get(address) or {}
    return p.get('handle') or address[:6].lower()


@app.get('/api/reputation/resolve/{query}')
async def resolve_profile(query: str):
    """@handle, display name or wallet address → profile address (for search + mentions)."""
    q = query.strip().lstrip('@')
    if _re.match(r'^0x[0-9a-fA-F]{40}$', q):
        return {'address': primary_of(q), 'handle': handle_of(primary_of(q))}
    if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', q):
        # Only wallets become profiles; token mints / pools stay coin searches.
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                info = await _rpc(http, 'getAccountInfo', [q, {'encoding': 'base64'}])
            owner = ((info or {}).get('value') or {}).get('owner')
        except Exception:
            owner = None
        if owner in (None, '11111111111111111111111111111111'):
            return {'address': primary_of(q), 'handle': handle_of(primary_of(q))}
        raise HTTPException(404, 'That address is a token or program, not a wallet.')
    ql = q.lower()
    for a, v in _profiles_load()['profiles'].items():
        if (v or {}).get('handle') == ql or str((v or {}).get('displayName') or '').lower() == ql:
            return {'address': a, 'handle': handle_of(a)}
    raise HTTPException(404, 'No profile with that name.')


@app.get('/api/reputation/activity/{address}')
async def activity(address: str, limit: int = 30):
    me = set(linked_of(address))
    rows = []
    for room, msgs in _chat_load()['rooms'].items():
        for m in msgs:
            if m.get('address') in me or (m.get('profile') or {}).get('address') in me:
                rows.append({'room': room, 'id': m['id'], 'text': m['text'][:200], 'ts': m['ts'], 'tokens': [t.get('symbol') for t in m.get('tokens') or []]})
    rows.sort(key=lambda r: -r['ts'])
    return {'address': address, 'posts': rows[:max(1, min(limit, 100))], 'handle': handle_of(primary_of(address))}


@app.get('/api/reputation/search')
async def search_profiles(q: str, limit: int = 6):
    """Profile search for the header search bar: @handle / display-name prefix matches."""
    ql = q.strip().lstrip('@').lower()
    if len(ql) < 2:
        return {'profiles': []}
    rows = []
    for a, v in _profiles_load()['profiles'].items():
        v = v or {}
        h, n = (v.get('handle') or ''), str(v.get('displayName') or '').lower()
        score = 3 if h == ql else 2 if h.startswith(ql) else 1 if n.startswith(ql) or ql in h else 0
        if score:
            rows.append((score, {'address': a, 'handle': h or a[:6].lower(), 'displayName': v.get('displayName'), 'avatarUrl': v.get('avatarUrl')}))
    rows.sort(key=lambda r: -r[0])
    return {'profiles': [r[1] for r in rows[:max(1, min(limit, 20))]]}



# ---- Live FEELESS intelligence counts (Learn tab) ------------------------------------------
_marked = {'snipers': set(), 'bundlers': set(), 'mints': set()}


def _absorb_intel(mint, out):
    creator = out.get('creator') if isinstance(out.get('creator'), str) else (out.get('creator') or {}).get('address')
    if creator:
        hp = DATA_DIR / 'hygiene.json'
        d = _json_load(hp, {})
        d.setdefault(creator, {'launches': {}})['launches'][mint] = {'snipers': len(out.get('sniperWallets') or []), 'bundled': len(out.get('bundledWallets') or [])}
        _json_save(hp, d)
    for w in out.get('sniperWallets') or []:
        _marked['snipers'].add(w if isinstance(w, str) else (w or {}).get('wallet') or (w or {}).get('owner'))
    for w in out.get('bundledWallets') or []:
        _marked['bundlers'].add(w if isinstance(w, str) else (w or {}).get('wallet') or (w or {}).get('owner'))
    _marked['mints'].add(mint)


_stats_cache = {'at': 0, 'data': None, 'lock': None}


@app.get('/api/reputation/stats')
async def live_stats():
    # Many viewers, one computation: recompute at most every 15s (and never concurrently).
    if _stats_cache['data'] and time.time() - _stats_cache['at'] < 15:
        return _stats_cache['data']
    if _stats_cache['lock'] is None:
        _stats_cache['lock'] = asyncio.Lock()
    async with _stats_cache['lock']:
        if _stats_cache['data'] and time.time() - _stats_cache['at'] < 15:
            return _stats_cache['data']
        data = await _live_stats_compute()
        _stats_cache.update(at=time.time(), data=data)
        return data


async def _live_stats_compute():
    for mint, (_, out) in list(_intel_cache.items()):
        if out:
            _absorb_intel(mint, out)
    bl = _block_load()['wallets']
    for w, r in bl.items():
        kinds = set(((r or {}).get('mints') or {}).values())
        if kinds & {'sniper', 'snipe'}:
            _marked['snipers'].add(w)
        if kinds & {'bundler', 'bundle'}:
            _marked['bundlers'].add(w)
    store = _load()
    scores = [score_creator(c) for c in store['creators'].values()]
    fd = _funders_load()
    return {'snipers': len(_marked['snipers'] - {None}), 'bundlers': len(_marked['bundlers'] - {None}),
            'blocklisted': sum(1 for r in bl.values() if _is_blocked(r)), 'mintsScanned': len(_marked['mints'] | set(store['mints'])),
            'creators': len(store['creators']), 'trustedCreators': sum(1 for x in scores if x.get('badge') == 'trusted'),
            'flaggedCreators': sum(1 for x in scores if x.get('badge') == 'flagged'),
            'flaggedFunders': len(fd.get('flagged') or []), 'walletsTraced': len(fd.get('offenderFunder') or {}), 'at': time.time()}


# ---- Invite / promo links: every wallet gets one ---------------------------------------------
REF_PATH = DATA_DIR / 'referrals.json'


class RefIn(BaseModel):
    address: str
    ref: str
    session: str


@app.post('/api/reputation/referral')
async def claim_referral(payload: RefIn):
    """Credit the inviter once. Proof of wallet ownership = the invitee's signed chat session."""
    if primary_of(session_address(payload.session) or "") != primary_of(payload.address) or not session_address(payload.session):
        raise HTTPException(401, 'Sign in to chat first.')
    inviter = _code_owner(payload.ref)
    if not inviter:
        try:
            inviter = (await resolve_profile(payload.ref))['address']
        except HTTPException:
            raise HTTPException(404, 'Unknown invite code.')
    me = primary_of(payload.address)
    if inviter == me:
        raise HTTPException(400, "You can't invite yourself.")
    async with _admin_lock:
        d = _json_load(REF_PATH, {'by': {}, 'of': {}})
        if me in d['of']:
            return {'ok': True, 'already': True, 'inviter': d['of'][me]}
        d['of'][me] = inviter
        d['by'].setdefault(inviter, []).append({'address': me, 'at': time.time()})
        _json_save(REF_PATH, d)
    _badge_cache.pop(inviter, None)
    notify(inviter, 'invite', f'@{handle_of(me)} joined with your invite link — claim +75 points.', f'/terminal/profile/{inviter}', me)
    return {'ok': True, 'inviter': inviter}


@app.get('/api/reputation/referral/{address}')
async def referral_info(address: str):
    a = primary_of(address)
    d = _json_load(REF_PATH, {'by': {}, 'of': {}})
    invited = d['by'].get(a, [])
    return {'address': a, 'code': invite_code(a), 'handle': handle_of(a), 'invited': len(invited), 'recent': invited[-10:][::-1], 'invitedBy': d['of'].get(a)}


@app.get('/api/reputation/admin/referrals')
async def admin_referrals(request: Request):
    _require_admin(request)
    d = _json_load(REF_PATH, {'by': {}, 'of': {}})
    rows = sorted(({'address': a, 'handle': handle_of(a), 'invited': len(v)} for a, v in d['by'].items()), key=lambda r: -r['invited'])
    return {'total': len(d['of']), 'top': rows[:50]}


# ---- Ads & announcements (creator wallet only) ----------------------------------------------
ADS_PATH = DATA_DIR / 'ads.json'
AD_PLACEMENTS = ('banner', 'ticker', 'trenches', 'profile')


class AdIn(BaseModel):
    id: Optional[str] = None
    title: str = Field(min_length=2, max_length=60)
    text: str = Field(default='', max_length=200)
    url: str = ''
    imageUrl: str = ''
    placement: str = 'banner'
    startsAt: float = 0
    endsAt: float = 0
    active: bool = True
    sponsor: str = Field(default='', max_length=40)


@app.get('/api/reputation/ads')
async def public_ads(placement: str = 'banner'):
    now = time.time()
    ads = [a for a in _json_load(ADS_PATH, {'ads': []})['ads'] if a['active'] and a['placement'] == placement and (not a['startsAt'] or a['startsAt'] <= now) and (not a['endsAt'] or now < a['endsAt'])]
    return {'ads': [{k: a[k] for k in ('id', 'title', 'text', 'url', 'imageUrl', 'sponsor')} for a in ads]}


@app.post('/api/reputation/ads/{ad_id}/event')
async def ad_event(ad_id: str, kind: str = Query('view')):
    if kind not in ('view', 'click'):
        raise HTTPException(400, 'Bad event.')
    async with _admin_lock:
        d = _json_load(ADS_PATH, {'ads': []})
        for a in d['ads']:
            if a['id'] == ad_id:
                a[kind + 's'] = a.get(kind + 's', 0) + 1
        _json_save(ADS_PATH, d)
    return {'ok': True}


@app.get('/api/reputation/admin/ads')
async def admin_ads(request: Request):
    _require_admin(request)
    return _json_load(ADS_PATH, {'ads': []})


@app.post('/api/reputation/admin/ads')
async def admin_ad_save(request: Request, payload: AdIn):
    admin = _require_admin(request)
    if payload.placement not in AD_PLACEMENTS:
        raise HTTPException(400, 'Unknown placement.')
    url = payload.url if payload.url.startswith('https://') or payload.url.startswith('/') else ''
    ad = {'id': payload.id or uuid.uuid4().hex[:10], 'title': payload.title, 'text': payload.text, 'url': url, 'imageUrl': _safe_url(payload.imageUrl),
          'placement': payload.placement, 'startsAt': payload.startsAt, 'endsAt': payload.endsAt, 'active': payload.active, 'sponsor': payload.sponsor}
    async with _admin_lock:
        d = _json_load(ADS_PATH, {'ads': []})
        old = next((a for a in d['ads'] if a['id'] == ad['id']), None)
        if old:
            ad['views'], ad['clicks'] = old.get('views', 0), old.get('clicks', 0)
            d['ads'] = [ad if a['id'] == ad['id'] else a for a in d['ads']]
        else:
            d['ads'].append(ad)
        _json_save(ADS_PATH, d)
        ad_log = _admin_load(); _audit(ad_log, admin, 'ad', f"{ad['title']} · {ad['placement']} · {'on' if ad['active'] else 'off'}"); _admin_save(ad_log)
    return {'ok': True, 'ad': ad}


@app.delete('/api/reputation/admin/ads/{ad_id}')
async def admin_ad_delete(request: Request, ad_id: str):
    _require_admin(request)
    async with _admin_lock:
        d = _json_load(ADS_PATH, {'ads': []})
        d['ads'] = [a for a in d['ads'] if a['id'] != ad_id]
        _json_save(ADS_PATH, d)
    return {'ok': True}


# ---- Command Center: pulse, moderation, broadcast, treasury ---------------------------------
MUTES_PATH = DATA_DIR / 'mutes.json'


def is_muted(address: str) -> float:
    until = _json_load(MUTES_PATH, {}).get(primary_of(address), 0)
    return until if until > time.time() else 0


@app.get('/api/reputation/admin/pulse')
async def admin_pulse(request: Request):
    _require_admin(request)
    now = time.time() * 1000
    rooms = _chat_load()['rooms']
    msgs = [m for ms in rooms.values() for m in ms if isinstance(m, dict)]
    last24 = [m for m in msgs if now - m.get('ts', 0) < 86400e3]
    hourly = [0] * 24
    for m in last24:
        hourly[23 - min(23, int((now - m['ts']) // 3600e3))] += 1
    busiest = sorted(((r, sum(1 for m in ms if now - m.get('ts', 0) < 86400e3)) for r, ms in rooms.items()), key=lambda x: -x[1])[:8]
    posters = {}
    for m in last24:
        if not m.get('system'):
            posters[m.get('identity') or m.get('address')] = posters.get(m.get('identity') or m.get('address'), 0) + 1
    profiles = _profiles_load()['profiles']
    fee = {}
    try:
        async with httpx.AsyncClient(timeout=6) as http:
            fee = (await http.get('http://127.0.0.1:5088/api/cats/leader')).json().get('cat') or {}
    except Exception:
        pass
    clicks = sorted(_json_load(CLICKS_PATH, {}).items(), key=lambda kv: -kv[1][0])[:6]
    return {'messages24h': len(last24), 'hourly': hourly, 'activeWallets24h': len(posters), 'profiles': len(profiles),
            'newProfiles24h': sum(1 for v in profiles.values() if time.time() - (v or {}).get('updatedAt', 0) < 86400),
            'busiestRooms': [{'room': r, 'messages': n} for r, n in busiest if n],
            'topPosters': [{'address': a, 'handle': handle_of(a), 'messages': n} for a, n in sorted(posters.items(), key=lambda x: -x[1])[:8]],
            'fee': {k: fee.get(k) for k in ('balanceSol', 'realizedPnlSol', 'winRate', 'wins', 'losses')} | {'open': len(fee.get('positions') or [])},
            'topClicks': [{'key': k, 'count': v[0]} for k, v in clicks],
            'pushSubscribers': len(_push_load()['subs']), 'muted': sum(1 for v in _json_load(MUTES_PATH, {}).values() if v > time.time())}


@app.get('/api/reputation/admin/chat-feed')
async def admin_chat_feed(request: Request, limit: int = 80):
    _require_admin(request)
    msgs = [m for r, ms in _chat_load()['rooms'].items() for m in ms if isinstance(m, dict) and not m.get('system')]
    msgs.sort(key=lambda m: -m.get('ts', 0))
    mutes = _json_load(MUTES_PATH, {})
    return {'messages': [{**{k: m.get(k) for k in ('id', 'room', 'address', 'username', 'handle', 'text', 'ts')}, 'muted': mutes.get(primary_of(m.get('address', '')), 0) > time.time()} for m in msgs[:max(1, min(limit, 300))]]}


class ModIn(BaseModel):
    room: str = ''
    id: str = ''
    address: str = ''
    hours: float = 24


@app.post('/api/reputation/admin/moderate/delete')
async def admin_delete_msg(request: Request, payload: ModIn):
    admin = _require_admin(request)
    async with _chat_lock:
        d = _chat_load()
        before = len(d['rooms'].get(payload.room, []))
        d['rooms'][payload.room] = [m for m in d['rooms'].get(payload.room, []) if m['id'] != payload.id]
        CHAT_PATH.write_text(json.dumps(d))
    ad = _admin_load(); _audit(ad, admin, 'mod-delete', f'{payload.room} #{payload.id}'); _admin_save(ad)
    return {'ok': before != len(d['rooms'].get(payload.room, []))}


@app.post('/api/reputation/admin/moderate/mute')
async def admin_mute(request: Request, payload: ModIn):
    admin = _require_admin(request)
    target = primary_of(payload.address)
    if target in _admin_wallets():
        raise HTTPException(400, "Can't mute the HQ wallet.")
    async with _admin_lock:
        d = _json_load(MUTES_PATH, {})
        d[target] = time.time() + max(0, min(payload.hours, 24 * 30)) * 3600 if payload.hours > 0 else 0
        _json_save(MUTES_PATH, d)
    ad = _admin_load(); _audit(ad, admin, 'mute' if payload.hours > 0 else 'unmute', f'@{handle_of(target)} {payload.hours:g}h'); _admin_save(ad)
    return {'ok': True, 'until': d[target]}


class BroadcastIn(BaseModel):
    title: str = Field(min_length=2, max_length=60)
    body: str = Field(min_length=2, max_length=240)
    url: str = '/terminal'
    push: bool = False
    rooms: list = []


@app.post('/api/reputation/admin/broadcast')
async def admin_broadcast(request: Request, payload: BroadcastIn):
    admin = _require_admin(request)
    url = payload.url if payload.url.startswith('/') or payload.url.startswith('https://') else '/terminal'
    posted = 0
    for room in [r for r in payload.rooms[:20] if _re.match(r'^[A-Za-z0-9_-]{3,160}$', str(r))]:
        chat_system_post(room, 'FEELESS HQ 👑', 'FEELESS-HQ', f'📢 {payload.title}\n{payload.body}')
        posted += 1
    sent = gone = 0
    if payload.push:
        subs = _push_load()['subs']
        for sid, entry in list(subs.items()):
            res = await asyncio.to_thread(_send_push, entry['subscription'], payload.title, payload.body, url, 'feeless-broadcast')
            sent += res == 'ok'
            gone += res == 'gone'
    ad = _admin_load(); _audit(ad, admin, 'broadcast', f"{payload.title} · {posted} rooms · push {sent}"); _admin_save(ad)
    return {'ok': True, 'rooms': posted, 'pushed': sent, 'stale': gone}


@app.get('/api/reputation/admin/treasury')
async def admin_treasury(request: Request):
    admin = _require_admin(request)
    stats = await wallet_stats(admin) if not admin.startswith('0x') else {}
    mints = await _ecosystem_mints()
    held = {}
    for aid, mint in mints.items():
        try:
            held[aid] = round(await _holding_usd(admin, mint), 2)
        except Exception:
            held[aid] = None
    recent = []
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            recent = [{'sig': s['signature'], 'at': s.get('blockTime'), 'ok': not s.get('err')} for s in (await _rpc(http, 'getSignaturesForAddress', [admin, {'limit': 12}])) or []]
    except Exception:
        pass
    return {'wallet': admin, 'sol': stats.get('sol'), 'holdingsUsd': held, 'recent': recent}


# ---- Holder gate for EVM coin rooms ---------------------------------------------------------
_ALCH_NET = {'ethereum': 'eth', 'base': 'base', 'bsc': 'bnb', 'arbitrum': 'arb', 'avalanche': 'avax', 'polygon': 'polygon', 'optimism': 'opt', 'zksync': 'zksync', 'zora': 'zora', 'cronos': 'cronos', 'unichain': 'unichain', 'worldchain': 'worldchain'}
EVM_RPC = {'ethereum': 'https://eth.llamarpc.com', 'base': 'https://mainnet.base.org', 'bsc': 'https://bsc-dataseed.binance.org',
           'arbitrum': 'https://arb1.arbitrum.io/rpc', 'avalanche': 'https://api.avax.network/ext/bc/C/rpc', 'polygon': 'https://polygon-rpc.com',
           'optimism': 'https://mainnet.optimism.io', 'zksync': 'https://mainnet.era.zksync.io', 'zora': 'https://rpc.zora.energy', 'cronos': 'https://evm.cronos.org',
           'unichain': 'https://mainnet.unichain.org', 'worldchain': 'https://worldchain-mainnet.g.alchemy.com/public'}
# Dedicated RPC per chain wins: <CHAIN>_RPC_URL, else Alchemy (one key covers every chain), else public.
for _c, _n in _ALCH_NET.items():
    EVM_RPC[_c] = os.environ.get(f'{_c.upper()}_RPC_URL', '').strip() or (f'https://{_n}-mainnet.g.alchemy.com/v2/{_alchemy}' if _alchemy else EVM_RPC[_c])
_evm_room_cache = {}


async def _evm_room(room: str):
    m = _re.match(r'^coin-(ethereum|base|bsc|arbitrum|avalanche|polygon|optimism|zksync|zora|cronos|unichain|worldchain)-(0x[0-9a-fA-F]{40})-(bulls|bears|trenches)$', room)
    if not m:
        return None
    chain, pair = m.group(1), m.group(2)
    hit = _evm_room_cache.get(pair)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    info = None
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            p = ((await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{pair}')).json().get('pairs') or [None])[0]
            if p:
                info = (chain, p['baseToken']['address'], p['baseToken']['symbol'], float(p.get('priceUsd') or 0))
    except Exception:
        pass
    _evm_room_cache[pair] = (time.time(), info)
    return info


async def _evm_holding_usd(owner: str, chain: str, token: str, price: float):
    call = lambda data: {'jsonrpc': '2.0', 'id': 1, 'method': 'eth_call', 'params': [{'to': token, 'data': data}, 'latest']}
    async with httpx.AsyncClient(timeout=10) as http:
        bal = int((await http.post(EVM_RPC[chain], json=call('0x70a08231' + owner[2:].lower().rjust(64, '0')))).json().get('result') or '0x0', 16)
        dec = int((await http.post(EVM_RPC[chain], json=call('0x313ce567'))).json().get('result') or '0x12', 16)
    return bal / (10 ** dec) * price


def _evm_account_for(address: str):
    if address.startswith('0x'):
        return address
    return next((a for a in linked_of(address) if a.startswith('0x')), None)


async def evm_gate(room: str, address: str):
    info = await _evm_room(room)
    if not info:
        return None
    chain, token, symbol, price = info
    acct = _evm_account_for(address) if address else None
    if not address:
        return {'gated': True, 'allowed': False, 'symbol': symbol, 'minUsd': MIN_HOLD_USD, 'holdingUsd': None}
    if not acct:
        return {'gated': True, 'allowed': False, 'symbol': symbol, 'minUsd': MIN_HOLD_USD, 'holdingUsd': None, 'needsChain': 'evm'}
    try:
        usd = await _evm_holding_usd(acct, chain, token, price)
    except Exception:
        usd = 0.0
    return {'gated': True, 'allowed': usd >= MIN_HOLD_USD, 'symbol': symbol, 'minUsd': MIN_HOLD_USD, 'holdingUsd': round(usd, 4), 'chain': chain}


# ---- Weekly caller leagues --------------------------------------------------------------------
def _week_start(ts=None):
    t = time.gmtime(ts or time.time())
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, 0)) - t.tm_wday * 86400 - time.timezone


@app.get('/api/reputation/league')
async def caller_league(week: int = 0):
    start = _week_start() - week * 7 * 86400
    end = start + 7 * 86400
    board = await caller_board(days=min(90, max(7, int((time.time() - start) / 86400) + 1)))
    rows = []
    for r in board['rows']:
        calls = [c for c in (r.get('callsList') or [])] if r.get('callsList') else None
        rows.append({'caller': r.get('caller'), 'address': r.get('callerAddress'), 'calls': r.get('calls'), 'hitRate': r.get('hitRate'), 'avgPeakX': r.get('avgPeakX'),
                     'points': round((r.get('calls') or 0) * 2 + (r.get('hitRate') or 0) * 50 + min(20, (r.get('avgPeakX') or 1) * 4), 1)})
    rows = [r for r in rows if r['address'] and r['address'] != 'FEE-LEADER-CAT']
    rows.sort(key=lambda r: -r['points'])
    return {'weekStart': start, 'weekEnd': end, 'rows': rows[:50], 'prizes': ['🥇 League Champion badge + airdrop', '🥈 badge', '🥉 badge']}


# ---- Rug radar + whale feed (background watcher) --------------------------------------------
_radar = {'hist': {}, 'events': [], 'whales': [], 'pairs': {}}


def _radar_pairs():
    pairs = {}
    try:
        for c in sorted(_calls_load()['calls'].values(), key=lambda c: -c.get('at', 0))[:200]:
            if time.time() - c.get('at', 0) < 86400 and c.get('chain') == 'solana':
                pairs[c['pairAddress']] = c.get('symbol') or '?'
    except Exception:
        pass
    for e in _push_load()['subs'].values():
        for w in e.get('watch', [])[:30]:
            if w.get('chainId') == 'solana':
                pairs[w['pairAddress']] = w.get('symbol') or '?'
    return dict(list(pairs.items())[:90])


async def _radar_loop():
    await asyncio.sleep(30)
    rot = 0
    while True:
        try:
            pairs = _radar_pairs()
            _radar['pairs'] = pairs
            now = time.time()
            async with httpx.AsyncClient(timeout=12) as http:
                keys = list(pairs)
                for i in range(0, len(keys), 30):
                    r = await http.get(f"https://api.dexscreener.com/latest/dex/pairs/solana/{','.join(keys[i:i + 30])}")
                    for p in (r.json() or {}).get('pairs') or []:
                        pa = p['pairAddress']; sym = p['baseToken']['symbol']
                        liq = float((p.get('liquidity') or {}).get('usd') or 0); px = float(p.get('priceUsd') or 0)
                        h = _radar['hist'].setdefault(pa, [])
                        h.append((now, liq, px)); h[:] = [x for x in h if now - x[0] < 1800]
                        old = next((x for x in h if now - x[0] <= 900), None)
                        if old and old[1] > 5000 and liq < old[1] * 0.7:
                            _radar_event('rug', pa, sym, f'${sym} liquidity pulled {(1 - liq / old[1]) * 100:.0f}% in {int((now - old[0]) / 60)}m (${old[1]/1e3:.1f}K → ${liq/1e3:.1f}K)')
                        if old and old[2] > 0 and px < old[2] * 0.5:
                            _radar_event('dump', pa, sym, f'${sym} dumped {(1 - px / old[2]) * 100:.0f}% in {int((now - old[0]) / 60)}m')
                # whale trades: a few pairs per minute from FEELESS's Helius-parsed swap feed
                for pa in keys[rot:rot + 3]:
                    try:
                        r = await http.get(f'http://127.0.0.1:5099/api/candles/trades/solana/{pa}')
                        rows = (r.json() or {}).get('trades') or []
                    except Exception:
                        rows = []
                    for t in rows[:50]:
                        usd = float(t.get('usd') or 0)
                        if usd >= 2500 and not any(w['tx'] == t.get('tx') for w in _radar['whales']):
                            _radar['whales'].insert(0, {'pair': pa, 'symbol': pairs.get(pa), 'kind': t.get('kind'), 'usd': round(usd), 'wallet': t.get('wallet'), 'tx': t.get('tx'), 'at': t.get('ts')})
                    _radar['whales'] = _radar['whales'][:120]
                rot = (rot + 3) % max(1, len(keys))
        except Exception as exc:
            print('radar error', exc)
        await asyncio.sleep(60)


def _radar_event(kind, pa, sym, text):
    last = next((e for e in _radar['events'] if e['pair'] == pa and e['kind'] == kind), None)
    if last and time.time() - last['at'] < 3600:
        return False
    _radar['events'].insert(0, {'kind': kind, 'pair': pa, 'symbol': sym, 'text': text, 'at': time.time()})
    _radar['events'] = _radar['events'][:100]
    return True


async def _push_snipers_out(mint):
    # Phones with push on and this coin on their watchlist hear it first; tapping opens the buy.
    for entry in list(_push_load()['subs'].values()):
        w = next((x for x in entry['watch'] if mint in (x.get('mint'), x.get('pairAddress'))), None)
        if w:
            await asyncio.to_thread(_send_push, entry['subscription'], f"🎯 {w.get('symbol') or mint[:4]}: snipers are out",
                                    'Every flagged sniper/bundler has sold. Tap to buy.', f"/terminal/chat?chain=solana&pair={w['pairAddress']}&room=bulls&buy=1", f'snipers-{mint}')


@app.on_event('startup')
async def _start_radar():
    asyncio.create_task(_radar_loop())


@app.get('/api/reputation/radar')
async def radar():
    return {'watching': len(_radar['pairs']), 'events': _radar['events'][:40], 'whales': _radar['whales'][:40]}


@app.get('/api/reputation/admin/feecat')
async def admin_feecat_get(request: Request):
    _require_admin(request)
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.get('http://127.0.0.1:5088/api/cats/internal/rules', headers={'x-feeless-internal': _internal_key()})
        prof = (await http.get('http://127.0.0.1:5088/api/cats/leader/profile')).json()
    return {**r.json(), 'learning': prof.get('learning'), 'stats': prof.get('stats'), 'cat': {k: (prof.get('cat') or {}).get(k) for k in ('balanceSol', 'realizedPnlSol', 'winRate', 'status')}}


@app.post('/api/reputation/admin/feecat')
async def admin_feecat_set(request: Request):
    admin = _require_admin(request)
    body = await request.json()
    async with httpx.AsyncClient(timeout=10) as http:
        r = await http.post('http://127.0.0.1:5088/api/cats/internal/rules', headers={'x-feeless-internal': _internal_key()}, json=body)
    if r.status_code != 200:
        raise HTTPException(r.status_code, 'Fee service rejected the change.')
    ad = _admin_load(); _audit(ad, admin, 'feecat', json.dumps({k: v for k, v in body.items() if k != 'rules'} | {'rules': list((body.get('rules') or {}).keys())})[:160]); _admin_save(ad)
    return r.json()


# ---- Notifications inbox (per identity) + push to the owner's devices ----------------------
NOTIF_PATH = DATA_DIR / 'notifications.json'


def notify(address: str, kind: str, text: str, url: str = '', actor: str = ''):
    to = primary_of(address)
    if not to or to in ('FEE-LEADER-CAT', 'FEELESS-HQ') or primary_of(actor or '') == to:
        return
    d = _json_load(NOTIF_PATH, {})
    box = d.setdefault(to, [])
    box.insert(0, {'id': uuid.uuid4().hex[:10], 'kind': kind, 'text': text[:200], 'url': url, 'actor': actor, 'at': time.time(), 'read': False})
    d[to] = box[:200]
    _json_save(NOTIF_PATH, d)
    try:
        for e in _push_load()['subs'].values():
            if primary_of((e.get('prefs') or {}).get('address') or '') == to:
                asyncio.get_running_loop().run_in_executor(None, _send_push, e['subscription'], {'dm': '💬 New message', 'follow': '➕ New follower', 'wall': '🧱 New wall post', 'mention': '📣 You were mentioned', 'reward': '🎁 Reward ready', 'invite': '🎉 Invite joined'}.get(kind, 'FEELESS'), text[:120], url or '/terminal', f'n-{kind}')
    except Exception:
        pass


def _session_or_401(address, session):
    owner = session_address(session)
    if not owner or primary_of(owner) != primary_of(address):
        raise HTTPException(401, 'Sign in to chat first (one signature, 7 days).')
    return primary_of(address)


@app.get('/api/reputation/notifications')
async def notifications(address: str, session: str):
    me = _session_or_401(address, session)
    box = _json_load(NOTIF_PATH, {}).get(me, [])
    return {'unread': sum(1 for n in box if not n['read']), 'items': box[:60]}


@app.post('/api/reputation/notifications/read')
async def notifications_read(payload: dict):
    me = _session_or_401(payload.get('address', ''), payload.get('session', ''))
    async with _admin_lock:
        d = _json_load(NOTIF_PATH, {})
        for n in d.get(me, []):
            n['read'] = True
        _json_save(NOTIF_PATH, d)
    return {'ok': True}


# ---- Direct messages (profile chat) -----------------------------------------------------------
DM_PATH = DATA_DIR / 'dms.json'
_dm_last = {}


def _dm_key(a, b):
    return '|'.join(sorted([primary_of(a), primary_of(b)]))


class DmIn(BaseModel):
    address: str
    session: str
    to: str
    text: str = Field(min_length=1, max_length=500)


@app.post('/api/reputation/dm')
async def dm_send(payload: DmIn):
    me = _session_or_401(payload.address, payload.session)
    to = primary_of(payload.to)
    if not _re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', to) or to == me:
        raise HTTPException(400, 'Pick another wallet to message.')
    if is_muted(me):
        raise HTTPException(403, 'You are muted for now.')
    if time.time() - _dm_last.get(me, 0) < 2:
        raise HTTPException(429, 'Slow down.')
    _dm_last[me] = time.time()
    msg = {'id': uuid.uuid4().hex[:12], 'from': me, 'to': to, 'text': payload.text.strip(), 'at': time.time()}
    async with _admin_lock:
        d = _json_load(DM_PATH, {})
        d.setdefault(_dm_key(me, to), []).append(msg)
        d[_dm_key(me, to)] = d[_dm_key(me, to)][-300:]
        _json_save(DM_PATH, d)
    notify(to, 'dm', f"@{handle_of(me)}: {payload.text.strip()}", f'/terminal/profile/{me}?dm=1', me)
    return {'ok': True, 'message': msg}


@app.get('/api/reputation/dm/{peer}')
async def dm_thread(peer: str, address: str, session: str):
    me = _session_or_401(address, session)
    return {'me': me, 'peer': primary_of(peer), 'messages': _json_load(DM_PATH, {}).get(_dm_key(me, peer), [])[-150:]}


@app.get('/api/reputation/dm-inbox')
async def dm_inbox(address: str, session: str):
    me = _session_or_401(address, session)
    rows = []
    for k, msgs in _json_load(DM_PATH, {}).items():
        a, b = k.split('|')
        if me in (a, b) and msgs:
            peer = b if a == me else a
            rows.append({'peer': peer, 'handle': handle_of(peer), 'last': msgs[-1], 'count': len(msgs)})
    rows.sort(key=lambda r: -r['last']['at'])
    return {'threads': rows[:50]}


# ---- Rewards: points you earn and claim -------------------------------------------------------
POINTS_PATH = DATA_DIR / 'points.json'
REWARDS = [
    {'id': 'daily', 'label': 'Daily check-in', 'points': 10, 'how': 'Come back every day — streaks add +5 per day (max +50).'},
    {'id': 'profile', 'label': 'Complete your profile', 'points': 50, 'how': 'Name, @handle, pic and bio.', 'once': True},
    {'id': 'post', 'label': 'Post in the Trenches', 'points': 5, 'how': 'Post at least once today in any chat.'},
    {'id': 'call-hit', 'label': 'Call hits 2×', 'points': 100, 'how': 'Each of your Call Ledger calls that reached 2×.'},
    {'id': 'invite', 'label': 'Invite a friend', 'points': 75, 'how': 'Each wallet credited to your invite link.'},
    {'id': 'fee-holder', 'label': 'Hold $FEE', 'points': 20, 'how': 'Hold $1+ of $FEE — claim daily.'},
    {'id': 'link', 'label': 'Link Solana + EVM', 'points': 40, 'how': 'Link both accounts of your wallet.', 'once': True},
]


def _pts():
    return _json_load(POINTS_PATH, {})


async def _reward_state(me: str):
    rec = _pts().get(me) or {'total': 0, 'claims': {}, 'streak': 0, 'log': []}
    day = time.strftime('%Y-%m-%d', time.gmtime())
    claims = rec['claims']
    prof = _profiles_load()['profiles'].get(me) or {}
    msgs_today = any(m for ms in _chat_load()['rooms'].values() for m in ms if isinstance(m, dict) and (m.get('identity') or m.get('address')) == me and time.strftime('%Y-%m-%d', time.gmtime(m.get('ts', 0) / 1000)) == day)
    board = await caller_board(days=90)
    hits = next((r['hits'] for r in board['rows'] if r.get('callerAddress') == me), 0)
    invited = len(_json_load(REF_PATH, {'by': {}})['by'].get(me, []))
    fee_ok = (await _perk_tier(me))[1] >= 1
    linked = len(linked_of(me)) > 1
    out = []
    for r in REWARDS:
        c = claims.get(r['id'])
        if r['id'] == 'daily':
            ok, amount = c != day, 10 + min(50, 5 * rec.get('streak', 0))
        elif r['id'] == 'profile':
            ok, amount = not c and all(prof.get(k) for k in ('displayName', 'handle', 'avatarUrl', 'bio')), r['points']
        elif r['id'] == 'post':
            ok, amount = msgs_today and c != day, r['points']
        elif r['id'] == 'call-hit':
            n = hits - int(c or 0); ok, amount = n > 0, n * r['points']
        elif r['id'] == 'invite':
            n = invited - int(c or 0); ok, amount = n > 0, n * r['points']
        elif r['id'] == 'fee-holder':
            ok, amount = fee_ok and c != day, r['points']
        else:
            ok, amount = linked and not c, r['points']
        out.append({**r, 'claimable': bool(ok), 'amount': amount, 'claimed': c})
    return rec, out, {'hits': hits, 'invited': invited, 'day': day}


@app.get('/api/reputation/rewards/{address}')
async def rewards(address: str):
    me = primary_of(address)
    rec, items, _ = await _reward_state(me)
    allp = _pts()
    rank = 1 + sum(1 for v in allp.values() if v.get('total', 0) > rec.get('total', 0))
    return {'address': me, 'total': rec.get('total', 0), 'streak': rec.get('streak', 0), 'rank': rank, 'items': items, 'log': rec.get('log', [])[:20]}


class ClaimIn(BaseModel):
    address: str
    session: str
    reward: str


@app.post('/api/reputation/rewards/claim')
async def rewards_claim(payload: ClaimIn):
    me = _session_or_401(payload.address, payload.session)
    async with _admin_lock:
        rec, items, ctx = await _reward_state(me)
        it = next((i for i in items if i['id'] == payload.reward), None)
        if not it or not it['claimable']:
            raise HTTPException(400, 'Nothing to claim for that yet.')
        d = _pts()
        rec = d.get(me) or rec
        day = ctx['day']
        if it['id'] == 'daily':
            yesterday = time.strftime('%Y-%m-%d', time.gmtime(time.time() - 86400))
            rec['streak'] = rec.get('streak', 0) + 1 if rec['claims'].get('daily') == yesterday else 1
        rec['claims'][it['id']] = ctx['hits'] if it['id'] == 'call-hit' else ctx['invited'] if it['id'] == 'invite' else day if it['id'] in ('daily', 'post', 'fee-holder') else True
        rec['total'] = rec.get('total', 0) + it['amount']
        rec.setdefault('log', []).insert(0, {'id': it['id'], 'label': it['label'], 'points': it['amount'], 'at': time.time()})
        try:
            season_award(me, it['amount'], it['id'])
        except Exception:
            pass
        rec['log'] = rec['log'][:100]
        d[me] = rec
        _json_save(POINTS_PATH, d)
    return {'ok': True, 'gained': it['amount'], 'total': rec['total'], 'streak': rec.get('streak', 0)}


@app.get('/api/reputation/rewards-board')
async def rewards_board(limit: int = 50):
    rows = sorted(({'address': a, 'handle': handle_of(a), 'points': v.get('total', 0), 'streak': v.get('streak', 0)} for a, v in _pts().items()), key=lambda r: -r['points'])
    return {'rows': rows[:max(1, min(limit, 200))]}



# ---- Verified identities ---------------------------------------------------------------------
FEE_RESERVE_WALLET = 'Btiq3W3yhqSRbF1FEf2TQMNrwsknMpQmeb5K9TeD83qU'


def is_verified(address: str) -> bool:
    a = primary_of(address or '')
    return a in _admin_wallets() or a == FEE_RESERVE_WALLET or a in (_admin_load().get('verified') or [])


@app.post('/api/reputation/admin/verify')
async def admin_verify(request: Request, payload: ModIn):
    admin = _require_admin(request)
    a = primary_of(payload.address)
    async with _admin_lock:
        d = _admin_load()
        v = set(d.get('verified') or [])
        v.add(a) if payload.hours >= 0 else v.discard(a)
        d['verified'] = sorted(v)
        _audit(d, admin, 'verify' if payload.hours >= 0 else 'unverify', f'@{handle_of(a)}')
        _admin_save(d)
    return {'ok': True, 'verified': is_verified(a)}


# ---- Unique invite codes + public site URL ---------------------------------------------------
def invite_code(address: str) -> str:
    a = primary_of(address)
    h = hashlib.sha256(f'feeless-invite:{a}'.encode()).digest()
    alphabet = '23456789abcdefghjkmnpqrstuvwxyz'
    n = int.from_bytes(h[:8], 'big')
    return ''.join(alphabet[(n >> (5 * i)) % len(alphabet)] for i in range(8))


def _code_owner(code: str):
    code = (code or '').lower()
    cands = set(_profiles_load()['profiles']) | set(_json_load(REF_PATH, {'by': {}})['by']) | set(_pts()) | set(_admin_wallets())
    return next((a for a in cands if invite_code(a) == code), None)


@app.get('/api/reputation/site')
async def site_config():
    return {'publicUrl': (_admin_load().get('site') or {}).get('publicUrl') or ''}


class SiteIn(BaseModel):
    publicUrl: str


@app.post('/api/reputation/admin/site')
async def admin_site(request: Request, payload: SiteIn):
    admin = _require_admin(request)
    url = payload.publicUrl.strip().rstrip('/')
    if url and not _re.match(r'^https://[a-z0-9.-]+\.[a-z]{2,}(/[\w./-]*)?$', url, _re.I):
        raise HTTPException(400, 'Use your public https:// domain (e.g. https://feeless.app).')
    async with _admin_lock:
        d = _admin_load(); d['site'] = {'publicUrl': url}; _audit(d, admin, 'site-url', url or '(cleared)'); _admin_save(d)
    hook = await sync_helius_webhook(url) if url else {'ok': False, 'reason': 'No domain'}
    return {'ok': True, 'publicUrl': url, 'webhook': hook}


# ---- Points shop: spend what you earn --------------------------------------------------------
SHOP = [
    {'id': 'ring-diamond-7d', 'label': 'Diamond ring · 7 days', 'cost': 400, 'kind': 'style', 'grant': {'ring': 'diamond'}, 'days': 7},
    {'id': 'ring-gold-3d', 'label': 'Molten Gold ring · 3 days', 'cost': 600, 'kind': 'style', 'grant': {'ring': 'gold'}, 'days': 3},
    {'id': 'name-rainbow-7d', 'label': 'Rainbow name · 7 days', 'cost': 250, 'kind': 'style', 'grant': {'nameFx': 'rainbow'}, 'days': 7},
    {'id': 'boost-3', 'label': '3 chat boosts (any tier)', 'cost': 150, 'kind': 'boost', 'grant': {'boosts': 3}},
    {'id': 'raffle', 'label': 'Airdrop raffle ticket', 'cost': 100, 'kind': 'raffle', 'grant': {'tickets': 1}},
    {'id': 'badge-og', 'label': '"Points OG" badge (permanent)', 'cost': 2000, 'kind': 'badge', 'grant': {'badge': 'points-og'}},
]


def _unlocks(address: str):
    rec = _pts().get(primary_of(address)) or {}
    now = time.time()
    return {k: v for k, v in (rec.get('unlocks') or {}).items() if v == 'forever' or float(v) > now}, rec


@app.get('/api/reputation/shop')
async def shop(address: str = ''):
    un, rec = _unlocks(address) if address else ({}, {})
    return {'items': SHOP, 'points': rec.get('total', 0), 'spent': rec.get('spent', 0), 'unlocks': un, 'boosts': rec.get('boostCredits', 0), 'tickets': rec.get('tickets', 0)}


class BuyIn(BaseModel):
    address: str
    session: str
    item: str


@app.post('/api/reputation/shop/buy')
async def shop_buy(payload: BuyIn):
    me = _session_or_401(payload.address, payload.session)
    it = next((x for x in SHOP if x['id'] == payload.item), None)
    if not it:
        raise HTTPException(404, 'Unknown item.')
    async with _admin_lock:
        d = _pts(); rec = d.get(me) or {'total': 0, 'claims': {}, 'log': []}
        balance = rec.get('total', 0) - rec.get('spent', 0)
        if balance < it['cost']:
            raise HTTPException(400, f"Need {it['cost'] - balance} more points.")
        rec['spent'] = rec.get('spent', 0) + it['cost']
        un = rec.setdefault('unlocks', {})
        g = it['grant']
        if it['kind'] == 'style':
            for k, v in g.items():
                un[f'{k}:{v}'] = time.time() + it['days'] * 86400
        elif it['kind'] == 'boost':
            rec['boostCredits'] = rec.get('boostCredits', 0) + g['boosts']
        elif it['kind'] == 'raffle':
            rec['tickets'] = rec.get('tickets', 0) + 1
        else:
            un[f"badge:{g['badge']}"] = 'forever'
        rec.setdefault('log', []).insert(0, {'id': it['id'], 'label': f"Bought {it['label']}", 'points': -it['cost'], 'at': time.time()})
        d[me] = rec; _json_save(POINTS_PATH, d)
    _badge_cache.pop(me, None)
    return {'ok': True, 'balance': rec['total'] - rec['spent']}


# ---- Trench Wars: weekly faction battle --------------------------------------------------------
FACTIONS = {'bulls': '🐂 Bulls', 'bears': '🐻 Bears', 'degens': '🎰 Degens'}
WARS_PATH = DATA_DIR / 'wars.json'


def _war_week():
    return time.strftime('%G-W%V', time.gmtime())


@app.get('/api/reputation/wars')
async def wars(address: str = ''):
    d = _json_load(WARS_PATH, {})
    wk = d.get(_war_week()) or {'members': {}}
    pts = _pts()
    week_start = _week_start()
    score = {f: 0 for f in FACTIONS}
    count = {f: 0 for f in FACTIONS}
    for a, f in wk['members'].items():
        gained = sum(l['points'] for l in (pts.get(a) or {}).get('log', []) if l['points'] > 0 and l['at'] >= week_start)
        score[f] += gained; count[f] += 1
    mine = wk['members'].get(primary_of(address)) if address else None
    last = d.get(time.strftime('%G-W%V', time.gmtime(time.time() - 7 * 86400))) or {}
    return {'week': _war_week(), 'factions': [{'id': f, 'label': l, 'score': score[f], 'members': count[f]} for f, l in FACTIONS.items()],
            'mine': mine, 'lastWinner': last.get('winner'), 'endsAt': _week_start() + 7 * 86400}


class JoinIn(BaseModel):
    address: str
    session: str
    faction: str


@app.post('/api/reputation/wars/join')
async def wars_join(payload: JoinIn):
    me = _session_or_401(payload.address, payload.session)
    if payload.faction not in FACTIONS:
        raise HTTPException(400, 'Pick bulls, bears or degens.')
    async with _admin_lock:
        d = _json_load(WARS_PATH, {})
        wk = d.setdefault(_war_week(), {'members': {}})
        if me in wk['members']:
            raise HTTPException(400, f"You're already fighting for {FACTIONS[wk['members'][me]]} this week.")
        wk['members'][me] = payload.faction
        _json_save(WARS_PATH, d)
    return {'ok': True, 'faction': payload.faction}


# ---- Wallet PnL from verified FEELESS receipts ------------------------------------------------
@app.get('/api/reputation/pnl/{address}')
async def wallet_pnl(address: str):
    me = set(linked_of(address))
    rows = [r for r in _receipt_rows() if r[2] in me]
    by = {}
    sol_flow = 0.0
    for r in rows:
        sol_flow += r[5] or 0
        for mint, delta in r[4]:
            if mint == WSOL:
                continue
            b = by.setdefault(mint, {'mint': mint, 'bought': 0.0, 'sold': 0.0, 'solIn': 0.0, 'solOut': 0.0, 'trades': 0})
            b['trades'] += 1
            if delta > 0:
                b['bought'] += delta; b['solIn'] += -(r[5] or 0)
            else:
                b['sold'] += -delta; b['solOut'] += (r[5] or 0)
    for b in by.values():
        b['realizedSol'] = round(b['solOut'] - b['solIn'] * (b['sold'] / b['bought'] if b['bought'] else 1), 6)
        b['holding'] = round(b['bought'] - b['sold'], 6)
    return {'trades': len(rows), 'netSolFlow': round(sol_flow, 6), 'tokens': sorted(by.values(), key=lambda b: -abs(b['realizedSol']))[:50],
            'note': 'From verified FEELESS trade receipts. Trades made outside FEELESS are not included.'}


# ---- Snipe risk for coin cards (cached intel only — never blocks a list) ----------------------
@app.get('/api/reputation/snipe-risk')
async def snipe_risk(mints: str):
    out = {}
    for m in mints.split(',')[:60]:
        hit = _intel_cache.get(m)
        if not hit or not hit[1]:
            continue
        d = hit[1]
        snip, bund, top10 = len(d.get('sniperWallets') or []), len(d.get('bundledWallets') or []), d.get('top10Pct') or 0
        funded_by_repeat = len(d.get('flaggedFunders') or {})
        risk = min(100, round(snip * 2 + bund * 5 + max(0, top10 - 20) + funded_by_repeat * 15))
        out[m] = {'risk': risk, 'level': 'high' if risk >= 60 else 'medium' if risk >= 30 else 'low', 'snipers': snip, 'bundled': bund, 'top10': top10, 'repeatFunders': funded_by_repeat}
    return {'risk': out}


# ---- Helius webhooks: instant whale / dev-sell events (needs HELIUS_WEBHOOK_SECRET) -----------
@app.post('/api/reputation/webhooks/helius')
async def helius_webhook(request: Request):
    secret = os.environ.get('HELIUS_WEBHOOK_SECRET') or (_admin_load().get('helius') or {}).get('secret', '')
    if not secret or not hmac.compare_digest(request.headers.get('authorization', ''), secret):
        raise HTTPException(403, 'Bad webhook secret.')
    events = await request.json()
    n = 0
    for ev in events if isinstance(events, list) else [events]:
        for tt in (ev.get('tokenTransfers') or [])[:20]:
            usd = None
            amt = float(tt.get('tokenAmount') or 0)
            mint = tt.get('mint')
            if not mint or amt <= 0:
                continue
            _radar['whales'].insert(0, {'pair': None, 'mint': mint, 'symbol': None, 'kind': 'transfer', 'usd': usd, 'wallet': tt.get('fromUserAccount'),
                                        'tx': ev.get('signature'), 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ev.get('timestamp') or time.time()))})
            n += 1
        _radar['whales'] = _radar['whales'][:120]
    return {'ok': True, 'ingested': n}


# ---- Auto-managed Helius webhook: follows the public domain set in the Command Center ---------
def _helius_key():
    m = _re.search(r'api-key=([0-9a-f-]{20,})', os.environ.get('SOLANA_RPC_URL', ''))
    return m.group(1) if m else None


def _webhook_secret():
    sec = os.environ.get('HELIUS_WEBHOOK_SECRET') or (_admin_load().get('helius') or {}).get('secret')
    if not sec:
        import secrets as _s
        sec = _s.token_urlsafe(32)
        d = _admin_load(); d.setdefault('helius', {})['secret'] = sec; _admin_save(d)
    return sec


async def sync_helius_webhook(public_url: str):
    """Create or update FEELESS's Helius webhook to point at the current public domain."""
    key = _helius_key()
    if not key or not public_url:
        return {'ok': False, 'reason': 'Needs a public domain and a Helius key in SOLANA_RPC_URL.'}
    mints = list((await _ecosystem_mints()).values())
    body = {'webhookURL': f'{public_url.rstrip("/")}/api/reputation/webhooks/helius', 'transactionTypes': ['SWAP', 'TRANSFER'],
            'accountAddresses': sorted(set(mints + _admin_wallets()))[:100], 'webhookType': 'enhanced', 'authHeader': _webhook_secret()}
    d = _admin_load(); hid = (d.get('helius') or {}).get('webhookId')
    async with httpx.AsyncClient(timeout=20) as http:
        if hid:
            r = await http.put(f'https://api.helius.xyz/v0/webhooks/{hid}?api-key={key}', json=body)
            if r.status_code == 404:
                hid = None
        if not hid:
            r = await http.post(f'https://api.helius.xyz/v0/webhooks?api-key={key}', json=body)
    if r.status_code >= 300:
        return {'ok': False, 'reason': f'Helius said {r.status_code}: {r.text[:120]}'}
    d = _admin_load(); d.setdefault('helius', {}).update({'webhookId': r.json().get('webhookID') or hid, 'url': body['webhookURL'], 'at': time.time()}); _admin_save(d)
    return {'ok': True, 'url': body['webhookURL'], 'watching': len(body['accountAddresses'])}


# ---- Portfolio: every coin a wallet holds, priced, with logos --------------------------------
_pf_cache = {}


@app.get('/api/reputation/portfolio/{address}')
async def portfolio(address: str):
    a = primary_of(address)
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a):
        return {'address': a, 'supported': False, 'tokens': [], 'totalUsd': None}
    hit = _pf_cache.get(a)
    if hit and time.time() - hit[0] < 90:
        return hit[1]
    held = {}
    sol = 0.0
    async with httpx.AsyncClient(timeout=25) as http:
        try:
            sol = ((await _rpc(http, 'getBalance', [a])) or {}).get('value', 0) / 1e9
        except Exception:
            pass
        for prog in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
            try:
                r = await _rpc(http, 'getTokenAccountsByOwner', [a, {'programId': prog}, {'encoding': 'jsonParsed'}])
            except Exception:
                r = None
            for acc in (r or {}).get('value', []):
                info = acc['account']['data']['parsed']['info']
                amt = float((info.get('tokenAmount') or {}).get('uiAmount') or 0)
                if amt > 0:
                    held[info['mint']] = held.get(info['mint'], 0) + amt
        mints = list(held)[:60]
        market = {}
        sem = asyncio.Semaphore(8)

        async def one(m):
            async with sem:
                p = None
                for url in (f'https://api.dexscreener.com/latest/dex/tokens/{m}', f'https://api.dexscreener.com/latest/dex/search?q={m}'):
                    try:
                        pairs = ((await http.get(url)).json() or {}).get('pairs') or []
                    except Exception:
                        pairs = []
                    mine = [x for x in pairs if (x.get('baseToken') or {}).get('address') == m]
                    if mine:
                        p = max(mine, key=lambda x: float((x.get('liquidity') or {}).get('usd') or 0)); break
                if not p:  # Jupiter covers pump.fun curve tokens DexScreener hasn't indexed
                    try:
                        j = ((await http.get(f'https://lite-api.jup.ag/tokens/v2/search?query={m}')).json() or [None])[0]
                    except Exception:
                        j = None
                    if j and j.get('usdPrice'):
                        p = {'baseToken': {'address': m, 'symbol': j.get('symbol'), 'name': j.get('name')}, 'priceUsd': j.get('usdPrice'),
                             'info': {'imageUrl': j.get('icon')}, 'priceChange': {'h24': (j.get('stats24h') or {}).get('priceChange')}, 'chainId': 'solana'}
                if p:
                    market[m] = p
        await asyncio.gather(*(one(m) for m in mints))
        sol_px = 0.0
        try:
            sol_px = float(((await http.get('https://lite-api.jup.ag/price/v3?ids=So11111111111111111111111111111111111111112')).json().get('So11111111111111111111111111111111111111112') or {}).get('usdPrice') or 0)
        except Exception:
            pass
    rows = []
    for m, amt in held.items():
        p = market.get(m)
        px = float(p.get('priceUsd') or 0) if p else 0
        rows.append({'mint': m, 'amount': amt, 'symbol': (p or {}).get('baseToken', {}).get('symbol'), 'name': (p or {}).get('baseToken', {}).get('name'),
                     'logo': ((p or {}).get('info') or {}).get('imageUrl'), 'priceUsd': px or None, 'usd': round(amt * px, 2) if px else None,
                     'change24h': ((p or {}).get('priceChange') or {}).get('h24'), 'chain': (p or {}).get('chainId'), 'pairAddress': (p or {}).get('pairAddress')})
    rows.sort(key=lambda r: -(r['usd'] or 0))
    priced = [r for r in rows if r['usd']]
    out = {'address': a, 'supported': True, 'sol': round(sol, 6), 'solUsd': round(sol * sol_px, 2), 'tokens': rows[:60],
           'unpriced': len(rows) - len(priced), 'totalUsd': round(sol * sol_px + sum(r['usd'] for r in priced), 2)}
    _pf_cache[a] = (time.time(), out)
    return out


# ---- Image proxy for coin logos whose hosts forbid cross-site embedding ------------------------
from fastapi.responses import Response as _Resp
_img_cache = {}


@app.get('/api/reputation/img')
async def img_proxy(u: str):
    if not _re.match(r'^https://[\w.-]+/', u) or len(u) > 600:
        raise HTTPException(400, 'Bad image URL.')
    hit = _img_cache.get(u)
    if hit and time.time() - hit[0] < 3600:
        return _Resp(content=hit[1], media_type=hit[2], headers={'Cache-Control': 'public, max-age=3600'})
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as http:
            r = await http.get(u, headers={'accept': 'image/*'})
    except Exception:
        raise HTTPException(502, 'Image host unreachable.')
    ctype = r.headers.get('content-type', '').split(';')[0]
    b = r.content[:12]
    sniff = 'image/png' if b.startswith(b'\x89PNG') else 'image/jpeg' if b.startswith(b'\xff\xd8') else 'image/gif' if b[:4] == b'GIF8' else 'image/webp' if b[:4] == b'RIFF' and b[8:12] == b'WEBP' else None
    ctype = sniff or ctype
    if r.status_code != 200 or not sniff or len(r.content) > 2_500_000:
        raise HTTPException(415, 'Not a usable image.')
    if len(_img_cache) > 800:
        _img_cache.clear()
    _img_cache[u] = (time.time(), r.content, ctype)
    return _Resp(content=r.content, media_type=ctype, headers={'Cache-Control': 'public, max-age=3600'})


# ---- Social graph: follow / followers / following ----------------------------------------------
FOLLOW_PATH = DATA_DIR / 'follows.json'


def _fol():
    return _json_load(FOLLOW_PATH, {'following': {}})


@app.get('/api/reputation/follows/{address}')
async def follows(address: str, viewer: str = ''):
    a = primary_of(address)
    d = _fol()['following']
    following = d.get(a, [])
    followers = [x for x, lst in d.items() if a in lst]
    return {'address': a, 'followers': len(followers), 'following': len(following), 'followersList': followers[-30:][::-1], 'followingList': following[-30:][::-1],
            'viewerFollows': bool(viewer) and a in d.get(primary_of(viewer), [])}


class FollowIn(BaseModel):
    address: str
    session: str
    target: str
    follow: bool = True


@app.post('/api/reputation/follow')
async def follow(payload: FollowIn):
    me = _session_or_401(payload.address, payload.session)
    t = primary_of(payload.target)
    if t == me or not _re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', t):
        raise HTTPException(400, "Can't follow that.")
    async with _admin_lock:
        d = _fol()
        lst = d['following'].setdefault(me, [])
        if payload.follow and t not in lst:
            lst.append(t); d['following'][me] = lst[-2000:]
            notify(t, 'follow', f'@{handle_of(me)} started following you', f'/terminal/profile/{me}', me)
        elif not payload.follow and t in lst:
            lst.remove(t)
        _json_save(FOLLOW_PATH, d)
    return {'ok': True, 'following': payload.follow}


# ---- Trust score for ANY wallet (0–100, evidence-only, with the breakdown) ----------------------
_trust_cache: dict = {}  # address -> (at, result)
_trust_pending: set = set()


async def _trust_fill(a):
    try:
        _trust_cache[a] = (time.time(), await trust_score(a))
    except Exception:
        pass
    finally:
        _trust_pending.discard(a)


@app.get('/api/reputation/trust-batch')
async def trust_batch(addresses: str = Query('', max_length=2400)):
    """Rep marks for names on screen (chat, lists). Answers from cache instantly and scores missing
    wallets in the background, a few at a time, so a busy chat never stalls on RPC calls."""
    out = {}
    for raw in [x for x in addresses.split(',') if x][:50]:
        a = primary_of(raw.strip())
        hit = _trust_cache.get(a)
        if hit:
            r = hit[1]; out[raw] = {'score': r.get('score'), 'level': r.get('level'), 'blocked': any('Blocklisted' in p['label'] for p in r.get('parts', [])), 'gold': _gold_creator(a)}
        if (not hit or time.time() - hit[0] > 600) and a not in _trust_pending and len(_trust_pending) < 8:
            _trust_pending.add(a); asyncio.create_task(_trust_fill(a))
    return {'trust': out}


@app.get('/api/reputation/trust/{address}')
async def trust_score(address: str):
    a = primary_of(address)
    parts, score, evidence = [], 50, 0
    st = await wallet_stats(a) if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a) else {}
    age_d = (time.time() - st['firstSeen']) / 86400 if st.get('firstSeen') else (365 if st.get('txCountCapped') else None)
    if age_d is not None:
        evidence += 1
        pts = 10 if age_d >= 180 else 6 if age_d >= 30 else 0 if age_d >= 7 else -8
        score += pts; parts.append({'label': f'Wallet age {int(age_d)}d', 'points': pts})
    bl = _block_load()['wallets'].get(a)
    if bl and _is_blocked(bl):
        score -= 45; evidence += 1; parts.append({'label': f"Blocklisted — caught on {len(bl.get('mints') or {})} launch(es)", 'points': -45})
    elif bl:
        score -= 15; evidence += 1; parts.append({'label': 'Seen sniping/bundling (not yet blocklisted)', 'points': -15})
    creator = _load()['creators'].get(_creator_key('solana', a))
    if creator:
        sc = score_creator(creator); sc = {**sc, **_hygiene(a, sc)}
        if sc.get('score') is not None:
            evidence += 1
            pts = round((sc['score'] - 50) * 0.6)
            score += pts; parts.append({'label': f"Creator record: {sc['badge']} ({sc['score']})", 'points': pts})
    board = await caller_board(days=90)
    me = next((r for r in board['rows'] if r.get('callerAddress') == a), None)
    if me and me['calls'] >= 3:
        evidence += 1
        pts = round((me['hitRate'] - 0.3) * 30)
        score += pts; parts.append({'label': f"Calls: {me['calls']}, {round(me['hitRate'] * 100)}% hit 2×", 'points': pts})
    fol = len([x for x, lst in _fol()['following'].items() if a in lst])
    if fol:
        pts = min(8, fol); score += pts; parts.append({'label': f'{fol} followers', 'points': pts})
    try:
        sh = shield_record(a)
        if sh['broken']:
            score -= 35 * sh['broken']; evidence += 1; parts.append({'label': f"Broke {sh['broken']} FEELESS Shield promise(s)", 'points': -35 * sh['broken']})
        if sh['kept']:
            score += 8 * sh['kept']; evidence += 1; parts.append({'label': f"Kept {sh['kept']} FEELESS Shield(s) to the end", 'points': 8 * sh['kept']})
    except Exception:
        pass
    if is_verified(a):
        score += 10; evidence += 1; parts.append({'label': 'Verified by FEELESS', 'points': 10})
    if is_muted(a):
        score -= 10; parts.append({'label': 'Currently muted by moderators', 'points': -10})
    score = max(0, min(100, score))
    if evidence == 0:
        return {'address': a, 'score': None, 'level': 'unknown', 'parts': parts, 'note': 'Not enough on-chain or FEELESS history to score this wallet yet.'}
    level = 'high' if score >= 75 else 'good' if score >= 60 else 'caution' if score >= 40 else 'risky'
    return {'address': a, 'score': score, 'level': level, 'parts': parts, 'evidence': evidence}



@app.get('/api/reputation/chat/session/check')
async def session_check(address: str, session: str):
    owner = session_address(session)
    return {'valid': bool(owner) and primary_of(owner) == primary_of(address)}


# ---- Edge network memory: every Edge read is a prediction; 24h later we grade it ------------
# Per chain, per grade (A–F): how did coins FEELESS graded that way actually do? The Edge score
# reads this back as its "Network memory" factor, so each network's scoring learns from its own
# outcomes — Base memes and Solana memes don't behave alike, and the score stops pretending they do.
EDGE_MEM_PATH = DATA_DIR / 'edge_memory.json'
EDGE_HORIZON = 24 * 3600
_edge_lock = asyncio.Lock()


def _edge_grade(score):
    return 'A' if score >= 80 else 'B' if score >= 65 else 'C' if score >= 50 else 'D' if score >= 35 else 'F'


class EdgeObservation(BaseModel):
    chain: str
    pairAddress: str
    score: float
    priceUsd: float


@app.post('/api/reputation/edge/observe')
async def edge_observe(o: EdgeObservation):
    if not (0 <= o.score <= 100) or o.priceUsd <= 0 or len(o.pairAddress) > 80 or len(o.chain) > 24:
        raise HTTPException(400, 'bad observation')
    async with _edge_lock:
        d = _json_load(EDGE_MEM_PATH, {'open': {}, 'done': []})
        key = f'{o.chain}:{o.pairAddress}'
        prev = d['open'].get(key)
        if prev and time.time() - prev['at'] < 6 * 3600:  # one open prediction per coin per 6h
            return {'ok': True, 'dedup': True}
        d['open'][key] = {'chain': o.chain, 'pair': o.pairAddress, 'grade': _edge_grade(o.score), 'score': round(o.score, 1),
                          'price': o.priceUsd, 'peak': o.priceUsd, 'low': o.priceUsd, 'at': time.time()}
        if len(d['open']) > 5000:  # hard cap: drop the oldest
            for k in sorted(d['open'], key=lambda k: d['open'][k]['at'])[:len(d['open']) - 5000]:
                d['open'].pop(k)
        _json_save(EDGE_MEM_PATH, d)
    return {'ok': True}


async def _refresh_edge_memory():
    while True:
        try:
            d = _json_load(EDGE_MEM_PATH, {'open': {}, 'done': []})
            by_chain = {}
            for o in d['open'].values():
                by_chain.setdefault(o['chain'], []).append(o['pair'])
            live = {}
            async with httpx.AsyncClient(timeout=10) as http:
                for chain, pairs in by_chain.items():
                    for i in range(0, len(pairs), 30):
                        try:
                            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{",".join(pairs[i:i + 30])}')
                            for p in (r.json() or {}).get('pairs') or []:
                                live[f"{chain}:{p.get('pairAddress')}"] = float(p.get('priceUsd') or 0)
                        except Exception:
                            pass
                        await asyncio.sleep(0.3)
            async with _edge_lock:
                d = _json_load(EDGE_MEM_PATH, {'open': {}, 'done': []})
                now = time.time()
                for key, o in list(d['open'].items()):
                    px = live.get(key)
                    if px:
                        o['last'] = px; o['peak'] = max(o['peak'], px); o['low'] = min(o['low'], px); o['seen'] = now
                    if now - o['at'] >= EDGE_HORIZON:
                        # Pool gone from DexScreener for the whole window's end = liquidity pulled.
                        vanished = not px and now - o.get('seen', o['at']) > 6 * 3600
                        end = px or o.get('last') or o['price']
                        d['done'].append({'chain': o['chain'], 'grade': o['grade'], 'ret': -100.0 if vanished else round((end / o['price'] - 1) * 100, 2),
                                          'peak': round((o['peak'] / o['price'] - 1) * 100, 2), 'rug': vanished or end / o['price'] <= 0.3, 'at': now})
                        d['open'].pop(key)
                d['done'] = d['done'][-20000:]
                _json_save(EDGE_MEM_PATH, d)
        except Exception as exc:
            print('edge memory refresh error', exc)
        await asyncio.sleep(1200)


@app.on_event('startup')
async def _start_edge_memory():
    asyncio.create_task(_refresh_edge_memory())


@app.get('/api/reputation/edge/memory')
async def edge_memory(chain: str):
    d = _json_load(EDGE_MEM_PATH, {'open': {}, 'done': []})
    rows = [x for x in d['done'] if x['chain'] == chain]
    grades = {}
    for g in 'ABCDF':
        rs = sorted(x['ret'] for x in rows if x['grade'] == g)
        if not rs:
            continue
        grp = [x for x in rows if x['grade'] == g]
        grades[g] = {'n': len(rs), 'medianRet': rs[len(rs) // 2], 'rugRate': round(sum(1 for x in grp if x['rug']) / len(grp) * 100, 1),
                     'hitRate': round(sum(1 for x in grp if x['peak'] >= 50) / len(grp) * 100, 1)}
    return {'chain': chain, 'resolved': len(rows), 'pending': sum(1 for o in d['open'].values() if o['chain'] == chain), 'grades': grades}


# ---- Command center: the numbers side --------------------------------------------------------
# One call for everything an owner watches: $FEE market, holder base, treasury, swap flow through
# FEELESS (from stored on-chain receipts), and the scanner's output. A snapshot is kept per day,
# so growth lines build themselves from the first time the owner opens this.
NUMBERS_PATH = DATA_DIR / 'numbers_history.json'


@app.get('/api/reputation/admin/numbers')
async def admin_numbers(request: Request):
    admin = _require_admin(request)
    mints = await _ecosystem_mints()
    fee_mint = mints.get('fee')
    market = None
    if fee_mint:
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                pairs = (await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{fee_mint}')).json().get('pairs') or []
            if pairs:
                p = max(pairs, key=lambda x: (x.get('liquidity') or {}).get('usd') or 0)
                tx = p.get('txns') or {}
                market = {'price': float(p.get('priceUsd') or 0), 'marketCap': p.get('marketCap'), 'fdv': p.get('fdv'),
                          'liquidity': (p.get('liquidity') or {}).get('usd'), 'volume': p.get('volume') or {}, 'change': p.get('priceChange') or {},
                          'buys24': (tx.get('h24') or {}).get('buys'), 'sells24': (tx.get('h24') or {}).get('sells'),
                          'pools': len(pairs), 'pair': p.get('pairAddress'), 'dex': p.get('dexId')}
        except Exception:
            pass
    holders = None
    if fee_mint:
        try:
            data = await _token_holders(fee_mint)
            rows = data['rows']
            lp = {r['owner'] for r in rows[:3] if (r['pct'] or 0) > 20}
            real = [r for r in rows if r['owner'] not in lp]
            holders = {'count': data.get('holderCount') or len(rows), 'top1': round(real[0]['pct'], 2) if real else None,
                       'top10': round(sum(r['pct'] or 0 for r in real[:10]), 2), 'whales': sum(1 for r in real if (r['pct'] or 0) >= 1),
                       'lpExcluded': len(lp)}
        except Exception:
            pass
    tre = {}
    try:
        tre = await admin_treasury(request)
    except Exception:
        pass
    now = time.time()
    rc = _receipt_rows()
    def flow(since):
        rs = [r for r in rc if (r[0] or 0) >= since]
        return {'swaps': len(rs), 'solVolume': round(sum(abs(r[5] or 0) for r in rs), 3), 'traders': len({r[2] for r in rs})}
    stats = await live_stats()
    snap = {'price': (market or {}).get('price'), 'marketCap': (market or {}).get('marketCap'), 'liquidity': (market or {}).get('liquidity'),
            'holders': (holders or {}).get('count'), 'sol': tre.get('sol'), 'swaps': len(rc)}
    hist = _json_load(NUMBERS_PATH, {'days': {}})
    day = time.strftime('%Y-%m-%d', time.gmtime(now))
    if any(v is not None for v in snap.values()):
        hist['days'][day] = snap
        hist['days'] = dict(sorted(hist['days'].items())[-400:])
        _json_save(NUMBERS_PATH, hist)
    return {'wallet': admin, 'feeMint': fee_mint, 'market': market, 'holders': holders,
            'treasury': {'sol': tre.get('sol'), 'holdingsUsd': tre.get('holdingsUsd')},
            'flow': {'h24': flow(now - 86400), 'd7': flow(now - 7 * 86400), 'all': flow(0)},
            'scanner': {k: stats.get(k) for k in ('mintsScanned', 'snipers', 'bundlers', 'flaggedFunders', 'blocklisted', 'creators')},
            'history': [{'day': k, **v} for k, v in hist['days'].items()], 'at': now}


# ---- Rep: where a wallet stands, and the dark side of the market ------------------------------
@app.get('/api/reputation/standing/{address}')
async def wallet_standing(address: str):
    """One wallet across every category FEELESS scores, each with the evidence behind it and a
    percentile against every wallet FEELESS has scored in that category."""
    a = primary_of(address)
    trust = await trust_score(a)
    cats = [{'id': 'trust', 'label': 'Overall trust', 'score': trust.get('score'), 'detail': f"{len(trust.get('parts') or [])} signals", 'good': (trust.get('score') or 0) >= 60}]
    store = _load()
    creator = store['creators'].get(_creator_key('solana', a))
    all_creator_scores = [x.get('score') for x in (score_creator(c) for c in store['creators'].values()) if x.get('score') is not None]
    if creator:
        sc = score_creator(creator)
        pct = round(sum(1 for v in all_creator_scores if v <= (sc.get('score') or 0)) / max(1, len(all_creator_scores)) * 100) if sc.get('score') is not None else None
        cats.append({'id': 'creator', 'label': 'Creator record', 'score': sc.get('score'), 'percentile': pct,
                     'detail': f"{sc.get('badge')} · {sc.get('tokenCount', 0)} launches · {sc.get('dumpedCount', 0)} dumped", 'good': sc.get('badge') in ('trusted', 'veteran')})
    board = await caller_board(days=90)
    me = next((r for r in board['rows'] if r.get('callerAddress') == a), None)
    if me:
        rates = sorted(r['hitRate'] for r in board['rows'] if r['calls'] >= 3)
        pct = round(sum(1 for v in rates if v <= me['hitRate']) / max(1, len(rates)) * 100) if me['calls'] >= 3 else None
        cats.append({'id': 'caller', 'label': 'Caller', 'score': round(me['hitRate'] * 100), 'percentile': pct,
                     'detail': f"{me['calls']} calls · {me['hits']} hit 2× · {me.get('rugs', 0)} rugged", 'good': me['hitRate'] >= 0.3})
    bl = _block_load()['wallets'].get(a)
    strikes = len((bl or {}).get('mints') or {})
    roles = sorted(set((bl or {}).get('mints', {}).values()))
    cats.append({'id': 'clean', 'label': 'Sniper / bundler record', 'score': 100 if not strikes else max(0, 100 - strikes * 30),
                 'detail': 'never caught sniping or bundling' if not strikes else f"caught on {strikes} launch(es) as {', '.join(roles)}{' · BLOCKLISTED' if _is_blocked(bl) else ''}",
                 'good': not strikes})
    fd = _funders_load()
    frec = fd['funders'].get(a)
    funded_by = fd['offenderFunder'].get(a)
    if frec or funded_by:
        cats.append({'id': 'funding', 'label': 'Funding trail', 'score': 0 if frec and _is_flagged_funder(frec) else 40,
                     'detail': (f"bankrolled {len(frec['funded'])} sniper/bundler wallets across {len(frec['mints'])} launch(es)" if frec else '')
                               + (f"{' · ' if frec else ''}funded by {funded_by[:4]}…{funded_by[-4:]}" if funded_by else ''), 'good': False})
    fol = len([x for x, lst in _fol()['following'].items() if a in lst])
    cats.append({'id': 'social', 'label': 'Community', 'score': min(100, fol * 10), 'detail': f"{fol} followers{' · verified' if is_verified(a) else ''}", 'good': fol >= 3 or is_verified(a)})
    return {'address': a, 'trust': trust, 'categories': cats, 'at': time.time()}


_dark_cache = {}


@app.get('/api/reputation/darkside')
async def darkside(limit: int = Query(12, ge=1, le=50)):
    """The other side of the ledger: the wallets and money behind snipes, bundles and rugs."""
    hit = _dark_cache.get(limit)
    if hit and time.time() - hit[0] < 20:
        return hit[1]
    data = await _darkside_compute(limit)
    _dark_cache[limit] = (time.time(), data)
    return data


async def _darkside_compute(limit):
    bl = _block_load()['wallets']
    offenders = sorted(({'wallet': w, 'strikes': len(r.get('mints') or {}), 'roles': sorted(set((r.get('mints') or {}).values())),
                         'blocked': _is_blocked(r), 'lastSeen': r.get('lastSeen')} for w, r in bl.items() if r.get('mints')),
                       key=lambda x: (-x['strikes'], -(x['lastSeen'] or 0)))[:limit]
    fd = _funders_load()
    funders = sorted(({'wallet': w, 'walletsFunded': len(r.get('funded') or []), 'launches': len(r.get('mints') or {}),
                       'flagged': _is_flagged_funder(r), 'lastSeen': r.get('lastSeen')} for w, r in fd['funders'].items()),
                     key=lambda x: (-x['walletsFunded'], -x['launches']))[:limit]
    return {'offenders': offenders, 'funders': funders, 'whales': _radar['whales'][:limit],
            'rugs': [e for e in _radar['events'] if e['kind'] in ('rug', 'dump')][:limit], 'at': time.time()}


# ---- Gas check: native balance on every EVM chain, one call -----------------------------------
GAS_MIN_USD = {'ethereum': 3.0}  # everywhere else ~$0.25 covers several swaps
NATIVE_SYMBOL = {'ethereum': 'ETH', 'base': 'ETH', 'arbitrum': 'ETH', 'optimism': 'ETH', 'zksync': 'ETH', 'zora': 'ETH', 'unichain': 'ETH',
                 'worldchain': 'ETH', 'bsc': 'BNB', 'avalanche': 'AVAX', 'polygon': 'POL', 'cronos': 'CRO'}
_native_px = {'at': 0, 'px': {}}


async def _native_prices(http):
    if time.time() - _native_px['at'] < 300 and _native_px['px']:
        return _native_px['px']
    ids = {'ETH': 'ethereum', 'BNB': 'binancecoin', 'AVAX': 'avalanche-2', 'POL': 'polygon-ecosystem-token', 'CRO': 'crypto-com-chain'}
    px = {}
    for sym, q in (('ETH', 'WETH'), ('BNB', 'WBNB'), ('AVAX', 'WAVAX'), ('POL', 'WPOL'), ('CRO', 'WCRO')):
        try:
            pairs = (await http.get('https://api.dexscreener.com/latest/dex/search', params={'q': f'{q} USDC'})).json().get('pairs') or []
            best = max((p for p in pairs if (p.get('baseToken') or {}).get('symbol') == q), key=lambda p: (p.get('liquidity') or {}).get('usd') or 0, default=None)
            if best:
                px[sym] = float(best.get('priceUsd') or 0)
        except Exception:
            pass
    _native_px.update(at=time.time(), px=px)
    return px


@app.get('/api/reputation/gas/{address}')
async def gas_check(address: str):
    """Which chains this wallet can (and can't) pay gas on — so the trade desk can offer a one-click
    route that converts something it already holds into gas where it's missing."""
    if not _re.match(r'^0x[0-9a-fA-F]{40}$', address):
        raise HTTPException(400, 'EVM address required (0x…).')
    async with httpx.AsyncClient(timeout=8) as http:
        px = await _native_prices(http)

        async def bal(chain, url):
            try:
                r = await http.post(url, json={'jsonrpc': '2.0', 'id': 1, 'method': 'eth_getBalance', 'params': [address, 'latest']})
                return chain, int(r.json()['result'], 16) / 1e18
            except Exception:
                return chain, None
        res = await asyncio.gather(*(bal(c, u) for c, u in EVM_RPC.items()))
    out = []
    for chain, amt in res:
        sym = NATIVE_SYMBOL.get(chain, 'ETH'); usd = amt * px.get(sym, 0) if amt is not None else None
        need = GAS_MIN_USD.get(chain, 0.25)
        out.append({'chain': chain, 'symbol': sym, 'balance': amt, 'usd': round(usd, 2) if usd is not None else None,
                    'enough': usd is not None and usd >= need, 'minUsd': need})
    return {'address': address, 'chains': sorted(out, key=lambda x: -(x['usd'] or 0)), 'at': time.time()}


@app.get('/api/reputation/fees/public')
async def fees_public():
    cfg = _fee_cfg()
    return {'platformFeeBps': cfg['platformFeeBps'], 'tierDiscountPct': cfg['tierDiscountPct'], 'promo': cfg.get('promo'),
            'feelessIntoFee': True, 'note': 'Trades into or out of $FEE-ecosystem coins never carry a FEELESS fee.'}


# ---- Holder themes: $1k+ in the FEELESS ecosystem recolors the logo + the whole site ----------
THEME_MIN_USD = 1000.0
POOL_BUILDER_MIN_USD = 5000.0
THEMES_PATH = DATA_DIR / 'themes.json'
_HEX = _re.compile(r'^#[0-9a-fA-F]{6}$')


async def _eco_holding_usd(address: str) -> float:
    if address.startswith('0x'):
        return 0.0
    total = 0.0
    for mint in (await _ecosystem_mints()).values():
        try:
            total += await _holding_usd(address, mint) or 0
        except Exception:
            pass
    return round(total, 2)


@app.get('/api/reputation/theme/{address}')
async def theme_get(address: str):
    a = primary_of(address)
    held = await _eco_holding_usd(a)
    saved = _json_load(THEMES_PATH, {}).get(a)
    if held >= POOL_BUILDER_MIN_USD:
        seen = _json_load(DATA_DIR / 'perk_notices.json', {})
        if not seen.get(a):
            seen[a] = time.time(); _json_save(DATA_DIR / 'perk_notices.json', seen)
            notify(a, 'perk', f'🏗 Pool builder unlocked — you hold ${held:,.0f} of $FEE coins. Open your profile to build pools.', f'/terminal/profile/{a}', a)
    return {'address': a, 'holdingUsd': held, 'poolBuilder': held >= POOL_BUILDER_MIN_USD, 'minUsd': THEME_MIN_USD, 'eligible': held >= THEME_MIN_USD,
            'theme': saved if held >= THEME_MIN_USD else None}


class ThemePayload(BaseModel):
    address: str
    session: str
    accent: str
    accent2: Optional[str] = None
    logo: Optional[str] = None


@app.post('/api/reputation/theme')
async def theme_set(p: ThemePayload):
    if primary_of(session_address(p.session) or '') != primary_of(p.address):
        raise HTTPException(401, 'Sign in again to change your theme.')
    for c in (p.accent, p.accent2, p.logo):
        if c is not None and not _HEX.match(c):
            raise HTTPException(400, 'Colors must be #RRGGBB.')
    a = primary_of(p.address)
    held = await _eco_holding_usd(a)
    if held < THEME_MIN_USD:
        raise HTTPException(403, f'Custom site colors unlock at ${THEME_MIN_USD:,.0f} held across $FEE coins (you hold ${held:,.2f}).')
    d = _json_load(THEMES_PATH, {})
    d[a] = {'accent': p.accent, 'accent2': p.accent2 or p.accent, 'logo': p.logo or p.accent, 'at': time.time()}
    _json_save(THEMES_PATH, d)
    return {'ok': True, 'theme': d[a]}


# ---- Meta engine: which narratives are forming, rising or dying, across every chain ------------
META_FAMILIES = {
    'ai': {'ai', 'agent', 'agents', 'gpt', 'bot', 'neural', 'agi', 'llm', 'deepseek', 'grok', 'claude', 'swarm'},
    'dog': {'dog', 'doge', 'inu', 'shib', 'wif', 'pup', 'puppy', 'bonk', 'shiba', 'corgi', 'dogwifhat'},
    'cat': {'cat', 'kitty', 'meow', 'mew', 'popcat', 'neko', 'kitten', 'mog'},
    'frog': {'frog', 'pepe', 'kek', 'toad', 'ribbit'},
    'politics': {'trump', 'maga', 'biden', 'melania', 'vance', 'usa', 'america', 'president', 'election', 'kamala'},
    'elon': {'elon', 'musk', 'tesla', 'spacex', 'x', 'doge'},
    'anime': {'anime', 'waifu', 'chan', 'kun', 'senpai', 'manga'},
    'gaming': {'game', 'gaming', 'play', 'pixel', 'quest', 'arcade'},
    'rwa': {'gold', 'rwa', 'treasury', 'bond', 'stock'},
    'food': {'burger', 'pizza', 'taco', 'sushi', 'banana', 'cheese'},
}
_META_STOP = {'the', 'of', 'and', 'coin', 'token', 'sol', 'eth', 'on', 'a', 'to', 'in', 'is', 'usd', 'usdc', 'wrapped', 'finance', 'protocol', 'official', 'v2', 'inu',
              'tether', 'usdt', 'btc', 'bitcoin', 'ethereum', 'ether', 'coinbase', 'staked', 'bridged', 'binance', 'bnb', 'arbitrum', 'avalanche', 'avax',
              'polygon', 'pol', 'matic', 'cronos', 'cro', 'optimism', 'base', 'solana', 'wbtc', 'weth', 'dai', 'stable', 'dollar', 'pegged', 'liquid', 'lido', 'restaked', 'cake', 'pancakeswap', 'uniswap', 'world', 'chain', 'network', 'swap', 'dao'}
_MAJOR_SYMBOLS = {'USDT', 'USDC', 'USDT0', 'DAI', 'WETH', 'WBTC', 'CBBTC', 'BTC.B', 'CBETH', 'WSTETH', 'STETH', 'WBNB', 'WAVAX', 'WPOL', 'WMATIC', 'WCRO', 'ARB', 'OP', 'ZK', 'SOL', 'WSOL', 'JITOSOL', 'MSOL', 'XAUT', 'PAXG', 'EURC', 'USDE', 'FDUSD', 'PYUSD', 'SUSDE'}
_meta_cache = {'at': 0, 'data': None}
_meta_hist = []   # (time, {meta: volShare})
META_CHAINS = ['solana', 'base', 'bsc', 'ethereum', 'arbitrum', 'avalanche', 'polygon', 'sui', 'cronos', 'optimism', 'unichain', 'worldchain', 'zksync']


def _meta_words(p):
    bt = p.get('baseToken') or {}
    raw = f"{bt.get('name') or ''} {bt.get('symbol') or ''}".lower()
    words = set(_re.findall(r'[a-z]{2,}', raw)) - _META_STOP
    fams = {f for f, vocab in META_FAMILIES.items() if words & vocab or any(v in raw.replace(' ', '') for v in vocab if len(v) >= 4)}
    return words, fams


@app.on_event('startup')
async def _start_metas():
    async def loop():
        await asyncio.sleep(30)
        while True:
            try:
                await metas(refresh=True)
            except Exception as exc:
                print('meta engine error', exc)
            await asyncio.sleep(120)
    asyncio.create_task(loop())


@app.get('/api/reputation/metas')
async def metas_public():
    return await metas(refresh=False)


async def metas(refresh: bool = False):
    # Users always get the background-computed snapshot instantly; only the loop recomputes.
    if not refresh and _meta_cache['data']:
        return _meta_cache['data']
    if not refresh and not _meta_cache['data']:
        return {'metas': [], 'coinsScanned': 0, 'chains': len(META_CHAINS), 'warming': True, 'at': time.time()}
    pairs = []
    async with httpx.AsyncClient(timeout=20) as http:
        async def pull(chain, kind):
            try:
                r = await http.get('http://127.0.0.1:5001/api/market/feed', params={'chain': chain, 'kind': kind})
                return r.json().get('pairs') or [] if r.status_code == 200 else []
            except Exception:
                return []
        for batch in await asyncio.gather(*(pull(c, k) for c in META_CHAINS for k in ('trending', 'new'))):
            pairs += batch
    uniq = {}
    for p in pairs:
        k = (p.get('chainId'), (p.get('baseToken') or {}).get('address'))
        if k[1] and k not in uniq:
            uniq[k] = p
    pairs = [p for p in uniq.values() if ((p.get('baseToken') or {}).get('symbol') or '').upper().strip() not in _MAJOR_SYMBOLS
             and not _re.search(r'usd|tether|bitcoin|wrapped|staked|bridged', ((p.get('baseToken') or {}).get('name') or '').lower())]
    groups, word_count = {}, {}
    for p in pairs:
        words, fams = _meta_words(p)
        for f in fams:
            groups.setdefault(f, []).append(p)
        for w in words:
            word_count.setdefault(w, []).append(p)
    # Emergent metas: a fresh word 3+ unrelated coins share that isn't already a family.
    for w, members in word_count.items():
        if len(members) >= 3 and len(w) >= 3 and not any(w in v for v in META_FAMILIES.values()):
            if len({(m.get('baseToken') or {}).get('symbol', '').upper() for m in members}) >= 3:
                groups.setdefault(w, members)
    total_vol = sum(float((p.get('volume') or {}).get('h24') or 0) for p in pairs) or 1
    now_ms = time.time() * 1000
    prev = next((h for t, h in reversed(_meta_hist) if time.time() - t >= 3000), None)
    out = []
    for name, members in groups.items():
        vol = sum(float((m.get('volume') or {}).get('h24') or 0) for m in members)
        ch = sorted(c for c in (float((m.get('priceChange') or {}).get('h24')) for m in members if (m.get('priceChange') or {}).get('h24') is not None) if abs(c) < 2000)
        fresh = sum(1 for m in members if m.get('pairCreatedAt') and now_ms - m['pairCreatedAt'] < 86400000)
        flagged = 0
        for m in members:
            hit = _intel_cache.get((m.get('baseToken') or {}).get('address'))
            if hit and hit[1] and (len(hit[1].get('sniperWallets') or []) >= 5 or len(hit[1].get('bundledWallets') or []) >= 3 or hit[1].get('flaggedFunders')):
                flagged += 1
        share = vol / total_vol
        trend = None if not prev or name not in prev else round((share - prev[name]) / max(prev[name], 1e-6) * 100, 1)
        top = sorted(members, key=lambda m: -float((m.get('volume') or {}).get('h24') or 0))[:8]
        out.append({'meta': name, 'family': name in META_FAMILIES, 'coins': len(members), 'volume24h': round(vol), 'volumeShare': round(share * 100, 2),
                    'avgChange24h': round(ch[len(ch) // 2], 1) if ch else None, 'freshLaunches24h': fresh,
                    'chains': sorted({m.get('chainId') for m in members}), 'riskShare': round(flagged / len(members) * 100) if members else 0,
                    'trend1h': trend, 'status': 'forming' if fresh >= max(2, len(members) * 0.5) else ('rising' if (trend or 0) > 10 else 'fading' if (trend or 0) < -10 else 'steady'),
                    'top': [{'symbol': (m.get('baseToken') or {}).get('symbol'), 'chain': m.get('chainId'), 'pairAddress': m.get('pairAddress'),
                             'change24h': (m.get('priceChange') or {}).get('h24'), 'volume24h': (m.get('volume') or {}).get('h24'),
                             'imageUrl': (m.get('info') or {}).get('imageUrl')} for m in top]})
    out.sort(key=lambda x: (-x['volume24h']))
    seen, deduped = set(), []
    for m in out:  # the same coins under two words = one meta (keep the family / longer name)
        sig = tuple(sorted(t['pairAddress'] or '' for t in m['top']))
        if sig in seen:
            continue
        seen.add(sig); deduped.append(m)
    out = deduped
    _meta_hist.append((time.time(), {m['meta']: m['volumeShare'] / 100 for m in out}))
    del _meta_hist[:-40]
    data = {'metas': out[:24], 'coinsScanned': len(pairs), 'chains': len(META_CHAINS), 'at': time.time()}
    _meta_cache.update(at=time.time(), data=data)
    return data


# ---- A Solana wallet's own swaps, parsed from its transactions (Helius) --------------------------
_STABLES = {'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'}


async def _maker_swaps(http, address):
    """[{ts, side, usd, price, token, tx}] for the wallet's recent swaps. SOL legs are priced at the
    live SOL rate; stablecoin legs count 1:1. [] when Helius is not configured."""
    key_ = _helius_key()
    if not key_:
        return []
    try:
        txs = (await http.get(f'https://api.helius.xyz/v0/addresses/{address}/transactions', params={'api-key': key_, 'type': 'SWAP', 'limit': 100})).json()
        sol_usd = float(((await http.get(f'https://lite-api.jup.ag/price/v3?ids={WSOL}')).json().get(WSOL) or {}).get('usdPrice') or 0)
    except Exception:
        return []
    out = []
    for tx in txs if isinstance(txs, list) else []:
        delta, quote_usd = {}, 0.0
        for t in tx.get('tokenTransfers') or []:
            amt = float(t.get('tokenAmount') or 0) * (1 if t.get('toUserAccount') == address else -1 if t.get('fromUserAccount') == address else 0)
            if not amt:
                continue
            if t.get('mint') == WSOL:
                quote_usd += amt * sol_usd
            elif t.get('mint') in _STABLES:
                quote_usd += amt
            else:
                delta[t['mint']] = delta.get(t['mint'], 0) + amt
        if not quote_usd:  # native SOL leg only when there was no wrapped-SOL/stable leg (else it's the same SOL twice)
            for n in tx.get('nativeTransfers') or []:
                lam = float(n.get('amount') or 0) / 1e9
                quote_usd += lam * sol_usd * (1 if n.get('toUserAccount') == address else -1 if n.get('fromUserAccount') == address else 0)
        moved = [(m, a) for m, a in delta.items() if a]
        if len(moved) != 1 or not quote_usd:
            continue  # token-for-token routes or transfers without a priced leg
        mint, amt = moved[0]
        usd = abs(quote_usd)
        out.append({'ts': tx.get('timestamp') or 0, 'side': 'buy' if amt > 0 else 'sell', 'usd': round(usd, 2),
                    'price': usd / abs(amt), 'token': mint, 'tx': tx.get('signature')})
    return out


# ---- KOL tracker: real trades of wallets FEELESS admins mark as KOLs, and why the pattern matters --
KOLS_PATH = DATA_DIR / 'kols.json'
_kol_cache = {}


class KolPayload(BaseModel):
    address: str
    name: str
    x: Optional[str] = ''
    chain: str = 'solana'


@app.post('/api/reputation/admin/kols')
async def admin_kol_add(request: Request, p: KolPayload):
    admin = _require_admin(request)
    if p.chain != 'solana' or not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.address):
        raise HTTPException(400, 'KOL tracking reads Solana wallets — enter a valid Solana address.')
    d = _json_load(KOLS_PATH, {})
    d[p.address] = {'name': p.name[:40], 'x': (p.x or '').lstrip('@')[:30], 'chain': p.chain, 'addedBy': admin, 'at': time.time()}
    _json_save(KOLS_PATH, d)
    return {'ok': True}


@app.delete('/api/reputation/admin/kols/{address}')
async def admin_kol_remove(request: Request, address: str):
    _require_admin(request)
    d = _json_load(KOLS_PATH, {}); d.pop(address, None); _json_save(KOLS_PATH, d)
    return {'ok': True}


async def _kol_stats(address, chain):
    hit = _kol_cache.get(address)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    if chain != 'solana' or not _helius_key():
        return None
    async with httpx.AsyncClient(timeout=15) as http:
        items = await _maker_swaps(http, address)
    by = {}
    for e in items:
        t = by.setdefault(e['token'], {'buys': [], 'sells': []})
        t['buys' if e['side'] == 'buy' else 'sells'].append((e['ts'], e['usd']))
    tokens, holds, flips, dumps, wins, closed = [], [], 0, 0, 0, 0
    for tok, t in by.items():
        bought = sum(u for _, u in t['buys']); sold = sum(u for _, u in t['sells'])
        if t['buys'] and t['sells']:
            first_buy = min(ts for ts, _ in t['buys']); first_sell = min((ts for ts, _ in t['sells'] if ts >= first_buy), default=None)
            if first_sell:
                closed += 1
                hold = (first_sell - first_buy) / 60; holds.append(hold)
                flips += hold <= 60
                dumps += (sold >= bought * 0.8 and hold <= 120)
                wins += sold > bought
        tokens.append({'token': tok, 'boughtUsd': round(bought), 'soldUsd': round(sold), 'pnlUsd': round(sold - bought) if t['sells'] else None, 'trades': len(t['buys']) + len(t['sells'])})
    tokens.sort(key=lambda x: -(x['boughtUsd'] + x['soldUsd']))
    avg_hold = sorted(holds)[len(holds) // 2] if holds else None
    flags = []
    if closed >= 3 and flips / closed >= 0.5:
        flags.append(f"Flips {round(flips / closed * 100)}% of positions within an hour — anyone buying after their call is likely their exit liquidity.")
    if closed >= 3 and dumps / closed >= 0.4:
        flags.append(f"Dumped most of the bag within 2h on {round(dumps / closed * 100)}% of coins — the classic call-and-dump pattern.")
    if closed >= 3 and wins / closed >= 0.7 and avg_hold is not None and avg_hold < 90:
        flags.append("Wins mostly by selling fast into buying pressure — their profit is often their followers' loss.")
    if not flags and closed >= 3:
        flags.append('No call-and-dump pattern in their recent trades.')
    stats = {'tradesSeen': len(items), 'tokens': len(by), 'closed': closed, 'medianHoldMin': round(avg_hold) if avg_hold is not None else None,
             'quickFlipPct': round(flips / closed * 100) if closed else None, 'dumpPct': round(dumps / closed * 100) if closed else None,
             'winPct': round(wins / closed * 100) if closed else None, 'netUsd': round(sum((x['pnlUsd'] or 0) for x in tokens)),
             'flags': flags, 'topTokens': tokens[:8], 'danger': bool(closed >= 3 and (flips / closed >= 0.5 or dumps / closed >= 0.4))}
    _kol_cache[address] = (time.time(), stats)
    return stats


@app.get('/api/reputation/kols')
async def kols():
    d = _json_load(KOLS_PATH, {})
    rows = await asyncio.gather(*(_kol_stats(a, v['chain']) for a, v in d.items()))
    return {'kols': [{'address': a, **v, 'stats': s} for (a, v), s in zip(d.items(), rows)], 'at': time.time()}


# ---- Traffic analytics for marketing: what people actually view (privacy-light) -----------------
# No raw IPs or wallets stored: visitors are a salted SHA-256 of IP+day (salt rotates daily), so
# uniques can be counted per day but never linked across days. Writes are batched in memory and
# flushed every 30s so page views cost no disk I/O at request time.
import hashlib as _hashlib, secrets as _secrets
TRAFFIC_PATH = DATA_DIR / 'traffic.json'
_tr_buf = {'views': {}, 'uniq': {}, 'coins': {}, 'refs': {}, 'hours': {}}
_tr_salt = {'day': '', 'salt': ''}
_tr_ip = {}


class PageView(BaseModel):
    path: str
    ref: Optional[str] = ''


@app.post('/api/reputation/pv')
async def page_view(request: Request, p: PageView):
    ip = request.headers.get('x-forwarded-for', request.client.host if request.client else '?').split(',')[0].strip()
    now = time.time()
    hits = [t for t in _tr_ip.get(ip, []) if now - t < 60]
    if len(hits) >= 120:
        return {'ok': False}
    _tr_ip[ip] = hits + [now]
    day = time.strftime('%Y-%m-%d', time.gmtime(now))
    if _tr_salt['day'] != day:
        _tr_salt.update(day=day, salt=_secrets.token_hex(16))
    who = _hashlib.sha256(f"{_tr_salt['salt']}{ip}".encode()).hexdigest()[:16]
    path = _re.sub(r'[^a-zA-Z0-9/_-]', '', p.path.split('?')[0])[:80] or '/'
    page = _re.sub(r'/(profile|coin)/[^/]+', r'/\1/:id', path)
    b = _tr_buf
    b['views'].setdefault(day, {}); b['views'][day][page] = b['views'][day].get(page, 0) + 1
    b['uniq'].setdefault(day, set()).add(who)
    m = _re.search(r'[?&]pair=([A-Za-z0-9]+)', p.path) or _re.search(r'coin=([a-z]+):([A-Za-z0-9]+)', p.path)
    if m:
        key = m.group(m.lastindex)
        b['coins'][key] = b['coins'].get(key, 0) + 1
    host = (_re.match(r'https?://([^/]+)', p.ref or '') or [None, None])[1]
    if host and 'localhost' not in host:
        b['refs'][host] = b['refs'].get(host, 0) + 1
    h = time.gmtime(now).tm_hour
    b['hours'][h] = b['hours'].get(h, 0) + 1
    return {'ok': True}


async def _flush_traffic():
    while True:
        await asyncio.sleep(30)
        b = _tr_buf
        if not any(b[k] for k in b):
            continue
        d = _json_load(TRAFFIC_PATH, {'views': {}, 'uniques': {}, 'coins': {}, 'refs': {}, 'hours': {}})
        for day, pages in b['views'].items():
            dd = d['views'].setdefault(day, {})
            for pg, n in pages.items():
                dd[pg] = dd.get(pg, 0) + n
        for day, s in b['uniq'].items():
            d.setdefault('uniqHashes', {}).setdefault(day, [])
            merged = set(d['uniqHashes'][day]) | s
            d['uniqHashes'][day] = list(merged)[:200000]
            d['uniques'][day] = len(merged)
        for k in ('coins', 'refs'):
            for key, n in b[k].items():
                d[k][key] = d[k].get(key, 0) + n
        for hr, n in b['hours'].items():
            d['hours'][str(hr)] = d['hours'].get(str(hr), 0) + n
        keep = sorted(d['views'])[-60:]
        d['views'] = {k: d['views'][k] for k in keep}; d['uniques'] = {k: v for k, v in d['uniques'].items() if k in keep}
        d['uniqHashes'] = {k: v for k, v in d.get('uniqHashes', {}).items() if k == keep[-1]}  # only today's hashes are kept
        _json_save(TRAFFIC_PATH, d)
        for k in b:
            b[k] = {}


@app.on_event('startup')
async def _start_traffic():
    asyncio.create_task(_flush_traffic())


@app.get('/api/reputation/admin/traffic')
async def admin_traffic(request: Request):
    _require_admin(request)
    d = _json_load(TRAFFIC_PATH, {'views': {}, 'uniques': {}, 'coins': {}, 'refs': {}, 'hours': {}})
    days = sorted(d['views'])[-14:]
    def top(pages_by_day, n=12):
        agg = {}
        for day in pages_by_day:
            for pg, c in d['views'].get(day, {}).items():
                agg[pg] = agg.get(pg, 0) + c
        return sorted(({'page': k, 'views': v} for k, v in agg.items()), key=lambda x: -x['views'])[:n]
    return {'daily': [{'day': k, 'views': sum(d['views'][k].values()), 'uniques': d['uniques'].get(k, 0)} for k in days],
            'topPages24h': top(days[-1:]), 'topPages7d': top(days[-7:]),
            'topCoins': sorted(({'pair': k, 'views': v} for k, v in d['coins'].items()), key=lambda x: -x['views'])[:12],
            'referrers': sorted(({'host': k, 'visits': v} for k, v in d['refs'].items()), key=lambda x: -x['visits'])[:10],
            'hours': [d['hours'].get(str(h), 0) for h in range(24)], 'topClicks': (await top_clicks(limit=10))['rows']}


# ================================================================================================
# FEELESS SHIELD — launches that make rugging structurally costly.
# A creator signs public promises (dev keeps X% for N days, no wallet above Y%, no known snipers).
# FEELESS checks every shielded launch on-chain, continuously. Breaking a promise is a permanent,
# public strike on the creator's reputation — it can't be deleted and it follows every future launch.
# (Honest scope: this is verification + consequences, not an on-chain lock contract.)
# ================================================================================================
SHIELD_PATH = DATA_DIR / 'shields.json'


class ShieldPayload(BaseModel):
    address: str
    session: str
    mint: str
    devKeepPct: float = 90       # dev must keep at least this % of its launch allocation
    lockDays: int = 30
    maxWalletPct: float = 5      # no non-pool wallet above this % of supply
    noKnownSnipers: bool = True  # no blocklisted wallet among early buyers


@app.post('/api/reputation/shield')
async def shield_commit(p: ShieldPayload):
    me = _session_or_401(p.address, p.session)
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.mint):
        raise HTTPException(400, 'Solana mint address required.')
    if not (50 <= p.devKeepPct <= 100 and 7 <= p.lockDays <= 365 and 0.5 <= p.maxWalletPct <= 20):
        raise HTTPException(400, 'Shield terms out of range (keep 50–100%, lock 7–365 days, max wallet 0.5–20%).')
    d = _json_load(SHIELD_PATH, {})
    if p.mint in d:
        raise HTTPException(409, 'This coin already has a Shield — promises can’t be rewritten.')
    try:
        data = await _token_holders(p.mint)
        mine = sum((r['pct'] or 0) for r in data['rows'] if r['owner'] == me)
    except Exception:
        mine = None
    d[p.mint] = {'creator': me, 'devKeepPct': p.devKeepPct, 'lockDays': p.lockDays, 'maxWalletPct': p.maxWalletPct,
                 'noKnownSnipers': p.noKnownSnipers, 'devStartPct': mine, 'at': time.time(), 'breaches': []}
    _json_save(SHIELD_PATH, d)
    return {'ok': True, 'shield': d[p.mint]}


async def _shield_check(mint, s):
    """Live compliance for one shielded coin. Appends (never removes) breaches."""
    now = time.time(); active = now - s['at'] < s['lockDays'] * 86400
    checks = []
    try:
        data = await _token_holders(mint)
        rows = data['rows']
        dev = sum((r['pct'] or 0) for r in rows if r['owner'] == s['creator'])
        lp = {r['owner'] for r in rows[:3] if (r['pct'] or 0) > 20}
        biggest = max(((r['pct'] or 0, r['owner']) for r in rows if r['owner'] not in lp and r['owner'] != s['creator']), default=(0, None))
        if s.get('devStartPct'):
            kept = dev / s['devStartPct'] * 100
            checks.append({'rule': f"Dev keeps ≥{s['devKeepPct']:.0f}% of its bag", 'ok': kept >= s['devKeepPct'] or not active, 'detail': f"dev holds {dev:.2f}% of supply ({kept:.0f}% of launch bag)"})
        checks.append({'rule': f"No wallet above {s['maxWalletPct']:.1f}%", 'ok': biggest[0] <= s['maxWalletPct'], 'detail': f"largest non-pool wallet {biggest[0]:.2f}%"})
    except Exception:
        checks.append({'rule': 'Holder read', 'ok': True, 'detail': 'chain read unavailable — retrying'})
    if s['noKnownSnipers']:
        intel = (_intel_cache.get(mint) or (0, None))[1]
        if intel:
            bl = _block_load()['wallets']
            known = [w for w in (intel.get('sniperWallets') or []) + (intel.get('bundledWallets') or []) if _is_blocked(bl.get(w))]
            checks.append({'rule': 'No known snipers at launch', 'ok': not known, 'detail': f"{len(known)} blocklisted wallet(s) bought the launch" if known else 'no blocklisted buyers'})
    broken = [c for c in checks if not c['ok']]
    if broken:
        d = _json_load(SHIELD_PATH, {})
        rec = d.get(mint)
        if rec:
            for c in broken:
                if not any(b['rule'] == c['rule'] for b in rec['breaches']):
                    rec['breaches'].append({'rule': c['rule'], 'detail': c['detail'], 'at': now})
            _json_save(SHIELD_PATH, d)
            s = rec
    status = 'broken' if s.get('breaches') else ('active' if active else 'completed')
    return {'mint': mint, **{k: s[k] for k in ('creator', 'devKeepPct', 'lockDays', 'maxWalletPct', 'noKnownSnipers', 'at')},
            'endsAt': s['at'] + s['lockDays'] * 86400, 'status': status, 'checks': checks, 'breaches': s.get('breaches', [])}


@app.get('/api/reputation/shield/{mint}')
async def shield_get(mint: str):
    s = _json_load(SHIELD_PATH, {}).get(mint)
    if not s:
        return {'mint': mint, 'status': 'none'}
    return await _shield_check(mint, s)


@app.get('/api/reputation/shields')
async def shields_list():
    d = _json_load(SHIELD_PATH, {})
    return {'shields': [{'mint': m, 'creator': s['creator'], 'status': 'broken' if s['breaches'] else ('active' if time.time() - s['at'] < s['lockDays'] * 86400 else 'completed'),
                         'breaches': len(s['breaches']), 'at': s['at']} for m, s in sorted(d.items(), key=lambda x: -x[1]['at'])][:100]}


def shield_record(creator: str):
    """For trust/creator scoring: kept vs broken shields."""
    d = _json_load(SHIELD_PATH, {})
    mine = [s for s in d.values() if s['creator'] == creator]
    return {'kept': sum(1 for s in mine if not s['breaches'] and time.time() - s['at'] >= s['lockDays'] * 86400), 'broken': sum(1 for s in mine if s['breaches']), 'active': sum(1 for s in mine if not s['breaches'] and time.time() - s['at'] < s['lockDays'] * 86400)}


async def _shield_watch():
    while True:
        await asyncio.sleep(600)
        for mint, s in list(_json_load(SHIELD_PATH, {}).items()):
            if time.time() - s['at'] < s['lockDays'] * 86400 + 86400:
                try:
                    await _shield_check(mint, s)
                except Exception:
                    pass
                await asyncio.sleep(2)


@app.on_event('startup')
async def _start_shield_watch():
    asyncio.create_task(_shield_watch())


# ================================================================================================
# SEASONS — monthly competitions that reward trust, not volume.
# ================================================================================================
SEASONS_PATH = DATA_DIR / 'seasons.json'
SEASON_TIERS = [('Recruit', 0), ('Bronze', 250), ('Silver', 750), ('Gold', 2000), ('Diamond', 5000), ('Legend', 12000)]


def _seasons():
    return _json_load(SEASONS_PATH, {'seasons': [], 'scores': {}})


def _current_season(d=None):
    d = d or _seasons(); now = time.time()
    return next((s for s in d['seasons'] if s['start'] <= now < s['end']), None)


def season_award(address: str, points: float, reason: str):
    """Called wherever FEELESS awards points. Blocklisted wallets never score."""
    d = _seasons(); s = _current_season(d)
    if not s or points <= 0 or _is_blocked(_block_load()['wallets'].get(address)):
        return
    sc = d['scores'].setdefault(s['id'], {})
    rec = sc.setdefault(address, {'score': 0, 'events': 0})
    rec['score'] = round(rec['score'] + points * float(s.get('multiplier') or 1), 1); rec['events'] += 1; rec['last'] = reason
    _json_save(SEASONS_PATH, d)


def _tier(score):
    name = SEASON_TIERS[0][0]
    for n, need in SEASON_TIERS:
        if score >= need:
            name = n
    nxt = next(((n, need) for n, need in SEASON_TIERS if need > score), None)
    return {'tier': name, 'next': nxt[0] if nxt else None, 'toNext': round(nxt[1] - score) if nxt else 0}


@app.get('/api/reputation/season')
async def season_get(address: str = ''):
    d = _seasons(); s = _current_season(d)
    upcoming = sorted((x for x in d['seasons'] if x['start'] > time.time()), key=lambda x: x['start'])[:1]
    if not s:
        return {'season': None, 'upcoming': upcoming[0] if upcoming else None, 'tiers': SEASON_TIERS}
    sc = d['scores'].get(s['id'], {})
    board = sorted(sc.items(), key=lambda kv: -kv[1]['score'])
    top = [{'rank': i + 1, 'address': a, 'handle': handle_of(a), 'name': _display_name(a), 'score': r['score'], **_tier(r['score'])} for i, (a, r) in enumerate(board[:25])]
    me = None
    if address:
        a = primary_of(address); r = sc.get(a)
        rank = next((i + 1 for i, (x, _) in enumerate(board) if x == a), None)
        me = {'address': a, 'score': r['score'] if r else 0, 'rank': rank, 'players': len(board), **_tier(r['score'] if r else 0)}
    return {'season': s, 'endsIn': round(s['end'] - time.time()), 'players': len(board), 'top': top, 'me': me, 'tiers': SEASON_TIERS,
            'upcoming': upcoming[0] if upcoming else None}


class SeasonPayload(BaseModel):
    name: str
    theme: str = ''
    start: float
    end: float
    prize: str = ''
    multiplier: float = 1.0
    accent: str = '#f5c542'


@app.post('/api/reputation/admin/seasons')
async def admin_season_upsert(request: Request, p: SeasonPayload):
    admin = _require_admin(request)
    if p.end <= p.start or p.end - p.start > 120 * 86400 or not _re.match(r'^#[0-9a-fA-F]{6}$', p.accent) or not (0.5 <= p.multiplier <= 5):
        raise HTTPException(400, 'Invalid season (end after start, ≤120 days, #hex accent, multiplier 0.5–5).')
    d = _seasons()
    if any(not (p.end <= s['start'] or p.start >= s['end']) for s in d['seasons']):
        raise HTTPException(409, 'Seasons cannot overlap.')
    sid = f"s{len(d['seasons']) + 1}"
    d['seasons'].append({'id': sid, 'name': p.name[:40], 'theme': p.theme[:160], 'start': p.start, 'end': p.end, 'prize': p.prize[:160],
                         'multiplier': p.multiplier, 'accent': p.accent, 'createdBy': admin})
    _json_save(SEASONS_PATH, d)
    return {'ok': True, 'id': sid}


@app.get('/api/reputation/admin/seasons')
async def admin_seasons(request: Request):
    _require_admin(request)
    d = _seasons()
    return {'seasons': d['seasons'], 'players': {k: len(v) for k, v in d['scores'].items()}}


# ================================================================================================
# COMMAND CENTER ROLES + IDEAS
# ================================================================================================
ROLES_PATH = DATA_DIR / 'roles.json'
ROLE_NAMES = ('admin', 'moderator', 'marketing')


def _owner_wallets():
    env = [a.strip() for a in os.environ.get('FEELESS_ADMIN_WALLETS', '').split(',') if a.strip()]
    return env or [FEE_CREATOR_WALLET]


def _granted():
    return _json_load(ROLES_PATH, {'grants': {}})['grants']


class RolePayload(BaseModel):
    address: str
    role: str


@app.get('/api/reputation/admin/roles')
async def admin_roles(request: Request):
    me = _require_admin(request)
    return {'owners': _owner_wallets(), 'grants': _granted(), 'youAreOwner': me in _owner_wallets(), 'roles': ROLE_NAMES}


@app.post('/api/reputation/admin/roles')
async def admin_role_grant(request: Request, p: RolePayload):
    me = _require_admin(request)
    if me not in _owner_wallets():
        raise HTTPException(403, 'Only the FEELESS owner wallet can grant command center access.')
    if p.role not in ROLE_NAMES or not (_re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.address) or _re.match(r'^0x[0-9a-fA-F]{40}$', p.address)):
        raise HTTPException(400, 'Valid wallet + role (admin, moderator, marketing) required.')
    d = _json_load(ROLES_PATH, {'grants': {}})
    d['grants'][p.address] = {'role': p.role, 'by': me, 'at': time.time()}
    _json_save(ROLES_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'role-grant', f'{p.address[:6]}… → {p.role}'); _admin_save(ad)
    return {'ok': True}


@app.delete('/api/reputation/admin/roles/{address}')
async def admin_role_revoke(request: Request, address: str):
    me = _require_admin(request)
    if me not in _owner_wallets():
        raise HTTPException(403, 'Only the owner wallet can revoke access.')
    d = _json_load(ROLES_PATH, {'grants': {}}); d['grants'].pop(address, None); _json_save(ROLES_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'role-revoke', address[:10]); _admin_save(ad)
    return {'ok': True}


IDEAS_PATH = DATA_DIR / 'ideas.json'
_IDEA_SEED = [{'id': 'passkeys', 'title': 'Passkey wallets + sponsored gas', 'status': 'saved', 'at': 0,
               'body': 'Onboard with Face ID / passkeys (no seed phrase) via smart accounts, and sponsor gas for first trades. Pairs with Get Gas: "trade anything from any chain, never think about gas." Needs a smart-wallet provider (e.g. Privy/Turnkey/Coinbase Smart Wallet) + a paymaster budget.'}]


@app.get('/api/reputation/admin/ideas')
async def admin_ideas(request: Request):
    _require_admin(request)
    return {'ideas': _json_load(IDEAS_PATH, {'ideas': _IDEA_SEED})['ideas']}


class IdeaPayload(BaseModel):
    title: str
    body: str = ''
    status: str = 'saved'


@app.post('/api/reputation/admin/ideas')
async def admin_idea_add(request: Request, p: IdeaPayload):
    me = _require_admin(request)
    d = _json_load(IDEAS_PATH, {'ideas': list(_IDEA_SEED)})
    d['ideas'].insert(0, {'id': uuid.uuid4().hex[:8], 'title': p.title[:80], 'body': p.body[:1000], 'status': p.status[:20], 'by': me, 'at': time.time()})
    _json_save(IDEAS_PATH, d)
    return {'ok': True}


# ---- Wallet swaps (profile activity + copy trading) ---------------------------------------------
_wtrades_cache = {}
_wtrades_all = {}


async def wallet_trades(address: str, limit: int = 40):
    hit = _wtrades_cache.get(address)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    async with httpx.AsyncClient(timeout=12) as http:
        rows = [] if address.startswith('0x') else [{**r, 'chain': 'solana'} for r in await _maker_swaps(http, address)]
        rows.sort(key=lambda x: -x['ts'])
        _wtrades_all[address] = (time.time(), list(rows))   # full window, used for positions
        rows = rows[:limit]
        meta = {}
        toks = list({r['token'] for r in rows})
        for i in range(0, len(toks), 30):
            try:
                pairs = (await http.get(f"https://api.dexscreener.com/latest/dex/tokens/{','.join(toks[i:i + 30])}")).json().get('pairs') or []
                for p in sorted(pairs, key=lambda p: -((p.get('liquidity') or {}).get('usd') or 0)):
                    a = (p.get('baseToken') or {}).get('address')
                    if a and a not in meta:
                        meta[a] = {'symbol': p['baseToken'].get('symbol'), 'pair': p.get('pairAddress'), 'chain': p.get('chainId'), 'imageUrl': (p.get('info') or {}).get('imageUrl')}
            except Exception:
                pass
    for r in rows:
        r.update(meta.get(r['token'], {'symbol': r['token'][:4] + '…', 'pair': None}))
    _wtrades_cache[address] = (time.time(), rows)
    return rows


@app.get('/api/reputation/wallet-trades/{address}')
async def wallet_trades_ep(address: str):
    if not (_re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) or _re.match(r'^0x[0-9a-fA-F]{40}$', address)):
        raise HTTPException(400, 'Bad address.')
    return {'address': address, 'trades': await wallet_trades(address), 'source': 'Helius'}


@app.get('/api/reputation/copy/check/{address}')
async def copy_check(address: str):
    """Is this wallet safe to mirror? Trust, sniper record, funder links and KOL dump pattern — any
    red flag pauses copying automatically."""
    a = primary_of(address)
    t = await trust_score(a)
    bl = _block_load()['wallets'].get(a)
    fd = _funders_load(); frec = fd['funders'].get(a)
    kol = _kol_cache.get(a, (0, None))[1]
    reasons = []
    if bl and _is_blocked(bl): reasons.append('blocklisted for sniping/bundling')
    elif bl: reasons.append('caught sniping/bundling')
    if frec and _is_flagged_funder(frec): reasons.append('bankrolls sniper wallets')
    if kol and kol.get('danger'): reasons.append('call-and-dump pattern')
    if (t.get('score') or 0) < 45: reasons.append(f"low trust ({t.get('score')})")
    return {'address': a, 'trust': t.get('score'), 'safe': not reasons, 'reasons': reasons}


# ---- Season drops: weekly badges + a lifelong vault --------------------------------------------
WEEK_THEMES = [
    ('spark', 'Genesis Spark', '✦', 'Showed up in the first week of the season.'),
    ('hunter', 'Rug Hunter', '🎯', 'Earned during the week FEELESS hunted snipers and bundlers.'),
    ('diamond', 'Diamond Hands', '💎', 'Earned during the week of holding through the chop.'),
    ('caller', 'Sharp Caller', '📣', 'Earned during the week of calls that actually hit.'),
    ('legend', 'Legend Week', '👑', 'Earned in the final push of the season.'),
]
RARITIES = [('legendary', 'Top 3 of the week'), ('epic', 'Top 10% of the week'), ('rare', '300+ points that week'), ('common', '50+ points that week')]
COLLECTION_PATH = DATA_DIR / 'collections.json'


def _season_weeks(s):
    weeks, t, i = [], s['start'], 0
    while t < s['end']:
        th = WEEK_THEMES[min(i, len(WEEK_THEMES) - 1)] if i < len(WEEK_THEMES) - 1 or t + 7 * 86400 >= s['end'] else WEEK_THEMES[i % (len(WEEK_THEMES) - 1)]
        ov = (s.get('weeks') or {}).get(str(i + 1)) or {}
        weeks.append({'week': i + 1, 'start': t, 'end': min(t + 7 * 86400, s['end']), 'theme': th[0], 'name': ov.get('name') or th[1], 'glyph': ov.get('glyph') or th[2],
                      'story': ov.get('story') or th[3], 'imageUrl': ov.get('imageUrl') or None})
        t += 7 * 86400; i += 1
    return weeks


def _week_of(s, ts):
    return next((w for w in _season_weeks(s) if w['start'] <= ts < w['end']), None)


_orig_season_award = season_award


def season_award(address: str, points: float, reason: str):  # noqa: F811 — extends the base award with weekly scoring
    _orig_season_award(address, points, reason)
    d = _seasons(); s = _current_season(d)
    if not s or points <= 0 or _is_blocked(_block_load()['wallets'].get(address)):
        return
    w = _week_of(s, time.time())
    if w:
        wk = d['scores'].setdefault(f"{s['id']}:w{w['week']}", {})
        rec = wk.setdefault(address, {'score': 0}); rec['score'] = round(rec['score'] + points * float(s.get('multiplier') or 1), 1)
        _json_save(SEASONS_PATH, d)


def _grant(col, address, item):
    items = col.setdefault(address, [])
    if not any(x['id'] == item['id'] for x in items):
        items.append(item)


def _distribute_drops():
    d = _seasons(); col = _json_load(COLLECTION_PATH, {}); done = set(d.setdefault('distributed', []))
    now = time.time(); changed = False
    for s in d['seasons']:
        for w in _season_weeks(s):
            key = f"{s['id']}:w{w['week']}"
            if w['end'] > now or key in done:
                continue
            board = sorted((d['scores'].get(key) or {}).items(), key=lambda kv: -kv[1]['score'])
            n = len(board)
            for i, (a, r) in enumerate(board):
                rarity = 'legendary' if i < 3 else 'epic' if i < max(1, round(n * 0.1)) else 'rare' if r['score'] >= 300 else 'common' if r['score'] >= 50 else None
                if rarity:
                    _grant(col, a, {'id': f"{key}:{w['theme']}", 'kind': 'weekly', 'season': s['id'], 'seasonName': s['name'], 'week': w['week'], 'name': w['name'], 'glyph': w['glyph'], 'imageUrl': w.get('imageUrl'),
                                    'story': w['story'], 'rarity': rarity, 'how': dict(RARITIES)[rarity], 'rank': i + 1, 'score': r['score'], 'accent': s['accent'], 'at': now})
            done.add(key); changed = True
        if s['end'] <= now and s['id'] not in done:
            for a, r in (d['scores'].get(s['id']) or {}).items():
                t = _tier(r['score'])['tier']
                _grant(col, a, {'id': f"{s['id']}:season", 'kind': 'season', 'season': s['id'], 'seasonName': s['name'], 'name': f"Season {s['id'][1:]} · {s['name']}", 'glyph': '🏅', 'imageUrl': s.get('badgeUrl'),
                                'story': s.get('theme', ''), 'rarity': {'Legend': 'legendary', 'Diamond': 'epic', 'Gold': 'rare'}.get(t, 'common'), 'how': f'Finished the season at {t} tier',
                                'tier': t, 'score': r['score'], 'accent': s['accent'], 'at': now})
            done.add(s['id']); changed = True
    if changed:
        d['distributed'] = sorted(done); _json_save(SEASONS_PATH, d); _json_save(COLLECTION_PATH, col)


async def _drops_loop():
    while True:
        try:
            _distribute_drops()
        except Exception as exc:
            print('drops error', exc)
        await asyncio.sleep(1800)


@app.on_event('startup')
async def _start_drops():
    asyncio.create_task(_drops_loop())


@app.get('/api/reputation/season/drops')
async def season_drops():
    d = _seasons(); s = _current_season(d)
    if not s:
        return {'weeks': []}
    now = time.time(); col = _json_load(COLLECTION_PATH, {})
    holders = {}
    for items in col.values():
        for it in items:
            holders[it['id'].rsplit(':', 1)[0]] = holders.get(it['id'].rsplit(':', 1)[0], 0) + 1
    return {'season': s['id'], 'accent': s['accent'], 'rarities': RARITIES,
            'weeks': [{**w, 'status': 'distributed' if w['end'] <= now else 'live' if w['start'] <= now else 'upcoming',
                       'players': len(d['scores'].get(f"{s['id']}:w{w['week']}") or {}), 'holders': holders.get(f"{s['id']}:w{w['week']}", 0)} for w in _season_weeks(s)]}


@app.get('/api/reputation/collection/{address}')
async def collection(address: str):
    items = _json_load(COLLECTION_PATH, {}).get(primary_of(address), [])
    return {'address': primary_of(address), 'items': sorted(items, key=lambda x: -x['at'])}



class SeasonEdit(BaseModel):
    name: Optional[str] = None
    theme: Optional[str] = None
    prize: Optional[str] = None
    start: Optional[float] = None
    end: Optional[float] = None
    multiplier: Optional[float] = None
    accent: Optional[str] = None
    bannerUrl: Optional[str] = None
    badgeUrl: Optional[str] = None
    bgFx: Optional[str] = None     # money | snow | leaves | fire | stars | none
    accent2: Optional[str] = None
    weeks: Optional[dict] = None   # {"1": {"name","glyph","story","imageUrl"}, ...}


def _is_upload_url(u):
    # Only FEELESS-hosted uploads (validated real images) — no arbitrary links.
    return u in (None, '') or bool(_re.match(r'^/api/reputation/uploads/[0-9a-f]{32}\.(png|jpg|webp|gif)$', u))


@app.put('/api/reputation/admin/seasons/{sid}')
async def admin_season_edit(request: Request, sid: str, p: SeasonEdit):
    admin = _require_admin(request)
    d = _seasons(); s = next((x for x in d['seasons'] if x['id'] == sid), None)
    if not s:
        raise HTTPException(404, 'Season not found.')
    new = {**s, **{k: v for k, v in p.dict().items() if v is not None and k != 'weeks'}}
    if new['end'] <= new['start'] or new['end'] - new['start'] > 120 * 86400 or not _re.match(r'^#[0-9a-fA-F]{6}$', new['accent']) or not (0.5 <= float(new['multiplier']) <= 5):
        raise HTTPException(400, 'Invalid season (end after start, ≤120 days, #hex accent, multiplier 0.5–5).')
    if any(x['id'] != sid and not (new['end'] <= x['start'] or new['start'] >= x['end']) for x in d['seasons']):
        raise HTTPException(409, 'Seasons cannot overlap.')
    if not all(_is_upload_url(new.get(k)) for k in ('bannerUrl', 'badgeUrl')):
        raise HTTPException(400, 'Upload images through FEELESS (png, jpg, webp or gif).')
    if new.get('bgFx') not in (None, 'money', 'snow', 'leaves', 'fire', 'stars', 'none'):
        raise HTTPException(400, 'Unknown background effect.')
    if new.get('accent2') and not _re.match(r'^#[0-9a-fA-F]{6}$', new['accent2']):
        raise HTTPException(400, 'Second color must be #hex.')
    if p.weeks is not None:
        clean = {}
        for wk, ov in list(p.weeks.items())[:20]:
            if not str(wk).isdigit() or not isinstance(ov, dict) or not _is_upload_url(ov.get('imageUrl')):
                raise HTTPException(400, f'Bad week {wk} override.')
            clean[str(int(wk))] = {k: str(ov[k])[:200] for k in ('name', 'glyph', 'story', 'imageUrl') if ov.get(k)}
        new['weeks'] = clean
    new['name'] = new['name'][:40]; new['theme'] = new.get('theme', '')[:160]; new['prize'] = new.get('prize', '')[:160]
    d['seasons'] = [new if x['id'] == sid else x for x in d['seasons']]
    _json_save(SEASONS_PATH, d)
    ad = _admin_load(); _audit(ad, admin, 'season-edit', sid); _admin_save(ad)
    return {'ok': True, 'season': new}


@app.delete('/api/reputation/admin/seasons/{sid}')
async def admin_season_delete(request: Request, sid: str):
    admin = _require_admin(request)
    d = _seasons(); s = next((x for x in d['seasons'] if x['id'] == sid), None)
    if not s:
        raise HTTPException(404, 'Season not found.')
    if s['start'] <= time.time() and d['scores'].get(sid):
        raise HTTPException(409, 'This season already has players — end it early by editing its end date instead.')
    d['seasons'] = [x for x in d['seasons'] if x['id'] != sid]
    _json_save(SEASONS_PATH, d)
    ad = _admin_load(); _audit(ad, admin, 'season-delete', sid); _admin_save(ad)
    return {'ok': True}


# ---- Token search for the swap box: every Solana token Jupiter knows ----------------------------
_tok_search_cache = {}


@app.get('/api/reputation/tokens/search')
async def token_search(q: str = Query(..., min_length=1, max_length=64)):
    q = q.strip()
    hit = _tok_search_cache.get(q.lower())
    if hit and time.time() - hit[0] < 30:
        return hit[1]
    rows = []
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.get('https://api.jup.ag/tokens/v2/search', params={'query': q}, headers={'x-api-key': os.environ.get('JUPITER_API_KEY', '')})
        for t in (r.json() if r.status_code == 200 else [])[:20]:
            rows.append({'mint': t.get('id'), 'symbol': t.get('symbol'), 'name': t.get('name'), 'icon': t.get('icon'), 'decimals': t.get('decimals'),
                         'price': t.get('usdPrice'), 'mcap': t.get('mcap'), 'liquidity': t.get('liquidity'), 'verified': bool(t.get('isVerified')),
                         'blocked': _is_blocked(_block_load()['wallets'].get(t.get('dev') or ''))})
    except Exception:
        pass
    rows.sort(key=lambda x: (not x['verified'], -(x['liquidity'] or 0)))
    data = {'q': q, 'tokens': rows}
    _tok_search_cache[q.lower()] = (time.time(), data)
    if len(_tok_search_cache) > 2000:
        _tok_search_cache.clear()
    return data


@app.get('/api/reputation/admin/is-admin/{address}')
async def is_admin(address: str):
    """Public yes/no so the UI can show admin controls. Every admin action still needs a signed session."""
    return {'admin': address in _admin_wallets(), 'owner': address in _owner_wallets()}



@app.get('/api/reputation/position/{address}/{token}')
async def position(address: str, token: str):
    """A wallet's position in one coin from its real swaps: average entry, size, live-ready.
    The chart turns this into the 'Your avg entry' line and a live P&L badge."""
    if not (_re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) or _re.match(r'^0x[0-9a-fA-F]{40}$', address)) or len(token) > 64:
        raise HTTPException(400, 'Bad address.')
    await wallet_trades(address)
    rows = [r for r in (_wtrades_all.get(address) or (0, []))[1] if r['token'].lower() == token.lower() and r['price'] > 0]
    buy_usd = sum(r['usd'] for r in rows if r['side'] == 'buy'); buy_tok = sum(r['usd'] / r['price'] for r in rows if r['side'] == 'buy')
    sell_usd = sum(r['usd'] for r in rows if r['side'] == 'sell'); sell_tok = sum(r['usd'] / r['price'] for r in rows if r['side'] == 'sell')
    if not buy_tok:
        return {'address': address, 'token': token, 'position': None}
    avg = buy_usd / buy_tok; held = max(0.0, buy_tok - sell_tok)
    return {'address': address, 'token': token, 'position': {'avgEntry': avg, 'tokensHeld': held, 'costUsd': round(avg * held, 2), 'realizedUsd': round(sell_usd - sell_tok * avg, 2),
                                                             'buys': sum(1 for r in rows if r['side'] == 'buy'), 'sells': sum(1 for r in rows if r['side'] == 'sell'), 'lastTradeAt': max(r['ts'] for r in rows)}}


# ---- Setup checklist for the command center: which keys/URLs are configured (never the values) ----
SETUP_KEYS = [
    ('SOLANA_RPC_URL', 'Solana RPC (Helius)', 'Chain reads, forensics, trades feed', True),
    ('ALCHEMY_API_KEY', 'Alchemy', 'EVM + Solana RPC, price history, gas checks', True),
    ('JUPITER_API_KEY', 'Jupiter', 'Solana swaps, token search, $FEE pricing', True),
    ('FEELESS_ADMIN_WALLETS', 'Owner wallets', 'Who can open the command center (defaults to creator wallet)', False),
    ('ALLOWED_ORIGINS', 'Site domain', 'Lock APIs to your domain before launch', False),
    ('HELIUS_WEBHOOK_SECRET', 'Helius webhook secret', 'Instant whale / dev-sell events', False),
    ('BASE_RPC_URL', 'Base RPC', 'Dedicated Base endpoint for pool reads', False),
    ('PUBLIC_SITE_URL', 'Public site URL', 'Hosts new coins\' metadata so wallets/explorers show name + image (required to launch)', True),
]


@app.get('/api/reputation/admin/setup')
async def admin_setup(request: Request):
    _require_admin(request)
    return {'keys': [{'key': k, 'name': n, 'why': w, 'required': req, 'set': bool(os.environ.get(k, '').strip())} for k, n, w, req in SETUP_KEYS],
            'launchRail': bool(_json_load(LAUNCH_RAIL_PATH, {}).get('config')), 'owners': _owner_wallets()}



# ---- Treasury routing: where FEELESS fee earnings go (addresses you control — never keys) --------
ROUTES_PATH = DATA_DIR / 'treasury_routes.json'


class RoutesPayload(BaseModel):
    routes: list


@app.get('/api/reputation/admin/treasury/routes')
async def routes_get(request: Request):
    _require_admin(request)
    return _json_load(ROUTES_PATH, {'routes': []})


@app.put('/api/reputation/admin/treasury/routes')
async def routes_set(request: Request, p: RoutesPayload):
    me = _require_admin(request)
    if me not in _owner_wallets():
        raise HTTPException(403, 'Only the FEELESS owner wallet can change treasury routing.')
    clean = []
    for r in p.routes[:10]:
        addr = str(r.get('address', '')).strip(); pct = float(r.get('pct') or 0)
        if not (_re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', addr) or _re.match(r'^0x[0-9a-fA-F]{40}$', addr)) or not (0 < pct <= 100):
            raise HTTPException(400, 'Each route needs a valid wallet address and a % between 0 and 100.')
        clean.append({'label': str(r.get('label', ''))[:40], 'address': addr, 'pct': round(pct, 2)})
    if clean and abs(sum(r['pct'] for r in clean) - 100) > 0.01:
        raise HTTPException(400, 'Route percentages must add up to 100%.')
    _json_save(ROUTES_PATH, {'routes': clean, 'updatedBy': me, 'at': time.time()})
    ad = _admin_load(); _audit(ad, me, 'treasury-routes', f"{len(clean)} routes"); _admin_save(ad)
    return {'ok': True, 'routes': clean}


# ---- Shield leaderboard + weekly Rug Report ----------------------------------------------------
@app.get('/api/reputation/shields/leaderboard')
async def shield_leaderboard():
    now = time.time(); by = {}
    for mint, s in _json_load(SHIELD_PATH, {}).items():
        r = by.setdefault(s['creator'], {'creator': s['creator'], 'kept': 0, 'broken': 0, 'active': 0, 'coins': []})
        st = 'broken' if s['breaches'] else ('active' if now - s['at'] < s['lockDays'] * 86400 else 'kept')
        r[st] += 1; r['coins'].append({'mint': mint, 'status': st})
    rows = sorted(by.values(), key=lambda r: (-(r['kept'] * 3 + r['active'] - r['broken'] * 10), -r['kept']))
    for r in rows:
        r['handle'] = handle_of(r['creator']); r['score'] = r['kept'] * 3 + r['active'] - r['broken'] * 10
    return {'rows': rows[:50]}


@app.get('/api/reputation/rug-report')
async def rug_report(days: int = Query(7, ge=1, le=30)):
    """The week's receipts: who got caught, who funded them, which promises broke."""
    since = time.time() - days * 86400
    bl = _block_load()['wallets']
    caught = [{'wallet': w, 'roles': sorted(set((r.get('mints') or {}).values())), 'launches': len(r.get('mints') or {}), 'blocked': _is_blocked(r)}
              for w, r in bl.items() if (r.get('firstSeen') or 0) >= since]
    fd = _funders_load()
    funders = [{'wallet': w, 'walletsFunded': len(r.get('funded') or []), 'launches': len(r.get('mints') or {})}
               for w, r in fd['funders'].items() if _is_flagged_funder(r) and (r.get('lastSeen') or 0) >= since]
    broken = [{'mint': m, 'creator': s['creator'], 'rules': [b['rule'] for b in s['breaches']]}
              for m, s in _json_load(SHIELD_PATH, {}).items() if any(b['at'] >= since for b in s['breaches'])]
    rugs = [e for e in _radar['events'] if e['kind'] in ('rug', 'dump') and e['at'] >= since]
    return {'days': days, 'from': since, 'to': time.time(),
            'totals': {'caught': len(caught), 'blocklisted': sum(1 for c in caught if c['blocked']), 'funders': len(funders), 'brokenShields': len(broken), 'rugs': len(rugs)},
            'caught': sorted(caught, key=lambda c: -c['launches'])[:10], 'funders': sorted(funders, key=lambda f: -f['walletsFunded'])[:5],
            'brokenShields': broken[:5], 'rugs': rugs[:8]}


# ---- FEELESS launch rail (Meteora Dynamic Bonding Curve) -------------------------------------
# The owner creates ONE on-chain DBC config (curve, fees, fee claimer, graduation) from their own
# wallet in the command center. Every FEELESS launch then creates its pool on that config, signed by
# the creator's wallet. The server stores only public addresses and never signs anything.
LAUNCH_RAIL_PATH = DATA_DIR / 'launch_rail.json'
TOKEN_META_DIR = DATA_DIR / 'token_meta'
DBC_PROGRAM = 'dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN'
_B58 = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'


class LaunchRailIn(BaseModel):
    config: str
    feeClaimer: str
    params: dict = {}


@app.get('/api/reputation/launch-rail')
async def launch_rail():
    r = _json_load(LAUNCH_RAIL_PATH, {})
    return {'ready': bool(r.get('config')), **r, 'siteUrl': os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/')}


@app.put('/api/reputation/admin/launch-rail')
async def launch_rail_set(request: Request, p: LaunchRailIn):
    me = _require_admin(request)
    if me not in _owner_wallets():
        raise HTTPException(403, 'Only the FEELESS owner wallet can set the launch rail.')
    if not (_re.match(_B58, p.config) and _re.match(_B58, p.feeClaimer)):
        raise HTTPException(400, 'Config and fee claimer must be Solana addresses.')
    # Only accept a config that really exists on-chain and belongs to the DBC program.
    async with httpx.AsyncClient(timeout=10) as http:
        info = await _rpc(http, 'getAccountInfo', [p.config, {'encoding': 'base64'}])
    owner = ((info or {}).get('value') or {}).get('owner')
    if owner != DBC_PROGRAM:
        raise HTTPException(409, 'That config is not on-chain yet (or is not a Meteora DBC config). Wait for confirmation and retry.')
    keep = {k: p.params[k] for k in ('initialMarketCap', 'migrationMarketCap', 'startingFeeBps', 'endingFeeBps', 'feeDecayMin', 'creatorFeePct', 'lockedLpPct', 'supply') if k in p.params}
    rec = {'config': p.config, 'feeClaimer': p.feeClaimer, 'params': keep, 'setBy': me, 'at': time.time()}
    _json_save(LAUNCH_RAIL_PATH, rec)
    return rec


class TokenMetaIn(BaseModel):
    address: str
    session: str
    name: str
    symbol: str
    description: str = ''
    image: str = ''
    website: str = ''
    twitter: str = ''
    telegram: str = ''


@app.post('/api/reputation/token-meta')
async def token_meta_create(p: TokenMetaIn, request: Request):
    """Hosts the Metaplex metadata JSON a new coin's `uri` points to (name, image, links)."""
    _session_or_401(p.address, p.session)
    name, symbol = p.name.strip()[:32], p.symbol.strip().upper()[:10]
    if not name or not _re.match(r'^[A-Z0-9$]{1,10}$', symbol):
        raise HTTPException(400, 'Name and a 1–10 character ticker are required.')
    site = os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/') or (request.headers.get('origin') or '').rstrip('/')
    # FEELESS-rail coins are minted with IMMUTABLE metadata: a localhost/LAN uri would leave the coin
    # nameless and imageless forever, so refuse anything that isn't a public https address.
    host = _re.sub(r'^https?://', '', site).split('/')[0].split(':')[0]
    if not site.startswith('https://') or host in ('localhost', '127.0.0.1', '0.0.0.0') or host.endswith('.local') or _re.match(r'^(10|192\.168|172\.(1[6-9]|2\d|3[01]))\.', host):
        raise HTTPException(503, 'FEELESS launches need a public https domain (set PUBLIC_SITE_URL). Coin metadata is permanent, so a local address would break the coin forever. Pump.fun launches work now.')
    img = p.image.strip()
    if img.startswith('/api/reputation/uploads/'):
        img = site + img
    link = lambda v: v.strip()[:200] if v.strip().startswith('https://') else ''
    meta = {'name': name, 'symbol': symbol, 'description': p.description.strip()[:600], 'image': img[:300],
            'external_url': link(p.website), 'extensions': {'website': link(p.website), 'twitter': link(p.twitter), 'telegram': link(p.telegram)},
            'properties': {'files': [{'uri': img[:300], 'type': 'image/webp'}] if img else [], 'category': 'image'}}
    TOKEN_META_DIR.mkdir(parents=True, exist_ok=True)
    mid = uuid.uuid4().hex
    (TOKEN_META_DIR / f'{mid}.json').write_text(json.dumps(meta))
    return {'uri': f'{site}/api/reputation/token-meta/{mid}.json'}


@app.get('/api/reputation/token-meta/{name}')
async def token_meta_get(name: str):
    from fastapi.responses import FileResponse
    if not _re.match(r'^[a-f0-9]{32}\.json$', name) or not (TOKEN_META_DIR / name).exists():
        raise HTTPException(404, 'Not found')
    return FileResponse(TOKEN_META_DIR / name, media_type='application/json')


# Browser-side Solana RPC relay for wallet-signed launches: the Helius key stays on the server and
# only read/send methods pass. Nothing here can sign — the user's wallet signs in the browser.
RPC_ALLOW = {'getAccountInfo', 'getMultipleAccounts', 'getLatestBlockhash', 'getMinimumBalanceForRentExemption', 'sendTransaction',
             'getSignatureStatuses', 'simulateTransaction', 'getBalance', 'getTokenAccountBalance', 'getFeeForMessage', 'getSlot',
             'getBlockHeight', 'isBlockhashValid', 'getEpochInfo'}
_rpc_hits: dict = {}


@app.post('/api/reputation/rpc')
async def rpc_relay(request: Request):
    ip = request.client.host if request.client else '?'
    now = time.time(); hits = [t for t in _rpc_hits.get(ip, []) if now - t < 10]
    if len(hits) >= 60:
        raise HTTPException(429, 'Too many RPC calls.')
    _rpc_hits[ip] = hits + [now]
    body = await request.json()
    calls = body if isinstance(body, list) else [body]
    if len(calls) > 10 or any(not isinstance(c, dict) or c.get('method') not in RPC_ALLOW for c in calls):
        raise HTTPException(403, 'RPC method not allowed.')
    endpoint = _dedicated or _next_rpc_endpoint()
    async with httpx.AsyncClient(timeout=20) as http:
        r = await http.post(endpoint, json=body)
    from fastapi.responses import Response
    return Response(r.content, status_code=r.status_code, media_type='application/json')



# ---- Pump.fun launches (via PumpPortal's local-transaction API) --------------------------------
# PumpPortal only BUILDS the create transaction for the creator's public key; the browser adds the
# new mint's signature and the creator's wallet signs. No PumpPortal key, no custody.
class PumpCreateIn(BaseModel):
    address: str
    session: str
    mint: str
    name: str
    symbol: str
    description: str = ''
    image: str
    website: str = ''
    twitter: str = ''
    telegram: str = ''
    devBuySol: float = 0


@app.post('/api/reputation/pump/create-tx')
async def pump_create_tx(p: PumpCreateIn):
    me = _session_or_401(p.address, p.session)
    if not (_re.match(_B58, p.mint) and _re.match(_B58, p.address)):
        raise HTTPException(400, 'Bad address.')
    if not (0 <= p.devBuySol <= 50):
        raise HTTPException(400, 'Dev buy must be between 0 and 50 SOL.')
    m = _re.match(r'^/api/reputation/uploads/([a-f0-9]{32}\.(png|jpg|webp|gif))$', p.image.strip())
    if not m or not (UPLOAD_DIR / m.group(1)).exists():
        raise HTTPException(400, 'Upload the coin image first.')
    img = (UPLOAD_DIR / m.group(1)).read_bytes()
    mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'webp': 'image/webp', 'gif': 'image/gif'}[m.group(2)]
    form = {'name': p.name.strip()[:32], 'symbol': p.symbol.strip().upper()[:10], 'description': p.description.strip()[:600], 'showName': 'true'}
    for k in ('website', 'twitter', 'telegram'):
        v = getattr(p, k).strip()
        if v.startswith('https://'):
            form[k] = v[:200]
    async with httpx.AsyncClient(timeout=30, headers={'User-Agent': 'Mozilla/5.0'}) as http:
        r = await http.post('https://pump.fun/api/ipfs', data=form, files={'file': (m.group(1), img, mime)})
        if r.status_code != 200:
            raise HTTPException(502, 'Pump.fun metadata upload failed — try again.')
        uri = (r.json() or {}).get('metadataUri')
        t = await http.post('https://pumpportal.fun/api/trade-local', json={'publicKey': p.address, 'action': 'create', 'tokenMetadata': {'name': form['name'], 'symbol': form['symbol'], 'uri': uri},
                                                                           'mint': p.mint, 'denominatedInSol': 'true', 'amount': p.devBuySol, 'slippage': 10, 'priorityFee': 0.0005, 'pool': 'pump'})
    if t.status_code != 200:
        raise HTTPException(502, f'Pump.fun could not build the launch ({t.text[:120]}).')
    import base64 as _b64
    return {'tx': _b64.b64encode(t.content).decode(), 'uri': uri}



def _gold_creator(a):
    """Creator streak: 3+ launches, none dumped or rugged, scored Trusted. Earns the gold R."""
    entry = _load()['creators'].get(_creator_key('solana', a))
    if not entry:
        return False
    sc = score_creator(entry)
    return sc.get('badge') == 'trusted' and sc.get('tokenCount', 0) >= 3 and not (sc.get('dumpedCount', 0) + sc.get('ruggedCount', 0))


# ---- Launch radar: every coin launched through FEELESS, newest first, with its evidence ----------
@app.get('/api/reputation/launch-radar')
async def launch_radar(limit: int = Query(30, ge=1, le=100)):
    launches = sorted((_load().get('feelessLaunches') or {}).values(), key=lambda l: -(l.get('at') or 0))[:limit]
    shields = _json_load(SHIELD_PATH, {})
    rows, queued = [], 0
    for l in launches:
        hit = _intel_cache.get(l['mint'])
        intel = hit[1] if hit else None
        if not hit and queued < 3:
            queued += 1; asyncio.create_task(_quiet(token_intel('solana', l['mint'])))
        w = primary_of(l['wallet'])
        t = _trust_cache.get(w)
        if not t and w not in _trust_pending and len(_trust_pending) < 8:
            _trust_pending.add(w); asyncio.create_task(_trust_fill(w))
        sh = shields.get(l['mint'])
        rows.append({'mint': l['mint'], 'symbol': l.get('symbol'), 'creator': w, 'rail': l.get('rail') or 'feeless', 'config': l.get('config'), 'at': l.get('at'),
                     'snipers': None if not intel else len(intel.get('sniperWallets') or []) + len(intel.get('bundledWallets') or []),
                     'shield': None if not sh else ('broken' if sh.get('broken') else 'active'),
                     'rep': None if not t else {'score': t[1].get('score'), 'level': t[1].get('level')}, 'gold': _gold_creator(w)})
    return {'launches': rows}


async def _quiet(coro):
    try:
        await coro
    except Exception:
        pass


# ---- Rug-proof check: mint can't inflate, can't freeze, liquidity can't be pulled -------------------
POOLS_REG_PATH = DATA_DIR / 'pools_registry.json'
_rugproof_cache: dict = {}


@app.get('/api/reputation/rugproof/{mint}')
async def rugproof(mint: str):
    if not _re.match(_B58, mint):
        raise HTTPException(400, 'Solana mint required.')
    hit = _rugproof_cache.get(mint)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    async with httpx.AsyncClient(timeout=10) as http:
        info = await _rpc(http, 'getAccountInfo', [mint, {'encoding': 'jsonParsed'}])
    parsed = ((((info or {}).get('value') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
    if not parsed:
        raise HTTPException(404, 'Not a token mint.')
    launch = (_load().get('feelessLaunches') or {}).get(mint) or {}
    rail = _json_load(LAUNCH_RAIL_PATH, {})
    reg = [p for p in _json_load(POOLS_REG_PATH, {'pools': []})['pools'] if p['mint'] == mint]
    if any(p.get('locked') for p in reg):
        lp = {'ok': True, 'how': 'FEELESS pool with liquidity permanently locked'}
    elif launch.get('rail') == 'feeless' and launch.get('config') == rail.get('config') and float((rail.get('params') or {}).get('lockedLpPct', 100)) >= 100:
        lp = {'ok': True, 'how': 'FEELESS rail locks 100% of graduated liquidity forever'}
    else:
        lp = {'ok': False, 'how': 'No verified permanent liquidity lock known to FEELESS'}
    out = {'mint': mint, 'mintRevoked': not parsed.get('mintAuthority'), 'freezeRevoked': not parsed.get('freezeAuthority'), 'lpLocked': lp}
    out['rugProof'] = out['mintRevoked'] and out['freezeRevoked'] and lp['ok']
    _rugproof_cache[mint] = (time.time(), out)
    return out


class PoolRegIn(BaseModel):
    pool: str
    mint: str
    signature: str
    locked: bool = True


@app.post('/api/reputation/admin/pools/register')
async def pools_register(request: Request, p: PoolRegIn):
    """Record a pool created from the command center. Verified on-chain: succeeded, signed by this admin."""
    admin = _require_admin(request)
    async with httpx.AsyncClient(timeout=20) as http:
        tx = await _rpc(http, 'getTransaction', [p.signature, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}])
    if not tx or (tx.get('meta') or {}).get('err'):
        raise HTTPException(409, 'Transaction not confirmed yet.')
    keys = tx['transaction']['message']['accountKeys']
    if admin not in [k['pubkey'] for k in keys if k.get('signer')] or p.pool not in [k['pubkey'] for k in keys]:
        raise HTTPException(400, 'That transaction did not create this pool from your wallet.')
    d = _json_load(POOLS_REG_PATH, {'pools': []})
    d['pools'] = [x for x in d['pools'] if x['pool'] != p.pool] + [{'pool': p.pool, 'mint': p.mint, 'locked': p.locked, 'signature': p.signature, 'by': admin, 'at': time.time()}]
    _json_save(POOLS_REG_PATH, d); _rugproof_cache.pop(p.mint, None)
    return {'ok': True}


# ---- Coin logos: find once, cache on disk, serve fast -----------------------------------------------
# Public IPFS gateways rate-limit (ipfs.io returns 429), and some coins only carry their image inside
# on-chain metadata. This resolves a mint's logo from DexScreener / Jupiter / on-chain metadata, tries
# several IPFS gateways, stores the bytes, and serves them with a long cache.
LOGO_DIR = DATA_DIR / 'logos'
IPFS_GATEWAYS = ['https://cloudflare-ipfs.com/ipfs/', 'https://gateway.pinata.cloud/ipfs/', 'https://nftstorage.link/ipfs/', 'https://dweb.link/ipfs/', 'https://ipfs.io/ipfs/']
_logo_miss: dict = {}
_logo_locks: dict = {}


def _ipfs_variants(u):
    m = _re.search(r'/ipfs/([^?#]+)', u or '') or _re.match(r'^ipfs://(.+)$', u or '')
    return [g + m.group(1) for g in IPFS_GATEWAYS] if m else [u]


async def _fetch_first(http, urls, want_json=False):
    for u in urls:
        try:
            r = await http.get(u, timeout=8, follow_redirects=True)
            if r.status_code != 200:
                continue
            if want_json:
                return r.json()
            ct = r.headers.get('content-type', '').split(';')[0]
            if ct.startswith('image/') and 0 < len(r.content) <= 2_500_000:
                return ct, r.content
        except Exception:
            continue
    return None


@app.get('/api/reputation/token-logo/{mint}')
async def token_logo(mint: str):
    from fastapi.responses import FileResponse, Response
    if not _re.match(_B58, mint):
        raise HTTPException(400, 'Solana mint required.')
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    hit = next(LOGO_DIR.glob(f'{mint}.*'), None)
    headers = {'Cache-Control': 'public, max-age=604800, immutable'}
    if hit:
        return FileResponse(hit, headers=headers)
    if time.time() - _logo_miss.get(mint, 0) < 3600:
        raise HTTPException(404, 'No logo found.')
    lock = _logo_locks.setdefault(mint, asyncio.Lock())
    async with lock:
        hit = next(LOGO_DIR.glob(f'{mint}.*'), None)
        if hit:
            return FileResponse(hit, headers=headers)
        cands = []
        async with httpx.AsyncClient(headers={'User-Agent': 'Mozilla/5.0'}) as http:
            try:
                d = (await http.get(f'https://api.dexscreener.com/tokens/v1/solana/{mint}', timeout=8)).json()
                cands += [(p.get('info') or {}).get('imageUrl') for p in (d or [])[:3]]
            except Exception:
                pass
            try:
                d = (await http.get(f'https://lite-api.jup.ag/tokens/v2/search?query={mint}', timeout=8)).json()
                cands += [x.get('icon') for x in d if x.get('id') == mint]
            except Exception:
                pass
            try:
                a = await _rpc(http, 'getAsset', {'id': mint})
                c = (a or {}).get('content') or {}
                cands += [f.get('cdn_uri') for f in c.get('files') or []] + [(c.get('links') or {}).get('image')]
                if c.get('json_uri'):
                    meta = await _fetch_first(http, _ipfs_variants(c['json_uri']), want_json=True)
                    cands.append((meta or {}).get('image'))
            except Exception:
                pass
            got = None
            for u in [x for x in cands if x]:
                got = await _fetch_first(http, _ipfs_variants(u))
                if got:
                    break
        if not got:
            _logo_miss[mint] = time.time()
            raise HTTPException(404, 'No logo found.')
        ct, body = got
        ext = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif', 'image/svg+xml': 'svg'}.get(ct, 'img')
        (LOGO_DIR / f'{mint}.{ext}').write_bytes(body)
        return Response(body, media_type=ct, headers=headers)


# ---- Command center: chart & data-provider latency --------------------------------------------------
LATENCY_PROBES = [
    # (name, role in the chart pipeline, env var that controls/replaces it, url builder)
    ('Jupiter chart data', 'Chart history #1 (Solana)', '—', lambda: f"https://datapi.jup.ag/v2/charts/So11111111111111111111111111111111111111112?interval=1_MINUTE&to={int(time.time()*1000)}&candles=2&type=price&quote=usd"),
    ('Jupiter price', 'Live price + chart anchor', 'JUPITER_API_KEY', lambda: 'https://lite-api.jup.ag/price/v3?ids=So11111111111111111111111111111111111111112'),
    ('DexScreener', 'Pair discovery, search, fallback price', '—', lambda: 'https://api.dexscreener.com/latest/dex/search?q=SOL'),
    ('Helius RPC', 'On-chain reads, swap history, live stream trigger', 'SOLANA_RPC_URL', None),
    ('FEELESS candles', 'Serves every chart (cache + fallbacks)', '—', lambda: 'http://127.0.0.1:5099/api/candles/stream-stats'),
]


@app.get('/api/reputation/admin/latency')
async def admin_latency(request: Request):
    _require_admin(request)
    return {**await _probe_latency(), 'alarms': [{'name': k, 'since': v['since'], 'posted': bool(v.get('posted'))} for k, v in _latency_bad.items()]}


async def _probe_latency():
    out = []
    async with httpx.AsyncClient(timeout=8) as http:
        for name, role, env, url in LATENCY_PROBES:
            t0 = time.time(); ok, note = False, ''
            try:
                if name == 'Helius RPC':
                    rpc = os.environ.get('SOLANA_RPC_URL', '').strip()
                    r = await http.post(rpc, json={'jsonrpc': '2.0', 'id': 1, 'method': 'getSlot'}) if rpc else None
                    ok = bool(r and r.status_code == 200 and 'result' in r.json()); note = '' if rpc else 'not configured'
                else:
                    r = await http.get(url()); ok = r.status_code == 200; note = '' if ok else f'HTTP {r.status_code}'
            except Exception as exc:
                note = type(exc).__name__
            out.append({'name': name, 'role': role, 'env': env, 'ok': ok, 'ms': round((time.time() - t0) * 1000), 'note': note})
    return {'providers': out, 'chartOrder': ['Jupiter chart data', 'Alchemy', 'Helius swaps', 'FEELESS-recorded ticks'],
            'checkedAt': time.time()}


_latency_bad = {}


async def _latency_alarm():
    # Any provider down or >1.5s for 5 straight minutes gets posted to the admin Updates room, once per outage.
    while True:
        await asyncio.sleep(60)
        try:
            rows = (await _probe_latency())['providers']
            for r in rows:
                bad = r['note'] != 'not configured' and (not r['ok'] or r['ms'] > 1500)
                st = _latency_bad.get(r['name'])
                if not bad:
                    if st and st.get('posted'):
                        chat_system_post('feeless-updates', 'FEELESS status', 'system', f"✅ {r['name']} recovered ({r['ms']} ms).")
                    _latency_bad.pop(r['name'], None)
                    continue
                st = _latency_bad.setdefault(r['name'], {'since': time.time()})
                if not st.get('posted') and time.time() - st['since'] >= 300:
                    st['posted'] = True
                    why = r['note'] or 'down' if not r['ok'] else f"{r['ms']} ms"
                    chat_system_post('feeless-updates', 'FEELESS status', 'system', f"⚠️ {r['name']} ({r['role']}) degraded for 5+ min: {why}. Fallbacks are serving; we're on it.")
        except Exception as exc:
            print('latency alarm error', exc)


@app.on_event('startup')
async def _start_latency_alarm():
    asyncio.create_task(_latency_alarm())


# ---- Circle developer-controlled wallets (creator/owner only) -------------------------------------
# Proxies to the localhost Circle sidecar. Only owner wallets may list or create; keys never leave .env.
class CircleWalletIn(BaseModel):
    blockchain: str
    name: str = 'Creator wallet'


async def _circle(method, path, body=None):
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.request(method, f'http://127.0.0.1:5111{path}', json=body)
    except httpx.HTTPError:
        raise HTTPException(503, 'Circle wallet service is not running (node circle/server.mjs).')
    data = r.json() if r.content else {}
    if r.status_code >= 400:
        raise HTTPException(r.status_code, data.get('detail') or 'Circle request failed.')
    return data


def _require_owner(request: Request):
    me = _require_admin(request)
    if me not in _owner_wallets():
        raise HTTPException(403, 'Only the FEELESS creator wallet can manage Circle wallets.')
    return me


@app.get('/api/reputation/admin/circle/status')
async def circle_status(request: Request):
    _require_owner(request)
    return await _circle('GET', '/status')


@app.get('/api/reputation/admin/circle/wallets')
async def circle_wallets(request: Request):
    _require_owner(request)
    return await _circle('GET', '/wallets')


@app.post('/api/reputation/admin/circle/wallets')
async def circle_create_wallet(request: Request, p: CircleWalletIn):
    me = _require_owner(request)
    out = await _circle('POST', '/wallets', {'blockchain': p.blockchain, 'name': p.name[:40]})
    ad = _admin_load(); _audit(ad, me, 'circle-wallet', f"{p.blockchain} {(out.get('wallet') or {}).get('address', '')}"); _admin_save(ad)
    return out
