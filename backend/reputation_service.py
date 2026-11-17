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
import investigate   # noqa: F401  (read by rep_intel, rep_more_reads as rs.investigate)
import name_lock as _name_lock   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
import agent_deposit as _deposit   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
import collective_pool as _cpool   # noqa: F401  (read by rep_admin_reads, rep_admin_routes as rs._cpool)
import collective_stake as _stake   # noqa: F401  (read by rep_fees, rep_money_routes as rs._stake)
import collective_stash as _stash   # noqa: F401  (read by rep_* modules as rs._stash)
import looks as _looks   # 🎨 the site's looks: Plasma default, free + advanced (looks.py)   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
import reserve_pool   # noqa: F401  (read by rep_money_routes, rep_public_reads as rs.reserve_pool)
import perf   # noqa: F401  (read by rep_admin_reads, rep_core as rs.perf)
import verify   # noqa: F401  (read by rep_treasury as rs.verify)
import launch_meta   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
import fee_report   # noqa: F401  (read by rep_admin_reads, rep_more_reads as rs.fee_report)
import money_pulse   # noqa: F401  (read by rep_treasury as rs.money_pulse)
import badge_cards   # noqa: F401  (read by rep_admin_routes, rep_money_routes as rs.badge_cards)
import intel_desk   # noqa: F401  (read by rep_admin_reads, rep_more_reads as rs.intel_desk)
import nft_studio   # noqa: F401  (read by rep_admin_reads, rep_admin_routes as rs.nft_studio)
import coin_meta   # noqa: F401  (read by rep_market as rs.coin_meta)
from ecosystem import ecosystem_mints   # noqa: F401  (read by rep_ai, rep_chat as rs.ecosystem_mints)
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
import uuid   # noqa: F401  (read by rep_admin_routes, rep_chat as rs.uuid)
from pathlib import Path
import random   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
from typing import List, Optional

import httpx   # noqa: F401  (read by rep_admin_reads, rep_admin_routes as rs.httpx)
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


# ↪ moved to rep_core.py: _empty_store, _load


_store_dirty = {'on': False}


# ↪ moved to rep_core.py: _save, _store_flush, _store_flush_loop, _save_now, resolve_creator, _creator_key, resolve_funding_source, _push_feed


DUMP_MIN_AGE = 2 * 3600


# ↪ moved to rep_core.py: token_outcome, score_creator


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


# ↪ moved to rep_core.py: _hygiene


_market_cache: dict = {}
MARKET_TTL = 60


# ↪ moved to rep_core.py: fetch_token_markets, trust_verdict, _apply_markets, _refresh_all_markets


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


# ↪ moved to rep_core.py: _loop_lag_dump


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


# ↪ moved to rep_core.py: upload_cap


class UploadPayload(BaseModel):
    dataUrl: str


_upload_ip = _HITS('upload')


# ↪ moved to rep_core.py: _ip_hit


_IP_HIT_LOCAL: dict = {}


_intel_cache: dict = {}
_launch_facts: dict = {}   # mint → {creator, bundled, snipers, createSlot, historyComplete, at} — read once, kept on disk
_flag_hold: dict = {}      # mint → (at, {wallet: % held})
FLAG_HOLD_TTL = 900.0
LAUNCH_RETRY_SEC = 6 * 3600.0   # a launch read that could not reach the launch is tried again after 6h, not every 15-min re-scan
SIG_PAGES = 16   # (2026-10-18: 8 left 35% of busy launch coins unread — the agents traded them blind on bundles / snipers) launch facts: page back up to 8,000 txs to reach a coin's creation (read once per coin, kept on disk)
INTEL_TTL = 900   # holders re-read every 15 min (launch facts are read once): a re-scan is 4 calls. 2026-10-08: at 300s a ~100-coin board needed 1.3 calls/s of re-scans against a 0.5/s budget, so 184 of 200 feed coins (14 of 18 RUNNING ones) read 'not scanned yet' and nothing running could ever be bought
SYSTEM_PROGRAM = '11111111111111111111111111111111'


# ↪ moved to rep_core.py: _coin_card, _early_buy


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


# ↪ moved to rep_core.py: chain_rpc_url, _ping_chain, resolve_evm_creator


GLOBE_NETS = ['solana', 'ethereum', 'base', 'bsc', 'arbitrum', 'avalanche', 'polygon', 'sui', 'optimism', 'zksync', 'zora', 'cronos', 'unichain', 'worldchain']
GLOBE_MIN_MC = 1_000_000  # the globe shows a $1M+ tier and a $10M+ tier
_globe_cache = {'at': 0, 'data': None}


# ↪ moved to rep_core.py: _refresh_globe


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


# ↪ moved to rep_core.py: _any_agent_wallets


# ---- Web push alerts ---------------------------------------------------------
import base64   # noqa: F401  (read by rep_admin_routes, rep_ai as rs.base64)
import hashlib   # noqa: F401  (read by rep_admin_routes, rep_ai as rs.hashlib)
import hmac   # noqa: F401  (read by rep_money_routes, rep_more_reads as rs.hmac)

PUSH_PATH = DATA_DIR / 'push.json'
VAPID_PATH = DATA_DIR / 'vapid.json'
_push_lock = asyncio.Lock()
DEFAULT_RULES = {'up': 20, 'down': 15, 'move24h': 0, 'liqDrain': 30, 'volSpike': 4, 'feeRead': True, 'creatorFlag': True}
DEFAULT_PREFS = {'cooldownMin': 30, 'minLiquidity': 0, 'quietStart': None, 'quietEnd': None}


# ↪ moved to rep_core.py: _vapid, _push_load, _push_save, _sub_id


class PushSubscribe(BaseModel):
    subscription: dict
    watch: list = []
    prefs: dict = {}
    session: str = ''


# ↪ moved to rep_core.py: _push_prefs


class PushUnsubscribe(BaseModel):
    endpoint: str


# Where each watch rule's evidence comes from (shown under the alert in the inbox).
ALERT_SOURCE = {'up': 'Live price (DexScreener)', 'down': 'Live price (DexScreener)', 'volSpike': '5m vs 24h volume (DexScreener)',
                'feeRead': 'FeeCat entry rules', 'creatorFlag': 'FEELESS creator reputation'}


# ↪ moved to rep_core.py: _inbox_alert, _send_push


class PushTest(BaseModel):
    endpoint: str


# ↪ moved to rep_core.py: _in_quiet, _evaluate_alerts


@app.on_event('startup')
async def _start_push_watcher():
    _vapid()
    _LEAD.start(_evaluate_alerts)


# ---- Call Ledger: every coin posted in the Trenches, priced at the moment and tracked forever
CALLS_PATH = DATA_DIR / 'calls.json'
_calls_lock = asyncio.Lock()


# ↪ moved to rep_chat.py: _calls_load, _calls_save


class CallPayload(BaseModel):
    room: str
    messageId: str
    caller: str
    callerAddress: Optional[str] = None
    chain: str
    pairAddress: str
    ts: Optional[float] = None


FEED_CALL_POINTS = ((2, 50), (5, 150), (10, 400))


# ↪ moved to rep_chat.py: _award_feed_call, _record_feed_calls, _call_view, _refresh_calls


@app.on_event('startup')
async def _start_calls():
    _LEAD.start(_refresh_calls)


_board_cache: dict = {}


# ↪ moved to rep_chat.py: _build_caller_board


# ---- Chat reactions ------------------------------------------------------------
REACT_PATH = DATA_DIR / 'reactions.json'
REACTIONS = ['🔥', '🚀', '💎', '💀']
_react_lock = asyncio.Lock()


# ↪ moved to rep_chat.py: _react_load


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


# ↪ moved to rep_chat.py: _prof, _profiles_load, _safe_url, _clean_profile


class ProfileSave(BaseModel):
    address: str
    message: str = ''
    signature: str = ''
    session: str = ''    # the 7-day wallet session (signed once) replaces a per-save signature
    profile: dict
    target: Optional[str] = None


_verify_evm = _hq_auth.verify_evm            # 🔐 wallet signatures live in hq_auth.py (pure); the old names stay for callers + tests
_verify_solana = _hq_auth.verify_solana


# ↪ moved to rep_chat.py: _verify_wallet


class FeaturedBadgesIn(BaseModel):
    address: str
    session: str
    badges: list = []


# 𝕏 SIGN IN WITH X (owner 2026-10-26: "a true account link so they're actually signed in to X, not an API"): X's own OAuth 2.0 (PKCE). FEELESS asks
# only to read who you are (users.read), stores your verified @handle on your profile and keeps NO token. Needs the owner's X app: X_CLIENT_ID
# (+ X_CLIENT_SECRET for a confidential app) and the callback URL X_REDIRECT_URI (default PUBLIC_SITE_URL/api/reputation/x/oauth/callback).
_x_states: dict = {}


# ↪ moved to rep_chat.py: _x_redirect


# ---- Evidence-based blocklist of snipers and bundlers ----------------------------
BLOCK_PATH = DATA_DIR / 'blocklist.json'
_block_lock = asyncio.Lock()
AUTO_BLOCK_STRIKES = 3


# ↪ moved to rep_chat.py: _protected_wallets


_block_view = {'key': None, 'd': None}


# ↪ moved to rep_chat.py: _block_load


BLOCK_SAVE_SEC = 300   # scanner strikes only (a person's report + shutdown write at once): a 15 MB dump every minute was ~0.5s of blocked loop each
_block_dirty = {'on': False, 'at': 0.0}


# ↪ moved to rep_chat.py: _block_flush, _block_save, _is_blocked, _record_offenders


# ---- Funder graph: who bankrolls sniper/bundler wallets, so a serial funder gets caught even
# before their next puppet wallet snipes anything --------------------------------------------
FUNDERS_PATH = DATA_DIR / 'funders.json'
FUNDER_STRIKE_MINTS = 2   # a funder linked to offenders across 2+ different launches is a pattern
FUNDER_STRIKE_WALLETS = 3  # or has bankrolled 3+ distinct sniper/bundler wallets total
_funder_lock = asyncio.Lock()
_funder_resolved = set()  # offender wallets we've already traced (in-memory, this process)


# ↪ moved to rep_chat.py: _funders_load, _is_flagged_funder, _trace_funders, funder_lookup


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


# ↪ moved to rep_chat.py: _chat_load, _display_name, _room_mint, _holding_usd


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


# ↪ moved to rep_chat.py: _chat_message_to_sign, feeless_post, chat_system_post


ALPHA_ROOMS = [{'id': 'alpha-100', 'name': '$100 Club', 'minUsd': 100, 'icon': '🥉', 'vibe': 'First look at FeeCat calls + early meta chatter'},
               {'id': 'alpha-1k', 'name': '$1K Vault', 'minUsd': 1_000, 'icon': '🥈', 'vibe': 'Deeper calls, Shield intel, launch previews'},
               {'id': 'alpha-10k', 'name': '$10K Council', 'minUsd': 10_000, 'icon': '🥇', 'vibe': 'Council votes, pool-builder strategy, direct line to the team'},
               {'id': 'alpha-1m', 'name': '$1M Throne', 'minUsd': 1_000_000, 'icon': '👑', 'vibe': 'The throne room. Legends only.'}]
_ALPHA = {r['id']: r for r in ALPHA_ROOMS}


# ↪ moved to rep_chat.py: _fee_usd, _is_staff, _alpha_allowed


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


# ↪ moved to rep_chat.py: _norm, _spam_check, _guard_log, _track_pin


FEE_ADDRESS = 'FEE-LEADER-CAT'


class FeeCallPayload(BaseModel):
    chain: str = 'solana'
    pairAddress: str = ''
    text: str
    registerCall: bool = False
    room: str = ''   # 'wall' → Fee's own profile wall (meta talk); default is the coin's trenches room
    tokens: list = []   # coin cards to attach (wall reports)


INTERNAL_KEY_PATH = DATA_DIR / 'internal.key'


# ↪ moved to rep_chat.py: _internal_key


class InternalNotify(BaseModel):
    address: str = Field(..., max_length=64)
    kind: str = Field('cat', max_length=16)
    text: str = Field(..., max_length=400)
    url: str = Field('', max_length=200)
    once: str = Field('', max_length=80)


_badge_cache: dict = {}
# ↪ moved to rep_chat.py: _ecosystem_mints


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


import jup_audit as _ja   # noqa: F401  (read by rep_ai, rep_fuse as rs._ja)
_jup_facts: dict = {}   # mint → (at, jup_audit.facts) — Jupiter's audit for every listed coin (holder %, dev record, organic flow)
JUP_FACTS_TTL = 180


# ↪ moved to rep_fuse.py: _jup_lite, _cand_map, _read_for


_coin_read_cache: dict = {}   # mint → (at, read) — 15s


COIN_READ_JUP_SEC = 1.5   # coin-read p95 was 6.5s (perf_view 2026-10-17): Jupiter's public lane rate-limited, the header waited for it


import chart_wallets as _cw   # noqa: F401  (read by rep_ai, rep_more_reads as rs._cw)
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
import crowd as _crowd   # noqa: F401  (read by rep_coin_edge as rs._crowd)
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


# ↪ moved to rep_coin_edge.py: _crowd_build


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


import trench as _trench   # noqa: F401  (read by rep_ai, rep_fuse as rs._trench)

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


# ↪ moved to rep_prime.py: _sf_client


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


import confluence as _cf   # noqa: F401  (read by rep_predict, rep_prime as rs._cf)
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


# ↪ moved to rep_crews.py: familia_perps


_kalshi_cache: dict = {'at': 0.0, 'rows': {}}


# ↪ moved to rep_crews.py: familia_kalshi


# ⏱ KALSHI TRADES FROM THE WALLET (kalshi_trade.py — DFlow's tokenized Kalshi markets; Proof KYC; the wallet signs; FEELESS sends only what it built)
_kproof: dict = {}       # wallet → True (verified is cached; "not verified" never is)
_kmeta: dict = {}        # ticker / mint → (at, market | None) — 60 s (10 min for a mint that is not a Kalshi outcome token)


# ↪ moved to rep_crews.py: _kt_need, _kt_proof


# ↪ moved to rep_crews.py: _fmk_http_get


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
import fee_markets as _fmk   # noqa: F401  (read by rep_crews, rep_more_reads as rs._fmk)
_fmk_cache = {'at': 0.0, 'v': None, 'prev': {}, 'lock': None}
import fee_pools as _fpl   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
_fpl_cache = {'at': 0.0, 'v': None, 'lock': None}
FPL_SEC = 600


# ↪ moved to rep_crews.py: _fpl_fetch


import sleep_money as _slm   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
_slm_cache = {'at': 0.0, 'km': None}


import cat_fund as _cfund   # noqa: F401  (read by rep_crews, rep_money_routes as rs._cfund)
import wallet_swaps as _wswaps   # noqa: F401  (read by rep_intel as rs._wswaps)
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


# ↪ moved to rep_crews.py: _fmk_fetch


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


import flow as _flow   # noqa: F401  (read by rep_ai, rep_more_reads as rs._flow)
FLOW_PROOF_PATH = FUSE_HQ_PATH.parent / 'flow_proof.json'   # 🌊 every flow / rug exit: noted at its sell price, judged 1h later (lower = it saved money)
FLOW_EVERY = 15.0
_flow_now: dict = {}    # pairAddress → (at, window) — the latest tape read of every coin we watch
_flow_at = {'t': 0.0}
_flow_trades: dict = {}   # pairAddress → (at, raw trades) of the last tape read
import degen as _dg   # noqa: F401  (read by rep_predict as rs._dg)
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


# ↪ moved to rep_predict.py: _prime_tick_inner


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


# ↪ moved to rep_fuse_wallet.py: circle_profile_view, circle_profile_merge


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
import candle_clock as _ccl   # noqa: F401  (read by rep_ai, rep_predict as rs._ccl)


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


import ai_seat as _seat   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._seat)
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


# ↪ moved to rep_ai_chat.py: _brain_load, _chat_persist, _chat_extra
AI_CHAT_CTX_SEC = 20.0   # the compact agent-state context is rebuilt at most this often (and only its text changes the model's input)


# ↪ moved to rep_ai_chat.py: _chat_props, _chat_context, _chat_olds, _ai_proposal_apply


import ai_play as _play   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
AI_PLAY_PATH = DATA_DIR / 'ai_playground.json'


AI_RIG_PATH = DATA_DIR / 'ai_rig.json'
AI_PRESETS_PATH = DATA_DIR / 'ai_presets.json'   # 🔖 per-model rig presets (ai_rig.preset_*)


# ↪ moved to rep_ai_chat.py: _rig_apply


_lms_reloading: set = set()   # ⚡ models reloading right now (one reload per model at a time)
LMS_MARK_PATH = DATA_DIR / 'lms_reloading'   # 🚧 scripts/keep-alive.sh's LM watchdog stands down while this file is < 5 min old (no double load mid-reload)


# ↪ moved to rep_ai_chat.py: _lms_reload
_lms_seen: dict = {}   # 🧠 {key: (at, lms_row)} — what each LM Studio REALLY runs (15s cache; a reload clears it)


# ↪ moved to rep_ai_chat.py: _lms_states


# 🧠 THE MODEL DESK (owner, 2026-10-23: "the Models tab should really show it all — server settings, MCP, load, inference … more vitals"):
# Brain › Models per model = INFO · LOAD · INFERENCE · SERVER · MCP + live VITALS for every model (model_desk.py). One cached read per source.
import model_desk as _mdk   # noqa: E402
_mdk_seen: dict = {}


# ↪ moved to rep_ai_chat.py: _mdk_cached, _mdk_lms, _mdk_mcp, _model_desk_view


# 🎭 PROMPT STUDIO (owner, 2026-10-22): each model's live context, its record, what the record says is wrong, and four prompt sets written from it
# (ELITE · DEGEN TRENCH · PROGRESSIVE · AUTO-TUNED). The owner applies one → the router appends it to every call that model gets (prompt_studio.py).
import prompt_studio as _pstu   # noqa: E402
PROMPT_STUDIO_PATH = DATA_DIR / 'prompt_studio.json'


# ↪ moved to rep_ai_chat.py: _studio_apply


_studio_lms_note = {}


# ↪ moved to rep_ai_chat.py: _studio_lms, _studio_trades, _studio_core


_studio_auto_at = {'t': 0.0}


# ↪ moved to rep_ai_chat.py: _studio_auto, _studio_auto_safe, _studio_layer, _studio_view, _studio_fee


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


# ↪ moved to rep_ai_chat.py: _colony_value, _colony_view


COLONY_POOL_JS = Path(__file__).resolve().parent.parent / 'circle' / 'colony-pool.mjs'


POOL_QUOTES = {'SOL': ('So11111111111111111111111111111111111111112', 0.01, 1000), 'USDC': ('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 1, 100000)}
# ↪ moved to rep_ai_chat.py: _pool_tokens, _colony_pool_build


import chat_evidence as _cev   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._cev)
_cev_cache: dict = {}


# ↪ moved to rep_ai_chat.py: _chat_syms, _chat_coin, _owner_brief, _chat_evidence, _chat_learned


_CHAT_IMG = _re.compile(r'^/api/reputation/uploads/([0-9a-f]{32}\.(png|jpg|webp|gif))$')


# ↪ moved to rep_ai_chat.py: _chat_image, _build_state


_rpc_warned = {'day': ''}


# ↪ moved to rep_ai_chat.py: _rpc_quota_notice, _agents_loop, _fuse_warm_loop


_fuse_warm_n = {'n': 0}


import data_cleaner as _dc   # noqa: F401  (read by rep_ai as rs._dc)
import storage_trim as _strim   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._strim)

_data_clean_last: dict = {}


# ↪ moved to rep_ai_chat.py: _data_clean


INTEL_DISK = DATA_DIR / 'intel_cache.json'
INTEL_DISK_MAX_AGE, INTEL_DISK_KEEP = 6 * 3600.0, 400   # scan RESULTS kept across a restart (a result older than its TTL is served as STALE while its refresh waits its turn)
LAUNCH_DISK, LAUNCH_KEEP = DATA_DIR / 'launch_facts.json', 4000
ENRICH_DISK = DATA_DIR / 'enrich_fresh.json'             # the scheduler's freshness book: last success / last attempt / back-off per mint
_intel_saved: dict = {'key': None}


# ↪ moved to rep_ai_chat.py: _intel_save, _intel_restore


import paper_desk as _pd   # 📝 the OFFLINE practice record (graded paper calls) — it has no live authority   # noqa: F401  (read by rep_admin_reads, rep_ai as rs._pd)
import trench_kernel.universe as _uni   # noqa: F401  (read by rep_ai, rep_coin_edge as rs._uni)
import trench_kernel.senses as _sn   # noqa: F401  (read by rep_ai as rs._sn)
import trench_mind as _tm   # noqa: F401  (read by rep_ai as rs._tm)
import opportunity as _opp   # noqa: F401  (read by rep_ai, rep_predict as rs._opp)
import launch_intel as _li   # noqa: F401  (read by rep_ai, rep_prime as rs._li)
import market_wake as _mw   # noqa: F401  (read by rep_ai, rep_prime as rs._mw)
import judge_review as _jr   # noqa: F401  (read by rep_ai as rs._jr)
import real_memory as _rm   # noqa: F401  (read by rep_ai as rs._rm)
import shadow_book as _sb   # noqa: F401  (read by rep_ai as rs._sb)
import coach as _co   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._co)
import trench_rounds as _tr   # noqa: F401  (read by rep_ai as rs._tr)
import generations as _gen   # noqa: F401  (read by rep_ai as rs._gen)
import trench_kernel.kernel as _tk   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._tk)
import trench_kernel.brain as _tkb   # noqa: F401  (read by rep_ai as rs._tkb)
import trench_kernel.lifecycle as _tkl   # noqa: F401  (read by rep_ai as rs._tkl)
import trench_kernel.positions as _pos   # noqa: F401  (read by rep_ai, rep_predict as rs._pos)
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


# ↪ moved to rep_coach.py: _lc_book


_lc_sh_memo: dict = {}


# ↪ moved to rep_coach.py: _lc_shadows, _lc_shadows_raw


import evolution_lab as _evo   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._evo)
EVO_PATH = DATA_DIR / 'evolution_lab.json'   # 🧪 COL-11: the lab's OWN append-only ledger. It never writes the live trading tunables.
_evo_memo: dict = {}


# ↪ moved to rep_coach.py: _evo_view, _lifecycle, _lc_evaluate


ROUNDS_PATH = FUSE_HQ_PATH.parent / 'trench_rounds.json'   # ⏱ candidates' 5-minute rounds + the round history (trench_rounds.py)
_rounds: dict = {'state': None}


# ↪ moved to rep_coach.py: _rounds_state, _judge_weights, _paper_view, _kernel_view, _edge_rules, _edge_view, _kernel_ctx


OWNER_REVIEW_PATH = FUSE_HQ_PATH.parent / 'owner_review.json'   # 👤 the owner's review / track / arm list (owner_review.py)
_owner: dict = {'book': None, 'only': set()}
_tape_seen: dict = {'ledger': 0.0, 'reap': {}, 'regime': None, 'hub': 0}


# ↪ moved to rep_coach.py: _owner_book, _owner_view, _owner_resolve, _owner_act, _tape_flush, _tape_ledger, _tape_reaper


ENRICH_TOP = 4      # 🔎 Tier 2: holder / early-wallet scans for the strongest candidates only (Tier 0 = the whole intake, zero RPC)
ENRICH_MOVERS = 2   # … + at most this many brand-new movers a pass


import survival_watch as _surv   # noqa: F401  (read by rep_ai as rs._surv)
_FEATS: dict = {}   # 🧪 mint → its audit tags, refreshed every pass
_SURV: dict = {}   # ⏱ mint → its 1 / 5 / 15-min checkpoints since we first sensed it (survival_watch; memory only, rebuilt from the next passes)


# ↪ moved to rep_coach.py: _kernel_pass, _rounds_pass
SHADOW_PATH = FUSE_HQ_PATH.parent / 'shadow_book.json'   # 📄 paper decisions + controls (shadow_book.py), graded at 30s … 1h
_shadow: dict = {'book': None, 'cost': None, 'costAt': 0.0, 'dirty': False}


# ↪ moved to rep_coach.py: _shadow_cost, _st_med, _shadow_book, _shadow_px, _shadow_note, _shadow_controls, _shadow_real_buys, _shadow_settle
# ↪ moved to rep_coach.py: _shadow_flush


_real_tr: dict = {'at': 0.0, 'rows': []}


_dial_mem: dict = {'at': 0.0, 'v': None}


# ↪ moved to rep_coach.py: _dial_lab, _desk_stats_view


import night_guard as _ng   # noqa: F401  (read by rep_ai, rep_prime as rs._ng)
NIGHT_PATH = DATA_DIR / 'night_guard.json'
_night: dict = {'st': None, 'v': None}


# ↪ moved to rep_coach.py: _night_check, _real_trades


AFTER_PATH = DATA_DIR / 'after_paths.json'   # 👁 what each coin did in the 30 min AFTER our exit (after_path.py) — the replay's missing half
_after_mem = _ms.MemStore(lambda: AFTER_PATH, 60.0, lambda p_, d_: _json_load(p_, d_), lambda p_, o_: _json_save(p_, o_))


# ↪ moved to rep_coach.py: _after_step, _trail_view, _capital_view, _real_mem


COACH_PATH = FUSE_HQ_PATH.parent / 'agent_coach.json'   # 👑 the creator's + the model's live directives (coach.py) — small, written on each change
_coach: dict = {'s': None, 'tapeAt': 0.0, 'tape': None, 'aiAt': 0.0}
COACH_AI_EVERY = 900.0   # the model coach looks at the last real trades at most every 15 min (one cheap cloud call; never the local model)


# ↪ moved to rep_coach.py: _coach_state, _coach_put, _coach_pens, _coach_view, _trade_tape, _coach_grade


import rule_lab as _rlab   # noqa: F401  (read by rep_ai as rs._rlab)
import teach as _tch   # noqa: F401  (read by rep_admin_routes, rep_ai as rs._tch)
import jup_keys as _jkeys   # noqa: F401  (read by rep_crews, rep_fuse as rs._jkeys)
TEACH_PATH = DATA_DIR / 'agent_teach.json'
_teach: dict = {'st': None}


# ↪ moved to rep_coach.py: _teach_state


import taught_rules as _trl   # noqa: F401  (read by rep_ai, rep_money_routes as rs._trl)


# ↪ moved to rep_coach.py: _taught_rules, _taught_stamp, _taught_view
import regret as _rg   # noqa: F401  (read by rep_ai, rep_predict as rs._rg)
import capital as _cap   # noqa: F401  (read by rep_ai, rep_predict as rs._cap)
import after_path as _ap   # noqa: F401  (read by rep_ai, rep_predict as rs._ap)
REGRET_PATH = DATA_DIR / 'regret.json'
_regret: dict = {'b': None, 'at': 0.0, 'savedAt': 0.0}


# ↪ moved to rep_coach.py: _regret_book, _regret_note, _regret_limits, _regret_tick


LAB_PATH = DATA_DIR / 'rule_lab.json'
LAB_EVERY, LAB_JUDGE_EVERY = 3600.0, 600.0
_lab: dict = {'st': None, 'at': 0.0, 'judgedAt': 0.0, 'said': None}


# ↪ moved to rep_coach.py: _lab_state, _lab_tick, _lab_view, _coach_ai


_reap_prev: dict = {}   # mint → (at, px): the fast stop guard's previous live read (office.spike_held)


GERM_REBUY_SEC = 7200.0   # 🦠 a Gstop sale is watched this long for a new germ floor


# ↪ moved to rep_coach.py: _germ_rebuy_step, _germ_of, _agent_blocked, _g4_blocked, _seat_refusals


AGENT_NOROUTE_SEC = 1800.0   # no way back to SOL / no route at all: 30 min (a curve coin's route does not appear in two)
AGENT_PRE_SEC = 180.0   # a coin that failed the seat pre-check (no live pool read / pool under the floor) sits out 3 min
SEAT_PRE_OK_SEC = 20.0
_seat_pre_ok = {}       # mint → (at, {liq, px}): coins that passed the pre-check in the last 20s
_agent_refused = {}     # mint → (until, why, at): the 🛂 seat pre-check's own refusals (memory only)


# ↪ moved to rep_coach.py: _seat_precheck, _agents_tick


import office as _of   # noqa: F401  (read by rep_ai, rep_money_routes as rs._of)
OFFICE_PATH = FUSE_HQ_PATH.parent / 'agent_office.json'     # 🏢 tunables promoted by shadow tests · candidates · open positions · latency rings · counters
ARCHIVE_PATH = FUSE_HQ_PATH.parent / 'agent_archive.json'   # 🗄 hash-chained decision lineage (≤ 600 cases) + closed real positions (≤ 300); older fold into totals
_verify_memo: dict = {}


# ↪ moved to rep_coach.py: _arch_verify
_office: dict = {'state': None, 'pos': {}, 'exiting': [], 'gone': [], 'lat': {}, 'sized': {}, 'reports': [], 'warden': None, 'courier': None, 'payload': None, 'last': None, 'vetoAt': {},
                 'charts': {}, 'theses': {}, 'candles': {}, 'cmeta': {}, 'load': {}, 'boot': {'at': time.time(), 'passes': 0, 'coins': 0, 'reconciled': False}, 'seatWakeAt': 0.0, 'seatWakes': 0, 'ticks': [], 'candleStat': {'req': 0, 'cached': 0, 'merged': 0, 'dup': 0, 'ms': 0.0, 'coins': 0}}
import chart_intel as _ci   # noqa: F401  (read by rep_ai, rep_coin_edge as rs._ci)
import market_data as _md   # noqa: F401  (read by rep_ai as rs._md)
import office_edge as _oe   # noqa: F401  (read by rep_ai, rep_money_routes as rs._oe)
import seat_ops as _so   # noqa: F401  (read by rep_ai, rep_predict as rs._so)
OFFICE_CANDLE_TTL = 12.0    # 👁 live: the chart is re-read when it is older than this (one batched local call for the whole desk); one read of a coin's 1-minute candles serves every desk for the whole pass (and the tier ticks until the next one)
# ↪ moved to rep_office.py: _deep_bucket


OFFICE_CANDLE_CASES = 18    # real candles for the held coins + the top of the bench / strongest cases; every other coin is read from Tally's own tape (no request at all)
OFFICE_CANDLE_NEW = 6       # … + the busiest launches under ~20 min old (local candles service, one request per pool, 50s cache)


# ↪ moved to rep_office.py: _office_candles
OFFICE_LAT_N = 120
OFFICE_REFRESH_MAX = 40     # ⚡ per tier tick (one batched call): at most this many pools get their candles re-read (only those whose read is older than OFFICE_CANDLE_TTL)


# ↪ moved to rep_office.py: _mkt_view, _office_vels


_wake: dict = {'pos': {}, 'candAt': 0.0, 'log': [], 'n': 0, 'candN': 0}


LIVE_PX_SEC, LIVE_PX_BULK_SEC = 3, 8   # a few held seats answer fast; a 60-coin grading batch may take two upstream calls — a 3s cut-off
# returned NOTHING for the whole batch, and the graders read that as every coin vanishing (2026-10-13)


# ↪ moved to rep_office.py: _live_px, _wake_note, _market_wake, _office_candle_refresh


CYCLE_LOG_N = 20
import intake as _in   # noqa: F401  (read by rep_ai, rep_predict as rs._in)
INTAKE_PATH = FUSE_HQ_PATH.parent / 'intake_registry.json'   # 🕸 the one deduped intake registry (first / last seen per source + the office stamps)
INTAKE_JUP = 150            # coins an outlet lists that the board does not carry: rows from Jupiter's token data (100 a call, 60s cache)
_intake: dict = {'reg': None, 'last': None, 'prev': [], 'saveAt': 0.0}


# ↪ moved to rep_office.py: _intake_reg


_intake_ds: dict = {}   # mint → (at, DexScreener pair | None) — 45s


# ↪ moved to rep_office.py: _intake_dex, _intake_pass, _intake_after, _intake_view, _office_seat_payload, _office_cycle_log, _office_fresh
# ↪ moved to rep_office.py: _office_load_pass


import social_research as _sr   # noqa: F401  (read by rep_ai as rs._sr)
SOCIAL_PATH = FUSE_HQ_PATH.parent / 'social_cache.json'   # 🔎 the research packets (≤ SOCIAL_KEEP, newest kept) — reloaded once after a restart
SOCIAL_KEEP = 400
SOCIAL_V = 4   # bump when the parser changes (v2: mints from visible text only · v3: no X link on a site = unknown · v4: evidence items + legal read)
_social: dict = {'cache': None, 'busy': False, 'searched': {}}


# ↪ moved to rep_office.py: _social_cache, _social_flush, _research_tick, _seat_wake_maybe, _office_state, _office_lat, _office_ledger, _office_real
# ↪ moved to rep_office.py: _office_ctx, _office_warden, _office_reap, _office_chart_view, _office_bars, _office_positions


_DELTA_DROP = ('ages', 'decidedAgo')      # relative ages tick every second: the stream sends absolute `times` / `decidedAt` instead
_POS_DROP = ('bars',)                      # a position's candles are the snapshot's (and the charts' own stream) — never re-sent per tick


# ↪ moved to rep_office.py: _hub_publish


_SSE = {'connects': 0, 'disconnects': 0, 'resyncs': 0, 'active': 0, 'since': time.time()}   # 📡 measured: live streams + reconnects


# ↪ moved to rep_office.py: _net_stats


STREAM_MAX_SEC = 1800.0     # a stream ends after 30 min (the page reconnects with its last sequence — nothing is lost)
STREAM_BEAT_SEC = 15.0


# ↪ moved to rep_office.py: _office_light, _office_pass, _agents_real, _kernel_row, _agent_inherit_rows, _agents_go_rows, _agents_snapshot


# ⚡ WHAT THE PAGE GETS: the snapshot minus the sections no screen draws (they fed the retired room / seat views — 2026-10-12: ~350 KB of a
# 616 KB answer, most of it each row's research packet), serialized ONCE per 2s for every reader instead of encoded per request.
AGENTS_PAGE_DROP = ('index', 'social', 'cycleLog', 'intakeView', 'rpc', 'lifecycle', 'seatScores', 'seatActions', 'opp', 'loadPass', 'switchTests')
AGENTS_ROW_DROP = ('social',)
AGENTS_PAGE_SEC = 2
_agents_page: dict = {'key': None, 'body': b'{}'}


_duo_tape_c: dict = {'at': 0.0, 'v': ([], [])}


# ↪ moved to rep_duo.py: _duo_tape, _duo_totals, _duo_rooms, _duo_holding, _duo_card_legs, _duo_coin_rooms


DUO_PIN_PER, DUO_PIN_CARD = 8, 60   # 📣 chart comments kept per coin: 8 for coins off the card, the WHOLE history (≤ 60) for coins on it
_duo_cap_seen: dict = {}            # a line written without a cap keeps the cap of the moment it was first shown (never today's cap on an old pin)


# ↪ moved to rep_duo.py: _duo_pin_cap


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


# ↪ moved to rep_duo.py: _duo_cap, _duo_phase, _duo_view, _agents_page_dict, _agents_page_body, _fuse_warm


_runner_disc_cache = {'at': 0.0, 'data': None}


# ↪ moved to rep_duo.py: _round_move, _scenario_stage, _pg_pick_ok, _engine_auto, _engine_nudge, _top_anchor, _pg_scenario_cards, _pg_battle_view
# ↪ moved to rep_duo.py: _pg_battle_tick


import pg_sim as _pgs   # noqa: F401  (read by rep_ai as rs._pgs)
PG_SIM_PATH = DATA_DIR / 'pg_sim.json'   # its own file: never bloats runners.json


import pick_edge as _pedge   # noqa: F401  (read by rep_ai, rep_market as rs._pedge)
import pick_style as _ps   # noqa: F401  (read by rep_ai, rep_predict as rs._ps)
import owner_moves as _om   # noqa: F401  (read by rep_ai, rep_predict as rs._om)
EDGE_PATH = FUSE_HQ_PATH.parent / 'edge.json'
_edge_state: dict = {}


# ↪ moved to rep_duo.py: _edge_load, _pg_sim_tick, _brain_patch, _engine_self_fix


import verdict as _verdict   # noqa: F401  (read by rep_ai, rep_money_routes as rs._verdict)


VERDICT_PATH = DATA_DIR / 'fuse_verdict.json'
# 🧾 what one click can do with a verdict row (area → actions). Sim configs map onto the tier engine's own keys.
SIM_KEYS = {'minDrop': 'rotateMinDrop', 'confirm': 'rotateConfirm', 'rideAt': 'rideAt', 'trail': 'rideTrail', 'tp': 'tp', 'sl': 'sl'}


# ↪ moved to rep_duo.py: _verdict_acts, _retired, _verdict_build, _verdict_tick


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


# ↪ moved to rep_quests.py: _asset_owner, _fuse_pay_to, _site


class FuseCardIn(BaseModel):
    signature: str
    collection: str = ''
    asset: str = ''


class FuseBuy(BaseModel):
    address: str
    session: str
    signature: str


# ---- FUSE Vault (backend/fuse_vault.py; on-chain program in programs/fuse_vault) ----------------------------------
import fuse_vault as _vault   # noqa: F401  (read by rep_admin_reads, rep_admin_routes as rs._vault)
VAULTS_PATH = DATA_DIR / 'fuse_vaults.json'   # {'vaults': {id: {name, emoji, pools[≤3], mgmtBps, perfBps, status}}}
VAULT_MAX_MGMT_BPS, VAULT_MAX_PERF_BPS = 300, 3000   # ≤3%/yr management, ≤30% performance


_SOL_LAST: dict = {}   # {'px', 'at'} — the last good SOL price


# ↪ moved to rep_quests.py: _sol_usd_live, _vault_view


# ---- Quest engine: 40 animated badges (FEELESS + Fee Reserve), daily/weekly quests, levels (backend/quests.py) ----
import quests as _quests   # noqa: F401  (read by rep_admin_reads, rep_admin_routes as rs._quests)
QUESTS_PATH = DATA_DIR / 'quests.json'            # admin: {'badges': {id: override}, 'manual': {wallet: {grant, revoke}}}
QUEST_STATE_PATH = DATA_DIR / 'quest_state.json'  # {wallet: {'days': [YYYY-MM-DD], 'first': ts}} — moved into quest_state.db (SITE-8), kept read-only
_qs_docs: dict = {}


# ↪ moved to rep_quests.py: _qs
EDITIONS_PATH = DATA_DIR / 'quest_editions.json'  # {badge: [wallets in earn order]} — first EDITION_CAP are numbered
EDITION_CAP = 100
_quest_cache: dict = {}


# ↪ moved to rep_quests.py: _quest_defs, _streak, _fuse_quest_stats, _quest_raw


QUEST_SEASON_DEFAULT = {'id': 's1', 'name': 'Season 1', 'paused': True, 'start': None}   # paused until FEELESS launches


# ↪ moved to rep_quests.py: _quest_season, _quest_summary


_rarity_cache: dict = {}


# ↪ moved to rep_quests.py: _quest_rarity


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


# ↪ moved to rep_hq.py: _guard_s


# ↪ moved to rep_hq.py: _guard_save


import defence as _def
DEF_PATH = DATA_DIR / 'defence.json'
_def_state = None
_def_dirty = {'at': 0.0}


# ↪ moved to rep_hq.py: _def_s


# ↪ moved to rep_hq.py: _def_save


# ⚔️ SEC-1 War Room: the owner-only security dashboard's state (war_room.py). Sits on top of _def; all data is observed on our own server.
import war_room as _war          # noqa: E402
import war_hardening as _war_hard  # noqa: E402
WAR_PATH = DATA_DIR / 'war_room.json'
_war_state = None
_war_dirty = {'at': 0.0}


# ↪ moved to rep_hq.py: _war_s


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


# ↪ moved to rep_hq.py: _require_admin


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
import street_chat as _stc   # noqa: F401  (read by rep_admin_routes, rep_chat as rs._stc)
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


# ↪ moved to rep_hq.py: _legal_s


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


# ↪ moved to rep_quests.py: _receipt_rows


class ReceiptIn(BaseModel):
    sig: str
    wallet: str
    kind: str = 'swap'


_receipt_hits = _HITS('receipt')


# ↪ moved to rep_quests.py: store_receipt


# ---- Airdrop engine: hold duration + holder snapshots ------------------------------------
_age_cache = {}
SNAP_PATH = DATA_DIR / 'snapshots.json'


# ↪ moved to rep_quests.py: _first_active, _snaps


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


# ↪ moved to rep_quests.py: _perk_tier


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


# ↪ moved to rep_quests.py: _ids, primary_of, linked_of


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


# ↪ moved to rep_fees.py: _fee_cfg, _engine_cfg


_fee_owner_cache: dict = {}


# ↪ moved to rep_fees.py: _fee_owner_sol, _swap_fee_accounts, _swap_fee_account, _leg_usd, _agent_owner, effective_fee, _agent_wallets


AGENT_FEES_SENT = DATA_DIR / 'agent_fees_sent.json'


_GROW = {'at': 0.0, 'rows': [], 'detail': {}}
GROW_SOL_POOL = 'Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE'   # Orca's deepest SOL-USDC, for SOL's real price


# ↪ moved to rep_fees.py: _grow_rows, _site_landed, _site_fees_total, _collective_view


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


# ↪ moved to rep_fees.py: _rounds_cfg


_rounds_pay_cache: dict = {'at': 0.0, 'to': None}


# ↪ moved to rep_fees.py: _rounds_pay_to


class RoundsIn(BaseModel):
    address: str
    session: str
    id: str = Field(..., max_length=16)
    mode: str = Field(..., max_length=10)        # pay | compound | settle
    signature: str = Field(default='', max_length=100)


# ↪ moved to rep_fees.py: _fuse_rounds


# 🏠 HOUSE FEES — the fees that used to be hard-coded, set in HQ › Core with the rest (owner: "all FEELESS fees set from HQ › Core"):
# the Fuse creator's max share of the FEELESS fee, FeeCat's paper fee per side (pushed to her service), the MP → FEECAT redeem rate.
HOUSE_DEFAULTS = {'fuseCreatorMaxBps': 5000, 'feecatFeePct': 1.0, 'redeemMp': 1_000_000, 'redeemFeecat': 10_000}


# ↪ moved to rep_fees.py: _house


class HouseFees(BaseModel):
    fuseCreatorMaxBps: int = Field(5000, ge=0, le=10_000)
    feecatFeePct: float = Field(1.0, ge=0, le=5)
    redeemMp: int = Field(1_000_000, ge=10_000, le=1_000_000_000)
    redeemFeecat: int = Field(10_000, ge=1, le=1_000_000_000)


JUP_ULTRA_REFERRAL_PROJECT = 'DkiqsTrw1u1bYFumumC7sCG2S8K25qc2vemJFHyW2wJc'
JUP_REFERRAL_PROGRAM = 'REFER4ZgmyYx9c6He5XfaTMiGfdLwRnkV4RPp9t9iF3'


TOKEN_PROGRAMS = {'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA', 'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb'}


# ↪ moved to rep_fees.py: _swap_fee_health


_fee_coin_names: dict = {}


# ---- Rug shield: one verdict for the swap review / quick trade, from on-chain forensics --------------


# ↪ moved to rep_intel.py: shield_verdict


# ---- Investigation engine: case files for wallets and coins (scoring lives in investigate.py) -------------
_case_cache: dict = {}
_funding_memo: dict = {}


# ↪ moved to rep_intel.py: _funder_of, _mint_authorities, _wallet_case, _coin_case


# ---- BOT SHIELD (backend/bot_shield.py): the defender. Engines over FEELESS records; ties into rep, rewards, Fuse --------
import bot_shield as _shield   # noqa: F401  (read by rep_admin_routes, rep_intel as rs._shield)
SHIELD_PATH = DATA_DIR / 'bot_shield.json'   # {'manual': {wallet: 'cleared' | 'bot'}, 'at': {...}}
_shield_cache: dict = {}


# ↪ moved to rep_intel.py: _shield_features, _ts_num, _shield_of, _fuse_rep, _shield_scan_all


_case_peak: dict = {}   # mint → peak volume $/h seen (live case files)


# ---- Copy callers: calls from wallets you follow, newest first, with each caller's record ---------------


# ↪ moved to rep_intel.py: _fee_wallet_owner, _quote_fee_bps


# ---- Chat sessions: sign once, chat for 7 days --------------------------------------------
import secrets as _secrets   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
SESSIONS_PATH = DATA_DIR / 'chat_sessions.json'
SESSION_TTL = 7 * 86400


# ↪ moved to rep_intel.py: _sess, session_address


class SessionIn(BaseModel):
    address: str
    ts: int
    signature: str


# ↪ moved to rep_intel.py: handle_of


# ---- Live FEELESS intelligence counts (Learn tab) ------------------------------------------
_marked = {'snipers': set(), 'bundlers': set(), 'mints': set()}
_hygiene_mem = {'d': None, 'dirty': False, 'at': 0.0}


# ↪ moved to rep_intel.py: _hygiene_flush, _absorb_intel


_stats_cache = {'at': 0, 'data': None, 'lock': None}


# ↪ moved to rep_intel.py: _live_stats_compute


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


# ↪ moved to rep_intel.py: is_muted


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


# ↪ moved to rep_intel.py: _evm_room, _evm_holding_usd, _evm_account_for, evm_gate


# ---- Weekly caller leagues --------------------------------------------------------------------
# ↪ moved to rep_intel.py: _week_start


# ---- Rug radar + whale feed (background watcher) --------------------------------------------
_radar = {'hist': {}, 'events': [], 'whales': [], 'pairs': {}}


# ↪ moved to rep_intel.py: _radar_pairs, _radar_loop


SNIPERS_OUT_COOLDOWN = 86400  # snipers can only sell out once; don't re-announce the same coin all day


# ↪ moved to rep_intel.py: _radar_event, _push_snipers_out


@app.on_event('startup')
async def _start_radar():
    _LEAD.start(_radar_loop)


# ↪ moved to rep_intel.py: _feecat_pins, _feecat_fast_trench


# ---- Notifications inbox (per identity) + push to the owner's devices ----------------------
NOTIF_PATH = DATA_DIR / 'notifications.json'
_notif_docs: dict = {}


# ↪ moved to rep_intel.py: _notif, _notif_box, notify, _session_or_401, _legacy_sniper_dedupe


# ---- Direct messages (profile chat) -----------------------------------------------------------
DM_PATH = DATA_DIR / 'dms.json'
_dm_last = {}


# ↪ moved to rep_intel.py: _dm_key


class DmIn(BaseModel):
    address: str
    session: str
    to: str
    text: str = Field(min_length=1, max_length=500)


# Who may message a wallet: everyone, requests (first message waits until accepted) or nobody.
DM_PREFS_PATH = DATA_DIR / 'dm_prefs.json'
DM_POLICIES = ('everyone', 'requests', 'nobody')


# ↪ moved to rep_intel.py: _dm_pref


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


# ↪ moved to rep_intel.py: _pts, _reward_state


class ClaimIn(BaseModel):
    address: str
    session: str
    reward: str


# ---- Verified identities ---------------------------------------------------------------------
FEE_RESERVE_WALLET = 'Btiq3W3yhqSRbF1FEf2TQMNrwsknMpQmeb5K9TeD83qU'


# ↪ moved to rep_intel.py: is_verified


# ---- Unique invite codes + public site URL ---------------------------------------------------
# ↪ moved to rep_intel.py: invite_code, _code_owner


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


# ↪ moved to rep_intel.py: _unlocks


class BuyIn(BaseModel):
    address: str
    session: str
    item: str


# ---- Trench Wars: weekly faction battle --------------------------------------------------------
FACTIONS = {'bulls': '🐂 Bulls', 'bears': '🐻 Bears', 'degens': '🎰 Degens'}
WARS_PATH = DATA_DIR / 'wars.json'


# ↪ moved to rep_intel.py: _war_week


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


# ↪ moved to rep_intel.py: _webhook_secret, sync_helius_webhook


# ---- Portfolio: every coin a wallet holds, priced, with logos --------------------------------
_pf_cache = {}


PF_STALE_SEC = 900.0
_pf_busy: set = set()


# ↪ moved to rep_intel.py: _portfolio_build


# ---- Image proxy for coin logos whose hosts forbid cross-site embedding ------------------------
from fastapi.responses import Response as _Resp   # noqa: F401  (read by rep_public_reads as rs._Resp)
from fnum import zero as _num_or_0   # noqa: F401 (re-exported: tests and modules reach it as rs.X)
_img_cache = {}


# ---- Social graph: follow / followers / following ----------------------------------------------
FOLLOW_PATH = DATA_DIR / 'follows.json'


# ↪ moved to rep_intel.py: _fol


class FollowIn(BaseModel):
    address: str
    session: str
    target: str
    follow: bool = True


# ---- Trust score for ANY wallet (0–100, evidence-only, with the breakdown) ----------------------
_trust_cache: dict = {}  # address -> (at, result)
_trust_pending: set = set()


# ↪ moved to rep_intel.py: _trust_fill


# ---- Edge network memory: every Edge read is a prediction; 24h later we grade it ------------
# Per chain, per grade (A–F): how did coins FEELESS graded that way actually do? The Edge score
# reads this back as its "Network memory" factor, so each network's scoring learns from its own
# outcomes — Base memes and Solana memes don't behave alike, and the score stops pretending they do.
EDGE_MEM_PATH = DATA_DIR / 'edge_memory.json'
EDGE_HORIZON = 24 * 3600
_edge_lock = asyncio.Lock()


# ↪ moved to rep_intel.py: _edge_grade


class EdgeObservation(BaseModel):
    chain: str
    pairAddress: str
    score: float
    priceUsd: float


# ↪ moved to rep_intel.py: _edge_price_ok


_edge_ip = _HITS('edge')


# ↪ moved to rep_intel.py: _refresh_edge_memory


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


# ↪ moved to rep_intel.py: _darkside_compute


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


# ↪ moved to rep_intel.py: _native_prices


# ---- Holder themes: $1k+ in the FEELESS ecosystem recolors the logo + the whole site ----------
THEME_MIN_USD = 1000.0
POOL_BUILDER_MIN_USD = 5000.0
THEMES_PATH = DATA_DIR / 'themes.json'
_theme_docs: dict = {}


# ↪ moved to rep_intel.py: _themes
_HEX = _re.compile(r'^#[0-9a-fA-F]{6}$')


_eco_hold_cache = {}


# ↪ moved to rep_intel.py: _eco_holding_usd


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


# ↪ moved to rep_intel.py: _meta_words


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


# ↪ moved to rep_intel.py: metas


# ---- A Solana wallet's own swaps, parsed from its transactions (Helius) --------------------------
_STABLES = {'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB'}


# ↪ moved to rep_intel.py: _maker_swaps


RPC_SWAP_SIGS, RPC_SWAP_PAR = 40, 6


# ↪ moved to rep_intel.py: _rpc_wallet_swaps


# ---- KOL tracker: real trades of wallets FEELESS admins mark as KOLs, and why the pattern matters --
KOLS_PATH = DATA_DIR / 'kols.json'
_kol_cache = {}


class KolPayload(BaseModel):
    address: str
    name: str
    x: Optional[str] = ''
    chain: str = 'solana'


# ↪ moved to rep_intel.py: _kol_stats


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


# ↪ moved to rep_market.py: _flush_traffic


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


# ↪ moved to rep_market.py: _shield_check, shield_record, _shield_watch


@app.on_event('startup')
async def _start_shield_watch():
    _LEAD.start(_shield_watch)


# ================================================================================================
# SEASONS — monthly competitions that reward trust, not volume.
# ================================================================================================
SEASONS_PATH = DATA_DIR / 'seasons.json'
SEASON_TIERS = [('Recruit', 0), ('Bronze', 250), ('Silver', 750), ('Gold', 2000), ('Diamond', 5000), ('Legend', 12000)]


# ↪ moved to rep_market.py: _seasons, _current_season


def season_award(address: str, points: float, reason: str):
    """Called wherever FEELESS awards points. Blocklisted wallets never score."""
    d = _seasons(); s = _current_season(d)
    if not s or points <= 0 or _is_blocked(_block_load()['wallets'].get(address)):
        return
    sc = d['scores'].setdefault(s['id'], {})
    rec = sc.setdefault(address, {'score': 0, 'events': 0})
    rec['score'] = round(rec['score'] + points * float(s.get('multiplier') or 1), 1); rec['events'] += 1; rec['last'] = reason
    _json_save(SEASONS_PATH, d)


# ↪ moved to rep_market.py: _tier


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


# ↪ moved to rep_market.py: _owner_wallets, _granted


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


# ↪ moved to rep_market.py: wallet_trades


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


# ↪ moved to rep_market.py: _season_weeks, _week_of


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


# ↪ moved to rep_market.py: _grant, _distribute_drops, _drops_loop


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


# ↪ moved to rep_market.py: _is_upload_url


# ---- Token search for the swap box: every Solana token Jupiter knows ----------------------------
_tok_search_cache = {}


_fills_cache: dict = {}


# ↪ moved to rep_market.py: _feeless_fills, _chain_fills


_repair_tried: dict = {}


# ↪ moved to rep_market.py: _repair_estimates, _locked_fills


_version_cache: dict = {}


# ↪ moved to rep_market.py: _git


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


# ↪ moved to rep_market.py: _pass_site, _agent_pass_rules, _owned_cat


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


# ↪ moved to rep_market.py: _chart_fill


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


# ↪ moved to rep_market.py: _rpc_call_ok
_rpc_hits = _HITS('rpc')


# ↪ moved to rep_market.py: _relay_spent


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


# ↪ moved to rep_market.py: _gold_creator


# ---- Launch radar: every coin launched through FEELESS, newest first, with its evidence ----------


# ↪ moved to rep_market.py: _quiet


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


# ↪ moved to rep_market.py: _ipfs_variants, _public_get, _fetch_first


LOGO_THUMBS = (64, 128, 256)


# ↪ moved to rep_market.py: _logo_thumb, _token_logo_any


# ---- HQ: chart & data-provider latency --------------------------------------------------
LATENCY_PROBES = [
    # (name, role in the chart pipeline, env var that controls/replaces it, url builder)
    ('Jupiter chart data', 'Chart history #1 (Solana)', '—', lambda: f"https://datapi.jup.ag/v2/charts/So11111111111111111111111111111111111111112?interval=1_MINUTE&to={int(time.time()*1000)}&candles=2&type=price&quote=usd"),
    ('Jupiter price', 'Live price + chart anchor', 'JUPITER_API_KEY', lambda: 'https://lite-api.jup.ag/price/v3?ids=So11111111111111111111111111111111111111112'),
    ('DexScreener', 'Pair discovery, search, fallback price', '—', lambda: 'https://api.dexscreener.com/latest/dex/search?q=SOL'),
    ('Helius RPC', 'On-chain reads, swap history, live stream trigger', 'SOLANA_RPC_URL', None),
    ('FEELESS candles', 'Serves every chart (cache + fallbacks)', '—', lambda: 'http://127.0.0.1:5099/api/candles/stream-stats'),
]


# ↪ moved to rep_market.py: _probe_latency


_latency_bad = {}


# ↪ moved to rep_market.py: _latency_alarm, _ops_note


@app.on_event('startup')
async def _start_latency_alarm():
    _LEAD.start(_latency_alarm)


# ---- HQ: marketing — 3-day top movers + top/bottom reputations, ready to post -------------
MARKETING_PATH = DATA_DIR / 'marketing.json'
_movers_cache = {'at': 0, 'rows': []}


# ↪ moved to rep_market.py: _three_day_movers, _post_text


# ---- Circle developer-controlled wallets (creator/owner only) -------------------------------------
# Proxies to the localhost Circle sidecar. Only owner wallets may list or create; keys never leave .env.
class CircleWalletIn(BaseModel):
    blockchain: str
    name: str = 'Creator wallet'


CIRCLE_DIR = Path(__file__).resolve().parents[1] / 'circle'
_circle_boot = {'at': 0.0}


# ↪ moved to rep_treasury.py: _circle_start, _circle, _require_owner, _reserve_plan


class ReservePaid(BaseModel):
    sigs: list[str] = Field(min_length=1, max_length=40)
    perKey: dict = {}           # badge pools: the plan's per-holder amount per badge key (scaled to what moved)
    plannedSol: float = 0


class CirclePayIn(BaseModel):
    confirm: str = ''          # must read "PAY <total SOL>" exactly


_circle_pay_lock = asyncio.Lock()


# ↪ moved to rep_treasury.py: _circle_pay


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


# ↪ moved to rep_treasury.py: _pools, _pool_inputs, _pool_plan


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


# ↪ moved to rep_treasury.py: _code_health_scan, _code_health_run, _code_health_loop


CH_QUEUE_TAG = '🧹 Remove '


class ChQueue(BaseModel):
    file: str = Field(..., max_length=200)
    name: str = Field('', max_length=120)
    kind: str = Field('', max_length=20)
    fix: str = Field('', max_length=300)


_mach_cache = {'at': 0, 'v': {}}


# ↪ moved to rep_treasury.py: _machine_read, _quick_rep, trade_points


FEE_LEDGER_PATH = DATA_DIR / 'fee_ledger.json'
FEE_TOTALS_PATH = DATA_DIR / 'fee_totals.json'
FEELESS_TRADES_PATH = DATA_DIR / 'feeless_trades.json'   # {wallet: [confirmed FEELESS trades]} for positions + chart pins        # lifetime per-account fee book (the payback base)
FEEBACK_PAID_PATH = DATA_DIR / 'feeback_paid.json'     # {account: usd already paid back}


# ↪ moved to rep_treasury.py: _fee_totals_heal


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


# ↪ moved to rep_treasury.py: _sol_usd


_sol_px: dict = {}


# ↪ moved to rep_treasury.py: _trade_record


# ---- Wallet watch: one tap from any case file; alerts on the watched wallet's next buys/sells --------------
WATCH_PATH = DATA_DIR / 'wallet_watch.json'
WATCH_MAX_PER_USER = 25


class WatchIn(BaseModel):
    address: str
    session: str
    target: str
    on: bool = True


# ↪ moved to rep_treasury.py: watch_alerts, _watch_loop


@app.on_event('startup')
async def _start_watch():
    _LEAD.start(_watch_loop)


# ---- After the sell: FeeCat's lesson log, pointed at your own trades ------------------------------------
# ↪ moved to rep_treasury.py: after_sell_lessons


# ---- Treasury hub: where the money sits, the split plan, and verified splits signed by the owner ----------
USDC_MINT = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'


_pulse_cache: dict = {}


# ↪ moved to rep_treasury.py: _money_pulse_build


PREFLIGHT_STATE_PATH = DATA_DIR / 'preflight_state.json'


# ↪ moved to rep_treasury.py: _preflight_watch


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


# ↪ moved to rep_treasury.py: _verify_store, _verify_facts, _verify_run, _verify_fill


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


# ↪ moved to rep_treasury.py: _nft_load, _public_site, _nft_platforms, _nft_api


class NftOnchainIn(BaseModel):
    address: str
    signature: str
    assets: list = []     # for drops: [{address, owner}]


# ↪ moved to rep_treasury.py: _nft_verify


class NftDropIn(BaseModel):
    to: list = []
    confirm: str = ''


# ---- Intel desk: the reputation department's database of ruggers, snipers, bundlers, funders and their crews -------
INTEL_DESK_PATH = DATA_DIR / 'intel_desk.json'
_desk = {'at': 0, 'snap': None, 'rings': [], 'actors': {}}


# ↪ moved to rep_treasury.py: _desk_build, _desk_build_bg


_desk_flight: dict = {}


# ↪ moved to rep_treasury.py: _desk_get, _desk_loop


@app.on_event('startup')
async def _desk_start():
    _LEAD.start(_desk_loop)


# ---- FEELESS cards: every badge + season drop as a 3D card (front art, back lore + money) ----------------------
CARDS_PATH = DATA_DIR / 'badge_cards.json'
_cards_cache: dict = {}


# ↪ moved to rep_treasury.py: _card_defaults, _collection_card_key, _cards_all


# ---- Circle wallets: names, descriptions, sends (owner-only, audited) -----------------------------------
CIRCLE_META_PATH = DATA_DIR / 'circle_meta.json'


class CircleMetaIn(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    description: str = Field(default='', max_length=200)


CIRCLE_DEST_PATH = DATA_DIR / 'circle_destinations.json'


# ↪ moved to rep_treasury.py: _circle_destinations


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


# ↪ moved to rep_treasury.py: _fuse_card_free_sol, _fuse_send_guard


# ---- 🧹 WALLET DUST CLEANUP (Trade › 🧹 Dust): read every coin a USER's wallet holds; they choose swap / burn + close; THEY sign ----
import dust as _dust   # noqa: F401  (read by rep_money_routes, rep_more_reads as rs._dust)
_EVM_ADDR = r'^0x[0-9a-fA-F]{40}$'
CRONOS_RPCS = ('https://evm.cronos.org', 'https://cronos-evm-rpc.publicnode.com', 'https://cronos.drpc.org')
_lifi_tok_cache: dict = {}


class DustCloseIn(BaseModel):
    address: str
    accounts: List[str] = Field(default_factory=list, max_length=40)


# ↪ moved to rep_treasury.py: _sol_token_accounts


_cro_idx_cache: dict = {}    # wallet → (at, tokens the wallet index says it holds)
_cro_list_cache: dict = {}   # 'dex' → (at, DEX token list)
CRONOS_DEX_LIST = 'https://raw.githubusercontent.com/cronaswap/default-token-list/main/assets/tokens/cronos.json'
CRONOS_WALLET_INDEX = 'https://api.rabby.io/v1/user/token_list'   # discovery only: which contracts a wallet holds (balances are re-read on-chain by us)


# ↪ moved to rep_treasury.py: _cronos_batch, _cronos_candidates


# ---- 🎵 MINI PLAYER: search (YouTube, + Spotify when keyed), top played (Apple chart), endless Next — read-only public data ----
import music as _music   # noqa: F401  (read by rep_public_reads, rep_treasury as rs._music)
_music_cache: dict = {}
_UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.9'}


# ↪ moved to rep_treasury.py: _yt_search, _spotify_search


# 🟦 FEE TRADES FROM HER CIRCLE WALLET (owner 2026-10-30: "feecat (nexa) should be able to use the wallet, not just read only").
# feecat_service's agent pass (agent_trade.py) runs every guard first (one in flight, per-buy + daily caps, the quote must echo the exact coins);
# here Circle signs ONLY a wallet of the creator's own Circle project that is assigned to that cat, our RPC sends it, and key → signature is
# written BEFORE the broadcast so a lost reply asked again with the same key never sends a second trade. Internal key only.
AGENT_CIRCLE_SENT = DATA_DIR / 'agent_circle_sent.json'


# ↪ moved to rep_treasury.py: _internal_ok


_CIRCLE_HELD: set = set()


# ↪ moved to rep_treasury.py: _agent_sol_to, _agent_circle_sign_send, _agent_send_loop

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
import rep_ai_chat as _rep_ai_chat   # noqa: E402  🧹 split out of rep_ai.py by scripts/split-module.py
import rep_coach as _rep_coach   # noqa: E402  🧹 split out of rep_ai.py by scripts/split-module.py
import rep_office as _rep_office   # noqa: E402  🧹 split out of rep_ai.py by scripts/split-module.py
import rep_duo as _rep_duo   # noqa: E402  🧹 split out of rep_ai.py by scripts/split-module.py
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
_brain_load = _rep_ai_chat._brain_load
_chat_persist = _rep_ai_chat._chat_persist
_chat_extra = _rep_ai_chat._chat_extra
_chat_props = _rep_ai_chat._chat_props
_chat_context = _rep_ai_chat._chat_context
_chat_olds = _rep_ai_chat._chat_olds
_ai_proposal_apply = _rep_ai_chat._ai_proposal_apply
_rig_apply = _rep_ai_chat._rig_apply
_lms_reload = _rep_ai_chat._lms_reload
_lms_states = _rep_ai_chat._lms_states
_mdk_cached = _rep_ai_chat._mdk_cached
_mdk_lms = _rep_ai_chat._mdk_lms
_mdk_mcp = _rep_ai_chat._mdk_mcp
_model_desk_view = _rep_ai_chat._model_desk_view
_studio_apply = _rep_ai_chat._studio_apply
_studio_lms = _rep_ai_chat._studio_lms
_studio_trades = _rep_ai_chat._studio_trades
_studio_core = _rep_ai_chat._studio_core
_studio_auto = _rep_ai_chat._studio_auto
_studio_auto_safe = _rep_ai_chat._studio_auto_safe
_studio_layer = _rep_ai_chat._studio_layer
_studio_view = _rep_ai_chat._studio_view
_studio_fee = _rep_ai_chat._studio_fee
_colony_value = _rep_ai_chat._colony_value
_colony_view = _rep_ai_chat._colony_view
_pool_tokens = _rep_ai_chat._pool_tokens
_colony_pool_build = _rep_ai_chat._colony_pool_build
_chat_syms = _rep_ai_chat._chat_syms
_chat_coin = _rep_ai_chat._chat_coin
_owner_brief = _rep_ai_chat._owner_brief
_chat_evidence = _rep_ai_chat._chat_evidence
_chat_learned = _rep_ai_chat._chat_learned
_chat_image = _rep_ai_chat._chat_image
_build_state = _rep_ai_chat._build_state
_rpc_quota_notice = _rep_ai_chat._rpc_quota_notice
_agents_loop = _rep_ai_chat._agents_loop
_fuse_warm_loop = _rep_ai_chat._fuse_warm_loop
_data_clean = _rep_ai_chat._data_clean
_intel_save = _rep_ai_chat._intel_save
_intel_restore = _rep_ai_chat._intel_restore
_lc_book = _rep_coach._lc_book
_lc_shadows = _rep_coach._lc_shadows
_lc_shadows_raw = _rep_coach._lc_shadows_raw
_evo_view = _rep_coach._evo_view
_lifecycle = _rep_coach._lifecycle
_lc_evaluate = _rep_coach._lc_evaluate
_rounds_state = _rep_coach._rounds_state
_judge_weights = _rep_coach._judge_weights
_paper_view = _rep_coach._paper_view
_kernel_view = _rep_coach._kernel_view
_edge_rules = _rep_coach._edge_rules
_edge_view = _rep_coach._edge_view
_kernel_ctx = _rep_coach._kernel_ctx
_owner_book = _rep_coach._owner_book
_owner_view = _rep_coach._owner_view
_owner_resolve = _rep_coach._owner_resolve
_owner_act = _rep_coach._owner_act
_tape_flush = _rep_coach._tape_flush
_tape_ledger = _rep_coach._tape_ledger
_tape_reaper = _rep_coach._tape_reaper
_kernel_pass = _rep_coach._kernel_pass
_rounds_pass = _rep_coach._rounds_pass
_shadow_cost = _rep_coach._shadow_cost
_st_med = _rep_coach._st_med
_shadow_book = _rep_coach._shadow_book
_shadow_px = _rep_coach._shadow_px
_shadow_note = _rep_coach._shadow_note
_shadow_controls = _rep_coach._shadow_controls
_shadow_real_buys = _rep_coach._shadow_real_buys
_shadow_settle = _rep_coach._shadow_settle
_shadow_flush = _rep_coach._shadow_flush
_dial_lab = _rep_coach._dial_lab
_desk_stats_view = _rep_coach._desk_stats_view
_night_check = _rep_coach._night_check
_real_trades = _rep_coach._real_trades
_after_step = _rep_coach._after_step
_trail_view = _rep_coach._trail_view
_capital_view = _rep_coach._capital_view
_real_mem = _rep_coach._real_mem
_coach_state = _rep_coach._coach_state
_coach_put = _rep_coach._coach_put
_coach_pens = _rep_coach._coach_pens
_coach_view = _rep_coach._coach_view
_trade_tape = _rep_coach._trade_tape
_coach_grade = _rep_coach._coach_grade
_teach_state = _rep_coach._teach_state
_taught_rules = _rep_coach._taught_rules
_taught_stamp = _rep_coach._taught_stamp
_taught_view = _rep_coach._taught_view
_regret_book = _rep_coach._regret_book
_regret_note = _rep_coach._regret_note
_regret_limits = _rep_coach._regret_limits
_regret_tick = _rep_coach._regret_tick
_lab_state = _rep_coach._lab_state
_lab_tick = _rep_coach._lab_tick
_lab_view = _rep_coach._lab_view
_coach_ai = _rep_coach._coach_ai
_germ_rebuy_step = _rep_coach._germ_rebuy_step
_germ_of = _rep_coach._germ_of
_agent_blocked = _rep_coach._agent_blocked
_g4_blocked = _rep_coach._g4_blocked
_seat_refusals = _rep_coach._seat_refusals
_seat_precheck = _rep_coach._seat_precheck
_agents_tick = _rep_coach._agents_tick
_arch_verify = _rep_coach._arch_verify
_deep_bucket = _rep_office._deep_bucket
_office_candles = _rep_office._office_candles
_mkt_view = _rep_office._mkt_view
_office_vels = _rep_office._office_vels
_live_px = _rep_office._live_px
_wake_note = _rep_office._wake_note
_market_wake = _rep_office._market_wake
_office_candle_refresh = _rep_office._office_candle_refresh
_intake_reg = _rep_office._intake_reg
_intake_dex = _rep_office._intake_dex
_intake_pass = _rep_office._intake_pass
_intake_after = _rep_office._intake_after
_intake_view = _rep_office._intake_view
_office_seat_payload = _rep_office._office_seat_payload
_office_cycle_log = _rep_office._office_cycle_log
_office_fresh = _rep_office._office_fresh
_office_load_pass = _rep_office._office_load_pass
_social_cache = _rep_office._social_cache
_social_flush = _rep_office._social_flush
_research_tick = _rep_office._research_tick
_seat_wake_maybe = _rep_office._seat_wake_maybe
_office_state = _rep_office._office_state
_office_lat = _rep_office._office_lat
_office_ledger = _rep_office._office_ledger
_office_real = _rep_office._office_real
_office_ctx = _rep_office._office_ctx
_office_warden = _rep_office._office_warden
_office_reap = _rep_office._office_reap
_office_chart_view = _rep_office._office_chart_view
_office_bars = _rep_office._office_bars
_office_positions = _rep_office._office_positions
_hub_publish = _rep_office._hub_publish
_net_stats = _rep_office._net_stats
_office_light = _rep_office._office_light
_office_pass = _rep_office._office_pass
_agents_real = _rep_office._agents_real
_kernel_row = _rep_office._kernel_row
_agent_inherit_rows = _rep_office._agent_inherit_rows
_agents_go_rows = _rep_office._agents_go_rows
_agents_snapshot = _rep_office._agents_snapshot
_duo_tape = _rep_duo._duo_tape
_duo_totals = _rep_duo._duo_totals
_duo_rooms = _rep_duo._duo_rooms
_duo_holding = _rep_duo._duo_holding
_duo_card_legs = _rep_duo._duo_card_legs
_duo_coin_rooms = _rep_duo._duo_coin_rooms
_duo_pin_cap = _rep_duo._duo_pin_cap
_duo_cap = _rep_duo._duo_cap
_duo_phase = _rep_duo._duo_phase
_duo_view = _rep_duo._duo_view
_agents_page_dict = _rep_duo._agents_page_dict
_agents_page_body = _rep_duo._agents_page_body
_fuse_warm = _rep_duo._fuse_warm
_round_move = _rep_duo._round_move
_scenario_stage = _rep_duo._scenario_stage
_pg_pick_ok = _rep_duo._pg_pick_ok
_engine_auto = _rep_duo._engine_auto
_engine_nudge = _rep_duo._engine_nudge
_top_anchor = _rep_duo._top_anchor
_pg_scenario_cards = _rep_duo._pg_scenario_cards
_pg_battle_view = _rep_duo._pg_battle_view
_pg_battle_tick = _rep_duo._pg_battle_tick
_edge_load = _rep_duo._edge_load
_pg_sim_tick = _rep_duo._pg_sim_tick
_brain_patch = _rep_duo._brain_patch
_engine_self_fix = _rep_duo._engine_self_fix
_verdict_acts = _rep_duo._verdict_acts
_retired = _rep_duo._retired
_verdict_build = _rep_duo._verdict_build
_verdict_tick = _rep_duo._verdict_tick

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

import rep_treasury as _rep_treasury   # noqa: E402  🧹 moved by scripts/move-section.py
_circle_start = _rep_treasury._circle_start
_circle = _rep_treasury._circle
_require_owner = _rep_treasury._require_owner
_reserve_plan = _rep_treasury._reserve_plan
_circle_pay = _rep_treasury._circle_pay
_pools = _rep_treasury._pools
_pool_inputs = _rep_treasury._pool_inputs
_pool_plan = _rep_treasury._pool_plan
_code_health_scan = _rep_treasury._code_health_scan
_code_health_run = _rep_treasury._code_health_run
_code_health_loop = _rep_treasury._code_health_loop
_machine_read = _rep_treasury._machine_read
_quick_rep = _rep_treasury._quick_rep
trade_points = _rep_treasury.trade_points
_fee_totals_heal = _rep_treasury._fee_totals_heal
_sol_usd = _rep_treasury._sol_usd
_trade_record = _rep_treasury._trade_record
watch_alerts = _rep_treasury.watch_alerts
_watch_loop = _rep_treasury._watch_loop
after_sell_lessons = _rep_treasury.after_sell_lessons
_money_pulse_build = _rep_treasury._money_pulse_build
_preflight_watch = _rep_treasury._preflight_watch
_verify_store = _rep_treasury._verify_store
_verify_facts = _rep_treasury._verify_facts
_verify_run = _rep_treasury._verify_run
_verify_fill = _rep_treasury._verify_fill
_nft_load = _rep_treasury._nft_load
_public_site = _rep_treasury._public_site
_nft_platforms = _rep_treasury._nft_platforms
_nft_api = _rep_treasury._nft_api
_nft_verify = _rep_treasury._nft_verify
_desk_build = _rep_treasury._desk_build
_desk_build_bg = _rep_treasury._desk_build_bg
_desk_get = _rep_treasury._desk_get
_desk_loop = _rep_treasury._desk_loop
_card_defaults = _rep_treasury._card_defaults
_collection_card_key = _rep_treasury._collection_card_key
_cards_all = _rep_treasury._cards_all
_circle_destinations = _rep_treasury._circle_destinations
_fuse_card_free_sol = _rep_treasury._fuse_card_free_sol
_fuse_send_guard = _rep_treasury._fuse_send_guard
_sol_token_accounts = _rep_treasury._sol_token_accounts
_cronos_batch = _rep_treasury._cronos_batch
_cronos_candidates = _rep_treasury._cronos_candidates
_yt_search = _rep_treasury._yt_search
_spotify_search = _rep_treasury._spotify_search
_internal_ok = _rep_treasury._internal_ok
_agent_sol_to = _rep_treasury._agent_sol_to
_agent_circle_sign_send = _rep_treasury._agent_circle_sign_send
_agent_send_loop = _rep_treasury._agent_send_loop

import rep_market as _rep_market   # noqa: E402  🧹 moved by scripts/move-section.py
_flush_traffic = _rep_market._flush_traffic
_shield_check = _rep_market._shield_check
shield_record = _rep_market.shield_record
_shield_watch = _rep_market._shield_watch
_seasons = _rep_market._seasons
_current_season = _rep_market._current_season
_tier = _rep_market._tier
_owner_wallets = _rep_market._owner_wallets
_granted = _rep_market._granted
wallet_trades = _rep_market.wallet_trades
_season_weeks = _rep_market._season_weeks
_week_of = _rep_market._week_of
_grant = _rep_market._grant
_distribute_drops = _rep_market._distribute_drops
_drops_loop = _rep_market._drops_loop
_is_upload_url = _rep_market._is_upload_url
_feeless_fills = _rep_market._feeless_fills
_chain_fills = _rep_market._chain_fills
_repair_estimates = _rep_market._repair_estimates
_locked_fills = _rep_market._locked_fills
_git = _rep_market._git
_pass_site = _rep_market._pass_site
_agent_pass_rules = _rep_market._agent_pass_rules
_owned_cat = _rep_market._owned_cat
_chart_fill = _rep_market._chart_fill
_rpc_call_ok = _rep_market._rpc_call_ok
_relay_spent = _rep_market._relay_spent
_gold_creator = _rep_market._gold_creator
_quiet = _rep_market._quiet
_ipfs_variants = _rep_market._ipfs_variants
_public_get = _rep_market._public_get
_fetch_first = _rep_market._fetch_first
_logo_thumb = _rep_market._logo_thumb
_token_logo_any = _rep_market._token_logo_any
_probe_latency = _rep_market._probe_latency
_latency_alarm = _rep_market._latency_alarm
_ops_note = _rep_market._ops_note
_three_day_movers = _rep_market._three_day_movers
_post_text = _rep_market._post_text

import rep_intel as _rep_intel   # noqa: E402  🧹 moved by scripts/move-section.py
shield_verdict = _rep_intel.shield_verdict
_funder_of = _rep_intel._funder_of
_mint_authorities = _rep_intel._mint_authorities
_wallet_case = _rep_intel._wallet_case
_coin_case = _rep_intel._coin_case
_shield_features = _rep_intel._shield_features
_ts_num = _rep_intel._ts_num
_shield_of = _rep_intel._shield_of
_fuse_rep = _rep_intel._fuse_rep
_shield_scan_all = _rep_intel._shield_scan_all
_fee_wallet_owner = _rep_intel._fee_wallet_owner
_quote_fee_bps = _rep_intel._quote_fee_bps
_sess = _rep_intel._sess
session_address = _rep_intel.session_address
handle_of = _rep_intel.handle_of
_hygiene_flush = _rep_intel._hygiene_flush
_absorb_intel = _rep_intel._absorb_intel
_live_stats_compute = _rep_intel._live_stats_compute
is_muted = _rep_intel.is_muted
_evm_room = _rep_intel._evm_room
_evm_holding_usd = _rep_intel._evm_holding_usd
_evm_account_for = _rep_intel._evm_account_for
evm_gate = _rep_intel.evm_gate
_week_start = _rep_intel._week_start
_radar_pairs = _rep_intel._radar_pairs
_radar_loop = _rep_intel._radar_loop
_radar_event = _rep_intel._radar_event
_push_snipers_out = _rep_intel._push_snipers_out
_feecat_pins = _rep_intel._feecat_pins
_feecat_fast_trench = _rep_intel._feecat_fast_trench
_notif = _rep_intel._notif
_notif_box = _rep_intel._notif_box
notify = _rep_intel.notify
_session_or_401 = _rep_intel._session_or_401
_legacy_sniper_dedupe = _rep_intel._legacy_sniper_dedupe
_dm_key = _rep_intel._dm_key
_dm_pref = _rep_intel._dm_pref
_pts = _rep_intel._pts
_reward_state = _rep_intel._reward_state
is_verified = _rep_intel.is_verified
invite_code = _rep_intel.invite_code
_code_owner = _rep_intel._code_owner
_unlocks = _rep_intel._unlocks
_war_week = _rep_intel._war_week
_webhook_secret = _rep_intel._webhook_secret
sync_helius_webhook = _rep_intel.sync_helius_webhook
_portfolio_build = _rep_intel._portfolio_build
_fol = _rep_intel._fol
_trust_fill = _rep_intel._trust_fill
_edge_grade = _rep_intel._edge_grade
_edge_price_ok = _rep_intel._edge_price_ok
_refresh_edge_memory = _rep_intel._refresh_edge_memory
_darkside_compute = _rep_intel._darkside_compute
_native_prices = _rep_intel._native_prices
_themes = _rep_intel._themes
_eco_holding_usd = _rep_intel._eco_holding_usd
_meta_words = _rep_intel._meta_words
metas = _rep_intel.metas
_maker_swaps = _rep_intel._maker_swaps
_rpc_wallet_swaps = _rep_intel._rpc_wallet_swaps
_kol_stats = _rep_intel._kol_stats

import rep_fees as _rep_fees   # noqa: E402  🧹 moved by scripts/move-section.py
_fee_cfg = _rep_fees._fee_cfg
_engine_cfg = _rep_fees._engine_cfg
_fee_owner_sol = _rep_fees._fee_owner_sol
_swap_fee_accounts = _rep_fees._swap_fee_accounts
_swap_fee_account = _rep_fees._swap_fee_account
_leg_usd = _rep_fees._leg_usd
_agent_owner = _rep_fees._agent_owner
effective_fee = _rep_fees.effective_fee
_agent_wallets = _rep_fees._agent_wallets
_grow_rows = _rep_fees._grow_rows
_site_landed = _rep_fees._site_landed
_site_fees_total = _rep_fees._site_fees_total
_collective_view = _rep_fees._collective_view
_rounds_cfg = _rep_fees._rounds_cfg
_rounds_pay_to = _rep_fees._rounds_pay_to
_fuse_rounds = _rep_fees._fuse_rounds
_house = _rep_fees._house
_swap_fee_health = _rep_fees._swap_fee_health

import rep_quests as _rep_quests   # noqa: E402  🧹 moved by scripts/move-section.py
app.include_router(_rep_quests.router)
_receipt_rows = _rep_quests._receipt_rows
store_receipt = _rep_quests.store_receipt
_first_active = _rep_quests._first_active
_snaps = _rep_quests._snaps
_perk_tier = _rep_quests._perk_tier
_ids = _rep_quests._ids
primary_of = _rep_quests.primary_of
linked_of = _rep_quests.linked_of
_guard_s = _rep_hq._guard_s
_def_s = _rep_hq._def_s
_war_s = _rep_hq._war_s
_require_admin = _rep_hq._require_admin
_legal_s = _rep_hq._legal_s
_asset_owner = _rep_quests._asset_owner
_fuse_pay_to = _rep_quests._fuse_pay_to
_site = _rep_quests._site
_sol_usd_live = _rep_quests._sol_usd_live
_vault_view = _rep_quests._vault_view
_qs = _rep_quests._qs
_quest_defs = _rep_quests._quest_defs
_streak = _rep_quests._streak
_fuse_quest_stats = _rep_quests._fuse_quest_stats
_quest_raw = _rep_quests._quest_raw
_quest_season = _rep_quests._quest_season
_quest_summary = _rep_quests._quest_summary
_quest_rarity = _rep_quests._quest_rarity
circle_profile_view = _rep_fuse_wallet.circle_profile_view
circle_profile_merge = _rep_fuse_wallet.circle_profile_merge
_prime_tick_inner = _rep_predict._prime_tick_inner
app.include_router(_rep_crews.router)
familia_perps = _rep_crews.familia_perps
familia_kalshi = _rep_crews.familia_kalshi
_fmk_http_get = _rep_crews._fmk_http_get
_fpl_fetch = _rep_crews._fpl_fetch
_fmk_fetch = _rep_crews._fmk_fetch
_sf_client = _rep_prime._sf_client
_crowd_build = _rep_coin_edge._crowd_build

import rep_chat as _rep_chat   # noqa: E402  🧹 moved by scripts/move-section.py
_calls_load = _rep_chat._calls_load
_calls_save = _rep_chat._calls_save
_award_feed_call = _rep_chat._award_feed_call
_record_feed_calls = _rep_chat._record_feed_calls
_call_view = _rep_chat._call_view
_refresh_calls = _rep_chat._refresh_calls
_build_caller_board = _rep_chat._build_caller_board
_react_load = _rep_chat._react_load
_prof = _rep_chat._prof
_profiles_load = _rep_chat._profiles_load
_safe_url = _rep_chat._safe_url
_clean_profile = _rep_chat._clean_profile
_verify_wallet = _rep_chat._verify_wallet
_x_redirect = _rep_chat._x_redirect
_protected_wallets = _rep_chat._protected_wallets
_block_load = _rep_chat._block_load
_block_flush = _rep_chat._block_flush
_block_save = _rep_chat._block_save
_is_blocked = _rep_chat._is_blocked
_record_offenders = _rep_chat._record_offenders
_funders_load = _rep_chat._funders_load
_is_flagged_funder = _rep_chat._is_flagged_funder
_trace_funders = _rep_chat._trace_funders
funder_lookup = _rep_chat.funder_lookup
_chat_load = _rep_chat._chat_load
_display_name = _rep_chat._display_name
_room_mint = _rep_chat._room_mint
_holding_usd = _rep_chat._holding_usd
_chat_message_to_sign = _rep_chat._chat_message_to_sign
feeless_post = _rep_chat.feeless_post
chat_system_post = _rep_chat.chat_system_post
_fee_usd = _rep_chat._fee_usd
_is_staff = _rep_chat._is_staff
_alpha_allowed = _rep_chat._alpha_allowed
_norm = _rep_chat._norm
_spam_check = _rep_chat._spam_check
_guard_log = _rep_chat._guard_log
_track_pin = _rep_chat._track_pin
_internal_key = _rep_chat._internal_key
_ecosystem_mints = _rep_chat._ecosystem_mints

import rep_core as _rep_core   # noqa: E402  🧹 moved by scripts/move-section.py
_empty_store = _rep_core._empty_store
_load = _rep_core._load
_save = _rep_core._save
_store_flush = _rep_core._store_flush
_store_flush_loop = _rep_core._store_flush_loop
_save_now = _rep_core._save_now
resolve_creator = _rep_core.resolve_creator
_creator_key = _rep_core._creator_key
resolve_funding_source = _rep_core.resolve_funding_source
_push_feed = _rep_core._push_feed
token_outcome = _rep_core.token_outcome
score_creator = _rep_core.score_creator
_hygiene = _rep_core._hygiene
fetch_token_markets = _rep_core.fetch_token_markets
trust_verdict = _rep_core.trust_verdict
_apply_markets = _rep_core._apply_markets
_refresh_all_markets = _rep_core._refresh_all_markets
_loop_lag_dump = _rep_core._loop_lag_dump
upload_cap = _rep_core.upload_cap
_ip_hit = _rep_core._ip_hit
_coin_card = _rep_core._coin_card
_early_buy = _rep_core._early_buy
chain_rpc_url = _rep_core.chain_rpc_url
_ping_chain = _rep_core._ping_chain
resolve_evm_creator = _rep_core.resolve_evm_creator
_refresh_globe = _rep_core._refresh_globe
_any_agent_wallets = _rep_core._any_agent_wallets
_vapid = _rep_core._vapid
_push_load = _rep_core._push_load
_push_save = _rep_core._push_save
_sub_id = _rep_core._sub_id
_push_prefs = _rep_core._push_prefs
_inbox_alert = _rep_core._inbox_alert
_send_push = _rep_core._send_push
_in_quiet = _rep_core._in_quiet
_evaluate_alerts = _rep_core._evaluate_alerts
