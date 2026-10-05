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
import investigate
import reserve_pool
import perf
import verify
import launch_meta
import fee_report
import money_pulse
import badge_cards
import intel_desk
import nft_studio
import coin_meta
from ecosystem import ecosystem_mints
import asyncio
import math
import contextvars
import trade_fills
import collections
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
from fastapi.responses import JSONResponse, Response
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
STORE_PATH = DATA_DIR / 'reputation.json'

# Solana RPC pool + retrying client live in chain_rpc.py (one module per job); imported here so every caller is unchanged.
import chain_rpc as _chain
from chain_rpc import quota_state as _rpc_quota_state, RPC_POOL, RPC_COOLDOWN_SECONDS, RPC_MAX_RETRIES, _alchemy, _dedicated, _rpc_cooldown_until, _next_rpc_endpoint, _rpc, broadcast as _rpc_broadcast, rpc_priority as _krpc  # noqa: F401

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


_upload_ip: dict = {}


@app.post('/api/reputation/uploads')
async def upload_image(payload: UploadPayload, request: Request):
    """Images for profiles, launches and seasons. Everyone: 2 MB (animated GIFs: 6 MB). A signed-in creator/admin
    (HQ session) may upload big GIFs/art up to 25 MB."""
    import base64
    import re
    m = re.match(r'^data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/=]+)$', payload.dataUrl or '')
    if not m:
        raise HTTPException(400, 'Only PNG, JPG, WEBP or GIF images are supported.')
    raw = base64.b64decode(m.group(2))
    try:
        _require_admin(request); cap = 25_000_000
    except HTTPException:
        cap = 6_000_000 if m.group(1) == 'image/gif' else 2_000_000   # animated profile covers / avatars
        # No sign-in needed to upload, so cap it: 20 images per hour per IP (stops anyone filling the disk).
        ip = request.headers.get('x-forwarded-for', request.client.host if request.client else '?').split(',')[0]
        hits = [x for x in _upload_ip.get(ip, []) if time.time() - x < 3600]
        if len(hits) >= 20:
            raise HTTPException(429, 'Upload limit reached — try again in an hour.')
        _upload_ip[ip] = hits + [time.time()]
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
    from fastapi.responses import JSONResponse, FileResponse
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


async def _coin_card(http, mint):
    """Deepest pool + symbol/name/market cap for alerts. DexScreener first, Jupiter when the coin isn't indexed yet."""
    card = {'pair': mint, 'symbol': None, 'name': None, 'mcap': None}
    try:
        pools = (await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{mint}')).json().get('pairs') or []
        if pools:
            top = max(pools, key=lambda p: (p.get('liquidity') or {}).get('usd') or 0)
            base = top.get('baseToken') or {}
            card.update(pair=top.get('pairAddress') or mint, symbol=base.get('symbol'), name=base.get('name'), mcap=top.get('marketCap') or top.get('fdv'))
    except Exception:
        pass
    if not card['symbol']:
        try:
            hit = next((t for t in (await http.get('https://lite-api.jup.ag/tokens/v2/search', params={'query': mint})).json() if t.get('id') == mint), None)
            if hit:
                card.update(symbol=hit.get('symbol'), name=hit.get('name'), mcap=card['mcap'] or hit.get('mcap'))
        except Exception:
            pass
    card['symbol'] = card['symbol'] or f'{mint[:4]}…{mint[-4:]}'
    return card


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
        if not supply and mint.endswith(('pump', 'bonk')):   # launchpad coins mint exactly 1B — an RPC hiccup must not blank the scan
            supply = 1_000_000_000.0
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
                coin = await _coin_card(http, mint)
                url = f"/terminal/chat?chain=solana&pair={coin['pair']}&room=bulls"
                if _radar_event('snipers-out', coin['pair'], coin['symbol'], f"All {len(fh)} flagged snipers/bundlers sold out. No sniper supply left to dump.",
                                mint=mint, mcap=coin['mcap'], name=coin['name'], cooldown=SNIPERS_OUT_COOLDOWN):
                    asyncio.create_task(_push_snipers_out(mint))
                # The creator hears it once per coin (it used to repeat on every intel refresh).
                if creator:
                    notify(creator, 'snipers', f"Every sniper on your coin {coin['symbol']} has sold out", url, once=f'snipers:{mint}',
                           meta={'mint': mint, 'symbol': coin['symbol'], 'name': coin['name'], 'mcap': coin['mcap'], 'flagged': len(fh)})
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
    try:   # the Intel desk: are known crews inside this launch?
        crew = intel_desk.check(_desk_build()['snap']['index'], _desk['rings'], all_offenders + ([creator] if creator else []))
    except Exception:
        crew = {'known': {}, 'rings': []}
    out['knownActors'] = len(crew['known'])
    out['knownRings'] = crew['rings']
    if crew['rings']:
        r0 = max(crew['rings'], key=lambda r: r['threat'])
        rugs = f", {r0['rugs']} rugs" if r0['rugs'] else ''
        flags.append(f"Known crew inside: ring {r0['id']} ({r0['size']} wallets, {r0['launchesHit']} launches hit{rugs}).")
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
GLOBE_MIN_MC = 1_000_000  # the globe shows a $1M+ tier and a $10M+ tier
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
    """$1M+ coins per chain for the globe, from FEELESS's own DexScreener-backed market feed
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
    profile: Optional[dict] = None  # {description, bannerUrl, website, twitter, telegram} from the launch form


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
    pr = payload.profile or {}
    if isinstance(pr, dict) and any(pr.get(k) for k in ('bannerUrl', 'website', 'twitter', 'telegram', 'description')):
        ban = str(pr.get('bannerUrl') or '').strip()[:300]
        ban = launch_meta.upload_path(ban) or (ban if ban.startswith('https://') else '')
        rec = {'description': str(pr.get('description') or '').strip()[:600], 'bannerUrl': ban,
               **{k: launch_meta.social_url(k, str(pr.get(k) or '')) for k in ('website', 'twitter', 'telegram')}, 'claimedBy': primary_of(creator), 'updatedAt': time.time()}
        async with _admin_lock:
            d = _json_load(COIN_PROFILES_PATH, {})
            if payload.mint not in d:
                d[payload.mint] = rec; _json_save(COIN_PROFILES_PATH, d)
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
            return _cached_json(PUSH_PATH)
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


# Where each watch rule's evidence comes from (shown under the alert in the inbox).
ALERT_SOURCE = {'up': 'Live price (DexScreener)', 'down': 'Live price (DexScreener)', 'volSpike': '5m vs 24h volume (DexScreener)',
                'feeRead': 'FeeCat entry rules', 'creatorFlag': 'FEELESS creator reputation'}


def _inbox_alert(entry, kind, text, w):
    """A phone alert also lands in the wallet's in-app inbox (one stream), with the rule and its data source."""
    address = (entry.get('prefs') or {}).get('address')
    if address:
        notify(address, 'alert', text, f"/?coin={w['chainId']}:{w['pairAddress']}", push=False,
               meta={'symbol': w.get('symbol'), 'rule': kind, 'claim': text, 'source': ALERT_SOURCE.get(kind, 'Watchlist rule')})


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
                        _inbox_alert(entry, kind, text, w)
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
            return _cached_json(CALLS_PATH)  # parsed once per file version, not on every request
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
async def recent_calls(room: Optional[str] = None, pair: Optional[str] = None, mint: Optional[str] = None, limit: int = Query(30, ge=1, le=100)):
    calls = [_call_view(c) for c in _calls_load()['calls'].values() if (not room or c['room'].startswith(room)) and (not pair or c['pairAddress'] == pair) and (not mint or c.get('mint') == mint)]
    calls.sort(key=lambda c: -c['at'])
    return {'calls': calls[:limit]}


@app.get('/api/reputation/calls/leaderboard')
async def caller_board(days: int = Query(7, ge=1, le=90), room: Optional[str] = None):
    # Profiles, the league and the feed all ask for this: rebuild at most every 20s.
    hit = _board_cache.get((days, room))
    if hit and time.time() - hit[0] < 20:
        return hit[1]
    out = _build_caller_board(days, room)
    _board_cache[(days, room)] = (time.time(), out)
    return out


_board_cache: dict = {}


def _build_caller_board(days, room):
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
            return _cached_json(REACT_PATH)
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
                return {'amount': ((r or {}).get('value') or 0) / 1e9, 'decimals': 9, 'raw': str((r or {}).get('value') or 0)}
            r = await _rpc(http, 'getTokenAccountsByOwner', [owner, {'mint': mint}, {'encoding': 'jsonParsed'}])
    except Exception:
        raise HTTPException(502, 'Balance unavailable right now.')
    total, decimals, raw = 0.0, None, 0
    for acc in (r or {}).get('value') or []:
        info = (((acc.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
        amt = (info.get('tokenAmount') or {})
        total += float(amt.get('uiAmount') or 0)
        raw += int(amt.get('amount') or 0)
        decimals = amt.get('decimals', decimals)
    return {'amount': total, 'decimals': decimals, 'raw': str(raw)}


# ---- Wallet profiles (customizable, wallet-signed) ------------------------------
PROFILE_PATH = DATA_DIR / 'profiles.json'
_profile_lock = asyncio.Lock()
HEX = set('0123456789abcdefABCDEF')


def _profiles_load():
    if PROFILE_PATH.exists():
        try:
            return _cached_json(PROFILE_PATH)
        except Exception:
            pass
    return {'profiles': {}}


def _safe_url(v, max_len=400):
    v = (v or '').strip()
    return v if (v.startswith('https://') or v.startswith('/api/reputation/uploads/')) and len(v) <= max_len else ''


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
        'theme': p.get('theme') if p.get('theme') in PROFILE_THEMES else 'grid',
        'friends': [str(f)[:44] for f in (p.get('friends') or [])[:8] if _re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', str(f))],
        'songs': [{'url': str(x.get('url'))[:300], 'title': str(x.get('title') or '')[:60]} for x in (p.get('songs') or [])[:15]
                  if isinstance(x, dict) and _re.match(r'^https://(www\.|m\.|music\.|open\.)?(youtube\.com|youtu\.be|spotify\.com|soundcloud\.com)/', str(x.get('url') or ''))],
        'handle': str(p.get('handle') or '').lower().lstrip('@')[:20] if _re.match(r'^@?[a-z0-9_]{3,20}$', str(p.get('handle') or '').lower()) else '',
        'ring': p.get('ring') if p.get('ring') in RING_TIERS else 'none',
        'nameFx': p.get('nameFx') if p.get('nameFx') in NAMEFX_TIERS else 'none',
        'featuredBadges': list(dict.fromkeys(str(b)[:40] for b in (p.get('featuredBadges') or []) if _re.match(r'^[a-z0-9-]{2,40}$', str(b))))[:_badge_limits()['profile']],
    }


class ProfileSave(BaseModel):
    address: str
    message: str = ''
    signature: str = ''
    session: str = ''    # the 7-day wallet session (signed once) replaces a per-save signature
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
    """Ed25519 check. Wallets encode the 64-byte signature differently (base64 from our client,
    base58 or hex from some wallets), so try each decoding that yields exactly 64 bytes."""
    try:
        import base58
        from nacl.signing import VerifyKey
        key = VerifyKey(base58.b58decode(address))
    except Exception:
        return False
    sig = (signature_b64 or '').strip()
    hexsig = sig[2:] if sig.lower().startswith('0x') else sig
    decoders = (lambda: base64.b64decode(sig, validate=True), lambda: base58.b58decode(sig), lambda: bytes.fromhex(hexsig))
    for decode in decoders:
        try:
            raw = decode()
            if len(raw) != 64:
                continue
            key.verify(message.encode(), raw)
            return True
        except Exception:
            continue
    return False


class FeaturedBadgesIn(BaseModel):
    address: str
    session: str
    badges: list = []


@app.post('/api/reputation/profile/featured-badges')
async def set_featured_badges(payload: FeaturedBadgesIn):
    """Pick which earned badges show next to your name in chat (only this field changes; chat session signs it)."""
    owner = _session_or_401(payload.address, payload.session)
    ids = list(dict.fromkeys(str(b) for b in payload.badges if _re.match(r'^[a-z0-9-]{2,40}$', str(b))))
    earned = {b['id'] for b in (await wallet_badges(owner))['badges']}
    picked = [b for b in ids if b in earned][:_badge_limits()['chat']]
    async with _profile_lock:
        d = _profiles_load()
        prof = d['profiles'].setdefault(owner, {})
        prof['featuredBadges'] = picked
        tmp = PROFILE_PATH.with_suffix('.tmp'); tmp.write_text(json.dumps(d)); tmp.replace(PROFILE_PATH)
    return {'featuredBadges': picked}


@app.post('/api/reputation/profile')
async def save_profile(payload: ProfileSave):
    if payload.session:
        who = session_address(payload.session)
        if not who or primary_of(who) != primary_of(payload.address):
            raise HTTPException(401, 'Session expired — sign once to continue.')
        ts = time.time()
    else:
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
            raise HTTPException(403, {1: 'That backdrop is a $FEE holder perk: hold $10+ of $FEE.', 2: 'That backdrop is an Alpha perk: reach Fee Insider tier.',
                                      3: 'That backdrop is a Whale perk: reach Fee Whale tier.'}[TIER_THEMES[clean['theme']]])
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


def _protected_wallets():
    """FEELESS's own wallets can never be blocklisted (its launches buy in the mint slot by design)."""
    extra = [a.strip() for a in os.environ.get('FEELESS_PROTECTED_WALLETS', '').split(',') if a.strip()]
    return set(_owner_wallets()) | set(_admin_wallets()) | {FEE_CREATOR_WALLET} | set(extra)


def _block_load():
    d = {'wallets': {}}
    if BLOCK_PATH.exists():
        try:
            d = _cached_json(BLOCK_PATH)
        except Exception:
            pass
    safe = _protected_wallets()
    return {**d, 'wallets': {w: r for w, r in (d.get('wallets') or {}).items() if w not in safe}}


def _is_blocked(rec):
    if not rec:
        return False
    return bool(rec.get('reported')) or len(rec.get('mints', {})) >= AUTO_BLOCK_STRIKES


async def _record_offenders(mint, bundled, snipers):
    safe = _protected_wallets()
    bundled, snipers = [w for w in bundled if w not in safe], [w for w in snipers if w not in safe]
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
    is_admin = primary_of(payload.address) in {primary_of(w) for w in _admin_wallets()}  # admins post anywhere, unthrottled
    if payload.room == 'feeless-updates' and not is_admin:
        raise HTTPException(403, 'Updates is read-only — only FEELESS admins post here.')
    if not is_admin and payload.room in _ALPHA and not await _alpha_allowed(payload.room, payload.address):
        raise HTTPException(403, f"{_ALPHA[payload.room]['name']} unlocks at ${_ALPHA[payload.room]['minUsd']:,} held in $FEE.")
    eg = None if is_admin else await evm_gate(payload.room, payload.address)
    if eg and not eg['allowed']:
        raise HTTPException(403, f"{eg['symbol']} is an EVM coin — link or switch to your 0x account." if eg.get('needsChain') else f"Hold at least ${MIN_HOLD_USD:.0f} of {eg['symbol']} to chat here (you hold ${eg['holdingUsd'] or 0:.2f}).")
    coin = None if is_admin else await _room_mint(payload.room)
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
        if not is_admin and time.time() - d.get('lastAt', {}).get(payload.address, 0) < 3:
            raise HTTPException(429, 'Slow down — one message every 3 seconds.')
        verdict = None if is_admin else _spam_check(d, payload.room, payload.address, text, tier)
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


def feeless_post(room: str, text: str):
    """Posts from FEELESS itself go out as the one real FEELESS profile — the owner wallet's — never a stand-in account."""
    owner = primary_of(((_owner_wallets() or _admin_wallets()) or ['FEELESS'])[0])
    msg = chat_system_post(room, _display_name(owner), owner, text)
    msg.update(system=False, identity=owner, handle=handle_of(owner), official=True)
    d = _chat_load(); d['rooms'][room][-1] = msg; CHAT_PATH.write_text(json.dumps(d))
    return msg


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


def _is_staff(address: str) -> bool:
    """FEELESS HQ = the admin/creator wallets (any linked wallet of theirs). Staff get every unlock: all badges and
    their perks, every chat background, colors, Fee Reserve rooms, top perk tier."""
    if not address:
        return False
    admins = _admin_wallets()
    return address in admins or primary_of(address) in {primary_of(w) for w in admins}


async def _alpha_allowed(room: str, address: str) -> bool:
    r = _ALPHA.get(room)
    if not r:
        return True
    a = primary_of(address or '')
    return bool(a) and (_is_staff(a) or await _fee_usd(a) >= r['minUsd'])


@app.get('/api/reputation/alpha-rooms')
async def alpha_rooms(address: str = ''):
    held = await _fee_usd(primary_of(address)) if address else 0.0
    admin = primary_of(address) in _admin_wallets() if address else False
    d = _chat_load()
    return {'holdingUsd': held, 'rooms': [{**r, 'unlocked': admin or held >= r['minUsd'], 'messages': len(d['rooms'].get(r['id'], []))} for r in ALPHA_ROOMS]}


@app.exception_handler(RuntimeError)
async def _rpc_busy(request: Request, exc: RuntimeError):
    # The shared Solana RPC pool is rate-limited: a clear, retryable 503 instead of a crash.
    if 'RPC pool exhausted' in str(exc):
        return JSONResponse({'detail': 'Solana data is busy — try again in a few seconds.'}, status_code=503, headers={'Retry-After': '5'})
    raise exc


@app.get('/api/reputation/room-sentiment/{chain}/{pair}')
async def room_sentiment(chain: str, pair: str):
    """Community mood for a coin: last-24h posts and posters in its Bulls vs Bears rooms."""
    part = lambda v: _re.sub(r'%[0-9a-fA-F]{2}', '_', quote(str(v), safe=''))
    rooms = _chat_load()['rooms']; since = (time.time() - 86400) * 1000
    out = {}
    for side in ('bulls', 'bears', 'trenches'):
        msgs = [m for m in rooms.get(f'coin-{part(chain)}-{part(pair)}-{side}', []) if m.get('ts', 0) >= since and not m.get('system')]
        out[side] = {'posts': len(msgs), 'posters': len({m.get('identity') or m.get('address') for m in msgs})}
    # Posters weigh double: one loud wallet can't swing the mood alone.
    bull = out['bulls']['posts'] + 2 * out['bulls']['posters']; bear = out['bears']['posts'] + 2 * out['bears']['posters']
    out['bullPct'] = round(bull / (bull + bear) * 100) if bull + bear else None
    return out


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
    pairAddress: str = ''
    text: str
    registerCall: bool = False
    room: str = ''   # 'wall' → Fee's own profile wall (meta talk); default is the coin's trenches room
    tokens: list = []   # coin cards to attach (wall reports)


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
    if payload.room == 'wall':
        cards = [t for t in payload.tokens[:3] if isinstance(t, dict) and isinstance(t.get('pair'), dict)]
        msg = chat_system_post(f'wall-{FEE_ADDRESS}', 'Fee 🐱', FEE_ADDRESS, payload.text[:2000], tokens=cards)
        return {'ok': True, 'messageId': msg['id'], 'callId': None}
    room = f'coin-{payload.chain}-{payload.pairAddress}-trenches'
    # Attach the coin card: the call ledger only accepts calls whose message carries the coin,
    # and readers see what Fee bought right in the post.
    tokens = [{'chainId': payload.chain, 'pairAddress': payload.pairAddress}]
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{payload.chain}/{payload.pairAddress}')
            snap = ((r.json() or {}).get('pairs') or [None])[0]
        if snap:
            tokens = [{'chainId': payload.chain, 'pairAddress': payload.pairAddress, 'pair': snap,
                       'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}]
    except Exception:
        pass
    msg = chat_system_post(room, 'Fee 🐱', FEE_ADDRESS, payload.text[:2000], tokens=tokens)
    try:
        head = payload.text.split('\n', 1)[0][:120]
        followers = [e for e in _push_load()['subs'].values() if (e.get('prefs') or {}).get('followFee')]
        for e in followers[:500]:
            asyncio.get_running_loop().run_in_executor(None, _send_push, e['subscription'], 'Fee 🐱 just traded', head, f"/terminal/coin/solana/{payload.pairAddress}", 'fee-copy')
            if (e.get('prefs') or {}).get('address'):
                notify(e['prefs']['address'], 'feecat', head, f"/terminal/coin/solana/{payload.pairAddress}", push=False,
                       meta={'claim': head, 'source': 'FeeCat trade post'})
    except Exception:
        pass
    call_id = None
    if payload.registerCall:
        res = await register_call(CallPayload(room=room, messageId=msg['id'], caller='Fee 🐱', callerAddress=FEE_ADDRESS,
                                               chain=payload.chain, pairAddress=payload.pairAddress, ts=time.time()))
        call_id = res.get('id')
    return {'ok': True, 'messageId': msg['id'], 'callId': call_id}


_badge_cache: dict = {}
async def _ecosystem_mints():
    # Config only (env or launch defaults): no network round trip on the fee / quote path.
    return ecosystem_mints()


@app.get('/api/reputation/badges/catalog')
async def badge_catalog():
    return {'catalog': BADGE_CATALOG}


@app.get('/api/reputation/badges/limits')
async def badge_limits_public():
    return _badge_limits()


# ---- FUSE: fused pools (backend/fuse.py) — named baskets of live pools, creator revenue on Fuse buys ----------------
import fuse as _fuse
FUSES_PATH = DATA_DIR / 'fuses.json'   # {'fuses': {id: {...}}, 'buys': [{fuse, sig, wallet, usd, feeUsd, creatorUsd, at}], 'paid': {id: usd}}
_fuse_pairs_cache: dict = {}


async def _fuse_pairs(legs):
    """Live DexScreener pairs for every leg: one batched call per chain (≤30 pairs), cached 60s."""
    out, need = {}, {}
    for leg in legs:
        hit = _fuse_pairs_cache.get(leg['pairAddress'])
        if hit and time.time() - hit[0] < 60:
            out[leg['pairAddress']] = hit[1]
        else:
            need.setdefault(leg['chainId'], []).append(leg['pairAddress'])
    if need:
        async with httpx.AsyncClient(timeout=8) as http:
            async def one(chain, pairs):
                try:
                    r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/{chain}/{",".join(pairs[:30])}')
                    return (r.json() or {}).get('pairs') or []
                except Exception:
                    return []
            for rows in await asyncio.gather(*[one(c, p) for c, p in need.items()]):
                for p in rows:
                    _fuse_pairs_cache[p.get('pairAddress')] = (time.time(), p); out[p.get('pairAddress')] = p
    return out


def _fuse_risky(pair):
    """Launch-forensics flag from CACHED intel only (never blocks a list): heavy top-10 or repeat-rug funders."""
    hit = _intel_cache.get((pair.get('baseToken') or {}).get('address'))
    d = hit[1] if hit else None
    return bool(d) and ((d.get('top10Pct') or 0) > 60 or bool(d.get('flaggedFunders')))


async def _fuse_view(fid, f, store):
    pairs = await _fuse_pairs(f['legs'])
    legs = [{**leg, **(_fuse.leg_meta(pairs[leg['pairAddress']]) if pairs.get(leg['pairAddress']) else {'missing': True})} for leg in f['legs']]
    metas = [leg for leg in legs if not leg.get('missing')]
    now_px = {leg['pairAddress']: leg.get('priceUsd') for leg in metas}
    buys = [b for b in store.get('buys', []) if b['fuse'] == fid]
    earned = round(sum(b['creatorUsd'] for b in buys), 6); paid = round(float((store.get('paid') or {}).get(fid, 0)), 6)
    return {'id': fid, **{k: f.get(k) for k in ('name', 'emoji', 'tagline', 'creator', 'creatorBps', 'createdAt', 'enabled', 'aura', 'featured', 'arena', 'dial', 'cfg', 'fromScenario')}, 'legs': legs,
            'index': _fuse.index(f['legs'], f.get('basePrices') or {}, now_px), 'score': _fuse.score(metas, sum(1 for leg in f['legs'] if pairs.get(leg['pairAddress']) and _fuse_risky(pairs[leg['pairAddress']]))),
            'tvlUsd': round(sum(m['liquidityUsd'] for m in metas)), 'volume24h': round(sum(m['volume24h'] for m in metas)),
            'aprEst': round(sum(m['aprEst'] * m['weight'] for m in metas) / max(1, sum(m['weight'] for m in metas)), 1),
            'trust': {'buyers': len({b['wallet'] for b in buys}), 'trusted': len({b['wallet'] for b in buys if not b.get('selfDeal') and not b.get('bot')})},
            'stats': {'buys': len(buys), 'volumeUsd': round(sum(b['usd'] for b in buys), 2), 'creatorEarnedUsd': earned, 'creatorPaidUsd': paid, 'creatorOwedUsd': round(max(0.0, earned - paid), 6)}}


@app.get('/api/reputation/fuses')
async def fuses_list():
    store = _json_load(FUSES_PATH, {'fuses': {}})
    rows = await asyncio.gather(*[_fuse_view(fid, f, store) for fid, f in store['fuses'].items() if f.get('enabled', True)])
    return {'fuses': sorted(rows, key=lambda r: -_hq.trust_rank(r['score']['points'], r['trust']['buyers'], r['trust']['trusted']))}


@app.get('/api/reputation/fuses/search')
async def fuses_search(request: Request, q: str = Query(..., min_length=2, max_length=60)):
    """Pool picker for the Fuse builder: live pools with the meta a builder needs (depth, volume, APR est., turnover).
    A pasted CA does a direct token lookup (search can miss fresh coins). HQ sees EVERY pool (thin ones flagged, not hidden)."""
    is_ca = bool(_re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', q.strip()))
    async with httpx.AsyncClient(timeout=8) as http:
        try:
            url = f'https://api.dexscreener.com/tokens/v1/solana/{q.strip()}' if is_ca else 'https://api.dexscreener.com/latest/dex/search'
            got = (await http.get(url, params=None if is_ca else {'q': q})).json()
            pairs = got if isinstance(got, list) else (got or {}).get('pairs') or []
        except Exception:
            pairs = []
    admin = _is_admin_req(request)
    real = {p.get('pairAddress') for p in _fuse.real_pools(pairs)}
    src = pairs if admin else [p for p in pairs if p.get('pairAddress') in real]
    rows = [{'chainId': p.get('chainId'), 'pairAddress': p.get('pairAddress'), **_fuse.leg_meta(p), **({'thin': True} if p.get('pairAddress') not in real else {})}
            for p in src[:20] if p.get('chainId') == 'solana']
    qu = q.strip().upper().lstrip('$')
    if qu in _fuse.MAJOR_ALIASES or any(qu == v[0].upper() for v in _fuse.MAJORS.values()):   # 'BTC' → the real ones, always
        have = {r['pairAddress'] for r in rows}
        rows += [r for r in await _majors_rows() if r['pairAddress'] not in have]
    hidden = sum(1 for p in pairs if p.get('chainId') == 'solana' and p.get('pairAddress') not in real) if not admin else 0
    return {'pools': _fuse.mark_real(rows, qu)[:15], 'hidden': hidden,
            'why': ('That coin has no tradable pool yet (still on its launch curve, or no volume) — a card can only swap into a live pool.' if is_ca and not rows
                    else f'{hidden} pool{"s" if hidden != 1 else ""} hidden: no volume or a parked pool.' if hidden and not rows else '')}


_fuse_discover_cache = {}
FUSE_DISCOVER_Q = {'solana': ('SOL', 'USDC', 'raydium', 'orca', 'meteora', 'pumpswap', 'JUP', 'BONK')}


async def _fuse_discover_pairs(chain):
    """Every existing discovery rail in one deduped pool: DexScreener search/boost plus FEELESS trending/new/launchpad feeds."""
    hit = _fuse_discover_cache.get(chain)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    async with httpx.AsyncClient(timeout=8) as http:
        async def search(q):
            try:
                return ((await http.get('https://api.dexscreener.com/latest/dex/search', params={'q': q})).json() or {}).get('pairs') or []
            except Exception:
                return []

        async def boosted():
            try:
                toks = [t.get('tokenAddress') for t in (await http.get('https://api.dexscreener.com/token-boosts/top/v1')).json() or [] if t.get('chainId') == chain][:30]
                return (await http.get(f'https://api.dexscreener.com/tokens/v1/{chain}/{",".join(toks)}')).json() or [] if toks else []
            except Exception:
                return []
        async def feed(kind, page=1, scope=None):
            try:
                params = {'kind': kind, 'chain': chain, 'page': page}
                if scope:
                    params['scope'] = scope
                r = await http.get('http://127.0.0.1:5001/api/market/feed', params=params)
                return r.json().get('pairs') or [] if r.status_code == 200 else []
            except Exception:
                return []
        got = await asyncio.gather(*[search(q) for q in FUSE_DISCOVER_Q.get(chain, (chain,))], boosted(),
                                   feed('trending'), feed('new'), feed('trending', 2), feed('new', 2),
                                   feed('trending', scope='launchpads'), feed('new', scope='launchpads'), feed('trending', scope='pump'))
    pairs = []
    seen = set()
    for rows in got:
        for p in rows if isinstance(rows, list) else []:
            key = p.get('pairAddress')
            if key and key not in seen:
                seen.add(key); pairs.append(p)
    _fuse_discover_cache[chain] = (time.time(), pairs)
    return pairs


@app.get('/api/reputation/fuses/discover')
async def fuses_discover(lens: str = Query('popular'), chain: str = Query('solana')):
    """Fuse Lab: browse real pools on the chain you're on, by lens (popular / yield / deep / new)."""
    if lens == 'majors':   # 🪙 the REAL SOL / BTC / ETH / … on Solana (hard-coded mints), deepest pool each
        return {'lens': 'majors', 'chain': 'solana', 'pools': await _majors_rows()}
    if lens == 'risers':   # 🚀 new majors: young coins that arrived big with real volume
        base_ = await _fuse_discover_pairs('solana')
        rs_ = _fuse.risers(base_, time.time() * 1000)
        try:   # 🟢 + Pump's top 15 graduated coins (trending pump board), never duplicated
            async with httpx.AsyncClient(timeout=8) as http:
                pump_ = (await http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': 'trending', 'chain': 'solana', 'page': 1, 'scope': 'pump'})).json().get('pairs') or []
        except Exception:
            pump_ = []
        have_ = {(r.get('baseToken') or {}).get('address') or r.get('baseAddress') for r in rs_}
        return {'lens': 'risers', 'chain': 'solana', 'pools': rs_ + _fuse.pump_majors(pump_ + base_, have_)}
    lens = lens if lens in _fuse.LENSES else 'popular'
    return {'lens': lens, 'chain': chain, 'pools': _fuse.discover(await _fuse_discover_pairs(chain), lens, chain, now_ms=time.time() * 1000)}


_majors_cache: dict = {'at': 0.0, 'rows': []}


async def _majors_rows():
    if _majors_cache['rows'] and time.time() - _majors_cache['at'] < 120:
        return _majors_cache['rows']
    by = {}
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            for p in (await http.get(f"https://api.dexscreener.com/tokens/v1/solana/{','.join(_fuse.MAJORS)}")).json() or []:
                by.setdefault((p.get('baseToken') or {}).get('address'), []).append(p)
    except Exception:
        return _majors_cache['rows']
    rows = _fuse.majors_pools(by)
    _majors_cache.update(at=time.time(), rows=rows)
    return rows


class FusePreview(BaseModel):
    pools: list
    sol: float = 1.0
    manual: bool = False     # HQ only: use the pools' own weights instead of auto
    runners: bool = False    # Runner add-on: bolt the top 2 runners on as a small slice
    runnerMints: list = []   # Fuse card: the runners YOU picked (≤3 traders / ≤6 HQ), each from the live board
    runnerSlice: float = 20.0


def _is_admin_req(request):
    try:
        _require_admin(request)
        return True
    except Exception:
        return False


@app.post('/api/reputation/fuses/preview')
async def fuses_preview(payload: FusePreview, request: Request = None):
    """Fuse Lab preview: auto-weights (fee APR × depth, 10–70% per pool) and where `sol` SOL would go. Read-only — moves nothing.
    Traders fuse up to 3 pools; HQ up to 6 and may set manual weights."""
    admin = request is not None and _is_admin_req(request)
    cap = _fuse.legs_cap(admin)
    if len(payload.pools or []) > cap:
        raise HTTPException(400, f'Fuse up to {cap} pools.')
    pools = _fuse.clean_legs([{**p, 'weight': p.get('weight') or 1} for p in payload.pools or []])
    n_run = len({str(x) for x in payload.runnerMints or [] if x})
    if len(pools) + n_run < 2:
        raise HTTPException(400, 'Pick at least 2 legs (pools and/or runners).')
    if not _hq.legs_ok(len(pools), n_run, admin):
        raise HTTPException(400, f'FEELESS cards hold up to {_hq.ADMIN_LEGS} legs (pools + runners).' if admin else
                            f'A card holds up to {_hq.CARD_POOLS} pools + {_hq.CARD_RUNNERS} runners.')
    pairs, sol_usd = await asyncio.gather(_fuse_pairs(pools) if pools else asyncio.sleep(0, {}), _sol_usd_live())
    metas = {k: _fuse.leg_meta(v) for k, v in pairs.items()}
    w = (_fuse.manual_weights(payload.pools) if admin and payload.manual else _vault.auto_weights(pools, metas, min_share=_fuse.min_share(len(pools)))) if pools else {}
    added = []; dropped_runners = []
    if payload.runnerMints:   # Fuse card: picked runners, 10% each, must be passing every gate right now
        live = await _runner_live()
        board_by = {r['mint']: r for r in live['passing'] + _rn.fresh_grads(live['dropped'])}   # 🎓 fresh grads are addable too
        rnd = (_json_load(RUNNERS_PATH, {'rounds': []}).get('rounds') or [None])[-1]
        for p_ in ((rnd or {}).get('picks') or []):
            board_by.setdefault(p_['mint'], p_) if p_['mint'] in board_by else None
        lim = _hq.ADMIN_RUNNERS if admin else _hq.CARD_RUNNERS
        wanted = [m for m in dict.fromkeys(str(x) for x in payload.runnerMints) if m]
        picked = [board_by[m] for m in wanted if m in board_by][:lim]
        # a runner that JUST failed a gate is skipped (never an error for the whole card) — the Lab unticks it and says why
        why = {r['mint']: (r.get('gates') or ['left the live feed'])[0] for r in live['dropped']}
        dropped_runners = [{'mint': m, 'symbol': next((r.get('symbol') for r in live['dropped'] if r['mint'] == m), None), 'why': why.get(m, 'left the live feed')}
                           for m in wanted if m not in board_by]
        if not picked and not pools:
            raise HTTPException(400, 'Every picked runner just failed a gate — pick from the live board.')
        legs = _rn.addon([{**p, 'weight': w[p['pairAddress']] * 100} for p in pools], picked, 10.0 * len(picked), len(picked))
        added = [l for l in legs if l.get('runner')]
        if added:
            rp = await _fuse_pairs(added)
            metas.update({k: _fuse.leg_meta(v) for k, v in rp.items()})
            pools = pools + [{k: l[k] for k in ('chainId', 'pairAddress', 'symbol')} for l in added if l['pairAddress'] in rp]
            w = {l['pairAddress']: l['weight'] / 100 for l in legs if l['pairAddress'] in metas}
    elif payload.runners:   # Runner add-on: top 2 runners of the current round as a small slice (server-picked, gated)
        live = await _runner_live()
        rnd = (_json_load(RUNNERS_PATH, {'rounds': []}).get('rounds') or [None])[-1]
        tops = [p for p in ((rnd or {}).get('picks') or []) if p['mint'] in {r['mint'] for r in live['passing']}] or live['passing']
        legs = _rn.addon([{**p, 'weight': w[p['pairAddress']] * 100} for p in pools], [t for t in tops if t['pairAddress'] not in w], payload.runnerSlice, 2)
        added = [l for l in legs if l.get('runner')]
        if added:
            rp = await _fuse_pairs(added)
            metas.update({k: _fuse.leg_meta(v) for k, v in rp.items()})
            pools = pools + [{k: l[k] for k in ('chainId', 'pairAddress', 'symbol')} for l in added if l['pairAddress'] in rp]
            w = {l['pairAddress']: l['weight'] / 100 for l in legs if l['pairAddress'] in metas}
    out = _fuse.preview(pools, metas, max(0.0, min(100000.0, payload.sol)), sol_usd, w)
    if payload.runnerMints and dropped_runners:
        out = {**out, 'droppedRunners': dropped_runners}
    rinfo = {l['pairAddress']: l for l in added}
    out['legs'] = [{**x, **({'runner': True, 'exits': rinfo[x['pairAddress']]['exits'], 'lane': rinfo[x['pairAddress']]['lane']} if x['pairAddress'] in rinfo else {})} for x in out['legs']]
    return {**out, 'cap': cap, 'admin': admin, 'runners': len(added)}


class FuseEvolveIn(BaseModel):
    style: str = 'yield'
    legs: int = Field(default=3, ge=2, le=10)
    generations: int = Field(default=16, ge=1, le=40)
    population: int = Field(default=32, ge=8, le=80)
    sol: float = Field(default=0.05, gt=0, le=1000)
    chain: str = 'solana'
    seed: int = 0
    bloodline: bool = False


@app.post('/api/reputation/admin/fuses/evolve')
async def fuses_evolve(request: Request, p: FuseEvolveIn):
    """🧬 HQ: breed Fuse baskets from the chain's live pools (best 40 across popular/yield/deep/new) over generations.
    Read-only ranking — the champion is loaded into the Lab, where Fuse in still needs your wallet."""
    _require_admin(request)
    raw = await _fuse_discover_pairs(p.chain)
    cands = {}
    for lens in _fuse.LENSES:
        for r in _fuse.discover(raw, lens, p.chain, now_ms=time.time() * 1000, limit=12):
            cands.setdefault(r['pairAddress'], r)
    metas = dict(list(cands.items())[:40])
    sol_usd = await _sol_usd_live()
    seeds = _hq.bloodline_seeds(_json_load(FUSE_HQ_PATH, {}).get('bloodline') or [], set(metas), p.legs) if p.bloodline else []
    out = await asyncio.to_thread(_fuse.evolve, metas, p.legs, p.generations, p.population, p.style if p.style in _fuse.STYLES else 'yield',
                                  p.sol, sol_usd, p.seed or int(time.time()), seeds)
    out['seeded'] = len(seeds)
    out['champions'] = [_champ_view(c, metas, p.chain) for c in out['champions']]
    return {**out, 'solUsd': sol_usd, 'styles': list(_fuse.STYLES)}


# ---- FUSE HQ (backend/fuse_hq.py): real Fuse P&L, paper arena, bloodlines, health, trader "Find my best 3" -------------
import fuse_hq as _hq
import crowd as _crowd
FUSE_HQ_PATH = DATA_DIR / 'fuse_hq.json'   # {'positions': [], 'arena': [], 'bloodline': []}
_fuse_lite_cache: dict = {}


class FusePositionIn(BaseModel):
    address: str
    session: str
    name: str = Field(default='Lab fuse', max_length=40)
    fuseId: str = ''
    copyOf: str = Field(default='', max_length=16)   # ⚡ copied from another trader's open card (its owner earns copyPct of your fee)
    back: str = Field(default='', max_length=120)    # 💰 bought to back a battle side ('kind:id'): counts on the paid bar, never the free one
    champ: bool = False                               # 👑 bought via "Buy the champion" (copy of the reigning bracket champion)
    plan: dict = {}     # 🎯 card plan from the Lab: {at, mode, onProfit, legs: {pairAddress: {tp, sl}}}
    legs: list          # [{pairAddress, chainId, symbol, signature}]
    prepaySig: str = Field(default='', max_length=100)   # 💳 the prepaid-swaps SOL transfer signed in the SAME approval as the buy
    expected: list = []  # every pairAddress the buyer approved — any that didn't land is kept as `missing` (retry or sell back)


@app.post('/api/reputation/fuses/position')
async def fuse_position(p: FusePositionIn):
    """A one-click Fuse in landed: each leg counts only if its signature is one of YOUR confirmed FEELESS buys (cost and
    tokens come from that trade record, never from the client)."""
    me = _session_or_401(p.address, p.session)
    mine = set(linked_of(me)) | {me}
    trades = {x.get('tx'): x for w, rows in _json_load(FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or []}
    legs = []
    for leg in (p.legs or [])[:_fuse.MAX_LEGS]:
        t = trades.get(str(leg.get('signature') or ''))
        if t and t.get('side', 'buy') == 'buy' and _fuse._f(t.get('tokens')) > 0:
            legs.append({'pairAddress': str(leg.get('pairAddress'))[:64], 'chainId': str(leg.get('chainId') or 'solana')[:16], 'symbol': str(leg.get('symbol') or '')[:16],
                         'mint': t.get('token'), 'sig': t['tx'], 'usd': _hq.pool_usd(t), 'tokens': _fuse._f(t.get('tokens')), 'tokens0': _fuse._f(t.get('tokens')),
                         'role': 'runner' if leg.get('role') == 'runner' else 'pool'})
    if not legs:
        raise HTTPException(400, 'None of those legs is a confirmed FEELESS buy from your wallet (yet).')
    prepaid_usd = 0.0
    if p.prepaySig and _re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', p.prepaySig) and p.prepaySig not in (_json_load(FUSE_HQ_PATH, {}).get('roundSigs') or []):
        to = await _rounds_pay_to()
        tx = None
        if to:
            async with httpx.AsyncClient(timeout=20) as http:
                for _ in range(4):
                    tx = await _rpc(http, 'getTransaction', [p.prepaySig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
                    if tx:
                        break
                    await asyncio.sleep(2)
            prepaid_usd = max((_hq.paid_lamports(tx, w, to) for w in mine), default=0) / 1e9 * (await _sol_usd_live() or 0)
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        used = {leg['sig'] for pos in d.get('positions') or [] for leg in pos['legs']}
        legs = [leg for leg in legs if leg['sig'] not in used]
        if not legs:
            return {'ok': True, 'counted': False}
        pos = {'id': uuid.uuid4().hex[:10], 'wallet': me, 'name': p.name.strip() or 'Lab fuse', 'fuseId': p.fuseId[:16], 'at': time.time(), 'legs': legs}
        choice = _hq.card_choice(p.plan, _fee_cfg().get('prepay'), _rounds_cfg())   # 🎟 the buyer's rounds · swaps per round · pay now or not
        credited = _hq.choice_credit(pos, prepaid_usd, choice) if choice['chosen'] else (prepaid_usd > 0 and _hq.prepay_credit(pos, prepaid_usd, _fee_cfg().get('prepay')))
        if credited and p.prepaySig:
            d['roundSigs'] = (d.get('roundSigs') or [])[-500:] + [p.prepaySig]   # a payment is never reused
        planned = [str(x)[:64] for x in (p.expected or [])[:_fuse.MAX_LEGS]]
        pos['missing'] = _hq.missing_legs(planned, legs)   # ⚠ approved but not landed — never hidden, never counted
        try:
            plan = _hq.clean_plan(p.plan, _json_load(FUSE_HQ_PATH, {}).get('cardRules'), [leg['pairAddress'] for leg in legs], [leg['pairAddress'] for leg in legs if leg.get('role') == 'runner']) if p.plan else None
        except ValueError:
            plan = None   # a bad plan never blocks recording a real buy
        if plan:
            pos.update(mode=plan['mode'], onProfit=plan['onProfit'], risk=plan.get('risk', 'custom'), rotateHours=plan.get('rotateHours', 24), slMode=plan.get('slMode', 'sell'), cycle=plan.get('cycle', 'steady'), payoutPct=plan.get('payoutPct', 100), compoundStyle=plan.get('compoundStyle', 'smart'), autoFees=plan.get('autoFees', True),
                       frozen=plan.get('frozen') or [], coinRotate=plan.get('coinRotate') or {}, coinModes=plan.get('coinModes') or {})
            if plan['legs']:
                pos['legGuard'] = {pa: {**g, 'firedAt': None} for pa, g in plan['legs'].items()}
            if plan['at']:
                pos['autoYield'] = {'at': plan['at'], 'base': round(sum(_fuse._f(x.get('usd')) for x in legs), 6), 'armedAt': time.time(), 'firedAt': None}
        src = next((x for x in d.get('positions') or [] if p.copyOf and x['id'] == p.copyOf), None)
        if src and primary_of(src['wallet']) != primary_of(me) and src['wallet'] not in set(linked_of(me)):   # never a self-copy
            pos.update(copyOf=src['id'], copyOwner=src['wallet'])
            reign = ((d.get('bracket') or {}).get('champions') or [{}])[-1].get('key')
            if p.champ and reign == f"user:{src['id']}":   # 👑 champion's share: double copy cut for the reigning champion's owner
                pos['champCopy'] = True
        dflt = d.get('autoYieldDefault') or {}
        if dflt.get('on'):   # HQ default: new cards arm 💸 collect-profit at +at% of what was put in
            pos['autoYield'] = {'at': float(dflt.get('at') or _hq.YIELD_DEFAULT_AT), 'base': round(sum(_fuse._f(x.get('usd')) for x in legs), 6), 'armedAt': time.time(), 'firedAt': None}
        d.setdefault('positions', []).append(pos)
        bt = d.get('battles') or {}
        if p.back and any(p.back in (x['a']['key'], x['b']['key']) for x in bt.get('pairs') or []):
            bt.setdefault('paid', {})[pos['id']] = {'key': p.back, 'wallet': me, 'usd': round(sum(_fuse._f(x.get('usd')) for x in legs), 2)}
            pos['backKey'] = p.back
        _json_save(FUSE_HQ_PATH, d)
    # AFTER notice (inbox + phone): the card is recorded. Never P&L here — numbers live in Fuse › My cards / the profile.
    miss = pos.get('missing') or []
    notify(me, 'fuse-card', (f"⚠ {pos['name']}: {len(legs)}/{len(legs) + len(miss)} coins landed — retry the other {len(miss)} or sell back, from My cards." if miss else
                             f"🧬 Card bought in one approval: {pos['name']} — {', '.join('$' + (leg.get('symbol') or '?') for leg in legs[:4])}{f' +{len(legs) - 4}' if len(legs) > 4 else ''}{' · ' + _hq.RISK_DIALS[pos['risk']]['label'] if pos.get('risk') in _hq.RISK_DIALS else ''}. Receipt + live P&L in My cards."),
           url=f"/terminal/fuse?tab=cards&card={pos['id']}", once=f"card-open-{pos['id']}", meta={'claim': 'Confirmed FEELESS buys from your wallet', 'source': 'Fuse cards'})
    return {'ok': True, 'counted': True, 'legs': len(legs), 'id': pos['id'], 'missing': miss}


class FuseReceiptIn(BaseModel):
    address: str
    legs: list          # [{sig, symbol, usd, tokens, feeUsd, networkUsd}] as quoted on the review screen


@app.post('/api/reputation/fuses/receipt')
async def fuse_receipt(p: FuseReceiptIn):
    """Before vs after: what the review screen quoted vs what each confirmed FEELESS trade actually cost (exact fill)."""
    mine = set(linked_of(primary_of(p.address))) | {primary_of(p.address), p.address}
    sigs = {str(x.get('sig') or '') for x in (p.legs or [])[:_fuse.MAX_LEGS]}
    actual = {x['tx']: x for w, rows in _json_load(FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or [] if x.get('tx') in sigs}
    return _hq.receipt((p.legs or [])[:_fuse.MAX_LEGS], actual)


class FuseCloseIn(BaseModel):
    address: str
    session: str
    id: str
    signatures: list


@app.post('/api/reputation/fuses/position/close')
async def fuse_position_close(p: FuseCloseIn):
    """Unfuse: each leg is closed only by one of YOUR confirmed FEELESS sells of that leg's coin (realized $ from that record)."""
    me = _session_or_401(p.address, p.session)
    mine = set(linked_of(me)) | {me}
    sigs = {str(x) for x in (p.signatures or [])[:_fuse.MAX_LEGS]}
    sells = [x for w, rows in _json_load(FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or [] if x.get('tx') in sigs and x.get('side') == 'sell']
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine), None)
        if not pos:
            raise HTTPException(404, 'No such Fuse position for this wallet.')
        used = {sg for x in d.get('positions') or [] for leg in x['legs'] for sg in (leg.get('sellSigs') or [leg.get('sellSig')])}
        pos, n = _hq.close_legs(pos, [t for t in sells if t['tx'] not in used], now=time.time())
        if n and all(leg.get('soldUsd') is not None for leg in pos['legs']):
            pos['closedAt'] = time.time()
        if n and pos.get('autoYield') and not pos.get('closedAt'):   # collected → re-arm from the new held value (next tick)
            pos['autoYield'].update(firedAt=None, rebase=True)
        if n:
            _hq.use_prepaid(pos, n)   # 💳 prepaid swaps cover these sells first
        _json_save(FUSE_HQ_PATH, d)
    if n:   # AFTER notice — no P&L in the text
        closed = bool(pos.get('closedAt'))
        notify(me, 'fuse-card', f"{'↩ Card withdrawn' if closed else '💰 Profit taken'}: {pos.get('name') or 'your Fuse card'} — {n} coin sell{'s' if n != 1 else ''} confirmed. {'Receipt on your profile.' if closed else 'Live P&L in My cards.'}",
               url=f"/terminal/profile/{me}" if closed else f"/terminal/fuse?tab=cards&card={pos['id']}", once=f"card-sell-{pos['id']}-{sorted(sigs)[0] if sigs else ''}",
               meta={'claim': 'Confirmed FEELESS sells from your wallet', 'source': 'Fuse cards'})
    return {'ok': True, 'closedLegs': n}


class FuseGuardIn(BaseModel):
    address: str
    session: str
    id: str
    tp: float = 0
    sl: float = 0
    trail: float = 0
    off: bool = False
    rebalance: float = 0      # auto-rebalance: alert when the card drifts this many points from its weights (0 = off)


@app.post('/api/reputation/fuses/guard')
async def fuse_guard(p: FuseGuardIn):
    """Basket limits on YOUR Fuse position. Setting them costs nothing: fees are only paid if and when you Unfuse."""
    me = _session_or_401(p.address, p.session)
    mine = set(linked_of(me)) | {me}
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine), None)
        if not pos:
            raise HTTPException(404, 'No such Fuse position for this wallet.')
        if p.rebalance or (p.off and not (p.tp or p.sl or p.trail) and pos.get('autoRebalance')):
            pos['autoRebalance'] = {'tol': round(min(50.0, max(3.0, p.rebalance)), 1), 'lastAt': 0} if p.rebalance and not p.off else None
            if not pos['autoRebalance']:
                pos.pop('autoRebalance')
            _json_save(FUSE_HQ_PATH, d)
            return {'ok': True, 'autoRebalance': pos.get('autoRebalance')}
        if p.off:
            pos.pop('guard', None)
        else:
            try:
                g = _hq.clean_guard(p.dict())
            except ValueError as e:
                raise HTTPException(400, str(e))
            pos['guard'] = {**g, 'peak': 0.0, 'armedAt': time.time(), 'firedAt': None}
        _json_save(FUSE_HQ_PATH, d)
    return {'ok': True, 'guard': pos.get('guard')}


def _card_rules():
    return _hq.clean_rules(_json_load(FUSE_HQ_PATH, {}).get('cardRules'))


_ledger_idx: dict = {'src': None, 'by': {}}


def _ledger_by_sig():
    """Fee ledger rows by signature (rebuilt only when the cached ledger object changes)."""
    led = _json_load(FEE_LEDGER_PATH, {})
    if _ledger_idx['src'] is not led:
        _ledger_idx.update(src=led, by={r.get('sig'): r for v in led.values() for r in (v or []) if r.get('sig')})
    return _ledger_idx['by']


def _card_fees(pos, by_sig=None):
    """FEELESS fees actually paid on a card (its buy + sell signatures found in the fee ledger)."""
    by_sig = by_sig if by_sig is not None else _ledger_by_sig()
    sigs = {s for leg in pos.get('legs') or [] for s in [leg.get('sig'), *(leg.get('sellSigs') or [leg.get('sellSig')])] if s}
    return round(sum(_fuse._f((by_sig.get(s) or {}).get('feeUsd')) for s in sigs), 6)


def _exit_fee(r):
    cfg = _fee_cfg(); rl = _card_rules()
    return _hq.exit_fee_usd(r, _hq.clean_bundle(cfg.get('bundle')), int(cfg.get('platformFeeBps') or 0), rl['netFeeUsdPerLeg'])


async def _fuse_yield_tick(d, now):
    """💸 Auto-collect: re-arm cards that just collected (base = held now); alert once when held ≥ base × (1 + at%) with a
    pre-filled Collect-profit link (sells only the gain). The holder's wallet still approves — FEELESS never signs."""
    ys = [x for x in d.get('positions') or [] if x.get('autoYield') and not x.get('closedAt') and not x['autoYield'].get('firedAt')]
    if not ys:
        return 0
    px = await _hq_prices([leg for x in ys for leg in x['legs']])
    upd, fired = {}, []
    for x in ys:
        r = _hq.position_pnl(x, px)
        y = x['autoYield']
        if y.get('rebase'):
            upd[x['id']] = {'base': round(_hq.held_value(r), 6), 'rebase': False}
        elif _hq.yield_due(r, y):   # price move only — fees are paid per trade and shown on the receipt
            pct = _hq.collect_pct(r, y)
            upd[x['id']] = {'firedAt': now}
            fired.append((x, r, pct))
    if upd:
        async with _admin_lock:
            d2 = _json_load(FUSE_HQ_PATH, {})
            for x in d2.get('positions') or []:
                if x['id'] in upd and x.get('autoYield'):
                    x['autoYield'].update(upd[x['id']])
            _json_save(FUSE_HQ_PATH, d2)
    for x, r, pct in fired:
        gain = _hq.held_value(r) - x['autoYield']['base']
        if x.get('onProfit') == 'compound':   # ♻ compound: move the gain from the winners into the rest of the card
            notify(x['wallet'], 'fuse-guard', f"♻ {x.get('name') or 'Your Fuse card'} hit your +{x['autoYield']['at']:.0f}% level — compound it: trim the winners, top up the rest. One approval (numbers in My cards).",
                   url=f"/terminal/fuse?tab=cards&rebalance={x['id']}", once=f"compound-{x['id']}-{x['autoYield'].get('armedAt')}-{int(x['autoYield']['base'] * 100)}",
                   meta={'claim': f"Held value up {x['autoYield']['at']:.0f}% on your base", 'source': 'Fuse P&L (live prices)'})
            continue
        notify(x['wallet'], 'fuse-guard', f"💸 {x.get('name') or 'Your Fuse card'} hit your +{x['autoYield']['at']:.0f}% level — collect the gain (sells {pct:.0f}% of each leg, your base stays in). One approval (numbers in My cards).",
               url=f"/terminal/fuse?tab=cards&collect={x['id']}&pct={pct}", once=f"yield-{x['id']}-{x['autoYield'].get('armedAt')}-{int(x['autoYield']['base'] * 100)}",
               meta={'claim': f"Held value up {x['autoYield']['at']:.0f}% on your base", 'source': 'Fuse P&L (live prices)'})
    return len(fired)


async def _fuse_swap_tick(d, now):
    """Swap mode (holder's choice per card): when a leg fails a runner gate or drops past swapDropPct, alert ONCE per leg
    with a pre-filled ⇄ Switch (sell the weak leg, buy the best gated runner) — one approval. Hold mode is never touched."""
    sw = [x for x in d.get('positions') or [] if x.get('mode') == 'swap' and not x.get('closedAt') and now >= _hq.next_switch_at(x)]   # 1 rotation / 24h
    await _rounds_out_notice(d, now)
    sw = [x for x in sw if _hq.rounds_left(x, _is_staff(x['wallet'])) > 0]   # 🔁 out of rounds → no auto rounds until +5
    if not sw:
        return 0
    live, px = await asyncio.gather(_runner_live(), _hq_prices([leg for x in sw for leg in x['legs']]))
    failing = {x['mint']: x.get('gates') or ['failed a gate'] for x in live['dropped']}
    rules = _card_rules(); n = 0
    for x in sw:
        pnl_ = _hq.position_pnl(x, px)
        pool_ = live['passing']
        if _hq.cycle_pick(x, pnl_.get('pnlPct')) == 'majors':   # 🔄 adaptive cycle: a losing card swaps its weak coin into a major
            pool_ = [{'mint': m.get('baseAddress'), 'symbol': m.get('symbol'), 'pairAddress': m.get('pairAddress'), 'logo': m.get('logo'), 'score': 100} for m in await _majors_rows() if m.get('pairAddress')]
        s = _hq.swap_suggest(pnl_, failing, pool_, rules['swapDropPct'], set(x.get('frozen') or []) | _hq.coins_not_due(x, now))
        if not s:
            continue
        n += 1
        win = int(now // (_hq.rotate_hours(x.get('rotateHours')) * 3600))   # the card's own clock (5m … 24h)
        await _spend_round(x, f"swap-{win}")
        notify(x['wallet'], 'fuse-guard', f"⇄ {x.get('name') or 'Your Fuse card'}: ${s['out']['symbol']} {s['why']} — swap it for ${s['in']['symbol']} (gated runner, score {round(_fuse._f(s['in'].get('score')))}). One approval.",
               url=f"/terminal/fuse?tab=cards&switch={x['id']}&out={s['out']['pairAddress']}&in={s['in']['mint']}&sym={s['in']['symbol']}&pair={s['in'].get('pairAddress') or ''}",
               once=f"swap-{x['id']}-{win}", meta={'claim': s['why'], 'source': 'Runner gates + Fuse P&L (live prices)'})
    return n


async def _spend_round(x, key):
    """Spend one of the card's rounds for this alert window (staff cards are unlimited)."""
    if _is_staff(x['wallet']):
        return
    async with _admin_lock:
        d2 = _json_load(FUSE_HQ_PATH, {})
        for x2 in d2.get('positions') or []:
            if x2['id'] == x['id'] and _hq.use_round(x2, key):
                _json_save(FUSE_HQ_PATH, d2)
                x.update(roundsLeft=x2['roundsLeft'], lastRoundKey=key)


async def _rounds_out_notice(d, now):
    """A card that spent its last round gets ONE notice with the +5 offer (pay now, or let compound pay when allowed)."""
    cfg = _rounds_cfg()
    out = [x for x in d.get('positions') or [] if not x.get('closedAt') and (x.get('mode') == 'swap' or x.get('parked')) and not x.get('outOfRoundsAt')
           and _hq.rounds_left(x, _is_staff(x['wallet'])) <= 0]
    if not out:
        return
    # 💸 cards that pay their own fees: up more than the pack price → +5 rounds charged to the compound (owed till the next take)
    auto = [x for x in out if x.get('autoFees', True)]
    px = await _hq_prices([l for x in auto for l in x['legs']]) if auto else {}
    pnl = {x['id']: _hq.position_pnl(x, px)['pnlUsd'] for x in auto}
    paid_ = set()
    async with _admin_lock:
        d2 = _json_load(FUSE_HQ_PATH, {})
        for x2 in d2.get('positions') or []:
            if x2['id'] in {x['id'] for x in out}:
                if x2['id'] in pnl and x2.setdefault('autoFees', True) and _hq.auto_rounds(x2, cfg, pnl[x2['id']]):
                    paid_.add(x2['id'])
                else:
                    x2['outOfRoundsAt'] = now
        _json_save(FUSE_HQ_PATH, d2)
    for x in [x for x in out if x['id'] in paid_]:
        notify(x['wallet'], 'fuse-card', f"🔁 {x.get('name') or 'Your Fuse card'} paid +{cfg['step']} rounds from its profit (${cfg['per5Usd']:.2f}, settled at the next profit take).",
               url=f"/terminal/fuse?tab=cards&card={x['id']}", once=f"rounds-auto-{x['id']}-{len(x.get('roundBuys') or [])}", meta={'claim': 'Card pays its fees from profit', 'source': 'Fuse cards'})
    out = [x for x in out if x['id'] not in paid_]
    for x in out:
        notify(x['wallet'], 'fuse-card', f"🔁 {x.get('name') or 'Your Fuse card'} used its {_hq.ROUNDS_DEFAULT} auto rounds. +{cfg['step']} for ${cfg['per5Usd']:.2f}{' — or let its compound pay' if cfg['compoundPay'] else ''}.",
               url=f"/terminal/fuse?tab=cards&card={x['id']}", once=f"rounds-out-{x['id']}-{len(x.get('roundBuys') or [])}", meta={'claim': 'Rounds used', 'source': 'Fuse cards'})


async def _fuse_buyback_tick(d, now):
    """🅿 Park & buy-back (real cards, non-custodial): a parked coin that's been SOLD and is back at its stop-out entry with
    buyers leading → ONE alert with a pre-filled buy back into the card (the holder approves)."""
    rows = [(x, pa, pk) for x in d.get('positions') or [] if not x.get('closedAt') for pa, pk in (x.get('parked') or {}).items()
            if not pk.get('alertedAt') and any(l['pairAddress'] == pa and l.get('soldUsd') is not None for l in x['legs']) and _hq.rounds_left(x, _is_staff(x['wallet'])) > 0]
    if not rows:
        return 0
    pairs = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': pa} for _, pa, _ in rows])
    fired = []
    for x, pa, pk in rows:
        p = pairs.get(pa) or {}; tx = (p.get('txns') or {}).get('h1') or {}; b, s_ = _fuse._f(tx.get('buys')), _fuse._f(tx.get('sells'))
        mom = {'buyShare': b / (b + s_) * 100 if b + s_ else 0, 'chg1h': _fuse._f((p.get('priceChange') or {}).get('h1'))}
        if _hq.buyback_due(pk, _fuse._f(p.get('priceUsd')), mom):
            fired.append((x, pa, pk))
    if fired:
        async with _admin_lock:
            d2 = _json_load(FUSE_HQ_PATH, {})
            for x2 in d2.get('positions') or []:
                for x, pa, _ in fired:
                    if x2['id'] == x['id'] and pa in (x2.get('parked') or {}):
                        x2['parked'][pa]['alertedAt'] = now
                        if not _is_staff(x2['wallet']):
                            _hq.use_round(x2, f"buyback-{pa}-{int(now)}")
            _json_save(FUSE_HQ_PATH, d2)
    for x, pa, pk in fired:
        notify(x['wallet'], 'fuse-guard', f"↩ ${pk.get('symbol')} is back at your entry with buyers leading — buy it back into {x.get('name') or 'your card'}. One approval.",
               url=f"/terminal/fuse?tab=cards&topup={x['id']}&pair={pa}", once=f"buyback-{x['id']}-{pa}-{int(pk.get('at') or 0)}",
               meta={'claim': 'Price back at the stop-out entry, buyers ≥ 50%', 'source': 'Live pool data'})
    return len(fired)


async def _fuse_leg_tick(d, now):
    """🎯 Per-coin take-profit / stop-loss: alert once per limit with that coin's sell pre-filled (one approval)."""
    lg = [x for x in d.get('positions') or [] if (x.get('legGuard') or _fuse._f(x.get('rideAt')) > 0) and not x.get('closedAt')]
    if not lg:
        return 0
    px = await _hq_prices([leg for x in lg for leg in x['legs']])
    fired, rides = [], {}
    for x in lg:
        r_ = _hq.position_pnl(x, px)
        hits_, riding_, st_ = _hq.ride_hits(r_, x.get('rideAt'), x.get('rideTrail'), x.get('rides'))   # ❄ freeze + peak trail (alerts only)
        if st_ != (x.get('rides') or {}):
            rides[x['id']] = st_
        for leg, why in hits_:
            fired.append((x, leg, 'ride', why))
        for leg, kind, pct in _hq.leg_limit_hits(r_, x.get('legGuard') or {}):
            if kind == 'sl' and _hq.coin_sl_mode(x, leg['pairAddress']) == 'hold':   # ❄ hold: no stop alerts (card or this coin)
                continue
            if kind == 'tp' and leg['pairAddress'] in riding_:   # a riding coin's TP waits — the peak trail sells it
                continue
            fired.append((x, leg, kind, pct))
    if rides and not fired:
        async with _admin_lock:
            d2 = _json_load(FUSE_HQ_PATH, {})
            for x in d2.get('positions') or []:
                if x['id'] in rides:
                    x['rides'] = rides[x['id']]
            _json_save(FUSE_HQ_PATH, d2)
    if not fired:
        return 0
    async with _admin_lock:
        d2 = _json_load(FUSE_HQ_PATH, {})
        ids = {(x['id'], leg['pairAddress']) for x, leg, k_, _ in fired if k_ != 'ride'}
        parks = {(x['id'], leg['pairAddress']): leg for x, leg, kind, _ in fired if kind == 'sl' and _hq.coin_sl_mode(x, leg['pairAddress']) == 'park'}
        for x in d2.get('positions') or []:
            if x['id'] in rides:
                x['rides'] = rides[x['id']]
            for pa, g in (x.get('legGuard') or {}).items():
                if (x['id'], pa) in ids:
                    g['firedAt'] = now
                if (x['id'], pa) in parks:   # 🅿 remember the stop-out entry: a buy-back alert comes when price is back here
                    lg_ = parks[(x['id'], pa)]
                    x.setdefault('parked', {})[pa] = {'entry': _fuse._f(lg_.get('usd')) / max(_fuse._f(lg_.get('tokens')), 1e-18), 'symbol': lg_.get('symbol'), 'mint': lg_.get('mint'), 'at': now}
        _json_save(FUSE_HQ_PATH, d2)
    for x, leg, kind, pct in fired:
        if kind == 'ride':   # ❄ the frozen coin came off its peak — sell it, one approval (no P&L in the notice text)
            notify(x['wallet'], 'fuse-guard', f"❄ ${leg.get('symbol')} in {x.get('name') or 'your Fuse card'} rode its run and {pct}. Sell it — one approval (numbers in My cards).",
                   url=f"/terminal/fuse?tab=cards&collect={x['id']}&pct=100&legs={leg['pairAddress']}", once=f"leg-ride-{x['id']}-{leg['pairAddress']}-{int((x.get('rides') or {}).get(leg['pairAddress'], {}).get('peak', 0) * 1000)}",
                   meta={'claim': f"Frozen at +{_fuse._f(x.get('rideAt')):g}%, {pct}", 'source': 'Fuse P&L (live prices)'})
            continue
        what = f"hit its +{x['legGuard'][leg['pairAddress']]['tp']:g}% take-profit" if kind == 'tp' else f"hit its −{x['legGuard'][leg['pairAddress']]['sl']:g}% stop"
        notify(x['wallet'], 'fuse-guard', f"{'🎯' if kind == 'tp' else '🛑'} ${leg.get('symbol')} in {x.get('name') or 'your Fuse card'} {what}. Sell it — one approval (numbers in My cards).",
               url=f"/terminal/fuse?tab=cards&collect={x['id']}&pct=100&legs={leg['pairAddress']}", once=f"leg-{kind}-{x['id']}-{leg['pairAddress']}",
               meta={'claim': f"{leg.get('symbol')} {pct:+.1f}% since your buy", 'source': 'Fuse P&L (live prices)'})
    return len(fired)


class FusePlanIn(BaseModel):
    address: str
    session: str
    id: str
    plan: dict


@app.post('/api/reputation/fuses/plan')
async def fuse_plan(p: FusePlanIn):
    """Edit an open card's plan: per-coin TP / SL (re-arms them), collect vs compound, hold vs swap."""
    me = _session_or_401(p.address, p.session)
    mine = set(linked_of(me)) | {me}
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise HTTPException(404, 'No such open Fuse card for this wallet.')
        try:
            plan = _hq.clean_plan({**p.plan, 'at': None} if p.plan.get('risk') not in _hq.RISK_DIALS else p.plan, d.get('cardRules'),
                                  [leg['pairAddress'] for leg in pos['legs'] if leg.get('soldUsd') is None], [leg['pairAddress'] for leg in pos['legs'] if leg.get('role') == 'runner'])
        except ValueError as e:
            raise HTTPException(400, str(e))
        pos.update(mode=plan['mode'], onProfit=plan['onProfit'], risk=plan.get('risk', 'custom'), rotateHours=plan.get('rotateHours', 24), slMode=plan.get('slMode', 'sell'), cycle=plan.get('cycle', 'steady'), payoutPct=plan.get('payoutPct', 100), compoundStyle=plan.get('compoundStyle', 'smart'), autoFees=plan.get('autoFees', True),
                   rideAt=plan.get('rideAt', 0.0), rideTrail=plan.get('rideTrail', 10.0), legGuard={pa: {**g, 'firedAt': None} for pa, g in plan['legs'].items()},
                   **({k: plan[k] for k in ('frozen', 'coinRotate', 'coinModes')} if (p.plan or {}).get('coins') else {}))
        if plan.get('risk') in _hq.RISK_DIALS and plan.get('at'):   # the dial also re-arms the card's profit level
            pos['autoYield'] = {'at': plan['at'], 'base': round(sum(_fuse._f(x.get('heldUsd') or x.get('usd')) for x in pos['legs'] if x.get('soldUsd') is None), 6), 'armedAt': time.time(), 'firedAt': None, 'rebase': True}
        _json_save(FUSE_HQ_PATH, d)
    return {'ok': True, 'plan': {k: plan.get(k) for k in ('risk', 'mode', 'onProfit', 'legs', 'at', 'rotateHours', 'slMode')}}


class FuseModeIn(BaseModel):
    address: str
    session: str
    id: str
    mode: str = 'hold'


@app.post('/api/reputation/fuses/mode')
async def fuse_mode(p: FuseModeIn):
    """Per card: 'hold' (stay together) or 'swap' (alert + pre-filled switch when a leg turns weak)."""
    me = _session_or_401(p.address, p.session)
    if p.mode not in ('hold', 'swap'):
        raise HTTPException(400, 'Mode is hold or swap.')
    mine = set(linked_of(me)) | {me}
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise HTTPException(404, 'No such open Fuse card for this wallet.')
        pos['mode'] = p.mode
        _json_save(FUSE_HQ_PATH, d)
    _arena_mega_cache.update(at=0.0, data=None)
    return {'ok': True, 'mode': p.mode}


@app.get('/api/reputation/admin/fuses/payouts/plan')
async def admin_fuse_payout_plan(request: Request):
    """💸 This week's Fuse payout: every wallet owed Fee-Back + copy cuts, in SOL at today's price (FEELESS wallets and bots
    excluded, dust waits). The plan is frozen so the paid record uses the same price."""
    _require_admin(request)
    book = await _feeback_book()
    wallets = [r['wallet'] for r in book['rows'] if r['owedUsd'] > 0]
    verdicts = await asyncio.gather(*[_shield_of(w) for w in wallets], return_exceptions=True)
    bots = {w for w, v in zip(wallets, verdicts) if isinstance(v, dict) and v.get('verdict') == 'bot'}
    plan = _hq.payout_plan(book['rows'], await _sol_usd_live(), exclude=set(_protected_wallets()) | bots)
    plan = {**plan, 'id': uuid.uuid4().hex[:10], 'at': time.time(), 'bots': len(bots)}
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {}); d['payoutPlan'] = plan; _json_save(FUSE_HQ_PATH, d)
    return {**plan, 'history': (d.get('payouts') or [])[-8:][::-1]}


class FusePaidIn(BaseModel):
    planId: str
    sigs: list


@app.post('/api/reputation/admin/fuses/payouts/paid')
async def admin_fuse_payout_paid(request: Request, p: FusePaidIn):
    """Record a payout the fee wallet signed. Every signature must be on-chain and succeeded; only SOL transfers whose
    SOURCE signed the transaction count, and each wallet is credited what actually moved (× the plan's price, ≤ owed)."""
    admin = _require_admin(request)
    sigs = [str(x) for x in (p.sigs or [])][:20]
    if not sigs or not all(_re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', x) for x in sigs):
        raise HTTPException(400, 'Bad transaction signature.')
    d = _json_load(FUSE_HQ_PATH, {})
    plan = d.get('payoutPlan') or {}
    if plan.get('id') != p.planId or time.time() - _fuse._f(plan.get('at')) > 2 * 3600:
        raise HTTPException(409, 'That payout plan expired — open Pay again for fresh amounts.')
    used = {s for x in d.get('payouts') or [] for s in x.get('sigs') or []}
    if used & set(sigs):
        raise HTTPException(409, 'Those transactions were already recorded.')
    async with httpx.AsyncClient(timeout=20) as http:
        txs = await asyncio.gather(*(_rpc(http, 'getTransaction', [x, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}]) for x in sigs))
    paid_sol: dict = {}
    for sig, tx in zip(sigs, txs):
        if not tx or (tx.get('meta') or {}).get('err'):
            raise HTTPException(400, f'Transaction {sig[:8]}… is not on-chain or failed.')
        signers = {k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')}
        for ix in tx['transaction']['message'].get('instructions') or []:
            info = (ix.get('parsed') or {}).get('info') or {}
            if ix.get('program') == 'system' and (ix.get('parsed') or {}).get('type') == 'transfer' and info.get('source') in signers:
                paid_sol[info['destination']] = round(paid_sol.get(info['destination'], 0) + info['lamports'] / 1e9, 9)
    credit = _hq.credit_paid(paid_sol, plan)
    if not credit:
        raise HTTPException(400, 'None of those transfers went to a wallet in this payout plan.')
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        fb = d.setdefault('feebackPaid', {})
        for w, usd in credit.items():
            fb[w] = round(_fuse._f(fb.get(w)) + usd, 6)
        d.setdefault('payouts', []).append({'at': time.time(), 'by': admin, 'sigs': sigs, 'planId': plan['id'], 'solUsd': plan['solUsd'],
                                            'rows': [{'wallet': w, 'usd': u, 'sol': paid_sol.get(w)} for w, u in credit.items()]})
        d['payouts'] = d['payouts'][-200:]; d.pop('payoutPlan', None)
        _json_save(FUSE_HQ_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'fuse-payout', f"${sum(credit.values()):,.2f} to {len(credit)} wallets"); _admin_save(ad)
    for w, usd in credit.items():
        notify(w, 'fuse-guard', f"💸 You were paid ${usd:,.2f} in Fuse Fee-Back + copy cuts ({paid_sol[w]:.4f} SOL).", url='/terminal/fuse?tab=cards',
               once=f"fuse-paid-{sigs[0][:16]}-{w}", meta={'claim': 'SOL transfer confirmed on-chain', 'source': 'Fuse payout'})
    return {'ok': True, 'paidUsd': round(sum(credit.values()), 6), 'wallets': len(credit)}


# ---- 🧠 Crowd edge: FeeCat learns from FEELESS traders (verified buys only) ------------------------------------------
_crowd_cache: dict = {'at': 0.0, 'data': None}


async def _crowd_build():
    trades = _json_load(FEELESS_TRADES_PATH, {})
    now = time.time()
    toks = list({t.get('token') for rows in trades.values() for t in rows or [] if t.get('side', 'buy') == 'buy' and t.get('token')})[:600]
    prices = await _token_prices(toks) if toks else {}
    skills = {w: _crowd.trader_skill(rows, prices, now) for w, rows in trades.items()}
    el = _crowd.elites(skills, exclude=set(_protected_wallets()))
    data = {'elites': len(el), 'scored': sum(1 for s in skills.values() if s['n']), 'flow': _crowd.elite_flow(trades, el, now), 'at': now,
            'rule': f"elite = ≥{_crowd.ELITE_N} verified buys scored after 24h, ≥{_crowd.ELITE_WR:g}% won ≥ +{_crowd.WIN_PCT:g}%, avg ≥ +{_crowd.ELITE_AVG:g}%"}
    _crowd_cache.update(at=now, data=data, elites_set=el)   # the set stays server-side; the API returns counts only
    return data


# ---- COIN EDGE (backend/coin_edge.py): ONE record per coin for every surface — read from caches that already exist -------
import coin_edge as _edge
_edge_cache: dict = {}   # mint -> (at, record)
_edge_pulse: dict = {}   # mint -> (at, pulse)


async def _edge_pulses(mints):
    """5m pulse for many coins in ONE call to the market service (15s per coin)."""
    now = time.time()
    need = [m for m in mints if now - _edge_pulse.get(m, (0, None))[0] > 15]
    if need:
        try:
            async with httpx.AsyncClient(timeout=6) as http:
                coins = (await http.get('http://127.0.0.1:5001/api/market/pulse', params={'mints': ','.join(need[:60])})).json().get('coins') or {}
        except Exception:
            coins = {}
        for m in need:
            _edge_pulse[m] = (now, coins.get(m))
    return {m: _edge_pulse.get(m, (0, None))[1] for m in mints}


@app.get('/api/reputation/edge')
async def coin_edge(mints: str = Query('', max_length=3000), intel: bool = False):
    """Coin edge for up to 60 coins: pulse, snipers out, verification, forensics, runner gates + bond boxes, Fuse sources, elite
    flow — 15s cache per coin, nothing slow on the request path. intel=1 (≤3 coins) also runs the holder scan if it isn't cached
    (the trade tape's wallet tags need it)."""
    ms = [m for m in dict.fromkeys(x.strip() for x in mints.split(',')) if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', m)][:60]
    now = time.time()
    out = {m: _edge_cache[m][1] for m in ms if now - _edge_cache.get(m, (0, None))[0] < 15 and not (intel and not _edge_cache[m][1].get('intel'))}
    todo = [m for m in ms if m not in out]
    if todo:
        if intel and len(todo) <= 3:
            await asyncio.gather(*[_runner_intel(m) for m in todo], return_exceptions=True)
        pulses = await _edge_pulses(todo)
        ver = (await verify_batch(','.join(todo)))['verify']
        snip = {}
        for e in _radar['events']:
            if e['kind'] == 'snipers-out' and now - e['at'] < 6 * 3600:
                snip.setdefault(e.get('mint') or e['pair'], e)
        live = _runner_live_cache.get('data') or {}
        runner = {r['mint']: r for r in (live.get('dropped') or []) + (live.get('passing') or [])}
        disc = {r['mint']: r.get('sources') or [] for r in ((_runner_disc_cache.get('data') or {}).get('runners') or [])}
        flow = ((_crowd_cache.get('data') or {}).get('flow')) or {}
        for m in todo:
            rec = _edge.compose(m, pulses.get(m), snip.get(m), ver.get(m), (_intel_cache.get(m) or (0, None))[1], runner.get(m), disc.get(m), flow.get(m))
            _edge_cache[m] = (now, rec); out[m] = rec
        if len(_edge_cache) > 5000:
            _edge_cache.clear()
    return {'edge': out, 'at': now}


@app.get('/api/reputation/crowd/elite-flow')
async def crowd_elite_flow():
    """Coins FEELESS's proven traders bought in the last 6h (counts only — no wallets exposed). Rebuilt every ~10 min."""
    if _crowd_cache['data'] and time.time() - _crowd_cache['at'] < 900:
        return _crowd_cache['data']
    return await _crowd_build()


@app.get('/api/reputation/fuses/rules')
async def fuse_rules_public():
    """What traders can pick (auto-profit levels) and the Fee-Back / swap / Arena rules HQ set."""
    return _card_rules()


@app.get('/api/reputation/admin/fuses/rules')
async def admin_fuse_rules_get(request: Request):
    _require_admin(request)
    return {'rules': _card_rules(), 'defaults': _hq.CARD_RULES, 'ranges': _hq.RULE_RANGES, 'feeback': await _feeback_book()}


@app.post('/api/reputation/admin/fuses/rules')
async def admin_fuse_rules_set(request: Request):
    """HQ › Fuse › Card rules: auto-profit levels, swap trigger, Arena top tier, Fee-Back shares. 'paidUsd' + 'wallet'
    records a Fee-Back payout."""
    admin = _require_admin(request)
    body = await request.json()
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        if body.get('wallet') and body.get('paidUsd') is not None:
            fb = d.setdefault('feebackPaid', {})
            fb[body['wallet']] = round(_fuse._f(fb.get(body['wallet'])) + max(0.0, _fuse._f(body['paidUsd'])), 6)
        else:
            d['cardRules'] = _hq.clean_rules(body)
        _json_save(FUSE_HQ_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'fuse-rules', json.dumps(body)[:200]); _admin_save(ad)
    _arena_mega_cache.update(at=0.0, data=None)
    return {'rules': _card_rules(), 'feeback': await _feeback_book()}


async def _feeback_book():
    """Fuse Fee-Back per wallet: earned (unlocked shares of fees paid on cards), paid, owed."""
    d = _json_load(FUSE_HQ_PATH, {})
    rules = _card_rules(); by = _ledger_by_sig(); now = time.time(); wins = _season_wins()
    hot = {c['id'] for c in (_arena_mega_cache.get('data') or []) if c.get('kind') == 'user' and c['activity']['tier'] in ('hot', 'blazing')}
    out = {}
    for x in d.get('positions') or []:
        fb = _hq.card_feeback(_card_fees(x, by), (x.get('closedAt') or now) - _fuse._f(x.get('at')), x['id'] in hot, rules, x['id'] in wins)
        a = out.setdefault(x['wallet'], {'wallet': x['wallet'], 'earnedUsd': 0.0, 'cards': 0, 'copyUsd': 0.0})
        a['earnedUsd'] = round(a['earnedUsd'] + fb['usd'], 6); a['cards'] += 1
        if x.get('copyOwner'):
            o = out.setdefault(x['copyOwner'], {'wallet': x['copyOwner'], 'earnedUsd': 0.0, 'cards': 0, 'copyUsd': 0.0})
            cut = _hq.copy_cut(_card_fees(x, by), rules, champ=bool(x.get('champCopy')))
            o['earnedUsd'] = round(o['earnedUsd'] + cut, 6); o['copyUsd'] = round(o['copyUsd'] + cut, 6)
    for pz in d.get('backerPrizes') or []:   # ⚔ weekly top backers' prize share
        o = out.setdefault(pz['wallet'], {'wallet': pz['wallet'], 'earnedUsd': 0.0, 'cards': 0, 'copyUsd': 0.0})
        o['earnedUsd'] = round(o['earnedUsd'] + _fuse._f(pz['usd']), 6); o['backerUsd'] = round(_fuse._f(o.get('backerUsd')) + _fuse._f(pz['usd']), 6)
    paid = d.get('feebackPaid') or {}
    rows = [{**a, 'paidUsd': _fuse._f(paid.get(w)), 'owedUsd': round(max(0.0, a['earnedUsd'] - _fuse._f(paid.get(w))), 6)} for w, a in out.items()]
    return {'rows': sorted(rows, key=lambda a: -a['owedUsd'])[:200], 'owedUsd': round(sum(a['owedUsd'] for a in rows), 6), 'earnedUsd': round(sum(a['earnedUsd'] for a in rows), 6)}


class FuseYieldIn(BaseModel):
    address: str
    session: str
    id: str
    at: float = 0
    off: bool = False


@app.post('/api/reputation/fuses/auto-yield')
async def fuse_auto_yield(p: FuseYieldIn):
    """Arm / disarm 💸 auto-collect on YOUR card: alert + pre-filled Collect profit when held value is up `at`%."""
    me = _session_or_401(p.address, p.session)
    mine = set(linked_of(me)) | {me}
    rules = _card_rules()
    if not p.off:
        at = float(p.at or rules['yieldDefault'])
        if at not in rules['yieldLevels']:
            raise HTTPException(400, f"Pick one of the auto-profit levels: {', '.join(f'+{v:g}%' for v in rules['yieldLevels'])}.")
    d = _json_load(FUSE_HQ_PATH, {})
    pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
    if not pos:
        raise HTTPException(404, 'No such open Fuse card for this wallet.')
    # Entry = your confirmed buy + its FEELESS fee; after a collect, what's still held.
    rr = None if p.off else _hq.position_pnl(pos, await _hq_prices(pos['legs']))
    base = 0.0 if p.off else round(rr['costUsd'] if not rr['realizedUsd'] else _hq.held_value(rr), 6)   # entry = confirmed buy at the pool, no fees
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        pos = next(x for x in d['positions'] if x['id'] == p.id)
        if p.off:
            pos.pop('autoYield', None)
        else:
            pos['autoYield'] = {'at': at, 'base': base, 'armedAt': time.time(), 'firedAt': None}
        _json_save(FUSE_HQ_PATH, d)
    return {'ok': True, 'autoYield': pos.get('autoYield')}


@app.get('/api/reputation/admin/fuses/auto-yield')
async def admin_auto_yield_get(request: Request):
    _require_admin(request)
    return _json_load(FUSE_HQ_PATH, {}).get('autoYieldDefault') or {'on': False, 'at': _hq.YIELD_DEFAULT_AT}


@app.post('/api/reputation/admin/fuses/auto-yield')
async def admin_auto_yield_set(request: Request):
    """HQ default for NEW Fuse cards (users can still turn it off per card)."""
    admin = _require_admin(request)
    body = await request.json()
    try:
        at = _hq.clean_yield_at(body.get('at') or _hq.YIELD_DEFAULT_AT)
    except ValueError as e:
        raise HTTPException(400, str(e))
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        d['autoYieldDefault'] = {'on': bool(body.get('on')), 'at': at}
        _json_save(FUSE_HQ_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'fuse-auto-yield', json.dumps(d['autoYieldDefault'])); _admin_save(ad)
    return d['autoYieldDefault']


async def _fuse_guard_tick():
    """Every minute: value open, guarded positions; when a limit hits, alert the holder once (inbox + phone) with a
    one-tap Unfuse link. FEELESS never signs for you — the exit is still your wallet's approval."""
    d = _json_load(FUSE_HQ_PATH, {})
    now = time.time()
    rb = [x for x in d.get('positions') or [] if x.get('autoRebalance') and not x.get('closedAt') and now - (x['autoRebalance'].get('lastAt') or 0) > 6 * 3600]
    if rb:   # auto-rebalance: one alert (≤ every 6h) with a one-tap rebalance link when a card drifts past its tolerance
        rpx = await _hq_prices([leg for x in rb for leg in x['legs']])
        fired = []
        for x in rb:
            dr = _hq.drift(_hq.position_pnl(x, rpx))
            if dr >= x['autoRebalance']['tol']:
                fired.append(x['id'])
                notify(x['wallet'], 'fuse-guard', f"⚖ {x.get('name') or 'Your Fuse card'} drifted {dr:.0f} pts from its weights — tap to rebalance (one approval).",
                       url=f"/terminal/fuse?tab=cards&rebalance={x['id']}", once=f"rb-{x['id']}-{int(now // (6 * 3600))}",
                       meta={'claim': f'Largest leg is {dr:.0f} points off its target share', 'source': 'Fuse P&L (live prices)'})
        if fired:
            async with _admin_lock:
                d2 = _json_load(FUSE_HQ_PATH, {})
                for x in d2.get('positions') or []:
                    if x['id'] in fired and x.get('autoRebalance'):
                        x['autoRebalance']['lastAt'] = now
                _json_save(FUSE_HQ_PATH, d2)
        d = _json_load(FUSE_HQ_PATH, {})
    await _fuse_yield_tick(d, now)
    await _fuse_swap_tick(d, now)
    await _fuse_leg_tick(d, now)
    await _fuse_buyback_tick(_json_load(FUSE_HQ_PATH, {}), now)
    d = _json_load(FUSE_HQ_PATH, {})
    live = [x for x in d.get('positions') or [] if x.get('guard') and not x['guard'].get('firedAt') and not x.get('closedAt')]
    if not live:
        return 0
    px = await _hq_prices([leg for x in live for leg in x['legs']])
    hits, peaks = [], {}
    for x in live:
        r = _hq.position_pnl(x, px)
        hit, peak = _hq.guard_check(x['guard'], r['pnlPct'])
        peaks[x['id']] = peak
        if hit:
            hits.append((x, hit, r))
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        by = {x['id']: x for x in d.get('positions') or []}
        for pid, pk in peaks.items():
            if pid in by and by[pid].get('guard'):
                by[pid]['guard']['peak'] = round(pk, 2)
        for x, hit, r in hits:
            if by.get(x['id'], {}).get('guard'):
                by[x['id']]['guard']['firedAt'] = time.time(); by[x['id']]['guard']['hit'] = hit
        _json_save(FUSE_HQ_PATH, d)
    label = {'tp': '🎯 Take-profit hit', 'sl': '🛑 Stop-loss hit', 'trail': '📉 Trailing stop hit'}
    for x, hit, r in hits:
        notify(x['wallet'], 'fuse-guard', f"{label[hit]} on {x.get('name') or 'your Fuse'}. Tap to Unfuse — one approval (numbers in My cards).",
               url=f"/terminal/trade?tab=fuse&unfuse={x['id']}", once=f"guard-{x['id']}-{x['guard'].get('armedAt')}",
               meta={'claim': f"Basket P&L {r['pnlPct']:+.1f}% vs your limit", 'source': 'Fuse P&L (live DexScreener prices)'})
    return len(hits)


async def _card_signal_tick(now=None):
    """ONE signal stream (the inbox you already have — no new tab): coins on your OPEN cards that just got a coin-edge signal
    (🔔 bond run, 🎯 snipers out, ⚠ now failing a runner gate) → one inbox + phone notice each, with the card one tap away.
    Reads caches only. No P&L in the text."""
    now = now or time.time()
    d = _json_load(FUSE_HQ_PATH, {})
    live = _runner_live_cache.get('data') or {}
    board = {r['mint']: r for r in (live.get('passing') or []) + (live.get('dropped') or [])}
    snip = {e.get('mint') or e['pair'] for e in _radar['events'] if e['kind'] == 'snipers-out' and now - e['at'] < 3600}
    n = 0
    for x in d.get('positions') or []:
        if x.get('closedAt'):
            continue
        for leg in x['legs']:
            if leg.get('soldUsd') is not None or not leg.get('mint'):
                continue
            m, sym = leg['mint'], leg.get('symbol') or '?'
            r = board.get(m) or {}
            sigs = []
            if r.get('bondTier'):
                sigs.append(('bond', f"🔔 ${sym} on {x.get('name') or 'your card'}: {r['bondTier']} — every bond box ticked.", 'Fuse Runners bond check'))
            if m in snip or leg.get('pairAddress') in snip:
                sigs.append(('snipers', f"🎯 ${sym} on {x.get('name') or 'your card'}: every flagged sniper sold out.", 'Launch forensics radar'))
            if leg.get('role') == 'runner' and r.get('gates'):
                sigs.append(('gate', f"⚠ ${sym} on {x.get('name') or 'your card'} now fails: {r['gates'][0]}. Switch or sell it — one approval.", 'Fuse Runners gates'))
            for kind, text, src in sigs:
                notify(x['wallet'], 'fuse-signal', text, url=f"/terminal/fuse?tab=cards&card={x['id']}", once=f"sig-{x['id']}-{m}-{kind}-{int(now // 21600)}",
                       meta={'claim': text, 'source': src})
                n += 1
    return n


async def _fuse_guard_loop():
    await asyncio.sleep(45)
    while True:
        try:
            await _fuse_guard_tick()
            await _card_signal_tick()
        except Exception as e:
            print('fuse guard:', e)
        await asyncio.sleep(60)


@app.on_event('startup')
async def _fuse_guard_start():
    if not os.environ.get('PYTEST_CURRENT_TEST'):
        asyncio.create_task(_fuse_guard_loop())


class FuseSwitchIn(BaseModel):
    address: str
    session: str
    id: str
    legs: list          # [{pairAddress, symbol, role, signature}] — the BUYS that land in this card


@app.post('/api/reputation/fuses/position/switch')
async def fuse_position_switch(p: FuseSwitchIn):
    """Switch-in / top-up: new legs join YOUR card only from your verified FEELESS buys, within 3 pools + 3 runners."""
    me = _session_or_401(p.address, p.session)
    mine = set(linked_of(me)) | {me}
    metas = [x for x in (p.legs or [])[:6] if isinstance(x, dict)]
    trades = {x.get('tx'): x for w, rows in _json_load(FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or []}
    pairs = [(trades[str(m.get('signature'))], m) for m in metas if str(m.get('signature')) in trades and trades[str(m.get('signature'))].get('side', 'buy') == 'buy']
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise HTTPException(404, 'No open Fuse card with that id for this wallet.')
        used = {leg.get('sig') for x in d.get('positions') or [] for leg in x['legs']}
        pairs = [(t, m) for t, m in pairs if t['tx'] not in used]
        buys_before = sum(1 for e in pos.get('events') or [] if e.get('kind') == 'buy')
        pos, n = _hq.add_legs(pos, [t for t, _ in pairs], [m for _, m in pairs], now=time.time())
        filled = [m.get('pairAddress') for _, m in pairs if m.get('pairAddress') in (pos.get('missing') or [])]
        if filled:   # ↻ a retry completed the original buy — not a switch, the 24h clock is untouched
            pos['missing'] = [x for x in pos.get('missing') or [] if x not in filled]
        switched = not filled and sum(1 for e in pos.get('events') or [] if e.get('kind') == 'buy') > buys_before
        if switched:   # a real switch-in (not a top-up)
            pos['lastSwitchAt'] = time.time()
            pos['switchTimes'] = (pos.get('switchTimes') or [])[-9:] + [pos['lastSwitchAt']]
        if n and not filled:
            _hq.use_prepaid(pos, n)   # 💳 prepaid swaps cover these buys first
        _json_save(FUSE_HQ_PATH, d)
    if n:
        notify(me, 'fuse-card', f"{'⇄ Switched in' if switched else '⚖ Topped up'}: {', '.join('$' + (m.get('symbol') or '?') for _, m in pairs[:3])} on {pos.get('name') or 'your Fuse card'}.{' Next switch in 24h.' if switched and not _is_staff(me) else ''}",
               url=f"/terminal/fuse?tab=cards&card={pos['id']}", once=f"card-in-{pos['id']}-{pairs[0][0]['tx'] if pairs else ''}", meta={'claim': 'Confirmed FEELESS buys from your wallet', 'source': 'Fuse cards'})
    return {'ok': True, 'added': n, 'nextSwitchAt': _hq.next_switch_at(pos, _is_staff(me))}



class FuseFreezeIn(BaseModel):
    address: str
    session: str
    id: str
    pairAddress: str = Field(..., max_length=64)
    frozen: bool = True


@app.post('/api/reputation/fuses/freeze')
async def fuse_freeze(p: FuseFreezeIn):
    """❄ Freeze a coin / pool on YOUR card: the engine (swap mode, auto-rotate suggestions) never touches it — only you can
    switch or sell it. Freeze 1, 2 or all of them; unfreeze any time."""
    me = _session_or_401(p.address, p.session)
    mine = set(linked_of(me)) | {me}
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise HTTPException(404, 'No open Fuse card with that id for this wallet.')
        if not any(leg['pairAddress'] == p.pairAddress and leg.get('soldUsd') is None for leg in pos['legs']):
            raise HTTPException(400, 'That coin is not open on this card.')
        fz = [x for x in pos.get('frozen') or [] if x != p.pairAddress] + ([p.pairAddress] if p.frozen else [])
        pos['frozen'] = fz
        _json_save(FUSE_HQ_PATH, d)
    return {'ok': True, 'frozen': fz}

class CoinModeIn(BaseModel):
    address: str
    session: str
    id: str
    pairAddress: str = Field(..., max_length=64)
    slMode: str = Field(default='', max_length=8)   # sell | park | hold | card (= follow the card) · '' = leave as is
    tp: float | None = None                          # this coin's take-profit % (alert, one-tap) · 0 = off
    sl: float | None = None                          # this coin's stop % · 0 = off
    rotateHours: float | None = None                 # ⇄ replace this coin at most every … (5m–24h) · 0 = follow the card


@app.post('/api/reputation/fuses/coin-mode')
async def fuse_coin_mode(p: CoinModeIn):
    """Per-coin stop mode on YOUR card: ✂ sell · 🅿 park (sell to SOL, one-tap buy-back when it's back with buyers) · ❄ hold —
    or 'card' to follow the card's setting. Pairs with ❄ freeze (engine hands off the coin)."""
    me = _session_or_401(p.address, p.session)
    mine = set(linked_of(me)) | {me}
    if p.slMode and p.slMode not in (*_hq.SL_MODES, 'card'):
        raise HTTPException(400, 'slMode must be sell, park, hold or card.')
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise HTTPException(404, 'No open Fuse card with that id for this wallet.')
        if not any(leg['pairAddress'] == p.pairAddress and leg.get('soldUsd') is None for leg in pos['legs']):
            raise HTTPException(400, 'That coin is not open on this card.')
        cm = dict(pos.get('coinModes') or {})
        if p.slMode:
            cm.pop(p.pairAddress, None)
            if p.slMode != 'card':
                cm[p.pairAddress] = p.slMode
        pos['coinModes'] = cm
        if p.tp is not None or p.sl is not None:   # 🎯 this coin's own TP / SL (alerts once, one-tap sell)
            g = {**(pos.get('legGuard') or {}).get(p.pairAddress, {})}
            if p.tp is not None:
                g['tp'] = max(0.0, min(5000.0, float(p.tp)))
            if p.sl is not None:
                g['sl'] = max(0.0, min(95.0, float(p.sl)))
            g['firedAt'] = None
            pos.setdefault('legGuard', {})[p.pairAddress] = g
        if p.rotateHours is not None:
            cr = {k: v for k, v in (pos.get('coinRotate') or {}).items() if k != p.pairAddress}
            if p.rotateHours:
                cr[p.pairAddress] = _hq.rotate_hours(p.rotateHours)
            pos['coinRotate'] = cr
        _json_save(FUSE_HQ_PATH, d)
    return {'ok': True, 'coinModes': cm, 'legGuard': (pos.get('legGuard') or {}).get(p.pairAddress), 'coinRotate': pos.get('coinRotate') or {}}


@app.get('/api/reputation/fuses/limits/{address}')
async def fuse_limits(address: str):
    """How many Fuse cards this wallet may hold open: 2, or 3 with ≥ $200 of $FEE. Each card: 3 pools + 3 runners."""
    me = primary_of(address)
    mine = set(linked_of(me)) | {me}
    open_n = sum(1 for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or [] if x['wallet'] in mine and not x.get('closedAt'))
    try:
        fee = await _fee_usd(me)
    except Exception:
        fee = 0.0
    mx = _hq.card_limit(fee, _is_staff(me))
    return {'open': open_n, 'max': mx, 'canOpen': open_n < mx, 'feeUsd': round(fee, 2), 'feeFor3rd': _hq.FEE_FOR_3RD_CARD,
            'pools': _hq.CARD_POOLS, 'runners': _hq.CARD_RUNNERS}


@app.get('/api/reputation/fuses/receipts/{address}')
async def fuse_receipts(address: str):
    """Profile › Fuse receipts: every withdrawn (closed) card with its whole lifecycle — legs in, take-profits, switches, out."""
    me = primary_of(address)
    mine = set(linked_of(me)) | {me}
    by, rl = _ledger_by_sig(), _card_rules()
    # each receipt carries its moves (buys / sells / switches / top-ups) and the FEELESS fees actually paid (fee ledger) +
    # a network estimate — shown on the receipt, never inside P&L
    rows = [{**_hq.position_pnl(x, {}), 'events': (x.get('events') or [])[-30:], 'feesUsd': _card_fees(x, by),
             'netUsd': round(rl['netFeeUsdPerLeg'] * 2 * len(x.get('legs') or []), 4)}
            for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or [] if x['wallet'] in mine and x.get('closedAt')]
    return {'receipts': sorted(rows, key=lambda r: -(r.get('closedAt') or 0))[:30]}


async def _hq_prices(legs):
    pairs = await _fuse_pairs([{'chainId': leg.get('chainId', 'solana'), 'pairAddress': leg['pairAddress']} for leg in legs])
    return {k: _fuse._f(v.get('priceUsd')) for k, v in pairs.items()}


_held_cache: dict = {}


async def _wallet_held(wallets, mints):
    """{mint: tokens} summed over these wallets from chain (both token programs), cached 60s. None = RPC unavailable (never guess)."""
    key = tuple(wallets)
    hit = _held_cache.get(key)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            res = await asyncio.gather(*[_rpc(http, 'getTokenAccountsByOwner', [w, {'programId': pg}, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}])
                                         for w in wallets[:6] for pg in _FW_TOKEN_PROGRAMS])
    except Exception:
        return None
    held = {}
    for r in res:
        for a in (r or {}).get('value') or []:
            info = (((a.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
            if info.get('mint'):
                held[info['mint']] = held.get(info['mint'], 0.0) + _fuse._f((info.get('tokenAmount') or {}).get('uiAmountString') or (info.get('tokenAmount') or {}).get('uiAmount'))
    _held_cache[key] = (time.time(), held)
    return held


@app.get('/api/reputation/fuses/pnl/{address}')
async def fuse_pnl(address: str):
    mine = set(linked_of(primary_of(address))) | {primary_of(address), address}
    pos = [x for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or [] if x['wallet'] in mine]
    open_mints = {l.get('mint') for x in pos if not x.get('closedAt') for l in x['legs'] if l.get('soldUsd') is None and l.get('mint')}
    if open_mints:   # 🔗 a card never counts coins the wallet doesn't REALLY hold (on-chain balances, all linked wallets, 60s cache)
        held = await _wallet_held(sorted(mine), open_mints)
        if held is not None:
            capped = {x['id']: x for x in _hq.cap_to_wallet([x for x in pos if not x.get('closedAt')], held)}
            pos = [capped.get(x['id'], x) for x in pos]
    px = await _hq_prices([leg for x in pos for leg in x['legs']]) if pos else {}
    by, rules, now = _ledger_by_sig(), _card_rules(), time.time()
    hot = {c['id'] for c in (_arena_mega_cache.get('data') or []) if c.get('kind') == 'user' and c['activity']['tier'] in ('hot', 'blazing')}
    wins = _season_wins()
    by_ = _ledger_by_sig()   # FEELESS fees already paid on each card (for the profit trail's book)
    rows = sorted(({**_hq.position_pnl(x, px), 'guard': x.get('guard'), 'autoRebalance': x.get('autoRebalance'), 'autoYield': x.get('autoYield'), 'mode': x.get('mode') or 'hold', 'nextSwitchAt': _hq.next_switch_at(x), 'rotateHours': x.get('rotateHours') or 24, 'slMode': x.get('slMode') or 'sell', 'coinModes': x.get('coinModes') or {}, 'coinRotate': x.get('coinRotate') or {}, 'cycle': x.get('cycle') or 'steady', 'payoutPct': x.get('payoutPct', 100 if (x.get('onProfit') or 'collect') == 'collect' else 0), 'compoundStyle': x.get('compoundStyle') or 'smart', 'autoFees': x.get('autoFees', True), 'missing': x.get('missing') or [],
                  'heldShort': [l['pairAddress'] for l in x['legs'] if l.get('heldShort')],
                  'roundsLeft': _hq.rounds_left(x, _is_staff(x['wallet'])), 'roundsUsed': x.get('roundsUsed') or 0, 'roundsOwedUsd': x.get('roundsOwedUsd') or 0,
                  'feesPaidUsd': _card_fees(x, by_), 'roundsPaidUsd': round(sum(_fuse._f(rb.get('usd')) for rb in x.get('roundBuys') or [] if rb.get('mode') == 'pay'), 4), 'roundPacks': len(x.get('roundBuys') or []), 'parked': x.get('parked') or {}, 'risk': x.get('risk') or 'custom',
                    'onProfit': x.get('onProfit') or 'collect', 'legGuard': x.get('legGuard') or {},
                    'feeback': _hq.card_feeback(_card_fees(x, by), (x.get('closedAt') or now) - _fuse._f(x.get('at')), x['id'] in hot, rules, x['id'] in wins), 'onArena': x['id'] in hot,
                    'seasonWin': wins.get(x['id']), 'beatCat': [w['week'] for w in _json_load(FUSE_HQ_PATH, {}).get('catChallenge') or [] if x['id'] in (w.get('ids') or [])]} for x in pos), key=lambda r: -(r['at'] or 0))
    allpos = _json_load(FUSE_HQ_PATH, {}).get('positions') or []
    copies = {}
    for c in allpos:
        if c.get('copyOf'):
            k = copies.setdefault(c['copyOf'], {'n': 0, 'usd': 0.0}); k['n'] += 1; k['usd'] = round(k['usd'] + _hq.copy_cut(_card_fees(c, by), rules, champ=bool(c.get('champCopy'))), 6)
    box = _json_load(NOTIF_PATH, {}).get(primary_of(address)) or []
    frz = {x['id']: x.get('frozen') or [] for x in pos}
    rows = [{**r, 'frozen': frz.get(r['id'], []), 'autos': _hq.card_autos(box, r['id'], now), 'drift': _hq.drift(r), 'exitFeeUsd': 0.0 if r['closed'] else _exit_fee(r), 'streak': _hq.swap_streak(r), 'compound': _hq.compound_streak(r),
             'copies': (copies.get(r['id']) or {}).get('n', 0), 'copyEarnedUsd': (copies.get(r['id']) or {}).get('usd', 0.0)} for r in rows]
    held = [r for r in rows if not r['closed']]
    return {**_hq.book(rows), 'rows': rows[:20], 'rules': {k: rules[k] for k in ('yieldLevels', 'yieldDefault', 'swapDropPct')},
            'held': {'cards': len(held), 'costUsd': round(sum(r['costUsd'] for r in held), 4), 'valueUsd': round(sum(r['valueUsd'] for r in held), 4),
                     'pnlUsd': round(sum(r['pnlUsd'] for r in held), 4), 'pnlPct': round((sum(r['valueUsd'] for r in held) / max(1e-9, sum(r['costUsd'] for r in held)) - 1) * 100, 2) if held else 0.0},
            'feebackUsd': round(sum(r['feeback']['usd'] for r in rows), 6)}


_fuse_holders_cache: dict = {}


@app.get('/api/reputation/fuses/creators')
async def fuse_creators():
    """Fuse creator season (this week, from Monday 00:00 UTC): ranked by buyers' real P&L. 60s cache."""
    hit = _fuse_holders_cache.get('creators')
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    now = time.time(); since = now - ((time.gmtime(now).tm_wday * 86400) + now % 86400)
    pos = [x for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or [] if (x.get('at') or 0) >= since and x.get('fuseId')]
    px = await _hq_prices([leg for x in pos for leg in x['legs']]) if pos else {}
    fz = {fid: {'creator': f.get('creator'), 'name': f.get('name')} for fid, f in _json_load(FUSES_PATH, {'fuses': {}})['fuses'].items()}
    board = _hq.creator_board([{**_hq.position_pnl(x, px), 'wallet': x['wallet'], 'fuseId': x['fuseId'], 'at': x.get('at')} for x in pos], fz, since)
    out = {'since': since, 'endsAt': since + 7 * 86400, 'minBuyers': _hq.MIN_BUYERS, 'rows': [{**r, 'handle': handle_of(r['creator'])} for r in board[:30]]}
    _fuse_holders_cache['creators'] = (time.time(), out)
    return out





@app.get('/api/reputation/fuses/holders')
async def fuse_holders():
    """Fuse holders board (Fuse chat side panel): every wallet with verified Fuse positions, live P&L, best first. 60s cache."""
    hit = _fuse_holders_cache.get('all')
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    pos = _json_load(FUSE_HQ_PATH, {}).get('positions') or []
    px = await _hq_prices([leg for x in pos for leg in x['legs']]) if pos else {}
    by = {}
    for x in pos:
        r = _hq.position_pnl(x, px)
        a = by.setdefault(x['wallet'], {'address': x['wallet'], 'handle': handle_of(x['wallet']), 'fuses': 0, 'costUsd': 0.0, 'valueUsd': 0.0, 'lastAt': 0, 'names': []})
        a['fuses'] += 1; a['costUsd'] += r['costUsd']; a['valueUsd'] += r['valueUsd']; a['lastAt'] = max(a['lastAt'], x.get('at') or 0)
        if r.get('name') and r['name'] not in a['names']:
            a['names'].append(r['name'])
    rows = [{**a, 'names': a['names'][:3], 'costUsd': round(a['costUsd'], 2), 'pnlPct': round((a['valueUsd'] / a['costUsd'] - 1) * 100, 2) if a['costUsd'] else 0.0}
            for a in by.values()]
    out = {'holders': sorted(rows, key=lambda r: -r['pnlPct'])[:50], 'total': len(rows)}
    for r in out['holders']:
        r.pop('valueUsd', None)
    _fuse_holders_cache['all'] = (time.time(), out)
    return out


async def _arena_settle(px=None, now=None):
    """Close every arena run older than 24h at today's prices, once. Returns the saved store."""
    now = now or time.time()
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        due = [e for e in d.get('arena') or [] if not e.get('close') and now - e['at'] >= _hq.ARENA_HOURS * 3600]
        if due:
            px = px if px is not None else await _hq_prices([leg for e in due for leg in e['legs']])
            for e in due:
                e['close'] = {leg['pairAddress']: px.get(leg['pairAddress']) or leg['start'] for leg in e['legs']}; e['closedAt'] = now
            _json_save(FUSE_HQ_PATH, d)
    return d


# ---- 🏆 Fuse seasons: weekly (Monday 00:00 UTC), cards opened that week ranked by real P&L %; top 3 crowned once ----------
_fuse_season_cache: dict = {'at': 0.0, 'data': None}


async def _season_rows(since, until):
    pos = [x for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or [] if since <= _fuse._f(x.get('at')) < until]
    if not pos:
        return [], set()
    px = await _hq_prices([leg for x in pos for leg in x['legs'] if leg.get('soldUsd') is None])
    rows = []
    for x in pos:
        rr = _hq.position_pnl(x, px)
        rows.append({**rr, 'wallet': x['wallet'], 'streak': _hq.swap_streak({**rr, 'events': x.get('events')})})
    wallets = list({x['wallet'] for x in pos})
    verdicts = await asyncio.gather(*[_shield_of(w) for w in wallets], return_exceptions=True)
    bots = {w for w, v in zip(wallets, verdicts) if isinstance(v, dict) and v.get('verdict') == 'bot'}
    return rows, bots


def _season_wins():
    """{card id: {'week', 'rank'}} for every crowned card (drives the 🏆 badge + the season Fee-Back boost)."""
    return {t_['id']: {'week': s['week'], 'rank': t_['rank']} for s in _json_load(FUSE_HQ_PATH, {}).get('seasons') or [] for t_ in s.get('top') or []}


async def _fuse_season_tick(now):
    """Once per week: crown last week's top 3 cards (stored forever, winners notified, Fee-Back boost on those cards)."""
    start = _hq.season_start(now); prev = start - _hq.WEEK
    if _fuse._f(_json_load(FUSE_HQ_PATH, {}).get('seasonAwarded')) >= prev:
        return None
    rows, bots = await _season_rows(prev, start)
    top = _hq.season_board(rows, prev, start, bots)[:3]
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        if _fuse._f(d.get('seasonAwarded')) >= prev:
            return None
        d['seasonAwarded'] = prev
        if top:
            d.setdefault('seasons', []).append({'week': prev, 'n': len(rows), 'top': [{**t_, 'handle': handle_of(t_['wallet'])} for t_ in top]})
        _json_save(FUSE_HQ_PATH, d)
    # ⚔ backer season: last week's top 3 backers split the HQ prize pool (owed in the Fee-Back book → weekly payout)
    dd = _json_load(FUSE_HQ_PATH, {})
    prizes = _hq.backer_prizes(_hq.backer_board(dd.get('backLog'), dd.get('backWins'), prev, start, set(_protected_wallets()) | bots), _card_rules().get('backerPoolUsd', 0))
    if prizes:
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {})
            d['backerPrizes'] = (d.get('backerPrizes') or []) + [{**pz, 'week': prev} for pz in prizes]
            _json_save(FUSE_HQ_PATH, d)
        for pz in prizes:
            notify(pz['wallet'], 'fuse-card', f"⚔ Top backer #{pz['rank']} last week — ${pz['usd']:.2f} prize, paid with the weekly Fee-Back.", url='/terminal/fuse?tab=arena',
                   once=f"backer-{prev}-{pz['wallet']}", meta={'claim': 'Most winning battle backs that week', 'source': 'Arena battles'})
    # 🐱 FeeCat challenge: every card opened last week that beat her average trade that week
    cat = await _feecat_raw()
    cat_pct = _hq.feecat_week_pct((cat or {}).get('exits'), (cat or {}).get('positions'), prev, start) if cat else None
    beat = _hq.beats_cat(_hq.season_board(rows, prev, start, bots), cat_pct)
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        d.setdefault('catChallenge', []).append({'week': prev, 'catPct': cat_pct, 'ids': beat})
        d['catChallenge'] = d['catChallenge'][-52:]
        _json_save(FUSE_HQ_PATH, d)
    owners = {x['id']: x for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or []}
    for cid in beat:
        if cid in owners:
            notify(owners[cid]['wallet'], 'fuse-guard', f"🐱 Your card {owners[cid].get('name') or ''} beat FeeCat last week ({cat_pct:+.1f}% her average trade). +{_hq.CAT_WIN_PTS} Fuse score.",
                   url='/terminal/fuse?tab=arena', once=f"beatcat-{prev}-{cid}", meta={'claim': 'Card P&L above FeeCat\'s weekly average trade', 'source': 'Fuse season + FeeCat sim book'})
    # 🐱 FeeCat's weekly note: every wallet with a card opened last week, once per week
    dial = _json_load(RUNNERS_PATH, {}).get('cfgDial')
    tuned = sum(1 for a in _admin_load().get('audit') or [] if a.get('action') == 'runners-config' and prev <= _fuse._f(a.get('at')) < start)
    beat_wallets = {owners[c]['wallet'] for c in beat if c in owners}
    for w in {r['wallet'] for r in rows if r.get('wallet')}:
        notify(w, 'fuse-card', _hq.feecat_weekly(dial, tuned, w in beat_wallets, cat_pct), url='/terminal/fuse?tab=arena', once=f"feecat-week-{prev}",
               meta={'claim': "FeeCat's sim book + engine changes that week", 'source': 'Fuse season + HQ audit log'})
    plan = _hq.payout_plan((await _feeback_book())['rows'], await _sol_usd_live(), exclude=_protected_wallets())
    if plan['totalUsd'] >= 1:
        for adm in _admin_wallets():
            notify(adm, 'shield', f"💸 Weekly Fuse payout ready: ${plan['totalUsd']:,.2f} to {len(plan['rows'])} wallets (Fee-Back + copy cuts). HQ › Fuse › Card rules › Pay.",
                   url='/terminal/command?tab=fuse', once=f"fuse-payout-{prev}", meta={'claim': 'Owed from the fee ledger', 'source': 'Fuse Fee-Back book'})
    medal = {1: '🥇', 2: '🥈', 3: '🥉'}
    if top:
        _fuse_chat('fuse-lab', '🏆 Fuse season crowned: ' + ' · '.join(f"{medal[t_['rank']]} {handle_of(t_['wallet']) or t_['wallet'][:4] + '…'} {t_.get('name') or ''} {t_['pnlPct']:+.1f}%" for t_ in top), f"season-{prev}")
    for t_ in top:
        notify(t_['wallet'], 'fuse-guard', f"🏆 {medal[t_['rank']]} Your card {t_.get('name') or ''} finished #{t_['rank']} in this week's Fuse season ({t_['pnlPct']:+.1f}%). "
               f"+{_card_rules()['seasonBoostPct']:g}% Fee-Back on it.", url='/terminal/fuse?tab=arena', once=f"season-{prev}-{t_['id']}",
               meta={'claim': f"#{t_['rank']} of {len(rows)} cards opened that week, by real P&L", 'source': 'Fuse season (verified FEELESS trades)'})
    _fuse_season_cache.update(at=0.0, data=None)
    return top


_season_moves: dict = {'week': 0, 'prev': {}, 'list': []}


def _season_race(week, board, now):
    """Rank changes since the last background build → the Arena race ticker; a card entering or leaving the top 3 alerts
    its owner once (per card, week and direction)."""
    if _season_moves['week'] != week:
        _season_moves.update(week=week, prev={}, list=[])
    prev = _season_moves['prev']
    moves = _hq.rank_moves(prev, board) if prev else []
    _season_moves['list'] = (_season_moves['list'] + [{**m, 'at': now} for m in moves])[-30:]
    now_rank = {b['id']: b['rank'] for b in board}
    for b in board:
        was = prev.get(b['id']) if prev else None
        if prev and b['rank'] <= 3 and (was is None or was > 3):
            notify(b['wallet'], 'fuse-guard', f"🏆 Your card {b.get('name') or ''} just entered the Fuse season top 3 (#{b['rank']}, {b['pnlPct']:+.1f}%). Hold it to Monday 00:00 UTC.",
                   url='/terminal/fuse?tab=arena', once=f"top3-in-{week}-{b['id']}", meta={'claim': f"#{b['rank']} by real P&L this week", 'source': 'Fuse season'})
    if prev:
        for cid, was in prev.items():
            if was <= 3 and now_rank.get(cid, 99) > 3:
                own = next((b for b in board if b['id'] == cid), None)
                pos = own or next((x for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or [] if x['id'] == cid), None)
                if pos:
                    notify(pos['wallet'], 'fuse-guard', f"⚠ Your card dropped out of the Fuse season top 3 (now #{now_rank.get(cid, '10+')}). There's still time before Monday 00:00 UTC.",
                           url='/terminal/fuse?tab=arena', once=f"top3-out-{week}-{cid}-{int(now // 3600)}", meta={'claim': 'Rank fell below #3', 'source': 'Fuse season'})
    _season_moves['prev'] = now_rank


_replay_cache: dict = {}


async def _series_24h(pair):
    """Last 24h of 15m closes for one pool (candles service), [[t, close], …]. 60s cache."""
    hit = _replay_cache.get(pair)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=6) as http:
            cs = (await http.get(f'http://127.0.0.1:5099/api/candles/solana/{pair}', params={'interval': '15m'})).json().get('candles') or []
    except Exception:
        cs = []
    since = time.time() - 86400
    out = [[int(c[0]), c[4]] for c in cs if c and c[0] >= since and c[4]]
    _replay_cache[pair] = (time.time(), out)
    return out


@app.get('/api/reputation/fuses/replay/{kind}/{cid}')
async def fuse_replay(kind: str, cid: str):
    """▶ Card replay: each coin's last 24h path (15m) + the card's moments (buys, take-profits, swaps, compounds) as markers."""
    now = time.time(); legs, marks = [], []
    if kind == 'user':
        pos = next((x for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or [] if x['id'] == cid), None)
        if not pos:
            raise HTTPException(404, 'No such card.')
        legs = [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'entry': round(_fuse._f(l.get('usd')) / _fuse._f(l.get('tokens0') or l.get('tokens')), 12) if _fuse._f(l.get('tokens0') or l.get('tokens')) else None,
                 'at': l.get('addedAt') or pos.get('at')} for l in pos['legs']]
        marks = [{'at': e.get('at'), 'kind': e.get('kind'), 'label': f"{e.get('kind')} {e.get('symbol') or ''}".strip()} for e in pos.get('events') or [] if e.get('at')]
        marks.insert(0, {'at': pos.get('at'), 'kind': 'open', 'label': 'card opened'})
    elif kind in ('lit', 'round'):
        rd = _json_load(RUNNERS_PATH, {'rounds': []})
        c = next((x for x in (rd.get('litCards') or []) + (rd.get('rounds') or []) if str(x.get('id')) == cid), None)
        if not c:
            raise HTTPException(404, 'No such card.')
        legs = [{'pairAddress': p.get('pairAddress') or p['mint'], 'symbol': p.get('symbol'), 'entry': p.get('entry'), 'at': p.get('swappedIn') or c['at']} for p in c['picks']]
        marks = [{'at': c['at'], 'kind': 'open', 'label': 'lit' if kind == 'lit' else 'round dealt'}] + [{'at': s['at'], 'kind': 'swap', 'label': f"swap ${s['out'].get('symbol')} → ${s['in'].get('symbol')}"} for s in c.get('swaps') or []]
    elif kind == 'mega':
        f = (_json_load(FUSES_PATH, {'fuses': {}}).get('fuses') or {}).get(cid)
        if not f:
            raise HTTPException(404, 'No such card.')
        legs = [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'entry': (f.get('basePrices') or {}).get(l['pairAddress']), 'at': f.get('createdAt')} for l in f['legs']]
    elif kind == 'auto':
        ac = _json_load(RUNNERS_PATH, {}).get('autoCard') or {}
        if cid not in (ac.get('id'), 'arena-pick'):
            raise HTTPException(404, 'No such card.')
        legs = [{k: l.get(k) for k in ('pairAddress', 'symbol', 'entry')} | {'at': ac['at']} for l in ac['legs']]
        marks = [{'at': ac['at'], 'kind': 'open', 'label': 'arena dealt it'}]
    elif kind == 'feecat':
        fc = await _feecat_card()
        legs = [{k: l.get(k) for k in ('pairAddress', 'symbol', 'entry', 'at')} for l in (fc or {}).get('legs') or []]
        marks = [{'at': l['at'], 'kind': 'buy', 'label': f"🐱 bought ${l['symbol']}"} for l in legs if l.get('at')]
    else:
        raise HTTPException(400, 'Unknown card kind.')
    legs = legs[:12]
    series = await asyncio.gather(*[_series_24h(l['pairAddress']) for l in legs])
    return {'from': now - 86400, 'to': now, 'legs': [{**l, 'series': s} for l, s in zip(legs, series)],
            'markers': [m for m in marks if _fuse._f(m.get('at')) >= now - 86400]}


@app.get('/api/reputation/fuses/season')
async def fuse_season():
    """This week's live Fuse season board (top 10) + the last 4 crowned weeks. 60s cache, warmed in the background."""
    now = time.time()
    if _fuse_season_cache['data'] and now - _fuse_season_cache['at'] < 60 and not _FUSE_FORCE.get():
        return _fuse_season_cache['data']
    start = _hq.season_start(now)
    rows, bots = await _season_rows(start, start + _hq.WEEK)
    board = [{**b, 'handle': handle_of(b['wallet']) or f"{b['wallet'][:4]}…{b['wallet'][-4:]}"} for b in _hq.season_board(rows, start, start + _hq.WEEK, bots)[:10]]
    cat = await _feecat_raw()
    cat_pct = _hq.feecat_week_pct((cat or {}).get('exits'), (cat or {}).get('positions'), start, start + _hq.WEEK) if cat else None
    beat = set(_hq.beats_cat(board, cat_pct))
    board = [{**b, 'beatsCat': b['id'] in beat} for b in board]
    if _FUSE_FORCE.get():   # background only: the race ticker + top-3 alerts (viewers never trigger them)
        _season_race(start, board, now)
    season = {**QUEST_SEASON_DEFAULT, **(_json_load(QUESTS_PATH, {}).get('season') or {})}
    hq_ = _json_load(FUSE_HQ_PATH, {})
    data = {'week': start, 'endsAt': start + _hq.WEEK, 'cards': len(rows), 'board': board, 'seasonName': season.get('name'), 'feecat': {'pct': cat_pct, 'winPts': _hq.CAT_WIN_PTS}, 'boostPct': _card_rules()['seasonBoostPct'], 'moves': list(_season_moves['list'])[-12:],
            'past': list(reversed((_json_load(FUSE_HQ_PATH, {}).get('seasons') or [])[-4:])), 'at': now,
            'backers': {'board': [{**r, 'handle': handle_of(r['wallet']) or f"{r['wallet'][:4]}…{r['wallet'][-4:]}"} for r in _hq.backer_board(
                hq_.get('backLog'), hq_.get('backWins'), start, start + _hq.WEEK, _protected_wallets())[:5]],
                        'poolUsd': _card_rules().get('backerPoolUsd', 0), 'split': list(_hq.BACKER_SPLIT), 'minBacks': _hq.BACKER_MIN_BACKS}}
    _fuse_season_cache.update(at=now, data=data)
    return data


_fuse_score_cache: dict = {}


async def _fuse_score(address, fresh=False):
    """⚛️ Fuse score for a wallet (2 min cache): real card P&L, medals, copies, streaks, holding + reputation."""
    a = primary_of(address)
    hit = _fuse_score_cache.get(a)
    if hit and not fresh and time.time() - hit[0] < 120:
        return hit[1]
    mine = set(linked_of(a)) | {a}
    allp = _json_load(FUSE_HQ_PATH, {}).get('positions') or []
    pos = [x for x in allp if x['wallet'] in mine]
    px = await _hq_prices([leg for x in pos for leg in x['legs'] if leg.get('soldUsd') is None]) if pos else {}
    now = time.time()
    rows = []
    for x in pos:
        rr = _hq.position_pnl(x, px)
        rows.append({**rr, 'streak': _hq.swap_streak({**rr, 'events': x.get('events')}), 'compound': _hq.compound_streak({**rr, 'events': x.get('events')}),
                     'heldS': (x.get('closedAt') or now) - _fuse._f(x.get('at'))})
    ids = {x['id'] for x in pos}
    wins = [w for cid, w in _season_wins().items() if cid in ids]
    copies = sum(1 for c in allp if c.get('copyOwner') in mine)
    tr = (_trust_cache.get(a) or (0, {}))[1].get('score')
    sh = await _shield_of(a)
    cat_wins = sum(1 for w in _json_load(FUSE_HQ_PATH, {}).get('catChallenge') or [] for cid in w.get('ids') or [] if cid in ids)
    rec = _json_load(FUSE_HQ_PATH, {}).get('battleRecord') or {}
    bat = {k: sum(int((rec.get(f'user:{cid}') or {}).get(k) or 0) for cid in ids) for k in ('w', 'l', 'd')}
    medals = {str(r): sum(1 for w in wins if w.get('rank') == r) for r in (1, 2, 3)}
    held = [r for r in rows if not r.get('closed')]
    out = {'address': a, **_hq.fuse_score(rows, wins, copies, tr, bot=sh.get('verdict') == 'bot', cat_wins=cat_wins),
           # Trader page (profile top): the record behind the score, every number from FEELESS's own Fuse records
           'trader': {'medals': medals, 'battles': bat, 'catWins': cat_wins, 'copies': copies, 'held': len(held),
                      'heldPnlUsd': round(sum(r['pnlUsd'] for r in held), 2), 'bestPct': round(max((r['pnlPct'] for r in rows), default=0.0), 2),
                      'closed': sum(1 for r in rows if r.get('closed'))}}
    _fuse_score_cache[a] = (time.time(), out)
    return out


@app.get('/api/reputation/fuses/score/{address}')
async def fuse_score_get(address: str):
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        raise HTTPException(400, 'Bad address.')
    return await _fuse_score(address)



_ids_warming: set = set()


@app.get('/api/reputation/fuses/ids')
async def fuse_ids(addrs: str = ''):
    """🪪 Trader chips (Arena, season board, chat): ⚛️ score + medals + battle W/L for up to 40 wallets, from the CACHE only so
    the chip never waits. Missing wallets warm in the background and show on the next poll."""
    want = [x for x in dict.fromkeys(addrs.split(',')) if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', x)][:40]
    out, cold = {}, []
    for w in want:
        hit = _fuse_score_cache.get(primary_of(w))
        if hit and time.time() - hit[0] < 900:
            v = hit[1]; t = v.get('trader') or {}
            out[w] = {'score': v.get('score'), 'medals': t.get('medals'), 'battles': t.get('battles'), 'catWins': t.get('catWins'), 'held': t.get('held')}
        elif w not in _ids_warming:
            cold.append(w)
    if cold:
        _ids_warming.update(cold)

        async def warm():
            try:
                await asyncio.gather(*[_fuse_score(w) for w in cold], return_exceptions=True)
            finally:
                _ids_warming.difference_update(cold)
        asyncio.create_task(warm())
    return {'ids': out}

async def _fuse_autopilot_tick(now=None):
    """Hourly: settle due arena runs, then enter each strategy's current champion ($5 paper, 3 pools) once per hour —
    the arena proves strategies on its own. Then alert HQ about wallets newly flagged as bots."""
    now = now or time.time()
    await _fuse_season_tick(now)
    await _arena_settle(now=now)
    arena = _json_load(FUSE_HQ_PATH, {}).get('arena') or []
    dead = _retired(_hq.arena_board([_hq.arena_value(e, {}, now) for e in arena]))   # ☠ losers: one probe a day, not hourly
    styles = [st for st in _fuse.STYLES if _hq.autopilot_due(arena, st, now, retired=dead)]
    if styles:
        metas, sol_usd = await asyncio.gather(_fuse_candidates(), _sol_usd_live())
        if len(metas) >= 3:
            runs = await asyncio.gather(*[asyncio.to_thread(_fuse.evolve, metas, 3, 14, 28, st, 5 / sol_usd, sol_usd, int(now // 3600)) for st in styles])
            champs = [(st, _champ_view(ev['champions'][0], metas)) for st, ev in zip(styles, runs) if ev['champions']]
            prices = await _hq_prices([leg for _, c in champs for leg in c['legs']])
            async with _admin_lock:
                d = _json_load(FUSE_HQ_PATH, {})
                for st, c in champs:
                    if _hq.autopilot_due(d.get('arena') or [], st, now, retired=dead):
                        d['arena'] = ((d.get('arena') or []) + [{**_hq.arena_entry(c, st, prices, now, uuid.uuid4().hex[:10]), 'auto': True}])[-300:]
                _json_save(FUSE_HQ_PATH, d)
    await _shield_alerts()


async def _shield_alerts():
    """Bot shield → HQ inbox: each wallet newly judged 'bot' is reported once to every admin wallet (cited)."""
    rows = _shield_scan_all()
    d = _json_load(SHIELD_PATH, {})
    told = set(d.get('alerted') or [])
    new = [r for r in rows if r['verdict'] == 'bot' and not r.get('manual') and r['address'] not in told]
    for r in new[:20]:
        claim = r['hits'][0]['evidence'][0] if r['hits'] else {'claim': r['why'], 'source': 'Bot shield'}
        for adm in _admin_wallets():
            notify(adm, 'shield', f"🛡 Bot shield flagged {r['address'][:4]}…{r['address'][-4:]} ({r['score']}): {claim['claim']}",
                   url='/terminal/command', once=f"shield-{r['address']}", meta={'claim': claim['claim'], 'source': claim['source']}, push=False)
        told.add(r['address'])
    if new:
        d['alerted'] = sorted(told)[-5000:]
        _json_save(SHIELD_PATH, d)
    return len(new)


async def _fuse_autopilot_loop():
    await asyncio.sleep(90)
    while True:
        try:
            await _fuse_autopilot_tick()
        except Exception as e:
            print('fuse autopilot:', e)
        await asyncio.sleep(_hq.AUTOPILOT_EVERY)


@app.on_event('startup')
async def _fuse_autopilot_start():
    if not os.environ.get('PYTEST_CURRENT_TEST'):
        asyncio.create_task(_fuse_autopilot_loop())


def _card_look(body, prev):
    """A published card's look + configs (engine scenario cards): dial safe|balanced|degen, TP/SL/rotate/stop-mode chips."""
    dial = body.get('dial', prev.get('dial', ''))
    cfg = body.get('cfg') if isinstance(body.get('cfg'), dict) else prev.get('cfg')
    out = {'dial': dial if dial in _rn.CARD_NAMES else ''}
    if cfg:
        out['cfg'] = {'tp': max(0, min(5000, int(_fuse._f(cfg.get('tp'))))), 'sl': max(0, min(95, int(_fuse._f(cfg.get('sl'))))), 'window': str(cfg.get('window') or '')[:6],
                      'rotateHours': max(0.08, min(48, _fuse._f(cfg.get('rotateHours')) or 24)), 'slMode': cfg.get('slMode') if cfg.get('slMode') in ('sell', 'park', 'hold') else 'sell'}
    if body.get('fromScenario') or prev.get('fromScenario'):
        out['fromScenario'] = str(body.get('fromScenario') or prev.get('fromScenario'))[:40]
    return out


@app.get('/api/reputation/fuses/arena')
async def fuse_arena_public():
    """Fuse 🧬 › Arena for everyone: strategies' settled paper runs, the honest outlook, and the Runners proof — no admin data."""
    d = _json_load(FUSE_HQ_PATH, {})
    now = time.time()
    vals = [_hq.arena_value(e, {}, now) for e in d.get('arena') or []]
    board = _hq.arena_board(vals)
    rd = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
    cfg = _runner_cfg()
    rounds = []
    for r in rd['rounds'][-24:]:
        mults = [_rn.play_exits(p['lane'], p['entry'], [x for t, x in rd['paths'].get(p['mint'], []) if t > r['at']], cfg) for p in r['picks']]
        if mults:
            rounds.append({'at': r['at'], 'symbols': [p.get('symbol') for p in r['picks']], 'pct': round((sum(mults) / len(mults) - 1) * 100, 2)})
    mega = await _arena_mega(rd, cfg, now)
    return {'board': board, 'outlook': _hq.outlook(board), 'bestStyle': _hq.best_style(board), 'runs': [v for v in sorted(vals, key=lambda v: -v['at']) if v['settled']][:12],
            'runners': {'proof': _rn.proof(rd['rounds'], rd['paths'], now, cfg=cfg), 'rounds': rounds}, 'minSettled': _hq.MIN_SETTLED,
            'mega': [c for c in mega if not c.get('bench') and not c.get('fighterOnly')], 'bench': [c for c in mega if c.get('bench')], 'fighters': [c for c in mega if c.get('fighterOnly')] + _league_extra(mega),
            'battles': _battle_view(mega, now),
            # 🎚 auto paper cards per Risk dial: every round also played with each dial's TP/SL — proves a dial BEFORE it goes auto live
            'dials': {k: {**v, 'label': _hq.RISK_DIALS[k]['label'], 'why': _hq.RISK_DIALS[k]['why']} for k, v in _rn.dial_proof(rd['rounds'], rd['paths'], now, _hq.RISK_DIALS).items()},
            'engineDial': rd.get('cfgDial') or 'custom'}


_arena_mega_cache: dict = {'at': 0.0, 'data': None}


FUSE_ARENA_NAME = '⚔ Fuse Arena'


def _fuse_chat(room, text, key, tokens=None):
    """Fuse moments into chat — battle results, bond runs, FeeCat's book, season crowns. Once per key (kept 2 days)."""
    d = _json_load(FUSE_HQ_PATH, {})
    posted = d.get('chatPosted') or {}
    if key in posted:
        return None
    msg = chat_system_post(room, FUSE_ARENA_NAME, FEE_ADDRESS, text[:600], tokens=tokens)
    now = time.time()
    d['chatPosted'] = {k: v for k, v in {**posted, key: now}.items() if now - v < 2 * 86400}
    _json_save(FUSE_HQ_PATH, d)
    return msg


def _fuse_chat_tick(now):
    """Background: 🔔 new bond runs → the coin's own room + fuse-lab; 🐱 FeeCat book changes → fuse-lab."""
    live = _runner_live_cache.get('data') or {}
    for r in live.get('passing') or []:
        if r.get('bondTier') == 'run' and r.get('pairAddress'):
            txt = f"🔔 BOND RUN: ${r.get('symbol')} ticked every box at {_fuse._f(r.get('curve')):.0f}% up the curve — {r.get('buyShare')}% buys, curve +{_fuse._f(r.get('curveSpeed')):.0f} pts in 10m. Gated, not a promise."
            tok = [{'chainId': 'solana', 'pairAddress': r['pairAddress'], 'baseToken': {'address': r['mint'], 'symbol': r.get('symbol'), 'name': r.get('name') or r.get('symbol')},
                    'priceUsd': r.get('price'), 'marketCap': r.get('mcap'), 'volume': {'h1': r.get('vol1h')}, 'info': {'imageUrl': r.get('logo')},
                    'signals': {'score_label': f"🔔 Bond run · score {round(_fuse._f(r.get('score')))}", 'score_reasons': [f"{_fuse._f(r.get('curve')):.0f}% up the curve", f"{r.get('buyShare')}% buys", 'gated by Fuse runners']}}]
            _fuse_chat(f"coin-solana-{r['pairAddress']}-trenches", txt, f"bond-{r['mint']}-{int(now // 21600)}", tok)
            _fuse_chat('fuse-lab', txt, f"bond-lab-{r['mint']}-{int(now // 21600)}", tok)
    fc = next((c for c in _arena_mega_cache.get('data') or [] if c.get('kind') == 'feecat'), None)
    if fc:
        syms = sorted(l.get('symbol') or '?' for l in fc['legs'])
        _fuse_chat('fuse-lab', f"🐱 FeeCat's book now: {' · '.join('$' + s for s in syms)} ({(fc['index'] or 100) - 100:+.1f}% sim, {fc['record'].get('winRate')}% wins). Beat her this week for +8 Fuse score.",
                   f"feecat-book-{'-'.join(syms)}")


def _battle_view(mega, now):
    """⚔ Live battlefield: each pair with both cards' move since the bell (live from the stage), time left, recent results."""
    b = _json_load(FUSE_HQ_PATH, {}).get('battles') or {}
    pct = {f"{c['kind']}:{c['id']}": (c['index'] or 100) - 100 for c in mega}
    backs = list((b.get('backs') or {}).values()); paid = list((b.get('paid') or {}).values())
    paper = b.get('paper') or {}
    pnow = lambda k, start, bs=0.0: round(paper[k]['pct'] - bs, 2) if (paper.get(k) or {}).get('pct') is not None else round(pct.get(k, start) - start, 2)   # THIS bell's move on the season book
    pairs = [{side: {**x[side], 'now': pnow(x[side]['key'], x[side]['start'], _fuse._f(x[side].get('bookStart'))), 'paper': {kk: (paper.get(x[side]['key']) or {}).get(kk) for kk in ('startUsd', 'valueUsd', 'feesUsd', 'hiPct', 'loPct')} if paper.get(x[side]['key']) else None,
                     'frames': {str(m): _pgb.frame_pct(paper.get(x[side]['key']), now, m) for m in _pgb.FRAMES} if paper.get(x[side]['key']) else None,
                     'spark': [round(v - _fuse._f(x[side].get('bookStart')), 2) for v in _pgb.spark(paper.get(x[side]['key']), b.get('at'))],   # 📈 the race line: % since the bell, 1 point a minute
                     'backers': backs.count(x[side]['key']),
                     'paidN': sum(1 for q in paid if q['key'] == x[side]['key']), 'paidUsd': round(sum(q['usd'] for q in paid if q['key'] == x[side]['key']), 2)} for side in ('a', 'b')}
             for x in b.get('pairs') or []]
    for i, x in enumerate(b.get('pairs') or []):   # ⚡ the game's live scoreboard: six coin-vs-coin duels since the bell
        bell_a, bell_b = x['a'].get('bellPx'), x['b'].get('bellPx')
        pairs[i]['duels'] = _pgb.duels(paper.get(x['a']['key']), paper.get(x['b']['key']), bell_a, bell_b) if bell_a and bell_b else None
        for side in ('a', 'b'):
            pairs[i][side].pop('bellPx', None)
    br = _json_load(FUSE_HQ_PATH, {}).get('bracket') or {}
    bc = br.get('cards') or {}
    cbs = _json_load(FUSE_HQ_PATH, {}).get('comebacks') or {}
    board = []
    for c in _rn.unique_cards(mega):
        k = f"{c['kind']}:{c['id']}"; r = bc.get(k) or {'w': 0, 'l': 0}
        board.append({'key': k, 'comebacks': int(cbs.get(k) or 0), 'name': c.get('name') or 'Card', 'emoji': c.get('emoji'), 'dial': c.get('dial'), 'w': r.get('w', 0), 'l': r.get('l', 0),
                      'pct': round((c.get('index') or 100) - 100, 2), 'status': 'winners' if r.get('l', 0) == 0 else 'losers' if r.get('l', 0) == 1 else 'out'})
    board.sort(key=lambda x: ({'winners': 0, 'losers': 1, 'out': 2}[x['status']], -x['w'], -x['pct']))
    lg_ = _json_load(FUSE_HQ_PATH, {}).get('league') or None
    league_view = None
    if lg_:   # 🏆 the league table IS the board: points, W-D-L, the season book's $ (started at $20)
        t_ = _lg.table(lg_); half = max(1, len(t_) // 2)
        board = [{'key': r['key'], 'name': r['name'], 'emoji': r.get('emoji'), 'w': r['w'], 'd': r['d'], 'l': r['l'], 'pts': r['pts'], 'rank': i + 1,
                  'usd': _fuse._f((paper.get(r['key']) or {}).get('valueUsd')) or _fuse._f((r.get('hist') or [_lg.START_USD])[-1]),
                  'pct': _fuse._f((paper.get(r['key']) or {}).get('pct')), 'comebacks': int(cbs.get(r['key']) or 0), 'src': r.get('src'),
                  'status': 'winners' if i < half else 'losers'} for i, r in enumerate(t_)]
        league_view = {'n': lg_['n'], 'round': lg_.get('round', 0), 'rounds': lg_.get('rounds', _lg.ROUNDS), 'startUsd': _lg.START_USD, 'fieldMax': _lg.FIELD_MAX,
                       'cycled': (lg_.get('cycled') or [])[-6:][::-1], 'cut': {'usd': _lg.CUT_USD, 'dropPct': _lg.CUT_DROP, 'bells': _lg.CUT_BELLS}}
    fighting = {p_[s_]['key'] for p_ in pairs for s_ in ('a', 'b')}
    calls = list((br.get('picks') or {}).values())
    for x in board:
        x['calls'] = calls.count(x['key'])
    up_next = [] if league_view else [x for x in board if x['status'] != 'out' and x['key'] not in fighting][:3]
    return {'pairs': pairs, 'league': league_view, 'endsAt': b.get('endsAt'), 'log': (_json_load(FUSE_HQ_PATH, {}).get('battleLog') or [])[-8:][::-1],
            'bracket': {'board': board, 'season': br.get('season') or 1, 'champions': list(reversed(br.get('champions') or []))[:5], 'upNext': up_next, 'calls': len(calls)}, 'max': _rn.BATTLE_MAX}


@app.get('/api/reputation/fuses/paper')
async def fuse_paper(key: str = Query(..., max_length=120)):
    """📜 A card's Arena paper audit: its live battle book (entries at true fills → now, fees apart) + its finished books."""
    d = _json_load(FUSE_HQ_PATH, {})
    live = ((d.get('battles') or {}).get('paper') or {}).get(key)
    view = None
    if live:
        pairs_ = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in live.get('legs') or []])
        view = _pgb.paper_view(live, {k: _fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}, {k: _fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_.items()})
    past = [x for x in reversed(d.get('paperLog') or []) if x.get('key') == key][:10]
    rec = {'won': sum(1 for x in past if x.get('result') == 'won'), 'lost': sum(1 for x in past if x.get('result') == 'lost'),
           'pnlUsd': round(sum(_fuse._f(x.get('pnlUsd')) for x in past), 4), 'feesUsd': round(sum(_fuse._f(x.get('feesUsd')) for x in past), 4)}
    return {'live': view, 'past': past, 'record': rec}


@app.get('/api/reputation/fuses/battles/{address}')
async def fuse_my_battles(address: str):
    """⚔ A wallet's cards in Arena battles: the live ones (with both sides' move since the bell) + the last results."""
    me = primary_of(address); mine = set(linked_of(me)) | {me}
    d = _json_load(FUSE_HQ_PATH, {})
    keys = {f"user:{x['id']}": x.get('name') or 'Fuse card' for x in d.get('positions') or [] if x['wallet'] in mine}
    view = _battle_view(_arena_mega_cache.get('data') or [], time.time())
    live = [{**p_, 'mine': 'a' if p_['a']['key'] in keys else 'b'} for p_ in view['pairs'] if p_['a']['key'] in keys or p_['b']['key'] in keys]
    past = [{**r, 'mine': 'a' if r.get('aKey') in keys else 'b', 'won': r.get('winnerKey') in keys} for r in reversed(d.get('battleLog') or [])
            if r.get('aKey') in keys or r.get('bKey') in keys][:20]
    rec = {'w': sum(1 for r in past if r['won']), 'l': sum(1 for r in past if not r['won'] and not r.get('draw')), 'd': sum(1 for r in past if r.get('draw'))}
    return {'live': live, 'past': past, 'record': rec, 'endsAt': view.get('endsAt'), 'cards': len(keys)}


class BracketPick(BaseModel):
    address: str
    session: str
    key: str = Field(..., max_length=120)


@app.post('/api/reputation/fuses/bracket/pick')
async def bracket_pick(p: BracketPick):
    """🔮 Call the bracket champion — free, one call per wallet per bracket, locked once made. Right = season XP + inbox."""
    me = _session_or_401(p.address, p.session)
    keys = {f"{c['kind']}:{c['id']}" for c in _rn.unique_cards(_arena_mega_cache.get('data') or [])}
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {}); br = d.setdefault('bracket', {})
        if p.key not in keys or int(((br.get('cards') or {}).get(p.key) or {}).get('l') or 0) >= 2:
            raise HTTPException(400, 'That card is not standing in this bracket.')
        picks = br.setdefault('picks', {})
        if me in picks:
            raise HTTPException(409, 'You already called this bracket.')
        picks[me] = p.key; _json_save(FUSE_HQ_PATH, d)
    return {'ok': True, 'key': p.key, 'season': br.get('season') or 1}


class BattleBack(BaseModel):
    address: str
    session: str
    key: str = Field(..., max_length=120)


@app.post('/api/reputation/fuses/battle/back')
async def battle_back(p: BattleBack):
    """⚔ Back a side in the live battle — free, points only (no money). One pick per wallet per battle, locked once made."""
    me = _session_or_401(p.address, p.session)
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {}); b = d.get('battles') or {}
        if not any(p.key in (x['a']['key'], x['b']['key']) for x in b.get('pairs') or []):
            raise HTTPException(400, 'That card is not in the current battle.')
        backs = b.setdefault('backs', {})
        if me in backs:
            raise HTTPException(409, 'You already backed a side this battle.')
        backs[me] = p.key; d['battles'] = b
        d.setdefault('backLog', {})[me] = ((d.get('backLog') or {}).get(me) or [])[-199:] + [time.time()]
        _json_save(FUSE_HQ_PATH, d)
    rec = (_json_load(FUSE_HQ_PATH, {}).get('backRecord') or {}).get(me) or {'w': 0, 'l': 0}
    return {'ok': True, 'key': p.key, 'record': rec}


import arena_league as _lg


def _league_card(d, key, mega):
    """The coins a fighter plays: its league seat (playground cards live only there), else its live Arena card."""
    r = next((x for x in ((d.get('league') or {}).get('field') or []) if x['key'] == key), None)
    return r or next((c for c in mega if f"{c['kind']}:{c['id']}" == key), None)


def _league_extra(mega):
    """League seats that aren't live Arena cards (cycled-in playground cards) as cards the Pit can draw in its corners."""
    have = {f"{c['kind']}:{c['id']}" for c in mega}
    out = []
    for r in ((_json_load(FUSE_HQ_PATH, {}).get('league') or {}).get('field') or []):
        if r['key'] not in have and ':' in r['key']:
            kind, cid = r['key'].split(':', 1)
            out.append({'kind': kind, 'id': cid, 'name': r['name'], 'emoji': r.get('emoji'), 'legs': r.get('legs') or [], 'fighterOnly': True, 'league': True,
                        'activity': {'tier': 'warm', 'score': 30}})
    return out


def _league_playground():
    """Fresh engine-playground cards for the league (cycled-in seats + filling a thin field): the HQ battle field, best record first."""
    pg = (_json_load(RUNNERS_PATH, {}).get('pgBattle') or {})
    rec = pg.get('record') or {}
    cards = sorted((pg.get('cards') or {}).items(), key=lambda kv: -((rec.get(kv[0]) or {}).get('w', 0) - (rec.get(kv[0]) or {}).get('l', 0)))
    out = []
    for k, c in cards:
        legs = [{'pairAddress': l.get('pairAddress'), 'symbol': l.get('symbol'), 'baseAddress': l.get('mint'), 'weight': _fuse._f(l.get('usd')) or 1.0,
                 'runner': (l.get('role') or 'runner') == 'runner'} for l in c.get('legs') or [] if l.get('pairAddress')]
        if len(legs) >= 2:
            name = str(c.get('name') or k)
            out.append({'key': f"pg:{k}", 'name': name.split(' ', 1)[-1] if ' ' in name else name, 'emoji': name.split(' ', 1)[0] if ' ' in name else '🧪', 'legs': legs, 'src': 'playground'})
    return out


async def _battle_tick(now):
    """Background: when the bell rings, settle every pair (bigger move since the start wins), write W/L/D records, alert
    trader-card owners who won, then pair the stage again for the next round."""
    mega = _arena_mega_cache.get('data') or []
    d = _json_load(FUSE_HQ_PATH, {})
    b = d.get('battles') or {}
    # 📜 paper books: every fighting card is marked live at true fills (what selling it all would really pay)
    paper = dict(b.get('paper') or {})
    pairs_px = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for k in paper for l in paper[k].get('legs') or []] +
                                 [{'chainId': 'solana', 'pairAddress': l['pairAddress']} for r in ((d.get('league') or {}).get('field') or []) for l in r.get('legs') or [] if l.get('pairAddress')] +
                                 [{'chainId': 'solana', 'pairAddress': l['pairAddress']} for c in mega for l in c.get('legs') or [] if l.get('pairAddress')]) if (paper or mega) else {}
    ppx = {k: _fuse._f(v.get('priceUsd')) for k, v in pairs_px.items()}
    pliq = {k: _fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_px.items()}
    if b.get('pairs'):   # a fighter without a book (dealt before books existed / joined late) gets one now — both sides from the same moment
        fee_coin0 = _hq.clean_bundle(_fee_cfg().get('bundle'))['perLegUsd']
        for x in b['pairs']:
            if not all(paper.get(x[s_]['key']) for s_ in ('a', 'b')):
                for s_ in ('a', 'b'):
                    if paper.get(x[s_]['key']):
                        continue
                    cm = _league_card(d, x[s_]['key'], mega)
                    bk = _pgb.paper_book(x[s_]['key'], cm, ppx, pliq, now, _lg.START_USD, fee_coin0) if cm else None
                    if bk:
                        paper[x[s_]['key']] = bk
    if paper:
        paper = {k: _pgb.paper_mark(v, ppx, pliq, now) for k, v in paper.items()}
        async with _admin_lock:
            d0 = _json_load(FUSE_HQ_PATH, {}); bb = d0.get('battles') or {}
            if bb.get('at') == b.get('at'):
                bb['paper'] = paper; d0['battles'] = bb; _json_save(FUSE_HQ_PATH, d0)
        b = {**b, 'paper': paper}
    pct0 = {f"{c['kind']}:{c['id']}": (c['index'] or 100) - 100 for c in mega}
    if b.get('pairs'):   # 🔥 track each side's worst deficit this battle (a win from there is a comeback)
        low = dict(b.get('low') or {}); changed = False
        for x in b['pairs']:
            for s1, s2 in (('a', 'b'), ('b', 'a')):
                k1, k2 = x[s1]['key'], x[s2]['key']
                if k1 in pct0 and k2 in pct0:
                    dfc = (pct0[k2] - x[s2]['start']) - (pct0[k1] - x[s1]['start'])
                    if dfc > _fuse._f(low.get(k1)):
                        low[k1] = round(dfc, 2); changed = True
        if changed:
            async with _admin_lock:
                d0 = _json_load(FUSE_HQ_PATH, {}); bb = d0.get('battles') or {}
                if bb.get('at') == b.get('at'):
                    bb['low'] = low; d0['battles'] = bb; _json_save(FUSE_HQ_PATH, d0)
            b = {**b, 'low': low}
    if b.get('endsAt') and now < b['endsAt'] and b.get('pairs'):
        return None   # mid-battle — or nothing to pair yet (an empty field pairs as soon as 2 cards are on stage)
    pct = {f"{c['kind']}:{c['id']}": (c['index'] or 100) - 100 for c in mega}
    owners = {x['id']: x['wallet'] for x in d.get('positions') or []}
    results = []
    for x in b.get('pairs') or []:
        a, bb = x['a'], x['b']
        pa_, pb_ = paper.get(a['key']), paper.get(bb['key'])
        if pa_ and pb_ and pa_.get('pct') is not None and pb_.get('pct') is not None:   # settle on the season books: THIS bell's move
            ma, mb = pa_['pct'] - _fuse._f(a.get('bookStart')), pb_['pct'] - _fuse._f(bb.get('bookStart'))
            # ⚡ a game = six duels (coin vs the coin in its seat); level on sparks → the whole card's move, as before
            dl = _pgb.duels(pa_, pb_, a.get('bellPx'), bb.get('bellPx')) if a.get('bellPx') and bb.get('bellPx') else None
            w = _pgb.duel_winner(dl, ma, mb) if dl else _rn.settle_battle(0, ma, 0, mb)
            x['_sparks'] = [dl['a'], dl['b']] if dl else None
            pct[a['key']], pct[bb['key']] = a['start'] + ma, bb['start'] + mb
        elif a['key'] not in pct or bb['key'] not in pct:
            continue
        else:
            w = _rn.settle_battle(a['start'], pct[a['key']], bb['start'], pct[bb['key']])
        results.append({'at': now, 'a': a['name'], 'b': bb['name'], 'winner': {'a': a['name'], 'b': bb['name']}.get(w), 'draw': w == 'draw',
                        'winnerKey': {'a': a['key'], 'b': bb['key']}.get(w), 'aKey': a['key'], 'bKey': bb['key'],
                        'comeback': w in ('a', 'b') and _fuse._f((b.get('low') or {}).get({'a': a['key'], 'b': bb['key']}[w])) >= _hq.COMEBACK_PTS,
                        'aMove': round(pct[a['key']] - a['start'], 2), 'bMove': round(pct[bb['key']] - bb['start'], 2),
                        **({'sparks': x['_sparks']} if x.get('_sparks') else {})})
        for side, key in (('a', a['key']), ('b', bb['key'])):
            r_ = d.setdefault('battleRecord', {}).setdefault(key, {'w': 0, 'l': 0, 'd': 0})
            r_['d' if w == 'draw' else 'w' if w == side else 'l'] += 1
            if w == side and key.startswith('user:') and key[5:] in owners:
                notify(owners[key[5:]], 'fuse-guard', f"⚔ Your card won its Arena battle vs {(bb if side == 'a' else a)['name']}.", url='/terminal/fuse?tab=arena',
                       once=f"battle-{now:.0f}-{key}", meta={'claim': 'Bigger move since the bell', 'source': 'Arena battles'})
    for r_ in results:   # 🔥 comebacks: badge count + chat callout + the owner's inbox
        if r_.get('comeback'):
            d.setdefault('comebacks', {})[r_['winnerKey']] = int((d.get('comebacks') or {}).get(r_['winnerKey']) or 0) + 1
            _fuse_chat('fuse-lab', f"🔥 COMEBACK: {r_['winner']} was down {(b.get('low') or {}).get(r_['winnerKey'])} pts (HP under 20) and still won.", f"comeback-{int(now)}-{r_['winnerKey']}")
            if r_['winnerKey'].startswith('user:') and r_['winnerKey'][5:] in owners:
                notify(owners[r_['winnerKey'][5:]], 'fuse-card', f"🔥 Comeback! Your card {r_['winner']} won from under 20 HP.", url='/terminal/fuse?tab=arena', once=f"cb-{int(now)}-{r_['winnerKey']}",
                       meta={'claim': 'Won after trailing ≥ 13 pts', 'source': 'Arena battles'})
    # backers: a pick on the winning card is a ✓ on the wallet's backing record (+ inbox); a draw counts for nobody
    won = {x['winnerKey'] for x in results if x.get('winnerKey')}; fought = {k for x in b.get('pairs') or [] for k in (x['a']['key'], x['b']['key'])}
    for w_, key in (b.get('backs') or {}).items():
        if key not in fought or key not in pct:
            continue
        rr_ = d.setdefault('backRecord', {}).setdefault(w_, {'w': 0, 'l': 0})
        if key in won:
            rr_['w'] += 1
            d.setdefault('backWins', {})[w_] = ((d.get('backWins') or {}).get(w_) or [])[-199:] + [now]
            notify(w_, 'fuse-card', f"⚔ You backed the winner — your backing record is {rr_['w']}–{rr_['l']}.", url='/terminal/fuse?tab=arena', once=f"back-{int(now)}-{w_}",
                   meta={'claim': 'Bigger move since the bell', 'source': 'Arena battles'})
        elif not any(x.get('draw') and key in (x.get('aKey'), x.get('bKey')) for x in results):
            rr_['l'] += 1
    for pid, q in (b.get('paid') or {}).items():   # 💰 bought-to-back: the buyer owns the card — tell them it won (no P&L in notices)
        if q['key'] in won:
            notify(q['wallet'], 'fuse-card', '💰 The card you bought to back won its battle.', url=f"/terminal/fuse?tab=cards&card={pid}", once=f"paidback-{int(now)}-{pid}",
                   meta={'claim': 'Bigger move since the bell', 'source': 'Arena battles'})
    mins = _runner_cfg()['battleMins']
    # 🏆 LEAGUE (arena_league): a capped field on $20 season books, fixed rounds, a champion, then a fresh season
    fee_coin = _hq.clean_bundle(_fee_cfg().get('bundle'))['perLegUsd']
    owners_ = owners
    seeds = [{'key': f"{c['kind']}:{c['id']}", 'name': c['name'], 'emoji': c.get('emoji'), 'legs': c.get('legs') or [], 'src': c.get('kind')}
             for c in _rn.unique_cards(mega) if c.get('legs')]
    fresh = _league_playground()
    # 💵 real-money cards always have a seat (on top of the 8), whatever their clock or config — keyed by tier, never by config
    must_ = [f"{c['kind']}:{c['id']}" for c in mega if c.get('real') and c.get('legs')]
    seeds += [{'key': k_, 'name': c['name'], 'emoji': c.get('emoji'), 'legs': c.get('legs') or [], 'src': c.get('kind')}
              for c in mega if (k_ := f"{c['kind']}:{c['id']}") in must_ and k_ not in {x['key'] for x in seeds}]
    league = d.get('league') or None
    champs = list((d.get('bracket') or {}).get('champions') or [])
    cycled_now = []
    new_paper = dict(paper)
    if league and results:
        books = {k: _fuse._f(v.get('valueUsd')) for k, v in paper.items()}
        league = _lg.settle(league, results, books)
        league, cycled_now = _lg.cycle(league, fresh, now)
        for m in cycled_now:
            new_paper.pop(m['outKey'], None)
            _fuse_chat('fuse-lab', f"♻ {m['out']} cycled out ({m['why']}){' — ' + m['in'] + ' takes its seat on $20' if m.get('in') else ''}.", f"cycle-{int(now)}-{m['outKey']}")
    if not league or _lg.done(league) or len(league.get('field') or []) < 2:
        if league and _lg.done(league):   # 👑 season over: the table decides
            ch = _lg.champion(league)
            if ch:
                champs = (champs + [{'at': now, 'key': ch['key'], 'name': ch['name'], 'emoji': ch.get('emoji'), 'w': ch['w'], 'pts': ch['pts'], 'season': league['n'],
                                     'usd': (ch.get('hist') or [0])[-1], 'legs': [{k_: l.get(k_) for k_ in ('pairAddress', 'symbol', 'baseAddress', 'weight', 'runner')} for l in ch.get('legs') or []][:12]}])[-12:]
                _fuse_chat('fuse-lab', f"👑 Arena season #{league['n']} champion: {ch.get('emoji') or ''} {ch['name']} — {ch['pts']} pts, $20 → ${_fuse._f((ch.get('hist') or [0])[-1]):.2f}. A new season starts on $20.", f"season-{league['n']}")
                for w_, k_ in ((d.get('bracket') or {}).get('picks') or {}).items():   # 🔮 called the champion → XP + inbox
                    if k_ == ch['key']:
                        d.setdefault('bracketWins', {})[w_] = ((d.get('bracketWins') or {}).get(w_) or [])[-49:] + [now]
                        notify(w_, 'fuse-card', f"🔮 You called it — {ch['name']} won Arena season #{league['n']}. Season XP added.", url='/terminal/fuse?tab=arena',
                               once=f"seasonpick-{league['n']}-{w_}", meta={'claim': 'Your call was the champion', 'source': 'Arena league'})
                if ch['key'].startswith('user:') and ch['key'][5:] in owners_:
                    notify(owners_[ch['key'][5:]], 'fuse-card', f"👑 Your card won Arena season #{league['n']}.", url='/terminal/fuse?tab=arena', once=f"champ-{league['n']}-{ch['key']}",
                           meta={'claim': 'Top of the league table', 'source': 'Arena league'})
        prev_n = int((league or {}).get('n') or int((d.get('bracket') or {}).get('season') or 0))
        played = bool(league and int(league.get('round') or 0) > 0)
        league = _lg.new_season(seeds + fresh, prev_n + 1 if (played or not league) else prev_n, now, must=must_)   # a field that never got going keeps its number
        new_paper = {}
    league, _ = _lg.ensure(league, seeds, must_, now)   # 💵 a real card always fights — funded mid-season it joins at once
    for r in league.get('field') or []:   # every seat has its season book ($20 at true fills) — dealt once, kept all season
        if not new_paper.get(r['key']):
            bk = _pgb.paper_book(r['key'], r, ppx, pliq, now, _lg.START_USD, fee_coin)
            if bk:
                new_paper[r['key']] = bk
    by_key = {r['key']: r for r in league.get('field') or []}
    pairs = [{'a': {'key': ka, 'name': by_key[ka]['name'], 'emoji': by_key[ka].get('emoji'), 'start': 0.0, 'bookStart': _fuse._f((new_paper.get(ka) or {}).get('pct')),
                    'bellPx': _pgb.seat_prices(new_paper.get(ka), ppx)},
              'b': {'key': kb, 'name': by_key[kb]['name'], 'emoji': by_key[kb].get('emoji'), 'start': 0.0, 'bookStart': _fuse._f((new_paper.get(kb) or {}).get('pct')),
                    'bellPx': _pgb.seat_prices(new_paper.get(kb), ppx)}}
             for ka, kb in _lg.pair_round(league) if new_paper.get(ka) and new_paper.get(kb)]
    t_ = _lg.table(league)
    bracket = {r['key']: {'w': r['w'], 'l': r['l']} for r in t_}
    season_n = league['n']
    done_books = [{**_pgb.paper_view(paper[k_], ppx, pliq), 'result': 'cycled out' if k_ in {m['outKey'] for m in cycled_now} else 'season over', 'endedAt': now}
                  for k_ in paper if k_ not in new_paper]   # a book closes only when its card leaves (cycled) or the season ends
    if results:
        _fuse_chat('fuse-lab', '⚔ Battle results: ' + ' · '.join(f"{'🤝 ' + x['a'] + ' = ' + x['b'] if x['draw'] else '🏆 ' + x['winner'] + ' beat ' + (x['b'] if x['winner'] == x['a'] else x['a'])} ({x['aMove']:+.1f}% vs {x['bMove']:+.1f}%)" for x in results[:4]),
                   f"battles-{int(now)}")
    async with _admin_lock:
        d2 = _json_load(FUSE_HQ_PATH, {})
        d2['battles'] = {'at': now, 'endsAt': now + mins * 60, 'pairs': pairs, 'paper': new_paper}
        d2['paperLog'] = ((d2.get('paperLog') or []) + done_books)[-60:]
        d2['battleLog'] = ((d2.get('battleLog') or []) + results)[-40:]
        d2['league'] = league
        d2['bracket'] = {'cards': bracket, 'champions': champs, 'season': season_n,
                         'picks': {} if league.get('round') == 0 else ((d2.get('bracket') or {}).get('picks') or {})}
        d2['bracketWins'] = {**(d2.get('bracketWins') or {}), **(d.get('bracketWins') or {})}
        d2['battleRecord'] = d.get('battleRecord') or {}
        d2['comebacks'] = d.get('comebacks') or d2.get('comebacks') or {}
        d2['backRecord'] = d.get('backRecord') or {}
        d2['backWins'] = {**(d2.get('backWins') or {}), **(d.get('backWins') or {})}
        _json_save(FUSE_HQ_PATH, d2)
    return results


async def _arena_auto_refresh(now):
    """Background: deal a fresh Arena build once per runner round (best gated coins + best live pools)."""
    rd = _json_load(RUNNERS_PATH, {'rounds': []})
    last = (rd.get('rounds') or [None])[-1]
    if not last or ((rd.get('autoCard') or {}).get('at') or 0) >= last['at']:
        return None
    live, pools = await asyncio.gather(_runner_live(), _fuse_candidates())
    rd_ = _json_load(RUNNERS_PATH, {})
    cfg_ = _runner_cfg()
    if rd_.get('sitOut'):   # 🩺 nothing wins → the Arena Pick sits out runners (pools only) until a filter proves itself
        cfg_ = {**cfg_, 'autoCoins': 0}
    card = _rn.auto_card(_rn.apply_filter(live['passing'], rd_.get('pickFilter'), cfg_.get('autoCoins') or 0), list(pools.values()), now, cfg_)
    if card:
        async with _admin_lock:
            rd = _json_load(RUNNERS_PATH, {'rounds': []}); rd['autoCard'] = card; _json_save(RUNNERS_PATH, rd)
    return card


async def _feecat_raw():
    try:
        async with httpx.AsyncClient(timeout=2.5) as http:
            c = (await http.get('http://127.0.0.1:5088/api/cats/leader')).json()
        return c.get('cat') or c
    except Exception:
        return None


async def _feecat_card():
    """🐱 FeeCat on the Arena: her open simulated book as one card (legs = her positions, entry = her fill), with her
    record, so traders can see whether her edge beats theirs. Never real money — labelled sim everywhere."""
    c = await _feecat_raw()
    if not c:
        return None
    ps = [p for p in c.get('positions') or [] if p.get('pairAddress')]
    if not ps:
        return None
    cost = sum(_fuse._f(p.get('costSol')) for p in ps) or 1.0
    pct = round(sum(_fuse._f(p.get('costSol')) * _fuse._f(p.get('currentChange')) for p in ps) / cost, 2)
    wr = _fuse._f(c.get('winRate'))
    act = _hq.activity(len(ps), 0, sum(_fuse._f(p.get('entryVolH1')) for p in ps) * 24, pct)
    return {'kind': 'feecat', 'id': 'feecat', 'name': f"{c.get('name') or 'FeeCat'}'s book", 'emoji': '🐱', 'aura': '', 'chat': 'fuse-card-feecat',
            'legs': [{'pairAddress': p['pairAddress'], 'symbol': p.get('symbol'), 'baseAddress': p.get('mint'), 'entry': _fuse._f(p.get('entryPriceUsd')),
                      'weight': round(_fuse._f(p.get('costSol')) / cost * 100, 2), 'at': p.get('openedAt')} for p in ps],
            'index': round(100 + pct, 2), 'grade': 'A' if wr >= 55 else 'B' if wr >= 45 else 'C', 'buyers': 0, 'activity': act,
            'record': {'winRate': round(wr), 'wins': c.get('wins'), 'losses': c.get('losses'), 'realizedSol': round(_fuse._f(c.get('realizedPnlSol')), 4),
                       'lives': (c.get('discipline') or {}).get('lives')}}


async def _arena_mega(rd, cfg, now):
    """Cards on the Arena stage: HQ mega cards (published Fuses flagged `arena`) + runner cards that lit after their
    rounds. Each carries its live activity (fuse_hq.activity → hard-coded effect tier). 30s cache, parallel lookups."""
    if _arena_mega_cache['data'] is not None and now - _arena_mega_cache['at'] < 40 and not _FUSE_FORCE.get():
        return _arena_mega_cache['data']
    store = _json_load(FUSES_PATH, {'fuses': {}})
    staged = sorted(((fid, f) for fid, f in (store.get('fuses') or {}).items() if f.get('arena') and f.get('enabled', True)), key=lambda x: -_fuse._f(x[1].get('createdAt')))[:8]   # newest first
    views = await asyncio.gather(*[_fuse_view(fid, f, store) for fid, f in staged], return_exceptions=True)
    out = []
    for v in views:
        if isinstance(v, BaseException):
            continue
        day = [b for b in store.get('buys', []) if b['fuse'] == v['id'] and now - _fuse._f(b.get('at')) < 86400]
        act = _hq.activity(len(day), len({b['wallet'] for b in day}), v['volume24h'], (v['index'] or 100) - 100)
        base = (store['fuses'].get(v['id']) or {}).get('basePrices') or {}
        out.append({'kind': 'mega', 'id': v['id'], 'name': v['name'], 'emoji': v['emoji'], 'aura': v.get('aura') or '', 'chat': f"fuse-card-{str(v['id']).lower()}",
                    'dial': v.get('dial') or '', 'cfg': v.get('cfg') or None, 'tagline': v.get('tagline') or '',
                    'legs': [{**l, 'base': base.get(l['pairAddress'])} for l in v['legs']],
                    'index': v['index'], 'grade': (v['score'] or {}).get('grade'), 'buyers': v['trust']['buyers'], 'activity': act})
    live = {r['mint']: r for r in (await _runner_live())['passing']}
    for c in [c for c in reversed(rd.get('litCards') or []) if not c.get('downAt')][:6]:
        pct = _rn.card_result(c, rd['paths'], now, cfg)
        flow = sum(_fuse._f(live.get(p['mint'], {}).get('vol1h')) * 24 for p in c['picks'])
        out.append({'kind': 'lit', 'id': c['id'], 'name': ' · '.join(f"${p.get('symbol')}" for p in c['picks'][:4]), 'emoji': '🔥', 'aura': '',
                    'legs': [{'pairAddress': p.get('pairAddress') or p['mint'], 'symbol': p.get('symbol'), 'baseAddress': p['mint'], 'logo': p.get('logo'),
                              'weight': round(100 / max(1, len(c['picks'])), 2), 'entry': p.get('entry')} for p in c['picks']], 'chat': f"fuse-card-{c['id']}",
                    'index': round(100 + pct, 2), 'grade': 'A' if pct > 0 else 'C', 'buyers': 0, 'at': c['at'], 'proof': c.get('proof'),
                    'streak': _hq.swap_streak({'events': [{'kind': 'buy'}] * len(c.get('swaps') or []), 'pnlPct': pct}), 'swaps': (c.get('swaps') or [])[-3:],
                    'activity': _hq.activity(0, 0, flow, pct)})
    # Traders' cards: every open card shows until it's withdrawn; one that's up ≥ topTierPct takes the top tier.
    hq_all = _json_load(FUSE_HQ_PATH, {}).get('positions') or []
    hq = [x for x in hq_all if not x.get('closedAt')]
    hq = sorted(hq, key=lambda x: -_fuse._f(x.get('at')))[:24]
    if hq:
        upx = await _hq_prices([leg for x in hq for leg in x['legs']])
        top = _card_rules()['topTierPct']
        for x in hq:
            rr = _hq.position_pnl(x, upx)
            if rr['closed']:
                continue
            stk = _hq.swap_streak({**rr, 'events': x.get('events')})
            cmp_ = _hq.compound_streak({**rr, 'events': x.get('events')})
            ncopy = sum(1 for c in hq_all if c.get('copyOf') == x['id'])
            act = _hq.activity(len(rr['legs']) + ncopy, 1 + ncopy, rr['valueUsd'] * 24, rr['pnlPct'])
            act = {**act, 'score': min(100, act['score'] + stk['bonus'] + cmp_['bonus'])}
            act['tier'] = next(tn for cut, tn in _hq.ACTIVITY_TIERS if act['score'] >= cut)
            if rr['pnlPct'] >= top:
                act = {'score': max(act['score'], 90), 'tier': 'blazing'}
            out.append({'kind': 'user', 'id': x['id'], 'name': x.get('name') or 'Fuse card', 'emoji': '🃏', 'aura': '', 'owner': handle_of(x['wallet']) or f"{x['wallet'][:4]}…{x['wallet'][-4:]}",
                        'legs': [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'baseAddress': l.get('mint'), 'weight': round(_fuse._f(l.get('usd')) / max(1e-9, rr['costUsd']) * 100, 2),
                                  'usd': l.get('usd'), 'tokens': l.get('tokens'), 'realizedUsd': l.get('realizedUsd'), 'soldUsd': l.get('soldUsd'), 'heldUsd': l.get('heldUsd'),
                                  'entry': (_fuse._f(l.get('usd')) / _fuse._f(l.get('tokens'))) if _fuse._f(l.get('tokens')) > 0 else None} for l in rr['legs']],   # true entry from the confirmed buy
                        'costUsd': rr['costUsd'], 'compound': cmp_, 'chat': f"fuse-card-{x['id']}",
                        'index': round(100 + rr['pnlPct'], 2), 'grade': 'A' if rr['pnlPct'] >= top else 'B' if rr['pnlPct'] >= 0 else 'C', 'buyers': 1, 'mode': x.get('mode') or 'hold',
                        'pnlPct': rr['pnlPct'], 'at': x.get('at'), 'activity': act, 'streak': stk, 'copies': ncopy, 'copyPct': _card_rules()['copyPct']})
    fc = await _feecat_card()
    if fc:
        out.append(fc)
    ac = rd.get('autoCard')
    if ac and ac.get('legs'):
        apx = await _hq_prices([l for l in ac['legs']])
        moves = [apx[l['pairAddress']] / l['entry'] for l in ac['legs'] if _fuse._f(apx.get(l['pairAddress'])) > 0 and _fuse._f(l.get('entry')) > 0]
        pct = round((sum(moves) / len(moves) - 1) * 100, 2) if moves else 0.0
        coins = sum(1 for l in ac['legs'] if l.get('runner'))
        out.append({'kind': 'auto', 'id': 'arena-pick', 'name': 'Arena Pick',   # stable id: its bracket record + chat survive each round's re-deal 'emoji': '⚔', 'aura': '', 'dial': 'degen' if coins >= 3 else 'balanced',
                    'tagline': f"{coins} coins + {len(ac['legs']) - coins} pools",
                    'legs': ac['legs'], 'index': round(100 + pct, 2), 'grade': 'A' if pct > 0 else 'B', 'buyers': 0, 'at': ac['at'], 'chat': f"fuse-card-{ac['id']}",
                    'activity': _hq.activity(len(ac['legs']), 0, sum(_fuse._f(l.get('vol1h')) for l in ac['legs']) * 24, pct)})
    published = {f.get('fromScenario') for f in (store.get('fuses') or {}).values() if f.get('arena') and f.get('fromScenario')}
    bench_names = set()
    for sc in rd.get('scenarioStage') or []:   # 🥈 runners-up: engine scenario cards waiting for HQ's audit (published ones show as mega)
        if sc.get('src') in published:
            continue
        spx = await _hq_prices([l for l in sc['legs']])
        mv_ = [spx[l['pairAddress']] / l['entry'] for l in sc['legs'] if _fuse._f(spx.get(l['pairAddress'])) > 0 and _fuse._f(l.get('entry')) > 0]
        pct_ = round((sum(m * _fuse._f(l['weight']) for m, l in zip(mv_, sc['legs'])) / max(1e-9, sum(_fuse._f(l['weight']) for l in sc['legs'][:len(mv_)])) - 1) * 100, 2) if mv_ else 0.0
        dial = sc.get('dial') or _rn.dial_of(sc['tp'], sc['sl'])
        own = f"{sc['emoji']} {sc['name']}" if sc.get('dial') and sc.get('emoji') else None
        nm_ = own if own and own not in bench_names else _rn.card_name(dial, sc['id'], bench_names)   # never two runners-up with one name
        bench_names.add(nm_)
        out.append({'kind': 'scenario', 'bench': True, 'id': sc['id'], 'src': sc.get('src'), 'version': sc.get('version'), 'name': nm_.split(' ', 1)[-1], 'emoji': nm_.split(' ', 1)[0], 'aura': '', 'legs': sc['legs'], 'index': round(100 + pct_, 2), 'dial': dial,
                    'cfg': sc.get('cfg') or _rn.card_cfg(dial, sc), 'grade': 'A' if pct_ > 0 else 'B', 'buyers': 0, 'at': sc['at'], 'chat': f"fuse-card-{sc['id']}", 'pnlPct': pct_,
                    'tagline': f"engine card · TP +{sc['tp']}% / stop −{sc['sl']}%",
                    'activity': _hq.activity(len(sc['legs']), 0, 0, pct_)})
    # 🏆 the engine's top battle winner is the ONE engine card that reaches the Arena by itself (HQ 🎨 picks the rest)
    pgb = rd.get('pgBattle') or {}
    champ_id = _pgb.champion(pgb.get('record'), pgb.get('cards'))
    if champ_id and champ_id not in set(rd.get('creatorPicks') or []):
        champ_id = None   # 🔒 HQ verifies every big engine card before it reaches the Arena (🎨 pick it in the playground)
    if champ_id and not any(x.get('src') == champ_id for x in out):
        cc = pgb['cards'][champ_id]; r_ = pgb['record'][champ_id]
        cpx = await _hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in cc['legs']])
        mv_ = [(_fuse._f(cpx.get(l['pairAddress'])) / l['entry'] - 1) * 100 for l in cc['legs'] if _fuse._f(cpx.get(l['pairAddress'])) > 0 and _fuse._f(l.get('entry')) > 0]
        pct_ = round(sum(mv_) / len(mv_), 2) if mv_ else 0.0
        nm_ = cc.get('name') or 'Engine champ'
        out.append({'kind': 'engine', 'bench': True, 'engineChamp': True, 'id': champ_id, 'src': champ_id, 'name': nm_.split(' ', 1)[-1], 'emoji': nm_.split(' ', 1)[0] if ' ' in nm_ else '🏆',
                    'legs': [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'baseAddress': l.get('mint'), 'weight': round(100 / max(1, len(cc['legs'])), 2), 'runner': l.get('role') == 'runner', 'entry': l.get('entry')} for l in cc['legs']],
                    'index': round(100 + pct_, 2), 'grade': 'A' if pct_ > 0 else 'B', 'buyers': 0, 'at': cc.get('at'), 'chat': f"fuse-card-{champ_id}", 'pnlPct': pct_, 'dial': cc.get('dial'),
                    'cfg': {'tp': int(_fuse._f(cc.get('tp'))), 'sl': int(_fuse._f(cc.get('sl'))), 'rotateHours': 1, 'slMode': 'sell'},
                    'tagline': f"engine champion · {r_.get('w', 0)}–{r_.get('l', 0)} in playground battles", 'activity': _hq.activity(len(cc['legs']), 0, 0, pct_)})
    # 🎛 at most 4 engine cards on the Arena, each with ≥ 6 coins: the engine champion first, then the best runners-up
    eng = [x for x in out if x.get('kind') in ('scenario', 'engine') and x.get('bench')]
    arena_runner_cards = sum(1 for x in out if x.get('kind') in ('lit', 'round', 'auto'))   # cards the Arena's own runner rounds made
    keep = sorted([x for x in eng if len(x.get('legs') or []) >= _pgb.MIN_COINS], key=lambda x: (not x.get('engineChamp'), -_fuse._f(x.get('pnlPct'))))[:min(4, arena_runner_cards)]   # ⚖ never more playground than Arena picks
    out = [x for x in out if x not in eng or x in keep]
    # ⭐ top-tier cards fight in the bracket too (fighters only — they already have their own section at the top of the Arena)
    tier_dial = {'diamond': 'safe', 'ever': 'safe', 'gold': 'balanced', 'blaze': 'degen', 'next': 'degen'}
    pcfg = _prime_cfg()
    for pc_ in await _prime_view():
        out.append({'kind': 'prime', 'fighterOnly': True, 'id': pc_['tpl'], 'name': pc_['label'].split(' ', 1)[-1], 'emoji': pc_['label'].split(' ', 1)[0],
                    'legs': [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'baseAddress': l.get('mint'), 'weight': round(_fuse._f(l.get('usd')) / max(1e-9, pc_['valueUsd']) * 100, 2), 'runner': l.get('role') == 'runner', 'entry': l.get('entry')} for l in pc_['legs']],
                    'index': round(100 + _fuse._f(pc_.get('pnlPct')), 2), 'grade': 'A' if _fuse._f(pc_.get('pnlPct')) > 0 else 'B', 'buyers': 0, 'at': pc_.get('at'), 'chat': f"fuse-card-prime-{pc_['tpl']}",
                    'dial': tier_dial.get(pc_.get('tier')), 'cfg': {'tp': pc_.get('tp'), 'sl': pc_.get('sl'), 'rotateHours': pcfg.get('rotateHours'), 'slMode': {'replace': 'sell'}.get(pcfg.get('slMode'), pcfg.get('slMode')), 'cycle': pc_.get('cycleMode')},
                    'tagline': f"top-tier card · {pc_.get('rounds', 0)} rounds", 'activity': _hq.activity(len(pc_['legs']), 0, 0, _fuse._f(pc_.get('pnlPct'))),
                    'real': pc_.get('cfgScope') == 'real'})
    rnd = (rd.get('rounds') or [None])[-1]
    if not [x for x in out if not x.get('fighterOnly')] and rnd and rnd.get('picks'):   # never an empty stage: the live round stands in as a proving card
        ps = rnd['picks']
        moves = [((_fuse._f(live.get(p['mint'], {}).get('price')) or p['entry']) / p['entry'] - 1) * 100 for p in ps if _fuse._f(p.get('entry')) > 0]
        mv = round(sum(moves) / len(moves), 2) if moves else 0.0
        out.append({'kind': 'round', 'id': str(rnd.get('id')), 'name': ' · '.join(f"${p.get('symbol')}" for p in ps[:4]), 'emoji': '⏳', 'aura': '',
                    'legs': [{'pairAddress': p.get('pairAddress') or p['mint'], 'symbol': p.get('symbol'), 'baseAddress': p['mint'], 'logo': p.get('logo'),
                              'weight': round(100 / len(ps), 2), 'entry': p.get('entry')} for p in ps], 'chat': f"fuse-card-{rnd.get('id')}",
                    'index': round(100 + mv, 2), 'grade': 'B', 'buyers': 0, 'at': rnd.get('at'),
                    'activity': _hq.activity(0, 0, sum(_fuse._f(live.get(p['mint'], {}).get('vol1h')) * 24 for p in ps), mv)})
    rec = _json_load(FUSE_HQ_PATH, {}).get('battleRecord') or {}
    out = [{**c, 'record_wl': rec.get(f"{c['kind']}:{c['id']}")} for c in out]
    out = await _card_dna_tag(out, rd)
    out.sort(key=lambda x: -x['activity']['score'])
    _arena_mega_cache.update(at=now, data=out)
    return out


async def _card_dna_tag(cards, rd):
    """🧬 Every Arena card carries its own DNA: user cards = their plan · tier cards = their tier config · engine cards = the battle DNA ·
    everything else gets a unique DNA (stable per card, stored) — so no two cards play alike."""
    pcfg = _prime_cfg(); pos = {x['id']: x for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or []}
    pgd = ((rd.get('pgBattle') or {}).get('dna') or {})
    fixed = {}
    for c in cards:
        k = f"{c['kind']}:{c['id']}"
        if c['kind'] == 'user' and c['id'] in pos:
            x = pos[c['id']]
            fixed[k] = _dna.clean({'cycle': x.get('cycle') if x.get('cycle') in ('classic', 'adaptive', 'safe', 'press', 'rescue', 'auto') else 'off', 'compound': x.get('compoundStyle') or 'smart', 'payoutPct': x.get('payoutPct', 100),
                                   'clock': x.get('rotateHours') or 24, 'stop': x.get('slMode') or 'sell'})
        elif c['kind'] == 'prime':
            fixed[k] = _dna.clean({'cycle': (pcfg.get('cycles') or {}).get(c['id'], 'off'), 'compound': pcfg.get('compoundStyle', 'smart') if pcfg.get('compound') else 'off',
                                   'payoutPct': (pcfg.get('payouts') or {}).get(c['id'], 0), 'clock': pcfg.get('rotateHours'), 'stop': {'replace': 'sell'}.get(pcfg.get('slMode'), pcfg.get('slMode')), 'trail': pcfg.get('trail', True)})
        elif c['kind'] == 'engine' and pgd.get(c['id']):
            fixed[k] = pgd[c['id']]
    store = _json_load(FUSE_HQ_PATH, {}).get('cardDna') or {}
    known = {**store, **fixed}
    assigned = _dna.assign([{'id': f"{c['kind']}:{c['id']}", 'dial': c.get('dial')} for c in cards], known=known)
    new = {k: v for k, v in assigned.items() if k not in fixed and k not in store}
    if new:
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {}); d['cardDna'] = {**dict(list((d.get('cardDna') or {}).items())[-300:]), **new}; _json_save(FUSE_HQ_PATH, d)
    return [{**c, 'dna': assigned[f"{c['kind']}:{c['id']}"], 'dnaLabel': _dna.label(assigned[f"{c['kind']}:{c['id']}"])} for c in cards]


@app.get('/api/reputation/admin/fuses/hq')
async def fuse_hq_admin(request: Request):
    """HQ › Fuse HQ: everyone's Fuse P&L, the paper arena (settles at 24h), bloodlines, published-Fuse health."""
    _require_admin(request)
    d = _json_load(FUSE_HQ_PATH, {})
    now = time.time()
    pos, arena = d.get('positions') or [], d.get('arena') or []
    px = await _hq_prices([leg for x in pos for leg in x['legs']] + [leg for e in arena if not e.get('close') for leg in e['legs']])
    vals = [_hq.arena_value(e, px, now) for e in arena]
    if any(v['due'] for v in vals):
        d = await _arena_settle(px, now)
        vals = [_hq.arena_value(e, px, now) for e in d.get('arena') or []]
    rows = [_hq.position_pnl(x, px) for x in pos]
    board = _hq.arena_board(vals)
    return {'book': _hq.book(rows), 'rows': sorted(rows, key=lambda r: -r['pnlUsd'])[:50], 'arena': sorted(vals, key=lambda v: -v['at'])[:40],
            'board': board, 'bestStyle': _hq.best_style(board), 'bloodline': d.get('bloodline') or [], 'minSettled': _hq.MIN_SETTLED,
            'outlook': _hq.outlook(board), 'published': len(_json_load(FUSES_PATH, {'fuses': {}})['fuses']),
            'blockedCuts': sum(1 for b in _json_load(FUSES_PATH, {}).get('buys') or [] if b.get('selfDeal') or b.get('bot'))}


@app.post('/api/reputation/admin/fuses/hq')
async def fuse_hq_admin_save(request: Request):
    """Enter a champion in the paper arena, save / drop it from the bloodline."""
    admin = _require_admin(request)
    body = await request.json()
    champ = body.get('champion') or {}
    legs = [leg for leg in champ.get('legs') or [] if leg.get('pairAddress')][:_fuse.MAX_LEGS]
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        if body.get('action') == 'arena' and len(legs) >= 2:
            e = _hq.arena_entry({**champ, 'legs': legs}, str(body.get('style') or 'yield')[:12], await _hq_prices(legs), time.time(), uuid.uuid4().hex[:10])
            d['arena'] = ((d.get('arena') or []) + [e])[-200:]
        elif body.get('action') == 'bloodline' and len(legs) >= 2:
            pools = sorted(leg['pairAddress'] for leg in legs)
            if not any(b['pools'] == pools for b in d.get('bloodline') or []):
                d['bloodline'] = ((d.get('bloodline') or []) + [{'pools': pools, 'symbols': [leg.get('symbol') for leg in legs], 'fitness': champ.get('fitness'),
                                                                 'style': body.get('style'), 'at': time.time()}])[-30:]
        elif body.get('action') == 'unbloodline':
            d['bloodline'] = [b for b in d.get('bloodline') or [] if b['pools'] != sorted(body.get('pools') or [])]
        else:
            raise HTTPException(400, 'arena | bloodline | unbloodline with a champion.')
        _json_save(FUSE_HQ_PATH, d)
        ad = _admin_load(); _audit(ad, admin, f"fuse-{body.get('action')}", ','.join(leg.get('symbol') or '' for leg in legs)[:120]); _admin_save(ad)
    return {'ok': True}


@app.get('/api/reputation/admin/fuses/health')
async def fuse_health(request: Request):
    """Each published Fuse re-scored on live numbers vs a fresh champion of the same size."""
    _require_admin(request)
    store = _json_load(FUSES_PATH, {'fuses': {}})
    raw = await _fuse_discover_pairs('solana')
    cands = {}
    for lens in _fuse.LENSES:
        for r in _fuse.discover(raw, lens, 'solana', now_ms=time.time() * 1000, limit=12):
            cands.setdefault(r['pairAddress'], r)
    out = []
    for fid, f in store['fuses'].items():
        pairs = await _fuse_pairs(f['legs'])
        metas = {k: _fuse.leg_meta(v) for k, v in pairs.items()}
        if len(metas) < 2:
            out.append({'id': fid, 'name': f.get('name'), 'dead': True}); continue
        mine = _fuse.fitness(list(metas), metas)['fitness']
        champ = await asyncio.to_thread(_fuse.evolve, {**dict(list(cands.items())[:40]), **metas}, len(metas), 10, 24, 'yield', 0.05, 150.0, 11, [list(metas)])
        out.append({'id': fid, 'name': f.get('name'), 'emoji': f.get('emoji'), **_hq.health(mine, champ['champions'][0]['fitness'] if champ['champions'] else 0),
                    'suggest': champ['champions'][0]['pools'] if champ['champions'] else []})
    return {'fuses': out}


async def _fuse_candidates(chain='solana'):
    """The gene pool: best ~40 live pools across popular / yield / deep / new (one row per pool)."""
    raw = await _fuse_discover_pairs(chain)
    cands = {}
    for lens in _fuse.LENSES:
        for r in _fuse.discover(raw, lens, chain, now_ms=time.time() * 1000, limit=12):
            cands.setdefault(r['pairAddress'], r)
    return cands


def _champ_view(c, metas, chain='solana'):
    return {**c, 'legs': [{**{k: metas[pa].get(k) for k in ('symbol', 'quote', 'dex', 'logo', 'liquidityUsd', 'aprEst', 'change24h', 'baseAddress', 'quoteAddress')},
                           'chainId': chain, 'pairAddress': pa, 'weight': c['weights'][pa]} for pa in c['pools']]}


@app.get('/api/reputation/fuses/yield-math')
async def fuse_yield_math():
    """Fuse vs Vault on live pools: what $1 earns from LP fees (Vault) vs what price moves did to $1 (Fuse)."""
    return _hq.yield_math(await _fuse_candidates())


_fuse_prebuilt_cache: dict = {}


@app.get('/api/reputation/fuses/prebuilt')
async def fuses_prebuilt(request: Request, legs: int = Query(3, ge=2, le=12), budget: float = Query(20, ge=1, le=10000)):
    """Discover rail: the best basket for EACH strategy right now (bred from live pools), with that strategy's arena record.
    Traders get 3-pool baskets; HQ may ask for up to 12. Cached 5 min per size."""
    legs = legs if _is_admin_req(request) else min(legs, _fuse.USER_MAX_LEGS)
    # Breeding buckets (fee drag + size guard depend on size): $1 · $5 · $20 · $100. The buyer's exact amount is used at Fuse in.
    key = (legs, 1 if budget < 3 else 5 if budget < 12 else 20 if budget < 60 else 100)
    hit = _fuse_prebuilt_cache.get(key)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    metas, sol_usd = await asyncio.gather(_fuse_candidates(), _sol_usd_live())
    board = {r['style']: r for r in _hq.arena_board([_hq.arena_value(e, {}, time.time()) for e in _json_load(FUSE_HQ_PATH, {}).get('arena') or []])}
    seed = int(time.time() // 300)
    runs = await asyncio.gather(*[asyncio.to_thread(_fuse.evolve, metas, legs, 14, 28, st, key[1] / sol_usd, sol_usd, seed) for st in _fuse.STYLES])
    dead = _retired(list(board.values()))   # ☠ strategies the arena proved to lose never reach a trader's rail
    cards = [{'style': st, 'arena': board.get(st), **_champ_view(ev['champions'][0], metas)} for st, ev in zip(_fuse.STYLES, runs) if ev['champions'] and st not in dead]
    out = {'legs': legs, 'budgetUsd': key[1], 'solUsd': sol_usd, 'retired': sorted(dead), 'cards': sorted(cards, key=lambda c: -((c['arena'] or {}).get('avgPct') or -999))}
    _fuse_prebuilt_cache[key] = (time.time(), out)
    return out


# ---- FUSE RUNNERS (backend/runners.py): coins come to it — live launchpad feed → gates → lanes → rounds → paper proof --
import runners as _rn
RUNNERS_PATH = DATA_DIR / 'runners.json'      # {'rounds': [...], 'paths': {mint: [[t, price], ...]}}
_runner_live_cache = {'at': 0.0, 'data': None}
# Set only inside the background warmer's own task: it rebuilds caches while viewers keep reading the last good copy.
_FUSE_FORCE = contextvars.ContextVar('fuse_force', default=False)
_mayhem_mints: set = set()


def _runner_cfg():
    return _rn.clean_cfg(_json_load(RUNNERS_PATH, {}).get('cfg') or {})
_runner_sem = asyncio.Semaphore(4)


async def _runner_intel(mint):
    hit = _intel_cache.get(mint)
    # an INCOMPLETE scan (no top-10 — RPC hiccup) is retried after 60s instead of failing the coin for the whole TTL
    if hit and time.time() - hit[0] < (INTEL_TTL if (hit[1] or {}).get('top10Pct') is not None else 60):
        return hit[1]
    async with _runner_sem:
        try:
            return await asyncio.wait_for(token_intel('solana', mint), 12)
        except Exception:
            return None


_runner_widen = {'level': 0, 'at': 0.0, 'log': []}


import meme_terms as _mt
import pg_battle as _pgb
import card_dna as _dna
MEME_PATH = DATA_DIR / 'meme_terms.json'


async def _meme_tick(now):
    """📖 Feed the meme-term learner: names + tickers of today's launchpad coins (trending + new + the live launch stream)
    and the last hour of FEELESS chat. Counts only — nothing here trades."""
    samples = []
    async with httpx.AsyncClient(timeout=10) as http:
        async def get(url, params, key):
            try:
                return (await http.get(url, params=params)).json().get(key) or []
            except Exception:
                return []
        tr, nw, pl = await asyncio.gather(get('http://127.0.0.1:5001/api/market/feed', {'kind': 'trending', 'chain': 'solana', 'page': 1, 'scope': 'launchpads'}, 'pairs'),
                                          get('http://127.0.0.1:5001/api/market/feed', {'kind': 'new', 'chain': 'solana', 'page': 1, 'scope': 'launchpads'}, 'pairs'),
                                          get('http://127.0.0.1:5001/api/pump/pulse', {'limit': 100}, 'launches'))
    for x in tr + nw:
        b = x.get('baseToken') or {}
        if b.get('address'):
            samples.append((f"{b.get('name') or ''} {b.get('symbol') or ''}", 'coin', b['address']))
    for x in pl:
        if x.get('mint'):
            samples.append((f"{x.get('name') or ''} {x.get('symbol') or ''}", 'coin', x['mint']))
    chat = _json_load(CHAT_PATH, {})
    rooms = chat.get('rooms', chat) if isinstance(chat, dict) else {}
    for room, msgs in rooms.items():
        for m in (msgs if isinstance(msgs, list) else [])[-200:]:
            ts = (m.get('ts', 0) / (1000 if m.get('ts', 0) > 1e12 else 1)) if isinstance(m, dict) else 0
            if ts and now - ts < 3600 and m.get('text'):
                samples.append((str(m['text'])[:280], 'chat', str(m.get('id') or f"{room}-{ts}")))
    async with _admin_lock:
        st = _mt.learn(_json_load(MEME_PATH, {}), samples, now)
        _json_save(MEME_PATH, st)
    return len(samples)


@app.get('/api/reputation/meme-terms')
async def meme_terms(term: str = ''):
    """📖 Today's trench language: new / spiking terms with meaning (known slang) or what the engine learned (ticker wave /
    chat slang), plus how many terms it knows. ?term= explains one word."""
    st = _json_load(MEME_PATH, {})
    if term:
        return _mt.explain(st, term[:24])
    now = time.time()
    return {'terms': _mt.trending(st, now), 'learned': len(st.get('firstSeen') or {}), 'glossary': len(_mt.GLOSSARY),
            'today': sum(((st.get('days') or {}).get(str(_mt.day_of(now))) or {}).values()), 'at': now}


RUNNER_SCANS = 60   # holder scans per board build (cached per coin): the busiest launch coins by 1h volume


async def _runner_live():
    """Every launchpad coin the feed sees right now (trending + new, pre-bond + graduated), forensics for the busiest,
    gated + scored. 30s cache — the board is shared by every viewer."""
    if _runner_live_cache['data'] and time.time() - _runner_live_cache['at'] < 40 and not _FUSE_FORCE.get():   # warmed every 25s in the background
        return _runner_live_cache['data']
    async with httpx.AsyncClient(timeout=10) as http:
        async def feed(kind, page=1):
            try:
                return (await http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': kind, 'chain': 'solana', 'page': page, 'scope': 'launchpads'})).json().get('pairs') or []
            except Exception:
                return []

        async def pulse():   # the live launch stream is the only place mayhem-mode is flagged: remember every one seen
            try:
                return (await http.get('http://127.0.0.1:5001/api/pump/pulse', params={'limit': 100})).json().get('launches') or []
            except Exception:
                return []
        # 🌊 4 pages each (it was 2): the feed now carries Pump's 250 biggest + 200 most recently traded coins
        got, launches = await asyncio.gather(asyncio.gather(*[feed(k, pg) for pg in (1, 2, 3, 4) for k in ('trending', 'new')]), pulse())
    _mayhem_mints.update(x['mint'] for x in launches if x.get('mayhem') and x.get('mint'))
    now_ms = time.time() * 1000
    seen, pairs = set(), []
    for p in [x for rows in got for x in rows]:
        m = (p.get('baseToken') or {}).get('address')
        if m and m not in seen and (now_ms - _fuse._f(p.get('pairCreatedAt'))) <= _rn.MAX_AGE_H * 3.6e6:
            seen.add(m); pairs.append(p)
    busiest = sorted(pairs, key=lambda p: -_fuse._f((p.get('volume') or {}).get('h1')))[:RUNNER_SCANS]   # warmed in the background (cached scans)
    # 🗑 trench breakouts get a holder scan too (they're rarely among the 40 busiest — the scan never reached them before)
    busiest += [p for p in sorted((p for p in pairs if p not in busiest and _trench.market_pair(p, time.time() * 1000, _trench.widen(len(_trench.WIDEN) - 1))),
                                  key=lambda p: -_fuse._f((p.get('volume') or {}).get('h1')))[:10]]
    # Never block the board on scans: wait ≤6s, the rest keep running and land in the cache for the next refresh.
    tasks = {(p.get('baseToken') or {}).get('address'): asyncio.ensure_future(_runner_intel((p.get('baseToken') or {}).get('address'))) for p in busiest}
    if tasks:
        await asyncio.wait(list(tasks.values()), timeout=6)
    intel = {m: t.result() for m, t in tasks.items() if t.done() and not t.cancelled() and t.exception() is None}
    blocks = _block_load()['wallets']
    out_pairs = {e['pair'] for e in _radar['events'] if e['kind'] == 'snipers-out'}
    cands = []
    smart = _smart_buyers(time.time())
    for p in pairs:
        m = (p.get('baseToken') or {}).get('address'); it = intel.get(m) or (_intel_cache.get(m) or (0, None))[1]
        creator = (it or {}).get('creator')
        brec = blocks.get(creator) if creator else None
        # ⛔ hard out: a creator REPORTED for a rug, or a bot. One blocklisted only for sniping OTHER launches is a warning (same as the
        # rug shield) — treated as suspect, so its coin must prove itself on its own numbers (`runners.banger_proof`).
        flagged = bool(creator and ((_is_blocked(brec) and brec.get('reported')) or (_shield_cache.get(creator, (0, {}))[1] or {}).get('verdict') == 'bot'))
        crep = None
        if creator:
            try:
                crep = _quick_rep(creator).get('level')
            except Exception:
                crep = None
            if _is_blocked(brec) and not brec.get('reported') and crep != 'high':
                crep = 'suspect'
        hist = _runner_track(m, time.time(), _fuse._f(p.get('curveProgress')), (it or {}).get('top10Pct'), (it or {}).get('devHoldingPct'))
        cands.append(_rn.candidate(p, it, flagged, p.get('pairAddress') in out_pairs or m in out_pairs, now_ms, mayhem=m in _mayhem_mints, creator_rep=crep,
                                   hist=hist, smart=smart.get(m, 0)))
    # 🔧 auto-widen: a dead board (fewer than 3 passing) loosens the SOFT gates a step (max 3, hard floors); a full board
    # (8+) steps back toward the configured engine. At most one step per 2 minutes; every step is logged with what moved.
    base = _runner_cfg(); wz = _runner_widen
    eff = _rn.widen(base, wz['level'])
    _runner_cands[:] = cands   # 🗑 every candidate (not just passing + the top 30 dropped) — the trench scan reads all of them
    data = {**_rn.board(cands, eff), 'seen': len(cands), 'at': time.time()}
    if time.time() - wz['at'] >= 120:
        nxt = _rn.widen_level(wz['level'], len(data['passing']))
        if nxt != wz['level']:
            wz.update(level=nxt, at=time.time()); wz['log'] = (wz['log'] + [{'at': time.time(), 'level': nxt, 'passing': len(data['passing'])}])[-20:]
            eff = _rn.widen(base, nxt)
            data = {**_rn.board(cands, eff), 'seen': len(cands), 'at': time.time()}
    if int(time.time()) % 300 < 40:   # ~every 5 min: remember rejected pre-bond coins for gate regret (cheap, capped)
        try:
            async with _admin_lock:
                rd_ = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); rd_['dropLog'] = _rn.log_drops(rd_.get('dropLog'), data['dropped'], time.time()); _json_save(RUNNERS_PATH, rd_)
        except Exception:
            pass
    data['widen'] = {'level': wz['level'], 'max': _rn.WIDEN_MAX, 'moved': {k: [base.get(k), eff.get(k)] for k in _rn.WIDEN_STEPS if base.get(k) != eff.get(k)}}
    _runner_live_cache.update(at=time.time(), data=data)
    return data


_runner_hist: dict = {}   # mint → [(t, curve, top10, dev)] over the last ~20 min (new checks + kill switch)


def _runner_track(mint, now, curve, top10, dev):
    """Remember this coin's curve / top-10 / dev % and derive: curve speed (pts gained over ~10 min), top-10 jump over 5 min,
    and whether the dev sold (dev % fell ≥1 pt from its recent high)."""
    if not mint:
        return {}
    h = [x for x in _runner_hist.get(mint, []) if now - x[0] <= 20 * 60] + [(now, curve, top10, dev)]
    _runner_hist[mint] = h[-60:]
    old = [x for x in h if now - x[0] >= 8 * 60]
    speed = round(curve - old[-1][1], 2) if old and curve else None
    t5 = [x[2] for x in h if now - x[0] <= 5 * 60 and x[2] is not None]
    jump = round(t5[-1] - min(t5), 2) if len(t5) >= 2 else 0.0
    devs = [x[3] for x in h if x[3] is not None]
    sold = bool(devs) and max(devs) > 0.5 and devs[-1] < max(devs) - 1
    if len(_runner_hist) > 3000:
        for k in [k for k, v in _runner_hist.items() if now - v[-1][0] > 20 * 60]:
            _runner_hist.pop(k, None)
    return {'curveSpeed': speed, 'top10Jump': jump, 'devSold': sold}


def _smart_buyers(now, window=30 * 60):
    """Smart FEELESS buyers per coin in the last 30 min: wallets with cached trust ≥ 75 or on the elite list (verified buys only)."""
    elites = _crowd_cache.get('elites_set') or set()
    out: dict = {}
    for w, rows in _json_load(FEELESS_TRADES_PATH, {}).items():
        smart = w in elites or _fuse._f(((_trust_cache.get(w) or (0, {}))[1] or {}).get('score')) >= 75
        if not smart:
            continue
        for x in rows or []:
            if x.get('side', 'buy') == 'buy' and now - _fuse._f(x.get('ts')) <= window and x.get('token'):
                out.setdefault(x['token'], set()).add(w)
    return {m: len(ws) for m, ws in out.items()}


async def _token_prices(mints):
    """Best-liquidity USD price per mint (DexScreener tokens/v1, 30 per call, in parallel)."""
    out = {}
    async with httpx.AsyncClient(timeout=10) as http:
        async def batch(chunk):
            try:
                for p in (await http.get(f"https://api.dexscreener.com/tokens/v1/solana/{','.join(chunk)}")).json() or []:
                    m = (p.get('baseToken') or {}).get('address')
                    liq = _fuse._f((p.get('liquidity') or {}).get('usd'))
                    if m and (m not in out or liq > out[m][0]):
                        out[m] = (liq, _fuse._f(p.get('priceUsd')))
            except Exception:
                pass
        ms = list(mints)
        await asyncio.gather(*[batch(ms[i:i + 30]) for i in range(0, len(ms), 30)])
    return {m: v[1] for m, v in out.items() if v[1] > 0}


_jup_px_cache: dict = {}


async def _jup_prices(mints):
    """🎯 Jupiter's own USD price per mint (price v3 — the price its routes trade at, across every pool), cached 20s. Paper fills
    and values use THIS so paper sees the same price real money gets (a single DexScreener pair can sit 20–40% away on runners)."""
    now = time.time()
    want = [m for m in dict.fromkeys(mints or []) if m]
    out = {m: v for m in want for t, v in [_jup_px_cache.get(m, (0, 0))] if now - t < 20 and v > 0}
    miss = [m for m in want if m not in out]
    if miss:
        key = os.environ.get('JUPITER_API_KEY')
        sources = ([('https://api.jup.ag/price/v3', {'x-api-key': key})] if key else []) + [('https://lite-api.jup.ag/price/v3', {})]   # keyed first, public fallback
        async with httpx.AsyncClient(timeout=6) as http:
            for base, hdr in sources:
                todo = [m for m in miss if m not in out]
                if not todo:
                    break
                try:
                    for i in range(0, len(todo), 50):
                        d = (await http.get(base, params={'ids': ','.join(todo[i:i + 50])}, headers=hdr)).json() or {}
                        for m, v in d.items():
                            px = _fuse._f((v or {}).get('usdPrice'))
                            if px > 0:
                                out[m] = px; _jup_px_cache[m] = (now, px)
                except Exception:
                    continue   # next source; callers fall back to the pool price when Jupiter has none
    return out


async def _runner_tick(now=None, force=False):
    """Every 5 min: record prices for every pick of the last 24h (the proof's price paths); every 15 min (or forced): a new
    round — the best runners stay, newcomers fill the rest."""
    now = now or time.time()
    live = await _runner_live()
    d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
    recent = [r for r in d['rounds'] if now - r['at'] <= 24 * 3600]
    lit_recent = [c for c in d.get('litCards') or [] if now - c['at'] <= 72 * 3600]   # lit cards are tracked for 72h
    watch = {p['mint'] for r in recent for p in r['picks']} | {p['mint'] for c in lit_recent for p in c['picks']}
    px = {r['mint']: r['price'] for r in live['passing'] + live['dropped'] if r.get('price')}
    missing = [m for m in watch if m not in px]
    if missing:
        px.update(await _token_prices(missing))
    async with _admin_lock:
        d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
        for m in watch:
            if px.get(m):
                d['paths'].setdefault(m, []).append([now, px[m]])
        d['paths'] = {m: pts[-900:] for m, pts in d['paths'].items() if m in watch or pts and now - pts[-1][0] < 26 * 3600}
        last = d['rounds'][-1] if d['rounds'] else None
        cfg = _runner_cfg()
        if force or not last or now - last['at'] >= _rn.ROUND_SECONDS:
            weights = _rn.lane_weights(_rn.lane_proofs(d['rounds'], d['paths'], now, cfg))   # self-tuning lanes
            pool_ = _rn.apply_filter(live['passing'], d.get('pickFilter'), cfg['roundSize'])   # 🩺 the doctor's pick filter first
            new = _rn.next_round(last, pool_, now, size=cfg['roundSize'], rid=uuid.uuid4().hex[:8], weights=weights, cooled=_rn.recently_out(d['rounds']))   # 🧊 3-round cool-down
            pf = _rn.proof(d['rounds'], d['paths'], now, cfg=cfg)
            d['rounds'] = (d['rounds'] + [new])[-200:]
            if pf['lights'] and new['picks']:   # dealt while lit → it joins the lit-cards list
                d['litCards'] = ((d.get('litCards') or []) + [_rn.lit_card(new, pf)])[-30:]
        elif last:
            # Auto-swap: one pick that now FAILS a gate is replaced by the best passing runner (closed on paper, reason kept)
            failing = {x['mint']: x.get('gates') or ['failed a gate'] for x in live['dropped']}
            d['rounds'][-1], _swap = _rn.swap_failing(last, live['passing'], failing, d['paths'], now, cfg, cooled=_rn.recently_out(d['rounds']))
        # Lit cards stay strong: 2+ strong + 1 weak → the weak coin is swapped for a new runner; fewer than 2 strong → taken down.
        failing = {x['mint']: x.get('gates') or ['failed a gate'] for x in live['dropped']}
        for i, c in enumerate(d.get('litCards') or []):
            if now - c['at'] <= 72 * 3600:
                d['litCards'][i], _ = _rn.rebuild_lit(c, d['paths'], live['passing'], failing, now, cfg)
        _json_save(RUNNERS_PATH, d)
    return d['rounds'][-1] if d['rounds'] else None


async def _runner_loop():
    """Price paths every 5 min, and wake exactly when the next round is due (the countdown never sits at 00:00)."""
    await asyncio.sleep(60)
    while True:
        try:
            await _runner_tick()
        except Exception as e:
            print('runners:', e)
        rounds = _json_load(RUNNERS_PATH, {'rounds': []}).get('rounds') or []
        due = (rounds[-1]['at'] + _rn.ROUND_SECONDS - time.time()) if rounds else 300
        await asyncio.sleep(max(5.0, min(300.0, due + 2)))


@app.on_event('startup')
async def _runner_start():
    if not os.environ.get('PYTEST_CURRENT_TEST'):
        asyncio.create_task(_runner_loop())
        asyncio.create_task(_fuse_warm_loop())
        asyncio.create_task(_prime_bell_loop())


# ---- ⭐ ARENA PRIME (backend/arena_prime.py): FEELESS's top-tier cards, FULLY AUTO on paper — the proof before configs go live ----
import arena_prime as _prime


def _prime_cfg():
    cfg = _prime.clean_cfg((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cfg') or {})
    cal = _fw.calibrate(_fw_load().get('ledger'))
    if cal.get('feeUsd') is not None:   # 🎯 paper pays what a real swap from the Fuse wallet costs (network + priority)
        cfg['paperFeeUsd'] = cal['feeUsd']
    return cfg


def _prime_real_cfg(pr=None):
    """💵 The REAL card's own config (`prime.realCfg`): separate from paper — HQ/engine tunes, meta config and tier locks only ever write the
    paper `cfg`. Not set yet → it starts as a copy of today's paper config. Any clock (5 min too) is allowed."""
    pr = pr if pr is not None else (_json_load(FUSE_HQ_PATH, {}).get('prime') or {})
    paper = _prime_cfg()
    rc = pr.get('realCfg')
    if isinstance(rc, dict) and rc:
        out = _prime.clean_cfg(rc)
        if 'instantSwapPct' not in rc:
            out['instantSwapPct'] = out['rotateMinDrop']
        return {**_prime.real_guard(out, pr.get('realOwnerSet') or ())[0], 'paperFeeUsd': paper['paperFeeUsd']}   # 💵 hard floors (owner's OFF hold wins)
    return _prime.real_guard({**paper, 'instantSwapPct': paper.get('rotateMinDrop', 0)})[0]


import trench as _trench

_trench_cache: dict = {'at': 0.0, 'rows': [], 'checked': []}
_runner_cands: list = []   # every runner candidate of the last board build (filled by _runner_live)
TRENCH_SCAN = 8   # on-chain holder counts are heavy: only the 5 busiest coins that already pass every cheap check


async def _trench_build(now):
    """🗑 Every ~2 min (warm loop): fresh launches breaking out with a real crowd. Cheap checks on the whole runner feed, then the
    on-chain holder count + mint/freeze authority for the busiest survivors only. Result cached for the tier tick (never fetched
    inside it). `checked` keeps why each finalist passed or failed (HQ / tests)."""
    if now - _trench_cache['at'] < 120 or os.environ.get('PYTEST_CURRENT_TEST'):
        return _trench_cache
    _trench_cache['at'] = now
    live = await _runner_live()
    seen, pool = set(), []
    own0 = _trench.clean_own((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('trenchCfg'))
    # finalists by the LOOSEST soft checks (the strictest level that passes wins) — or by the owner's own checks
    loose = _trench.own_gate(own0) if own0['mode'] == 'own' else _trench.widen(len(_trench.WIDEN) - 1)
    every = list(_runner_cands) or (live.get('passing') or []) + (live.get('dropped') or [])
    _trench_cache['seen'], _trench_cache['funnel'] = len(every), _trench.funnel(every, loose)[:8]   # 🔎 why coins didn't make it
    for r in every:
        if r.get('mint') and r['mint'] not in seen and not _trench.precheck(r, loose):
            seen.add(r['mint']); pool.append(r)
    pool = sorted(pool, key=lambda r: -_fuse._f(r.get('vol1h')))[:TRENCH_SCAN]
    async def one(r):
        try:
            h = await asyncio.wait_for(_token_holders(r['mint']), 25)
            async with httpx.AsyncClient(timeout=8) as http:
                auth = await _mint_authorities(http, r['mint'])
        except Exception:
            return None
        return r, (h or {}).get('holders'), auth
    got = [x for x in await asyncio.gather(*[one(r) for r in pool]) if x]
    own = _trench.clean_own((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('trenchCfg'))
    if own['mode'] == 'own':   # 🎛 the owner's own soft checks (crowd, trades, volume, cap band, age) — the safety checks never move
        g_own = _trench.own_gate(own)
        res = [(g, *_trench.gate(g[0], g[1], g[2], g_own)) for g in got]
        rows = [{**_trench_row(g[0], g[1], g[2], g_own), 'trenchLevel': 'own'} for g, _ok, _f in res]
        _trench_cache.update(rows=[x for x in rows if x['ok']], checked=rows, level='own', own=own)
        return _trench_cache
    lvl, res = _trench.best_level(got, lambda g, cfg: _trench.gate(g[0], g[1], g[2], cfg))
    rows = [{**_trench_row(g[0], g[1], g[2], _trench.widen(lvl or 0)), 'trenchLevel': lvl or 0} for g, _ok, _f in res]
    _trench_cache.update(rows=[x for x in rows if x['ok']], checked=rows, level=lvl, own=own)
    return _trench_cache


@app.get('/api/reputation/fuses/trench')
async def fuse_trench():
    """🗑 The trench scan's latest finalists (coin data only): holders, market cap, age and every check passed / failed."""
    keys = ('mint', 'symbol', 'pairAddress', 'price', 'liq', 'holders', 'mcap', 'ageH', 'vol1h', 'buyShare', 'ok', 'fails', 'trenchWhy', 'trenchScore', 'trenchLevel')
    own = _trench.clean_own((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('trenchCfg'))
    g = _trench.own_gate(own) if own['mode'] == 'own' else _trench.widen(_trench_cache.get('level') if isinstance(_trench_cache.get('level'), int) else 0)
    return {'cfg': own, 'options': _trench.OWN_OPTIONS, 'checked': [{k: r.get(k) for k in keys} for r in _trench_cache.get('checked') or []], 'pass': len(_trench_cache.get('rows') or []),
            'rows': [{**{k: r.get(k) for k in keys}, 'score': r.get('trenchScore'), 'trench': True} for r in _trench_cache.get('rows') or []],   # 🗑 pickable
            'floor': _fw.clean_cfg(_fw_load().get('cfg') or {})['trenchMinLiqUsd'], 'level': _trench_cache.get('level'),
            'seen': _trench_cache.get('seen', 0), 'funnel': _trench_cache.get('funnel') or [],
            'at': _trench_cache.get('at'), 'rules': f"≤ {g['maxAgeH']:g}h old · broke ${g['minMcap'] / 1000:g}K · ≥ {g['minHolders']} holders · ≥ {g['minTxns1h']} trades/h · "
                                                     f"≥ {g['minBuyShare']:g}% buys · top-10 < {g['maxTop10']:g}% · dev < {g['maxDev']:g}% · creator not suspect / high · mint + freeze revoked"}


def _trench_row(r, holders, auth, cfg=None):
    ok, fails = _trench.gate(r, holders, auth, cfg)
    sc, parts = _trench.score(r, holders)
    return {'mint': r['mint'], 'pairAddress': r.get('pairAddress'), 'symbol': r.get('symbol'), 'price': r.get('price'), 'liq': r.get('liq'),
            'ageH': r.get('ageH'), 'mcap': r.get('mcap'), 'vol1h': r.get('vol1h'), 'buyShare': r.get('buyShare'), 'holders': holders,
            'score': max(60.0, sc), 'trenchScore': sc, 'trenchWhy': parts, 'fails': fails, 'ok': ok, 'trenchOnly': True, 'division': 'trench'}


REAL_LIQ_MARGIN = 1.15   # a real card's candidates clear the keeper's pool floor by 15%


def _real_weather():
    """🌦 Runner weather for the real card, from the sim brain's last run (pg_sim.json)."""
    return _prime.weather(_json_load(PG_SIM_PATH, {}))


def _prime_cool_candidates(rows, cooling_mints, minimum, strict=False):
    """Keep recently exited mints out. Real money is strict: a thin candidate
    set may leave a slot in cash, but must never bypass its stop cooldown and
    immediately rebuy the same loser. Paper keeps the historical fallback."""
    fresh = [x for x in rows if x.get('mint') not in cooling_mints]
    return fresh if strict or len(fresh) >= minimum else rows


PAPER_MIN_LIQ = 20_000.0   # paper tiers deal any gated coin with a ≥$20K pool (the REAL card uses the Fuse wallet's own floors)


async def _prime_candidates():
    """Pools: the deepest busy pools from the Fuse gene pool. Runners: pre-bond coins passing every runner gate, best first."""
    metas = await _fuse_candidates()
    pools = sorted(({'mint': m.get('baseAddress'), 'pairAddress': pa, 'symbol': m.get('symbol'), 'price': m.get('priceUsd'),
                     'liquidityUsd': m.get('liquidityUsd'), 'volume24h': m.get('volume24h'), 'rank': min(400.0, _fuse._f(m.get('aprEst'))) * math.log10(max(10.0, _fuse._f(m.get('liquidityUsd'))))} for pa, m in metas.items()
                    if m.get('baseAddress') and _fuse._f(m.get('priceUsd')) > 0 and _fuse._f(m.get('liquidityUsd')) >= 100_000), key=lambda x: -x['rank'])
    # 🏁 every coin the site already ranks is a candidate: the Gauntlet's pool divisions (popular · top yield · deepest · new 72h, built
    # from the same feeds as the Lab, Trenches and Pump radar) join the gene pool — from the warm cache, never a new fetch
    seen_p = {x['mint'] for x in pools}
    for dv in ((_contenders_cache.get('data') or {}).get('divisions') or []):
        if dv.get('role') != 'pool':
            continue
        for r in dv.get('rows') or []:
            if r.get('mint') and r['mint'] not in seen_p and _fuse._f(r.get('liq')) >= 100_000 and _fuse._f(r.get('price')) > 0:
                seen_p.add(r['mint'])
                pools.append({'mint': r['mint'], 'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'price': r['price'], 'liquidityUsd': r['liq'],
                              'volume24h': r.get('vol24h'), 'rank': _fuse._f(r.get('score')), 'contender': dv['key']})
    live = await _runner_live()
    # runners = pre-bond coins passing every gate + CLEAN GRADUATED young coins (<48h, failing ONLY the pre-bond gate)
    young = list(live.get('passing') or []) + [r for r in live.get('dropped') or [] if r.get('gates') == ['Pre-bond (still on the curve)']]
    runners = sorted(({'mint': r['mint'], 'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'price': r.get('price'), 'score': r.get('score'),
                      'vol1h': r.get('vol1h'), 'buyShare': r.get('buyShare'), 'liq': r.get('liq'), 'ageH': r.get('ageH')} for r in young if _fuse._f(r.get('price')) > 0),   # depth travels with the coin (else every runner read $0 and failed the real-buy floor)
                     key=lambda x: -_fuse._f(x['score']))
    # 🚀 NEW MAJORS (young coins that arrived big: ≤14d, $800K–$50M, $300K+ volume, $100K+ pool) — the secure growth slot when no
    # runner is safe to buy, so a card is never ONLY old majors
    try:
        if os.environ.get('PYTEST_CURRENT_TEST'):
            raise RuntimeError('tests never fetch live pools')
        have = {r['mint'] for r in runners}
        runners += [{'mint': r.get('baseAddress'), 'pairAddress': r.get('pairAddress'), 'symbol': r.get('symbol'), 'price': r.get('priceUsd'), 'score': 60,
                     'liquidity': r.get('liquidityUsd'), 'buyShare': r.get('buyShare'), 'change24h': r.get('change24h'), 'newMajor': True,
                     'change1h': r.get('change1h'), 'change6h': r.get('change6h'), 'mcap': r.get('mcap'), 'createdAt': r.get('createdAt'), 'volume24h': r.get('volume24h')}
                    for r in (await fuses_discover(lens='risers', chain='solana')).get('pools') or [] if r.get('baseAddress') not in have and _fuse._f(r.get('priceUsd')) > 0]   # 🚀 risers + 🟢 Pump's top 15 by volume (same as the Lab lens)
    except Exception as e:
        if not os.environ.get('PYTEST_CURRENT_TEST'):
            print('new majors:', e)
    # ⚓ Anchors: every real major (BTC, ETH, SOL, JUP, PUMP, BONK, WIF, POPCAT, TRUMP, PENGU, …) + big NEW majors, ranked by what
    # they are DOING right now (turnover, 1h/6h/24h moves, buyers, depth) — SOL gets no head start; stables / LSTs never anchor
    nm_rows = [r for r in runners if r.get('newMajor')]
    risers_a = [{'baseAddress': r['mint'], 'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'priceUsd': r.get('price'), 'liquidityUsd': r.get('liquidity'),
                 'mcap': r.get('mcap'), 'createdAt': r.get('createdAt'), 'change1h': r.get('change1h'), 'change6h': r.get('change6h'), 'change24h': r.get('change24h'),
                 'volume24h': r.get('volume24h'), 'buyShare': r.get('buyShare')} for r in nm_rows]
    anchors = [{'mint': r.get('baseAddress'), 'pairAddress': r.get('pairAddress'), 'symbol': r.get('symbol'), 'price': r.get('priceUsd'), 'liquidityUsd': r.get('liquidityUsd'),
                'anchorScore': r.get('anchorScore'), 'anchorWhy': r.get('anchorWhy'), 'volume24h': r.get('volume24h'), **({'newMajor': True} if r.get('newMajor') else {})}
               for r in _fuse.rank_anchors(await _majors_rows(), risers_a, now_ms=time.time() * 1000)]
    # ARENA-backed coins go first: this round's runner picks, live lit cards, and every coin on a stage / battle card
    rd = _json_load(RUNNERS_PATH, {'rounds': []}); rnd = (rd.get('rounds') or [None])[-1] or {}
    arena = {p.get('mint') for p in rnd.get('picks') or []} | {p.get('mint') for c in rd.get('litCards') or [] if not c.get('downAt') for p in c.get('picks') or []}
    arena |= {leg.get(k) for c in (_arena_mega_cache.get('data') or []) for leg in c.get('legs') or [] for k in ('pairAddress', 'mint', 'baseAddress')}
    arena |= set(((_contenders_cache.get('data') or {}).get('nextUp') or {}))   # 🏁 ⏭ next-up contenders earned an Arena-backed seat
    arena.discard(None)
    # 🏁 every candidate carries the Gauntlet division it ranks in (shown on the card: where each new coin came from)
    div_of = {}
    for dv in ((_contenders_cache.get('data') or {}).get('divisions') or []):
        for r in dv.get('rows') or []:
            div_of.setdefault(r.get('mint'), dv['key'])
    for x in pools + runners + anchors:
        if div_of.get(x.get('mint')):
            x['division'] = div_of[x['mint']]
        elif x.get('contender'):
            x['division'] = x['contender']
    for x in pools + runners:
        if x.get('mint') in arena or x.get('pairAddress') in arena:
            x['arena'] = True
    # 🎭 lookalikes are out of every seat: a coin wearing a major's ticker that is not that major (a "SOL" at $0.0004)
    real_ = lambda xs: [x for x in xs if not _fw.lookalike(x.get('symbol'), x.get('mint'), _fuse.MAJORS)]
    return real_(pools), real_(runners), anchors


import contenders as _ct

_contenders_cache: dict = {'at': 0.0, 'data': None}
_contenders_lock = asyncio.Lock()


async def _contenders_build():
    """🏁 The Arena qualifier league: every pick list is a division, ranked on live facts; rebuilt at most every 30s (one build at a time)."""
    if _contenders_cache['data'] and time.time() - _contenders_cache['at'] < 30:
        return _contenders_cache['data']
    async with _contenders_lock:
        if _contenders_cache['data'] and time.time() - _contenders_cache['at'] < 30:
            return _contenders_cache['data']
        now = time.time()
        pairs, majors, risers, live = await asyncio.gather(_fuse_discover_pairs('solana'), _majors_rows(), fuses_discover(lens='risers', chain='solana'),
                                                           _runner_live(), return_exceptions=True)
        pairs = pairs if isinstance(pairs, list) else []
        live = live if isinstance(live, dict) else {}
        young = list(live.get('passing') or []) + [r for r in live.get('dropped') or [] if r.get('gates') == ['Pre-bond (still on the curve)']]
        src = {'majors': majors if isinstance(majors, list) else [], 'risers': (risers.get('pools') if isinstance(risers, dict) else []) or [],
               'fresh': young, 'proven': young,
               **{k: _fuse.discover(pairs, lens, 'solana', now_ms=now * 1000) for k, lens in (('yield', 'yield'), ('deep', 'deep'), ('popular', 'popular'), ('new', 'new'))}}
        # 📉 dip buys + 💳 dex paid read every pool the site already has (popular · new · risers), no extra fetch
        src['dip'] = src['paid'] = (_fuse.discover(pairs, 'popular', 'solana', now_ms=now * 1000, limit=120) + src['new'] + src['risers'])
        src['volume'] = young
        src['trench'] = list(_trench_cache.get('rows') or [])
        # 👀 never an empty Trench list: nothing passing → the scan's closest misses, else the busiest fresh launches (watch only)
        src['trench_watch'] = [{**r, 'trenchOnly': False} for r in (_trench_cache.get('checked') or []) if not r.get('ok')] or \
            sorted((r for r in _runner_cands if r.get('ageH') is not None and _fuse._f(r.get('ageH')) <= 24), key=lambda r: -_fuse._f(r.get('vol1h')))[:8]
        cards = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
        on_card = {l.get('mint') for c in cards.values() for l in c.get('legs') or []}
        on_card |= {leg.get(k) for c in (_arena_mega_cache.get('data') or []) for leg in c.get('legs') or [] for k in ('mint', 'baseAddress')}
        on_card.discard(None)
        data = {**_ct.league(src, on_card, _contenders_cache.get('data')), 'at': now, 'weather': _real_weather()}
        _contenders_cache.update(at=now, data=data)
        return data


def _pick_row(pair, mint):
    """A live DexScreener pair → a swap-pick row, or None: the pool must be THIS mint, have a live price, ≥ $25K depth, and not be a
    dollar coin (it never moves). Real cards additionally need the real-buy floor (checked by the caller)."""
    if not pair or (pair.get('baseToken') or {}).get('address') != mint:
        return None
    m = _fuse.leg_meta(pair)
    if m['priceUsd'] <= 0 or m['liquidityUsd'] < 25_000 or str(m.get('symbol') or '').upper() in _ct.STABLES or _fw.lookalike(m.get('symbol'), mint, _fuse.MAJORS):
        return None
    return {'mint': mint, 'pairAddress': pair.get('pairAddress'), 'symbol': m.get('symbol'), 'price': m['priceUsd'], 'liq': m['liquidityUsd']}


@app.get('/api/reputation/fuses/contenders')
async def fuses_contenders():
    """Public: the divisions, their ranked coins (score + cited parts, ▲▼, streak) and who is ⏭ next up for a card seat."""
    return await _contenders_build()


_prime_tick_lock = asyncio.Lock()


async def _prime_tick(now):
    async with _prime_tick_lock:   # the warm loop and the 🔔 round bell never run two ticks at once
        n = await _prime_tick_inner(now)
    try:
        await _fw_tick(now)   # 👛 real tier cards follow the engine with real swaps
    except Exception as e:
        print('fuse wallet:', e)
    return n


async def _prime_bell_loop():
    """🔔 Wake exactly when the next tier round is due (the 10s countdown on screen ends on time, never at 00:00 for a minute)."""
    await asyncio.sleep(30)
    while True:
        try:
            cards = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
            rcfg = _prime_real_cfg(); pcfg_b = _prime_cfg(); locks_b = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('locks') or {}
            # ⏱ every card has its OWN clock: the real card's, a locked tier's, or the tier's entry in `clocks`
            rot_of = lambda c: (rcfg if c.get('real') else _prime.clean_cfg(locks_b[c['tpl']]) if c.get('tpl') in locks_b else _prime.tier_cfg(pcfg_b, c.get('tpl')))['rotateHours'] * 3600
            # deal time = round end + 10s bell (💵 real: `dealLeadSec` earlier · a floored card wakes when its rest ends, not every 5s)
            due = min(((_fuse._f(c['flooredAt']) + max(60.0, _fuse._f(rcfg.get('floorRestMins') if c.get('real') else 0) * 60)) if c.get('flooredAt') else
                       (_fuse._f(c.get('lastRotateAt')) + rot_of(c) + _prime.BELL_SEC - (_fuse._f(rcfg.get('dealLeadSec')) if c.get('real') else 0))
                       for c in cards.values() if c.get('lastRotateAt')), default=time.time() + 60)
            wait = due - time.time()
            kick = _FW_KICK.get('at')   # ⏳ a real buy was just refused → re-pick that seat 15s later (never a whole tick later)
            if kick and time.time() >= kick + _fw.RETRY_SEC:
                _FW_KICK.pop('at', None)
                wait = min(wait, 0.0)
            if 0.5 < wait <= 12:   # 🔔 inside the 10s countdown: warm the candidates + prices now, so the re-deal is instant at 0
                await _prime_candidates()
                await asyncio.sleep(max(0.0, due - time.time()))
                wait = 0
            if wait <= 0.5:
                await _prime_tick(time.time())
                wait = 5
            if _FW_KICK.get('at'):
                wait = min(wait, _FW_KICK['at'] + _fw.RETRY_SEC - time.time())
            await asyncio.sleep(max(1.0, min(60.0, wait + 0.2)))
        except Exception as e:
            print('prime bell:', e)
            await asyncio.sleep(30)


def _fw_market_rows(cards, books):
    """Every pair whose live price can affect a card or its confirmed real-money book."""
    rows = {}
    for c in (cards or {}).values():
        for l in list(c.get('legs') or []) + list((c.get('parked') or {}).values()):
            if l.get('pairAddress'):
                rows[l['pairAddress']] = {'pairAddress': l['pairAddress'], 'mint': l.get('mint')}
    for b in (books or {}).values():
        for mint, l in (b.get('legs') or {}).items():
            if l.get('pair'):
                rows[l['pair']] = {'pairAddress': l['pair'], 'mint': mint}
    return list(rows.values())


PRIME_RESET = 'paper20'   # one-time: every PAPER tier card starts over on $20 (the real card is never touched)


PRIME_UNIQUE = 'unique2'


async def _prime_unique_fix(now):
    """🃏 Once: undo "Add to all cards" — every paper card gets its OWN exits back (its explicit per-card edits are kept; any exit key it
    lost to the shared edit returns to that card's unique default; the shared TP / stop go back to 'tier'). The real card is never touched."""
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        if pr.get('uniqueFix') == PRIME_UNIQUE:
            return False
        cfg = _prime.clean_cfg(pr.get('cfg') or {})
        cfg['tierCfg'] = _prime.unique_exits(cfg['tierCfg'])
        cfg['tp'] = cfg['sl'] = 0.0
        pr['cfg'] = _prime.clean_cfg(cfg); pr['uniqueFix'] = PRIME_UNIQUE
        _json_save(FUSE_HQ_PATH, d)
    ad = _admin_load(); _audit(ad, 'engine-auto', 'arena-prime', 'every paper card back on its own unique exits (real card untouched)'); _admin_save(ad)
    return True


async def _prime_reset_paper(now):
    """🔁 Start every paper tier card over at $20, once. Their old runs go to the permanent record + `prime.archive`; the tick deals
    fresh cards at the new size right after. Real-money cards keep running exactly as they are."""
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        if pr.get('reset') == PRIME_RESET:
            return 0
        cards = pr.get('cards') or {}
        gone = {k: c for k, c in cards.items() if not c.get('real')}
        for k, c in gone.items():
            try:
                _store.Ledger(CARD_RECORDS_PATH, table='runs').append({'at': now, 'card': k, 'label': c.get('label'), 'startUsd': c.get('startUsd'), 'real': False, 'closed': True, 'why': 'restart on $20'})
            except Exception as e:
                print('card records (reset):', e)
        pr['archive'] = ((pr.get('archive') or []) + [{'at': now, 'why': 'paper restart on $20', 'cards': {k: {x: c.get(x) for x in ('label', 'startUsd', 'putInUsd', 'walletUsd', 'rounds')} for k, c in gone.items()}}])[-20:]
        pr['cards'] = {k: c for k, c in cards.items() if c.get('real')}
        pr['cfg'] = _prime.clean_cfg({**(pr.get('cfg') or {}), 'sizeUsd': 20.0})
        pr['reset'] = PRIME_RESET
        _json_save(FUSE_HQ_PATH, d)
    return len(gone)


async def _prime_tick_inner(now):
    await _prime_unique_fix(now)
    await _prime_reset_paper(now)
    cfg = _prime_cfg()
    if not cfg['on']:
        return 0
    pools, runners, anchors = await _prime_candidates()
    d = _json_load(FUSE_HQ_PATH, {})
    cards = dict((d.get('prime') or {}).get('cards') or {})
    # one pair fetch → live price AND momentum for EVERY coin on the cards (majors + pools too, not only runner-board coins)
    books = (_fw_load().get('books') or {})
    market_rows = _fw_market_rows(cards, books)
    pairs_ = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in market_rows]) if market_rows else {}
    px = {k: _fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}
    jup = await _jup_prices([l.get('mint') for l in market_rows])
    for l in market_rows:   # 🎯 confirmed book holdings waiting on a sell need live prices too
        if jup.get(l.get('mint')):
            px[l['pairAddress']] = jup[l['mint']]
    def _mom(p):
        tx = (p.get('txns') or {}).get('h1') or {}; b, s_ = _fuse._f(tx.get('buys')), _fuse._f(tx.get('sells'))
        return {'chg1h': _fuse._f((p.get('priceChange') or {}).get('h1')), 'buyShare': round(b / (b + s_) * 100, 1) if b + s_ else None,
                'vol5m': _fuse._f((p.get('volume') or {}).get('m5')), 'vol1h': _fuse._f((p.get('volume') or {}).get('h1'))}
    pair_mom = {k: _mom(v) for k, v in pairs_.items()}
    # live momentum per pair (runner board: 1h move, buy share, 5m/1h volume) → exit_plan decides ride / gain / bank / cut early
    live = _runner_live_cache.get('data') or {}
    mom = {**pair_mom, **{r['pairAddress']: {k: r.get(k) for k in ('chg1h', 'buyShare', 'vol5m', 'vol1h')} for r in (live.get('passing') or []) + (live.get('dropped') or []) if r.get('pairAddress')}}
    locks = (d.get('prime') or {}).get('locks') or {}
    before_runs = {tid: max((_fuse._f(r.get('at')) for r in (c or {}).get('runs') or []), default=0.0) for tid, c in cards.items()}   # newest run already recorded
    taken = set()   # 🎲 coins already on a tier dealt earlier this tick — later tiers pick OTHER coins when they can (no 5 identical cards)
    order_t = sorted(_prime.TEMPLATES, key=lambda t: 0 if (cards.get(t) or {}).get('real') else 1)   # real cards pick first
    for tid in order_t:
        cur = cards.get(tid)
        liqs = {k: _fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_.items()}
        cfg_t = {**_prime.clean_cfg(locks[tid]), 'paperFeeUsd': cfg['paperFeeUsd']} if tid in locks else _prime.tier_cfg(cfg, tid)   # 🔒 a locked tier runs its own frozen config · every other tier its own ⏱ clock
        real_t = bool((cur or {}).get('real'))
        if real_t:
            cfg_t = _prime_real_cfg(d.get('prime') or {})   # 💵 the real card runs ITS OWN config — paper edits / locks / engine tunes never touch it
        # 🎯 PAPER = REAL: every tier (paper too) only rotates into coins real money could buy (pool ≥ minLiqUsd), so paper results are an
        # honest preview. ✅ Runners also need confirmation: rising over the last hour with buyers in control (≥55% buys) — no buying the top.
        def _lq(x):
            v = x.get('liquidity'); return _fuse._f(v.get('usd') if isinstance(v, dict) else v) or _fuse._f(x.get('liq')) or liqs.get(x.get('pairAddress'), 0.0)
        fw_cfg = _fw_load().get('cfg') or {}
        floor_of = (lambda x: _fw.liq_floor(fw_cfg, x.get('arena'))) if real_t else (lambda x: PAPER_MIN_LIQ)   # paper ⇄ real floors are separate
        def _confirmed(x):
            if x.get('newMajor'):   # a new major: green over 24h with buyers at least even
                return _fuse._f(x.get('change24h')) > 0 and _fuse._f(x.get('buyShare')) >= 50
            m = mom.get(x.get('pairAddress')) or {}
            bs = _fuse._f(m.get('buyShare')); bs = bs * 100 if 0 < bs <= 1 else bs
            return _fuse._f(m.get('chg1h')) > 0 and bs >= 55
        # 💵 real money: a coin must clear its floor with REAL_LIQ_MARGIN room (cached depth drifts before the keeper's live re-check) and
        # there is NO fallback to thin pools — that fallback dealt coins the keeper then refused ("pool too thin") while the slot sat in cash
        mg = REAL_LIQ_MARGIN if real_t else 1.0
        p_t = [x for x in pools if _lq(x) >= floor_of(x) * mg] or ([] if real_t else pools)
        r_t = [x for x in runners if _lq(x) >= floor_of(x) * mg and _confirmed(x)]
        if real_t:   # 🌦 real money buys runners by the weather the engine's own sims measured (rain = strong + deep only · storm = none)
            r_t = _prime.weather_runners(r_t, _real_weather()['level'], _fw.clean_cfg(fw_cfg)['minLiqUsd'], _lq)
        # 🗑 trench coins (strict gate, cached by the warm loop) — only a 🗑 trench slot ever takes one; own pool floor; real money
        # never buys one in a runner storm. The real-money runner age rule doesn't apply to them: the trench gate replaces it.
        tr_floor = _fw.clean_cfg(fw_cfg)['trenchMinLiqUsd']   # paper uses the same floor (paper = what real money could buy)
        if not (real_t and _real_weather()['level'] == 'storm'):
            r_t = r_t + [x for x in _trench_cache.get('rows') or [] if _lq(x) >= tr_floor * mg and x.get('mint') not in {y.get('mint') for y in r_t}]
        # 🪑 coins real money couldn't buy safely (2× in 10 min) are benched 1h for EVERY tier — paper never trades what real can't
        bench = set().union(*[_fw.benched(b, now) for b in (_fw_load().get('books') or {}).values()] or [set()])
        if bench:
            p_t, r_t = [x for x in p_t if x.get('mint') not in bench], [x for x in r_t if x.get('mint') not in bench]
        if real_t:   # 🚪 real money never buys a coin that is falling right now (coins already on the card are not judged here)
            on_ = {l.get('mint') for l in (cur or {}).get('legs') or []}
            p_t = [x for x in p_t if x.get('mint') in on_ or _prime.entry_ok(x, mom)]
            r_t = [x for x in r_t if x.get('mint') in on_ or _prime.entry_ok(x, mom)]
        book_s = (_fw_load().get('books') or {}).get(tid) or {} if cur and cur.get('real') else {}
        stuck = set(_fw.stuck_buys(cur, now, bench, missed=book_s.get('misses'), pending_mint=(book_s.get('pending') or {}).get('toMint') or (book_s.get('pending') or {}).get('mint'))) if cur and cur.get('real') else set()
        if stuck:   # ⏳ the real card swaps a coin whose buy can't land (benched, or refused 15s ago) for a buyable one NOW
            before_ = cur
            cool_s = _prime.cooling(cur, now, cfg_t['rotateHours'], px)   # 🧊 … never for a coin that just left this card
            p_t, r_t = [x for x in p_t if x.get('mint') not in cool_s], [x for x in r_t if x.get('mint') not in cool_s]
            for pa in stuck:
                l = next((x for x in cur['legs'] if x.get('pairAddress') == pa), None)
                if not l:
                    continue
                why_s = "couldn't be bought safely — benched" if l.get('mint') in bench else "buy was refused — trying the next best coin" if l.get('mint') in (book_s.get('misses') or {}) else 'buy never landed in 2 min'
                try:
                    tmp = {**cur, 'legs': [{**x, 'units': _fuse._f(x.get('wantUnits'))} if x is l else x for x in cur['legs']]}
                    cur = _prime.replace_leg(tmp, pa, px, p_t, r_t, anchors, cfg_t, now)
                    cur['events'] = cur['events'][:-1] + [{**cur['events'][-1], 'why': f"⏳ ${l.get('symbol')} {why_s} — swapped for a buyable coin"}]
                except ValueError:   # nothing buyable of its role: the slot goes back to card cash (refilled next round), never waits forever
                    cur = {**cur, 'legs': [x for x in cur['legs'] if x is not l], 'events': list(cur.get('events') or []) + [
                        {'at': now, 'kind': 'rotate', 'symbol': l.get('symbol'), 'usd': 0.0, 'why': f"⏳ ${l.get('symbol')} {why_s} — slot back to card cash"}]}
            cur = _prime.note_dropped(before_, cur, now, cfg_t['rotateHours'], px)   # 🧊 the stuck coin cools like any coin that left
        # ⏱ each clock gets ITS coins: fast rounds rank by what is moving now, slow rounds keep depth / score order
        p_t, r_t = _prime.clock_rank(p_t, cfg_t['rotateHours'], mom), _prime.clock_rank(r_t, cfg_t['rotateHours'], mom)
        mine = {l.get('mint') for l in (cur or {}).get('legs') or []}
        p_t = [x for x in p_t if x.get('mint') not in taken or x.get('mint') in mine]
        r_t = [x for x in r_t if x.get('mint') not in taken or x.get('mint') in mine]
        a_t = anchors
        cool = _prime.cooling(cur, now, cfg_t['rotateHours'], px) - mine   # 🧊 coins this card just dropped sit out a few rounds → new coins flow in
        if cool:
            # 💵 A real stop must stay stopped. Falling back to the unfiltered
            # list when discovery was thin caused sell→immediate-rebuy churn.
            p_t = _prime_cool_candidates(p_t, cool, 2, strict=real_t)
            r_t = _prime_cool_candidates(r_t, cool, 3, strict=real_t)
        # 🧊 anchors cool too: a major this card just sold isn't bought back for 3 rounds while another major is available
        a_t = _prime_cool_candidates(anchors, cool, 2, strict=real_t and len([x for x in anchors if x.get('mint') not in cool]) >= 1) if cool else anchors
        true_usd = None
        if real_t:   # 💵 floor / rescue / fix / runs judge the TRUE book (confirmed coins + card SOL), never the engine's estimate
            bk = (_fw_load().get('books') or {}).get(tid)
            try:
                sol_px_t = await _sol_usd_live() if bk else 0.0
            except Exception:
                sol_px_t = 0.0
            if bk and sol_px_t > 0 and not bk.get('pending'):
                true_usd = _fw.book_value(bk, px, sol_px_t) or None
        cards[tid] = _prime.tick(cur, px, p_t, r_t, cfg_t, now, a_t, mom, liqs, true_usd=true_usd) if cur else _prime.deal(tid, p_t, r_t, cfg_t, now, anchors)
        cards[tid] = _prime.note_dropped(cur, cards[tid], now, cfg_t['rotateHours'], px)
        taken |= {l.get('mint') for l in (cards[tid] or {}).get('legs') or [] if l.get('role') != 'anchor'}
    cards = {k: v for k, v in cards.items() if v}
    try:   # 📏 vs holding SOL: remember SOL's price when each run starts (a new run = a new startUsd)
        sol_now = await _sol_usd_live()
        for v in cards.values():
            if sol_now and v.get('solStartFor') != v.get('startUsd'):
                # a run already underway when first seen has no true SOL baseline → no comparison until its next run starts
                v['solLate'] = 'solStart' not in v
                v['solStart'], v['solStartFor'] = sol_now, v.get('startUsd')
    except Exception:
        pass
    _record_runs(before_runs, cards)
    win = _prime.crown_round(cards)
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {}); d.setdefault('prime', {})['cards'] = cards
        if any(c.get('real') for c in cards.values()) and not d['prime'].get('realCfg'):
            # 💵 the first time a card runs real money its config is FROZEN as its own — HQ / engine tunes on paper can't reach it after this
            d['prime']['realCfg'] = _prime.clean_cfg(d['prime'].get('cfg') or {})
            d['prime']['realCfg']['instantSwapPct'] = d['prime']['realCfg'].get('rotateMinDrop', 0)
        if win:
            d['prime']['roundWinner'] = {'id': win, 'at': now}
        _json_save(FUSE_HQ_PATH, d)
    return len(cards)


CARD_RECORDS_PATH = DATA_DIR / 'card_records.json'   # → card_records.db: every ended run of every tier card, append-only, forever


def _record_runs(before, cards):
    """📜 Permanent record: each run that just ended on a tier card goes into the append-only ledger (never trimmed, never edited)."""
    try:
        lg = _store.Ledger(CARD_RECORDS_PATH, table='runs')
        for tid, c in cards.items():
            for r in c.get('runs') or []:   # runs keep only the last 10 on the card — the timestamp tells what's new
                if _fuse._f(r.get('at')) > before.get(tid, 0.0):
                    lg.append({**r, 'card': tid, 'label': c.get('label'), 'real': bool(c.get('real'))})
    except Exception as e:
        print('card records:', e)


@app.get('/api/reputation/fuses/record/{tpl}')
async def fuse_card_record(tpl: str):
    """📜 A tier card's permanent public record: every run it ever finished (start → end, %), best / worst / win rate."""
    if tpl not in _prime.TEMPLATES:
        raise HTTPException(404, 'Unknown card.')
    rows = _store.Ledger(CARD_RECORDS_PATH, table='runs').rows(limit=500, card=tpl)
    pcts = [_fuse._f(r.get('pct')) for r in rows]
    return {'card': tpl, 'runs': rows, 'n': len(rows), 'won': sum(1 for p in pcts if p > 0), 'bestPct': max(pcts) if pcts else None,
            'worstPct': min(pcts) if pcts else None, 'avgPct': round(sum(pcts) / len(pcts), 2) if pcts else None}


async def _prime_view():
    cards = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    if not cards:
        return []
    fw_books = _fw_load().get('books') or {}
    market_rows = _fw_market_rows(cards, fw_books)
    px = await _hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in market_rows])
    jup = await _jup_prices([l.get('mint') for l in market_rows])
    px.update({l['pairAddress']: jup[l['mint']] for l in market_rows if jup.get(l.get('mint'))})
    cyc = _prime_cfg().get('cycles') or _prime.DEFAULT_CYCLES
    def _cyc(tpl):
        seq = _prime.CYCLE_MODES.get(cyc.get(tpl, 'off'))
        return list(seq) if isinstance(seq, tuple) else ['anchor', 'mixed', 'degen'] if seq == 'adaptive' else None
    pcfg = _prime_cfg()
    rcfg = _prime_real_cfg()
    try:
        sol_now = await _sol_usd_live()
    except Exception:
        sol_now = 0.0
    def _vs(c, sm):   # card % minus what simply holding SOL did over the same run
        if not (sol_now and _fuse._f(c.get('solStart'))) or c.get('solLate', True):
            return {}
        hold = (sol_now / _fuse._f(c['solStart']) - 1) * 100
        return {'holdSolPct': round(hold, 2), 'vsSolPct': round(_fuse._f(sm.get('pnlPct')) - hold, 2)}
    locks = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('locks') or {}
    def _eff(c):
        if c.get('real'):
            return rcfg   # the real card shows ITS OWN config
        return {**pcfg, **_prime.clean_cfg(locks[c['tpl']])} if c.get('tpl') in locks else _prime.tier_cfg(pcfg, c.get('tpl'))
    def _cfgv(c):
        e = _eff(c); return {'clockMin': round(e['rotateHours'] * 60), 'confirm': e['rotateConfirm'], 'minDrop': e['rotateMinDrop'],
                             'instantSwapPct': e.get('instantSwapPct', 0), 'holdMin': e['minHoldMins'], 'rideAt': e.get('rideAt'), 'rideTrail': e.get('rideTrail'),
                             'cycle': (e.get('cycles') or {}).get(c['tpl']), 'reshape': e['cycleEvery'], 'slMode': e['slMode'], 'locked': c.get('tpl') in locks}
    def _truth(c, sm):
        b = fw_books.get(c.get('tpl')) if c.get('real') else None
        if not b or sol_now <= 0:
            return sm
        v = _fw.book_value(b, px, sol_now)   # confirmed holdings + card SOL + segregated payout SOL
        paid = _fuse._f(b.get('bankSol')) * sol_now
        start = _fw.real_run_start(c, b) or 1
        held = max(0.0, v - paid)
        card_fees = round(_fuse._f(b.get('cardFeesSol')) * sol_now, 4)   # 🧾 network fees the CARD paid (from round 5) — apart from P&L
        return {**sm, 'startUsd': round(start, 4), 'valueUsd': v, 'cardFeesUsd': card_fees, 'walletUsd': round(paid, 4), 'pnlPct': round((v / start - 1) * 100, 2),
                'legacyRunBaseline': not bool(c.get('realBaselineAt')),
                'payoutTargetUsd': round(_fuse._f(c.get('walletUsd')), 4),
                'pendingPayoutUsd': round(max(0.0, _fuse._f(c.get('walletUsd')) - _fuse._f(b.get('bankUsd'))), 4),
                'math': {**sm.get('math', {}), 'putIn': round(_fuse._f(b.get('fundedUsd')) or start, 4), 'runStartUsd': round(start, 4), 'heldUsd': round(held, 4), 'paidOutUsd': round(paid, 4),
                         'nowUsd': v, 'feesUsd': card_fees, 'pnlUsd': round(v + card_fees - (_fuse._f(b.get('fundedUsd')) or start), 4)}}   # P&L = price result; fees apart
    return [{**(sm := _truth(c, _prime.summary(c, px, _eff(c)))), **_vs(c, sm), 'cfgView': _cfgv(c), 'cfgScope': 'real' if c.get('real') else 'locked' if c.get('tpl') in locks else 'shared', 'cfgEff': _eff(c), 'holdAll': bool(c.get('holdAll')), 'handsOffUntil': c.get('handsOffUntil') if _prime.hands_off_left(c, time.time()) else None, 'cyclePeek': _prime.cycle_peek(c, _eff(c)), 'cycleMode': cyc.get(c['tpl'], 'off'), 'cycle': _cyc(c['tpl']), 'realBook': _fw_public(c['tpl'], sm.get('valueUsd'), sol_now, px) if c.get('real') else None,
             'audit': [{k: e.get(k) for k in ('at', 'kind', 'symbol', 'usd', 'why', 'to', 'mode')} for e in (c.get('events') or [])[-40:][::-1]]} for c in cards.values()]


@app.get('/api/reputation/fuses/prime')
async def fuse_prime():
    """⭐ Arena Prime cards (paper, fully auto) with every automation event + the config they run."""
    return {'cards': await _prime_view(), 'cfg': _prime_cfg(), 'templates': _prime.TEMPLATES, 'weather': _real_weather(), 'suggest': _json_load(PG_SIM_PATH, {}).get('byClock') or {}, 'realGuard': _prime.real_guard({**_prime.clean_cfg((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}), 'instantSwapPct': _fuse._f(((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('realCfg') or {}).get('instantSwapPct'))}, (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('realOwnerSet') or ())[1], 'paperMatch': _fw.paper_match(_fw_load().get('quoteAudit')), 'locks': {k: v.get('lockedAt') for k, v in ((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('locks') or {}).items()}, 'lockCfg': ((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('locks') or {}), 'roundWinner': (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('roundWinner'), 'realOwnerSet': (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('realOwnerSet') or []}


@app.post('/api/reputation/admin/arena/prime')
async def fuse_prime_admin(request: Request):
    """HQ › Arena: turn Prime on/off, set size, rotation (hours / coins), compound; reset deals 3 fresh cards."""
    admin = _require_admin(request)
    body = await request.json()
    kick_real_keeper = False
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        was = {t: (_prime.clean_cfg(pr.get('cfg') or {}).get('cycles') or {}).get(t) for t in _prime.TEMPLATES}
        was.update({t: (l.get('cycles') or {}).get(t) for t, l in (pr.get('locks') or {}).items()})
        inc = dict(body.get('cfg') or {})
        tc = {t: dict(v) for t, v in (_prime.clean_cfg(pr.get('cfg') or {}).get('tierCfg') or {}).items()}
        for t, row_ in (inc.pop('tierCfg', None) or {}).items() if isinstance(inc.get('tierCfg'), dict) else ():   # 🃏 one card's own exits
            if t in tc and isinstance(row_, dict):
                tc[t].update(row_)
        for k_ in _prime.TIER_KEYS:   # 🃏 exits are each card's OWN: a shared edit never overwrites them (no "all cards at once")
            inc.pop(k_, None)
        pr['cfg'] = _prime.clean_cfg({**(pr.get('cfg') or {}), **inc, 'tierCfg': tc})
        if isinstance(body.get('realCfg'), dict):   # 💵 the real card's own config (paper untouched); first edit copies today's paper config
            base = pr.get('realCfg') if isinstance(pr.get('realCfg'), dict) and pr.get('realCfg') else pr['cfg']
            pr['realCfg'] = _prime.clean_cfg({**base, **body['realCfg']})
            # 🪙 THE OWNER PICKS: every setting saved here is the owner's — the engine's self-fix never changes it afterwards
            pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {k for k in body['realCfg'] if isinstance(k, str)})[:60]
        if body.get('lock') in _prime.TEMPLATES:   # 🔒 lock a tier's FULL config as it is now (engine, tunes and meta config never change it)
            locks = dict(pr.get('locks') or {})
            if isinstance(body.get('patch'), dict) and locks.get(body['lock']):   # ⚙ edit a LOCKED tier: change only its own frozen config
                base = {k: v for k, v in locks[body['lock']].items() if k != 'lockedAt'}
                locks[body['lock']] = {**_prime.clean_cfg({**base, **body['patch']}), 'lockedAt': time.time()}
            elif body.get('on', True):
                if not locks.get(body['lock']):   # locking keeps an existing lock as it is (never overwritten by the shared config)
                    locks[body['lock']] = {**_prime.clean_cfg(_prime.tier_cfg(pr['cfg'], body['lock'])), 'lockedAt': time.time()}   # its OWN exits + clock
            else:
                locks.pop(body['lock'], None)
            pr['locks'] = locks
        now_c = {t: (pr['cfg'].get('cycles') or {}).get(t) for t in _prime.TEMPLATES}
        now_c.update({t: (l.get('cycles') or {}).get(t) for t, l in (pr.get('locks') or {}).items()})
        for t, cards_ in [(t, pr.get('cards') or {}) for t in _prime.TEMPLATES if now_c.get(t) != was.get(t) and t in (pr.get('cards') or {})]:
            cards_[t] = _prime.owner_cycle(cards_[t], now_c[t], time.time())   # 🎛 the owner's new cycle beats any auto safe / rescue fix
        hd = body.get('hold') or {}
        if hd.get('tpl') in _prime.TEMPLATES and (pr.get('cards') or {}).get(hd['tpl']):   # ✋ hold all: no swaps / re-shapes (stops + rug shield still run)
            c_ = pr['cards'][hd['tpl']]; c_['holdAll'] = bool(hd.get('on'))
            c_['events'] = (list(c_.get('events') or []) + [{'kind': 'hold', 'at': time.time(), 'why': '✋ hold all — no swaps or re-shapes until released' if hd.get('on') else '▶ released — the engine swaps and re-shapes again'}])[-60:]
        ho = body.get('handsOff') or {}
        if ho.get('tpl') in _prime.TEMPLATES and (pr.get('cards') or {}).get(ho['tpl']):   # 🔒 hands-off lock (owner's own picks / hand swaps wait)
            pr['cards'][ho['tpl']] = _prime.set_hands_off(pr['cards'][ho['tpl']], ho.get('hours'), time.time())
        if body.get('reset'):
            pr['cards'] = {}
        if body.get('fix') in _prime.TEMPLATES and ((pr.get('cards') or {}).get(body['fix']) or {}).get('real'):
            c_ = pr['cards'][body['fix']]   # 🔧 manual fix: re-fund every waiting buy from the SOL anchor NOW + fresh retries (no 60s / round wait)
            c_['rebuyAt'], c_['rebuyRound'] = 0, -1
            c_['events'] = (list(c_.get('events') or []) + [{'kind': 'fix', 'at': time.time(), 'why': '🔧 fix buys/sells — waiting coins re-funded, fresh retries'}])[-60:]
        if body.get('redeal') in _prime.TEMPLATES:          # one tier fresh
            cur_ = (pr.get('cards') or {}).get(body['redeal'])
            if cur_ and cur_.get('real'):   # 💵 a real card re-deals its coins in place (same money, same run) — never a fresh $100 paper card
                cur_['redealNow'] = True
            else:
                (pr.get('cards') or {}).pop(body['redeal'], None)
        _json_save(FUSE_HQ_PATH, d)
    if body.get('fix') in _prime.TEMPLATES:   # 🔧 (outside the HQ lock — never hold both locks at once)
        async with _fw_lock:
            fd = _fw_load(); b_ = fd['books'].get(body['fix'])
            if b_ is not None:
                b_['misses'] = {}   # every coin gets fresh retries (benched coins stay benched — they really failed the safety checks)
                b_['manualCashSol'] = 0.0   # 🔧 held cash goes back to work: Fix = "use this card's money" (✂ again to hold some apart)
                _fw_save(fd)
    if isinstance(body.get('trenchCfg'), dict):   # 🎛 the owner's trench settings (auto = engine widens by itself · own = these numbers)
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {}); d.setdefault('prime', {})['trenchCfg'] = _trench.clean_own(body['trenchCfg'])
            _json_save(FUSE_HQ_PATH, d)
        _trench_cache['at'] = 0.0   # re-scan with the new rules on the next warm pass
    pk = body.get('pickSwap') or {}
    if pk.get('tpl') in _prime.TEMPLATES and pk.get('pairAddress'):   # 🎯 the owner picks WHICH coin comes in at the next round (or cancels)
        cand = None
        if pk.get('to'):
            # only a coin the Gauntlet ranks RIGHT NOW (live price, real pool, not a dollar coin) can be picked
            row = next((r for dv in ((await _contenders_build()).get('divisions') or []) for r in dv.get('rows') or [] if r.get('mint') == pk['to']), None)
            row = row or next((r for r in _trench_cache.get('rows') or [] if r.get('mint') == pk['to']), None)   # 🗑 a passing trench coin
            if not row and pk.get('toPair'):   # 🔎 any coin from the Lab lenses / search: verified LIVE on its own pool right now
                lp = (await _fuse_pairs([{'chainId': 'solana', 'pairAddress': pk['toPair']}])).get(pk['toPair']) or {}
                row = _pick_row(lp, pk['to'])
            if not row:
                raise HTTPException(400, 'Pick a coin from the live lists — that one has no live pool right now.')
            cand = {'mint': row['mint'], 'pairAddress': row['pairAddress'], 'symbol': row.get('symbol'), 'price': row.get('price'), 'liquidityUsd': row.get('liq'),
                    **({'trenchOnly': True} if row.get('trenchOnly') else {}),
                    'division': next((dv['key'] for dv in (_contenders_cache.get('data') or {}).get('divisions') or [] if any(r.get('mint') == row['mint'] for r in dv.get('rows') or [])), None)}
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            card = cards.get(pk['tpl'])
            if not card:
                raise HTTPException(404, 'No card for that tier yet.')
            if cand and card.get('real'):   # 💵 real money keeps its own floor: the pick must be buyable
                floor = _fw.liq_floor(_fw_load().get('cfg') or {}, True, bool(cand.get('trenchOnly')))   # 🗑 trench picks use the trench floor
                if _fuse._f(cand.get('liquidityUsd')) < floor:
                    raise HTTPException(400, f"${cand['symbol']} pool is ${_fuse._f(cand.get('liquidityUsd')):,.0f} — under the ${floor:,.0f} real-buy floor (Edit Fuse › Limits).")
            if cand and _prime.hands_off_left(card, time.time()):
                raise HTTPException(400, f"🔒 Hands-off lock: {int(_prime.hands_off_left(card, time.time()) // 60) + 1} min left — picks wait. The engine and your stops keep working.")
            if cand:   # 🧊 the same coin never comes straight back: a coin that just left sits out its rounds, the owner's pick too
                rc_ = _prime_real_cfg(d.get('prime') or {}) if card.get('real') else _prime.tier_cfg(_prime_cfg(), pk['tpl'])
                left = _prime.cool_left(card, cand['mint'], time.time(), rc_['rotateHours'])
                if left:
                    raise HTTPException(400, f"${cand['symbol']} just left this card — it can come back in {left} round{'s' if left != 1 else ''}. Pick another coin.")
            try:
                cards[pk['tpl']] = _prime.queue_swap(card, pk['pairAddress'], cand)
            except ValueError as e:
                raise HTTPException(400, str(e))
            _json_save(FUSE_HQ_PATH, d)
    rep = body.get('replace') or {}
    if rep.get('tpl') in _prime.TEMPLATES and rep.get('pairAddress'):   # ⇄ one coin on one Prime card
        pools, runners, anchors = await _prime_candidates()
        # ⇄ a manual swap picks only BUYABLE coins (same gates as the engine): pool ≥ the real-buy floor, not benched, not on another tier
        fw_cfg = _fw_load().get('cfg') or {}
        bench = set().union(*[_fw.benched(b, time.time()) for b in (_fw_load().get('books') or {}).values()] or [set()])
        def _lq(x):
            v = x.get('liquidity'); return _fuse._f(v.get('usd') if isinstance(v, dict) else v) or _fuse._f(x.get('liq')) or _fuse._f(x.get('liquidityUsd'))
        other = {l.get('mint') for t, cc in ((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}).items() if t != rep['tpl'] for l in cc.get('legs') or [] if l.get('role') != 'anchor'}
        ok_ = lambda xs: [x for x in xs if _lq(x) >= _fw.liq_floor(fw_cfg, x.get('arena')) and x.get('mint') not in bench]
        pools, runners = ok_(pools), sorted(ok_(runners), key=lambda x: x.get('mint') in other)
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            card = cards.get(rep['tpl'])
            if not card:
                raise HTTPException(404, 'No card for that tier yet.')
            if _prime.hands_off_left(card, time.time()):
                raise HTTPException(400, f"🔒 Hands-off lock: {int(_prime.hands_off_left(card, time.time()) // 60) + 1} min left — hand swaps wait. The engine and your stops keep working.")
            px = await _hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in card['legs']])
            try:
                old_m = {l.get('mint') for l in card['legs']}
                cfg_r = _prime_real_cfg(d.get('prime') or {}) if card.get('real') else pr['cfg']
                cool_r = _prime.cooling(card, time.time(), cfg_r['rotateHours'], px)   # 🧊 a hand swap never brings back a coin that just left
                pools, runners = [x for x in pools if x.get('mint') not in cool_r], [x for x in runners if x.get('mint') not in cool_r]
                cards[rep['tpl']] = _prime.note_dropped(card, _prime.replace_leg(card, rep['pairAddress'], px, pools, runners, anchors, cfg_r, time.time()), time.time(), cfg_r['rotateHours'], px)
                kick_real_keeper = bool(card.get('real'))   # manual ⇄ on real money runs NOW; keeper enforces sell-confirm-before-buy
                for l in cards[rep['tpl']]['legs']:   # 👆 YOUR pick: carried through the next re-shape (it once got sold 4 min later)
                    if l.get('mint') not in old_m:
                        l['picked'] = True
            except ValueError as e:
                raise HTTPException(400, str(e))
            _json_save(FUSE_HQ_PATH, d)
    ms = body.get('manualSell') or {}
    if ms.get('tpl') in _prime.TEMPLATES and (ms.get('pairAddress') or ms.get('all')):
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            card = cards.get(ms['tpl'])
            if not card or not card.get('real'):
                raise HTTPException(400, 'Manual sell-to-cash is only available on a real card.')
            px = await _hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in card.get('legs') or []])
            try:
                # ✂ the owner's manual sell: one coin or every coin, any % (25 / 50 / 100) — the only way principal ever leaves a card
                pairs_ms = [l['pairAddress'] for l in card.get('legs') or [] if l.get('mint') != _fw.SOL_MINT and _fuse._f(l.get('units')) > 0] if ms.get('all') else [ms['pairAddress']]
                for pa in pairs_ms:
                    card = _prime.sell_leg_to_cash(card, pa, px, time.time(), ms.get('pct') or 100)
                cards[ms['tpl']] = card
                kick_real_keeper = True
            except ValueError as e:
                raise HTTPException(400, str(e))
            _json_save(FUSE_HQ_PATH, d)
    sk = body.get('skim') or {}
    if sk.get('tpl') in _prime.TEMPLATES and sk.get('pairAddress'):   # 💰 take ONE coin's profit now (stake keeps riding) → other coins, or held as cash
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            card = cards.get(sk['tpl'])
            if not card:
                raise HTTPException(404, 'No card for that tier yet.')
            px = await _hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in card.get('legs') or []])
            try:
                cards[sk['tpl']] = _prime.skim_leg(card, sk['pairAddress'], px, {}, time.time(), sk.get('to') or 'card')
                kick_real_keeper = bool(card.get('real'))
            except ValueError as e:
                raise HTTPException(400, str(e))
            _json_save(FUSE_HQ_PATH, d)
    lg = body.get('leg') or {}
    if lg.get('tpl') in _prime.TEMPLATES and lg.get('pairAddress'):   # ❄ freeze / own stop mode for one coin on one tier card
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {}); cards = (d.get('prime') or {}).get('cards') or {}
            if not cards.get(lg['tpl']):
                raise HTTPException(404, 'No card for that tier yet.')
            try:
                cards[lg['tpl']] = _prime.set_leg(cards[lg['tpl']], lg['pairAddress'], lg.get('frozen'), lg.get('slMode'), lg.get('tp'), lg.get('sl'))
            except ValueError as e:
                raise HTTPException(400, str(e))
            _json_save(FUSE_HQ_PATH, d)
    ad = _admin_load(); _audit(ad, admin, 'arena-prime', json.dumps(pr['cfg'])[:120] + (' reset' if body.get('reset') else '') + (f" manualSell {json.dumps(ms)[:60]}" if ms else '') + (f" leg {json.dumps(lg)[:60]}" if lg else '')); _admin_save(ad)
    if body.get('reset') or body.get('redeal'):
        await _prime_tick(time.time())
    if kick_real_keeper:
        await _fw_tick(time.time())   # manual real-money ⇄: sell old coin now; buy waits until no sell remains
    return {'cfg': pr['cfg'], 'cards': await _prime_view()}


# ---- 👛 FUSE WALLET (backend/fuse_wallet.py): the owner's Fuse Circle wallet funds the tier cards with REAL money ----
import fuse_wallet as _fw
FUSE_WALLET_PATH = DATA_DIR / 'fuse_wallet.json'   # {'cfg', 'books': {tier: book}, 'ledger': [orders · top-ups · defunds]}
_fw_lock = asyncio.Lock()
_FW_TOKEN_PROGRAMS = ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')


import store as _store


def _fw_load():
    """🗄 The Fuse wallet lives in SQLite (crash-safe, one transaction per write) — never a half-written JSON file."""
    d = _store.KV(FUSE_WALLET_PATH).get({}) or {}
    d.setdefault('books', {}); d.setdefault('ledger', [])
    return d


def _fw_save(d):
    _store.KV(FUSE_WALLET_PATH).put(d)


def _fw_cfg():
    return _fw.clean_cfg(_fw_load().get('cfg') or {})


_fw_signer = {'ok': False, 'at': 0.0}


def _fw_signer_ready():
    """Owner-approved Circle signing (sidecar POST /sign) is live when the Circle service is configured (cached ≤60s)."""
    return bool(_fw_signer['ok'])


async def _fw_signer_check():
    if time.time() - _fw_signer['at'] < 60:
        return _fw_signer['ok']
    try:
        st = await _circle('GET', '/status')
        _fw_signer.update(ok=bool(st.get('configured')), at=time.time())
    except Exception:
        _fw_signer.update(ok=False, at=time.time())
    return _fw_signer['ok']


async def _fw_sign(cfg, raw_b64, memo):
    """Circle signs ONE keeper transaction — only ever for the picked Fuse wallet id. Never sends."""
    if not cfg.get('walletId') or not raw_b64:
        raise HTTPException(400, 'No Fuse wallet / transaction to sign.')
    return await _circle('POST', '/sign', {'walletId': cfg['walletId'], 'rawTransaction': raw_b64, 'memo': memo[:80]})


async def _fw_balances(addr):
    """SOL + every token the Fuse wallet holds (atoms + decimals), one parallel RPC read."""
    async with httpx.AsyncClient(timeout=12) as http:
        bal, *toks = await asyncio.gather(_krpc(http, 'getBalance', [addr, {'commitment': 'confirmed'}]),
                                          *[_krpc(http, 'getTokenAccountsByOwner', [addr, {'programId': pg}, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}]) for pg in _FW_TOKEN_PROGRAMS])
    tokens, decs = {}, {}
    for t in toks:
        for a in (t or {}).get('value') or []:
            info = (((a.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
            amt = info.get('tokenAmount') or {}
            if info.get('mint'):
                tokens[info['mint']] = tokens.get(info['mint'], 0) + int(amt.get('amount') or 0); decs[info['mint']] = int(amt.get('decimals') or 0)
    return {'sol': int((bal or {}).get('value') or 0) / 1e9, 'tokens': tokens, 'decimals': decs}


async def _fw_jup(method, path, **kw):
    key = os.environ.get('JUPITER_API_KEY')
    base = 'https://api.jup.ag' if key else 'https://lite-api.jup.ag'
    async with httpx.AsyncClient(timeout=20) as http:
        for attempt in range(3):   # 429 / 5xx = Jupiter busy (several coins at once) → short back-off, never a lost buy
            r = await http.request(method, base + path, headers={'x-api-key': key} if key else {}, **kw)
            if r.status_code != 429 and r.status_code < 500:
                break
            await asyncio.sleep(1.5 * (attempt + 1))
    try:
        data = r.json() if r.content else {}
    except ValueError:
        data = {}
    if r.status_code >= 400:
        raise HTTPException(400, f"{str(data.get('error') or data.get('errorMessage') or 'Jupiter route unavailable')[:140]} (HTTP {r.status_code})")
    return data


async def _fw_quote(order, cfg):
    """A REAL Jupiter quote for one keeper order (SOL → coin to buy, coin → SOL to sell). Read-only."""
    q = {'inputMint': _fw.SOL_MINT if order['side'] == 'buy' else order['mint'], 'outputMint': order['mint'] if order['side'] == 'buy' else _fw.SOL_MINT,
         'amount': str(order['lamports'] if order['side'] == 'buy' else order['atoms']), 'slippageBps': str(cfg['slippageBps'])}
    # 🎯 ONE-HOP route first (coin ⇄ SOL in one pool): a multi-hop route opens accounts for the coins it passes through (rent parked
    # until they close), builds transactions too big to send, and fails more often. Multi-hop only when one hop is missing or costly.
    try:
        direct = await _fw_jup('GET', '/swap/v1/quote', params={**q, 'onlyDirectRoutes': 'true'})
        if _fuse._f(direct.get('outAmount')) > 0 and _fuse._f(direct.get('priceImpactPct')) * 100 <= min(1.0, _fuse._f(cfg.get('maxImpactPct')) or 1.0):
            return direct
    except HTTPException:
        direct = None
    multi = await _fw_jup('GET', '/swap/v1/quote', params={**q, 'restrictIntermediateTokens': 'true'})
    if direct and _fuse._f(direct.get('outAmount')) >= _fuse._f(multi.get('outAmount')) * 0.995:
        return direct   # one hop pays (nearly) the same → still the cleaner transaction
    return multi


async def _fw_secure_buy(order, cfg, q):
    """🛡 A buy quote is safe when it is near the market price AND the coins really sell straight back (both read-only quotes).
    → (ok, why, sell-back %)"""
    try:
        back = await _fw_jup('GET', '/swap/v1/quote', params={'inputMint': order['mint'], 'outputMint': _fw.SOL_MINT, 'amount': str(q.get('outAmount')), 'slippageBps': str(cfg['slippageBps'])})
        back_l = _fuse._f(back.get('outAmount'))
    except HTTPException:
        back_l = None
    try:   # market = Jupiter's own price (what routes really pay); a DexScreener pair can lag on young coins
        jp = _fuse._f(((await _jup_prices([order['mint']])) or {}).get(order['mint']))
    except Exception:
        jp = 0.0
    ok_s, why_s = _fw.buy_safety({**order, 'midPx': jp or order.get('midPx')}, q.get('outAmount'), await _mint_decimals(order['mint']), back_l)
    return ok_s, why_s, None if back_l is None else round((back_l / max(1, order['lamports']) - 1) * 100, 2)


async def _fw_preflight(tid, buys, cfg, now):
    """🔒 Before a swap SELLS anything: can each new coin really be bought? Live pool (one fresh call for all), the owner's limits,
    then a real quote + the secure-buy checks. A coin that fails is booked as a refused buy (→ benched / re-picked) and returned, so
    the keeper keeps the old coin instead of selling it into cash. Read-only: nothing is signed here."""
    bad, live = set(), {}
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            mr = await http.get('https://api.dexscreener.com/latest/dex/pairs/solana/' + ','.join(sorted({str(o.get('pair')) for o in buys if o.get('pair')})[:12]))
        live = {p.get('pairAddress'): p for p in ((mr.json() if mr.status_code == 200 else {}) or {}).get('pairs') or [] if p}
    except Exception:
        return bad   # no reading = no verdict here: the buy's own final gate still fails closed
    for o in buys:
        row = {**o, 'card': tid, 'status': 'skipped', 'at': now}
        ok, why, snap = _fw.live_buy_market(o, live.get(o.get('pair')), cfg)
        row.update(snap)
        if ok:
            ok, why = _fw.check(row, cfg, _fw_load().get('ledger'), now)
            if not ok and any(x in why for x in _FW_NOT_COIN):
                continue   # a cap / pause is not the coin's fault — nothing to hold a sell for
        if ok and o.get('lamports', 0) > 0:
            try:
                q = await _fw_quote(o, cfg)
                ok, why, _back = await _fw_secure_buy(o, cfg, q)
                if ok and _fuse._f(q.get('priceImpactPct')) * 100 > cfg['maxImpactPct']:
                    ok, why = False, f"price impact {_fuse._f(q.get('priceImpactPct')) * 100:.2f}% > {cfg['maxImpactPct']:g}%"
            except HTTPException as e:
                if any(x in str(e.detail) for x in _FW_NOT_COIN):
                    continue
                ok, why = False, str(e.detail)[:140]
        if not ok:
            bad.add(o['mint'])
            row['err'] = f'{why} — checked before selling, the old coin is kept'[:160]
            async with _fw_lock:
                d = _fw_load()
                if not _fw.logged_recently(d.get('ledger'), row, now, 120):
                    _fw_record(d, row); _fw_save(d)
    return bad


def _fw_keep(d, tid, book):
    """Save a card's book without losing the miss / bench counts written meanwhile by _fw_record."""
    old = (d.get('books') or {}).get(tid) or {}
    return {**book, 'misses': old.get('misses', book.get('misses') or {}), 'benched': old.get('benched', book.get('benched') or {})}


_FW_NOT_COIN = ('not armed', 'paused', 'per-swap cap', 'daily cap', 'No Fuse wallet', 'signing not available', 'RPC pool', 'live market unavailable',
                '(HTTP 429)', '(HTTP 5')   # … and a busy Jupiter is never the coin's fault
_FW_KICK: dict = {}   # {'at': when a real buy was refused / failed} → the round loop re-picks that seat RETRY_SEC later, not a tick later


def _fw_record(d, row):
    if row.get('side') == 'buy' and row.get('status') in ('skipped', 'failed') and row.get('mint') and row.get('card') in (d.get('books') or {}) \
            and not any(x in str(row.get('err') or '') for x in _FW_NOT_COIN):   # 🪑 a coin that keeps failing its buy gets benched
        b, out = _fw.note_miss(d['books'][row['card']], row['mint'], _fuse._f(row.get('at')) or time.time(), str(row.get('err') or ''))
        d['books'][row['card']] = b
        _FW_KICK['at'] = _fuse._f(row.get('at')) or time.time()
        if out:
            print(f"fuse wallet: benched {row.get('symbol')} for 1h — {row.get('err')}")
    if row.get('id') and any(r.get('id') == row['id'] and r.get('status') == row.get('status') for r in (d.get('ledger') or [])[-50:]):
        return   # the same order outcome is booked once (two ticks resolving one tx can't double the trail)
    d['ledger'] = (d.get('ledger') or [])[-1999:] + [row]   # recent 2000 for fast reads …
    try:
        _store.Ledger(FUSE_WALLET_PATH).append(row)          # … and the append-only audit table keeps EVERY row forever
    except Exception as e:
        print('fuse wallet ledger:', e)


async def _fw_execute(tid, order, book, cfg, sol_px, liq):
    """One keeper order: real Jupiter quote → the owner's hard limits → Circle signs (Fuse wallet only) → we broadcast → the confirmed
    tx's balance changes ARE the fill. Every outcome goes to the audit ledger; fills + failures reach the owner's inbox."""
    if book.get('pending'):
        return book   # defense in depth: never overwrite the one in-flight signature with a second sell or buy
    now = time.time()
    # `card` must be present on every outcome. Without it, secure-quote refusals (price gap / no sell-back route) were logged but
    # never counted by _fw_record, so the same unsafe mint retried forever instead of reaching the existing bench-and-replace path.
    row = {**order, 'card': tid, 'liq': liq, 'status': 'quoted'}
    if order.get('side') == 'buy':
        # FINAL BUY GATE: cached radar liquidity is never authority for real money.
        # Re-fetch this exact pair immediately before quote/sign and fail closed if it cannot be verified.
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                mr = await http.get(f"https://api.dexscreener.com/latest/dex/pairs/solana/{order.get('pair')}")
            data = mr.json() if mr.status_code == 200 else {}
            live_pairs = (data or {}).get('pairs') or ([data.get('pair')] if isinstance(data, dict) and data.get('pair') else [])
            live_pair = next((p for p in live_pairs if p and p.get('pairAddress') == order.get('pair')), None)
            ok_live, why_live, snap = _fw.live_buy_market(order, live_pair, cfg)
        except Exception:
            ok_live, why_live, snap = False, 'live market unavailable — buy refused', {}
        row.update(snap)
        if not ok_live:
            row.update(status='skipped', err=why_live)
            async with _fw_lock:
                d = _fw_load()
                if not _fw.logged_recently(d.get('ledger'), row, now):
                    _fw_record(d, row)
                    _fw_save(d)
            return book
    async with _fw_lock:   # 🚦 limits a quote can't change (armed · paused · per-swap · daily cap · thin pool) are checked BEFORE quoting:
        d = _fw_load()        # no Jupiter calls, and the skip is booked once per 15 min instead of every tick (the cap retry loop)
        ok, why = _fw.check(row, cfg, d.get('ledger'), now)
        if not ok:
            skip = {**row, 'card': tid, 'status': 'skipped', 'err': why}
            if not _fw.logged_recently(d.get('ledger'), skip, now):
                _fw_record(d, skip); _fw_save(d)
            return book
    try:
        for attempt in range(3):   # 🔁 strong retry: a busy route gets fresh quotes, each with a little more slippage (≤ the 3% hard cap)
            try:
                q = await _fw_quote(order, {**cfg, 'slippageBps': min(300, int(cfg['slippageBps']) + 75 * attempt)})
                break
            except HTTPException:
                if attempt == 2:
                    raise
                await asyncio.sleep(1.5)
        row['impactPct'] = round(_fuse._f(q.get('priceImpactPct')) * 100, 3); row['quoteOut'] = q.get('outAmount')
        if order['side'] == 'buy':   # 🛡 secure buy: near market price + it really sells back (both read-only quotes)
            ok_s, why_s, row['sellBackPct'] = await _fw_secure_buy(order, cfg, q)
            if not ok_s:
                raise HTTPException(400, why_s)
        elif order['side'] == 'sell' and 'rug' not in str(order.get('why') or ''):   # 🛡 secure sell: the route must pay near the market price
            try:
                jp = _fuse._f(((await _jup_prices([order['mint']])) or {}).get(order['mint']))
            except Exception:
                jp = 0.0
            ok_s, why_s = _fw.sell_safety(order, q.get('outAmount'), sol_px, jp)
            if not ok_s:
                raise HTTPException(400, why_s)
    except HTTPException as e:
        row.update(status='skipped', err=str(e.detail)[:140])
        async with _fw_lock:   # the same refusal is booked once per 15 min (the keeper keeps retrying quietly)
            d = _fw_load()
            if row.get('side') == 'buy' or not _fw.logged_recently(d.get('ledger'), row, now):   # buy misses all count (2 → benched)
                _fw_record(d, row); _fw_save(d)
        return book
    async with _fw_lock:
        ok, why = _fw.check(row, cfg, _fw_load().get('ledger'), now, row['impactPct'])   # row carries the pool's liquidity
    if not ok or not _fw_signer_ready():
        row.update(status='skipped' if not ok else 'dry', err=why or 'signing not available — quoted only')
        async with _fw_lock:
            d = _fw_load(); _fw_record(d, row); _fw_save(d)
        return book
    async with _fw_lock:   # ⚡ txs that didn't land lately → this one pays a higher priority fee (24% of buys timed out at a flat fee)
        boost = _fw.landing_boost(_fw_load().get('ledger'), tid, now)
    try:
        for attempt in range(3):   # build + sign retried too (Jupiter / Circle blips); nothing is sent until a signed tx exists
            try:
                swap = await _fw_jup('POST', '/swap/v1/swap', json={'quoteResponse': q, 'userPublicKey': cfg['address'], 'wrapAndUnwrapSol': True, 'dynamicComputeUnitLimit': True,
                                                                    'prioritizationFeeLamports': {'priorityLevelWithMaxLamports': {'maxLamports': _fw.priority_cap(attempt, boost, sol_px), 'priorityLevel': 'veryHigh' if attempt or boost else 'high'}}})
                row['lastValidBlockHeight'] = swap.get('lastValidBlockHeight')
                signed = await _fw_sign(cfg, swap.get('swapTransaction'), f"FEELESS {tid} {order['side']} {order.get('symbol')}")
                break
            except HTTPException:
                if attempt == 2:
                    raise
                await asyncio.sleep(1.5)
                q = await _fw_quote(order, cfg)   # fresh quote for the rebuild
    except HTTPException as e:
        row.update(status='failed', err=f'build/sign: {str(e.detail)[:120]}')
        async with _fw_lock:
            d = _fw_load(); _fw_record(d, row); _fw_save(d)
        _fw_notify(row)
        return book
    for slip_try in range(3):   # price moved past slippage at send time (Jupiter 0x1771) → fresh quote with a bit more room, ≤ 3%
        sig = signed.get('signature') or signed.get('txHash')
        book = {**book, 'pending': {**row, 'sig': sig, 'status': 'sent', 'sentAt': now}}
        async with _fw_lock:   # pending is saved BEFORE the send: a crash mid-flight can never double-buy
            d = _fw_load(); d['books'][tid] = _fw_keep(d, tid, book); _fw_save(d)
        try:
            async with httpx.AsyncClient(timeout=15) as http:
                await _krpc(http, 'sendTransaction', [signed.get('signedTransaction'), {'encoding': 'base64', 'maxRetries': 3, 'preflightCommitment': 'confirmed'}])
            _fw_raw_keep(sig, signed.get('signedTransaction'))   # 📡 passed simulation → re-sent to every node until it lands or expires
            break
        except Exception as e:
            msg = str(e)
            if 'simulation failed' not in msg.lower():
                _fw_raw_keep(sig, signed.get('signedTransaction'))   # node trouble, not a bad tx → the other nodes still get it
                print('fuse wallet send:', msg[:200]); break   # network trouble: the tx may still land → resolve decides
            # simulation failed = this tx can NEVER land → clear pending now (no 2-min wait), maybe retry with more slippage
            book = {**book, 'pending': None}
            async with _fw_lock:
                d = _fw_load(); d['books'][tid] = _fw_keep(d, tid, book); _fw_save(d)
            slip = min(300, int(cfg['slippageBps']) + 75 * (slip_try + 1))
            if ('0x1771' not in msg and '6001' not in msg) or slip_try == 2:
                row.update(status='failed', err=('slippage exceeded at send' if ('0x1771' in msg or '6001' in msg) else 'simulation failed') + f' (tried ≤{slip / 100:.2f}%)')
                async with _fw_lock:
                    d = _fw_load(); _fw_record(d, row); _fw_save(d)
                _fw_notify(row)
                return book
            try:
                q = await _fw_quote(order, {**cfg, 'slippageBps': slip})
                swap = await _fw_jup('POST', '/swap/v1/swap', json={'quoteResponse': q, 'userPublicKey': cfg['address'], 'wrapAndUnwrapSol': True, 'dynamicComputeUnitLimit': True,
                                                                    'prioritizationFeeLamports': {'priorityLevelWithMaxLamports': {'maxLamports': _fw.priority_cap(slip_try + 1, boost, sol_px), 'priorityLevel': 'veryHigh'}}})
                row['lastValidBlockHeight'] = swap.get('lastValidBlockHeight')
                signed = await _fw_sign(cfg, swap.get('swapTransaction'), f"FEELESS {tid} {order['side']} {order.get('symbol')} retry")
                row['retrySlipBps'] = slip
            except HTTPException as e2:
                row.update(status='failed', err=f'retry build/sign: {str(e2.detail)[:100]}')
                async with _fw_lock:
                    d = _fw_load(); _fw_record(d, row); _fw_save(d)
                return book
    return await _fw_resolve(tid, book, cfg, sol_px, wait=40)


C2C_COOL_SEC = 600   # after a one-transaction swap fails, that card does plain two-step swaps for 10 minutes


async def _fw_execute_swap(tid, sell, buy, book, cfg, sol_px, liq):
    """🔀 ONE transaction: the old coin straight into the new one. Decided BEFORE anything moves — three read-only quotes (old → SOL,
    SOL → new, old → new); the one-step route is used only when it delivers at least as many coins as the two swaps would and its
    impact is ≤ 4% (`fuse_wallet.c2c_ok`), the new coin passes the live-pool, limit and secure-buy checks, and the old coin's sale
    is near market. Returns the book when a swap was sent (or settled); None = not suitable → the keeper does the two swaps."""
    if book.get('pending') or not _fw_signer_ready():
        return None
    now = time.time()
    d0 = _fw_load()
    if any(r.get('card') == tid and r.get('side') == 'swap' and r.get('status') == 'failed' and now - _fuse._f(r.get('at')) < C2C_COOL_SEC for r in (d0.get('ledger') or [])[-40:]):
        return None
    brow = {**buy, 'usd': sell['usd'], 'liq': liq, 'card': tid}
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            mr = await http.get(f"https://api.dexscreener.com/latest/dex/pairs/solana/{buy.get('pair')}")
        live_pair = next((p for p in ((mr.json() if mr.status_code == 200 else {}) or {}).get('pairs') or [] if p and p.get('pairAddress') == buy.get('pair')), None)
        ok, _why, snap = _fw.live_buy_market(buy, live_pair, cfg)
        brow.update(snap)
        if ok:
            ok, _why = _fw.check(brow, cfg, d0.get('ledger'), now)
        if not ok:
            return None   # the normal path books the refusal (and benches the coin)
        q_sell = await _fw_quote(sell, cfg)
        lam = int(_fuse._f(q_sell.get('outAmount')))
        if lam <= 0:
            return None
        q_buy = await _fw_quote({**buy, 'lamports': lam}, cfg)
        q_dir = await _fw_jup('GET', '/swap/v1/quote', params={'inputMint': sell['mint'], 'outputMint': buy['mint'], 'amount': str(sell['atoms']),
                                                               'slippageBps': str(cfg['slippageBps']), 'restrictIntermediateTokens': 'true'})
        impact = round(_fuse._f(q_dir.get('priceImpactPct')) * 100, 3)
        ok, why = _fw.c2c_ok(q_dir.get('outAmount'), q_buy.get('outAmount'), impact)
        if not ok or impact > cfg['maxImpactPct']:
            return None
        ok_s, _why_s, back = await _fw_secure_buy({**buy, 'lamports': lam}, cfg, q_dir)   # near market + really sells back
        if not ok_s:
            return None
        if 'rug' not in str(sell.get('why') or ''):
            jp = _fuse._f(((await _jup_prices([sell['mint']])) or {}).get(sell['mint']))
            if not _fw.sell_safety(sell, q_sell.get('outAmount'), sol_px, jp)[0]:
                return None
        async with _fw_lock:
            boost = _fw.landing_boost(_fw_load().get('ledger'), tid, now)
        swap = await _fw_jup('POST', '/swap/v1/swap', json={'quoteResponse': q_dir, 'userPublicKey': cfg['address'], 'wrapAndUnwrapSol': True, 'dynamicComputeUnitLimit': True,
                                                            'prioritizationFeeLamports': {'priorityLevelWithMaxLamports': {'maxLamports': _fw.priority_cap(0, boost, sol_px), 'priorityLevel': 'veryHigh' if boost else 'high'}}})
        signed = await _fw_sign(cfg, swap.get('swapTransaction'), f"FEELESS {tid} swap {sell.get('symbol')} to {buy.get('symbol')}")
    except Exception as e:
        print('fuse wallet c2c (falling back to two swaps):', str(getattr(e, 'detail', e))[:120])
        return None
    sig = signed.get('signature') or signed.get('txHash')
    row = {'id': f"{tid}:{now:.0f}:x:{sell['mint'][:6]}", 'card': tid, 'side': 'swap', 'mint': sell['mint'], 'pair': sell.get('pair'), 'symbol': sell.get('symbol'),
           'atoms': int(sell['atoms']), 'decimals': sell.get('decimals'), 'toMint': buy['mint'], 'toPair': buy.get('pair'), 'toSymbol': buy.get('symbol'),
           'toMidPx': brow.get('midPx') or buy.get('midPx'), 'usd': sell['usd'], 'at': now, 'why': f'🔀 one transaction — {why}', 'liq': brow.get('liq'),
           'minIn': int(_fuse._f(q_dir.get('otherAmountThreshold'))), 'quoteOut': q_dir.get('outAmount'), 'impactPct': impact, 'sellBackPct': back,
           'lastValidBlockHeight': swap.get('lastValidBlockHeight'), **({'cardPays': True} if sell.get('cardPays') else {})}
    book = {**book, 'pending': {**row, 'sig': sig, 'status': 'sent', 'sentAt': now}}
    async with _fw_lock:   # pending is saved BEFORE the send: a crash mid-flight can never double-trade
        d = _fw_load(); d['books'][tid] = _fw_keep(d, tid, book); _fw_save(d)
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            await _krpc(http, 'sendTransaction', [signed.get('signedTransaction'), {'encoding': 'base64', 'maxRetries': 3, 'preflightCommitment': 'confirmed'}])
        _fw_raw_keep(sig, signed.get('signedTransaction'))
    except Exception as e:
        if 'simulation failed' in str(e).lower():   # this tx can never land → clear it now; the two-step path takes over next tick
            book = {**book, 'pending': None}
            async with _fw_lock:
                d = _fw_load(); d['books'][tid] = _fw_keep(d, tid, book)
                _fw_record(d, {**row, 'status': 'failed', 'err': 'one-transaction swap failed simulation — doing two swaps'}); _fw_save(d)
            return book
        _fw_raw_keep(sig, signed.get('signedTransaction'))   # node trouble: it may still land → resolve decides
    return await _fw_resolve(tid, book, cfg, sol_px, wait=40)


def _fw_notify(row):
    """Every real fill / failure on a tier card → the owner wallets' inbox (audit trail link). No P&L in the text.
    A failing coin retries every tick, so its failure notice goes out once an hour, not once per try."""
    once = f"fw-{row.get('id')}-{row.get('status')}" if row.get('status') != 'failed' else f"fw-fail-{row.get('card')}-{row.get('mint')}-{int(time.time() // 3600)}"
    word = {'filled': '✅', 'failed': '⚠'}.get(row.get('status'), 'ℹ')
    for w in _owner_wallets():
        notify(w, 'fuse-card', f"{word} Fuse wallet · {row.get('card')}: {row.get('side')} ${row.get('symbol') or ''} {row.get('status')}{(' — ' + row['err']) if row.get('err') else ''}",
               url='/terminal/hq?tab=fuse', push=False, once=once, meta={'claim': 'Keeper order', 'source': 'Fuse wallet audit trail'})


_FW_RAW: dict = {}   # sig → (signed tx, kept at): in memory only, a blockhash lives ~90s


def _fw_raw_keep(sig, raw):
    now = time.time()
    for k in [k for k, v in _FW_RAW.items() if now - v[1] > 180]:
        _FW_RAW.pop(k, None)
    if sig and raw:
        _FW_RAW[sig] = (raw, now)


async def _fw_rebroadcast(http, sig):
    """📡 The perma-fix for "expired" buys / sells: the SAME signed tx goes to every RPC node again (one signature can only land once)."""
    raw = (_FW_RAW.get(sig) or (None,))[0]
    if not raw or os.environ.get('PYTEST_CURRENT_TEST'):
        return 0
    try:
        return await _rpc_broadcast(http, raw)
    except Exception:
        return 0


async def _fw_resolve(tid, book, cfg, sol_px, wait=0):
    """Settle a sent order from the chain. RPC absence is never failure: keep the pending lock until the chain returns a
    transaction, so a delayed buy/sell cannot be submitted twice. Only validated confirmed balance changes mutate the book."""
    p = book.get('pending')
    if not p:
        return book
    tx = None
    async with httpx.AsyncClient(timeout=15) as http:
        for _ in range(max(1, int(wait / 2))):
            try:
                tx = await _krpc(http, 'getTransaction', [p['sig'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
            except Exception:
                tx = None
            if tx:
                break
            await _fw_rebroadcast(http, p['sig'])
            if wait <= 0:
                break
            await asyncio.sleep(2)
    if not tx:
        failed, chain_err = False, None
        try:
            async with httpx.AsyncClient(timeout=15) as http:
                st = await _krpc(http, 'getSignatureStatuses', [[p['sig']], {'searchTransactionHistory': True}])
                status = ((st or {}).get('value') or [None])[0]
                failed = bool(status and status.get('err'))
                chain_err = status.get('err') if failed else None
                if not failed and p.get('lastValidBlockHeight') is not None:
                    height = await _krpc(http, 'getBlockHeight', [{'commitment': 'confirmed'}])
                    failed = int(height or 0) > int(p['lastValidBlockHeight'])
        except Exception:
            pass
        if not failed:
            return book   # unknown is not failed; retain the lock and retry the same signature next tick
        row = {k: v for k, v in p.items() if k != 'sentAt'}
        # two different problems, two different fixes: "expired" = never reached a block (landing) · "failed on-chain" = it ran and
        # reverted (price moved past slippage) — the audit trail now says which
        row.update(status='failed', err=f'failed on-chain: {str(chain_err)[:60]}' if chain_err else 'transaction expired — never landed')
        _FW_RAW.pop(p.get('sig'), None)
        book = {**book, 'pending': None}
        async with _fw_lock:
            d = _fw_load(); d['books'][tid] = _fw_keep(d, tid, book); _fw_record(d, row); _fw_save(d)
        _fw_notify(row)
        return book
    if p.get('side') == 'swap':   # 🔀 one transaction, two coins: booked as a sell row + a buy row on the same signature
        _FW_RAW.pop(p.get('sig'), None)
        base = {k: v for k, v in p.items() if k not in ('sentAt', 'toMidPx')}
        sfill = None if (tx.get('meta') or {}).get('err') else _fw.swap_fill_from_meta(tx, cfg['address'], p['mint'], p['toMint'])
        bad = _fw.swap_fill_error(p, sfill, book) if sfill else ''
        rows_ = []
        if sfill and not bad:
            try:
                px_in = _fuse._f(((await _jup_prices([p['toMint']])) or {}).get(p['toMint']))
            except Exception:
                px_in = 0.0
            book, f = _fw.apply_swap(book, p, sfill, sol_px, px_in or _fuse._f(p.get('toMidPx')))
            fee_usd = round(sfill['feeSol'] * sol_px, 6)
            rows_ = [{**base, 'id': p['id'] + ':s', 'side': 'sell', 'status': 'filled', 'usd': f['usd'], 'proceedsUsd': f['usd'], 'costUsd': f['costUsd'], 'realizedPnlUsd': f['realizedPnlUsd'],
                      'units': f['unitsOut'], 'sol': 0.0, 'feeSol': sfill['feeSol'], 'feeUsd': fee_usd, 'openedSol': 0.0, 'why': f"🔀 swapped straight into ${p.get('toSymbol')} (one transaction)"},
                     {**base, 'id': p['id'] + ':b', 'side': 'buy', 'mint': p['toMint'], 'pair': p.get('toPair'), 'symbol': p.get('toSymbol'), 'status': 'filled', 'usd': f['usd'],
                      'units': f['unitsIn'], 'px': f['px'], 'sol': 0.0, 'feeSol': 0.0, 'feeUsd': 0.0, 'why': f"🔀 swapped straight from ${p.get('symbol')} (one transaction)"}]
            _FW_GAS['at'] = 0.0; _FW_BAL.pop('bal', None)
        elif bad:
            rows_ = [{**base, 'status': 'failed', 'err': bad}]
            book = {**book, 'halt': True, 'haltWhy': bad}
        else:
            rows_ = [{**base, 'status': 'failed', 'err': 'tx failed on-chain'}]
        book = {**book, 'pending': None}
        async with _fw_lock:
            d = _fw_load(); d['books'][tid] = _fw_keep(d, tid, book)
            for r_ in rows_:
                _fw_record(d, r_)
            _fw_save(d)
        _fw_notify(rows_[0])
        return book
    fill = _fw.fill_from_meta(tx, cfg['address'], p['mint']) if tx else None
    _FW_RAW.pop(p.get('sig'), None)
    row = {k: v for k, v in p.items() if k != 'sentAt'}
    mismatch = _fw.fill_error(p, fill, book) if not ((tx.get('meta') or {}).get('err')) else ''
    if fill and not mismatch:
        if p.get('side') == 'sell':   # 🧾 use the confirmed token debit, never the requested/quoted amount
            row['costUsd'] = _fw.cost_of(book, p['mint'], abs(int(fill.get('atoms') or 0)))
        book, f = _fw.apply_fill(book, p, fill, sol_px)
        row.update(status='filled', px=f['px'], units=f['units'], usd=f['usd'] or row['usd'], sol=f['sol'], feeSol=fill['feeSol'], feeUsd=round(fill['feeSol'] * sol_px, 6),
                   openedSol=_fuse._f(fill.get('openedSol')))
        if p.get('side') == 'sell':
            row.update(proceedsUsd=f['usd'], realizedPnlUsd=round(f['usd'] - row['costUsd'], 6))
        # The cached wallet balance predates this confirmed fill. Force the keeper's
        # post-tick balance read so a sold token cannot remain displayed as recoverable.
        _FW_GAS['at'] = 0.0
        _FW_BAL.pop('bal', None)
    elif mismatch:
        row.update(status='failed', err=mismatch)
        book = {**book, 'halt': True, 'haltWhy': mismatch}
    else:
        row.update(status='failed', err='tx failed on-chain')
    book = {**book, 'pending': None}
    async with _fw_lock:
        d = _fw_load(); d['books'][tid] = _fw_keep(d, tid, book); _fw_record(d, row); _fw_save(d)
    _fw_notify(row)
    return book


_fw_tick_lock = asyncio.Lock()


async def _fw_tick(now):
    """ONE keeper at a time: the round bell and the warm loop both call this after their tier tick — two keepers at once traded the
    same orders twice (sold WETH ×2, bought SPEC ×2 at 14:56). A tick that finds one running skips; the next tick catches up."""
    if _fw_tick_lock.locked():
        return 0
    async with _fw_tick_lock:
        n = await _fw_tick_inner(now)
        if time.time() - _FW_GAS.get('at', 0) > 60:   # ⛽ one balance read a minute (never per viewer)
            try:
                cfg = _fw_cfg()
                if cfg.get('address'):
                    bal = await _fw_balances(cfg['address'])
                    _FW_GAS.update(sol=bal['sol'], at=time.time()); _FW_BAL.update(bal=bal, at=time.time(), addr=cfg['address'])
                    async with _fw_lock:   # 🧹 adopt keeper coins no card books (they sell back to SOL inside their card next tick)
                        d = _fw_load()
                        missing = _fw.reconcile(bal.get('tokens'), d['books'])
                        sol_short = _fw.reconcile_sol(bal.get('sol'), d['books'])
                        if missing or sol_short:   # confirmed wallet balances beat our books; stop every affected card before another order
                            bad = {x['mint'] for x in missing}
                            for tid, b in d['books'].items():
                                if sol_short or bad.intersection((b.get('legs') or {})):
                                    why = 'confirmed wallet SOL is below card books' if sol_short else 'confirmed wallet token balance is below card books'
                                    d['books'][tid] = {**b, 'halt': True, 'haltWhy': why}
                        for tid, b in list(d['books'].items()):   # 🔓 an automatic halt lifts once the wallet shows it's fixed
                            if _fw.halt_cleared(b, sol_short, [x['mint'] for x in missing]):
                                d['books'][tid] = {**b, 'halt': False, 'haltWhy': None}
                                _fw_record(d, {'id': f'unhalt:{tid}:{time.time():.0f}', 'card': tid, 'side': 'fix', 'at': time.time(), 'status': 'done',
                                               'why': f"🔓 resumed by itself — {b.get('haltWhy')} is fixed (wallet and card books match)"})
                        if not sol_short and not missing:   # 🏦 rent is the reserve's: old card-paid deposits go back to work in the card
                            d['books'], freed = _fw.release_rent_deposits(d['books'], _fw.free_sol(bal.get('sol'), d['books'], cfg.get('reserveSol')))
                            for tid, sol_ in freed.items():
                                _fw_record(d, {'id': f'rentfree:{tid}:{time.time():.0f}', 'card': tid, 'side': 'fix', 'sol': sol_, 'at': time.time(), 'status': 'done',
                                               'why': f'🏦 {sol_:.5f} SOL of coin-account rent moved to the wallet reserve — it is card cash again (the card never pays rent now)'})
                        for st in _fw.strays(bal.get('tokens'), bal.get('decimals'), d['books'], d['ledger'], time.time()):
                            d['books'][st['card']] = _fw.adopt(d['books'][st['card']], st)
                            _fw_record(d, {'card': st['card'], 'side': 'adopt', 'mint': st['mint'], 'symbol': st['symbol'], 'atoms': st['atoms'], 'usd': 0.0, 'at': time.time(),
                                           'status': 'done', 'why': '🧹 recovered: keeper coins no card counted — sold back to SOL inside the card'})
                            print(f"fuse wallet: adopted stray {st['symbol']} into {st['card']}")
                        _fw_save(d)
                    await _fw_deposit_scan(cfg, time.time())
                    _rpc_quota_notice()
            except Exception as e:
                print('fuse wallet gas:', e)
        return n


FUSE_DEPOSITS_PATH = DATA_DIR / 'fuse_deposits.json'   # {'address', 'cursor': newest sig seen, 'rows': [{sig, at, sol, from}]} — chain-audited
_fw_dep_at = {'t': 0.0}


async def _fw_deposit_scan(cfg, now):
    """💰 Every 10 min: new signatures on the Fuse wallet that the keeper did NOT make are read once; a tx the wallet did not sign that
    raised its SOL is a DEPOSIT (booked forever + owner inbox). This is what makes "unassigned SOL" explainable instead of a mystery."""
    if now - _fw_dep_at['t'] < 600 or not cfg.get('address'):
        return 0
    _fw_dep_at['t'] = now
    dd = _json_load(FUSE_DEPOSITS_PATH, {})
    if dd.get('address') != cfg['address']:
        dd = {'address': cfg['address'], 'cursor': None, 'rows': []}
    ours = {r.get('sig') for r in _fw_load().get('ledger') or [] if r.get('sig')}
    added = 0
    async with httpx.AsyncClient(timeout=15) as http:
        sigs = await _krpc(http, 'getSignaturesForAddress', [cfg['address'], {'limit': 40, **({'until': dd['cursor']} if dd.get('cursor') else {})}]) or []
        have = {r.get('sig') for r in dd['rows']}
        for srow in sigs[::-1]:   # oldest first
            sig = srow.get('signature')
            if not sig or srow.get('err') or sig in ours or sig in have:
                continue
            tx = await _krpc(http, 'getTransaction', [sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
            dep = _fw.deposit_from_tx(tx, cfg['address'])
            if dep:
                dd['rows'].append({'sig': sig, 'at': (tx or {}).get('blockTime') or now, **dep}); added += 1
                for w in _owner_wallets():
                    notify(w, 'fuse-card', f"💰 Fuse wallet received {dep['sol']:.4f} SOL — it is UNASSIGNED until you put it in a card.", url='/terminal/hq?tab=fuse',
                           push=False, once=f'fw-dep-{sig[:16]}', meta={'claim': 'Deposit', 'source': 'Confirmed on-chain transfer'})
    if sigs:
        dd['cursor'] = sigs[0].get('signature')
    if sigs or added:
        _json_save(FUSE_DEPOSITS_PATH, dd)
    return added


_FW_GAS = {}
_FW_BAL = {}   # last good full balance read of the Fuse wallet (shown while the RPC is rate-limited)


async def _fw_tick_inner(now):
    """After every tier tick: each funded card's REAL book is moved to what the engine says it holds (sells, then buys), then the
    card shows its true coins, entries and fees. Paused / unarmed / missing-coin cards wait. Paper learns from the fills."""
    await _fw_signer_check()
    d = _fw_load()
    cal = _fw_calibration(d)
    _prime.IMPACT_MULT = cal['impactMult']; _prime.SPREAD = cal.get('spread') or 0.0
    cfg = _fw.clean_cfg(d.get('cfg') or {})
    if not d['books'] or not cfg['armed'] or cfg['paused'] or not cfg['address']:
        return 0
    hq = _json_load(FUSE_HQ_PATH, {}); cards = (hq.get('prime') or {}).get('cards') or {}
    pairs_ = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': pa} for tid, b in d['books'].items()
                                for pa in [l['pairAddress'] for l in (cards.get(tid) or {}).get('legs') or []] + [l.get('pair') for l in (b.get('legs') or {}).values() if l.get('pair')]])
    px = {k: _fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}
    jup = await _jup_prices([l.get('mint') for c in cards.values() for l in c.get('legs') or []] +
                            [m for b in d['books'].values() for m in (b.get('legs') or {})])
    for c in cards.values():
        for l in c.get('legs') or []:
            if jup.get(l.get('mint')):
                px[l['pairAddress']] = jup[l['mint']]
    for b in d['books'].values():
        for mint, l in (b.get('legs') or {}).items():
            if jup.get(mint) and l.get('pair'):
                px[l['pair']] = jup[mint]
    liqs = {k: _fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_.items()}
    sol_px = await _sol_usd_live()
    done = 0
    for tid, book in list(d['books'].items()):
        card = cards.get(tid)
        if not card or (book.get('halt') and not _fw.halt_allows_sells(book)):
            continue
        if book.get('pending'):
            book = await _fw_resolve(tid, book, cfg, sol_px)
            if book.get('pending'):
                continue
        equity_usd = _fw.book_value(book, px, sol_px)
        book, returned_sol = _fw.enforce_principal_floor(book, equity_usd, sol_px)
        if returned_sol > 0:
            equity_usd = _fw.book_value(book, px, sol_px)
        book = _fw.bank(book, card.get('walletUsd'), sol_px, equity_usd)
        want = {**card, 'legs': []} if book.get('defund') else card
        # 🔒 check the buy BEFORE the sell: a swap whose new coin can't be bought keeps the old coin (≤ 45s) while the engine re-picks
        plan0 = _fw.orders(tid, want, book, px, sol_px, cfg, now, count_sells=True)
        new_buys = [o for o in plan0 if o['side'] == 'buy' and not _fw.held_units(book, o['mint'])]
        hold = False
        # only a SWAP-OUT waits for its replacement — a cut of a coin that stays (bank at the lock, 💰 skim, ✂) never does
        swap_out = lambda o: o['side'] == 'sell' and not o.get('manualCash') and o.get('why') == 'not on the card any more'
        if new_buys and any(swap_out(o) for o in plan0) and not book.get('defund') and not book.get('halt'):
            book, hold = _fw.hold_sells(book, card, await _fw_preflight(tid, new_buys, cfg, now), now)
        elif book.get('sellHoldAt'):
            book, _h = _fw.hold_sells(book, card, set(), now)
        if cfg.get('coinToCoin') and not hold and not book.get('halt') and not book.get('defund') and not book.get('pending'):
            for s_o, b_o in _fw.swap_pairs(plan0, book)[:1]:   # 🔀 one swap per tick, like every other order
                leg_liq = next((_fuse._f(l.get('liqNow')) or _fuse._f(l.get('liq')) for l in card.get('legs') or [] if l.get('mint') == b_o.get('mint')), 0.0)
                done_ = await _fw_execute_swap(tid, {**s_o, 'cardPays': int(card.get('rounds') or 0) >= 5}, b_o, book, cfg, sol_px, liqs.get(b_o.get('pair')) or leg_liq)
                if done_ is not None:
                    book = done_
        for side in (('sell',) if book.get('halt') or book.get('pending') else ('sell', 'buy')):   # ⏸ halted = sells only (owner's queued sells still land)
            for o in [{**x, 'cardPays': int(card.get('rounds') or 0) >= 5} for x in _fw.orders(tid, want, book, px, sol_px, cfg, now, count_sells=side == 'sell') if x['side'] == side]:
                if hold and swap_out(o):
                    continue   # the replacement isn't buyable yet → this coin stays (cuts and the owner's own ✂ always go through)
                leg_liq = next((_fuse._f(l.get('liqNow')) or _fuse._f(l.get('liq')) for l in card.get('legs') or [] if l.get('mint') == o.get('mint')), 0.0)
                book = await _fw_execute(tid, o, book, cfg, sol_px, liqs.get(o.get('pair')) or leg_liq)   # pair read blank → the engine's own liquidity reading
                if book.get('pending'):
                    break
            if book.get('pending'):
                break   # one card, one in-flight transaction; a pending sell must never be overwritten by a buy
            if side == 'sell' and not book.get('pending'):
                # Confirmed sell proceeds fund payouts first. Paid-out SOL is segregated before any subsequent compound buys.
                equity_usd = _fw.book_value(book, px, sol_px)
                book, returned_sol = _fw.enforce_principal_floor(book, equity_usd, sol_px)
                if returned_sol > 0:
                    equity_usd = _fw.book_value(book, px, sol_px)
                book = _fw.bank(book, card.get('walletUsd'), sol_px, equity_usd)
                # 🔒 SELL-BEFORE-BUY BARRIER: if ANY sell is still required after the sell pass
                # (route refused, tx expired, partial max-swap chunk, etc.), do not buy anything yet.
                # The next keeper tick retries the remaining sell first. This prevents a failed sell
                # from leaving the old coin held while spare SOL buys its replacement too.
                remaining_sells = [x for x in _fw.orders(tid, want, book, px, sol_px, cfg, time.time(), count_sells=True) if x['side'] == 'sell']
                if remaining_sells:
                    break
        written_off = []
        if book.get('defund') and not book.get('pending'):   # 🧹 a dead coin's dust can't be sold — it must not keep "selling…" on screen forever
            book, written_off = _fw.write_off_dust(book, px)
        async with _fw_lock:
            d2 = _fw_load()
            for w in written_off:
                _fw_record(d2, {'card': tid, 'side': 'writeoff', 'mint': w['mint'], 'pair': w.get('pair'), 'symbol': w['symbol'], 'usd': w['usd'], 'costUsd': w['costUsd'], 'at': now, 'status': 'done',
                                'why': f"dead coin written off: worth ${w['usd']:.4f} (cost ${w['costUsd']:.2f}) — too small for any route; the coins stay in the wallet"})
            if book.get('defund') and not book.get('legs') and not book.get('pending'):
                d2['books'].pop(tid, None)
                _fw_record(d2, {'card': tid, 'side': 'defund', 'usd': round(_fw.book_value(book, px, sol_px), 4), 'at': now, 'status': 'done'})
            else:
                d2['books'][tid] = _fw_keep(d2, tid, book)
            _fw_save(d2)
        async with _admin_lock:
            h = _json_load(FUSE_HQ_PATH, {}); cs = (h.get('prime') or {}).get('cards') or {}
            if cs.get(tid):
                still_real = tid in _fw_load()['books']
                was_label = cs[tid].get('label')
                cs[tid] = _fw.sync_card(cs[tid], book, px, sol_px) if still_real else _fw.back_to_paper(cs[tid], _fw.book_value(book, px, sol_px), now)
                _json_save(FUSE_HQ_PATH, h)
                if not still_real and cs[tid].get('runs'):   # 📜 the sell-all IS the end of a real run — it goes on the permanent record
                    try:                                       # (the tier tick only records runs it ends itself, so this one was lost)
                        _store.Ledger(CARD_RECORDS_PATH, table='runs').append({**cs[tid]['runs'][-1], 'card': tid, 'label': was_label, 'real': True, 'closed': True})
                    except Exception as e:
                        print('card records (defund):', e)
        done += 1
    await _fw_close_empty(cfg, now)
    return done


_fw_close_at = {'t': 0.0}


async def _fw_rent_credit(cfg):
    """♻ A CONFIRMED close puts its rent back into the card that opened those coin accounts (`fuse_wallet.rent_back`); a close that
    failed or never landed credits nothing. Each close is credited once (its 'credited' row)."""
    d = _fw_load()
    if not d.get('rentFix1'):   # 🩹 undo the first rule's phantom credits (every historical refund was credited into the card again)
        sol_px0 = await _sol_usd_live()
        if sol_px0 <= 0:
            return
        async with _fw_lock:
            d = _fw_load()
            d['books'], gone = _fw.undo_rent_credits(d['books'], d['ledger'], sol_px0)
            bal_sol = _FW_GAS.get('sol')
            for tid, b in d['books'].items():   # the shortage that halted the card is gone → it may trade again (owner sees why)
                if b.get('halt') and 'below card books' in str(b.get('haltWhy') or '') and bal_sol is not None and not _fw.reconcile_sol(bal_sol, d['books']):
                    d['books'][tid] = {**b, 'halt': False, 'haltWhy': None}
            for tid, sol in gone.items():
                _fw_record(d, {'id': f'rentfix:{tid}', 'card': tid, 'side': 'fix', 'sol': -sol, 'usd': round(-sol * sol_px0, 4), 'at': time.time(), 'status': 'done',
                               'why': '🩹 removed rent credited by mistake (old refunds the reserve had already re-used) — card books match the wallet again'})
            d['rentFix1'] = time.time()
            _fw_save(d)
        if gone:
            _fw_notify({'card': next(iter(gone)), 'side': 'fix', 'status': 'done', 'usd': 0, 'why': 'rent credit mistake repaired — card books match the wallet again'})
    if not d.get('rentFix2'):   # 🩹 the first repair priced the removed SOL at today's price → PUT IN drifted (5.00 read 4.82): rebuild it
        async with _fw_lock:
            d = _fw_load()
            for tid, b in d['books'].items():
                if any(r.get('id') == f'rentfix:{tid}' for r in d['ledger']):
                    f_ = _fw.funded_from_ledger(b, d['ledger'], tid)
                    if f_ > 0:
                        d['books'][tid] = {**b, 'fundedUsd': f_}
            d['rentFix2'] = time.time()
            _fw_save(d)
    if not d.get('routeFix1') and not os.environ.get('PYTEST_CURRENT_TEST'):
        # 🩹 sells whose multi-hop route parked rent in accounts it opened were booked as price losses (baton −87%, ORCA −50%). That SOL
        # came back to the wallet when the accounts closed; it is the card's sale money → back into card cash, once, from the chain.
        try:
            found, checked = {}, {}
            sol_px0 = await _sol_usd_live()
            if sol_px0 <= 0:
                raise RuntimeError('no SOL price')
            async with httpx.AsyncClient(timeout=20) as http:
                for r in _fw.route_fix_rows(d['ledger'], time.time() - 3 * 86400)[-40:]:
                    tx = await _krpc(http, 'getTransaction', [r['sig'], {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
                    if not tx:
                        raise RuntimeError('tx not readable yet')
                    checked[r['sig']] = _fw.opened_sol(tx, cfg['address'])
                    await asyncio.sleep(0.6)   # paced: this may run on public nodes
                    if checked[r['sig']] > 0:
                        found[r.get('card')] = round(found.get(r.get('card'), 0.0) + checked[r['sig']], 9)
            async with _fw_lock:
                d = _fw_load()
                bal_sol = _FW_GAS.get('sol')
                if found and bal_sol is None:
                    raise RuntimeError('wallet balance not read yet')
                d['books'], credits = _fw.route_fix(d['books'], found, _fw.free_sol(bal_sol, d['books'], cfg.get('reserveSol')) if found else 0.0, sol_px0)
                for r in d['ledger']:
                    if r.get('sig') in checked and r.get('side') == 'sell':
                        r['openedSol'] = checked[r['sig']]
                        if checked[r['sig']] > 0 and r.get('card') in credits:   # the trail shows the true price result of that sale
                            r['usd'] = r['proceedsUsd'] = round(_fuse._f(r.get('usd')) + checked[r['sig']] * sol_px0, 6)
                            r['realizedPnlUsd'] = round(r['usd'] - _fuse._f(r.get('costUsd')), 6)
                for tid, sol in credits.items():
                    _fw_record(d, {'id': f'routefix:{tid}', 'card': tid, 'side': 'fix', 'sol': sol, 'usd': round(sol * sol_px0, 4), 'at': time.time(), 'status': 'done',
                                   'why': f'🩹 {sol:.5f} SOL of route rent was booked as a sale loss — it came back to the wallet and is back in this card'})
                if not found or credits:
                    d['routeFix1'] = time.time()
                _fw_save(d)
            if credits:   # the run that restarted on the short value gets the same $ in its baseline: the money is back, it is not a gain
                async with _admin_lock:
                    h = _json_load(FUSE_HQ_PATH, {}); cs = (h.get('prime') or {}).get('cards') or {}
                    for tid, sol in credits.items():
                        if cs.get(tid):
                            for k_ in ('startUsd', 'roundStartUsd', 'dayStartUsd'):
                                if cs[tid].get(k_) is not None:
                                    cs[tid][k_] = round(_fuse._f(cs[tid][k_]) + sol * sol_px0, 4)
                    _json_save(FUSE_HQ_PATH, h)
            for tid in credits:
                _fw_notify({'card': tid, 'side': 'fix', 'status': 'done', 'usd': 0, 'why': 'route rent booked as a loss is back in the card'})
        except Exception as e:
            print('fuse wallet route fix (retries next sweep):', str(e)[:120])
    if not d.get('cashFix1'):   # 🩹 recovery sells used to park their SOL as "owner's held cash" (never re-spent) → back to work, once
        async with _fw_lock:
            d = _fw_load()
            for tid, b in d['books'].items():
                held = _fuse._f(b.get('manualCashSol'))
                if held > 0:
                    d['books'][tid] = {**b, 'manualCashSol': 0.0}
                    _fw_record(d, {'id': f'cashfix:{tid}', 'card': tid, 'side': 'fix', 'sol': held, 'at': time.time(), 'status': 'done',
                                   'why': '♻ recovered-coin cash released — it trades in the card again (it was always counted in IN CARD)'})
            d['cashFix1'] = time.time()
            _fw_save(d)
    done = {r.get('id') for r in d['ledger'] if r.get('side') == 'close' and r.get('status') in ('credited', 'lost')}
    # only closes that list their coin accounts (this rule) — a refund goes back only to the card that paid that coin's deposit
    todo = [r for r in d['ledger'][-2000:] if r.get('side') == 'close' and r.get('status') == 'sent' and r.get('sig') and r.get('closed') and r['id'] not in done]
    if not todo:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            st = ((await _krpc(http, 'getSignatureStatuses', [[r['sig'] for r in todo], {'searchTransactionHistory': True}])) or {}).get('value') or []
    except Exception:
        return
    sol_px = await _sol_usd_live()
    async with _fw_lock:
        d = _fw_load()
        for r, s_ in zip(todo, st):
            ok = bool(s_) and not s_.get('err') and s_.get('confirmationStatus') in ('confirmed', 'finalized')
            if ok and sol_px > 0:
                d['books'], cr = _fw.rent_back(d['books'], r['closed'], sol_px)
                _fw_record(d, {**{k: v for k, v in r.items() if k != 'closed'}, 'status': 'credited', 'credits': cr, 'at': time.time(),
                               'why': 'rent deposit back into the card' if cr else 'rent back to the reserve (it fronted it)'})
            elif (s_ and s_.get('err')) or (not s_ and time.time() - _fuse._f(r.get('at')) > 600):
                _fw_record(d, {**{k: v for k, v in r.items() if k != 'closed'}, 'status': 'lost', 'at': time.time(), 'why': 'close never landed — nothing credited'})
        _fw_save(d)


async def _fw_close_empty(cfg, now):
    """♻ Every 2 rounds of the real card's clock (5-min rounds → every 10 min; never under 10, never over 30): close the Fuse wallet's
    EMPTY token accounts (coins fully sold) → their rent deposits come back to the wallet reserve, which paid them (the card never pays
    rent, so its numbers stay exact). One tx, CloseAccount only (destination = the wallet itself), Circle signs, logged + owner inbox."""
    await _fw_rent_credit(cfg)
    every = _fw.close_every(_fuse._f(_prime_real_cfg().get('rotateHours')))
    if now - _fw_close_at['t'] < every or not cfg.get('armed') or cfg.get('paused') or not _fw_signer_ready():
        return
    _fw_close_at['t'] = now
    d = _fw_load()
    if any(b.get('pending') for b in d['books'].values()):
        return
    keep = {m for b in d['books'].values() for m in (b.get('legs') or {})}
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            res = await asyncio.gather(*[_krpc(http, 'getTokenAccountsByOwner', [cfg['address'], {'programId': pg}, {'encoding': 'jsonParsed', 'commitment': 'confirmed'}]) for pg in _FW_TOKEN_PROGRAMS])
            rows = [{'pubkey': a.get('pubkey'), 'program': pg, 'lamports': (a.get('account') or {}).get('lamports'),
                     'info': ((((a.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {})} for pg, r in zip(_FW_TOKEN_PROGRAMS, res) for a in (r or {}).get('value') or []]
            empty = _fw.empty_accounts(rows, keep)
            if not empty:
                return
            bh = ((await _krpc(http, 'getLatestBlockhash', [{'commitment': 'finalized'}])) or {}).get('value', {}).get('blockhash')
            signed = await _fw_sign(cfg, _fw.close_tx(cfg['address'], empty, bh), f'FEELESS close {len(empty)} empty accounts')
            sig = signed.get('signature') or signed.get('txHash')
            await _krpc(http, 'sendTransaction', [signed.get('signedTransaction'), {'encoding': 'base64', 'maxRetries': 3, 'preflightCommitment': 'confirmed'}])
        rent = round(sum(_fuse._f(r.get('lamports')) for r in rows if r['pubkey'] in {e['pubkey'] for e in empty}) / 1e9, 9)
        closed = [{'mint': e.get('mint'), 'lamports': next((r.get('lamports') for r in rows if r['pubkey'] == e['pubkey']), 0)} for e in empty]
        row = {'id': f'close:{now:.0f}', 'card': 'wallet', 'side': 'close', 'n': len(empty), 'sol': rent, 'sig': sig, 'at': now, 'status': 'sent', 'closed': closed,
               'why': 'empty coin accounts closed — rent goes back into the card once confirmed'}
    except Exception as e:
        err = str(getattr(e, 'detail', e))[:120]
        # Empty-account cleanup is maintenance, not a card trade. When the shared
        # public RPC pool is busy, back off quietly instead of hammering it every
        # three minutes and filling the audit trail with zero-dollar failures.
        if 'RPC pool exhausted' in err:
            _fw_close_at['t'] = now - 1800 + 900   # retry in ~15 min
            return
        row = {'id': f'close:{now:.0f}', 'card': 'wallet', 'side': 'close', 'at': now, 'status': 'failed', 'err': err}
        _fw_close_at['t'] = now - 1800 + 300   # non-rate-limit failure → retry in 5 min
    async with _fw_lock:
        d = _fw_load(); _fw_record(d, row); _fw_save(d)
    _fw_notify(row)


_mint_dec: dict = {}


async def _mint_decimals(mint):
    if mint in _mint_dec:
        return _mint_dec[mint]
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await _krpc(http, 'getTokenSupply', [mint])
        _mint_dec[mint] = int(((r or {}).get('value') or {}).get('decimals'))
    except Exception:
        return None
    return _mint_dec[mint]


async def _paper_quote_audit(now):
    """📏 Paper ⇄ real, every ~5 min: up to 4 coins on the tier cards are priced the way paper fills them AND with a REAL Jupiter quote
    for the same $ (read-only, nothing signed). The gap is logged and the paper impact model learns from it before any money moves."""
    cards = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    legs = [l for c in cards.values() for l in c.get('legs') or [] if l.get('mint') and l['mint'] != _fw.SOL_MINT]
    if not legs:
        return 0
    k = int(now // 300)
    pick = [legs[(k * 4 + i) % len(legs)] for i in range(min(4, len(legs)))]
    pairs_ = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in pick])
    sol_px = await _sol_usd_live()
    rows = []
    for l in pick:
        p_ = pairs_.get(l['pairAddress']) or {}
        mid, liq = (await _jup_prices([l['mint']])).get(l['mint']) or _fuse._f(p_.get('priceUsd')), _fuse._f((p_.get('liquidity') or {}).get('usd'))
        dec = await _mint_decimals(l['mint'])
        if mid <= 0 or dec is None or sol_px <= 0:
            continue
        usd = max(5.0, min(300.0, _fuse._f(l.get('units')) * mid))
        try:
            q = await _fw_jup('GET', '/swap/v1/quote', params={'inputMint': _fw.SOL_MINT, 'outputMint': l['mint'], 'amount': str(int(usd / sol_px * 1e9)), 'slippageBps': '100'})
        except HTTPException:
            continue
        rows.append({**_fw.quote_row(l.get('symbol'), usd, mid, liq, _prime.buy_px(mid, usd, liq), int(q.get('outAmount') or 0) / 10 ** dec, now), 'mint': l['mint']})
    if rows:
        async with _fw_lock:
            d = _fw_load(); d['quoteAudit'] = (d.get('quoteAudit') or [])[-199:] + rows; _fw_save(d)
    return len(rows)


def _fw_calibration(d):
    """Real fills win; until there are 3, paper learns from the real-quote audit."""
    real = _fw.calibrate(d.get('ledger'))
    return real if real['n'] >= 3 else {**_fw.calibrate(d.get('quoteAudit')), 'feeUsd': real.get('feeUsd'), 'fees': real.get('fees'), 'from': 'quotes'}


def _fw_public(tid, equity_usd=None, sol_px=None, prices=None):
    """What everyone sees on a REAL tier card: since when, $ funded, the last swaps with their tx, real network fees."""
    d = _fw_load(); b = d['books'].get(tid)
    if not b:
        return None
    seen, rows = set(), []
    for o in reversed(d['ledger']):   # newest first, each tx / funding once
        if o.get('card') != tid or o.get('side') not in ('buy', 'sell', 'topup') or not (o.get('status') in ('filled', 'done') or o.get('side') == 'topup'):
            continue
        k = (o.get('sig'), o.get('side')) if o.get('sig') else f"{o.get('id')}:{o.get('side')}:{o.get('at')}"
        if k not in seen:
            seen.add(k); rows.append(o)
        if len(rows) >= 12:
            break
    cfg = _fw_cfg(); pend = b.get('pending') or {}
    dead = []
    seen_dead = set()
    for o in reversed(d['ledger']):
        if o.get('card') != tid or o.get('side') not in ('buy', 'sell'):
            continue
        kdead = (o.get('side'), o.get('mint') or o.get('symbol'))
        if kdead in seen_dead:
            continue
        seen_dead.add(kdead)
        if o.get('status') not in ('failed', 'skipped'):
            continue
        dead.append({k: o.get(k) for k in ('side', 'symbol', 'mint', 'pair', 'usd', 'at', 'status', 'err')})
        if len(dead) >= 8:
            break
    fail = dead[0] if dead else None
    keeper = {'armed': bool(cfg.get('armed')), 'paused': bool(cfg.get('paused') or b.get('halt')), 'halt': bool(b.get('halt')), 'selling': bool(b.get('defund')),
              'minLiqUsd': cfg.get('minLiqUsd'), 'arenaMinLiqUsd': cfg.get('arenaMinLiqUsd'), 'minOrderUsd': cfg.get('minOrderUsd'), 'maxSwapUsd': cfg.get('maxSwapUsd'), 'slippageBps': cfg.get('slippageBps'),
              'maxImpactPct': cfg.get('maxImpactPct'), 'dailyUsd': cfg.get('dailyUsd'), 'pending': pend.get('symbol') and f"{pend.get('side')} ${pend.get('symbol')}",
              'lastFail': fail and {'symbol': fail.get('symbol'), 'side': fail.get('side'), 'mint': fail.get('mint'), 'pair': fail.get('pair'), 'err': (fail.get('err') or '')[:90], 'at': fail.get('at')},
              'lastFill': next((o.get('at') for o in rows if o.get('status') == 'filled'), None),
              'gas': _fw.gas_tank(_FW_GAS['sol'], d['books'], cfg.get('reserveSol')) if 'sol' in _FW_GAS else None,
              'landing': _fw.landing(d['ledger'], tid, time.time(), broadcast_only=True),
              'rpc': _rpc_quota_state()}
    # walletUsd is the engine's cumulative realized-profit payout counter and survives reinvests; old real ledgers did not
    # stamp payoutUsd on sell rows, which made PAID OUT EVER falsely show $0. Never infer history from current bankSol.
    card = ((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}).get(tid) or {}
    visible = {l.get('mint') for l in card.get('legs') or []}
    off_card = []
    for mint, leg in (b.get('legs') or {}).items():
        if mint in visible or not int(_fuse._f(leg.get('atoms'))):
            continue
        units = int(_fuse._f(leg.get('atoms'))) / 10 ** int(leg.get('decimals') or 0)
        px_now = _fuse._f((prices or {}).get(leg.get('pair'))) or _fuse._f(leg.get('entryPx'))
        off_card.append({'mint': mint, 'symbol': leg.get('symbol') or mint[:6], 'usd': round(units * px_now, 4),
                         'costUsd': round(_fuse._f(leg.get('costUsd')), 4), 'status': 'awaiting confirmed sell'})
    ledger_paid = sum(max(0.0, _fuse._f(o.get('payoutUsd'))) for o in d.get('ledger') or [] if o.get('card') == tid and o.get('status') == 'filled' and o.get('side') == 'sell')
    paid_ever = round(max(_fuse._f(card.get('walletUsd')), _fuse._f(b.get('payoutSeenUsd')), ledger_paid, _fuse._f(b.get('manualProfitPaidUsd'))), 4)
    profit_available = _fw.profit_available(b, equity_usd, sol_px) if equity_usd is not None and sol_px else 0.0
    payout_cash = min(profit_available, max(0.0, _fuse._f(b.get('sol')) - _fuse._f(b.get('manualCashSol'))) * _fuse._f(sol_px)) if sol_px else 0.0
    wallet_sol = _fuse._f(_FW_GAS.get('sol')) if _FW_GAS.get('sol') is not None else None
    all_book_sol = sum(_fuse._f(bb.get('sol')) + _fuse._f(bb.get('bankSol')) for bb in d['books'].values())
    reserve_sol = _fuse._f(cfg.get('reserveSol'))
    outside_sol = max(0.0, wallet_sol - all_book_sol - reserve_sol) if wallet_sol is not None else None
    recoverable = []
    bal = _FW_BAL.get('bal') if _FW_BAL.get('addr') == cfg.get('address') else None
    newest_fill = max((_fuse._f(o.get('at')) for o in d.get('ledger') or [] if o.get('status') == 'filled'), default=0.0)
    balance_is_current = _fuse._f(_FW_BAL.get('at')) >= newest_fill
    if bal and bal.get('source') != 'circle' and balance_is_current:
        booked = {}
        for bb in d['books'].values():
            for mint, leg in (bb.get('legs') or {}).items():
                booked[mint] = booked.get(mint, 0) + int(_fuse._f(leg.get('atoms')))
        for mint, held in (bal.get('tokens') or {}).items():
            excess = int(_fuse._f(held)) - int(booked.get(mint, 0))
            if excess <= 0:
                continue
            hist = [o for o in d['ledger'] if o.get('card') == tid and o.get('mint') == mint and o.get('pair')]
            if not hist:
                continue
            last = hist[-1]
            recoverable.append({'mint': mint, 'symbol': last.get('symbol') or mint[:6], 'atoms': excess,
                                'lastStatus': last.get('status'), 'lastErr': (last.get('err') or '')[:90], 'lastAt': last.get('at')})
    try:   # 👁 the swap as steps (done → sending → next), one transaction at a time
        plan = _fw.orders(tid, {**card, 'legs': []} if b.get('defund') else card, b, prices or {}, sol_px, cfg, time.time()) if sol_px and card else []
        keeper['flow'] = _fw.swap_flow(b, d['ledger'], tid, plan, time.time())
    except Exception:
        keeper['flow'] = []
    keeper['holdingSell'] = bool(b.get('sellHoldAt'))
    return {'since': b.get('since'), 'fundedUsd': b.get('fundedUsd'), 'feesUsd': round(_fuse._f(b.get('feesUsd')), 4),
            'paidOutEverUsd': paid_ever, 'paidOutSol': round(_fuse._f(b.get('bankSol')), 9),
            'profitAvailableUsd': round(profit_available, 4), 'profitCashAvailableUsd': round(payout_cash, 4), 'recoverable': recoverable, 'offCard': off_card,
            'wallet': cfg['address'], 'keeper': keeper, 'deadOrders': dead,
            'reconciliation': {'cardEquityUsd': round(_fuse._f(equity_usd), 4),
                               'cardCashSol': round(_fuse._f(b.get('sol')), 9),
                               'cardCashUsd': round(_fuse._f(b.get('sol')) * _fuse._f(sol_px), 4) if sol_px else None,
                               'walletSol': round(wallet_sol, 9) if wallet_sol is not None else None,
                               'gasReserveSol': round(reserve_sol, 9),
                               'outsideCardSol': round(outside_sol, 9) if outside_sol is not None else None,
                               'outsideCardUsd': round(outside_sol * _fuse._f(sol_px), 4) if outside_sol is not None and sol_px else None},
            'orders': [{k: o.get(k) for k in ('side', 'symbol', 'usd', 'proceedsUsd', 'realizedPnlUsd', 'sol', 'px', 'sig', 'at', 'status', 'feeUsd', 'why', 'costUsd')} for o in rows], **_fw.totals(d['ledger'], tid)}


async def _circle_wallets_live():
    """Circle supplies token ids needed for sends; confirmed chain lamports supply the display truth for Solana wallets.
    A Circle balance-endpoint error must never turn a funded wallet into an apparently empty wallet in HQ."""
    wallets = list((await _circle('GET', '/wallets')).get('wallets') or [])
    sol = [w for w in wallets if str(w.get('blockchain') or '').upper().startswith('SOL') and w.get('address')]
    if not sol:
        return wallets
    try:
        async with httpx.AsyncClient(timeout=12) as http:
            got = await _rpc(http, 'getMultipleAccounts', [[w['address'] for w in sol], {'encoding': 'base64', 'commitment': 'confirmed'}])
        lamports = {w['address']: int((a or {}).get('lamports') or 0) for w, a in zip(sol, (got or {}).get('value') or [])}
        out = []
        for w in wallets:
            if w.get('address') not in lamports:
                out.append(w); continue
            rows = [dict(b) for b in (w.get('balances') or [])]
            old = next((b for b in rows if str(b.get('symbol') or '').upper() == 'SOL'), None)
            amount = str(lamports[w['address']] / 1e9)
            if old:
                old['amount'] = amount
            elif lamports[w['address']] > 0:
                rows.insert(0, {'symbol': 'SOL', 'amount': amount, 'tokenId': None, 'source': 'chain'})
            out.append({**w, 'balances': rows, 'balanceSource': 'confirmed-chain'})
        return out
    except Exception:
        return wallets


@app.get('/api/reputation/admin/circle/profiles')
async def circle_profiles(request: Request):
    """Owner: every Circle wallet with its FEELESS profile (so it can be searched + edited from the creator wallet)."""
    _require_owner(request)
    ws = await _circle_wallets_live()
    profs = _profiles_load()['profiles']
    return {'wallets': [{'id': w.get('id'), 'address': w.get('address'), 'name': w.get('name'), 'blockchain': w.get('blockchain'),
                         'profile': {k: (profs.get(w.get('address')) or {}).get(k) for k in ('name', 'handle', 'bio', 'avatar', 'banner')}} for w in ws]}


@app.post('/api/reputation/admin/circle/profile')
async def circle_profile_save(request: Request, body: dict):
    """Owner: edit the public profile of one of YOUR Circle wallets (name, @handle, bio, avatar, banner). Audited."""
    me = _require_owner(request)
    addr = str(body.get('address') or '')
    ws = (await _circle('GET', '/wallets')).get('wallets') or []
    if addr not in {w.get('address') for w in ws}:
        raise HTTPException(403, 'Only your own Circle wallets can be edited here.')
    async with _profile_lock:
        d = _profiles_load()
        prev = d['profiles'].get(addr, {})
        clean = _clean_profile({**{k: prev.get(k) for k in ('name', 'handle', 'bio', 'avatar', 'banner')}, **(body.get('profile') or {})})
        if clean.get('handle') and any(a != addr and (v or {}).get('handle') == clean['handle'] for a, v in d['profiles'].items()):
            raise HTTPException(409, f"@{clean['handle']} is taken.")
        d['profiles'][addr] = {**prev, **{k: clean.get(k) for k in ('name', 'handle', 'bio', 'avatar', 'banner') if k in clean}, 'lastTs': time.time(), 'editedBy': me}
        tmp = PROFILE_PATH.with_suffix('.tmp'); tmp.write_text(json.dumps(d)); tmp.replace(PROFILE_PATH)
    ad = _admin_load(); _audit(ad, me, 'circle-profile', f'{addr[:6]}… {clean.get("handle") or clean.get("name") or ""}'); _admin_save(ad)
    return {'ok': True, 'address': addr, 'profile': d['profiles'][addr]}


@app.get('/api/reputation/admin/fuse-wallet/report')
async def fuse_wallet_report(request: Request, card: str = Query('', max_length=40)):
    """🩺 Owner: what each real run did (from the audit ledger) + the flaws it shows, each with its fix. Read-only."""
    _require_owner(request)
    return {'reports': await _fw_reports(card)}


async def _fw_reports(card=''):
    d = _fw_load(); hq = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    ids = [card] if card else sorted({r.get('card') for r in d.get('ledger') or [] if r.get('card') and r.get('card') != 'wallet'})
    sol_px = await _sol_usd_live()
    mints = [m for tid in ids for m in ((d['books'].get(tid) or {}).get('legs') or {})]
    jup = await _jup_prices(mints) if mints else {}
    out = []
    for tid in ids:
        b = d['books'].get(tid) or {}
        c = hq.get(tid) or {}
        px = {l.get('pair'): _fuse._f(jup.get(m)) or _fuse._f(l.get('entryPx')) for m, l in (b.get('legs') or {}).items()}   # live Jupiter value
        eq = _fw.book_value(b, px, sol_px) if b else None
        hold = round((sol_px / _fuse._f(c['solStart']) - 1) * 100, 2) if sol_px and _fuse._f(c.get('solStart')) else None
        out.append({**_fw.run_report(d.get('ledger'), tid, time.time(), b.get('fundedUsd'), eq, hold), 'label': c.get('label') or tid, 'open': bool(b)})
    return out


@app.get('/api/reputation/admin/fuse-wallet')
async def fuse_wallet_view(request: Request):
    """HQ › Fuse › 👛 Fuse wallet: the wallet's funds, each funded tier card's real book, caps, calibration and the audit trail."""
    _require_owner(request)
    await _fw_signer_check()
    d = _fw_load(); cfg = _fw.clean_cfg(d.get('cfg') or {})
    wallets, bal, err = [], None, None
    try:
        wallets = [w for w in await _circle_wallets_live() if str(w.get('blockchain', '')).startswith('SOL')]
    except HTTPException as e:
        err = str(e.detail)
    if cfg['address']:
        try:
            bal = await _fw_balances(cfg['address'])
            _FW_BAL.update(bal=bal, at=time.time(), addr=cfg['address'])
        except Exception as e:   # 🛟 RPC busy (rate limit): never show an EMPTY wallet — last good read, else Circle's own balances
            bal = _FW_BAL.get('bal') if _FW_BAL.get('addr') == cfg['address'] else None
            if bal is None:
                bal = _fw.circle_balances(wallets, cfg['address'])
            if bal is None:
                err = err or f'balance read failed: {str(e)[:80]}'
            else:
                bal = {**bal, 'stale': True}
    sol_px = await _sol_usd_live()
    cards = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    market_rows = _fw_market_rows(cards, d.get('books') or {})
    px = await _hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in market_rows]) if market_rows else {}
    jup = await _jup_prices([l.get('mint') for l in market_rows]) if market_rows else {}
    px.update({l['pairAddress']: jup[l['mint']] for l in market_rows if jup.get(l.get('mint'))})
    books = {tid: {**b, 'valueUsd': _fw.book_value(b, px, sol_px), 'label': (cards.get(tid) or {}).get('label') or tid, **_fw.totals(d['ledger'], tid)} for tid, b in d['books'].items()}
    recoverable = []
    if bal and bal.get('source') != 'circle':
        booked = {}
        for b in d['books'].values():
            for mint, leg in (b.get('legs') or {}).items():
                booked[mint] = booked.get(mint, 0) + int(_fuse._f(leg.get('atoms')))
        for mint, held in (bal.get('tokens') or {}).items():
            excess = int(_fuse._f(held)) - int(booked.get(mint, 0))
            if excess <= 0:
                continue
            hist = [r for r in d['ledger'] if r.get('mint') == mint and r.get('card') in d['books'] and r.get('pair')]
            if not hist:
                continue   # never offer unrelated wallet tokens
            last = hist[-1]
            recoverable.append({'card': last['card'], 'mint': mint, 'symbol': last.get('symbol') or mint[:6],
                                'pair': last.get('pair'), 'atoms': excess, 'decimals': int((bal.get('decimals') or {}).get(mint) or last.get('decimals') or 0),
                                'lastStatus': last.get('status'), 'lastErr': (last.get('err') or '')[:100], 'lastAt': last.get('at')})
    rent_returned = round(sum(_fuse._f(r.get('sol')) for r in d.get('ledger') or []
                              if r.get('side') == 'close' and r.get('status') == 'sent'), 9)
    funded_sol = round(sum(_fuse._f(r.get('sol')) for r in d.get('ledger') or []
                           if r.get('side') == 'topup' and r.get('status') == 'done'), 9)
    dep_doc = _json_load(FUSE_DEPOSITS_PATH, {})
    dep_rows = (dep_doc.get('rows') or []) if dep_doc.get('address') == cfg.get('address') else []
    return {'cfg': cfg, 'signer': _fw_signer_ready(), 'wallets': wallets, 'balances': bal, 'solUsd': sol_px, 'error': err,
            'freeSol': _fw.free_sol((bal or {}).get('sol'), d['books'], cfg['reserveSol']) if bal else None,
            # Unassigned SOL is fungible: it can include owner deposits and token-account rent returned after card sells.
            # Expose both audit totals so the UI never presents it as known-new owner funding or card profit.
            'solProvenance': {'cardFundedSol': funded_sol, 'rentReturnedSol': rent_returned,
                              **(_fw.sol_story(dep_rows, d['books'], cfg['reserveSol'], bal.get('sol'), sum(_fuse._f(b.get('valueUsd')) for b in books.values()) / sol_px - sum(_fuse._f(b.get('sol')) + _fuse._f(b.get('bankSol')) for b in d['books'].values())) if bal and sol_px and dep_rows else {}),
                              'deposits': dep_rows[-12:][::-1]},
            'missing': _fw.reconcile((bal or {}).get('tokens'), d['books']) if bal and bal.get('source') != 'circle' else [],   # Circle rows have no mints
            'books': books, 'tiers': {k: v['label'] for k, v in _prime.TEMPLATES.items()}, 'recoverable': recoverable, 'calibration': _fw_calibration(d),
            'paperMatch': _fw.paper_match(d.get('quoteAudit')), 'quoteAudit': (d.get('quoteAudit') or [])[-20:][::-1],
            'totals': _fw.totals(d['ledger']), 'ledger': d['ledger'][-200:][::-1]}


@app.post('/api/reputation/admin/fuse-wallet/recover-sell')
async def fuse_wallet_recover_sell(request: Request):
    """Owner rescue: sell an old keeper token still physically in the Fuse wallet but no longer booked on a card.
    Only excess atoms with matching keeper history are adopted; unrelated wallet tokens are refused.
    Confirmed proceeds stay inside the original card as active cash/SOL."""
    me = _require_owner(request)
    body = await request.json()
    tid, mint = body.get('tpl'), str(body.get('mint') or '').strip()
    if tid not in _prime.TEMPLATES or not mint:
        raise HTTPException(400, 'Pick a real tier card and token.')
    cfg = _fw_cfg()
    if not cfg.get('address') or not cfg.get('armed') or cfg.get('paused'):
        raise HTTPException(400, 'Fuse wallet must be armed and running.')
    bal = await _fw_balances(cfg['address'])
    async with _fw_lock:
        d = _fw_load()
        if tid not in d['books']:
            raise HTTPException(404, 'That tier has no real card book.')
        booked_total = sum(int(_fuse._f(((b.get('legs') or {}).get(mint) or {}).get('atoms'))) for b in d['books'].values())
        held = int(_fuse._f((bal.get('tokens') or {}).get(mint)))
        excess = max(0, held - booked_total)
        hist = [r for r in d['ledger'] if r.get('card') == tid and r.get('mint') == mint and r.get('pair')]
        if excess <= 0:
            raise HTTPException(400, 'No unbooked wallet balance remains for that token.')
        if not hist:
            raise HTTPException(400, 'Refused: this wallet token has no keeper history for that card.')
        last = hist[-1]
        st = {'card': tid, 'mint': mint, 'atoms': excess,
              'decimals': int((bal.get('decimals') or {}).get(mint) or last.get('decimals') or 0),
              'pair': last.get('pair'), 'symbol': last.get('symbol') or mint[:6]}
        book = _fw.adopt(d['books'][tid], st)
        book['legs'][mint]['manualCash'] = True
        book['legs'][mint]['recovered'] = True
        d['books'][tid] = book
        _fw_record(d, {'card': tid, 'side': 'adopt', 'mint': mint, 'symbol': st['symbol'], 'atoms': excess,
                       'usd': 0.0, 'at': time.time(), 'status': 'done',
                       'why': '🧹 owner recovered old keeper balance for force sell → proceeds stay in card cash'})
        _fw_save(d)
    await _fw_tick(time.time())
    ad = _admin_load(); _audit(ad, me, 'fuse-wallet-recover-sell', f'{tid} {st["symbol"]} {excess} atoms'); _admin_save(ad)
    return {'ok': True, 'card': tid, 'symbol': st['symbol'], 'atoms': excess, 'status': 'sell queued/running'}


@app.post('/api/reputation/admin/fuse-wallet/recover-sell-all')
async def fuse_wallet_recover_sell_all(request: Request):
    """Queue every confirmed dead/off-card keeper holding for sale into its card cash.
    Failed buys have no confirmed atoms and are deliberately ignored. Nothing is removed or credited until its sell confirms."""
    me = _require_owner(request)
    body = await request.json()
    tid = body.get('tpl')
    if tid not in _prime.TEMPLATES:
        raise HTTPException(400, 'Pick a funded real tier card.')
    cfg = _fw_cfg()
    if not cfg.get('address') or not cfg.get('armed') or cfg.get('paused'):
        raise HTTPException(400, 'Fuse wallet must be armed and running.')
    cards = ((_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {})
    card = cards.get(tid)
    if not card or not card.get('real'):
        raise HTTPException(400, 'That tier is not a real card.')
    bal = await _fw_balances(cfg['address'])
    async with _fw_lock:
        d = _fw_load(); book = d['books'].get(tid)
        if not book:
            raise HTTPException(400, 'That tier is not funded.')
        if book.get('pending'):
            raise HTTPException(409, 'Wait for the current transaction to settle first.')
        book, marked = _fw.mark_off_card_cash(book, card)
        booked = {}
        for bb in d['books'].values():
            for mint, leg in (bb.get('legs') or {}).items():
                booked[mint] = booked.get(mint, 0) + int(_fuse._f(leg.get('atoms')))
        adopted = []
        for mint, held_raw in (bal.get('tokens') or {}).items():
            excess = int(_fuse._f(held_raw)) - int(booked.get(mint, 0))
            if excess <= 0:
                continue
            hist = [r for r in d['ledger'] if r.get('card') == tid and r.get('mint') == mint and r.get('pair')]
            if not hist:
                continue
            last = hist[-1]
            st = {'card': tid, 'mint': mint, 'atoms': excess,
                  'decimals': int((bal.get('decimals') or {}).get(mint) or last.get('decimals') or 0),
                  'pair': last.get('pair'), 'symbol': last.get('symbol') or mint[:6]}
            book = _fw.adopt(book, st)
            book['legs'][mint] = {**book['legs'][mint], 'manualCash': True, 'recovered': True}
            adopted.append(mint)
        queued = list(dict.fromkeys(marked + adopted))
        if not queued:
            raise HTTPException(400, 'No confirmed dead/off-card holdings need selling.')
        d['books'][tid] = book
        _fw_record(d, {'card': tid, 'side': 'repair-sell-all', 'mints': queued, 'n': len(queued), 'at': time.time(), 'status': 'done',
                       'why': 'owner queued every confirmed dead/off-card holding -> proceeds stay in card cash'})
        _fw_save(d)
    ad = _admin_load(); _audit(ad, me, 'fuse-wallet-recover-sell-all', f'{tid} {len(queued)} confirmed holdings'); _admin_save(ad)
    await _fw_tick(time.time())
    return {'ok': True, 'tpl': tid, 'queued': len(queued), 'mints': queued, 'status': 'confirmed holdings queued/running'}


@app.post('/api/reputation/admin/fuse-wallet/cfg')
async def fuse_wallet_cfg(request: Request):
    """Owner only: pick the Fuse Circle wallet and set the hard limits. Arming needs signing enabled + a picked wallet."""
    me = _require_owner(request)
    body = await request.json()
    async with _fw_lock:
        d = _fw_load()
        cfg = _fw.clean_cfg({**(d.get('cfg') or {}), **{k: v for k, v in body.items() if k in _fw.DEFAULT_CFG}})
        if cfg['armed'] and (not cfg['address'] or not _fw_signer_ready()):
            raise HTTPException(400, 'Pick the Fuse wallet first (and the Circle service must be running) before arming real money.')
        d['cfg'] = cfg; _fw_save(d)
    ad = _admin_load(); _audit(ad, me, 'fuse-wallet-cfg', json.dumps({k: cfg[k] for k in cfg if k != 'walletId'})[:160]); _admin_save(ad)
    return {'cfg': cfg}


@app.get('/api/reputation/admin/rpc')
async def admin_rpc_status(request: Request):
    """Owner only: the keeper's RPC lanes — provider domain, in quota or not, minutes until it resets. Never a URL or a key."""
    _require_owner(request)
    lanes = _rpc_quota_state()
    return {'lanes': lanes, 'needsKey': not lanes or all(x['spent'] for x in lanes), 'slots': [{'slot': k, 'set': any(x['slot'] == k for x in lanes)} for k in _chain.LANE_KEYS]}


@app.post('/api/reputation/admin/rpc')
async def admin_rpc_set(request: Request):
    """Owner only: put a new keyed RPC URL on lane 1 or 2. It is TESTED first (answers + holder lookup), saved to backend/.env as
    the one active line of its key, and used by the keeper at once — no restart. The URL is never returned, logged or audited."""
    me = _require_owner(request)
    body = await request.json()
    slot = int(_fuse._f(body.get('slot'))) if int(_fuse._f(body.get('slot'))) in _chain.LANE_KEYS else 1
    try:
        url = _chain.clean_rpc_url(body.get('url'))
    except ValueError as e:
        raise HTTPException(400, str(e))
    async with httpx.AsyncClient(timeout=10) as http:
        res = await _chain.probe(http, url)
    if not res.get('ok'):
        raise HTTPException(400, f"Not saved — {res.get('err')}.")
    env = Path(__file__).parent / '.env'
    if not os.environ.get('PYTEST_CURRENT_TEST'):
        env.write_text(_chain.env_with_key(env.read_text() if env.exists() else '', _chain.LANE_KEYS[slot], url))
    _chain.set_lane(slot, url)
    ad = _admin_load(); _audit(ad, me, 'rpc-lane', f"lane {slot} → {_chain.provider_of(url)}"); _admin_save(ad)
    return {'ok': True, 'slot': slot, 'provider': _chain.provider_of(url), 'holders': bool(res.get('holders')), 'ms': res.get('ms'), 'lanes': _rpc_quota_state()}


_rpc_warned = {'day': ''}


def _rpc_quota_notice():
    """🔑 Once a day: every keyed lane is out of quota → the owner's inbox gets one notice that opens the key box in HQ."""
    lanes = _rpc_quota_state()
    day = time.strftime('%Y-%m-%d')
    if lanes and not all(x['spent'] for x in lanes) or _rpc_warned['day'] == day:
        return False
    _rpc_warned['day'] = day
    for w in _owner_wallets():
        notify(w, 'fuse-card', '🔑 Every RPC key is out of quota — real swaps are on slower public nodes. Tap to add a key (takes one paste).' if lanes
               else '🔑 No RPC key is set — real swaps are on slower public nodes. Tap to add one (takes one paste).',
               url='/terminal/hq?tab=fuse&rpc=1', push=False, once=f'rpc-key-{day}', meta={'claim': 'RPC key needed', 'source': 'Keeper RPC lanes'})
    return True


@app.post('/api/reputation/admin/fuse-wallet/preview')
async def fuse_wallet_preview(request: Request):
    """Dry run: the swaps a $ amount on one tier would need right now, each with a REAL Jupiter quote. Never signs or sends."""
    _require_owner(request)
    body = await request.json()
    tid, usd = body.get('tpl'), _fuse._f(body.get('usd'))
    cards = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    if tid not in _prime.TEMPLATES or not cards.get(tid) or not 1 <= usd <= 50000:
        raise HTTPException(400, 'Pick a dealt tier and $1–$50,000.')
    card, sol_px = cards[tid], await _sol_usd_live()
    px = await _hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in card['legs']])
    scale = usd / (_prime.value({**card, 'walletUsd': 0, 'parked': {}}, px) or 1)
    want = {**card, 'legs': [{**l, 'units': l['units'] * scale} for l in card['legs']]}
    cfg = {**_fw_cfg(), 'maxSwapUsd': 10000, 'minOrderUsd': 0.25}
    status = _fw.paper_status(card, px, usd)
    rows = []
    for o in _fw.orders(tid, want, _fw.new_book(usd, sol_px, time.time()), px, sol_px, cfg, time.time()):
        try:
            q = await _fw_quote(o, cfg)
            out = int(q.get('outAmount') or 0)
            rows.append({**o, 'impactPct': round(_fuse._f(q.get('priceImpactPct')) * 100, 3), 'outAmount': out, 'route': [r.get('swapInfo', {}).get('label') for r in q.get('routePlan') or []][:3]})
        except HTTPException as e:
            rows.append({**o, 'err': str(e.detail)[:120]})
    held_mints = set()
    if _fw_cfg()['address']:
        try:
            held_mints = set((await _fw_balances(_fw_cfg()['address']))['tokens'])
        except Exception:
            pass
    new_coins = len({o['mint'] for o in rows if o.get('side') == 'buy' and o['mint'] not in held_mints})
    net_usd, rent_usd = round(len(rows) * 0.00006 * sol_px, 4), round(new_coins * 0.00204 * sol_px, 4)
    return {'orders': rows, 'card': status, 'solUsd': sol_px, 'networkUsdEst': net_usd, 'rentUsdEst': rent_usd, 'newCoins': new_coins,
            'feesUsdEst': round(net_usd + rent_usd, 4), 'cardUsd': usd,
            'note': 'Fund continues THIS card with real money: same coins, same phase, same clock and config — only the $ and the start time change.'}


@app.post('/api/reputation/admin/fuse-wallet/topup')
async def fuse_wallet_topup(request: Request):
    """Owner only: fund (or add to) one tier card from the Fuse wallet's free SOL. A top-up RESETS the card as a new real run."""
    me = _require_owner(request)
    body = await request.json()
    tid, usd = body.get('tpl'), round(_fuse._f(body.get('usd')), 2)
    cfg = _fw_cfg()
    if tid not in _prime.TEMPLATES or usd < 1:
        raise HTTPException(400, 'Pick a tier and at least $1.')
    if not cfg['armed'] or not _fw_signer_ready():
        raise HTTPException(400, 'Arm the Fuse wallet first (signing must be enabled).')
    bal, sol_px = await _fw_balances(cfg['address']), await _sol_usd_live()
    now = time.time()
    async with _fw_lock:
        d = _fw_load()
        if usd / sol_px > _fw.free_sol(bal['sol'], d['books'], cfg['reserveSol']):
            raise HTTPException(400, f"Not enough free SOL in the Fuse wallet for ${usd:.2f} (network-fee reserve {cfg['reserveSol']} SOL is kept back).")
        cards = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
        card = cards.get(tid)
        px = await _hq_prices([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in (card or {}).get('legs') or []]) if card else {}
        jup = await _jup_prices([l.get('mint') for l in (card or {}).get('legs') or []]) if card else {}
        if card:
            px.update({l['pairAddress']: jup[l['mint']] for l in card.get('legs') or [] if jup.get(l.get('mint'))})
        first = tid not in d['books']
        cur = _fw.book_value(d['books'][tid], px, sol_px) if not first else 0
        if cur + usd > cfg['maxCardUsd']:
            raise HTTPException(400, f"Over the ${cfg['maxCardUsd']:g} per-card cap (card holds ${cur:.2f}).")
        if _FW_GAS.get('sol') is not None and sol_px > 0:   # 💵 a top-up only ASSIGNS SOL already in the wallet — never more than is unassigned
            free = _fw.free_sol(_FW_GAS['sol'], d['books'], cfg['reserveSol'])
            if usd / sol_px > free + 1e-6:
                raise HTTPException(400, f"Only ${free * sol_px:.2f} unassigned SOL in the Fuse wallet (fee reserve kept apart) — send SOL to it first.")
        if first:   # the SAME card goes real: same coins, phase, clock and config — scaled to the $, time + P&L start over
            if not card or not card.get('legs'):
                raise HTTPException(503, 'That tier has no card dealt yet — try again in a minute.')
            new = _fw.topup_card(card, usd, px, now, first=True)
            d['books'][tid] = _fw.new_book(usd, sol_px, now)
        else:
            b = d['books'][tid]
            truth = _fw.sync_card(card, b, px, sol_px)
            current = _prime.value(truth, px)
            new = _fw.topup_card(truth, usd, px, now, current_usd=current)
            d['books'][tid] = {**b, 'sol': round(_fuse._f(b.get('sol')) + usd / sol_px, 9), 'fundedUsd': round(_fuse._f(b.get('fundedUsd')) + usd, 4)}
        _fw_record(d, {'card': tid, 'side': 'topup', 'usd': usd, 'sol': round(usd / sol_px, 9), 'at': now, 'by': me, 'status': 'done',
                       'why': 'funded — new real run' if first else 'new money top-up — new run'})
        _fw_save(d)
    async with _admin_lock:
        h = _json_load(FUSE_HQ_PATH, {}); h.setdefault('prime', {}).setdefault('cards', {})[tid] = new; _json_save(FUSE_HQ_PATH, h)
    ad = _admin_load(); _audit(ad, me, 'fuse-wallet-topup', f'{tid} ${usd:.2f}{" (first funding)" if first else ""}'); _admin_save(ad)
    asyncio.create_task(_fw_tick(time.time()))
    return {'ok': True, 'tpl': tid, 'usd': usd, 'first': first}


@app.post('/api/reputation/admin/fuse-wallet/retry-dead')
async def fuse_wallet_retry_dead(request: Request):
    """Owner repair for a failed/skipped keeper order.
    Sell repairs are prioritized and return confirmed SOL to the card.
    Buy repairs simply clear the bench/miss state and wake the keeper to spend only existing card cash."""
    me = _require_owner(request)
    body = await request.json()
    tid, side, mint = body.get('tpl'), body.get('side'), str(body.get('mint') or '').strip()
    if tid not in _prime.TEMPLATES or side not in ('buy', 'sell') or not mint:
        raise HTTPException(400, 'Pick a failed buy/sell on a funded card.')
    async with _fw_lock:
        d = _fw_load(); b = d['books'].get(tid)
        if not b:
            raise HTTPException(400, 'That tier is not funded.')
        if b.get('pending'):
            raise HTTPException(409, 'Wait for the current transaction to settle first.')
        if side == 'buy':
            misses = dict(b.get('misses') or {}); misses.pop(mint, None)
            bench = dict(b.get('benched') or {}); bench.pop(mint, None)
            b = {**b, 'misses': misses, 'benched': bench}
            d['books'][tid] = b
            _fw_record(d, {'card': tid, 'side': 'repair-buy', 'mint': mint, 'at': time.time(), 'status': 'done',
                           'why': 'owner retried dead buy from available card cash'})
        else:
            leg = (b.get('legs') or {}).get(mint)
            if not leg or int(_fuse._f(leg.get('atoms'))) <= 0:
                raise HTTPException(400, 'No held balance remains for that failed sell.')
            b = {**b, 'legs': {**(b.get('legs') or {}), mint: {**leg, 'manualCash': True, 'recovered': True}}}
            d['books'][tid] = b
            _fw_record(d, {'card': tid, 'side': 'repair-sell', 'mint': mint, 'symbol': leg.get('symbol'), 'at': time.time(), 'status': 'done',
                           'why': 'owner retried dead sell -> proceeds stay in card cash'})
        _fw_save(d)
    ad = _admin_load(); _audit(ad, me, 'fuse-wallet-retry-dead', f'{tid} {side} {mint[:8]}'); _admin_save(ad)
    await _fw_tick(time.time())
    return {'ok': True, 'tpl': tid, 'side': side, 'mint': mint}

@app.post('/api/reputation/admin/fuse-wallet/payout-profit')
async def fuse_wallet_payout_profit(request: Request):
    """Owner only: move currently available PROFIT cash from the card into paid-out SOL.
    Funded principal is a hard floor; this never sells a coin and never touches principal."""
    me = _require_owner(request)
    body = await request.json()
    tid = body.get('tpl')
    ask = body.get('usd')
    if tid not in _prime.TEMPLATES:
        raise HTTPException(400, 'Pick a funded tier.')
    sol_px = await _sol_usd_live()
    cards = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    card = cards.get(tid)
    if not card:
        raise HTTPException(404, 'Card not found.')
    pairs_ = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress']} for l in card.get('legs') or []])
    px = {k: _fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}
    jup = await _jup_prices([l.get('mint') for l in card.get('legs') or []])
    for l in card.get('legs') or []:
        if jup.get(l.get('mint')):
            px[l['pairAddress']] = jup[l['mint']]
    async with _fw_lock:
        d = _fw_load(); b = d['books'].get(tid)
        if not b:
            raise HTTPException(400, 'That tier is not funded.')
        if b.get('pending'):
            raise HTTPException(409, 'Wait for the current transaction to settle first.')
        equity = _fw.book_value(b, px, sol_px)
        avail = _fw.profit_available(b, equity, sol_px)
        nb, paid = _fw.payout_profit_cash(b, equity, sol_px, ask)
        if paid <= 0:
            raise HTTPException(400, 'No profit cash is available to pay out right now.')
        d['books'][tid] = nb
        _fw_record(d, {'card': tid, 'side': 'payout', 'usd': paid, 'sol': round(paid / sol_px, 9), 'at': time.time(), 'by': me,
                       'status': 'done', 'why': 'owner payout - profit only; funded principal protected'})
        _fw_save(d)
    ad = _admin_load(); _audit(ad, me, 'fuse-wallet-payout-profit', f'{tid} ${paid:.2f}'); _admin_save(ad)
    return {'ok': True, 'tpl': tid, 'paidUsd': paid, 'availableBeforeUsd': avail, 'fundedUsd': b.get('fundedUsd')}

@app.post('/api/reputation/admin/fuse-wallet/withdraw-cash')
async def fuse_wallet_withdraw_cash(request: Request):
    """Owner only: take card cash OUT of a real card (all of it, or `usd`). The principal drops by what was taken, so profit is
    measured above what is still in. An internal reallocation — no coin sold, nothing sent: the SOL becomes unassigned wallet SOL."""
    me = _require_owner(request)
    body = await request.json()
    tid = body.get('tpl')
    if tid not in _prime.TEMPLATES:
        raise HTTPException(400, 'Pick a funded tier.')
    sol_px = await _sol_usd_live()
    async with _fw_lock:
        d = _fw_load(); b = d['books'].get(tid)
        if not b:
            raise HTTPException(400, 'That tier is not funded.')
        if b.get('pending') or b.get('defund'):
            raise HTTPException(409, 'Wait for the current Fuse transaction to settle, then withdraw.')
        nb, took = _fw.withdraw_cash(b, sol_px, body.get('usd'))
        if took <= 0:
            raise HTTPException(400, 'This card has no cash to withdraw — sell part of a coin to card cash first.')
        d['books'][tid] = nb
        _fw_record(d, {'card': tid, 'side': 'withdraw', 'sol': round(took / sol_px, 9), 'usd': round(took, 4), 'at': time.time(), 'by': me, 'status': 'done',
                       'why': f"owner took ${took:.2f} out — principal is now ${nb['fundedUsd']:.2f}"})
        _fw_save(d)
    async with _admin_lock:   # the paper side stops holding that cash for the owner
        hd = _json_load(FUSE_HQ_PATH, {}); cd = ((hd.get('prime') or {}).get('cards') or {}).get(tid)
        if cd:
            cd['holdCashUsd'] = round(max(0.0, _fuse._f(cd.get('holdCashUsd')) - took), 6); _json_save(FUSE_HQ_PATH, hd)
    ad = _admin_load(); _audit(ad, me, 'fuse-wallet-withdraw', f"{tid} ${took:.2f} principal→${nb['fundedUsd']:.2f}"); _admin_save(ad)
    return {'ok': True, 'tookUsd': took, 'principalUsd': nb['fundedUsd']}


@app.post('/api/reputation/admin/fuse-wallet/reinvest-paid')
async def fuse_wallet_reinvest_paid(request: Request):
    """Owner only: move this card's currently segregated paid-out SOL back into active card capital.
    This is an internal reallocation, not new funding: fundedUsd never changes and the historical bankUsd trail is preserved."""
    me = _require_owner(request)
    body = await request.json()
    tid = body.get('tpl')
    if tid not in _prime.TEMPLATES:
        raise HTTPException(400, 'Pick a funded tier.')
    now = time.time()
    async with _fw_lock:
        d = _fw_load(); b = d['books'].get(tid)
        if not b:
            raise HTTPException(400, 'That tier is not funded.')
        if b.get('pending'):
            raise HTTPException(409, 'Wait for the current Fuse transaction to settle, then reinvest paid out.')
        if b.get('defund'):
            raise HTTPException(409, 'This card is selling out right now.')
        nb, sol = _fw.reinvest_bank(b)
        if sol <= 0:
            raise HTTPException(400, 'This card has no paid-out SOL available to reinvest.')
        d['books'][tid] = nb
        _fw_record(d, {'card': tid, 'side': 'reinvest', 'sol': sol, 'usd': round(sol * (await _sol_usd_live()), 4), 'at': now, 'by': me, 'status': 'done',
                       'why': 'paid-out SOL moved back into active card capital — not new funding'})
        _fw_save(d)
    ad = _admin_load(); _audit(ad, me, 'fuse-wallet-reinvest-paid', f'{tid} {sol:.9f} SOL'); _admin_save(ad)
    asyncio.create_task(_fw_tick(time.time()))
    return {'ok': True, 'tpl': tid, 'sol': sol, 'fundedUsd': nb.get('fundedUsd'), 'bankUsd': nb.get('bankUsd')}


@app.post('/api/reputation/admin/fuse-wallet/card')
async def fuse_wallet_card(request: Request):
    """Owner only: ↩ defund a tier (every coin sold back to SOL, the card returns to paper) or ▶ resume a halted card."""
    me = _require_owner(request)
    body = await request.json()
    tid, act = body.get('tpl'), body.get('action')
    async with _fw_lock:
        d = _fw_load(); b = d['books'].get(tid)
        if not b or act not in ('defund', 'resume', 'halt'):
            raise HTTPException(400, 'Pick a funded tier and defund / halt / resume.')
        d['books'][tid] = {**b, 'defund': True} if act == 'defund' else {**b, 'halt': act == 'halt'}
        if act == 'defund':   # freeze the paper card to come back to BEFORE the selling changes the coins
            async with _admin_lock:
                h = _json_load(FUSE_HQ_PATH, {}); cs = (h.get('prime') or {}).get('cards') or {}
                if cs.get(tid) and not cs[tid].get('paperBefore'):
                    cs[tid]['paperBefore'] = _fw.paper_snapshot(cs[tid]); _json_save(FUSE_HQ_PATH, h)
        _fw_save(d)
    ad = _admin_load(); _audit(ad, me, f'fuse-wallet-{act}', tid); _admin_save(ad)
    return {'ok': True}


async def _fuse_warm_loop():
    """Fuse runs in the background: every 25s the live runner board, Runner discovery, the Arena stage and the season board
    are rebuilt, so every page load is served from a fresh cache and never waits on scans or prices."""
    await asyncio.sleep(20)
    while True:
        try:
            await _fuse_warm()
        except Exception as e:
            print('fuse warm:', e)
        await asyncio.sleep(25)


_fuse_warm_n = {'n': 0}


import data_cleaner as _dc

_data_clean_last: dict = {}


async def _data_clean(now):
    """🧹 Hourly: slim stale chat token snapshots (the chat file is rewritten on every message, so its size is everyone's lag).
    Runs under the chat lock; writes only when something was freed; the result is kept for HQ and logged."""
    async with _chat_lock:
        d = _chat_load()
        out, st = _dc.slim_chat(d, now)
        if st['messages']:
            CHAT_PATH.write_text(json.dumps(out))
    _data_clean_last.update(at=now, chat=st)
    if st['messages']:
        print(f"data cleaner: chat −{st['bytes'] / 1e6:.2f} MB ({st['messages']} old messages slimmed)")
    return st


@app.get('/api/reputation/admin/data-cleaner')
async def admin_data_cleaner(request: Request):
    """HQ: what the cleaner freed on its last run."""
    _require_admin(request)
    return {'last': _data_clean_last, 'rules': ['Chat: coin snapshots older than 1h lose their stale signal blocks (text, author and the coin stay)']}


async def _fuse_warm():
    _FUSE_FORCE.set(True)          # task-local: viewers never see it, they keep reading the previous copy
    _fuse_warm_n['n'] += 1
    if _fuse_warm_n['n'] % 24 == 2:   # ~10 min: who the elite traders are + what they bought (FeeCat learns from it)
        await _crowd_build()
    try:   # 🗑 trench scan (~2 min, cached; heavy on-chain counts only for the 5 busiest finalists)
        await _trench_build(time.time())
    except Exception as e:
        print('trench:', e)
    if _fuse_warm_n['n'] % 144 == 31:   # ~1h: 🧾 what's working / what's not, always running (owner inbox when something flips)
        try:
            await _verdict_tick(time.time())
        except Exception as e:
            print('verdict:', e)
    if _fuse_warm_n['n'] % 144 == 7:   # ~1h: 🧹 data cleaner (stale derived data only — never money records or message text)
        try:
            await _data_clean(time.time())
        except Exception as e:
            print('data cleaner:', e)
    try:   # 🏁 the contenders league is kept warm, so the Arena reads it in ms and the tier engine always knows who is next up
        await _contenders_build()
    except Exception as e:
        print('contenders:', e)
    if _fuse_warm_n['n'] % 36 == 5:   # ~15 min (one runner round): auto-strength picks the proven-best engine dial
        await _engine_auto(time.time())
    if _fuse_warm_n['n'] % 144 == 3:  # ~1h: nudge HQ if a stronger engine config is waiting
        _engine_nudge(time.time())
    if _fuse_warm_n['n'] % 12 == 1:   # ~5 min: refresh card holders' Fuse scores (feeds their trust score)
        holders = list({x['wallet'] for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or []})[:200]
        await asyncio.gather(*[_fuse_score(w, fresh=True) for w in holders], return_exceptions=True)
    if _fuse_warm_n['n'] % 36 == 20:   # ~15 min: 🧠 300 background sim cards → the brain
        try:
            await _pg_sim_tick(time.time())
        except Exception as e:
            print('pg sim:', e)
    if _fuse_warm_n['n'] % 12 == 9:   # ~5 min: 📏 paper ⇄ real quotes (paper's fill model is checked against Jupiter)
        try:
            await _paper_quote_audit(time.time())
            _cal0 = _fw_calibration(_fw_load()); _prime.IMPACT_MULT = _cal0['impactMult']; _prime.SPREAD = _cal0.get('spread') or 0.0
        except Exception as e:
            print('quote audit:', e)
    if _fuse_warm_n['n'] % 12 == 7:   # ~5 min: 📖 the rep engine learns today's meme terms (new launches + chat)
        await _meme_tick(time.time())
    if _fuse_warm_n['n'] % 2 == 1:    # ~50s: ⚔ engine playground battles (paper, HQ only)
        try:
            await _pg_battle_tick(time.time())
        except Exception as e:
            print(f'[pg-battle] {e}')
    await _prime_tick(time.time())    # ~25s: ⭐ tier cards (paper + real) — stops, rug shield and the keeper can't wait
    await _runner_live()
    await _arena_auto_refresh(time.time())
    await asyncio.gather(runners_discover(), fuse_arena_public(), fuse_season(), _sol_usd_live(), return_exceptions=True)
    await _battle_tick(time.time())
    _fuse_chat_tick(time.time())


_runner_disc_cache = {'at': 0.0, 'data': None}


def _round_move(p, live):
    """A round pick's live move since entry, or None when the feed no longer sees the coin (never a fake 0%)."""
    now_px = _fuse._f(({x['mint']: x for x in live['passing'] + live['dropped']}.get(p['mint']) or {}).get('price'))
    entry = _fuse._f(p.get('entry'))
    return round((now_px / entry - 1) * 100, 2) if now_px > 0 and entry > 0 else None


@app.get('/api/reputation/admin/runners/suggest')
async def admin_runner_suggest(request: Request):
    """⚡ Stronger engine found? Every setting where the live config is weaker than the recommended one (with why), plus each
    lane's self-tuning record. Apply = POST /admin/runners/config with the merged values (one click in HQ)."""
    _require_admin(request)
    d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
    cfg = _runner_cfg(); pr = _rn.lane_proofs(d['rounds'], d['paths'], time.time(), cfg)
    return {'suggestions': _rn.suggest_cfg(cfg), 'lanes': pr, 'weights': _rn.lane_weights(pr), 'cfg': cfg}


async def _scenario_stage(rd, now):
    """Once per runner round (or when HQ changes its picks): the scenario cards HQ PICKED in the engine playground
    (🎨 Creator's pick) are dealt onto the Arena at today's prices with this round's runners + SOL anchor. Runner-ups stay in
    the engine until picked; picked cards fill empty battle seats; ⭐ Publish puts one on the stage for good."""
    rnd = (rd.get('rounds') or [None])[-1]
    picks = sorted(rd.get('creatorPicks') or [])
    if not rnd or not rnd.get('picks') or (rd.get('scenarioStageRound') == rnd.get('id') and rd.get('scenarioStagePicks') == picks):
        return None
    scen = [x for x in _rn.scenarios(rd.get('rounds') or [], rd.get('paths') or {}, now, _hq.RISK_DIALS) if x['id'] in set(picks)]
    anchor = await _top_anchor()
    cards = _rn.scenario_cards(scen, rnd['picks'], anchor, top=8, losers_ok=True)
    pgb_ = rd.get('pgBattle') or {}
    live_ = await _runner_live()
    cand_ = [{'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'mint': r.get('mint')} for r in live_.get('passing') or [] if r.get('pairAddress')]
    for i, c in enumerate(cards):   # 🎨 a picked card plays the playground's shape (≥ 4 coins, ≤ 2 pools) on the timeframe it proved best
        cards[i] = _pgb.fit_shape(c, cand_, _pgb.MIN_COINS)
        mins = _pgb.assign_clock((pgb_.get('cardClocks') or {}).get(c['id']), i)
        cards[i]['clock'] = mins; cards[i]['cfg'] = {**(c.get('cfg') or {}), 'rotateHours': round(mins / 60, 4)}
    if not cards:
        async with _admin_lock:
            d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['scenarioStage'] = []; d['scenarioStageRound'] = rnd.get('id'); d['scenarioStagePicks'] = picks; _json_save(RUNNERS_PATH, d)
        _arena_mega_cache.update(at=0.0, data=None)
        return 0
    px = await _hq_prices([l for c in cards for l in c['legs']])
    stage = [{'id': f"scen-{c['id']}-{str(rnd['id'])[:6]}", 'src': c['id'], 'emoji': c['name'].split(' ', 1)[0], 'name': c['name'].split(' ', 1)[-1], 'at': now, 'tp': c['tp'], 'sl': c['sl'],
              'dial': c['dial'], 'cfg': c['cfg'], 'label': c['label'], 'clock': c.get('clock'),
              'legs': [{'pairAddress': l['pairAddress'], 'symbol': l.get('symbol'), 'baseAddress': l.get('mint'), 'weight': l['weight'], 'runner': l['role'] == 'runner', 'entry': _fuse._f(px.get(l['pairAddress']))}
                       for l in c['legs'] if _fuse._f(px.get(l['pairAddress'])) > 0]} for c in cards]
    async with _admin_lock:
        d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
        vers = d.setdefault('scenarioVersions', {})
        for st in stage:   # each new deal of the same scenario = its next version (v.01, v.02 …)
            vers[st['src']] = int(vers.get(st['src']) or 0) + 1; st['version'] = vers[st['src']]
        d['scenarioStage'] = stage; d['scenarioStageRound'] = rnd.get('id'); d['scenarioStagePicks'] = picks; _json_save(RUNNERS_PATH, d)
    _arena_mega_cache.update(at=0.0, data=None)
    return len(stage)


def _pg_pick_ok(rd, sid):
    """🎨 A big card reaches the Arena only once it EARNED a playground seat: the background field (≤ 8) competes and only its top
    3 (`pg_battle.shown`) can be picked. With no field yet (battles off / still dealing) any scenario card can be picked."""
    b = rd.get('pgBattle') or {}
    ids = list(b.get('cards') or {})
    return len(ids) < _pgb.SHOWN or sid in _pgb.shown(b.get('record'), b.get('pcts'), ids)


@app.post('/api/reputation/admin/fuses/scenario-pick')
async def scenario_pick(request: Request, body: dict):
    """🎨 Creator's pick: HQ puts an engine runner-up on the Arena (or takes it off). Dealt right away. Audited."""
    admin = _require_admin(request)
    sid = str(body.get('id') or '')[:40]
    if not sid:
        raise HTTPException(400, 'Pick a scenario card.')
    async with _admin_lock:
        d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
        if body.get('on', True) and sid not in (d.get('creatorPicks') or []) and not _pg_pick_ok(d, sid):
            raise HTTPException(400, f"Only the playground's top {_pgb.SHOWN} big cards can be picked — this one is still competing in the background.")
        cur = [x for x in d.get('creatorPicks') or [] if x != sid] + ([sid] if body.get('on', True) else [])
        d['creatorPicks'] = cur[-4:]; _json_save(RUNNERS_PATH, d)   # max 4 big engine cards on the Arena
        ad = _admin_load(); _audit(ad, admin, 'creator-pick', f"{sid} {'on' if body.get('on', True) else 'off'}"); _admin_save(ad)
    await _scenario_stage(_json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}), time.time())
    return {'creatorPicks': _json_load(RUNNERS_PATH, {}).get('creatorPicks') or []}


async def _engine_auto(now):
    """🔧 Auto-strength, once per runner round: if another engine dial is PROVEN better (runners.auto_pick on the dial proof),
    switch to it and log it (audit + admin inbox). Off when HQ turned auto-tune off (RUNNERS_PATH.autoTune = False)."""
    rd = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
    await _scenario_stage(rd, now)
    if rd.get('autoTune') is not False and rd.get('rounds'):   # 🩺 doctor: learn which picks win, apply that filter or sit out
        cfg_d = _rn.clean_cfg(rd.get('cfg') or {})
        f24 = _rn.filter_proof(rd['rounds'], rd.get('paths') or {}, now, cfg_d, 24 * 3600)
        f72 = _rn.filter_proof(rd['rounds'], rd.get('paths') or {}, now, cfg_d, 72 * 3600)
        doc = _rn.doctor(f24, f72)
        if doc['filter'] != rd.get('pickFilter') or doc['sitOut'] != bool(rd.get('sitOut')):
            async with _admin_lock:
                d_ = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); d_['pickFilter'] = doc['filter']; d_['sitOut'] = doc['sitOut']; d_['doctorWhy'] = doc['why']; d_['doctorAt'] = now
                _json_save(RUNNERS_PATH, d_)
                ad = _admin_load(); _audit(ad, 'engine-auto', 'runners-config', f"🩺 doctor: filter {doc['filter'] or 'none'} · sit out {doc['sitOut']} — {doc['why']}"[:200]); _admin_save(ad)
            for w in _admin_wallets():
                notify(w, 'admin', f"🩺 Fuse engine doctor: {('pick filter → ' + _rn.PICK_FILTERS[doc['filter']][0]) if doc['filter'] else ('sitting out runners' if doc['sitOut'] else 'filter cleared')} — {doc['why']}",
                       url='/terminal/command?tab=fuse', once=f"doctor-{doc['filter']}-{doc['sitOut']}-{int(now // 3600)}", meta={'claim': doc['why'], 'source': 'Runner rounds (paper, real prices)'})
            rd = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
    if rd.get('autoTune') is False or not rd.get('rounds'):
        return None
    # 💡 scenario winner → runner exits (same TP×SL combo best in 24h AND 72h, ahead of the current exits) — audited
    cfg0 = _rn.clean_cfg(rd.get('cfg') or {})
    ex, ex_why = _rn.exits_pick({w: _rn.scenario_grid(rd['rounds'], rd['paths'], now, sec) for w, sec in (('24h', 86400), ('72h', 3 * 86400))},
                                (int(cfg0.get('runnerTp2') or 100), int(cfg0.get('runnerStop') or 30)))
    if ex:
        async with _admin_lock:
            d0 = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); d0['cfg'] = {**(d0.get('cfg') or {}), 'runnerTp2': ex[0], 'runnerStop': ex[1]}; d0['cfgDial'] = 'custom'; _json_save(RUNNERS_PATH, d0)
        ad0 = _admin_load(); _audit(ad0, 'engine-auto', 'runners-config', f'scenario exits → TP +{ex[0]}% / stop −{ex[1]}%: {ex_why}'[:300]); _admin_save(ad0)
        rd = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
    proofs = {w: _rn.dial_proof(rd['rounds'], rd['paths'], now, _hq.RISK_DIALS, window=sec) for w, sec in _rn.PROOF_WINDOWS.items()}
    dial, why = _rn.auto_pick_multi(proofs, rd.get('cfgDial'))
    if not dial or dial not in _rn.ENGINE_DIALS:
        return None
    async with _admin_lock:
        d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['cfg'] = _rn.engine_dial(dial, d.get('cfg') or {}); d['cfgDial'] = dial; _json_save(RUNNERS_PATH, d)
    ad = _admin_load(); _audit(ad, 'engine-auto', 'runners-config', f'auto-strength → {dial}: {why}'); _admin_save(ad)
    for adm in _admin_wallets():
        notify(adm, 'shield', f"🔧 Engine auto-strength: switched to the {dial} dial — {why}. Turn off in HQ › Fuse › Engine.", url='/terminal/command?tab=fuse', once=f"engine-auto-{dial}-{int(now // 3600)}")
    return dial


def _engine_nudge(now):
    """Once per new set of suggestions: tell HQ a stronger engine config is waiting (they click to apply)."""
    s = _rn.suggest_cfg(_runner_cfg())
    if s:
        key = ','.join(f"{x['key']}:{x['to']}" for x in s)
        for adm in _admin_wallets():
            notify(adm, 'shield', f"⚡ Stronger Fuse engine config found ({len(s)} settings) — review and apply in HQ › Fuse › Engine.",
                   url='/terminal/command?tab=fuse', once=f"engine-{hashlib.sha1(key.encode()).hexdigest()[:12]}", meta={'claim': s[0]['why'], 'source': 'runners.RECOMMENDED'})
    return s


@app.get('/api/reputation/runners/discover')
async def runners_discover():
    """Fuse 🧬 › Runners: one gated list of good runners, tagged by every source that independently likes them —
    arena round, lit cards, pump scan, snipers-out radar, creators' picks (proven callers + published Fuses). 20s cache."""
    now = time.time()
    if _runner_disc_cache['data'] and now - _runner_disc_cache['at'] < 40 and not _FUSE_FORCE.get():
        return _runner_disc_cache['data']
    live, board = await asyncio.gather(_runner_live(), caller_board(days=30))
    d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
    cfg = _runner_cfg()
    tags: dict = {}
    tag = lambda m, k, v: m and tags.setdefault(m, {}).setdefault(k, v)
    rnd = d['rounds'][-1] if d['rounds'] else None
    for p in (rnd or {}).get('picks') or []:
        tag(p['mint'], 'arena', f"{p.get('lane', 'runner')} lane · round {str((rnd or {}).get('id', ''))[:4]}")
    for c in d.get('litCards') or []:
        if now - c['at'] <= 72 * 3600:
            res = _rn.card_result(c, d['paths'], now, cfg)
            for p in c['picks']:
                tag(p['mint'], 'lit', f"lit card {res:+.1f}% since lit")
    for r in live['passing']:   # every coin passing every gate is a pump-scan find (never a dead tab while anything passes)
        tag(r['mint'], 'pump', f"passes every gate · score {round(_fuse._f(r.get('score')))}")
        if r.get('bondTier') == 'watch':
            tag(r['mint'], 'watch', f"{_fuse._f(r.get('curve')):.0f}% up the curve, rep-confirmed — {r.get('smartBuyers')} smart buyers")
        if _rn.near_bond(r, cfg):
            tag(r['mint'], 'bond', f"{_fuse._f(r.get('curve')):.0f}% up the curve, {r.get('buyShare')}% buys — about to bond")
    for e in _radar['events']:
        if e.get('kind') == 'snipers-out' and now - (e.get('at') or 0) < 6 * 3600:
            tag(e.get('mint'), 'snipers', 'every flagged sniper sold')
    sharp = {r.get('callerAddress'): r for r in board['rows'] if r.get('calls', 0) >= 3 and r.get('hitRate', 0) >= 0.5}
    for c in (_json_load(CALLS_PATH, {}).get('calls') or {}).values():
        if c.get('callerAddress') in sharp and now - (c.get('at') or 0) < 48 * 3600:
            tag(c.get('mint'), 'creator', f"called by {c.get('caller') or 'a sharp caller'} ({round(sharp[c['callerAddress']]['hitRate'] * 100)}% hit)")
    for f in (_json_load(FUSES_PATH, {'fuses': {}}).get('fuses') or {}).values():
        if f.get('enabled', True):
            for leg in f.get('legs') or []:
                if leg.get('role') == 'runner':
                    tag(leg.get('baseAddress') or leg.get('mint'), 'creator', f"in the {f.get('name')} Fuse")
    for c in _arena_mega_cache.get('data') or []:   # 🏟 runner coins on the cards fighting in the Arena right now (stage, tiers, picks)
        for leg in c.get('legs') or []:
            if leg.get('runner') or c.get('kind') in ('lit', 'round'):
                tag(leg.get('baseAddress') or leg.get('mint'), 'arena', f"on {c.get('emoji') or ''} {c.get('name') or 'an Arena card'}".strip())
    passing_mints = {r['mint'] for r in live['passing']}
    for f in (_json_load(FUSES_PATH, {'fuses': {}}).get('fuses') or {}).values():   # 📣 any passing coin inside a published HQ Fuse
        for leg in f.get('legs') or []:
            m_ = leg.get('baseAddress') or leg.get('mint')
            if f.get('enabled', True) and m_ in passing_mints:
                tag(m_, 'creator', f"in the {f.get('name')} Fuse")
    grads = _rn.fresh_grads(live['dropped'])
    for r in grads:
        tag(r['mint'], 'grad', f"graduated, passes every other gate · score {round(_fuse._f(r.get('score')))}")
    rows = [{**r, 'passedAt': now} for r in _rn.discover(live['passing'] + grads, tags, limit=80)]
    rows = _rn.sticky((_runner_disc_cache.get('data') or {}).get('runners'), rows, live['dropped'], now)   # 🧲 never a flickering list
    data = {'runners': rows, 'counts': {k: sum(1 for r in rows if any(s['kind'] == k for s in r['sources'])) for k in _rn.SOURCES},
            'sources': _rn.SOURCES, 'nextRoundAt': (rnd['at'] + _rn.ROUND_SECONDS) if rnd else now, 'gates': [g[1] for g in _rn.gates(cfg)],
            'swaps': ((rnd or {}).get('swaps') or [])[-5:], 'at': now, 'seen': live['seen'],
            # This round's picks with their live state (still passing = addable; failing shows why).
            'round': [{**{k: p.get(k) for k in ('mint', 'symbol', 'logo', 'lane', 'pairAddress', 'score', 'entry')}, 'passing': p['mint'] in {x['mint'] for x in live['passing']},
                       'move': _round_move(p, live),
                       'gates': next((x.get('gates') for x in live['dropped'] if x['mint'] == p['mint']), None) or ([] if p['mint'] in {x['mint'] for x in live['passing']} else ['left the live feed'])}
                      for p in (rnd or {}).get('picks') or []],
            # ⚠️ NEW runners: minutes-old coins through the tight launch filter (site + X, clean creator first) — riskier lane
            'newRunners': [{k: x.get(k) for k in ('mint', 'symbol', 'logo', 'pairAddress', 'mcap', 'vol1h', 'chg1h', 'buyShare', 'ageH', 'score', 'creatorRep', 'why', 'price')}
                           for x in _rn.new_runners(live['passing'] + [x for x in live['dropped'] if (x.get('gates') or [''])[0].startswith(('mcap', 'vol'))])],
            # Watch-only: the busiest coins that FAILED a gate, with the reason — shown so the tab is never dead, never addable.
            'watching': [{k: x.get(k) for k in ('mint', 'symbol', 'logo', 'mcap', 'vol1h', 'chg1h', 'buyShare', 'gates')}
                         for x in sorted(live['dropped'], key=lambda x: -_fuse._f(x.get('vol1h')))[:12]]}
    _runner_disc_cache.update(at=now, data=data)
    return data


@app.get('/api/reputation/runners')
async def runners_board():
    """FUSE RUNNERS: live board (every arriving coin gated + scored), the current round by lane, recent rounds' paper
    results and the proof that decides whether the Fuse button lights up."""
    live, sol_usd = await asyncio.gather(_runner_live(), _sol_usd_live())
    d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
    now = time.time()
    rnd = d['rounds'][-1] if d['rounds'] else None
    cfg = _runner_cfg(); ex = _rn.exits(cfg)
    hist = []
    for r in reversed(d['rounds'][-8:-1] if len(d['rounds']) > 1 else []):
        mults = [_rn.play_exits(p['lane'], p['entry'], [x for t, x in d['paths'].get(p['mint'], []) if t > r['at']], cfg) for p in r['picks']]
        hist.append({'id': r['id'], 'at': r['at'], 'symbols': [p.get('symbol') for p in r['picks']], 'pct': round((sum(mults) / len(mults) - 1) * 100, 2) if mults else 0.0})
    cur = {p['mint']: p for p in live['passing']}
    picks = [{**p, 'now': cur.get(p['mint'], {}).get('price') or p['price'], 'exits': ex[p['lane']]['label']} for p in (rnd or {}).get('picks', [])]
    return {'live': live['passing'][:60], 'dropped': live['dropped'][:30], 'seen': live['seen'], 'widen': live.get('widen'), 'round': rnd and {**rnd, 'picks': picks},
            'nextRoundAt': (rnd['at'] + _rn.ROUND_SECONDS) if rnd else now, 'history': hist, 'proof': _rn.proof(d['rounds'], d['paths'], now, cfg=cfg),
            'exits': {k: v['label'] for k, v in ex.items()}, 'gates': [g[1] for g in _rn.gates(cfg)], 'lightMinRounds': cfg['lightRounds'], 'solUsd': sol_usd,
            'litCards': [{**c, 'pct': _rn.card_result(c, d['paths'], now, cfg)} for c in reversed((d.get('litCards') or [])[-12:])],
            'lanes': (lp := _rn.lane_proofs(d['rounds'], d['paths'], now, cfg)), 'laneWeights': _rn.lane_weights(lp)}


@app.post('/api/reputation/admin/runners/autotune')
async def runners_autotune(request: Request):
    admin = _require_admin(request); on = bool((await request.json()).get('on'))
    async with _admin_lock:
        d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['autoTune'] = on; _json_save(RUNNERS_PATH, d)
    ad = _admin_load(); _audit(ad, admin, 'runners-autotune', 'on' if on else 'off'); _admin_save(ad)
    return {'autoTune': on}



@app.get('/api/reputation/admin/fuses/playground')
async def fuse_playground(request: Request):
    """🧪 Engine playground: every scenario the engines are testing — strategy runs, bloodline, dial proofs over 6h/24h/72h,
    top-tier cards, runner rounds + lit cards, auto-tune log — and what's proven + ready for the Arena."""
    _require_admin(request)
    now = time.time()
    d = _json_load(FUSE_HQ_PATH, {}); rd = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
    vals = [_hq.arena_value(e, {}, now) for e in d.get('arena') or []]
    board = _hq.arena_board(vals)
    dials = {w: _rn.dial_proof(rd.get('rounds') or [], rd.get('paths') or {}, now, _hq.RISK_DIALS, window=sec) for w, sec in _rn.PROOF_WINDOWS.items()}
    prime = await _prime_view()
    auto = [a for a in (_admin_load().get('audit') or []) if a.get('action') in ('runners-config', 'runners-autotune', 'arena-prime')][-12:][::-1]
    return {'counts': {'arenaRuns': len(vals), 'settled': sum(1 for v in vals if v.get('settled')), 'open': sum(1 for v in vals if not v.get('settled')),
                       'bloodline': len(d.get('bloodline') or []), 'runnerRounds': len(rd.get('rounds') or []), 'litCards': len(rd.get('litCards') or []),
                       'dialScenarios': sum(p.get('rounds', 0) for proof in dials.values() for p in proof.values()), 'tierCards': len(prime),
                       'published': len(_json_load(FUSES_PATH, {'fuses': {}})['fuses'])},
            'board': board, 'dials': dials, 'bloodline': (d.get('bloodline') or [])[-12:][::-1], 'prime': [{k: c.get(k) for k in ('label', 'tier', 'pnlPct', 'lowPct', 'goodDays', 'loggedDays')} for c in prime],
            'autoLog': auto, 'engineDial': rd.get('cfgDial') or 'custom', 'autoTune': rd.get('autoTune') is not False,
            'gateRegret': _rn.gate_regret(rd.get('dropLog') or [], await _hq_prices([{'chainId': 'solana', 'pairAddress': e['pairAddress']} for e in (rd.get('dropLog') or [])[-120:] if e.get('pairAddress')]), now),
            'scenarios': (scen := _rn.scenarios(rd.get('rounds') or [], rd.get('paths') or {}, now, _hq.RISK_DIALS)),
            'scenarioCards': await _pg_scenario_cards(rd, scen, now, coins=_pgb.REGULAR_COINS),
            'shownIds': _pgb.shown((rd.get('pgBattle') or {}).get('record'), (rd.get('pgBattle') or {}).get('pcts'), list(((rd.get('pgBattle') or {}).get('cards') or {}))),
            'filters': {'24h': _rn.filter_proof(rd.get('rounds') or [], rd.get('paths') or {}, now, _rn.clean_cfg(rd.get('cfg') or {}), 24 * 3600),
                        '72h': _rn.filter_proof(rd.get('rounds') or [], rd.get('paths') or {}, now, _rn.clean_cfg(rd.get('cfg') or {}), 72 * 3600)},
            'doctor': {'filter': rd.get('pickFilter'), 'sitOut': bool(rd.get('sitOut')), 'why': rd.get('doctorWhy'), 'at': rd.get('doctorAt')},
            'pgBattle': _pg_battle_view(rd),
            **_hq.playground_ready(board, dials, prime, battle_rows=_pgb.ready_rows((rd.get('pgBattle') or {}).get('record'), {k: c.get('name') for k, c in ((rd.get('pgBattle') or {}).get('cards') or {}).items()}))}

async def _top_anchor():
    """⚓ The engine cards' anchor: the most ACTIVE major right now (`fuse.rank_anchors`), never SOL by name."""
    top = next(iter(_fuse.rank_anchors(await _majors_rows())), None)
    return {'chainId': 'solana', 'pairAddress': top['pairAddress'], 'symbol': top.get('symbol'), 'mint': top.get('baseAddress')} if top else None


async def _pg_scenario_cards(rd, scen=None, now=None, losers_ok=False, top=6, coins=None):
    """The playground's best scenario cards (this round's gated runners + SOL anchor), versioned and tagged with where they're listed.
    `coins` = the regular card shape (6 coins, ≤ 2 pools, topped up with the best gated runners)."""
    scen = scen if scen is not None else _rn.scenarios(rd.get('rounds') or [], rd.get('paths') or {}, now or time.time(), _hq.RISK_DIALS)
    anchor = await _top_anchor()
    listed = {**{x: 'pick' for x in rd.get('creatorPicks') or []}, **{x.get('src'): 'bench' for x in rd.get('scenarioStage') or []},
              **{f.get('fromScenario'): 'stage' for f in (_json_load(FUSES_PATH, {'fuses': {}}).get('fuses') or {}).values() if f.get('arena') and f.get('fromScenario')}}
    out = _rn.tag_versions(_rn.scenario_cards(scen, ((rd.get('rounds') or [{}])[-1] or {}).get('picks'), anchor, top=top, losers_ok=losers_ok), rd.get('scenarioVersions') or {}, listed)
    if coins:
        cand = [{'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'mint': r.get('mint')} for r in (await _runner_live()).get('passing') or [] if r.get('pairAddress')]
        out = [_pgb.fit_shape(c, cand, coins) for c in out]
        for c in out:   # weights back to 100% after the top-up
            tot = sum(_fuse._f(l.get('weight')) for l in c['legs']) or 1.0
            c['legs'] = [{**l, 'weight': round(_fuse._f(l.get('weight')) / tot * 100, 1)} for l in c['legs']]
    return out


def _pg_battle_view(rd):
    b = rd.get('pgBattle') or {}
    cards = b.get('cards') or {}
    view = lambda k: {**{x: (cards.get(k) or {}).get(x) for x in ('id', 'name', 'dial', 'tp', 'sl', 'swaps', 'phase', 'rounds', 'bredFrom')}, 'pct': (b.get('pcts') or {}).get(k),
                      'dna': (b.get('dna') or {}).get(k), 'dnaLabel': _dna.label((b.get('dna') or {}).get(k)) if (b.get('dna') or {}).get(k) else None,
                      'legs': [{x: l.get(x) for x in ('symbol', 'role', 'pairAddress')} for l in (cards.get(k) or {}).get('legs') or []], 'record': (b.get('record') or {}).get(k),
                      'clock': _pgb.assign_clock((b.get('cardClocks') or {}).get(k), list(cards).index(k) if k in cards else 0), 'clocks': (b.get('cardClocks') or {}).get(k) or {}}
    return {'cfg': _pgb.clean_cfg(b.get('cfg')), 'clockStats': b.get('clockStats') or {}, 'bestClock': b.get('bestClock'), 'roundNow': b.get('roundMins'), 'locked': b.get('locked') or [], 'scrapped': len(b.get('scrapped') or []), 'picks': rd.get('creatorPicks') or [], 'endsAt': b.get('endsAt'), 'pairs': [{'a': view(p['a']), 'b': view(p['b'])} for p in b.get('pairs') or []],
            'field': [view(k) for k in cards], 'shown': [view(k) for k in _pgb.shown(b.get('record'), b.get('pcts'), list(cards))],
            'log': (b.get('log') or [])[-12:][::-1], 'record': b.get('record') or {}, 'names': {k: c.get('name') for k, c in cards.items()},
            'brain': {**_dna.best(b.get('brain') or {}), 'label': _dna.label(_dna.best(b.get('brain') or {})['dna']), 'scores': b.get('brain') or {}}}


async def _pg_battle_tick(now):
    """⚔ Engine playground battles (paper, HQ only): deal the best scenario cards, swap TP / stop / dead coins mid-round,
    settle at the bell (bigger % wins), winners keep their coins, losers re-bred from this round's picks."""
    rd = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}})
    b = rd.get('pgBattle') or {}
    cfg = _pgb.clean_cfg(b.get('cfg'))
    if not cfg['on']:
        return None
    scs = {c['id']: c for c in await _pg_scenario_cards(rd, None, now, losers_ok=True, top=max(8, cfg['cards']))}   # battles field the top-ranked scenarios even when negative
    if len(scs) < 2:
        return None
    cards = dict(b.get('cards') or {})
    scrapped = set(b.get('scrapped') or [])   # 🗑 dead strategies stay off the field (record kept)
    want = [k for k in scs if k not in scrapped][:cfg['cards']]
    legs = [{'chainId': 'solana', 'pairAddress': l['pairAddress']} for k in want for l in (cards.get(k) or scs[k])['legs']]
    live = await _runner_live()
    cand = [r for r in live.get('passing') or [] if r.get('pairAddress')]
    pairs_ = await _fuse_pairs(legs + [{'chainId': 'solana', 'pairAddress': r['pairAddress']} for r in cand[:12]])
    prices = {k: _fuse._f(v.get('priceUsd')) for k, v in pairs_.items()}
    liqs = {k: _fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_.items()}
    quiet = {k: not (_fuse._f(((v.get('txns') or {}).get('m5') or {}).get('buys')) + _fuse._f(((v.get('txns') or {}).get('m5') or {}).get('sells'))) and not _fuse._f((v.get('volume') or {}).get('m5'))
             for k, v in pairs_.items()}
    cand = [{'pairAddress': r['pairAddress'], 'symbol': r.get('symbol'), 'mint': r.get('mint'), 'price': prices.get(r['pairAddress']) or r.get('price'), 'liq': liqs.get(r['pairAddress'])} for r in cand]
    rcfg_ = _runner_cfg()
    targets = _pgb.coin_targets(int(rcfg_.get('autoCoins') or 4) + int(rcfg_.get('autoPools') or 3))   # HQ's amount: half · same · double, ≥ 4
    for i, k in enumerate(want):   # deal any missing card — ≥ 4 coins, ≤ 2 pools; the engine experiments with the coin count
        if k not in cards or not cards[k].get('legs'):
            cards[k] = {**_pgb.deal(_pgb.fit_shape(scs[k], cand, targets[i % len(targets)]), prices, liqs, now, cfg['sizeUsd']), 'target': targets[i % len(targets)]}
    dna = {k: v for k, v in (b.get('dna') or {}).items() if k in want}
    dna = _dna.assign([{'id': k, 'dial': scs[k].get('dial')} for k in want], known=dna)   # 🧬 every battle card plays its own DNA
    results = []
    if now >= _fuse._f(b.get('endsAt')):
        pcts = {k: _pgb.round_pct(cards[k], prices, liqs) for k in cards if k in want}
        results, record, losers = _pgb.settle(b.get('pairs'), pcts, b.get('record'), now)
        # 🧠 the engine learns which DNA wins (trait win rates), then breeds the first loser with the winning DNA (exploit) — the rest
        # get fresh unique DNA (explore)
        sc_ = _dna.learn([{'winner': r_['winner'], 'loser': r_['b'] if r_['winner'] == r_['a'] else r_['a']} for r_ in results if r_.get('winner')], dna)
        brain = b.get('brain') or {}
        for t_, vals in sc_.items():
            for v_, st_ in vals.items():
                cur_ = brain.setdefault(t_, {}).setdefault(v_, {'w': 0, 'n': 0}); cur_['w'] += st_['w']; cur_['n'] += st_['n']
        b['brain'] = brain
        best_ = _dna.best(brain)['dna']; exploited = False
        locked = set(b.get('locked') or [])   # 🔒 HQ-locked cards keep their coins + DNA even after a loss
        beat_by = {(r_['b'] if r_['winner'] == r_['a'] else r_['a']): r_['winner'] for r_ in results if r_.get('winner')}
        lineage = dict(b.get('lineage') or {})
        for k in want:
            if k in losers and k not in locked:   # 🧬 re-bred: same scenario, this round's picks, fresh $ (same coin-count experiment)
                cards[k] = {**_pgb.deal(_pgb.fit_shape(scs[k], cand, cards.get(k, {}).get('target') or targets[0]), prices, liqs, now, cfg['sizeUsd']), 'target': cards.get(k, {}).get('target') or targets[0]}
                par = beat_by.get(k)
                if par and cards.get(par):   # it now plays the strategy that beat it → named as that strategy's next version (v.0x)
                    gen = int((lineage.get(par) or {}).get('gen') or 0) + 1
                    lineage[k] = {'parent': par, 'gen': gen}
                    cards[k]['name'] = _pgb.child_name(cards[par].get('name'), gen + 1); cards[k]['bredFrom'] = cards[par].get('name')
                if not exploited and _dna.sig(best_) not in {_dna.sig(v) for kk, v in dna.items() if kk != k}:
                    dna[k] = best_; exploited = True
                else:
                    dna.pop(k, None)
            else:             # winner keeps its coins, re-shaped by its DNA cycle (true fills); the next round counts from here
                cards[k] = _pgb.cycle_rebalance(cards[k], dna.get(k), pcts.get(k), prices, liqs)
                cards[k] = {**cards[k], 'roundUsd': _pgb.value(cards[k], prices, liqs)}
        dead_now = _pgb.dead(record, locked)
        for k in dead_now:   # 🗑 scrap strategies that only lose — they stop using data, the record stays
            scrapped.add(k); cards.pop(k, None); dna.pop(k, None)
        if dead_now and set(dead_now) & set(rd.get('creatorPicks') or []):   # a dead big card leaves the Arena too; the engine deals new ones
            async with _admin_lock:
                rd2 = _json_load(RUNNERS_PATH, {}); rd2['creatorPicks'] = [x for x in rd2.get('creatorPicks') or [] if x not in set(dead_now)]; _json_save(RUNNERS_PATH, rd2)
            rd['creatorPicks'] = [x for x in rd.get('creatorPicks') or [] if x not in set(dead_now)]
        want = [k for k in want if k not in scrapped]
        dna = _dna.assign([{'id': k, 'dial': scs[k].get('dial')} for k in want], known=dna)
        played = int(b.get('roundMins') or cfg['roundMins'])
        b['clockStats'] = _pgb.clock_learn(b.get('clockStats'), played, list(pcts.values()))   # ⏱ what each round length did
        b['cardClocks'] = _pgb.card_clock_learn(b.get('cardClocks'), played, pcts)            # ⏱ … and per card: its own best timeframe
        nxt_clock = _pgb.next_clock(cfg, int(b.get('bells') or 0))   # first round 5 min, then 15 · 30 · 60 · 5 …
        b = {**b, 'lineage': {k: v for k, v in lineage.items() if k in want}, 'bells': int(b.get('bells') or 0) + 1, 'roundMins': nxt_clock, 'bestClock': _pgb.best_clock(b['clockStats']),
             'record': record, 'scrapped': sorted(scrapped)[-300:], 'pairs': _pgb.pair_up(want), 'endsAt': now + nxt_clock * 60,
             'log': ((b.get('log') or []) + [{**r_, 'aName': cards.get(r_['a'], {}).get('name'), 'bName': cards.get(r_['b'], {}).get('name')} for r_ in results])[-40:]}
    else:
        for k in want:
            cards[k] = _pgb.tick(cards[k], prices, liqs, quiet, cand, cfg, now, dna.get(k))
    b['cards'] = {k: cards[k] for k in want}
    b['dna'] = dna
    b['pcts'] = {k: _pgb.round_pct(cards[k], prices, liqs) for k in want}
    b['cfg'] = cfg
    async with _admin_lock:
        d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['pgBattle'] = b; _json_save(RUNNERS_PATH, d)
    return len(results)


import pg_sim as _pgs
PG_SIM_PATH = DATA_DIR / 'pg_sim.json'   # its own file: never bloats runners.json


async def _pg_sim_tick(now):
    """🧠 Background playground: 300 sim cards (random clock / TP / SL / hold / rotate-only-losers) replayed over the REAL recorded
    price paths of the last 24h and 6h, fees on every swap. The brain keeps the trait scores; HQ can apply its pick to the tier engine."""
    paths = _json_load(RUNNERS_PATH, {}).get('paths') or {}
    res24, res6 = await asyncio.to_thread(_pgs.run, paths, now, 200, 24), await asyncio.to_thread(_pgs.run, paths, now, 100, 6)
    res = res24 + res6
    if not res:
        return 0
    d = _json_load(PG_SIM_PATH, {})
    score = _pgs.learn(res)
    was = _prime.weather(d)['level']
    d['prevBest'] = d.get('best') or {}   # 🧷 the self-fix only moves a setting when the same value wins twice in a row
    d.update(at=now, summary=_pgs.summary(res), s24=_pgs.summary(res24), s6=_pgs.summary(res6), score=score, best=_pgs.best(score), byClock=_pgs.by_clock(res),
             history=((d.get('history') or []) + [{'at': now, **_pgs.summary(res)}])[-96:])
    _json_save(PG_SIM_PATH, d)
    wx = _prime.weather(d)
    if wx['level'] != was:   # 🌦 the real card's runner rule just changed → tell the owner once, in plain words
        say = {'clear': '☀ Runner weather cleared — the real card may buy every gated runner again.',
               'rain': f"🌧 Runner weather turned (sims {wx['avgPct']:+.1f}%) — the real card now buys only strong runners in deep pools.",
               'storm': f"⛈ Runner storm (sims {wx['avgPct']:+.1f}%) — the real card buys no runners, new majors only, until it clears."}[wx['level']]
        for w in _owner_wallets():
            notify(w, 'fuse-card', say, url='/terminal/hq?tab=fuse', push=True, once=f"wx-{wx['level']}-{int(now // 3600)}",
                   meta={'claim': 'Runner weather', 'source': f"{wx['n']} sim cards on real recorded prices"})
    await _engine_self_fix(now, d)
    return len(res)


def _brain_patch(cfg, s24, best, prev=None, owner_set=()):
    """What the sim brain would change on ONE config (paper or the real card's own); {} when its 🧠 switch is off. Keys the OWNER set
    by hand (`owner_set`, e.g. 5-min rounds with patience 2) are never touched — the owner picks, the brain only fills the rest."""
    if not cfg.get('autoBrain', True):
        return {}
    patch = {}
    bad = s24.get('n', 0) >= 100 and _fuse._f(s24.get('avgPct')) <= -5
    if bad != bool(cfg.get('strictRunners')):
        patch['strictRunners'] = bad
    floor_confirm = 3 if cfg['rotateHours'] * 60 <= 5 else 2   # 🔒 the SELF-FIX never takes patience under 3 on fast clocks. The owner may still pick 2 by hand (real guard floor = 2) — with 🧠 Auto-tune on, the brain can raise it back.
    for trait, key, cast in (('minDrop', 'rotateMinDrop', float), ('confirm', 'rotateConfirm', int)):
        b = best.get(trait)
        if b and b.get('n', 0) >= 30:
            v = max(floor_confirm, cast(b['value'])) if key == 'rotateConfirm' else cast(b['value'])
            # 🧷 no flapping: a value is applied only when the SAME value won the previous sim run too (rotateConfirm went
            # 3 → 4 → 3 → 4 every 30 min, rewriting the config and spamming every card's log)
            steady = not prev or (prev.get(trait) or {}).get('value') == b['value']
            if v != cfg.get(key) and steady:
                patch[key] = v
    return {k: v for k, v in patch.items() if k not in set(owner_set or ())}


async def _engine_self_fix(now, sim):
    """🔧 The engine fixes itself from the sim brain (cfg `autoBrain`, default on; the clock is never touched):
      • 🌧 runner weather — the last 24h of sims averaging ≤ −5% → strict runners (only coins with real flow + buyers get in);
      • the brain's rotate-only-losers threshold + patience (rounds in a row) are applied once 30+ sims back each value.
    Paper and the 💵 real card are tuned SEPARATELY, each only if its own 🧠 switch is on. Audited + a `brain` event only on cards it changed."""
    s24, best = sim.get('s24') or {}, sim.get('best') or {}
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
        paper = _prime.clean_cfg(pr.get('cfg') or {})
        real = _prime.clean_cfg(pr['realCfg']) if isinstance(pr.get('realCfg'), dict) and pr.get('realCfg') else None
        prev = sim.get('prevBest') or {}
        pp = _brain_patch(paper, s24, best, prev)
        rp = _brain_patch(real, s24, best, prev, owner_set=pr.get('realOwnerSet')) if real else {}
        if not pp and not rp:
            return None
        if pp:
            pr['cfg'] = _prime.clean_cfg({**paper, **pp})
        if rp:
            pr['realCfg'] = _prime.clean_cfg({**real, **rp})
        for c in (pr.get('cards') or {}).values():
            patch = (rp if real else pp) if c.get('real') else pp
            if patch:
                why = ' · '.join(f'{k} → {v}' for k, v in patch.items())
                c.setdefault('events', []).append({'at': now, 'kind': 'brain', 'why': f'🧠 engine self-fix from {s24.get("n", 0)} sims: {why}'})
        _json_save(FUSE_HQ_PATH, d)
    ad = _admin_load(); _audit(ad, 'engine', 'self-fix', json.dumps({'paper': pp, 'real': rp})); _admin_save(ad)
    return {**pp, **({'real': rp} if rp else {})}


@app.get('/api/reputation/fuses/strategies')
async def fuse_strategies(hours: float = Query(1.0, ge=0.01, le=48)):
    """🎯 3 strategies for a card's round length (🛡 Steady · 🧠 Engine pick · 🔥 Hunt) from the background sims on REAL recorded prices
    (fees in, re-run every ~15 min). Longer clocks than the sims play read the nearest one (said so). Never a promise."""
    bc = _json_load(PG_SIM_PATH, {}).get('byClock') or {}
    rows = [(float(k), v) for k, v in bc.items() if v.get('strategies')]
    if not rows:
        return {'clock': None, 'strategies': [], 'note': 'The sim brain needs ~15 min of recorded prices first.'}
    want = hours * 60
    clock, v = min(rows, key=lambda kv: abs(kv[0] - want))
    note = '' if abs(clock - want) < 1 else f"Sims play 5–60 min rounds; these are for {int(clock)} min, the nearest to your clock."
    return {'clock': int(clock), 'n': v.get('n'), 'strategies': v['strategies'], 'note': note, 'at': _json_load(PG_SIM_PATH, {}).get('at')}


import verdict as _verdict


VERDICT_PATH = DATA_DIR / 'fuse_verdict.json'
# 🧾 what one click can do with a verdict row (area → actions). Sim configs map onto the tier engine's own keys.
SIM_KEYS = {'minDrop': 'rotateMinDrop', 'confirm': 'rotateConfirm', 'rideAt': 'rideAt', 'trail': 'rideTrail', 'tp': 'tp', 'sl': 'sl'}


def _verdict_acts(r):
    a = r.get('area') or ''
    if a == '🧠 Sim config' and r['name'].split(' = ')[0] in {_verdict.TRAIT_WORDS.get(k, k) for k in SIM_KEYS}:
        return [['apply-one', '🃏 One card'], ['apply-real', '💵 Real card']] if r['verdict'] != 'scrap' else []   # every card keeps its OWN config — never all at once
    if a == '🏟 Strategy':
        return [['scrap', '🗑 Scrap']] if r['verdict'] != 'keep' else [['keep', '📌 Keep on rails']]
    if a == '🎚 Engine dial' and r['verdict'] == 'keep':
        return [['apply', '🎚 Use this dial']]
    if a == '⭐ Tier card' and r['verdict'] == 'scrap':
        return [['redeal', '🃏 Re-deal fresh']]
    return []


def _retired(board):
    """☠ Retired strategies = proven losers + the ones HQ scrapped from the verdict, minus the ones HQ chose to keep."""
    d = _json_load(FUSE_HQ_PATH, {})
    return (_hq.retired_styles(board) | set(d.get('scrappedStyles') or [])) - set(d.get('keptStyles') or [])


async def _verdict_build(real=True):
    now = time.time()
    d = _json_load(FUSE_HQ_PATH, {}); rd = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); sim = _json_load(PG_SIM_PATH, {})
    lg = _store.Ledger(CARD_RECORDS_PATH, table='runs')
    tiers = {}
    for tpl, t in _prime.TEMPLATES.items():
        rows = [r for r in lg.rows(limit=500, card=tpl) if not r.get('real')]
        tiers[tpl] = {'label': t.get('label') or tpl, 'pcts': [_fuse._f(r.get('pct')) for r in rows]}
    board = _hq.arena_board([_hq.arena_value(e, {}, now) for e in d.get('arena') or []])
    lanes = _rn.lane_proofs(rd.get('rounds') or [], rd.get('paths') or {}, now, _runner_cfg())
    dials = {w: _rn.dial_proof(rd.get('rounds') or [], rd.get('paths') or {}, now, _hq.RISK_DIALS, window=sec) for w, sec in _rn.PROOF_WINDOWS.items()}
    try:
        reals = await _fw_reports('') if real else []
    except Exception:
        reals = []
    out = _verdict.build(tiers, board, lanes, dials, sim.get('score'), (rd.get('pgBattle') or {}).get('clockStats'), reals)
    for r in out['rows']:
        r['acts'] = _verdict_acts(r)
    scr = set(d.get('scrappedStyles') or []); kept = set(d.get('keptStyles') or [])
    for r in out['rows']:
        if r['area'] == '🏟 Strategy':
            r['state'] = 'scrapped' if r['name'] in scr else 'kept' if r['name'] in kept else None
    return {**out, 'at': now}


@app.get('/api/reputation/admin/fuses/verdict')
async def fuse_verdict(request: Request):
    """🧾 Owner: what's working and what's not, before anything is scrapped — every engine judged on its own record (tier card runs,
    strategies, runner lanes, engine dials, playground clocks, sim configs, real runs). Fresh on open; the background keeps it hourly."""
    _require_owner(request)
    out = await _verdict_build(real=True)
    out['history'] = (_json_load(VERDICT_PATH, {}).get('history') or [])[-48:]
    return out


async def _verdict_tick(now):
    """🧾 Hourly: Fuse always runs what's-working-what's-not. A row that turns ✅ or ❌ (with enough samples) → owner inbox once."""
    prev = _json_load(VERDICT_PATH, {})
    out = await _verdict_build(real=True)
    before = {f"{r['area']}|{r['name']}": r['verdict'] for r in prev.get('rows') or []}
    flips = [r for r in out['rows'] if r['verdict'] in ('keep', 'scrap') and before.get(f"{r['area']}|{r['name']}") not in (None, r['verdict'])]
    hist = ((prev.get('history') or []) + [{'at': now, 'keep': out['keep'], 'scrap': out['scrap'], 'watch': out['watch']}])[-96:]
    _json_save(VERDICT_PATH, {**out, 'history': hist})
    for r in flips[:6]:
        for w in _owner_wallets():
            notify(w, 'admin', f"🧾 Fuse verdict: {r['area']} {r['name']} is now {'✅ working' if r['verdict'] == 'keep' else '❌ not working'} — one click in HQ › Fuse to act on it.",
                   url='/terminal/hq?tab=fuse', push=False, once=f"verdict-{r['area']}-{r['name']}-{r['verdict']}-{int(now // 86400)}", meta={'claim': r['why'], 'source': 'Fuse verdict (own records)'})
    return len(flips)


class VerdictActIn(BaseModel):
    area: str
    name: str
    act: str
    tier: str = ''


@app.post('/api/reputation/admin/fuses/verdict/act')
async def fuse_verdict_act(request: Request, p: VerdictActIn):
    """🧾 One click on a verdict row (owner, audited): ➕ add a proven sim setting to ALL paper cards (a shared edit — every card follows
    it), to ONE tier card, or to the 💵 real card · 🗑 scrap / 📌 keep a strategy on the trader rails · 🎚 use a proven engine dial ·
    🃏 re-deal a losing tier card."""
    me = _require_owner(request)
    now = time.time(); done = ''
    if p.area == '🧠 Sim config':
        word, _, val = p.name.partition(' = ')
        key = next((SIM_KEYS[k] for k in SIM_KEYS if _verdict.TRAIT_WORDS.get(k, k) == word), None)
        if not key:
            raise HTTPException(400, 'That setting has no card equivalent.')
        v = _prime.clean_exit(key, val)
        if v is None:
            raise HTTPException(400, f'{val} is not an option for {word}.')
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {})
            if p.act == 'apply-one' and p.tier in _prime.TEMPLATES:
                cfg = _prime.clean_cfg(pr.get('cfg') or {}); tc = cfg['tierCfg']; tc.setdefault(p.tier, {})[key] = v
                pr['cfg'] = _prime.clean_cfg({**(pr.get('cfg') or {}), 'tierCfg': tc}); done = f'{key} = {v:g} on {p.tier}'
            elif p.act == 'apply-real':
                base = pr.get('realCfg') if isinstance(pr.get('realCfg'), dict) and pr.get('realCfg') else pr.get('cfg') or {}
                pr['realCfg'] = _prime.clean_cfg({**base, key: v})
                pr['realOwnerSet'] = sorted(set(pr.get('realOwnerSet') or []) | {key})[:60]; done = f'{key} = {v:g} on the real card'
            else:
                raise HTTPException(400, 'Every card keeps its own config — pick one card or the real card.')
            _json_save(FUSE_HQ_PATH, d)
    elif p.area == '🏟 Strategy' and p.act in ('scrap', 'keep'):
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {})
            scr = set(d.get('scrappedStyles') or []); kept = set(d.get('keptStyles') or [])
            (scr.add if p.act == 'scrap' else scr.discard)(p.name); (kept.add if p.act == 'keep' else kept.discard)(p.name)
            d['scrappedStyles'] = sorted(scr); d['keptStyles'] = sorted(kept); _json_save(FUSE_HQ_PATH, d)
        done = f"strategy {p.name} {'scrapped' if p.act == 'scrap' else 'kept'}"
    elif p.area == '🎚 Engine dial' and p.act == 'apply':
        dial = p.name.split(' · ')[0]
        try:
            dialed = _rn.engine_dial(dial, _runner_cfg())
        except ValueError:
            raise HTTPException(400, 'Unknown dial.')
        dial, cfg = dialed.pop('dial'), _rn.clean_cfg(dialed)
        async with _admin_lock:
            d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['cfg'] = cfg; d['cfgDial'] = dial; _json_save(RUNNERS_PATH, d)
        done = f'engine dial {dial}'
    elif p.area == '⭐ Tier card' and p.act == 'redeal':
        tpl = next((t for t, x in _prime.TEMPLATES.items() if x.get('label') == p.name), None)
        if not tpl:
            raise HTTPException(400, 'Unknown tier card.')
        async with _admin_lock:
            d = _json_load(FUSE_HQ_PATH, {}); cards = (d.setdefault('prime', {}).setdefault('cards', {}))
            if (cards.get(tpl) or {}).get('real'):
                raise HTTPException(400, 'That is the real-money card — withdraw it from HQ › Fuse wallet instead.')
            cards.pop(tpl, None); _json_save(FUSE_HQ_PATH, d)
        done = f'{p.name} re-dealt'
    else:
        raise HTTPException(400, 'Nothing to do for that row.')
    ad = _admin_load(); _audit(ad, me, 'verdict-act', f'{p.area} {p.name}: {done}'[:200]); _admin_save(ad)
    return {'ok': True, 'done': done, 'at': now}


@app.get('/api/reputation/admin/fuses/sim')
async def pg_sim_view(request: Request):
    _require_admin(request)
    return _json_load(PG_SIM_PATH, {})


@app.post('/api/reputation/admin/fuses/sim/apply')
async def pg_sim_apply(request: Request):
    """Apply the brain's pick (round clock + rotate-only-losers threshold) to the tier engine. Audited."""
    me = _require_admin(request)
    b = (_json_load(PG_SIM_PATH, {}).get('best') or {})
    patch = {}
    if b.get('clock'):
        patch['rotateHours'] = int(b['clock']['value']) / 60
    if b.get('minDrop'):
        patch['rotateMinDrop'] = float(b['minDrop']['value'])
    if not patch:
        raise HTTPException(400, 'The brain needs more sims first.')
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {}); pr = d.setdefault('prime', {}); pr['cfg'] = _prime.clean_cfg({**(pr.get('cfg') or {}), **patch}); _json_save(FUSE_HQ_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'sim-apply', json.dumps(patch)); _admin_save(ad)
    return {'ok': True, 'applied': patch, 'cfg': pr['cfg']}


@app.get('/api/reputation/fuses/dna/unique')
async def fuse_dna_unique(dial: str = '', seed: str = ''):
    """🎲 A card DNA nobody on FEELESS holds right now (every Arena card + every open trader card) — so a new card plays its own way."""
    taken = dict((_json_load(FUSE_HQ_PATH, {}).get('cardDna') or {}))
    for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or []:
        if not x.get('closedAt'):
            taken[f"user:{x['id']}"] = _dna.clean({'cycle': x.get('cycle') if x.get('cycle') in ('classic', 'adaptive', 'safe', 'press', 'rescue', 'auto') else 'off', 'compound': x.get('compoundStyle') or 'smart',
                                                   'payoutPct': x.get('payoutPct', 100), 'clock': x.get('rotateHours') or 24, 'stop': x.get('slMode') or 'sell'})
    new_id = f"new:{seed or uuid.uuid4().hex[:8]}"
    d = _dna.assign([*({'id': k} for k in taken), {'id': new_id, 'dial': dial if dial in ('safe', 'balanced', 'degen') else None}], known=taken)[new_id]
    return {'dna': d, 'label': _dna.label(d)}


@app.get('/api/reputation/fuses/brain')
async def fuse_brain():
    """🧠 The engine's best card DNA so far (learned from playground battles) — the Lab offers it as a one-tap setup."""
    br = (_json_load(RUNNERS_PATH, {}).get('pgBattle') or {}).get('brain') or {}
    best = _dna.best(br)
    return {**best, 'label': _dna.label(best['dna']), 'fights': sum(v['n'] for vals in br.values() for v in vals.values()) // 5 if br else 0}


@app.post('/api/reputation/admin/runners/pick-filter')
async def runners_pick_filter(request: Request, body: dict):
    """HQ overrides the doctor: set a pick filter ('' = none) and/or sit out. Audited; the doctor may change it next round."""
    admin = _require_admin(request)
    fid = body.get('filter') or None
    if fid and fid not in _rn.PICK_FILTERS:
        raise HTTPException(400, 'Unknown pick filter.')
    async with _admin_lock:
        d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['pickFilter'] = fid
        if 'sitOut' in body:
            d['sitOut'] = bool(body['sitOut'])
        d['doctorWhy'] = 'set from HQ'; d['doctorAt'] = time.time(); _json_save(RUNNERS_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'runners-config', f"pick filter {fid or 'none'} · sit out {d.get('sitOut')}"); _admin_save(ad)
    return {'filter': fid, 'sitOut': bool(_json_load(RUNNERS_PATH, {}).get('sitOut'))}


@app.get('/api/reputation/admin/fuses/pg-battles')
async def pg_battles_get(request: Request):
    _require_admin(request)
    return _pg_battle_view(_json_load(RUNNERS_PATH, {}))


@app.post('/api/reputation/admin/fuses/pg-battles')
async def pg_battles_set(request: Request, body: dict):
    """HQ controls for playground battles: on/off, round length (5/15/30/60 min), cards (2/4/6), $ size, swap rules, or
    `reset` (fresh cards + records). Audited."""
    admin = _require_admin(request)
    async with _admin_lock:
        d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); b = d.get('pgBattle') or {}
        b['cfg'] = _pgb.clean_cfg({**(b.get('cfg') or {}), **(body.get('cfg') or {})})
        if body.get('lock'):   # 🔒 lock / unlock one playground card's configs (coins + DNA survive a loss, the brain never re-breeds it)
            lk = set(b.get('locked') or [])
            (lk.add if body.get('on', True) else lk.discard)(str(body['lock'])[:60])
            b['locked'] = sorted(lk)
        if body.get('reset'):
            b = {'cfg': b['cfg'], 'locked': b.get('locked') or []}
        elif body.get('bell'):
            b['endsAt'] = 0
        d['pgBattle'] = b; _json_save(RUNNERS_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'pg-battles', json.dumps({**b['cfg'], 'reset': bool(body.get('reset')), 'bell': bool(body.get('bell'))})[:160]); _admin_save(ad)
    await _pg_battle_tick(time.time())
    return _pg_battle_view(_json_load(RUNNERS_PATH, {}))


@app.get('/api/reputation/admin/runners/config')
async def runners_cfg_get(request: Request):
    _require_admin(request)
    return {'cfg': _runner_cfg(), 'defaults': _rn.DEFAULT_CFG, 'ranges': _rn.CFG_RANGES, 'dial': _json_load(RUNNERS_PATH, {}).get('cfgDial') or 'custom',
            'dials': {k: {'label': v['label'], 'why': v['why']} for k, v in _rn.ENGINE_DIALS.items()}, 'autoTune': _json_load(RUNNERS_PATH, {}).get('autoTune') is not False}


@app.post('/api/reputation/admin/runners/config')
async def runners_cfg_set(request: Request):
    """HQ › Runners settings: gates, round size, each lane's exits, rounds needed to light up. Range-checked; reset = defaults."""
    admin = _require_admin(request)
    body = await request.json()
    if body.get('dial'):   # 🎚 Engine dial: Safe / Balanced / Degen sets gates + lanes together
        try:
            dialed = _rn.engine_dial(str(body['dial']), _runner_cfg())
        except ValueError as e:
            raise HTTPException(400, str(e))
        dial, cfg = dialed.pop('dial'), _rn.clean_cfg(dialed)
    else:
        dial, cfg = 'custom', (_rn.DEFAULT_CFG if body.get('reset') else _rn.clean_cfg({**_runner_cfg(), **(body.get('cfg') or {})}))
    async with _admin_lock:
        d = _json_load(RUNNERS_PATH, {'rounds': [], 'paths': {}}); d['cfg'] = cfg; d['cfgDial'] = dial; _json_save(RUNNERS_PATH, d)
    _runner_live_cache.update(at=0, data=None)
    ad = _admin_load(); _audit(ad, admin, 'runners-config', json.dumps(cfg)[:160]); _admin_save(ad)
    return {'cfg': cfg, 'dial': dial}


@app.post('/api/reputation/admin/runners/round')
async def runners_force_round(request: Request):
    _require_admin(request)
    return {'round': await _runner_tick(force=True)}


class FuseLiteIn(BaseModel):
    budgetUsd: float = Field(default=10, ge=1, le=10000)


@app.post('/api/reputation/fuses/best3')
async def fuse_best3(p: FuseLiteIn):
    """Traders' one button: the best 3-pool basket for this budget, bred with the strategy that has PROVEN itself in the
    paper arena (else yield). Cached 2 min per budget bucket so it stays cheap."""
    bucket = 5 if p.budgetUsd < 12 else 20 if p.budgetUsd < 60 else 100
    hit = _fuse_lite_cache.get(bucket)
    if hit and time.time() - hit[0] < 120:
        return hit[1]
    d = _json_load(FUSE_HQ_PATH, {})
    style = _hq.best_style(_hq.arena_board([_hq.arena_value(e, {}, time.time()) for e in d.get('arena') or []]))
    raw = await _fuse_discover_pairs('solana')
    cands = {}
    for lens in _fuse.LENSES:
        for r in _fuse.discover(raw, lens, 'solana', now_ms=time.time() * 1000, limit=12):
            cands.setdefault(r['pairAddress'], r)
    metas = dict(list(cands.items())[:40])
    sol_usd = await _sol_usd_live()
    ev = await asyncio.to_thread(_fuse.evolve, metas, 3, 14, 28, style, bucket / sol_usd, sol_usd, int(time.time() // 120))
    c = ev['champions'][0] if ev['champions'] else None
    out = {'style': style, 'solUsd': sol_usd, 'proven': style != 'yield' or any(r['style'] == 'yield' and r['runs'] >= _hq.MIN_SETTLED for r in _hq.arena_board([_hq.arena_value(e, {}, time.time()) for e in d.get('arena') or []])),
           'champion': c and _champ_view(c, metas)}
    _fuse_lite_cache[bucket] = (time.time(), out)
    return out


# ---- Fuse cards: 1/1 Metaplex Core NFT per published Fuse; the HOLDER is paid its creator cut -------------------------
_asset_owner_cache: dict = {}


async def _asset_owner(asset):
    """Current owner of a Core asset (DAS getAsset), cached 5 min. None if unknown."""
    hit = _asset_owner_cache.get(asset)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            r = await _rpc(http, 'getAsset', {'id': asset})
        owner = ((r or {}).get('ownership') or {}).get('owner')
    except Exception:
        owner = None
    _asset_owner_cache[asset] = (time.time(), owner)
    return owner


async def _fuse_pay_to(f):
    """Who the creator cut is paid to: the card's on-chain holder if the Fuse has a card, else the creator."""
    card = f.get('card') or {}
    return (await _asset_owner(card['asset']) if card.get('asset') else None) or f.get('creator')


def _site(request):
    return os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/') or str(request.base_url).rstrip('/')


@app.get('/api/reputation/fuse-card/{name}')
async def fuse_card_public(name: str, request: Request):
    """Public card files: collection.json, {fid}.json (Metaplex metadata), {fid}.svg (image)."""
    if name == 'collection.json':
        return {'name': 'FEELESS Fuse Cards', 'symbol': 'FUSE', 'description': 'Each card is one published FEELESS Fuse. Its holder earns that Fuse\'s creator cut.',
                'image': f'{_site(request)}/api/reputation/fuse-card/collection.svg'}
    m = _re.match(r'^([a-f0-9]{6,16}|collection)\.(json|svg)$', name)
    store = _json_load(FUSES_PATH, {'fuses': {}})
    if not m:
        raise HTTPException(404, 'Not found')
    if m.group(1) == 'collection':
        view = {'name': 'Fuse Cards', 'score': {'grade': 'A'}, 'legs': []}
    else:
        f = store['fuses'].get(m.group(1))
        if not f:
            raise HTTPException(404, 'Not found')
        view = await _fuse_view(m.group(1), f, store)
    if m.group(2) == 'svg':
        return Response(_hq.card_svg(view), media_type='image/svg+xml', headers={'Cache-Control': 'public, max-age=600'})
    return _hq.card_meta(m.group(1), view, _site(request))


class FuseCardIn(BaseModel):
    signature: str
    collection: str = ''
    asset: str = ''


@app.post('/api/reputation/admin/fuses/card-collection')
async def fuse_card_collection(request: Request, p: FuseCardIn):
    """Record the Fuse Cards collection the owner's wallet created (verified on-chain)."""
    me = _require_owner(request)
    if not _re.match(_B58, p.collection):
        raise HTTPException(400, 'Bad collection address.')
    await _nft_verify(p.signature, me, [p.collection])
    async with _admin_lock:
        d = _json_load(FUSES_PATH, {'fuses': {}}); d['cardCollection'] = {'address': p.collection, 'sig': p.signature, 'at': time.time()}; _json_save(FUSES_PATH, d)
    return {'ok': True}


@app.post('/api/reputation/admin/fuses/{fid}/card')
async def fuse_card_minted(request: Request, fid: str, p: FuseCardIn):
    """Record a minted Fuse card (verified on-chain). From now on the card's holder is paid the creator cut."""
    me = _require_owner(request)
    if not _re.match(_B58, p.asset):
        raise HTTPException(400, 'Bad asset address.')
    d = _json_load(FUSES_PATH, {'fuses': {}})
    col = (d.get('cardCollection') or {}).get('address')
    if not col or fid not in d['fuses']:
        raise HTTPException(404, 'Create the Fuse Cards collection and publish this Fuse first.')
    if (d['fuses'][fid].get('card') or {}).get('asset'):
        raise HTTPException(400, 'This Fuse already has its card (1 of 1).')
    await _nft_verify(p.signature, me, [p.asset, col])
    async with _admin_lock:
        d = _json_load(FUSES_PATH, {'fuses': {}})
        d['fuses'][fid]['card'] = {'asset': p.asset, 'sig': p.signature, 'at': time.time()}
        _json_save(FUSES_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'fuse-card', f'{fid} → {p.asset[:8]}…'); _admin_save(ad)
    return {'ok': True}


@app.post('/api/reputation/admin/fuses/{fid}/aura')
async def fuse_aura(request: Request, fid: str):
    """Pick the live aura (outside-the-card effect) a Fuse's card shows everywhere."""
    admin = _require_admin(request)
    aura = str((await request.json()).get('aura') or '')
    if aura not in ('', *badge_cards.AURAS):
        raise HTTPException(400, 'Unknown aura.')
    async with _admin_lock:
        d = _json_load(FUSES_PATH, {'fuses': {}})
        if fid not in d['fuses']:
            raise HTTPException(404, 'No such Fuse.')
        d['fuses'][fid]['aura'] = aura; _json_save(FUSES_PATH, d)
    ad = _admin_load(); _audit(ad, admin, 'fuse-aura', f'{fid} {aura or "none"}'); _admin_save(ad)
    return {'ok': True, 'aura': aura}


@app.get('/api/reputation/admin/fuses/cards')
async def fuse_cards_admin(request: Request):
    """NFT tab: collection status + every published Fuse with its card, current holder (paid the cut) and owed amount."""
    _require_admin(request)
    store = _json_load(FUSES_PATH, {'fuses': {}})
    views = await asyncio.gather(*[_fuse_view(fid, f, store) for fid, f in store['fuses'].items()])
    pay = await asyncio.gather(*[_fuse_pay_to(f) for f in store['fuses'].values()])
    rows = [{**v, 'card': store['fuses'][v['id']].get('card'), 'payTo': p} for v, p in zip(views, pay)]
    return {'collection': store.get('cardCollection'), 'rows': rows, 'site': _site(request)}


class FuseBuy(BaseModel):
    address: str
    session: str
    signature: str


@app.post('/api/reputation/fuses/{fid}/buy')
async def fuse_buy(fid: str, payload: FuseBuy):
    """A Fuse leg bought: counted once, only if the signature is already one of YOUR confirmed FEELESS trades.
    The creator's share of that trade's FEELESS fee is recorded for payout."""
    me = _session_or_401(payload.address, payload.session)
    mine = set(linked_of(me)) | {me}
    trade = next((x for w, rows in _json_load(FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or [] if x.get('tx') == payload.signature), None)
    if not trade:
        raise HTTPException(400, 'That trade is not a confirmed FEELESS trade from your wallet (yet).')
    async with _admin_lock:
        store = _json_load(FUSES_PATH, {'fuses': {}})
        f = store['fuses'].get(fid)
        if not f:
            raise HTTPException(404, 'No such Fuse.')
        if any(b['sig'] == payload.signature for b in store.get('buys', [])):
            return {'ok': True, 'counted': False}
        fee = float(trade.get('feelessFeeUsd') or 0)
        self_deal = primary_of(f.get('creator') or '') == me or me in set(linked_of(primary_of(f.get('creator') or '')))
        bot = (await _shield_of(me))['verdict'] == 'bot'
        store.setdefault('buys', []).append({'fuse': fid, 'sig': payload.signature, 'wallet': me, 'usd': float(trade.get('usd') or trade.get('poolUsd') or 0),
                                             'feeUsd': fee, 'creatorUsd': 0.0 if self_deal or bot else _fuse.creator_cut(fee, f.get('creatorBps', 0)),
                                             'selfDeal': self_deal, 'bot': bot, 'at': time.time()})
        _json_save(FUSES_PATH, store)
    return {'ok': True, 'counted': True}


@app.get('/api/reputation/admin/fuses')
async def admin_fuses(request: Request):
    _require_admin(request)
    store = _json_load(FUSES_PATH, {'fuses': {}})
    views = await asyncio.gather(*[_fuse_view(fid, f, store) for fid, f in store['fuses'].items()])
    pay = await asyncio.gather(*[_fuse_pay_to(store['fuses'][v['id']]) for v in views])
    return {'fuses': [{**v, 'payTo': p, 'card': store['fuses'][v['id']].get('card')} for v, p in zip(views, pay)], 'maxCreatorBps': _fuse.MAX_CREATOR_BPS, 'maxLegs': _fuse.MAX_LEGS}


@app.post('/api/reputation/admin/fuses')
async def admin_fuses_save(request: Request):
    """Create / edit / delete a Fuse, or record a creator payout. Launch prices are captured on create (index = 100)."""
    admin = _require_admin(request)
    body = await request.json()
    async with _admin_lock:
        store = _json_load(FUSES_PATH, {'fuses': {}})
        fid = body.get('id') or uuid.uuid4().hex[:10]
        if body.get('delete'):
            store['fuses'].pop(fid, None)
        elif body.get('paidUsd') is not None:
            store.setdefault('paid', {})[fid] = round(float((store.get('paid') or {}).get(fid, 0)) + max(0.0, float(body['paidUsd'])), 6)
        else:
            legs = _fuse.clean_legs(body.get('legs'))
            name = str(body.get('name') or '').strip()[:40]
            if not name or len(legs) < 2:
                raise HTTPException(400, 'A Fuse needs a name and at least 2 pools.')
            prev = store['fuses'].get(fid) or {}
            pairs = await _fuse_pairs(legs)
            base = {**(prev.get('basePrices') or {}), **{leg['pairAddress']: float(pairs[leg['pairAddress']].get('priceUsd') or 0) for leg in legs
                                                         if pairs.get(leg['pairAddress']) and leg['pairAddress'] not in (prev.get('basePrices') or {})}}
            store['fuses'][fid] = {'name': name, 'emoji': str(body.get('emoji') or '⚛️')[:4], 'tagline': str(body.get('tagline') or '')[:120], 'legs': legs,
                                   'creator': body.get('creator') or prev.get('creator') or admin, 'creatorBps': max(0, min(_fuse.MAX_CREATOR_BPS, int(body.get('creatorBps') or 0))),
                                   'enabled': bool(body.get('enabled', True)), 'basePrices': base, 'createdAt': prev.get('createdAt') or time.time(),
                                   'featured': bool(body.get('featured', prev.get('featured', False))), 'aura': prev.get('aura', ''),
                                   'arena': bool(body.get('arena', prev.get('arena', not prev))),   # a NEW HQ card goes on the Arena by default
                                   **_card_look(body, prev)}
            _arena_mega_cache.update(at=0.0, data=None)
        _json_save(FUSES_PATH, store)
        ad = _admin_load(); _audit(ad, admin, 'fuse', json.dumps({'id': fid, **{k: body.get(k) for k in ('name', 'delete', 'paidUsd') if k in body}})[:160]); _admin_save(ad)
    return {'ok': True, 'id': fid}


# ---- FUSE Vault (backend/fuse_vault.py; on-chain program in programs/fuse_vault) ----------------------------------
import fuse_vault as _vault
VAULTS_PATH = DATA_DIR / 'fuse_vaults.json'   # {'vaults': {id: {name, emoji, pools[≤3], mgmtBps, perfBps, status}}}
VAULT_MAX_MGMT_BPS, VAULT_MAX_PERF_BPS = 300, 3000   # ≤3%/yr management, ≤30% performance


async def _sol_usd_live():
    try:
        p = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': '58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2'}])   # Raydium SOL/USDC
        return float(next(iter(p.values())).get('priceUsd') or 0) or 150.0
    except Exception:
        return 150.0


async def _vault_view(vid, v, deposit_sol=10.0):
    pools = _vault.clean_pools(v.get('pools'))
    pairs = await _fuse_pairs(pools)
    meta = {k: _fuse.leg_meta(p) for k, p in pairs.items()}
    sol_usd = await _sol_usd_live()
    sim = _vault.simulate(pools, meta, sol_usd, deposit_sol, v.get('mgmtBps', 0), v.get('perfBps', 0))
    return {'id': vid, **{k: v.get(k) for k in ('name', 'emoji', 'tagline', 'mgmtBps', 'perfBps', 'status', 'programId', 'createdAt')},
            'pools': [{**p, **meta.get(p['pairAddress'], {}), 'liveWeight': sim['weights'].get(p['pairAddress'])} for p in pools],
            'solUsd': sol_usd, 'sim': sim, 'feeWallet': _fee_cfg().get('vaultFeeWallet') or ''}


@app.get('/api/reputation/vaults')
async def vaults_list(deposit: float = Query(10.0, gt=0, le=100000)):
    d = _json_load(VAULTS_PATH, {'vaults': {}})
    return {'vaults': await asyncio.gather(*[_vault_view(vid, v, deposit) for vid, v in d['vaults'].items() if v.get('status') != 'off'])}


@app.get('/api/reputation/vaults/pools')
async def vault_pool_search(q: str = Query(..., min_length=2, max_length=60)):
    """Pool picker for the vault designer: real pools only, tagged v2 (constant product) or v3 (concentrated)."""
    async with httpx.AsyncClient(timeout=8) as http:
        try:
            pairs = ((await http.get('https://api.dexscreener.com/latest/dex/search', params={'q': q})).json() or {}).get('pairs') or []
        except Exception:
            pairs = []
    # Solana ONLY (DexScreener search returns every chain — Base/ETH rows are dropped here), deepest first, and the real
    # coin flagged (✓ REAL major mint vs ⚠ lookalike ticker) the same way the Fuse Lab search does.
    pairs = sorted((p for p in _fuse.real_pools(pairs) if p.get('chainId') == 'solana'), key=lambda p: -_fuse._f((p.get('liquidity') or {}).get('usd')))[:15]
    rows = [{'chainId': 'solana', 'pairAddress': p.get('pairAddress'), 'kind': _vault.kind_of(p), 'venue': p.get('dexId'), **_fuse.leg_meta(p)} for p in pairs]
    return {'pools': _fuse.mark_real(rows, q)}


@app.get('/api/reputation/admin/vaults')
async def admin_vaults(request: Request, deposit: float = Query(10.0, gt=0, le=100000)):
    _require_admin(request)
    d = _json_load(VAULTS_PATH, {'vaults': {}})
    return {'vaults': await asyncio.gather(*[_vault_view(vid, v, deposit) for vid, v in d['vaults'].items()]), 'maxPools': _vault.MAX_POOLS,
            'maxMgmtBps': VAULT_MAX_MGMT_BPS, 'maxPerfBps': VAULT_MAX_PERF_BPS, 'feeWallet': _fee_cfg().get('vaultFeeWallet') or ''}


@app.post('/api/reputation/admin/vaults')
async def admin_vaults_save(request: Request):
    """Design a vault: up to 3 pools (v2/v3), base weights, per-pool caps (% of pool TVL), v3 range widths, fees.
    Status stays 'design' until the on-chain program is deployed and audited — nothing here moves funds."""
    admin = _require_admin(request)
    body = await request.json()
    async with _admin_lock:
        d = _json_load(VAULTS_PATH, {'vaults': {}})
        vid = body.get('id') or uuid.uuid4().hex[:10]
        if body.get('delete'):
            d['vaults'].pop(vid, None)
        else:
            pools = _vault.clean_pools(body.get('pools'))
            name = str(body.get('name') or '').strip()[:40]
            if not name or not 1 <= len(pools) <= _vault.MAX_POOLS:
                raise HTTPException(400, f'A vault needs a name and 1–{_vault.MAX_POOLS} pools.')
            prev = d['vaults'].get(vid) or {}
            d['vaults'][vid] = {'name': name, 'emoji': str(body.get('emoji') or '🏦')[:4], 'tagline': str(body.get('tagline') or '')[:120], 'pools': pools,
                                'mgmtBps': max(0, min(VAULT_MAX_MGMT_BPS, int(body.get('mgmtBps') or 0))), 'perfBps': max(0, min(VAULT_MAX_PERF_BPS, int(body.get('perfBps') or 0))),
                                'status': prev.get('status', 'design') if body.get('status') not in ('design', 'off') else body['status'],
                                'programId': prev.get('programId'), 'createdAt': prev.get('createdAt') or time.time()}
        _json_save(VAULTS_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'vault', json.dumps({'id': vid, 'name': body.get('name'), 'delete': body.get('delete')})[:160]); _admin_save(ad)
    return {'ok': True, 'id': vid}


# ---- Quest engine: 40 animated badges (FEELESS + Fee Reserve), daily/weekly quests, levels (backend/quests.py) ----
import quests as _quests
QUESTS_PATH = DATA_DIR / 'quests.json'            # admin: {'badges': {id: override}, 'manual': {wallet: {grant, revoke}}}
QUEST_STATE_PATH = DATA_DIR / 'quest_state.json'  # {wallet: {'days': [YYYY-MM-DD], 'first': ts}}
EDITIONS_PATH = DATA_DIR / 'quest_editions.json'  # {badge: [wallets in earn order]} — first EDITION_CAP are numbered
EDITION_CAP = 100
_quest_cache: dict = {}


def _quest_defs():
    return _quests.merge(_quests.DEFAULTS, _json_load(QUESTS_PATH, {}))


def _streak(days):
    have, n, d = set(days), 0, time.time()
    if time.strftime('%Y-%m-%d', time.gmtime(d)) not in have:
        d -= 86400   # today not checked in yet: the streak is still alive from yesterday
    while time.strftime('%Y-%m-%d', time.gmtime(d)) in have:
        n += 1; d -= 86400
    return n


def _fuse_quest_stats(mine):
    """⚛️ Fuse → the ONE season: cards opened, survivors (swapped a weak coin and closed in profit), battles won, weeks
    that beat FeeCat, season medals — counts for badges + timestamps so weekly quests and season XP see them."""
    d = _json_load(FUSE_HQ_PATH, {})
    pos = [x for x in d.get('positions') or [] if x['wallet'] in mine]
    ids = {x['id'] for x in pos}
    surv = [x for x in pos if x.get('closedAt') and any(e.get('kind') == 'buy' for e in x.get('events') or []) and _hq.position_pnl(x, {})['pnlUsd'] > 0]
    wins = [b['at'] for b in d.get('battleLog') or [] if (b.get('winnerKey') or '').startswith('user:') and b['winnerKey'][5:] in ids]
    beats = [w['week'] + _hq.WEEK for w in d.get('catChallenge') or [] for cid in w.get('ids') or [] if cid in ids]
    medals = [s['week'] + _hq.WEEK for s in d.get('seasons') or [] for t_ in s.get('top') or [] if t_['id'] in ids]
    return {'counts': {'fuse_cards': len(pos), 'fuse_survivors': len(surv), 'battle_wins': len(wins), 'feecat_beats': len(beats), 'season_medals': len(medals)},
            'events': {'fuse_card': [_fuse._f(x.get('at')) for x in pos], 'battle_win': wins, 'feecat_beat': beats, 'season_medal': medals,
                       # ⚔ backing feeds the season too: every back + every winning back is XP (daily + weekly quests) → rank
                       'battle_back': [t for w in mine for t in ((d.get('backLog') or {}).get(w) or [])],
                       'back_win': [t for w in mine for t in ((d.get('backWins') or {}).get(w) or [])],
                       'bracket_win': [t for w in mine for t in ((d.get('bracketWins') or {}).get(w) or [])]}}


async def _quest_raw(me, board=None):
    """Everything the engine measures, read from FEELESS's own records (nothing self-reported)."""
    mine = set(linked_of(me)) | {me}
    trades = [{'side': x.get('side'), 'usd': x.get('usd') or x.get('poolUsd') or 0, 'token': x.get('token'), 'ts': x.get('ts')}
              for w, rows in _json_load(FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or []]
    chat = [{'room': m.get('room'), 'chain': m.get('chain'), 'ts': m.get('ts')} for ms in _chat_load()['rooms'].values() for m in ms
            if isinstance(m, dict) and not m.get('system') and (m.get('identity') or m.get('address')) in mine]
    calls = [c for c in (_json_load(CALLS_PATH, {}).get('calls') or {}).values() if c.get('callerAddress') in mine]
    board = board or await caller_board(days=90)
    hits = sum(r.get('hits', 0) for r in board['rows'] if r.get('callerAddress') in mine)
    pts = _pts().get(me) or {}
    st = _json_load(QUEST_STATE_PATH, {}).get(me) or {}
    days = set(st.get('days') or []) | ({pts['claims']['daily']} if (pts.get('claims') or {}).get('daily') else set())
    creator = _load()['creators'].get(_creator_key('solana', me))
    return {'trades': trades, 'chat': chat, 'call_ts': [c.get('at') or 0 for c in calls], 'call_hits': hits,
            'invited': len(_json_load(REF_PATH, {'by': {}})['by'].get(me, [])),
            'followers': sum(1 for lst in (_json_load(FOLLOW_PATH, {}).get('following') or {}).values() if me in lst),
            'launches': score_creator(creator)['tokenCount'] if creator else 0, 'points': int(pts.get('total') or 0),
            'signin_days': sorted(days), 'streak': max(_streak(days), int(pts.get('streak') or 0)),
            'fee_usd': await _fee_usd(me), 'fee_mints': [m for m in (await _ecosystem_mints()).values() if m], 'first_seen': st.get('first'),
            'events': {**(st.get('events') or {}), **(fz := _fuse_quest_stats(mine))['events']}, 'fuse': fz['counts'],
            'alerts_set': sum(len(e.get('watch') or []) for e in _push_load()['subs'].values() if (e.get('prefs') or {}).get('address') in mine)}


QUEST_SEASON_DEFAULT = {'id': 's1', 'name': 'Season 1', 'paused': True, 'start': None}   # paused until FEELESS launches


def _quest_season():
    return {**QUEST_SEASON_DEFAULT, **(_json_load(QUESTS_PATH, {}).get('season') or {})}


async def _quest_summary(address):
    me = primary_of(address)
    hit = _quest_cache.get(me)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    manual = (_json_load(QUESTS_PATH, {}).get('manual') or {}).get(me)
    if _is_staff(me):   # FEELESS HQ: every badge (and so every perk) unlocked
        manual = {**(manual or {}), 'grant': [b['id'] for b in _quest_defs()], 'revoke': []}
    raw = await _quest_raw(me)
    out = {'address': me, **_quests.summary(_quest_defs(), raw, manual)}
    # First time each badge shows as earned is its earn date (season scoring + "new" flags). Written only on change.
    st_all = _json_load(QUEST_STATE_PATH, {}); st = st_all.get(me) or {}
    earned_at = dict(st.get('earned') or {})
    new = [b['id'] for b in out['badges'] if b['earned'] and b['id'] not in earned_at]
    if new:
        # Editions: the first EDITION_CAP wallets to EARN a badge (not granted) are numbered forever: #007 / 100.
        eds = _json_load(EDITIONS_PATH, {})
        for bid in new:
            earned_at[bid] = time.time()
            real = next((b for b in out['badges'] if b['id'] == bid and not b.get('granted')), None)
            lst = eds.setdefault(bid, [])
            if real and me not in lst and len(lst) < EDITION_CAP:
                lst.append(me)
        _json_save(EDITIONS_PATH, eds)
        st_all[me] = {**st, 'earned': earned_at, 'first': st.get('first') or time.time(), 'days': st.get('days') or []}
        _json_save(QUEST_STATE_PATH, st_all)
    season = _quest_season()
    eds = _json_load(EDITIONS_PATH, {})
    out['editions'] = {bid: lst.index(me) + 1 for bid, lst in eds.items() if me in lst}
    out['editionCap'] = EDITION_CAP
    out.update(earnedAt=earned_at, season={**season, 'score': _quests.season_score(out['badges'], raw, earned_at, season)},
               trophies=[it for it in _json_load(COLLECTION_PATH, {}).get(me, []) if it.get('kind') == 'quest'])
    _quest_cache[me] = (time.time(), out)
    return out


_rarity_cache: dict = {}


async def _quest_rarity():
    """Share of active wallets holding each badge, recomputed at most every 10 minutes (one caller-board read)."""
    if _rarity_cache.get('at', 0) > time.time() - 600:
        return _rarity_cache['data']
    wallets = set(_json_load(FEELESS_TRADES_PATH, {})) | set(_pts()) | set(_json_load(QUEST_STATE_PATH, {}))
    board = await caller_board(days=90); defs = _quest_defs(); held = {}
    for w in list(wallets)[:2000]:
        try:
            s = _quests.summary(defs, await _quest_raw(primary_of(w), board), (_json_load(QUESTS_PATH, {}).get('manual') or {}).get(primary_of(w)))
        except Exception:
            continue
        for b in s['badges']:
            if b['earned']:
                held[b['id']] = held.get(b['id'], 0) + 1
    data = {'pct': _quests.rarity(held, len(wallets)), 'holders': held, 'wallets': len(wallets)}
    _rarity_cache.update(at=time.time(), data=data)
    return data


@app.get('/api/reputation/quests/{address}')
async def quest_board(address: str):
    s = await _quest_summary(address)
    r = await _quest_rarity()
    eds = _json_load(EDITIONS_PATH, {})
    left = {b['id']: max(0, EDITION_CAP - len(eds.get(b['id']) or [])) for b in s['badges']}   # edition hunt: numbered spots left
    return {**s, 'rarity': r['pct'], 'holders': r['holders'], 'editionsLeft': left, 'metricsLabels': _quests.METRICS}


class QuestCheckin(BaseModel):
    address: str
    session: str


@app.post('/api/reputation/quests/checkin')
async def quest_checkin(payload: QuestCheckin):
    me = _session_or_401(payload.address, payload.session)
    day = time.strftime('%Y-%m-%d', time.gmtime())
    async with _admin_lock:
        d = _json_load(QUEST_STATE_PATH, {})
        st = d.setdefault(me, {'days': [], 'first': time.time()})
        st['checkinAt'] = ((st.get('checkinAt') or []) + [time.time()])[-60:]   # Bot shield: clockwork / batch engines
        if (await _shield_of(me))['verdict'] == 'bot':   # bots don't earn daily rewards
            _json_save(QUEST_STATE_PATH, d)
            return {'ok': True, 'fresh': False, 'streak': _streak(st['days']), 'days': len(st['days']), 'shield': 'bot'}
        fresh = day not in st['days']
        if fresh:
            st['days'] = (st['days'] + [day])[-400:]
            _json_save(QUEST_STATE_PATH, d)
    _quest_cache.pop(me, None); _badge_cache.pop(me, None)
    return {'ok': True, 'fresh': fresh, 'streak': _streak(st['days']), 'days': len(st['days'])}


class QuestEvent(BaseModel):
    address: str
    session: str
    kind: str
    ref: str = Field(default='', max_length=120)


@app.post('/api/reputation/quests/event')
async def quest_event(payload: QuestEvent):
    """Tool quests. case_open: one per wallet looked at per day (max 30/day). warroom_trade: only a signature that is
    already one of YOUR verified FEELESS trades counts, once."""
    me = _session_or_401(payload.address, payload.session)
    if payload.kind not in ('case_open', 'warroom_trade') or not payload.ref:
        raise HTTPException(400, 'Unknown quest event.')
    if payload.kind == 'warroom_trade':
        mine = set(linked_of(me)) | {me}
        if not any(x.get('tx') == payload.ref for w, rows in _json_load(FEELESS_TRADES_PATH, {}).items() if w in mine for x in rows or []):
            raise HTTPException(400, 'That trade is not a confirmed FEELESS trade from your wallet (yet).')
    now = time.time(); day = time.strftime('%Y-%m-%d', time.gmtime(now))
    async with _admin_lock:
        d = _json_load(QUEST_STATE_PATH, {})
        st = d.setdefault(me, {'days': [], 'first': now})
        ev = st.setdefault('events', {}); refs = st.setdefault('eventRefs', {})
        key = f'{payload.kind}:{payload.ref}' + (f':{day}' if payload.kind == 'case_open' else '')
        today = sum(1 for x in ev.get(payload.kind, []) if x >= now // 86400 * 86400)
        counted = key not in refs and not (payload.kind == 'case_open' and today >= 30)
        if counted:
            ev.setdefault(payload.kind, []).append(now); ev[payload.kind] = ev[payload.kind][-2000:]
            refs[key] = now
            if len(refs) > 4000:
                st['eventRefs'] = dict(sorted(refs.items(), key=lambda kv: kv[1])[-3000:])
            _json_save(QUEST_STATE_PATH, d)
    _quest_cache.pop(me, None)
    return {'ok': True, 'counted': counted}


_quest_board_cache: dict = {}


@app.get('/api/reputation/quests-leaderboard')
async def quest_leaderboard():
    """Season XP leaderboard (10 min cache). Paused season: no ranking, just the plan."""
    season = _quest_season()
    if season.get('paused') or not season.get('start'):
        return {'season': season, 'rows': [], 'paused': True}
    if _quest_board_cache.get('at', 0) > time.time() - 600:
        return _quest_board_cache['data']
    wallets = set(_json_load(FEELESS_TRADES_PATH, {})) | set(_pts()) | set(_json_load(QUEST_STATE_PATH, {}))
    rows = []
    for w in list(wallets)[:2000]:
        try:
            s = await _quest_summary(primary_of(w))
        except Exception:
            continue
        if s['season']['score'] > 0:
            prof = (_profiles_load()['profiles'].get(s['address']) or {})
            rows.append({'address': s['address'], 'name': prof.get('displayName') or prof.get('handle') or s['address'][:4] + '…' + s['address'][-4:],
                         'xp': s['season']['score'], 'level': s['level']['name'], 'badges': s['earned']})
    rows.sort(key=lambda r: -r['xp'])
    data = {'season': season, 'rows': rows[:50], 'paused': False}
    _quest_board_cache.update(at=time.time(), data=data)
    return data


@app.post('/api/reputation/admin/quests/season')
async def admin_quest_season(request: Request):
    """Name the season, set its start, pause/unpause (paused until launch), or award the week's top 3 a trophy."""
    admin = _require_admin(request)
    body = await request.json()
    async with _admin_lock:
        d = _json_load(QUESTS_PATH, {})
        s = {**QUEST_SEASON_DEFAULT, **(d.get('season') or {})}
        for k in ('name', 'paused', 'start'):
            if k in body:
                s[k] = body[k]
        if body.get('paused') is False and not s.get('start'):
            s['start'] = time.time()
        d['season'] = s
        awarded = []
        if body.get('awardWeek'):
            if s.get('paused') or not s.get('start'):
                raise HTTPException(400, 'Season is paused — unpause it (at launch) before awarding weeks.')
            _quest_board_cache.clear()
            top = (await quest_leaderboard())['rows'][:3]
            week = int((time.time() - float(s['start'])) // (7 * 86400)) + 1
            col = _json_load(COLLECTION_PATH, {})
            for rank, row in enumerate(top, 1):
                iid = f"quest:{s['id']}:w{week}:{rank}"
                items = col.setdefault(row['address'], [])
                if not any(it.get('id') == iid for it in items):
                    items.append({'id': iid, 'kind': 'quest', 'season': s['id'], 'week': week, 'rank': rank, 'name': f"{s['name']} · Week {week} #{rank}",
                                  'glyph': ['🥇', '🥈', '🥉'][rank - 1], 'rarity': ['mythic', 'legendary', 'epic'][rank - 1], 'xp': row['xp'], 'at': time.time()})
                    awarded.append(row['address'])
            _json_save(COLLECTION_PATH, col)
        _json_save(QUESTS_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'quest-season', json.dumps({k: s.get(k) for k in ('name', 'paused')} | {'awarded': len(awarded)})[:160]); _admin_save(ad)
    _quest_cache.clear(); _quest_board_cache.clear()
    return {'ok': True, 'season': s, 'awarded': awarded}


@app.get('/api/reputation/admin/quests')
async def admin_quests(request: Request):
    _require_admin(request)
    return {'badges': _quest_defs(), 'defaults': _quests.DEFAULTS, 'overrides': _json_load(QUESTS_PATH, {}), 'metrics': _quests.METRICS,
            'tiers': list(_quests.TIER_XP), 'daily': _quests.DAILY, 'weekly': _quests.WEEKLY, 'stats': await _quest_rarity(), 'season': _quest_season()}


@app.post('/api/reputation/admin/quests')
async def admin_quests_save(request: Request):
    """Edit any badge (name, tier, tasks/targets, on/off) or add one. Invalid task lists are refused."""
    admin = _require_admin(request)
    body = await request.json()
    edits = body.get('badges') or {}
    for bid, o in edits.items():
        if not _re.match(r'^[a-z0-9-]{2,40}$', bid) or (o.get('tasks') is not None and not _quests.is_valid_def({'name': o.get('name') or bid, 'tasks': o['tasks']})):
            raise HTTPException(400, f'Badge {bid}: every task needs a known metric and a positive target.')
        if o.get('tier') and o['tier'] not in _quests.TIER_XP:
            raise HTTPException(400, f'Badge {bid}: unknown tier.')
        if 'aura' in o and o['aura'] not in ('', *badge_cards.AURAS):
            raise HTTPException(400, f'Badge {bid}: unknown aura.')
    async with _admin_lock:
        d = _json_load(QUESTS_PATH, {})
        for bid, o in edits.items():
            if o.get('reset'):
                (d.get('badges') or {}).pop(bid, None)
            else:
                d.setdefault('badges', {})[bid] = {**(d.get('badges') or {}).get(bid, {}), **{k: v for k, v in o.items() if k in ('name', 'tier', 'enabled', 'tasks', 'art', 'set', 'perks', 'aura')}}
        _json_save(QUESTS_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'quests', ','.join(edits)[:160]); _admin_save(ad)
    _quest_cache.clear(); _badge_cache.clear(); _rarity_cache.clear()
    return {'ok': True, 'badges': _quest_defs()}


@app.post('/api/reputation/admin/quests/grant')
async def admin_quests_grant(request: Request):
    admin = _require_admin(request)
    body = await request.json()
    who, bid, action = primary_of(body.get('address', '')), body.get('badge', ''), body.get('action', 'grant')
    if not who or not any(b['id'] == bid for b in _quest_defs()) or action not in ('grant', 'revoke', 'clear'):
        raise HTTPException(400, 'Pick a wallet, a badge and grant / revoke / clear.')
    async with _admin_lock:
        d = _json_load(QUESTS_PATH, {})
        m = d.setdefault('manual', {}).setdefault(who, {'grant': [], 'revoke': []})
        m['grant'] = [x for x in m.get('grant', []) if x != bid]; m['revoke'] = [x for x in m.get('revoke', []) if x != bid]
        if action != 'clear':
            m[action].append(bid)
        _json_save(QUESTS_PATH, d)
        ad = _admin_load(); _audit(ad, admin, f'quest-{action}', f'{bid} {who[:8]}'); _admin_save(ad)
    _quest_cache.pop(who, None); _badge_cache.pop(who, None)
    return {'ok': True, 'manual': m}


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
        badges.append({'id': 'sharp-caller' if sharp else 'caller', 'label': 'Sharp Caller' if sharp else 'Caller', 'icon': '🏹' if sharp else '🎯', 'tone': 'gold' if sharp else 'plain',
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
        badges.append({'id': 'points-og', 'label': 'Points OG', 'icon': '🏅', 'tone': 'gold', 'why': 'Spent 2,000 earned points on it'})
    badges.extend(_admin_load()['badges'].get(address, {}).values())
    try:   # earned quest badges (animated art) join chat + profile badges, rarest first
        rank_q = {'mythic': 5, 'legendary': 4, 'epic': 3, 'rare': 2, 'common': 1}
        qs = [b for b in (await _quest_summary(address))['badges'] if b['earned']]
        for b in sorted(qs, key=lambda b: -rank_q.get(b['tier'], 0)):
            badges.append({'id': b['id'], 'label': b['name'], 'icon': '', 'art': b['art'], 'rarity': b['tier'], 'tone': 'gold' if rank_q.get(b['tier'], 0) >= 4 else 'mint',
                           'why': ' · '.join(t['label'] for t in b['tasks']) + (' (granted by FEELESS HQ)' if b.get('granted') else '')})
    except Exception:
        pass
    if address in _admin_wallets():
        badges.insert(0, {'id': 'feeless-hq', 'label': 'FEELESS HQ', 'icon': '👑', 'tone': 'gold', 'why': 'Created $FEE — runs the FEELESS HQ'})
    # Season cards count as badges too (best rarity first), so chat + profiles show them.
    rank = {'mythic': 5, 'legendary': 4, 'epic': 3, 'rare': 2, 'common': 1}
    seasonal = sorted((it for it in _json_load(COLLECTION_PATH, {}).get(primary_of(address), []) if it.get('kind') in ('season', 'weekly')),
                      key=lambda it: (-rank.get(it.get('rarity'), 0), -(it.get('at') or 0)))
    for it in seasonal[:2]:
        key = f"season:{it['season']}" if it['kind'] == 'season' else f"week:{it['season']}:w{it.get('week')}"
        badges.append({'id': key.replace(':', '-'), 'card': key, 'label': it.get('name') or 'Season card', 'icon': it.get('glyph') or '🏅',
                       'tone': 'gold' if rank.get(it.get('rarity'), 0) >= 3 else 'mint', 'rarity': it.get('rarity'), 'why': it.get('how') or 'Season card'})
    # Card edits (HQ › Badges › Cards) change the name + glyph everywhere, chat included.
    edits = _json_load(CARDS_PATH, {})
    for b in badges:
        e = edits.get(b.get('card') or f"badge:{b['id']}") or {}
        if e.get('title'):
            b['label'] = e['title']
        if e.get('glyph'):
            b['icon'] = e['glyph']
        if e.get('rarity'):
            b['rarity'] = e['rarity']
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


# ---- FEELESS HQ: creator-wallet admin tools ------------------------------
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
        d = _cached_json(ADMIN_PATH)
    except Exception:
        d = {}
    d.setdefault('badges', {}); d.setdefault('airdrops', []); d.setdefault('audit', [])
    return d


def _badge_limits():
    raw = _admin_load().get('badgeLimits') or {}
    return {'profile': max(0, min(12, int(raw.get('profile', 3)))),
            'chat': max(0, min(12, int(raw.get('chat', 3))))}


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


# Lookups that answer 404 by design when there's simply no data yet (a creator never seen before).
EXPECTED_404_PREFIXES = ('/api/reputation/creator/', '/api/reputation/intel/', '/api/reputation/position/')


import guard as _guard
GUARD_PATH = DATA_DIR / 'guard.json'
_guard_state = None


def _guard_s():
    """Counters live in memory; suspects, approved blocks and the decision log persist (guard.json)."""
    global _guard_state
    if _guard_state is None:
        _guard_state = _guard.new_state()
        saved = _json_load(GUARD_PATH, {})
        for k in ('suspects', 'blocks', 'log'):
            if isinstance(saved.get(k), type(_guard_state[k])):
                _guard_state[k] = saved[k]
    return _guard_state


def _guard_save():
    s = _guard_s()
    _json_save(GUARD_PATH, {k: s[k] for k in ('suspects', 'blocks', 'log')})


@app.middleware('http')
async def _record_status(request: Request, call_next):
    gs = _guard_s()
    ip = _guard.client_ip(request.headers, request.client.host if request.client else '', os.environ.get('FEELESS_TRUST_PROXY') == '1')
    n_sus = len(gs['suspects'])
    stop = _guard.check(gs, ip, request.method, request.url.path)
    if stop:
        _status_log.append((time.time(), request.method, request.url.path[:120], stop[0])); del _status_log[:-600]
        if len(gs['suspects']) != n_sus:
            _guard_save()
        return JSONResponse({'detail': stop[1]}, status_code=stop[0])
    resp = await call_next(request)
    _guard.after(gs, ip, request.method, request.url.path, resp.status_code)
    if len(gs['suspects']) != n_sus:
        _guard_save()
    if resp.status_code >= 400:
        _status_log.append((time.time(), request.method, request.url.path[:120], resp.status_code))
        del _status_log[:-600]
    return resp


def _require_admin(request: Request) -> str:
    """Session proof: the admin wallet signs `FEELESS HQ\\naddress:{a}\\nts:{ts}` (valid 1h)."""
    addr = request.headers.get('x-admin-address', '')
    ts = request.headers.get('x-admin-ts', '')
    sig = request.headers.get('x-admin-sig', '')
    if addr not in _admin_wallets():
        raise HTTPException(403, 'This wallet is not a FEELESS HQ wallet.')
    try:
        ts_i = int(ts)
    except ValueError:
        raise HTTPException(401, 'Missing HQ signature.')
    if abs(time.time() - ts_i) > 86400:
        raise HTTPException(401, 'HQ session expired — sign in again.')
    if not _verify_wallet(addr, f'FEELESS HQ\naddress:{addr}\nts:{ts_i}', sig):
        raise HTTPException(401, 'HQ signature does not match.')
    _role_gate(addr, request)
    return addr


# Granted roles are SCOPED (hard-coded): a moderator / marketing wallet only reaches its own HQ sections; 'admin'
# grants reach everything except owner-only money (Circle, referrals, NFTs… via _require_owner). Owners reach everything.
ROLE_SCOPES = {
    'moderator': {'moderate', 'bugs', 'shield', 'chat-guard', 'chat-feed', 'verify', 'coin-verify', 'intel-desk', 'latency', 'perf'},
    'marketing': {'marketing', 'broadcast', 'kols', 'ads', 'ideas', 'traffic', 'numbers'},
}
ROLE_READ = {'security', 'roles', 'whoami', 'is-admin'}      # every role may read these (its own access + health)


def _role_of(addr):
    if addr in _owner_wallets():
        return 'owner'
    return ((_json_load(DATA_DIR / 'roles.json', {'grants': {}})['grants'].get(addr)) or {}).get('role') or 'none'


def _role_gate(addr, request):
    role = _role_of(addr)
    if role not in ROLE_SCOPES:
        return
    path = str(getattr(getattr(request, 'url', None), 'path', '') or '')
    sec = path.split('/admin/', 1)[1].split('/', 1)[0] if '/admin/' in path else ''
    method = getattr(request, 'method', 'GET')
    if sec in ROLE_SCOPES[role] or (sec in ROLE_READ and method == 'GET'):
        return
    raise HTTPException(403, f'Your {role} access does not include this section.')


def _audit(d, admin, action, detail):
    d['audit'].append({'at': time.time(), 'admin': admin, 'action': action, 'detail': detail})
    d['audit'] = d['audit'][-300:]


@app.get('/api/reputation/admin/whoami')
async def admin_whoami(address: str = ''):
    return {'isAdmin': address in _admin_wallets()}   # yes/no only — every HQ action still needs a signed admin session


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


class BadgeLimits(BaseModel):
    profile: int = Field(ge=0, le=12)
    chat: int = Field(ge=0, le=12)


@app.get('/api/reputation/admin/badges/limits')
async def badge_limits_admin_get(request: Request):
    _require_admin(request)
    return _badge_limits()


@app.get('/api/reputation/admin/badges')
async def badge_awards_admin_get(request: Request):
    _require_admin(request)
    d = _admin_load()
    rows = [{'address': address, 'badges': list(items.values())} for address, items in d['badges'].items() if items]
    rows.sort(key=lambda row: -max((b.get('at', 0) for b in row['badges']), default=0))
    seen = {}
    for a, (at, rec) in list(_badge_cache.items()):
        if time.time() - at < 86400:
            for b in (rec or {}).get('badges', []):
                x = seen.setdefault(b['id'], {'id': b['id'], 'label': b.get('label'), 'icon': b.get('icon'), 'tone': b.get('tone'), 'why': b.get('why'), 'holders': 0, 'builtin': True})
                x['holders'] += 1
    custom = {b['id'] for row in rows for b in row['badges']}
    builtin = sorted((v for k, v in seen.items() if k not in custom), key=lambda v: -v['holders'])
    return {'rows': rows[:500], 'limits': _badge_limits(), 'wallets': len(rows), 'awards': sum(len(row['badges']) for row in rows), 'builtin': builtin}


@app.put('/api/reputation/admin/badges/limits')
async def badge_limits_admin_put(request: Request, payload: BadgeLimits):
    admin = _require_admin(request)
    async with _admin_lock:
        d = _admin_load()
        d['badgeLimits'] = payload.dict()
        _audit(d, admin, 'badge-limits', f'profile {payload.profile} · chat {payload.chat}')
        _admin_save(d)
    return _badge_limits()


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
            raise HTTPException(400, 'That transaction was not signed by your HQ wallet.')
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


def _bug_key(text, page):
    """Crash identity: the message + the component that threw (stack frames / hot-update hashes dropped) + the page path."""
    t = _re.sub(r'\s+·\s+at .*$', '', str(text or '').strip())
    t = _re.sub(r'[0-9a-f]{12,}', '#', t)
    return f"{t[:300]}|{str(page or '').split('?')[0]}"


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
        key = _bug_key(payload.text, payload.page)
        same = next((b for b in reversed(d['bugs']) if b.get('status', 'open') == 'open' and _bug_key(b['text'], b.get('page', '')) == key), None)
        if same:   # the same crash on the same page is ONE report with a count, never 33 rows
            same['count'] = int(same.get('count') or 1) + 1; same['lastAt'] = time.time()
            _json_save(BUGS_PATH, d)
            return {'ok': True, 'merged': True}
        d['bugs'].append({'id': uuid.uuid4().hex[:10], 'text': payload.text.strip(), 'page': payload.page, 'kind': kind,
                          'address': (payload.address or '')[:44] or None, 'status': 'open', 'at': time.time(), 'count': 1})
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
        if st == 404 and m == 'GET' and p.startswith(EXPECTED_404_PREFIXES):
            continue  # 'not observed yet' answers, not failures
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



@app.get('/api/reputation/admin/security/guard')
async def admin_guard(request: Request):
    _require_admin(request)
    return _guard.view(_guard_s())


class GuardDecision(BaseModel):
    ip: str = Field(..., max_length=64)
    action: str = Field(..., max_length=10)
    note: str = Field('', max_length=200)


@app.post('/api/reputation/admin/security/guard')
async def admin_guard_decide(payload: GuardDecision, request: Request):
    """Every block is an admin approval (audited). The guard itself only slows floods and flags suspects."""
    admin = _require_admin(request)
    try:
        _guard.decide(_guard_s(), payload.ip.strip(), payload.action, admin, note=payload.note)
    except ValueError as e:
        raise HTTPException(400, str(e))
    _guard_save()
    async with _admin_lock:
        d = _admin_load(); _audit(d, admin, f'guard-{payload.action}', payload.ip.strip()); _admin_save(d)
    return _guard.view(_guard_s())


# ⛓ Contract go-live checklist (HQ › Fuse › Contract): the owner records each real-money gate; READY only when all pass.
GOLIVE_STEPS = ('adapter', 'twap', 'devnet', 'audit', 'multisig')


@app.get('/api/reputation/admin/contract/golive')
async def contract_golive(request: Request):
    _require_admin(request)
    g = _admin_load().get('golive') or {}
    return {'steps': {k: g.get(k) or {} for k in GOLIVE_STEPS}, 'ready': all((g.get(k) or {}).get('done') for k in GOLIVE_STEPS)}


@app.post('/api/reputation/admin/contract/golive')
async def contract_golive_set(request: Request):
    admin = _require_owner(request)   # only the creator wallet can mark a real-money gate passed
    body = await request.json()
    step = str(body.get('step') or '')
    if step not in GOLIVE_STEPS:
        raise HTTPException(400, 'Unknown step.')
    proof = str(body.get('proof') or '')[:200]
    done = bool(body.get('done'))
    if done and step in ('devnet', 'audit', 'multisig') and not proof:
        raise HTTPException(400, 'Add the proof (tx / report link / Circle authority address) before marking this passed.')
    async with _admin_lock:
        d = _admin_load(); d.setdefault('golive', {})[step] = {'done': done, 'proof': proof, 'at': time.time(), 'by': admin}
        _audit(d, admin, 'contract-golive', f'{step} → {"passed" if done else "open"} {proof[:60]}'); _admin_save(d)
    return await contract_golive(request)

BADGE_CATALOG = [
    {'id': 'fee-holder', 'label': '$FEE Holder', 'icon': '🌿', 'tone': 'mint', 'tier': 1, 'how': 'Hold at least $1 of $FEE in your wallet.'},
    {'id': 'feecat-holder', 'label': 'FEECAT Holder', 'icon': '🐱', 'tone': 'mint', 'tier': 1, 'how': 'Hold at least $1 of FEECAT.'},
    {'id': 'rfee-holder', 'label': 'rFEE Holder', 'icon': '💠', 'tone': 'mint', 'tier': 1, 'how': 'Hold at least $1 of rFEE.'},
    {'id': 'rides-with-fee', 'label': 'Rides with Fee', 'icon': '🐾', 'tone': 'mint', 'tier': 2, 'how': 'Hold a coin the Leader cat is currently in (see FeeCats).'},
    {'id': 'caller', 'label': 'Caller', 'icon': '🎯', 'tone': 'plain', 'tier': 2, 'how': 'Drop a CA in chat — it lands on the Call Ledger and is tracked live.'},
    {'id': 'sharp-caller', 'label': 'Sharp Caller', 'icon': '🏹', 'tone': 'gold', 'tier': 3, 'how': '5+ calls in 30 days with at least half reaching 2×.'},
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
                notify(payload.wallet, 'reward', f"✅ {label} confirmed on-chain · {sol:+.4f} SOL", f'https://solscan.io/tx/{payload.sig}', once=f'tx:{payload.sig}')
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
# Profile page backdrops (the whole page, only on that profile). tier: 0 free · 1 $FEE holder · 2 alpha · 3 whale.
PROFILE_THEMES = {'midnight': 0, 'graphite': 0, 'navy': 0, 'plum': 0, 'ember': 0, 'slate': 0, 'grid': 0, 'feeglow': 0,
                  'glitter': 1, 'matrix': 1, 'sunset': 1, 'vapor': 1, 'aurora': 1, 'plasma': 1, 'goldrush': 1, 'neoncat': 1,
                  'alpha': 2, 'hologram': 2, 'diamond': 3, 'whale': 3}
TIER_THEMES = {k: v for k, v in PROFILE_THEMES.items() if v}
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
    if _is_staff(address):
        tier = max(t['tier'] for t in PERK_TIERS)
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
                'zeroFeeMints': [], 'promo': {'label': '', 'discountPct': 0, 'until': 0},
                # LI.FI (EVM swaps + bridges): fees go to the integrator's fee wallet registered at portal.li.fi.
                'lifiIntegrator': '', 'lifiFeeBps': 0,
                # Trading engine. 'swap' = Jupiter Swap API: FEELESS sets the fee (paid into its own SOL / USDC
                # token accounts), caps the priority fee and broadcasts. 'ultra' = Jupiter Ultra (referral fee,
                # 0.5–2.55%). ultraFallback: Ultra is only used when the Swap API fails AND this is switched on.
                'engine': 'swap', 'ultraFallback': False, 'feeAccountSol': '', 'feeAccountUsdc': '', 'priorityMaxLamports': 200000,
                # FUSE Vault: management + performance fees are paid in SOL to this wallet.
                'vaultFeeWallet': ''}
JUP_MIN_BPS, JUP_MAX_BPS = 50, 255   # Jupiter Ultra referral-fee limits
SWAP_MAX_BPS = 2000                  # FEELESS cap on the Swap API fee (20%)
PRIORITY_MAX_LAMPORTS = 5_000_000    # never let a setting spend more than 0.005 SOL on priority
WSOL_MINT, USDC_MINT = WSOL, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
LIFI_MAX_BPS = 300
FEE_SETTLEMENT_MINTS = {WSOL, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'}


def _fee_cfg():
    d = _admin_load()
    cfg = {**FEE_DEFAULTS, **(d.get('fees') or {})}
    cfg['tierDiscountPct'] = {**FEE_DEFAULTS['tierDiscountPct'], **(cfg.get('tierDiscountPct') or {})}
    return cfg


def _engine_cfg(cfg):
    return {'engine': cfg.get('engine') if cfg.get('engine') in ('swap', 'ultra') else 'swap', 'ultraFallback': bool(cfg.get('ultraFallback')),
            'priorityMaxLamports': max(0, min(PRIORITY_MAX_LAMPORTS, int(cfg.get('priorityMaxLamports') or 0)))}


def _swap_fee_accounts(cfg, input_mint, output_mint):
    """FEELESS token accounts that can take this swap's fee (their mint must be one side of the trade),
    pay side first, then receive side. Jupiter is tried with each in order."""
    by_mint = {WSOL_MINT: cfg.get('feeAccountSol'), USDC_MINT: cfg.get('feeAccountUsdc')}
    return [by_mint[m] for m in (input_mint, output_mint) if by_mint.get(m)]


def _swap_fee_account(cfg, input_mint, output_mint):
    return (_swap_fee_accounts(cfg, input_mint, output_mint) or [None])[0]


async def _leg_usd(input_mint, amount):
    """$ size of a swap from its pay side (SOL/USDC instantly; a coin from its live price, ≤3s)."""
    amount = _fuse._f(amount)
    if amount <= 0:
        return 0.0
    if input_mint in (USDC_MINT, 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'):
        return amount
    if input_mint == WSOL_MINT:
        return amount * (await _sol_usd_live() or 0)
    try:
        px = (await asyncio.wait_for(_token_prices([input_mint]), 3)).get(input_mint) or 0
    except Exception:
        px = 0
    return amount * px


async def effective_fee(wallet: str, input_mint: str = '', output_mint: str = '', bundle: int = 0, amount: float = 0, card: int = 0, card_id: str = ''):
    """The fee for one trade plus how each engine collects it.
    bps: Swap API fee (paid to feeAccount). ultraBps / referralAccount: the Ultra fallback's fee.
    bundle ≥ 2 = one leg of a Fuse / runner card bought all at once → bundle pricing (flat $ per coin); HQ (staff)
    pays no FEELESS fee on bundles — only the network / partner fees."""
    cfg = _fee_cfg()
    eng = _engine_cfg(cfg)
    base = int(cfg['platformFeeBps'] or 0)
    fee_account = _swap_fee_account(cfg, input_mint, output_mint)
    none = lambda note: {'bps': 0, 'ultraBps': 0, 'baseBps': base, 'notes': [note] if note else [], 'referralAccount': None, 'feeAccount': None, **eng}
    if not base:
        return none('No FEELESS fee on this trade.')
    mints = await _ecosystem_mints()
    # The ONLY fee-free trades: buying a FEELESS coin. There is no other exemption.
    # FEELESS coins ($FEE, FEECAT, rFEE) are free to BUY with SOL, USDC or USDT. Selling them, buying them with
    # any other token, and every other swap pays the platform fee.
    eco = {m: k for k, m in mints.items() if k in ('fee', 'feecat', 'rfee') and m}
    if output_mint in eco and input_mint in FEE_SETTLEMENT_MINTS:
        return none(f"Buying ${eco[output_mint].upper()} with SOL or USD is fee-free.")
    notes = []
    tier = (await _perk_tier(wallet))[0] if wallet else 0
    disc = min(90.0, float(cfg['tierDiscountPct'].get(str(tier), 0)))
    # Badge perk (e.g. Diamond Hands): read from the cached quest summary only, so a quote never waits on it.
    qhit = _quest_cache.get(primary_of(wallet)) if wallet else None
    if qhit and qhit[1]['perks']['feeDiscountPct'] > disc:
        disc = min(90.0, qhit[1]['perks']['feeDiscountPct'])
        notes.append(f"{qhit[1]['perks']['from'].get('fee', 'Badge')} badge: {disc:.0f}% off")
    promo = cfg.get('promo') or {}
    if promo.get('discountPct') and time.time() < float(promo.get('until') or 0):
        disc = min(90.0, max(disc, float(promo['discountPct'])))
        notes.append(f"{promo.get('label') or 'Promo'}: {promo['discountPct']:.0f}% off")
    bps = min(round(base * (1 - disc / 100)), SWAP_MAX_BPS)
    if disc and not any(' badge: ' in n for n in notes):
        notes.append(f'{disc:.0f}% holder discount (tier {tier})')
    if (bundle >= 2 or card) and wallet and _is_staff(wallet):
        return none('FEELESS card: no FEELESS fee — only network / partner fees.')
    if card and card_id and wallet:   # 💳 a card with prepaid swaps left pays no FEELESS fee on its swaps
        mine_ = set(linked_of(primary_of(wallet))) | {wallet}
        pos_ = next((x for x in _json_load(FUSE_HQ_PATH, {}).get('positions') or [] if x.get('id') == card_id and x.get('wallet') in mine_), None)
        if pos_ and int(pos_.get('prepaidSwaps') or 0) > 0:
            return none(f"Prepaid swap ({pos_['prepaidSwaps']} left) — no FEELESS fee.")
    if card and bundle < 2:   # a card's swap / sell / switch leg: flat $ per coin
        bcfg = _hq.clean_bundle(cfg.get('bundle'))
        flat = _hq.card_swap_bps(await _leg_usd(input_mint, amount), bcfg)
        if flat is not None:
            bps = min(round(flat * (1 - disc / 100)), SWAP_MAX_BPS)
            notes.append(f"Card swap: ${bcfg['swapUsd']:.2f} per coin (max {bcfg['maxPct']:g}% of the leg)")
    if bundle >= 2:
        bcfg = _hq.clean_bundle(cfg.get('bundle'))
        flat = _hq.bundle_bps(await _leg_usd(input_mint, amount), bcfg)
        if flat is not None:
            bps = min(round(flat * (1 - disc / 100)), SWAP_MAX_BPS)
            notes.append(f"Bundle pricing: ${bcfg['perLegUsd']:.2f} per coin (max {bcfg['maxPct']:g}% of the leg)")
    # Ultra can't charge below 0.5%: round a discounted fee up to its minimum instead of waiving it.
    ultra = max(JUP_MIN_BPS, min(bps, JUP_MAX_BPS)) if cfg['referralAccount'] and bps else 0
    out = {'bps': bps, 'ultraBps': ultra, 'baseBps': base, 'notes': notes,
           'referralAccount': cfg['referralAccount'] if ultra else None, 'feeAccount': fee_account if bps else None,
           'feeAccounts': _swap_fee_accounts(cfg, input_mint, output_mint) if bps else [],
           'feeAccountsByMint': {m: a for m, a in ((WSOL_MINT, cfg.get('feeAccountSol')), (USDC_MINT, cfg.get('feeAccountUsdc'))) if a and m in (input_mint, output_mint)} if bps else {},
           **eng}
    if bps and not fee_account and eng['engine'] == 'swap':
        # The fee is collected in SOL or USDC. A coin-to-coin trade has neither side, so it can't pay: refuse it
        # rather than let it through free.
        out['blocked'] = 'Every FEELESS trade pays the platform fee in SOL or USDC. Put SOL or USDC on one side (coin → SOL → coin).'
    return out


@app.get('/api/reputation/fees/quote')
async def fee_quote(wallet: str = '', inputMint: str = '', outputMint: str = ''):
    out = await effective_fee(wallet, inputMint, outputMint)
    return {k: v for k, v in out.items() if k not in ('referralAccount', 'feeAccount', 'feeAccounts')} | {'active': bool(out['bps'])}


@app.get('/api/reputation/internal/fees')
async def internal_fees(request: Request, wallet: str = '', inputMint: str = '', outputMint: str = '', bundle: int = Query(0, ge=0, le=12), amount: float = Query(0, ge=0), card: int = Query(0, ge=0, le=1), cardId: str = Query('', max_length=16)):
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), _internal_key()):
        raise HTTPException(403, 'Internal only.')
    return await effective_fee(wallet, inputMint, outputMint, bundle, amount, card, cardId)


@app.get('/api/reputation/fees/pricing')
async def fee_pricing(coins: int = Query(3, ge=1, le=12), usd: float = Query(20, ge=0, le=1e6), rounds: int = Query(5, ge=1, le=500), wallet: str = Query('', max_length=64)):
    """Public pricing: the % fee on a normal swap, the bundle price for cards bought all at once, card swaps, round packs —
    plus `plan` = what a card of `coins` coins / $`usd` costs over `rounds` rounds (the Lab's cost receipt)."""
    cfg = _fee_cfg()
    return {'swapBps': int(cfg['platformFeeBps'] or 0), 'bundle': _hq.clean_bundle(cfg.get('bundle')), 'rounds': {**_rounds_cfg(), 'payTo': await _rounds_pay_to()},
            'plan': _hq.fee_plan(cfg.get('bundle'), _rounds_cfg(), coins, usd, rounds),
            'prepay': _hq.clean_prepay(cfg.get('prepay')), 'staff': bool(wallet and _is_staff(wallet)),
            'choice': {'rounds': list(_hq.PLAN_ROUNDS), 'swaps': list(_hq.PLAN_SWAPS), 'free': _hq.ROUNDS_DEFAULT, 'step': _hq.ROUNDS_STEP},
            'cardLegs': {'pools': _hq.CARD_POOLS, 'runners': _hq.CARD_RUNNERS}, 'freeBuys': ['$FEE', 'FEECAT', 'rFEE']}


class FeeCfg(BaseModel):
    platformFeeBps: int = Field(ge=0, le=SWAP_MAX_BPS)
    engine: str = 'swap'
    ultraFallback: bool = False
    feeAccountSol: str = ''
    feeAccountUsdc: str = ''
    priorityMaxLamports: int = Field(200000, ge=0, le=PRIORITY_MAX_LAMPORTS)
    referralAccount: str = ''
    tierDiscountPct: dict = {}
    zeroFeeMints: list = []
    promo: dict = {}
    lifiIntegrator: str = ''
    lifiFeeBps: int = Field(0, ge=0, le=LIFI_MAX_BPS)
    vaultFeeWallet: str = ''

    # Settings saved by older builds can come back as null or out of range: clean them instead of
    # rejecting the whole save.
    @field_validator('engine', mode='before')
    @classmethod
    def _engine(cls, v):
        return v if v in ('swap', 'ultra') else 'swap'

    @field_validator('feeAccountSol', 'feeAccountUsdc', 'referralAccount', 'lifiIntegrator', mode='before')
    @classmethod
    def _text(cls, v):
        return '' if v is None else str(v).strip()

    @field_validator('vaultFeeWallet', mode='before')
    @classmethod
    def _vault_wallet(cls, v):
        v = '' if v is None else str(v).strip()
        return v if not v or _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', v) else ''

    @field_validator('tierDiscountPct', 'promo', mode='before')
    @classmethod
    def _obj(cls, v):
        return v if isinstance(v, dict) else {}

    @field_validator('zeroFeeMints', mode='before')
    @classmethod
    def _list(cls, v):
        return v if isinstance(v, list) else []

    @field_validator('platformFeeBps', 'priorityMaxLamports', 'lifiFeeBps', mode='before')
    @classmethod
    def _num(cls, v, info):
        top = {'platformFeeBps': SWAP_MAX_BPS, 'priorityMaxLamports': PRIORITY_MAX_LAMPORTS, 'lifiFeeBps': LIFI_MAX_BPS}[info.field_name]
        if v in (None, '') and info.field_name == 'priorityMaxLamports':
            return 200000
        try:
            return max(0, min(top, int(float(v or 0))))
        except (TypeError, ValueError):
            return 0

    @field_validator('ultraFallback', mode='before')
    @classmethod
    def _bool(cls, v):
        return bool(v)


@app.get('/api/reputation/admin/fuses/fees')
async def admin_fuse_fees(request: Request):
    """HQ › Fees: live $ from people fusing (Fuse card legs matched to the fee ledger by signature)."""
    _require_admin(request)
    rows = [r for v in _json_load(FEE_LEDGER_PATH, {}).values() for r in (v or [])]
    return _hq.fuse_fees(_json_load(FUSE_HQ_PATH, {}).get('positions') or [], rows, time.time())


@app.post('/api/reputation/admin/fees/prepay')
async def admin_fees_prepay(request: Request, body: dict):
    """HQ › Fees › 💳 Prepaid swaps: $ per swap × swaps per round × rounds, paid up front with a card's first buy (owner only)."""
    admin = _require_owner(request)
    async with _admin_lock:
        d = _admin_load(); pp = _hq.clean_prepay(body)
        d.setdefault('fees', {})['prepay'] = {k: pp[k] for k in ('on', 'perSwapUsd', 'swapsPerRound', 'rounds')}
        _audit(d, admin, 'fees', f"prepaid swaps {'on' if pp['on'] else 'off'} · ${pp['perSwapUsd']:.2f} × {pp['swapsPerRound']}/round × {pp['rounds']} = ${pp['usd']:.2f}")
        _admin_save(d)
    return {'prepay': pp}


@app.get('/api/reputation/admin/fuses/fee-list')
async def admin_fuse_fee_list(request: Request):
    """HQ › Fuse › 💲 Fees: every card fee (buy · swap · sell · round packs) with totals — each row links its transaction."""
    _require_admin(request)
    rows = [r for v in _json_load(FEE_LEDGER_PATH, {}).values() for r in (v or [])]
    cfg = _fee_cfg()
    return {**_hq.fee_list(_json_load(FUSE_HQ_PATH, {}).get('positions') or [], rows), 'bundle': _hq.clean_bundle(cfg.get('bundle')), 'rounds': _rounds_cfg(), 'prepay': _hq.clean_prepay(cfg.get('prepay')),
            'swapBps': int(cfg['platformFeeBps'] or 0), 'example': _hq.fee_plan(cfg.get('bundle'), _rounds_cfg(), 3, 20, 10)}


@app.post('/api/reputation/admin/fees/bundle')
async def admin_fees_bundle(request: Request, body: dict):
    """Core › Fees › Bundle pricing: flat $ per coin for cards bought all at once (Fuse / runners)."""
    admin = _require_admin(request)
    async with _admin_lock:
        d = _admin_load()
        b = _hq.clean_bundle(body)
        d.setdefault('fees', {})['bundle'] = b
        _audit(d, admin, 'fees', f"bundle pricing {'on' if b['on'] else 'off'} · ${b['perLegUsd']:.2f}/coin · max {b['maxPct']:g}% · legs ≤ ${b['maxLegUsd']:g}")
        _admin_save(d)
    return {'bundle': b}


def _rounds_cfg():
    return _hq.clean_rounds_cfg(_fee_cfg().get('rounds'))


_rounds_pay_cache: dict = {'at': 0.0, 'to': None}


async def _rounds_pay_to():
    """🔁 Where round packs are paid: the wallet that owns the SOL fee account (on-chain, cached 10 min)."""
    if time.time() - _rounds_pay_cache['at'] < 600:
        return _rounds_pay_cache['to']
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            to = await _fee_wallet_owner(http, _fee_cfg())
    except Exception:
        to = None
    _rounds_pay_cache.update(at=time.time(), to=to)
    return to


@app.post('/api/reputation/admin/fees/rounds')
async def admin_fees_rounds(request: Request, body: dict):
    """Core › Fees › 🔁 Card rounds: $ per +5 rounds, and whether a card's compound may pay for them (owner only)."""
    admin = _require_owner(request)
    async with _admin_lock:
        d = _admin_load()
        r = _hq.clean_rounds_cfg(body)
        d.setdefault('fees', {})['rounds'] = {'per5Usd': r['per5Usd'], 'compoundPay': r['compoundPay']}
        _audit(d, admin, 'fees', f"card rounds · ${r['per5Usd']:.2f} per {r['step']} · compound pays {'on' if r['compoundPay'] else 'off'}")
        _admin_save(d)
    return {'rounds': r}


class RoundsIn(BaseModel):
    address: str
    session: str
    id: str = Field(..., max_length=16)
    mode: str = Field(..., max_length=10)        # pay | compound | settle
    signature: str = Field(default='', max_length=100)


@app.post('/api/reputation/fuses/rounds')
async def fuse_rounds(p: RoundsIn):
    """🔁 +5 rounds on YOUR card: 'pay' = a confirmed SOL transfer YOU signed to the fee wallet (checked on-chain, never reused);
    'compound' = rounds now, the card owes the price until its next profit take; 'settle' = pay what the card owes."""
    me = _session_or_401(p.address, p.session)
    mine = set(linked_of(me)) | {me}
    cfg = _rounds_cfg(); paid_usd = 0.0
    if p.mode in ('pay', 'settle') and (cfg['per5Usd'] > 0 or p.mode == 'settle'):
        if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', p.signature or ''):
            raise HTTPException(400, 'Send the payment first — no signature yet.')
        if p.signature in (_json_load(FUSE_HQ_PATH, {}).get('roundSigs') or []):
            raise HTTPException(409, 'That payment was already used.')
        to = await _rounds_pay_to()
        if not to:
            raise HTTPException(503, 'Fee wallet not set — rounds cannot be bought right now.')
        tx = None
        async with httpx.AsyncClient(timeout=20) as http:
            for _ in range(5):
                tx = await _rpc(http, 'getTransaction', [p.signature, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
                if tx:
                    break
                await asyncio.sleep(2)
        lam = max((_hq.paid_lamports(tx, w, to) for w in mine), default=0)
        paid_usd = lam / 1e9 * (await _sol_usd_live() or 0)
        if paid_usd <= 0:
            raise HTTPException(400, 'No confirmed SOL payment from your wallet to the fee wallet in that transaction.')
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        pos = next((x for x in d.get('positions') or [] if x['id'] == p.id and x['wallet'] in mine and not x.get('closedAt')), None)
        if not pos:
            raise HTTPException(404, 'Open card not found.')
        try:
            if p.mode == 'settle':
                _hq.settle_owed(pos, paid_usd)
            else:
                _hq.extend_rounds(pos, p.mode, cfg, paid_usd, time.time(), p.signature)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if p.signature:
            d['roundSigs'] = (d.get('roundSigs') or [])[-500:] + [p.signature]
        _json_save(FUSE_HQ_PATH, d)
    return {'ok': True, 'roundsLeft': _hq.rounds_left(pos), 'roundsOwedUsd': pos.get('roundsOwedUsd') or 0}


@app.get('/api/reputation/admin/fees')
async def admin_fees_get(request: Request):
    _require_admin(request)
    return {'fees': {**_fee_cfg(), 'bundle': _hq.clean_bundle(_fee_cfg().get('bundle')), 'rounds': _rounds_cfg()}, 'limits': {'minBps': 0, 'maxBps': SWAP_MAX_BPS, 'ultraMinBps': JUP_MIN_BPS, 'ultraMaxBps': JUP_MAX_BPS, 'priorityMaxLamports': PRIORITY_MAX_LAMPORTS}}


@app.get('/api/reputation/admin/fees/balances')
async def admin_fee_balances(request: Request):
    _require_admin(request)
    referral = str(_fee_cfg().get('referralAccount') or '').strip()
    if not referral:
        return {'referralAccount': '', 'accounts': [], 'totalAccounts': 0}
    accounts = []
    async with httpx.AsyncClient(timeout=20) as http:
        for program in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
            result = await _rpc(http, 'getTokenAccountsByOwner', [referral, {'programId': program}, {'encoding': 'jsonParsed'}])
            for row in (result or {}).get('value', []):
                info = (((row.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}
                amount = info.get('tokenAmount') or {}
                if int(amount.get('amount') or 0) <= 0:
                    continue
                accounts.append({'tokenAccount': row.get('pubkey'), 'mint': info.get('mint'), 'amount': amount.get('uiAmountString') or '0', 'decimals': amount.get('decimals', 0), 'program': 'Token-2022' if program.startswith('Tokenz') else 'SPL Token'})
    return {'referralAccount': referral, 'accounts': accounts, 'totalAccounts': len(accounts),
            'note': 'Unclaimed on-chain referral-token balances. Claiming requires the referral authority wallet signature.'}


JUP_ULTRA_REFERRAL_PROJECT = 'DkiqsTrw1u1bYFumumC7sCG2S8K25qc2vemJFHyW2wJc'
JUP_REFERRAL_PROGRAM = 'REFER4ZgmyYx9c6He5XfaTMiGfdLwRnkV4RPp9t9iF3'


@app.get('/api/reputation/admin/fees/health')
async def admin_fee_health(request: Request):
    """Will Jupiter actually pay the FEELESS fee? Checks the referral account on-chain: it must belong to the
    Jupiter Ultra referral project (the one /swap/v2 pays into) and have SOL + USDC fee token accounts."""
    _require_admin(request)
    if _engine_cfg(_fee_cfg())['engine'] == 'swap':
        return await _swap_fee_health()
    import base64
    from solders.pubkey import Pubkey
    referral = str(_fee_cfg().get('referralAccount') or '').strip()
    if not referral:
        return {'ok': False, 'problem': 'No referral account configured.', 'fix': 'Create one under the Jupiter Ultra project at referral.jup.ag and paste it here.'}
    async with httpx.AsyncClient(timeout=20) as http:
        info = await _rpc(http, 'getAccountInfo', [referral, {'encoding': 'base64'}])
        value = (info or {}).get('value')
        if not value or value.get('owner') != JUP_REFERRAL_PROGRAM:
            return {'ok': False, 'problem': 'This address is not a Jupiter referral account.', 'fix': 'Create a referral account at referral.jup.ag (Jupiter Ultra project).'}
        raw = base64.b64decode(value['data'][0])
        project = str(Pubkey.from_bytes(raw[40:72]))
        partner = str(Pubkey.from_bytes(raw[8:40]))
        # Fee vaults = token accounts owned by the referral account (Jupiter Ultra creates regular token
        # accounts for it; the legacy referral_ata PDA layout is not guaranteed), so look them up by owner.
        held = set()
        for program in ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'):
            res = await _rpc(http, 'getTokenAccountsByOwner', [referral, {'programId': program}, {'encoding': 'jsonParsed'}])
            for row in (res or {}).get('value', []):
                held.add((((row.get('account') or {}).get('data') or {}).get('parsed') or {}).get('info', {}).get('mint'))
        vaults = {'SOL': 'So11111111111111111111111111111111111111112' in held, 'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v' in held}
    if project != JUP_ULTRA_REFERRAL_PROJECT:
        return {'ok': False, 'project': project, 'partner': partner, 'vaults': vaults,
                'problem': 'Referral account was created under an older Jupiter referral project, so Jupiter rejects the fee and every swap runs fee-free.',
                'fix': f'At referral.jup.ag, connect the partner wallet {partner[:4]}…{partner[-4:]}, choose the Jupiter Ultra project, create a referral account, create SOL and USDC token accounts, then paste the new referral account here.'}
    missing = [k for k, ok in vaults.items() if not ok]
    if missing:
        return {'ok': False, 'project': project, 'partner': partner, 'vaults': vaults,
                'problem': f"Missing fee token account for {', '.join(missing)}.", 'fix': 'Create the missing token accounts for this referral account at referral.jup.ag.'}
    return {'ok': True, 'project': project, 'partner': partner, 'vaults': vaults, 'note': 'Jupiter will pay the FEELESS fee into this referral account (SOL/USDC vaults ready).'}


TOKEN_PROGRAMS = {'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'}


async def _swap_fee_health():
    """Swap API engine: each fee account must be a live token account for its coin (wSOL / USDC)."""
    cfg = _fee_cfg()
    wanted = [(label, acct, mint) for label, acct, mint in (('SOL', cfg.get('feeAccountSol'), WSOL_MINT), ('USDC', cfg.get('feeAccountUsdc'), USDC_MINT)) if acct]
    if not wanted:
        return {'ok': False, 'problem': 'No fee account set, so the Swap engine collects nothing.',
                'fix': 'Create a wSOL token account owned by your treasury wallet (e.g. spl-token create-account So11111111111111111111111111111111111111112) and paste it.'}
    async with httpx.AsyncClient(timeout=20) as http:
        info = await _rpc(http, 'getMultipleAccounts', [[a for _, a, _ in wanted], {'encoding': 'jsonParsed'}])
    for (label, acct, mint), value in zip(wanted, (info or {}).get('value') or [None] * len(wanted)):
        parsed = (((value or {}).get('data') or {}).get('parsed') or {}) if isinstance((value or {}).get('data'), dict) else {}
        if not value or value.get('owner') not in TOKEN_PROGRAMS or parsed.get('type') != 'account':
            return {'ok': False, 'problem': f'{label} fee account {acct[:6]}… is not a token account on-chain.', 'fix': f'Create a {label} token account for your treasury and paste that address.'}
        if (parsed.get('info') or {}).get('mint') != mint:
            return {'ok': False, 'problem': f'{label} fee account holds a different coin.', 'fix': f'Use a token account whose mint is {mint}.'}
    fallback = 'on' if cfg.get('ultraFallback') else 'off'
    return {'ok': True, 'note': f"Swap engine ready: fees land in your {' + '.join(l for l, _, _ in wanted)} fee account(s). Ultra fallback {fallback}."}


@app.get('/api/reputation/admin/fees/earnings')
async def admin_fee_earnings(request: Request):
    """Live money: what sits in the fee accounts on-chain right now, plus fees from confirmed trades
    (last hour / 24h / 7d, top coins)."""
    _require_admin(request)
    cfg = _fee_cfg()
    accounts = [(label, acct) for label, acct in (('SOL', cfg.get('feeAccountSol')), ('USDC', cfg.get('feeAccountUsdc'))) if acct]
    async with httpx.AsyncClient(timeout=15) as http:
        async def balances():
            if not accounts:
                return []
            info = await _rpc(http, 'getMultipleAccounts', [[a for _, a in accounts], {'encoding': 'jsonParsed'}])
            rows = []
            for (label, acct), value in zip(accounts, (info or {}).get('value') or []):
                amt = ((((value or {}).get('data') or {}).get('parsed') or {}).get('info') or {}).get('tokenAmount') or {} if isinstance((value or {}).get('data'), dict) else {}
                rows.append({'label': label, 'account': acct, 'amount': float(amt.get('uiAmountString') or 0)})
            return rows

        async def trades():
            try:
                r = await http.get('http://127.0.0.1:5001/api/trading/internal/earnings', headers={'x-feeless-internal': _internal_key()})
                return r.json() if r.status_code == 200 else None
            except Exception:
                return None
        bal, stats = await asyncio.gather(balances(), trades())
    for c in (stats or {}).get('coins', []):
        card = _fee_coin_names.get(c['mint'])
        if card is None:
            async with httpx.AsyncClient(timeout=6) as http:
                card = _fee_coin_names[c['mint']] = (await _coin_card(http, c['mint']))['symbol']
        c['symbol'] = card
    return {'balances': bal, 'trades': stats, 'at': time.time()}


_fee_coin_names: dict = {}


# ---- Rug shield: one verdict for the swap review / quick trade, from on-chain forensics --------------
@app.get('/api/reputation/rugshield/{mint}')  # its own path: /shield/{mint} is the launch-promise Shield
async def rug_shield(mint: str):
    """ok / caution / danger with the reasons. danger = the trader must tick 'I understand' before signing."""
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', mint):
        raise HTTPException(400, 'Bad mint.')
    if mint in FEE_SETTLEMENT_MINTS:
        return {'mint': mint, 'level': 'ok', 'reasons': []}
    try:
        if mint in set((await _ecosystem_mints()).values()):
            return {'mint': mint, 'level': 'ok', 'reasons': [], 'official': True, 'note': 'Official FEELESS coin.'}
    except Exception:
        pass
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            intel, auth = await asyncio.gather(token_intel('solana', mint), _mint_authorities(http, mint))
    except HTTPException:
        return {'mint': mint, 'level': 'unknown', 'reasons': ['On-chain check unavailable right now.']}
    creator = intel.get('creator')
    if creator in _protected_wallets():
        intel = {**intel, 'creator': None}   # FEELESS wallets are never the risk
    return {'mint': mint, **shield_verdict(intel, _block_load()['wallets'], auth or {}, _quick_rep(creator) if creator and creator not in _protected_wallets() else None)}


def shield_verdict(intel, blocklist, auth=None, creator_rep=None):
    reasons, danger = list(intel.get('flags') or []), False
    auth = auth or {}
    if auth.get('freezeAuthority'):
        reasons.insert(0, 'Freeze authority is live: the creator can freeze your tokens so you cannot sell.'); danger = True
    if auth.get('mintAuthority'):
        reasons.append('Mint authority is live: the creator can print more supply.')
    creator = intel.get('creator')
    rec = blocklist.get(creator) if creator else None
    if creator and _is_blocked(rec) and rec.get('reported'):
        reasons.insert(0, 'Creator wallet was reported for a rug and is on the FEELESS blocklist.'); danger = True
    elif creator and _is_blocked(rec):
        # Blocklisted for sniping/bundling OTHER launches, not for rugging: a warning, not a hard stop.
        reasons.insert(0, f"Creator wallet snipes/bundles other launches ({len(rec.get('mints') or {})} on record) — no rug reported on this coin.")
    elif creator_rep and creator_rep.get('level') in ('suspect', 'high') and creator_rep.get('top'):
        # Same verdict and cited evidence as the creator's case file.
        reasons.insert(0, f"Creator case file: {creator_rep['label']} ({creator_rep['score']}/100): {creator_rep['top']['claim']}")
        danger = danger or creator_rep['level'] == 'high'
    if (intel.get('devHoldingPct') or 0) >= 20 or (intel.get('insidersHoldingPct') or 0) >= 25 or intel.get('flaggedFunders'):
        danger = True
    return {'level': 'danger' if danger else 'caution' if reasons else 'ok', 'reasons': reasons[:5],
            'devPct': intel.get('devHoldingPct'), 'insidersPct': intel.get('insidersHoldingPct'), 'top10Pct': intel.get('top10Pct')}


# ---- Investigation engine: case files for wallets and coins (scoring lives in investigate.py) -------------
_case_cache: dict = {}
_funding_memo: dict = {}


async def _funder_of(wallet):
    """First-transaction funder, memoised (the funding-graph store first, then one RPC trace)."""
    known = _funders_load()['offenderFunder'].get(wallet)
    if known:
        return known
    if wallet not in _funding_memo:
        _funding_memo[wallet] = await resolve_funding_source('solana', wallet)
    return _funding_memo[wallet]


async def _mint_authorities(http, mint):
    info = await _rpc(http, 'getAccountInfo', [mint, {'encoding': 'jsonParsed'}])
    parsed = ((((info or {}).get('value') or {}).get('data') or {}).get('parsed') or {}) if isinstance(((info or {}).get('value') or {}).get('data'), dict) else {}
    if parsed.get('type') != 'mint':
        return None
    i = parsed.get('info') or {}
    return {'mintAuthority': i.get('mintAuthority'), 'freezeAuthority': i.get('freezeAuthority'), 'decimals': i.get('decimals')}


async def _wallet_case(address):
    a = primary_of(address)
    fund = _funders_load()
    squads = fund['funders'].get(a)
    funded_by = await _funder_of(a)
    store = _load()
    entry = store['creators'].get(_creator_key('solana', a))
    creator = score_creator(entry) if entry else None
    linked = []
    fsrc = store['funding'].get(_creator_key('solana', a)) or funded_by
    if fsrc:
        for other in store['creators'].values():
            if other['address'] != a and store['funding'].get(_creator_key(other['chain'], other['address'])) == fsrc:
                sc = score_creator(other)
                linked.append({'address': other['address'], 'badge': sc.get('badge'), 'ruggedCount': sc.get('ruggedCount')})
    protected = a in _protected_wallets()

    async def safe(coro):
        try:
            return await coro
        except Exception:
            return None
    caller, vitals = await asyncio.gather(safe(_kol_stats(a, 'solana')), safe(wallet_stats(a)))
    if protected:
        caller = None  # the official wallet moves treasury/launch funds; trader stats would mislead
    ctx = {'blocked': None if protected else _block_load()['wallets'].get(a), 'funderOfSquads': squads, 'fundedBy': funded_by,
           'fundedByFlagged': bool(funded_by and _is_flagged_funder(fund['funders'].get(funded_by))),
           'creator': creator, 'caller': caller, 'linkedCreators': linked}
    evidence = [] if protected else investigate.wallet_evidence(ctx)
    if not protected:
        sh = await _shield_of(a)
        evidence += [{'kind': f"bot-{h['engine']}", 'weight': round(h['score'] / 2), 'claim': f"Bot shield · {h['evidence'][0]['claim']}", 'source': h['evidence'][0]['source']}
                     for h in sh['hits'] if h['score'] >= _shield.WATCH]
    prof = _profiles_load()['profiles'].get(a) or {}
    return {'kind': 'wallet', 'address': a, 'identity': {'name': prof.get('displayName'), 'handle': prof.get('handle')},
            **investigate.verdict(evidence, protected), 'evidence': evidence,
            'trail': {'fundedBy': funded_by, 'fundedWallets': (squads or {}).get('funded', [])[:20], 'squadLaunches': len((squads or {}).get('mints', {}))},
            'launches': {k: (creator or {}).get(k) for k in ('tokenCount', 'ruggedCount', 'dumpedCount', 'deadCount', 'bigWinners', 'sustainedCount', 'badge')} if creator else None,
            'linked': linked[:12],
            'vitals': {k: (vitals or {}).get(k) for k in ('sol', 'tokensHeld', 'txCount', 'txCountCapped', 'firstSeen')},
            'caller': {k: (caller or {}).get(k) for k in ('tradesSeen', 'tokens', 'closed', 'quickFlipPct', 'dumpPct', 'winPct', 'netUsd', 'medianHoldMin', 'danger')} if caller else None,
            'protected': protected}


async def _coin_case(mint, auth):
    intel = await token_intel('solana', mint)
    holders = [{'owner': r['owner'], 'pct': r.get('pct')} for r in intel.get('topHolders') or [] if r.get('kind') == 'wallet' and r.get('owner')]
    sem = asyncio.Semaphore(6)

    async def trace(w):
        async with sem:
            try:
                return w, await _funder_of(w)
            except Exception:
                return w, None
    funder_of = dict(await asyncio.gather(*(trace(h['owner']) for h in holders[:12])))
    cl = investigate.clusters(holders, {w: f for w, f in funder_of.items() if f})
    creator = intel.get('creator')
    blocked = bool(creator and _is_blocked(_block_load()['wallets'].get(creator)))
    risk = investigate.coin_risk(intel, auth, creator_blocked=blocked, linked_pct=cl['linkedPct'])
    return {'kind': 'coin', 'address': mint, **risk, 'authorities': auth, 'clusters': cl,
            'holders': {k: intel.get(k) for k in ('top10Pct', 'devHoldingPct', 'insidersHoldingPct', 'snipersHoldingPct', 'poolPct')},
            'launch': {'bundled': len(intel.get('bundledWallets') or []), 'snipers': len(intel.get('sniperWallets') or []), 'creator': creator},
            'creatorCase': (await _wallet_case(creator)) if creator else None}


# ---- BOT SHIELD (backend/bot_shield.py): the defender. Engines over FEELESS records; ties into rep, rewards, Fuse --------
import bot_shield as _shield
SHIELD_PATH = DATA_DIR / 'bot_shield.json'   # {'manual': {wallet: 'cleared' | 'bot'}, 'at': {...}}
_shield_cache: dict = {}


def _shield_features(me, ck_all=None, trades_all=None, chat_all=None):
    mine = set(linked_of(me)) | {me}
    trades_all = trades_all if trades_all is not None else _json_load(FEELESS_TRADES_PATH, {})
    trades = [{'side': x.get('side'), 'usd': x.get('usd') or x.get('poolUsd') or 0, 'token': x.get('token'), 'ts': x.get('ts')}
              for w, rows in trades_all.items() if w in mine for x in rows or []]
    chat_all = chat_all if chat_all is not None else [m for ms in _chat_load()['rooms'].values() for m in ms if isinstance(m, dict) and not m.get('system')]
    chat = [{'ts': _ts_num(m.get('ts')), 'text': m.get('text')} for m in chat_all if (m.get('identity') or m.get('address')) in mine]
    qs = _json_load(QUEST_STATE_PATH, {})
    st = qs.get(me) or {}
    ck_all = ck_all if ck_all is not None else {w: v.get('checkinAt') or [] for w, v in qs.items()}
    inv = _json_load(REF_PATH, {'by': {}})['by'].get(me, [])
    active = set(trades_all) | {(m.get('identity') or m.get('address')) for m in chat_all}
    fz = _json_load(FUSES_PATH, {'fuses': {}})
    own = {fid for fid, f in fz['fuses'].items() if primary_of(f.get('creator') or '') in mine}
    return {'signin_days': st.get('days') or [], 'checkin_at': st.get('checkinAt') or [], 'trades': trades, 'chat': chat,
            'batch_days': _shield.batch_days(ck_all, me), 'invitees': [{'active': w in active} for w in inv],
            'own_fuse_buys': sum(1 for b in fz.get('buys') or [] if b['fuse'] in own and b.get('wallet') in mine)}


def _ts_num(v):
    if isinstance(v, (int, float)):
        return float(v)
    try:
        from datetime import datetime as _dt
        return _dt.fromisoformat(str(v).replace('Z', '+00:00')).timestamp()
    except Exception:
        return 0.0


async def _shield_of(address):
    """One wallet's Bot shield verdict (cached 5 min). FEELESS wallets are never flagged; HQ decisions win."""
    a = primary_of(address)
    hit = _shield_cache.get(a)
    if hit and time.time() - hit[0] < 300:
        return hit[1]
    try:
        r = _shield.scan(_shield_features(a), protected=a in _protected_wallets(), manual=(_json_load(SHIELD_PATH, {}).get('manual') or {}).get(a))
    except Exception:
        r = {'verdict': 'clean', 'score': 0, 'hits': [], 'why': 'scan unavailable'}
    _shield_cache[a] = (time.time(), r)
    return r


def _fuse_rep(a):
    """Fuse ties into rep: published Fuses with real outside buyers earn trust; self-dealing costs it."""
    fz = _json_load(FUSES_PATH, {'fuses': {}})
    own = {fid for fid, f in fz['fuses'].items() if primary_of(f.get('creator') or '') == a}
    if not own:
        return None
    buys = [b for b in fz.get('buys') or [] if b['fuse'] in own]
    real = len({b['wallet'] for b in buys if not b.get('selfDeal') and not b.get('bot')})
    selfd = sum(1 for b in buys if b.get('selfDeal'))
    pts = min(10, real) - 10 * min(3, selfd)
    return {'label': f'Fuse creator: {real} outside buyer(s)' + (f', {selfd} self-buy(s)' if selfd else ''), 'points': pts} if pts else None


def _shield_scan_all():
    """Every known wallet through every engine, data loaded once (HQ list + hourly alerts)."""
    qs = _json_load(QUEST_STATE_PATH, {})
    trades_all = _json_load(FEELESS_TRADES_PATH, {})
    chat_all = [m for ms in _chat_load()['rooms'].values() for m in ms if isinstance(m, dict) and not m.get('system')]
    ck_all = {w: v.get('checkinAt') or [] for w, v in qs.items()}
    wallets = set(qs) | set(trades_all) | {m.get('identity') or m.get('address') for m in chat_all} | set(_json_load(REF_PATH, {'by': {}})['by'])
    wallets = {w for w in wallets if isinstance(w, str) and _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', w)}
    manual = _json_load(SHIELD_PATH, {}).get('manual') or {}
    prot = _protected_wallets()
    rows = []
    for w in wallets:
        r = _shield.scan(_shield_features(w, ck_all, trades_all, chat_all), protected=w in prot, manual=manual.get(w))
        _shield_cache[w] = (time.time(), r)
        rows.append({'address': w, **r, 'manual': manual.get(w)})
    return rows


@app.get('/api/reputation/admin/shield')
async def shield_admin(request: Request, verdict: str = Query('flagged')):
    """HQ › Security › Bot shield: scan every known wallet with every engine."""
    _require_admin(request)
    rows = _shield_scan_all()
    counts = {k: sum(1 for r in rows if r['verdict'] == k) for k in ('bot', 'watch', 'clean')}
    engines = {e.__name__: sum(1 for r in rows for h in r['hits'] if h['engine'] == e.__name__) for e in _shield.ENGINES}
    shown = [r for r in rows if verdict == 'all' or (verdict == 'flagged' and r['verdict'] != 'clean') or r['verdict'] == verdict]
    return {'scanned': len(rows), 'counts': counts, 'engines': engines, 'rows': sorted(shown, key=lambda r: -r['score'])[:200]}


@app.post('/api/reputation/admin/shield')
async def shield_admin_set(request: Request):
    admin = _require_admin(request)
    body = await request.json()
    a, act = primary_of(str(body.get('address') or '')), body.get('action')
    if act not in ('cleared', 'bot', 'reset') or not a:
        raise HTTPException(400, 'address + cleared | bot | reset')
    async with _admin_lock:
        d = _json_load(SHIELD_PATH, {})
        m = d.setdefault('manual', {})
        if act == 'reset':
            m.pop(a, None)
        else:
            m[a] = act
        _json_save(SHIELD_PATH, d)
    _shield_cache.pop(a, None); _case_cache.pop(a, None)
    ad = _admin_load(); _audit(ad, admin, f'shield-{act}', a); _admin_save(ad)
    return {'ok': True}


_case_peak: dict = {}   # mint → peak volume $/h seen (live case files)


@app.get('/api/reputation/case/{address}')
async def case_file(address: str, fresh: bool = False):
    """One case file for any Solana address: a coin (risk score, holder clusters, launch forensics, the creator's
    case) or a wallet (verdict, cited evidence, funding trail, launches, linked wallets, caller behaviour)."""
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        raise HTTPException(400, 'Paste a Solana wallet or coin address.')
    hit = _case_cache.get(address)
    if hit and time.time() - hit[0] < (20 if fresh and hit[1].get('kind') == 'coin' else 120):
        return hit[1]
    if fresh and (_intel_cache.get(address) or (0,))[0] < time.time() - 30:
        _intel_cache.pop(address, None)            # live coin case: re-read holders / snipers at most every 30s
    async with httpx.AsyncClient(timeout=12) as http:
        auth = await _mint_authorities(http, address)
    out = await (_coin_case(address, auth) if auth else _wallet_case(address))
    if out.get('kind') == 'coin':   # live until its volume dies (−85% from peak)
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                prs = (await http.get(f'https://api.dexscreener.com/tokens/v1/solana/{address}')).json() or []
            top = max(prs, key=lambda p: (p.get('volume') or {}).get('h1') or 0) if prs else {}
            vol = top.get('volume') or {}
            st = investigate.live_state(vol.get('m5'), vol.get('h1'), _case_peak.get(address, 0))
            _case_peak[address] = st['peakPerH']
            out['live'] = st
        except Exception:
            out['live'] = {'live': False, 'pctOfPeak': None}
    out['at'] = time.time()
    _case_cache[address] = (time.time(), out)
    if len(_case_cache) > 3000:
        _case_cache.clear()
    return out


# ---- Copy callers: calls from wallets you follow, newest first, with each caller's record ---------------
@app.get('/api/reputation/calls/following/{address}')
async def following_calls(address: str, hours: int = Query(24, ge=1, le=168)):
    me = primary_of(address)
    following = set(_fol()['following'].get(me, []))
    if not following:
        return {'calls': [], 'following': 0}
    since = time.time() - hours * 3600
    board = {r.get('callerAddress'): r for r in (await caller_board(days=30))['rows']}
    calls = [_call_view(c) for c in _calls_load()['calls'].values() if c['at'] >= since and primary_of(c.get('callerAddress') or '') in following]
    calls.sort(key=lambda c: -c['at'])
    for c in calls:
        b = board.get(c.get('callerAddress')) or {}
        c['callerHitRate'] = b.get('hitRate'); c['callerCalls'] = b.get('calls')
    return {'calls': calls[:30], 'following': len(following)}


async def _fee_wallet_owner(http, cfg):
    """The wallet that owns the SOL/USDC fee account (read on-chain), used as the self-test's trader."""
    for acct in (cfg.get('feeAccountSol'), cfg.get('feeAccountUsdc')):
        if not acct:
            continue
        try:
            info = await _rpc(http, 'getAccountInfo', [acct, {'encoding': 'jsonParsed'}])
            owner = (((((info or {}).get('value') or {}).get('data') or {}).get('parsed') or {}).get('info') or {}).get('owner')
            if owner:
                return owner
        except Exception:
            continue
    return None


def _quote_fee_bps(q):
    """The fee Jupiter says it will take on this quote: Swap API reports platformFee.feeBps, Ultra reports feeBps."""
    return int((q.get('platformFee') or {}).get('feeBps') or q.get('feeBps') or 0)


@app.get('/api/reputation/admin/fees/selftest')
async def admin_fee_selftest(request: Request):
    """Prove FEELESS gets paid: quotes go through the SAME server endpoints the swap boxes use
    (/api/trading/quote for Solana, /api/lifi/quote for EVM swaps + bridges). Nothing is signed or sent."""
    _require_admin(request)
    cfg = _fee_cfg()
    usdc = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
    mints = await _ecosystem_mints()
    checks = []
    async with httpx.AsyncClient(timeout=40) as http:
        pump = None
        try:
            board = (await http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': 'trending', 'chain': 'solana', 'page': 1, 'scope': 'pump'})).json().get('pairs') or []
            pump = next(((p.get('baseToken') or {}).get('address') for p in board if (p.get('baseToken') or {}).get('address', '').endswith('pump')), None)
        except Exception:
            pump = None
        cases = [('SOL → USDC', WSOL, usdc, '0.01'), ('SOL → top Pump coin', WSOL, pump, '0.01'), ('Top Pump coin → SOL (sell)', pump, WSOL, '1000')]
        if mints.get('fee'):
            cases += [('SOL → $FEE (free buy)', WSOL, mints['fee'], '0.01'), ('$FEE → SOL (sell pays fee)', mints['fee'], WSOL, '10000')]
        # Build the real transaction (not just a price) so Jupiter validates the fee account exactly as it does
        # for traders. The fee wallet is the test signer; nothing is signed or sent.
        test_wallet = await _fee_wallet_owner(http, cfg)
        for label, a, b, amount in cases:
            if not a or not b:
                checks.append({'label': label, 'ok': False, 'detail': 'No live Pump coin found to test with.'})
                continue
            # Same wallet as the quote below, so holder-tier discounts match.
            expected = int((await effective_fee(test_wallet or '', a, b))['bps'])
            try:
                r = await http.post('http://127.0.0.1:5001/api/trading/quote', headers={'x-feeless-internal': _internal_key()},
                                  json={'input_mint': a, 'output_mint': b, 'amount': amount, 'slippage_bps': 50, 'wallet': test_wallet, 'probe': True})
                d = r.json()
            except Exception as exc:
                checks.append({'label': label, 'ok': False, 'detail': f'Swap server unreachable: {exc}'})
                continue
            if r.status_code != 200 or not (d.get('quote') or {}).get('outAmount'):
                checks.append({'label': label, 'ok': False, 'detail': f"Quote failed ({r.status_code}): {str(d.get('detail') or d)[:140]}"})
                continue
            q = d['quote']
            charged = _quote_fee_bps(q)
            ff = d.get('feeless_fee') or {}
            fee_note = '; '.join(ff.get('notes') or [])
            engine = 'Swap API' if d.get('engine') == 'swap' else 'Ultra'
            if expected:
                ok = charged >= expected and not ff.get('fallback')
                detail = (f'✓ {engine} · Jupiter confirms your {charged / 100:.2f}% fee on this trade' if ok
                          else f'FEELESS fee NOT applied ({engine}) — Jupiter confirmed {charged / 100:.2f}%. {fee_note}')
            else:
                ok = True
                detail = 'Free by rule' + (f" · Jupiter's own fee {charged / 100:.2f}%" if charged else '')
            checks.append({'label': label, 'ok': ok, 'rule': expected, 'charged': charged, 'detail': detail})
            await asyncio.sleep(1.2)   # stay under Jupiter's per-key rate limit
        lifi_bps = int(cfg.get('lifiFeeBps') or 0)
        integrator = cfg.get('lifiIntegrator') or os.environ.get('LIFI_INTEGRATOR', '')
        lifi = []
        for label, fc, tc in (('Base swap ETH → USDC', 8453, 8453), ('Bridge Arbitrum → Base', 42161, 8453)):
            if not integrator or not lifi_bps:
                lifi.append({'label': label, 'ok': None, 'skipped': True, 'detail': 'Skipped: no LI.FI fee set, so EVM swaps and bridges are free (set one below to charge).'})
                continue
            to_token = '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913' if tc == fc else '0x0000000000000000000000000000000000000000'
            try:
                r = await http.get('http://127.0.0.1:5001/api/lifi/quote', params={'fromChain': fc, 'toChain': tc, 'fromToken': '0x0000000000000000000000000000000000000000',
                                   'toToken': to_token, 'fromAmount': '10000000000000000', 'fromAddress': '0x552008c0f6870c2f77e5cC1d2eb9bdff03e30Ea0'})
                d = r.json()
            except Exception as exc:
                lifi.append({'label': label, 'ok': False, 'detail': f'LI.FI proxy unreachable: {exc}'})
                continue
            if r.status_code != 200:
                lifi.append({'label': label, 'ok': False, 'detail': f"Quote failed: {str(d.get('detail'))[:140]}"})
                continue
            ours = int((d.get('feeless') or {}).get('feeBps') or 0)
            total = sum(float(f.get('percentage') or 0) for f in (d.get('estimate') or {}).get('feeCosts') or [])
            ok = ours == lifi_bps and total >= 0.0025 + lifi_bps / 10000 - 1e-6
            lifi.append({'label': label, 'ok': ok, 'detail': (f"FEELESS fee {ours / 100:.2f}% applied (LI.FI total {total * 100:.2f}% incl. its own 0.25%)" if ok
                                                         else (d.get('feeless') or {}).get('note') or f'FEELESS fee not applied (got {ours / 100:.2f}%)')})
    live = [x for x in lifi if not x.get('skipped')]
    return {'checks': checks, 'lifiChecks': lifi, 'lifi': {'ok': all(x['ok'] for x in live) if live else None, 'skipped': not live, 'detail': ' · '.join(x['detail'] for x in lifi)}, 'at': time.time(),
            'note': 'Quotes only through the real swap endpoints — nothing is signed or sent. A pass means FEELESS is paid on real trades.'}


@app.post('/api/reputation/admin/fees')
async def admin_fees_set(request: Request, payload: FeeCfg):
    admin = _require_admin(request)
    addr = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'
    if payload.engine not in ('swap', 'ultra'):
        raise HTTPException(400, 'Engine must be swap or ultra.')
    for label, v in (('Referral account', payload.referralAccount), ('SOL fee account', payload.feeAccountSol), ('USDC fee account', payload.feeAccountUsdc)):
        if v and not _re.match(addr, v):
            raise HTTPException(400, f'{label} must be a Solana address.')
    uses_ultra = payload.engine == 'ultra' or payload.ultraFallback
    if payload.platformFeeBps and payload.engine == 'swap' and not (payload.feeAccountSol or payload.feeAccountUsdc):
        raise HTTPException(400, 'Add a SOL (wSOL) or USDC fee token account: the Swap API pays your fee into it.')
    if payload.platformFeeBps and uses_ultra and not payload.referralAccount:
        raise HTTPException(400, 'Ultra needs a Jupiter referral account (referral.jup.ag) to pay your fee.')
    if payload.engine == 'ultra' and payload.platformFeeBps and not JUP_MIN_BPS <= payload.platformFeeBps <= JUP_MAX_BPS:
        raise HTTPException(400, f'Ultra charges {JUP_MIN_BPS}–{JUP_MAX_BPS} bps (0.5–2.55%). Use the Swap engine for other fees.')
    # Discounts lower the fee, never remove it: at most 90% off.
    tiers = {str(k): max(0.0, min(90.0, float(v))) for k, v in (payload.tierDiscountPct or {}).items() if str(k) in ('0', '1', '2', '3')}
    zero = []  # no fee-free list: only FEELESS coin buys are exempt (see effective_fee)
    promo = {'label': str((payload.promo or {}).get('label') or '')[:40], 'discountPct': max(0.0, min(90.0, float((payload.promo or {}).get('discountPct') or 0))),
             'until': float((payload.promo or {}).get('until') or 0)}
    integrator = (payload.lifiIntegrator or '').strip() or os.environ.get('LIFI_INTEGRATOR', '').strip()
    if integrator and not _re.match(r'^[A-Za-z0-9_.-]{2,40}$', integrator):
        raise HTTPException(400, 'LI.FI integrator name: 2–40 letters, numbers, dot, dash or underscore (as registered at portal.li.fi).')
    if payload.lifiFeeBps and not integrator:
        raise HTTPException(400, 'Register an integrator at portal.li.fi and enter its name before setting a LI.FI fee.')
    async with _admin_lock:
        d = _admin_load()
        d['fees'] = {'platformFeeBps': payload.platformFeeBps, 'referralAccount': payload.referralAccount, 'tierDiscountPct': tiers, 'zeroFeeMints': zero, 'promo': promo,
                     'lifiIntegrator': integrator, 'lifiFeeBps': payload.lifiFeeBps if integrator else 0,
                     'engine': payload.engine, 'ultraFallback': payload.ultraFallback, 'feeAccountSol': payload.feeAccountSol,
                     'feeAccountUsdc': payload.feeAccountUsdc, 'priorityMaxLamports': payload.priorityMaxLamports,
                     'vaultFeeWallet': payload.vaultFeeWallet, **{k: v for k, v in (d.get('fees') or {}).items() if k in ('bundle', 'rounds', 'prepay')}}
        tier_txt = ' / '.join(f"{float(tiers.get(k, 0)):g}%" for k in ('0', '1', '2', '3'))
        _audit(d, admin, 'fees', f"{'Swap API' if payload.engine == 'swap' else 'Ultra'} · fee {payload.platformFeeBps / 100:.2f}% · Ultra fallback {'on' if payload.ultraFallback else 'off'} · "
                                 f"holder discounts {tier_txt} · promo {promo['discountPct']:.0f}% · speed tip ≤ {payload.priorityMaxLamports / 1e9:.4f} SOL")
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
REF_CFG_PATH = DATA_DIR / 'referral_cfg.json'      # {'pct': % of invitees' FEELESS fees earned by the inviter}
REF_EARN_PATH = DATA_DIR / 'referral_earnings.json'


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
    earned = _json_load(REF_EARN_PATH, {}).get(a) or {}
    return {'address': a, 'code': invite_code(a), 'handle': handle_of(a), 'invited': len(invited), 'recent': invited[-10:][::-1], 'invitedBy': d['of'].get(a),
            'pct': float(_json_load(REF_CFG_PATH, {}).get('pct') or 0), 'earnedUsd': earned.get('usd', 0), 'earnedSol': earned.get('sol', 0),
            'paidUsd': earned.get('paidUsd', 0), 'tradingInvitees': len(earned.get('invitees') or [])}


@app.get('/api/reputation/admin/referrals')
async def admin_referrals(request: Request):
    _require_admin(request)
    d = _json_load(REF_PATH, {'by': {}, 'of': {}})
    earn = _json_load(REF_EARN_PATH, {})
    rows = sorted(({'address': a, 'handle': handle_of(a), 'invited': len(v), 'earnedUsd': (earn.get(a) or {}).get('usd', 0), 'earnedSol': (earn.get(a) or {}).get('sol', 0)}
                   for a, v in d['by'].items()), key=lambda r: (-r['earnedUsd'], -r['invited']))
    return {'total': len(d['of']), 'top': rows[:50], 'pct': float(_json_load(REF_CFG_PATH, {}).get('pct') or 0),
            'owedUsd': round(sum((r.get('usd') or 0) - (r.get('paidUsd') or 0) for r in earn.values()), 4)}


class RefCfgIn(BaseModel):
    pct: float = Field(ge=0, le=50)


@app.put('/api/reputation/admin/referrals/config')
async def admin_referral_cfg(request: Request, p: RefCfgIn):
    """Every inviter earns this % of the FEELESS fees their invitees pay (accrues on each confirmed trade)."""
    me = _require_owner(request)
    _json_save(REF_CFG_PATH, {'pct': round(p.pct, 2), 'by': me, 'at': time.time()})
    ad = _admin_load(); _audit(ad, me, 'referral-pct', f'{p.pct}% of invitee fees'); _admin_save(ad)
    return {'pct': round(p.pct, 2)}


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


# ---- HQ: pulse, moderation, broadcast, treasury ---------------------------------
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
        feeless_post(room, f'📢 {payload.title}\n{payload.body}')
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


SNIPERS_OUT_COOLDOWN = 86400  # snipers can only sell out once; don't re-announce the same coin all day


def _radar_event(kind, pa, sym, text, cooldown=3600, **extra):
    last = next((e for e in _radar['events'] if e['pair'] == pa and e['kind'] == kind), None)
    if last and time.time() - last['at'] < cooldown:
        return False
    _radar['events'].insert(0, {'kind': kind, 'pair': pa, 'symbol': sym, 'text': text, 'at': time.time(), **extra})
    _radar['events'] = _radar['events'][:100]
    return True


async def _push_snipers_out(mint):
    # Phones with push on and this coin on their watchlist hear it first; tapping opens the buy.
    for entry in list(_push_load()['subs'].values()):
        w = next((x for x in entry['watch'] if mint in (x.get('mint'), x.get('pairAddress'))), None)
        if w:
            if (entry.get('prefs') or {}).get('address'):
                notify(entry['prefs']['address'], 'snipers', f"Every flagged sniper/bundler on {w.get('symbol') or mint[:4]} has sold out",
                       f"/terminal/chat?chain=solana&pair={w['pairAddress']}&room=bulls", once=f'snipers-{mint}', push=False,
                       meta={'symbol': w.get('symbol'), 'claim': 'All flagged sniper/bundler wallets sold', 'source': 'Launch forensics (holder scan)'})
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
        activity = (await http.get('http://127.0.0.1:5088/api/cats/activity?catId=leader')).json()
    return {**r.json(), 'learning': prof.get('learning'), 'stats': prof.get('stats'), 'events': (activity.get('events') or [])[:8], 'cat': {k: (prof.get('cat') or {}).get(k) for k in ('balanceSol', 'realizedPnlSol', 'winRate', 'status', 'lastTick', 'positions')}}


@app.post('/api/reputation/admin/feecat')
async def admin_feecat_set(request: Request):
    admin = _require_admin(request)
    body = await request.json()
    action = body.pop('action', None)
    async with httpx.AsyncClient(timeout=30) as http:
        if action == 'run':
            run = await http.post('http://127.0.0.1:5088/api/cats/leader/action', json={'action': 'run'})
            if run.status_code != 200:
                raise HTTPException(run.status_code, 'Fee service could not run the intelligence cycle.')
        r = await http.post('http://127.0.0.1:5088/api/cats/internal/rules', headers={'x-feeless-internal': _internal_key()}, json=body)
    if r.status_code != 200:
        raise HTTPException(r.status_code, 'Fee service rejected the change.')
    ad = _admin_load(); _audit(ad, admin, 'feecat', json.dumps({k: v for k, v in body.items() if k != 'rules'} | {'rules': list((body.get('rules') or {}).keys())})[:160]); _admin_save(ad)
    return r.json()


# ---- Notifications inbox (per identity) + push to the owner's devices ----------------------
NOTIF_PATH = DATA_DIR / 'notifications.json'


def notify(address: str, kind: str, text: str, url: str = '', actor: str = '', once: str = '', meta: Optional[dict] = None, push: bool = True):
    """once: a dedupe key — a notification with the same key is never sent to this wallet twice.
    push=False: inbox only (the caller already pushed to the phone)."""
    to = primary_of(address)
    if not to or to in ('FEE-LEADER-CAT', 'FEELESS-HQ') or primary_of(actor or '') == to:
        return
    d = _json_load(NOTIF_PATH, {})
    box = d.setdefault(to, [])
    if once and any(n.get('once') == once for n in box):
        return
    box.insert(0, {'id': uuid.uuid4().hex[:10], 'kind': kind, 'text': text[:200], 'url': url, 'actor': actor, 'at': time.time(), 'read': False,
                   **({'once': once} if once else {}), **({'meta': meta} if meta else {})})
    d[to] = box[:200]
    _json_save(NOTIF_PATH, d)
    if not push:
        return
    try:
        for e in _push_load()['subs'].values():
            if primary_of((e.get('prefs') or {}).get('address') or '') == to:
                asyncio.get_running_loop().run_in_executor(None, _send_push, e['subscription'], {'dm': '💬 New message', 'follow': '➕ New follower', 'wall': '🧱 New wall post', 'mention': '📣 You were mentioned', 'reward': '🎁 Reward ready', 'invite': '🎉 Invite joined', 'snipers': '🎯 Snipers are out', 'watch': '👁 Watched wallet moved'}.get(kind, 'FEELESS'), text[:120], url or '/terminal', f'n-{kind}')
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
    box = _legacy_sniper_dedupe(_json_load(NOTIF_PATH, {}).get(me, []))
    return {'unread': sum(1 for n in box if not n['read']), 'items': box[:60]}


def _legacy_sniper_dedupe(box):
    """Older builds repeated the snipers-out alert on every intel refresh: keep only the newest per coin."""
    seen, out = set(), []
    for n in box:
        legacy = n.get('kind') == 'reward' and 'sniper on your coin' in n.get('text', '')
        key = n.get('text') if legacy else None
        if key and key in seen:
            continue
        if key:
            seen.add(key)
            n = {**n, 'kind': 'snipers'}
        out.append(n)
    return out


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


# Who may message a wallet: everyone, requests (first message waits until accepted) or nobody.
DM_PREFS_PATH = DATA_DIR / 'dm_prefs.json'
DM_POLICIES = ('everyone', 'requests', 'nobody')


def _dm_pref(addr):
    p = _json_load(DM_PREFS_PATH, {}).get(addr) or {}
    return {'policy': p.get('policy', 'everyone'), 'accepted': p.get('accepted', [])}


class DmPrefsIn(BaseModel):
    address: str
    session: str
    policy: Optional[str] = None
    accept: Optional[str] = None


@app.get('/api/reputation/dm-settings')
async def dm_settings(address: str, session: str):
    return _dm_pref(_session_or_401(address, session))


@app.post('/api/reputation/dm-settings')
async def dm_settings_set(payload: DmPrefsIn):
    me = _session_or_401(payload.address, payload.session)
    if payload.policy and payload.policy not in DM_POLICIES:
        raise HTTPException(400, 'Unknown message setting.')
    async with _admin_lock:
        d = _json_load(DM_PREFS_PATH, {}); cur = {**_dm_pref(me), **(d.get(me) or {})}
        if payload.policy:
            cur['policy'] = payload.policy
        if payload.accept:
            cur['accepted'] = sorted(set(cur.get('accepted', [])) | {primary_of(payload.accept)})[-500:]
        d[me] = cur; _json_save(DM_PREFS_PATH, d)
    return _dm_pref(me)


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
    pref = _dm_pref(to)
    thread = _json_load(DM_PATH, {}).get(_dm_key(me, to), [])
    replied = any(m['from'] == to for m in thread)  # they've written to me: the thread is open both ways
    is_admin = primary_of(me) in {primary_of(w) for w in _admin_wallets()}
    request = False
    if not is_admin and not replied and me not in pref['accepted']:
        if pref['policy'] == 'nobody':
            raise HTTPException(403, "This wallet isn't accepting messages.")
        if pref['policy'] == 'requests':
            if thread:
                raise HTTPException(403, 'Your message request is waiting — you can write again once they accept.')
            request = True
    _dm_last[me] = time.time()
    msg = {'id': uuid.uuid4().hex[:12], 'from': me, 'to': to, 'text': payload.text.strip(), 'at': time.time(), **({'request': True} if request else {})}
    async with _admin_lock:
        d = _json_load(DM_PATH, {})
        d.setdefault(_dm_key(me, to), []).append(msg)
        d[_dm_key(me, to)] = d[_dm_key(me, to)][-300:]
        _json_save(DM_PATH, d)
    notify(to, 'dm', f"{'📨 Message request from ' if request else ''}@{handle_of(me)}: {payload.text.strip()}", f'/terminal/profile/{to}?dm=1', me)
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
            pending = _dm_pref(me)['policy'] == 'requests' and peer not in _dm_pref(me)['accepted'] and not any(m['from'] == me for m in msgs)
            rows.append({'peer': peer, 'handle': handle_of(peer), 'last': msgs[-1], 'count': len(msgs), 'request': pending})
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


# ---- Auto-managed Helius webhook: follows the public domain set in the HQ ---------
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
async def portfolio(address: str, fresh: int = 0):
    a = primary_of(address)
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a):
        return {'address': a, 'supported': False, 'tokens': [], 'totalUsd': None}
    hit = _pf_cache.get(a)
    if hit and time.time() - hit[0] < (8 if fresh else 90):   # fresh=1 right after a trade (still shielded from hammering)
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
        case = _quick_rep(a) if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a) else None
        if case and case.get('level') in ('watch', 'suspect', 'high'):  # the case-file verdict rides along everywhere a name shows
            out.setdefault(raw, {'score': None, 'level': None})['case'] = case
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
    sh = await _shield_of(a)
    if _shield.rep_penalty(sh):
        score += _shield.rep_penalty(sh); evidence += 1; parts.append({'label': f"Bot shield: {sh['verdict']} — {sh['why']}", 'points': _shield.rep_penalty(sh)})
    fz = _fuse_rep(a)
    if fz:
        score += fz['points']; evidence += 1; parts.append(fz)
    fsc = (_fuse_score_cache.get(a) or (0, None))[1]   # cached only: trust never waits on (or loops through) the Fuse score
    if fsc and _hq.trust_from_fuse(fsc['perf'], fsc['cards']):
        pts = _hq.trust_from_fuse(fsc['perf'], fsc['cards'])
        score += pts; evidence += 1; parts.append({'label': f"Fuse score {fsc['score']} — verified card P&L, medals, copies, streaks", 'points': pts})
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


# ---- HQ: the numbers side --------------------------------------------------------
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
    integ = cfg.get('lifiIntegrator') or os.environ.get('LIFI_INTEGRATOR', '').strip()
    lifi = {'integrator': integ, 'fee': round(cfg['lifiFeeBps'] / 10000, 4)} if integ and cfg.get('lifiFeeBps') else None
    return {'platformFeeBps': cfg['platformFeeBps'], 'tierDiscountPct': cfg['tierDiscountPct'], 'promo': cfg.get('promo'), 'lifi': lifi,
            'feelessIntoFee': True, 'note': 'Buying $FEE, FEECAT or rFEE with SOL, USDC or USDT is fee-free. Selling them and every other swap, buy, sell or bridge pays the platform fee.'}


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
    staff = _is_staff(a)   # the creator / admin wallets always get their colors
    ok = staff or held >= THEME_MIN_USD
    return {'address': a, 'holdingUsd': held, 'poolBuilder': held >= POOL_BUILDER_MIN_USD, 'minUsd': THEME_MIN_USD, 'eligible': ok, 'staff': staff,
            'theme': saved if ok else None}


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
    if held < THEME_MIN_USD and a not in {primary_of(w) for w in _admin_wallets()}:
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
        # A position only counts as closed once a real part of it (20%+) was sold: dust/fee sells are not exits.
        if t['buys'] and t['sells'] and bought and sold >= bought * 0.2:
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
             # Percentages need a sample: one or two closed positions say nothing about a trader.
             'quickFlipPct': round(flips / closed * 100) if closed >= 3 else None, 'dumpPct': round(dumps / closed * 100) if closed >= 3 else None,
             'winPct': round(wins / closed * 100) if closed >= 3 else None, 'netUsd': round(sum((x['pnlUsd'] or 0) for x in tokens)),
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
    reserveWallet: str = ''
    badgeRewardPct: float = Field(default=0, ge=0, le=100)


@app.post('/api/reputation/admin/seasons')
async def admin_season_upsert(request: Request, p: SeasonPayload):
    admin = _require_admin(request)
    if p.end <= p.start or p.end - p.start > 120 * 86400 or not _re.match(r'^#[0-9a-fA-F]{6}$', p.accent) or not (0.5 <= p.multiplier <= 5):
        raise HTTPException(400, 'Invalid season (end after start, ≤120 days, #hex accent, multiplier 0.5–5).')
    d = _seasons()
    if any(not (p.end <= s['start'] or p.start >= s['end']) for s in d['seasons']):
        raise HTTPException(409, 'Seasons cannot overlap.')
    sid = f"s{len(d['seasons']) + 1}"
    if p.reserveWallet and not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.reserveWallet):
        raise HTTPException(400, 'Fee Reserve wallet must be a valid Solana address.')
    d['seasons'].append({'id': sid, 'name': p.name[:40], 'theme': p.theme[:160], 'start': p.start, 'end': p.end, 'prize': p.prize[:160],
                         'multiplier': p.multiplier, 'accent': p.accent, 'reserveWallet': p.reserveWallet,
                         'badgeRewardPct': p.badgeRewardPct, 'createdBy': admin})
    _json_save(SEASONS_PATH, d)
    return {'ok': True, 'id': sid}


@app.get('/api/reputation/admin/seasons')
async def admin_seasons(request: Request):
    _require_admin(request)
    d = _seasons()
    return {'seasons': d['seasons'], 'players': {k: len(v) for k, v in d['scores'].items()}}


# ================================================================================================
# HQ ROLES + IDEAS
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
    ts: int = 0
    sig: str = ''


def grant_message(address, role, ts):
    return f'FEELESS grant HQ access\nwallet:{address}\nrole:{role}\nts:{int(ts)}'


@app.get('/api/reputation/admin/roles')
async def admin_roles(request: Request):
    me = _require_admin(request)
    return {'owners': _owner_wallets(), 'grants': _granted(), 'youAreOwner': me in _owner_wallets(), 'roles': ROLE_NAMES,
            'yourRole': _role_of(me), 'scopes': {k: sorted(v) for k, v in ROLE_SCOPES.items()}}


@app.post('/api/reputation/admin/roles')
async def admin_role_grant(request: Request, p: RolePayload):
    me = _require_admin(request)
    if me not in _owner_wallets():
        raise HTTPException(403, 'Only the FEELESS owner wallet can grant HQ access.')
    if p.role not in ROLE_NAMES or not (_re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.address) or _re.match(r'^0x[0-9a-fA-F]{40}$', p.address)):
        raise HTTPException(400, 'Valid wallet + role (admin, moderator, marketing) required.')
    # The creator signs THIS grant (wallet, role, time) — a leaked HQ session alone can never hand out access.
    if abs(time.time() - p.ts) > 600 or not _verify_wallet(me, grant_message(p.address, p.role, p.ts), p.sig):
        raise HTTPException(401, 'Sign the grant with the owner wallet (signature missing, expired or wrong).')
    d = _json_load(ROLES_PATH, {'grants': {}})
    d['grants'][p.address] = {'role': p.role, 'by': me, 'at': time.time(), 'sig': p.sig[:120]}
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
                                'tier': t, 'score': r['score'], 'accent': s['accent'], 'reserveWallet': s.get('reserveWallet', ''),
                                'badgeRewardPct': float(s.get('badgeRewardPct') or 0), 'rewardStatus': 'planned', 'at': now})
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
    reserveWallet: Optional[str] = None
    badgeRewardPct: Optional[float] = Field(default=None, ge=0, le=100)


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
    if new.get('reserveWallet') and not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', new['reserveWallet']):
        raise HTTPException(400, 'Fee Reserve wallet must be a valid Solana address.')
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
    """Name, $ticker or contract → Solana coins, biggest market cap first.
    Jupiter (keyed, then the keyless lite API) and DexScreener are merged, so one provider being down,
    rate-limited or missing a fresh Pump coin never leaves the swap picker empty."""
    q = q.strip().lstrip('$')
    hit = _tok_search_cache.get(q.lower())
    if hit and time.time() - hit[0] < 30:
        return hit[1]
    found: dict = {}
    blocks = _block_load()['wallets']

    def add(mint, **row):
        if not mint:
            return
        cur = found.setdefault(mint, {'mint': mint, 'symbol': None, 'name': None, 'icon': None, 'decimals': None,
                                      'price': None, 'mcap': None, 'liquidity': None, 'verified': False, 'blocked': False})
        for k, v in row.items():
            if v not in (None, '') and (cur.get(k) in (None, '', False) or k in ('mcap', 'liquidity') and (v or 0) > (cur.get(k) or 0)):
                cur[k] = v

    async with httpx.AsyncClient(timeout=8) as http:
        async def jupiter():
            key = os.environ.get('JUPITER_API_KEY', '')
            urls = ([('https://api.jup.ag/tokens/v2/search', {'x-api-key': key})] if key else []) + [('https://lite-api.jup.ag/tokens/v2/search', {})]
            for url, headers in urls:
                try:
                    r = await http.get(url, params={'query': q}, headers=headers)
                    if r.status_code == 200 and isinstance(r.json(), list):
                        return r.json()[:30]
                except Exception:
                    continue
            return []

        async def dexscreener():
            try:
                r = await http.get('https://api.dexscreener.com/latest/dex/search', params={'q': q})
                return [p for p in ((r.json() or {}).get('pairs') or []) if p.get('chainId') == 'solana'][:40] if r.status_code == 200 else []
            except Exception:
                return []

        jup, dex = await asyncio.gather(jupiter(), dexscreener())
    for t in jup:
        add(t.get('id'), symbol=t.get('symbol'), name=t.get('name'), icon=t.get('icon'), decimals=t.get('decimals'), price=t.get('usdPrice'),
            mcap=t.get('mcap') or t.get('fdv'), liquidity=t.get('liquidity'), verified=bool(t.get('isVerified')),
            blocked=_is_blocked(blocks.get(t.get('dev') or '')))
    for p in dex:
        b = p.get('baseToken') or {}
        add(b.get('address'), symbol=b.get('symbol'), name=b.get('name'), icon=(p.get('info') or {}).get('imageUrl'),
            price=float(p['priceUsd']) if p.get('priceUsd') else None, mcap=p.get('marketCap') or p.get('fdv'),
            liquidity=(p.get('liquidity') or {}).get('usd'))
    # Biggest market cap first; an exact contract paste always leads.
    rows = sorted(found.values(), key=lambda x: (x['mint'] != q, -(x['mcap'] or 0), -(x['liquidity'] or 0)))[:20]
    data = {'q': q, 'tokens': rows, 'ok': bool(jup or dex)}
    if rows:  # never cache a miss: a provider hiccup must not blank the picker for 30s
        _tok_search_cache[q.lower()] = (time.time(), data)
    if len(_tok_search_cache) > 2000:
        _tok_search_cache.clear()
    return data


@app.get('/api/reputation/admin/is-admin/{address}')
async def is_admin(address: str):
    """Public yes/no so the UI can show admin controls. Every admin action still needs a signed session."""
    return {'admin': address in _admin_wallets(), 'owner': address in _owner_wallets()}



_fills_cache: dict = {}


async def _feeless_fills(address: str) -> list:
    """Every confirmed FEELESS order for this wallet (trading service), so a position shows even when the
    live confirm hook was missed (old trades, a restart, a closed tab). Cached 8s."""
    hit = _fills_cache.get(address)
    if hit and time.time() - hit[0] < 8:
        return hit[1]
    rows = hit[1] if hit else []
    if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        try:
            async with httpx.AsyncClient(timeout=4) as http:
                r = await http.get(f'http://127.0.0.1:5001/api/trading/internal/fills/{address}', params={'sol': await _sol_usd()},
                                   headers={'x-feeless-internal': _internal_key()})
                if r.status_code == 200:
                    rows = r.json().get('fills') or []
        except Exception:
            pass
    _fills_cache[address] = (time.time(), rows)
    return rows


async def _chain_fills(address: str, token: str) -> dict:
    """Exact fills from the wallet's own transactions (trading service RPC pool) + its live balance."""
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) or not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', token):
        return {}
    try:
        async with httpx.AsyncClient(timeout=15) as http:   # a wallet's first scan reads its history once; later ones are instant
            r = await http.get(f'http://127.0.0.1:5001/api/trading/chain-fills/{address}/{token}', headers={'x-feeless-internal': _internal_key()})
            return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


_repair_tried: dict = {}


async def _repair_estimates(address: str, token: str):
    """Self-heal: any of this wallet's FEELESS trades saved from a quote gets its exact on-chain fill read once and
    saved over the estimate (at most one attempt per trade per minute; never blocks the position for long)."""
    # Estimates, and exact rows saved before the pool amount was read, both get one exact re-read.
    rows = [r for r in _json_load(FEELESS_TRADES_PATH, {}).get(address, []) if r.get('token', '').lower() == token.lower() and not r.get('locked')]
    now = time.time()
    todo = [r['tx'] for r in rows if r.get('tx') and now - _repair_tried.get(r['tx'], 0) > 60][:3]
    if not todo:
        return

    async def one(sig):
        _repair_tried[sig] = now
        try:
            async with httpx.AsyncClient(timeout=6) as http:
                r = await http.get(f'http://127.0.0.1:5001/api/trading/internal/exact-fill/{sig}', headers={'x-feeless-internal': _internal_key()})
                return sig, (r.json().get('fill') if r.status_code == 200 else None)
        except Exception:
            return sig, None
    got = {sig: f for sig, f in await asyncio.gather(*(one(s) for s in todo)) if f and f.get('tokens')}
    if not got:
        return
    px = await _sol_usd()
    ft = _json_load(FEELESS_TRADES_PATH, {})
    fixed = []
    for r in ft.get(address) or []:
        f = got.get(r.get('tx'))
        usd = (f.get('usd') or (f.get('sol') or 0) * px) if f else 0
        if f and usd > 0:
            r = {**r, 'side': f['side'], 'tokens': f['tokens'], 'sol': f.get('sol'), 'networkSol': f.get('networkSol'), 'usd': round(usd, 4),
                 **{k: f[k] for k in ('poolUsd', 'feelessFeeUsd', 'networkUsd', 'solUsd', 'locked') if f.get(k) is not None},
                 'locked': True,   # read once, priced once: never re-read or re-priced again
                 'price': usd / f['tokens'], 'ts': f.get('ts') or r.get('ts'), 'via': 'chain'}
        fixed.append(r)
    ft[address] = fixed
    _json_save(FEELESS_TRADES_PATH, ft)


@app.get('/api/reputation/position/{address}/{token}')
async def position(address: str, token: str):
    """A wallet's position in one coin: exact on-chain fills first (any app), then the wallet-history provider, then
    FEELESS's own order records. Average entry, real balance, fees paid, per-trade P&L. Feeds the chart line + badge."""
    if not (_re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address) or _re.match(r'^0x[0-9a-fA-F]{40}$', address)) or len(token) > 64:
        raise HTTPException(400, 'Bad address.')

    async def history():
        try:
            await wallet_trades(address)
        except Exception:
            pass   # wallet-history provider down: the chain + FEELESS's own records still give the position
    await _repair_estimates(address, token)
    _, fills, chain = await asyncio.gather(history(), _feeless_fills(address), _chain_fills(address, token))
    tok = token.lower()
    provider = [r for r in (_wtrades_all.get(address) or (0, []))[1] if r['token'].lower() == tok]
    own = [r for r in _json_load(FEELESS_TRADES_PATH, {}).get(address, []) + fills if r['token'].lower() == tok]
    # Locked rows first — every one of them was read from the chain once and priced at its own moment (FEELESS trades
    # at signing, outside trades at their block time) — then anything still waiting for its price, then estimates.
    cf = chain.get('fills') or []
    rows = trade_fills.merge([r for r in cf if r.get('locked')], [r for r in own if r.get('locked')],
                             [r for r in cf if not r.get('locked')], [r for r in own if not r.get('locked')], provider)
    fees = {r.get('sig'): r.get('feeUsd') or 0 for r in _json_load(FEE_LEDGER_PATH, {}).get(primary_of(address), [])}
    pos = trade_fills.position(rows, chain.get('balance') if 'balance' in chain else None, fees)
    if pos:
        pos['sources'] = {k: sum(1 for r in rows if (r.get('via') or 'provider') == k) for k in ('chain', 'estimate', 'feeless', 'provider')}
        pos['chainRead'] = 'balance' in chain
    return {'address': address, 'token': token, 'position': pos, 'balance': chain.get('balance')}


async def _locked_fills(address: str) -> list:
    """Every locked fill stored for this wallet (all coins), from the trading service. Same numbers as the chart."""
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            r = await http.get(f'http://127.0.0.1:5001/api/trading/internal/wallet-fills/{address}', headers={'x-feeless-internal': _internal_key()})
            return r.json().get('fills') or [] if r.status_code == 200 else []
    except Exception:
        return []


@app.get('/api/reputation/trade-cards/{address}')
async def trade_cards(address: str):
    """A wallet's recent FEELESS trades as shareable cards: side, size, per-sell P&L (average cost), fee, tx, coin."""
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        raise HTTPException(400, 'Bad address.')
    own = _json_load(FEELESS_TRADES_PATH, {}).get(address, [])
    rows = trade_fills.merge(await _locked_fills(address), [r for r in own if r.get('locked')], own, await _feeless_fills(address))
    fees = {r.get('sig'): r.get('feeUsd') or 0 for r in _json_load(FEE_LEDGER_PATH, {}).get(primary_of(address), [])}
    cards = []
    for tok in {r['token'] for r in rows}:
        mine = [r for r in rows if r['token'] == tok]
        pos = trade_fills.position(mine, None, fees)
        for t in (pos or {}).get('trades') or []:
            cost = (t.get('tokens') or (t['usd'] / t['price'])) * pos['avgEntry']
            cards.append({**t, 'token': tok, 'pnlPct': round(t['pnlUsd'] / cost * 100, 2) if t.get('pnlUsd') is not None and cost else None})
    cards = sorted(cards, key=lambda c: -(c.get('ts') or 0))[:24]

    async def sym(mint):
        try:
            async with httpx.AsyncClient(timeout=4) as http:
                r = await http.get(f'http://127.0.0.1:5001/api/trading/mint/{mint}')
                return mint, (r.json().get('symbol') if r.status_code == 200 else None)
        except Exception:
            return mint, None
    symbols = dict(await asyncio.gather(*(sym(m) for m in list({c['token'] for c in cards})[:12])))
    for c in cards:
        c['symbol'] = symbols.get(c['token'])
    return {'address': address, 'cards': cards}


_version_cache: dict = {}


async def _git(*args, timeout=8):
    proc = await asyncio.create_subprocess_exec('git', *args, cwd=str(Path(__file__).resolve().parents[1]), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill(); return ''
    return out.decode().strip() if proc.returncode == 0 else ''


@app.get('/api/reputation/version')
async def version():
    """Which code this machine is running vs GitHub main, so a stale copy is obvious (footer shows it)."""
    hit = _version_cache.get('v')
    if hit and time.time() - hit[0] < 30:
        return hit[1]
    if time.time() - _version_cache.get('fetched', 0) > 300:
        _version_cache['fetched'] = time.time()
        await _git('fetch', '-q', 'origin', 'main', timeout=20)
    head, branch, behind, dirty = await asyncio.gather(_git('rev-parse', '--short', 'HEAD'), _git('rev-parse', '--abbrev-ref', 'HEAD'),
                                                       _git('rev-list', '--count', 'HEAD..origin/main'), _git('status', '--porcelain', '--untracked-files=no'))
    v = {'head': head or None, 'branch': branch or None, 'behind': int(behind) if behind.isdigit() else None,
         'dirty': [l[3:] for l in dirty.splitlines()][:8], 'fix': 'bash scripts/update.sh'}
    _version_cache['v'] = (time.time(), v)
    return v


@app.post('/api/reputation/local/update')
async def local_update(request: Request):
    """One-click update from the footer, for the machine running FEELESS itself: runs scripts/update.sh detached
    (it restarts this service). Refused from anywhere but localhost, so a public site can never be poked."""
    host = (request.client.host if request.client else '') or ''
    origin = (request.headers.get('origin') or '').lower()
    if host not in ('127.0.0.1', '::1', 'localhost') or (origin and not _re.match(r'^https?://(localhost|127\.0\.0\.1)(:\d+)?$', origin)):
        raise HTTPException(403, 'Updates can only be started on the machine running FEELESS.')
    root = Path(__file__).resolve().parents[1]
    log = open('/tmp/feeless-update.log', 'w')
    await asyncio.create_subprocess_exec('bash', str(root / 'scripts' / 'update.sh'), cwd=str(root), stdout=log, stderr=log, start_new_session=True)
    _version_cache.clear()
    return {'ok': True, 'log': '/tmp/feeless-update.log'}


@app.get('/api/reputation/local/update-log')
async def local_update_log(request: Request):
    host = (request.client.host if request.client else '') or ''
    if host not in ('127.0.0.1', '::1', 'localhost'):
        raise HTTPException(403, 'Local only.')
    try:
        return {'log': Path('/tmp/feeless-update.log').read_text()[-4000:]}
    except OSError:
        return {'log': ''}


# ---- Setup checklist for the HQ: which keys/URLs are configured (never the values) ----
SETUP_KEYS = [
    ('SOLANA_RPC_URL', 'Solana RPC (Helius)', 'Chain reads, forensics, trades feed', True),
    ('ALCHEMY_API_KEY', 'Alchemy', 'EVM + Solana RPC, price history, gas checks', True),
    ('JUPITER_API_KEY', 'Jupiter', 'Solana swaps, token search, $FEE pricing', True),
    ('FEELESS_ADMIN_WALLETS', 'Owner wallets', 'Who can open the HQ (defaults to creator wallet)', False),
    ('ALLOWED_ORIGINS', 'Site domain', 'Lock APIs to your domain before launch', False),
    ('HELIUS_WEBHOOK_SECRET', 'Helius webhook secret', 'Instant whale / dev-sell events', False),
    ('BASE_RPC_URL', 'Base RPC', 'Dedicated Base endpoint for pool reads', False),
    ('PUBLIC_SITE_URL', 'Public site URL', 'Hosts new coins\' metadata so wallets/explorers show name + image (required to launch)', True),
    ('PRICE_STREAM_WS_URL', 'Live chart stream', 'Tick-by-tick candles on charts (Helius / Triton websocket); without it charts poll', False),
    ('MONGO_URL', 'Database', 'Orders, swap history and trade receipts (required for trading)', True),
    ('LIFI_API_KEY', 'LI.FI', 'Higher rate limits for EVM swaps, bridges and gas', False),
    ('ETHERSCAN_API_KEY', 'Etherscan', 'EVM contract + holder reads', False),
    ('PUMPPORTAL_API_KEY', 'PumpPortal', 'Paid live Pump trade stream (instant new-coin flow)', False),
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
# wallet in the HQ. Every FEELESS launch then creates its pool on that config, signed by
# the creator's wallet. The server stores only public addresses and never signs anything.
LAUNCH_RAIL_PATH = DATA_DIR / 'launch_rail.json'
TOKEN_META_DIR = DATA_DIR / 'token_meta'
DBC_PROGRAM = 'dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN'
_B58 = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'


class LaunchRailIn(BaseModel):
    config: str
    feeClaimer: str
    params: dict = {}
    scope: str = 'public'      # public: the Launch page for everyone · house: owner/admin-only launches (FEELESS's own coins)
    label: str = ''


@app.get('/api/reputation/launch-rail')
async def launch_rail():
    r = _json_load(LAUNCH_RAIL_PATH, {})
    return {'ready': bool(r.get('config')), **r, 'tab': launch_meta.clean_tab(r.get('tab') or launch_meta.TAB_DEFAULT), 'costs': launch_meta.clean_costs(r.get('costs')), 'siteUrl': os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/')}


@app.put('/api/reputation/admin/launch-rail')
async def launch_rail_set(request: Request, p: LaunchRailIn):
    me = _require_admin(request)   # owner and admins: the config is verified on-chain below, and every change is audited
    if not (_re.match(_B58, p.config) and _re.match(_B58, p.feeClaimer)):
        raise HTTPException(400, 'Config and fee claimer must be Solana addresses.')
    # Only accept a config that really exists on-chain and belongs to the DBC program.
    async with httpx.AsyncClient(timeout=10) as http:
        info = await _rpc(http, 'getAccountInfo', [p.config, {'encoding': 'base64'}])
    owner = ((info or {}).get('value') or {}).get('owner')
    if owner != DBC_PROGRAM:
        raise HTTPException(409, 'That config is not on-chain yet (or is not a Meteora DBC config). Wait for confirmation and retry.')
    keep = {k: p.params[k] for k in ('initialMarketCap', 'migrationMarketCap', 'startingFeeBps', 'endingFeeBps', 'feeDecayMin', 'creatorFeePct', 'lockedLpPct', 'supply', 'quote', 'preset', 'buyBurn', 'poolCreationFeeSol') if k in p.params}
    rec = {'config': p.config, 'feeClaimer': p.feeClaimer, 'params': keep, 'setBy': me, 'at': time.time()}
    d = _json_load(LAUNCH_RAIL_PATH, {})
    if p.scope == 'house':
        # House configs never replace the public one; they sit beside it for owner-only launches.
        house = [h for h in d.get('house') or [] if h['config'] != p.config]
        house.append({**rec, 'id': p.config[:8], 'label': (p.label or 'House config')[:40]})
        d['house'] = house[-8:]
    elif p.scope == 'public':
        d = {**d, **rec}
    else:
        raise HTTPException(400, 'Scope must be public or house.')
    _json_save(LAUNCH_RAIL_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'launch-rail', f"{p.scope} config {p.config[:8]}"); _admin_save(ad)
    return d


class LaunchCostsIn(BaseModel):
    pumpSlippagePct: float = 1.0
    pumpPriorityFeeSol: float = 0.0001
    feelessPriorityFeeSol: float = 0.0001


@app.put('/api/reputation/admin/launch-costs')
async def launch_costs_set(request: Request, p: LaunchCostsIn):
    """Owner/admin: slippage + priority fee for pump.fun launches and priority fee for FEELESS / House launches.
    Stored beside the launch rules (nothing else in that file changes)."""
    me = _require_admin(request)
    d = _json_load(LAUNCH_RAIL_PATH, {}); d['costs'] = launch_meta.clean_costs(p.model_dump()); _json_save(LAUNCH_RAIL_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'launch-costs', ', '.join(f'{k} {v}' for k, v in d['costs'].items())); _admin_save(ad)
    return d['costs']


class LaunchTabIn(BaseModel):
    rails: list = ['feeless', 'pump']
    devBuy: bool = True
    maxDevBuySol: float = 5
    banner: bool = True


@app.put('/api/reputation/admin/launch-tab')
async def launch_tab_set(request: Request, p: LaunchTabIn):
    """Owner picks what the public Launch tab offers. Owners themselves always see every rail."""
    me = _require_owner(request)
    d = _json_load(LAUNCH_RAIL_PATH, {}); d['tab'] = launch_meta.clean_tab(p.model_dump()); _json_save(LAUNCH_RAIL_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'launch-tab', f"rails {','.join(d['tab']['rails'])} · first buy {'≤ ' + str(d['tab']['maxDevBuySol']) + ' SOL' if d['tab']['devBuy'] else 'off'}"); _admin_save(ad)
    return d['tab']


@app.get('/api/reputation/launch-check/{mint}')
async def launch_check(mint: str, rail: str = 'pump'):
    """After a launch: is the coin really live? Mint on-chain (RPC), listed on pump.fun (pump rail), seen by DexScreener."""
    if not _re.match(_B58, mint):
        raise HTTPException(400, 'Bad address.')

    async def chain():
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                return bool(((await _rpc(http, 'getAccountInfo', [mint, {'encoding': 'base64', 'commitment': 'confirmed'}])) or {}).get('value'))
        except Exception:
            return None

    async def pump():
        if rail != 'pump':
            return None
        try:
            async with httpx.AsyncClient(timeout=8, headers={'User-Agent': 'Mozilla/5.0'}) as http:
                r = await http.get(f'https://frontend-api-v3.pump.fun/coins/{mint}')
            return r.status_code == 200 and (r.json() or {}).get('mint') == mint
        except Exception:
            return None

    async def dex():
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                r = await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{mint}')
            return bool((r.json() or {}).get('pairs'))
        except Exception:
            return None
    on_chain, on_pump, on_dex = await asyncio.gather(chain(), pump(), dex())
    return {'mint': mint, 'rail': rail, 'onChain': on_chain, 'onPump': on_pump, 'onDex': on_dex,
            'pumpUrl': f'https://pump.fun/coin/{mint}' if rail == 'pump' else None}


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
    banner: str = ''


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
    meta = launch_meta.token_metadata(site, name, symbol, p.description, p.image, p.banner, p.website, p.twitter, p.telegram)
    TOKEN_META_DIR.mkdir(parents=True, exist_ok=True)
    mid = uuid.uuid4().hex
    (TOKEN_META_DIR / f'{mid}.json').write_text(json.dumps(meta))
    return {'uri': f'{site}/api/reputation/token-meta/{mid}.json'}


# ---- Coin profiles: claimed by the coin's creator wallet (or an admin) — never auto-created -------
COIN_PROFILES_PATH = DATA_DIR / 'coin_profiles.json'


class CoinProfileIn(BaseModel):
    address: str
    session: str
    mint: str
    description: str = ''
    bannerUrl: str = ''
    website: str = ''
    twitter: str = ''
    telegram: str = ''


@app.get('/api/reputation/coin-profile/{mint}')
async def coin_profile_get(mint: str):
    return _json_load(COIN_PROFILES_PATH, {}).get(mint) or {}


@app.post('/api/reputation/coin-profile')
async def coin_profile_set(p: CoinProfileIn):
    me = primary_of(_session_or_401(p.address, p.session))
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.mint):
        raise HTTPException(400, 'Bad coin address.')
    creator = await resolve_creator('solana', p.mint)
    is_admin = me in {primary_of(w) for w in _admin_wallets()}
    if not is_admin and (not creator or primary_of(creator) != me):
        raise HTTPException(403, "Only this coin's creator wallet can claim and edit its profile.")
    link = lambda v: v.strip()[:200] if v.strip().startswith('https://') else ''
    banner = p.bannerUrl.strip()[:300]
    rec = {'description': p.description.strip()[:600], 'bannerUrl': banner if banner.startswith(('https://', '/api/reputation/uploads/')) else '',
           'website': link(p.website), 'twitter': link(p.twitter), 'telegram': link(p.telegram), 'claimedBy': me, 'updatedAt': time.time()}
    async with _admin_lock:
        d = _json_load(COIN_PROFILES_PATH, {}); d[p.mint] = rec; _json_save(COIN_PROFILES_PATH, d)
    return rec


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
    if primary_of(me) not in {primary_of(w) for w in set(_owner_wallets()) | set(_admin_wallets())}:   # owner + admins launch freely
        tab = launch_meta.clean_tab(_json_load(LAUNCH_RAIL_PATH, {}).get('tab') or launch_meta.TAB_DEFAULT)
        if 'pump' not in tab['rails']:
            raise HTTPException(403, 'Pump.fun launches are switched off on FEELESS right now.')
        if not launch_meta.dev_buy_ok(tab, p.devBuySol):
            raise HTTPException(400, f"First buy is capped at {tab['maxDevBuySol']} SOL." if tab['devBuy'] else 'First buys are switched off right now.')
    m = _re.match(r'^/api/reputation/uploads/([a-f0-9]{32}\.(png|jpg|webp|gif))$', launch_meta.upload_path(p.image))
    if not m or not (UPLOAD_DIR / m.group(1)).exists():
        raise HTTPException(400, 'Upload the coin image first.')
    img = (UPLOAD_DIR / m.group(1)).read_bytes()
    mime = {'png': 'image/png', 'jpg': 'image/jpeg', 'webp': 'image/webp', 'gif': 'image/gif'}[m.group(2)]
    form = launch_meta.pump_form(p.name, p.symbol, p.description, p.website, p.twitter, p.telegram)
    costs = launch_meta.clean_costs(_json_load(LAUNCH_RAIL_PATH, {}).get('costs'))   # HQ › Launch › Costs
    async with httpx.AsyncClient(timeout=30, headers={'User-Agent': 'Mozilla/5.0'}) as http:
        r = await http.post('https://pump.fun/api/ipfs', data=form, files={'file': (m.group(1), img, mime)})
        if r.status_code != 200:
            raise HTTPException(502, 'Pump.fun metadata upload failed — try again.')
        uri = (r.json() or {}).get('metadataUri')
        t = await http.post('https://pumpportal.fun/api/trade-local', json={'publicKey': p.address, 'action': 'create', 'tokenMetadata': {'name': form['name'], 'symbol': form['symbol'], 'uri': uri},
                                                                           'mint': p.mint, 'denominatedInSol': 'true', 'amount': p.devBuySol,
                                                                           # the dev buy is the very first buy on a brand-new curve in the same tx: nobody can move
                                                                           # the price in between, so 1% slippage is plenty (10% made wallets preview a 10% bigger spend)
                                                                           'slippage': costs['pumpSlippagePct'], 'priorityFee': costs['pumpPriorityFeeSol'], 'pool': 'pump'})
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
    """Record a pool created from the HQ. Verified on-chain: succeeded, signed by this admin."""
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
LOGO_OVERRIDE_PATH = DATA_DIR / 'logo_overrides.json'


class LogoIn(BaseModel):
    mint: str
    image: str = ''       # an upload path; empty clears the override


@app.post('/api/reputation/admin/token-logo')
async def admin_token_logo(request: Request, p: LogoIn):
    """Owner sets a coin's logo by hand (FEELESS coins first). Clears the cached lookup so it shows everywhere now."""
    me = _require_admin(request)
    if not _re.match(_B58, p.mint):
        raise HTTPException(400, 'Solana mint required.')
    if p.image and not _re.match(r'^/api/reputation/uploads/[a-f0-9]{32}\.(png|jpg|webp|gif)$', p.image):
        raise HTTPException(400, 'Upload the image first.')
    d = _json_load(LOGO_OVERRIDE_PATH, {})
    if p.image:
        d[p.mint] = p.image
    else:
        d.pop(p.mint, None)
    _json_save(LOGO_OVERRIDE_PATH, d)
    for f in LOGO_DIR.glob(f'{p.mint}.*'):
        f.unlink(missing_ok=True)
    _logo_miss.pop(p.mint, None)
    ad = _admin_load(); _audit(ad, me, 'token-logo', f"{p.mint[:6]}… {'set' if p.image else 'cleared'}"); _admin_save(ad)
    return {'ok': True, 'mint': p.mint, 'image': p.image}
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
    over = _json_load(LOGO_OVERRIDE_PATH, {}).get(mint)
    if over and (UPLOAD_DIR / over.rsplit('/', 1)[-1]).exists():   # owner-set logo (HQ) always wins
        return FileResponse(UPLOAD_DIR / over.rsplit('/', 1)[-1], headers={'Cache-Control': 'public, max-age=300'})
    if hit:
        return FileResponse(hit, headers=headers)
    if time.time() - _logo_miss.get(mint, 0) < 600:
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
            try:   # on-chain Metaplex metadata: works on any RPC (getAsset below is Helius-only)
                acct = await _rpc(http, 'getAccountInfo', [coin_meta.metadata_pda(mint), {'encoding': 'base64'}])
                data = (((acct or {}).get('value') or {}).get('data') or [None])[0]
                if data:
                    uri = coin_meta.parse_metadata(data).get('uri')
                    if uri:
                        meta = await _fetch_first(http, _ipfs_variants(uri), want_json=True)
                        cands.append((meta or {}).get('image'))
            except Exception:
                pass
            if mint.endswith('pump'):
                try:
                    d = (await http.get(f'https://frontend-api-v3.pump.fun/coins/{mint}', timeout=8)).json()
                    cands.append((d or {}).get('image_uri'))
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


# ---- HQ: chart & data-provider latency --------------------------------------------------
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
                        feeless_post('feeless-updates', f"✅ {r['name']} recovered ({r['ms']} ms).")
                    _latency_bad.pop(r['name'], None)
                    continue
                st = _latency_bad.setdefault(r['name'], {'since': time.time()})
                if not st.get('posted') and time.time() - st['since'] >= 300:
                    st['posted'] = True
                    why = r['note'] or 'down' if not r['ok'] else f"{r['ms']} ms"
                    feeless_post('feeless-updates', f"⚠️ {r['name']} ({r['role']}) degraded for 5+ min: {why}. Fallbacks are serving; we're on it.")
        except Exception as exc:
            print('latency alarm error', exc)


@app.on_event('startup')
async def _start_latency_alarm():
    asyncio.create_task(_latency_alarm())


# ---- HQ: marketing — 3-day top movers + top/bottom reputations, ready to post -------------
MARKETING_PATH = DATA_DIR / 'marketing.json'
_movers_cache = {'at': 0, 'rows': []}


async def _three_day_movers():
    """% move over the last 72h for the globe's most-traded coins, from FEELESS's own hourly candles."""
    if time.time() - _movers_cache['at'] < 1800:
        return _movers_cache['rows']
    toks = sorted(((_globe_cache['data'] or {}).get('tokens') or []), key=lambda t: -(t.get('volume24h') or 0))[:40]
    sem = asyncio.Semaphore(6)
    async with httpx.AsyncClient(timeout=15) as http:
        async def one(t):
            async with sem:
                try:
                    c = (await http.get(f"http://127.0.0.1:5099/api/candles/{t['chain']}/{t['pairAddress']}", params={'interval': '1h'})).json().get('candles') or []
                except Exception:
                    return None
            cutoff = time.time() - 72 * 3600
            past = next((x for x in c if x[0] >= cutoff), None)
            if not past or not c or past[4] <= 0:
                return None
            return {**{k: t.get(k) for k in ('chain', 'symbol', 'name', 'imageUrl', 'pairAddress', 'marketCap')}, 'move3d': round((c[-1][4] / past[4] - 1) * 100, 1)}
        rows = [r for r in await asyncio.gather(*(one(t) for t in toks)) if r]
    rows.sort(key=lambda r: -r['move3d'])
    _movers_cache.update(at=time.time(), rows=rows)
    return rows


def _post_text(r):
    up = r['move3d'] >= 0
    return (f"${r['symbol']} {'+' if up else ''}{r['move3d']}% in 3 days on {r['chain'].title()} {'🚀' if up else '🩸'}\n"
            f"Chart it, chat it and trade it fee-free on FEELESS — every call on the record.\n#{r['chain']} #memecoins #FEELESS")


@app.get('/api/reputation/admin/marketing')
async def admin_marketing(request: Request):
    _require_admin(request)
    rows = await _three_day_movers()
    d = _json_load(MARKETING_PATH, {'snapshots': []})
    # A dated snapshot every 3 days, kept, so past windows stay reviewable.
    if rows and (not d['snapshots'] or time.time() - d['snapshots'][-1]['at'] >= 3 * 86400):
        d['snapshots'] = (d['snapshots'] + [{'at': time.time(), 'up': rows[:10], 'down': rows[::-1][:10]}])[-60:]
        _json_save(MARKETING_PATH, d)
    keys = ('chain', 'address', 'score', 'badge', 'tokenCount', 'bigWinners', 'dumpedCount', 'ruggedCount')
    good, bad = [[{k: r.get(k) for k in keys} for r in (await leaderboard(chain=None, view=v))['rows'][:10]] for v in ('trusted', 'flagged')]
    return {'movers': {'up': [{**r, 'post': _post_text(r)} for r in rows[:10]], 'down': [{**r, 'post': _post_text(r)} for r in rows[::-1][:10] if r['move3d'] < 0]},
            'reps': {'good': [{**r, 'post': f"🟢 Trusted creator {r['address'][:4]}…{r['address'][-4:]} — {r['bigWinners']} big winner(s), {r['dumpedCount']} dumps. Receipts on FEELESS."} for r in good],
                     'bad': [{**r, 'post': f"🚩 Flagged creator {r['address'][:4]}…{r['address'][-4:]} — {r['ruggedCount']} rug(s), {r['dumpedCount']} dumps. Check any wallet before you ape: FEELESS."} for r in bad]},
            'snapshots': [{'at': x['at'], 'top': (x['up'][:1] or [{}])[0].get('symbol')} for x in d['snapshots'][-20:]]}


# ---- Circle developer-controlled wallets (creator/owner only) -------------------------------------
# Proxies to the localhost Circle sidecar. Only owner wallets may list or create; keys never leave .env.
class CircleWalletIn(BaseModel):
    blockchain: str
    name: str = 'Creator wallet'


CIRCLE_DIR = Path(__file__).resolve().parents[1] / 'circle'
_circle_boot = {'at': 0.0}


async def _circle_start() -> bool:
    """Start the Circle sidecar if it's installed and keyed. At most one attempt per 20s; never raises."""
    if time.time() - _circle_boot['at'] < 20 or not (CIRCLE_DIR / 'node_modules').exists() or not os.environ.get('CIRCLE_API_KEY'):
        return False
    _circle_boot['at'] = time.time()
    try:
        import subprocess
        subprocess.Popen(['node', 'server.mjs'], cwd=str(CIRCLE_DIR), stdout=open('/tmp/feeless-circle.log', 'ab'), stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True)
    except Exception:
        return False
    await asyncio.sleep(1.5)
    return True


async def _circle(method, path, body=None):
    r = None
    for attempt in range(3):   # sidecar down → start it (owner is signed in: every caller is owner-gated) and retry
        try:
            async with httpx.AsyncClient(timeout=30) as http:
                r = await http.request(method, f'http://127.0.0.1:5111{path}', json=body)
            break
        except httpx.ConnectError:
            if attempt == 2 or not (await _circle_start() or attempt == 1):
                raise HTTPException(503, 'Circle wallet service is not running and could not be started (check CIRCLE_API_KEY and circle/node_modules).')
            await asyncio.sleep(1.5)
        except httpx.HTTPError:
            raise HTTPException(503, 'Circle wallet service did not answer.')
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
    return {'wallets': await _circle_wallets_live()}


@app.post('/api/reputation/admin/circle/wallets')
async def circle_create_wallet(request: Request, p: CircleWalletIn):
    me = _require_owner(request)
    out = await _circle('POST', '/wallets', {'blockchain': p.blockchain, 'name': p.name[:40]})
    ad = _admin_load(); _audit(ad, me, 'circle-wallet', f"{p.blockchain} {(out.get('wallet') or {}).get('address', '')}"); _admin_save(ad)
    return out


# ================================================================================================
# SEASON BADGE RESERVE POOL: tiers earn weighted shares of the Fee Reserve wallet, owner-signed payouts
# ================================================================================================
async def _reserve_plan(s, d, bal=None):
    wallet = s.get('reserveWallet') or ''
    pool = bal
    if wallet and bal is None:
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                pool = ((await _rpc(http, 'getBalance', [wallet])) or {}).get('value', 0) / 1e9
        except Exception:
            pool = None
    blocked = _block_load()['wallets']
    holders = [{'address': a, 'score': r['score'], 'tier': _tier(r['score'])['tier']}
               for a, r in (d['scores'].get(s['id']) or {}).items() if not _is_blocked(blocked.get(a))]
    plan = reserve_pool.payout_plan(pool or 0, float(s.get('badgeRewardPct') or 0), holders, excluded=frozenset(_protected_wallets()))
    return {**plan, 'season': {k: s.get(k) for k in ('id', 'name', 'start', 'end', 'accent', 'reserveWallet', 'badgeRewardPct')},
            'assigned': bool(wallet), 'balanceKnown': pool is not None, 'ended': s['end'] <= time.time(),
            'payout': (d.get('reservePayouts') or {}).get(s['id'])}


@app.get('/api/reputation/admin/reserve/{sid}')
async def admin_reserve_plan(request: Request, sid: str):
    _require_admin(request)
    d = _seasons(); s = next((x for x in d['seasons'] if x['id'] == sid), None)
    if not s:
        raise HTTPException(404, 'Season not found.')
    return await _reserve_plan(s, d)


class ReservePaid(BaseModel):
    sigs: list[str] = Field(min_length=1, max_length=40)
    perKey: dict = {}           # badge pools: the plan's per-holder amount per badge key (scaled to what moved)
    plannedSol: float = 0


@app.post('/api/reputation/admin/reserve/{sid}/paid')
async def admin_reserve_paid(request: Request, sid: str, p: ReservePaid):
    """Record a payout the reserve wallet signed. Every signature must be on-chain, succeeded and signed by the reserve wallet."""
    admin = _require_admin(request)
    d = _seasons(); s = next((x for x in d['seasons'] if x['id'] == sid), None)
    if not s:
        raise HTTPException(404, 'Season not found.')
    if (d.get('reservePayouts') or {}).get(sid):
        raise HTTPException(409, 'This season was already paid out.')
    wallet = s.get('reserveWallet')
    if not wallet:
        raise HTTPException(400, 'Assign a Fee Reserve wallet to this season first.')
    if not all(_re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', x) for x in p.sigs):
        raise HTTPException(400, 'Bad transaction signature.')
    plan = await _reserve_plan(s, d)
    async with httpx.AsyncClient(timeout=20) as http:
        txs = await asyncio.gather(*(_rpc(http, 'getTransaction', [x, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}]) for x in p.sigs))
    for sig, tx in zip(p.sigs, txs):
        if not tx or (tx.get('meta') or {}).get('err'):
            raise HTTPException(400, f'Transaction {sig[:8]}… is not on-chain or failed.')
        if wallet not in [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]:
            raise HTTPException(400, 'Payout must be signed by the season Fee Reserve wallet.')
    paid = {}  # record what actually moved on-chain, not what was planned
    for tx in txs:
        for ix in tx['transaction']['message'].get('instructions') or []:
            info = (ix.get('parsed') or {}).get('info') or {}
            if ix.get('program') == 'system' and (ix.get('parsed') or {}).get('type') == 'transfer' and info.get('source') == wallet:
                paid[info['destination']] = round(paid.get(info['destination'], 0) + info['lamports'] / 1e9, 9)
    if not paid:
        raise HTTPException(400, 'No SOL transfers from the reserve wallet in those transactions.')
    tiers = {r['address']: r['tier'] for r in plan['rows']}
    d = _seasons()
    d.setdefault('reservePayouts', {})[sid] = {'sigs': p.sigs, 'at': time.time(), 'by': admin, 'potSol': plan['potSol'],
                                               'rows': [{'address': a, 'tier': tiers.get(a, ''), 'sol': v} for a, v in paid.items()]}
    _json_save(SEASONS_PATH, d)
    col = _json_load(COLLECTION_PATH, {})
    for a, items in col.items():
        for it in items:
            if it.get('id') == f'{sid}:season' and a in paid:
                it['rewardStatus'] = 'paid'; it['rewardSol'] = paid[a]; it['rewardSig'] = p.sigs[0]
    _json_save(COLLECTION_PATH, col)
    total = round(sum(paid.values()), 6)
    ad = _admin_load(); _audit(ad, admin, 'reserve-payout', f"{sid} {total} SOL to {len(paid)}"); _admin_save(ad)
    return {'ok': True, 'paidSol': total, 'wallets': len(paid)}


class CirclePayIn(BaseModel):
    confirm: str = ''          # must read "PAY <total SOL>" exactly


_circle_pay_lock = asyncio.Lock()


async def _circle_pay(wallet_addr: str, rows: list, scope: str, confirm: str) -> list:
    """Pay each row from a Circle wallet (Circle signs server-side with the entity secret). Owner-only callers.
    Deterministic idempotency keys: a retry or double click re-sends nothing that already went out."""
    want = reserve_pool.circle_confirm_phrase(rows)
    if confirm.strip() != want:
        raise HTTPException(400, f'Type "{want}" to confirm.')
    ws = (await _circle('GET', '/wallets')).get('wallets') or []
    w = next((x for x in ws if x.get('address') == wallet_addr), None)
    if not w:
        raise HTTPException(400, 'This wallet is not one of your Circle wallets. Connect it in Phantom to pay instead.')
    if w.get('blockchain') != 'SOL':
        raise HTTPException(400, f"That Circle wallet is on {w.get('blockchain')}, not Solana mainnet.")
    tok = reserve_pool.circle_sol_token(w)
    bal = next((float(b.get('amount') or 0) for b in w.get('balances') or [] if b.get('tokenId') == tok), 0.0)
    total = round(sum(float(r['sol']) for r in rows), 6)
    if not tok or bal < total:
        raise HTTPException(400, f'The Circle wallet holds {bal} SOL; this payout needs {total} SOL plus network fees.')
    sem = asyncio.Semaphore(4)

    async def one(r):
        async with sem:
            try:
                out = await _circle('POST', '/transfer', {'walletId': w['id'], 'tokenId': tok, 'to': r['address'], 'amount': reserve_pool.circle_amount(r['sol']),
                                                          'idempotencyKey': reserve_pool.circle_idem(scope, r['address'], float(r['sol']))})
                return {**r, 'circleTx': out.get('id'), 'state': out.get('state') or 'INITIATED'}
            except HTTPException as e:
                return {**r, 'error': str(e.detail)[:160]}
    return list(await asyncio.gather(*(one(r) for r in rows)))


@app.post('/api/reputation/admin/reserve/{sid}/pay-circle')
async def admin_reserve_pay_circle(request: Request, sid: str, p: CirclePayIn):
    """Season reserve held in a Circle wallet: Circle sends each badge holder's share. Retries only the rows that failed."""
    me = _require_owner(request)
    async with _circle_pay_lock:
        d = _seasons(); s = next((x for x in d['seasons'] if x['id'] == sid), None)
        if not s or not s.get('reserveWallet'):
            raise HTTPException(404, 'Season or reserve wallet not found.')
        prev = (d.get('reservePayouts') or {}).get(sid)
        if prev and prev.get('via') != 'circle':
            raise HTTPException(409, 'This season was already paid out.')
        if prev:
            todo = prev.get('failed') or []
        else:
            plan = await _reserve_plan(s, d)
            todo = [{'address': r['address'], 'tier': r['tier'], 'sol': r['sol']} for r in plan['rows']]
        todo = [{k: r[k] for k in ('address', 'tier', 'sol') if k in r} for r in todo]
        if not todo:
            raise HTTPException(409, 'Nothing left to pay for this season.')
        res = await _circle_pay(s['reserveWallet'], todo, f'reserve:{sid}', p.confirm)
        ok, bad = [r for r in res if r.get('circleTx')], [r for r in res if not r.get('circleTx')]
        d = _seasons()
        rec = d.setdefault('reservePayouts', {}).get(sid) or {'via': 'circle', 'sigs': [], 'at': time.time(), 'by': me, 'rows': []}
        rec['rows'] = (rec.get('rows') or []) + ok; rec['failed'] = bad; rec['updatedAt'] = time.time()
        if ok or prev:
            d['reservePayouts'][sid] = rec
            _json_save(SEASONS_PATH, d)
        if ok:
            col = _json_load(COLLECTION_PATH, {}); sent = {r['address']: r for r in ok}
            for a, items in col.items():
                for it in items:
                    if it.get('id') == f'{sid}:season' and a in sent:
                        it['rewardStatus'] = 'paid'; it['rewardSol'] = sent[a]['sol']; it['rewardCircleTx'] = sent[a]['circleTx']
            _json_save(COLLECTION_PATH, col)
        ad = _admin_load(); _audit(ad, me, 'reserve-payout-circle', f"{sid} {round(sum(r['sol'] for r in ok), 6)} SOL to {len(ok)}, {len(bad)} failed"); _admin_save(ad)
    return {'ok': not bad, 'paidSol': round(sum(r['sol'] for r in ok), 6), 'wallets': len(ok), 'failed': bad}


@app.post('/api/reputation/admin/badge-pools/{pid}/pay-circle')
async def admin_badge_pool_pay_circle(request: Request, pid: str, p: CirclePayIn):
    """Badge pool held in a Circle wallet: Circle sends each holder's share of the current plan."""
    me = _require_owner(request)
    async with _circle_pay_lock:
        pool = next((x for x in _pools()['pools'] if x['id'] == pid), None)
        if not pool:
            raise HTTPException(404, 'Pool not found.')
        plan = await _pool_plan(pool)
        if (plan.get('cooldownLeft') or 0) > 0:
            raise HTTPException(409, 'This pool was paid within the last hour.')
        rows = [{'address': r['address'], 'sol': r['sol']} for r in plan['rows'] if r.get('sol', 0) > 0]
        if not rows:
            raise HTTPException(400, 'Nothing to pay from this pool yet.')
        res = await _circle_pay(pool['wallet'], rows, f"pool:{pid}:{len(pool.get('payouts') or [])}", p.confirm)
        ok, bad = [r for r in res if r.get('circleTx')], [r for r in res if not r.get('circleTx')]
        d = _pools(); pool = next((x for x in d['pools'] if x['id'] == pid), None)
        if ok and pool:
            scale = sum(r['sol'] for r in ok) / plan['paidSol'] if plan.get('paidSol') else 0
            pool.setdefault('payouts', []).append({'via': 'circle', 'sigs': [], 'at': time.time(), 'by': me, 'rows': ok, 'failed': bad,
                                                   'perKey': {k: int(v * scale * 1e6) / 1e6 for k, v in (plan.get('perKey') or {}).items()},
                                                   'totalSol': round(sum(r['sol'] for r in ok), 6)})
            pool['payouts'] = pool['payouts'][-50:]
            _json_save(BADGE_POOLS_PATH, d)
        ad = _admin_load(); _audit(ad, me, 'badge-pool-payout-circle', f"{pid} {round(sum(r['sol'] for r in ok), 6)} SOL to {len(ok)}, {len(bad)} failed"); _admin_save(ad)
    return {'ok': not bad, 'paidSol': round(sum(r['sol'] for r in ok), 6), 'wallets': len(ok), 'failed': bad}


_reserve_pub_cache = {}


@app.get('/api/reputation/season/reserve')
async def season_reserve(address: str = ''):
    """Public: the live season's reserve pot and this wallet's projected share."""
    d = _seasons(); s = _current_season(d)
    if not s or not s.get('reserveWallet') or not float(s.get('badgeRewardPct') or 0):
        return {'active': False}
    hit = _reserve_pub_cache.get(s['id'])
    if not hit or time.time() - hit[0] > 60:
        hit = (time.time(), await _reserve_plan(s, d)); _reserve_pub_cache[s['id']] = hit
    plan = hit[1]
    me = reserve_pool.wallet_share(plan, primary_of(address)) if address else None
    return {'active': True, 'season': plan['season']['name'], 'pct': plan['pct'], 'potSol': plan['potSol'], 'wallets': len(plan['rows']),
            'weights': plan['weights'], 'me': me}


# ---- Badge pools: any badge (season tier or custom award) earns a weighted cut of any wallet the owner picks ----
BADGE_POOLS_PATH = DATA_DIR / 'badge_pools.json'
POOL_COOLDOWN = 3600
_ADDR_RE = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'


class BadgePoolIn(BaseModel):
    id: str = ''
    name: str = Field(min_length=2, max_length=40)
    wallet: str
    pct: float = Field(ge=0, le=100)
    seasonId: str = ''
    weights: dict = Field(default_factory=dict)
    mode: str = 'pct'           # 'pct': each badge gets a fixed % of the pot · 'weight': legacy weighted split
    fixed: dict = Field(default_factory=dict)   # 'badge:<id>' | 'tier:<Tier>' -> SOL each holder gets, paid before the % pot


def _pools():
    return _json_load(BADGE_POOLS_PATH, {'pools': []})


def _pool_inputs(pool):
    """(holders, allocated %) — blocklisted and FEELESS wallets never hold a share."""
    tiers = {}
    if pool.get('seasonId'):
        tiers = {a: _tier(r['score'])['tier'] for a, r in (_seasons()['scores'].get(pool['seasonId']) or {}).items()}
    blocked, safe = _block_load()['wallets'], _protected_wallets() | {pool['wallet']}
    tiers = {a: t for a, t in tiers.items() if a not in safe and not _is_blocked(blocked.get(a))}
    badges = {a: list(items) for a, items in (_admin_load().get('badges') or {}).items() if items and a not in safe and not _is_blocked(blocked.get(a))}
    for a, (at, rec) in list(_badge_cache.items()):   # built-in badges (creator, caller, holder…) for wallets scored in the last day
        if time.time() - at < 86400 and a not in safe and not _is_blocked(blocked.get(a)):
            badges.setdefault(a, []).extend(b['id'] for b in (rec or {}).get('badges', []) if b.get('id') and b['id'] not in badges.get(a, []))
    pool['_tiers'], pool['_badges'] = tiers, badges
    if pool.get('mode', 'weight') == 'pct':
        return reserve_pool.pct_holders(pool.get('weights') or {}, tiers, badges)
    return reserve_pool.pool_holders(pool.get('weights') or {}, tiers, badges), 100.0


async def _pool_plan(pool, bal=None):
    known = bal is not None
    if bal is None:
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                bal = ((await _rpc(http, 'getBalance', [pool['wallet']])) or {}).get('value', 0) / 1e9
            known = True
        except Exception:
            bal, known = 0, False
    holders, allocated = _pool_inputs(pool)
    counts = badge_cards.key_counts(pool.get('_tiers'), pool.get('_badges'))
    # Fixed SOL-each badges are paid first (never more than the wallet can spare); the % pot comes from what's left.
    fixed, fixed_total = reserve_pool.fixed_rows(pool.get('fixed') or {}, pool.pop('_tiers', {}), pool.pop('_badges', {}), max(0.0, bal - reserve_pool.KEEP_SOL))
    rest = bal - fixed_total
    plan = reserve_pool.payout_plan(rest, pool['pct'] * allocated / 100, holders, excluded=frozenset(_protected_wallets()) | {pool['wallet']})
    by = {r['address']: r for r in plan['rows']}
    for a, v in fixed.items():
        if a in by:
            by[a]['sol'] = round(by[a]['sol'] + v, 6); by[a]['fixedSol'] = v
        elif v >= reserve_pool.DUST_SOL:
            plan['rows'].append({'address': a, 'tier': 'Recruit', 'score': 0, 'weight': 0, 'sharePct': 0, 'sol': v, 'fixedSol': v, 'why': 'fixed badge reward'})
    # What ONE holder of each badge / tier key gets from this payout: stored on the payout, summed on card backs.
    want = sum(float(v or 0) * counts.get(k, 0) for k, v in (pool.get('fixed') or {}).items())
    pct_mode = pool.get('mode', 'weight') == 'pct'
    plan['perKey'] = badge_cards.per_key_each('pct' if pct_mode else 'weight', pool.get('weights') or {}, pool.get('fixed') or {}, counts,
                                              (plan['potSol'] * 100 / allocated if allocated else 0) if pct_mode else plan['potSol'], plan['totalWeight'],
                                              fixed_total / want if want else 1.0)
    plan['fixedSol'] = fixed_total; plan['potSol'] = round(plan['potSol'] + fixed_total, 6)
    plan['paidSol'] = round(sum(r['sol'] for r in plan['rows']), 6)
    plan['allocatedPct'] = allocated
    last = (pool.get('payouts') or [None])[-1]
    return {**plan, 'pool': {k: v for k, v in pool.items() if k != 'payouts'}, 'balanceKnown': known, 'lastPayout': last,
            'cooldownLeft': max(0, round(POOL_COOLDOWN - (time.time() - last['at']))) if last else 0}


@app.get('/api/reputation/admin/badge-pools')
async def admin_badge_pools(request: Request):
    _require_admin(request)
    ad = _admin_load(); seen = {}
    for items in (ad.get('badges') or {}).values():
        for b in items.values():
            x = seen.setdefault(b['id'], {'id': b['id'], 'label': b.get('label'), 'icon': b.get('icon'), 'count': 0}); x['count'] += 1
    return {'pools': [{**p, 'payouts': (p.get('payouts') or [])[-5:]} for p in _pools()['pools']], 'badges': sorted(seen.values(), key=lambda b: -b['count']),
            'tiers': [t for t, _ in SEASON_TIERS], 'seasons': [{'id': s['id'], 'name': s['name']} for s in _seasons()['seasons']]}


@app.post('/api/reputation/admin/badge-pools')
async def admin_badge_pool_save(request: Request, p: BadgePoolIn):
    admin = _require_admin(request)
    if not _re.match(_ADDR_RE, p.wallet):
        raise HTTPException(400, 'Pool wallet must be a Solana address.')
    weights = {}
    for k, v in list(p.weights.items())[:60]:
        if not _re.match(r'^(tier|badge):[A-Za-z0-9_-]{1,40}$', str(k)):
            raise HTTPException(400, f'Bad weight key {k}.')
        try:
            w = float(v)
        except (TypeError, ValueError):
            raise HTTPException(400, f'Weight for {k} must be a number.')
        if not 0 <= w <= 100:
            raise HTTPException(400, 'Each badge share is 0–100.')
        if w:
            weights[k] = w
    if p.mode not in ('pct', 'weight'):
        raise HTTPException(400, 'Unknown pool mode.')
    if p.mode == 'pct' and sum(weights.values()) > 100.0001:
        raise HTTPException(400, f'Badge shares add up to {round(sum(weights.values()), 2)}% — keep the total at 100% or less.')
    d = _pools()
    pid = p.id or f"pool{int(time.time())}"
    prev = next((x for x in d['pools'] if x['id'] == pid), {})
    fixed = {}
    for k, v in list(p.fixed.items())[:60]:
        if not _re.match(r'^(tier|badge):[A-Za-z0-9_-]{1,40}$', str(k)):
            raise HTTPException(400, f'Bad key {k}.')
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise HTTPException(400, f'SOL each for {k} must be a number.')
        if not 0 <= v <= 100:
            raise HTTPException(400, 'SOL each must be 0–100.')
        if v:
            fixed[k] = v
    rec = {**prev, 'id': pid, 'name': p.name, 'wallet': p.wallet, 'pct': p.pct, 'seasonId': p.seasonId, 'weights': weights, 'mode': p.mode, 'fixed': fixed}
    d['pools'] = [x for x in d['pools'] if x['id'] != pid] + [rec]
    _json_save(BADGE_POOLS_PATH, d)
    ad = _admin_load(); _audit(ad, admin, 'badge-pool', f'{p.name} {p.pct}% of {p.wallet[:6]}'); _admin_save(ad)
    return {'ok': True, 'pool': rec}


@app.delete('/api/reputation/admin/badge-pools/{pid}')
async def admin_badge_pool_delete(request: Request, pid: str):
    _require_admin(request)
    d = _pools(); d['pools'] = [x for x in d['pools'] if x['id'] != pid]; _json_save(BADGE_POOLS_PATH, d)
    return {'ok': True}


@app.get('/api/reputation/admin/badge-pools/{pid}/plan')
async def admin_badge_pool_plan(request: Request, pid: str):
    _require_admin(request)
    pool = next((x for x in _pools()['pools'] if x['id'] == pid), None)
    if not pool:
        raise HTTPException(404, 'Pool not found.')
    return await _pool_plan(pool)


@app.post('/api/reputation/admin/badge-pools/{pid}/paid')
async def admin_badge_pool_paid(request: Request, pid: str, p: ReservePaid):
    admin = _require_admin(request)
    d = _pools(); pool = next((x for x in d['pools'] if x['id'] == pid), None)
    if not pool:
        raise HTTPException(404, 'Pool not found.')
    used = {s for x in d['pools'] for po in x.get('payouts') or [] for s in po['sigs']}
    if used & set(p.sigs):
        raise HTTPException(409, 'Those transactions were already recorded.')
    if not all(_re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', x) for x in p.sigs):
        raise HTTPException(400, 'Bad transaction signature.')
    async with httpx.AsyncClient(timeout=20) as http:
        txs = await asyncio.gather(*(_rpc(http, 'getTransaction', [x, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}]) for x in p.sigs))
    paid = {}
    for sig, tx in zip(p.sigs, txs):
        if not tx or (tx.get('meta') or {}).get('err'):
            raise HTTPException(400, f'Transaction {sig[:8]}… is not on-chain or failed.')
        if pool['wallet'] not in [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]:
            raise HTTPException(400, 'Payout must be signed by the pool wallet.')
        for ix in tx['transaction']['message'].get('instructions') or []:
            info = (ix.get('parsed') or {}).get('info') or {}
            if ix.get('program') == 'system' and (ix.get('parsed') or {}).get('type') == 'transfer' and info.get('source') == pool['wallet']:
                paid[info['destination']] = round(paid.get(info['destination'], 0) + info['lamports'] / 1e9, 9)
    if not paid:
        raise HTTPException(400, 'No SOL transfers from the pool wallet in those transactions.')
    moved = sum(paid.values()); scale = min(1.0, moved / p.plannedSol) if p.plannedSol > 0 else 0
    per_key = {str(k)[:60]: int(float(v) * scale * 1e6) / 1e6 for k, v in list((p.perKey or {}).items())[:200] if isinstance(v, (int, float)) and v > 0}
    pool.setdefault('payouts', []).append({'sigs': p.sigs, 'at': time.time(), 'by': admin, 'rows': [{'address': a, 'sol': v} for a, v in paid.items()], 'perKey': per_key,
                                           'totalSol': round(sum(paid.values()), 6)})
    pool['payouts'] = pool['payouts'][-50:]
    _json_save(BADGE_POOLS_PATH, d)
    ad = _admin_load(); _audit(ad, admin, 'badge-pool-payout', f"{pool['name']} {round(sum(paid.values()), 6)} SOL to {len(paid)}"); _admin_save(ad)
    return {'ok': True, 'paidSol': round(sum(paid.values()), 6), 'wallets': len(paid)}


_pool_pub_cache = {}


@app.get('/api/reputation/badge-pools')
async def badge_pools_public(address: str = ''):
    """Public: every live badge pool, its pot and what this wallet's badges earn from it."""
    hit = _pool_pub_cache.get('all')
    if not hit or time.time() - hit[0] > 60:
        plans = await asyncio.gather(*(_pool_plan(p) for p in _pools()['pools'] if p.get('pct')))
        hit = (time.time(), plans); _pool_pub_cache['all'] = hit
    a = primary_of(address) if address else ''
    return {'pools': [{'id': pl['pool']['id'], 'name': pl['pool']['name'], 'pct': pl['pct'], 'potSol': pl['potSol'], 'wallets': len(pl['rows']),
                       'earns': [k.split(':', 1)[1] for k in pl['pool'].get('weights', {})], 'me': reserve_pool.wallet_share(pl, a) if a else None} for pl in hit[1]]}


# ---- Lag catcher: browsers report API latency / long tasks / FPS once a minute; HQ sees the fix ----
PERF_CFG_PATH = DATA_DIR / 'perf_config.json'
_perf_samples = collections.deque(maxlen=4000)


class PerfIn(BaseModel):
    page: str = Field(default='/', max_length=80)
    api: dict = Field(default_factory=dict)
    longTasks: int = Field(default=0, ge=0, le=10000)
    longMs: int = Field(default=0, ge=0, le=600000)
    fps: Optional[float] = Field(default=None, ge=0, le=240)
    lite: bool = False
    errors: int = Field(default=0, ge=0, le=1000)


@app.post('/api/reputation/perf')
async def perf_report(p: PerfIn):
    api = {str(k)[:160]: [float(x) for x in v[:50] if isinstance(x, (int, float))] for k, v in list(p.api.items())[:40] if isinstance(v, list)}
    _perf_samples.append({**p.dict(), 'api': api, 'at': time.time()})
    return {'ok': True}


@app.get('/api/reputation/perf/config')
async def perf_config():
    return {'forceLite': bool(_json_load(PERF_CFG_PATH, {}).get('forceLite'))}


class PerfCfgIn(BaseModel):
    forceLite: bool


@app.put('/api/reputation/admin/perf/config')
async def perf_config_set(request: Request, p: PerfCfgIn):
    admin = _require_admin(request)
    _json_save(PERF_CFG_PATH, {'forceLite': p.forceLite})
    ad = _admin_load(); _audit(ad, admin, 'perf-lite', str(p.forceLite)); _admin_save(ad)
    return {'forceLite': p.forceLite}


@app.get('/api/reputation/admin/perf')
async def perf_admin(request: Request, hours: float = Query(1, ge=0.1, le=24)):
    _require_admin(request)
    since = time.time() - hours * 3600
    return {**perf.summarize([s for s in _perf_samples if s['at'] >= since]), 'forceLite': bool(_json_load(PERF_CFG_PATH, {}).get('forceLite')), 'hours': hours}


# ================================================================================================
# LINKED ENGINE: one reputation score everywhere · trades earn season points · wallet watch · after-the-sell
# ================================================================================================
def _quick_rep(address: str) -> dict:
    """The case-file verdict without network calls: a fresh case file if one was built, else the same scoring
    over local evidence (blocklist, funder graph, creator record, cached caller stats). Same claims, same sources."""
    a = primary_of(address)
    hit = _case_cache.get(a)
    if hit and time.time() - hit[0] < 900 and hit[1].get('kind') == 'wallet':
        c = hit[1]
        return {'score': c.get('score', 0), 'level': c.get('level'), 'label': c.get('label'), 'top': (c.get('evidence') or [None])[0]}
    if a in _protected_wallets():
        return {**investigate.verdict([], True), 'top': None}
    fund = _funders_load(); store = _load()
    entry = store['creators'].get(_creator_key('solana', a))
    fsrc = store['funding'].get(_creator_key('solana', a))
    ctx = {'blocked': _block_load()['wallets'].get(a), 'funderOfSquads': fund['funders'].get(a), 'fundedBy': fsrc,
           'fundedByFlagged': bool(fsrc and _is_flagged_funder(fund['funders'].get(fsrc))),
           'creator': score_creator(entry) if entry else None, 'caller': _kol_cache.get(a, (0, None))[1], 'linkedCreators': []}
    ev = investigate.wallet_evidence(ctx)
    v = investigate.verdict(ev)
    return {'score': v['score'], 'level': v['level'], 'label': v['label'], 'top': next((e for e in ev if e['weight'] > 0), None)}


@app.get('/api/reputation/rep')
async def rep_batch(addresses: str = Query('', max_length=4000)):
    """Batch lookup for chat names, holder lists, trade tickets: {address: {score, level, label, top}}."""
    out = {}
    for a in dict.fromkeys(x.strip() for x in addresses.split(',') if x.strip()):
        if len(out) >= 60:
            break
        if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a):
            out[a] = _quick_rep(a)
    return {'reps': out}


def trade_points(in_usd: float, fee_bps: int) -> float:
    """Season points for a landed FEELESS trade: fees paid weigh most, volume counts a little, capped per trade."""
    usd = max(0.0, float(in_usd or 0))
    fee_usd = usd * max(0, int(fee_bps or 0)) / 10000
    return round(min(50.0, fee_usd * 20 + min(usd, 1000) / 200), 1)


FEE_LEDGER_PATH = DATA_DIR / 'fee_ledger.json'
FEE_TOTALS_PATH = DATA_DIR / 'fee_totals.json'
FEELESS_TRADES_PATH = DATA_DIR / 'feeless_trades.json'   # {wallet: [confirmed FEELESS trades]} for positions + chart pins        # lifetime per-account fee book (the payback base)
FEEBACK_PAID_PATH = DATA_DIR / 'feeback_paid.json'     # {account: usd already paid back}


def _fee_totals_heal():
    """Lifetime totals must match the fee ledger (the source of truth) to the trade: rebuilt whenever the trade counts
    differ or the file is missing. Totals only exist to make the fee book fast; they never get to disagree."""
    led = _json_load(FEE_LEDGER_PATH, {})
    tot = _json_load(FEE_TOTALS_PATH, {}) if FEE_TOTALS_PATH.exists() else None
    if tot is not None and {k: len(v or []) for k, v in led.items() if v} == {k: int(v.get('trades') or 0) for k, v in tot.items()}:
        return tot
    fresh = {}
    for who, rows_ in led.items():
        for r in rows_ or []:
            fee_report.add_total(fresh, who, r)
    _json_save(FEE_TOTALS_PATH, fresh)
    return fresh


@app.get('/api/reputation/admin/fee-book')
async def admin_fee_book(request: Request, format: str = ''):
    """Every account's lifetime FEELESS fees, FeeBack earned, paid and still owed (CSV with ?format=csv)."""
    _require_admin(request)
    _fee_totals_heal()
    rows = fee_report.fee_book(_json_load(FEE_TOTALS_PATH, {}), _json_load(FEEBACK_PAID_PATH, {}))
    if format == 'csv':
        from fastapi.responses import Response
        cols = ['address', 'trades', 'volumeUsd', 'feeUsd', 'feeSol', 'feeUsdc', 'feeBackUsd', 'paidUsd', 'owedUsd', 'first', 'last']
        body = ','.join(cols) + '\n' + '\n'.join(','.join(str(r.get(c, '')) for c in cols) for r in rows)
        return Response(body, media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=feeless-fee-book.csv'})
    return {'accounts': len(rows), 'totalFeesUsd': round(sum(r['feeUsd'] for r in rows), 4), 'owedUsd': round(sum(r['owedUsd'] for r in rows), 4),
            'feeBackPct': fee_report.FEEBACK_PCT, 'rows': rows[:500]}


@app.get('/api/reputation/fee-report/{address}')
async def fee_report_get(address: str):
    """FEELESS fees this wallet paid (7d + all time, linked accounts count once), the FeeBack accrued / paid / owed,
    how much of the fees came back, and what the wallet earned meanwhile (XP, rep, points, badge fee perk)."""
    if not _re.match(r'^([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})$', address):
        raise HTTPException(400, 'Bad address.')
    me = primary_of(address)
    rep = fee_report.fee_report(_json_load(FEE_LEDGER_PATH, {}).get(me) or [], time.time())
    paid = round(float(_json_load(FEEBACK_PAID_PATH, {}).get(me, 0) or 0), 6)
    # What you earned while paying those fees: XP/level + badge fee perk (quests), rep verdict, season points.
    try:
        q = await _quest_summary(me)
        quest = {'xp': q['level']['xp'], 'level': q['level']['name'], 'badges': q['earned'], 'badgeFeeDiscountPct': q['perks']['feeDiscountPct'],
                 'badgeFeeFrom': q['perks']['from'].get('fee'), 'seasonXp': q['season']['score']}
    except Exception:
        quest = {}
    qr = _quick_rep(me)
    fees = rep.get('feesTotalUsd') or 0
    back = rep.get('feeBackUsd') or 0
    return {'address': address, **rep, 'feeBackPaidUsd': paid, 'feeBackOwedUsd': round(max(0.0, back - paid), 6),
            'paidBackPct': round(back / fees * 100, 1) if fees else 0.0,
            'earned': {**quest, 'rep': {'score': qr.get('score'), 'label': qr.get('label')}, 'points': int((_pts().get(me) or {}).get('total') or 0)}}


class TradeLanded(BaseModel):
    wallet: str
    signature: str
    inUsd: float = 0
    feeBps: int = 0
    inputMint: str = ''
    outputMint: str = ''
    feeAtoms: int = 0
    feeMint: str = ''
    inAmount: float = 0
    outAmount: float = 0
    fill: Optional[dict] = None   # exact on-chain fill read by the trading service at confirmation


async def _sol_usd() -> float:
    hit = _sol_px.get('v')
    if hit and time.time() - hit[0] < 120:
        return hit[1]
    try:
        async with httpx.AsyncClient(timeout=4) as http:
            v = float(((await http.get(f'https://lite-api.jup.ag/price/v3?ids={WSOL}')).json().get(WSOL) or {}).get('usdPrice') or 0)
    except Exception:
        v = hit[1] if hit else 0.0
    _sol_px['v'] = (time.time(), v)
    return v


_sol_px: dict = {}


def _trade_record(p: 'TradeLanded', coin: str, amt: float, side: str, sol_usd: float, fee_usd: Optional[float] = None) -> Optional[dict]:
    """The trader's position row. The exact on-chain fill wins (what really left / reached the wallet, fees in);
    the quote is only a fallback, with the FEELESS fee added so it is never rosier than reality."""
    f = p.fill or {}
    if f.get('token') == coin and f.get('tokens', 0) > 0 and f.get('side') == side:
        usd = f.get('usd') or (f.get('sol') or 0) * sol_usd
        if usd > 0:
            return {**{k: f[k] for k in ('side', 'tokens', 'sol', 'networkSol', 'balanceAfter', 'poolUsd', 'fillPrice', 'feelessFeeUsd', 'networkUsd', 'solUsd', 'priced', 'locked') if k in f}, 'ts': f.get('ts') or time.time(),
                    'usd': round(usd, 6), 'price': usd / f['tokens'], 'token': coin, 'tx': p.signature, 'via': 'chain', 'locked': bool(f.get('locked'))}
    if amt > 0 and p.inUsd > 0:
        fee = fee_usd if fee_usd is not None else p.inUsd * max(0, p.feeBps) / 10000   # the fee actually charged beats the %
        usd = p.inUsd + fee if side == 'buy' else max(0.0, p.inUsd - fee)
        return {'ts': time.time(), 'side': side, 'usd': round(usd, 4), 'price': usd / amt, 'tokens': amt, 'token': coin, 'tx': p.signature, 'via': 'estimate'}
    return None


@app.post('/api/reputation/internal/trade')
async def internal_trade(request: Request, p: TradeLanded):
    """Called by the trading service once a FEELESS trade is confirmed on-chain (idempotent per signature)."""
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), _internal_key()):
        raise HTTPException(403, 'Internal only.')
    who = primary_of(p.wallet)
    px = await _sol_usd() if p.feeAtoms and p.feeMint == WSOL else 0
    eco = set((await _ecosystem_mints()).values())
    row = fee_report.ledger_row(time.time(), p.signature, p.inUsd, p.feeBps, p.feeAtoms, p.feeMint, px, feeback=bool(eco & {p.inputMint, p.outputMint}))
    # The trader's position row is saved on EVERY call (idempotent per tx) — before the points dedupe below, which once
    # skipped it and left a trade with no locked entry. A locked row is never replaced by a weaker (unlocked) one.
    stable_ = {WSOL, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'}
    coin, amt, side_ = (p.outputMint, p.outAmount, 'buy') if p.inputMint in stable_ else (p.inputMint, p.inAmount, 'sell')
    rec = _trade_record(p, coin, amt, side_, await _sol_usd(), row.get('feeUsd')) if coin not in stable_ else None
    if rec:
        ft = _json_load(FEELESS_TRADES_PATH, {})
        mine = ft.get(p.wallet) or []
        old = next((r for r in mine if r.get('tx') == p.signature), None)
        if not (old and old.get('locked') and not rec.get('locked')):
            ft[p.wallet] = ([r for r in mine if r.get('tx') != p.signature] + [rec])[-300:]
            _json_save(FEELESS_TRADES_PATH, ft)
    d = _seasons(); seen = d.setdefault('tradeSigs', [])
    if p.signature in seen:
        return {'ok': True, 'points': 0, 'duplicate': True}
    pts = trade_points(p.inUsd, p.feeBps)
    d['tradeSigs'] = (seen + [p.signature])[-5000:]
    _json_save(SEASONS_PATH, d)
    led = _json_load(FEE_LEDGER_PATH, {})
    led[who] = (led.get(who) or [])[-1999:] + [row]
    _json_save(FEE_LEDGER_PATH, led)
    _json_save(FEE_TOTALS_PATH, fee_report.add_total(_json_load(FEE_TOTALS_PATH, {}), who, row))   # lifetime, never trimmed
    inviter = _json_load(REF_PATH, {'by': {}, 'of': {}})['of'].get(who)
    # The trade is confirmed on-chain (the trading service checked): tell the trader and refresh their holdings,
    # whether or not their browser is still open. Deduped with the receipt notification by signature.
    stable = {WSOL, 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'}
    side = 'Buy' if p.inputMint in stable and p.outputMint not in stable else 'Sell' if p.outputMint in stable else 'Swap'
    try:
        _pf_cache.pop(who, None); _badge_cache.pop(who, None)
        notify(p.wallet, 'reward', f"✅ {side} confirmed on-chain" + (f" · ${p.inUsd:,.2f}" if p.inUsd else '') + (f" · +{pts:g} season pts" if pts > 0 else ''),
               f'https://solscan.io/tx/{p.signature}', once=f'tx:{p.signature}')
    except Exception:
        pass
    pct = float(_json_load(REF_CFG_PATH, {}).get('pct') or 0)
    if inviter and pct > 0:
        _json_save(REF_EARN_PATH, fee_report.referral_credit(_json_load(REF_EARN_PATH, {}), inviter, who, row, pct, time.time()))
    if pts > 0:
        season_award(primary_of(p.wallet), pts, f'trade:{p.signature[:10]}')
    return {'ok': True, 'points': pts}


# ---- Wallet watch: one tap from any case file; alerts on the watched wallet's next buys/sells --------------
WATCH_PATH = DATA_DIR / 'wallet_watch.json'
WATCH_MAX_PER_USER = 25


class WatchIn(BaseModel):
    address: str
    session: str
    target: str
    on: bool = True


@app.post('/api/reputation/wallet-watch')
async def watch_set(p: WatchIn):
    me = _session_or_401(p.address, p.session)
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.target):
        raise HTTPException(400, 'Watch a Solana wallet address.')
    d = _json_load(WATCH_PATH, {'targets': {}, 'last': {}})
    mine = [t for t, ws in d['targets'].items() if me in ws]
    if p.on and p.target not in mine and len(mine) >= WATCH_MAX_PER_USER:
        raise HTTPException(409, f'You can watch up to {WATCH_MAX_PER_USER} wallets.')
    ws = set(d['targets'].get(p.target, []))
    (ws.add if p.on else ws.discard)(me)
    if ws:
        d['targets'][p.target] = sorted(ws)
    else:
        d['targets'].pop(p.target, None)
    _json_save(WATCH_PATH, d)
    return {'watching': p.on, 'count': len([t for t, w in d['targets'].items() if me in w])}


@app.get('/api/reputation/wallet-watch')
async def watch_list(address: str, session: str):
    me = _session_or_401(address, session)
    d = _json_load(WATCH_PATH, {'targets': {}})
    return {'targets': [{'address': t, **_quick_rep(t)} for t, ws in d['targets'].items() if me in ws]}


def watch_alerts(target: str, trades: list, last_ts: float, rep: dict, name: str) -> list:
    """Pure: new trades by a watched wallet → alert lines (dumps by suspect wallets called out)."""
    out = []
    for t in sorted((x for x in trades if (x.get('ts') or 0) > last_ts), key=lambda x: x['ts'])[-5:]:
        sym = t.get('symbol') or (t.get('token') or '')[:4]
        bad = rep.get('level') in ('suspect', 'high')
        verb = 'bought' if t.get('side') == 'buy' else ('is dumping' if bad else 'sold')
        out.append({'text': f"👁 {name} {verb} ${sym} (${t.get('usd', 0):,.0f}){' · ' + rep.get('label', '') if bad else ''}",
                    'url': f"/terminal/chat?chain=solana&pair={t['pair']}" if t.get('pair') else f'/terminal/profile/{target}', 'ts': t['ts'], 'tx': t.get('tx')})
    return out


async def _watch_loop():
    while True:
        await asyncio.sleep(120)
        try:
            d = _json_load(WATCH_PATH, {'targets': {}, 'last': {}})
            last = d.setdefault('last', {}); changed = False
            for target, watchers in list(d['targets'].items())[:150]:
                try:
                    trades = await wallet_trades(target)
                except Exception:
                    continue
                newest = max((t.get('ts') or 0 for t in trades), default=0)
                if target not in last:  # first look: remember where we are, don't replay history
                    last[target] = newest; changed = True
                    continue
                name = _display_name(target) or f'{target[:4]}…{target[-4:]}'
                for a in watch_alerts(target, trades, last[target], _quick_rep(target), name):
                    for w in watchers:
                        notify(w, 'watch', a['text'], a['url'], actor=target, once=f"watch:{a['tx'] or a['ts']}")
                if newest > last[target]:
                    last[target] = newest; changed = True
            if changed:
                _json_save(WATCH_PATH, d)
        except Exception as exc:
            print('watch loop error', exc)


@app.on_event('startup')
async def _start_watch():
    asyncio.create_task(_watch_loop())


# ---- After the sell: FeeCat's lesson log, pointed at your own trades ------------------------------------
def after_sell_lessons(trades: list, prices: dict) -> list:
    """Pure: your recent sells vs the coin's price now. A coin that ran 40%+ after you sold = 'sold a runner'."""
    out = []
    for t in trades:
        if t.get('side') != 'sell' or not t.get('price'):
            continue
        now = prices.get(t.get('token'))
        if not now:
            continue
        move = round((now / t['price'] - 1) * 100, 1)
        out.append({'token': t['token'], 'symbol': t.get('symbol'), 'pair': t.get('pair'), 'soldAt': t['price'], 'now': now, 'movePct': move,
                    'soldUsd': t.get('usd'), 'ts': t.get('ts'), 'lesson': 'runner' if move >= 40 else 'saved' if move <= -30 else 'fair'})
    return sorted(out, key=lambda x: -x['movePct'])[:12]


@app.get('/api/reputation/after-sell/{address}')
async def after_sell(address: str):
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        raise HTTPException(400, 'Bad address.')
    trades = [t for t in await wallet_trades(address) if t.get('side') == 'sell'][:20]
    toks = list({t['token'] for t in trades})[:30]
    prices = {}
    if toks:
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                for p in (await http.get(f"https://api.dexscreener.com/latest/dex/tokens/{','.join(toks)}")).json().get('pairs') or []:
                    a = (p.get('baseToken') or {}).get('address')
                    if a and a not in prices and p.get('priceUsd'):
                        prices[a] = float(p['priceUsd'])
        except Exception:
            pass
    rows = after_sell_lessons(trades, prices)
    return {'address': address, 'rows': rows, 'runners': sum(r['lesson'] == 'runner' for r in rows), 'saved': sum(r['lesson'] == 'saved' for r in rows)}


# ---- Treasury hub: where the money sits, the split plan, and verified splits signed by the owner ----------
USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'


@app.get('/api/reputation/admin/treasury/money')
async def treasury_money(request: Request):
    """Every wallet that holds FEELESS money, read live: fee accounts (wSOL / USDC), the admin wallet,
    season reserves and badge pools. Read-only; nothing here can move funds."""
    admin = _require_admin(request)
    cfg = _fee_cfg()
    fee_accts = [('SOL fee account (wSOL)', cfg.get('feeAccountSol') or '', 'wSOL'), ('USDC fee account', cfg.get('feeAccountUsdc') or '', 'USDC')]
    reserves = [(f"Season reserve · {s['name']}", s['reserveWallet']) for s in _seasons()['seasons'] if s.get('reserveWallet')]
    reserves += [(f"Badge pool · {p['name']}", p['wallet']) for p in _pools()['pools']]

    async with httpx.AsyncClient(timeout=10) as http:
        async def token(addr):
            if not addr:
                return None
            try:
                v = ((await _rpc(http, 'getAccountInfo', [addr, {'encoding': 'jsonParsed'}])) or {}).get('value') or {}
                info = ((v.get('data') or {}).get('parsed') or {}).get('info') or {}
                return {'owner': info.get('owner'), 'mint': info.get('mint'), 'amount': float((info.get('tokenAmount') or {}).get('uiAmount') or 0)}
            except Exception:
                return None

        async def sol(addr):
            try:
                return ((await _rpc(http, 'getBalance', [addr])) or {}).get('value', 0) / 1e9
            except Exception:
                return None
        results = await asyncio.gather(*(token(a) for _, a, _ in fee_accts), sol(admin), *(sol(a) for _, a in reserves))
    fee_rows = [{'label': l, 'address': a, 'asset': asset, **(r or {}), 'ok': bool(r)} for (l, a, asset), r in zip(fee_accts, results[:2])]
    return {'admin': admin, 'adminSol': results[2], 'feeAccounts': fee_rows,
            'reserves': [{'label': l, 'address': a, 'sol': b} for (l, a), b in zip(reserves, results[3:])],
            'routes': _json_load(ROUTES_PATH, {'routes': []}).get('routes', []), 'splits': (_admin_load().get('splits') or [])[-10:][::-1],
            'owners': list(_owner_wallets())}


_pulse_cache: dict = {}


@app.get('/api/reputation/admin/money-pulse')
async def admin_money_pulse(request: Request, fresh: int = 0):
    """ONE snapshot for every HQ money card: fee accounts, admin, season reserves, badge pools and Circle
    wallets (one batched chain read + Circle in parallel), their payout plans, a preflight of everything trading
    depends on, and nudges. Owners also get Circle (and calling it keeps the Circle service alive)."""
    me = _require_admin(request)
    owner = me in _owner_wallets()
    key = 'owner' if owner else 'admin'
    hit = _pulse_cache.get(key)
    if hit and not fresh and time.time() - hit[0] < 15:
        return {**hit[1], 'cached': True}
    out = await _money_pulse_build(me, owner)
    _pulse_cache[key] = (time.time(), out)
    return out


async def _money_pulse_build(me: str, owner: bool) -> dict:
    cfg = _fee_cfg(); d = _seasons(); pools = _pools()['pools']
    seasons = [x for x in d['seasons'] if x.get('reserveWallet')][-4:]
    addrs = list(dict.fromkeys([a for a in (cfg.get('feeAccountSol'), cfg.get('feeAccountUsdc'), me) if a] + [x['reserveWallet'] for x in seasons] + [p['wallet'] for p in pools]))

    async def chain():
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                res = await _rpc(http, 'getMultipleAccounts', [addrs[:100], {'encoding': 'jsonParsed', 'commitment': 'confirmed'}])
            return money_pulse.parse_accounts(addrs, (res or {}).get('value') or []), True
        except Exception:
            return {}, False

    async def circle():
        if not owner:
            return {'configured': False}
        try:
            # Money Pulse deliberately performs one batched chain read for its own cards. The dedicated Circle-wallet endpoint
            # enriches wallet rows with confirmed SOL without adding a second RPC call to this overview.
            return {'configured': True, 'up': True, 'wallets': (await _circle('GET', '/wallets')).get('wallets') or []}
        except HTTPException as e:
            return {'configured': bool(os.environ.get('CIRCLE_API_KEY')), 'up': False, 'error': str(e.detail)[:160], 'wallets': []}

    async def trading():
        try:
            async with httpx.AsyncClient(timeout=4) as http:
                return (await http.get('http://127.0.0.1:5001/api/trading/status')).json()
        except Exception:
            return {}
    (acc, chain_ok), circ, trade = await asyncio.gather(chain(), circle(), trading())
    sol = lambda a: (acc.get(a) or {}).get('sol') if chain_ok else None
    reserves, pool_plans = await asyncio.gather(
        asyncio.gather(*(_reserve_plan(x, d, bal=sol(x['reserveWallet'])) for x in seasons)),
        asyncio.gather(*(_pool_plan(dict(p), bal=sol(p['wallet'])) for p in pools)))
    fee_rows = []
    for label, a, asset in (('SOL fee account (wSOL)', cfg.get('feeAccountSol') or '', 'wSOL'), ('USDC fee account', cfg.get('feeAccountUsdc') or '', 'USDC')):
        t = (acc.get(a) or {}).get('token') if a else None
        fee_rows.append({'label': label, 'address': a, 'asset': asset, 'ok': bool(t), **(t or {})})
    ledger = _json_load(FEE_LEDGER_PATH, {})
    last = max((r[-1]['t'] for r in ledger.values() if r), default=0)
    now = time.time()
    fees_day = round(sum(x['feeUsd'] for r in ledger.values() for x in r if now - x['t'] < 86400), 4)
    fees_week = round(sum(x['feeUsd'] for r in ledger.values() for x in r if now - x['t'] < 7 * 86400), 4)
    env = {k: os.environ.get(k, '').strip() for k in ('SOLANA_RPC_URL', 'JUPITER_API_KEY')}
    env['_internal_key'] = (Path(__file__).parent / 'data' / 'internal.key').exists()
    checks = money_pulse.preflight(env, cfg, fee_rows, trade, last, time.time(), circ)
    if not chain_ok:
        checks.insert(0, {'key': 'chain', 'label': 'Chain read', 'ok': False, 'fix': 'RPC did not answer; balances below may be stale.'})
    trim = lambda plan: {**plan, 'rows': plan['rows'][:60]}
    out = {'at': time.time(), 'owner': owner, 'chainOk': chain_ok, 'feesTodayUsd': fees_day, 'fees7dUsd': fees_week, 'feesSince': min((x['t'] for r in ledger.values() for x in r), default=None), 'admin': me, 'adminSol': sol(me), 'feeAccounts': fee_rows,
           'reserves': {r['season']['id']: trim(r) for r in reserves}, 'pools': {p['pool']['id']: trim(p) for p in pool_plans},
           'circle': circ, 'checks': checks, 'alerts': money_pulse.alerts(reserves, pool_plans, circ.get('wallets'))}
    return out


PREFLIGHT_STATE_PATH = DATA_DIR / 'preflight_state.json'


async def _preflight_watch():
    """Every 10 min: re-run the money preflight; when a check turns red (or recovers) the owners get a bell + phone push."""
    await asyncio.sleep(90)
    while True:
        try:
            owners = sorted(_owner_wallets())
            if owners:
                snap = await _money_pulse_build(owners[0], True)
                _pulse_cache['owner'] = (time.time(), snap)
                prev = _json_load(PREFLIGHT_STATE_PATH, {})
                bad, fixed, state = money_pulse.check_flips(prev, snap['checks'])
                _json_save(PREFLIGHT_STATE_PATH, state)
                for c in bad:
                    for o in owners:
                        notify(o, 'system', f"⚠ Money check failing: {c['label']}. {c.get('fix') or ''}".strip(), '/terminal', once=f"pf-bad:{c['key']}:{int(time.time() // 3600)}")
                for c in fixed:
                    for o in owners:
                        notify(o, 'system', f"✅ Back to green: {c['label']}", '/terminal', once=f"pf-ok:{c['key']}:{int(time.time() // 3600)}")
        except Exception:
            pass
        await asyncio.sleep(600)


@app.on_event('startup')
async def _preflight_start():
    asyncio.create_task(_preflight_watch())


class SplitRecord(BaseModel):
    sigs: list[str] = Field(min_length=1, max_length=40)
    asset: str = 'SOL'


@app.post('/api/reputation/admin/treasury/split')
async def treasury_split_record(request: Request, p: SplitRecord):
    """Record a split the owner signed from their own wallet. Every signature is re-read on-chain and only the
    transfers the signer really made are stored."""
    admin = _require_admin(request)
    if not all(_re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', x) for x in p.sigs):
        raise HTTPException(400, 'Bad transaction signature.')
    ad = _admin_load()
    if {s for sp in ad.get('splits') or [] for s in sp['sigs']} & set(p.sigs):
        raise HTTPException(409, 'Already recorded.')
    async with httpx.AsyncClient(timeout=20) as http:
        txs = await asyncio.gather(*(_rpc(http, 'getTransaction', [x, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0}]) for x in p.sigs))
    moved, signer = [], None
    allowed = set(_owner_wallets()) | set(_admin_wallets())
    for sig, tx in zip(p.sigs, txs):
        if not tx or (tx.get('meta') or {}).get('err'):
            raise HTTPException(400, f'Transaction {sig[:8]}… is not on-chain or failed.')
        signers = [k['pubkey'] for k in tx['transaction']['message']['accountKeys'] if k.get('signer')]
        signer = next((s for s in signers if s in allowed), None)
        if not signer:
            raise HTTPException(400, 'Splits must be signed by a FEELESS owner/admin wallet.')
        moved += reserve_pool.parsed_transfers(tx, signer)
    if not moved:
        raise HTTPException(400, 'No transfers found in those transactions.')
    rec = {'sigs': p.sigs, 'asset': p.asset[:10], 'by': signer, 'at': time.time(), 'moved': moved[:60], 'total': round(sum(m['amount'] for m in moved), 6)}
    ad.setdefault('splits', []).append(rec); ad['splits'] = ad['splits'][-50:]
    _audit(ad, admin, 'treasury-split', f"{rec['total']} {p.asset} in {len(p.sigs)} tx"); _admin_save(ad)
    return {'ok': True, 'total': rec['total'], 'transfers': len(moved)}


# ================================================================================================
# COIN VERIFICATION: the green check over a coin's logo, earned by passing cited safety checks
# ================================================================================================
VERIFY_PATH = DATA_DIR / 'verify.json'
VERIFY_TTL = 6 * 3600
_verify_cache: dict = {}      # mint -> (at, report)
_verify_pending: set = set()


def _verify_store():
    return _json_load(VERIFY_PATH, {'mints': {}, 'requests': []})


async def _verify_facts(mint):
    """Everything the checks need, gathered in parallel: holder forensics, mint account, the live pool."""
    async def market():
        async with httpx.AsyncClient(timeout=10) as http:
            return (await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{mint}')).json().get('pairs') or []

    async def safe(coro, default):
        try:
            return await coro
        except Exception:
            return default
    async with httpx.AsyncClient(timeout=10) as http:
        intel, auth, pairs = await asyncio.gather(safe(token_intel('solana', mint), {}), safe(_mint_authorities(http, mint), None), safe(market(), []))
    pairs = sorted((p for p in pairs if p.get('chainId') == 'solana'), key=lambda p: -((p.get('liquidity') or {}).get('usd') or 0))
    top = pairs[0] if pairs else {}
    info = top.get('info') or {}
    tx = (top.get('txns') or {}).get('h24') or {}
    buys, sells = tx.get('buys') or 0, tx.get('sells') or 0
    reg = [p for p in _json_load(POOLS_REG_PATH, {'pools': []})['pools'] if p.get('mint') == mint and p.get('locked')]
    creator = intel.get('creator')
    rep = _quick_rep(creator) if creator else {}
    created = min((p.get('pairCreatedAt') or 9e15 for p in pairs), default=None)
    facts = {
        'mintAuthority': (auth or {}).get('mintAuthority') if auth is not None else 'unknown',
        'freezeAuthority': (auth or {}).get('freezeAuthority') if auth is not None else 'unknown',
        'creatorBlocked': bool(creator and _is_blocked(_block_load()['wallets'].get(creator))), 'creatorLevel': rep.get('level'),
        'ageHours': (time.time() * 1000 - created) / 3.6e6 if created and created < 9e15 else 0,
        'liquidityUsd': (top.get('liquidity') or {}).get('usd') or 0, 'volume24h': (top.get('volume') or {}).get('h24') or 0,
        'buyRatio': buys / (buys + sells) if buys + sells >= 50 else None,
        'socials': len(info.get('socials') or []) + len(info.get('websites') or []),
        'lpLocked': bool(reg) or str(top.get('dexId') or '').lower() == 'pumpswap',
        'top10Pct': intel.get('top10Pct'), 'insidersPct': intel.get('insidersHoldingPct'), 'devPct': intel.get('devHoldingPct'),
        'marketCapUsd': top.get('marketCap') or top.get('fdv') or 0,
        'bundled': len(intel.get('bundledWallets') or []), 'snipers': len(intel.get('sniperWallets') or []),
    }
    return facts, {'symbol': (top.get('baseToken') or {}).get('symbol'), 'pair': top.get('pairAddress'), 'dexId': top.get('dexId')}


async def _verify_run(mint):
    facts, meta = await _verify_facts(mint)
    manual = _verify_store()['mints'].get(mint)
    try:
        official = mint in set((await _ecosystem_mints()).values())
    except Exception:
        official = False
    rep = {**verify.verify_report(facts, manual, official), 'mint': mint, **meta, 'at': time.time()}
    snap = {'level': rep['level'], 'badges': [b['id'] for b in rep['badges'] if b['earned']]}
    d = _verify_store()
    prev = (d.get('last') or {}).get(mint)
    if prev != snap:   # coins earn AND lose checks + badges the same way: every run is compared with the last one
        events = [{**e, 'at': rep['at']} for e in verify.transitions(prev, rep)]
        d.setdefault('last', {})[mint] = snap
        if events:
            d.setdefault('history', {})[mint] = ((d.get('history') or {}).get(mint, []) + events)[-20:]
        _json_save(VERIFY_PATH, d)
    rep['history'] = list(reversed((d.get('history') or {}).get(mint, [])))[:10]
    _verify_cache[mint] = (time.time(), rep)
    if len(_verify_cache) > 5000:
        _verify_cache.clear()
    return rep


async def _verify_fill(mint):
    try:
        await _verify_run(mint)
    except Exception:
        pass
    finally:
        _verify_pending.discard(mint)


@app.get('/api/reputation/verify/batch')
async def verify_batch(mints: str = Query('', max_length=4000)):
    """Checks for logos on screen: answers from cache instantly, verifies missing coins in the background
    (a few at a time), and always reflects HQ grants/revokes immediately."""
    store = _verify_store()['mints']
    out = {}
    for m in [x.strip() for x in mints.split(',') if x.strip()][:60]:
        if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', m):
            continue
        manual = (store.get(m) or {}).get('state')
        hit = _verify_cache.get(m)
        if manual == 'revoked':
            out[m] = {'level': 'revoked'}
        elif manual == 'granted' and not (hit and 'suspended' in str(hit[1].get('reason'))):
            out[m] = {'level': 'gold', 'score': hit[1]['score'] if hit else None}
        elif hit:
            out[m] = {'level': hit[1]['level'], 'score': hit[1]['score']}
        if (not hit or time.time() - hit[0] > VERIFY_TTL) and m not in _verify_pending and len(_verify_pending) < 6:
            _verify_pending.add(m); asyncio.create_task(_verify_fill(m))
    return {'verify': out}


@app.get('/api/reputation/verify/{mint}')
async def verify_one(mint: str, fresh: bool = False):
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', mint):
        raise HTTPException(400, 'Bad mint.')
    hit = _verify_cache.get(mint)
    if hit and not fresh and time.time() - hit[0] < VERIFY_TTL:
        return hit[1]
    return await _verify_run(mint)


class VerifyRequest(BaseModel):
    address: str
    session: str
    mint: str
    note: str = Field(default='', max_length=280)


@app.post('/api/reputation/verify/request')
async def verify_request(p: VerifyRequest):
    """A creator asks for review (e.g. a strong coin that just misses a gate)."""
    me = _session_or_401(p.address, p.session)
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.mint):
        raise HTTPException(400, 'Bad mint.')
    d = _verify_store()
    if any(r['mint'] == p.mint and r.get('status') == 'open' for r in d['requests']):
        return {'ok': True, 'queued': False}
    d['requests'] = (d['requests'] + [{'mint': p.mint, 'by': me, 'note': p.note[:280], 'at': time.time(), 'status': 'open'}])[-300:]
    _json_save(VERIFY_PATH, d)
    return {'ok': True, 'queued': True}


class VerifyAdminIn(BaseModel):
    mint: str
    action: str            # grant | revoke | clear
    note: str = Field(default='', max_length=200)


@app.post('/api/reputation/admin/coin-verify')
async def verify_admin(request: Request, p: VerifyAdminIn):
    admin = _require_admin(request)
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.mint) or p.action not in ('grant', 'revoke', 'clear'):
        raise HTTPException(400, 'Mint + grant / revoke / clear.')
    d = _verify_store()
    if p.action == 'clear':
        d['mints'].pop(p.mint, None)
    else:
        d['mints'][p.mint] = {'state': 'granted' if p.action == 'grant' else 'revoked', 'note': p.note, 'by': admin, 'at': time.time()}
    for r in d['requests']:
        if r['mint'] == p.mint and r.get('status') == 'open':
            r['status'] = {'grant': 'granted', 'revoke': 'denied', 'clear': 'closed'}[p.action]
    _json_save(VERIFY_PATH, d)
    _verify_cache.pop(p.mint, None)
    ad = _admin_load(); _audit(ad, admin, f'verify-{p.action}', p.mint); _admin_save(ad)
    return {'ok': True, 'state': d['mints'].get(p.mint)}


@app.get('/api/reputation/admin/coin-verify')
async def verify_admin_list(request: Request):
    _require_admin(request)
    d = _verify_store()
    auto = sorted((r for _, r in _verify_cache.values() if r.get('level') == 'verified'), key=lambda r: -r['score'])[:40]
    return {'manual': [{'mint': m, **v} for m, v in d['mints'].items()], 'requests': [r for r in d['requests'] if r.get('status') == 'open'][-50:],
            'auto': [{k: r.get(k) for k in ('mint', 'symbol', 'score', 'level', 'at')} for r in auto]}


class BadgeEdit(BaseModel):
    label: str = Field(min_length=2, max_length=32)
    icon: str = Field(default='⭐', max_length=8)
    tone: str = 'gold'
    why: str = Field(default='', max_length=140)


@app.put('/api/reputation/admin/badges/{bid}')
async def admin_badge_edit(request: Request, bid: str, p: BadgeEdit):
    """Edit a badge everywhere it's held (label, icon, tone, why). Holders keep it; only the look changes."""
    admin = _require_admin(request)
    tone = p.tone if p.tone in ('mint', 'gold', 'plain', 'bad') else 'gold'
    n = 0
    async with _admin_lock:
        d = _admin_load()
        for a, items in d['badges'].items():
            if bid in items:
                items[bid].update({'label': p.label, 'icon': p.icon, 'tone': tone, 'why': p.why or items[bid].get('why', '')}); n += 1
                _badge_cache.pop(a, None)
        if not n:
            raise HTTPException(404, 'No one holds that badge.')
        _audit(d, admin, 'badge-edit', f'{bid} → {p.label}')
        _admin_save(d)
    return {'ok': True, 'holders': n}


# ---- NFT studio: FEELESS cards → NFT collections (Metaplex Core / Crossmint / Underdog) + drops ---------------------
NFT_PATH = DATA_DIR / 'nft_collections.json'
_nft_lock = asyncio.Lock()


def _nft_load():
    return _json_load(NFT_PATH, {'collections': []})


def _public_site(request: Request) -> str:
    """NFT + coin metadata is permanent: it must live on a public https domain, never localhost."""
    site = os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/') or (request.headers.get('origin') or '').rstrip('/')
    host = _re.sub(r'^https?://', '', site).split('/')[0].split(':')[0]
    if not site.startswith('https://') or host in ('localhost', '127.0.0.1', '0.0.0.0') or host.endswith('.local') or _re.match(r'^(10|192\.168|172\.(1[6-9]|2\d|3[01]))\.', host):
        raise HTTPException(503, 'NFTs need a public https domain for their metadata (set PUBLIC_SITE_URL). A local address would break them forever.')
    return site


def _nft_platforms() -> dict:
    cm, ud = os.environ.get('CROSSMINT_API_KEY', '').strip(), os.environ.get('UNDERDOG_API_KEY', '').strip()
    return {'metaplex': {'ready': True, 'how': 'Your connected wallet signs. ~0.003 SOL rent per NFT + network fee. No key needed.'},
            'crossmint': {'ready': bool(cm), 'env': 'staging' if cm.startswith(('sk_staging', 'sk_test')) else 'production' if cm else None,
                          'how': 'Add CROSSMINT_API_KEY (console.crossmint.com, scopes collections.create + nfts.create) to backend/.env.'},
            'underdog': {'ready': bool(ud), 'env': os.environ.get('UNDERDOG_ENV', 'mainnet'),
                         'how': 'Add UNDERDOG_API_KEY (app.underdogprotocol.com) to backend/.env; UNDERDOG_ENV=devnet to test.'}}


async def _nft_api(platform: str, method: str, path: str, body=None):
    if platform == 'crossmint':
        key = os.environ.get('CROSSMINT_API_KEY', '').strip()
        url, headers = nft_studio.crossmint_base(key) + path, {'X-API-KEY': key}
    else:
        key = os.environ.get('UNDERDOG_API_KEY', '').strip()
        url, headers = nft_studio.underdog_base(os.environ.get('UNDERDOG_ENV', '')) + path, {'Authorization': f'Bearer {key}'}
    if not key:
        raise HTTPException(400, f'{platform.title()} is not connected yet (API key missing).')
    try:
        async with httpx.AsyncClient(timeout=30) as http:
            r = await http.request(method, url, json=body, headers=headers)
    except httpx.HTTPError as e:
        raise HTTPException(502, f'{platform.title()} did not answer ({e.__class__.__name__}).')
    data = r.json() if r.content else {}
    if r.status_code >= 400:
        raise HTTPException(502, f"{platform.title()}: {str(data.get('message') or data.get('error') or data)[:160]}")
    return data


@app.get('/api/reputation/admin/nft')
async def nft_home(request: Request):
    _require_admin(request)
    return {'platforms': _nft_platforms(), 'collections': sorted(_nft_load()['collections'], key=lambda c: -c.get('createdAt', 0))}


@app.post('/api/reputation/admin/nft/collections')
async def nft_create(request: Request):
    """Create a collection. Crossmint / Underdog are created here via their API; Metaplex Core is created in the
    browser (your wallet signs) and recorded with /onchain."""
    me = _require_owner(request)
    try:
        c = nft_studio.clean_collection(await request.json())
    except ValueError as e:
        raise HTTPException(400, str(e))
    site = _public_site(request)
    cid = uuid.uuid4().hex[:12]
    c.update({'id': cid, 'createdAt': time.time(), 'by': me, 'drops': [], 'status': 'draft', 'address': None,
              'uri': f'{site}/api/reputation/nft-meta/{cid}.json'})
    if c['platform'] == 'crossmint':
        out = await _nft_api('crossmint', 'POST', '/api/2022-06-09/collections', nft_studio.crossmint_collection_body(c, site))
        c.update({'address': out.get('id'), 'status': 'live'})
    elif c['platform'] == 'underdog':
        out = await _nft_api('underdog', 'POST', '/v2/projects', nft_studio.underdog_project_body(c, site))
        c.update({'address': str(out.get('projectId') or out.get('id') or ''), 'mint': out.get('mintAddress'), 'status': 'live'})
    async with _nft_lock:
        d = _nft_load(); d['collections'].append(c); _json_save(NFT_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'nft-collection', f"{c['platform']} {c['name']} ({c['symbol']})"); _admin_save(ad)
    return c


class NftOnchainIn(BaseModel):
    address: str
    signature: str
    assets: list = []     # for drops: [{address, owner}]


async def _nft_verify(sig: str, signer: str, must_touch: list):
    async with httpx.AsyncClient(timeout=20) as http:
        tx = await _rpc(http, 'getTransaction', [sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
    if not tx or (tx.get('meta') or {}).get('err'):
        raise HTTPException(400, 'That transaction is not confirmed on-chain (or it failed).')
    keys = tx['transaction']['message']['accountKeys']
    if signer not in [k['pubkey'] for k in keys if k.get('signer')]:
        raise HTTPException(400, 'Signed by a different wallet.')
    if any(a not in [k['pubkey'] for k in keys] for a in must_touch):
        raise HTTPException(400, 'That transaction does not create this collection / these NFTs.')


@app.post('/api/reputation/admin/nft/collections/{cid}/onchain')
async def nft_onchain(request: Request, cid: str, p: NftOnchainIn):
    """Metaplex Core: record what the owner's wallet created (collection) or minted (a drop), verified on-chain."""
    me = _require_owner(request)
    if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', p.signature) or not _re.match(_B58, p.address):
        raise HTTPException(400, 'Bad signature or address.')
    assets = [a for a in p.assets if isinstance(a, dict) and _re.match(_B58, str(a.get('address') or '')) and _re.match(_B58, str(a.get('owner') or ''))][:nft_studio.MAX_DROP]
    await _nft_verify(p.signature, me, [p.address] + [a['address'] for a in assets])
    async with _nft_lock:
        d = _nft_load(); c = next((x for x in d['collections'] if x['id'] == cid), None)
        if not c or c['platform'] != 'metaplex':
            raise HTTPException(404, 'Metaplex collection not found.')
        if not assets:
            c.update({'address': p.address, 'status': 'live', 'createSig': p.signature})
        else:
            if c.get('address') != p.address:
                raise HTTPException(400, 'Those NFTs belong to a different collection.')
            c['drops'].append({'at': time.time(), 'ok': [{'to': a['owner'], 'asset': a['address'], 'sig': p.signature} for a in assets], 'failed': []})
        _json_save(NFT_PATH, d)
    return c


class NftDropIn(BaseModel):
    to: list = []
    confirm: str = ''


@app.post('/api/reputation/admin/nft/collections/{cid}/drop')
async def nft_drop(request: Request, cid: str, p: NftDropIn):
    """Crossmint / Underdog: mint one NFT to each wallet via the platform API. Type DROP <count> to confirm."""
    me = _require_owner(request)
    site = _public_site(request)
    c = next((x for x in _nft_load()['collections'] if x['id'] == cid), None)
    if not c or c['platform'] == 'metaplex' or c.get('status') != 'live':
        raise HTTPException(404, 'Live Crossmint / Underdog collection not found.')
    to = nft_studio.recipients(p.to)[:nft_studio.room_left(c)]
    if not to:
        raise HTTPException(400, 'No valid Solana wallets (or the supply cap is reached).')
    if p.confirm.strip() != f'DROP {len(to)}':
        raise HTTPException(400, f'Type "DROP {len(to)}" to confirm.')
    start = sum(len(x.get('ok') or []) for x in c['drops']) + 1
    sem = asyncio.Semaphore(4)

    async def one(i, w):
        async with sem:
            try:
                if c['platform'] == 'crossmint':
                    out = await _nft_api('crossmint', 'POST', f"/api/2022-06-09/collections/{c['address']}/nfts", nft_studio.crossmint_mint_body(c, site, w, start + i))
                else:
                    out = await _nft_api('underdog', 'POST', f"/v2/projects/{c['address']}/nfts", nft_studio.underdog_nft_body(c, site, w, start + i))
                return {'to': w, 'asset': str(out.get('id') or out.get('nftId') or out.get('mintAddress') or ''), 'ok': True}
            except HTTPException as e:
                return {'to': w, 'error': str(e.detail)[:160], 'ok': False}
    res = await asyncio.gather(*(one(i, w) for i, w in enumerate(to)))
    ok, bad = [r for r in res if r['ok']], [r for r in res if not r['ok']]
    async with _nft_lock:
        d = _nft_load(); cc = next(x for x in d['collections'] if x['id'] == cid)
        cc['drops'].append({'at': time.time(), 'by': me, 'ok': ok, 'failed': bad}); _json_save(NFT_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'nft-drop', f"{c['name']}: {len(ok)} minted, {len(bad)} failed"); _admin_save(ad)
    return {'minted': len(ok), 'failed': bad}


@app.get('/api/reputation/admin/nft/holders/{key:path}')
async def nft_card_holders(request: Request, key: str):
    """Wallets that hold a card (badge or season card): the natural drop list for that card's collection."""
    _require_admin(request)
    out = set()
    if key.startswith('badge:'):
        bid = key.split(':', 1)[1]
        out |= {a for a, items in (_admin_load().get('badges') or {}).items() if bid in items}
        out |= {a for a, (at, rec) in _badge_cache.items() if any(b.get('id') == bid for b in (rec or {}).get('badges', []))}
    else:
        out |= {a for a, items in _json_load(COLLECTION_PATH, {}).items() if any(_collection_card_key(it) == key for it in items)}
    safe = _protected_wallets()
    return {'key': key, 'wallets': sorted(a for a in out if _re.match(_B58, a) and a not in safe)[:nft_studio.MAX_DROP]}


@app.get('/api/reputation/nft-meta/{name}')
async def nft_meta(name: str, request: Request):
    """Public metadata JSON: {id}.json for the collection, {id}-{n}.json for item n."""
    m = _re.match(r'^([a-f0-9]{12})(?:-(\d{1,6}))?\.json$', name)
    c = m and next((x for x in _nft_load()['collections'] if x['id'] == m.group(1)), None)
    if not c:
        raise HTTPException(404, 'Not found')
    site = os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/') or str(request.base_url).rstrip('/')
    return nft_studio.item_json(c, site, int(m.group(2))) if m.group(2) else nft_studio.collection_json(c, site)


# ---- Intel desk: the reputation department's database of ruggers, snipers, bundlers, funders and their crews -------
INTEL_DESK_PATH = DATA_DIR / 'intel_desk.json'
_desk = {'at': 0, 'snap': None, 'rings': [], 'actors': {}}


def _desk_build(force=False):
    """Rebuild the desk from the blocklist, funder graph and creator records (cheap: local data only). Cached 10 min;
    the saved file keeps a daily history so the owner can see the department's catch grow."""
    if not force and _desk['snap'] and time.time() - _desk['at'] < 600:
        return _desk
    creators = {}
    for key, rec in (_load().get('creators') or {}).items():
        if not str(key).startswith('solana:'):
            continue
        sc = score_creator(rec)
        if sc.get('ruggedCount') or sc.get('dumpedCount'):
            creators[rec.get('address') or key.split(':', 1)[1]] = {'rugged': sc['ruggedCount'], 'dumped': sc['dumpedCount'], 'launches': sc['tokenCount'],
                                                                    'launchTimes': [t.get('firstSeenAt') for t in (rec.get('tokens') or {}).values()]}
    actors = intel_desk.build_actors(_block_load()['wallets'], _funders_load(), creators, protected=frozenset(_protected_wallets()))
    now = time.time()
    snap = intel_desk.snapshot(actors, now)
    rg = intel_desk.rings(actors)
    _desk.update({'at': now, 'snap': snap, 'rings': rg, 'actors': actors})
    saved = _json_load(INTEL_DESK_PATH, {'history': []})
    day = time.strftime('%Y-%m-%d', time.gmtime(now))
    hist = [h for h in saved.get('history', []) if h.get('day') != day] + [{'day': day, **snap['totals']}]
    _json_save(INTEL_DESK_PATH, {'at': now, 'totals': snap['totals'], 'history': hist[-90:], 'index': snap['index'],
                                 'rings': [{k: r[k] for k in ('id', 'core', 'size', 'launchesHit', 'rugs', 'threat', 'members')} for r in rg[:200]]})
    return _desk


async def _desk_loop():
    while True:
        try:
            _desk_build(force=True)
        except Exception:
            pass
        await asyncio.sleep(1800)


@app.on_event('startup')
async def _desk_start():
    asyncio.create_task(_desk_loop())


@app.get('/api/reputation/admin/intel-desk')
async def intel_desk_view(request: Request):
    """Most wanted, crews, predicted next moves and the department's daily catch."""
    _require_admin(request)
    d = _desk_build()
    snap = {k: v for k, v in d['snap'].items() if k != 'index'}
    return {**snap, 'history': _json_load(INTEL_DESK_PATH, {'history': []}).get('history', [])[-30:]}


@app.post('/api/reputation/admin/intel-desk/sweep')
async def intel_desk_sweep(request: Request):
    _require_admin(request)
    d = _desk_build(force=True)
    return {'ok': True, 'totals': d['snap']['totals']}


@app.get('/api/reputation/admin/intel-desk/actor/{address}')
async def intel_desk_actor(request: Request, address: str):
    _require_admin(request)
    d = _desk_build()
    a = d['actors'].get(address)
    if not a:
        raise HTTPException(404, 'Not in the database (no strikes, no funding links, no bad launches).')
    ring = next((r for r in d['rings'] if address in r['members']), None)
    return {**intel_desk.public_actor(a, time.time()), 'fundedWallets': a['funded'][:50], 'mints': sorted(a['mints'])[:50], 'crew': ring}


@app.get('/api/reputation/intel/check')
async def intel_check(addresses: str = Query('', max_length=6000)):
    """Which known ruggers / snipers / funders (and crews) are in this list of wallets. Used by FeeCat, shield, chat."""
    d = _desk_build()
    wanted = [a for a in dict.fromkeys(x.strip() for x in addresses.split(',')) if _re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', a)][:150]
    return intel_desk.check(d['snap']['index'], d['rings'], wanted)


# ---- FEELESS cards: every badge + season drop as a 3D card (front art, back lore + money) ----------------------
CARDS_PATH = DATA_DIR / 'badge_cards.json'
_cards_cache: dict = {}


def _card_defaults() -> dict:
    """Every card that exists: catalog badges, custom awards, built-ins seen lately, season + weekly drops."""
    out, holders = {}, {}
    for b in BADGE_CATALOG:
        out[f"badge:{b['id']}"] = badge_cards.default_badge_card(b)
    for a, items in (_admin_load().get('badges') or {}).items():
        for b in items.values():
            k = f"badge:{b['id']}"
            out.setdefault(k, badge_cards.default_badge_card({**b, 'tier': 4 if b.get('tone') == 'gold' else 3}))
            holders[k] = holders.get(k, 0) + 1
    for a, (at, rec) in list(_badge_cache.items()):
        if time.time() - at < 86400:
            for b in (rec or {}).get('badges', []):
                k = f"badge:{b['id']}"
                out.setdefault(k, badge_cards.default_badge_card(b))
                holders[k] = holders.get(k, 0) + 1
    col = _json_load(COLLECTION_PATH, {})
    for s in _seasons()['seasons']:
        out[f"season:{s['id']}"] = badge_cards.default_season_card(s)
        for w in _season_weeks(s):
            out[f"week:{s['id']}:w{w['week']}"] = badge_cards.default_week_card(s, w)
    for items in col.values():
        for it in items:
            k = _collection_card_key(it)
            if k:
                holders[k] = holders.get(k, 0) + 1
    return out, holders


def _collection_card_key(it):
    if it.get('kind') == 'season':
        return f"season:{it.get('season')}"
    if it.get('kind') == 'weekly':
        return f"week:{it.get('season')}:w{it.get('week')}"
    return None


def _cards_all() -> dict:
    hit = _cards_cache.get('all')
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    defaults, holders = _card_defaults()
    edits = _json_load(CARDS_PATH, {})
    pools = _pools()['pools']; d = _seasons()
    season_pct = {s['id']: float(s.get('badgeRewardPct') or 0) for s in d['seasons'] if s.get('reserveWallet')}
    cards = {k: {**badge_cards.merge(v, edits.get(k)), 'holders': holders.get(k, 0), **badge_cards.card_money(k, pools, d.get('reservePayouts') or {}, season_pct)}
             for k, v in defaults.items()}
    _cards_cache['all'] = (time.time(), cards)
    return cards


@app.get('/api/reputation/cards')
async def cards_catalog():
    """Every FEELESS card with its look, lore, holders and money (what it earns + earned so far per holder)."""
    return {'cards': list(_cards_all().values()), 'designs': list(badge_cards.DESIGNS), 'rarities': list(badge_cards.RARITIES)}


@app.get('/api/reputation/cards/{address}')
async def cards_of(address: str):
    """The cards this wallet holds, with what THIS wallet has earned from each."""
    me = primary_of(address)
    cards = _cards_all()
    held = {}
    try:
        for b in (await wallet_badges(address)).get('badges', []):
            held[f"badge:{b['id']}"] = {'why': b.get('why')}
    except Exception:
        pass
    for bid, b in ((_admin_load().get('badges') or {}).get(address) or {}).items():
        held[f'badge:{bid}'] = {'why': b.get('why')}
    for it in _json_load(COLLECTION_PATH, {}).get(me, []):
        k = _collection_card_key(it)
        if k:
            held[k] = {'why': it.get('how'), 'rarity': it.get('rarity'), 'rank': it.get('rank'), 'tier': it.get('tier'), 'rewardSol': it.get('rewardSol'), 'at': it.get('at')}
    mine_paid = {}
    for p in _pools()['pools']:
        for po in p.get('payouts') or []:
            if any(r.get('address') == me for r in po.get('rows') or []):
                for k, v in (po.get('perKey') or {}).items():
                    mine_paid[k] = mine_paid.get(k, 0) + v
    out = []
    for k, h in held.items():
        c = cards.get(k)
        if not c:
            continue
        mine = h.get('rewardSol') if k.startswith('season:') and h.get('rewardSol') else mine_paid.get(k, 0)
        out.append({**c, **({'rarity': h['rarity']} if h.get('rarity') else {}), 'why': h.get('why'), 'rank': h.get('rank'), 'tier': h.get('tier'), 'earnedMine': round(float(mine or 0), 6)})
    order = {r: i for i, r in enumerate(reversed(badge_cards.RARITIES))}
    out.sort(key=lambda c: (order.get(c['rarity'], 9), c['title']))
    return {'address': me, 'cards': out}


@app.put('/api/reputation/admin/cards/{key:path}')
async def admin_card_edit(request: Request, key: str):
    """Edit a card's look + lore everywhere it shows. Holders keep it; money rules stay in pools / reserve."""
    admin = _require_admin(request)
    if not _re.match(r'^(badge:[a-z0-9-]{1,40}|season:[\w-]{1,20}|week:[\w-]{1,20}:w\d{1,2})$', key):
        raise HTTPException(400, 'Unknown card.')
    edit = badge_cards.clean_edit(await request.json())
    async with _admin_lock:
        d = _json_load(CARDS_PATH, {}); d[key] = {**(d.get(key) or {}), **edit}; _json_save(CARDS_PATH, d)
        ad = _admin_load(); _audit(ad, admin, 'card-edit', f"{key} → {edit.get('title', '')} {edit.get('design', '')}".strip()); _admin_save(ad)
    _cards_cache.pop('all', None)
    _badge_cache.clear()   # chat + profile badges pick up the new name / glyph
    return _cards_all().get(key) or {'key': key, **edit}


# ---- Circle wallets: names, descriptions, sends (owner-only, audited) -----------------------------------
CIRCLE_META_PATH = DATA_DIR / 'circle_meta.json'


class CircleMetaIn(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    description: str = Field(default='', max_length=200)


@app.put('/api/reputation/admin/circle/wallets/{wid}')
async def circle_wallet_meta(request: Request, wid: str, p: CircleMetaIn):
    me = _require_owner(request)
    try:
        await _circle('POST', '/wallets/rename', {'id': wid, 'name': p.name})
    except HTTPException:
        pass  # Circle rename is best effort; the FEELESS label below is what the HQ shows
    d = _json_load(CIRCLE_META_PATH, {})
    d[wid] = {'name': p.name, 'description': p.description, 'at': time.time()}
    _json_save(CIRCLE_META_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'circle-meta', f'{wid[:8]} → {p.name}'); _admin_save(ad)
    return {'ok': True, **d[wid]}


CIRCLE_DEST_PATH = DATA_DIR / 'circle_destinations.json'


async def _circle_destinations(circle_wallets=None) -> list:
    d = _seasons()
    if circle_wallets is None:
        try:
            circle_wallets = (await _circle('GET', '/wallets')).get('wallets') or []
        except HTTPException:
            circle_wallets = []
    snap = (_pulse_cache.get('owner') or (0, {}))[1]   # fee account owners, as last read on-chain by the money pulse
    fee_owners = [f['owner'] for f in snap.get('feeAccounts') or [] if f.get('owner')]
    return money_pulse.known_destinations(sorted(_owner_wallets()), sorted(_admin_wallets()), fee_owners,
                                          [(f"Season reserve · {x['name']}", x['reserveWallet']) for x in d['seasons'] if x.get('reserveWallet')],
                                          [(f"Badge pool · {x['name']}", x['wallet']) for x in _pools()['pools']],
                                          _json_load(ROUTES_PATH, {'routes': []}).get('routes', []), circle_wallets,
                                          _json_load(CIRCLE_DEST_PATH, {'saved': []}).get('saved', []))


@app.get('/api/reputation/admin/circle/destinations')
async def circle_destinations(request: Request):
    """Where a Circle wallet may send: HQ wallets + ones the owner saved."""
    _require_owner(request)
    return {'destinations': await _circle_destinations()}


class CircleDestIn(BaseModel):
    address: str
    label: str = ''
    remove: bool = False


@app.post('/api/reputation/admin/circle/destinations')
async def circle_destination_save(request: Request, p: CircleDestIn):
    me = _require_owner(request)
    if not (_re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.address) or _re.match(r'^0x[0-9a-fA-F]{40}$', p.address)):
        raise HTTPException(400, 'That is not a wallet address.')
    d = _json_load(CIRCLE_DEST_PATH, {'saved': []})
    d['saved'] = [x for x in d.get('saved', []) if x['address'] != p.address]
    if not p.remove:
        d['saved'] = (d['saved'] + [{'address': p.address, 'label': (p.label or 'Saved wallet')[:40], 'by': me, 'at': time.time()}])[-50:]
    _json_save(CIRCLE_DEST_PATH, d)
    ad = _admin_load(); _audit(ad, me, 'circle-dest', f"{'removed' if p.remove else 'saved'} {p.address[:6]}… {p.label[:20]}"); _admin_save(ad)
    return {'saved': d['saved']}


@app.get('/api/reputation/admin/circle/meta')
async def circle_meta_get(request: Request):
    _require_owner(request)
    return _json_load(CIRCLE_META_PATH, {})


class CircleSendIn(BaseModel):
    walletId: str
    tokenId: str
    to: str
    amount: str
    confirm: str = ''          # must repeat the destination's last 4 characters


@app.post('/api/reputation/admin/circle/transfer')
async def circle_transfer(request: Request, p: CircleSendIn):
    me = _require_owner(request)
    if not (_re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', p.to) or _re.match(r'^0x[0-9a-fA-F]{40}$', p.to)):
        raise HTTPException(400, 'Destination must be a wallet address.')
    if p.confirm != p.to[-4:]:
        raise HTTPException(400, 'Type the last 4 characters of the destination to confirm.')
    dest = {x['address'] for x in await _circle_destinations()}
    if p.to not in dest:
        raise HTTPException(403, 'Circle wallets only send to FEELESS wallets or wallets you saved. Save this address first.')
    if not _re.match(r'^\d+(\.\d+)?$', p.amount) or float(p.amount) <= 0:
        raise HTTPException(400, 'Amount must be a positive number.')
    out = await _circle('POST', '/transfer', {'walletId': p.walletId, 'tokenId': p.tokenId, 'to': p.to, 'amount': p.amount, 'idempotencyKey': str(uuid.uuid4())})
    ad = _admin_load(); _audit(ad, me, 'circle-send', f'{p.amount} from {p.walletId[:8]} to {p.to[:6]}…'); _admin_save(ad)
    return out
