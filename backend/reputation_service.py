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
import name_lock as _name_lock   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
import agent_deposit as _deposit   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
import collective_pool as _cpool
import collective_stake as _stake
import collective_stash as _stash   # noqa: F401  (read by rep_* modules as rs._stash)
import looks as _looks   # 🎨 the site's looks: Plasma default, free + advanced (looks.py)   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
import reserve_pool
import perf
import verify
import launch_meta   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
import fee_report
import money_pulse
import badge_cards
import intel_desk
import nft_studio
import coin_meta
from ecosystem import ecosystem_mints
import asyncio
import threading   # noqa: F401  (read by rep_ai as rs.threading)
import math   # noqa: F401  (read by rep_prime as rs.math)
import contextvars
import trade_fills   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
import collections
import json
import shutil   # noqa: F401  (read by rep_ai, rep_model_lab as rs.shutil)
import os
import time
import uuid
from pathlib import Path
import random   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
from typing import List, Optional

import httpx
import ds_pace
import http_ctx
http_ctx.install()   # ⚡ every httpx client in this process shares ONE TLS context (a new client re-read the CA bundle)
import launchpad_board as _launchpad_board   # noqa: F401  (read by rep_ai, rep_fuse as rs._launchpad_board)
ds_pace.install(110, 20)   # 📡 this process's share of DexScreener's ~300/min per IP (market service takes 150)
from fastapi.responses import JSONResponse, Response, StreamingResponse   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
from urllib.parse import quote   # noqa: F401  (read by rep_public_reads as rs.quote)
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
import sql_store as _sqls_hits   # 🚦 SITE-8: per-device limits shared by every worker
_LEAD = _sqls_hits.Leader(lambda: DATA_DIR / 'loops.leader')   # 👑 SITE-8: only ONE worker runs the background loops (startup handlers below)
_HITS = lambda ns: _sqls_hits.SharedHits(lambda: DATA_DIR / 'ip_hits.json', ns)   # noqa: E731
STORE_PATH = DATA_DIR / 'reputation.json'

# Solana RPC pool + retrying client live in chain_rpc.py (one module per job); imported here so every caller is unchanged.
import loop_lag as _loop_lag
import chain_rpc as _chain   # noqa: F401  (read by rep_admin_reads, rep_admin_routes as rs._chain)
import hq_auth as _hq_auth
from chain_rpc import quota_state as _rpc_quota_state, RPC_POOL, KEEPER_PUBLIC as _KEEPER_PUBLIC, _alchemy, _dedicated, _rpc_cooldown_until, _next_rpc_endpoint, _rpc, broadcast as _rpc_broadcast, rpc_priority as _krpc  # noqa: F401

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


_store_dirty = {'on': False}


def _save(store: dict):
    """⚡ Debounced: /observe used to rewrite the 1.8 MB store on EVERY call (208 saves in 5 min).
    Readers get the new copy at once through the parse cache; the file is written ≤ every 15s
    (`_store_flush_loop`) and on stop. Tests write at once."""
    if os.environ.get('PYTEST_CURRENT_TEST') or not STORE_PATH.exists():
        return _save_now(store)
    st = STORE_PATH.stat()
    _parse_cache[str(STORE_PATH)] = ((st.st_mtime_ns, st.st_size), store)
    _store_dirty['on'] = True


def _store_flush():
    if _store_dirty['on']:
        hit = _parse_cache.get(str(STORE_PATH))
        if hit:
            _store_dirty['on'] = False
            _save_now(hit[1])


async def _store_flush_loop():
    while True:
        await asyncio.sleep(15)
        try:
            _store_flush()
        except Exception:
            pass


def _save_now(store: dict):
    t0 = time.perf_counter()
    STORE_PATH.write_text(json.dumps(store))   # ⚡ no indent: an indented dump runs the pure-Python encoder (6.7s stalls on 2.2 MB)
    st = STORE_PATH.stat()
    _parse_cache[str(STORE_PATH)] = ((st.st_mtime_ns, st.st_size), store)   # what was written IS the current version: no re-parse
    _json_cost_note('save', STORE_PATH, t0)


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
                    tx = await _rpc(http, 'getTransaction', [oldest, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}])
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
            tx = await _rpc(http, 'getTransaction', [oldest, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1}])
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


app.middleware('http')(http_ctx.sec_headers)   # 🔒 nosniff + no-referrer on every response (SITE-9)
# 🚦 writes are limited by `guard` (90 a minute per IP, local services exempt; it trusts X-Forwarded-For only with FEELESS_TRUST_PROXY=1).
# A second limiter here (2026-11-10) read X-Forwarded-For from anyone, so a fake header dodged it: removed (SITE-9, same day).


from starlette.middleware.gzip import GZipMiddleware as _GZip
app.add_middleware(_GZip, minimum_size=1024)   # ⚡ every list over 1KB goes compressed (a 287KB trench list was sent raw)
app.add_middleware(CORSMiddleware, **__import__('guard').cors_kwargs(), allow_methods=['*'], allow_headers=['*'])
app.add_middleware(__import__('http_armor').HttpArmor, is_internal=__import__('guard').is_internal)   # 🛡 SITE-2: body caps, slow-client 408, per-route bulkhead (outermost)


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
    try:
        _rig_apply()   # 🎛 the owner's model rig, live from the first call
    except Exception as e_:
        print('rig:', str(e_)[:80])
    _LEAD.start(_refresh_all_markets)
    asyncio.create_task(_store_flush_loop())
    if not os.environ.get('PYTEST_CURRENT_TEST'):
        _LEAD.start(_code_health_loop)
        _loop_lag.WATCH.start(asyncio.get_running_loop())
        asyncio.create_task(_loop_lag_dump())


async def _loop_lag_dump():
    # the catcher's own page for checking without an HQ sign-in (function names only, never data)
    while True:
        await asyncio.sleep(30)
        try:
            await asyncio.to_thread(_json_save, DATA_DIR / 'loop_lag.json', {**_loop_lag.WATCH.view(), 'json': sorted(([k, v[0], round(v[1], 2)] for k, v in _json_cost.items()), key=lambda r: -r[2])[:25]})
        except Exception:
            pass
        try:   # 🩺 what browsers FEEL (the lag catcher's own reports, last 15 min): routes by p95, pages by fps / blocked ms, the FX governor's counts — route + page names only
            cut_ = time.time() - 900
            rec_ = [x for x in _perf_samples if x['at'] >= cut_]
            fx_ = [x.get('fx') for x in rec_ if x.get('fx')][-6:]
            await asyncio.to_thread(_json_save, DATA_DIR / 'perf_view.json', {**perf.summarize(rec_), 'fx': fx_, 'at': time.time()})
        except Exception:
            pass


LEADERBOARD_VIEWS = ('trusted', 'flagged', 'serial', 'rising', 'active', 'feeless')
RISING_WINDOW_SECONDS = 60 * 60 * 24 * 2   # first observed within the last 2 days


class WatchPayload(BaseModel):
    ownerWallet: str
    session: str = ''
    chain: str
    address: str
    notifyNewToken: bool = True
    notifyFlag: bool = True


class UnwatchPayload(BaseModel):
    ownerWallet: str
    session: str = ''
    chain: str
    address: str


CLUSTER_RESOLVE_BATCH = 8   # cap RPC calls per request so this stays fast


class VotePayload(BaseModel):
    wallet: str
    itemId: str
    session: str = ''


UPLOAD_DIR = DATA_DIR / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_TYPES = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif'}


OWNER_GIF_CAP = 250_000_000   # memory guard only: the creator's GIFs are not size-limited in practice


def upload_cap(mime: str, role: str) -> int:
    """Bytes allowed per upload. Everyone: 15 MB stills / 40 MB GIFs (owner 2026-10-26: "backgrounds shouldn't have an MB cap" — uploads need no sign-in,
    so a ceiling stays against disk-filling; 20 / hour / IP). HQ admins: 40 MB. The creator: 40 MB stills, GIFs up to the memory guard."""
    if role == 'owner':
        return OWNER_GIF_CAP if mime == 'image/gif' else 40_000_000
    if role == 'admin':
        return 40_000_000
    return 40_000_000 if mime == 'image/gif' else 15_000_000


class UploadPayload(BaseModel):
    dataUrl: str


_upload_ip = _HITS('upload')


async def _ip_hit(store, request, n, win):
    """🔒 Audit #8: one per-device limiter (real IP via _guard.request_ip). → False when this device used its n calls in win seconds.
    🚦 SITE-8: `store` is a SharedHits, so the limit holds across every worker; the transaction runs in a thread (never stalls the loop)."""
    ip = _guard.request_ip(request)
    try:
        return await asyncio.to_thread(store.hit, ip, n, win)
    except Exception:   # the shared file is locked/broken: keep limiting in this process instead of failing the route
        now = time.time(); k = (store.ns, ip)
        hits = [t for t in _IP_HIT_LOCAL.get(k, []) if now - t < win]
        if len(hits) >= n:
            return False
        _IP_HIT_LOCAL[k] = hits + [now]
        if len(_IP_HIT_LOCAL) > 5000:
            _IP_HIT_LOCAL.clear()
        return True


_IP_HIT_LOCAL: dict = {}


_intel_cache: dict = {}
_launch_facts: dict = {}   # mint → {creator, bundled, snipers, createSlot, historyComplete, at} — read once, kept on disk
_flag_hold: dict = {}      # mint → (at, {wallet: % held})
FLAG_HOLD_TTL = 900.0
LAUNCH_RETRY_SEC = 6 * 3600.0   # a launch read that could not reach the launch is tried again after 6h, not every 15-min re-scan
SIG_PAGES = 16   # (2026-10-18: 8 left 35% of busy launch coins unread — the agents traded them blind on bundles / snipers) launch facts: page back up to 8,000 txs to reach a coin's creation (read once per coin, kept on disk)
INTEL_TTL = 900   # holders re-read every 15 min (launch facts are read once): a re-scan is 4 calls. 2026-10-08: at 300s a ~100-coin board needed 1.3 calls/s of re-scans against a 0.5/s budget, so 184 of 200 feed coins (14 of 18 RUNNING ones) read 'not scanned yet' and nothing running could ever be bought
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


def _early_buy(tx, payer, mint, supply):
    """🕵 One early transaction → {w, slot, sol, pct} when the payer RECEIVED this coin (a buy), else None. Public tx data only."""
    try:
        meta = tx.get('meta') or {}
        amt = lambda bals: sum(_fuse._f((b.get('uiTokenAmount') or {}).get('uiAmount')) for b in bals or [] if b.get('mint') == mint and b.get('owner') == payer)
        got = amt(meta.get('postTokenBalances')) - amt(meta.get('preTokenBalances'))
        if got <= 0:
            return None
        pre, post = meta.get('preBalances') or [0], meta.get('postBalances') or [0]
        sol = max(0.0, (_fuse._f(pre[0]) - _fuse._f(post[0])) / 1e9)
        return {'w': payer, 'slot': tx.get('slot'), 'sol': round(sol, 4), 'pct': round(got / supply * 100, 3) if supply else None}
    except Exception:
        return None


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
    _LEAD.start(_refresh_globe)


class FeelessLaunchPayload(BaseModel):
    chain: str = 'solana'
    wallet: str
    mint: str
    symbol: Optional[str] = None
    signature: Optional[str] = None
    rail: Optional[str] = None  # 'feeless' (Meteora DBC config) or 'pump'
    profile: Optional[dict] = None  # {description, bannerUrl, website, twitter, telegram} from the launch form


def _any_agent_wallets():
    """🚫 Every AI agent's OWN wallet (feecats.json, parsed once per version). An agent may launch coins on any other site, but these
    wallets can never launch a coin or make an agent ON FEELESS (owner 2026-10-31: "hardcode that the general agents can't")."""
    store = _json_load(DATA_DIR / 'feecats.json', {})
    return {str((c.get('agentWallet') or {}).get('address')) for c in (store.get('cats') or {}).values() if (c.get('agentWallet') or {}).get('address')}


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
    session: str = ''


def _push_prefs(prefs, prev, session):
    """🔒 A phone only gets a wallet's alerts if it proved that wallet (its signed session) or this same phone already held it. A claim without proof keeps the watchlist alerts and drops the wallet."""
    out = dict(prefs or {}); claim = str(out.get('address') or '')
    if claim and claim != (prev or {}).get('address'):
        owner = session_address(session) if session else None
        if not owner or primary_of(owner) != primary_of(claim):
            out.pop('address', None)
    return out


class PushUnsubscribe(BaseModel):
    endpoint: str


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
    _LEAD.start(_evaluate_alerts)


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
                        if time.time() - c['at'] < 3 * 86400:   # 📈 the receipt's mini chart (street coin cards draw it)
                            _stc.trail_add(c, px, time.time())
                    _award_feed_call(c)
                _calls_save(d)
        except Exception as exc:
            print('calls refresh error', exc)
        await asyncio.sleep(60)


@app.on_event('startup')
async def _start_calls():
    _LEAD.start(_refresh_calls)


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
    session: Optional[str] = None


# ---- Wallet profiles (customizable, wallet-signed) ------------------------------
PROFILE_PATH = DATA_DIR / 'profiles.json'
_profile_lock = asyncio.Lock()
HEX = set('0123456789abcdefABCDEF')


_prof_docs: dict = {}


def _prof():
    """🗄 SITE-8: wallet profiles, one row per wallet in SQLite (profiles.db). A save changes ONE wallet in one transaction, so any number
    of workers can save at once and none wipes another's (the old whole-file write did). profiles.json moved in once and is kept read-only."""
    import sql_store as _sqls
    k_ = str(PROFILE_PATH)
    if k_ not in _prof_docs:
        _prof_docs[k_] = _sqls.Docs(PROFILE_PATH, inner='profiles')
    return _prof_docs[k_]


def _profiles_load():
    """Read-only view {'profiles': {wallet: profile}} (cached until anybody writes). Never change it: write with _prof().update(wallet, fn)."""
    try:
        return {'profiles': _prof().all()}
    except Exception:
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


_verify_evm = _hq_auth.verify_evm            # 🔐 wallet signatures live in hq_auth.py (pure); the old names stay for callers + tests
_verify_solana = _hq_auth.verify_solana


def _verify_wallet(address: str, message: str, signature: str) -> bool:
    if _re.match(r'^0x[0-9a-fA-F]{40}$', address or ''):
        return _verify_evm(address, message, signature)
    return _verify_solana(address, message, signature)


class FeaturedBadgesIn(BaseModel):
    address: str
    session: str
    badges: list = []


# 𝕏 SIGN IN WITH X (owner 2026-10-26: "a true account link so they're actually signed in to X, not an API"): X's own OAuth 2.0 (PKCE). FEELESS asks
# only to read who you are (users.read), stores your verified @handle on your profile and keeps NO token. Needs the owner's X app: X_CLIENT_ID
# (+ X_CLIENT_SECRET for a confidential app) and the callback URL X_REDIRECT_URI (default PUBLIC_SITE_URL/api/reputation/x/oauth/callback).
_x_states: dict = {}


def _x_redirect():
    return os.getenv('X_REDIRECT_URI') or f"{(os.getenv('PUBLIC_SITE_URL') or '').rstrip('/')}/api/reputation/x/oauth/callback"


# ---- Evidence-based blocklist of snipers and bundlers ----------------------------
BLOCK_PATH = DATA_DIR / 'blocklist.json'
_block_lock = asyncio.Lock()
AUTO_BLOCK_STRIKES = 3


def _protected_wallets():
    """FEELESS's own wallets can never be blocklisted (its launches buy in the mint slot by design)."""
    extra = [a.strip() for a in os.environ.get('FEELESS_PROTECTED_WALLETS', '').split(',') if a.strip()]
    return set(_owner_wallets()) | set(_admin_wallets()) | {FEE_CREATOR_WALLET} | set(extra)


_block_view = {'key': None, 'd': None}


def _block_load():
    # ⚡ ONE filtered view per on-disk version: the runner board asks per creator, and rebuilding a 100K-wallet dict per row
    # blocked the event loop for up to 10s (loop_lag, 2026-10-12). Writers mutate the view, then write the file → a new version.
    d = {'wallets': {}}; ver = None
    if BLOCK_PATH.exists():
        try:
            d = _cached_json(BLOCK_PATH); ver = _parse_cache[str(BLOCK_PATH)][0]
        except Exception:
            ver = None
    safe = _protected_wallets()
    key = (ver, frozenset(safe))
    if ver is not None and _block_view['key'] == key:
        return _block_view['d']
    if _block_dirty['on'] and _block_view['d'] is not None:   # the view is being replaced: what it learned goes to disk first
        _block_flush(_block_view['d'])
        return _block_load()
    out = {**d, 'wallets': {w: r for w, r in (d.get('wallets') or {}).items() if w not in safe}}
    if ver is not None:
        _block_view.update(key=key, d=out)
    return out


BLOCK_SAVE_SEC = 300   # scanner strikes only (a person's report + shutdown write at once): a 15 MB dump every minute was ~0.5s of blocked loop each
_block_dirty = {'on': False, 'at': 0.0}


def _block_flush(d=None):
    d = d if d is not None else _block_view['d']
    if d is None:
        return
    t0 = time.perf_counter()
    tmp = BLOCK_PATH.with_suffix('.tmp'); tmp.write_text(json.dumps(d)); tmp.replace(BLOCK_PATH)
    st = BLOCK_PATH.stat(); ver = (st.st_mtime_ns, st.st_size)
    _parse_cache[str(BLOCK_PATH)] = (ver, d)   # what was written IS the current version: no 14 MB re-parse, no view rebuild
    _block_view.update(key=(ver, frozenset(_protected_wallets())), d=d)
    _block_dirty.update(on=False, at=time.time())
    _json_cost_note('save', BLOCK_PATH, t0)


def _block_save(d, now=False):
    """⚡ Strikes recorded by the scanner are written at most once a minute (each write was 14 MB serialized + parsed again on the event
    loop, several times a minute). The view in memory is the truth in between; a report by a person and a shutdown write at once."""
    _block_dirty['on'] = True
    if now or d is not _block_view['d'] or os.environ.get('PYTEST_CURRENT_TEST') or time.time() - _block_dirty['at'] >= BLOCK_SAVE_SEC:
        _block_flush(d)


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
        _block_save(d)
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
                _block_save(bl)


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
    _is_crew, _crew_ok = _crew_room_ok(room, address or '')
    if _is_crew:
        return {'gated': True, 'allowed': _crew_ok, 'symbol': 'crew', 'minUsd': 0, 'holdingUsd': None}
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
    return _hq_auth.is_staff(address, _admin_wallets() if address else [], primary_of)


async def _alpha_allowed(room: str, address: str) -> bool:
    r = _ALPHA.get(room)
    if not r:
        return True
    a = primary_of(address or '')
    return bool(a) and (_is_staff(a) or await _fee_usd(a) >= r['minUsd'])


@app.exception_handler(RuntimeError)
async def _rpc_busy(request: Request, exc: RuntimeError):
    # The shared Solana RPC pool is rate-limited: a clear, retryable 503 instead of a crash.
    if 'RPC pool exhausted' in str(exc):
        return JSONResponse({'detail': 'Solana data is busy — try again in a few seconds.'}, status_code=503, headers={'Retry-After': '5'})
    raise exc


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


class InternalNotify(BaseModel):
    address: str = Field(..., max_length=64)
    kind: str = Field('cat', max_length=16)
    text: str = Field(..., max_length=400)
    url: str = Field('', max_length=200)
    once: str = Field('', max_length=80)


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


_jup_tok_cache: dict = {}   # mint → (at, Jupiter token row) — 60s
_pair_mint: dict = {}       # pairAddress → mint, learned from every pair answer (the fallback looks coins up by mint)


# ↪ moved to rep_fuse.py: _jup_tokens, _fuse_pairs, _fuse_risky, _fuse_view, _creator_warn


_fuse_discover_cache = {}
FUSE_DISCOVER_Q = {'solana': ('SOL', 'USDC', 'raydium', 'orca', 'meteora', 'pumpswap', 'JUP', 'BONK')}


# ↪ moved to rep_fuse.py: _fuse_discover_pairs


PICK_DEAD_VOL1H = 3_000.0   # a launch coin trading under this an hour is dead for the picker — 6 of the 11 buy-bottom rows were (2026-10-08)
PICK_SCAN_TOP = 15          # the top rows of the list the owner opens get a holder scan queued (one scan per coin in flight)


import coin_clean as _clean   # noqa: F401  (read by rep_fuse as rs._clean)


import jup_audit as _ja
_jup_facts: dict = {}   # mint → (at, jup_audit.facts) — Jupiter's audit for every listed coin (holder %, dev record, organic flow)
JUP_FACTS_TTL = 180


# ↪ moved to rep_fuse.py: _jup_lite, _cand_map, _read_for


_coin_read_cache: dict = {}   # mint → (at, read) — 15s


COIN_READ_JUP_SEC = 1.5   # coin-read p95 was 6.5s (perf_view 2026-10-17): Jupiter's public lane rate-limited, the header waited for it


import chart_wallets as _cw
import consigliere as _cg   # noqa: F401  (read by rep_predict as rs._cg)
_cw_cache: dict = {}


# ↪ moved to rep_fuse.py: _up_vital


_PUMP_LINKS: dict = {}   # 🔗 mint → (at, {site, x, tg}) from Pump's own coin record (Jupiter often has none: $UNITS)
PUMP_LINKS_TTL = 3600
PUMP_LINKS_PER_PASS = 12


# ↪ moved to rep_fuse.py: _pump_links_put, _pump_links_warm, _clean_rows, _holder_facts


SIGNAL_LENSES, SIGNAL_CACHE_SEC = ('double', 'calls', 'fed'), 30   # 📣 the Pump-signal lists change once a minute at the source: one build serves 30s (no Jupiter burst)
LIST_CACHE_SEC = 10   # ⚡ every viewer of a pick list shares one build for 10s (the screens re-read every 20s)
_disc_cache: dict = {}
LIST_STALE_SEC = 180   # ⚡ a list past its cache time still answers AT ONCE for this long while ONE rebuild runs behind it
_LIST_REBUILD = contextvars.ContextVar('list_rebuild', default=False)
_list_flight: dict = {}


# ↪ moved to rep_fuse.py: _list_now
_best_rows: list = []   # 🏆 the engine's banger list from the last real-card tick (clean entry + tape-checked), best first


PICK_TAPE_TOP = 12   # 🌊 the tape is read for the first 12 rows of a list (one batched call, 12s cache)


# ↪ moved to rep_fuse.py: _with_tv


EXHALE_READS = ('DRYING UP', 'COOLING')   # the only reads with a positive 1h record (2026-10-09: +1.9% / 62% up · +0.6% / 57% up)


# ↪ moved to rep_fuse.py: _bangers


WAVE_PROVE_MIN = 10   # 🌊 the engine seats a wave leader only once the list's own 1h record is positive over this many settled coins


# ↪ moved to rep_fuse.py: _wave_rows, _prebreak_rows, _prebreak_ready, _wave_ready


EXHALE_ORGANIC_MIN = 10.0   # % of the hour's volume that is real (Jupiter's organic read) — under it the "cooling" is wash-traded flow


# ↪ moved to rep_fuse.py: _exhale_rows, _procall_rows


LIVE_MIN_VOL5M, LIVE_MIN_CHG5M, LIVE_MIN_BUY, LIVE_MIN_TX1H = 3000.0, 3.0, 50.0, 60


# ↪ moved to rep_fuse.py: _live_movers


_why_cache: dict = {}      # mint → (at, answer) — a checked coin is free for WHY_TTL (everyone reads the same answer)
_why_recent: list = []     # newest checks first (mint, symbol, headline, verdict, move, img, at) — "Latest checks"
_why_quota: dict = {}      # ip → [day, count] — new checks a day per visitor
_why_busy: dict = {}       # mint → asyncio.Task (one check per coin in flight)
WHY_TTL, WHY_FREE_DAY = 1800, 5


# ↪ moved to rep_fuse.py: _why_pair, _why_build


SWAP_BAD_READS = {'WASH TRADED', 'BLOW-OFF TOP', 'TREND DOWN', 'DEAD DIP'}   # + arena_prime.TRENCH_BAD_READS (added at use: module order)


# ↪ moved to rep_fuse.py: _swap_clean, _fuses_discover_raw


_majors_cache: dict = {'at': 0.0, 'rows': []}


# ↪ moved to rep_fuse.py: _majors_rows


class FusePreview(BaseModel):
    pools: list
    sol: float = 1.0
    manual: bool = False     # HQ only: use the pools' own weights instead of auto
    runners: bool = False    # Runner add-on: bolt the top 2 runners on as a small slice
    runnerMints: list = []   # Fuse card: the runners YOU picked (≤3 traders / ≤6 HQ), each from the live board
    runnerSlice: float = 20.0


# ↪ moved to rep_fuse.py: _is_admin_req


class FuseEvolveIn(BaseModel):
    style: str = 'yield'
    legs: int = Field(default=3, ge=2, le=10)
    generations: int = Field(default=16, ge=1, le=40)
    population: int = Field(default=32, ge=8, le=80)
    sol: float = Field(default=0.05, gt=0, le=1000)
    chain: str = 'solana'
    seed: int = 0
    bloodline: bool = False


# ---- FUSE HQ (backend/fuse_hq.py): real Fuse P&L, paper arena, bloodlines, health, trader "Find my best 3" -------------
import fuse_hq as _hq
import crowd as _crowd
FUSE_HQ_PATH = DATA_DIR / 'fuse_hq.json'   # {'positions': [], 'arena': [], 'bloodline': []}


# ↪ moved to rep_fuse_hq.py: _prime_cards, _real_card


FUSE_CHAT_POSTED_PATH = DATA_DIR / 'fuse_chat_posted.json'   # 🧈 _fuse_chat's once-per-key memory (was inside fuse_hq.json)
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


class FuseReceiptIn(BaseModel):
    address: str
    legs: list          # [{sig, symbol, usd, tokens, feeUsd, networkUsd}] as quoted on the review screen


class FuseCloseIn(BaseModel):
    address: str
    session: str
    id: str
    signatures: list


class FuseGuardIn(BaseModel):
    address: str
    session: str
    id: str
    tp: float = 0
    sl: float = 0
    trail: float = 0
    off: bool = False
    rebalance: float = 0      # auto-rebalance: alert when the card drifts this many points from its weights (0 = off)


# ↪ moved to rep_fuse_hq.py: _card_rules


_ledger_idx: dict = {'src': None, 'by': {}}


# ↪ moved to rep_fuse_hq.py: _ledger_by_sig, _card_fees, _exit_fee, _fuse_yield_tick, _fuse_swap_tick, _spend_round, _rounds_out_notice
# ↪ moved to rep_fuse_hq.py: _fuse_buyback_tick, _fuse_leg_tick


class FusePlanIn(BaseModel):
    address: str
    session: str
    id: str
    plan: dict


class FuseModeIn(BaseModel):
    address: str
    session: str
    id: str
    mode: str = 'hold'


class FusePaidIn(BaseModel):
    planId: str
    sigs: list


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
import coin_edge as _edge   # noqa: F401  (read by rep_coin_edge as rs._edge)
_edge_cache: dict = {}   # mint -> (at, record)
_edge_pulse: dict = {}   # mint -> (at, pulse)


# ↪ moved to rep_coin_edge.py: _edge_pulses


EDGE_STALE_SEC = 600.0     # an edge record this young is shown at once while a fresh one is built in the background
EDGE_COLD_BUDGET = 3.0     # a coin with NO record waits at most this long for pulse + verification (an incomplete record refills soon)
_edge_inflight: set = set()


_germ_seen: dict = {}    # mint -> (at, germ record): the last germ the agents read, kept 15 min after a coin leaves the desk
GERM_KEEP_SEC = 900.0


# ↪ moved to rep_coin_edge.py: _germ_rec, _edge_build, _edge_refresh, _feeback_book


class FuseYieldIn(BaseModel):
    address: str
    session: str
    id: str
    at: float = 0
    off: bool = False


# ↪ moved to rep_coin_edge.py: _fuse_guard_tick, _card_signal_tick, _fuse_guard_loop


@app.on_event('startup')
async def _fuse_guard_start():
    if not os.environ.get('PYTEST_CURRENT_TEST'):
        _LEAD.start(_fuse_guard_loop)


class FuseSwitchIn(BaseModel):
    address: str
    session: str
    id: str
    legs: list          # [{pairAddress, symbol, role, signature}] — the BUYS that land in this card


class FuseFreezeIn(BaseModel):
    address: str
    session: str
    id: str
    pairAddress: str = Field(..., max_length=64)
    frozen: bool = True


class CoinModeIn(BaseModel):
    address: str
    session: str
    id: str
    pairAddress: str = Field(..., max_length=64)
    slMode: str = Field(default='', max_length=8)   # sell | park | hold | card (= follow the card) · '' = leave as is
    tp: float | None = None                          # this coin's take-profit % (alert, one-tap) · 0 = off
    sl: float | None = None                          # this coin's stop % · 0 = off
    rotateHours: float | None = None                 # ⇄ replace this coin at most every … (5m–24h) · 0 = follow the card


# ↪ moved to rep_coin_edge.py: _hq_prices


_held_cache: dict = {}


# ↪ moved to rep_coin_edge.py: _wallet_held


_fuse_holders_cache: dict = {}


# ↪ moved to rep_coin_edge.py: _arena_settle


# ---- 🏆 Fuse seasons: weekly (Monday 00:00 UTC), cards opened that week ranked by real P&L %; top 3 crowned once ----------
_fuse_season_cache: dict = {'at': 0.0, 'data': None}


# ↪ moved to rep_seasons.py: _season_rows, _season_wins, _fuse_season_tick


_season_moves: dict = {'week': 0, 'prev': {}, 'list': []}


# ↪ moved to rep_seasons.py: _season_race


_replay_cache: dict = {}


# ↪ moved to rep_seasons.py: _series_24h


_fuse_score_cache: dict = {}


# ↪ moved to rep_seasons.py: _fuse_score


_ids_warming: set = set()


# ↪ moved to rep_seasons.py: _bred_load, _bred_tick, _fuse_autopilot_tick, _shield_alerts, _fuse_autopilot_loop


@app.on_event('startup')
async def _fuse_autopilot_start():
    if not os.environ.get('PYTEST_CURRENT_TEST'):
        _LEAD.start(_fuse_autopilot_loop)


# ↪ moved to rep_seasons.py: _card_look


_arena_best_cache: dict = {'at': 0.0, 'v': None}


_arena_mega_cache: dict = {'at': 0.0, 'data': None, 'boot': True}
ARENA_SNAPSHOT_PATH = DATA_DIR / 'arena_snapshot.json'


FUSE_ARENA_NAME = '⚔ Fuse Arena'


# ↪ moved to rep_seasons.py: _fuse_chat, _fuse_chat_tick, _battle_view


class BracketPick(BaseModel):
    address: str
    session: str
    key: str = Field(..., max_length=120)


class BattleBack(BaseModel):
    address: str
    session: str
    key: str = Field(..., max_length=120)


import arena_league as _lg


# ↪ moved to rep_seasons.py: _league_card, _league_extra, _league_playground


async def _battle_tick(now):
    """Background: when the bell rings, settle every pair (bigger move since the start wins), write W/L/D records, alert
    trader-card owners who won, then pair the stage again for the next round."""
    mega = _arena_mega_cache.get('data') or []
    d = _json_load(FUSE_HQ_PATH, {})
    b = d.get('battles') or {}
    # 📜 paper books: every fighting card is marked live at true fills (what selling it all would really pay)
    paper = dict(b.get('paper') or {})
    pairs_px = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for k in paper for l in paper[k].get('legs') or []] +
                                 [{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for r in ((d.get('league') or {}).get('field') or []) for l in r.get('legs') or [] if l.get('pairAddress')] +
                                 [{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for c in mega for l in c.get('legs') or [] if l.get('pairAddress')]) if (paper or mega) else {}
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
            _fuse_chat('fuse-lab', f"♻ {m['out']} cycled out ({m['why']}){' — ' + m['in'] + ' takes its seat on $' + format(_lg.START_USD, 'g') if m.get('in') else ''}.", f"cycle-{int(now)}-{m['outKey']}")
    restart_ = d.get('leagueReset') != LEAGUE_RESET   # 🔁 one-time: the owner restarted every Arena card's money (new season, all books back on $20)
    d['leagueReset'] = LEAGUE_RESET
    if restart_ or not league or _lg.done(league) or len(league.get('field') or []) < 2:
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
        d2['leagueReset'] = LEAGUE_RESET   # saved with the season it started — the one-time restart must never run twice
        d2['bracket'] = {'cards': bracket, 'champions': champs, 'season': season_n,
                         'picks': {} if league.get('round') == 0 else ((d2.get('bracket') or {}).get('picks') or {})}
        d2['bracketWins'] = {**(d2.get('bracketWins') or {}), **(d.get('bracketWins') or {})}
        d2['battleRecord'] = d.get('battleRecord') or {}
        d2['comebacks'] = d.get('comebacks') or d2.get('comebacks') or {}
        d2['backRecord'] = d.get('backRecord') or {}
        d2['backWins'] = {**(d2.get('backWins') or {}), **(d.get('backWins') or {})}
        _json_save(FUSE_HQ_PATH, d2)
    return results


# ↪ moved to rep_seasons.py: _arena_auto_refresh, _feecat_raw, _feecat_card, _arena_mega, _card_dna_tag, _fuse_candidates, _champ_view


_fuse_prebuilt_cache: dict = {}


# ---- FUSE RUNNERS (backend/runners.py): coins come to it — live launchpad feed → gates → lanes → rounds → paper proof --
import runners as _rn
RUNNERS_PATH = DATA_DIR / 'runners.json'      # {'rounds': [...], 'paths': {mint: [[t, price], ...]}}
_runner_live_cache = {'at': 0.0, 'data': None}
# Set only inside the background warmer's own task: it rebuilds caches while viewers keep reading the last good copy.
_FUSE_FORCE = contextvars.ContextVar('fuse_force', default=False)
_mayhem_mints: set = set()


# ↪ moved to rep_runners.py: _runner_cfg
import trench_kernel.enrich as _enr
# 🔎 THE ONE ENRICHMENT SCHEDULER (trench_kernel/enrich.py): every deep holder / launch scan in this process is asked for here, by priority,
# on a budget of RPC calls a second, with freshness that survives a restart. No caller starts a scan itself.
try:
    _ENRICH_CPS = max(0.2, float(os.environ.get('RPC_ENRICH_CPS', '') or _enr.CALLS_PER_SEC))
except ValueError:
    _ENRICH_CPS = _enr.CALLS_PER_SEC
_ENRICH = _enr.Enricher(boot_at=time.time(), calls_per_sec=_ENRICH_CPS, ttl=INTEL_TTL)
_intel_inflight = _ENRICH.inflight   # mint → when its ONE scan started (the scheduler's own book; kept under the old name for the page)
_intel_failed: dict = {}             # mint → when its last scan failed (display)
_intel_waiters: dict = {}            # mint → the future everyone waiting on that scan shares
_enrich_timer: dict = {'h': None}
ENRICH_WAIT_SEC = 14.0               # a caller that WAITS for a scan (a held / ready coin, a coin someone opened) waits at most this long


# ↪ moved to rep_runners.py: _intel_boot, _intel_fresh, _enrich_scan, _enrich_pump, _runner_intel


_runner_widen = {'level': 0, 'at': 0.0, 'log': []}


import meme_terms as _mt   # noqa: F401  (read by rep_ai, rep_crews as rs._mt)
import pg_battle as _pgb
import card_dna as _dna   # noqa: F401  (read by rep_ai, rep_public_reads as rs._dna)
MEME_PATH = DATA_DIR / 'meme_terms.json'


# ↪ moved to rep_runners.py: _meme_tick


RUNNER_SCANS = 60   # holder scans per board build (cached per coin): the busiest launch coins by 1h volume


# ↪ moved to rep_runners.py: _runner_live, _runner_live_build


_runner_hist: dict = {}   # mint → [(t, curve, top10, dev)] over the last ~20 min (new checks + kill switch)


# ↪ moved to rep_runners.py: _runner_track, _smart_buyers, _token_prices


_jup_px_cache: dict = {}


_jup_calls = {'n': 0}   # every Jupiter price request this process sent (the office reports the per-pass delta)


# ↪ moved to rep_runners.py: _jup_prices


JUDGE_STALE_SEC = 300   # a price this fresh still judges a result when every live source missed the coin this second


# ↪ moved to rep_runners.py: _judge_fill, _runner_tick, _runner_loop


@app.on_event('startup')
async def _runner_start():
    if not os.environ.get('PYTEST_CURRENT_TEST'):
        _LEAD.start(_runner_loop)
        _LEAD.start(_fuse_warm_loop)
        _LEAD.start(_agents_loop)
        _LEAD.start(_ai_loop)
        _LEAD.start(_g4_loop)
        _LEAD.start(_prime_warm)
        _LEAD.start(_prime_bell_loop)
        _LEAD.start(_real_guard_loop)


# ---- ⭐ ARENA PRIME (backend/arena_prime.py): FEELESS's top-tier cards, FULLY AUTO on paper — the proof before configs go live ----
import arena_prime as _prime


# ↪ moved to rep_prime.py: _prime_cfg, _ladder_value, _ladder_step, _prime_real_cfg


import trench as _trench

_trench_cache: dict = {'at': 0.0, 'rows': [], 'checked': []}
_runner_cands: list = []   # every runner candidate of the last board build (filled by _runner_live)
_open_meta: dict = {'at': 0.0}
_open_pairs: list = []    # every raw launch-feed pair of the last board build (the 🚪 open trench list + 📣 callouts read it)
_open_cache: dict = {'at': 0.0, 'rows': [], 'calls': {}}
TRENCH_CALLOUT_PATH = FUSE_HQ_PATH.parent / 'trench_callouts.json'


# ↪ moved to rep_prime.py: _open_board


_open_scan_memo: dict = {}   # mint → (scan checkedAt, judged) — one judgement per scan


# ↪ moved to rep_prime.py: _open_scan_judge, _jup_judge


import pump_calls as _pc

_pump_calls: dict = {'at': 0.0, 'board': {'coins': [], 'top': [], 'latest': [], 'n': 0}, 'map': {}, 'ok': 0.0}
_pump_calls_flight: dict = {}


# ↪ moved to rep_prime.py: _pump_calls_build, _pc_rows


PUMP_CALLERS_PATH = FUSE_HQ_PATH.parent / 'pump_callers.json'
PUMP_CALLERS_SAVE_SEC = 600
_pump_callers = {'st': None, 'saved': 0.0}


# ↪ moved to rep_prime.py: _pump_callers_pass
_rush_sent: dict = {}   # mint → when the owner was last told (one alert per coin per 6h)


# ↪ moved to rep_prime.py: _call_rush_alert


async def _double_rows():
    """🔥🔥 Double signal: coins that are BOTH called out by 2+ Pump users and have new launches paired with them."""
    await _pump_calls_build()
    rs = (await _feeders_build()).get('runners') or {}
    pm = _pump_calls['map']
    both = sorted((m for m in pm if m in rs and int(_fuse._f(pm[m].get('callers'))) >= 2), key=lambda m: -(pm[m].get('heat', 0) + rs[m]['score']))
    return await _mint_rows(both[:60], lambda m: {'divisionLabel': f"🔥🔥 {pm[m]['callers']} callers · {rs[m]['n']} coin{'' if rs[m]['n'] == 1 else 's'} paired", 'pc': _pc.summary(pm[m]), 'fd': rs[m],
                                                 'score': round((pm[m].get('heat', 0) + rs[m]['score']) / 2)})


# ↪ moved to rep_prime.py: _mint_rows, _pump_call_rows


import feeders as _fd

_feeders: dict = {'at': 0.0, 'board': {'runners': {}, 'kids': {}, 'seen': 0}, 'names': {}}
FEEDERS_TTL = 120


# ↪ moved to rep_prime.py: _feeders_build


def _fd_rows(rows):
    """🧲 `fd` on a runner new launches are paired with · ⛓ `pairedWith` on a coin launched against a runner. Cache read only. In place."""
    b = _feeders['board']
    rs, kids = b.get('runners') or {}, b.get('kids') or {}
    if rs or kids:
        for r in rows or []:
            m = r.get('mint') or r.get('baseAddress')
            if m in rs:
                r['fd'] = rs[m]
            if m in kids:
                r['pairedWith'] = {'mint': kids[m], 'symbol': (_feeders.get('names') or {}).get(kids[m])}
    return rows


async def _feeder_rows():
    """🧲 The picker's Fed runners list: runners with 2+ new coins paired with them, hardest-fed first."""
    b = await _feeders_build()
    rs = b.get('runners') or {}
    return await _mint_rows(_fd.ranked(b)[:80], lambda m: {'divisionLabel': _fd.label(rs[m]), 'fd': rs[m], 'score': rs[m]['score']})


import social_feed as _sfeed   # noqa: F401  (read by rep_admin_routes, rep_more_reads as rs._sfeed)
_SF_CACHE: dict = {}   # source → {'at', 'posts'}  (one read per source per minute, served stale while one refresh runs behind it)
_SF_TTL = 60.0
_SF_BUSY: set = set()
_sf_http = None


def _sf_client():
    global _sf_http
    if _sf_http is None or _sf_http.is_closed:
        _sf_http = httpx.AsyncClient(timeout=8, headers={'User-Agent': 'Mozilla/5.0 (FEELESS FEEd)'}, follow_redirects=True)
    return _sf_http


# ↪ moved to rep_prime.py: _sf_read, _sf_refresh


import feed_social as _fsoc   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
FEED_SOCIAL_PATH = DATA_DIR / 'feed_social.json'
FEED_X_PATH = DATA_DIR / 'feed_x.json'   # X posts people pasted into FEEd (X's public oEmbed: no key, no login)
X_SHARE_DAY = 20
_fsoc_lock = asyncio.Lock()


class FeedReact(BaseModel):
    address: str
    session: str
    id: str = Field(..., max_length=96)
    like: bool = False
    comment: str = Field(default='', max_length=400)


class FeedXShare(BaseModel):
    address: str
    session: str
    url: str = Field(..., max_length=200)


_SF_FIRST: dict = {}   # 🧾 post id → the cap FEELESS first saw it at (memory, newest 4,000)


# ↪ moved to rep_prime.py: _sf_receipts, _callout_tick


TRENCH_SCAN = 8   # on-chain holder counts are heavy: only the 5 busiest coins that already pass every cheap check


# ↪ moved to rep_prime.py: _trench_build


TRENCH_META_PATH = FUSE_HQ_PATH.parent / 'trench_meta.json'
ENTRY_PROOF_PATH = FUSE_HQ_PATH.parent / 'entry_proof.json'
OWNER_MOVES_PATH = FUSE_HQ_PATH.parent / 'owner_moves.json'   # 🧾 the owner's hand moves on each real card, scored 30 min later (owner_moves.py)
CALL_RUN_PCT = 25.0   # 📣 a callout that is up this much since the call is worth a chat line


import owner_study as _ost   # noqa: F401  (read by rep_prime as rs._ost)
import limit_orders as _lim
import impostor as _imp   # noqa: F401  (read by rep_ai as rs._imp)
import ai_memory as _aim   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._aim)
import mem_store as _ms0
RUNNER_PATHS_PATH = DATA_DIR / 'runner_paths.json'   # {mint: [[t, price], ...]} — split out of runners.json (it was rewritten whole every tick)
_paths_mem = _ms0.MemStore(lambda: RUNNER_PATHS_PATH, 60.0, lambda p_, d_: (json.loads(p_.read_text()) if p_.exists() else d_), lambda p_, o_: _json_save_soft(p_, o_))
AI_MEMORY_PATH = DATA_DIR / 'ai_memory.json'   # 🗄 the model's filed memory (ai_memory.py: 5 capped drawers, never the whole site)
_aim_mem = _ms0.MemStore(lambda: AI_MEMORY_PATH, 120.0, lambda p_, d_: _json_load(p_, d_), lambda p_, o_: _json_save(p_, o_))
_study = {'at': 0.0, 'v': None}
STUDY_EVERY = 600


# ↪ moved to rep_prime.py: _owner_study


HOLD_WIN_PCT = 10.0   # a graded hold whose coin ran ≥ +10% more = a lesson for the models


# ↪ moved to rep_prime.py: _hint_grade, _study_tick, _owner_moves_tick


CALL_PROOF_PATH = FUSE_HQ_PATH.parent / 'call_proof.json'   # 🗑 each trench-vital CALL's own 1-hour record (send / watch / cold / bait)
CALL_KEYS = {'SEND IT': 'send', 'WATCH': 'watch', 'COLD': 'cold', 'RUG BAIT': 'bait', 'BOND RUN': 'bond', 'EARLY RUSH': 'rush', 'DUMPING': 'dump',
             'SLOW CURVE': 'slow', 'BUY THE DIP': 'dip', 'FALLING KNIFE': 'knife', 'DEAD DIP': 'deaddip', 'BREAKOUT': 'breakout', 'BLOW-OFF TOP': 'blowoff',
             'COOLING': 'cooling', 'VOLUME SURGE': 'surge', 'WASH TRADED': 'wash', 'DRYING UP': 'dry', 'TREND UP': 'tup', 'TREND DOWN': 'tdown', 'CHOP': 'chop', 'NEAR BOND': 'near'}
CALL_AUTO_MIN = 10   # the engine takes 🔥 SEND IT coins by itself only after ≥ 10 settled calls with a typical result up and half or more up
_call_cache: dict = {'at': 0.0, 'send': [], 'proof': {}}


# ↪ moved to rep_prime.py: _call_track, _sendit_ready


PROCALL_PROOF_PATH = FUSE_HQ_PATH.parent / 'procall_proof.json'   # 🎯 every pro-call entry the engine could take, noted once at its price, judged 1h later


# ↪ moved to rep_prime.py: _procall_track


import trench_brain as _tb   # noqa: F401  (read by rep_ai, rep_more_reads as rs._tb)
import drain as _drn   # noqa: F401  (read by rep_prime as rs._drn)
LI_PATH = FUSE_HQ_PATH.parent / 'launch_intel.json'   # 🕵 launches noted with their early-buyer map → settled 1h later → wallet memory
_li_st: dict = {'st': None}


# ↪ moved to rep_prime.py: _li_state, _li_parts, _li_row, _li_attach, _li_track


BRAIN_PATH = FUSE_HQ_PATH.parent / 'trench_brain.json'   # 🧠 every trench coin seen, judged on the PLAY (+50% first = hit, −30% first = cut)
BRAIN_SEE = 120                                          # the open list's busiest coins noted each pass
BRAIN_NEW, BRAIN_NEW_H = 80, 3.0                         # + the 80 newest launches (≤ 3h old) — the brain learns where the trench actually starts
_brain: dict = {'at': 0.0, 'tbl': {}, 'sum': None}


ARENA_KEEP = 300   # paper strategy runs kept in fuse_hq.json (was 600 = 370 KB rewritten on every card tick)


# ↪ moved to rep_prime.py: _brain_track, _brain_clean, _brain_state, _rush_rows, _brain_ready, _brain_rows


BOTTOM_PROOF_PATH = FUSE_HQ_PATH.parent / 'bottom_proof.json'   # 🟢 the Buy-bottom list's own 1-hour paper record
_bottom_cache: dict = {'at': 0.0, 'rows': []}


# ↪ moved to rep_prime.py: _bottom_rows


LENS_PROOF_PATH = FUSE_HQ_PATH.parent / 'lens_proof.json'   # 📏 every picker list's own 1-hour paper record
LENS_TRACK = ('ptrend', 'movers', 'pump', 'volume', 'calls', 'fed', 'double', 'exhale', 'procall', 'wave', 'prebreak', 'brain', 'live')          # the live-feed lists (bottom + trench keep their own files)
LENS_TOP = 15                                                # the top rows of each list are what a picker actually picks from
_lens_rows: dict = {}                                        # {list: [rows in the list's own order]} — refreshed with the record (~2 min)


# ↪ moved to rep_prime.py: _lens_track


import confluence as _cf
EDGE_PROOF_PATH = FUSE_HQ_PATH.parent / 'edge_proof.json'   # 🧬 learned combos (bucket → settled 1h result) + Coming up's own record ('up')
EDGE_TRACK_TOP = 40          # the best-ranked coins whose combo bucket is noted each pass
EDGE_BUY_MIN = -25.0         # the engine never takes a coin whose evidence says it typically loses more than this in an hour
_edge_rank_cache: dict = {'at': 0.0, 'rows': []}   # 🧬 the confluence ranking (was named _edge_cache — the same name as the per-coin edge cache, which cleared it)
_up_last: list = []          # [(mint, price)] Coming up's ready coins at the last tier tick — scored like any list ('up')


# ↪ moved to rep_prime.py: _swapin_lists, _edge_rank, _edge_track


BS_FRESH = 30   # s: a coin someone is looking at gets its window stats re-read from Jupiter at most this often


# ↪ moved to rep_prime.py: _bs_rows, feecat_pool_rows, feecat_read, duo_word, duo_lessons, _list_records, _bottom_track
PICK_STYLE_PATH = FUSE_HQ_PATH.parent / 'pick_style.json'   # 👤 how the owner picks (pick_style.py): one note per hand pick
HUMAN_TIERS_DEFAULT = ['next']                               # which PAPER cards pick like the owner (HQ › Fuse › Arena › Cards)


# ↪ moved to rep_prime.py: _human_style, _pick_style_note, _trench_judge, _fuse_trench_raw, _trench_row


REAL_LIQ_MARGIN = 1.15   # a real card's candidates clear the keeper's pool floor by 15%


# ↪ moved to rep_prime.py: _real_weather, _prime_cool_candidates


PAPER_MIN_LIQ = 20_000.0   # paper tiers deal any gated coin with a ≥$20K pool (the REAL card uses the Fuse wallet's own floors)


# ↪ moved to rep_prime.py: _prime_candidates


import contenders as _ct   # noqa: F401  (read by rep_prime as rs._ct)

_contenders_cache: dict = {'at': 0.0, 'data': None, 'boot': True}
CONTENDERS_SNAPSHOT_PATH = DATA_DIR / 'contenders_snapshot.json'
_contenders_lock = asyncio.Lock()


CONTENDERS_STALE_SEC = 600   # ⚡ a copy this old is still SERVED at once while a fresh one builds in the background


# ↪ moved to rep_prime.py: _contenders_build, _contenders_rebuild, _creator_state, _pick_verify, _pick_row, _pick_why


DUELS_PATH = FUSE_HQ_PATH.parent / 'fuse_duels.json'
_proof_cache = {'at': 0.0, 'data': None}
PROOF_CFG_KEYS = ('rotateHours', 'coins', 'sl', 'rideAt', 'rideTrail', 'scoutPct', 'minHoldMins', 'runnerMinAgeH', 'newOnly', 'skimAt', 'lockBankPct', 'upMeta')


# ↪ moved to rep_prime.py: _proof_build


# ---- 🛡 Crews (crews.py): 2–8 wallets, an invite code, a members-only-post room, a weekly board of verified results ------------------------------
CREWS_PATH = FUSE_HQ_PATH.parent / 'crews.json'
import sql_store as _sqls_proc   # 🔒 SITE-8: cross-process locks + the shared payment holds
_crews_lock = _sqls_proc.ProcLock(lambda: CREWS_PATH)   # 🔒 SITE-8: one holder across every worker process (all 19 crews saves + payment checks sit inside it)
_crew_cache = {'at': 0.0, 'data': None}


# ↪ moved to rep_crews.py: _crew_pieces, _crew_book, _crew_name, _seat_of, _crew_cfg, _crew_badge_usd, _crew_view


_PAY_HELD = _sqls_proc.SharedSet(lambda: DATA_DIR / 'pay_held.json')   # 💳 payment signatures taken by a request right now, shared by every worker (audit 2026-11-12 #5: N parallel requests spent one payment N times; SITE-8: N workers too)


# ↪ moved to rep_crews.py: _pay_sig_used, _pay_hold, _verify_sol_payment, _verify_sol_payment_held


@app.get('/api/reputation/crews/price')
async def crew_price(address: str = '', name: str = '', tag: str = ''):
    """💳 What a crew costs, in SOL right now, and where it is paid; with `name` + `tag` it also says whether they are free (checked BEFORE you pay)."""
    import crews as _cr
    cfg = _crew_cfg(); sol = await _sol_usd_live() or 0; to = await _rounds_pay_to()
    me = primary_of(address) if address else ''
    free = bool(me and _is_staff(me))
    cu, pu, bu = _cr.price('create', cfg), _cr.price('seats', cfg), _crew_badge_usd(cfg)
    out = {'payTo': to, 'solUsd': round(sol, 2), 'free': free, 'baseSeats': _cr.BASE_SEATS, 'packSeats': _cr.PACK_SEATS,
           'create': {'usd': cu, 'sol': round(cu / sol, 6) if sol > 0 else None}, 'seats': {'usd': pu, 'sol': round(pu / sol, 6) if sol > 0 else None},
           'badge': {'usd': bu, 'sol': round(bu / sol, 6) if sol > 0 else None}, 'ok': True, 'why': ''}
    if name or tag:
        try:
            _crew_cfg(); _cr.check_new(_json_load(CREWS_PATH, {}), me, name, tag)
        except ValueError as e:
            out.update(ok=False, why=str(e))
    return out


@app.get('/api/reputation/crews/live')
async def crews_live():
    """🔴 La Familia live: every family's public events (newest first) + the live numbers. No wallets, no board posts."""
    import crews as _cr
    st_ = _json_load(CREWS_PATH, {}) or {}
    now_ = time.time()
    return {'events': _cr.events(st_, now_), 'vitals': _cr.vitals(st_, now_), 'at': round(now_)}


@app.get('/api/reputation/crews/mine')
async def crew_mine(address: str, session: str):
    """My crew with its members' week and the invite code (members only — needs the chat session)."""
    me = _session_or_401(address, session); st = _json_load(CREWS_PATH, {})
    import crews as _cr
    me = _seat_of(st, me); c = _cr.crew_of(st, me); now = time.time(); _crew_cfg()
    fams_ = [{'id': x_, 'tag': st['crews'][x_].get('tag'), 'name': st['crews'][x_].get('name'), 'active': i_ == 0} for i_, x_ in enumerate(_cr.families_of(st, me))]
    pcs_ = _crew_pieces(c['members'], now) if c else {}
    return {'crew': {**_crew_view(c, pcs_, with_code=True), 'book': _crew_book(pcs_)} if c else None,
            'invites': _cr.invites_for(st, me, now), 'sent': _cr.sent_by(st, c, now) if c else [], 'canAdd': _is_staff(me),
            'families': fams_, 'perWallet': _cr.PER_WALLET}


class CrewSwitch(BaseModel):
    address: str
    session: str
    cid: str = Field(..., max_length=40)


class CrewCreate(BaseModel):
    address: str
    session: str
    name: str = Field(..., max_length=40)
    tag: str = Field(..., max_length=8)
    signature: str = Field(default='', max_length=100)    # the SOL payment YOU signed to the fee wallet (staff start crews free)


class CrewJoin(BaseModel):
    address: str
    session: str
    code: str = Field(..., max_length=32)


class CrewWho(BaseModel):
    address: str
    session: str


class CrewSeats(BaseModel):
    address: str
    session: str
    signature: str = Field(default='', max_length=100)


@app.post('/api/reputation/crews/create')
async def crew_create(p: CrewCreate):
    """🛡 Start a crew: $25 in SOL to the fee wallet (verified on-chain, never reused; staff free) buys 5 seats including you. Name + tag are checked BEFORE the
    payment is accepted, and a payment is only consumed when the crew is made — if anything fails, the same signature can be sent again."""
    import crews as _cr
    me = _session_or_401(p.address, p.session); mine = set(linked_of(me)) | {me}
    if _is_blocked(_block_load()['wallets'].get(me)):
        raise HTTPException(403, 'This wallet cannot start a family.')
    async with _crews_lock:
        st = _json_load(CREWS_PATH, {})
        try:
            _crew_cfg(); name, tag = _cr.check_new(st, me, p.name, p.tag)
        except ValueError as e:
            raise HTTPException(400, str(e))
        paid = {'sig': '', 'usd': 0.0, 'at': time.time(), 'kind': 'create', 'staff': True} if _is_staff(me) else await _verify_sol_payment(p.signature, mine, _cr.price('create', _crew_cfg()), st)
        paid['kind'] = 'create'; paid['by'] = me
        _crew_cfg(); c = _cr.create(st, me, name, tag, time.time(), paid=paid)
        _json_save(CREWS_PATH, st)
    _crew_cache['data'] = None
    return {'crew': _crew_view(c, {}, with_code=True)}


@app.post('/api/reputation/crews/seats')
async def crew_seats(p: CrewSeats):
    """➕ The crew owner adds 5 seats for $5 in SOL to the fee wallet (verified on-chain, never reused; staff free)."""
    import crews as _cr
    me = _session_or_401(p.address, p.session); mine = set(linked_of(me)) | {me}
    async with _crews_lock:
        st = _json_load(CREWS_PATH, {})
        me = _seat_of(st, me); mine = mine | {me}; c0 = _cr.crew_of(st, me)
        if not c0 or c0['owner'] != me:
            raise HTTPException(403, 'Only the family owner can add seats.')
        paid = {'sig': '', 'usd': 0.0, 'at': time.time(), 'staff': True} if _is_staff(me) else await _verify_sol_payment(p.signature, mine, _cr.price('seats', _crew_cfg()), st)
        paid['kind'] = 'seats'; paid['by'] = me
        try:
            c = _cr.add_seats(st, me, paid)
        except ValueError as e:
            raise HTTPException(400, str(e))
        _json_save(CREWS_PATH, st)
    _crew_cache['data'] = None
    return {'crew': _crew_view(c, _crew_pieces(c['members'], time.time()), with_code=True)}


class CrewAct(BaseModel):
    address: str
    session: str
    act: str = Field(..., max_length=16)
    text: str = Field(default='', max_length=600)
    code: str = Field(default='', max_length=32)
    id: str = Field(default='', max_length=16)
    parent: str = Field(default='', max_length=16)
    reward: float = 0
    pay: bool = False
    mint: str = Field(default='', max_length=60)
    symbol: str = Field(default='', max_length=16)
    vs: str = Field(default='', max_length=16)       # ⚔ the other family's tag (war / ally)
    stake: int = 0
    startAt: float = 0
    hours: int = 0
    ok: bool = False
    team: list = Field(default_factory=list, max_length=8)
    to: str = Field(default='', max_length=60)       # ✉ the wallet invited / added
    role: Optional[str] = Field(default=None, max_length=12)   # 🎩 the Don's role / rank for `to`
    rank: Optional[str] = Field(default=None, max_length=12)
    card: dict = Field(default_factory=dict)          # 🃏 the Don's family-card style (style · fx · line)


@app.post('/api/reputation/crews/act')
async def crew_act(p: CrewAct):
    """🛡 One door for the crew's own life: `code` (owner sets / generates the join passcode — returned ONCE, stored hashed) · `post` (board, members) ·
    `bounty` / `claim` / `settle` (points only) · `launch` (owner pins the crew's coin). Points and words only — no money moves here."""
    import crews as _cr
    me = _session_or_401(p.address, p.session); now = time.time(); plain = None
    async with _crews_lock:
        st = _json_load(CREWS_PATH, {}); me = _seat_of(st, me) if p.act not in ('accept', 'decline') else me   # an invite is answered by the wallet it was sent to
        try:
            if p.act == 'code':
                c, plain = _cr.set_code(st, me, p.code or None)
            elif p.act == 'post':
                _cr.post(st, me, p.text, now, p.parent or None)
            elif p.act == 'bounty':
                _cr.bounty_add(st, me, p.text, p.reward, now, p.mint or None)
            elif p.act == 'claim':
                _cr.bounty_claim(st, me, p.id, p.text, now)
            elif p.act == 'settle':
                _cr.bounty_settle(st, me, p.id, p.pay, now)
            elif p.act == 'launch':
                _cr.launch(st, me, p.mint or None, p.symbol, p.text, now)
            elif p.act == 'war':      # ⚔ call another family out: points pot, a date, a length (family_wars.py)
                _fwar.challenge(st, me, p.vs, p.stake, p.startAt, p.hours, now, [str(x) for x in p.team])
            elif p.act == 'answer':
                _fwar.answer(st, me, p.id, p.ok, p.stake, now, [str(x) for x in p.team])
            elif p.act == 'raise':
                _fwar.raise_pot(st, me, p.id, p.stake, now)
            elif p.act == 'join':
                _fwar.join_side(st, me, p.id, p.stake, now, [str(x) for x in p.team])
            elif p.act == 'team':
                _fwar.set_team(st, me, p.id, [str(x) for x in p.team], now)
            elif p.act == 'ally':
                _fwar.ally(st, me, p.vs, now)
            elif p.act == 'unally':
                _fwar.break_ally(st, me, p.vs)
            elif p.act == 'invite':     # ✉ any member invites a wallet; it accepts or declines
                if _is_blocked(_block_load()['wallets'].get(p.to.strip())):
                    raise ValueError('That wallet cannot join a family.')
                _cr.invite(st, me, p.to, now)
            elif p.act == 'add':        # 👑 the creator / HQ wallet adds a wallet straight into its own family
                if not _is_staff(me):
                    raise ValueError('Only the creator wallet adds members directly — invite them instead.')
                _crew_cfg(); _cr.add_direct(st, me, p.to, now)
            elif p.act == 'accept':
                if _is_blocked(_block_load()['wallets'].get(me)):
                    raise ValueError('This wallet cannot join a family.')
                _crew_cfg(); _cr.accept(st, me, p.id, now)
            elif p.act == 'decline':
                _cr.decline(st, me, p.id, now)
            elif p.act == 'card':       # 🃏 the Don styles the family's card (fixed lists)
                _cr.set_card(st, me, p.card, now)
            elif p.act == 'role':       # 🎩 the Don gives a member a job and / or a fixed rank
                import family_room as _froom
                c_ = _cr.crew_of(st, me)
                if not c_:
                    raise ValueError('You are not in a family.')
                _froom.set_role(c_, me, p.to.strip(), p.role, p.rank)
            else:
                raise ValueError('Unknown family action.')
        except ValueError as e:
            raise HTTPException(400, str(e))
        _json_save(CREWS_PATH, st)
        c = _cr.crew_of(st, me)
    _crew_cache['data'] = None
    return {'crew': _crew_view(c, _crew_pieces(c['members'], now), with_code=True) if c else None, **({'plainCode': plain} if plain else {}),
            'invites': _cr.invites_for(st, me, now), 'sent': _cr.sent_by(st, c, now) if c else [], 'canAdd': _is_staff(me)}


# 🏙 LA FAMILIA CITY (family_city.py): each family's block — stores, mob points (MP, points only), goons, robberies. Paths avoid /crews/{cid}.
import family_city as _fcity


# ↪ moved to rep_crews.py: _city_ctx, _city_rivals, _city_tax


class CityAct(BaseModel):
    address: str
    session: str
    act: str = Field(..., max_length=12)
    lot: int = Field(default=-1, ge=-1, le=10_000_000)
    kind: str = Field(default='', max_length=16)
    vs: str = Field(default='', max_length=16)


@app.post('/api/reputation/familia-city/act')
async def familia_city_act(p: CityAct):
    """🏙 build · upgrade · hire · collect · rob — points only. Don / Underboss build, upgrade, hire and rob; any member collects; the creator
    wallet builds anything, free."""
    import crews as _cr
    me = _session_or_401(p.address, p.session); now = time.time(); res_ = None
    async with _crews_lock:
        st = _json_load(CREWS_PATH, {}); me = _seat_of(st, me); c = _cr.crew_of(st, me)
        if not c:
            raise HTTPException(404, 'Join a family to build a block.')
        staff_ = _is_staff(me)
        boost_, rk_ = _city_ctx(c, me, now)
        _fcity.accrue(_fcity.city_of(c, now), now, boost_)
        try:
            if p.act == 'build':
                _fcity.build(c, me, p.lot, p.kind, now, staff_, rk_)
            elif p.act == 'upgrade':
                _fcity.upgrade(c, me, p.lot, now, staff_, rk_)
            elif p.act == 'hire':
                _fcity.hire(c, me, p.kind, now, staff_, rk_)
            elif p.act == 'collect':
                got_, house_ = _fcity.collect(c, me, now, _city_tax())
                st['house'] = int(st.get('house') or 0) + house_
                c.setdefault('world', {})['collects'] = int((c.get('world') or {}).get('collects') or 0) + 1   # 🗺 counted for the recruitment challenges   # 🏦 the FEELESS house pool (points) — pays the season's prizes
                res_ = {'collected': got_, 'house': house_}
            elif p.act == 'dice':
                res_ = _fcity.casino(c, me, p.lot, now)
            elif p.act == 'rob':
                o_ = (st.get('crews') or {}).get(p.vs)
                if not o_:
                    raise ValueError('No such family.')
                _fcity.accrue(_fcity.city_of(o_, now), now)
                res_ = _fcity.rob(c, o_, me, now, staff_, rk_)
            else:
                raise ValueError('Unknown city action.')
        except ValueError as e:
            raise HTTPException(400, str(e))
        _json_save(CREWS_PATH, st)
        v_ = _fcity.view(c, now, staff=staff_, boost=boost_, mine=True, tax=_city_tax())
        v_['rivals'] = _city_rivals(st, c, now)
        v_['canBuild'] = staff_ or me == c.get('owner') or rk_.get(me) == 'underboss'
        v_['house'] = int(st.get('house') or 0)
    _crew_cache['data'] = None
    return {**v_, 'result': res_}


# 🏙 THE FAMILY BLOCK = REAL MARKETS (block_markets.py): the Don adds market buildings; each stays UNDER CONSTRUCTION until the family's wallets
# really hold a position there (receipt tokens · position NFTs · Kamino vault shares), read once a minute per family. Points never build these.
import block_markets as _bmk   # noqa: E402
import base64 as _b64m, base58 as _b58m   # noqa: E402  (C03 on-chain readers)

_fblock_held = {}   # cid → (at, {key: {amount, usd, n}})
FBLOCK_HELD_SEC = 60.0
TOKEN_PROGRAM = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'


# ↪ moved to rep_crews.py: _fblock_wallets, _fblock_reads, _fblock_ranges, _fblock_view


class BlockAct(BaseModel):
    address: str
    session: str
    act: str = Field(..., max_length=8)
    key: str = Field(..., max_length=24)


@app.post('/api/reputation/familia-block/act')
async def familia_block_act(p: BlockAct):
    """🏙 add / remove a market building, tadd / tdel a town tool building (Don · Underboss · creator). Adding builds nothing by itself — a real position does."""
    import crews as _cr
    me = _session_or_401(p.address, p.session); now = time.time()
    known_ = {m_['key'] for m_ in ((await familia_markets()) or {}).get('markets') or []}
    async with _crews_lock:
        st = _json_load(CREWS_PATH, {}); me = _seat_of(st, me); c = _cr.crew_of(st, me)
        if not c:
            raise HTTPException(404, 'Join a family to build a block.')
        staff_ = _is_staff(me); _b, rk_ = _city_ctx(c, me, now)
        try:
            if p.act == 'add':
                _bmk.add(c, p.key, me, now, staff_, rk_, known_)
            elif p.act == 'remove':
                _bmk.remove(c, p.key, me, staff_, rk_)
            elif p.act in ('tadd', 'tdel'):   # 🏘 stand / take down a tool building in the family's town
                _bmk.town_set(c, p.key, p.act == 'tadd', me, staff_, rk_)
            else:
                raise ValueError('Unknown block action.')
        except ValueError as e:
            raise HTTPException(400, str(e))
        _json_save(CREWS_PATH, st)
    _crew_cache['data'] = None
    _fblock_held.pop(c['id'], None)
    return await _fblock_view(c, me, staff_, rk_)


class BlockLayout(BaseModel):
    address: str
    session: str
    cells: list = Field(..., max_length=80)


@app.post('/api/reputation/familia-block/layout')
async def familia_block_layout(p: BlockLayout):
    """🏝 Save the family block's arrangement (Don · Underboss · creator): cells in order — buildings moved, lots picked, stands, MY POOLS,
    more islands joined by bridges. Stored server-side on the family; nothing is bought or sold by it."""
    import crews as _cr
    me = _session_or_401(p.address, p.session); now = time.time()
    async with _crews_lock:
        st = _json_load(CREWS_PATH, {}); me = _seat_of(st, me); c = _cr.crew_of(st, me)
        if not c:
            raise HTTPException(404, 'Join a family to build a block.')
        staff_ = _is_staff(me); _b, rk_ = _city_ctx(c, me, now)
        try:
            n_, cost_ = _bmk.expand_cost(c, p.cells, staff_)   # 🏝 a new island = family MP (points); the creator wallet expands for free
            _bmk.layout_set(__import__("copy").deepcopy(c), p.cells, me, staff_, rk_)   # every refusal BEFORE the bank is touched
            if cost_:
                import family_city as _fcy
                _fcy._pay(_fcy.city_of(c, now), cost_, f'{n_ - max(1, int(c.get("islands") or 1))} new island(s)')
            _bmk.layout_set(c, p.cells, me, staff_, rk_)
        except ValueError as e:
            raise HTTPException(400, str(e))
        _json_save(CREWS_PATH, st)
    _crew_cache['data'] = None
    return await _fblock_view(c, me, staff_, rk_)


# 🗺 LA FAMILIA WORLD (family_world.py): the big city — 6 boroughs × 16 blocks, bridges, turf, CPU towns, cartels from FEELESS rep, raids as chess
# moves, recruitment challenges, errands, rewards and the FEECAT redeem claim. Points only; the redeem is a claim the owner pays by hand.
import family_world as _fworld   # noqa: F401  (read by rep_admin_reads, rep_admin_routes as rs._fworld)

_cartel_cache = {'at': 0.0, 'rows': []}


# ↪ moved to rep_crews.py: _cartels_now, _world_target, _world_settle, _familia_rules, _world_tick, _world_metrics


_fuse_fam_c = {'n': -1, 'v': None}


# ↪ moved to rep_crews.py: _fuse_family_stats, _world_feecat_rate, _world_view


@app.on_event('startup')
async def _familia_prices_load():
    _fcity.set_prices(_admin_load().get('familiaPrices'))


_perps_cache: dict = {'at': 0.0, 'rows': []}


@app.get('/api/reputation/familia/perps')
async def familia_perps():
    """📉 The Perps Desk building: the busiest perps markets (Hyperliquid's public market data) — one shared read a minute; read-only."""
    global _fmk_http
    import perps_desk as _pdk
    now = time.time()
    if now - _perps_cache['at'] > 60:
        if _fmk_http is None:
            _fmk_http = httpx.AsyncClient(timeout=8, limits=httpx.Limits(max_connections=8))
        try:
            r_ = await _fmk_http.post(_pdk.INFO, json={'type': 'metaAndAssetCtxs'}, timeout=8)
            rows_ = _pdk.rows(r_.json()) if r_.status_code == 200 else []
        except Exception:
            rows_ = []
        _perps_cache.update(at=now, rows=rows_ or _perps_cache['rows'])
    return {'markets': _perps_cache['rows'], 'at': round(_perps_cache['at'])}


_kalshi_cache: dict = {'at': 0.0, 'rows': {}}


@app.get('/api/reputation/familia/kalshi')
async def familia_kalshi():
    """⏱ Kalshi's live UP / DOWN markets (US-legal, CFTC-regulated; read-only) — kalshi_odds.MARKETS: BTC · ETH · SOL · DOGE · XRP (each one's
    15-minute "up?" + the ladder strike nearest the live mark) and S&P 500 · Nasdaq-100 (the soonest window's at-the-money strike). One shared
    read every 10 s, every market in parallel; a failed read keeps the last good one."""
    global _fmk_http
    import kalshi_odds as _ko
    now = time.time()
    if now - _kalshi_cache['at'] > 10:
        if _fmk_http is None:
            _fmk_http = httpx.AsyncClient(timeout=8, limits=httpx.Limits(max_connections=8))
        marks_ = {r_.get('coin'): r_.get('mark') for r_ in _perps_cache.get('rows') or []}

        async def get(path_, params_):
            try:
                r_ = await _fmk_http.get(f'{_ko.API}/{path_}', params=params_, timeout=8)
                return r_.json() if r_.status_code == 200 else None
            except Exception:
                return None

        async def one(key_, m_):
            if m_['kind'] == 'index':   # the soonest window only (the Nasdaq ladder is 1,000+ rows across days)
                ev_ = await get('events', {'series_ticker': m_['day'], 'status': 'open', 'limit': 20})
                et_ = _ko.soonest_event((ev_ or {}).get('events')) if ev_ is not None else None
                mk_ = await get('markets', {'event_ticker': et_, 'limit': 1000}) if et_ else None
                if ev_ is None or (et_ and mk_ is None):
                    return key_, None
                up_ = _ko.atm((mk_ or {}).get('markets'))
                return key_, {'up': up_, 'day': None, 'ladder': _ko.ladder((mk_ or {}).get('markets'), (up_ or {}).get('target'))}
            f_, d_ = await asyncio.gather(get('markets', {'series_ticker': m_['m15'], 'status': 'open', 'limit': 50}),
                                          get('markets', {'series_ticker': m_['day'], 'status': 'open', 'limit': 1000}))
            if f_ is None and d_ is None:
                return key_, None
            m15_ = _ko.fifteen((f_ or {}).get('markets')) if f_ is not None else None
            mark_ = marks_.get(key_) or (m15_ or {}).get('target')
            return key_, {'up': m15_, 'm15': m15_, 'day': _ko.nearest((d_ or {}).get('markets'), mark_) if d_ is not None else None,
                          'ladder': _ko.ladder((d_ or {}).get('markets'), mark_) if d_ is not None else []}   # 🎯 the strike ladder
        got_ = await asyncio.gather(*[one(k_, m_) for k_, m_ in _ko.MARKETS.items()])
        rows_ = dict(_kalshi_cache['rows'])
        for k_, row_ in got_:
            if row_ is None:
                continue
            old_ = rows_.get(k_) or {}
            rows_[k_] = {**row_, 'up': row_['up'] or old_.get('up'), 'name': _ko.MARKETS[k_]['name'], 'kind': _ko.MARKETS[k_]['kind']}
        _kalshi_cache.update(at=now, rows=rows_)
    import kalshi_trade as _kt
    return {'coins': _kalshi_cache['rows'], 'at': round(_kalshi_cache['at']), 'venue': 'Kalshi (CFTC-regulated)', 'tradable': bool(_kt.key(os.environ)), 'min': _kt.MIN_USD, 'max': _kt.MAX_USD}


# ⏱ KALSHI TRADES FROM THE WALLET (kalshi_trade.py — DFlow's tokenized Kalshi markets; Proof KYC; the wallet signs; FEELESS sends only what it built)
_kproof: dict = {}       # wallet → True (verified is cached; "not verified" never is)
_kmeta: dict = {}        # ticker / mint → (at, market | None) — 60 s (10 min for a mint that is not a Kalshi outcome token)


# ↪ moved to rep_crews.py: _kt_need, _kt_proof


def _fmk_http_get():
    global _fmk_http
    if _fmk_http is None:
        _fmk_http = httpx.AsyncClient(timeout=8, limits=httpx.Limits(max_connections=8))
    return _fmk_http


# ↪ moved to rep_crews.py: _kt_market, _kt_addr


# 🏦 THE BROKERAGE (brokers.py, DECISIONS #9): the user's OWN broker through SnapTrade, linked to their Familia wallet session
BROKERS_PATH = DATA_DIR / 'brokers.json'   # primary wallet → {uid, sec (Fernet-sealed SnapTrade secret), at}
_brk_cache: dict = {}
_brk_lock = asyncio.Lock()


BROKER_SEAL_PATH = DATA_DIR / '.broker_seal'   # 🔐 the seal key FEELESS made for itself (0600) when BROKER_SECRET_KEY is not in .env


# ↪ moved to rep_crews.py: _brk_seal, _brk_need, _brk_call, _brk_q, _brk_user, _brk_alpaca, _alpaca_call, _brk_cdc, _cdc_call, _cdc_dev_key


_cdc_inst: dict = {'at': 0.0, 'rows': []}


# ↪ moved to rep_crews.py: _cdc_instruments


_UPDATES_CACHE = {'at': 0.0, 'rows': []}


PAPER_PERPS_PATH = DATA_DIR / 'paper_perps.json'   # 📉 one paper book per wallet (paper_perps.py) — never money, never an order
_pperp_lock = asyncio.Lock()


# ↪ moved to rep_crews.py: _pperp_board


class PaperPerpAct(BaseModel):
    address: str = Field(..., max_length=64)
    session: str = Field(..., max_length=400)
    act: str = Field(..., max_length=8)
    coin: str = Field('', max_length=16)
    side: str = Field('', max_length=6)
    margin: float = Field(0, ge=0, le=1e7)
    lev: int = Field(1, ge=1, le=100)
    id: str = Field('', max_length=16)


_intake_cache: dict = {'at': 0.0, 'rows': []}
_shared_intake: dict = {'at': 0.0, 'rows': []}


INTAKE_MAX = 20


_town_live_cache: dict = {'at': 0.0, 'v': None, 'lock': None}
TOWN_LIVE_SEC = 45


class WorldAct(BaseModel):
    address: str
    session: str
    act: str = Field(..., max_length=16)
    block: str = Field(default='', max_length=24)
    vs: str = Field(default='', max_length=40)
    kind: str = Field(default='', max_length=24)
    lot: int = Field(default=-1, ge=-1, le=24)
    raid: str = Field(default='', max_length=24)
    pool: str = Field(default='', max_length=64)
    mp: int = Field(default=0, ge=0, le=10_000_000)
    source: str = Field(default='own', max_length=8)
    text: str = Field(default='', max_length=120)   # 📺 billboard line
    mint: str = Field(default='', max_length=44)


# 🎯 STRIKE ZONE (arena.py, owner 2026-10-27: "a third-person shooter instead of the raceway — bots or online, real levelling + gun customisation"):
# your profile (XP → level → unlocks, the loadout you built), a one-use match token, the result (checked against the server's own clock → XP,
# and a family member's kills feed the family bank a little), and ONLINE rooms over a WebSocket (positions + shots relayed, ≤ 8 a room).
# Who you are: a signed-in wallet, else a verified Telegram player (tg_auth), else a guest (plays, saves nothing).
import arena as _ar   # noqa: F401  (read by rep_crews, rep_money_routes as rs._ar)
import tg_auth as _tga   # noqa: F401  (read by rep_crews as rs._tga)

ARENA_PATH = CREWS_PATH.parent / 'arena.json'
_arena_tokens = {}
_arena_rooms = {}   # room → {cid: {'ws', 'name', 'state'}}


# ↪ moved to rep_crews.py: _arena_day, _tg_user, _tg_group, _arena_who, _arena_unlock_level, _arena_profile


class ArenaWho(BaseModel):
    address: str = Field(default='', max_length=64)
    session: str = Field(default='', max_length=400)
    tg: str = Field(default='', max_length=4096)


class ArenaLoadout(ArenaWho):
    loadout: dict = Field(default_factory=dict)


class ArenaStart(ArenaWho):
    mode: str = Field(default='bots', max_length=8)


class ArenaResult(ArenaWho):
    token: str = Field(..., max_length=64)
    kills: int = Field(..., ge=0, le=999)
    deaths: int = Field(..., ge=0, le=999)
    heads: int = Field(default=0, ge=0, le=999)
    won: bool = False


from fastapi import WebSocket, WebSocketDisconnect   # noqa: E402  (the online rooms)


@app.websocket('/api/reputation/arena/ws')
async def arena_ws(ws: WebSocket, room: str = 'fee-city', name: str = 'guest'):
    """🌐 an online room: every message a player sends ({t: 'state' | 'shot' | 'hit' | 'dead', …}) is relayed to the others with their id; join /
    leave are announced. ≤ 8 a room. Hits are claimed by the shooter (casual play — the XP still goes through the clock check)."""
    room = ''.join(ch for ch in str(room)[:24] if ch.isalnum() or ch in '-_') or 'fee-city'
    peers = _arena_rooms.setdefault(room, {})
    if len(peers) >= 8:
        await ws.close(code=4008)
        return
    await ws.accept()
    cid = _secrets.token_hex(4); nm = ''.join(ch for ch in str(name)[:16] if ch.isprintable()) or 'guest'
    peers[cid] = {'ws': ws, 'name': nm}

    async def cast(msg, skip=None):
        for k_, v_ in list(peers.items()):
            if k_ == skip:
                continue
            try:
                await v_['ws'].send_json(msg)
            except Exception:
                peers.pop(k_, None)
    await ws.send_json({'t': 'hello', 'id': cid, 'peers': [{'id': k, 'name': v['name']} for k, v in peers.items() if k != cid]})
    await cast({'t': 'join', 'id': cid, 'name': nm}, skip=cid)
    try:
        while True:
            msg = await ws.receive_json()
            if isinstance(msg, dict) and msg.get('t') in ('state', 'shot', 'hit', 'dead', 'chat'):
                msg['id'] = cid
                if msg.get('t') == 'chat':
                    msg['text'] = str(msg.get('text') or '')[:120]
                await cast(msg, skip=cid)
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        peers.pop(cid, None)
        if not peers:
            _arena_rooms.pop(room, None)
        await cast({'t': 'leave', 'id': cid})


# ⚔ FAMILY FUSE (family_fuse.py): two families' Fuse cards in the Fuse Arena stadium — paper or MP, spectator bids, the Arena's six duels.
import family_fuse as _ffuse   # noqa: F401  (read by rep_admin_routes, rep_crews as rs._ffuse)
_ffuse_mark = {'at': 0.0}


# ↪ moved to rep_crews.py: _ffuse_cards, _ffuse_prices, _ffuse_book, _ffuse_pay, _ffuse_tick, _ffuse_view


# 🏦 FEE CITY'S MARKETS (fee_markets.py): real DeFi markets as buildings — DefiLlama TVL (one tiny call a market) + ONE DexScreener search for the
# live pools and today's top coins, in parallel, cached 60s, one pooled client. Read-only.
import fee_markets as _fmk
_fmk_cache = {'at': 0.0, 'v': None, 'prev': {}, 'lock': None}
import fee_pools as _fpl   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
_fpl_cache = {'at': 0.0, 'v': None, 'lock': None}
FPL_SEC = 600


async def _fpl_fetch():
    """DefiLlama's yield list (every chain, ~10 MB — trimmed to the Solana rows we keep, never stored whole) + our own trending pair feed."""
    global _fmk_http
    if _fmk_http is None:
        _fmk_http = httpx.AsyncClient(timeout=8, limits=httpx.Limits(max_connections=8))

    async def llama():
        try:
            r = await _fmk_http.get('https://yields.llama.fi/pools', timeout=40)
            return [x for x in ((r.json() or {}).get('data') or []) if x.get('chain') == 'Solana'] if r.status_code == 200 else []
        except Exception:
            return []

    async def feed(kind):
        try:
            r = await _fmk_http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': kind, 'chain': 'solana', 'page': 1})
            return (r.json() or {}).get('pairs') or []
        except Exception:
            return []
    ll, tr, nw = await asyncio.gather(llama(), feed('trending'), feed('new'))
    return ll, tr + nw


import sleep_money as _slm   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
_slm_cache = {'at': 0.0, 'km': None}


import cat_fund as _cfund   # noqa: F401  (read by rep_crews, rep_money_routes as rs._cfund)
import wallet_swaps as _wswaps
_cfund_plans: dict = {}   # f"{cat}:{owner}" → the transaction FEELESS built (memory only, PLAN_SEC) — a signed copy must match it byte for byte


class CatFundIn(BaseModel):
    address: str = Field(min_length=32, max_length=44)
    session: str = Field(min_length=8, max_length=200)
    usd: float = 0.0
    signed: str = Field('', max_length=4000)
    token: str = 'SOL'         # 💵 SOL | USDC
    creditUsd: float = 0.0     # 🧠 how much of `usd` becomes model credit; the rest goes into its wallet (one transaction)


# ↪ moved to rep_crews.py: _cat_for_fund, _cat_fund_rules


import agent_pay as _apay   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
_or_float: dict = {'at': 0.0, 'left': None}


# ↪ moved to rep_crews.py: _openrouter_left


class CatModelLimitIn(BaseModel):
    session: str = ''


class CatWithdrawIn(BaseModel):
    address: str = Field(min_length=32, max_length=44)
    session: str = Field(min_length=8, max_length=200)
    token: str = 'SOL'
    amount: float = 0.0        # 0 = all of it
    # 🔒 no destination field, on purpose: it only ever pays the wallet that owns this agent


_cat_out_busy: set = set()


import price_gap as _pgap   # noqa: F401  (read by rep_crews as rs._pgap)
_pgap_c = {'at': 0.0, 'v': None, 'book': {}}
PGAP_SEC = 60.0


# ↪ moved to rep_crews.py: _vault_gap_read


_pgap_coin = {}   # mint → {'at', 'v', 'book'} — one coin's gap board (SITE-11), ≤ 400 coins kept


_pgap_fly = {}   # key → the one running read; callers that miss the cache together share it (no stampede on DexScreener)


# ↪ moved to rep_crews.py: _pgap_once, _coin_gap_read


_fpl_charts = {}   # pool id → (at, points) — 30 min, ≤ 300 pools kept


_fle_hits = _HITS('fle')   # ip → [times] (the deposit builder: 30 an hour per IP)


_flv_hits = _HITS('flv')     # ip → [times] (the leverage builder: 30 an hour per IP)
_flv_vaults = {}   # 'at' + 'rows': Jupiter Lend's vaults, read at most once every 30 s


# ↪ moved to rep_crews.py: _jl_borrow, _jl_lend, _jl_markets


_fjp_hits = _HITS('fjp')    # ip → [times] (perps builds: 60 an hour per IP)
_fjp_pool = {}    # 'at' + 'rows': Jupiter Perps pool info per market, read at most once a minute


# ↪ moved to rep_crews.py: _jp_call


_fjp_stats: dict = {}   # 📊 Jupiter Perps market-stats per market, 10 s


_fjp_lead: dict = {}   # asset → (at, leaders) — Jupiter's weekly top traders, 5 min


_fjx_hits = _HITS('fjx')


_frun_tok = {}   # 'at' + 'rows': Jupiter Lend Earn's USDC / SOL doors, read at most once a minute


_rng_cache: dict = {}   # key → (at, rows): the venues' own pool reads, 2 min


# ↪ moved to rep_crews.py: _rng_get


AUTORANGE_PATH = DATA_DIR / 'autorange.json'   # {wallet: [armed band]} — the server watcher pings the phone when a band sits out of range


# ↪ moved to rep_crews.py: _collective_band_pass, _autorange_watch


@app.on_event('startup')
async def _autorange_boot():
    _LEAD.start(_autorange_watch)


_fmk_http = None


async def _fmk_fetch():
    global _fmk_http
    if _fmk_http is None:
        _fmk_http = httpx.AsyncClient(timeout=8, limits=httpx.Limits(max_connections=8))

    async def tvl(slug):
        try:
            r = await _fmk_http.get(f'https://api.llama.fi/tvl/{slug}')
            return slug, float(r.text) if r.status_code == 200 else None
        except Exception:
            return slug, None

    async def dex():
        try:
            r = await _fmk_http.get('https://api.dexscreener.com/latest/dex/search?q=SOL')
            return (r.json() or {}).get('pairs') or []
        except Exception:
            return []

    async def trending():   # 🪙 NEW MONEY: the search above answers SOL's own pools (no coins left after the SOL / stable filter) — our own trending feed has the coins
        try:
            r = await _fmk_http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': 'trending', 'chain': 'solana', 'page': 1})
            return (r.json() or {}).get('pairs') or []
        except Exception:
            return []
    res = await asyncio.gather(*[tvl(m[3]) for m in _fmk.MARKETS], dex(), trending())
    return {k: v for k, v in res[:-2] if v}, res[-2] + res[-1]


# 📱 SCAN TO SIGN IN TO HQ (hq_pair.py): the computer shows a one-time QR, Phantom on the phone signs the normal HQ message, the computer
# receives that session once. The signature is checked exactly like a normal sign-in before it is stored. Memory only.
import hq_pair as _hqp   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
_hqp_store = {}


# ↪ moved to rep_crews.py: _lan_ip, _hqp_site


_hqp_ip = _HITS('hqp')


class HqPairAnswer(BaseModel):
    nonce: str = Field(..., max_length=80)
    data: str = Field(..., max_length=4000)
    pub: str = Field(default='', max_length=80)
    port: int = Field(default=51367, ge=1, le=65535)


class HqPairSig(BaseModel):
    address: str = Field(..., max_length=64)
    ts: int
    sig: str = Field(..., max_length=200)


class FamFuseAct(BaseModel):
    address: str
    session: str
    act: str = Field(..., max_length=12)
    vs: str = Field(default='', max_length=40)
    card: str = Field(default='', max_length=80)
    stake: str = Field(default='paper', max_length=8)
    mp: int = Field(default=0, ge=0, le=10_000_000)
    mins: int = Field(default=15, ge=1, le=600)
    fight: str = Field(default='', max_length=24)
    side: str = Field(default='', max_length=2)
    amount: int = Field(default=0, ge=0, le=10_000_000)


class CrewBadge(BaseModel):
    address: str
    session: str
    badge: dict
    signature: str = Field(default='', max_length=100)


@app.post('/api/reputation/crews/badge')
async def crew_badge(p: CrewBadge):
    """🌹 The family head builds the ONE family badge (first build free) or restyles it ($ badgeUsd in SOL to the fee wallet, verified on-chain, never
    reused; staff free). Every part is re-checked against the family's tracked numbers — a locked part is refused."""
    import crews as _cr
    me = _session_or_401(p.address, p.session); mine = set(linked_of(me)) | {me}
    async with _crews_lock:
        st = _json_load(CREWS_PATH, {}); me = _seat_of(st, me); mine = mine | {me}; c0 = _cr.crew_of(st, me)
        if not c0 or c0['owner'] != me:
            raise HTTPException(403, 'Only the family head builds the badge.')
        try:
            _cr.clean_badge(p.badge, _cr.family_metrics(c0, st.get('awards'), _is_staff(me)), _crew_cfg())   # locked parts refused BEFORE any payment is consumed
        except ValueError as e:
            raise HTTPException(400, str(e))
        paid = None
        if c0.get('badge'):
            paid = {'sig': '', 'usd': 0.0, 'at': time.time(), 'staff': True} if _is_staff(me) or _crew_badge_usd() <= 0 else await _verify_sol_payment(p.signature, mine, _crew_badge_usd(), st)
            paid['by'] = me
        try:
            c = _cr.set_badge(st, me, p.badge, st.get('awards'), time.time(), _crew_cfg(), paid, _is_staff(me))
        except ValueError as e:
            raise HTTPException(400, str(e))
        _json_save(CREWS_PATH, st)
    _crew_cache['data'] = None
    return {'crew': _crew_view(c, _crew_pieces(c['members'], time.time()), with_code=True)}


CREW_PRIZES = (150, 100, 60)   # season points to EACH member of the week's top 3 ranked crews


import family_wars as _fwar


# ↪ moved to rep_crews.py: _wars_tick, _crew_season_tick, _crew_room_ok


# ---- ⚡ Free hourly call (predict.py): the engine's doors put a coin each on a ballot; pick the one that leads the next hour; points only --------
PREDICT_PATH = FUSE_HQ_PATH.parent / 'predict.json'
_predict_lock = asyncio.Lock()


# ↪ moved to rep_predict.py: _predict_symbols


import rep_markets as _repm   # noqa: F401  (read by rep_more_writes, rep_predict as rs._repm)
REP_MARKETS_PATH = FUSE_HQ_PATH.parent / 'rep_markets.json'
_rm_lock = asyncio.Lock()


# ↪ moved to rep_predict.py: _rm_rows, _rm_tick, _rep_of


class RepStake(BaseModel):
    address: str
    session: str
    market: str = Field(..., max_length=16)
    side: str = Field(..., max_length=3)
    chips: int = 0


# ↪ moved to rep_predict.py: _predict_tick


class PredictPick(BaseModel):
    address: str
    session: str
    round: int
    mint: str = Field(..., max_length=64)


_predict_view_cache = {'at': 0.0, 'data': None}


_bounty_cache = {'at': 0.0, 'data': None}


_whosin_cache: dict = {}


_track_cache: dict = {}


_myedge_cache = {'at': 0.0, 'data': None}


# ↪ moved to rep_predict.py: _owner_edge_rec


_paymap_cache = {'at': 0.0, 'data': None}


_prime_tick_lock = asyncio.Lock()


import single as _single
KEEPER_LOCK = DATA_DIR / 'keeper.lock'
_keeper_state = {'stopping': False, 'said': 0.0}


# ↪ moved to rep_predict.py: _is_keeper


@app.on_event('shutdown')
async def _keeper_stop():
    _keeper_state['stopping'] = True   # loops still running during shutdown must not trade
    _single.release(KEEPER_LOCK)
    for flush in (_store_flush, lambda: _block_flush() if _block_dirty['on'] else None, _hygiene_flush,   # debounced stores: nothing learned is lost on a stop
                  _agents_mem.flush, _lingo_mem.flush, _shadow_flush, _social_flush, _after_mem.flush, _aim_mem.flush, _g4_mem.flush, _paths_mem.flush):
        try:
            flush()
        except Exception:
            pass
    try:   # the caller scoreboard is written every 10 min: keep what was learned since
        if _pump_callers['st'] is not None and not os.environ.get('PYTEST_CURRENT_TEST'):
            _json_save(PUMP_CALLERS_PATH, _pump_callers['st'])
    except Exception:
        pass


# ↪ moved to rep_predict.py: _prime_tick, _prime_bell_loop


_guard_seen: dict = {}   # {mint: when the fast guard last woke the tick for it} — one wake per coin per 30s


import flow as _flow
FLOW_PROOF_PATH = FUSE_HQ_PATH.parent / 'flow_proof.json'   # 🌊 every flow / rug exit: noted at its sell price, judged 1h later (lower = it saved money)
FLOW_EVERY = 15.0
_flow_now: dict = {}    # pairAddress → (at, window) — the latest tape read of every coin we watch
_flow_at = {'t': 0.0}
_flow_trades: dict = {}   # pairAddress → (at, raw trades) of the last tape read
import degen as _dg
SMART_PATH = FUSE_HQ_PATH.parent / 'smart_wallets.json'   # 🐳 each wallet's first buys and how they did an hour later
_smart = {'set': {}, 'at': 0.0}
_smart_now: dict = {}     # mint → (at, [(wallet, usd)]) smart wallets seen buying it in its last tape
_burst_last: list = []    # [(mint, price)] coins showing a buy burst at the last flow entry — scored like any list ('burst')


# ↪ moved to rep_predict.py: _smart_track, _smart_on


import real_learn as _rl   # noqa: F401  (read by rep_ai, rep_predict as rs._rl)
REAL_LEARN_PATH = FUSE_HQ_PATH.parent / 'real_learn.json'   # 🧠 every coin that left the real card: its buy snapshot → how it ended
_rl_cache = {'at': 0.0, 'tbl': {}}


# ↪ moved to rep_predict.py: _learn_drops, _real_table, _flow_fetch, _flow_mark, _flow_intel


_consig_c: dict = {'at': 0.0, 'v': {}}


# ↪ moved to rep_predict.py: _consig_plans


REAP_ADJ_SEC = 120.0   # Reaper moves a coin's lines at most every 2 min


# ↪ moved to rep_predict.py: _reaper_lines, _flow_guard, _flow_settle


SEAT_HEARTBEAT_SEC = 8   # an empty agent seat gets a tier tick at least this often (the 30-second seat decision needs a tick to run in)


AGENT_GUARD_SEC = 3   # ⚡ while the agents hold a real seat the guard looks every 3s (one local batched live-price read), else every GUARD_SEC
_guard_agents = {'held': False}


# ↪ moved to rep_predict.py: _limit_check, _real_guard_loop, _fw_market_rows


LEAGUE_RESET = 'restart3-100'   # 2026-10-26: owner — "fix fuse arena paper cards … reset paper money with $100 each" (was 'restart2', 2026-10-19: owner — "arena numbers are off, reset all arena paper cards"
PAPER_START_USD = 100.0
PRIME_RESET = 'paper100a'   # 2026-10-26: owner — "reset paper money with $100 each" (was 'paper20e', 2026-10-19: owner — "reset all arena paper cards" (was 'paper20d')   # (2026-10-17: owner — "paper cards get the new mechanics: germ buying + per-coin lines; reset them")   # (2026-10-13: owner — "reset and upgrade fuse arena cards, they are losing"; ⚡ Next Level now inherits the agents)   # was 'paper20b'   # (2026-10-05: owner asked for a second restart)   # one-time: every PAPER tier card starts over on $20 (the real card is never touched)


PRIME_UNIQUE = 'unique2'


# ↪ moved to rep_predict.py: _prime_unique_fix, _cook_warn, _real_hold_fix, _real_ride_fix, _ladder_keep_fix


DEGEN_1009 = {'tpStakeUsd': 0.0, 'stackSkimUsd': 0.5, 'houseAt': 50, 'trenchHouseAt': 50, 'pickLockMins': 30, 'rideEnd': 'bank', 'minHoldMins': 30.0,
              'lockBankPct': 50.0, 'trenchAuto': False, 'ticketRide': False}


# ↪ moved to rep_predict.py: degen_patch_1009, _degen_fix_1009


OVERNIGHT_1009 = {'runnerMinAgeH': 12, 'runnerMinLiqK': 50, 'runnerMinVolK': 50, 'runnerMinChg1h': 0, 'runnerMinBuy': 65,
                  'scoutPct': 0, 'moverSwap': False, 'newOnly': False, 'coins': 3, 'swapCapHr': 2, 'skimHoldRounds': 2}


# ↪ moved to rep_predict.py: overnight_patch_1009, _overnight_fix_1009


HUNT_1009 = {'coins': 2, 'runnerMinAgeH': 12, 'runnerMinVolK': 50, 'runnerMinChg1h': 40, 'runnerMinLiqK': 25, 'runnerMinBuy': 0, 'edgeGate': False,
             'rideAt': 50.0, 'rideTrail': 30.0, 'peakSellPct': 50.0, 'houseAt': 50, 'sl': 30.0, 'instantSwapPct': 0, 'newOnly': True,
             'scoutPct': 0, 'moverSwap': False, 'rideEnd': 'bank'}
HUNT_1009_B = {'vitalMin': 35, 'organicMin': 5}   # the 50+ / 10% filter removed all 6 coins that cleared the hunt line


# ↪ moved to rep_predict.py: hunt_patch_1009, _hunt_fix_1009, _hunt_fix_1009b


TRENCH_1009 = {'rotateHours': 0.08, 'rotateConfirm': 2, 'trenchAuto': True, 'trenchSendOnly': True, 'trenchCoins': 2, 'minHoldMins': 15.0,
               'rideAt': 20.0, 'rideTrail': 15.0, 'trailStep': True, 'lockBankPct': 50.0, 'houseAt': 30, 'trenchHouseAt': 30, 'peakSellPct': 50.0, 'rideEnd': 'bank'}


# ↪ moved to rep_predict.py: trench_patch_1009, _trench_fix_1009, _procall_fix_1009, _topseat_fix_1009, _trench_safe_fix_1009


CLEAN_1009 = {'maxCoinPct': 35, 'bangerRefill': True, 'scoutPct': 0, 'stackSkimUsd': 0.0, 'secondTicketPct': 0, 'moverSwap': False}


# ↪ moved to rep_predict.py: _clean_fix_1009, _flow_tight_fix_1009


ENTRY_1009 = {'entryGate': True, 'flowMinHoldMins': 10, 'runnerMinChg1h': 0}


# ↪ moved to rep_predict.py: _entry_fix_1009, _vital_off_fix_1009, _moon_fix_1009, _floor_fix_1009, _flow_fix_1009


EDGE_AUDIT_PATH = FUSE_HQ_PATH.parent / 'edge_audit.json'


# ↪ moved to rep_predict.py: _proof_gate_tick, _proof_gate_fix_1010, _proof_clean_1013, _agent_open_fix_1012, _agent_real_fix_1012, _trail_fix_1014
# ↪ moved to rep_predict.py: _curve_fix_1011, _g4seat_fix_1016, _youticket_fix_1016, _germline_fix_1016, _mcfloor_fix_1016, _minage_fix_1014
# ↪ moved to rep_predict.py: _armed_fix_1013, _agent_control_set, _desk_buys_fix_1105, _agent_control_fix_1010, _agent_duty_fix_1010
# ↪ moved to rep_predict.py: _keephalf_fix_1010, _floor_off_fix_1009, _night_off_fix_1017, _rush_fix_1009, _volcycle_fix_1009, _degen_crazy_fix_1009
# ↪ moved to rep_predict.py: _agent_test_fix_1009, _agent_learn_fix_1009, _agent_seat_fix_1009, _ticket_ride_fix, _prime_reset_paper
# ↪ moved to rep_predict.py: _proven_candidates, _paper_broke


async def _prime_tick_inner(now):
    await _prime_unique_fix(now)
    await _prime_reset_paper(now)
    await _real_hold_fix(now)
    await _real_ride_fix(now)
    await _ticket_ride_fix(now)
    await _degen_fix_1009(now)
    await _overnight_fix_1009(now)
    await _hunt_fix_1009(now)
    await _hunt_fix_1009b(now)
    await _trench_fix_1009(now)
    await _procall_fix_1009(now)
    await _topseat_fix_1009(now)
    await _trench_safe_fix_1009(now)
    await _clean_fix_1009(now)
    await _flow_tight_fix_1009(now)
    await _entry_fix_1009(now)
    await _vital_off_fix_1009(now)
    await _moon_fix_1009(now)
    await _floor_fix_1009(now)
    await _flow_fix_1009(now)
    await _floor_off_fix_1009(now)
    await _night_off_fix_1017(now)
    await _keephalf_fix_1010(now)
    await _proof_gate_fix_1010(now)
    await _curve_fix_1011(now)
    _trail_fix_1014(now)
    await _armed_fix_1013(now)
    await _desk_buys_fix_1105(now)
    await _proof_clean_1013(now)
    await _minage_fix_1014(now)
    await _mcfloor_fix_1016(now)
    await _germline_fix_1016(now)
    await _g4seat_fix_1016(now)
    await _youticket_fix_1016(now)
    await _agent_real_fix_1012(now)
    await _agent_open_fix_1012(now)
    await _agent_control_fix_1010(now)
    await _agent_duty_fix_1010(now)
    await _rush_fix_1009(now)
    await _volcycle_fix_1009(now)
    await _degen_crazy_fix_1009(now)
    await _agent_test_fix_1009(now)
    await _agent_learn_fix_1009(now)
    await _agent_seat_fix_1009(now)
    await _ladder_keep_fix(now)
    cfg = _prime_cfg()
    if not cfg['on']:
        return 0
    pools, runners, anchors = await _prime_candidates()
    d = _json_load(FUSE_HQ_PATH, {})
    cards = dict((d.get('prime') or {}).get('cards') or {})
    snap_, ver_ = _prime.card_snap(cards), _hq_ver()   # what the tick STARTED from (an owner write during the tick must win)
    # one pair fetch → live price AND momentum for EVERY coin on the cards (majors + pools too, not only runner-board coins)
    books = (_fw_peek().get('books') or {})
    market_rows = _fw_market_rows(cards, books)
    pairs_ = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': l['pairAddress'], 'mint': l.get('mint')} for l in market_rows]) if market_rows else {}
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
    hs_tiers, hs_prof, _hs_n = _human_style()
    for tid in order_t:
        cur = cards.get(tid)
        liqs = {k: _fuse._f((v.get('liquidity') or {}).get('usd')) for k, v in pairs_.items()}
        _prime.LIQ_SRC.update({k: v.get('source') or 'dex' for k, v in pairs_.items()})   # 🧪 the rug shield never compares Jupiter's one-sided depth with a DexScreener entry
        cfg_t = {**_prime.clean_cfg(locks[tid]), 'paperFeeUsd': cfg['paperFeeUsd']} if tid in locks else _prime.tier_cfg(cfg, tid)   # 🔒 a locked tier runs its own frozen config · every other tier its own ⏱ clock
        _raw_paper = (d.get('prime') or {}).get('cfg') or {}
        cfg_t = {**cfg_t, **{k: v for k, v in _prime.PAPER_TRY.items() if k not in _raw_paper}}   # 🧪 fed lock + second ticket are tried on paper first
        real_t = bool((cur or {}).get('real'))
        if real_t:
            cfg_t = _prime_real_cfg(d.get('prime') or {})   # 💵 the real card runs ITS OWN config — paper edits / locks / engine tunes never touch it
            if cur is not None and _prime_real_cfg(d.get('prime') or {}).get('ladder'):
                cur = _ladder_step(cur, {'ladder': True}, now)
                cfg_t = _prime_real_cfg({**(d.get('prime') or {}), 'cards': {**((d.get('prime') or {}).get('cards') or {}), tid: cur}})
        if real_t and cur is not None and cfg_t.get('calloutSell', True):   # 📣 CALLOUT SPIKE SELL: profit sold into a rush of Pump callers (degen.py)
            try:
                rushing_ = {h['mint']: h['callers'] for h in _pc.rush(_pump_calls.get('calls') or [], now * 1000, 1e15, n=3, window_min=10)}
                hits_ = _dg.spike_sells(cur, px, rushing_, now) if rushing_ else []
                if hits_:
                    cur = {**cur, 'legs': [dict(x) for x in cur['legs']], 'events': list(cur.get('events') or []), 'spikeAt': dict(cur.get('spikeAt') or {})}
                    for pa_, why_ in hits_:
                        l_ = next((x for x in cur['legs'] if x.get('pairAddress') == pa_), None)
                        if l_ and _prime._skim(cur, l_, _fuse._f(px.get(pa_)), liqs, now, to=cfg_t.get('skimTo') or 'card', frac=_dg.SPIKE_FRAC, why=why_) > 0:
                            cur['spikeAt'][l_['mint']] = now
            except Exception as e:
                print('callout spike:', e)
        if cur is not None:   # 🔁 the card carries its own "no same coin unless it dipped" rule (arena_prime.cooling / note_dropped read it)
            cur = {**cur, 'rebuyDip': int(cfg_t.get('rebuyDipPct') or 0), 'ticketOff': bool(real_t and not cfg_t.get('youngTicket', False)), 'ticketRide': bool(real_t and cfg_t.get('ticketRide'))}
        # 🎯 PAPER = REAL: every tier (paper too) only rotates into coins real money could buy (pool ≥ minLiqUsd), so paper results are an
        # honest preview. ✅ Runners also need confirmation: rising over the last hour with buyers in control (≥55% buys) — no buying the top.
        def _lq(x):
            v = x.get('liquidity'); return _fuse._f(v.get('usd') if isinstance(v, dict) else v) or _fuse._f(x.get('liq')) or liqs.get(x.get('pairAddress'), 0.0)
        fw_cfg = _fw_peek().get('cfg') or {}
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
        # 🔎 PIPELINE (real cards): how many launch coins survive each step — shown on the card, so "why no new coin" is a number
        fun_ = []
        def _step(label, rows):
            if real_t:
                fun_.append([label, len([x for x in rows if not x.get('trenchOnly')])])
        _step('launch coins that pass every safety gate', runners)
        r_t = [x for x in runners if _lq(x) >= floor_of(x) * mg]
        _step(f'pool at least ${floor_of({}) * mg / 1000:,.0f}K (Fuse wallet min pool)', r_t)
        r_t = [x for x in r_t if _confirmed(x)]
        _step('up on the hour with buyers at 55%+', r_t)
        if real_t:   # 🌦 real money buys runners by the weather the engine's own sims measured (rain = strong + deep only · storm = none)
            r_t = _prime.weather_runners(r_t, _real_weather()['level'], _fw.clean_cfg(fw_cfg)['minLiqUsd'], _lq, cfg_t)
            _step(f"runner weather ({_real_weather()['level']}) + min age {_fuse._f(cfg_t.get('runnerMinAgeH')):g}h", r_t)
        else:   # 📄 paper = what real money could buy: no runner under 12h old (unknown age = out) — the paper Arena cards bled on launch pumps
            r_t = _prime.weather_runners(r_t, 'clear', 0, _lq, cfg_t)
        # 🗑 trench coins (strict gate, cached by the warm loop) — only a 🗑 trench slot ever takes one; own pool floor; real money
        # never buys one in a runner storm. The real-money runner age rule doesn't apply to them: the trench gate replaces it.
        tr_floor = _fw.clean_cfg(fw_cfg)['trenchMinLiqUsd']   # paper uses the same floor (paper = what real money could buy)
        # 🗑 `trenchAuto` off (the owner's switch): the engine is handed NO trench coin — they stay on the list for the owner's hand
        if cfg_t.get('trenchAuto', True) and not (real_t and (_real_weather()['level'] == 'storm')):
            # 🗑 THE TRENCH DROP reads the whole trench LIST, not the trench settings (owner: "no settings or configs — one of the
            # best possible coins from the trench list"): coins passing the owner's filter, then the engine scan's own passes, then
            # coins that clear every SAFETY check and miss only a crowd / age / size line. Safety is never skipped. Smart entry
            # (`trench_entry`: not falling, not mid-spike, buyers ≥ 55%) decides WHEN; best trench score first.
            tr_all, tr_seen = [], {y.get('mint') for y in r_t}
            # 🔥 SEND IT first — only once the call has PROVEN itself on its own record and the owner's switch is on (safe coins only)
            sendit_ = [{**x, 'trenchScore': 100 + _fuse._f((x.get('tv') or {}).get('heat')), 'sendIt': True} for x in (_call_cache.get('send') or [])] \
                if (cfg_t.get('sendItAuto', True) and _sendit_ready()) else []
            # 🔥 SEND IT ONLY (owner's switch): the trench list itself reads −79% an hour on its own record, the SEND IT call +0.5% (52% won)
            # 🧠 TRENCH BRAIN first — only once its walk-forward proof holds and the owner's switch is on (safe coins, learned play > 0)
            if cfg_t.get('trenchBrain', True) and _brain_ready():
                sendit_ = [x for x in _brain_rows()[:6] if x['brain']['est'] > 0 and x.get('safe') is True] + sendit_
            pro_ = _pc.pro_entries(_pump_calls.get('calls') or [], _pump_calls.get('callers') or {}, [_with_tv(x) for x in _open_board()], now * 1000) if cfg_t.get('proCallEntry') else []
            if (cfg_t.get('agentFeed') or cfg_t.get('agentLearn')) and not cfg_t.get('deskBuysOff'):   # 🤖 the agents' GO calls first — proven, or ONE small 🎓 learning seat
                sendit_ = _agents_go_rows((cur or {}).get('legs'), cfg_t.get('agentSeats'), cfg_t.get('agentLearn'), cfg_t.get('agentLearnPct'), cfg_t.get('agentTrust')) + sendit_
            if cfg_t.get('trenchRush'):   # ⚡ RUSH: the engine buys what the Rush board shows — trench + open-list coins that PASSED the scan, ranked by rush_score
                sendit_ = _rush_rows() + sendit_
            pool_t = _prime.trench_pool(sendit_, _trench_cache.get('rows'), _trench_cache.get('fallback'),
                                        [y for y in _trench_cache.get('checked') or [] if not y.get('ok') and _trench.soft_only(y.get('fails'))], cfg_t, pro=pro_)
            for x in pool_t:
                if x.get('mint') not in tr_seen and _lq(x) >= tr_floor * mg and _prime.trench_entry(x, mom) and _prime.trench_read_ok(_with_tv(x)) and (not real_t or _prime.trench_age_ok(x, cfg_t)):   # 🚨 real money: never a coin under the card's trench min age
                    tr_seen.add(x.get('mint')); tr_all.append({**x, 'trenchOnly': True})
            r_t = r_t + sorted(tr_all, key=lambda x: -_fuse._f(x.get('trenchScore') or x.get('score')))
        # 🪑 coins real money couldn't buy safely (2× in 10 min) are benched 1h for EVERY tier — paper never trades what real can't
        bench = set().union(*[_fw.benched(b, now) for b in (_fw_peek().get('books') or {}).values()] or [set()])
        if bench:
            p_t, r_t = [x for x in p_t if x.get('mint') not in bench], [x for x in r_t if x.get('mint') not in bench]
        if real_t:   # 🚪 real money never buys a coin that is falling right now (coins already on the card are not judged here)
            on_ = {l.get('mint') for l in (cur or {}).get('legs') or []}
            p_t = [x for x in p_t if x.get('mint') in on_ or _prime.entry_ok(x, mom)]
            r_t = [x for x in r_t if x.get('mint') in on_ or _prime.entry_ok(x, mom)]
        book_s = (_fw_peek().get('books') or {}).get(tid) or {} if cur and cur.get('real') else {}
        # 💵 the smallest order this card can send (sized to its seats) — the engine never opens a seat or cuts a coin by less
        mo_t = 0.0
        if cur and cur.get('real'):
            eq_t = _prime.value(cur, px, liqs)
            want_n = int(_fuse._f(cfg_t.get('coins'))) or len(cur.get('legs') or [])
            fit_n = _fw.fit_seats(eq_t, want_n)   # 🪑 a card too small for the owner's coin count holds the seats it can really fill
            if 0 < fit_n < want_n:
                cfg_t = {**cfg_t, 'coins': fit_n}
                if cur.get('seatFit') != fit_n:
                    cur = {**cur, 'seatFit': fit_n, 'events': list(cur.get('events') or []) + [{'at': now, 'kind': 'seat-wait', 'usd': round(eq_t, 4),
                           'why': f"🪑 the card is worth ${eq_t:.2f}: it holds {fit_n} of your {want_n} coins for now — a seat needs ${_fw.MIN_ORDER_FLOOR * _fw.SEAT_ROOM:.3f} or its buy cannot be sent. Seat {fit_n + 1} opens at ${(fit_n + 1) * _fw.MIN_ORDER_FLOOR * _fw.SEAT_ROOM:.2f}."}]}
            elif cur.get('seatFit'):
                cur = {k: v for k, v in cur.items() if k != 'seatFit'}
            mo_t = _fw.min_order(fw_cfg, eq_t, min(want_n, fit_n) or want_n)
        if mo_t:
            cfg_t = {**cfg_t, 'minOrderUsd': mo_t}
        stuck = set(_fw.stuck_buys(cur, now, bench, missed=book_s.get('misses'), pending_mint=(book_s.get('pending') or {}).get('toMint') or (book_s.get('pending') or {}).get('mint'),
                                     busy=bool(book_s.get('pending')) or _fw.slip_busy(book_s, now) or now - max([_fuse._f(t) for t in (book_s.get('soldAt') or {}).values()] or [0.0]) < 45,
                                     buy_pass_at=_FW_BUY_PASS.get(tid, 0.0))) if cur and cur.get('real') else set()
        if stuck:   # 🧾 a buy the LEDGER shows filled in the last 3 min is not stuck — the card's book just hasn't synced yet ($Americaexe filled 13:48:59, sent back to cash 13:49:01)
            landed_ = {r_.get('mint') for r_ in _fw_full_ledger()[-200:] if r_.get('card') == tid and r_.get('side') == 'buy' and r_.get('status') == 'filled' and now - _fuse._f(r_.get('at')) < 180}
            stuck = {pa_ for pa_ in stuck if next((l_.get('mint') for l_ in cur.get('legs') or [] if l_.get('pairAddress') == pa_), None) not in landed_}
        # (the stuck-buy swap runs BELOW, after every filter — see "⏳ STUCK BUYS")
        # ⏳ EVERY door obeys the card's min age on real money (pools, runners, seat refills, replacements, mover swaps): a row whose
        # age is known and under `runnerMinAgeH` is out whatever list it came from. $Grok came in 20 minutes old through a list
        # that was never age-checked and was pulled an hour later (−99.7%).
        if real_t:
            def _too_young(x, lim=_fuse._f(cfg_t.get('runnerMinAgeH'))):
                a_ = x.get('ageH')
                if a_ is None and _fuse._f(x.get('createdAt')) > 0:
                    a_ = (time.time() * 1000 - _fuse._f(x.get('createdAt'))) / 3.6e6
                return lim > 0 and a_ is not None and _fuse._f(a_) < lim and not x.get('trenchOnly')
            p_t = [x for x in p_t if not _too_young(x)]; r_t = [x for x in r_t if not _too_young(x)]
            # 🩺 EVIDENCE FLOOR (owner, 2026-10-08: "why put me in this coin" — $Attention+ came in as a ride-end replacement with buyers at 50% and no
            # 1h volume reading): a coin the engine buys by itself needs buyers ≥ FALLBACK_MIN_BUY when that number is known, and 1h volume ≥ FALLBACK_MIN_VOL
            # when THAT is known. Majors, stocks, comebacks and trench rows keep their own rules; the owner's hand picks are never judged.
            p_t = [x for x in p_t if not _prime.thin_flow(x)]; r_t = [x for x in r_t if not _prime.thin_flow(x)]
        # 💵 dollar-named tickers are never the engine's choice (pools, runners, new majors) — see fuse_wallet.dollar_named
        p_t = [x for x in p_t if not _fw.dollar_named(x.get('symbol'))]; r_t = [x for x in r_t if not _fw.dollar_named(x.get('symbol'))]
        # ⏱ each clock gets ITS coins: fast rounds rank by what is moving now, slow rounds keep depth / score order
        p_t, r_t = _prime.clock_rank(p_t, cfg_t['rotateHours'], mom), _prime.clock_rank(r_t, cfg_t['rotateHours'], mom)
        # 🧠 EDGE: runners are ranked by what the board's own record says about coins like them (pick_edge.py) — the hand-written score and
        # the "what is hot now" order both pointed at the coins that lost most. Real money buys only runners the record does not
        # expect to lose (cfg `edgeGate`, on by default); no table yet / table failing its own test = the order above stands.
        human_t = bool(not real_t and hs_prof and tid in hs_tiers)
        agents_t = bool(not real_t and cfg_t.get('pickStyle') == 'agents')   # 🤖 this PAPER card inherits the agents' judged list (below)
        tb_ = _edge_load().get('table')
        pth_ = _json_load(RUNNERS_PATH, {}).get('paths') or {}   # 📈 each candidate's own chart read (chart_read.py) joins its snapshot — table or not
        r_t = [{**x, **_pedge._chart.keys(pth_.get(x.get('mint')) or [], now)} for x in r_t]
        if real_t:   # 📈 a coin new to the board has no record of ours yet — read its chart from the market's own 15-min candles
            r_t = await _chart_fill(r_t, now)
        if tb_:
            r_t = _pedge.rank(r_t, tb_)
            if cfg_t.get('edgeGate', True) and not human_t and not agents_t:   # real AND paper (paper = real); a 👤 card is ordered by the owner's style instead
                r_t = _pedge.gate(r_t, tb_, float(cfg_t.get('edgeFloor') or 0))
        if agents_t:   # 🤖 its runner candidates ARE the agents' own READY / contending coins (no second scan; old list kept only when the desk is cold)
            inh_ = _agent_inherit_rows()
            r_t = inh_ or r_t
        if human_t:   # 👤 this PAPER card buys what the owner would pick: closest to their own picks first (pick_style.py)
            r_t = _ps.rank(r_t, hs_prof)
            # … and EXITS the way the owner does: the real card's own stop / lock / trail / hold / patience (its coins stay its own)
            rc_h = _prime_real_cfg(d.get('prime') or {})
            cfg_t = {**cfg_t, **{k: rc_h[k] for k in _prime.TIER_KEYS if k != 'trenchCoins' and rc_h.get(k) is not None}}
        if real_t and cur and cfg_t.get('pickVerify', True):   # ✅ a queued pick that turned bad before the bell is dropped, the old coin stays
            for l_ in cur.get('legs') or []:
                to_ = l_.get('swapTo') or {}
                c_ = next((r for r in _runner_cands if r.get('mint') == to_.get('mint')), None) if to_ else None
                bad_ = _rn.pick_check(c_, _runner_cfg())[1] if c_ and c_.get('scanned') and not to_.get('ack') else []   # an acknowledged pick is the owner's call
                if bad_:
                    l_.pop('swapTo', None)
                    cur['events'] = list(cur.get('events') or []) + [{'at': now, 'kind': 'rotate', 'symbol': to_.get('symbol'), 'usd': 0.0,
                                                                       'why': f"✅ your pick ${to_.get('symbol')} failed verification before the bell ({bad_[0]}) — not bought, ${l_.get('symbol')} stays"}]
        # 🆕 NEW COINS ONLY (cfg `newOnly`): the engine's choices are launch coins and nothing else — every door that reached for a
        # major or an old pool (shape seats, seat refills, "no runner → take a pool", extra seats) finds none, so a seat with no
        # qualifying new coin WAITS IN CASH. Coins the owner picked by hand stay (a re-shape never drops a pick).
        new_only_ = bool(real_t and cfg_t.get('newOnly'))
        if new_only_:
            p_t = []
        _step('not too young · not dollar-named · record gate', r_t)
        if real_t and cur and cur.get('rebuy'):   # 🔄 a rebuy waits for its sale to land, then the same coin takes the seat at a new entry
            bl_ = (((_fw_peek().get('books') or {}).get(tid) or {}).get('legs') or {}).get(cur['rebuy'].get('mint')) or {}
            cur = _prime.rebuy_in(cur, _fuse._f(bl_.get('atoms')) > 0, now)
        r_pre_ = list(r_t)   # 🔭 the scout's small ticket may take any SAFE mover (age + checks passed), not only coins on the card's full hunt line
        cb_ready_ = {}
        if real_t and cur and cfg_t.get('comeback', True) and cur.get('comeback'):   # 🔁 riders that left, watched for a recovered dip
            cb_store_, cb_ready_ = _prime.comeback_step(cur.get('comeback'), {x.get('mint'): _fuse._f(x.get('price')) for x in r_pre_}, now)
            cur = {**cur, 'comeback': cb_store_}
            if cb_ready_:
                r_pre_ = [({**x, 'comeback': cb_ready_[x['mint']]} if x.get('mint') in cb_ready_ else x) for x in r_pre_]
                r_t = [({**x, 'comeback': cb_ready_[x['mint']]} if x.get('mint') in cb_ready_ else x) for x in r_t]
        watch_ = []
        if real_t and cfg_t.get('upMeta', True):   # 🧭 UP NEXT IS META: the engine's own buys need a chart it can read, not falling
            watch_ = [x for x in r_t if not _prime.meta_ready(x)]   # 👀 shown under Coming up as "watching", with the reason
            r_pre_, r_t = _prime.meta_only(r_pre_, cfg_t, mom), _prime.meta_only(r_t, cfg_t, mom)
            _step('not mid-spike · not at its highs · chart readable · not trending down (up-next meta)', r_t)
        if real_t or cfg_t.get('pickStyle') in ('hunt', 'sniper'):   # 🏊 the owner's own runner line (real) · a paper card's own pick style
            r_t = _prime.deep_runners(r_t, cfg_t.get('runnerMinLiqK'), cfg_t.get('runnerMinBuy'), cfg_t.get('runnerMinVolK'), cfg_t.get('runnerMinChg1h'))
            _step('your hunt line (pool · volume · 1h move · buyers)', r_t)
        if real_t and cfg_t.get('entryGate'):   # 🎯 clean entries (trench tickets keep their own rules)
            r_t = [x for x in r_t if x.get('trenchOnly') or not _prime.entry_gate(x, mom)]
            _step('clean entry — buyers 50%+, not chasing, not at its highs, $50K+ pool, 6h+, $50K+/h', r_t)
        if real_t:   # 💀 never a dead coin (owner: "Coming up coins shouldn't be dead"): nothing in 5 min / < $3K or < 20 trades an hour
            r_t, r_pre_ = [x for x in r_t if not _ja.dead_why(x)], [x for x in r_pre_ if not _ja.dead_why(x)]
            _step('alive — traded in the last 5 min, $3K+ and 20+ trades an hour', r_t)
        if real_t and (cfg_t.get('vitalMin') or cfg_t.get('organicMin') or cfg_t.get('noSerial')):   # 🎛 the owner's vital filter (Coming up)
            vok_ = lambda x: _ja.filter_why((_jup_facts.get(x.get('mint')) or (0, None))[1], x, cfg_t) is None
            r_t, r_pre_ = [x for x in r_t if vok_(x)], [x for x in r_pre_ if vok_(x)]
            _step('your vital filter (grade · organic · crew)', r_t)
        # ⏳ STUCK BUYS are replaced HERE, from the fully filtered lists (min age, dollar names, record gate, chart / meta, the owner's
        # hunt line). This swap used to run before all of them, so a refused buy was replaced by ANY liquid coin: $BTT ("−100% inside
        # one candle this hour") took a seat, was refused too, and the seat looped through coins the card would never choose.
        if stuck:   # ⏳ the real card swaps a coin whose buy can't land (benched, or refused 15s ago) for a buyable one NOW
            before_ = cur
            cool_s = _prime.cooling(cur, now, cfg_t['rotateHours'], px)   # 🧊 … never for a coin that just left this card
            p_t, r_t = [x for x in p_t if x.get('mint') not in cool_s], [x for x in r_t if x.get('mint') not in cool_s]
            for pa in stuck:
                l = next((x for x in cur['legs'] if x.get('pairAddress') == pa), None)
                if not l:
                    continue
                why_s = "couldn't be bought safely — benched" if l.get('mint') in bench else "buy was refused — trying the next best coin" if l.get('mint') in (book_s.get('misses') or {}) else 'buy never landed in 2 min'
                why_x = ((book_s.get('benched') or {}).get(l.get('mint')) or (book_s.get('misses') or {}).get(l.get('mint')) or {}).get('why')
                why_s += f' ({why_x})' if why_x else ''   # the keeper's own reason, so a refused pick is never silent
                if l.get('picked'):   # 👤 YOUR pick is never swapped out or dropped by the engine — it waits (the keeper retries); ⏏ Pull is yours
                    if now - _fuse._f(l.get('waitNoteAt')) > 300:
                        l['waitNoteAt'] = now
                        cur = {**cur, 'events': list(cur.get('events') or []) + [{'at': now, 'kind': 'rotate', 'symbol': l.get('symbol'), 'usd': 0.0,
                                                                                    'why': f"⏳ your pick ${l.get('symbol')}: {why_s} — kept on your seat, the keeper keeps trying (⏏ Pull to drop it)"}]}
                    continue
                try:
                    if cur.get('holdBy') in ('proof', 'agents'):   # 🎮 held: the ENGINE swaps nothing in (2026-10-12: a refused agent buy became $Business, an engine pick)
                        why_s += ' — the card is held, no replacement'
                        raise ValueError('held')
                    want_usd = _fuse._f(l.get('wantUnits')) * (_fuse._f(px.get(pa)) or _fuse._f(l.get('entry')))
                    floor_s = _fw.NEW_SEAT_MIN if not _fw.held_units(book_s, l.get('mint')) else mo_t   # the keeper's own floor: a NEW coin opens its seat down to $0.05
                    if floor_s and want_usd < floor_s and want_usd < _fw.LEFTOVER_MIN_USD:
                        # the seat's money is under the smallest order the keeper sends: another coin would wait just the same
                        why_s = f"its ${want_usd:.2f} is under the smallest order the card can send (${floor_s:.2f})"
                        raise ValueError('unfundable seat')
                    tmp = {**cur, 'legs': [{**x, 'units': _fuse._f(x.get('wantUnits'))} if x is l else x for x in cur['legs']]}
                    # ⏭ NEXT UP FIRST (owner: "fall back to retry or swap to the next up buyable"): Coming up's ready coins from the last tick, in its order
                    up_ord = [u.get('mint') for u in ((cur.get('pipeline') or {}).get('up') or []) if not u.get('wait') and u.get('mint') != l.get('mint')]
                    r_pref = sorted(r_t, key=lambda x: up_ord.index(x.get('mint')) if x.get('mint') in up_ord else len(up_ord))
                    cur = _prime.replace_leg(tmp, pa, px, p_t, r_pref, anchors, cfg_t, now)
                    in_s = next((x.get('symbol') for x in cur['legs'] if x.get('mint') not in {y.get('mint') for y in tmp['legs']}), None)
                    cur['events'] = cur['events'][:-1] + [{**cur['events'][-1], 'why': f"⏳ ${l.get('symbol')} {why_s} — swapped for {'$' + in_s if in_s else 'a buyable coin'}{' (next up)' if in_s and any(x.get('symbol') == in_s and x.get('mint') in up_ord for x in r_pref) else ''}"}]
                except ValueError:   # nothing buyable of its role: the slot goes back to card cash (refilled next round), never waits forever
                    cur = {**cur, 'legs': [x for x in cur['legs'] if x is not l], 'events': list(cur.get('events') or []) + [
                        {'at': now, 'kind': 'rotate', 'symbol': l.get('symbol'), 'usd': 0.0, 'why': f"⏳ ${l.get('symbol')} {why_s} — slot back to card cash"}]}
            cur = _prime.note_dropped(before_, cur, now, cfg_t['rotateHours'], px)   # 🧊 the stuck coin cools like any coin that left
        mine = {l.get('mint') for l in (cur or {}).get('legs') or []}
        p_t = [x for x in p_t if x.get('mint') not in taken or x.get('mint') in mine]
        r_t = [x for x in r_t if x.get('mint') not in taken or x.get('mint') in mine]
        a_t = anchors
        run_ = ({x.get('mint') for x in _prime.movers(r_pre_, {}) + _prime.movers(r_pre_, cfg_t)} | set(cb_ready_)) if real_t else set()   # 🚀 running now → only the short cool-down
        cool = _prime.cooling(cur, now, cfg_t['rotateHours'], px, run_) - mine   # 🧊 coins this card just dropped sit out a few rounds → new coins flow in
        if cool:
            # 💵 A real stop must stay stopped. Falling back to the unfiltered
            # list when discovery was thin caused sell→immediate-rebuy churn.
            p_t = _prime_cool_candidates(p_t, cool, 2, strict=real_t)
            r_t = _prime_cool_candidates(r_t, cool, 3, strict=real_t)
        # 🪑 30-SECOND SEAT FALLBACK (real card; owner: "fill seats should be 30 secs, not the round"): when no coin clears the card's
        # full line, a seat empty for 30s takes the NEXT-BEST coin — one that passed safety, pool floor, weather, min age and the
        # record gate but is still being watched (at its highs / chart too short / under the hunt line). Never one falling now,
        # mid-spike, trending down, too wild, cooling or already on the card.
        if real_t and cur:
            fb_ids = {x.get('mint') for x in r_t} | set(cool) | mine
            fb_ = [x for x in _prime.flow_rank([y for y in list(r_pre_) + list(watch_) if not y.get('trenchOnly')])
                   if x.get('mint') not in fb_ids and _prime.seat_fallback_ok(x, mom)]
            # 🟢 … then BUY-BOTTOM coins (the owner's dips: far under their high, at the low of their range, no longer sliding) that
            # passed every safety check, clear the pool floor and the card's min age — a dip before a coin that already ran
            bt_m = {r.get('baseAddress'): r.get('divisionLabel') for r in _bottom_cache.get('rows') or []}
            min_age_ = _fuse._f(cfg_t.get('runnerMinAgeH'))
            bots_ = [{**r, 'tag': '🟢 buy bottom', 'bottomWhy': bt_m[r['mint']]} for r in _runner_cands
                     if r.get('mint') in bt_m and r.get('scanned') and not _rn.safety_fails(r, _runner_cfg()) and r['mint'] not in fb_ids
                     and _lq(r) >= floor_of(r) and _fuse._f(r.get('price')) > 0 and (r.get('ageH') is not None and _fuse._f(r.get('ageH')) >= min_age_)]
            fb_ = fb_ + [x for x in bots_ if x['mint'] not in {y.get('mint') for y in fb_}]
            if real_t:   # 🎛 the 30s seat fallback obeys the owner's vital filter too — and never takes a dead coin
                fb_ = [x for x in fb_ if _ja.filter_why((_jup_facts.get(x.get('mint')) or (0, None))[1], x, cfg_t) is None and not _ja.dead_why(x)]
            # ⏭ COMING UP BY CATEGORY (owner: "pick 1 of the best from the top for swap in categories"): each list (Pump trending,
            # Volume, Dips & bottoms, Movers, New launches, Trench) walked from ITS top; the first coin that passed the safety scan,
            # clears the pool floor + the card's min age, isn't dollar-named and is a sane entry (not falling / mid-spike / trending
            # down / too wild / at its highs) is that category's pick. They go FIRST in the 30s seat fallback: what Coming up shows
            # is what an empty seat takes.
            cand_by = {r.get('mint'): r for r in _runner_cands if r.get('mint')}
            seen_by = {x.get('mint'): x for x in list(r_pre_) + list(watch_) if x.get('mint')}
            def _cat_row(r):
                c_ = cand_by.get(r.get('mint'))
                return {**c_, **(seen_by.get(r.get('mint')) or {})} if c_ else None
            def _cat_ok(r):   # True, or the FIRST check it failed (shown per category under Coming up)
                x = _cat_row(r)
                if not x:
                    return 'not on the runner board yet'
                if not x.get('scanned'):
                    return 'holder scan not done'
                if _rn.safety_fails(x, _runner_cfg()):
                    return 'failed safety'
                if x['mint'] in fb_ids:
                    return 'on the card / cooling / already next'
                if _lq(x) < floor_of(x):
                    return 'pool under your floor'
                if _fuse._f(x.get('price')) <= 0:
                    return 'no live price'
                if x.get('ageH') is None or _fuse._f(x.get('ageH')) < min_age_:
                    return f'under your {min_age_:g}h min age'
                if _fw.dollar_named(x.get('symbol')):
                    return 'dollar-named'
                if _prime.at_high(x):
                    return 'at its highs'   # 🏔 never a coin sitting at its highs (owner)
                if not _prime.seat_fallback_ok(x, mom):
                    return 'falling / spiking'
                if real_t and _ja.dead_why(x):
                    return 'dead (nobody trading it)'
                vw_ = _ja.filter_why((_jup_facts.get(x['mint']) or (0, None))[1], x, cfg_t) if real_t else None
                if vw_:
                    return 'your vital filter'
                return True
            open_by = {r['mint']: r for r in (_open_board() if _open_pairs else (_open_cache.get('rows') or [])) if r.get('mint')}   # every feed coin, scanned or not
            cat_lists = {**_lens_rows, 'bottom': [{'mint': r.get('baseAddress')} for r in _bottom_cache.get('rows') or []],
                         'trench': [{'mint': r.get('mint')} for r in _trench_cache.get('rows') or []] or [{'mint': m} for m in list(open_by)[:60]]}   # 🗑 never an empty door: the open list stands in
            try:
                cat_picks, cat_miss = _prime.category_picks(cat_lists, _cat_ok, _list_records())
            except Exception:
                cat_picks, cat_miss = [], {}
            cat_rows = [{**_cat_row(p_), 'tag': f"{p_['catLabel']} #{p_['rank']}", 'cat': p_['cat'], 'catRank': p_['rank']} for p_ in cat_picks]
            # 🧬 EDGE FIRST (owner: "coming up should be the best of my swap-in, not bs"): every coin of the swap-in lists ranked by evidence
            # (confluence.py); the ones that clear every check of this card come first — Coming up shows them and an empty seat takes them.
            edge_ready, edge_watch = [], []
            if real_t:
                for e_ in _edge_rank()[:80]:
                    m_ = e_.get('mint')
                    if not m_ or m_ in mine:
                        continue
                    if e_['edge']['known'] and e_['edge']['edge'] <= EDGE_BUY_MIN:
                        continue   # the evidence says it typically loses badly: never Coming up, never an engine buy
                    v_ = _cat_ok({'mint': m_})
                    if v_ is True:
                        edge_ready.append({**_cat_row({'mint': m_}), 'tag': _cf.words(e_['edge']), 'edge': e_['edge'], 'cat': 'edge'})
                    elif v_ not in ('not on the runner board yet', 'holder scan not done', 'failed safety', 'dead (nobody trading it)') and len(edge_watch) < 6:
                        edge_watch.append({**(_cat_row({'mint': m_}) or e_), 'tag': _cf.words(e_['edge']), 'edge': e_['edge'], 'watchWhy': v_})
                    if len(edge_ready) >= 6:
                        break
                if edge_ready and cfg_t.get('flowEntry', True):   # 🌊 FLOW ENTRY: never buy into a minute where sellers lead (the tape of the top 4)
                    fl_ = await _flow_fetch([x.get('pairAddress') for x in edge_ready[:8]])
                    ok_, held_ = [], []
                    for x in edge_ready:
                        w_ = fl_.get(x.get('pairAddress'))
                        why_ = _flow.entry_why(w_) if x.get('pairAddress') in fl_ else None
                        x = {**x, 'flow': {k: w_.get(k) for k in ('buyUsd', 'sellUsd', 'n', 'pxChg')} if w_ else None}
                        (held_ if why_ else ok_).append({**x, 'watchWhy': why_} if why_ else x)
                    burst_ = []
                    for x in ok_:   # ⚡ BUY BURST: a coin whose last 90s is a buying burst goes to the front (it is tagged; its own record is 'burst')
                        bw_ = _dg.burst_why(fl_.get(x.get('pairAddress')))
                        if bw_:
                            burst_.append({**x, 'tag': f"⚡ buy burst · {x.get('tag') or ''}".strip(' ·'), 'burst': bw_})
                    edge_ready = burst_ + [x for x in ok_ if x.get('mint') not in {y['mint'] for y in burst_}]
                    global _burst_last
                    _burst_last = [(x['mint'], _fuse._f(x.get('price'))) for x in burst_]
                    for x in edge_ready:
                        if _smart_on(x.get('mint')):
                            x['tag'] = f"🐳 {len(_smart_on(x['mint']))} smart · {x.get('tag') or ''}".strip(' ·')
                    edge_watch = held_ + edge_watch
                cat_rows = edge_ready + [x for x in cat_rows if x.get('mint') not in {y['mint'] for y in edge_ready}]
            # 🚪 EVERY DOOR ALWAYS SHOWS ONE COIN (owner: "1 trench, 1 pump, 1 volume"): a door with nothing that clears every check shows its
            # best coin as WATCHING, with the first check it misses. Watch rows are only shown — never seated by the engine, owner-pickable.
            door_watch = _prime.door_watch(
                cat_picks, cat_lists, lambda r_: _cat_row(r_) or open_by.get(r_.get('mint')),
                lambda r_, x_: _cat_ok(r_) if _cat_row(r_) else ('failed safety' if x_.get('safe') is False else 'holder scan not done'),
                lambda m_, x_: m_ in fb_ids or m_ in mine or _fuse._f(x_.get('price')) <= 0 or _fw.dollar_named(x_.get('symbol')))
            fb_ = cat_rows + [x for x in fb_ if x.get('mint') not in {y['mint'] for y in cat_rows}]
            cfg_t = {**cfg_t, 'seatFallback': list({x.get('mint'): x for x in reversed(fb_)}.values())[::-1][:8], 'catPicks': cat_rows, 'catWatch': door_watch, 'catMiss': cat_miss,
                     'edgeReady': edge_ready, 'edgeWatch': edge_watch}
        if real_t and cfg_t.get('bangerRefill'):   # 🚀 every seat that opens (flow exit, stop, rotation, ride over) takes a banger first
            b_ = _bangers(mine, cool, mom, _lq, _fw.clean_cfg(fw_cfg)['minLiqUsd'], now, gate=bool(cfg_t.get('entryGate')))
            if b_:   # 🌊 the tape decides the order: ⚡ burst / 🧲 absorb first, a 🩸 dump or 🏔 climax (buying the top) waits
                fl_b = await _flow_fetch([x.get('pairAddress') for x in b_[:8]])
                tp_ = {x['mint']: _flow.tape_read(fl_b.get(x.get('pairAddress'))) for x in b_}
                b_ = [{**x, 'tape': tp_.get(x['mint']), **({'tag': f"{_flow.TAPES[tp_[x['mint']]]} · {x['tag']}"} if tp_.get(x['mint']) in ('burst', 'absorb') else {})}
                      for x in b_ if tp_.get(x['mint']) not in ('dump', 'climax')]
                b_ = sorted(b_, key=lambda x: 0 if x['tag'].startswith(('⚡', '🧲')) else 1)
            cfg_t = {**cfg_t, 'bangers': b_}
            _best_rows[:] = list(b_ or [])   # 🏆 the 🏆 Best now tab + the card's Best 3 read this list
        if real_t and cfg_t.get('entryGate'):   # 🎯 the 30s seat fallback and Coming up's category picks obey clean entries too
            cfg_t = {**cfg_t, 'seatFallback': [x for x in cfg_t.get('seatFallback') or [] if not _prime.entry_gate(x, mom, core=True)]}   # 🪑 the 30s fill: core rules only
        if real_t and cfg_t.get('volCycle'):   # 🪑 EMPTY SEATS FILL FROM THE VOLUME LIST TOO (owner: "seats are supposed to auto fill"): the engine's own funnel
            # often ends at 0 coins, and the volume cycle only ever REPLACED a flat coin — an empty seat sat in cash. Same rows the cycle buys
            # (6h+, $50K+ pool, $50K+/h, buyers ahead, rush-clean), busiest first, ahead of the 30s fallback list.
            vr_ = [{**x, 'liquidityUsd': x.get('liq'), 'tag': '🌊 volume'} for x in _prime.vol_cycle_rows([_with_tv(y) for y in _open_board() or [] if y.get('safe') is True])
                   if x.get('mint') not in mine and x.get('mint') not in cool and x.get('mint') not in bench and _lq(x) >= _fw.clean_cfg(fw_cfg)['minLiqUsd']
                   and not _fw.dollar_named(x.get('symbol')) and _fuse._f(x.get('price')) > 0][:4]
            cfg_t = {**cfg_t, 'seatFallback': vr_ + [x for x in cfg_t.get('seatFallback') or [] if x.get('mint') not in {y['mint'] for y in vr_}]}
        # 🧊 anchors cool too: a major this card just sold isn't bought back for 3 rounds while another major is available
        a_t = _prime_cool_candidates(anchors, cool, 2, strict=real_t and len([x for x in anchors if x.get('mint') not in cool]) >= 1) if cool else anchors
        if new_only_:
            a_t = []
        # 🚀 MOVER UPGRADE (real cards, cfg `moverSwap`): a coin that is not moving (±10% of its entry after 20 min, never a rider /
        # frozen / picked coin) gives its seat to a coin that IS — the card's own hunt selection, else ≥ $50K in the hour and up
        # ≥ 20%. One per card per 30 min. Rotation only ever swapped LOSERS, so a flat coin sat on the card for good while a
        # hunt-ready coin waited on the board (2026-10-06: $USDP +2% held, $GOMO +44% / $123K an hour not bought).
        # 🔭 SCOUT & PROMOTE (cfg `scoutPct` > 0) replaces the plain mover swap: one small ticket hops between movers every round;
        # a scout that proves itself is promoted to a full-size holder (arena_prime.scout_step).
        _lrec = _list_records() if real_t else {}
        _movers_off = _prime.list_paused(_lrec, 'movers')   # movers' own 1h record is a clear loser → the FULL-SIZE mover swap sits out (the scout's small ticket still hunts)
        if real_t and cur and _fuse._f(cfg_t.get('scoutPct')) > 0 and now - _fuse._f(cur.get('scoutAt')) >= max(120.0, _fuse._f(cfg_t.get('rotateHours')) * 3600 * 0.9):
            was_ = cur
            hot_s = [x for x in [y for y in r_pre_ if y.get('comeback')] + _prime.movers(r_t, cfg_t) + _prime.movers(r_pre_, {}) if x.get('mint') not in mine and x.get('mint') not in cool and x.get('mint') not in taken]
            nw_ = _prime.scout_step(cur, px, _prime.flow_rank(list({x['mint']: x for x in reversed(hot_s)}.values())[::-1]), cfg_t, now, p_t, anchors)   # the scout takes the best-LOOKING mover, not just the biggest hour
            if nw_ is not cur:
                cur = _prime.note_dropped(was_, {**nw_, 'scoutAt': now}, now, cfg_t['rotateHours'], px)
        elif real_t and cur and not _movers_off and cfg_t.get('moverSwap', True) and not cur.get('holdAll') and not cur.get('flooredAt') and now - _fuse._f(cur.get('moverAt')) >= _prime.MOVER_EVERY_SEC:
            hot_ = [x for x in _prime.movers(r_t, cfg_t) if x.get('mint') not in mine]
            fl_ = _prime.flat_leg(cur, px, now, max(_prime.FLAT_HOLD_SEC, _fuse._f(cfg_t.get('minHoldMins')) * 60)) if hot_ else None
            if fl_:
                try:
                    was_ = cur
                    nw_ = _prime.replace_leg(cur, fl_['pairAddress'], px, p_t, hot_, anchors, cfg_t, now)
                    in_ = next((l for l in nw_['legs'] if l.get('mint') not in mine), None)
                    row_ = next((x for x in hot_ if in_ and x.get('mint') == in_.get('mint')), {})
                    nw_['events'] = nw_['events'][:-1] + [{**nw_['events'][-1], 'why': f"🚀 mover in: ${(in_ or {}).get('symbol')} is up {_fuse._f(row_.get('chg1h')):+.0f}% on the hour on ${_fuse._f(row_.get('vol1h')) / 1000:,.0f}K volume — ${fl_.get('symbol')} was not moving"}]
                    nw_['moverAt'] = now
                    cur = _prime.note_dropped(was_, nw_, now, cfg_t['rotateHours'], px)
                except ValueError:
                    pass
        # 🌊 VOLUME CYCLE (owner: "need to be cycling new volume coins"): every `volEvery` min a coin that is NOT moving (±10% after its hold —
        # your picks too, the owner gave the keys; ❄ frozen / riding / house coins never) gives its seat to the busiest clean volume coin
        # on the open list. Every keeper check still decides the buy.
        if real_t and cur and cfg_t.get('volCycle') and not cur.get('holdAll') and not cur.get('flooredAt') and now - _fuse._f(cur.get('volAt')) >= _fuse._f(cfg_t.get('volEvery') or 10) * 60:
            fwc_v = _fw.clean_cfg(fw_cfg)
            hot_v = [x for x in _prime.vol_cycle_rows([_with_tv(y) for y in _open_board() or [] if y.get('safe') is True])
                     if x.get('mint') not in mine and x.get('mint') not in cool and x.get('mint') not in bench and _lq(x) >= fwc_v['minLiqUsd']
                     and not _fw.dollar_named(x.get('symbol')) and _fuse._f(x.get('price')) > 0][:6]
            fl_v = _prime.flat_leg(cur, px, now, max(600.0, _fuse._f(cfg_t.get('minHoldMins')) * 60), picks=True) if hot_v else None
            if fl_v:
                try:
                    was_ = cur
                    hot_v = [{**x, 'liquidityUsd': x.get('liq'), 'score': 100} for x in hot_v]
                    nw_ = _prime.replace_leg(cur, fl_v['pairAddress'], px, p_t, hot_v, anchors, cfg_t, now)
                    in_ = next((l for l in nw_['legs'] if l.get('mint') not in mine), None)
                    row_ = next((x for x in hot_v if in_ and x.get('mint') == in_.get('mint')), {})
                    g_ = (_fuse._f(px.get(fl_v['pairAddress'])) / _fuse._f(fl_v.get('entry')) - 1) * 100 if _fuse._f(fl_v.get('entry')) > 0 else 0.0
                    nw_['events'] = nw_['events'][:-1] + [{**nw_['events'][-1], 'why': f"🌊 volume cycle: ${(in_ or {}).get('symbol')} in — ${_fuse._f(row_.get('vol1h')) / 1000:,.0f}K traded this hour, {_fuse._f(row_.get('buyShare')):.0f}% buys, {_fuse._f(row_.get('chg1h')):+.0f}% 1h — ${fl_v.get('symbol')} was flat ({g_:+.1f}%)"}]
                    for l in nw_['legs']:
                        if in_ and l.get('mint') == in_.get('mint'):
                            l['bought'] = {**(l.get('bought') or {}), 'tag': '🌊 volume'}
                            l.pop('picked', None)   # the ENGINE's choice (replace_leg marks hand swaps as yours) — you-vs-engine stays true
                    nw_['volAt'] = now
                    cur = _prime.note_dropped(was_, nw_, now, cfg_t['rotateHours'], px)
                except ValueError:
                    pass
        # 🤖 AGENT SEATS: coins the agents put on the card hold until `agentTakePct` profit; in profit the desk reads them again and lets them
        # run, pulls them (profit to cash, seat left open) or swaps them for a fresh GO runner (agents.manage). Only while they are proven.
        if real_t and cur:   # 🎮 the card as seats for HQ › Agents (display only)
            _agents['card'] = _pos.card_seats(cur, None, px, cfg_t, take=_of.take_line(cfg_t, _agents.get('scalp')))
        # 🎮 AGENT CONTROL (cfg `agentControl`; owner, 2026-10-10: "the agents should have control over my seats and switching coins … real
        # moves on my real money card — GO"): the card is held BY THE AGENTS (`holdBy: 'agents'` — every engine door that checks holdAll is
        # off: rotation, re-shape, rush, cycles, the engine's seat refill) and only they buy: they fill empty seats with `eligible` GO coins,
        # switch a coin whose read broke (after 15 min), bank at their take line. ≤ CONTROL_MOVES_HR real buys an hour.
        ctl_ = bool(real_t and cur and cfg_t.get('agentControl') and not cur.get('flooredAt'))
        if ctl_ and not (cur.get('holdAll') and cur.get('holdBy') == 'agents') and (not cur.get('holdAll') or cur.get('holdBy') == 'proof'):
            cur = {**cur, 'holdAll': True, 'holdBy': 'agents', 'events': (list(cur.get('events') or []) + [{'at': now, 'kind': 'hold', 'why': '🎮 the agents control every seat — the engine\'s own swaps are off'}])[-60:]}
        ctl_ = bool(ctl_ and cur.get('holdBy') == 'agents')   # a hold the owner set by hand stays a hold: nobody trades
        pol_ = _oe.policy(cfg_t) if real_t and cur else None   # 🎛 the creator's limits: per control AGENTS CHOOSE or CREATOR OVERRIDE
        if real_t and cur:   # 🔌 positions are "reconciled" once every held coin was read back with a live price in this process
            if all(_fuse._f(px.get(l.get('pairAddress'))) > 0 for l in cur.get('legs') or [] if not l.get('placeholder') and _fuse._f(l.get('units')) > 0):
                _office['boot']['reconciled'] = True
            _office['ticks'] = (list(_office.get('ticks') or []) + [now])[-6:]
        rd_ = _oe.ready(_office['boot'], now)
        _office['ready'] = rd_   # the kernel's Courier reads the office's readiness
        if ctl_:
            cur['agentWant'] = pol_['seats']
        moves_ = max(0, _uni.CONTROL_MOVES_HR - _oe.real_buys(cur.get('events'), _fw_full_ledger(), tid, now, moves=('swap',))) if ctl_ else None   # 🧮 SWITCHES (real buys only)
        fills_left_ = max(0, _uni.FILL_MOVES_HR - _oe.real_buys(cur.get('events'), _fw_full_ledger(), tid, now, moves=('fill',))) if ctl_ else None   # 🪑 empty-seat fills
        if real_t and cur and (ctl_ or (((cfg_t.get('agentFeed') and (_agents.get('view') or {}).get('feed')) or cfg_t.get('agentLearn')) and not cur.get('holdAll'))) and not cur.get('flooredAt'):
            # ⚙ HELD SEATS — ONE brain: the kernel's position manager (trench_kernel.positions) + Reaper (office.reap). A challenger is a coin the
            # kernel has READY; a held coin and its challenger are compared on the kernel's own rank. No paper call, case file, lean or duty clock.
            due_ = bool(ctl_ and moves_ and _oe.cycle_due(pol_, cur.get('agentCycleAt'), now))
            if due_:
                cur['agentCycleAt'] = now; _office['cycleN'] = int(_office.get('cycleN') or 0) + 1
            cool = set(cool) | _agent_blocked(cur, now)
            on_k = {l.get('mint') for l in cur.get('legs') or []}
            ranks_ = _tk.KERNEL.ranks()
            ready_ = [c_ for c_ in (_tk.KERNEL.candidate(m_, d_) for m_, d_ in _tk.KERNEL.ready(exclude=set(cool) | on_k)) if c_ and not _fw.dollar_named(c_.get('symbol'))]
            cases_ = _tk.KERNEL.cases(exclude=on_k) if ctl_ else []
            full_ = bool(ctl_ and len([l for l in cur.get('legs') or [] if not l.get('placeholder')]) >= pol_['seats'])
            # 🔌 a coin is "off the board" only when the office is LIVE again after a restart AND it has been missing for the grace
            radar_ = {m_ for m_, p_ in (_office.get('pos') or {}).items() if _oe.radar_gone(p_.get('offSince'), now, rd_['live'])}
            vels_, margins_ = {}, {}
            scores_ = {m_: {'score': r_} for m_, r_ in ranks_.items()}   # 🏅 the kernel's rank IS the seat score (one ranking)
            if ctl_:
                try:
                    vels_ = _office_vels(cur, px, now)
                    best_r = ranks_.get(ready_[0]['mint']) if ready_ else None
                    for l in cur.get('legs') or []:
                        hr_ = ranks_.get(l.get('mint'))
                        if best_r is not None and hr_ is not None:   # (how far the best READY coin outranks this seat, what a switch needs)
                            margins_[l.get('mint')] = (round(best_r - hr_, 1), round(hr_ * (_pos.margin_need(pol_['switch'].get('mode')) - 1), 1))
                except Exception as e:
                    print('seat ranks:', e)
            dec_ = _pos.manage(cur.get('legs'), _agents.get('table'), px, cfg_t, _agents.get('scalp'), control=ctl_, now=now, moves_left=((1 if due_ and full_ else 0) if ctl_ else moves_),   # an EMPTY seat comes first: no switch while one is open
                               challengers=ready_, pol=pol_, radar=radar_, reviews={r_.get('mint'): r_.get('verdict') for r_ in _office.get('reports') or []}, live=rd_['live'], ranks=ranks_, vels=vels_ or None)
            # 🪑 A TIME EXIT IS A SWAP: it fires only while a buy is free AND a READY replacement exists NOW (after the empty seats take theirs)
            open_n = max(0, int(_fuse._f((pol_ or {}).get('seats'))) - len([l for l in cur.get('legs') or [] if not l.get('placeholder')]))
            spare_ = None if fills_left_ is None else min(fills_left_, len(ready_)) - open_n
            dec_ = _office_reap(cur, px, cfg_t, ctl_, now, dec_, pol_, rd_['live'], vels_, margins_, spare_, edge=margins_)   # ☠ Reaper's exit requests join the SAME decision list (it has no path of its own)
            cert_ = {l.get('pairAddress') for l in cur.get('legs') or [] if l.get('certified') and not l.get('placeholder')}
            if cert_:   # 🛡 a coin YOU certified is yours to hold — the desk's own swap / pull never touches it (only a pulled pool, −45%, your limits)
                dec_ = [x for x in dec_ if x.get('pair') not in cert_ or any(h_ in str(x.get('why')) for h_ in ('R1 ', 'R5x', 'R5c', 'R5g', 'R9c', 'drain'))]
            g4p_ = {l.get('pairAddress'): l for l in cur.get('legs') or [] if l.get('aiSeat') and not l.get('placeholder')}
            for gs_ in [x_ for x_ in (_g4.pop('set', None), _g4.pop('setAgent', None)) if x_ and _seat.fresh(x_, now)]:   # 🎯 a model moved take / stop / trail: its own seat, or an agents coin (never yours / certified)
                for l in cur['legs']:
                    if l.get('pairAddress') == gs_.get('pair') and not l.get('placeholder') and not l.get('certified') and (l.get('aiSeat') if gs_.get('own') is not False else (_uni.is_agent(l) and not l.get('picked') and not l.get('aiSeat'))):
                        e_, p_ = _fuse._f(l.get('entry')), _fuse._f(px.get(l.get('pairAddress')))
                        ch_ = _seat.line_change(l, {'aiTp': gs_.get('tp'), 'aiSl': gs_.get('sl'), 'aiTrail': gs_.get('trail')}, (p_ / e_ - 1) * 100 if e_ > 0 and p_ > 0 else None)   # 🛑 no −3% stops, no 35 ↔ 30 jitter
                        l.update(ch_)
                        if ch_ and not l.get('aiSeat'):
                            l['aiBy'] = gs_.get('by')
                        if ch_:
                            cur.setdefault('events', []).append({'at': now, 'kind': 'agent', 'move': 'lines', 'why': f"🎯 {gs_.get('by')} set ${l.get('symbol')}: " + ' · '.join(f"{ {'aiTp': 'TP +', 'aiSl': 'SL −', 'aiTrail': 'trail ↩'}[k_]}{v_:g}%" for k_, v_ in ch_.items())})
            if g4p_:   # 🧠 G4's seat: the agents only argue — a pulled pool, −45% and the creator's own limits still sell it
                dec_ = [x for x in dec_ if x.get('pair') not in g4p_ or any(h_ in str(x.get('why')) for h_ in ('R1 ', 'R5x', 'R5c', 'R9c', 'drain'))]
                w_ = _g4.get('want')
                if w_ and w_.get('action') == 'SELL' and _seat.fresh(w_, now) and pol_.get('aiSeat') == 'real' and w_.get('pair') in g4p_ and not any(x.get('pair') == w_['pair'] for x in dec_):
                    dec_.append({'action': 'pull', 'pair': w_['pair'], 'symbol': g4p_[w_['pair']].get('symbol'), 'why': f"🧠 {w_.get('model') or 'G4'} sold: {w_.get('why')}", 'bank': w_.get('bank'), 'bankBy': w_.get('model')})
                    _g4['want'] = None
                elif w_ and w_.get('action') == 'TRIM' and _seat.fresh(w_, now) and pol_.get('aiSeat') == 'real' and w_.get('pair') in g4p_ and not any(x.get('pair') == w_['pair'] for x in dec_):
                    dec_.append({'action': 'trim', 'pair': w_['pair'], 'symbol': g4p_[w_['pair']].get('symbol'), 'pct': w_.get('trim') or 50, 'why': f"🧠 {w_.get('model') or 'G4'} banked {w_.get('trim') or 50}%: {w_.get('why')}", 'bank': w_.get('bank'), 'bankBy': w_.get('model')})   # ✂ its trade, its call
                    _g4['want'] = None
            if ctl_:   # ⇄ the switching evaluation the page shows: each held coin against the best READY challenger (display only — `positions.manage` decided)
                try:
                    verd_ = {r_.get('mint'): r_.get('verdict') for r_ in _office.get('reports') or []}
                    held_l = [l for l in cur.get('legs') or [] if not l.get('placeholder') and _fuse._f(l.get('units')) > 0 and _fuse._f(l.get('entry')) > 0 and _fuse._f(px.get(l.get('pairAddress'))) > 0]
                    tests_ = [{'mint': l.get('mint'), **_pos.switch_view(l, (_fuse._f(px[l['pairAddress']]) / _fuse._f(l['entry']) - 1) * 100, (now - _fuse._f(l.get('at'))) / 60 if l.get('at') else 0.0,
                                                                        ready_[0] if ready_ else None, ranks_, pol_, verd_.get(l.get('mint')), vels_.get(l.get('mint')))} for l in held_l]
                    _agents['switchTests'] = tests_
                    _agents['switchEval'] = None if not tests_ else {**min(tests_, key=lambda t_: (not t_['switch'], t_['current']['pnl'])), 'at': now, 'dueIn': max(0, round(_fuse._f(cur.get('agentCycleAt')) + max(30.0, _fuse._f(pol_['seatTarget'])) - now)), 'full': full_}
                except Exception as e:
                    print('switch eval:', e)
            try:
                cur = _germ_rebuy_step(cur, px, now)   # 🦠 a coin your Gstop sold printed a NEW germ floor: it is queued back as your seat pick
            except Exception as e:
                print('germ rebuy:', e)
            _agents['decisions'] = [{k: v for k, v in x.items() if k != 'to'} | ({'toSym': x['to']['symbol']} if x.get('to') else {}) for x in dec_]
            _agents['card'] = _pos.card_seats(cur, _agents['decisions'], px, cfg_t, take=_of.take_line(cfg_t, _agents.get('scalp')))
            night_ = False
            if real_t and cfg_t.get('nightGuard', True) is not False:   # 🌙 the circuit breaker: a paused card buys NOTHING real (exits keep running)
                try:
                    if _night_check(now):
                        cfg_t, night_ = {**cfg_t, 'agentPaper': True}, True
                except Exception as e:
                    print('night guard:', str(e)[:120])
            paper_ = bool(cfg_t.get('agentPaper'))
            for x in dec_:
                try:
                    if x['action'] == 'swap' and (paper_ or cfg_t.get('deskBuysOff')):   # 📄 a switch-in is a real BUY: on paper, or with desk buys off, it is only recorded (the shadow book)
                        _shadow_note(x.get('to'), 'switch', now, cur); continue
                    if x['action'] == 'swap' and ctl_ and _office_warden(cur, x['to'], _fuse._f(next((_fuse._f(l.get('units')) * (_fuse._f(px.get(l.get('pairAddress'))) or _fuse._f(l.get('entry'))) for l in cur.get('legs') or [] if l.get('pairAddress') == x['pair']), 0.0)), cfg_t, now, 'swap')['veto']:
                        continue   # 🛡 a switch carries the old seat's money as it is: the Warden may only veto it
                    if x['action'] == 'pull' and 'R5g' in str(x.get('why')):   # 🦠 a Gstop sale: watch the coin for a NEW germ floor to buy it back
                        lg_g = next((l for l in cur.get('legs') or [] if l.get('pairAddress') == x['pair']), None)
                        if lg_g:
                            cur['germRebuy'] = {**{m_: v_ for m_, v_ in (cur.get('germRebuy') or {}).items() if now - _fuse._f(v_.get('at')) < GERM_REBUY_SEC},
                                                lg_g.get('mint'): {'pair': x['pair'], 'symbol': lg_g.get('symbol'), 'lens': lg_g.get('gstop') or 'both', 'at': now, 'px': _fuse._f(px.get(x['pair']))}}
                    if real_t and x['action'] in ('pull', 'trim') and ctl_:   # 🕰 agent min hold: a soft exit of a red coin waits 15 min from the buy
                        lg_w = next((l for l in cur.get('legs') or [] if l.get('pairAddress') == x['pair']), None)
                        w_ = _prime.agent_hold_wait(lg_w, px.get(x['pair']), x.get('why'), now)
                        if w_ > 0:
                            x['held'] = f"🕰 min hold: {round(w_ / 60)} min left before an agent may sell it (stops / rug still act)"
                            continue
                    if x['action'] == 'pull' and ctl_:
                        was_ = cur
                        lg_ = next((l for l in cur.get('legs') or [] if l.get('pairAddress') == x['pair']), None)
                        if lg_ and _fuse._f(lg_.get('entry')) > 0 and 0 < _fuse._f(px.get(x['pair'])) < _fuse._f(lg_['entry']):   # left at a loss: this thesis is not bought back for 6h
                            st_o = _office_state(); st_o['lostAt'] = {**{m_: a_ for m_, a_ in (st_o.get('lostAt') or {}).items() if now - _fuse._f(a_) < _oe.FAILED_SEC}, lg_.get('mint'): now}
                        cur['agentExitAt'] = now
                        cur = _prime.agent_pull(cur, x['pair'], px, liqs, now, x['why'])   # in control: banked to FREE card cash, the seat opens for their next coin
                        if x.get('bank'):   # 🅿 the model chose to park this sale's proceeds out of the coins for 1–3 rounds
                            cur = _prime.park_bank(cur, _fuse._f((cur['events'][-1] or {}).get('usd')), x['bank'], now, x.get('symbol'), x.get('bankBy'))
                        cur = _prime.note_dropped(was_, cur, now, cfg_t['rotateHours'], px)
                    elif x['action'] == 'trim' and ctl_:   # 💰 scale-out: half banked, the rest rides the trail
                        cur = _prime.agent_trim(cur, x['pair'], px, liqs, now, x.get('pct') or _of.PICK_LOCK_SELL if (x.get('pct') or 'R5b' in str(x['why'])) else (_of.scale_of(pol_) or (0, _of.SCALE_PCT))[1], x['why'])   # 🔒 your pick: a portion, the rest rides your stop
                        if x.get('bank'):
                            cur = _prime.park_bank(cur, _fuse._f((cur['events'][-1] or {}).get('usd')), x['bank'], now, x.get('symbol'), x.get('bankBy'))
                    elif x['action'] == 'pull':
                        cur = _prime.sell_leg_to_cash(cur, x['pair'], px, now, 100.0)
                        cur['events'].append({'at': now, 'kind': 'agent', 'symbol': x['symbol'], 'why': f"🤖 agents pulled ${x['symbol']}: {x['why']}"})
                    elif x['action'] == 'swap':
                        t_ = x['to']
                        row_ = {'mint': t_['mint'], 'symbol': t_['symbol'], 'pairAddress': t_['pair'], 'price': t_['px'], 'liquidityUsd': (t_.get('nums') or {}).get('liq'), 'score': 100,
                                'ageH': (t_.get('vitals') or {}).get('ageH'), 'vol1h': (t_.get('vitals') or {}).get('vol1h'), 'buyShare': (t_.get('nums') or {}).get('buy')}
                        was_ = cur
                        cur = _prime.replace_leg(cur, x['pair'], px, p_t, [row_], anchors, cfg_t, now)
                        for l in cur['legs']:
                            if l.get('mint') == t_['mint']:
                                l.update(bought={**(l.get('bought') or {}), 'tag': '🤖 agents READY · switch'}, slMode='hold', rideOrRug=True, ticket=True); l.pop('picked', None)
                                if _uni.in_lane(t_.get('vitals') or {}):
                                    l['trench'] = True
                        cur['events'] = cur['events'][:-1] + [{**cur['events'][-1], 'kind': 'agent', 'move': 'swap', 'mint': t_['mint'], 'why': f"🤖 agents swapped ${x['symbol']} for ${t_['symbol']}: {x['why']}"}]
                        if ctl_:
                            cur['agentDutyAt'] = now
                        cur = _prime.note_dropped(was_, cur, now, cfg_t['rotateHours'], px)
                except ValueError:
                    continue
        if ctl_:   # ⚙ EMPTY SEATS — ONE candidate lifecycle: every fill comes from the kernel's READY list (ranked once, by the ten-agent brain)
            used_ = _oe.real_buys(cur.get('events'), _fw_full_ledger(), tid, now, moves=('fill',))   # 🪑 empty-seat fills (real buys only: a seat that never bought is not a buy)
            cfg_s = {**cfg_t, 'coins': pol_['seats']}
            held_n = len([l for l in cur.get('legs') or [] if not l.get('placeholder')])
            empty_n = max(0, pol_['seats'] - held_n)
            sic_want_ = (_g4.get('want') or {}).get('source') == 'sicario'   # 🎩 owner 2026-11-05: all 4 seats are open to a Sicario's PoW, desk buys stay off for everything else
            g4_seat_ = pol_.get('aiSeat') == 'real' and ((not cfg_t.get('deskBuysOff') and not any(l.get('aiSeat') and not l.get('placeholder') for l in cur.get('legs') or [])) or (sic_want_ and empty_n > 0))
            if g4_seat_ and empty_n:   # 🧠 one empty seat is G4's while its seat is on: the agents fill the rest
                empty_n -= 1
            if empty_n and not cur.get('agentEmptyAt'):
                cur['agentEmptyAt'] = now
            elif not empty_n:
                cur.pop('agentEmptyAt', None); _office.pop('validSince', None)
            _DUO_GATE['on'] = cfg_t.get('agentDuoGate', True) is not False
            blk_ = _agent_blocked(cur, now) | {l.get('mint') for l in cur.get('legs') or []}
            valid_ = [c_ for c_ in (_tk.KERNEL.candidate(m_, d_) for m_, d_ in _tk.KERNEL.ready(exclude=blk_)) if c_ and not _fw.dollar_named(c_.get('symbol'))]
            valid_ = sorted([c_ for c_ in valid_ if _agent_entry_ok(c_)],   # 🎯 EVERY agent door enters like OSSY / G4 (owner, 2026-10-18: "they are on point"): the three setups, no gun line / chase / spike /
                            key=lambda c_: (0 if (_pred_of(c_.get('mint'), now) or 0) >= 5 else 1,   # 🔮 a PROVEN model calls it up ≥ 5%: first
                                            0 if _fuse._f(c_.get('size')) >= 0.75 else 1,   # 🛡 the Warden's full-size picks first — the one desk whose call separates winners (−2.6 vs −4.9 typical, 187 real trades)
                                            _seat.germ_rank(_opp.germ_d(c_.get('chart') or {})[0], _uni.germ_max()),   # SKIP, no losing read, no young coin with an unread launch — germ floor first, like the models' list
                                            -sum(_oe.SETUP_SCORE.get(k_, 0) for k_ in c_.get('setups') or ()), -_fuse._f(c_.get('rank'))))
            for c_ in valid_:
                c_.update(tier='A', opp=c_['rank'], nearReady=f"⚡ {c_['kwhy']} · rank {c_['rank']:g} · size ×{c_['size']:g}")
            cases_ = _tk.KERNEL.cases(exclude={l.get('mint') for l in cur.get('legs') or []})
            cooled_ = [c_ for c_ in cases_ if c_['cleared'] and c_['mint'] in blk_]   # READY, but it left the card lately / the keeper refused it: the rebuy block holds it
            moved_, live_ = [], {}
            try:   # 👁 the LIVE chart for every held coin + the READY coins (one batched local call) and what a live breakout is measured from
                cand_ = valid_[:max(6, pol_['seats'] + 2)] + [c_ for c_ in (_tk.KERNEL.candidate(x_['mint']) for x_ in cases_ if x_['status'] == 'CONTENDING') if c_][:6]
                held_p = {l.get('mint'): l.get('pairAddress') for l in cur.get('legs') or [] if l.get('mint') and not l.get('placeholder')}
                if cand_ or held_p:
                    await _jup_prices([t_['mint'] for t_ in cand_] + list(held_p))
                    await _office_candle_refresh({**held_p, **{t_['mint']: t_['pair'] for t_ in cand_ if t_.get('pair')}}, now)
                    _office['watchC'] = {t_['mint']: {'sym': t_.get('symbol'), 'px': _fuse._f((_jup_px_cache.get(t_['mint']) or (0, 0))[1]) or _fuse._f(t_.get('px')),
                                                      'high': max([_fuse._f(r_[2]) for r_ in ((_office['candles'].get(t_['pair']) or (0, []))[1] or [])[-10:]] or [0])}
                                         for t_ in cand_ if t_.get('mint') and t_.get('pair')}   # ⚡ what a live breakout / material move is measured from
                _office['live'] = {'at': now, 'checked': []}
            except Exception as e:
                print('live refresh:', e)
            if empty_n and valid_ and not _office.get('validSince'):
                _office['validSince'] = now
            free_ = max(0.0, _fuse._f(cur.get('cash')) - _fuse._f(cur.get('holdCashUsd')))
            tk_ = _office.get('ticks') or []
            every_ = sorted(b_ - a_ for a_, b_ in zip(tk_, tk_[1:]))[len(tk_) // 2 - 1] if len(tk_) >= 3 else 50.0
            bk_ = ((_fw_peek().get('books') or {}).get(tid) or {}) if real_t else {}
            seat_ctx_ = {'want': pol_['seats'], 'held': held_n, 'cases': [c_ for c_ in cases_ if c_ not in cooled_ and c_['status'] != 'TRACKING'], 'valid': valid_, 'movesLeft': _uni.FILL_MOVES_HR - used_, 'movesHr': _uni.FILL_MOVES_HR, 'courier': (_office.get('courier') or {}).get('health'),
                         'manual': pol_['manual'], 'live': rd_['live'], 'readyWhy': rd_['why'], 'freeUsd': free_, 'minUsd': max(0.05, _fuse._f(cfg_t.get('minOrderUsd'))), 'emptySince': cur.get('agentEmptyAt'), 'target': pol_['seatTarget'], 'now': now, 'nextTickIn': min(every_, pol_['seatTarget']),
                         'control': True, 'halt': (bk_.get('haltWhy') or 'halted') if bk_.get('halt') else None, 'cooled': [c_.get('symbol') for c_ in cooled_], 'moved': moved_, 'timerIn': 0}
            vetoed_ = 0
            # the money boundary for a fill: the creator not on manual · the office LIVE · the keeper not halted · Courier not BAD · the runaway guard
            plan_ = valid_[:empty_n + 3] if (empty_n and not pol_['manual'] and rd_['live'] and not seat_ctx_['halt'] and seat_ctx_['courier'] != 'BAD' and used_ < _uni.FILL_MOVES_HR) else []
            _fw.set_agent_limits(_regret_limits(cfg_t))   # 😴 tuned by the regret ledger where the owner left AGENTS · 🎛 the owner's price-gap / sell-back / pool-floor / curve limits for agent buys: the pre-check and the keeper read the same ones
            if plan_ is not None and pol_.get('entry') == 'armed' and empty_n and not pol_['manual'] and rd_['live'] and not seat_ctx_['halt'] and seat_ctx_['courier'] != 'BAD' and used_ < _uni.FILL_MOVES_HR:
                # 🎯 KEEP SEATS FULL (the owner's entry mode): a seat empty past the owner's target with too few READY coins takes the best ARMED
                # coins (Trigger: "building, not yet") at HALF a seat — never a WAIT / NO coin, never a hard veto, never a blocked one
                try:
                    arm_ = _oe.armed_fill([c_ for c_ in (_tk.KERNEL.candidate(x_['mint']) for x_ in cases_ if x_['status'] == 'CONTENDING') if c_ and not _fw.dollar_named(c_.get('symbol')) and _agent_entry_ok(c_)],
                                          cur.get('agentEmptyAt'), pol_['seatTarget'], now, len(valid_), empty_n, blk_)
                    for c_ in arm_:
                        c_.update(tier='C', opp=c_['rank'], armed=True, nearReady=f"🎯 ARMED · {c_['kwhy']} · rank {c_['rank']:g} — your seat target passed, half a seat")
                    plan_ = plan_ + arm_
                    _office['armed'] = {'at': now, 'n': len(arm_), 'syms': [c_.get('symbol') for c_ in arm_]}
                except Exception as e:
                    print('armed fill:', str(e)[:120])
            if not plan_ and empty_n and not pol_['manual'] and rd_['live'] and not seat_ctx_['halt'] and seat_ctx_['courier'] != 'BAD' and used_ < _uni.FILL_MOVES_HR and cfg_t.get('agentValve', True):
                # 🪫 THE PATIENCE VALVE: an empty seat never sits all morning — after 10 min with nothing READY or armed, ONE chart-held coin
                # (wait for confirmation / breakout only) at the smallest seat, once per 15 min; it closes itself when its own record loses
                try:
                    vrec_ = _oe.valve_record(_real_trades())
                    v_ = _oe.valve_fill([c_ for c_ in (_tk.KERNEL.candidate(x_['mint']) for x_ in cases_ if x_['status'] == 'CONTENDING') if c_ and not _fw.dollar_named(c_.get('symbol')) and _agent_entry_ok(c_)],
                                        cur.get('agentEmptyAt'), now, cur.get('agentValveAt'), blk_, vrec_)
                    for c_ in v_:
                        c_.update(tier='C', opp=c_['rank'], armed=True, valve=True, size=min(_fuse._f(c_.get('size')) or 1, _oe.VALVE_SIZE),
                                  nearReady=f"🪫 VALVE · seat empty {int((now - _fuse._f(cur.get('agentEmptyAt'))) // 60)} min · the chart said {c_.get('chartCall', '').lower()} · smallest seat")
                    if v_:
                        cur['agentValveAt'] = now
                    plan_ = plan_ + v_
                    _office['valve'] = {'at': now, 'n': len(v_), 'syms': [c_.get('symbol') for c_ in v_], 'record': vrec_}
                except Exception as e:
                    print('valve fill:', str(e)[:120])
            cw_ = _ccl.wait_why(now, {'candleClock': cfg_t.get('candleClock', True) is not False and _rg.effective(cfg_t, _regret_book()).get('candleClock', True) is not False})
            if plan_ and cw_:   # ⏱ THE CANDLE CLOCK: no new buy in the first 100s of a 5-minute candle (record: worse in both halves, rugs left out)
                _office['flowWait'] = {'at': now, 'rows': [{'symbol': t_.get('symbol'), 'why': cw_} for t_ in plan_[:6]]}
                for t_ in plan_[:3]:
                    _regret_note(t_['mint'], 'clock:EARLY', _fuse._f(t_.get('px')), t_.get('symbol'))
                plan_ = []
            if plan_:   # 🌊 THE TAPE DECIDES THE MOMENT: each coin about to take a seat is read on its last 90s of real swaps — never into sellers, never at the top of a spike; a crowd buying goes first
                try:
                    fl_ = await _flow_fetch([t_.get('pair') for t_ in plan_ if t_.get('pair')])
                    keep_, waits_ = [], []
                    for t_ in plan_:
                        v_ = _flow.vital(fl_.get(t_.get('pair')))
                        if v_:
                            _flow_mark(t_['mint'], v_, t_.get('symbol'), now)
                        why_ = _flow.vital_block(v_)
                        wt_ = _rg.effective(cfg_t, _regret_book())
                        if why_ and not wt_.get({'PEAK': 'peakWait', 'SELLERS': 'sellersWait'}.get((v_ or {}).get('state'), ''), True):
                            why_ = None   # 😴 this tape wait was switched off by the regret ledger: the coins it held back kept beating the ones taken
                        if why_:
                            _regret_note(t_['mint'], f"flow:{v_.get('state')}", _fuse._f(t_.get('px')), t_.get('symbol'))
                            waits_.append({'symbol': t_.get('symbol'), 'why': why_})
                            _tk.KERNEL.note('trigger', 'WAIT', f"the tape says wait — {why_}", now, mint=t_['mint'], key=f"flow:{int(now // 120)}")
                            continue
                        wm_ = None
                        tr_w = _flow_trades.get(t_.get('pair'))
                        if tr_w and now - tr_w[0] < 30:   # 🐋 what the snipers / bundles / dev / top holders / whales / top traders did in the last 5 min
                            wm_ = _cw.moves_since(_cw.tag_trades(tr_w[1], (_intel_cache.get(t_['mint']) or (0, None))[1] or {}), now - 300)
                        if wm_ and not t_.get('g4') and _fuse._f(wm_['badSell']) >= _of.REAP_BAD_USD and _fuse._f(wm_['badSell']) > 2 * _fuse._f(wm_['badBuy']):
                            why_w = f"early hands are dumping it right now — {wm_['words']}: watch, then move"
                            _regret_note(t_['mint'], 'wallets:DUMP', _fuse._f(t_.get('px')), t_.get('symbol'))   # 😴 graded like every wait: the regret ledger says if it was right
                            waits_.append({'symbol': t_.get('symbol'), 'why': why_w})
                            _tk.KERNEL.note('trigger', 'WAIT', why_w, now, mint=t_['mint'], key=f"wal:{int(now // 120)}")
                            continue
                        smart_ = bool(wm_ and _fuse._f(wm_['smartBuy']) >= _of.REAP_SMART_USD and _fuse._f(wm_['smartBuy']) > _fuse._f(wm_['smartSell']))
                        sus_ = any(((n_ or {}).get('advice') or {}).get('stance') == 'CAUTION' for n_ in (_ai['notes'].get(t_['mint']) or {}).values())   # 🧠 SECOND LOOK: the rug-sniffer already flagged this coin → it goes behind the ones it did not (no call made here, never a block)
                        keep_.append(((0 if v_ and v_.get('state') == 'BUYERS' and v_.get('hot') else 1 if v_ and v_.get('state') == 'BUYERS' else 2) + (3 if sus_ else 0) - (1 if smart_ else 0), t_))   # 🐋 smart money buying it goes first
                    plan_ = [t_ for _g, t_ in sorted(keep_, key=lambda kv: kv[0])]
                    _office['flowWait'] = {'at': now, 'rows': waits_[:6]}
                except Exception as e:
                    print('flow gate:', str(e)[:120])
            _office['open'] = {'at': now, 'read': len(_tk.KERNEL.store.mints), 'ranked': len(valid_), 'top': [{'symbol': c_['symbol'], 'score': c_['rank'], 'narrative': c_['narrative']} for c_ in valid_[:8]],
                               'skipped': _tk.KERNEL.metrics(now)['byStatus']}
            _office['opp'] = {'at': now, 'cap': _agents.get('laneCap'), 'top': [{'symbol': c_['symbol'], 'tier': c_['status'], 'score': c_['rank']} for c_ in cases_[:6]]}
            if plan_ and real_t and empty_n > 0 and not cfg_t.get('agentPaper'):   # 🛂 the model's read BEFORE the seat (cloud only, ≤ 7s; it can only hold a coin back)
                try:
                    plan_, aiw_ = await _ai_gate(plan_, empty_n, cfg_t, now)
                    if aiw_:
                        _office['flowWait'] = {'at': now, 'rows': (list((_office.get('flowWait') or {}).get('rows') or []) + aiw_)[:6]}
                except Exception as e:
                    print('ai gate:', str(e)[:120])
            if cfg_t.get('agentPaper'):   # 📄 PAPER: every seat the kernel would fill is recorded in the shadow book at the live price — no real buy
                for t_ in plan_[:max(0, empty_n)]:
                    _shadow_note(t_, 'fill', now, cur)
                _shadow_controls(plan_[:max(0, empty_n)], [c_['row'] for c_ in cases_ if c_['status'] == 'CONTENDING'][:12], cases_, now)
                plan_ = []
            night_g4_ = night_ and ((_night.get('st') or {}).get('kind') == 'rug')   # 🔁 the AI seat is ONE trade at a time: only a rug-level trip pauses it (owner: "REAL seat"); drawdown / streak pauses stop the agents' fills only
            try:   # 🤝 the agents STRONGLY consider OSSY / G4 (owner, 2026-10-17): a coin a model called BUY in the last 10 min goes first into an open agent seat (every check still runs); a coin a model just said SELL / warned on is skipped
                dl_ = (_g4_mem.get() or {}).get('log') or []
                dpk_ = [r_.get('mint') for r_ in reversed(dl_) if r_.get('action') == 'BUY' and r_.get('mint') and now - _fuse._f(r_.get('at')) < 600]
                dwn_ = {r_.get('mint') for r_ in dl_ if r_.get('mint') and now - _fuse._f(r_.get('at')) < 900 and (r_.get('action') == 'SELL' or r_.get('view') == 'SELL')}
                if plan_:
                    plan_ = sorted([t_ for t_ in plan_ if t_['mint'] not in dwn_], key=lambda t_: dpk_.index(t_['mint']) if t_['mint'] in dpk_ else 99)
                    for t_ in plan_:
                        if t_['mint'] in dpk_ and '🤝' not in str(t_.get('nearReady') or ''):
                            t_['nearReady'] = '🤝 the models picked it · ' + str(t_.get('nearReady') or '')
                        elif t_.get('duoWhy') and '🤝' not in str(t_.get('nearReady') or ''):
                            t_['nearReady'] = f"🤝 {t_['duoWhy']} · " + str(t_.get('nearReady') or '')
            except Exception as e:
                print('duo consider:', str(e)[:80])
            w_, g4n_ = _g4.get('want'), 0   # 🔁 the AI seat is REAL even while the agents' own fills are on paper (owner, 2026-10-16); the night guard still stops it
            if w_ and w_.get('action') == 'BUY':   # 🧾 say WHY a model's BUY did not reach the card (it used to vanish silently)
                why_no = ('stale (older than 2 min)' if not _seat.fresh(w_, now) else 'seat off / not real' if not g4_seat_ else '🌙 night guard: a rug-level trip pauses the AI seat too' if night_g4_
                          else 'manual authority' if pol_['manual'] else 'office not LIVE yet' if not rd_['live'] else 'keeper halted' if seat_ctx_['halt']
                          else 'courier BAD' if seat_ctx_['courier'] == 'BAD' else 'hourly fill guard' if used_ >= _uni.FILL_MOVES_HR
                          else 'refused: ' + str((_agent_refused.get(w_.get('mint')) or (0, 'your own rule / a lesson / the keeper bench'))[1])[:100] if w_.get('mint') in _g4_blocked(cur, now) else None)
                if why_no:
                    _g4_fate(w_, why_no, now)
            if (g4_seat_ and w_ and w_.get('action') == 'BUY' and _seat.fresh(w_, now) and not night_g4_ and not pol_['manual'] and rd_['live'] and not seat_ctx_['halt']
                    and seat_ctx_['courier'] != 'BAD' and used_ < _uni.FILL_MOVES_HR and w_.get('mint') not in _g4_blocked(cur, now)):
                _g4['want'], _g4['pendSeat'] = None, {**w_}   # (kept until the save: an owner edit mid-tick drops this tick → the BUY is retried, never lost)
                lg_ = _seat.adoptable(cur.get('legs'), w_['mint'])
                if lg_ is not None:   # 🤝 the agents bought this very coin while the model thought ($onboard, 2026-10-17): the model ADOPTS that seat — no second buy, it is the model's trade now
                    lg_.update(aiSeat=True, aiBy=w_.get('by'), bought={**(lg_.get('bought') or {}), 'tag': '🤖 🧠 G4 seat'}, **{k_: v_ for k_, v_ in (('aiTp', w_.get('tp')), ('aiSl', w_.get('sl'))) if v_})
                    cur.setdefault('events', []).append({'at': now, 'kind': 'agent', 'symbol': lg_.get('symbol'), 'why': f"🤝 {w_.get('model') or 'the model'} took over the agents' seat on ${lg_.get('symbol')} — its trade now, no second buy"})
                    m0_ = _g4_mem.get() or {}
                    _g4_mem.put({**m0_, 'opener': w_.get('by'), 'opened': {**{k_: v_ for k_, v_ in (m0_.get('opened') or {}).items() if now - _fuse._f(v_) < 3600}, w_['mint']: now}}, now)
                    _g4['pendSeat'] = {**w_, 'seated': True}
                    _g4_fate(w_, 'adopted the agents\' seat on this coin — the model runs it now', now)
                    w_ = None
                gt_ = _tk.KERNEL.candidate(w_['mint']) if w_ else None
                bad_ = _g4_bad_entry(gt_) if gt_ else None
                if bad_:   # 🔫 the coin ran to its gun line while the model thought: no buy, it picks again next minute
                    _g4_fate(w_, 'not bought — ' + str(bad_)[:90], now)
                    gt_ = None
                elif gt_ and _g4_picks_only() and not gt_.get('pick'):   # 🧪 picks only — the HARD stop: a coin that is not a proven pick right now is never bought by the seat
                    _g4_fate(w_, '🧪 picks only: not a proven-rule pick right now — no buy', now)
                    gt_ = None
                if gt_ and gt_.get('pair'):
                    plan_, g4n_ = [{**gt_, 'g4': True, 'g4By': w_.get('by'), 'g4Tp': w_.get('tp'), 'g4Sl': w_.get('sl'), 'nearReady': f"🧠 {w_.get('model') or 'G4'}: {w_.get('why')}"}] + [t_ for t_ in plan_ if t_['mint'] != gt_['mint']], 1
                    _g4_fate(w_, 'sent to the seat check', now)
                elif not bad_ and w_:
                    _g4_fate(w_, 'coin left the desk before the buy', now)
            if cfg_t.get('deskBuysOff'):   # ⚖ the last door: nothing on the plan reaches the card but the coin a Sicario's PoW asked for
                plan_ = _seat.desk_off_plan(plan_, sic_want_); g4n_ = len(plan_)
            pre_ = await _seat_precheck(plan_[:empty_n + 3 + g4n_], cfg_t, now, seat_usd=_prime.agent_seat_usd(cur, px, cfg_s), need=empty_n + g4n_) if (plan_ and real_t) else None   # 🛂 the keeper's market gate BEFORE the seat
            _office['pre'] = {'at': now, 'asked': len(plan_), 'passed': len(pre_) if pre_ is not None else None,
                              'refused': [{'symbol': t_.get('symbol'), 'why': _agent_refused[t_['mint']][1]} for t_ in plan_ if pre_ is not None and t_['mint'] in _agent_refused][:6]}
            ag_fill_ = 0
            for t_ in plan_:   # 🔌 no fill until the office is LIVE after a restart · never while the keeper is halted or the Courier reads BAD
                t_ = {**t_, 'trench': _uni.in_lane(t_.get('vitals') or {})}   # 🗑 a lane launch → the keeper's trench pool floor
                if used_ >= _uni.FILL_MOVES_HR:
                    break
                if g4_seat_ and not t_.get('g4') and ag_fill_ >= empty_n:   # 🧠 one empty seat stays G4's while its seat is on
                    break
                if t_['mint'] in (_g4_blocked(cur, now) if t_.get('g4') else _agent_blocked(cur, now)):   # 🚫 banked / pulled / refused earlier in THIS tick (OSSY / G4: only the keeper's and your own blocks)
                    if t_.get('g4'):   # 🧾 never silent: the board said "sent to the seat check" for good while the refusal sat here
                        _g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'keeper refused: ' + str((_agent_refused.get(t_['mint']) or (0, 'blocked by your rule / keeper bench'))[1])[:90] + ' — the model picks again next minute', now)
                    continue
                if pre_ is not None:
                    if t_['mint'] not in pre_:   # 🛂 the keeper would refuse it: no seat, the next READY coin is tried
                        if t_.get('g4'):
                            _g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'keeper pre-check refused: ' + str((_agent_refused.get(t_['mint']) or (0, 'busy route'))[1])[:80], now)
                        continue
                    lv_ = pre_[t_['mint']]
                    if not t_.get('g4') and _fuse._f(lv_.get('px')) > 0 and _fuse._f(t_.get('px')) > 0 and _fuse._f(lv_['px']) >= _fuse._f(t_['px']) * (1 + SPIKED_SINCE_READ / 100):
                        _agent_refused[t_['mint']] = (now + 120, f"jumped {(_fuse._f(lv_['px']) / _fuse._f(t_['px']) - 1) * 100:.0f}% since the agents read it — waits for the pullback", now)
                        continue   # 🚀 it spiked between the read and the buy: no chasing the candle that just printed
                    t_ = {**t_, 'px': lv_.get('px') or t_['px'], 'nums': {**(t_.get('nums') or {}), 'liq': lv_.get('liq') or (t_.get('nums') or {}).get('liq')}}
                try:
                    wd_ = _office_warden(cur, t_, _prime.agent_seat_usd(cur, px, cfg_s), cfg_t, now, 'fill')   # 🛡 sizes THIS seat: it can lower or veto, never raise
                    if t_.get('g4') and wd_['veto']:   # 🧼 owner 2026-10-28 ("G4 buys washed coins, not listening"): the models obey every Warden VETO
                        _g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'Warden VETO (models obey vetoes): ' + str(wd_.get('decided') or '')[:60], now)
                        vetoed_ += 1
                        continue
                    if t_.get('g4'):   # 🔁 OSSY / G4's turn is THEIR call (owner, 2026-10-16: "the agents can't stop them, they use the agents as helpers"): the Warden's word is advice, the seat is the card's full seat; the keeper's own money checks still run
                        if wd_['veto'] or wd_['allowed'] < _prime.agent_seat_usd(cur, px, cfg_s):
                            _g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'Warden advised: ' + str(wd_.get('why') or wd_.get('rules') or 'smaller')[:70] + ' — the model\'s call stands', now)
                        wd_ = {**wd_, 'veto': False, 'allowed': _prime.agent_seat_usd(cur, px, cfg_s)}
                    if wd_['veto']:
                        vetoed_ += 1
                        if t_.get('g4'):
                            _g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'Warden vetoed: ' + str(wd_.get('why') or wd_.get('rules') or '')[:80], now)
                        continue
                    cur = _prime.agent_seat(cur, {'mint': t_['mint'], 'symbol': t_['symbol'], 'pairAddress': t_['pair'], 'price': t_['px'], 'liquidityUsd': (t_.get('nums') or {}).get('liq'), 'trench': t_['trench'], 'curve': bool((t_.get('vitals') or {}).get('curve') and cfg_t.get('agentCurve')),
                                                  'ageH': (t_.get('vitals') or {}).get('ageH'), 'vol1h': (t_.get('vitals') or {}).get('vol1h'), 'buyShare': (t_.get('nums') or {}).get('buy'),
                                                  'riskScale': wd_.get('riskScale'),
                                                  'tag': '🤖 agents · ⚡ READY (kernel)' if not t_.get('armed') else '🤖 agents · 🪫 VALVE (empty seat)' if t_.get('valve') else '🤖 agents · 🎯 ARMED (seat target)', 'why': t_['nearReady']}, px, cfg_s, now,
                                          max_usd=wd_['allowed'] * (_oe.VALVE_SIZE if t_.get('valve') else _cap.armed_size(_capital_view()) if t_.get('armed') else 1.0))   # 🎯 an armed fill: half — the full size once the ARMED door's own real record proves it
                    used_ += 1; cur['agentDutyAt'] = now; cur['agentFillAt'] = now
                    if not t_.get('g4') and _DUO_GATE['on']:   # 🤝 the agents trade a model-backed coin on THAT model's own lines (R6m / R5m / R7a)
                        bl_ = _seat.backer_lines((_g4_mem.get() or {}).get('log') or [], t_['mint'], now)
                        for l_ in (cur.get('legs') or []) if bl_ else []:
                            if l_.get('mint') == t_['mint'] and not l_.get('aiSeat') and not l_.get('picked'):
                                l_.update({k2_: v2_ for k2_, v2_ in (('aiTp', bl_.get('tp')), ('aiSl', bl_.get('sl')), ('aiTrail', bl_.get('trail'))) if v2_}); l_['linesBy'] = bl_.get('by')
                    if t_.get('g4'):   # 🧠 the leg is G4's: the agents only argue on it from now on
                        _g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'seated — the keeper buys it next pass', now)
                        if (_g4.get('pendSeat') or {}).get('mint') == t_['mint']:
                            _g4['pendSeat']['seated'] = True
                        for l in cur['legs']:
                            if l.get('mint') == t_['mint']:
                                l['aiSeat'] = True
                                l['aiBy'] = t_.get('g4By')   # 🔁 whose trade this is: the turn moves only on a seat that really opened
                                for k_, v_ in (('aiTp', t_.get('g4Tp')), ('aiSl', t_.get('g4Sl'))):
                                    if v_:
                                        l[k_] = v_
                                l['bought'] = {**(l.get('bought') or {}), 'tag': '🤖 🧠 G4 seat'}
                        try:
                            m0_ = _g4_mem.get() or {}
                            m0_ = {**m0_, 'opened': {**{k_: v_ for k_, v_ in (m0_.get('opened') or {}).items() if now - _fuse._f(v_) < 3600}, t_['mint']: now}}   # 🚫 neither model buys this coin again for 1h
                            if not m0_.get('statsFrom'):   # 🔁 the first time a model's BUY really takes the seat, the duel board's stats restart from real play (owner, 2026-10-16)
                                m0_ = {**m0_, 'log': [], 'statsFrom': now}
                            _g4_mem.put({**m0_, 'opener': t_.get('g4By')}, now)
                        except Exception as e:
                            print('g4 opener:', str(e)[:80])
                        g4_seat_ = False
                    else:
                        ag_fill_ += 1
                    _ai.setdefault('fillQ', {})[t_['mint']] = now
                    _regret_note(t_['mint'], 'taken', _fuse._f(t_.get('px')), t_.get('symbol'))   # 😴 the baseline every blocked coin is graded against   # 📍 the model reads this coin once more AT the fill (record only — it never undoes a buy)
                    try:   # 📏 decision → order · discovery → entry · the coin's age at entry
                        K_ = _tk.KERNEL
                        K_.timings.note('readyToSeatSec', now - _fuse._f((K_.store.cand.get(t_['mint']) or {}).get('since') or now))
                        K_.timings.note('discoveryToEntrySec', now - _fuse._f(K_.store.stats['firstSeen'].get(t_['mint']) or now))
                        K_.timings.note('ageAtEntryMin', None if (t_.get('vitals') or {}).get('ageH') is None else _fuse._f(t_['vitals']['ageH']) * 60)
                        K_.store.set_status(t_['mint'], 'ORDER_PENDING', now, 'seat created — the keeper buys it')
                    except Exception as e:
                        print('timings:', e)
                    _intake['reg'] = _in.stamp(_intake_reg(), 'seat', [t_['mint']], now)   # 🕸 clear → seat latency
                    st_o = _office_state()   # ⏱ how long the seat sat empty, how long a valid candidate waited, how long after an exit the next fill came
                    sp_ = st_o.get('speed') or {}
                    if cur.get('agentEmptyAt'):
                        sp_ = _oe.speed_note(sp_, 'seatEmpty', now - _fuse._f(cur['agentEmptyAt']))
                    if _office.get('validSince'):
                        sp_ = _oe.speed_note(sp_, 'validToFill', now - _fuse._f(_office['validSince']))
                    if cur.get('agentExitAt'):
                        sp_ = _oe.speed_note(sp_, 'exitToFill', now - _fuse._f(cur['agentExitAt']))
                    st_o['speed'] = sp_
                    cur.pop('agentExitAt', None); cur.pop('agentEmptyAt', None); _office.pop('validSince', None)
                except ValueError as e_:
                    if t_.get('g4'):   # 🧾 the model's BUY used to vanish here (no free cash / no seat) — say why, and make room when cash is the reason
                        why_ = str(e_)
                        if 'free' in why_:
                            try:
                                cur, got_, ts_ = _prime.make_room(cur, _prime.agent_seat_usd(cur, px, cfg_s), px, None, now, pol_['seats'], t_.get('g4By') and str(t_.get('g4By')).upper() or 'the model')
                            except Exception as e2_:
                                got_, ts_ = 0.0, None
                                print('g4 make room:', str(e2_)[:80])
                            if got_ > 0:
                                why_ += f' — trimmed ${got_:.2f} of ${ts_} to pay it; the seat fills next tick'
                                if _g4.get('pendSeat'):
                                    _g4['want'] = {**_g4['pendSeat'], 'at': now}
                        _g4_fate({'mint': t_['mint'], 'symbol': t_.get('symbol')}, 'not seated — ' + why_[:140], now)
                        continue
                    break
            held_n = len([l for l in cur.get('legs') or [] if not l.get('placeholder')])   # 🪑 the seat truth AFTER this tick's fills
            _agents['seat'] = {**_oe.seat_state({**seat_ctx_, 'held': held_n, 'vetoed': vetoed_, 'valid': [t_ for t_ in valid_ if t_['mint'] not in {l.get('mint') for l in cur.get('legs') or []}] if held_n < pol_['seats'] else valid_}),
                               'at': now, 'tickEvery': round(every_, 1), 'movesLeft': max(0, _uni.FILL_MOVES_HR - used_), 'freeUsd': round(max(0.0, _fuse._f(cur.get('cash')) - _fuse._f(cur.get('holdCashUsd'))), 2),
                               'refused': _seat_refusals(tid, now) if real_t else []}
            _agents['card'] = _pos.card_seats(cur, _agents.get('decisions'), px, cfg_t, take=_of.take_line(cfg_t, _agents.get('scalp')))
            try:   # 🪑 THE BENCH + EVERY SEAT THIS CYCLE (display — the decisions above were made by manage / Reaper / fill_plan)
                on2_ = {l.get('mint') for l in cur.get('legs') or [] if l.get('mint')}
                bench_ = _so.bench(cases_, scores_, on2_, {m_: (v_['ok'], v_['why']) for m_, v_ in live_.items()}, [c_['mint'] for c_ in cooled_])
                inp_ = {l.get('mint'): _mkt_view(l.get('mint'), l.get('pairAddress'), now).get('pxAt') for l in cur.get('legs') or [] if l.get('mint')}
                _agents['bench'] = bench_
                _agents['seatBoard'] = _so.seat_board((_agents['card'] or {}).get('seats'), _office.get('reports'), _agents.get('decisions'), vels_, scores_, bench_,
                                                      _agents.get('switchTests'), now, now, inp_, _agents.get('seat'), pol_['switch'].get('mode'))
                _agents['seatSummary'] = {**_so.summary(held_n, pol_['seats'], bench_, used_, _uni.FILL_MOVES_HR, max(0.0, _fuse._f(cur.get('cash')) - _fuse._f(cur.get('holdCashUsd')))),
                                          'hunt': list(_so.universe(_agents.get('money')))}   # 🧭 what the seats hunt in this phase
                _agents['seatScores'] = {m_: v_ for m_, v_ in scores_.items() if m_ in on2_ or m_ in {b_['mint'] for b_ in bench_}}
                bs_ = _so.bench_stats(bench_, (_agents.get('benchStats') or {}).get('mints'))
                _agents['benchStats'] = bs_
                st_u = _office_state(); st_u['util'] = _so.util_note(st_u.get('util'), _agents['seatBoard'], now)   # ⏱ seat time: occupied · empty (waiting · safety · budget · cash)
                _agents['util'] = _so.util_view(st_u['util'])
            except Exception as e:
                print('seat board:', e)
            _office['tickAt'] = now
        elif real_t and cur and pol_:   # 🪑 Agent Control OFF (or a hold the owner set): the seats still say why the agents fill nothing
            _agents['seat'] = {**_oe.seat_state({'want': pol_['seats'], 'held': len([l for l in cur.get('legs') or [] if not (l.get('placeholder') and not l.get('manualCash'))]), 'now': now, 'control': False,
                                                 'offWhy': None if not cfg_t.get('agentControl') else ('the card is floored — it re-deals before the agents act' if cur.get('flooredAt') else 'your own ✋ hold stands — nobody trades until you release it')}),
                               'at': now, 'movesLeft': 0, 'freeUsd': round(max(0.0, _fuse._f(cur.get('cash')) - _fuse._f(cur.get('holdCashUsd'))), 2)}
        if real_t and cur:
            _office_light(tid, cur, now)   # 🏢 the office's live bits (positions · last real action · duty clock) — memory only
        # 🔥 TOP-3 AUTO SEAT (owner, 2026-10-09: "those coins automatically get swapped into a seat and buy-vs-sell gets it gone"): the
        # card's TOP 1/3 coin takes the weakest seat that is not winning, one per 10 min — still the real-buy pool floor, no dollar names,
        # not falling right now; the flow exit sells it when sellers take over.
        if real_t and cur and cfg_t.get('topSeat') and not cur.get('holdAll') and not cur.get('flooredAt') and now - _fuse._f(cur.get('topSeatAt')) >= _prime.TOP_SEAT_SEC:
            tops_ = _prime.top_three((_contenders_cache.get('data') or {}).get('divisions'), mine, cool)
            fwc_ = _fw.clean_cfg(fw_cfg)
            cand_ = next((x for x in tops_ if _lq(x) >= fwc_['minLiqUsd'] and not _fw.dollar_named(x.get('symbol')) and _fuse._f(x.get('price')) > 0
                          and _prime.entry_ok(x, mom) and not (cfg_t.get('entryGate') and _prime.entry_gate(x, mom))), None)
            vic_ = _prime.top_victim(cur, px, now, max(120.0, _fuse._f(cfg_t.get('minHoldMins')) * 60)) if cand_ else None
            if cand_ and vic_:
                try:
                    was_ = cur
                    nw_ = _prime.replace_leg(cur, vic_['pairAddress'], px, p_t, [{**cand_, 'tag': '🔥 top 3'}], anchors, cfg_t, now)
                    nw_['events'] = nw_['events'][:-1] + [{**nw_['events'][-1], 'why': f"🔥 TOP 3 auto-seat: ${cand_.get('symbol')} (${_fuse._f(cand_.get('vol1h')) / 1000:,.0f}K/h, {_fuse._f(cand_.get('chg1h')):+.0f}% 1h) took ${vic_.get('symbol')}'s seat"}]
                    nw_['topSeatAt'] = now
                    cur = _prime.note_dropped(was_, nw_, now, cfg_t['rotateHours'], px)
                except ValueError:
                    pass
        true_usd = None
        if real_t:   # 💵 floor / rescue / fix / runs judge the TRUE book (confirmed coins + card SOL), never the engine's estimate
            bk = (_fw_peek().get('books') or {}).get(tid)
            try:
                sol_px_t = await _sol_usd_live() if bk else 0.0
            except Exception:
                sol_px_t = 0.0
            if bk and sol_px_t > 0 and not bk.get('pending'):
                true_usd = _fw.book_value(bk, px, sol_px_t) or None
        if not real_t:   # 🦠 paper cards buy at the germ: coins inside the germ line first, past 2× it only when nothing else is left
            gd_ = lambda m_: (lambda g_: _fuse._f(g_['dist']) if g_ and g_.get('dist') is not None else None)((((_office.get('charts') or {}).get(m_) or {}).get('f') or {}).get('germ'))
            r_t = _prime.germ_order(r_t, gd_, _uni.germ_max())
        if not real_t:   # 🧪 UNIQUE COINS: a paper card never holds a coin another card holds (anchors too, while another major is free)
            taken_ = {l.get('mint') for t2, c2 in cards.items() if t2 != tid for l in (c2 or {}).get('legs') or [] if l.get('symbol') != 'SOL'}
            p_t, r_t = _prime.unique_rows(p_t, taken_), _prime.unique_rows(r_t, taken_)
            a_t = _prime.unique_rows(a_t, taken_) or a_t
            dup_ = _prime.shared_leg(cur, taken_) if cur and not cur.get('flooredAt') else None
            if dup_:   # a coin it already shares is swapped for one of its own (one a tick, on paper)
                try:
                    was_u = cur
                    new_u = _prime.replace_leg(cur, dup_, px, p_t, r_t, a_t, cfg_t, now)
                    old_m = {l.get('mint') for l in was_u.get('legs') or []}
                    for l_ in new_u['legs']:
                        if l_.get('mint') not in old_m:
                            l_.pop('picked', None)   # the engine's swap, not a hand pick
                    new_u['events'][-1]['why'] = '🧪 unique coins — another card already holds it, this card takes one of its own'
                    new_u.pop('ownerOut', None) if not was_u.get('ownerOut') else None
                    cur = _prime.note_dropped(was_u, new_u, now, cfg_t['rotateHours'], px)
                except Exception:
                    cur = was_u
        for l_ in (cur or {}).get('legs') or []:   # 🧲 / 📣 what Pump's own feeds say about each coin the card holds (fed lock · second ticket)
            l_['fedN'] = int(((_feeders['board'].get('runners') or {}).get(l_.get('mint')) or {}).get('n') or 0)
            l_['calledN'] = int((_pump_calls['map'].get(l_.get('mint')) or {}).get('callers') or 0)
        if real_t and cfg_t.get('trenchSlAuto', True) and _fuse._f(cfg_t.get('trenchSlPct')) < 100:   # 🧠 tickets use the stop that paid best when the brain replayed every stop on the same paths
            bs_ = ((_brain_state()['sum'] or {}).get('stops') or {}).get('best')
            if bs_ is not None:
                cfg_t = {**cfg_t, 'ticketSl': bs_}
        cards[tid] = _prime.tick(cur, px, p_t, r_t, cfg_t, now, a_t, mom, liqs, true_usd=true_usd, blind=bool(real_t and true_usd is None)) if cur else _prime.deal(tid, p_t, r_t, cfg_t, now, [] if new_only_ else anchors)
        if cards[tid] is not None:
            cards[tid]['rebuyDip'] = int(cfg_t.get('rebuyDipPct') or 0)
        if not real_t and cards[tid] is not None:   # 🎯 no one strat fits every coin: each paper coin gets its OWN take / stop from its chart, once (no agent, no AI)
            t_l = _prime.card_template(cards[tid].get('tpl'), cfg_t)
            for l_ in cards[tid].get('legs') or []:
                if l_.get('autoLv') or l_.get('placeholder') or _fuse._f(l_.get('tp')) > 0 or _fuse._f(l_.get('sl')) > 0 or _prime.safe_anchor(l_):
                    continue
                ch_ = (_office.get('charts') or {}).get(l_.get('mint')) or {}
                ln_ = _prime.coin_lines(l_, t_l, ch_.get('f'), ch_.get('state'), {'liq': l_.get('liq'), 'ageH': l_.get('ageH')})
                if ln_:
                    l_.update(ln_, autoLv=round(now))
        cards[tid] = _prime.note_dropped(cur, cards[tid], now, cfg_t['rotateHours'], px)
        if real_t and cur and cards[tid]:   # 🧠 every coin that left the real card this tick is a lesson
            try:
                _learn_drops(cur, cards[tid], lambda l: _fuse._f(px.get(l.get('pairAddress'))), now)
            except Exception as e:
                print('real learn:', e)
        if real_t and cur and cards[tid] and cfg_t.get('comeback', True):   # 🔁 a rider that left this tick is watched for its comeback
            cards[tid]['comeback'] = _prime.comeback_note(cur.get('comeback'), cur, cards[tid], px, now)
        if real_t and cards[tid]:
            on_ = {l.get('mint') for l in cards[tid].get('legs') or []}
            free_ = [x for x in r_t if x.get('mint') not in on_ and not x.get('trenchOnly')]
            scout_ = [x for x in _prime.movers(r_pre_, {}) if x.get('mint') not in on_]
            row_ = lambda x: {'mint': x.get('mint'), 'pairAddress': x.get('pairAddress'), 'symbol': x.get('symbol'), 'chg1h': _fuse._f(x.get('chg1h')), 'vol1h': _fuse._f(x.get('vol1h')), 'tag': x.get('tag') or '',
                              'ageH': x.get('ageH'), 'liq': _lq(x), 'pad': x.get('pad'), 'mcap': x.get('mcap'), 'buyShare': x.get('buyShare'), 'top10': x.get('top10'), 'dev': x.get('dev'),
                              'insiders': x.get('insiders'), 'site': x.get('site'), 'x': x.get('x'), 'tg': x.get('tg'), 'chg5m': x.get('chg5m'),
                              'vol5m': x.get('vol5m'), 'txns1h': x.get('txns1h'), 'trench': x.get('trench'), 'trenchOnly': x.get('trenchOnly')}
            seen_u, up_ = set(), []
            for x in cfg_t.get('edgeReady') or []:   # 🧬 the best of the swap-in lists that this card would buy right now
                if x.get('mint') not in on_ and x['mint'] not in seen_u and len(up_) < 6:
                    seen_u.add(x['mint']); up_.append({**row_(x), 'cat': 'edge', 'tag': x.get('tag') or '', 'edge': x.get('edge')})
            global _up_last
            _up_last = [(x['mint'], _fuse._f((x.get('price') or 0))) for x in (cfg_t.get('edgeReady') or [])[:4]]
            for x in cfg_t.get('edgeWatch') or []:   # 👀 then the best-evidence coins one check away, with that check
                if x.get('mint') and x['mint'] not in on_ and x['mint'] not in seen_u and len(up_) < 4:
                    seen_u.add(x['mint']); up_.append({**row_(x), 'tag': x.get('tag') or '', 'edge': x.get('edge'), 'wait': x.get('watchWhy')})
            doors_ = {x.get('cat'): x for x in (cfg_t.get('catPicks') or []) if x.get('cat') != 'edge'}
            for x in cfg_t.get('catWatch') or []:
                doors_.setdefault(x.get('cat'), x)
            for k_ in [c[0] for c in _prime.CATEGORIES]:   # ⏭ ONE coin per door in the owner's order (trench · pump · volume): ready, else watching with its reason
                x = doors_.get(k_)
                if x and x.get('mint') not in on_ and x['mint'] not in seen_u:
                    seen_u.add(x['mint']); up_.append({**row_(x), 'cat': x.get('cat'), 'catRank': x.get('catRank'), 'tag': x.get('tag') or '', **({'wait': x['watchWhy']} if x.get('watchWhy') else {})})
            for x in _prime.flow_rank(free_ + [y for y in scout_ if y.get('mint') not in {z.get('mint') for z in free_}]):   # ⏭ COMING UP: by what each coin looks like now (setup · chart), then hourly move
                if x.get('mint') and x['mint'] not in seen_u:
                    seen_u.add(x['mint']); up_.append(row_(x))
            # 👀 watching, DIPS FIRST: buy-bottom coins the 30s seat fallback may take, then coins waiting on their chart; a coin that
            # already ran (at its highs / too far / too hot / too wild) goes LAST — the owner: "next up giving stuff that peaked"
            for x in (cfg_t.get('seatFallback') or []):
                if x.get('bottomWhy') and x.get('mint') not in seen_u and x.get('mint') not in on_ and len(up_) < 6:
                    seen_u.add(x['mint']); up_.append({**row_(x), 'tag': '🟢 buy bottom', 'wait': f"dip — {x['bottomWhy']} · takes a seat that stays empty 30s"})
            peaked_ = lambda w: any(k in w for k in ('at its highs', 'too far', 'too hot', 'too wild'))
            wrows_ = [(x, _prime.meta_why(x) or 'not ready') for x in _prime.flow_rank([y for y in watch_ if y.get('mint') not in on_ and not y.get('trenchOnly')])]
            for x, w_ in sorted(wrows_, key=lambda t: peaked_(t[1])):
                if x.get('mint') and x['mint'] not in seen_u and len(up_) < 6:
                    seen_u.add(x['mint']); up_.append({**row_(x), 'wait': w_ + (' — already ran' if peaked_(w_) else '')})
            up_ = [y for y in up_ if not str(y.get('wait') or '').startswith(('failed safety', 'holder scan', 'not on the runner board'))]   # 🧹 a coin that failed safety is never "coming up"
            # 💀 never a dead coin under Coming up (a 0 on the row = not read, the runner board's numbers win)
            cards[tid]['pipeline'] = {'at': now, 'steps': fun_ + [['not on the card and not cooling', len(free_)]], 'up': [_up_vital(u_) for u_ in [y for y in up_ if not _ja.dead_why({**{k: v for k, v in y.items() if v not in (None, 0, 0.0)}, **(_cand_map().get(y.get('mint')) or {})})][:6]], 'catMiss': cfg_t.get('catMiss') or {},
                                      'next': [f"${x.get('symbol')} {_fuse._f(x.get('chg1h')):+.0f}%" for x in sorted(free_, key=lambda x: -_fuse._f(x.get('chg1h')))[:4]],
                                      'scout': [f"${x.get('symbol')} {_fuse._f(x.get('chg1h')):+.0f}%" for x in scout_[:4]],
                                      'best': [_up_vital({k: x.get(k) for k in ('mint', 'pairAddress', 'symbol', 'price', 'chg1h', 'chg5m', 'vol1h', 'liq', 'tag', 'tape', 'buyShare')})
                                               for x in (cfg_t.get('bangers') or [])[:3]]}
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
    async with _admin_lock:
        d = _json_load(FUSE_HQ_PATH, {})
        if _hq_ver() != ver_:   # the file was saved while this tick worked: the owner's pick / skim / lock on a card beats the tick
            cards = _prime.merge_tick(snap_, cards, (d.get('prime') or {}).get('cards') or {})
        ps_ = _g4.pop('pendSeat', None)
        if ps_ and ps_.get('seated') and not ps_.get('retried') and not any(l_.get('mint') == ps_.get('mint') and not l_.get('placeholder') for c_ in cards.values() if (c_ or {}).get('real') for l_ in c_.get('legs') or []):
            _g4['want'] = {**ps_, 'at': time.time(), 'thinkAt': now, 'retried': True, 'seated': False}   # 🔁 your edit saved the card while this tick ran (it wins) → the model's seat is retried next tick, never silently lost
            _g4_fate(ps_, 'your edit saved the card at the same moment — retrying the seat next tick', now)
        _record_runs(before_runs, cards)
        try:
            cards = _paper_broke(d, cards, px, now)   # ♻ broke paper cards restart on a NEW config, the old one is scrapped
        except Exception as e:
            print('paper broke:', e)
        win = _prime.crown_round(cards)
        d.setdefault('prime', {})['cards'] = cards
        if any(c.get('real') for c in cards.values()) and not d['prime'].get('realCfg'):
            # 💵 the first time a card runs real money its config is FROZEN as its own — HQ / engine tunes on paper can't reach it after this
            d['prime']['realCfg'] = _prime.clean_cfg(d['prime'].get('cfg') or {})
            d['prime']['realCfg']['instantSwapPct'] = d['prime']['realCfg'].get('rotateMinDrop', 0)
        if win:
            d['prime']['roundWinner'] = {'id': win, 'at': now}
        _json_save(FUSE_HQ_PATH, d)
    return len(cards)


CARD_RECORDS_PATH = DATA_DIR / 'card_records.json'   # → card_records.db: every ended run of every tier card, append-only, forever


# ↪ moved to rep_predict.py: _hq_ver, _record_runs


PRIME_DS_BUDGET = 3.0     # DexScreener is only the FALLBACK price here (Jupiter wins for every coin it knows); after a restart its paced
                          # queue made the first /fuses/prime wait ~12s — it gets this long, then the coin uses the Jupiter price / its own
_prime_stages: dict = {}


# ↪ moved to rep_predict.py: _prime_reads


async def _prime_view():
    cards = (_json_load(FUSE_HQ_PATH, {}).get('prime') or {}).get('cards') or {}
    if not cards:
        return []
    fw_books = _fw_peek().get('books') or {}
    market_rows = _fw_market_rows(cards, fw_books)
    px, jup, sol_pre = await _prime_reads(market_rows)
    px.update({l['pairAddress']: jup[l['mint']] for l in market_rows if jup.get(l.get('mint'))})
    cyc = _prime_cfg().get('cycles') or _prime.DEFAULT_CYCLES
    def _cyc(tpl):
        seq = _prime.CYCLE_MODES.get(cyc.get(tpl, 'off'))
        return list(seq) if isinstance(seq, tuple) else ['anchor', 'mixed', 'degen'] if seq == 'adaptive' else None
    pcfg = _prime_cfg()
    rcfg = _prime_real_cfg()
    sol_now = sol_pre
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
        card_fees = _fw.card_fees_usd(b, sol_now)   # 🧾 network fees the CARD paid (from round 5), at each fill's SOL price — apart from P&L
        return {**sm, 'startUsd': round(start, 4), 'valueUsd': v, 'cardFeesUsd': card_fees, 'walletUsd': round(paid, 4), 'pnlPct': round((v / start - 1) * 100, 2),
                'legacyRunBaseline': not bool(c.get('realBaselineAt')),
                'payoutTargetUsd': round(_fuse._f(c.get('walletUsd')), 4),
                'pendingPayoutUsd': round(max(0.0, _fuse._f(c.get('walletUsd')) - _fuse._f(b.get('bankUsd'))), 4),
                'math': {**sm.get('math', {}), 'putIn': round(_fuse._f(b.get('fundedUsd')) or start, 4), 'runStartUsd': round(start, 4), 'heldUsd': round(held, 4), 'paidOutUsd': round(paid, 4),
                         'nowUsd': v, 'feesUsd': card_fees, 'pnlUsd': round(v + card_fees - (_fuse._f(b.get('fundedUsd')) or start), 4)}}   # P&L = price result; fees apart
    return [{**(sm := _truth(c, _prime.summary(c, px, _eff(c)))), **_vs(c, sm), 'seatPick': c.get('seatPick'), 'holdBy': c.get('holdBy'), 'proofWords': (_json_load(EDGE_AUDIT_PATH, {}).get('words') if c.get('real') else None), 'rebuying': (c.get('rebuy') or {}).get('mint'), 'seatQueue': c.get('seatQueue') or [], 'limits': [{**x_, 'word': _lim.word(x_)} for x_ in c.get('limits') or []], 'pipeline': c.get('pipeline'), 'parkedUsd': round(sum(_fuse._f(x.get('usd')) for x in c.get('skimPark') or []), 4), 'parkedN': len(c.get('skimPark') or []), 'heldUsd': round(max(0.0, _fuse._f(c.get('holdCashUsd')) - sum(_fuse._f(x.get('usd')) for x in c.get('skimPark') or [])), 4), 'cfgView': _cfgv(c), 'cfgScope': 'real' if c.get('real') else 'locked' if c.get('tpl') in locks else 'shared', 'cfgEff': _eff(c), 'pickStyle': None if c.get('real') else _eff(c).get('pickStyle'), 'holdAll': bool(c.get('holdAll')), 'pickCool': {}, 'handsOffUntil': c.get('handsOffUntil') if _prime.hands_off_left(c, time.time()) else None, 'cyclePeek': _prime.cycle_peek(c, _eff(c)), 'cycleMode': cyc.get(c['tpl'], 'off'), 'cycle': _cyc(c['tpl']), 'realBook': _fw_public(c['tpl'], sm.get('valueUsd'), sol_now, px) if c.get('real') else None,
             'audit': [{k: e.get(k) for k in ('at', 'kind', 'symbol', 'usd', 'why', 'to', 'mode')} for e in (c.get('events') or [])[-40:][::-1]]} for c in cards.values()]


PRIME_FRESH_SEC = 3.0     # a /fuses/prime answer this young is served as is
PRIME_STALE_SEC = 30.0    # this young: served at once while ONE background rebuild runs (a full build awaits prices — it took 12–13s at times)
_prime_resp: dict = {'at': 0.0, 'data': None, 'task': None, 'cleared': 0.0, 'snap': False, 'savedAt': 0.0}


# ↪ moved to rep_predict.py: _prime_resp_clear


PRIME_SNAPSHOT_PATH = DATA_DIR / 'prime_snapshot.json'   # 💾 the last good answer, served on the FIRST request after a restart
PRIME_SNAP_MAX = 900.0      # a snapshot older than 15 min is never served
PRIME_SNAP_EVERY = 60.0     # written at most once a minute


# ↪ moved to rep_predict.py: _prime_resp_build, _prime_snapshot, _prime_warm, _fuse_prime_build


# ---- 👛 FUSE WALLET (backend/fuse_wallet.py): the owner's Fuse Circle wallet funds the tier cards with REAL money ----
import fuse_wallet as _fw
FUSE_WALLET_PATH = DATA_DIR / 'fuse_wallet.json'   # {'cfg', 'books': {tier: book}, 'ledger': [orders · top-ups · defunds]}
_fw_lock = asyncio.Lock()
# ↪ moved to rep_fuse_wallet.py: _parsed_info


_FW_TOKEN_PROGRAMS = ('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')


import store as _store   # noqa: F401  (read by rep_ai, rep_fuse_wallet as rs._store)


# ↪ moved to rep_fuse_wallet.py: _fw_load, _fw_save


_fw_peek_cache = {'key': None, 'd': None}


# ↪ moved to rep_fuse_wallet.py: _fw_peek, _fw_cfg


_fw_signer = {'ok': False, 'at': 0.0}


# ↪ moved to rep_fuse_wallet.py: _fw_signer_ready, _fw_signer_check, _fw_sign, _fw_balances


JUP_BUSY_SEC = 20.0
_FW_JUP_BUSY = {'at': 0.0}   # when Jupiter last answered 429 / 5xx — sells and real buys keep the quota


JUP_GAP_SEC = 0.2            # (tests) scale of the per-lane spacing below
JUP_LANE_GAP = {'https://api.jup.ag': 1.05, 'https://lite-api.jup.ag': 0.35}   # a free key = ~1 request a second; the public lane is shared with our own price reads
JUP_LANE_REST = 8.0          # a lane that answered 429 rests this long (or its Retry-After, ≤ 20s)
_FW_JUP_PACE = {'lock': None, 'next': {}, 'rest': {}}


_JUP_KEY_N: dict = {}   # key → its lane number (1 = the first key: its pacing slot keeps the plain base name)


# ↪ moved to rep_fuse_wallet.py: _jup_keys, _jup_lanes, _jup_lid, _jup_pick, _fw_jup, _fw_quote, _fw_secure_buy


LIVE_SRC_SEC = 4.0      # 📡 each fresh source of the final buy gate answers inside this, or is skipped for this read (a paced / 429'd source used to hold the buy 12s+)
LIVE_PUMP_MAX = 12      # Pump records read in parallel per call (one short GET each)


# ↪ moved to rep_fuse_wallet.py: _fw_live_pairs, _fw_preflight, _fw_keep


_FW_NOT_COIN = ('not armed', 'paused', 'per-swap cap', 'daily cap', 'No Fuse wallet', 'signing not available', 'RPC pool', 'live market unavailable',
                '(HTTP 429)', '(HTTP 5')   # … and a busy Jupiter is never the coin's fault
_fw_bg: set = set()


# ↪ moved to rep_fuse_wallet.py: _fw_kick_now


_FW_BUY_PASS: dict = {}   # {card id: when the keeper last reached its BUY step} — the stuck-buy clock runs only after one (fuse_wallet.stuck_buys)
_FW_KICK: dict = {}   # {'at': when a real buy was refused / failed} → the round loop re-picks that seat RETRY_SEC later, not a tick later


# ↪ moved to rep_fuse_wallet.py: _fw_record, _fw_execute


_FW_DUPES = {'n': 0}   # 🔁 orders dropped because the card already had a tx in flight (one in-flight tx per card)
C2C_COOL_SEC = 600   # after a one-transaction swap fails, that card does plain two-step swaps for 10 minutes


# ↪ moved to rep_fuse_wallet.py: _fw_execute_swap, _fw_notify


_FW_RAW: dict = {}   # sig → (signed tx, kept at): in memory only, a blockhash lives ~90s


# ↪ moved to rep_fuse_wallet.py: _fw_raw_keep, _fw_rebroadcast, _fw_resolve


_fw_tick_lock = asyncio.Lock()


_FW_AGAIN: dict = {'at': 0.0}   # a keeper pass was asked for while one was running


# ↪ moved to rep_fuse_wallet.py: _fw_catch_up, _fw_tick


FUSE_DEPOSITS_PATH = DATA_DIR / 'fuse_deposits.json'   # {'address', 'cursor': newest sig seen, 'rows': [{sig, at, sol, from}]} — chain-audited
_fw_dep_at = {'t': 0.0}


# ↪ moved to rep_fuse_wallet.py: _fw_deposit_scan


_FW_GAS = {}
_FW_BAL = {}   # last good full balance read of the Fuse wallet (shown while the RPC is rate-limited)


# ↪ moved to rep_fuse_wallet.py: _fw_tick_inner


_fw_close_at = {'t': 0.0}


# ↪ moved to rep_fuse_wallet.py: _fw_rent_credit


_fw_rent_parked: dict = {}   # {sol, accounts, empty, at} from the last sweep's look at the wallet's coin accounts


# ↪ moved to rep_fuse_wallet.py: _fw_close_empty


_mint_dec: dict = {}


# ↪ moved to rep_fuse_wallet.py: _mint_decimals, _paper_quote_audit, _fw_calibration


_fw_full_cache: dict = {'n': -1, 'rows': []}


# ↪ moved to rep_fuse_wallet.py: _fw_full_ledger


_vs_c: dict = {}   # card → (ledger rows, at, (versus, realized)): the 24h you-vs-engine split + realized sales re-read the WHOLE ledger (3.9s of blocked loop)


# ↪ moved to rep_fuse_wallet.py: _vs_cached


_FW_LED_MEMO: dict = {}


# ↪ moved to rep_fuse_wallet.py: _fw_led_memo, _fw_public, _circle_wallets_live


CIRCLE_PROFILE_KEYS = {'name': 'displayName', 'handle': 'handle', 'bio': 'bio', 'avatar': 'avatarUrl', 'banner': 'bannerUrl'}


def circle_profile_view(prof: dict) -> dict:
    """The stored profile in the editor's short field names."""
    return {k: prof.get(real) for k, real in CIRCLE_PROFILE_KEYS.items()}


def circle_profile_merge(prev: dict, edit: dict) -> dict:
    """The stored profile with the editor's fields laid over it (the editor used short names the profile never stored:
    name / avatar / banner were silently dropped)."""
    return {**prev, **{real: edit[k] for k, real in CIRCLE_PROFILE_KEYS.items() if k in edit}}


# ↪ moved to rep_fuse_wallet.py: _fw_reports, _fw_recover_sell


ALLIANCES_PATH = DATA_DIR / 'alliances.json'
_alliance_lock = asyncio.Lock()


# ↪ moved to rep_fuse_wallet.py: _alliance_view


COLLECTIVE_THEMES = ('NEBULA', 'TOXIC', 'INFERNO', 'GLACIER', 'VOID', 'SOLAR', 'MATRIX', 'ULTRA')


# ---- 🧠 THE AI ROUTER (backend/ai_router.py): optional, advisory, never in a hot loop or at the money boundary ----
import ai_router as _air   # noqa: F401  (read by rep_admin_reads, rep_admin_routes as rs._air)
import ai_learn as _ail   # noqa: F401  (read by rep_ai as rs._ail)
import trench_crew as _tcrew   # noqa: F401  (read by rep_ai as rs._tcrew)
AI_CFG_PATH = DATA_DIR / 'ai_providers.json'   # the provider order + on / off (no secrets — keys live in backend/.env only)
AI_EVERY = 15.0                                 # one advisory round every 15s, ≤ AI_JOBS cases (local inference is one at a time)
AI_JOBS = 3                                     # owner review · a split desk · a READY coin · an ambiguous setup — two calls a round at most (was 4)
AI_NOTES_KEEP = 60
AI_PROOF_PATH = DATA_DIR / 'ai_proof.json'      # 🧠 the model's stances, each judged 15 min later (ai_learn.py) — its record is what the agents learn from


# ↪ moved to rep_ai.py: _ai_book


_AI_URL = _re.compile(r'https?://\S+|www\.\S+|[A-Za-z0-9]{32,}')


# ↪ moved to rep_ai.py: _ai_quote, _ai_brief, _ai_learn_note, _ai_learn_settle, _ai_exit_settle, _ai_weights, _ai_learn_on


AI_LOG_KEEP = 60            # 🧠 the model's own decisions, newest last (memory only): what it was asked, what it said, what the kernel said
_ai = {'notes': {}, 'http': None, 'rounds': 0, 'lastAt': None, 'lastMs': None, 'log': [], 'fillQ': {}, 'exit': {}, 'exitBook': None}   # exit {mint: {word, at, sym, why}} = the model's last exit read on a HELD coin (exit_read.py)
AI_EXIT_PATH = DATA_DIR / 'ai_exit_proof.json'   # 🧠☠ every exit read, graded 15 min later — the record that decides whether Reaper may use it
import exit_read as _er   # noqa: F401  (read by rep_ai as rs._er)
import ai_snapshot as _snp   # noqa: F401  (read by rep_ai as rs._snp)
import candle_clock as _ccl


# ↪ moved to rep_ai.py: _ai_exit_book, _ai_exit_effects


_chart_widen: dict = {}   # {mint: {word: 'WIDEN', at}} — the chart's own read of each red seat this pass


# ↪ moved to rep_ai.py: _chart_widen_note, _ai_exit_words, _ai_log, _ai_cfg, _ai_http, _ai_view, _ai_jobs, _ai_signals, _ai_conflict, _ai_ambiguous


_learned_mem: dict = {'at': 0.0, 'chart': None, 'learned': None}


# ↪ moved to rep_ai.py: _ai_learned


_owner_line = {'at': 0.0, 'v': None}


# ↪ moved to rep_ai.py: _ai_owner, _agent_pred, _ai_snap, _ai_case


FEECAT_DUO_SEC = 240.0   # 🐱🤝 FeeCat gets ONE duo read every 4 min (owner, 2026-10-19: "calling OSSY or G4 every 3-5 min about a few coins")
FEECAT_DUO_ASK = ("You are FeeCat's trade desk: two models read the SAME packet — her open trades and the coins she may buy next, each with its vitals "
                  "(cap · age · 5-min move · buyers % · pool · status · the agents' read). Answer with ONE JSON object and nothing else: "
                  '{"avoid": [pairAddress …], "exit": [pairAddress …], "why": "one line per coin you named, numbers from the packet"}. '
                  "avoid = a candidate she should NOT buy now (falling, sellers leading, thin pool, rug signs). exit = an OPEN trade to bank now. "
                  "Name only pairAddresses that are in the packet. Name nothing when nothing is clearly wrong — an empty list is a fine answer.")
_feecat_ai: dict = {'at': 0.0, 'avoid': [], 'exit': [], 'why': '', 'models': [], 'split': []}


# ↪ moved to rep_ai.py: _feecat_packet, _feecat_duo


import ai_seat as _seat
AI_SEAT_PATH = DATA_DIR / 'ai_seat.json'
_g4_mem = _ms0.MemStore(lambda: AI_SEAT_PATH, 60.0, lambda p_, d_: _json_load(p_, d_), lambda p_, o_: _json_save(p_, o_))
import duo_votes as _dv   # noqa: E402  👍👎 every call is graded by the market at 5 min / 1 h / 24 h (votes raise the stakes)
DUO_VOTES_PATH = DATA_DIR / 'duo_votes.json'
_dv_mem = _ms0.MemStore(lambda: DUO_VOTES_PATH, 30.0, lambda p_, d_: _json_load(p_, d_), lambda p_, o_: _json_save(p_, o_))
_dv_key = lambda r_: f"{int(r_.get('at') or 0)}-{r_.get('model')}"


# ↪ moved to rep_ai.py: _dv_note, _dv_settle
_g4 = {'busy': False, 'at': 0.0, 'want': None}


# ↪ moved to rep_ai.py: _g4_fate, _g4_state, _g4_qwen, _g4_real_record


_g4_les: dict = {'at': 0.0, 'v': None}


# ↪ moved to rep_ai.py: _g4_lessons, _duo_push, _g4_review


ADVISE_SEC, G4_STUCK_SEC = 45.0, 240.0   # the partner's advice never holds the holder's minute; a stuck tick is let go


# ↪ moved to rep_ai.py: _feecat_duo_safe, _g4_tick, _g4_idle


PARTNER_EVERY = 60.0   # (each coin re-read inside the 3-min window Reaper trusts a read) 🤝 Reaper's partner reads one of his coins this often (rotating)


# ↪ moved to rep_ai.py: _reaper_partner


_pred_c: dict = {'at': 0.0, 'proven': set()}


# ↪ moved to rep_ai.py: _pred_of


_lose_c: dict = {'at': 0.0, 'v': {}}
SPIKED_SINCE_READ = 8.0   # 🚀 the live price at the buy ≥ 8% over the price the agents decided on = no buy (they read a pass ago; the candle moved)


_DUO_GATE = {'on': True}   # 🤝 realCfg agentDuoGate (each tier tick): agent coins must be BACKED by OSSY / G4 first (ai_seat.duo_backs)
_duo_pred_c: dict = {'at': 0.0, 'rows': []}


# ↪ moved to rep_ai.py: _duo_backed, _agent_entry_ok


_g4_brake_c = {'at': 0.0, 'v': {}}


# ↪ moved to rep_ai.py: _g4_brake


G4_SPIKE_GERM = 5.0   # 🚀 a model may take a 5-min spike only this close (%) to its germ floor — the agents' 15% germ line let $mil (+23.9% in 5 min, 12% over its floor) through


# ↪ moved to rep_ai.py: _g4_picks_only, _g4_bad_entry, _g4_view


_stall_seen: dict = {}   # 🩺 model key → when its stall alert last went out (one per STALL_ALERT_EVERY)
STALL_ALERT_EVERY = 1800


# ↪ moved to rep_ai.py: _ai_stall_watch, _ai_round


LOCAL_LANE_EVERY = 180.0   # 💻 the local model's own lane: one pre-read per this many seconds (LOCAL_LANE_SEC in backend/.env; 0 = off)
_local_lane = {'at': 0.0, 'busy': False, 'n': 0, 'last': None, 'watch': None, 'every': None, 'whyEvery': None, 'lastMs': None, 'pausedAt': 0.0}
LOCAL_WATCH_PATH = DATA_DIR / 'local_watch.json'   # 💻 the local lane's 24h watch (24 hourly rows, tiny) — survives a backend restart


# ↪ moved to rep_ai.py: _lw_note, _local_lane_pick


import ai_duet as _duet   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._duet)
_duet_at = {'second': 0.0}


# ↪ moved to rep_ai.py: _duet_second


_exit2 = {'at': 0.0, 'busy': False}
EXIT2_EVERY = 75.0   # 🤝 the second model re-reads a held seat at most this often (it may share this Mac's GPU)


# ↪ moved to rep_ai.py: _exit_second, _local_lane_run


AI_GATE_SEC = 7.0   # 🛂 a seat waits at most this long for the model's read of the coin (a cloud answer takes ~5s); no answer in time = the coin goes


# ↪ moved to rep_ai.py: _ai_keep, _ai_gate


AI_DUTY = 0.5   # 💻 the local model may be busy at most half the time: after a round, wait at least as long as it took (owner, 2026-10-13: "so laggy")


# ↪ moved to rep_ai.py: _ai_pause


G4_LOOP_SEC = 5.0   # 🔁 the duo's own clock: checked every 5s, one decision a minute (_seat.EVERY_SEC)


# ↪ moved to rep_ai.py: _g4_loop, _ai_loop, _ai_general_context


# ── 💬 DIRECT LM CHAT + OWNER-APPROVED AGENT UPDATES (ai_chat.py) ────────────────────────────────────────────────────────────────────
import ai_chat as _aic   # noqa: F401  (read by rep_admin_reads, rep_admin_routes as rs._aic)
BUILD_QUEUE_PATH = DATA_DIR / 'build_queue.json'   # 📋 owner-approved build items — the next engineering session reads this first
AI_PROPOSALS_PATH = DATA_DIR / 'ai_proposals.json'   # compact proposal + audit records only (≤ 60; never a raw prompt or a raw response)
_chat: dict = {'th': {}, 'ctx': (None, None, 0.0), 'busy': False, 'props': None, 'build': None, 'loaded': False, 'saved': [], 'settings': None}   # one short thread PER MODE
AI_CHAT_PATH = DATA_DIR / 'ai_chat_state.json'   # 💾 the Brain's threads + saved conversations + settings (text only, small) — survive a restart


# ↪ moved to rep_ai.py: _brain_load, _chat_persist, _chat_extra
AI_CHAT_CTX_SEC = 20.0   # the compact agent-state context is rebuilt at most this often (and only its text changes the model's input)


# ↪ moved to rep_ai.py: _chat_props, _chat_context, _chat_olds, _ai_proposal_apply


import ai_play as _play   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
AI_PLAY_PATH = DATA_DIR / 'ai_playground.json'


AI_RIG_PATH = DATA_DIR / 'ai_rig.json'
AI_PRESETS_PATH = DATA_DIR / 'ai_presets.json'   # 🔖 per-model rig presets (ai_rig.preset_*)


# ↪ moved to rep_ai.py: _rig_apply


_lms_reloading: set = set()   # ⚡ models reloading right now (one reload per model at a time)
LMS_MARK_PATH = DATA_DIR / 'lms_reloading'   # 🚧 scripts/keep-alive.sh's LM watchdog stands down while this file is < 5 min old (no double load mid-reload)


# ↪ moved to rep_ai.py: _lms_reload
_lms_seen: dict = {}   # 🧠 {key: (at, lms_row)} — what each LM Studio REALLY runs (15s cache; a reload clears it)


# ↪ moved to rep_ai.py: _lms_states


# 🧠 THE MODEL DESK (owner, 2026-10-23: "the Models tab should really show it all — server settings, MCP, load, inference … more vitals"):
# Brain › Models per model = INFO · LOAD · INFERENCE · SERVER · MCP + live VITALS for every model (model_desk.py). One cached read per source.
import model_desk as _mdk   # noqa: E402
_mdk_seen: dict = {}


# ↪ moved to rep_ai.py: _mdk_cached, _mdk_lms, _mdk_mcp, _model_desk_view


# 🎭 PROMPT STUDIO (owner, 2026-10-22): each model's live context, its record, what the record says is wrong, and four prompt sets written from it
# (ELITE · DEGEN TRENCH · PROGRESSIVE · AUTO-TUNED). The owner applies one → the router appends it to every call that model gets (prompt_studio.py).
import prompt_studio as _pstu   # noqa: E402
PROMPT_STUDIO_PATH = DATA_DIR / 'prompt_studio.json'


# ↪ moved to rep_ai.py: _studio_apply


_studio_lms_note = {}


# ↪ moved to rep_ai.py: _studio_lms, _studio_trades, _studio_core


_studio_auto_at = {'t': 0.0}


# ↪ moved to rep_ai.py: _studio_auto, _studio_auto_safe, _studio_layer, _studio_view, _studio_fee


@app.on_event('startup')
async def _studio_boot():
    """The owner's applied mindsets ride every call from the FIRST one after a restart (+ the LM Studio live preset). This used to run at import
    time, before `_json_load` exists further down this file — 'name _json_load is not defined' on every restart, so no mindset rode G4 / OSSY's
    calls until someone opened Brain › Prompts (found 2026-10-23)."""
    try:
        _studio_apply()
    except Exception as e:
        print('prompt studio:', str(e)[:80])


COLONY_PATH = DATA_DIR / 'colony.json'
POOL_PATH = DATA_DIR / 'collective_pool.json'


# ↪ moved to rep_ai.py: _colony_value, _colony_view


COLONY_POOL_JS = Path(__file__).resolve().parent.parent / 'circle' / 'colony-pool.mjs'


POOL_QUOTES = {'SOL': ('So11111111111111111111111111111111111111112', 0.01, 1000), 'USDC': ('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 1, 100000)}
# ↪ moved to rep_ai.py: _pool_tokens, _colony_pool_build


import chat_evidence as _cev   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._cev)
_cev_cache: dict = {}


# ↪ moved to rep_ai.py: _chat_syms, _chat_coin, _owner_brief, _chat_evidence, _chat_learned


_CHAT_IMG = _re.compile(r'^/api/reputation/uploads/([0-9a-f]{32}\.(png|jpg|webp|gif))$')


# ↪ moved to rep_ai.py: _chat_image, _build_state


_rpc_warned = {'day': ''}


# ↪ moved to rep_ai.py: _rpc_quota_notice, _agents_loop, _fuse_warm_loop


_fuse_warm_n = {'n': 0}


import data_cleaner as _dc   # noqa: F401  (read by rep_ai as rs._dc)
import storage_trim as _strim

_data_clean_last: dict = {}


# ↪ moved to rep_ai.py: _data_clean


INTEL_DISK = DATA_DIR / 'intel_cache.json'
INTEL_DISK_MAX_AGE, INTEL_DISK_KEEP = 6 * 3600.0, 400   # scan RESULTS kept across a restart (a result older than its TTL is served as STALE while its refresh waits its turn)
LAUNCH_DISK, LAUNCH_KEEP = DATA_DIR / 'launch_facts.json', 4000
ENRICH_DISK = DATA_DIR / 'enrich_fresh.json'             # the scheduler's freshness book: last success / last attempt / back-off per mint
_intel_saved: dict = {'key': None}


# ↪ moved to rep_ai.py: _intel_save, _intel_restore


import paper_desk as _pd   # 📝 the OFFLINE practice record (graded paper calls) — it has no live authority   # noqa: F401  (read by rep_admin_reads, rep_ai as rs._pd)
import trench_kernel.universe as _uni
import trench_kernel.senses as _sn   # noqa: F401  (read by rep_ai as rs._sn)
import trench_mind as _tm   # noqa: F401  (read by rep_ai as rs._tm)
import opportunity as _opp
import launch_intel as _li   # noqa: F401  (read by rep_ai, rep_prime as rs._li)
import market_wake as _mw   # noqa: F401  (read by rep_ai, rep_prime as rs._mw)
import judge_review as _jr   # noqa: F401  (read by rep_ai as rs._jr)
import real_memory as _rm   # noqa: F401  (read by rep_ai as rs._rm)
import shadow_book as _sb   # noqa: F401  (read by rep_ai as rs._sb)
import coach as _co   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._co)
import trench_rounds as _tr   # noqa: F401  (read by rep_ai as rs._tr)
import generations as _gen   # noqa: F401  (read by rep_ai as rs._gen)
import trench_kernel.kernel as _tk
import trench_kernel.brain as _tkb   # noqa: F401  (read by rep_ai as rs._tkb)
import trench_kernel.lifecycle as _tkl   # noqa: F401  (read by rep_ai as rs._tkl)
import trench_kernel.positions as _pos
import trench_kernel.view as _tkv   # noqa: F401  (read by rep_ai as rs._tkv)
import trench_kernel.metrics as _tkm   # noqa: F401  (read by rep_ai as rs._tkm)
import trench_kernel.events as _tke   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._tke)
import trench_kernel.supply as _tks   # noqa: F401  (read by rep_ai as rs._tks)
import owner_review as _owr   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._owr)
import ai_keys as _aik   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
LINGO_PATH = FUSE_HQ_PATH.parent / 'trench_lingo.json'   # 📖 slang the desk learned from Pump callers' own words (per-day counts + learned words)
AGENTS_PATH = FUSE_HQ_PATH.parent / 'agents.json'   # 🤖 the agent desk: Tally's tapes, every call, every judged result
import mem_store as _ms
AGENTS_SAVE_SEC, LINGO_SAVE_SEC, SHADOW_SAVE_SEC, SOCIAL_SAVE_SEC, VIEW_SAVE_SEC = 90.0, 600.0, 60.0, 120.0, 60.0   # 💾 storage-efficient: the agents' stores live in memory
_agents_mem = _ms.MemStore(lambda: AGENTS_PATH, AGENTS_SAVE_SEC, lambda p_, d_: _json_load(p_, d_), lambda p_, o_: _json_save(p_, o_))   # loaded once, written ≤ every 90s + on shutdown (it was parsed AND written every pass)
_lingo_mem = _ms.MemStore(lambda: LINGO_PATH, LINGO_SAVE_SEC, lambda p_, d_: _json_load(p_, d_), lambda p_, o_: _json_save(p_, o_))
AGENTS_EVERY = 18.0                                 # ⚡ 3× a minute (owner, 2026-10-11: "seats never empty — 3× as fast"); a pass takes ~2s
# 🕸 the intake = office_edge.intake (reserved room for rechecks · newest · accelerating · graduations · momentum · busiest · listed, ≤ INTAKE_MAX)
_agents: dict = {'at': 0.0, 'table': [], 'view': None}


_rm_cache: dict = {'at': 0.0, 'mem': None}


LIFECYCLE_PATH = FUSE_HQ_PATH.parent / 'agent_lifecycle.json'   # 🧬 the ONE generation book of all ten roles (trench_kernel/lifecycle.py)
_lc_mem: dict = {'book': None}


# ↪ moved to rep_ai.py: _lc_book


_lc_sh_memo: dict = {}


# ↪ moved to rep_ai.py: _lc_shadows, _lc_shadows_raw


import evolution_lab as _evo   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._evo)
EVO_PATH = DATA_DIR / 'evolution_lab.json'   # 🧪 COL-11: the lab's OWN append-only ledger. It never writes the live trading tunables.
_evo_memo: dict = {}


# ↪ moved to rep_ai.py: _evo_view, _lifecycle, _lc_evaluate


ROUNDS_PATH = FUSE_HQ_PATH.parent / 'trench_rounds.json'   # ⏱ candidates' 5-minute rounds + the round history (trench_rounds.py)
_rounds: dict = {'state': None}


# ↪ moved to rep_ai.py: _rounds_state, _judge_weights, _paper_view, _kernel_view, _edge_rules, _edge_view, _kernel_ctx


OWNER_REVIEW_PATH = FUSE_HQ_PATH.parent / 'owner_review.json'   # 👤 the owner's review / track / arm list (owner_review.py)
_owner: dict = {'book': None, 'only': set()}
_tape_seen: dict = {'ledger': 0.0, 'reap': {}, 'regime': None, 'hub': 0}


# ↪ moved to rep_ai.py: _owner_book, _owner_view, _owner_resolve, _owner_act, _tape_flush, _tape_ledger, _tape_reaper


ENRICH_TOP = 4      # 🔎 Tier 2: holder / early-wallet scans for the strongest candidates only (Tier 0 = the whole intake, zero RPC)
ENRICH_MOVERS = 2   # … + at most this many brand-new movers a pass


import survival_watch as _surv   # noqa: F401  (read by rep_ai as rs._surv)
_FEATS: dict = {}   # 🧪 mint → its audit tags, refreshed every pass
_SURV: dict = {}   # ⏱ mint → its 1 / 5 / 15-min checkpoints since we first sensed it (survival_watch; memory only, rebuilt from the next passes)


# ↪ moved to rep_ai.py: _kernel_pass, _rounds_pass
SHADOW_PATH = FUSE_HQ_PATH.parent / 'shadow_book.json'   # 📄 paper decisions + controls (shadow_book.py), graded at 30s … 1h
_shadow: dict = {'book': None, 'cost': None, 'costAt': 0.0, 'dirty': False}


# ↪ moved to rep_ai.py: _shadow_cost, _st_med, _shadow_book, _shadow_px, _shadow_note, _shadow_controls, _shadow_real_buys, _shadow_settle
# ↪ moved to rep_ai.py: _shadow_flush


_real_tr: dict = {'at': 0.0, 'rows': []}


_dial_mem: dict = {'at': 0.0, 'v': None}


# ↪ moved to rep_ai.py: _dial_lab, _desk_stats_view


import night_guard as _ng   # noqa: F401  (read by rep_ai, rep_prime as rs._ng)
NIGHT_PATH = DATA_DIR / 'night_guard.json'
_night: dict = {'st': None, 'v': None}


# ↪ moved to rep_ai.py: _night_check, _real_trades


AFTER_PATH = DATA_DIR / 'after_paths.json'   # 👁 what each coin did in the 30 min AFTER our exit (after_path.py) — the replay's missing half
_after_mem = _ms.MemStore(lambda: AFTER_PATH, 60.0, lambda p_, d_: _json_load(p_, d_), lambda p_, o_: _json_save(p_, o_))


# ↪ moved to rep_ai.py: _after_step, _trail_view, _capital_view, _real_mem


COACH_PATH = FUSE_HQ_PATH.parent / 'agent_coach.json'   # 👑 the creator's + the model's live directives (coach.py) — small, written on each change
_coach: dict = {'s': None, 'tapeAt': 0.0, 'tape': None, 'aiAt': 0.0}
COACH_AI_EVERY = 900.0   # the model coach looks at the last real trades at most every 15 min (one cheap cloud call; never the local model)


# ↪ moved to rep_ai.py: _coach_state, _coach_put, _coach_pens, _coach_view, _trade_tape, _coach_grade


import rule_lab as _rlab   # noqa: F401  (read by rep_ai as rs._rlab)
import teach as _tch   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._tch)
import jup_keys as _jkeys   # noqa: F401  (read by rep_crews, rep_fuse as rs._jkeys)
TEACH_PATH = DATA_DIR / 'agent_teach.json'
_teach: dict = {'st': None}


# ↪ moved to rep_ai.py: _teach_state


import taught_rules as _trl   # noqa: F401  (read by rep_ai, rep_money_routes as rs._trl)


# ↪ moved to rep_ai.py: _taught_rules, _taught_stamp, _taught_view
import regret as _rg
import capital as _cap
import after_path as _ap   # noqa: F401  (read by rep_ai, rep_predict as rs._ap)
REGRET_PATH = DATA_DIR / 'regret.json'
_regret: dict = {'b': None, 'at': 0.0, 'savedAt': 0.0}


# ↪ moved to rep_ai.py: _regret_book, _regret_note, _regret_limits, _regret_tick


LAB_PATH = DATA_DIR / 'rule_lab.json'
LAB_EVERY, LAB_JUDGE_EVERY = 3600.0, 600.0
_lab: dict = {'st': None, 'at': 0.0, 'judgedAt': 0.0, 'said': None}


# ↪ moved to rep_ai.py: _lab_state, _lab_tick, _lab_view, _coach_ai


_reap_prev: dict = {}   # mint → (at, px): the fast stop guard's previous live read (office.spike_held)


GERM_REBUY_SEC = 7200.0   # 🦠 a Gstop sale is watched this long for a new germ floor


# ↪ moved to rep_ai.py: _germ_rebuy_step, _germ_of, _agent_blocked, _g4_blocked, _seat_refusals


AGENT_NOROUTE_SEC = 1800.0   # no way back to SOL / no route at all: 30 min (a curve coin's route does not appear in two)
AGENT_PRE_SEC = 180.0   # a coin that failed the seat pre-check (no live pool read / pool under the floor) sits out 3 min
SEAT_PRE_OK_SEC = 20.0
_seat_pre_ok = {}       # mint → (at, {liq, px}): coins that passed the pre-check in the last 20s
_agent_refused = {}     # mint → (until, why, at): the 🛂 seat pre-check's own refusals (memory only)


# ↪ moved to rep_ai.py: _seat_precheck, _agents_tick


import office as _of
OFFICE_PATH = FUSE_HQ_PATH.parent / 'agent_office.json'     # 🏢 tunables promoted by shadow tests · candidates · open positions · latency rings · counters
ARCHIVE_PATH = FUSE_HQ_PATH.parent / 'agent_archive.json'   # 🗄 hash-chained decision lineage (≤ 600 cases) + closed real positions (≤ 300); older fold into totals
_verify_memo: dict = {}


# ↪ moved to rep_ai.py: _arch_verify
_office: dict = {'state': None, 'pos': {}, 'exiting': [], 'gone': [], 'lat': {}, 'sized': {}, 'reports': [], 'warden': None, 'courier': None, 'payload': None, 'last': None, 'vetoAt': {},
                 'charts': {}, 'theses': {}, 'candles': {}, 'cmeta': {}, 'load': {}, 'boot': {'at': time.time(), 'passes': 0, 'coins': 0, 'reconciled': False}, 'seatWakeAt': 0.0, 'seatWakes': 0, 'ticks': [], 'candleStat': {'req': 0, 'cached': 0, 'merged': 0, 'dup': 0, 'ms': 0.0, 'coins': 0}}
import chart_intel as _ci   # noqa: F401  (read by rep_ai, rep_coin_edge as rs._ci)
import market_data as _md   # noqa: F401  (read by rep_ai as rs._md)
import office_edge as _oe
import seat_ops as _so
OFFICE_CANDLE_TTL = 12.0    # 👁 live: the chart is re-read when it is older than this (one batched local call for the whole desk); one read of a coin's 1-minute candles serves every desk for the whole pass (and the tier ticks until the next one)
# ↪ moved to rep_ai.py: _deep_bucket


OFFICE_CANDLE_CASES = 18    # real candles for the held coins + the top of the bench / strongest cases; every other coin is read from Tally's own tape (no request at all)
OFFICE_CANDLE_NEW = 6       # … + the busiest launches under ~20 min old (local candles service, one request per pool, 50s cache)


# ↪ moved to rep_ai.py: _office_candles
OFFICE_LAT_N = 120
OFFICE_REFRESH_MAX = 40     # ⚡ per tier tick (one batched call): at most this many pools get their candles re-read (only those whose read is older than OFFICE_CANDLE_TTL)


# ↪ moved to rep_ai.py: _mkt_view, _office_vels


_wake: dict = {'pos': {}, 'candAt': 0.0, 'log': [], 'n': 0, 'candN': 0}


LIVE_PX_SEC, LIVE_PX_BULK_SEC = 3, 8   # a few held seats answer fast; a 60-coin grading batch may take two upstream calls — a 3s cut-off
# returned NOTHING for the whole batch, and the graders read that as every coin vanishing (2026-10-13)


# ↪ moved to rep_ai.py: _live_px, _wake_note, _market_wake, _office_candle_refresh


CYCLE_LOG_N = 20
import intake as _in
INTAKE_PATH = FUSE_HQ_PATH.parent / 'intake_registry.json'   # 🕸 the one deduped intake registry (first / last seen per source + the office stamps)
INTAKE_JUP = 150            # coins an outlet lists that the board does not carry: rows from Jupiter's token data (100 a call, 60s cache)
_intake: dict = {'reg': None, 'last': None, 'prev': [], 'saveAt': 0.0}


# ↪ moved to rep_ai.py: _intake_reg


_intake_ds: dict = {}   # mint → (at, DexScreener pair | None) — 45s


# ↪ moved to rep_ai.py: _intake_dex, _intake_pass, _intake_after, _intake_view, _office_seat_payload, _office_cycle_log, _office_fresh
# ↪ moved to rep_ai.py: _office_load_pass


import social_research as _sr   # noqa: F401  (read by rep_ai as rs._sr)
SOCIAL_PATH = FUSE_HQ_PATH.parent / 'social_cache.json'   # 🔎 the research packets (≤ SOCIAL_KEEP, newest kept) — reloaded once after a restart
SOCIAL_KEEP = 400
SOCIAL_V = 4   # bump when the parser changes (v2: mints from visible text only · v3: no X link on a site = unknown · v4: evidence items + legal read)
_social: dict = {'cache': None, 'busy': False, 'searched': {}}


# ↪ moved to rep_ai.py: _social_cache, _social_flush, _research_tick, _seat_wake_maybe, _office_state, _office_lat, _office_ledger, _office_real
# ↪ moved to rep_ai.py: _office_ctx, _office_warden, _office_reap, _office_chart_view, _office_bars, _office_positions


_DELTA_DROP = ('ages', 'decidedAgo')      # relative ages tick every second: the stream sends absolute `times` / `decidedAt` instead
_POS_DROP = ('bars',)                      # a position's candles are the snapshot's (and the charts' own stream) — never re-sent per tick


# ↪ moved to rep_ai.py: _hub_publish


_SSE = {'connects': 0, 'disconnects': 0, 'resyncs': 0, 'active': 0, 'since': time.time()}   # 📡 measured: live streams + reconnects


# ↪ moved to rep_ai.py: _net_stats


STREAM_MAX_SEC = 1800.0     # a stream ends after 30 min (the page reconnects with its last sequence — nothing is lost)
STREAM_BEAT_SEC = 15.0


# ↪ moved to rep_ai.py: _office_light, _office_pass, _agents_real, _kernel_row, _agent_inherit_rows, _agents_go_rows, _agents_snapshot


# ⚡ WHAT THE PAGE GETS: the snapshot minus the sections no screen draws (they fed the retired room / seat views — 2026-10-12: ~350 KB of a
# 616 KB answer, most of it each row's research packet), serialized ONCE per 2s for every reader instead of encoded per request.
AGENTS_PAGE_DROP = ('index', 'social', 'cycleLog', 'intakeView', 'rpc', 'lifecycle', 'seatScores', 'seatActions', 'opp', 'loadPass', 'switchTests')
AGENTS_ROW_DROP = ('social',)
AGENTS_PAGE_SEC = 2
_agents_page: dict = {'key': None, 'body': b'{}'}


_duo_tape_c: dict = {'at': 0.0, 'v': ([], [])}


# ↪ moved to rep_ai.py: _duo_tape, _duo_totals, _duo_rooms, _duo_holding, _duo_card_legs, _duo_coin_rooms


DUO_PIN_PER, DUO_PIN_CARD = 8, 60   # 📣 chart comments kept per coin: 8 for coins off the card, the WHOLE history (≤ 60) for coins on it
_duo_cap_seen: dict = {}            # a line written without a cap keeps the cap of the moment it was first shown (never today's cap on an old pin)


# ↪ moved to rep_ai.py: _duo_pin_cap


def _duo_chart_rows(log, per=DUO_PIN_PER, card=None):
    """📣 model / owner / Reaper lines PER COIN (the chart of any coin shows its own talk): every line kept in the log for a coin on the card
    (owner, 2026-10-17: "full comment bubble history should show on chart"), the newest `per` for the rest."""
    out, n, card = [], {}, set(card or ())
    for r in reversed((log or [])[-400:]):
        m = r.get('mint')
        if m and r.get('action') in ('BUY', 'SELL', 'TALK', 'HOLD', 'TRIM', 'LINES') and n.get(m, 0) < (DUO_PIN_CARD if m in card else per):
            n[m] = n.get(m, 0) + 1
            out.append(r)
    return out[::-1]


# ↪ moved to rep_ai.py: _duo_cap, _duo_phase, _duo_view, _agents_page_dict, _agents_page_body, _fuse_warm


_runner_disc_cache = {'at': 0.0, 'data': None}


# ↪ moved to rep_ai.py: _round_move, _scenario_stage, _pg_pick_ok, _engine_auto, _engine_nudge, _top_anchor, _pg_scenario_cards, _pg_battle_view
# ↪ moved to rep_ai.py: _pg_battle_tick


import pg_sim as _pgs   # noqa: F401  (read by rep_ai as rs._pgs)
PG_SIM_PATH = DATA_DIR / 'pg_sim.json'   # its own file: never bloats runners.json


import pick_edge as _pedge
import pick_style as _ps
import owner_moves as _om   # noqa: F401  (read by rep_ai, rep_predict as rs._om)
EDGE_PATH = FUSE_HQ_PATH.parent / 'edge.json'
_edge_state: dict = {}


# ↪ moved to rep_ai.py: _edge_load, _pg_sim_tick, _brain_patch, _engine_self_fix


import verdict as _verdict   # noqa: F401  (read by rep_ai, rep_money_routes as rs._verdict)


VERDICT_PATH = DATA_DIR / 'fuse_verdict.json'
# 🧾 what one click can do with a verdict row (area → actions). Sim configs map onto the tier engine's own keys.
SIM_KEYS = {'minDrop': 'rotateMinDrop', 'confirm': 'rotateConfirm', 'rideAt': 'rideAt', 'trail': 'rideTrail', 'tp': 'tp', 'sl': 'sl'}


# ↪ moved to rep_ai.py: _verdict_acts, _retired, _verdict_build, _verdict_tick


class VerdictActIn(BaseModel):
    area: str
    name: str
    act: str
    tier: str = ''


class FuseLiteIn(BaseModel):
    budgetUsd: float = Field(default=10, ge=1, le=10000)
    again: int = Field(default=0, ge=0)                 # a nonce: 'Breed again' = a different random breed, never the cached one
    avoid: List[str] = Field(default_factory=list, max_length=12)   # coins the other baskets already hold → this one is unique


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


class FuseCardIn(BaseModel):
    signature: str
    collection: str = ''
    asset: str = ''


class FuseBuy(BaseModel):
    address: str
    session: str
    signature: str


# ---- FUSE Vault (backend/fuse_vault.py; on-chain program in programs/fuse_vault) ----------------------------------
import fuse_vault as _vault
VAULTS_PATH = DATA_DIR / 'fuse_vaults.json'   # {'vaults': {id: {name, emoji, pools[≤3], mgmtBps, perfBps, status}}}
VAULT_MAX_MGMT_BPS, VAULT_MAX_PERF_BPS = 300, 3000   # ≤3%/yr management, ≤30% performance


_SOL_LAST: dict = {}   # {'px', 'at'} — the last good SOL price


async def _sol_usd_live():
    """SOL in $: Jupiter's price (what real swaps route at) → DexScreener's SOL/USDC pool → the last good price (≤ 10 min) → 0.
    NEVER a made-up number: it used to fall back to a hard-coded $150 when DexScreener answered empty (2026-10-07, SOL was $116) —
    every real buy then read "~30% above market" and was refused, and card values were priced at $150 SOL. 0 = callers wait."""
    px = 0.0
    try:
        px = _fuse._f(((await _jup_prices([_fw.SOL_MINT])) or {}).get(_fw.SOL_MINT))
    except Exception:
        px = 0.0
    if px <= 0:
        try:
            p = await _fuse_pairs([{'chainId': 'solana', 'pairAddress': '58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2', 'mint': _fw.SOL_MINT}])   # Raydium SOL/USDC
            px = _fuse._f(next(iter(p.values())).get('priceUsd')) if p else 0.0
        except Exception:
            px = 0.0
    px = _fw.sol_price_pick(px, _SOL_LAST, time.time())
    return px


async def _vault_view(vid, v, deposit_sol=10.0):
    pools = _vault.clean_pools(v.get('pools'))
    pairs = await _fuse_pairs(pools)
    meta = {k: _fuse.leg_meta(p) for k, p in pairs.items()}
    sol_usd = await _sol_usd_live()
    sim = _vault.simulate(pools, meta, sol_usd, deposit_sol, v.get('mgmtBps', 0), v.get('perfBps', 0))
    return {'id': vid, **{k: v.get(k) for k in ('name', 'emoji', 'tagline', 'mgmtBps', 'perfBps', 'status', 'programId', 'createdAt')},
            'pools': [{**p, **meta.get(p['pairAddress'], {}), 'liveWeight': sim['weights'].get(p['pairAddress'])} for p in pools],
            'solUsd': sol_usd, 'sim': sim, 'feeWallet': _fee_cfg().get('vaultFeeWallet') or ''}


# ---- Quest engine: 40 animated badges (FEELESS + Fee Reserve), daily/weekly quests, levels (backend/quests.py) ----
import quests as _quests
QUESTS_PATH = DATA_DIR / 'quests.json'            # admin: {'badges': {id: override}, 'manual': {wallet: {grant, revoke}}}
QUEST_STATE_PATH = DATA_DIR / 'quest_state.json'  # {wallet: {'days': [YYYY-MM-DD], 'first': ts}} — moved into quest_state.db (SITE-8), kept read-only
_qs_docs: dict = {}


def _qs():
    """🗄 SITE-8: quest state as one row per wallet in SQLite: any number of workers check in at once without wiping each other (sql_store)."""
    import sql_store as _sqls
    k_ = str(QUEST_STATE_PATH)
    if k_ not in _qs_docs:
        _qs_docs[k_] = _sqls.Docs(QUEST_STATE_PATH)
    return _qs_docs[k_]
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
    st = _qs().get(me) or {}
    days = set(st.get('days') or []) | ({pts['claims']['daily']} if (pts.get('claims') or {}).get('daily') else set())
    creator = _load()['creators'].get(_creator_key('solana', me))
    return {'trades': trades, 'chat': chat, 'call_ts': [c.get('at') or 0 for c in calls], 'call_hits': hits,
            'invited': len(_json_load(REF_PATH, {'by': {}})['by'].get(me, [])),
            'followers': sum(1 for lst in (_json_load(FOLLOW_PATH, {}).get('following') or {}).values() if me in lst),
            'launches': score_creator(creator)['tokenCount'] if creator else 0, 'points': int(pts.get('total') or 0),
            'signin_days': sorted(days), 'streak': max(_streak(days), int(pts.get('streak') or 0)),
            'fee_usd': await _fee_usd(me), 'fee_mints': [m for m in (await _ecosystem_mints()).values() if m], 'first_seen': st.get('first'),
            'events': {**(st.get('events') or {}), **(fz := _fuse_quest_stats(mine))['events'], 'rug_found': __import__('bounty').find_events(_block_load()['wallets'], mine),
                       'predict_pick': [t for w in mine for t in (((_json_load(PREDICT_PATH, {}).get('players') or {}).get(w) or {}).get('pickAt') or [])],
                       'predict_win': [t for w in mine for t in (((_json_load(PREDICT_PATH, {}).get('players') or {}).get(w) or {}).get('winAt') or [])]}, 'fuse': fz['counts'],
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
    st = _qs().get(me) or {}
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
        _qs().update(me, lambda cur: {**(cur or {}), 'earned': {**earned_at, **((cur or {}).get('earned') or {})}, 'first': (cur or {}).get('first') or time.time(), 'days': (cur or {}).get('days') or []})
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
    wallets = set(_json_load(FEELESS_TRADES_PATH, {})) | set(_pts()) | set(_qs().all())
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


class QuestCheckin(BaseModel):
    address: str
    session: str


class QuestEvent(BaseModel):
    address: str
    session: str
    kind: str
    ref: str = Field(default='', max_length=120)


_quest_board_cache: dict = {}


import chain_rpc as _chain_rpc_mod   # noqa: E402,F401  (provider names for /health, read as rs._chain_rpc_mod)


# ---- FEELESS HQ: creator-wallet admin tools ------------------------------
# $FEE's creator wallet (fee payer of the mint's first transaction on-chain) is the default
# admin; FEELESS_ADMIN_WALLETS in backend/.env (comma separated) overrides it.
FEE_CREATOR_WALLET = _hq_auth.FEE_CREATOR_WALLET
ADMIN_PATH = DATA_DIR / 'admin.json'
BUGS_PATH = ADMIN_PATH.parent / 'bugs.json'
_admin_lock = _sqls_proc.ProcLock(lambda: FUSE_HQ_PATH)   # 🔒 SITE-8: one holder across every worker process — guards fuse_hq.json (117 saves) + runners.json (16)
_status_log = []          # rolling (ts, method, path, status) for the security monitor
_holder_cache = {}
_bug_ip_hits = _HITS('bug')


# ↪ moved to rep_hq.py: _admin_wallets, _admin_load, _badge_limits, _admin_save


_parse_cache = {}


# ↪ moved to rep_hq.py: _cached_json


_json_cost = {}   # 'load:runners.json' → [times, seconds] (bounded by the number of stores; shown by the loop-lag catcher)


# ↪ moved to rep_hq.py: _json_cost_note, _json_load, _json_save, _json_save_soft


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


# ↪ moved to rep_hq.py: _guard_save


import defence as _def
DEF_PATH = DATA_DIR / 'defence.json'
_def_state = None
_def_dirty = {'at': 0.0}


def _def_s():
    global _def_state
    if _def_state is None:
        _def_state = _def.new_state()
        saved = _json_load(DEF_PATH, {})
        for k in ('blocks', 'rules', 'incidents', 'uaHits'):
            if isinstance(saved.get(k), type(_def_state[k])):
                _def_state[k] = saved[k]
    return _def_state


# ↪ moved to rep_hq.py: _def_save


# ⚔️ SEC-1 War Room: the owner-only security dashboard's state (war_room.py). Sits on top of _def; all data is observed on our own server.
import war_room as _war          # noqa: E402
import war_hardening as _war_hard  # noqa: E402
WAR_PATH = DATA_DIR / 'war_room.json'
_war_state = None
_war_dirty = {'at': 0.0}


def _war_s():
    global _war_state
    if _war_state is None:
        _war_state = _war.new_state()
        saved = _json_load(WAR_PATH, {})
        for k in ('seq', 'events', 'captures', 'canaries', 'hits', 'nets', 'netSeen', 'sigs', 'revoked', 'reports', 'moves'):
            if k in saved and isinstance(saved[k], type(_war_state[k])):
                _war_state[k] = saved[k]
    return _war_state


# ↪ moved to rep_hq.py: _war_save


_BOUNTY_SCOPE = {
    'title': 'FEELESS responsible-disclosure bounty',
    'intro': 'Found a real security issue? Report it privately, give us time to fix, and get paid. Probing within scope is welcome — '
             'draining, phishing real users, or hitting anyone else is not.',
    'inScope': ['The FEELESS web app + API (reputation, candles, feecat services)', 'Fund-safety / signing / quote-integrity bugs',
                'Admin / session / privilege-escalation bugs', 'On-chain logic that could misroute fees or funds'],
    'outOfScope': ['Denial of service / volumetric floods', 'Automated scanner noise (our decoys handle it)', 'Anything touching other users\' funds or data',
                   'Social engineering of staff', 'Physical / third-party (Jupiter, Helius, the RPC nodes)'],
    'rules': ['Report privately first (this form), no public disclosure until fixed', 'No data exfiltration beyond proof-of-concept',
              'One wallet per researcher for payout', 'The owner reviews every report and decides the reward — crypto-native, severity-based'],
    'severity': [['Critical — funds at risk', 'top reward'], ['High — auth / privilege', 'high'], ['Medium — data / integrity', 'mid'], ['Low — hardening', 'small / swag']],
}


@app.middleware('http')
async def _record_status(request: Request, call_next):
    gs = _guard_s()
    ip = _guard.client_ip(request.headers, request.client.host if request.client else '', os.environ.get('FEELESS_TRUST_PROXY') == '1')
    ua = request.headers.get('user-agent', '')
    if not _guard.is_internal(ip) and _war.net_banned(_war_s(), ip):   # ⚔️ a subnet caught running scanners into our decoys
        return JSONResponse({'detail': 'Blocked.'}, status_code=403)
    auth_ = request.headers.get('authorization', '') or request.headers.get('x-api-key', '')
    if 'sk_live_' in auth_ and _war.canary_key_hit(_war_s(), auth_, ip, ua, request.url.path):   # ⚔️ a key planted in a decoy came back at us
        _war_save(force=True)
        return JSONResponse({'detail': 'Unauthorized.'}, status_code=401)
    d_ = _def.check(_def_s(), ip, ua, request.method, request.url.path, internal=_guard.is_internal(ip))   # 🛡 learned defence: decoys, rules, tarpits
    if d_:
        if d_[0] == 'honeypot':   # ⚔️ serve a fake page + capture the request, plant canaries, note the subnet — then study it in the War Room
            _def_save()
            try:
                ws = _war_s(); kind = _war.page_kind(request.url.path) or 'env'
                body_ = ''
                try:
                    body_ = (await request.body()).decode('utf-8', 'replace') if request.method in ('POST', 'PUT', 'PATCH') else ''
                except Exception:
                    body_ = ''
                _war.capture(ws, ip, ua, request.method, request.url.path, request.url.query, dict(request.headers), body_)
                _, canary_url, fake_key = _war.mint_canary(ws, origin=f'{kind}-decoy', note=request.url.path)
                _war.note_net(ws, ip, _def.fingerprint(ip, ua))
                _war_save(force=True)
                ctype, page = _war.decoy_page(kind, canary_url, fake_key)
                return Response(content=page, media_type=ctype, status_code=200 if kind != 'keys' else 200)
            except Exception:
                return JSONResponse({'detail': 'Not Found'}, status_code=404)
        if d_[0] == 'block':
            _def_save()
            return JSONResponse({'detail': 'Blocked.'}, status_code=403)
        await asyncio.sleep(d_[1])   # 🐢 tarpit: slowed, never refused
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
    """Session proof: the admin wallet signs `FEELESS HQ\\naddress:{a}\\nts:{ts}` (valid a day) — rules in hq_auth.py."""
    addr = _hq_auth.check_session(request.headers.get('x-admin-address', ''), request.headers.get('x-admin-ts', ''),
                                  request.headers.get('x-admin-sig', ''), _admin_wallets(), _verify_wallet, time.time())
    try:   # 🛡 the same HQ signature from a new fingerprint = a stolen session (flagged + tarpitted, the owner sees it in Security)
        ip_ = _guard.client_ip(request.headers, request.client.host if request.client else '', os.environ.get('FEELESS_TRUST_PROXY') == '1')
        sig_ = request.headers.get('x-admin-sig', ''); ua_ = request.headers.get('user-agent', '')
        if _def.seen_sig(_def_s(), sig_, ip_, ua_, request.url.path):
            _def_save(force=True)
        if _war.note_sig(_war_s(), sig_, ip_, ua_):   # ⚔️ same HQ signature from a second device → revoke (owner re-signs)
            _war_save(force=True)
        if _war.sig_revoked(_war_s(), sig_):
            raise HTTPException(401, 'This session was used from another device and has been revoked — sign in again.')
    except HTTPException:
        raise
    except Exception:
        pass
    _role_gate(addr, request)
    return addr


ROLE_SCOPES, ROLE_READ = _hq_auth.ROLE_SCOPES, _hq_auth.ROLE_READ   # 🔐 scoped roles (hq_auth.py)


# ↪ moved to rep_hq.py: _role_of, _role_gate, _audit, _token_holders


class AdminBadge(BaseModel):
    addresses: list
    label: str = Field(min_length=2, max_length=32)
    icon: str = Field(default='⭐', max_length=8)
    tone: str = 'gold'
    why: str = Field(default='', max_length=140)


class BadgeLimits(BaseModel):
    profile: int = Field(ge=0, le=12)
    chat: int = Field(ge=0, le=12)


@app.put('/api/reputation/admin/badges/limits')
async def badge_limits_admin_put(request: Request, payload: BadgeLimits):
    admin = _require_admin(request)
    async with _admin_lock:
        d = _admin_load()
        d['badgeLimits'] = payload.dict()
        _audit(d, admin, 'badge-limits', f'profile {payload.profile} · chat {payload.chat}')
        _admin_save(d)
    return _badge_limits()


class Airdrop(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    asset: str = 'fee'
    recipients: list
    scheduledAt: float
    note: str = Field(default='', max_length=280)


class AirdropStatus(BaseModel):
    status: str
    txSig: Optional[str] = None


class BugReport(BaseModel):
    text: str = Field(min_length=5, max_length=2000)
    page: str = Field(default='', max_length=300)
    kind: str = 'bug'
    address: Optional[str] = None


# ↪ moved to rep_hq.py: _bug_key


SUPPORT_PATH = DATA_DIR / 'support.json'   # 🛟 polls + "me too" marks (support.py); the reports themselves stay in bugs.json


class SupportAct(BaseModel):
    wallet: str
    session: str = ''
    plus: Optional[str] = None
    poll: Optional[str] = None
    opt: Optional[int] = None
    q: Optional[str] = None
    options: Optional[list] = None
    react: Optional[str] = None       # 👍 / 👎 any report · poll · idea (v = 1 | -1; the same again clears it)
    v: Optional[int] = None
    comment: Optional[str] = None     # 💬 the card id …
    text: Optional[str] = None        # … and the words (also a new idea's text)
    idea: Optional[bool] = None


BUG_FRESH_S = 3 * 86400   # 🐞 HQ's open-bug count: reports seen in 3 days (a dev-reload crash from weeks ago is not news)


# ↪ moved to rep_hq.py: _bug_seen


import presence as _pres   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
_presence = {}   # 🟢 wallet → (mode, at) — memory only, capped in presence.py


class PresenceBeat(BaseModel):
    address: str = Field(..., max_length=64)
    session: str = Field(..., max_length=400)
    mode: str = Field('online', max_length=12)


# 💬 THE STREETS — the Familia city chat, dressed (street_chat.py): crest + Don flag per line, call receipts, reactions, who is on the block, vitals
import street_chat as _stc
_street_here: dict = {}   # city → {wallet: last heartbeat} — memory only
_street_typing: dict = {}   # city → {wallet: last keystroke beat} — memory only (✍ typing presence)


# ↪ moved to rep_hq.py: _street_fams


class StreetTyping(BaseModel):
    address: str = Field(..., max_length=64)
    session: str = Field(..., max_length=400)


class StreetMod(BaseModel):
    address: str = Field(..., max_length=64)
    session: str = Field(..., max_length=400)
    id: str = Field('', max_length=40)
    act: str = Field('pull', max_length=8)
    sec: int = Field(0, ge=0, le=600)


_appr_hits = _HITS('appr')


class DefenceLift(BaseModel):
    fp: str = Field('', max_length=40)
    ua: str = Field('', max_length=40)


# ⚔️ SEC-1 War Room -------------------------------------------------------------------------------------------------------------


class WarTrace(BaseModel):
    wallet: str = Field(..., max_length=64)


class BountyReport(BaseModel):
    wallet: str = Field('', max_length=64)
    url: str = Field('', max_length=300)
    detail: str = Field(..., min_length=10, max_length=4000)
    reward: str = Field('', max_length=40)


# ⚖ LEGAL-1: versioned terms acceptance per wallet, a per-feature country / age gate (the owner switches it in HQ › Legal & regions),
# and a self-serve export / delete of a wallet's off-chain data. legal.py holds every rule; this only feeds it.
import legal as _legal   # noqa: E402
LEGAL_PATH = DATA_DIR / 'legal.json'
_legal_state = None


def _legal_s():
    global _legal_state
    if _legal_state is None:
        st = _legal.new_state(); saved = _json_load(LEGAL_PATH, {})
        if isinstance(saved.get('accept'), dict):
            st['accept'] = saved['accept']
        if isinstance(saved.get('cfg'), dict):
            st['cfg'] = _legal.clean_cfg(saved['cfg'])
        if isinstance(saved.get('requests'), list):
            st['requests'] = saved['requests']
        _legal_state = st
    return _legal_state


# ↪ moved to rep_hq.py: _legal_save, _legal_me


class LegalAccept(BaseModel):
    wallet: str = Field(..., min_length=20, max_length=64)
    session: str = Field(..., max_length=200)
    version: str = Field(..., max_length=20)
    country: str = Field(..., min_length=2, max_length=2)
    adult: bool = False
    notRestricted: bool = False


class LegalMine(BaseModel):
    wallet: str = Field(..., min_length=20, max_length=64)
    session: str = Field(..., max_length=200)
    confirm: Optional[str] = Field(None, max_length=20)


class LegalCfg(BaseModel):
    cfg: dict


# ↪ moved to rep_hq.py: _legal_hold, _legal_parts, _legal_wipe


class GuardDecision(BaseModel):
    ip: str = Field(..., max_length=64)
    action: str = Field(..., max_length=10)
    note: str = Field('', max_length=200)


# ⛓ Contract go-live checklist (HQ › Fuse › Contract): the owner records each real-money gate; READY only when all pass.
GOLIVE_STEPS = ('adapter', 'twap', 'devnet', 'audit', 'multisig')


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


_receipt_hits = _HITS('receipt')


@app.post('/api/reputation/receipts')
async def store_receipt(payload: ReceiptIn, request: Request):
    global _receipt_sigs
    if not await _ip_hit(_receipt_hits, request, 20, 60):  # each receipt costs RPC lookups; cap per IP
        raise HTTPException(429, 'Too many receipts — slow down.')
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
            tx = await _rpc(http, 'getTransaction', [payload.sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
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


def _snaps():
    return _json_load(SNAP_PATH, {'snaps': []})


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


# ---- Click tracking for $TICKERS, CAs and @mentions in chat -------------------------------
CLICKS_PATH = DATA_DIR / 'clicks.json'
_click_ip = _HITS('click')


class ClickIn(BaseModel):
    kind: str
    value: str = Field(min_length=1, max_length=64)
    room: str = Field(default='', max_length=140)


CLICKS_MAX = 20000


# ---- Auto profile: every wallet gets real on-chain stats before it ever sets up ------------
_wstats_cache = {}


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


class ChatDelete(BaseModel):
    room: str
    id: str
    address: str
    ts: int
    signature: str = ''
    session: str = ''


# ---- Trading fees & discounts, controlled only by the creator wallet -----------------------
# Jupiter's integrator fee: charged via a referral account the creator owns (50–255 bps allowed).
FEE_DEFAULTS = {'platformFeeBps': 0, 'referralAccount': '', 'tierDiscountPct': {'0': 0, '1': 10, '2': 25, '3': 50},
                'zeroFeeMints': [], 'promo': {'label': '', 'discountPct': 0, 'until': 0},
                # LI.FI (EVM swaps + bridges): fees go to the integrator's fee wallet registered at portal.li.fi.
                'lifiIntegrator': '', 'lifiFeeBps': 0, 'agentPassFeeLamports': 0,
                # Trading engine. 'swap' = Jupiter Swap API: FEELESS sets the fee (paid into its own SOL / USDC
                # token accounts), caps the priority fee and broadcasts. 'ultra' = Jupiter Ultra (referral fee,
                # 0.5–2.55%). ultraFallback: Ultra is only used when the Swap API fails AND this is switched on.
                'engine': 'swap', 'ultraFallback': False, 'feeAccountSol': '', 'feeAccountUsdc': '', 'priorityMaxLamports': 200000,
                # FUSE Vault: management + performance fees are paid in SOL to this wallet.
                'vaultFeeWallet': '', 'catFeeUsd': 2.0, 'catMinUsd': 10.0, 'catMaxModels': 3, 'agentTradeFeeUsd': 0.05, 'agentOtherFeeUsd': 0.10}
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


_fee_owner_cache: dict = {}


def _fee_owner_sol(acct):
    """🩹 which admin / owner wallet owns the SOL fee account (its wSOL ATA) — trading pays that wallet plain SOL while the account is closed."""
    if not acct:
        return None
    if acct not in _fee_owner_cache:
        import fee_tx as _ftx
        _fee_owner_cache[acct] = _ftx.fee_owner(acct, list(dict.fromkeys(_owner_wallets() + _admin_wallets())))
    return _fee_owner_cache[acct]


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


def _agent_owner(wallet: str) -> str:
    """👛 the wallet that OWNS an agent wallet (FeeCat's own Crossmint wallet per cat): `agentWallet.owner` is the signed-in wallet that made it
    (feecat_service checks the signature before it records it). '' when this isn't a live agent wallet."""
    if not wallet:
        return ''
    cats = (_json_load(DATA_DIR / 'feecats.json', {}) or {}).get('cats') or {}
    for c in cats.values():
        w = c.get('agentWallet') or {}
        if w.get('address') == wallet and not c.get('revoked'):
            return str(w.get('owner') or '')
    return ''


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
    if wallet and _is_staff(wallet):   # 👑 owner 2026-10-29: "creator wallet or admins don't pay fees site wide" — every trade, any engine
        return none('Creator / admin wallet: no FEELESS fee, site-wide.')
    if wallet and _is_staff(_agent_owner(wallet)):   # 👑 owner 2026-10-30: "no fee for staff" — an agent wallet a staff wallet owns trades fee-free too
        return none("Staff-owned agent wallet: no FEELESS fee.")
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
           'feeOwnerSol': _fee_owner_sol(cfg.get('feeAccountSol')) if bps else None,
           **eng}
    if bps and not fee_account and eng['engine'] == 'swap':
        # The fee is collected in SOL or USDC. A coin-to-coin trade has neither side, so it can't pay: refuse it
        # rather than let it through free.
        out['blocked'] = 'Every FEELESS trade pays the platform fee in SOL or USDC. Put SOL or USDC on one side (coin → SOL → coin).'
    return out


def _agent_wallets():
    return {(c.get('agentWallet') or {}).get('address') for c in (_json_load(DATA_DIR / 'feecats.json', {}).get('cats') or {}).values() if (c.get('agentWallet') or {}).get('circleAcct') == 'agent'}


AGENT_FEES_SENT = DATA_DIR / 'agent_fees_sent.json'


_GROW = {'at': 0.0, 'rows': [], 'detail': {}}
GROW_SOL_POOL = 'Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE'   # Orca's deepest SOL-USDC, for SOL's real price


async def _grow_rows():
    """💰 Every option, read from each venue's own numbers, at most every 5 minutes. A venue that fails only shrinks the list."""
    import grow_board as _gb
    if _GROW['rows'] and time.time() - _GROW['at'] < 300:
        return _GROW['rows']

    async def llama():
        r_ = await _fmk_http_get().get('https://yields.llama.fi/pools', timeout=25)
        return _gb.lend_rows((await asyncio.to_thread(json.loads, r_.content)).get('data') if r_.status_code == 200 else [])

    async def stocks():
        r_ = await _fmk_http_get().get('https://api.dexscreener.com/latest/dex/search', params={'q': 'xStock'}, timeout=12)
        return _gb.stock_rows(r_.json().get('pairs') if r_.status_code == 200 else [])

    async def planned():
        out_ = []; state_ = _cpool.load(POOL_PATH)
        for p_ in (state_.get('pools') or [])[:12]:
            if p_.get('address') and p_.get('mint'):
                out_ += [x_ for x_ in (await familia_pools_ranges(mint=p_['mint'], quote='', top=0, reads=1))['pools'] if x_['pool'] == p_['address']]
        return out_
    top_, lends_, stocks_, plan_ = await asyncio.gather(familia_pools_ranges(mint='', quote='', top=1, reads=1), llama(), stocks(), planned(), return_exceptions=True)
    ok_ = lambda v_: [] if isinstance(v_, BaseException) else v_
    rows_ = _gb.board(ok_(plan_) + (ok_(top_) or {}).get('pools', [] if not isinstance(top_, BaseException) else []) if not isinstance(top_, BaseException) else ok_(plan_), ok_(lends_), ok_(stocks_))
    _GROW.update(at=time.time(), rows=rows_, detail={})
    return rows_


def _site_landed(tx, pot):
    """(token, units) a successful transaction really added to the Collective wallet, or None."""
    meta = (tx or {}).get('meta') or {}
    if not tx or meta.get('err') is not None:
        return None
    keys = [str(k.get('pubkey') if isinstance(k, dict) else k) for k in ((tx.get('transaction') or {}).get('message') or {}).get('accountKeys') or []]
    if pot in keys:
        i = keys.index(pot); gain = int((meta.get('postBalances') or [0] * (i + 1))[i]) - int((meta.get('preBalances') or [0] * (i + 1))[i])
        if gain > 0:
            return 'SOL', gain
    bal = lambda rows: sum(int((r.get('uiTokenAmount') or {}).get('amount') or 0) for r in rows or [] if r.get('owner') == pot and r.get('mint') == USDC_MINT)
    gain = bal(meta.get('postTokenBalances')) - bal(meta.get('preTokenBalances'))
    return ('USDC', gain) if gain > 0 else None


def _site_fees_total():
    """Every swap fee FEELESS has really taken from regular traders, from its own ledger."""
    return sum(float(r.get('feeUsd') or 0) for v in (_json_load(FEE_LEDGER_PATH, {}) or {}).values() for r in (v or []) if isinstance(r, dict))


async def _collective_view():
    try:
        st = _cpool.load(POOL_PATH)
    except _cpool.Tampered as e:
        raise HTTPException(503, f'The ledger failed its seal and is locked: {e}')
    px = float(await _sol_usd() or 0)
    rows = sorted(((_cpool._locked_usd(a, px) + sum(_cpool._usd(a['owed'][t], t, px) for t in _cpool.TOKENS), c, a) for c, a in st['agents'].items()), key=lambda r: -r[0])[:12]
    return {**_stake.owner_view(st, px, time.time()), 'cfg': st['cfg'], 'defaults': _cpool.DEFAULTS, 'bounds': _cpool.BOUNDS, 'totals': _cpool.totals(st, px), 'chain': st.get('chain'), 'solUsd': px, 'wallet': ((_json_load(COLONY_PATH, {}) or {}).get('wallet') or {}).get('address'),
            'agents': [{'id': c, 'name': a.get('name'), 'owner': (a.get('owner') or '')[:6], **{k: v for k, v in _cpool.view(st, c, st.get('at') or 0, px).items() if k in ('lockedUsd', 'owedUsd', 'sentUsd', 'earnedUsd', 'boost', 'levers')}} for _, c, a in rows], 'log': (st.get('cfgLog') or [])[::-1], 'withdrawals': False, 'site': {'feesUsd': round(_site_fees_total(), 4), 'movedUsd': round(float(st.get('siteMovedUsd') or 0), 4), 'owedUsd': _cpool.site_owed(st['cfg'], _site_fees_total(), st.get('siteMovedUsd'))}, 'held': [{'cat': c, 'name': a.get('name'), **{k: r.get(k) for k in ('id', 'sym', 'at', 'review', 'sig')}} for c, a in st['agents'].items() for r in a.get('streams') or [] if r.get('held')][:30], 'reviewed': sum(1 for a in st['agents'].values() for r in a.get('streams') or [] if r.get('review')), 'hist': (st.get('hist') or [])[-180:], 'audit': st.get('auditNow'), 'head': st.get('head'), 'links': st.get('links') or 0, 'potKinds': list(_cpool.POT_KINDS)}


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
    catFeeUsd: float = Field(2.0, ge=0, le=100)     # 💵 FeeCat: FEELESS's one-time cut out of a cat's first funding (cat_fund.py)
    agentPassFeeLamports: int = Field(0, ge=0, le=5_000_000_000)   # 🎫 the Agent Pass mint fee; 0 = auto, 2× what Solana charges
    catMaxModels: int = Field(3, ge=1, le=8)
    agentTradeFeeUsd: float = Field(0.05, ge=0, le=10)   # 🤖 flat fee per swap / trench trade from an agent's wallet (replaces the % fee on it)
    agentOtherFeeUsd: float = Field(0.10, ge=0, le=10)   # 🤖 flat fee per finished task, anything that is not a trade
    catMinUsd: float = Field(10.0, ge=1, le=1000)   # 💵 FeeCat: the least a cat's first funding may be

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


class RoundsIn(BaseModel):
    address: str
    session: str
    id: str = Field(..., max_length=16)
    mode: str = Field(..., max_length=10)        # pay | compound | settle
    signature: str = Field(default='', max_length=100)


async def _fuse_rounds(p):
    """🔁 +5 rounds on YOUR card: 'pay' = a confirmed SOL transfer YOU signed to the fee wallet (checked on-chain, never reused);
    'compound' = rounds now, the card owes the price until its next profit take; 'settle' = pay what the card owes."""
    me = _session_or_401(p.address, p.session)
    mine = set(linked_of(me)) | {me}
    cfg = _rounds_cfg(); paid_usd = 0.0
    if p.mode in ('pay', 'settle') and (cfg['per5Usd'] > 0 or p.mode == 'settle'):
        if not _re.match(r'^[1-9A-HJ-NP-Za-km-z]{64,90}$', p.signature or ''):
            raise HTTPException(400, 'Send the payment first — no signature yet.')
        to = await _rounds_pay_to()
        if not to:
            raise HTTPException(503, 'Fee wallet not set — rounds cannot be bought right now.')
        tx = None
        async with httpx.AsyncClient(timeout=20) as http:
            for _ in range(5):
                tx = await _rpc(http, 'getTransaction', [p.signature, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
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


# 🏠 HOUSE FEES — the fees that used to be hard-coded, set in HQ › Core with the rest (owner: "all FEELESS fees set from HQ › Core"):
# the Fuse creator's max share of the FEELESS fee, FeeCat's paper fee per side (pushed to her service), the MP → FEECAT redeem rate.
HOUSE_DEFAULTS = {'fuseCreatorMaxBps': 5000, 'feecatFeePct': 1.0, 'redeemMp': 1_000_000, 'redeemFeecat': 10_000}


def _house():
    h_ = _fee_cfg().get('house') or {}
    return {**HOUSE_DEFAULTS, **{k_: h_[k_] for k_ in HOUSE_DEFAULTS if h_.get(k_) is not None}}


class HouseFees(BaseModel):
    fuseCreatorMaxBps: int = Field(5000, ge=0, le=10_000)
    feecatFeePct: float = Field(1.0, ge=0, le=5)
    redeemMp: int = Field(1_000_000, ge=10_000, le=1_000_000_000)
    redeemFeecat: int = Field(10_000, ge=1, le=1_000_000_000)


JUP_ULTRA_REFERRAL_PROJECT = 'DkiqsTrw1u1bYFumumC7sCG2S8K25qc2vemJFHyW2wJc'
JUP_REFERRAL_PROGRAM = 'REFER4ZgmyYx9c6He5XfaTMiGfdLwRnkV4RPp9t9iF3'


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


_fee_coin_names: dict = {}


# ---- Rug shield: one verdict for the swap review / quick trade, from on-chain forensics --------------


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
    qs = _qs().all()
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
    qs = _qs().all()
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


_case_peak: dict = {}   # mint → peak volume $/h seen (live case files)


# ---- Copy callers: calls from wallets you follow, newest first, with each caller's record ---------------


async def _fee_wallet_owner(http, cfg):
    """The wallet that owns the SOL/USDC fee account (read on-chain), used as the self-test's trader."""
    for acct in (cfg.get('feeAccountSol'), cfg.get('feeAccountUsdc')):
        if not acct:
            continue
        try:
            info = await _rpc(http, 'getAccountInfo', [acct, {'encoding': 'jsonParsed'}])
            owner = _parsed_info((info or {}).get('value')).get('owner')
            if owner:
                return owner
        except Exception:
            continue
    return None


def _quote_fee_bps(q):
    """The fee Jupiter says it will take on this quote: Swap API reports platformFee.feeBps, Ultra reports feeBps."""
    return int((q.get('platformFee') or {}).get('feeBps') or q.get('feeBps') or 0)


# ---- Chat sessions: sign once, chat for 7 days --------------------------------------------
import secrets as _secrets   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
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


def handle_of(address: str) -> str:
    p = _profiles_load()['profiles'].get(address) or {}
    return p.get('handle') or address[:6].lower()


# ---- Live FEELESS intelligence counts (Learn tab) ------------------------------------------
_marked = {'snipers': set(), 'bundlers': set(), 'mints': set()}
_hygiene_mem = {'d': None, 'dirty': False, 'at': 0.0}


def _hygiene_flush():
    hp = DATA_DIR / 'hygiene.json'
    if _hygiene_mem['d'] is None or not _hygiene_mem['dirty']:
        return
    _json_save(hp, _hygiene_mem['d'])
    st = hp.stat()
    _parse_cache[str(hp)] = ((st.st_mtime_ns, st.st_size), _hygiene_mem['d'])   # readers (`_hygiene`) keep reading the copy in memory
    _hygiene_mem.update(dirty=False, at=time.time())


def _absorb_intel(mint, out):
    creator = out.get('creator') if isinstance(out.get('creator'), str) else (out.get('creator') or {}).get('address')
    if creator:
        hp = DATA_DIR / 'hygiene.json'
        d = _hygiene_mem['d'] if _hygiene_mem['d'] is not None and not os.environ.get('PYTEST_CURRENT_TEST') else _json_load(hp, {})
        _hygiene_mem['d'] = d
        rec = {'snipers': len(out.get('sniperWallets') or []), 'bundled': len(out.get('bundledWallets') or [])}
        la = d.setdefault(creator, {'launches': {}})['launches']
        if la.get(mint) != rec:   # ⚡ a re-scan with the same counts writes nothing (the 6 MB store was re-written + re-parsed per scan)
            la[mint] = rec
            _hygiene_mem['dirty'] = True
        if _hygiene_mem['dirty'] and (os.environ.get('PYTEST_CURRENT_TEST') or time.time() - _hygiene_mem['at'] >= 60):
            _hygiene_flush()
    for w in out.get('sniperWallets') or []:
        _marked['snipers'].add(w if isinstance(w, str) else (w or {}).get('wallet') or (w or {}).get('owner'))
    for w in out.get('bundledWallets') or []:
        _marked['bundlers'].add(w if isinstance(w, str) else (w or {}).get('wallet') or (w or {}).get('owner'))
    _marked['mints'].add(mint)


_stats_cache = {'at': 0, 'data': None, 'lock': None}


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


class RefCfgIn(BaseModel):
    pct: float = Field(ge=0, le=50)


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


_ad_ev_ip = _HITS('adev')


# ---- HQ: pulse, moderation, broadcast, treasury ---------------------------------
MUTES_PATH = DATA_DIR / 'mutes.json'


def is_muted(address: str) -> float:
    until = _json_load(MUTES_PATH, {}).get(primary_of(address), 0)
    return until if until > time.time() else 0


# 🛠 old service-health pings posted into rooms ("Jupiter price … degraded for 3+ min", "recovered (124 ms)"): never social, never mod work
_OPS_PING = _re.compile(r'(recovered \(\d+ ms\)|degraded for \d+\+ min|Fallbacks are serving)')


class ModIn(BaseModel):
    room: str = ''
    id: str = ''
    address: str = ''
    hours: float = 24


class BroadcastIn(BaseModel):
    title: str = Field(min_length=2, max_length=60)
    body: str = Field(min_length=2, max_length=240)
    url: str = '/terminal'
    push: bool = False
    rooms: list = []


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
                    try:   # a 429 answers an HTML page — skip this batch (it printed "radar error Expecting value" every minute)
                        rj_ = r.json() if r.status_code == 200 else {}
                    except ValueError:
                        rj_ = {}
                    for p in (rj_ or {}).get('pairs') or []:
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
    _LEAD.start(_radar_loop)


def _feecat_pins(positions, top, now=None):
    """🤖🔁 HQ's Fee desk: for each coin she holds or would take next — the agents' current verdict (kernel status + why, at the coin's live cap)
    and OSSY / G4 / Reaper lines on it (the duo log, same rows the Agents chart pins). {mint: {agents: {...} | None, duo: [rows]}}. HQ only: users
    see Fee's own calls, never these."""
    now = time.time() if now is None else now
    mints = [m for m in dict.fromkeys([p.get('mint') for p in positions or []] + [t.get('mint') for t in top or []]) if m][:10]
    if not mints:
        return {}
    try:
        rows = _duo_chart_rows(_g4_state()['log'], card=mints)
    except Exception:
        rows = []
    out = {}
    for m in mints:
        try:
            x = _tk.KERNEL.candidate(m)
        except Exception:
            x = None
        cap = _duo_cap(m)
        ag = {'status': x.get('status'), 'why': str(x.get('kwhy') or '')[:200], 'rank': round(_fuse._f(x.get('rank')), 1), 'cap': cap, 'at': now} if x else None
        out[m] = {'agents': ag, 'duo': [{**r, 'cap': r.get('cap') or cap} for r in rows if r.get('mint') == m][-20:]}
    return out


def _feecat_fast_trench():
    """⚡ FeeCat's ONE dial (owner, 2026-10-16: "one dial only and that's FAST trench, same configs as the agents tab to start"): her rules seeded
    from the agents' live realCfg (MC floor, youngest age, pool floor, 1h volume, take / stop, seats). The page clamps each to her own bounds."""
    c_ = _prime_real_cfg() or {}
    f_ = lambda k_, d_: _fuse._f(c_.get(k_)) or d_
    vol_ = f_('agentMinVol1h', 5000)
    return {'minMarketCap': f_('agentMcMin', 12000), 'minAgeHours': max(0.05, f_('agentMinAgeH', 0.25)), 'minLiquidity': f_('agentPoolMin', 8000),
            'minVolume24h': vol_ * 24, 'takeProfit1': f_('agentTp', 30), 'takeProfit2': f_('agentTp', 30) * 2.5, 'hardStop': -f_('agentSl', 25),
            'runnerTrail': 20, 'maxHoldHours': 2, 'maxM5Chase': 4, 'maxPositions': 4, 'add1At': -15, 'add2At': -25, 'maxExposure': 0.4,
            'from': {k_: c_.get(k_) for k_ in ('agentMcMin', 'agentMcMax', 'agentMinAgeH', 'agentPoolMin', 'agentMinVol1h', 'agentTp', 'agentSl')}}


# ---- Notifications inbox (per identity) + push to the owner's devices ----------------------
NOTIF_PATH = DATA_DIR / 'notifications.json'
_notif_docs: dict = {}


def _notif():
    """🗄 SITE-8: the inbox, one row per wallet in SQLite (notifications.db). A new alert changes ONE wallet's row in one transaction, so
    any number of workers can notify at once and none wipes another's (the old whole-file write rewrote 4 MB per alert and lost races).
    notifications.json moved in once and is kept read-only."""
    import sql_store as _sqls
    k_ = str(NOTIF_PATH)
    if k_ not in _notif_docs:
        _notif_docs[k_] = _sqls.Docs(NOTIF_PATH)
    return _notif_docs[k_]


def _notif_box(wallet):
    """One wallet's inbox, newest first ([] when none or the store is unreadable)."""
    try:
        return _notif().get(wallet) or []
    except Exception:
        return []


def notify(address: str, kind: str, text: str, url: str = '', actor: str = '', once: str = '', meta: Optional[dict] = None, push: bool = True):
    """once: a dedupe key — a notification with the same key is never sent to this wallet twice.
    push=False: inbox only (the caller already pushed to the phone)."""
    to = primary_of(address)
    if not to or to in ('FEE-LEADER-CAT', 'FEELESS-HQ') or primary_of(actor or '') == to:
        return
    import sql_store as _sqls
    row = {'id': uuid.uuid4().hex[:10], 'kind': kind, 'text': text[:200], 'url': url, 'actor': actor, 'at': time.time(), 'read': False,
           **({'once': once} if once else {}), **({'meta': meta} if meta else {})}

    def add(box):
        box = box or []
        if once and any(n.get('once') == once for n in box):
            return _sqls.Result(box or None, False)
        return _sqls.Result([row, *box][:200], True)
    if not _notif().update(to, add):
        return
    if not push:
        return
    try:
        for e in _push_load()['subs'].values():
            if primary_of((e.get('prefs') or {}).get('address') or '') == to:
                asyncio.get_running_loop().run_in_executor(None, _send_push, e['subscription'], {'dm': '💬 New message', 'follow': '➕ New follower', 'wall': '🧱 New wall post', 'mention': '📣 You were mentioned', 'reward': '🎁 Reward ready', 'invite': '🎉 Invite joined', 'snipers': '🎯 Snipers are out', 'watch': '👁 Watched wallet moved', 'autorange': '🤖 AutoRange'}.get(kind, 'FEELESS'), text[:120], url or '/terminal', f'n-{kind}')
    except Exception:
        pass


def _session_or_401(address, session):
    owner = session_address(session)
    if not owner or primary_of(owner) != primary_of(address):
        raise HTTPException(401, 'Sign in to chat first (one signature, 7 days).')
    return primary_of(address)


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


class ClaimIn(BaseModel):
    address: str
    session: str
    reward: str


# ---- Verified identities ---------------------------------------------------------------------
FEE_RESERVE_WALLET = 'Btiq3W3yhqSRbF1FEf2TQMNrwsknMpQmeb5K9TeD83qU'


def is_verified(address: str) -> bool:
    a = primary_of(address or '')
    return bool(a) and (_is_staff(a) or a == FEE_RESERVE_WALLET or a in (_admin_load().get('verified') or []))


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


class SiteIn(BaseModel):
    publicUrl: str


# ---- Points shop: spend what you earn --------------------------------------------------------
SHOP = [
    {'id': 'ring-diamond-7d', 'label': 'Diamond ring · 7 days', 'cost': 400, 'kind': 'style', 'grant': {'ring': 'diamond'}, 'days': 7},
    {'id': 'ring-gold-3d', 'label': 'Molten Gold ring · 3 days', 'cost': 600, 'kind': 'style', 'grant': {'ring': 'gold'}, 'days': 3},
    {'id': 'name-rainbow-7d', 'label': 'Rainbow name · 7 days', 'cost': 250, 'kind': 'style', 'grant': {'nameFx': 'rainbow'}, 'days': 7},
    {'id': 'boost-3', 'label': '3 chat boosts (any tier)', 'cost': 150, 'kind': 'boost', 'grant': {'boosts': 3}},
    {'id': 'raffle', 'label': 'Airdrop raffle ticket', 'cost': 100, 'kind': 'raffle', 'grant': {'tickets': 1}},
    {'id': 'badge-og', 'label': '"Points OG" badge (permanent)', 'cost': 2000, 'kind': 'badge', 'grant': {'badge': 'points-og'}},
    # 💎 ONE points system (docs/RULINGS.md #3): points power your family — 1 point = 100 MP into its bank, ≤ PTS_TO_MP_WEEK points a week
    {'id': 'family-mp', 'label': '10,000 MP into your family bank', 'cost': 100, 'kind': 'mp', 'grant': {'mp': 10_000}},
]
MP_PER_PT, PTS_TO_MP_WEEK = 100, 1000


def _unlocks(address: str):
    rec = _pts().get(primary_of(address)) or {}
    now = time.time()
    return {k: v for k, v in (rec.get('unlocks') or {}).items() if v == 'forever' or float(v) > now}, rec


class BuyIn(BaseModel):
    address: str
    session: str
    item: str


# ---- Trench Wars: weekly faction battle --------------------------------------------------------
FACTIONS = {'bulls': '🐂 Bulls', 'bears': '🐻 Bears', 'degens': '🎰 Degens'}
WARS_PATH = DATA_DIR / 'wars.json'


def _war_week():
    return time.strftime('%G-W%V', time.gmtime())


class JoinIn(BaseModel):
    address: str
    session: str
    faction: str


# ---- Wallet PnL from verified FEELESS receipts ------------------------------------------------


_mm_cache: dict = {}   # wallet → (at, view) — 45 s


# ---- Snipe risk for coin cards (cached intel only — never blocks a list) ----------------------


# ---- Helius webhooks: instant whale / dev-sell events (needs HELIUS_WEBHOOK_SECRET) -----------


# ---- Auto-managed Helius webhook: follows the public domain set in the HQ ---------
from chain_rpc import helius_key as _helius_key  # noqa: E402 (one copy)


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


PF_STALE_SEC = 900.0
_pf_busy: set = set()


async def _portfolio_build(a):
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
        async def ds_batch(chunk):   # ⚡ ONE DexScreener call per 30 coins (it was 2 calls per coin, paced: a 60-coin wallet waited > 1 min)
            try:
                rows_ = (await http.get(f"https://api.dexscreener.com/tokens/v1/solana/{','.join(chunk)}", timeout=8)).json() or []
            except Exception:
                rows_ = []
            for x in rows_ if isinstance(rows_, list) else []:
                m = (x.get('baseToken') or {}).get('address')
                if m in held and (m not in market or float((x.get('liquidity') or {}).get('usd') or 0) > float((market[m].get('liquidity') or {}).get('usd') or 0)):
                    market[m] = x
        await asyncio.gather(*(ds_batch(mints[i:i + 30]) for i in range(0, len(mints), 30)))
        miss = [m for m in mints if m not in market]
        if miss:   # Jupiter covers pump.fun curve tokens DexScreener hasn't indexed — batched, cached
            try:
                jt = await _jup_tokens(miss)
            except Exception:
                jt = {}
            for m in miss:
                j = (jt or {}).get(m)
                if j and j.get('usdPrice'):
                    market[m] = {'baseToken': {'address': m, 'symbol': j.get('symbol'), 'name': j.get('name')}, 'priceUsd': j.get('usdPrice'),
                                 'info': {'imageUrl': j.get('icon')}, 'priceChange': {'h24': (j.get('stats24h') or {}).get('priceChange')}, 'chainId': 'solana'}
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
from fastapi.responses import Response as _Resp   # noqa: F401  (read by rep_public_reads as rs._Resp)
from fnum import zero as _num_or_0   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
_img_cache = {}


# ---- Social graph: follow / followers / following ----------------------------------------------
FOLLOW_PATH = DATA_DIR / 'follows.json'


def _fol():
    return _json_load(FOLLOW_PATH, {'following': {}})


class FollowIn(BaseModel):
    address: str
    session: str
    target: str
    follow: bool = True


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


def _edge_price_ok(sent, live):
    """🔒 The browser's price is only believed near the server's own: a forged observation can't plant fake grades. With no live read, it is not filed."""
    return bool(live) and live / 3 <= sent <= live * 3


_edge_ip = _HITS('edge')


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
    _LEAD.start(_refresh_edge_memory)


# ---- HQ: the numbers side --------------------------------------------------------
# One call for everything an owner watches: $FEE market, holder base, treasury, swap flow through
# FEELESS (from stored on-chain receipts), and the scanner's output. A snapshot is kept per day,
# so growth lines build themselves from the first time the owner opens this.
NUMBERS_PATH = DATA_DIR / 'numbers_history.json'


# ---- Rep: where a wallet stands, and the dark side of the market ------------------------------


_dark_cache = {}


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
# ⛽ 2026-10-23: the station read EVERY tank as "unavailable" once Alchemy ran out of quota — each chain now falls through to a public node.
# Zora is off the station: LI.FI no longer routes it, so a Zora tank could never be filled in place.
GAS_RPC_PUBLIC = {'ethereum': 'https://ethereum-rpc.publicnode.com', 'base': 'https://base-rpc.publicnode.com', 'bsc': 'https://bsc-rpc.publicnode.com',
                  'arbitrum': 'https://arbitrum-one-rpc.publicnode.com', 'avalanche': 'https://avalanche-c-chain-rpc.publicnode.com',
                  'polygon': 'https://polygon-bor-rpc.publicnode.com', 'optimism': 'https://optimism-rpc.publicnode.com', 'zksync': 'https://mainnet.era.zksync.io',
                  'cronos': 'https://cronos-evm-rpc.publicnode.com', 'unichain': 'https://unichain-rpc.publicnode.com', 'worldchain': 'https://worldchain.drpc.org'}
NATIVE_SYMBOL = {'ethereum': 'ETH', 'base': 'ETH', 'arbitrum': 'ETH', 'optimism': 'ETH', 'zksync': 'ETH', 'zora': 'ETH', 'unichain': 'ETH',
                 'worldchain': 'ETH', 'bsc': 'BNB', 'avalanche': 'AVAX', 'polygon': 'POL', 'cronos': 'CRO'}
_native_px = {'at': 0, 'px': {}}


async def _native_prices(http):
    if time.time() - _native_px['at'] < 300 and _native_px['px']:
        return _native_px['px']
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


# ---- Holder themes: $1k+ in the FEELESS ecosystem recolors the logo + the whole site ----------
THEME_MIN_USD = 1000.0
POOL_BUILDER_MIN_USD = 5000.0
THEMES_PATH = DATA_DIR / 'themes.json'
_theme_docs: dict = {}


def _themes():
    """🗄 SITE-8: saved looks / colours, one row per wallet in SQLite (themes.db); themes.json moved in once and is kept read-only."""
    import sql_store as _sqls
    k_ = str(THEMES_PATH)
    if k_ not in _theme_docs:
        _theme_docs[k_] = _sqls.Docs(THEMES_PATH)
    return _theme_docs[k_]
_HEX = _re.compile(r'^#[0-9a-fA-F]{6}$')


_eco_hold_cache = {}


async def _eco_holding_usd(address: str) -> float:
    if address.startswith('0x'):
        return 0.0
    hit = _eco_hold_cache.get(address)
    if hit and time.time() - hit[1] < 60:   # ⚡ the theme route waited ~10s p95 on one lookup per coin, one after another
        return hit[0]

    async def one(mint):
        try:
            return await _holding_usd(address, mint) or 0
        except Exception:
            return 0
    vals = await asyncio.gather(*(one(m) for m in (await _ecosystem_mints()).values()))
    total = round(sum(vals), 2)
    if len(_eco_hold_cache) > 5000:
        _eco_hold_cache.clear()
    _eco_hold_cache[address] = (total, time.time())
    return total


class ThemePayload(BaseModel):
    address: str
    session: str
    accent: Optional[str] = None
    accent2: Optional[str] = None
    logo: Optional[str] = None
    look: Optional[str] = None   # 🎨 a look id (looks.py); with no accent it is the whole theme


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
    _LEAD.start(loop)


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
    sol_usd = await _sol_usd_live()   # Jupiter → DexScreener SOL/USDC → the last good price (a 0 here dropped every SOL-priced swap)
    txs = None
    if key_:
        try:
            r_ = await http.get(f'https://api.helius.xyz/v0/addresses/{address}/transactions', params={'api-key': key_, 'type': 'SWAP', 'limit': 100})
            txs = r_.json() if r_.status_code == 200 else None
        except Exception:
            txs = None
    if not isinstance(txs, list):   # 🔁 N07: Helius out of quota / down / not set → the wallet's own Solana RPC history (wallet_swaps.py), never an empty page
        return await _rpc_wallet_swaps(http, address, sol_usd)
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


RPC_SWAP_SIGS, RPC_SWAP_PAR = 40, 6


async def _rpc_wallet_swaps(http, address, sol_usd):
    """The wallet's last RPC_SWAP_SIGS transactions from Solana RPC (the pooled lanes: Alchemy / Helius RPC / public) → its swaps, read from
    its own balance changes (wallet_swaps.parse). RPC_SWAP_PAR reads at a time; a read that fails is skipped, never guessed."""
    try:
        sigs = await _rpc(http, 'getSignaturesForAddress', [address, {'limit': RPC_SWAP_SIGS, 'commitment': 'confirmed'}]) or []
    except Exception:
        return []
    sem = asyncio.Semaphore(RPC_SWAP_PAR)

    async def one(sig):
        async with sem:
            try:
                return await _rpc(http, 'getTransaction', [sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 0, 'commitment': 'confirmed'}])
            except Exception:
                return None
    txs = await asyncio.gather(*(one(x_['signature']) for x_ in sigs if x_.get('signature') and x_.get('err') is None))
    return [r_ for r_ in (_wswaps.parse(t_, address, sol_usd) for t_ in txs if t_) if r_]


# ---- KOL tracker: real trades of wallets FEELESS admins mark as KOLs, and why the pattern matters --
KOLS_PATH = DATA_DIR / 'kols.json'
_kol_cache = {}


class KolPayload(BaseModel):
    address: str
    name: str
    x: Optional[str] = ''
    chain: str = 'solana'


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


# ---- Traffic analytics for marketing: what people actually view (privacy-light) -----------------
# No raw IPs or wallets stored: visitors are a salted SHA-256 of IP+day (salt rotates daily), so
# uniques can be counted per day but never linked across days. Writes are batched in memory and
# flushed every 30s so page views cost no disk I/O at request time.
import hashlib as _hashlib   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
TRAFFIC_PATH = DATA_DIR / 'traffic.json'
_tr_buf = {'views': {}, 'uniq': {}, 'coins': {}, 'refs': {}, 'hours': {}}
_tr_salt = {'day': '', 'salt': ''}
_tr_ip = _HITS('pv')


TR_MAP_MAX = 2000


class PageView(BaseModel):
    path: str
    ref: Optional[str] = ''


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
    _LEAD.start(_shield_watch)


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


# ================================================================================================
# HQ ROLES + IDEAS
# ================================================================================================
ROLES_PATH = DATA_DIR / 'roles.json'
ROLE_NAMES = _hq_auth.ROLE_NAMES


def _owner_wallets():
    return _hq_auth.owner_wallets(os.environ.get('FEELESS_ADMIN_WALLETS', ''))


def _granted():
    return _json_load(ROLES_PATH, {'grants': {}})['grants']


class RolePayload(BaseModel):
    address: str
    role: str
    ts: int = 0
    sig: str = ''


grant_message = _hq_auth.grant_message


IDEAS_PATH = DATA_DIR / 'ideas.json'
_IDEA_SEED = [{'id': 'passkeys', 'title': 'Passkey wallets + sponsored gas', 'status': 'saved', 'at': 0,
               'body': 'Onboard with Face ID / passkeys (no seed phrase) via smart accounts, and sponsor gas for first trades. Pairs with Get Gas: "trade anything from any chain, never think about gas." Needs a smart-wallet provider (e.g. Privy/Turnkey/Coinbase Smart Wallet) + a paymaster budget.'}]


class IdeaPayload(BaseModel):
    title: str
    body: str = ''
    status: str = 'saved'


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
    _LEAD.start(_drops_loop)


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


# ---- Token search for the swap box: every Solana token Jupiter knows ----------------------------
_tok_search_cache = {}


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


async def _locked_fills(address: str) -> list:
    """Every locked fill stored for this wallet (all coins), from the trading service. Same numbers as the chart."""
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            r = await http.get(f'http://127.0.0.1:5001/api/trading/internal/wallet-fills/{address}', headers={'x-feeless-internal': _internal_key()})
            return r.json().get('fills') or [] if r.status_code == 200 else []
    except Exception:
        return []


_version_cache: dict = {}


async def _git(*args, timeout=8):
    proc = await asyncio.create_subprocess_exec('git', *args, cwd=str(Path(__file__).resolve().parents[1]), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except asyncio.TimeoutError:
        proc.kill(); return ''
    return out.decode().strip() if proc.returncode == 0 else ''


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
    ('TELEGRAM_BOT_TOKEN', 'Telegram bot', 'Strike Zone inside Telegram: players shoot under their Telegram name + the bot posts level-ups to your group (docs/specs/site.md)', False),
    ('TELEGRAM_GROUP_ID', 'Telegram group', 'Where the bot posts level-ups (-100… id)', False),
    ('TELEGRAM_APP_URL', 'Telegram app link', 'https://t.me/<bot>/strike — the PLAY button on group posts', False),
]


# ---- Treasury routing: where FEELESS fee earnings go (addresses you control — never keys) --------
ROUTES_PATH = DATA_DIR / 'treasury_routes.json'


class RoutesPayload(BaseModel):
    routes: list


# ---- Shield leaderboard + weekly Rug Report ----------------------------------------------------


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


class LaunchCostsIn(BaseModel):
    pumpSlippagePct: float = 1.0
    pumpPriorityFeeSol: float = 0.0001
    feelessPriorityFeeSol: float = 0.0001


class LaunchTabIn(BaseModel):
    rails: list = ['feeless', 'pump']
    devBuy: bool = True
    maxDevBuySol: float = 5
    banner: bool = True


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


# 🎫 THE AGENT PASS (agent_pass.py): rules · prepare (number + metadata) · confirm (checked on-chain) — the owner's wallet mints and pays
import agent_pass as _apass  # noqa: E402
APASS_FILE = DATA_DIR / 'agent_passes.json'


class AgentPassIn(BaseModel):
    address: str
    session: str
    image: str = ''
    signature: str = ''
    asset: str = ''


def _pass_site():
    site = os.environ.get('PUBLIC_SITE_URL', '').strip().rstrip('/')
    host = _re.sub(r'^https?://', '', site).split('/')[0].split(':')[0]
    ok = site.startswith('https://') and host not in ('localhost', '127.0.0.1', '0.0.0.0') and not host.endswith('.local') and not _re.match(r'^(10|192\.168|172\.(1[6-9]|2\d|3[01]))\.', host)
    return site if ok else ''


async def _agent_pass_rules():
    cfg = _fee_cfg(); fee_w = ((_json_load(COLONY_PATH, {}) or {}).get('wallet') or {}).get('address') or ''   # 🪙 an agent's fee goes to the Collective
    try:
        async with httpx.AsyncClient(timeout=8) as http:
            rent = int(await _rpc(http, 'getMinimumBalanceForRentExemption', [_apass.ASSET_BYTES]) or 0)
    except Exception:
        rent = 0
    prov = _apass.provider_lamports(rent) if rent else 0
    fee = _apass.fee_lamports(prov, cfg.get('agentPassFeeLamports') or 0) if prov else int(cfg.get('agentPassFeeLamports') or 0)
    why = '' if _pass_site() else 'Minting opens when FEELESS has its public domain (PUBLIC_SITE_URL, https) — a Pass\'s picture link is permanent.'
    why = why or ('' if fee_w else 'The Collective wallet is not open yet.') or ('' if prov else 'Solana did not answer — try again in a minute.')
    return {'ready': not why, 'why': why, 'feeWallet': fee_w, 'providerLamports': prov, 'feeLamports': fee, 'royaltyBps': _apass.ROYALTY_BPS, 'auto': not (cfg.get('agentPassFeeLamports') or 0)}


async def _owned_cat(cat_id, me):
    if not _re.match(r'^[A-Za-z0-9_-]{1,64}$', cat_id or ''):
        raise HTTPException(400, 'Not an agent id.')
    r = await _ai_http().get(f'http://127.0.0.1:5088/api/cats/{cat_id}', headers={'x-feeless-internal': _internal_key()}, timeout=8)
    if r.status_code != 200:
        raise HTTPException(404, 'Agent not found.')
    cat = (r.json() or {}).get('cat') or {}
    if me not in (cat.get('ownerWallet'), (cat.get('agentWallet') or {}).get('owner')):
        raise HTTPException(403, "Only this agent's owner wallet can mint its Pass.")
    return cat


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


_CHART_FILL = {}   # pairAddress → (at, keys)


async def _chart_fill(rows, now, limit=14):
    """📈 Candidates whose chart our own record cannot read yet (new to the board) get it from the market's 15-min candles
    (candles service, last 4h). ≤ `limit` lookups a tick, in parallel, 4 min cache; a miss leaves the row as it was. Tests never fetch."""
    need = [x for x in rows if not x.get('cBars') and x.get('pairAddress')][:limit]
    todo = [x['pairAddress'] for x in need if now - (_CHART_FILL.get(x['pairAddress']) or (0, None))[0] > 240]
    if todo and not os.environ.get('PYTEST_CURRENT_TEST'):
        async def one(http, pa):
            try:
                r = await http.get(f'http://127.0.0.1:5099/api/candles/solana/{pa}', params={'interval': '15m'})
                return pa, _pedge._chart.keys(_pedge._chart.points_from_candles((r.json() or {}).get('candles') or []), now)
            except Exception:
                return pa, None
        async with httpx.AsyncClient(timeout=5) as http:
            for pa, k in await asyncio.gather(*(one(http, pa) for pa in todo)):
                if k is not None:
                    _CHART_FILL[pa] = (now, k)
        if len(_CHART_FILL) > 400:
            for pa in sorted(_CHART_FILL, key=lambda q: _CHART_FILL[q][0])[:200]:
                _CHART_FILL.pop(pa, None)
    out = []
    for x in rows:
        hit = _CHART_FILL.get(x.get('pairAddress')) if not x.get('cBars') else None
        out.append({**x, **hit[1]} if hit and hit[1].get('cBars') else x)
    return out


_PUMP_PROFILE = {}   # mint → (at, profile | None)


# Browser-side Solana RPC relay for wallet-signed launches: the Helius key stays on the server and
# only read/send methods pass. Nothing here can sign — the user's wallet signs in the browser.
RPC_ALLOW = {'getAccountInfo', 'getMultipleAccounts', 'getLatestBlockhash', 'getMinimumBalanceForRentExemption', 'sendTransaction',
             'getSignatureStatuses', 'simulateTransaction', 'getBalance', 'getTokenAccountBalance', 'getFeeForMessage', 'getSlot',
             'getBlockHeight', 'isBlockhashValid', 'getEpochInfo',
             'getTokenAccountsByOwner', 'getBlockTime'}   # 🏗 LP positions in place (2026-10-23): the wallet's position NFTs + a pool's activation clock
# 🤖 AutoRange (2026-10-26): Meteora DLMM lists a wallet's positions with getProgramAccounts — allowed ONLY on these programs and ONLY with a
# memcmp filter (by owner / pool), never the unfiltered scan that would cost the relay a whole program's accounts.
RPC_GPA_PROGRAMS = {'LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo', 'CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK'}


def _rpc_call_ok(c) -> bool:
    if not isinstance(c, dict):
        return False
    if c.get('method') in RPC_ALLOW:
        return True
    if c.get('method') != 'getProgramAccounts':
        return False
    p_ = c.get('params') or []
    opt_ = p_[1] if len(p_) > 1 and isinstance(p_[1], dict) else {}
    return bool(p_) and p_[0] in RPC_GPA_PROGRAMS and any(isinstance(f_, dict) and 'memcmp' in f_ for f_ in (opt_.get('filters') or []))
_rpc_hits = _HITS('rpc')


def _relay_spent(r) -> bool:
    """An RPC answer that means 'this endpoint is out of quota / rate-limited' (HTTP 429, or a JSON-RPC error with code 429)."""
    if r.status_code == 429:
        return True
    try:
        b = r.json()
    except Exception:
        return False
    return any(isinstance(x, dict) and isinstance(x.get('error'), dict) and x['error'].get('code') in (429, -32429) for x in (b if isinstance(b, list) else [b]))


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


def _gold_creator(a):
    """Creator streak: 3+ launches, none dumped or rugged, scored Trusted. Earns the gold R."""
    entry = _load()['creators'].get(_creator_key('solana', a))
    if not entry:
        return False
    sc = score_creator(entry)
    return sc.get('badge') == 'trusted' and sc.get('tokenCount', 0) >= 3 and not (sc.get('dumpedCount', 0) + sc.get('ruggedCount', 0))


# ---- Launch radar: every coin launched through FEELESS, newest first, with its evidence ----------


async def _quiet(coro):
    try:
        await coro
    except Exception:
        pass


# ---- Rug-proof check: mint can't inflate, can't freeze, liquidity can't be pulled -------------------
POOLS_REG_PATH = DATA_DIR / 'pools_registry.json'
_rugproof_cache: dict = {}


class PoolRegIn(BaseModel):
    pool: str
    mint: str
    signature: str
    locked: bool = True


# ---- Coin logos: find once, cache on disk, serve fast -----------------------------------------------
# Public IPFS gateways rate-limit (ipfs.io returns 429), and some coins only carry their image inside
# on-chain metadata. This resolves a mint's logo from DexScreener / Jupiter / on-chain metadata, tries
# several IPFS gateways, stores the bytes, and serves them with a long cache.
LOGO_DIR = DATA_DIR / 'logos'
IPFS_GATEWAYS = ['https://cloudflare-ipfs.com/ipfs/', 'https://gateway.pinata.cloud/ipfs/', 'https://nftstorage.link/ipfs/', 'https://dweb.link/ipfs/', 'https://ipfs.io/ipfs/']
LOGO_BUDGET = 4.0          # all logo sources together; never a 7–20s wait for one coin
LOGO_SLOW_RETRY = 180.0    # a lookup that ran out of time is tried again after 3 min (a missing logo: 10 min)
_logo_miss: dict = {}
LOGO_OVERRIDE_PATH = DATA_DIR / 'logo_overrides.json'


class LogoIn(BaseModel):
    mint: str
    image: str = ''       # an upload path; empty clears the override


_logo_locks: dict = {}


def _ipfs_variants(u):
    m = _re.search(r'/ipfs/([^?#]+)', u or '') or _re.match(r'^ipfs://(.+)$', u or '')
    return [g + m.group(1) for g in IPFS_GATEWAYS] if m else [u]


async def _public_get(http, u, hops=3):
    """🔒 SITE-9 (2026-11-10): a URL from a coin's own metadata is the launcher's to choose, so it could name 127.0.0.1 or the LAN and make this
    server call it. Every hop must be a public http(s) address (`feeless_mcp.safe_url`); redirects are followed by hand so each one is checked."""
    import feeless_mcp as _fm
    from urllib.parse import urljoin
    for _ in range(hops + 1):
        if await asyncio.to_thread(_fm.safe_url, u):
            return None
        r = await http.get(u, timeout=8, follow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get('location'):
            u = urljoin(u, r.headers['location']); continue
        return r
    return None


async def _fetch_first(http, urls, want_json=False):
    for u in urls:
        try:
            r = await _public_get(http, u)
            if r is None or r.status_code != 200:
                continue
            if want_json:
                return r.json()
            ct = r.headers.get('content-type', '').split(';')[0]
            if ct.startswith('image/') and 0 < len(r.content) <= 2_500_000:
                return ct, r.content
        except Exception:
            continue
    return None


LOGO_THUMBS = (64, 128, 256)


def _logo_thumb(raw, w):
    """🖼 SITE-2: a coin logo at the size it is shown (2× its CSS px). 940 px logos were decoded for 22 px rows. → webp bytes, or None to serve the original."""
    import io
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(raw))
        if getattr(im, 'is_animated', False) or max(im.size) <= w:   # an animated logo keeps its motion; a small one is already small
            return None
        im = im.convert('RGBA'); im.thumbnail((w, w), Image.LANCZOS); out = io.BytesIO(); im.save(out, 'WEBP', quality=86, method=4)
        return out.getvalue()
    except Exception:   # noqa: BLE001 — anything Pillow can't read (svg) is served as it is
        return None


async def _token_logo_any(mint: str):
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
        async def _find():
            # Each source's picture is tried the moment it is known: DexScreener answers in 0.1 s, and waiting
            # for the slower sources first ran out LOGO_BUDGET and answered 404 for coins that do have a logo.
            async with httpx.AsyncClient(headers={'User-Agent': 'Mozilla/5.0'}) as http:
                async def _try(cands):
                    for u in [x for x in cands if x]:
                        got = await _fetch_first(http, _ipfs_variants(u))
                        if got:
                            return got
                    return None
                try:
                    d = (await http.get(f'https://api.dexscreener.com/tokens/v1/solana/{mint}', timeout=8)).json()
                    got = await _try([(p.get('info') or {}).get('imageUrl') for p in (d or [])[:3]])
                    if got:
                        return got
                except Exception:
                    pass
                try:
                    d = (await http.get(f'https://lite-api.jup.ag/tokens/v2/search?query={mint}', timeout=8)).json()
                    got = await _try([x.get('icon') for x in d if x.get('id') == mint])
                    if got:
                        return got
                except Exception:
                    pass
                try:   # on-chain Metaplex metadata: works on any RPC (getAsset below is Helius-only)
                    acct = await _rpc(http, 'getAccountInfo', [coin_meta.metadata_pda(mint), {'encoding': 'base64'}])
                    data = (((acct or {}).get('value') or {}).get('data') or [None])[0]
                    if data:
                        uri = coin_meta.parse_metadata(data).get('uri')
                        if uri:
                            meta = await _fetch_first(http, _ipfs_variants(uri), want_json=True)
                            got = await _try([(meta or {}).get('image')])
                            if got:
                                return got
                except Exception:
                    pass
                if mint.endswith('pump'):
                    try:
                        d = (await http.get(f'https://frontend-api-v3.pump.fun/coins-v2/{mint}', timeout=8)).json()
                        got = await _try([(d or {}).get('image_uri')])
                        if got:
                            return got
                    except Exception:
                        pass
                try:
                    a = await _rpc(http, 'getAsset', {'id': mint})
                    c = (a or {}).get('content') or {}
                    cands = [f.get('cdn_uri') for f in c.get('files') or []] + [(c.get('links') or {}).get('image')]
                    if c.get('json_uri'):
                        meta = await _fetch_first(http, _ipfs_variants(c['json_uri']), want_json=True)
                        cands.append((meta or {}).get('image'))
                    return await _try(cands)
                except Exception:
                    return None

        try:   # ⏱ every source together gets LOGO_BUDGET; a slow miss answers 404 at once (the page falls back to the next logo / glyph)
            got = await asyncio.wait_for(_find(), timeout=LOGO_BUDGET)
        except asyncio.TimeoutError:
            got = None
            _logo_miss[mint] = time.time() - (600 - LOGO_SLOW_RETRY)   # a SLOW coin is retried after LOGO_SLOW_RETRY, a missing one after 10 min
            raise HTTPException(404, 'No logo found in time.')
        if not got:
            _logo_miss[mint] = time.time()
            raise HTTPException(404, 'No logo found.')
        ct, body = got
        ext = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif', 'image/svg+xml': 'svg'}.get(ct, 'img')
        if _strim.cache_logo_ok(body):   # a huge logo is served, never cached (the cache had grown to 1.0 GB)
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
                        _ops_note(f"✅ {r['name']} recovered ({r['ms']} ms).")
                    _latency_bad.pop(r['name'], None)
                    continue
                st = _latency_bad.setdefault(r['name'], {'since': time.time()})
                if not st.get('posted') and time.time() - st['since'] >= 300:
                    st['posted'] = True
                    why = r['note'] or 'down' if not r['ok'] else f"{r['ms']} ms"
                    _ops_note(f"⚠️ {r['name']} ({r['role']}) degraded for 5+ min: {why}. Fallbacks are serving.")
        except Exception as exc:
            print('latency alarm error', exc)


def _ops_note(text):
    """🛠 Service health goes to the owners' private inbox (HQ), never the public FEEd (owner 2026-10-26: a social feed full of 'Jupiter price recovered' isn't real)."""
    for w_ in (_owner_wallets() or [])[:3]:
        notify(w_, 'ops', text, url='/terminal/hq', push=False, meta={'claim': 'ops', 'source': 'latency'})


@app.on_event('startup')
async def _start_latency_alarm():
    _LEAD.start(_latency_alarm)


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


# ---- Circle developer-controlled wallets (creator/owner only) -------------------------------------
# Proxies to the localhost Circle sidecar. Only owner wallets may list or create; keys never leave .env.
class CircleWalletIn(BaseModel):
    blockchain: str
    name: str = 'Creator wallet'


CIRCLE_DIR = Path(__file__).resolve().parents[1] / 'circle'
_circle_boot = {'at': 0.0}


async def _circle_start(agent=False) -> bool:
    """Start a Circle sidecar if it's installed and keyed (agent: the family + agent wallets account, port 5112). At most one attempt per 20s; never raises."""
    boot_ = 'agentAt' if agent else 'at'
    if time.time() - _circle_boot.get(boot_, 0) < 20 or not (CIRCLE_DIR / 'node_modules').exists() or not os.environ.get('CIRCLE_AGENT_API_KEY' if agent else 'CIRCLE_API_KEY'):
        return False
    _circle_boot[boot_] = time.time()
    try:
        import subprocess
        subprocess.Popen(['node', 'server.mjs'], cwd=str(CIRCLE_DIR), stdout=open('/tmp/feeless-circle-agent.log' if agent else '/tmp/feeless-circle.log', 'ab'), stderr=subprocess.STDOUT,
                         stdin=subprocess.DEVNULL, start_new_session=True, env={**os.environ, 'CIRCLE_TENANT': 'agent'} if agent else None)
    except Exception:
        return False
    await asyncio.sleep(1.5)
    return True


async def _circle(method, path, body=None, agent=False):
    r = None
    for attempt in range(3):   # sidecar down → start it (owner is signed in: every caller is owner-gated) and retry
        try:
            async with httpx.AsyncClient(timeout=30) as http:
                r = await http.request(method, f"http://127.0.0.1:{5112 if agent else 5111}{path}", json=body)
            break
        except httpx.ConnectError:
            if attempt == 2 or not (await _circle_start(agent) or attempt == 1):
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
        raise HTTPException(403, 'Only the FEELESS creator wallet can do this: it moves money, routes fees or holds keys.')
    return me


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


class ReservePaid(BaseModel):
    sigs: list[str] = Field(min_length=1, max_length=40)
    perKey: dict = {}           # badge pools: the plan's per-holder amount per badge key (scaled to what moved)
    plannedSol: float = 0


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


_reserve_pub_cache = {}


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


_pool_pub_cache = {}


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
    errRoutes: dict = Field(default_factory=dict)   # 'route · ErrorName' → count (which request failed, never a body)
    fx: dict = Field(default_factory=dict)   # the FX governor's counts: {running, paused, shed, pressure}
    layout: Optional[dict] = None   # 🧱 the page watcher: {sideways px, spills: [class], covered: [class]} — class names only


class PerfCfgIn(BaseModel):
    forceLite: bool


CODE_HEALTH_PATH = DATA_DIR / 'code_health.json'
_code_health_busy = {'on': False}


def _code_health_scan():
    import code_health as _ch
    _json_save(CODE_HEALTH_PATH, _ch.scan(Path(__file__).resolve().parent.parent))


async def _code_health_run():
    if _code_health_busy['on']:
        return
    _code_health_busy['on'] = True
    try:
        await asyncio.to_thread(_code_health_scan)   # a static file scan (~5s) — never on the loop, never on a GET
    finally:
        _code_health_busy['on'] = False


async def _code_health_loop():
    while True:
        try:
            st = CODE_HEALTH_PATH.stat().st_mtime if CODE_HEALTH_PATH.exists() else 0
            if time.time() - st > 6 * 3600:
                await _code_health_run()
        except Exception:
            pass
        await asyncio.sleep(1800)


CH_QUEUE_TAG = '🧹 Remove '


class ChQueue(BaseModel):
    file: str = Field(..., max_length=200)
    name: str = Field('', max_length=120)
    kind: str = Field('', max_length=20)
    fix: str = Field('', max_length=300)


_mach_cache = {'at': 0, 'v': {}}


async def _machine_read():
    """🖥 Load + swap of the machine running the services (60s cache, a thread — sysctl is a subprocess). Mac only; elsewhere load only."""
    if time.time() - _mach_cache['at'] < 60:
        return _mach_cache['v']

    def read():
        out = {'cores': os.cpu_count() or 8}
        try:
            out['load1'] = round(os.getloadavg()[0], 1)
        except OSError:
            pass
        try:
            import subprocess
            t = subprocess.run(['sysctl', '-n', 'vm.swapusage'], capture_output=True, text=True, timeout=3).stdout
            nums = {k: float(v.rstrip('M')) for k, v in _re.findall(r'(total|used) = ([\d.]+M)', t)}
            if nums.get('total'):
                out['swapPct'] = round(100 * nums.get('used', 0) / nums['total'], 1)
        except Exception:
            pass
        return out
    _mach_cache.update(at=time.time(), v=await asyncio.to_thread(read))
    return _mach_cache['v']


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
        v = 0.0
    if v <= 0:   # 🛟 this free endpoint rate-limits (429): the full chain (Jupiter key → DexScreener → last good), and a miss is never remembered as the price
        try:
            v = float(await _sol_usd_live() or 0)
        except Exception:
            v = 0.0
    if v <= 0:
        return hit[1] if hit and time.time() - hit[0] < 600 else 0.0
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


# ---- Wallet watch: one tap from any case file; alerts on the watched wallet's next buys/sells --------------
WATCH_PATH = DATA_DIR / 'wallet_watch.json'
WATCH_MAX_PER_USER = 25


class WatchIn(BaseModel):
    address: str
    session: str
    target: str
    on: bool = True


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
    _LEAD.start(_watch_loop)


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


# ---- Treasury hub: where the money sits, the split plan, and verified splits signed by the owner ----------
USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'


_pulse_cache: dict = {}


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
    _LEAD.start(_preflight_watch)


class SplitRecord(BaseModel):
    sigs: list[str] = Field(min_length=1, max_length=40)
    asset: str = 'SOL'


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


class VerifyRequest(BaseModel):
    address: str
    session: str
    mint: str
    note: str = Field(default='', max_length=280)


class VerifyAdminIn(BaseModel):
    mint: str
    action: str            # grant | revoke | clear
    note: str = Field(default='', max_length=200)


class BadgeEdit(BaseModel):
    label: str = Field(min_length=2, max_length=32)
    icon: str = Field(default='⭐', max_length=8)
    tone: str = 'gold'
    why: str = Field(default='', max_length=140)


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


class NftOnchainIn(BaseModel):
    address: str
    signature: str
    assets: list = []     # for drops: [{address, owner}]


async def _nft_verify(sig: str, signer: str, must_touch: list):
    async with httpx.AsyncClient(timeout=20) as http:
        tx = await _rpc(http, 'getTransaction', [sig, {'encoding': 'jsonParsed', 'maxSupportedTransactionVersion': 1, 'commitment': 'confirmed'}])
    if not tx or (tx.get('meta') or {}).get('err'):
        raise HTTPException(400, 'That transaction is not confirmed on-chain (or it failed).')
    keys = tx['transaction']['message']['accountKeys']
    if signer not in [k['pubkey'] for k in keys if k.get('signer')]:
        raise HTTPException(400, 'Signed by a different wallet.')
    if any(a not in [k['pubkey'] for k in keys] for a in must_touch):
        raise HTTPException(400, 'That transaction does not create this collection / these NFTs.')


class NftDropIn(BaseModel):
    to: list = []
    confirm: str = ''


# ---- Intel desk: the reputation department's database of ruggers, snipers, bundlers, funders and their crews -------
INTEL_DESK_PATH = DATA_DIR / 'intel_desk.json'
_desk = {'at': 0, 'snap': None, 'rings': [], 'actors': {}}


def _desk_build(force=False):
    """Rebuild the desk from the blocklist, funder graph and creator records (cheap: local data only). Cached 10 min;
    the saved file keeps a daily history so the owner can see the department's catch grow."""
    if not force and _desk['snap'] and (_desk.get('bg') or time.time() - _desk['at'] < 600):
        return _desk   # with the background loop running a reader NEVER rebuilds inline (it froze the service ~7s every 10 min)
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


def _desk_build_bg(force=False):
    # in a worker thread: ~7s of pure Python over the blocklist + funder graph. The loop may change a store mid-read → try again.
    for _ in range(3):
        try:
            return _desk_build(force)
        except RuntimeError:
            time.sleep(0.5)
    return _desk


_desk_flight: dict = {}


async def _desk_get(force=False):
    """The desk for an async reader: the copy in memory, or (first read after a start / a forced sweep) ONE shared build in a worker thread."""
    if _desk['snap'] is not None and not force:
        return _desk
    t = _desk_flight.get('t')
    if t is None or t.done():
        t = _desk_flight['t'] = asyncio.ensure_future(asyncio.to_thread(_desk_build_bg, True))
    try:
        await asyncio.shield(t)
    except Exception:
        pass
    return _desk


async def _desk_loop():
    _desk['bg'] = True
    await asyncio.sleep(5)
    while True:
        await _desk_get(force=True)
        await asyncio.sleep(600)


@app.on_event('startup')
async def _desk_start():
    _LEAD.start(_desk_loop)


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


# ---- Circle wallets: names, descriptions, sends (owner-only, audited) -----------------------------------
CIRCLE_META_PATH = DATA_DIR / 'circle_meta.json'


class CircleMetaIn(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    description: str = Field(default='', max_length=200)


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


class CircleDestIn(BaseModel):
    address: str
    label: str = ''
    remove: bool = False


class CircleSendIn(BaseModel):
    walletId: str
    tokenId: str
    to: str
    amount: str
    confirm: str = ''          # must repeat the destination's last 4 characters


def _fuse_card_free_sol(card_sol, wallet_sol):
    """SOL a Fuse card's wallet may send out by hand: everything except the card's own cash (its trading money), less one network fee."""
    return max(0.0, _fuse._f(wallet_sol) - _fuse._f(card_sol) - 0.00001)


async def _fuse_send_guard(wallet_id, token_id, amount):
    """🧯 A Circle send of SOL from a REAL Fuse card's wallet never takes the card's own cash (2026-11-11): the card's books would claim SOL
    that left. Withdraw from the card first (that moves the book), then send. Other wallets and tokens pass untouched."""
    w = next((x for x in (await _circle_wallets_live()) or [] if x.get('id') == wallet_id), None)
    if not w:
        return
    row = next((b for b in w.get('balances') or [] if b.get('tokenId') == token_id), None)
    if not row or str(row.get('symbol') or '').upper() != 'SOL' or row.get('mint'):
        return
    cards = ((_json_load(FUSE_HQ_PATH, {}) or {}).get('prime') or {}).get('cards') or {}
    for tid, c in cards.items():
        if not (c or {}).get('real'):
            continue
        v = _fw_public(tid)
        if v.get('wallet') != w.get('address'):
            continue
        r = v.get('reconciliation') or {}
        free = _fuse_card_free_sol(r.get('cardCashSol'), r.get('walletSol') if r.get('walletSol') is not None else row.get('amount'))
        if amount > free + 1e-9:
            raise HTTPException(409, f"That would take the Fuse card's own trading cash. This wallet can send up to {free:.6f} SOL now. "
                                     "Withdraw from the card first (Fuse › Withdraw), then send. Nothing moved.")
        return


# ---- 🧹 WALLET DUST CLEANUP (Trade › 🧹 Dust): read every coin a USER's wallet holds; they choose swap / burn + close; THEY sign ----
import dust as _dust
_EVM_ADDR = r'^0x[0-9a-fA-F]{40}$'
CRONOS_RPCS = ('https://evm.cronos.org', 'https://cronos-evm-rpc.publicnode.com', 'https://cronos.drpc.org')
_lifi_tok_cache: dict = {}


class DustCloseIn(BaseModel):
    address: str
    accounts: List[str] = Field(default_factory=list, max_length=40)


async def _sol_token_accounts(http, owner):
    async def read(pg):   # a busy public node is retried twice (1s apart) before the wallet reads as "busy"
        for k in range(3):
            try:
                return await _rpc(http, 'getTokenAccountsByOwner', [owner, {'programId': pg}, {'encoding': 'jsonParsed'}], scan=False)
            except Exception as e:
                if k == 2:
                    return e
                await asyncio.sleep(1.0)
    res = await asyncio.gather(*[read(pg) for pg in _dust.TOKEN_PROGRAMS])
    out = []
    for pg, r in zip(_dust.TOKEN_PROGRAMS, res):
        if isinstance(r, Exception):
            raise HTTPException(503, 'Solana RPC is busy — try again in a few seconds.')
        for a in (r or {}).get('value') or []:
            info = _parsed_info(a.get('account'))
            amt = info.get('tokenAmount') or {}
            if not info.get('mint'):
                continue
            out.append({'pubkey': a.get('pubkey'), 'program': pg, 'mint': info['mint'], 'owner': info.get('owner'), 'raw': int(amt.get('amount') or 0),
                        'decimals': int(amt.get('decimals') or 0), 'ui': _fuse._f(amt.get('uiAmount')), 'lamports': (a.get('account') or {}).get('lamports') or 0})
    return out


_cro_idx_cache: dict = {}    # wallet → (at, tokens the wallet index says it holds)
_cro_list_cache: dict = {}   # 'dex' → (at, DEX token list)
CRONOS_DEX_LIST = 'https://raw.githubusercontent.com/cronaswap/default-token-list/main/assets/tokens/cronos.json'
CRONOS_WALLET_INDEX = 'https://api.rabby.io/v1/user/token_list'   # discovery only: which contracts a wallet holds (balances are re-read on-chain by us)


async def _cronos_batch(http, calls):
    """JSON-RPC calls → {id: result}, 10 a batch across the public nodes (a big batch comes back as ONE error object)."""
    res = {}

    async def batch(chunk):
        for rpc_ in CRONOS_RPCS:
            try:
                j = (await http.post(rpc_, json=chunk)).json()
                if isinstance(j, list):
                    return {x.get('id'): x.get('result') for x in j}
            except Exception:
                continue
        return {}
    for got in await asyncio.gather(*[batch(calls[k:k + 10]) for k in range(0, len(calls), 10)]):
        res.update(got)
    return res


async def _cronos_candidates(http, address):
    """Every contract worth a balance read for this wallet: the swap router's list + a DEX list + what a wallet index says it holds."""
    now = time.time()
    hit = _lifi_tok_cache.get(25)
    if not hit or now - hit[0] > 600:
        try:
            r = await http.get('https://li.quest/v1/tokens', params={'chains': 25})
            toks = [t for t in ((r.json().get('tokens') or {}).get('25') or []) if t.get('address') and t['address'] != _dust.NATIVE_EVM]
            _lifi_tok_cache[25] = hit = (now, toks)
        except Exception:
            hit = hit or (0, [])
    dex = _cro_list_cache.get('dex')
    if not dex or now - dex[0] > 3600:
        try:
            r = await http.get(CRONOS_DEX_LIST)
            dex = (now, [t for t in r.json() if isinstance(t, dict) and t.get('chainId') == 25]) if r.status_code == 200 else (dex or (0, []))
        except Exception:
            dex = dex or (0, [])
        _cro_list_cache['dex'] = dex
    idx = _cro_idx_cache.get(address.lower())
    if not idx or now - idx[0] > 60:
        got, ok = [], False
        try:
            r = await http.get(CRONOS_WALLET_INDEX, params={'id': address, 'chain_id': 'cro', 'is_all': 'true'}, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200:
                got, ok = _dust.index_tokens(r.json()), True
        except Exception:
            pass
        idx = (now, got, ok) if ok or not idx else idx   # a failed read keeps the last answer
        _cro_idx_cache[address.lower()] = idx
        if len(_cro_idx_cache) > 300:
            for k in sorted(_cro_idx_cache, key=lambda k: _cro_idx_cache[k][0])[:100]:
                _cro_idx_cache.pop(k, None)
    return _dust.merge_tokens(hit[1], dex[1], idx[1]), bool(len(idx) > 2 and idx[2])


# ---- 🎵 MINI PLAYER: search (YouTube, + Spotify when keyed), top played (Apple chart), endless Next — read-only public data ----
import music as _music
_music_cache: dict = {}
_UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.9'}


async def _yt_search(q):
    key = ('yt', q.lower())
    hit = _music_cache.get(key)
    if hit and time.time() - hit[0] < 600:
        return hit[1]
    rows = []
    async with httpx.AsyncClient(timeout=10, headers=_UA, follow_redirects=True) as http:
        try:
            r = await http.get('https://www.youtube.com/results', params={'search_query': q, 'sp': 'EgIQAQ%3D%3D'})
            rows = _music.yt_results(r.text)
        except Exception:
            rows = []
        if not rows:   # fallback: a public Piped node (same videos, its own JSON)
            try:
                j = (await http.get('https://api.piped.private.coffee/search', params={'q': q, 'filter': 'videos'})).json()
                rows = [{'id': (x.get('url') or '').split('v=')[-1][:11], 'title': x.get('title'), 'channel': x.get('uploaderName'), 'length': '', 'views': '',
                         'url': f"https://www.youtube.com{x.get('url')}", 'thumb': x.get('thumbnail')} for x in (j.get('items') or []) if x.get('type') == 'stream'][:20]
            except Exception:
                rows = []
    if len(_music_cache) > 400:
        _music_cache.clear()
    _music_cache[key] = (time.time(), rows)
    return rows


async def _spotify_search(q):
    cid, sec = os.getenv('SPOTIFY_CLIENT_ID', ''), os.getenv('SPOTIFY_CLIENT_SECRET', '')
    if not (cid and sec):
        return None
    async with httpx.AsyncClient(timeout=8) as http:
        tok = _music_cache.get(('sp-token',))
        if not tok or time.time() - tok[0] > 3000:
            r = await http.post('https://accounts.spotify.com/api/token', data={'grant_type': 'client_credentials'}, auth=(cid, sec))
            tok = _music_cache[('sp-token',)] = (time.time(), r.json().get('access_token'))
        r = await http.get('https://api.spotify.com/v1/search', params={'q': q, 'type': 'track', 'limit': 10}, headers={'Authorization': f'Bearer {tok[1]}'})
        return _music.spotify_tracks(r.json())


# 🟦 FEE TRADES FROM HER CIRCLE WALLET (owner 2026-10-30: "feecat (nexa) should be able to use the wallet, not just read only").
# feecat_service's agent pass (agent_trade.py) runs every guard first (one in flight, per-buy + daily caps, the quote must echo the exact coins);
# here Circle signs ONLY a wallet of the creator's own Circle project that is assigned to that cat, our RPC sends it, and key → signature is
# written BEFORE the broadcast so a lost reply asked again with the same key never sends a second trade. Internal key only.
AGENT_CIRCLE_SENT = DATA_DIR / 'agent_circle_sent.json'


def _internal_ok(request):
    return bool(_internal_key()) and hmac.compare_digest(request.headers.get('x-feeless-internal', ''), _internal_key())


_CIRCLE_HELD: set = set()


def _agent_sol_to(cat_id):
    """Where an agent's SOL may go besides its own wrapped SOL: the Collective pot, and the top-up address its owner confirmed. Read from
    the server's own files, never from the request."""
    out = []
    try:
        pot = ((_json_load(DATA_DIR / 'colony.json', {}) or {}).get('wallet') or {}).get('address')
        out += [pot] if pot else []
        topup = ((((_json_load(DATA_DIR / 'feecats.json', {}) or {}).get('cats') or {}).get(cat_id) or {}).get('topup') or {}).get('address')
        out += [topup] if topup else []
    except Exception:   # noqa: BLE001 — an unreadable file only narrows where it may send
        pass
    return out


async def _agent_circle_sign_send(body, key_, tx_, wid_, addr_):
    acct_ = body.get('acct') == 'agent'   # 🟦 an agent's own wallet lives on the separate account; Fee's assigned wallet on the FEELESS one
    w_ = (await _circle('POST', '/wallet', {'id': wid_}, agent=True)).get('wallet') if acct_ else next((w for w in (await _circle_wallets_live()) or [] if w.get('id') == wid_), None)
    if not w_ or w_.get('address') != addr_:
        raise HTTPException(403, 'That Circle wallet is not this agent\'s assigned wallet.')
    signed_ = await _circle('POST', '/sign', {'walletId': wid_, 'rawTransaction': tx_, 'memo': f"FEELESS agent {str(body.get('catId') or '')[:20]}"}, agent=acct_)
    sig_ = str(signed_.get('signature') or signed_.get('txHash') or '')
    if not signed_.get('signedTransaction') or not sig_:
        raise HTTPException(502, 'Circle did not sign it.')
    async with _admin_lock:   # reloaded under the lock: an overlapping send's key is never overwritten by a stale copy
        _json_save(AGENT_CIRCLE_SENT, {**_json_load(AGENT_CIRCLE_SENT, {}), key_: sig_})   # written BEFORE the send
    async with httpx.AsyncClient(timeout=20) as http_:
        took_ = await _krpc(http_, 'sendTransaction', [signed_['signedTransaction'], {'encoding': 'base64', 'maxRetries': 3, 'preflightCommitment': 'confirmed'}])
    if not took_:
        print(f"[agent send] {key_}: the first RPC refused it or gave no answer; broadcasting until its blockhash dies")
    asyncio.create_task(_agent_send_loop(signed_['signedTransaction'], sig_))
    return {'signature': sig_}


async def _agent_send_loop(signed, sig, seconds=75):
    """📡 The keeper's rule on an agent's send too: one send through one busy node is why trades expire. The same signed bytes go to every node until the
    chain has them or the blockhash is dead. Same signature: it can only ever land once."""
    end_ = time.time() + seconds
    async with httpx.AsyncClient(timeout=8) as http_:
        while time.time() < end_:
            try:
                await _rpc_broadcast(http_, signed)
                await asyncio.sleep(2.5)
                st_ = await _krpc(http_, 'getSignatureStatuses', [[sig]])
                if ((st_ or {}).get('value') or [None])[0]:
                    return
            except (httpx.HTTPError, ValueError) as e:
                print(f'[agent send] {sig[:10]}: {str(e)[:80]}')
                await asyncio.sleep(2.5)

import rep_tools as _rep_tools  # noqa: E402
app.include_router(_rep_tools.router)   # 🧩 Q02: the first routes moved out of this file
import rep_admin_reads as _rep_admin_reads   # noqa: E402  🧩 Q02 slice 2: read-only admin views
app.include_router(_rep_admin_reads.router)
import rep_model_lab as _rep_model_lab   # 🧪 Model Lab: the owner's dataset, review queue and clean export
app.include_router(_rep_model_lab.router)
import rep_guardrails as _rep_guardrails   # 🛡 AGX-7: the owner's restrict-only guardrail switches
app.include_router(_rep_guardrails.router)
import rep_watch as _rep_watch   # 📺 Watch folder highlights: official channels' public feeds, filtered by team / player / gamer
app.include_router(_rep_watch.router)
import deploy_hosts as _deploy_hosts   # 🚀 Go live: hosts for a built page, cheapest first, each re-checked on its own pricing page daily
app.include_router(_deploy_hosts.router)


@app.on_event('startup')
async def _start_comp_collect():   # 🌐 COMP's internet learner, every 10 min
    _LEAD.start(_rep_model_lab.start_collect_loop)
admin_guard, admin_ai_providers = _rep_admin_reads.admin_guard, _rep_admin_reads.admin_ai_providers   # tests call these on this module
fuse_health = _rep_admin_reads.fuse_health
admin_familia_rules = _rep_admin_reads.admin_familia_rules
admin_familia_unlocks = _rep_admin_reads.admin_familia_unlocks
circle_profiles = _rep_admin_reads.circle_profiles
admin_rpc_status = _rep_admin_reads.admin_rpc_status
admin_ai_rig = _rep_admin_reads.admin_ai_rig
admin_ai_activity = _rep_admin_reads.admin_ai_activity
admin_ai_playground = _rep_admin_reads.admin_ai_playground
admin_ai_chat_get = _rep_admin_reads.admin_ai_chat_get
admin_runner_funnel = _rep_admin_reads.admin_runner_funnel
runners_cfg_get = _rep_admin_reads.runners_cfg_get
fuse_cards_admin = _rep_admin_reads.fuse_cards_admin
admin_fuses = _rep_admin_reads.admin_fuses
admin_vaults = _rep_admin_reads.admin_vaults
admin_holders = _rep_admin_reads.admin_holders
admin_stores = _rep_admin_reads.admin_stores
contract_golive = _rep_admin_reads.contract_golive
admin_grow = _rep_admin_reads.admin_grow
admin_fuse_fees = _rep_admin_reads.admin_fuse_fees
admin_fuse_fee_list = _rep_admin_reads.admin_fuse_fee_list
admin_fee_balances = _rep_admin_reads.admin_fee_balances
admin_treasury = _rep_admin_reads.admin_treasury
admin_seasons = _rep_admin_reads.admin_seasons
admin_roles = _rep_admin_reads.admin_roles
admin_setup = _rep_admin_reads.admin_setup
admin_reserve_plan = _rep_admin_reads.admin_reserve_plan
admin_badge_pool_plan = _rep_admin_reads.admin_badge_pool_plan
perf_code_health = _rep_admin_reads.perf_code_health
perf_admin = _rep_admin_reads.perf_admin
admin_fee_book = _rep_admin_reads.admin_fee_book
nft_card_holders = _rep_admin_reads.nft_card_holders
intel_desk_view = _rep_admin_reads.intel_desk_view
intel_desk_actor = _rep_admin_reads.intel_desk_actor
admin_fuse_rules_get = _rep_admin_reads.admin_fuse_rules_get
admin_auto_yield_get = _rep_admin_reads.admin_auto_yield_get
fuse_wallet_report = _rep_admin_reads.fuse_wallet_report
admin_providers = _rep_admin_reads.admin_providers
admin_ai_key_status = _rep_admin_reads.admin_ai_key_status
admin_ai_seat = _rep_admin_reads.admin_ai_seat
admin_agent_slots = _rep_admin_reads.admin_agent_slots
admin_colony = _rep_admin_reads.admin_colony
admin_ai_prompts = _rep_admin_reads.admin_ai_prompts
admin_agents_office = _rep_admin_reads.admin_agents_office
admin_agents = _rep_admin_reads.admin_agents
admin_agents_log = _rep_admin_reads.admin_agents_log
admin_runner_suggest = _rep_admin_reads.admin_runner_suggest
fuse_verdict = _rep_admin_reads.fuse_verdict
pg_sim_view = _rep_admin_reads.pg_sim_view
pg_battles_get = _rep_admin_reads.pg_battles_get
admin_quests = _rep_admin_reads.admin_quests
admin_defence = _rep_admin_reads.admin_defence
admin_stash = _rep_admin_reads.admin_stash
admin_py_agents = _rep_admin_reads.admin_py_agents
admin_collective = _rep_admin_reads.admin_collective
admin_fees_get = _rep_admin_reads.admin_fees_get
routes_get = _rep_admin_reads.routes_get
circle_status = _rep_admin_reads.circle_status
circle_wallets = _rep_admin_reads.circle_wallets
perf_loop = _rep_admin_reads.perf_loop
admin_money_pulse = _rep_admin_reads.admin_money_pulse
circle_destinations = _rep_admin_reads.circle_destinations
circle_meta_get = _rep_admin_reads.circle_meta_get


import rep_public_reads as _rep_public_reads   # noqa: E402  🧩 SITE-5 slice 5: small public read routes
app.include_router(_rep_public_reads.router)
caller_board = _rep_public_reads.caller_board
meme_terms = _rep_public_reads.meme_terms
rep_markets = _rep_public_reads.rep_markets
health = _rep_public_reads.health
support_board = _rep_public_reads.support_board
radar = _rep_public_reads.radar
notifications = _rep_public_reads.notifications
shop = _rep_public_reads.shop
wars = _rep_public_reads.wars
darkside = _rep_public_reads.darkside
season_reserve = _rep_public_reads.season_reserve
perf_config = _rep_public_reads.perf_config
reactions = _rep_public_reads.reactions
fuses_search = _rep_public_reads.fuses_search
fuse_replay = _rep_public_reads.fuse_replay
fuse_my_battles = _rep_public_reads.fuse_my_battles
fuses_prebuilt = _rep_public_reads.fuses_prebuilt
fuse_sparks = _rep_public_reads.fuse_sparks
fuse_strategies = _rep_public_reads.fuse_strategies
fuse_dna_unique = _rep_public_reads.fuse_dna_unique
top_clicks = _rep_public_reads.top_clicks
kols = _rep_public_reads.kols
badge_pools_public = _rep_public_reads.badge_pools_public
after_sell = _rep_public_reads.after_sell


fuses_list = _rep_public_reads.fuses_list
familia_block_visit = _rep_public_reads.familia_block_visit
quest_board = _rep_public_reads.quest_board
perks = _rep_public_reads.perks
identity = _rep_public_reads.identity
resolve_profile = _rep_public_reads.resolve_profile
follows = _rep_public_reads.follows
collection = _rep_public_reads.collection
version = _rep_public_reads.version
launch_rail = _rep_public_reads.launch_rail
pump_profile_get = _rep_public_reads.pump_profile_get
rugproof = _rep_public_reads.rugproof
nft_meta = _rep_public_reads.nft_meta

import rep_more_reads as _rep_more_reads   # noqa: E402  🧩 SITE-5 slice 8: plain read routes, moved by scripts/move-routes.py
app.include_router(_rep_more_reads.router)
creator_profile = _rep_more_reads.creator_profile
get_watchlist_feed = _rep_more_reads.get_watchlist_feed
global_feed = _rep_more_reads.global_feed
case_studies = _rep_more_reads.case_studies
get_upload = _rep_more_reads.get_upload
x_oauth_callback = _rep_more_reads.x_oauth_callback
chat_room = _rep_more_reads.chat_room
why_pump = _rep_more_reads.why_pump
coin_edge = _rep_more_reads.coin_edge
fuses_arena_best = _rep_more_reads.fuses_arena_best
fuses_feecat_pool = _rep_more_reads.fuses_feecat_pool
crew_public = _rep_more_reads.crew_public
site_updates = _rep_more_reads.site_updates
familia_broker_cdc_caps = _rep_more_reads.familia_broker_cdc_caps
familia_kalshi_proof = _rep_more_reads.familia_kalshi_proof
familia_kalshi_status = _rep_more_reads.familia_kalshi_status
familia_kalshi_positions = _rep_more_reads.familia_kalshi_positions
familia_paper_perps = _rep_more_reads.familia_paper_perps
familia_intake = _rep_more_reads.familia_intake
familia_town_live = _rep_more_reads.familia_town_live
familia_pools_sleep = _rep_more_reads.familia_pools_sleep
cat_fund_rules = _rep_more_reads.cat_fund_rules
familia_pools_gaps = _rep_more_reads.familia_pools_gaps
coin_price_gap = _rep_more_reads.coin_price_gap
familia_perps_real = _rep_more_reads.familia_perps_real
familia_perps_real_leaders = _rep_more_reads.familia_perps_real_leaders
familia_leverage = _rep_more_reads.familia_leverage
fuse_prime = _rep_more_reads.fuse_prime
evolution_lab = _rep_more_reads.evolution_lab
fuse_card_public = _rep_more_reads.fuse_card_public
vault_pool_search = _rep_more_reads.vault_pool_search
token_approvals = _rep_more_reads.token_approvals
internal_fees = _rep_more_reads.internal_fees
case_file = _rep_more_reads.case_file
live_stats = _rep_more_reads.live_stats
referral_info = _rep_more_reads.referral_info
dm_thread = _rep_more_reads.dm_thread
portfolio = _rep_more_reads.portfolio
wallet_trades_ep = _rep_more_reads.wallet_trades_ep
copy_check = _rep_more_reads.copy_check
launch_radar = _rep_more_reads.launch_radar
fee_report_get = _rep_more_reads.fee_report_get
watch_list = _rep_more_reads.watch_list
verify_one = _rep_more_reads.verify_one
internal_circle_wallet = _rep_more_reads.internal_circle_wallet
leaderboard = _rep_more_reads.leaderboard
get_watchlist = _rep_more_reads.get_watchlist
get_clusters = _rep_more_reads.get_clusters
roadmap_votes = _rep_more_reads.roadmap_votes
token_intel = _rep_more_reads.token_intel
hot_calls = _rep_more_reads.hot_calls
calls_by_room = _rep_more_reads.calls_by_room
token_balance = _rep_more_reads.token_balance
get_blocklist = _rep_more_reads.get_blocklist
chart_wallets = _rep_more_reads.chart_wallets
coin_read = _rep_more_reads.coin_read
fuses_discover = _rep_more_reads.fuses_discover
why_pump_board = _rep_more_reads.why_pump_board
fuse_holders = _rep_more_reads.fuse_holders
fuse_season = _rep_more_reads.fuse_season
fuse_ids = _rep_more_reads.fuse_ids
fuse_arena_public = _rep_more_reads.fuse_arena_public
fuse_paper = _rep_more_reads.fuse_paper
social_feed_thread = _rep_more_reads.social_feed_thread
social_feed = _rep_more_reads.social_feed
fuse_trench_open = _rep_more_reads.fuse_trench_open
fuse_call_proof = _rep_more_reads.fuse_call_proof
fuse_trench = _rep_more_reads.fuse_trench
familia_world = _rep_more_reads.familia_world
familia_pool_chart = _rep_more_reads.familia_pool_chart
familia_markets = _rep_more_reads.familia_markets
predict_state = _rep_more_reads.predict_state
rug_bounty = _rep_more_reads.rug_bounty
wallet_track_record = _rep_more_reads.wallet_track_record
fuses_pay_map = _rep_more_reads.fuses_pay_map
fuse_card_record = _rep_more_reads.fuse_card_record
internal_sicario_wallet = _rep_more_reads.internal_sicario_wallet
internal_sicario_fate = _rep_more_reads.internal_sicario_fate
runners_discover = _rep_more_reads.runners_discover
runners_board = _rep_more_reads.runners_board
quest_leaderboard = _rep_more_reads.quest_leaderboard
war_canary = _rep_more_reads.war_canary
war_bounty_scope = _rep_more_reads.war_bounty_scope
legal_status = _rep_more_reads.legal_status
list_receipts = _rep_more_reads.list_receipts
wallet_stats = _rep_more_reads.wallet_stats
activity = _rep_more_reads.activity
search_profiles = _rep_more_reads.search_profiles
caller_league = _rep_more_reads.caller_league
dm_inbox = _rep_more_reads.dm_inbox
rewards = _rep_more_reads.rewards
rewards_board = _rep_more_reads.rewards_board
wallet_pnl = _rep_more_reads.wallet_pnl
familia_my_money = _rep_more_reads.familia_my_money
trust_batch = _rep_more_reads.trust_batch
trust_score = _rep_more_reads.trust_score
wallet_standing = _rep_more_reads.wallet_standing
gas_check = _rep_more_reads.gas_check
token_search = _rep_more_reads.token_search
position = _rep_more_reads.position
trade_cards = _rep_more_reads.trade_cards
shield_leaderboard = _rep_more_reads.shield_leaderboard
launch_check = _rep_more_reads.launch_check
token_logo = _rep_more_reads.token_logo
wallet_dust_solana = _rep_more_reads.wallet_dust_solana
wallet_dust_cronos = _rep_more_reads.wallet_dust_cronos
wallet_dust_evm = _rep_more_reads.wallet_dust_evm

import rep_more_writes as _rep_more_writes   # noqa: E402  🧩 SITE-5: plain write routes, moved by scripts/move-routes.py
app.include_router(_rep_more_writes.router)
observe = _rep_more_writes.observe
watch_creator = _rep_more_writes.watch_creator
unwatch_creator = _rep_more_writes.unwatch_creator
roadmap_vote = _rep_more_writes.roadmap_vote
register_feeless_launch = _rep_more_writes.register_feeless_launch
push_subscribe = _rep_more_writes.push_subscribe
push_unsubscribe = _rep_more_writes.push_unsubscribe
push_test = _rep_more_writes.push_test
register_call = _rep_more_writes.register_call
react = _rep_more_writes.react
set_featured_badges = _rep_more_writes.set_featured_badges
x_oauth_start = _rep_more_writes.x_oauth_start
add_to_blocklist = _rep_more_writes.add_to_blocklist
internal_notify = _rep_more_writes.internal_notify
fee_post = _rep_more_writes.fee_post
fuses_preview = _rep_more_writes.fuses_preview
fuse_guard = _rep_more_writes.fuse_guard
fuse_mode = _rep_more_writes.fuse_mode
fuse_auto_yield = _rep_more_writes.fuse_auto_yield
fuse_freeze = _rep_more_writes.fuse_freeze
fuse_coin_mode = _rep_more_writes.fuse_coin_mode
bracket_pick = _rep_more_writes.bracket_pick
battle_back = _rep_more_writes.battle_back
social_feed_react = _rep_more_writes.social_feed_react
crew_switch = _rep_more_writes.crew_switch
crew_join = _rep_more_writes.crew_join
familia_broker_keys = _rep_more_writes.familia_broker_keys
familia_broker_order = _rep_more_writes.familia_broker_order
familia_broker_unlink = _rep_more_writes.familia_broker_unlink
familia_kalshi_order = _rep_more_writes.familia_kalshi_order
familia_paper_perps_act = _rep_more_writes.familia_paper_perps_act
internal_openrouter_check = _rep_more_writes.internal_openrouter_check
familia_perps_real_execute = _rep_more_writes.familia_perps_real_execute
familia_autorange_arm = _rep_more_writes.familia_autorange_arm
hq_pair_new = _rep_more_writes.hq_pair_new
hq_pair_connect = _rep_more_writes.hq_pair_connect
hq_pair_signed = _rep_more_writes.hq_pair_signed
hq_pair_sign = _rep_more_writes.hq_pair_sign
crew_leave = _rep_more_writes.crew_leave
rep_market_stake = _rep_more_writes.rep_market_stake
internal_agent_image = _rep_more_writes.internal_agent_image
internal_agent_bid = _rep_more_writes.internal_agent_bid
predict_pick = _rep_more_writes.predict_pick
alliances_act = _rep_more_writes.alliances_act
internal_sicario_want = _rep_more_writes.internal_sicario_want
fuse_best3 = _rep_more_writes.fuse_best3
quest_checkin = _rep_more_writes.quest_checkin
quest_event = _rep_more_writes.quest_event
report_bug = _rep_more_writes.report_bug
support_act = _rep_more_writes.support_act
presence_beat = _rep_more_writes.presence_beat
familia_street_typing = _rep_more_writes.familia_street_typing
legal_accept = _rep_more_writes.legal_accept
legal_export = _rep_more_writes.legal_export
track_click = _rep_more_writes.track_click
identity_link = _rep_more_writes.identity_link
chat_delete = _rep_more_writes.chat_delete
fuse_rounds = _rep_more_writes.fuse_rounds
chat_session = _rep_more_writes.chat_session
claim_referral = _rep_more_writes.claim_referral
ad_event = _rep_more_writes.ad_event
notifications_read = _rep_more_writes.notifications_read
dm_settings_set = _rep_more_writes.dm_settings_set
rewards_claim = _rep_more_writes.rewards_claim
wars_join = _rep_more_writes.wars_join
follow = _rep_more_writes.follow
edge_observe = _rep_more_writes.edge_observe
page_view = _rep_more_writes.page_view
shield_commit = _rep_more_writes.shield_commit
agent_pass_prepare = _rep_more_writes.agent_pass_prepare
agent_pass_confirm = _rep_more_writes.agent_pass_confirm
token_meta_create = _rep_more_writes.token_meta_create
rpc_relay = _rep_more_writes.rpc_relay
perf_report = _rep_more_writes.perf_report
internal_trade = _rep_more_writes.internal_trade
watch_set = _rep_more_writes.watch_set
verify_request = _rep_more_writes.verify_request
wallet_dust_close_tx = _rep_more_writes.wallet_dust_close_tx
internal_agent_circle_send = _rep_more_writes.internal_agent_circle_send
internal_agent_close_empty = _rep_more_writes.internal_agent_close_empty

import rep_admin_routes as _rep_admin_routes   # noqa: E402  🧩 SITE-5: admin routes, moved by scripts/move-routes.py
app.include_router(_rep_admin_routes.router)
upload_image = _rep_admin_routes.upload_image
save_profile = _rep_admin_routes.save_profile
chat_post = _rep_admin_routes.chat_post
alpha_rooms = _rep_admin_routes.alpha_rooms
admin_chat_guard = _rep_admin_routes.admin_chat_guard
fuses_evolve = _rep_admin_routes.fuses_evolve
admin_auto_yield_set = _rep_admin_routes.admin_auto_yield_set
fuse_position_switch = _rep_admin_routes.fuse_position_switch
fuse_limits = _rep_admin_routes.fuse_limits
fuse_hq_admin = _rep_admin_routes.fuse_hq_admin
fuse_hq_admin_save = _rep_admin_routes.fuse_hq_admin_save
social_feed_x = _rep_admin_routes.social_feed_x
crews_board = _rep_admin_routes.crews_board
crew_of_wallet = _rep_admin_routes.crew_of_wallet
admin_crews_revenue = _rep_admin_routes.admin_crews_revenue
admin_fees_crews = _rep_admin_routes.admin_fees_crews
familia_city = _rep_admin_routes.familia_city
familia_city_visit = _rep_admin_routes.familia_city_visit
familia_block = _rep_admin_routes.familia_block
admin_familia_overwatch = _rep_admin_routes.admin_familia_overwatch
admin_familia_rules_set = _rep_admin_routes.admin_familia_rules_set
familia_broker = _rep_admin_routes.familia_broker
familia_broker_link = _rep_admin_routes.familia_broker_link
familia_trade_center = _rep_admin_routes.familia_trade_center
familia_world_act = _rep_admin_routes.familia_world_act
cat_model_limit = _rep_admin_routes.cat_model_limit
familia_fuse_act = _rep_admin_routes.familia_fuse_act
crew_badge_catalog = _rep_admin_routes.crew_badge_catalog
fuse_wallet_recover_sell = _rep_admin_routes.fuse_wallet_recover_sell
fuse_wallet_coin_sell = _rep_admin_routes.fuse_wallet_coin_sell
fuse_wallet_recover_sell_all = _rep_admin_routes.fuse_wallet_recover_sell_all
fuse_wallet_cfg = _rep_admin_routes.fuse_wallet_cfg
admin_rpc_set = _rep_admin_routes.admin_rpc_set
admin_alliance_days = _rep_admin_routes.admin_alliance_days
admin_collective_look = _rep_admin_routes.admin_collective_look
admin_provider_key = _rep_admin_routes.admin_provider_key
admin_ai_key_set = _rep_admin_routes.admin_ai_key_set
admin_ai_seat_post = _rep_admin_routes.admin_ai_seat_post
admin_ai_providers_set = _rep_admin_routes.admin_ai_providers_set
admin_ai_ask = _rep_admin_routes.admin_ai_ask
admin_ai_test = _rep_admin_routes.admin_ai_test
admin_ai_load = _rep_admin_routes.admin_ai_load
admin_agent_slots_set = _rep_admin_routes.admin_agent_slots_set
admin_ai_prompts_set = _rep_admin_routes.admin_ai_prompts_set
admin_ai_rig_preset = _rep_admin_routes.admin_ai_rig_preset
admin_ai_rig_set = _rep_admin_routes.admin_ai_rig_set
admin_ai_calls = _rep_admin_routes.admin_ai_calls
admin_ai_learned = _rep_admin_routes.admin_ai_learned
admin_ai_playground_make = _rep_admin_routes.admin_ai_playground_make
admin_ai_playground_decide = _rep_admin_routes.admin_ai_playground_decide
admin_ai_chat = _rep_admin_routes.admin_ai_chat
admin_ai_chat_clear = _rep_admin_routes.admin_ai_chat_clear
admin_ai_image = _rep_admin_routes.admin_ai_image
admin_ai_chat_open = _rep_admin_routes.admin_ai_chat_open
admin_ai_chat_saved = _rep_admin_routes.admin_ai_chat_saved
admin_ai_chat_settings = _rep_admin_routes.admin_ai_chat_settings
admin_ai_build = _rep_admin_routes.admin_ai_build
admin_ai_chat_remember = _rep_admin_routes.admin_ai_chat_remember
admin_ai_proposal_decide = _rep_admin_routes.admin_ai_proposal_decide
fuse_wallet_retry_dead = _rep_admin_routes.fuse_wallet_retry_dead
fuse_wallet_reinvest_paid = _rep_admin_routes.fuse_wallet_reinvest_paid
fuse_wallet_card = _rep_admin_routes.fuse_wallet_card
admin_data_cleaner = _rep_admin_routes.admin_data_cleaner
evolution_rollback = _rep_admin_routes.evolution_rollback
scenario_pick = _rep_admin_routes.scenario_pick
runners_autotune = _rep_admin_routes.runners_autotune
fuse_playground = _rep_admin_routes.fuse_playground
pg_sim_apply = _rep_admin_routes.pg_sim_apply
runners_pick_filter = _rep_admin_routes.runners_pick_filter
pg_battles_set = _rep_admin_routes.pg_battles_set
runners_cfg_set = _rep_admin_routes.runners_cfg_set
runners_force_round = _rep_admin_routes.runners_force_round
fuse_card_collection = _rep_admin_routes.fuse_card_collection
fuse_card_minted = _rep_admin_routes.fuse_card_minted
fuse_aura = _rep_admin_routes.fuse_aura
admin_vaults_save = _rep_admin_routes.admin_vaults_save
admin_quest_season = _rep_admin_routes.admin_quest_season
admin_quests_save = _rep_admin_routes.admin_quests_save
admin_quests_grant = _rep_admin_routes.admin_quests_grant
wallet_badges = _rep_admin_routes.wallet_badges
admin_whoami = _rep_admin_routes.admin_whoami
badge_awards_admin_get = _rep_admin_routes.badge_awards_admin_get
admin_award = _rep_admin_routes.admin_award
admin_revoke = _rep_admin_routes.admin_revoke
admin_airdrops = _rep_admin_routes.admin_airdrops
admin_schedule = _rep_admin_routes.admin_schedule
admin_airdrop_status = _rep_admin_routes.admin_airdrop_status
admin_bug_status = _rep_admin_routes.admin_bug_status
admin_support_poll = _rep_admin_routes.admin_support_poll
admin_security = _rep_admin_routes.admin_security
familia_street = _rep_admin_routes.familia_street
familia_street_mod = _rep_admin_routes.familia_street_mod
admin_defence_lift = _rep_admin_routes.admin_defence_lift
admin_war_room = _rep_admin_routes.admin_war_room
admin_war_evidence = _rep_admin_routes.admin_war_evidence
legal_admin = _rep_admin_routes.legal_admin
legal_admin_save = _rep_admin_routes.legal_admin_save
admin_guard_decide = _rep_admin_routes.admin_guard_decide
contract_golive_set = _rep_admin_routes.contract_golive_set
admin_holder_ages = _rep_admin_routes.admin_holder_ages
admin_snapshot = _rep_admin_routes.admin_snapshot
admin_snapshot_diff = _rep_admin_routes.admin_snapshot_diff
admin_grow_detail = _rep_admin_routes.admin_grow_detail
admin_py_agents_ask = _rep_admin_routes.admin_py_agents_ask
fee_pricing = _rep_admin_routes.fee_pricing
admin_fees_prepay = _rep_admin_routes.admin_fees_prepay
admin_fees_bundle = _rep_admin_routes.admin_fees_bundle
admin_fees_rounds = _rep_admin_routes.admin_fees_rounds
admin_fees_house = _rep_admin_routes.admin_fees_house
admin_fee_earnings = _rep_admin_routes.admin_fee_earnings
shield_admin = _rep_admin_routes.shield_admin
shield_admin_set = _rep_admin_routes.shield_admin_set
admin_fees_set = _rep_admin_routes.admin_fees_set
admin_referrals = _rep_admin_routes.admin_referrals
admin_referral_cfg = _rep_admin_routes.admin_referral_cfg
admin_ad_save = _rep_admin_routes.admin_ad_save
admin_ad_delete = _rep_admin_routes.admin_ad_delete
admin_pulse = _rep_admin_routes.admin_pulse
admin_chat_feed = _rep_admin_routes.admin_chat_feed
admin_delete_msg = _rep_admin_routes.admin_delete_msg
admin_mute = _rep_admin_routes.admin_mute
admin_feecat_get = _rep_admin_routes.admin_feecat_get
admin_feecat_set = _rep_admin_routes.admin_feecat_set
dm_send = _rep_admin_routes.dm_send
admin_verify = _rep_admin_routes.admin_verify
admin_site = _rep_admin_routes.admin_site
theme_get = _rep_admin_routes.theme_get
looks_catalog = _rep_admin_routes.looks_catalog
theme_set = _rep_admin_routes.theme_set
admin_kol_add = _rep_admin_routes.admin_kol_add
admin_kol_remove = _rep_admin_routes.admin_kol_remove
admin_traffic = _rep_admin_routes.admin_traffic
admin_season_upsert = _rep_admin_routes.admin_season_upsert
admin_role_grant = _rep_admin_routes.admin_role_grant
admin_role_revoke = _rep_admin_routes.admin_role_revoke
admin_idea_add = _rep_admin_routes.admin_idea_add
admin_season_edit = _rep_admin_routes.admin_season_edit
admin_season_delete = _rep_admin_routes.admin_season_delete
is_admin = _rep_admin_routes.is_admin
local_update = _rep_admin_routes.local_update
routes_set = _rep_admin_routes.routes_set
launch_costs_set = _rep_admin_routes.launch_costs_set
launch_tab_set = _rep_admin_routes.launch_tab_set
coin_profile_set = _rep_admin_routes.coin_profile_set
pump_create_tx = _rep_admin_routes.pump_create_tx
pools_register = _rep_admin_routes.pools_register
admin_token_logo = _rep_admin_routes.admin_token_logo
admin_marketing = _rep_admin_routes.admin_marketing
admin_badge_pool_save = _rep_admin_routes.admin_badge_pool_save
admin_badge_pool_delete = _rep_admin_routes.admin_badge_pool_delete
perf_config_set = _rep_admin_routes.perf_config_set
perf_code_health_queue = _rep_admin_routes.perf_code_health_queue
perf_code_health_scan = _rep_admin_routes.perf_code_health_scan
treasury_money = _rep_admin_routes.treasury_money
verify_admin = _rep_admin_routes.verify_admin
verify_admin_list = _rep_admin_routes.verify_admin_list
admin_badge_edit = _rep_admin_routes.admin_badge_edit
nft_home = _rep_admin_routes.nft_home
nft_create = _rep_admin_routes.nft_create
nft_onchain = _rep_admin_routes.nft_onchain
nft_drop = _rep_admin_routes.nft_drop
intel_desk_sweep = _rep_admin_routes.intel_desk_sweep
admin_card_edit = _rep_admin_routes.admin_card_edit
circle_destination_save = _rep_admin_routes.circle_destination_save

import rep_money_routes as _rep_money_routes   # noqa: E402  🧩 SITE-5: money routes, moved by scripts/move-routes.py
app.include_router(_rep_money_routes.router)
fuse_position = _rep_money_routes.fuse_position
fuse_receipt = _rep_money_routes.fuse_receipt
fuse_position_close = _rep_money_routes.fuse_position_close
fuse_plan = _rep_money_routes.fuse_plan
admin_fuse_payout_plan = _rep_money_routes.admin_fuse_payout_plan
admin_fuse_payout_paid = _rep_money_routes.admin_fuse_payout_paid
admin_fuse_rules_set = _rep_money_routes.admin_fuse_rules_set
fuse_receipts = _rep_money_routes.fuse_receipts
fuse_pnl = _rep_money_routes.fuse_pnl
familia_kalshi_send = _rep_money_routes.familia_kalshi_send
familia_pools = _rep_money_routes.familia_pools
cat_fund_build = _rep_money_routes.cat_fund_build
cat_withdraw = _rep_money_routes.cat_withdraw
cat_fund_send = _rep_money_routes.cat_fund_send
familia_pools_earn = _rep_money_routes.familia_pools_earn
familia_perps_real_build = _rep_money_routes.familia_perps_real_build
familia_pools_ranges = _rep_money_routes.familia_pools_ranges
familia_pools_run = _rep_money_routes.familia_pools_run
familia_leverage_build = _rep_money_routes.familia_leverage_build
fuse_prime_admin = _rep_money_routes.fuse_prime_admin
circle_profile_save = _rep_money_routes.circle_profile_save
fuse_wallet_view = _rep_money_routes.fuse_wallet_view
admin_colony_set = _rep_money_routes.admin_colony_set
fuse_wallet_preview = _rep_money_routes.fuse_wallet_preview
fuse_wallet_topup = _rep_money_routes.fuse_wallet_topup
fuse_wallet_payout_profit = _rep_money_routes.fuse_wallet_payout_profit
fuse_wallet_close_dust = _rep_money_routes.fuse_wallet_close_dust
fuse_wallet_withdraw_cash = _rep_money_routes.fuse_wallet_withdraw_cash
admin_agents_stream = _rep_money_routes.admin_agents_stream
admin_agents_set = _rep_money_routes.admin_agents_set
fuse_verdict_act = _rep_money_routes.fuse_verdict_act
fuse_buy = _rep_money_routes.fuse_buy
admin_fuses_save = _rep_money_routes.admin_fuses_save
vaults_list = _rep_money_routes.vaults_list
admin_war_trace = _rep_money_routes.admin_war_trace
war_bounty_report = _rep_money_routes.war_bounty_report
internal_legal_gate = _rep_money_routes.internal_legal_gate
legal_delete = _rep_money_routes.legal_delete
fee_quote = _rep_money_routes.fee_quote
internal_agent_fee = _rep_money_routes.internal_agent_fee
admin_collective_set = _rep_money_routes.admin_collective_set
admin_fee_health = _rep_money_routes.admin_fee_health
admin_fee_selftest = _rep_money_routes.admin_fee_selftest
admin_broadcast = _rep_money_routes.admin_broadcast
shop_buy = _rep_money_routes.shop_buy
helius_webhook = _rep_money_routes.helius_webhook
launch_rail_set = _rep_money_routes.launch_rail_set
circle_create_wallet = _rep_money_routes.circle_create_wallet
admin_reserve_paid = _rep_money_routes.admin_reserve_paid
admin_reserve_pay_circle = _rep_money_routes.admin_reserve_pay_circle
admin_badge_pool_pay_circle = _rep_money_routes.admin_badge_pool_pay_circle
admin_badge_pools = _rep_money_routes.admin_badge_pools
admin_badge_pool_paid = _rep_money_routes.admin_badge_pool_paid
treasury_split_record = _rep_money_routes.treasury_split_record
cards_of = _rep_money_routes.cards_of
circle_wallet_meta = _rep_money_routes.circle_wallet_meta
circle_transfer = _rep_money_routes.circle_transfer
internal_agent_x402_pay = _rep_money_routes.internal_agent_x402_pay
internal_agent_circle_wallet = _rep_money_routes.internal_agent_circle_wallet
fuse_feeders = _rep_money_routes.fuse_feeders
arena_loadout = _rep_money_routes.arena_loadout
arena_start = _rep_money_routes.arena_start
arena_result = _rep_money_routes.arena_result
coin_whos_in = _rep_money_routes.coin_whos_in
edge_memory = _rep_money_routes.edge_memory
admin_numbers = _rep_money_routes.admin_numbers

import rep_ai as _rep_ai   # noqa: E402  🧹 moved by scripts/move-section.py
_ai_book = _rep_ai._ai_book
_ai_quote = _rep_ai._ai_quote
_ai_brief = _rep_ai._ai_brief
_ai_learn_note = _rep_ai._ai_learn_note
_ai_learn_settle = _rep_ai._ai_learn_settle
_ai_exit_settle = _rep_ai._ai_exit_settle
_ai_weights = _rep_ai._ai_weights
_ai_learn_on = _rep_ai._ai_learn_on
_ai_exit_book = _rep_ai._ai_exit_book
_ai_exit_effects = _rep_ai._ai_exit_effects
_chart_widen_note = _rep_ai._chart_widen_note
_ai_exit_words = _rep_ai._ai_exit_words
_ai_log = _rep_ai._ai_log
_ai_cfg = _rep_ai._ai_cfg
_ai_http = _rep_ai._ai_http
_ai_view = _rep_ai._ai_view
_ai_jobs = _rep_ai._ai_jobs
_ai_signals = _rep_ai._ai_signals
_ai_conflict = _rep_ai._ai_conflict
_ai_ambiguous = _rep_ai._ai_ambiguous
_ai_learned = _rep_ai._ai_learned
_ai_owner = _rep_ai._ai_owner
_agent_pred = _rep_ai._agent_pred
_ai_snap = _rep_ai._ai_snap
_ai_case = _rep_ai._ai_case
_feecat_packet = _rep_ai._feecat_packet
_feecat_duo = _rep_ai._feecat_duo
_dv_note = _rep_ai._dv_note
_dv_settle = _rep_ai._dv_settle
_g4_fate = _rep_ai._g4_fate
_g4_state = _rep_ai._g4_state
_g4_qwen = _rep_ai._g4_qwen
_g4_real_record = _rep_ai._g4_real_record
_g4_lessons = _rep_ai._g4_lessons
_duo_push = _rep_ai._duo_push
_g4_review = _rep_ai._g4_review
_feecat_duo_safe = _rep_ai._feecat_duo_safe
_g4_tick = _rep_ai._g4_tick
_g4_idle = _rep_ai._g4_idle
_reaper_partner = _rep_ai._reaper_partner
_pred_of = _rep_ai._pred_of
_duo_backed = _rep_ai._duo_backed
_agent_entry_ok = _rep_ai._agent_entry_ok
_g4_brake = _rep_ai._g4_brake
_g4_picks_only = _rep_ai._g4_picks_only
_g4_bad_entry = _rep_ai._g4_bad_entry
_g4_view = _rep_ai._g4_view
_ai_stall_watch = _rep_ai._ai_stall_watch
_ai_round = _rep_ai._ai_round
_lw_note = _rep_ai._lw_note
_local_lane_pick = _rep_ai._local_lane_pick
_duet_second = _rep_ai._duet_second
_exit_second = _rep_ai._exit_second
_local_lane_run = _rep_ai._local_lane_run
_ai_keep = _rep_ai._ai_keep
_ai_gate = _rep_ai._ai_gate
_ai_pause = _rep_ai._ai_pause
_g4_loop = _rep_ai._g4_loop
_ai_loop = _rep_ai._ai_loop
_ai_general_context = _rep_ai._ai_general_context
_brain_load = _rep_ai._brain_load
_chat_persist = _rep_ai._chat_persist
_chat_extra = _rep_ai._chat_extra
_chat_props = _rep_ai._chat_props
_chat_context = _rep_ai._chat_context
_chat_olds = _rep_ai._chat_olds
_ai_proposal_apply = _rep_ai._ai_proposal_apply
_rig_apply = _rep_ai._rig_apply
_lms_reload = _rep_ai._lms_reload
_lms_states = _rep_ai._lms_states
_mdk_cached = _rep_ai._mdk_cached
_mdk_lms = _rep_ai._mdk_lms
_mdk_mcp = _rep_ai._mdk_mcp
_model_desk_view = _rep_ai._model_desk_view
_studio_apply = _rep_ai._studio_apply
_studio_lms = _rep_ai._studio_lms
_studio_trades = _rep_ai._studio_trades
_studio_core = _rep_ai._studio_core
_studio_auto = _rep_ai._studio_auto
_studio_auto_safe = _rep_ai._studio_auto_safe
_studio_layer = _rep_ai._studio_layer
_studio_view = _rep_ai._studio_view
_studio_fee = _rep_ai._studio_fee
_colony_value = _rep_ai._colony_value
_colony_view = _rep_ai._colony_view
_pool_tokens = _rep_ai._pool_tokens
_colony_pool_build = _rep_ai._colony_pool_build
_chat_syms = _rep_ai._chat_syms
_chat_coin = _rep_ai._chat_coin
_owner_brief = _rep_ai._owner_brief
_chat_evidence = _rep_ai._chat_evidence
_chat_learned = _rep_ai._chat_learned
_chat_image = _rep_ai._chat_image
_build_state = _rep_ai._build_state
_rpc_quota_notice = _rep_ai._rpc_quota_notice
_agents_loop = _rep_ai._agents_loop
_fuse_warm_loop = _rep_ai._fuse_warm_loop
_data_clean = _rep_ai._data_clean
_intel_save = _rep_ai._intel_save
_intel_restore = _rep_ai._intel_restore
_lc_book = _rep_ai._lc_book
_lc_shadows = _rep_ai._lc_shadows
_lc_shadows_raw = _rep_ai._lc_shadows_raw
_evo_view = _rep_ai._evo_view
_lifecycle = _rep_ai._lifecycle
_lc_evaluate = _rep_ai._lc_evaluate
_rounds_state = _rep_ai._rounds_state
_judge_weights = _rep_ai._judge_weights
_paper_view = _rep_ai._paper_view
_kernel_view = _rep_ai._kernel_view
_edge_rules = _rep_ai._edge_rules
_edge_view = _rep_ai._edge_view
_kernel_ctx = _rep_ai._kernel_ctx
_owner_book = _rep_ai._owner_book
_owner_view = _rep_ai._owner_view
_owner_resolve = _rep_ai._owner_resolve
_owner_act = _rep_ai._owner_act
_tape_flush = _rep_ai._tape_flush
_tape_ledger = _rep_ai._tape_ledger
_tape_reaper = _rep_ai._tape_reaper
_kernel_pass = _rep_ai._kernel_pass
_rounds_pass = _rep_ai._rounds_pass
_shadow_cost = _rep_ai._shadow_cost
_st_med = _rep_ai._st_med
_shadow_book = _rep_ai._shadow_book
_shadow_px = _rep_ai._shadow_px
_shadow_note = _rep_ai._shadow_note
_shadow_controls = _rep_ai._shadow_controls
_shadow_real_buys = _rep_ai._shadow_real_buys
_shadow_settle = _rep_ai._shadow_settle
_shadow_flush = _rep_ai._shadow_flush
_dial_lab = _rep_ai._dial_lab
_desk_stats_view = _rep_ai._desk_stats_view
_night_check = _rep_ai._night_check
_real_trades = _rep_ai._real_trades
_after_step = _rep_ai._after_step
_trail_view = _rep_ai._trail_view
_capital_view = _rep_ai._capital_view
_real_mem = _rep_ai._real_mem
_coach_state = _rep_ai._coach_state
_coach_put = _rep_ai._coach_put
_coach_pens = _rep_ai._coach_pens
_coach_view = _rep_ai._coach_view
_trade_tape = _rep_ai._trade_tape
_coach_grade = _rep_ai._coach_grade
_teach_state = _rep_ai._teach_state
_taught_rules = _rep_ai._taught_rules
_taught_stamp = _rep_ai._taught_stamp
_taught_view = _rep_ai._taught_view
_regret_book = _rep_ai._regret_book
_regret_note = _rep_ai._regret_note
_regret_limits = _rep_ai._regret_limits
_regret_tick = _rep_ai._regret_tick
_lab_state = _rep_ai._lab_state
_lab_tick = _rep_ai._lab_tick
_lab_view = _rep_ai._lab_view
_coach_ai = _rep_ai._coach_ai
_germ_rebuy_step = _rep_ai._germ_rebuy_step
_germ_of = _rep_ai._germ_of
_agent_blocked = _rep_ai._agent_blocked
_g4_blocked = _rep_ai._g4_blocked
_seat_refusals = _rep_ai._seat_refusals
_seat_precheck = _rep_ai._seat_precheck
_agents_tick = _rep_ai._agents_tick
_arch_verify = _rep_ai._arch_verify
_deep_bucket = _rep_ai._deep_bucket
_office_candles = _rep_ai._office_candles
_mkt_view = _rep_ai._mkt_view
_office_vels = _rep_ai._office_vels
_live_px = _rep_ai._live_px
_wake_note = _rep_ai._wake_note
_market_wake = _rep_ai._market_wake
_office_candle_refresh = _rep_ai._office_candle_refresh
_intake_reg = _rep_ai._intake_reg
_intake_dex = _rep_ai._intake_dex
_intake_pass = _rep_ai._intake_pass
_intake_after = _rep_ai._intake_after
_intake_view = _rep_ai._intake_view
_office_seat_payload = _rep_ai._office_seat_payload
_office_cycle_log = _rep_ai._office_cycle_log
_office_fresh = _rep_ai._office_fresh
_office_load_pass = _rep_ai._office_load_pass
_social_cache = _rep_ai._social_cache
_social_flush = _rep_ai._social_flush
_research_tick = _rep_ai._research_tick
_seat_wake_maybe = _rep_ai._seat_wake_maybe
_office_state = _rep_ai._office_state
_office_lat = _rep_ai._office_lat
_office_ledger = _rep_ai._office_ledger
_office_real = _rep_ai._office_real
_office_ctx = _rep_ai._office_ctx
_office_warden = _rep_ai._office_warden
_office_reap = _rep_ai._office_reap
_office_chart_view = _rep_ai._office_chart_view
_office_bars = _rep_ai._office_bars
_office_positions = _rep_ai._office_positions
_hub_publish = _rep_ai._hub_publish
_net_stats = _rep_ai._net_stats
_office_light = _rep_ai._office_light
_office_pass = _rep_ai._office_pass
_agents_real = _rep_ai._agents_real
_kernel_row = _rep_ai._kernel_row
_agent_inherit_rows = _rep_ai._agent_inherit_rows
_agents_go_rows = _rep_ai._agents_go_rows
_agents_snapshot = _rep_ai._agents_snapshot
_duo_tape = _rep_ai._duo_tape
_duo_totals = _rep_ai._duo_totals
_duo_rooms = _rep_ai._duo_rooms
_duo_holding = _rep_ai._duo_holding
_duo_card_legs = _rep_ai._duo_card_legs
_duo_coin_rooms = _rep_ai._duo_coin_rooms
_duo_pin_cap = _rep_ai._duo_pin_cap
_duo_cap = _rep_ai._duo_cap
_duo_phase = _rep_ai._duo_phase
_duo_view = _rep_ai._duo_view
_agents_page_dict = _rep_ai._agents_page_dict
_agents_page_body = _rep_ai._agents_page_body
_fuse_warm = _rep_ai._fuse_warm
_round_move = _rep_ai._round_move
_scenario_stage = _rep_ai._scenario_stage
_pg_pick_ok = _rep_ai._pg_pick_ok
_engine_auto = _rep_ai._engine_auto
_engine_nudge = _rep_ai._engine_nudge
_top_anchor = _rep_ai._top_anchor
_pg_scenario_cards = _rep_ai._pg_scenario_cards
_pg_battle_view = _rep_ai._pg_battle_view
_pg_battle_tick = _rep_ai._pg_battle_tick
_edge_load = _rep_ai._edge_load
_pg_sim_tick = _rep_ai._pg_sim_tick
_brain_patch = _rep_ai._brain_patch
_engine_self_fix = _rep_ai._engine_self_fix
_verdict_acts = _rep_ai._verdict_acts
_retired = _rep_ai._retired
_verdict_build = _rep_ai._verdict_build
_verdict_tick = _rep_ai._verdict_tick

import rep_hq as _rep_hq   # noqa: E402  🧹 moved by scripts/move-section.py
_admin_wallets = _rep_hq._admin_wallets
_admin_load = _rep_hq._admin_load
_badge_limits = _rep_hq._badge_limits
_admin_save = _rep_hq._admin_save
_cached_json = _rep_hq._cached_json
_json_cost_note = _rep_hq._json_cost_note
_json_load = _rep_hq._json_load
_json_save = _rep_hq._json_save
_json_save_soft = _rep_hq._json_save_soft
_guard_save = _rep_hq._guard_save
_def_save = _rep_hq._def_save
_war_save = _rep_hq._war_save
_role_of = _rep_hq._role_of
_role_gate = _rep_hq._role_gate
_audit = _rep_hq._audit
_token_holders = _rep_hq._token_holders
_bug_key = _rep_hq._bug_key
_bug_seen = _rep_hq._bug_seen
_street_fams = _rep_hq._street_fams
_legal_save = _rep_hq._legal_save
_legal_me = _rep_hq._legal_me
_legal_hold = _rep_hq._legal_hold
_legal_parts = _rep_hq._legal_parts
_legal_wipe = _rep_hq._legal_wipe

import rep_predict as _rep_predict   # noqa: E402  🧹 moved by scripts/move-section.py
_predict_symbols = _rep_predict._predict_symbols
_rm_rows = _rep_predict._rm_rows
_rm_tick = _rep_predict._rm_tick
_rep_of = _rep_predict._rep_of
_predict_tick = _rep_predict._predict_tick
_owner_edge_rec = _rep_predict._owner_edge_rec
_is_keeper = _rep_predict._is_keeper
_prime_tick = _rep_predict._prime_tick
_prime_bell_loop = _rep_predict._prime_bell_loop
_smart_track = _rep_predict._smart_track
_smart_on = _rep_predict._smart_on
_learn_drops = _rep_predict._learn_drops
_real_table = _rep_predict._real_table
_flow_fetch = _rep_predict._flow_fetch
_flow_mark = _rep_predict._flow_mark
_flow_intel = _rep_predict._flow_intel
_consig_plans = _rep_predict._consig_plans
_reaper_lines = _rep_predict._reaper_lines
_flow_guard = _rep_predict._flow_guard
_flow_settle = _rep_predict._flow_settle
_limit_check = _rep_predict._limit_check
_real_guard_loop = _rep_predict._real_guard_loop
_fw_market_rows = _rep_predict._fw_market_rows
_prime_unique_fix = _rep_predict._prime_unique_fix
_cook_warn = _rep_predict._cook_warn
_real_hold_fix = _rep_predict._real_hold_fix
_real_ride_fix = _rep_predict._real_ride_fix
_ladder_keep_fix = _rep_predict._ladder_keep_fix
degen_patch_1009 = _rep_predict.degen_patch_1009
_degen_fix_1009 = _rep_predict._degen_fix_1009
overnight_patch_1009 = _rep_predict.overnight_patch_1009
_overnight_fix_1009 = _rep_predict._overnight_fix_1009
hunt_patch_1009 = _rep_predict.hunt_patch_1009
_hunt_fix_1009 = _rep_predict._hunt_fix_1009
_hunt_fix_1009b = _rep_predict._hunt_fix_1009b
trench_patch_1009 = _rep_predict.trench_patch_1009
_trench_fix_1009 = _rep_predict._trench_fix_1009
_procall_fix_1009 = _rep_predict._procall_fix_1009
_topseat_fix_1009 = _rep_predict._topseat_fix_1009
_trench_safe_fix_1009 = _rep_predict._trench_safe_fix_1009
_clean_fix_1009 = _rep_predict._clean_fix_1009
_flow_tight_fix_1009 = _rep_predict._flow_tight_fix_1009
_entry_fix_1009 = _rep_predict._entry_fix_1009
_vital_off_fix_1009 = _rep_predict._vital_off_fix_1009
_moon_fix_1009 = _rep_predict._moon_fix_1009
_floor_fix_1009 = _rep_predict._floor_fix_1009
_flow_fix_1009 = _rep_predict._flow_fix_1009
_proof_gate_tick = _rep_predict._proof_gate_tick
_proof_gate_fix_1010 = _rep_predict._proof_gate_fix_1010
_proof_clean_1013 = _rep_predict._proof_clean_1013
_agent_open_fix_1012 = _rep_predict._agent_open_fix_1012
_agent_real_fix_1012 = _rep_predict._agent_real_fix_1012
_trail_fix_1014 = _rep_predict._trail_fix_1014
_curve_fix_1011 = _rep_predict._curve_fix_1011
_g4seat_fix_1016 = _rep_predict._g4seat_fix_1016
_youticket_fix_1016 = _rep_predict._youticket_fix_1016
_germline_fix_1016 = _rep_predict._germline_fix_1016
_mcfloor_fix_1016 = _rep_predict._mcfloor_fix_1016
_minage_fix_1014 = _rep_predict._minage_fix_1014
_armed_fix_1013 = _rep_predict._armed_fix_1013
_agent_control_set = _rep_predict._agent_control_set
_desk_buys_fix_1105 = _rep_predict._desk_buys_fix_1105
_agent_control_fix_1010 = _rep_predict._agent_control_fix_1010
_agent_duty_fix_1010 = _rep_predict._agent_duty_fix_1010
_keephalf_fix_1010 = _rep_predict._keephalf_fix_1010
_floor_off_fix_1009 = _rep_predict._floor_off_fix_1009
_night_off_fix_1017 = _rep_predict._night_off_fix_1017
_rush_fix_1009 = _rep_predict._rush_fix_1009
_volcycle_fix_1009 = _rep_predict._volcycle_fix_1009
_degen_crazy_fix_1009 = _rep_predict._degen_crazy_fix_1009
_agent_test_fix_1009 = _rep_predict._agent_test_fix_1009
_agent_learn_fix_1009 = _rep_predict._agent_learn_fix_1009
_agent_seat_fix_1009 = _rep_predict._agent_seat_fix_1009
_ticket_ride_fix = _rep_predict._ticket_ride_fix
_prime_reset_paper = _rep_predict._prime_reset_paper
_proven_candidates = _rep_predict._proven_candidates
_paper_broke = _rep_predict._paper_broke
_hq_ver = _rep_predict._hq_ver
_record_runs = _rep_predict._record_runs
_prime_reads = _rep_predict._prime_reads
_prime_resp_clear = _rep_predict._prime_resp_clear
_prime_resp_build = _rep_predict._prime_resp_build
_prime_snapshot = _rep_predict._prime_snapshot
_prime_warm = _rep_predict._prime_warm
_fuse_prime_build = _rep_predict._fuse_prime_build

import rep_crews as _rep_crews   # noqa: E402  🧹 moved by scripts/move-section.py
_crew_pieces = _rep_crews._crew_pieces
_crew_book = _rep_crews._crew_book
_crew_name = _rep_crews._crew_name
_seat_of = _rep_crews._seat_of
_crew_cfg = _rep_crews._crew_cfg
_crew_badge_usd = _rep_crews._crew_badge_usd
_crew_view = _rep_crews._crew_view
_pay_sig_used = _rep_crews._pay_sig_used
_pay_hold = _rep_crews._pay_hold
_verify_sol_payment = _rep_crews._verify_sol_payment
_verify_sol_payment_held = _rep_crews._verify_sol_payment_held
_city_ctx = _rep_crews._city_ctx
_city_rivals = _rep_crews._city_rivals
_city_tax = _rep_crews._city_tax
_fblock_wallets = _rep_crews._fblock_wallets
_fblock_reads = _rep_crews._fblock_reads
_fblock_ranges = _rep_crews._fblock_ranges
_fblock_view = _rep_crews._fblock_view
_cartels_now = _rep_crews._cartels_now
_world_target = _rep_crews._world_target
_world_settle = _rep_crews._world_settle
_familia_rules = _rep_crews._familia_rules
_world_tick = _rep_crews._world_tick
_world_metrics = _rep_crews._world_metrics
_fuse_family_stats = _rep_crews._fuse_family_stats
_world_feecat_rate = _rep_crews._world_feecat_rate
_world_view = _rep_crews._world_view
_kt_need = _rep_crews._kt_need
_kt_proof = _rep_crews._kt_proof
_kt_market = _rep_crews._kt_market
_kt_addr = _rep_crews._kt_addr
_brk_seal = _rep_crews._brk_seal
_brk_need = _rep_crews._brk_need
_brk_call = _rep_crews._brk_call
_brk_q = _rep_crews._brk_q
_brk_user = _rep_crews._brk_user
_brk_alpaca = _rep_crews._brk_alpaca
_alpaca_call = _rep_crews._alpaca_call
_brk_cdc = _rep_crews._brk_cdc
_cdc_call = _rep_crews._cdc_call
_cdc_dev_key = _rep_crews._cdc_dev_key
_cdc_instruments = _rep_crews._cdc_instruments
_pperp_board = _rep_crews._pperp_board
_arena_day = _rep_crews._arena_day
_tg_user = _rep_crews._tg_user
_tg_group = _rep_crews._tg_group
_arena_who = _rep_crews._arena_who
_arena_unlock_level = _rep_crews._arena_unlock_level
_arena_profile = _rep_crews._arena_profile
_ffuse_cards = _rep_crews._ffuse_cards
_ffuse_prices = _rep_crews._ffuse_prices
_ffuse_book = _rep_crews._ffuse_book
_ffuse_pay = _rep_crews._ffuse_pay
_ffuse_tick = _rep_crews._ffuse_tick
_ffuse_view = _rep_crews._ffuse_view
_cat_for_fund = _rep_crews._cat_for_fund
_cat_fund_rules = _rep_crews._cat_fund_rules
_openrouter_left = _rep_crews._openrouter_left
_vault_gap_read = _rep_crews._vault_gap_read
_pgap_once = _rep_crews._pgap_once
_coin_gap_read = _rep_crews._coin_gap_read
_jl_borrow = _rep_crews._jl_borrow
_jl_lend = _rep_crews._jl_lend
_jl_markets = _rep_crews._jl_markets
_jp_call = _rep_crews._jp_call
_rng_get = _rep_crews._rng_get
_collective_band_pass = _rep_crews._collective_band_pass
_autorange_watch = _rep_crews._autorange_watch
_lan_ip = _rep_crews._lan_ip
_hqp_site = _rep_crews._hqp_site
_wars_tick = _rep_crews._wars_tick
_crew_season_tick = _rep_crews._crew_season_tick
_crew_room_ok = _rep_crews._crew_room_ok

import rep_runners as _rep_runners   # noqa: E402  🧹 moved by scripts/move-section.py
_runner_cfg = _rep_runners._runner_cfg
_intel_boot = _rep_runners._intel_boot
_intel_fresh = _rep_runners._intel_fresh
_enrich_scan = _rep_runners._enrich_scan
_enrich_pump = _rep_runners._enrich_pump
_runner_intel = _rep_runners._runner_intel
_meme_tick = _rep_runners._meme_tick
_runner_live = _rep_runners._runner_live
_runner_live_build = _rep_runners._runner_live_build
_runner_track = _rep_runners._runner_track
_smart_buyers = _rep_runners._smart_buyers
_token_prices = _rep_runners._token_prices
_jup_prices = _rep_runners._jup_prices
_judge_fill = _rep_runners._judge_fill
_runner_tick = _rep_runners._runner_tick
_runner_loop = _rep_runners._runner_loop

import rep_seasons as _rep_seasons   # noqa: E402  🧹 moved by scripts/move-section.py
_season_rows = _rep_seasons._season_rows
_season_wins = _rep_seasons._season_wins
_fuse_season_tick = _rep_seasons._fuse_season_tick
_season_race = _rep_seasons._season_race
_series_24h = _rep_seasons._series_24h
_fuse_score = _rep_seasons._fuse_score
_bred_load = _rep_seasons._bred_load
_bred_tick = _rep_seasons._bred_tick
_fuse_autopilot_tick = _rep_seasons._fuse_autopilot_tick
_shield_alerts = _rep_seasons._shield_alerts
_fuse_autopilot_loop = _rep_seasons._fuse_autopilot_loop
_card_look = _rep_seasons._card_look
_fuse_chat = _rep_seasons._fuse_chat
_fuse_chat_tick = _rep_seasons._fuse_chat_tick
_battle_view = _rep_seasons._battle_view
_league_card = _rep_seasons._league_card
_league_extra = _rep_seasons._league_extra
_league_playground = _rep_seasons._league_playground
_arena_auto_refresh = _rep_seasons._arena_auto_refresh
_feecat_raw = _rep_seasons._feecat_raw
_feecat_card = _rep_seasons._feecat_card
_arena_mega = _rep_seasons._arena_mega
_card_dna_tag = _rep_seasons._card_dna_tag
_fuse_candidates = _rep_seasons._fuse_candidates
_champ_view = _rep_seasons._champ_view

import rep_fuse_wallet as _rep_fuse_wallet   # noqa: E402  🧹 moved by scripts/move-section.py
_parsed_info = _rep_fuse_wallet._parsed_info
_fw_load = _rep_fuse_wallet._fw_load
_fw_save = _rep_fuse_wallet._fw_save
_fw_peek = _rep_fuse_wallet._fw_peek
_fw_cfg = _rep_fuse_wallet._fw_cfg
_fw_signer_ready = _rep_fuse_wallet._fw_signer_ready
_fw_signer_check = _rep_fuse_wallet._fw_signer_check
_fw_sign = _rep_fuse_wallet._fw_sign
_fw_balances = _rep_fuse_wallet._fw_balances
_jup_keys = _rep_fuse_wallet._jup_keys
_jup_lanes = _rep_fuse_wallet._jup_lanes
_jup_lid = _rep_fuse_wallet._jup_lid
_jup_pick = _rep_fuse_wallet._jup_pick
_fw_jup = _rep_fuse_wallet._fw_jup
_fw_quote = _rep_fuse_wallet._fw_quote
_fw_secure_buy = _rep_fuse_wallet._fw_secure_buy
_fw_live_pairs = _rep_fuse_wallet._fw_live_pairs
_fw_preflight = _rep_fuse_wallet._fw_preflight
_fw_keep = _rep_fuse_wallet._fw_keep
_fw_kick_now = _rep_fuse_wallet._fw_kick_now
_fw_record = _rep_fuse_wallet._fw_record
_fw_execute = _rep_fuse_wallet._fw_execute
_fw_execute_swap = _rep_fuse_wallet._fw_execute_swap
_fw_notify = _rep_fuse_wallet._fw_notify
_fw_raw_keep = _rep_fuse_wallet._fw_raw_keep
_fw_rebroadcast = _rep_fuse_wallet._fw_rebroadcast
_fw_resolve = _rep_fuse_wallet._fw_resolve
_fw_catch_up = _rep_fuse_wallet._fw_catch_up
_fw_tick = _rep_fuse_wallet._fw_tick
_fw_deposit_scan = _rep_fuse_wallet._fw_deposit_scan
_fw_tick_inner = _rep_fuse_wallet._fw_tick_inner
_fw_rent_credit = _rep_fuse_wallet._fw_rent_credit
_fw_close_empty = _rep_fuse_wallet._fw_close_empty
_mint_decimals = _rep_fuse_wallet._mint_decimals
_paper_quote_audit = _rep_fuse_wallet._paper_quote_audit
_fw_calibration = _rep_fuse_wallet._fw_calibration
_fw_full_ledger = _rep_fuse_wallet._fw_full_ledger
_vs_cached = _rep_fuse_wallet._vs_cached
_fw_led_memo = _rep_fuse_wallet._fw_led_memo
_fw_public = _rep_fuse_wallet._fw_public
_circle_wallets_live = _rep_fuse_wallet._circle_wallets_live
_fw_reports = _rep_fuse_wallet._fw_reports
_fw_recover_sell = _rep_fuse_wallet._fw_recover_sell
_alliance_view = _rep_fuse_wallet._alliance_view

import rep_prime as _rep_prime   # noqa: E402  🧹 moved by scripts/move-section.py
_prime_cfg = _rep_prime._prime_cfg
_ladder_value = _rep_prime._ladder_value
_ladder_step = _rep_prime._ladder_step
_prime_real_cfg = _rep_prime._prime_real_cfg
_open_board = _rep_prime._open_board
_open_scan_judge = _rep_prime._open_scan_judge
_jup_judge = _rep_prime._jup_judge
_pump_calls_build = _rep_prime._pump_calls_build
_pc_rows = _rep_prime._pc_rows
_pump_callers_pass = _rep_prime._pump_callers_pass
_call_rush_alert = _rep_prime._call_rush_alert
_mint_rows = _rep_prime._mint_rows
_pump_call_rows = _rep_prime._pump_call_rows
_feeders_build = _rep_prime._feeders_build
_sf_read = _rep_prime._sf_read
_sf_refresh = _rep_prime._sf_refresh
_sf_receipts = _rep_prime._sf_receipts
_callout_tick = _rep_prime._callout_tick
_trench_build = _rep_prime._trench_build
_owner_study = _rep_prime._owner_study
_hint_grade = _rep_prime._hint_grade
_study_tick = _rep_prime._study_tick
_owner_moves_tick = _rep_prime._owner_moves_tick
_call_track = _rep_prime._call_track
_sendit_ready = _rep_prime._sendit_ready
_procall_track = _rep_prime._procall_track
_li_state = _rep_prime._li_state
_li_parts = _rep_prime._li_parts
_li_row = _rep_prime._li_row
_li_attach = _rep_prime._li_attach
_li_track = _rep_prime._li_track
_brain_track = _rep_prime._brain_track
_brain_clean = _rep_prime._brain_clean
_brain_state = _rep_prime._brain_state
_rush_rows = _rep_prime._rush_rows
_brain_ready = _rep_prime._brain_ready
_brain_rows = _rep_prime._brain_rows
_bottom_rows = _rep_prime._bottom_rows
_lens_track = _rep_prime._lens_track
_swapin_lists = _rep_prime._swapin_lists
_edge_rank = _rep_prime._edge_rank
_edge_track = _rep_prime._edge_track
_bs_rows = _rep_prime._bs_rows
feecat_pool_rows = _rep_prime.feecat_pool_rows
feecat_read = _rep_prime.feecat_read
duo_word = _rep_prime.duo_word
duo_lessons = _rep_prime.duo_lessons
_list_records = _rep_prime._list_records
_bottom_track = _rep_prime._bottom_track
_human_style = _rep_prime._human_style
_pick_style_note = _rep_prime._pick_style_note
_trench_judge = _rep_prime._trench_judge
_fuse_trench_raw = _rep_prime._fuse_trench_raw
_trench_row = _rep_prime._trench_row
_real_weather = _rep_prime._real_weather
_prime_cool_candidates = _rep_prime._prime_cool_candidates
_prime_candidates = _rep_prime._prime_candidates
_contenders_build = _rep_prime._contenders_build
_contenders_rebuild = _rep_prime._contenders_rebuild
_creator_state = _rep_prime._creator_state
_pick_verify = _rep_prime._pick_verify
_pick_row = _rep_prime._pick_row
_pick_why = _rep_prime._pick_why
_proof_build = _rep_prime._proof_build

import rep_coin_edge as _rep_coin_edge   # noqa: E402  🧹 moved by scripts/move-section.py
_edge_pulses = _rep_coin_edge._edge_pulses
_germ_rec = _rep_coin_edge._germ_rec
_edge_build = _rep_coin_edge._edge_build
_edge_refresh = _rep_coin_edge._edge_refresh
_feeback_book = _rep_coin_edge._feeback_book
_fuse_guard_tick = _rep_coin_edge._fuse_guard_tick
_card_signal_tick = _rep_coin_edge._card_signal_tick
_fuse_guard_loop = _rep_coin_edge._fuse_guard_loop
_hq_prices = _rep_coin_edge._hq_prices
_wallet_held = _rep_coin_edge._wallet_held
_arena_settle = _rep_coin_edge._arena_settle

import rep_fuse_hq as _rep_fuse_hq   # noqa: E402  🧹 moved by scripts/move-section.py
_prime_cards = _rep_fuse_hq._prime_cards
_real_card = _rep_fuse_hq._real_card
_card_rules = _rep_fuse_hq._card_rules
_ledger_by_sig = _rep_fuse_hq._ledger_by_sig
_card_fees = _rep_fuse_hq._card_fees
_exit_fee = _rep_fuse_hq._exit_fee
_fuse_yield_tick = _rep_fuse_hq._fuse_yield_tick
_fuse_swap_tick = _rep_fuse_hq._fuse_swap_tick
_spend_round = _rep_fuse_hq._spend_round
_rounds_out_notice = _rep_fuse_hq._rounds_out_notice
_fuse_buyback_tick = _rep_fuse_hq._fuse_buyback_tick
_fuse_leg_tick = _rep_fuse_hq._fuse_leg_tick

import rep_fuse as _rep_fuse   # noqa: E402  🧹 moved by scripts/move-section.py
_jup_tokens = _rep_fuse._jup_tokens
_fuse_pairs = _rep_fuse._fuse_pairs
_fuse_risky = _rep_fuse._fuse_risky
_fuse_view = _rep_fuse._fuse_view
_creator_warn = _rep_fuse._creator_warn
_fuse_discover_pairs = _rep_fuse._fuse_discover_pairs
_jup_lite = _rep_fuse._jup_lite
_cand_map = _rep_fuse._cand_map
_read_for = _rep_fuse._read_for
_up_vital = _rep_fuse._up_vital
_pump_links_put = _rep_fuse._pump_links_put
_pump_links_warm = _rep_fuse._pump_links_warm
_clean_rows = _rep_fuse._clean_rows
_holder_facts = _rep_fuse._holder_facts
_list_now = _rep_fuse._list_now
_with_tv = _rep_fuse._with_tv
_bangers = _rep_fuse._bangers
_wave_rows = _rep_fuse._wave_rows
_prebreak_rows = _rep_fuse._prebreak_rows
_prebreak_ready = _rep_fuse._prebreak_ready
_wave_ready = _rep_fuse._wave_ready
_exhale_rows = _rep_fuse._exhale_rows
_procall_rows = _rep_fuse._procall_rows
_live_movers = _rep_fuse._live_movers
_why_pair = _rep_fuse._why_pair
_why_build = _rep_fuse._why_build
_swap_clean = _rep_fuse._swap_clean
_fuses_discover_raw = _rep_fuse._fuses_discover_raw
_majors_rows = _rep_fuse._majors_rows
_is_admin_req = _rep_fuse._is_admin_req
