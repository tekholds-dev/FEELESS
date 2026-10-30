"""
FEELESS Cats — the paper-trading agent lab backend.

Paper trading against REAL live markets: every entry and exit is marked at the
actual DexScreener SOL-native price of a real Solana pair at that moment, with a
1% per-side fee/slippage haircut on the BALANCE (real money); P&L is the price move only, fees tracked apart (feesSol).
Only the money is simulated — never the prices.

File-backed JSON store, zero external dependencies, standalone FastAPI app.
"""
import env_loader  # noqa: F401  (must run before reading os.environ)
import agent_wallet as _aw
import agent_trade as _at
import cat_agent as _ca
import cat_browser as _cb
_AGENT_MAX = 4   # cats with their own wallet per owner wallet (owner 2026-10-29: "up to 4 cats per user"; cat_fund.MAX_CATS)
import asyncio
import json
import re
import os
import math
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx
import http_ctx
http_ctx.install()   # ⚡ every httpx client in this process shares ONE TLS context (a new client re-read the CA bundle)
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import feecat_brain
import launch_cat as _lc
import cat_policy as _cp
import cat_recovery as _recovery
import agent_pay as _ap
import cat_real as _real   # 💵 real-money cats = option A: the user's wallet signs every trade (docs/DECISIONS.md #2)
import cat_orders as _co   # 🧭 a General AI cat's plain-words orders → one guarded proposal
import cat_model as _cm
import cat_tools as _ct   # 🧰 FEELESS-first read-only tools for general agents
import cat_vault as _cv   # 🔐 a general agent's saved logins + 🖼 media drawer
import cat_keys as _ck   # 🔐 a cat's API drawer (sealed keys, never sent to a page)

DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
STORE_PATH = DATA_DIR / 'feecats.json'

TICK_SECONDS = 20
# ✂ 2026-10-23 (P2 #1): the old catalog showed Claude / GPT / Grok labels that only ever ran the rule engine — one honest row now. Real AI
# brains are picked in Launch a Cat (`brains` / OpenRouter); FEELESS's own models come from cat_model.
RULE_ENGINE = {'id': 'rules', 'provider': 'FEELESS', 'label': 'FEELESS rule engine'}
STRATEGY_LABELS = {'balanced': 'Momentum', 'momentum': 'Breakouts', 'conservative': 'Scalping', 'signals': 'On-chain signals', 'trend': 'Trend following', 'conviction': 'Conviction'}


def _empty_store():
    return {'cats': {}, 'events': []}


def honest_brain(cat):
    """✂ A cat saved under the retired catalog (a 'GPT-6 Astra' label that only ran the rule engine) reads as what it is. Pure (tests)."""
    if cat.get('brainsCfg') or cat.get('modelBrain') or cat.get('isLeader') or cat.get('brain') == RULE_ENGINE['id']:
        return cat
    cat.update(brain=RULE_ENGINE['id'], brainLabel=RULE_ENGINE['label'],
               brainProfile={**(cat.get('brainProfile') or {}), 'provider': RULE_ENGINE['provider'], 'status': 'live', 'available': False})
    return cat


def _load() -> dict:
    if STORE_PATH.exists():
        try:
            store = json.loads(STORE_PATH.read_text())
            for c in (store.get('cats') or {}).values():
                honest_brain(c)
            return store
        except Exception:
            pass
    return _empty_store()


# 🔒 The engine loads every cat, works for minutes, then saves its whole copy: anything an owner did meanwhile was wiped (owner 2026-10-30: a new agent wallet vanished
# seconds after it was made). What an owner's action sets is kept here and laid over every save, so an old copy can never lose a wallet, a funding or a limit.
OWNER_KEYS = ('agentWallet', 'agentFunded', 'creditPaid', 'recovery', 'recoverySet', 'recoveryConfirmedAt', 'limits', 'taskCap', 'ownerId', 'mode', 'realWallet', 'budgetSol', 'paperByOwner')
_KEPT: dict = {}


def keep_owned(cat):
    """Remember the owner's fields of `cat` as they stand now (after an owner's action)."""
    _KEPT[cat['id']] = json.loads(json.dumps({k: cat[k] for k in OWNER_KEYS if k in cat}))


def _save(store: dict):
    for cid, kept in _KEPT.items():
        c = (store.get('cats') or {}).get(cid)
        if not c:
            continue
        have = {x.get('sig') for x in c.get('creditPaid') or []}
        for x in kept.get('creditPaid') or []:   # bought credit an old copy has not seen: added, never lost
            if x.get('sig') not in have and c.get('brainsCfg'):
                c['brainsCfg']['credit'] = round((c['brainsCfg'].get('credit') or 0) + float(x.get('usd') or 0), 6); c.pop('brainPaused', None)
        for k in OWNER_KEYS:
            if k in kept:
                c[k] = json.loads(json.dumps(kept[k]))
            else:
                c.pop(k, None)
    STORE_PATH.write_text(json.dumps(store, indent=2))


_ECHO_OLD = re.compile(r':?\s*under \d{1,2} words(?:, numbers)?')
_INTERNAL = re.compile(r'(?:🪟\s*)?\b(?:NEXA(?: SICARIO)?|OSSY|G4)\b', re.I)


def public_words(text):
    """🔒 P0-QUICK #4: internal model names (NEXA / OSSY / G4) never reach users — every public sink (events, receipts, Fee's chat posts,
    position reasons on /api/cats/leader) says 'FeeCat AI'. The owner's HQ reads the `nexa` flag instead. Pure (tests)."""
    if not isinstance(text, str):
        return text
    text = _ECHO_OLD.sub('', _INTERNAL.sub('🔮 FeeCat AI', text))   # receipts written before nexa.real_why still carry her placeholder
    return text.replace('her AI desk', 'FeeCat AI')


def _no_keys(obj):
    """🔐 every cat on its way out: the sealed API keys stay on the server — the page gets the drawer (provider · last 4 · wired)."""
    if isinstance(obj, list):
        return [_no_keys(x) for x in obj]
    if isinstance(obj, dict):
        out = {k: _no_keys(v) for k, v in obj.items() if k not in ('apiKeys', 'logins', 'ownerId', 'recovery')}   # 🔒 ownerId is the owner's control key — it never leaves the server
        if 'brains' in obj:   # ☁ each mind's own cloud is its owner's private notes — only the owner's /work view carries it
            out.pop('minds', None)
        if 'apiKeys' in obj or ('brainsCfg' in obj and 'ownerId' in obj):
            out['apiDrawer'] = _ck.public(obj)
        if obj.get('logins'):   # 🔐 sealed passwords never leave the server — site · username · when only
            out['logins'] = _cv.public_logins(obj)
        return out
    return obj


def _pub(obj):
    """🔒 A public response with every internal model name scrubbed (old events / reasons written before the scrub included)."""
    return json.loads(public_words(json.dumps(_no_keys(obj), ensure_ascii=False)))


def _log_event(store, cat, kind, detail, pnl=None, pair=None, price=None, market_cap=None, entry_market_cap=None):
    store['events'].insert(0, {
        'id': uuid.uuid4().hex, 'catId': cat['id'], 'catName': cat['name'],
        'type': kind, 'detail': public_words(detail), 'ts': time.time() * 1000,
        'pnlSol': pnl, 'decisionSource': 'selected_brain' if cat.get('brainProfile', {}).get('available') else 'rule_engine',
        'brainLabel': public_words(cat.get('brainLabel')), 'pairAddress': pair, 'priceNative': price,
        # Persisted with the paper receipt so shared cards never invent MC data later.
        'marketCapUsd': market_cap, 'entryMarketCapUsd': entry_market_cap,
    })
    store['events'] = store['events'][:200]


DESK_SCENES = ('globe', 'creek', 'forest', 'night')   # 🎨 CatCockpit.SCENES (change both)
BRIEF_EVERY = 3600   # 📜 a general agent's brief: you edit it, or its minds propose one, at most once an hour
MODEL_LOCK_SEC = 24 * 3600   # 🔁 a cat's models can be switched 24 h after it was made
FEE_PER_SIDE = 0.01   # the default paper fee per side — HQ › Core › house fees sets the live one (RULES['feePerSidePct'])


def fee_side():
    """FeeCat's paper fee per side as a fraction (HQ › Core can change it: 0–5 %)."""
    return float(RULES.get('feePerSidePct', FEE_PER_SIDE * 100)) / 100

ENGINE_VERSION = 'arena-v1'   # 2026-10-15: arena / agent coins only — the paper trail restarted (old store archived once)
LEADER_ID = 'leader'
POOL_URL = 'http://127.0.0.1:5077/api/reputation/fuses/feecat-pool'   # 🐱 arena + agent coins only (2026-10-15)
RULES = {'minLiquidity': 40_000, 'minVolume24h': 100_000, 'minMarketCap': 150_000, 'maxMarketCap': 50_000_000,
         'minAgeHours': 3, 'coreMinAgeHours': 72, 'h1Min': 3, 'h1Max': 40, 'h6Max': 120, 'h24Max': 400, 'minBuySellRatio': 1.2,
         'maxPositions': 5, 'cooldownHours': 2, 'feePerSidePct': 1.0,
         # safety gates at entry
         'maxM5Chase': 8, 'maxTop10Pct': 35, 'maxInsiderPct': 20, 'maxDevPct': 10, 'maxSnipers': 15, 'maxBundled': 10,
         # Trench Lord v2 — thesis-based position management (see run_engine):
         # open with a starter, add on healthy dips (re-averaging the entry), hold while the thesis holds,
         # take profit in pieces, let a runner ride, and cut only when the thesis breaks or the hard stop hits.
         # v3 discipline: cut losers fast, never average down, add only to a winner, let the runner ride.
         'starterFraction': 0.6, 'add1At': -18, 'add1Fraction': 0.0, 'add2At': -32, 'add2Fraction': 0.0,
         'pyramidAt': 15, 'pyramidFraction': 0.4,
         'hardStop': -20, 'lowCapHardStop': -25, 'lowCapMc': 300_000,
         'protectAt': 20, 'timeStopHours': 2, 'timeStopMin': 8,
         'takeProfit1': 40, 'takeProfit1Sell': 0.4, 'takeProfit2': 100, 'takeProfit2Sell': 0.4, 'runnerTrail': 25,
         'liqPullPct': 30, 'dumpSellRatio': 2.0, 'thesisVolKeep': 0.3, 'deadMoneyHours': 12, 'maxHoldHours': 48,
         'maxExposure': 0.4,
         # fresh-launch lane at half size
         'freshMinMinutes': 10, 'freshMinLiquidity': 15_000, 'freshSize': 0.5}
_intel_cache = {}


async def _jup_audit(http, mint):
    """🪐 Jupiter's public token audit for one coin → {top10, dev, authority} (None when Jupiter has nothing)."""
    try:
        rows = (await http.get('https://lite-api.jup.ag/tokens/v2/search', params={'query': mint}, timeout=6)).json()
        t = next((r for r in rows or [] if r.get('id') == mint), None)
    except Exception:
        return None
    if not t:
        return None
    a = t.get('audit') or {}
    top = a.get('topHoldersPercentage')
    return {'top10': float(top) if top is not None else None, 'dev': float(a.get('devBalancePercentage') or 0),
            'authority': a.get('mintAuthorityDisabled') is False or a.get('freezeAuthorityDisabled') is False}


async def _safety(http, p):
    """Rug/insider gate from FEELESS on-chain intel. Returns (ok, why, conviction 0.5–1.5)."""
    mint = (p.get('baseToken') or {}).get('address')
    if not mint:
        return False, 'no mint', 0
    hit = _intel_cache.get(mint)
    # a complete read is kept 30 min; an EMPTY one (the RPC scan didn't reach the holders) only 60s — it used to block that coin for 30 min,
    # so 2026-10-21 Fee passed coins every scan and bought nothing ("no holder intel yet" on every one)
    if hit and time.time() - hit[0] < (1800 if (hit[1] or {}).get('top10Pct') is not None else 60):
        d = hit[1]
    else:
        try:
            d = (await http.get(f'http://127.0.0.1:5077/api/reputation/intel/solana/{mint}', timeout=25)).json()
        except Exception:
            d = None
        if not d or d.get('top10Pct') is None:   # 🪐 the agents' fallback: Jupiter's own holder audit (top 10, dev, live authority)
            j = await _jup_audit(http, mint)
            if j and j.get('authority'):
                _intel_cache[mint] = (time.time(), d)
                return False, 'mint or freeze authority is still live', 0
            if j and j.get('top10') is not None:
                d = {**(d or {}), 'top10Pct': j['top10'], 'devHoldingPct': j.get('dev') or 0, '_jup': True}
        _intel_cache[mint] = (time.time(), d)
    if not d or d.get('top10Pct') is None:
        return False, 'no holder intel yet', 0
    R = {**RULES, **_ENTRY_TUNE}
    snip, bund = len(d.get('sniperWallets') or []), len(d.get('bundledWallets') or [])
    checks = [(_num(d.get('top10Pct')) <= R['maxTop10Pct'], f"top 10 wallets hold {_num(d.get('top10Pct')):.0f}%"),
              (_num(d.get('insidersHoldingPct')) <= R['maxInsiderPct'], f"insiders hold {_num(d.get('insidersHoldingPct')):.0f}%"),
              (_num(d.get('devHoldingPct')) <= R['maxDevPct'], f"dev holds {_num(d.get('devHoldingPct')):.0f}%"),
              (snip <= R['maxSnipers'], f'{snip} snipers'), (bund <= R['maxBundled'], f'{bund} bundled wallets'),
              # Learned from the FEELESS blocklist: a coin whose snipers were bankrolled by a known
              # repeat funder is the same crew running the same play — Fee never touches it.
              (not d.get('flaggedFunders'), f"{len(d.get('flaggedFunders') or {})} sniper(s) funded by a known repeat rug/snipe funder"),
              # Intel desk: a known crew (funder + puppets) inside the launch with rugs on record, or a high-threat crew, is a veto.
              (not any(r.get('rugs') or (r.get('threat') or 0) >= 60 for r in d.get('knownRings') or []),
               'known crew inside: ' + ', '.join(f"ring {r.get('id')} ({r.get('size')} wallets, {r.get('rugs') or 0} rugs)" for r in (d.get('knownRings') or [])[:2]))]
    for ok, why in checks:
        if not ok:
            return False, why, 0
    # Creator record (brutal scoring): never buy from flagged/risky creators or launch farms.
    try:
        rep = (await http.get(f'http://127.0.0.1:5077/api/reputation/token/solana/{mint}', timeout=10)).json()
    except Exception:
        rep = {}
    if rep.get('badge') in ('flagged', 'risky') or rep.get('serialLauncher'):
        return False, f"creator is {rep.get('badge')}" + (' (launch farm)' if rep.get('serialLauncher') else ''), 0
    # Cleaner distribution → more conviction.
    conviction = 1.5 - min(1.0, _num(d.get('top10Pct')) / R['maxTop10Pct']) * 0.6 - (0.2 if snip > 5 else 0) - (0.2 if bund else 0)
    if rep.get('badge') == 'trusted':
        conviction += 0.25
    if d.get('_jup'):   # holders from Jupiter only (no launch read): smaller bet
        conviction = min(conviction, 0.6)
    return True, f"top10 {_num(d.get('top10Pct')):.0f}%, insiders {_num(d.get('insidersHoldingPct')):.0f}%, {snip} snipers, {bund} bundled, creator {rep.get('badge') or 'unknown'}", max(0.5, min(1.75, round(conviction, 2)))


from fnum import plain as _num  # noqa: E402


_POOL_META: dict = {'duo': {}}


def setup_gate(p):
    """🐱 FEECAT ENTERS LIKE THE AGENTS AND OSSY / G4 (owner, 2026-10-18: "running with the latest methods — HH/HL, germ"). Pure.
    A coin the agents' chart read covers must show one of the three setups (HH/HL pullback · on its germ floor · a held breakout) and must not
    be a bad entry (gun line / chase / spike / SKIP); OSSY / G4 saying SELL on it in the last 30 min = out; their BUY = first (×1.2).
    A coin with no read yet keeps her own lanes' verdict (she never trades MORE because a read is missing). → (ok, why, mult, setups)."""
    rd, dw = p.get('_read') or None, p.get('_duo') or None
    if dw and dw.get('action') == 'SELL':
        return False, f"🤝 {dw.get('who')} said sell", 1.0, []
    if rd:
        if rd.get('bad'):
            return False, f"🔫 {str(rd['bad'])[:60]}", 1.0, []
        if not rd.get('setups'):
            return False, 'no HH/HL · germ · FVG support · breakout setup', 1.0, []
    tags = list((rd or {}).get('setups') or [])
    if dw and dw.get('action') == 'BUY':
        return True, f"🤝 {dw.get('who')} bought it", 1.2, tags
    return True, '', 1.0, tags


SETUP_WORD = {'hhhl': 'HH/HL pullback', 'germ': 'on its germ floor', 'fvg': 'on its FVG support', 'breakout': 'held breakout'}


async def _market_candidates(http):
    """🐱 FEE TAKES ONLY ARENA / AGENT COINS (owner, 2026-10-15): her pool is what the ten agents judged READY / CONTENDING and what the Arena
    ranks — `GET /fuses/feecat-pool` on the reputation service — never the raw market feed. Each coin's live pair is read so her own safety
    gates still decide; the pool being empty means she waits."""
    try:
        d_ = (await http.get(POOL_URL, timeout=6)).json() or {}
        rows = d_.get('rows') or []
        _POOL_META['duo'] = d_.get('duo') or _POOL_META.get('duo') or {}
        _POOL_META['limits'] = d_.get('limits') or _POOL_META.get('limits') or {}
    except Exception:
        rows = []
    # 🔗 each coin's deepest SOL pool (2026-10-16: 15 of 39 pool coins came with a TRUMP / ZEC / USDC / stock pool and failed "not SOL-quoted")
    by_mint = {r['mint']: r for r in rows if r.get('mint')}
    pairs = await _sol_pairs(http, list(by_mint))
    out = []
    for m, p in pairs.items():
        r = by_mint.get(m) or {}
        out.append({**p, '_src': r.get('src'), '_srcWhy': r.get('why'), '_read': r.get('read'), '_duo': r.get('duo'), '_status': r.get('status')})
    return out


async def _sol_pairs(http, mints):
    """{mint: its deepest SOL / WSOL-quoted live pair} — ONE DexScreener /tokens/v1 call per 30 coins."""
    out = {}
    for i in range(0, len(mints), 30):
        try:
            r = await http.get(f"https://api.dexscreener.com/tokens/v1/solana/{','.join(mints[i:i + 30])}")
            rows = r.json() if r.status_code == 200 else []
        except Exception:
            rows = []
        for p in rows if isinstance(rows, list) else []:
            m = (p.get('baseToken') or {}).get('address')
            if m not in mints or ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
                continue
            if m not in out or _num((p.get('liquidity') or {}).get('usd')) > _num((out[m].get('liquidity') or {}).get('usd')):
                out[m] = p
    return out


NEXA_MIN_LIQ = 5000.0   # 🪟 trench law: a pool under $5K can't be exited — her YES never overrides that


def nexa_lane(p):
    """🪟 NEXA's YES is the lane: (score, reason) when the pool can be exited, else (None, why). Pure (tests)."""
    liq = _num((p.get('liquidity') or {}).get('usd'))
    if liq < NEXA_MIN_LIQ:
        return None, f'🪟 NEXA said yes but the pool is under ${NEXA_MIN_LIQ / 1000:.0f}K — no exit'
    return 1.0, '🪟 NEXA said YES'


def nexa_drives(cat, p):
    """🪟🐱 NEXA TRADES AS FEECAT (owner, 2026-10-23: "I wanted nexa trading in feecat's tab AS FEECAT"): on her own cat, her fresh YES is the
    call — FeeCat's soft second opinions (chart setup, the desk's skip, Fuse / proof / setup-memory vetoes) step aside. The rug guards never
    do: the $5K pool floor, the holder check, discipline, daily loss, cooldown, exposure. Paper only. Pure (tests)."""
    return bool(p.get('_nexa') and _cm.model_of(cat))


async def _pair_prices(http, pair_addresses):
    out = {}
    for i in range(0, len(pair_addresses), 30):
        try:
            r = await http.get(f'https://api.dexscreener.com/latest/dex/pairs/solana/{",".join(pair_addresses[i:i + 30])}')
            for p in (r.json() or {}).get('pairs') or []:
                out[p.get('pairAddress')] = p
        except Exception:
            pass
    return out


def _qualifies(p, now):
    if ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
        return None, 'not SOL-quoted'
    liq = _num((p.get('liquidity') or {}).get('usd'))
    vol = _num((p.get('volume') or {}).get('h24'))
    mc = _num(p.get('marketCap') or p.get('fdv'))
    ch = p.get('priceChange') or {}
    m5, h1, h6, h24 = _num(ch.get('m5')), _num(ch.get('h1')), _num(ch.get('h6')), _num(ch.get('h24'))
    tx = (p.get('txns') or {}).get('h1') or {}
    buys, sells = _num(tx.get('buys')), _num(tx.get('sells'))
    age_h = (now * 1000 - _num(p.get('pairCreatedAt'), now * 1000)) / 3_600_000
    R = {**RULES, **_ENTRY_TUNE}
    checks = [(liq >= R['minLiquidity'], 'liquidity'), (vol >= R['minVolume24h'], 'volume'),
              (R['minMarketCap'] <= mc <= R['maxMarketCap'], 'market cap band'), (age_h >= max(R['minAgeHours'], R.get('coreMinAgeHours', 0)), 'too new'),
              (m5 > 0, '5m momentum'), (m5 <= R['maxM5Chase'], 'chasing a 5m spike'), (R['h1Min'] <= h1 <= R['h1Max'], '1h move'), (0 < h6 <= R['h6Max'], '6h trend'),
              (h24 <= R['h24Max'], 'overextended'), (sells == 0 or buys / max(sells, 1) >= R['minBuySellRatio'], 'buy pressure')]
    for ok, why in checks:
        if not ok:
            return None, why
    score = h1 * math.log10(max(vol, 10)) * min(buys / max(sells, 1), 3)
    reason = f"1h +{h1:.1f}%, 6h +{h6:.1f}%, {buys:.0f}/{sells:.0f} buys/sells, ${liq/1000:.0f}K liq, ${vol/1000:.0f}K vol"
    return score, reason


def _fmt_usd(v):
    v = _num(v)
    return f'${v/1e6:.2f}M' if v >= 1e6 else f'${v/1e3:.1f}K' if v >= 1e3 else f'${v:.2f}'


def _buy_analysis(p, size, sym, safety='', conviction=1.0):
    ch = p.get('priceChange') or {}
    tx = (p.get('txns') or {}).get('h1') or {}
    b, s = _num(tx.get('buys')), _num(tx.get('sells'))
    liq, mc, vol = _num((p.get('liquidity') or {}).get('usd')), _num(p.get('marketCap') or p.get('fdv')), _num((p.get('volume') or {}).get('h24'))
    age_h = (time.time() * 1000 - _num(p.get('pairCreatedAt'), time.time() * 1000)) / 3_600_000
    R = {**RULES, **_ENTRY_TUNE}
    return (f"🐱 Fee is buying ${sym} — {size} SOL (paper trade, live price).\n\n"
            f"Why this one passed every rule:\n"
            f"• Order flow: {b:.0f} buys vs {s:.0f} sells in the last hour ({(b / max(b + s, 1)) * 100:.0f}% buys) — buyers are in control.\n"
            f"• Momentum: 5m {_num(ch.get('m5')):+.1f}%, 1h {_num(ch.get('h1')):+.1f}%, 6h {_num(ch.get('h6')):+.1f}% — trending up without being vertical (my cap is +{R['h1Max']}% 1h / +{R['h6Max']}% 6h).\n"
            f"• Liquidity: {_fmt_usd(liq)} ({(liq / mc * 100) if mc else 0:.1f}% of {_fmt_usd(mc)} market cap) — deep enough to get out.\n"
            f"• Activity: {_fmt_usd(vol)} traded in 24h; pool is {age_h:.1f}h old (I skip anything under {max(R['minAgeHours'], R.get('coreMinAgeHours', 0)):g}h).\n"
            f"• Holders (FEELESS on-chain intel): {safety or 'checked'} — I skip anything with top-10 over {R['maxTop10Pct']}%, insiders over {R['maxInsiderPct']}%, dev over {R['maxDevPct']}% or heavy sniping/bundling.\n"
            f"• Size: {conviction}× conviction — cleaner holder distribution earns a bigger position.\n\n"
            f"Plan (trench + stock mindset): this is a {int(R['starterFraction'] * 100)}% starter. If it dips {R['add1At']}% and {R['add2At']}% from here while liquidity, volume and buyers still hold, "
            f"I add and re-average my entry instead of panic-selling. I take {int(R['takeProfit1Sell'] * 100)}% profit at +{R['takeProfit1']}% and more at +{R['takeProfit2']}%, "
            f"then let the rest run with a {R['runnerTrail']}% trailing stop that never drops below break-even. "
            f"I only cut early if the thesis breaks (liquidity pulled {R['liqPullPct']}%+, sellers dumping {R['dumpSellRatio']:.0f}:1, or volume dies while red); hard stop {R['hardStop']}% from my average. "
            f"Every trade pays 1% each way so you see real costs.\n\nNot financial advice — this is how a disciplined bot thinks, out loud.")


LEARN_BOUNDS = {'runnerTrail': (20, 45), 'takeProfit1': (30, 90)}


# ---- Hourly entry tuning (bounded): tighten after a bad day, freeze + study after a good one -----
ENTRY_BOUNDS = {'minLiquidity': (40_000, 150_000), 'maxM5Chase': (3, 12), 'maxSnipers': (5, 20), 'maxTop10Pct': (20, 40)}
_ENTRY_TUNE: dict = {}


def _tune_entries(store):
    cat = store['cats'].get(LEADER_ID)
    if not cat:
        return
    L = cat.setdefault('learn', {'params': {}, 'log': [], 'missed': 0, 'good': 0})
    E = {**{k: RULES[k] for k in ENTRY_BOUNDS}, **(L.get('entry') or {})}
    day = [e for e in cat.get('exits', []) if time.time() - e['exitAt'] < 86400 and e.get('pnlSol') is not None]
    note = None
    if len(day) < 4:
        mode = 'warming'
    else:
        wins = [e for e in day if e['pnlSol'] > 0]; wr = len(wins) / len(day); net = sum(e['pnlSol'] for e in day)
        # Last time she opened anything: open positions, or the most recent exit.
        last_open = max([p.get('openedAt', 0) for p in cat.get('positions', [])] + [e['exitAt'] for e in cat.get('exits', [])] + [0])
        if not cat.get('positions') and time.time() - last_open > 3 * 3600:
            # Drought: rules tightened so far nothing qualifies. Ease halfway back to defaults —
            # safety checks (liquidity pull, dev dump, blocklist) are untouched.
            mode = 'drought-relax'
            for k in ENTRY_BOUNDS:
                E[k] = round(E[k] + (RULES[k] - E[k]) * 0.5)
            note = f"No entries for {int((time.time() - last_open) / 3600)}h — easing entry rules halfway back to defaults."
        elif wr < 0.4 and time.time() - (L.get('tightenedAt') or 0) < 6 * 3600:
            mode = 'holding'  # tighten at most once per 6h; the same bad day must not compound every hour
        elif wr < 0.4:
            mode = 'tightening'; L['tightenedAt'] = time.time()
            E['minLiquidity'] = round(E['minLiquidity'] * 1.15)
            E['maxM5Chase'] -= 1; E['maxSnipers'] -= 2; E['maxTop10Pct'] -= 3
            note = f"24h win rate {wr:.0%} over {len(day)} trades — tightening entries."
        elif wr >= 0.6 and net > 0:
            mode = 'studying'
            L['study'] = {'at': time.time(), 'winRate': round(wr * 100), 'netSol': round(net, 4), 'winners': [{'symbol': e['symbol'], 'why': e.get('why'), 'change': e.get('changeAtExit')} for e in wins[:10]]}
            note = f"24h win rate {wr:.0%} (+{net:.3f} SOL) — freezing settings and studying {len(wins)} winners."
        else:
            mode = 'steady'
            for k in ENTRY_BOUNDS:
                E[k] = round(E[k] + (RULES[k] - E[k]) * 0.25)
    for k, (lo, hi) in ENTRY_BOUNDS.items():
        E[k] = max(lo, min(hi, E[k]))
    L['entry'] = E; L['mode'] = mode; L['tunedAt'] = time.time()
    # 💪 auto-strength (hourly): her own 24h + 72h record decides ×0.6 / ×1 / ×1.15 size — cold at once, hot only when proven twice
    was = (cat.get('strength') or {}).get('level')
    st = feecat_brain.strength(cat.get('exits', []), time.time(), cat.get('strength'), cat.get('discipline'))
    cat['strength'] = {**st, 'at': time.time()}
    if st['level'] != (was or 'steady'):
        _log_event(store, cat, 'LEARN', f"Strength {st['label']}: {st['why']}.")
    _ENTRY_TUNE.clear(); _ENTRY_TUNE.update(E)
    if note:
        L['log'].insert(0, {'at': time.time(), 'note': note, 'symbol': '', 'missed': mode == 'tightening'}); L['log'] = L['log'][:40]
        _log_event(store, cat, 'LEARN', note)


async def _tune_loop():
    await asyncio.sleep(30)
    while True:
        try:
            store = _load(); _tune_entries(store); _save(store)
        except Exception as exc:
            print('tune error', exc)
        await asyncio.sleep(3600)


def _params(cat):
    return {**RULES, **((cat.get('learn') or {}).get('params') or {})}


def _learn(store, cat):
    """Adapt exits from what happened AFTER Fee sold. Runners it cut early → loosen; good exits → tighten back."""
    done = [e for e in cat.get('exits', []) if time.time() - e['exitAt'] >= 6 * 3600 and not e.get('scored')]
    if not done:
        return
    L = cat.setdefault('learn', {'params': {}, 'log': [], 'missed': 0, 'good': 0})
    P = _params(cat)
    for e in done:
        e['scored'] = True
        # A profit-taking or patience exit is "too early" when the coin kept running long after.
        early = e['peakAfter'] >= 60 and any(k in e['why'] for k in ('trailing', 'profit', 'dead money', 'max hold'))
        if early:
            L['missed'] += 1
            P['runnerTrail'] = min(LEARN_BOUNDS['runnerTrail'][1], P['runnerTrail'] + 5)
            P['takeProfit1'] = min(LEARN_BOUNDS['takeProfit1'][1], P['takeProfit1'] + 10)
            note = f"Sold {e['symbol']} at {e['changeAtExit']:+.1f}%, it ran another +{e['peakAfter']:.0f}%. Giving winners more room: runner trail {P['runnerTrail']}%, first profit at +{P['takeProfit1']}%."
        else:
            L['good'] += 1
            for k in LEARN_BOUNDS:
                P[k] = round(P[k] + (RULES[k] - P[k]) * 0.25, 2)  # drift back toward the defaults
            note = f"Exit on {e['symbol']} held up (best after sell +{e['peakAfter']:.0f}%, low {e['lowAfter']:.0f}%). Keeping discipline."
        L['params'] = {k: P[k] for k in LEARN_BOUNDS}
        L['log'].insert(0, {'at': time.time(), 'note': note, 'symbol': e['symbol'], 'missed': early})
        L['log'] = L['log'][:40]
        _log_event(store, cat, 'LEARN', note)


FEE_OPENERS = {   # 💅 her voice (owner, 2026-10-23: "make Fee's chat litty — her girly convos"): one opener per post, the numbers stay hers
    'buy': ('ok besties, hear me out 💅', 'not me aping again 🙈', 'mother is entering 👑', 'girls, we\'re so back ✨'),
    'win': ('told y\'all 💖', 'secured the bag, obviously 💅', 'that\'s called taste ✨', 'hot girl profit szn 🔥'),
    'loss': ('ugh, he ghosted me 🙄', 'not my finest moment 🫠', 'we move, bestie 💔', 'rules said bye, so bye 👋'),
    'add': ('doubling down on my fave 💕', 'more of what works, babe ✨'),
}


def fee_voice(text):
    """→ Fee's post with ONE opener in her voice, picked by what happened (buy / win / loss / add) and the text itself (stable). Pure (tests)."""
    t = str(text or '')
    kind = ('add' if 'Added' in t else 'win' if ('took profit' in t or ('sold' in t and 'P&L +' in t)) else 'loss' if 'sold' in t else 'buy')
    pool = FEE_OPENERS[kind]
    return f"{pool[sum(map(ord, t)) % len(pool)]}\n{t}"


def _post_as_fee(pair_address, text, register_call=False):
    try:
        key = (DATA_DIR / 'internal.key').read_text().strip()
        r = httpx.post('http://127.0.0.1:5077/api/reputation/internal/fee-post', json={'pairAddress': pair_address, 'text': public_words(fee_voice(text)), 'registerCall': register_call},
                       headers={'x-feeless-internal': key}, timeout=15)
        if r.status_code != 200:
            print('fee post rejected', r.status_code, r.text[:200])
    except Exception as exc:
        print('fee post failed', exc)


def _notify_real(cat, p):
    """💵 Tell the cat's real wallet a proposal is waiting (inbox + phone, via reputation's internal notify). Never blocks the engine."""
    try:
        key = (DATA_DIR / 'internal.key').read_text().strip()
        verb = f"BUY ${p['symbol']} with {p['sol']} SOL" if p['side'] == 'buy' else f"SELL {round(p['fraction'] * 100)}% of your ${p['symbol']}"
        httpx.post('http://127.0.0.1:5077/api/reputation/internal/notify', headers={'x-feeless-internal': key}, timeout=2,
                   json={'address': cat['realWallet'], 'kind': 'cat', 'text': f"🐱 {cat.get('name') or 'Your cat'} " + (f"is doing it from its own wallet: {verb} — {p['why'][:80]}." if (cat.get('agentWallet') or {}).get('mode') == 'auto'
                         else f"wants to {verb} — {p['why'][:80]}. " + ('Approve within 15 min — its wallet sends it.' if cat.get('agentWallet') else 'Approve within 15 min; your wallet signs.')),
                         'url': '/terminal/feecat/agents', 'once': f"cat-prop-{p['id']}"})
    except Exception:
        pass


def _close(store, cat, pos, price_native, why, fraction=1.0, market_cap=None):
    if _real.is_real(cat):   # 💵 a REAL cat: its exit becomes a proposal for the coin the user really bought (sell X % — the wallet signs)
        p_ = _real.propose(cat, 'sell', pos.get('mint'), pos.get('pairAddress'), pos.get('symbol'), why, time.time(), fraction=fraction, px=price_native)
        if p_:
            _notify_real(cat, p_)
    gross = pos['notionalSol'] * fraction * (price_native / pos['entryPriceNative'])
    # 🎯 TRUE FILL on the sell: price impact against the pool (entry liquidity, SOL→$ at entry) — what a wallet would receive
    r_usd = _num(pos.get('entryLiq')) / 2; su = _num(pos.get('solUsdAtEntry'))
    if r_usd > 0 and su > 0:
        gross = gross / (1 + gross * su / r_usd)
    proceeds = gross * (1 - fee_side())
    # 🔒 Same rule as real cards: P&L = the price move on the money that reached the pool (fees apart). The balance still
    # receives `proceeds` (real money after the sell fee); both sides' fees are tracked in `feesSol`, never inside P&L.
    pnl = round(gross - pos['notionalSol'] * fraction, 6)
    fee_sol = (pos['costSol'] - pos['notionalSol']) * fraction + (gross - proceeds)
    cat['feesSol'] = round(cat.get('feesSol', 0) + fee_sol, 6)
    if fraction < 1:
        pos['realizedPartialSol'] = round(pos.get('realizedPartialSol', 0) + pnl, 6)
        pos.setdefault('costBasisSol', pos['costSol'])
        pos['notionalSol'] = round(pos['notionalSol'] * (1 - fraction), 6)
        pos['costSol'] = round(pos['costSol'] * (1 - fraction), 6)
    cat['balanceSol'] = round(cat['balanceSol'] + proceeds, 6)
    cat['realizedPnlSol'] = round(cat.get('realizedPnlSol', 0) + pnl, 6)
    cat['totalPnlSol'] = cat['realizedPnlSol']
    cat['volumeSol'] = round(cat.get('volumeSol', 0) + gross, 6)
    cat['wins' if pnl >= 0 else 'losses'] = cat.get('wins' if pnl >= 0 else 'losses', 0) + 1
    cat['xp'] = cat.get('xp', 0) + (20 if pnl >= 0 else 6)
    cat['level'] = max(1, cat['xp'] // 100 + 1)
    cat.setdefault('dailyLoss', {})
    day = time.strftime('%Y-%m-%d')
    if pnl < 0:
        cat['dailyLoss'][day] = round(cat['dailyLoss'].get(day, 0) - pnl, 6)
    cat.setdefault('cooldowns', {})[pos['pairAddress']] = time.time()
    bc = cat.get('brainsCfg')
    if bc:   # 🚀 a cat with brains: 'profit pays' settles what its model calls owe from a winning sale (fees apart from P&L, like every fee)
        su_ = _num(pos.get('solUsdAtEntry'))
        paid = _lc.settle(bc, pnl * su_) if su_ > 0 else 0.0
        if paid > 0:
            cat['balanceSol'] = round(cat['balanceSol'] - paid / su_, 6)
            cat['brainFeesUsd'] = round(cat.get('brainFeesUsd', 0) + paid, 6)
        if fraction >= 1 and pos.get('brainBy'):
            rec = bc.setdefault('record', {}).setdefault(pos['brainBy'], {'n': 0, 'won': 0, 'pnlSol': 0.0})
            rec['n'] += 1; rec['won'] += 1 if pnl + pos.get('realizedPartialSol', 0) >= 0 else 0
            rec['pnlSol'] = round(rec['pnlSol'] + pnl + pos.get('realizedPartialSol', 0), 6)
    if fraction >= 1:
        cat.setdefault('exits', []).append({'pairAddress': pos['pairAddress'], 'symbol': pos['symbol'], 'exitPx': price_native, 'exitAt': time.time(),
                                            'why': why, 'pnlSol': pnl, 'changeAtExit': round((price_native / pos['entryPriceNative'] - 1) * 100, 2), 'peakAfter': 0.0, 'lowAfter': 0.0})
        cat['exits'] = cat['exits'][-60:]
        # File the whole trade (partial profits included) under its setup so the next entry learns from it.
        total_pnl = round(pnl + pos.get('realizedPartialSol', 0), 6)
        ret = total_pnl / max(pos.get('costBasisSol') or pos['costSol'], 1e-9) * 100
        cat['setupMemory'] = feecat_brain.remember(cat.get('setupMemory') or [], pos.get('setup'), ret, total_pnl, time.time())
    cat.setdefault('pnlHistory', []).append({'value': cat['realizedPnlSol'], 't': time.time()})
    cat['pnlHistory'] = cat['pnlHistory'][-60:]
    closed = cat.get('wins', 0) + cat.get('losses', 0)
    cat['winRate'] = round(cat.get('wins', 0) / closed * 100) if closed else None
    change = (price_native / pos['entryPriceNative'] - 1) * 100
    part = f'{int(fraction * 100)}% of ' if fraction < 1 else ''
    _log_event(store, cat, 'SELL', f"Sold {part}{pos['symbol']} at {change:+.1f}% — {why}. P&L {pnl:+.4f} SOL on the price move (fees apart, paper, live price).", pnl, pos.get('pairAddress'), price_native, market_cap, pos.get('entryMarketCapUsd'))
    if cat.get('isLeader') and pos.get('pairAddress'):
        held = (time.time() - pos.get('openedAt', time.time())) / 3600
        verdict = 'Took the win.' if pnl >= 0 else 'The thesis broke, so I cut it — protecting capital beats hoping.'
        if fraction < 1:
            _post_as_fee(pos['pairAddress'], f"🐱 Fee took profit on ${pos['symbol']}: sold {int(fraction * 100)}% at {change:+.1f}% — {why}. Locked {pnl:+.4f} SOL.\nThe rest keeps riding with a trailing stop, and it can't turn into a loss: the floor is my break-even.")
            return
        _post_as_fee(pos['pairAddress'], f"🐱 Fee sold ${pos['symbol']} at {change:+.1f}% after {held:.1f}h — {why}.\nP&L {pnl:+.4f} SOL on the price move — fees shown apart (peak was {pos.get('peakChange', 0):+.1f}%).\n{verdict} The rules decide the exit, not feelings.")


def _fresh_qualifies(p, now):
    """Fresh-launch lane (the 'could be a moon' read): brand-new coin with a real narrative footprint
    (X account + website), buyers in control and volume moving fast relative to its liquidity."""
    if ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
        return None, 'not SOL-quoted'
    age_min = (now * 1000 - _num(p.get('pairCreatedAt'), now * 1000)) / 60_000
    info = p.get('info') or {}
    socials = {(x.get('type') or '').lower() for x in info.get('socials') or []}
    liq = _num((p.get('liquidity') or {}).get('usd')); vh1 = _num((p.get('volume') or {}).get('h1'))
    t1 = (p.get('txns') or {}).get('h1') or {}; buys, sells = _num(t1.get('buys')), _num(t1.get('sells'))
    m5 = _num((p.get('priceChange') or {}).get('m5'))
    checks = [(RULES['freshMinMinutes'] <= age_min < RULES['minAgeHours'] * 60, 'not in fresh window'), (liq >= RULES['freshMinLiquidity'], 'thin liquidity'),
              ('twitter' in socials, 'no X account'), (bool(info.get('websites')), 'no website'), (buys >= 1.5 * max(sells, 1), 'buyers not in control'),
              (vh1 >= 0.5 * liq, 'volume not moving'), (0 < m5 <= RULES['maxM5Chase'], '5m momentum')]
    for ok, why in checks:
        if not ok:
            return None, why
    return vh1 / max(liq, 1) * min(buys / max(sells, 1), 3), f"fresh launch {age_min:.0f}m old: X + site, {buys:.0f}/{sells:.0f} buys/sells, 1h vol {vh1 / max(liq, 1):.1f}× liquidity"


LEARN_SIZE = 0.25        # 🎓 learning-lane trades are a quarter of a normal size (paper)
LEARN_MIN_LIQ = 15_000


AGENT_LANE_KEYS = ('mcMin', 'mcMax', 'minAgeH', 'maxAgeH', 'minVol1h', 'poolMin')


def agent_lane(base, own=None):
    """🐱🤖 The agents' band for her agents lane, with HER own overrides on top (HQ › Fee › agents lane; None / missing = the agents' value)."""
    out = {k: _num((base or {}).get(k)) for k in AGENT_LANE_KEYS}
    for k, v in (own or {}).items():
        if k in AGENT_LANE_KEYS and v is not None and _num(v) >= 0:
            out[k] = _num(v)
    return out


def clean_lane(raw):
    """🐱 Her agents-lane overrides from HQ: only the band keys, a number ≥ 0; empty / None = follow the agents (key dropped)."""
    out = {}
    for k, v in (raw or {}).items():
        if k in AGENT_LANE_KEYS and v not in (None, '') and _num(v, -1) >= 0:
            out[k] = min(_num(v), 1e9)
    return out


def _agents_qualifies(p, now, lim):
    """🐱🤖 FEECAT = THE AGENTS + OSSY / G4 (owner, 2026-10-19: "same intake, same agents, she has my agents settings but I can tune hers"):
    a coin the ten agents put READY / CONTENDING is judged on the agents' own band (live cap, age, pool, 1h volume) instead of her old core /
    fresh lanes — those refused all 39 of their coins (cap band 16, liquidity 11, too new 7). Not dumping, not chasing, buyers not outsold.
    Her safety scan, setup gate, discipline and proof gate still decide after this. READY = full size, CONTENDING = half."""
    if ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
        return None, 'not SOL-quoted'
    R = {**RULES, **_ENTRY_TUNE}
    age_h = (now * 1000 - _num(p.get('pairCreatedAt'), now * 1000)) / 3_600_000
    mc = _num(p.get('marketCap') or p.get('fdv')); liq = _num((p.get('liquidity') or {}).get('usd')); vh1 = _num((p.get('volume') or {}).get('h1'))
    t5 = (p.get('txns') or {}).get('m5') or {}; b5, s5 = _num(t5.get('buys')), _num(t5.get('sells'))
    m5 = _num((p.get('priceChange') or {}).get('m5'))
    mx_age = lim.get('maxAgeH') or 0
    checks = [(not lim.get('mcMin') or mc >= lim['mcMin'], 'under the agents\' MC floor'), (not lim.get('mcMax') or mc <= lim['mcMax'], 'over the agents\' MC top'),
              (age_h >= (lim.get('minAgeH') or 0), 'younger than the agents\' min age'), (not mx_age or mx_age == float('inf') or age_h <= mx_age, 'older than the agents\' max age'),
              (liq >= (lim.get('poolMin') or 8000), 'under the agents\' pool floor'), (vh1 >= (lim.get('minVol1h') or 0), 'under the agents\' 1h volume'),
              (m5 >= -5, 'dumping (5m)'), (m5 <= R['maxM5Chase'], 'chasing (5m)'), (b5 >= s5 * 0.8, 'sellers lead the 5m')]
    for ok, why in checks:
        if not ok:
            return None, why
    full = p.get('_status') == 'READY'
    return (vh1 / max(liq, 1) + 1) * (1.0 if full else 0.6), f"🤖 agents lane: {p.get('_status') or 'CONTENDING'} on the agents' desk · {age_h:.1f}h old · {'full' if full else 'half'} size"


def _learn_qualifies(p, now):
    """🎓 LEARNING LANE (owner, 2026-10-16: "the cat isn't trading"): her core lane only buys coins 3+ days old and her fresh lane only < 3h
    launches with X + site — her pool (the agents' + the Arena's coins) is mostly 3h–3 days old, so she sat out every coin. This lane takes
    that gap at LEARN_SIZE: a SOL pool ≥ $15K, buyers ahead (≥ 1.3× sells in the hour), not dumping (5m ≥ −2%), not a spike (5m ≤ her
    chase cap), 1h volume ≥ a third of the pool. Her safety scan, discipline, proof gate and setup memory still decide after this."""
    if ((p.get('quoteToken') or {}).get('symbol') or '').upper() not in ('SOL', 'WSOL'):
        return None, 'not SOL-quoted'
    R = {**RULES, **_ENTRY_TUNE}
    age_h = (now * 1000 - _num(p.get('pairCreatedAt'), now * 1000)) / 3_600_000
    liq = _num((p.get('liquidity') or {}).get('usd')); vh1 = _num((p.get('volume') or {}).get('h1'))
    t1 = (p.get('txns') or {}).get('h1') or {}; buys, sells = _num(t1.get('buys')), _num(t1.get('sells'))
    m5, h1 = _num((p.get('priceChange') or {}).get('m5')), _num((p.get('priceChange') or {}).get('h1'))
    checks = [(R['minAgeHours'] <= age_h < max(R['minAgeHours'], R.get('coreMinAgeHours', 0)), 'not in the learning window'), (liq >= LEARN_MIN_LIQ, 'thin liquidity'),
              (buys >= 1.3 * max(sells, 1), 'buyers not ahead'), (-2 <= m5 <= R['maxM5Chase'], '5m momentum'), (vh1 >= liq / 3, 'volume not moving'), (h1 <= R['h1Max'], '1h move')]
    for ok, why in checks:
        if not ok:
            return None, why
    return vh1 / max(liq, 1) * min(buys / max(sells, 1), 3) * 0.5, f"🎓 learning lane: {age_h:.0f}h old, {buys:.0f}/{sells:.0f} buys/sells, 1h vol {vh1 / max(liq, 1):.1f}× pool — quarter size"


async def _fvg(http, pair_address, price_usd):
    """Bullish fair value gap on 5m candles: a bar whose low sits above the high two bars earlier leaves
    an unfilled gap. Price trading back inside the most recent such gap is a retest entry."""
    try:
        c = (await http.get(f'http://127.0.0.1:5099/api/candles/solana/{pair_address}', params={'interval': '5m'})).json().get('candles') or []
    except Exception:
        return None
    c = c[-40:]
    for i in range(len(c) - 1, 1, -1):
        lo, hi = c[i - 2][2], c[i][3]  # gap between bar i-2's high and bar i's low
        if hi > lo:
            filled = any(x[3] <= lo for x in c[i + 1:])
            if not filled and lo <= price_usd <= hi:
                return lo, hi
            return None
    return None


def _thesis(pos, live, R):
    """Is the reason Fee bought still true? Returns (broken_reason | None, ok_to_add, h1 volume vs entry)."""
    liq_now = _num((live.get('liquidity') or {}).get('usd'))
    vol_h1 = _num((live.get('volume') or {}).get('h1'))
    t5 = (live.get('txns') or {}).get('m5') or {}
    t1 = (live.get('txns') or {}).get('h1') or {}
    b5, s5, b1, s1 = _num(t5.get('buys')), _num(t5.get('sells')), _num(t1.get('buys')), _num(t1.get('sells'))
    change = (_num(live.get('priceNative')) / pos['entryPriceNative'] - 1) * 100
    entry_liq, entry_vol = _num(pos.get('entryLiq')), _num(pos.get('entryVolH1'))
    vol_ratio = vol_h1 / entry_vol if entry_vol else None
    if entry_liq and liq_now and liq_now < entry_liq * (1 - R['liqPullPct'] / 100):
        return f"liquidity pulled ({_fmt_usd(entry_liq)} → {_fmt_usd(liq_now)})", False, vol_ratio
    if s5 >= 10 and s5 >= b5 * R['dumpSellRatio'] and change < 0:
        return f'sellers dumping ({s5:.0f} sells vs {b5:.0f} buys in 5m)', False, vol_ratio
    if vol_ratio is not None and vol_ratio < R['thesisVolKeep'] and change < -10:
        return f'volume dried up ({vol_ratio:.0%} of entry-hour volume) while red', False, vol_ratio
    if s1 >= 40 and s1 > b1 * 1.6 and change < 0:
        return f'sellers own the hour ({s1:.0f} sells vs {b1:.0f} buys)', False, vol_ratio
    ok_to_add = b5 >= s5 and (vol_ratio is None or vol_ratio >= 0.5) and (not entry_liq or liq_now >= entry_liq * 0.85)
    return None, ok_to_add, vol_ratio


async def _crowd_feed(http):
    """Coins FEELESS's elite traders bought in the last 6h (counts only), so she learns from the best users."""
    try:
        r = await http.get('http://127.0.0.1:5077/api/reputation/crowd/elite-flow', timeout=4)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


async def _duo_read(http):
    """🐱🤝 Her one duo AI read (every 10 min, reputation service `/cats-ai`): pairs BOTH models said to skip / bank. {} when unread or stale."""
    try:
        r = await http.get('http://127.0.0.1:5077/api/reputation/cats-ai', timeout=3)
        d = r.json() if r.status_code == 200 else {}
        return d if time.time() - float(d.get('read') or 0) <= 900 else {'nexa': d.get('nexa')}   # 🪟 her cats judge her read's age themselves
    except Exception:
        return {}


async def _fuse_discover(http):
    """The Fuse runner engine's view (gated runners + sources + coins that failed a gate). Served from its warm cache."""
    try:
        r = await http.get('http://127.0.0.1:5077/api/reputation/runners/discover', timeout=4)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


def creator_adjust(ranked, reps, rejections):
    """Fresh launches lean on WHO made them: a clean creator (rep engine) is a better chance → score ×1.25 + cited; a suspect /
    high-risk creator → out. Unknown creators keep their score. Only ever filters or re-ranks, never adds an entry."""
    out = []
    for score, reason, p in ranked:
        rep = reps.get((p.get('baseToken') or {}).get('address')) if p.get('_fresh') else None
        if rep in ('suspect', 'high'):
            rejections['creator rep'] = rejections.get('creator rep', 0) + 1
            continue
        out.append((score * 1.25, f"{reason} · 🧼 clean creator", p) if rep == 'clean' else (score, reason, p))
    return out


async def _creator_check(ranked, rejections):
    mints = [(p.get('baseToken') or {}).get('address') for _, _, p in ranked if p.get('_fresh')][:10]
    if not mints:
        return ranked
    try:
        async with httpx.AsyncClient(timeout=5) as http:
            recs = (await http.get('http://127.0.0.1:5077/api/reputation/edge', params={'mints': ','.join(m for m in mints if m)})).json()
        recs = recs.get('edge', recs) if isinstance(recs, dict) else {}
        reps = {m: ((r or {}).get('runner') or {}).get('creatorRep') for m, r in recs.items() if isinstance(r, dict)}
    except Exception:
        reps = {}
    return creator_adjust(ranked, reps, rejections)


_MODELS = {'at': 0, 'rows': None}


async def _or_models():
    """OpenRouter's public model list, cached an hour (the last good copy is kept when it fails)."""
    if _MODELS['rows'] is not None and time.time() - _MODELS['at'] < 3600:
        return _MODELS['rows']
    try:
        async with httpx.AsyncClient(timeout=15) as h:
            r = await h.get('https://openrouter.ai/api/v1/models')
        if r.status_code == 200:
            _MODELS.update(at=time.time(), rows=_lc.catalog(r.json().get('data') or []))
    except Exception:
        pass
    return _MODELS['rows'] or _lc.catalog([])


def _brains_live():
    return os.environ.get('LAUNCH_CAT_LIVE', '').lower() in ('1', 'true', 'on') and bool(os.environ.get('OPENROUTER_API_KEY'))


SORT_SYS = ('You are the new lead model of a FEELESS agent. Below is its old memory, one numbered note per line. Keep only notes that will still help '
            'you decide well (facts, lessons, patterns that held up); drop stale, duplicate or wrong ones. Answer ONLY JSON: {"keep": [<note numbers>]}')
SORT_MAX = 60


def _kept(text, n):
    """The note numbers the model kept, in range and unique — anything unreadable keeps everything (a sort never loses memory by mistake)."""
    m = re.search(r'\{.*\}', str(text or ''), re.S)
    try:
        keep = json.loads(m.group(0)).get('keep') if m else None
    except ValueError:
        keep = None
    if not isinstance(keep, list):
        return list(range(n))
    return sorted({int(i) for i in keep if str(i).lstrip('-').isdigit() and 0 <= int(i) < n})


async def _sort_cloud(cat_id, model):
    """🧠 owner 2026-10-30: on a model swap the new lead sorts the old cloud — keeps what helps, deletes the rest. One call, charged like any other."""
    await asyncio.sleep(1)   # after the switch itself is saved
    cat = _load()['cats'].get(cat_id)
    items = ((cat or {}).get('brainsCfg') or {}).get('cloud') or []
    if not items:
        return
    items = items[-SORT_MAX:]
    note = lambda c: c.get('text') or f"{c.get('word', '')} ${c.get('sym', '')} {c.get('why', '')}"
    lines = '\n'.join(f'{i}: {note(c)}'[:240] for i, c in enumerate(items))
    try:
        own = _ck.key_for(cat, 'openrouter', data_dir=DATA_DIR)
        text, cost = await _or_call(model, [{'role': 'system', 'content': SORT_SYS}, {'role': 'user', 'content': lines}], max_tokens=400, **({'key': own} if own else {}))
    except Exception as e:   # the model is down: its memory stays exactly as it was
        print(f'cloud sort failed for {cat_id}: {e}')
        return
    keep = _kept(text, len(items))
    store = _load(); cat = store['cats'].get(cat_id)
    if not cat or not cat.get('brainsCfg'):
        return
    cat['brainsCfg']['cloud'] = [items[i] for i in keep]
    if not own:
        _lc.charge(cat['brainsCfg'], cost or 0)
    _log_event(store, cat, 'LEARN', f"🧠 {model.split('/')[-1]} sorted its memory: kept {len(keep)} of {len(items)} notes")
    _save(store)


_OR_LAST: dict = {}   # why the last model call came back empty, in plain words


async def _agent_usdc(http, addr):
    """(usdc, sol) live in an agent's wallet."""
    h_ = await http.get(f'{_at.TRADE}/holdings/{addr}', timeout=15)
    if h_.status_code != 200:
        return 0.0, 0.0
    tk_ = {t_.get('mint'): float(t_.get('amount') or 0) for t_ in ((h_.json() or {}).get('tokens') or [])}
    return tk_.get(_cf_usdc, 0.0), tk_.get(_at.SOL, 0.0)


_cf_usdc = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
_THINK_AT: dict = {}
THINK_MIN_USDC, THINK_SWAP_SOL, THINK_KEEP_SOL = 0.30, 0.012, 0.006   # under $0.30 of USDC it swaps about $1 of its own SOL, always keeping gas


async def _thinking_money(cat):
    """💳 USDC ready for this agent's model calls: its wallet's own, topped up from its own SOL when low. No manual swap for the owner. → usdc available."""
    w_ = cat.get('agentWallet') or {}; addr = w_.get('address'); now = time.time()
    async with httpx.AsyncClient(timeout=25) as http:
        usdc, sol = await _agent_usdc(http, addr)
        amount = min(THINK_SWAP_SOL, sol - THINK_KEEP_SOL)
        if usdc >= THINK_MIN_USDC or amount < 0.002 or now - _THINK_AT.get(cat['id'], 0) < 180:
            return usdc
        _THINK_AT[cat['id']] = now
        try:
            q_ = await http.post(f'{_at.TRADE}/quote', json={'input_mint': _at.SOL, 'output_mint': _cf_usdc, 'amount': f'{amount:.6f}', 'wallet': addr, 'slippage_bps': _at.SLIP_BPS}, timeout=20)
            qj = q_.json() if q_.status_code == 200 else {}
            if qj.get('input_mint') != _at.SOL or qj.get('output_mint') != _cf_usdc or not (qj.get('quote') or {}).get('transaction'):
                return usdc
            await _at._circle_post(http, cat, {'key': f"feeless-{cat['id']}-think-{round(now)}", 'tx': qj['quote']['transaction']})
        except (ValueError, httpx.HTTPError) as e:
            print(f"[agent think swap] {cat['id']}: {str(e)[:120]}")
            return usdc
        for _ in range(8):
            await asyncio.sleep(3)
            now_usdc, _sol = await _agent_usdc(http, addr)
            if now_usdc > usdc:
                return now_usdc
    return usdc


async def _wallet_call(cat, model, messages, max_tokens, ceiling):
    """💳 One model call paid from this agent's own USDC (agent_pay.py). → (text, $ paid); ('', 0.0) = nothing paid, the next route takes it."""
    w_ = cat.get('agentWallet') or {}
    try:
        async with httpx.AsyncClient(timeout=70) as h:
            body = {'model': _ap.provider_model(model), 'messages': messages, 'max_tokens': int(max_tokens or 1000)}
            r = await h.post(_ap.PROVIDER, json=body)
            if r.status_code == 400:
                body['model'] = _ap.FALLBACK_MODEL
                r = await h.post(_ap.PROVIDER, json=body)
            if r.status_code != 402:
                return '', 0.0
            doc, entry = _ap.pick_quote(r.headers.get('payment-required'), ceiling)
            s_ = await h.post('http://127.0.0.1:5077/api/reputation/internal/agent-x402-pay', headers=_internal_headers(), json={'catId': cat['id'], 'walletId': w_.get('circleId'), 'address': w_.get('address'), 'entry': entry})
            if s_.status_code != 200:
                return '', 0.0
            head = _ap.payment_header(doc, entry, s_.json()['signedTransaction'])
            r2 = await h.post(_ap.PROVIDER, json=body, headers={'PAYMENT-SIGNATURE': head, 'X-PAYMENT': head})
            if r2.status_code != 200:
                print(f"[agent pay] {cat['id']}: provider {r2.status_code} {r2.text[:120]}")
                return '', 0.0
            return ((r2.json().get('choices') or [{}])[0].get('message') or {}).get('content') or '', int(entry['amount']) / _ap.USDC_SCALE
    except (ValueError, KeyError, httpx.HTTPError) as e:
        print(f"[agent pay] {cat['id']}: {str(e)[:120]}")
        return '', 0.0


async def _groq_backup(messages, max_tokens=None):
    """🛟 FEELESS covers an agent when OpenRouter can't (owner 2026-10-30): Groq's free tier answers instead. Costs the agent nothing. → text ('' = no backup either)."""
    key = os.environ.get('GROQ_API_KEY', '').strip()
    if not key:
        return ''
    try:
        async with httpx.AsyncClient(timeout=40) as h:
            r = await h.post('https://api.groq.com/openai/v1/chat/completions', headers={'Authorization': f'Bearer {key}'},
                             json={'model': os.environ.get('GROQ_MODEL', '').strip() or BACKUP_MODEL, 'messages': messages, 'max_tokens': min(int(max_tokens or 2000), 4000), 'temperature': 0.2})
        if r.status_code == 200:
            return ((r.json().get('choices') or [{}])[0].get('message') or {}).get('content') or ''
        _OR_LAST['err'] = 'OpenRouter is out of credit and the free backup is busy. Nothing was charged. Try again in a minute.' if r.status_code == 429 else f'OpenRouter is out of credit and the backup refused the call ({r.status_code}). Nothing was charged.'
    except Exception:
        _OR_LAST['err'] = 'OpenRouter is out of credit and the backup did not answer. Nothing was charged.'
    return ''


async def _or_call(model, messages, max_tokens=None, effort=None, key=None, backup=False):
    """One decision from OpenRouter; returns (text, $ it cost). The cost is OpenRouter's own report, else the price list estimate.
    `key` = the cat owner's own OpenRouter key from its API drawer (they pay OpenRouter; FEELESS's key is not used)."""
    est = next((m['perDecision'] for m in ((_MODELS['rows'] or {}).get('models') or []) if m['id'] == model), 0.0)
    try:
        async with httpx.AsyncClient(timeout=40) as h:
            r = await h.post('https://openrouter.ai/api/v1/chat/completions', headers={'Authorization': f"Bearer {key or os.environ.get('OPENROUTER_API_KEY')}"},
                             json={'model': model, 'messages': messages, 'max_tokens': max_tokens or _lc.OUT_TOK, 'temperature': 0.2, **({'reasoning': {'effort': effort}} if effort else {}), 'usage': {'include': True}})
        if r.status_code != 200:   # a refused call costs nothing and says why (it used to read as 'no answer' and bill the estimate)
            _OR_LAST['err'] = 'The AI provider account is out of credit. Add credit at OpenRouter, then ask again. Nothing was charged.' if r.status_code == 402 else f'The AI provider refused the call ({r.status_code}). Nothing was charged.'
            if r.status_code == 402:   # the owner hears it (once a day) and credit sales pause
                try:
                    async with httpx.AsyncClient(timeout=8) as h2:
                        await h2.post('http://127.0.0.1:5077/api/reputation/internal/openrouter-check', headers=_internal_headers())
                except Exception:
                    pass
                if backup and not key:   # never on the owner's own key: that bill is theirs to fix
                    text_ = await _groq_backup(messages, max_tokens)
                    _OR_LAST['backup'] = bool(text_)
                    return text_, 0.0
            return '', 0.0
        d = r.json()
        text = ((d.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
        return text, float((d.get('usage') or {}).get('cost') or est)
    except Exception:
        return '', 0.0


async def _brain_decide(store, cat, kind, sym, case, owner=None):
    """🚀 Launch a Cat: ask the cat's brain(s). Returns (word, by, why) or None = the rule engine decides (calls off / no credit)."""
    b = cat.get('brainsCfg')
    if not b:
        return None
    now = time.time()
    own_key = _ck.key_for(cat, 'openrouter', data_dir=DATA_DIR)   # 🔐 its owner's own OpenRouter key: their bill, no FEELESS credit, no owner switch
    if not own_key and not _lc.can_ask(b):
        if b.get('billing') == 'payg' and cat.get('status') == 'running':
            cat['status'] = 'stopped'; cat['brainPaused'] = 'out of model credit — top up to start again'
            _log_event(store, cat, 'STOPPED', f"{cat['name']} paused: its model credit is used up (pay as you go). Top up to start it again.")
        return None
    if not own_key and not _brains_live():
        _lc.note(b, kind, sym, 'RULES', 'rule engine', 'model calls are off (owner switch) — the rule engine decided', 0, now)
        return None
    models = [owner] if owner else _lc.who_asks(b, b.get('asks') or 0)
    answers, partner, why, cost = [], None, '', 0.0
    for m in models:
        text, usd = await _or_call(m, _lc.ask_messages(b, case, partner), **({'key': own_key} if own_key else {}), **({'effort': b['efforts'][m]} if (b.get('efforts') or {}).get(m) else {}))
        w, why = _lc.parse_word(text, kind)
        if not own_key:
            _lc.charge(b, usd)
        cost += usd
        answers.append((m, w))
        partner = f"{w or 'no answer'}: {why}"
    word = _lc.merge(b, answers, kind)
    by = ' + '.join(m.split('/')[-1] for m in models)
    if _lc.cloud_check(b, sym, word, by, why, now, together=answers if len(answers) > 1 else None):   # ☁ both brains agree → the head cloud
        _log_event(store, cat, 'LEARN', f"☁ head cloud: both brains say {word} ${sym}")
    _lc.note(b, kind, sym, word, by, why, cost, now)
    _log_event(store, cat, 'LEARN', f"🧠 {by}: {word} ${sym} — {why or 'no reason given'}")
    return word, models[-1], why


async def run_engine(store, cats):
    now = time.time()
    async with httpx.AsyncClient(timeout=10) as http:
        held = sorted({p['pairAddress'] for c in cats for p in c['positions'] if p.get('pairAddress')}
                      | {e['pairAddress'] for c in cats for e in c.get('exits', []) if now - e['exitAt'] < 24 * 3600})
        prices = await _pair_prices(http, held) if held else {}
        candidates, fuse_view, crowd_feed, duo = await asyncio.gather(_market_candidates(http), _fuse_discover(http), _crowd_feed(http), _duo_read(http))
    duo_avoid, duo_exit = set(duo.get('avoid') or []), set(duo.get('exit') or [])   # 🐱🤝 only what BOTH AI models agreed on
    if isinstance((duo.get('nexa') or {}).get('talk'), list):   # 💬 her desk words → bubbles on FeeCat's public charts (scrubbed by _pub on the way out)
        store['aiTalk'] = duo['nexa']['talk'][-24:]
    nexa_read = _cm.read_of(duo.get('nexa'), now)   # 🪟 a cat assigned to NEXA buys her favored coins + sells her exits (fresh reads only)
    # 🪟 NEXA'S LANE (owner, 2026-10-23: "nexa not trading"): her desk said YES to 6 coins while FeeCat's own lanes passed 0 of 42 — FeeCat only
    # walks her own list, so NEXA never traded. Her fresh YES now IS the lane (it replaces the age / cap-band filters); every guard still runs:
    # the chart's setup gate, a $5K pool floor, the rug / safety check, cooldowns, discipline. Her picks the feed didn't carry are fetched.
    nx_fav = set(nexa_read['favor']) if nexa_read and any(_cm.model_of(c_) for c_ in cats) else set()
    if nx_fav:
        have_ = {p_.get('pairAddress') for p_ in candidates}
        miss_ = sorted(nx_fav - have_)[:12]
        if miss_:
            try:
                async with httpx.AsyncClient(timeout=10) as http_n:
                    r_n = await http_n.get(f'https://api.dexscreener.com/latest/dex/pairs/solana/{",".join(miss_)}')
                    candidates = list(candidates) + [p_ for p_ in (r_n.json().get('pairs') or []) if p_.get('pairAddress') in nx_fav]
            except Exception:
                pass
    ranked, rejections = [], {}
    for p in candidates:
        score, reason = (None, None)
        if p.get('pairAddress') in nx_fav:
            score, reason = nexa_lane(p)
            if score is None:
                rejections[reason] = rejections.get(reason, 0) + 1
                continue
            p['_nexa'] = True
        if score is None and p.get('_src') == 'agents':   # 🐱🤖 the agents' coins: the agents' band (+ her overrides), not her old lanes
            score, reason = _agents_qualifies(p, now, agent_lane(_POOL_META.get('limits'), (store['cats'].get(LEADER_ID) or {}).get('agentLane')))
            if score is not None:
                p['_agentsLane'] = True
        if score is None and p.get('_src') != 'agents' and not p.get('_nexa'):
            score, reason = _qualifies(p, now)
        if score is None and p.get('_src') != 'agents' and not p.get('_nexa'):
            fscore, freason = _fresh_qualifies(p, now)
            if fscore is not None:
                p['_fresh'] = True
                score, reason = fscore, freason
            else:
                lscore, lreason = _learn_qualifies(p, now)
                if lscore is not None:   # 🎓 the gap her two lanes skip (3h – 3 days): a quarter-size paper trade she learns from
                    p['_learn'] = True
                    score, reason = lscore, lreason
        if score is not None:
            ok_, why_, mult_, tags_ = setup_gate(p)
            if not ok_ and p.get('_nexa'):   # 🪟 her YES outranks the chart's second opinion (rug guards still run below)
                ok_, why_, mult_ = True, f'🪟 over the chart ({why_})', 1.0
            if not ok_:
                rejections[why_] = rejections.get(why_, 0) + 1
                continue
            p['_setups'] = tags_
            words_ = ' + '.join(SETUP_WORD[t] for t in tags_ if t in SETUP_WORD)
            reason = ' · '.join(x for x in (why_, f'🎯 {words_}' if words_ else '', reason) if x)
            ranked.append((score * mult_, reason, p))
        else:
            rejections[reason] = rejections.get(reason, 0) + 1
    ranked = await _creator_check(ranked, rejections)
    _duo_learn(store, _POOL_META.get('duo') or {}, now)
    store['scan'] = {'at': now, 'scanned': len(candidates), 'passed': len(ranked), 'rejections': rejections,
                     'top': [{'symbol': (p.get('baseToken') or {}).get('symbol'), 'reason': r, 'url': p.get('url'), 'pairAddress': p.get('pairAddress'),
                             'mint': (p.get('baseToken') or {}).get('address'), 'setups': p.get('_setups') or [], 'read': p.get('_read'), 'duo': p.get('_duo')} for _, r, p in ranked[:5]]}
    ranked.sort(key=lambda x: -x[0])
    for cat in cats:
        for e in cat.get('exits', []):
            live = prices.get(e['pairAddress'])
            if live and now - e['exitAt'] < 24 * 3600 and e.get('exitPx'):
                ch = (_num(live.get('priceNative')) / e['exitPx'] - 1) * 100
                e['peakAfter'] = round(max(e.get('peakAfter', 0), ch), 2)
                e['lowAfter'] = round(min(e.get('lowAfter', 0), ch), 2)
        _learn(store, cat)
        R = _params(cat)
        for pos in list(cat['positions']):
            live = prices.get(pos.get('pairAddress'))
            if not live:
                continue
            px = _num(live.get('priceNative'))
            if px <= 0:
                continue
            pos.setdefault('firstEntryPriceNative', pos['entryPriceNative'])
            pos.setdefault('plannedSol', round(pos['costSol'] / R['starterFraction'], 4))
            pos.setdefault('adds', 1 if pos.get('dipAdded') else 0)
            pos.setdefault('profitTaken', 1 if pos.get('scaled') else 0)
            pos['lastPx'] = px
            if cat.get('brainsCfg') and _lc.live_due(pos):   # 🚀 a live decision only on a ±10% move, ≤ 3 per coin
                chg_ = (px / pos['entryPriceNative'] - 1) * 100
                d_ = await _brain_decide(store, cat, 'live', pos['symbol'], f"you hold ${pos['symbol']} at {chg_:+.1f}% since your buy (peak {pos.get('peakChange', 0):+.1f}%), held {(now - pos.get('openedAt', now)) / 60:.0f} min. HOLD, SELL or TRIM?", owner=pos.get('brainBy') if (cat['brainsCfg'].get('brainMode') == 'battle') else None)
                pos['brainAsks'] = (pos.get('brainAsks') or 0) + 1; pos['brainAskPx'] = px
                if d_ and d_[0] == 'SELL':
                    cat['positions'].remove(pos)
                    _close(store, cat, pos, px, f"🧠 {d_[1].split('/')[-1]} sold: {d_[2] or 'its call'}")
                    continue
                if d_ and d_[0] == 'TRIM':
                    _close(store, cat, pos, px, f"🧠 {d_[1].split('/')[-1]} trimmed half: {d_[2] or 'its call'}", 0.5)
            nx_out = _cm.sell_now(nexa_read, pos.get('pairAddress')) if _cm.model_of(cat) else None
            if nx_out:   # 🪟 her fresh read named this coin EXIT: sold at the live price (paper)
                cat['positions'].remove(pos)
                _close(store, cat, pos, px, nx_out)
                continue
            nx_chg = (px / pos['entryPriceNative'] - 1) * 100 if pos.get('entryPriceNative') else 0.0
            nx_line = _cm.line_exit(nexa_read, pos, nx_chg) if _cm.model_of(cat) else None
            if nx_line:   # 🎯 her 2-min check moved a stop / take on this coin and it was hit
                cat['positions'].remove(pos)
                _close(store, cat, pos, px, nx_line)
                continue
            nx_skim = _cm.skim_now(nexa_read, pos) if _cm.model_of(cat) else None
            if nx_skim:   # ✂ her SKIM: bank half once per call, the rest rides her lines + FeeCat's stops
                pos['nxSkimAt'] = nexa_read['skim'][pos['pairAddress']]
                _close(store, cat, pos, px, nx_skim, 0.5)
            change = (px / pos['entryPriceNative'] - 1) * 100            # vs average entry
            from_first = (px / pos['firstEntryPriceNative'] - 1) * 100   # vs first buy (drives the dip ladder)
            pos['currentChange'] = round(change, 2)
            pos['peakChange'] = max(pos.get('peakChange', 0), change)
            pos['peakPx'] = max(pos.get('peakPx', 0), px)
            pos['lastPriceUsd'] = live.get('priceUsd')
            mc_now = _num(live.get('marketCap') or live.get('fdv'))
            held_h = (now - pos['openedAt']) / 3600
            broken, add_ok, vol_ratio = _thesis(pos, live, R)
            hard = R['lowCapHardStop'] if 0 < _num(pos.get('entryMarketCapUsd')) < R['lowCapMc'] else R['hardStop']
            why = None
            if broken:
                why = f'thesis broken: {broken}'
            elif change <= hard:
                why = f'hard stop {hard}% from my average entry'
            elif pos.get('pairAddress') in duo_exit and change >= 2:
                why = f'🤝 the FEELESS desk agrees: bank it at {change:+.1f}%'
            elif pos['profitTaken'] and change <= 0:
                why = 'runner fell back to break-even after taking profit'
            elif pos['peakChange'] >= R['protectAt'] and change <= 2:
                why = f'protected break-even: was up +{pos["peakChange"]:.0f}%, never let a winner turn red'
            elif held_h >= R['timeStopHours'] and pos['peakChange'] < R['timeStopMin'] and change < 3:
                why = f'time stop: no follow-through in {held_h:.1f}h (best +{pos["peakChange"]:.0f}%) — momentum trades work fast or not at all'
            elif pos['profitTaken'] and px <= pos['peakPx'] * (1 - R['runnerTrail'] / 100):
                why = f'trailing stop: {R["runnerTrail"]}% off the peak (peak +{pos["peakChange"]:.0f}%)'
            elif pos['profitTaken'] == 0 and change >= R['takeProfit1']:
                pos['profitTaken'] = 1
                _close(store, cat, pos, px, f'first profit target +{R["takeProfit1"]}%', R['takeProfit1Sell'], mc_now)
                continue
            elif pos['profitTaken'] == 1 and change >= R['takeProfit2']:
                pos['profitTaken'] = 2
                _close(store, cat, pos, px, f'second profit target +{R["takeProfit2"]}%', R['takeProfit2Sell'], mc_now)
                continue
            elif held_h >= R['deadMoneyHours'] and abs(change) < 10 and vol_ratio is not None and vol_ratio < 0.4:
                why = f'dead money: flat for {held_h:.0f}h and volume faded'
            elif held_h >= R['maxHoldHours'] and not pos['profitTaken']:
                why = f'max hold {R["maxHoldHours"]}h without a profit target'
            else:
                # Never average down. Add once to a WINNER: up +pyramidAt% with buyers still in control and the 5m green.
                m5_change = _num((live.get('priceChange') or {}).get('m5'))
                if pos['adds'] == 0 and add_ok and R['pyramidAt'] <= from_first <= R['pyramidAt'] + 25 and m5_change > 0 and R['pyramidFraction'] > 0:
                    add = round(min(pos['plannedSol'] * R['pyramidFraction'], cat['balanceSol']), 4)
                    if add >= 0.01:
                        old_avg_mc = _num(pos.get('entryMarketCapUsd'))
                        tokens_old = pos['notionalSol'] / pos['entryPriceNative']; tokens_new = add * (1 - fee_side()) / px
                        pos['entryPriceNative'] = (pos['notionalSol'] + add * (1 - fee_side())) / (tokens_old + tokens_new)
                        if old_avg_mc and mc_now:
                            pos['entryMarketCapUsd'] = round((old_avg_mc * tokens_old + mc_now * tokens_new) / (tokens_old + tokens_new), 2)
                        pos['costSol'] = round(pos['costSol'] + add, 6); pos['notionalSol'] = round(pos['notionalSol'] + add * (1 - fee_side()), 6)
                        pos['adds'] += 1; pos['peakChange'] = 0; pos['peakPx'] = px
                        cat['balanceSol'] = round(cat['balanceSol'] - add, 6); cat['volumeSol'] = round(cat.get('volumeSol', 0) + add, 6)
                        detail = (f"Added {add} SOL to winner {pos['symbol']} at {_fmt_usd(mc_now)} MC ({from_first:+.0f}% from my first buy) — buyers, volume and liquidity still hold. "
                                  f"New average entry {_fmt_usd(pos.get('entryMarketCapUsd'))} MC (paper).")
                        _log_event(store, cat, 'BUY', detail, None, pos['pairAddress'], px, mc_now, pos.get('entryMarketCapUsd'))
                        if cat.get('isLeader'):
                            _post_as_fee(pos['pairAddress'], f"🐱 {detail}\nAdding to what works, never to what doesn't.")
            if why:
                cat['positions'].remove(pos)
                _close(store, cat, pos, px, why, market_cap=mc_now)
        day = time.strftime('%Y-%m-%d')
        if cat.get('dailyLoss', {}).get(day, 0) >= float(cat['risk'].get('maxDailyLossSol') or 0.5):
            continue
        disc = feecat_brain.discipline(cat.get('exits', []), now)
        prev = (cat.get('discipline') or {}).get('why')
        cat['discipline'] = {**disc, 'at': now}
        if disc['why'] != prev and disc['sizeMult'] != 1.0:
            _log_event(store, cat, 'LEARN', f"Discipline: {disc['why']}.")
        if disc['pause']:
            continue
        if (cat.get('brainsCfg') or {}).get('kind') == 'general':   # 🧭 a General cat buys only what YOU order (its stops still run above)
            continue
        block = {x.upper() for x in cat['risk'].get('blocklist') or []}
        allow = {x.upper() for x in cat['risk'].get('allowlist') or []}
        safety_checks = 0
        for score, reason, p in ranked:
            if len(cat['positions']) >= R['maxPositions']:
                break
            sym = ((p.get('baseToken') or {}).get('symbol') or '?')
            pa = p.get('pairAddress')
            if sym.upper() in block or (allow and sym.upper() not in allow):
                continue
            if any(x['pairAddress'] == pa for x in cat['positions']):
                continue
            nx_drive = nexa_drives(cat, p)
            if pa in duo_avoid and not nx_drive:   # 🐱🤝 both AI models said skip it: she only ever trades LESS on their word
                store.setdefault('scan', {}).setdefault('brainRejects', []).append({'symbol': sym, 'why': '🤝 the FEELESS desk: skip it now', 'at': now})
                store['scan']['brainRejects'] = store['scan']['brainRejects'][-10:]
                continue
            nx_cover = False
            if _cm.model_of(cat) and nexa_read is None:   # 🐱 NEXA silent: FeeCat's own engine covers, half size
                nx_cover = True
                reason = f'{_cm.COVER_WHY}; {reason}'
            elif _cm.model_of(cat):   # 🪟 NEXA's cat: only her favored coins (every guard below still has to pass them)
                nx_ok, nx_why = _cm.buy_ok(nexa_read, pa)
                if not nx_ok:
                    continue
                reason = f'{nx_why}; {reason}'
            if now - cat.get('cooldowns', {}).get(pa, 0) < R['cooldownHours'] * 3600:
                last = next((e for e in reversed(cat.get('exits', [])) if e['pairAddress'] == pa), None)
                tx1 = (p.get('txns') or {}).get('h1') or {}
                strong = _num(tx1.get('buys')) >= 1.5 * max(_num(tx1.get('sells')), 1)
                if not (last and last.get('exitPx') and _num(p.get('priceNative')) >= last['exitPx'] * 1.10 and strong):
                    continue
                reason = f"re-entry on strength (+{(_num(p.get('priceNative')) / last['exitPx'] - 1) * 100:.0f}% above my exit, buyers 1.5×+); " + reason
            if safety_checks >= 4:
                break
            safety_checks += 1
            async with httpx.AsyncClient(timeout=30) as http2:
                safe, safe_why, conviction = await _safety(http2, p)
            if not safe:
                store.setdefault('scan', {}).setdefault('safetyRejects', []).append({'symbol': sym, 'why': safe_why})
                store['scan']['safetyRejects'] = store['scan']['safetyRejects'][-10:]
                continue
            async with httpx.AsyncClient(timeout=10) as http3:
                gap = await _fvg(http3, pa, _num(p.get('priceUsd')))
            if gap:
                conviction = round(conviction * 1.2, 2)
                reason = f'{reason}; retesting a 5m fair value gap (${gap[0]:.6g}–${gap[1]:.6g})'
            # Fuse edge: a coin the runner gates already failed is skipped; one several Fuse sources like gets a small boost.
            fe = feecat_brain.fuse_edge((p.get('baseToken') or {}).get('address'), fuse_view)
            if fe['veto'] and not nx_drive:
                store.setdefault('scan', {}).setdefault('brainRejects', []).append({'symbol': sym, 'why': fe['why'], 'at': now})
                store['scan']['brainRejects'] = store['scan']['brainRejects'][-10:]
                continue
            pg = feecat_brain.proof_gate(cat.get('exits') or [], now)
            if pg['sit_out'] and not nx_drive:
                store.setdefault('scan', {}).setdefault('brainRejects', []).append({'symbol': sym, 'why': pg['why'], 'at': now})
                store['scan']['brainRejects'] = store['scan']['brainRejects'][-10:]
                continue
            # Setup memory: her own closed trades decide whether this kind of entry deserves more, less or no size.
            ce = feecat_brain.crowd_edge((p.get('baseToken') or {}).get('address'), crowd_feed)
            setup = feecat_brain.setup_features(p, now, fresh=bool(p.get('_fresh')), gap=bool(gap), fuse=fe['tag'], crowd=ce['tag'])
            brain = feecat_brain.setup_edge(setup, feecat_brain.edge_table(cat.get('setupMemory') or []))
            if brain['veto'] and not nx_drive:
                store.setdefault('scan', {}).setdefault('brainRejects', []).append({'symbol': sym, 'why': brain['why'], 'at': now})
                store['scan']['brainRejects'] = store['scan']['brainRejects'][-10:]
                continue
            if nx_drive:   # 🪟 she overrode a veto: half size, the risk named on the receipt
                for v_ in (brain, fe):
                    if v_.get('veto'):
                        reason = f"{reason}; 🪟 NEXA over: {v_['why']} (half size)"
                        v_['mult'] = 0.5
            disc_cut = disc['sizeMult'] < 1.0   # discipline only ever makes her trade LESS: no Fuse boost while it's cutting size
            if disc['sizeMult'] != 1.0:
                conviction = round(conviction * disc['sizeMult'], 2)
            st_mult = float((cat.get('strength') or {}).get('mult') or 1.0)
            if st_mult < 1.0 or (st_mult > 1.0 and disc['sizeMult'] >= 1.0):   # 💪 auto-strength: down always, up only when discipline isn't cutting
                conviction = round(conviction * st_mult, 2)
                reason = f"{reason}; strength {(cat.get('strength') or {}).get('label')} ×{st_mult}"
            if brain['mult'] != 1.0:
                conviction = round(conviction * brain['mult'], 2)
                reason = f"{reason}; setup memory ×{brain['mult']} ({brain['why']})"
            if fe['mult'] != 1.0 and not disc_cut:
                conviction = round(conviction * fe['mult'], 2)
                reason = f"{reason}; {fe['why']} ×{fe['mult']}"
            if ce['mult'] != 1.0 and not disc_cut:
                conviction = round(conviction * ce['mult'], 2)
                reason = f"{reason}; learned from users: {ce['why']} ×{ce['mult']}"
            if nx_cover:
                conviction = round(conviction * _cm.COVER_MULT, 2)
            reason = f'{reason}; holders: {safe_why}; conviction {conviction}×'
            px = _num(p.get('priceNative'))
            planned = round(min(float(cat['risk']['maxPositionSol']), cat['balanceSol'] * 0.1 * conviction) * (R['freshSize'] if p.get('_fresh') else LEARN_SIZE if p.get('_learn') else (1 if p.get('_status') == 'READY' else 0.5) if p.get('_agentsLane') else 1), 4)
            size = round(planned * R['starterFraction'], 4)
            invested = sum(x['costSol'] for x in cat['positions'])
            if invested + planned > R['maxExposure'] * (cat['balanceSol'] + invested):
                break  # capital first: never more than maxExposure of equity at work
            if px <= 0 or size < 0.01 or cat['balanceSol'] < size:
                continue
            if cat.get('brainsCfg'):   # 🚀 ONE decision before a buy; one ask per tick, a SKIP cools that coin
                if cat.get('_askedTick') == now:
                    break
                cat['_askedTick'] = now
                b_ = cat['brainsCfg']
                owner_ = (b_['brains'][(b_.get('asks') or 0) % len(b_['brains'])] if b_.get('brainMode') == 'battle' else None)
                d_ = await _brain_decide(store, cat, 'buy', sym, f"candidate ${sym}: {reason}. Mcap {_fmt_usd(_num(p.get('marketCap') or p.get('fdv')))}, liquidity {_fmt_usd(_num((p.get('liquidity') or {}).get('usd')))}. BUY or SKIP?", owner=owner_)
                if d_ and d_[0] != 'BUY':
                    cat.setdefault('cooldowns', {})[pa] = now
                    continue
                brain_by_ = d_[1] if d_ else None
            else:
                brain_by_ = None
            cat['balanceSol'] = round(cat['balanceSol'] - size, 6)
            cat['volumeSol'] = round(cat.get('volumeSol', 0) + size, 6)
            # 🎯 TRUE FILL: her buy pays price impact against the pool's quote-side reserve (≈ half its liquidity), like a wallet
            sol_usd = _num(p.get('priceUsd')) / px if px > 0 else 0
            r_usd = _num((p.get('liquidity') or {}).get('usd')) / 2
            mid = px
            px = px * (1 + size * sol_usd / r_usd) if r_usd > 0 and sol_usd > 0 else px
            cat['positions'].append({
                'mint': (p.get('baseToken') or {}).get('address'), 'pairAddress': pa, 'symbol': sym, 'provider': 'DexScreener',
                'url': p.get('url'), 'costSol': size, 'notionalSol': round(size * (1 - fee_side()), 6),
                'entryPriceNative': px, 'entryPriceUsd': p.get('priceUsd'), 'entryChange': 0, 'currentChange': 0,
                'peakChange': 0, 'openedAt': now, 'reason': public_words(reason), 'nexa': bool(p.get('_nexa')),
                'entryLiq': _num((p.get('liquidity') or {}).get('usd')), 'conviction': conviction,
                'entryMarketCapUsd': _num(p.get('marketCap') or p.get('fdv')),
                'entryVolH1': _num((p.get('volume') or {}).get('h1')), 'plannedSol': planned,
                'firstEntryPriceNative': px, 'adds': 0, 'profitTaken': 0, 'peakPx': px, 'brainBy': brain_by_, 'setup': setup, 'setups': p.get('_setups') or [], 'read': p.get('_read'), 'duoAtEntry': p.get('_duo'), 'midAtEntry': mid, 'solUsdAtEntry': sol_usd,
            })
            _log_event(store, cat, 'BUY', f"Bought {size} SOL of {sym} at live price — {reason} (paper).", None, pa, px, _num(p.get('marketCap') or p.get('fdv')))
            if _real.is_real(cat) and not (cat.get('isLeader') and not p.get('_nexa')):   # 💵 the same buy, proposed to the owner's wallet (≤ budget); real Fee proposes NEXA's calls only
                p_ = _real.propose(cat, 'buy', (p.get('baseToken') or {}).get('address'), pa, sym, reason, now, sol=size, px=px)
                if p_:
                    _notify_real(cat, p_)
            if cat.get('isLeader'):
                _post_as_fee(pa, _buy_analysis(p, size, sym, safe_why, conviction), register_call=True)
        cat['lastTick'] = now


def _duo_learn(store, duo, now):
    """🎓 What she takes from OSSY / G4, explicitly: their record + each NEW final-review lesson becomes a LEARN line in her activity (once each)."""
    store['duoLearn'] = {'at': now, **(duo or {})}
    seen = set(store.get('duoSeen') or [])
    for les in reversed((duo or {}).get('lessons') or []):
        key = f"{les.get('who')}:{les.get('at')}"
        if key in seen or not les.get('lesson'):
            continue
        seen.add(key)
        pct = les.get('pct')
        line = f"🎓 from the FEELESS desk on ${les.get('symbol')}{'' if pct is None else f' ({pct:+.1f}%)'}: {les['lesson']}"
        cats_ = store.get('cats') or {}
        cat = cats_.get(LEADER_ID) or next(iter(cats_.values()), None)
        if cat is not None:
            _log_event(store, cat, 'LEARN', line)
    store['duoSeen'] = list(seen)[-80:]


def _migrate(store):
    if store.get('rulesVersion') not in ('trench-lord-v2', 'trench-lord-v3'):
        # Trench Lord v2 changed what the hold/exit settings mean; drop old-engine overrides for them.
        ov = store.get('rulesOverride') or {}
        store['rulesOverride'] = {k: v for k, v in ov.items() if k in TUNABLE and k != 'maxHoldHours'}
        store['rulesVersion'] = 'trench-lord-v2'
    if store.get('rulesVersion') != 'trench-lord-v3':
        # v3 discipline: stops, adds and profit targets changed meaning — old overrides / learned exits would undo it.
        exit_keys = {'add1At', 'add2At', 'hardStop', 'takeProfit1', 'takeProfit2', 'runnerTrail', 'maxHoldHours'}
        store['rulesOverride'] = {k: v for k, v in (store.get('rulesOverride') or {}).items() if k not in exit_keys}
        for c in store['cats'].values():
            if isinstance(c.get('learn'), dict):
                c['learn']['params'] = {}
        store['rulesVersion'] = 'trench-lord-v3'
    if any(c.get('engine') != ENGINE_VERSION for c in store['cats'].values()) and not (DATA_DIR / 'feecats_before_arena1015.json').exists():
        (DATA_DIR / 'feecats_before_arena1015.json').write_text(json.dumps(store))   # the old paper trail, kept once before the restart
        store['events'] = []
    for cat in store['cats'].values():
        if cat.get('engine') != ENGINE_VERSION:
            cat['exits'] = []   # 🐱 a fresh paper trail: no exit memory from the old market-wide engine
            # Earlier numbers came from a random-walk simulator — reset so every figure shown is real.
            cat['balanceSol'] = float(cat.get('startingBalanceSol') or 10)
            cat.update({'positions': [], 'realizedPnlSol': 0, 'totalPnlSol': 0, 'volumeSol': 0, 'wins': 0, 'losses': 0,
                        'winRate': None, 'pnlHistory': [{'value': 0}], 'engine': ENGINE_VERSION, 'xp': 0, 'level': 1})
    if LEADER_ID not in store['cats']:
        now = time.time()
        store['cats'][LEADER_ID] = {
            'id': LEADER_ID, 'ownerId': 'feeless-system', 'name': 'Fee', 'handle': 'fee', 'avatar': 'Mint Mackerel',
            'isLeader': True, 'brain': 'rules', 'brainLabel': 'FEELESS rule engine',
            'brainProfile': {'provider': 'FEELESS', 'status': 'rule_engine', 'available': False, 'estimatedTokenCostUsd': 0},
            'strategy': 'trend', 'strategyLabel': 'Trench Lord', 'status': 'running', 'level': 1, 'xp': 0,
            'wallet': 'paper', 'startingBalanceSol': 25, 'balanceSol': 25, 'realizedPnlSol': 0, 'totalPnlSol': 0,
            'volumeSol': 0, 'wins': 0, 'losses': 0, 'winRate': None, 'positions': [], 'pnlHistory': [{'value': 0}],
            'risk': {'maxPositionSol': 2, 'maxDailyLossSol': 3, 'allowlist': [], 'blocklist': []},
            'revoked': False, 'createdAt': now, 'lastTick': now, 'engine': ENGINE_VERSION,
        }
    for cat in store['cats'].values():
        if 'exits' not in cat:
            cat['exits'] = []
            for ev in reversed(store.get('events', [])):
                if ev.get('catId') == cat['id'] and ev.get('type') == 'SELL' and ev.get('pairAddress') and ev.get('priceNative') and 'Sold ' in ev.get('detail', '') and '% of' not in ev.get('detail', ''):
                    d = ev['detail']
                    try:
                        sym = d.split('Sold ', 1)[1].split(' at ', 1)[0]
                        ch = float(d.split(' at ', 1)[1].split('%', 1)[0])
                        why = d.split(' — ', 1)[1].split('. Net', 1)[0]
                    except (IndexError, ValueError):
                        continue
                    cat['exits'].append({'pairAddress': ev['pairAddress'], 'symbol': sym, 'exitPx': ev['priceNative'], 'exitAt': ev['ts'] / 1000,
                                         'why': why, 'pnlSol': ev.get('pnlSol'), 'changeAtExit': ch, 'peakAfter': 0.0, 'lowAfter': 0.0})
    leader = store['cats'][LEADER_ID]
    leader['name'], leader['handle'] = 'Fee', 'fee'
    leader['title'] = 'The Leader of the FEELESS Cats'
    leader['strategyLabel'] = 'Trench Lord'


WALL_EVERY = 30 * 60


def _wall_post(text, tokens=None):
    try:
        key = (DATA_DIR / 'internal.key').read_text().strip()
        r = httpx.post('http://127.0.0.1:5077/api/reputation/internal/fee-post', json={'room': 'wall', 'text': text, 'tokens': tokens or []},
                       headers={'x-feeless-internal': key}, timeout=15)
        if r.status_code != 200:
            print('fee wall post rejected', r.status_code, r.text[:200])
    except Exception as exc:
        print('fee wall post failed', exc)


def _pct(v):
    v = _num(v)
    return f"{'+' if v >= 0 else ''}{v:.0f}%"


async def _meta_post(store):
    """Fee's wall: what the trenches look like right now — the board's bangers, the weather, the big coins, her book."""
    async with httpx.AsyncClient(timeout=20) as http:
        try:
            board = (await http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': 'trending', 'chain': 'solana', 'page': 1, 'scope': 'launchpads'})).json().get('pairs') or []
        except Exception:
            board = []
        try:
            fresh = (await http.get('http://127.0.0.1:5001/api/market/feed', params={'kind': 'new', 'chain': 'solana', 'page': 1, 'scope': 'launchpads'})).json().get('pairs') or []
        except Exception:
            fresh = []
        try:
            sol = (await http.get('https://api.dexscreener.com/latest/dex/pairs/solana/58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2')).json().get('pairs', [{}])[0]
        except Exception:
            sol = {}
    if not board:
        return
    moves = sorted(_num((p.get('priceChange') or {}).get('h1')) for p in board)
    median = moves[len(moves) // 2] if moves else 0
    green = sum(1 for m in moves if m > 0) / max(1, len(moves))
    weather = ('☀️ scorching' if green >= 0.7 and median >= 20 else '🌤️ mostly green' if green >= 0.55
               else '⛅ crab weather' if green >= 0.4 else '🌧️ red rain')
    lines = [f"🐱 Trench report — {weather}: {green:.0%} of the board is green, median {_pct(median)} on the hour."]
    if sol:
        lines.append(f"SOL {_fmt_usd(sol.get('priceUsd'))} ({_pct((sol.get('priceChange') or {}).get('h24'))} 24h) — the tide every meme swims in.")
    lines.append('\nBangers on my radar:')
    for p in board[:3]:
        why = ', '.join(r for r in (p.get('quality') or {}).get('reasons') or [] if not r.endswith(' 1h') or 'vol' in r) or 'steady two-sided flow'
        lines.append(f"• ${(p.get('baseToken') or {}).get('symbol')} — MC {_fmt_usd(p.get('marketCap'))}, {_pct((p.get('priceChange') or {}).get('h1'))} 1h ({why})")
    if fresh:
        f = fresh[0]
        lines.append(f"\nFresh one with real traction: ${(f.get('baseToken') or {}).get('symbol')} at {_fmt_usd(f.get('marketCap'))} — early, so size small.")
    leader = store['cats'].get(LEADER_ID) or {}
    pos = leader.get('positions') or []
    if pos:
        book = ', '.join(f"${x['symbol']} {_pct(x.get('currentChange'))}" for x in pos[:4])
        lines.append(f"\nMy book: {book}. Thesis intact = I hold; a healthy dip with buyers still there = I add.")
    else:
        lines.append("\nMy book is flat — waiting for a setup that passes every rule. Cash is a position too.")
    lines.append('Meta, not advice. Paper trades on live prices.')
    # Coin cards (with each coin's Pump cover image) for the three picks.
    cards = [{'chainId': 'solana', 'pairAddress': p.get('pairAddress'), 'pair': p, 'fetched_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
             for p in board[:3] if p.get('pairAddress')]
    _wall_post('\n'.join(lines), cards)
    store['lastWallPost'] = time.time()


# 🧠🧠 THE GENERAL CAT AT WORK (cat_agent.py + cat_browser.py, P2). One task per cat at a time, in memory; its windows are hosted browsers
# (Steel → Browserbase → the reader). The ENGINE LOOP is the only writer of the cat store: a finished task's cost + its chat lines are applied
# in `_work_settle` (the cat's credit pays, the owner's per-task $ cap bounds it). Live / snapshot views go only to the cat's owner.
_WORK: dict = {}
TASK_CAP_DEFAULT, TASK_CAP_MAX = 0.05, 2.0
BACKUP_MODEL = 'openai/gpt-oss-120b'   # Groq's free tier: tested with the agent's JSON step format
WORK_QUEUE_MAX = 10   # 🏇 let it go: asks waiting their turn
CHAT_KEEP = 60


def _work_live():
    """General cats' model calls: their OWN switch (GENERAL_CAT_LIVE) so the owner can test a general cat without turning on every trading
    cat's brain calls (LAUNCH_CAT_LIVE turns both on). Needs the OpenRouter key either way."""
    return bool(os.environ.get('OPENROUTER_API_KEY')) and (os.environ.get('GENERAL_CAT_LIVE', '').lower() in ('1', 'true', 'on') or _brains_live())


def _work_view(cat_id, owner=False):
    w = _WORK.get(cat_id) or {}
    t = w.get('task')
    if not t:
        return {'task': None}
    wins = []
    for x in t['windows']:
        s_ = (w.get('sessions') or [None, None])[x['i']] or {}
        wins.append({**{k: x.get(k) for k in ('i', 'model', 'goal', 'status', 'bubble', 'url', 'title', 'human', 'answer', 'cost', 'coin', 'scratchN')}, 'scratch': len(x.get('scratch') or []), 'steps': x['steps'][-10:],
                     'provider': s_.get('provider'), 'note': s_.get('note'), **({'live': s_.get('live'), 'shot': bool((w.get('pages') or [None, None])[x['i']] and not s_.get('live'))} if owner else {})})
    return {'task': {k: t.get(k) for k in ('id', 'text', 'mode', 'status', 'cap', 'cost', 'answer', 'fast', 'why', 'stepsMax', 'keep', 'backup', 'walletPaid')}, 'windows': wins}


def clean_limits(raw):
    """🎚 A general agent's spend limits, clamped; 0 = no extra limit. mindUsd: $ each mind may spend on one task · steps: actions each mind may take · dayUsd: $ a day."""
    r = raw if isinstance(raw, dict) else {}
    num = lambda v, hi: max(0.0, min(float(hi), float(_num(v) or 0)))
    return {'mindUsd': [round(num(v, TASK_CAP_MAX), 4) for v in list(r.get('mindUsd') or [])[:2]], 'steps': int(num(r.get('steps'), _ca.GO_STEPS)), 'dayUsd': round(num(r.get('dayUsd'), 100), 4)}


def ensure_real(cat):
    """👛 A general agent with its own wallet trades from that wallet: its orders are real, sized by its MAX A TRADE. It buys only what you order (a general cat never hunts). Owner's ⏸ Paper stands."""
    w = cat.get('agentWallet') or {}
    if not w.get('address') or not w.get('owner') or cat.get('isLeader') or cat.get('paperByOwner') or _real.is_real(cat) or (cat.get('brainsCfg') or {}).get('kind') != 'general':
        return False
    _real.go_real(cat, w['owner'], max(_real.MIN_BUDGET, min(0.5, _num((cat.get('risk') or {}).get('maxPositionSol')) or 0.05)), time.time())
    return True


def day_left(cat):
    """$ left today under its daily limit (None = no daily limit)."""
    day = float((cat.get('limits') or {}).get('dayUsd') or 0)
    if not day:
        return None
    return max(0.0, day - float(((cat.get('brainsCfg') or {}).get('daySpend') or {}).get(time.strftime('%Y-%m-%d', time.gmtime()), 0)))


def _work_start(cat_id, cat, text, to=None):
    """Start one task in the cat's windows. 🏇 Let it go (cat.workGo): a long step budget (cat_agent.GO_STEPS) — it stops only when done, at
    its $ cap, or when a person is needed (a sign-in / CAPTCHA / payment: it never types a password or a card)."""
    b = cat.get('brainsCfg') or {}
    cap = min(float(cat.get('taskCap') or TASK_CAP_DEFAULT), max(0.005, float(b.get('credit') or 0) - _lc.CREDIT_RESERVE))   # its own credit only, always leaving the reserve
    left_ = day_left(cat)
    if left_ is not None:
        if left_ <= 0:
            raise HTTPException(409, "It reached today's $ limit. Raise it in its limits, or it carries on tomorrow.")
        cap = min(cap, left_)
    lim_ = cat.get('limits') or {}
    models = list(b['brains'])[:8]
    if to not in (None, 'both') and str(to).isdigit() and int(to) < len(models):   # talk to ONE of its minds: that model takes the whole task
        models = [models[int(to)]]
    names = [str(m).split('/')[-1][:24] for m in models]
    steps = int(lim_.get('steps') or 0) or (_ca.GO_STEPS if cat.get('workGo') else _ca.STEP_MAX)
    _WORK[cat_id] = {'task': _ca.new_task(uuid.uuid4().hex[:10], text, models, cap, steps, cat.get('workMode') or 'plan', lim_.get('mindUsd') if len(models) > 1 else None), 'events': {}, 'go': {}, 'sessions': [None] * len(models), 'pages': [None] * len(models), 'at': time.time()}
    _WORK[cat_id]['task']['tools'] = _cp.toolkit(cat.get('job', 'agent'), cat.get('tools'))
    _WORK[cat_id]['task']['clouds'] = {i: [x.get('text', '') for x in (b.get('minds') or {}).get(m, [])][-8:] for i, m in enumerate(models)}   # ☁ each mind reads its own cloud
    _WORK[cat_id]['runner'] = asyncio.create_task(_work_run(cat_id, models, names, text, cap, str(b.get('prompt') or '')[:1200], b.get('efforts') or {},
                                                            _ck.key_for(cat, 'openrouter', data_dir=DATA_DIR)))


async def _work_run(cat_id, models, names, text, cap, brief='', efforts=None, own_key=None):
    w = _WORK[cat_id]
    await _or_models()   # the price list: after a restart every model read as 'unknown cost' and the budget check stopped the task
    cat_now = _load()['cats'].get(cat_id) or {}; paid_ = {'usdc': 0.0, 'on': False}
    if (cat_now.get('agentWallet') or {}).get('circleAcct') == 'agent' and not own_key:   # 💳 it pays for its own thinking from its own wallet
        try:
            paid_.update(usdc=await _thinking_money(cat_now), on=True)
        except (httpx.HTTPError, ValueError) as e:
            print(f'[agent think] {cat_id}: {str(e)[:120]}')
    env = os.environ
    async with httpx.AsyncClient(timeout=30) as http:
        sessions, pages = [], []
        try:
            for i, _m in enumerate(models):
                s_, _tried = await _cb.open_session(http, env)
                sessions.append(s_)
                try:
                    pages.append(await _cb.LivePage(s_['connect']).start() if s_.get('connect') else _cb.ReaderPage(http))
                except Exception as e:   # the live browser did not connect → the reader keeps the model working
                    sessions[-1] = {**s_, 'provider': 'reader', 'live': None, 'note': f"{s_['provider']} did not connect ({str(e)[:60]})"}
                    pages.append(_cb.ReaderPage(http))
            w.update(sessions=sessions, pages=pages)

            orders = [{'role': 'system', 'content': f"Your owner's standing orders, sealed at launch — follow them on every step: {brief}"}] if brief else []

            def reply_room(model, messages):
                """🎚 The longest reply that still fits what is left of its $ cap (owner's low cap: a short question must still run), up to 4096 tokens."""
                row = next((m for m in ((_MODELS.get('rows') or {}).get('models') or []) if m['id'] == model), None)
                if row is None or not row.get('outUsd'):
                    return 4096
                t_ = w['task']; sent = len(json.dumps(orders + messages, ensure_ascii=False).encode('utf-8')) / 3 + 256
                return max(0, min(4096, int((t_['cap'] - t_['cost'] - sent * row['inUsd'] / 1e6) / row['outUsd'] * 1e6)))

            async def ask(model, messages):   # 📜 the sealed brief rides every call (plan · each browsing step · merge)
                _OR_LAST.pop('err', None); _OR_LAST.pop('backup', None)
                room_ = paid_['usdc'] - _ap.RESERVE_USD
                if paid_['on'] and room_ > 0:
                    t_ = w['task']; text_, usd_ = await _wallet_call(cat_now, model, orders + messages, reply_room(model, messages), min(room_, t_['cap'] - t_['cost']))
                    if str(text_ or '').strip():
                        paid_['usdc'] -= usd_; t_['walletPaid'] = round((t_.get('walletPaid') or 0) + usd_, 6)
                        return text_, usd_
                text_, usd_ = await _or_call(model, orders + messages, max_tokens=reply_room(model, messages), backup=True, **({'key': own_key} if own_key else {}), **({'effort': efforts[model]} if (efforts or {}).get(model) else {}))
                if not str(text_ or '').strip():
                    raise _ca.Stopped(_OR_LAST.get('err') or 'The model returned nothing. Try again.')
                if _OR_LAST.get('backup'):
                    w['task']['backup'] = True
                return text_, usd_

            def cost_bound(model, messages):
                row = next((m for m in ((_MODELS.get('rows') or {}).get('models') or []) if m['id'] == model), None)
                if row is None:
                    return float('inf')
                tokens = len(json.dumps(orders + messages, ensure_ascii=False).encode('utf-8')) / 3 + 256
                room = reply_room(model, messages)
                return float('inf') if room < 256 else (tokens * row['inUsd'] + room * row['outUsd']) / 1e6
            ask.cost_bound = cost_bound

            async def wait_human(i):
                ev = w['events'][i] = asyncio.Event()
                await ev.wait()
                return bool(w['go'].pop(i, False))
            async def feeless(tool, q=''):   # 🧰 FEELESS first: our own read-only tools, server-side (the browser is walled off from us)
                return await _ct.run_tool(http, tool, q)
            await _ca.run(w['task'], ask, pages, wait_human, names, feeless)
        finally:
            for pg in pages:
                await pg.close()
            for s_ in sessions:
                await _cb.close_session(http, env, s_)
            w['pages'] = [None] * len(models)
            w['done'] = True


def _work_settle(store):
    """The engine's pass: a finished task's $ is charged to the cat's credit and its question + answer join the cat's chat (one writer)."""
    for cid, w in list(_WORK.items()):
        if not w.get('done') or w.get('settled'):
            continue
        cat = store['cats'].get(cid)
        t = w.get('task') or {}
        if cat and cat.get('brainsCfg'):
            cat['artifacts'] = (list(cat.get('artifacts') or []) + t.get('artifacts', []))[-30:]
            cat['refusals'] = (list(cat.get('refusals') or []) + [{'at': time.time(), 'why': x} for x in t.get('refusals', [])])[-100:]
            if not _ck.key_for(cat, 'openrouter', data_dir=DATA_DIR):   # its owner's own key pays OpenRouter directly — no FEELESS credit
                _lc.charge(cat['brainsCfg'], max(0.0, (t.get('cost') or 0) - (t.get('walletPaid') or 0)))   # what its wallet paid never comes off its FEELESS credit
            if t.get('status') == 'done':   # 🤖 the flat fee for anything that is not a trade
                cat['feesDue'] = (list(cat.get('feesDue') or []) + [{'key': f"task-{t.get('id')}"}])[-20:]
            for lg_ in t.get('logins') or []:   # 🔐 every sign-up's password → sealed in its vault, then gone from memory
                try:
                    _cv.put_login(cat, lg_.get('site'), lg_.get('user'), lg_.get('pw'), data_dir=DATA_DIR)
                except (ValueError, RuntimeError):
                    pass
            t['logins'] = []
            for md_ in t.get('media') or []:
                try:
                    _cv.add_media(cat, md_.get('url'), md_.get('title'))
                except ValueError:
                    pass
            for w_ in t.get('windows') or []:   # ☁ each mind's best notes → its OWN cloud
                if w_.get('best'):
                    mc_ = cat['brainsCfg'].setdefault('minds', {})
                    mc_[w_['model']] = ((mc_.get(w_['model']) or []) + [{'at': time.time(), 'text': str(x)[:240]} for x in w_['best']])[-_ca.MIND_CLOUD_MAX:]
                    w_['best'] = []
            for k_ in t.get('keep') or []:   # ☁ the best of both scratch pads → its main cloud (the rest was thrown away)
                cat['brainsCfg']['cloud'] = ((cat['brainsCfg'].get('cloud') or []) + [{'at': time.time(), 'word': 'KEEP', 'sym': '', 'text': str(k_)[:240], 'by': ['both']}])[-_lc.CLOUD_MAX:]
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': t.get('text'), 'at': w.get('at')},
                           {'by': 'cats', 'text': (f"💳 Paid ${t.get('walletPaid'):.4f} from its wallet: " if t.get('walletPaid') else '') + ("🛟 Backup model, free (OpenRouter has no credit): " if t.get('backup') else '') + (t.get('answer') or f"({t.get('status')}: {t.get('why') or 'no answer'})"), 'at': time.time(), 'cost': t.get('cost'), 'fast': t.get('fast')}])[-CHAT_KEEP:]
        w['settled'] = True
        # 🏇 let it go: the next queued ask starts on its own (a stopped task pauses the queue — you stopped it for a reason)
        if cat and cat.get('workGo') and cat.get('workQueue') and t.get('status') != 'stopped' and _work_live() and _lc.can_ask(cat.get('brainsCfg') or {}):
            if day_left(cat) is None or day_left(cat) > 0:   # at its daily $ limit the queue waits
                nxt = cat['workQueue'].pop(0)
                _work_start(cid, cat, nxt.get('text'), nxt.get('to'))


async def _agent_pass(store):
    """🏇 Agent trades (agent_trade.py): every REAL cat with its own wallet settles what is in flight and sends its next proposal — inside this
    loop's own load → save, so no other writer races it. A failure is logged and never stops the engine."""
    key = os.environ.get('CROSSMINT_API_KEY', '').strip()
    cats = [c for c in store['cats'].values() if (c.get('agentWallet') or {}).get('address') and _real.is_real(c) and not c.get('revoked')]
    cats = [c for c in cats if key or (c.get('agentWallet') or {}).get('provider') == 'circle']   # a Circle wallet needs no Crossmint key
    if not cats:
        return
    now = time.time()
    async with httpx.AsyncClient(timeout=25) as http_a:
        for c in cats:
            try:
                for w_ in await _at.run(http_a, key, c, now):
                    _log_event(store, c, 'TRADE', f"{c.get('name')}: {w_}")
                await _agent_fees(http_a, c, now)
            except Exception as exc:
                print('agent pass', c.get('id'), exc)


async def _agent_fees(http, cat, now):
    """🤖 HQ › Fees flat fees: one per trade that landed, one per finished task. A wallet that can't pay yet is asked again later; the key means never twice."""
    w_ = cat.get('agentWallet') or {}
    if w_.get('circleAcct') != 'agent' or now - float(cat.get('feeTry') or 0) < 120:
        return
    due = [('trade', t.get('key') or t.get('id'), t) for t in cat.get('agentTx') or [] if t.get('status') == 'success' and not t.get('feeDone')]
    due += [('other', x['key'], x) for x in cat.get('feesDue') or []]
    for kind, key, row in due[:3]:
        r = await http.post('http://127.0.0.1:5077/api/reputation/internal/agent-fee', headers=_internal_headers(), timeout=30,
                            json={'catId': cat['id'], 'walletId': w_.get('circleId'), 'address': w_.get('address'), 'owner': w_.get('owner'), 'kind': kind, 'key': f'fee-{key}'})
        if r.status_code != 200:
            cat['feeTry'] = now
            return
        if kind == 'trade':
            row['feeDone'] = True
        else:
            cat['feesDue'] = [x for x in cat['feesDue'] if x['key'] != key]


async def _engine_loop():
    while True:
        try:
            store = _load()
            _migrate(store)
            _apply_overrides(store)
            running = [c for c in store['cats'].values() if c['status'] == 'running' and not c['revoked']]
            if running:
                await run_engine(store, running)
            await _agent_pass(store)
            _work_settle(store)
            if time.time() - store.get('lastWallPost', 0) >= WALL_EVERY:
                store['lastWallPost'] = time.time()   # claim the slot first; a failed post retries next window
                await _meta_post(store)
            _save(store)
        except Exception as exc:  # keep the loop alive; surface in logs
            print('engine error', exc)
        await asyncio.sleep(TICK_SECONDS)


def _score(cat):
    return {
        'id': cat['id'], 'name': cat['name'], 'avatar': cat['avatar'], 'level': cat['level'],
        'strategyLabel': cat['strategyLabel'], 'realizedPnlSol': cat['realizedPnlSol'],
        'volumeSol': cat.get('volumeSol', 0), 'winRate': cat.get('winRate'), 'isLeader': bool(cat.get('isLeader')),
        'openPositions': len(cat.get('positions', [])), 'trades': cat.get('wins', 0) + cat.get('losses', 0),
        # 🏆 the board + live activity draw each agent as it looks (owner 2026-10-30): its look, its desk colour, live or not, what kind — nothing private
        'look': cat.get('look'), 'skin': cat.get('skin'), 'status': cat.get('status'), 'kind': (cat.get('brainsCfg') or {}).get('kind') or 'rules',
        'brains': [str(m).split('/')[-1] for m in ((cat.get('brainsCfg') or {}).get('brains') or [])][:2],
        # 📸 its recent snapshot for the board cards: the last 24 points of its P/L curve + the coin it is on / just left
        'curve': [round(float(x.get('value') or 0), 6) for x in (cat.get('pnlHistory') or [])[-24:]],
        'coin': ((cat.get('positions') or [{}])[0].get('symbol') if cat.get('positions') else ((cat.get('exits') or [{}])[-1].get('symbol') if cat.get('exits') else None)),
    }


app = FastAPI(title='FEELESS Cats')
from starlette.middleware.gzip import GZipMiddleware as _GZip
app.add_middleware(_GZip, minimum_size=1024)   # ⚡ every list over 1KB goes compressed (a 287KB trench list was sent raw)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in (os.environ.get('ALLOWED_ORIGINS') or '*').split(',') if o.strip()], allow_methods=['*'], allow_headers=['*'])


@app.on_event('startup')
async def _start_engine():
    asyncio.create_task(_engine_loop())
    asyncio.create_task(_tune_loop())


@app.get('/api/cats/brains')
async def brains():
    """The brain list: FEELESS's own model(s) first (🪟 NEXA = live when her desk read is fresh), the catalog rows run on the rule engine."""
    async with httpx.AsyncClient(timeout=4) as http:
        nx = (await _duo_read(http)).get('nexa')
    own = [{**m, **_cm.status(nx), 'available': False, 'ownerOnly': True, 'trades': 'FeeCat', 'estimatedTokenCostUsd': 0, 'model': True} for m in _cm.MODELS.values()]   # 🪟 she trades FeeCat herself (owner's HQ switch), never a user's cat
    return _pub({'brains': own + [{**RULE_ENGINE, 'status': 'live', 'available': True, 'estimatedTokenCostUsd': 0}]})


def _set_model_brain(cat, model_id):
    """🪟 Assign a FEELESS model to a cat (or back to the rule engine). Owner-only, FeeCat herself (`/api/cats/internal/brain`). Paper only."""
    m = _cm.MODELS.get(str(model_id or '').lower())
    if m:
        cat['modelBrain'] = m['id']; cat['brain'] = m['id']; cat['brainLabel'] = m['name']
        cat['brainProfile'] = {'provider': m['provider'], 'status': 'live', 'available': True, 'estimatedTokenCostUsd': 0}
    else:
        cat.pop('modelBrain', None)
        cat['brainProfile'] = {**(cat.get('brainProfile') or {}), 'status': 'rule_fallback', 'available': False}
    return m


LOOK_OPTIONS = {'gear': ('none', 'crown', 'shades', 'chain', 'headset', 'halo', 'cap', 'bow', 'rose'), 'aura': ('none', 'royal', 'gold', 'ice', 'blaze', 'nebula', 'toxic'),
                'eyes': ('classic', 'laser', 'gold', 'ice', 'void')}   # 🐆 mirrors components/command/CatLook.jsx LOOK (change both)


def clean_look(x):
    """🐆 A cat's look: listed options only + a ≤ 12-char name tag (letters, digits, space . $ - _). Pure look, the engine never reads it."""
    x = x if isinstance(x, dict) else {}
    out = {k: (x.get(k) if x.get(k) in opts else opts[0 if k != 'aura' else 1]) for k, opts in LOOK_OPTIONS.items()}
    out['tag'] = re.sub(r'[^\w .$-]', '', str(x.get('tag') or ''))[:12]
    return out


class CreatePayload(BaseModel):
    ownerId: str
    name: str
    handle: str
    avatar: Any = 0
    brain: str = 'rules'
    strategy: str = 'momentum'
    instructions: Optional[str] = ''
    startingBalanceSol: Any = '10'
    maxPositionSol: Any = '0.25'
    dailyBuyLimitSol: Any = '2'
    maxDailyLossSol: Any = '0.5'
    walletMode: str = 'paper'
    coinPlan: str = 'later'
    allowlist: Optional[str] = ''
    blocklist: Optional[str] = ''
    brains: Optional[list] = None
    brainMode: Optional[str] = None
    brainKind: Optional[str] = None    # 📈 trading · 🧭 general (set once at launch)
    billing: Optional[str] = None
    prompt: Optional[str] = None
    efforts: Optional[dict] = None
    look: Optional[dict] = None
    session: Optional[str] = None
    job: str = "agent"
    tools: Optional[dict] = None
    venues: Optional[list] = None     # 📈 trading cat: FEELESS rails only (cat_keys.VENUES)
    workMode: Optional[str] = None    # 🧭 general cat: plan (plan → split → merge) · jobs (each mind its own job)
    taskCap: Optional[float] = None   # 💵 general cat: most it may spend on one task (clamped to TASK_CAP_MAX)


@app.get('/api/cats/models')
async def cat_models(session: str = ""):
    """🚀 Launch a Cat: OpenRouter's whole public model list (price, context, what it's good at), FEELESS's three on top."""
    return {**(await _or_models()), 'live': _brains_live(), 'generalLive': _work_live(), 'maxModels': await _model_limit(session)}


async def _model_limit(session=''):
    try:
        async with httpx.AsyncClient(timeout=5) as h:
            r = await h.post('http://127.0.0.1:5077/api/reputation/cats/model-limit', json={'session': session})
        if r.status_code == 200:
            return max(1, min(8, int(r.json()['maxModels'])))
    except Exception:
        pass
    return 2


AGENT_MAX = 2   # 🤖 a user runs at most 2 agents (owner, 2026-10-22: "users pick if they want 1-2 cat AI agents"); a revoked one frees its slot


@app.post('/api/cats')
async def create_cat(payload: CreatePayload):
    store = _load()
    if sum(1 for c in store['cats'].values() if c.get('ownerId') == payload.ownerId and not c.get('revoked')) >= AGENT_MAX:
        raise HTTPException(400, f'You run {AGENT_MAX} agents — retire one to start another.')
    cat_id = uuid.uuid4().hex
    now = time.time()
    cat = {
        'id': cat_id, 'ownerId': payload.ownerId, 'name': payload.name, 'handle': payload.handle,
        'avatar': payload.avatar, 'brain': RULE_ENGINE['id'], 'brainLabel': RULE_ENGINE['label'],
        'brainProfile': {'provider': RULE_ENGINE['provider'], 'status': 'live', 'available': False, 'estimatedTokenCostUsd': 0},
        'strategy': payload.strategy, 'strategyLabel': STRATEGY_LABELS.get(payload.strategy, 'Momentum'),
        'status': 'stopped', 'level': 1, 'xp': 0, 'wallet': 'paper',
        'balanceSol': float(payload.startingBalanceSol or 10), 'realizedPnlSol': 0, 'totalPnlSol': 0,
        'volumeSol': 0, 'wins': 0, 'losses': 0, 'winRate': None, 'positions': [], 'pnlHistory': [{'value': 0}],
        'risk': {
            'maxPositionSol': float(payload.maxPositionSol or 0.25), 'maxDailyLossSol': float(payload.maxDailyLossSol or 0.5),
            'allowlist': [s.strip() for s in (payload.allowlist or '').split(',') if s.strip()],
            'blocklist': [s.strip() for s in (payload.blocklist or '').split(',') if s.strip()],
        },
        'revoked': False, 'createdAt': now, 'lastTick': now, 'engine': ENGINE_VERSION,
        'startingBalanceSol': float(payload.startingBalanceSol or 10), 'look': clean_look(payload.look),
    }
    if payload.brains:
        cat_ = await _or_models()
        ids_ = {m['id'] for m in cat_.get('models') or []}
        try:
            cat['brainsCfg'] = _lc.clean(payload.model_dump(), None, ids_ or None, max_models=await _model_limit(payload.session or ''))
            cat['job'] = payload.job if payload.brainKind == 'general' else 'trading'
            cat['tools'] = _cp.toolkit(cat['job'], payload.tools)
            if payload.brainKind != 'general':
                cat['venues'] = _ck.venues(payload.venues)   # 📈 FEELESS rails only (trench · perps)
            else:
                cat['workMode'] = payload.workMode if payload.workMode in _ca.MODES else 'plan'
                if payload.taskCap: cat['taskCap'] = max(0.005, min(TASK_CAP_MAX, float(payload.taskCap)))
        except ValueError as e:
            raise HTTPException(400, str(e))
        for model, effort in cat['brainsCfg'].get('efforts', {}).items():
            row = next((m for m in cat_.get('models', []) if m['id'] == model), {})
            if effort not in row.get('efforts', []):
                raise HTTPException(400, 'That model does not expose the selected effort level.')
        cat['brainLabel'] = ' + '.join(x.split('/')[-1] for x in cat['brainsCfg']['brains'])
        cat['brainProfile'] = {'provider': 'OpenRouter', 'status': 'live' if _brains_live() else 'calls off', 'available': _brains_live(), 'estimatedTokenCostUsd': 0}
    store['cats'][cat_id] = cat
    _save(store)
    return {'cat': {**_no_keys(cat), 'mine': True}}   # (a random "recovery key" used to ride here — it unlocked nothing; the wallet's safe-keeping is SafeKeeping on the desk)


@app.get('/api/cats')
async def list_cats(ownerId: str):
    store = _load()
    cats = [c for c in store['cats'].values() if ownerId and c['ownerId'] == ownerId]
    cats.sort(key=lambda c: -c['createdAt'])
    return {'cats': [{**x, 'mine': True} for x in _no_keys(cats)]}


@app.get('/api/cats/brain')
def cats_brain():
    """🐱 FeeCat's own auto-strength, live: entry mode (warming / tightening / holding / drought-relax), the entry rules she's
    running vs defaults, the exit params she learned, and her last notes. Read-only."""
    store = _load()
    cat = (store.get('cats') or {}).get(LEADER_ID) or {}
    L = cat.get('learn') or {}
    entry = L.get('entry') or {}
    return {'mode': L.get('mode') or 'warming', 'tunedAt': L.get('tunedAt'),
            'entry': {k: {'now': entry.get(k, RULES[k]), 'default': RULES[k]} for k in ENTRY_BOUNDS},
            'exits': {k: {'now': v, 'default': RULES.get(k)} for k, v in (L.get('params') or {}).items()},
            'log': (L.get('log') or [])[:10], 'good': L.get('good', 0), 'missed': L.get('missed', 0)}


@app.get('/api/cats/leader')
async def leader():
    store = _load()
    _migrate(store)
    return _pub({'cat': store['cats'].get(LEADER_ID), 'rules': RULES, 'feePerSide': fee_side(), 'scan': store.get('scan'), 'talk': store.get('aiTalk') or []})


class EvaluatePayload(BaseModel):
    pairs: list


@app.post('/api/cats/evaluate')
async def evaluate(payload: EvaluatePayload):
    """Fee's read: runs any Solana pairs through the Leader's live entry rules."""
    addrs = [str(p.get('pairAddress')) for p in payload.pairs[:60] if isinstance(p, dict) and p.get('chainId') == 'solana' and p.get('pairAddress')]
    async with httpx.AsyncClient(timeout=10) as http:
        live = await _pair_prices(http, addrs) if addrs else {}
    now = time.time()
    out = {}
    for a in addrs:
        p = live.get(a)
        if not p:
            out[a] = {'passes': False, 'reason': 'no live market'}
            continue
        score, reason = _qualifies(p, now)
        out[a] = {'passes': score is not None, 'reason': reason}
    return {'reads': out, 'rules': RULES}


@app.get('/api/cats/trades')
async def cat_trades(pairAddress: str, catId: str = LEADER_ID):
    store = _load()
    return _pub({'trades': [e for e in store['events'] if e.get('pairAddress') == pairAddress and e['catId'] == catId and e['type'] in ('BUY', 'SELL')]})


@app.get('/api/cats/leaderboard')
async def leaderboard(view: str = 'pnl'):
    store = _load()
    rows = [_score(c) for c in store['cats'].values() if not c['revoked']]
    if view == 'volume':
        rows.sort(key=lambda r: -r['volumeSol'])
    elif view == 'win_rate':
        rows = [r for r in rows if r['winRate'] is not None]
        rows.sort(key=lambda r: -r['winRate'])
    else:
        rows.sort(key=lambda r: -r['realizedPnlSol'])
    return _pub({'rows': rows[:50]})


@app.get('/api/cats/activity')
async def activity(catId: Optional[str] = None):
    store = _load()
    events = store['events']
    if catId:
        events = [e for e in events if e['catId'] == catId]
    return _pub({'events': events[:60]})


@app.get('/api/cats/health')
async def health():
    store = _load()
    return {'ok': True, 'cats': len(store['cats']), 'events': len(store['events'])}


TUNABLE = {'minLiquidity': (10_000, 500_000), 'minVolume24h': (20_000, 5_000_000), 'minMarketCap': (20_000, 5_000_000), 'maxMarketCap': (500_000, 500_000_000),
           'minAgeHours': (0.5, 72), 'maxPositions': (1, 8), 'maxTop10Pct': (15, 50), 'maxSnipers': (0, 40), 'maxBundled': (0, 20), 'maxM5Chase': (3, 20),
           'add1At': (-35, -8), 'add2At': (-50, -15), 'hardStop': (-40, -10), 'takeProfit1': (20, 150), 'takeProfit2': (50, 400),
           'runnerTrail': (15, 50), 'maxHoldHours': (6, 96), 'maxExposure': (0.1, 0.8), 'feePerSidePct': (0.0, 5.0)}


def _apply_overrides(store):
    for k, v in (store.get('rulesOverride') or {}).items():
        if k in TUNABLE:  # clamp: settings saved under an older engine may sit outside today's safe range
            lo, hi = TUNABLE[k]
            RULES[k] = type(RULES[k])(max(lo, min(hi, float(v))))


@app.get('/api/cats/internal/rules')
async def internal_rules_get(request: Request):
    _internal(request)
    store = _load()
    return {'rules': {k: RULES[k] for k in TUNABLE}, 'bounds': TUNABLE, 'overrides': store.get('rulesOverride') or {}, 'strategyPreset': store.get('strategyPreset', 'feecat'),
            'leader': {k: store['cats'][LEADER_ID].get(k) for k in ('status', 'risk')},
            'agentLane': store['cats'][LEADER_ID].get('agentLane') or {}, 'agentLimits': _POOL_META.get('limits') or {}}


@app.post('/api/cats/internal/brain')
async def internal_brain(request: Request):
    """🪟🐱 Owner only (via HQ › Fee › NEXA's desk): NEXA trades AS FeeCat (model='nexa') or FeeCat is back on her own rules ('rules'). Paper."""
    _internal(request)
    body = await request.json()
    store = _load()
    cat = store['cats'].get(LEADER_ID)
    if not cat:
        raise HTTPException(404, 'FeeCat is not set up yet.')
    m = _set_model_brain(cat, body.get('model'))
    _log_event(store, cat, 'LEARN', f"🪟 NEXA now trades FeeCat (paper): she buys only coins NEXA says YES to — every guard still applies — and sells what NEXA says SELL." if m else 'FeeCat is back on her own rule engine.')
    _save(store)
    return {'model': cat.get('modelBrain') or 'rules'}


@app.post('/api/cats/internal/rules')
async def internal_rules_set(request: Request):
    _internal(request)
    body = await request.json()
    store = _load()
    ov = store.setdefault('rulesOverride', {})
    for k, v in (body.get('rules') or {}).items():
        if k in TUNABLE:
            lo, hi = TUNABLE[k]
            ov[k] = type(RULES[k])(max(lo, min(hi, float(v))))
    leader = store['cats'][LEADER_ID]
    if body.get('status') in ('running', 'paused'):
        leader['status'] = body['status']
    if body.get('maxPositionSol') is not None:
        leader['risk']['maxPositionSol'] = max(0.1, min(10.0, float(body['maxPositionSol'])))
    if body.get('resetLearning'):
        leader.pop('learn', None)
    if isinstance(body.get('agentLane'), dict):   # 🐱🤖 her own tuning on top of the agents' band (empty = follow the agents)
        leader['agentLane'] = clean_lane(body['agentLane'])
    if body.get('strategyPreset') in ('feecat', 'trench', 'meme', 'scalper', 'fast'):   # ⚡ fast = the one dial (agents' configs)
        store['strategyPreset'] = body['strategyPreset']
    _apply_overrides(store)
    _save(store)
    return {'ok': True, 'rules': {k: RULES[k] for k in TUNABLE}, 'status': leader['status']}


def _internal_headers():
    try:
        return {'x-feeless-internal': (DATA_DIR / 'internal.key').read_text().strip()}
    except OSError:
        return {}


def _internal(request):
    import hmac
    try:
        key = (DATA_DIR / 'internal.key').read_text().strip()
    except OSError:
        key = ''
    if not key or not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), key):
        raise HTTPException(403, 'Internal only.')


class WorkPayload(BaseModel):
    op: str
    ownerId: Optional[str] = None
    text: Optional[str] = None
    i: Optional[int] = None
    cap: Any = None
    to: Any = None                     # 🧠 'both' (default) or 0 / 1 — one model works the whole task in its own window
    job: Optional[str] = None
    tools: Optional[dict] = None
    on: Optional[bool] = None          # 🏇 op 'go': let it go on / off
    user: Optional[str] = None         # 🔑 op 'login': the owner's own username …
    secret: Optional[str] = None       # … and password — sealed at once, typed only as placeholders, never echoed or logged


@app.post('/api/cats/{cat_id}/work')
async def cat_work(cat_id: str, p: WorkPayload):
    """🧠🧠 A general cat's workbench (the cat's OWNER only): ask · state · continue / stop (a human-needed window) · stop · cap ($ per task)."""
    store = _load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise HTTPException(404, 'Cat not found.')
    if not p.ownerId or p.ownerId != cat.get('ownerId'):
        raise HTTPException(403, "Only this cat's owner can work with it.")
    b = cat.get('brainsCfg') or {}
    w = _WORK.get(cat_id)
    if p.op == 'tools':
        if w and not w.get('done'):
            raise HTTPException(409, 'Stop the current task before changing its tools.')
        try:
            cat['tools'] = _cp.toolkit(p.job or cat.get('job', 'agent'), p.tools)
            cat['job'] = p.job or cat.get('job', 'agent')
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        _save(store)
    if p.op == 'cap':
        v = max(0.005, min(TASK_CAP_MAX, float(p.cap or TASK_CAP_DEFAULT)))
        cat['taskCap'] = round(v, 4); _save(store)
        return {'cap': cat['taskCap']}
    if p.op == 'login':   # 🔑 the owner's own login for the site its window asked about: sealed in its vault, handed to the live window, the window continues
        t_ = (w or {}).get('task') or {}; wins_ = t_.get('windows') or []
        i_ = int(p.i or 0)
        if not (0 <= i_ < len(wins_)) or (wins_[i_].get('human') or {}).get('kind') != 'login':
            raise HTTPException(400, 'That window is not asking for a login.')
        site_ = wins_[i_]['human'].get('site') or ''
        if not (p.user or '').strip() or not (p.secret or ''):
            raise HTTPException(400, 'Type the username and the password.')
        try:
            _cv.put_login(cat, site_, p.user.strip(), p.secret, data_dir=DATA_DIR); _save(store)
        except (ValueError, RuntimeError) as e:
            raise HTTPException(400, str(e)[:120])
        wins_[i_]['pw'] = {'site': site_, 'user': p.user.strip()[:120], 'pw': p.secret}
        ev_ = (w or {}).get('events', {}).get(i_)
        if ev_:
            w['go'][i_] = True; ev_.set()
        return {'ok': True, 'site': site_}
    if p.op == 'reveal':   # 🔐 the owner's own reveal of one saved password (never in a list, never logged)
        try:
            return {'password': _cv.reveal(cat, p.text or '', p.job or '', data_dir=DATA_DIR)}
        except Exception as e:
            raise HTTPException(400, str(e)[:120])
    if p.op == 'unlogin':
        _cv.drop_login(cat, p.text or '', p.job or ''); _save(store)
        return {'logins': _cv.public_logins(cat)}
    if p.op == 'unmedia':
        cat['media'] = [m for m in cat.get('media') or [] if m.get('url') != p.text]; _save(store)
        return {'media': cat['media']}
    if p.op == 'mode':   # 🧭 plan together → one answer · each mind its own job
        if p.job not in _ca.MODES:
            raise HTTPException(400, 'Pick plan or jobs.')
        cat['workMode'] = p.job; _save(store)
        return {'workMode': cat['workMode']}
    if p.op == 'go':
        cat['workGo'] = bool(p.on)
        if not cat['workGo']:
            cat['workQueue'] = []
        _save(store)
    elif p.op == 'unqueue':
        q_ = list(cat.get('workQueue') or [])
        if p.i is not None and 0 <= int(p.i) < len(q_):
            q_.pop(int(p.i)); cat['workQueue'] = q_; _save(store)
    elif p.op in ('continue', 'stop_window') and w:
        ev = (w.get('events') or {}).get(int(p.i or 0))
        if ev:
            w['go'][int(p.i or 0)] = p.op == 'continue'; ev.set()
    elif p.op == 'stop' and w and w.get('task'):
        w['task']['stop'] = True
        for i, ev in list((w.get('events') or {}).items()):
            w['go'][i] = False; ev.set()
    elif p.op == 'ask':
        if b.get('kind') != 'general' or not b.get('brains'):
            raise HTTPException(400, 'Only a General AI cat with its models works in browsers.')
        busy = bool(w and not w.get('done'))
        if busy and not cat.get('workGo'):
            raise HTTPException(409, 'It is still working on your last ask — stop it, wait, or LET IT GO to queue asks.')
        why = _cp.refusal(p.text)
        if why:
            cat['refusals'] = (list(cat.get('refusals') or []) + [{'at': time.time(), 'why': why}])[-100:]
            _save(store)
            raise HTTPException(400, why)
        if not _work_live():
            raise HTTPException(400, 'Model calls are off on this server (GENERAL_CAT_LIVE) — nothing was sent or charged.')
        if not _lc.can_ask(b):
            raise HTTPException(400, 'It stopped 10 cents before its model credit ran out. Top up to ask again.')
        text = str(p.text or '').strip()
        if not text:
            raise HTTPException(400, 'Type what you want it to do.')
        if _co.parse_order(text):   # 💵 "buy 0.05 SOL of $BONK" in the chat is an ORDER on its wallet, not research: guards, then your OK (or auto)
            async with httpx.AsyncClient(timeout=15) as http_o:
                row_ = await _run_order(store, cat, text, http_o)
            cat['chat'] = (list(cat.get('chat') or []) + [{'by': 'you', 'text': text[:400], 'at': time.time()}, {'by': 'cats', 'text': row_['why'], 'at': time.time()}])[-40:]
            keep_owned(cat); _save(store)
            return {**_work_view(cat_id, owner=True), 'cap': float(cat.get('taskCap') or TASK_CAP_DEFAULT), 'credit': b.get('credit'), 'spent': b.get('spent'), 'chat': cat['chat'][-20:], 'live': _work_live(), 'order': row_}
        if busy:   # 🏇 let it go: it takes the next ask the moment this one ends
            q_ = list(cat.get('workQueue') or [])
            if len(q_) >= WORK_QUEUE_MAX:
                raise HTTPException(400, f'Its queue is full ({WORK_QUEUE_MAX}) — let it work through some first.')
            cat['workQueue'] = q_ + [{'text': text[:2000], 'to': p.to, 'at': time.time()}]; _save(store)
        else:
            _work_start(cat_id, cat, text, p.to)
    out = _work_view(cat_id, owner=True)
    return {**out, 'cap': float(cat.get('taskCap') or TASK_CAP_DEFAULT), 'credit': b.get('credit'), 'spent': b.get('spent'), 'chat': (cat.get('chat') or [])[-20:],
            'live': _work_live(), 'providers': _cb.chain(os.environ), 'go': bool(cat.get('workGo')), 'workMode': cat.get('workMode') or 'plan',
            'cloud': (b.get('cloud') or [])[-8:], 'minds': {m: v[-8:] for m, v in (b.get('minds') or {}).items()}, 'handoffs': len((w.get('task') or {}).get('handoffs') or []) if w else 0, 'createdAt': cat.get('createdAt'),
            'logins': _cv.public_logins(cat), 'media': _cv.clean_media(cat),
            'job': cat.get('job', 'agent'), 'tools': _cp.toolkit(cat.get('job', 'agent'), cat.get('tools')), 'toolkits': _cp.TOOLS,
            'refusals': (cat.get('refusals') or [])[-20:] + [{'why': x} for x in ((w or {}).get('task') or {}).get('refusals', [])],
            'artifacts': (cat.get('artifacts') or [])[-10:] + ([] if (w or {}).get('settled') else ((w or {}).get('task') or {}).get('artifacts', [])),
            'queue': [{'text': q.get('text'), 'to': q.get('to')} for q in (cat.get('workQueue') or [])]}


@app.get('/api/cats/{cat_id}/work/shot/{i}')
async def cat_work_shot(cat_id: str, i: int, ownerId: str = ''):
    """📸 A window's snapshot (JPEG) when its provider gives no live view — the cat's owner only."""
    cat = _load()['cats'].get(cat_id)
    if not cat or not ownerId or ownerId != cat.get('ownerId'):
        raise HTTPException(403, "Only this cat's owner sees its windows.")
    pages = (_WORK.get(cat_id) or {}).get('pages') or []
    pg = pages[i] if 0 <= i < len(pages) else None
    jpg = await pg.shot() if pg else None
    if not jpg:
        raise HTTPException(404, 'No snapshot right now.')
    return Response(content=jpg, media_type='image/jpeg', headers={'Cache-Control': 'no-store'})


@app.get('/api/cats/{cat_id}/agent-wallet')
async def cat_agent_wallet(cat_id: str):
    """👛 The cat's own Crossmint wallet: address, mode and its live SOL / USDC (a public address — no key, nothing private)."""
    cat = _load()['cats'].get(cat_id)
    if not cat:
        raise HTTPException(404, 'Cat not found.')
    w = cat.get('agentWallet')
    if not w:
        return {'wallet': None, 'kind': (cat.get('brainsCfg') or {}).get('kind')}
    try:
        async with httpx.AsyncClient(timeout=15) as http_b:
            if w.get('provider', 'crossmint') == 'crossmint':
                bal = await _aw.balances(http_b, os.environ.get('CROSSMINT_API_KEY', '').strip(), w['address'])
            else:   # 👁 watch-only: its balance from the chain (the trading service's holdings read)
                h_ = await http_b.get(f"{_at.TRADE}/holdings/{w['address']}", timeout=15)
                tk_ = {t_.get('mint'): float(t_.get('amount') or 0) for t_ in ((h_.json() or {}).get('tokens') or [])} if h_.status_code == 200 else None
                bal = {'sol': tk_.get(_at.SOL, 0.0), 'usdc': tk_.get('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', 0.0)} if tk_ is not None else {'error': 'no chain read'}
    except (ValueError, httpx.HTTPError) as e:
        bal = {'error': str(e)}
    return {'wallet': {k: w.get(k) for k in ('address', 'mode', 'provider', 'at', 'assigned')}, 'balance': bal, 'kind': (cat.get('brainsCfg') or {}).get('kind')}


@app.get('/api/cats/{cat_id}/profile')
async def cat_profile(cat_id: str):
    store = _load()
    _migrate(store)
    cat = store['cats'].get(cat_id)
    if not cat:
        raise HTTPException(404, 'Cat not found')
    trades = [e for e in store.get('events', []) if e.get('catId') == cat_id and e.get('type') in ('BUY', 'SELL')]
    learn = cat.get('learn') or {}
    closed = cat.get('wins', 0) + cat.get('losses', 0)
    pnls = [e.get('pnlSol') for e in trades if e.get('pnlSol') is not None]
    return _pub({
        'cat': {k: cat.get(k) for k in ('id', 'name', 'title', 'avatar', 'strategyLabel', 'level', 'xp', 'balanceSol', 'startingBalanceSol', 'realizedPnlSol',
                                        'volumeSol', 'wins', 'losses', 'winRate', 'positions', 'pnlHistory', 'status', 'lastTick', 'look', 'skin')},   # 🎨 her look rides along: every viewer sees the creator's style
        'stats': {'trades': closed, 'best': max(pnls) if pnls else None, 'worst': min(pnls) if pnls else None,
                  'roiPct': round((cat.get('balanceSol', 0) + sum(p.get('costSol', 0) for p in cat.get('positions', [])) - cat.get('startingBalanceSol', 0)) / max(cat.get('startingBalanceSol', 1), 1e-9) * 100, 2)},
        # Live discipline: 9 lives, size mode and why — computed now, the same rule the trading loop enforces.
        'discipline': feecat_brain.discipline(cat.get('exits', []), time.time()),
        'strength': cat.get('strength') or {'level': 'steady', 'mult': 1.0, 'label': feecat_brain.STRENGTH['steady']['label'], 'why': 'warming up — needs trades on record'},
        'trades': trades[:80],
        'exits': list(reversed(cat.get('exits', [])))[:30],
        'learning': {'params': {**{k: RULES[k] for k in LEARN_BOUNDS}, **{k: v for k, v in (learn.get('params') or {}).items() if k in LEARN_BOUNDS}}, 'defaults': {k: RULES[k] for k in LEARN_BOUNDS},
                     'entry': {**{k: RULES[k] for k in ENTRY_BOUNDS}, **(learn.get('entry') or {})}, 'mode': learn.get('mode', 'warming'), 'tunedAt': learn.get('tunedAt'), 'study': learn.get('study'),
                     'missed': learn.get('missed', 0), 'good': learn.get('good', 0), 'log': learn.get('log', []),
                     'playbook': feecat_brain.playbook(feecat_brain.edge_table(cat.get('setupMemory') or [])), 'memory': len(cat.get('setupMemory') or []),
                     'vetoes': (store.get('scan') or {}).get('brainRejects', [])[-5:] if cat.get('isLeader') else []},
        'rules': {k: RULES[k] for k in ('hardStop', 'add1At', 'add2At', 'takeProfit1', 'takeProfit2', 'runnerTrail', 'maxHoldHours', 'maxTop10Pct', 'maxInsiderPct', 'maxSnipers', 'maxBundled', 'maxM5Chase')},
    })


@app.get('/api/cats/{cat_id}')
async def get_cat(cat_id: str, ownerId: str = ''):
    """One cat, public view. `ownerId` (this browser's own id) only answers `mine` yes / no — the owner id itself is never returned."""
    import hmac as _hm
    store = _load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise HTTPException(404, 'Cat not found.')
    if _real.is_real(cat) and _real.expire(cat, time.time()):
        _save(store)
    out = _pub({'cat': {k: v for k, v in cat.items() if k not in ('artifacts', 'refusals')}})
    out['cat']['mine'] = bool(ownerId) and _hm.compare_digest(str(ownerId), str(cat.get('ownerId') or ''))
    return out


async def _order_pair(http, coin):
    """An order's coin → its deepest Solana pool (a mint → DexScreener /tokens; a symbol → /search)."""
    try:
        if re.fullmatch(_co.MINT, str(coin)):
            r = await http.get(f'https://api.dexscreener.com/latest/dex/tokens/{coin}')
        else:
            r = await http.get('https://api.dexscreener.com/latest/dex/search', params={'q': str(coin).lstrip('$')})
        return _co.best_pair((r.json() or {}).get('pairs') or [], coin)
    except Exception:
        return None


async def _run_order(store, cat, text, http):
    """🧭 A General cat's order: understood (words first, its brain only when the words don't parse) → guarded → REAL = a proposal your wallet
    signs · paper = a paper fill. → the order-log row (also on cat['orders'])."""
    now = time.time()
    b = cat.get('brainsCfg') or {}
    ensure_real(cat)
    order = _co.parse_order(text)
    if not order and _brains_live() and _lc.can_ask(b) and b.get('brains'):
        reply, usd = await _or_call(b['brains'][0], [{'role': 'system', 'content': _co.ORDER_SYS}, {'role': 'user', 'content': str(text)[:300]}])
        _lc.charge(b, usd)
        order = _co.order_from_json(reply)
    if not order:
        return _co.note(cat, text, None, 'unclear', '🤔 not a buy or a sell of one coin — try "buy 0.05 SOL of $BONK" or "sell half of $WIF"', now)
    if order['side'] == 'sell':
        c_ = str(order['coin']).lstrip('$').lower()
        real_ = next(((m, v) for m, v in (cat.get('realHeld') or {}).items() if m.lower() == c_ or str(v.get('symbol') or '').lower() == c_), None) if _real.is_real(cat) else None
        if real_:   # a coin its own wallet really holds
            p_ = _real.propose(cat, 'sell', real_[0], real_[1].get('pair'), real_[1].get('symbol'), f"your order: {text}", now, fraction=order['fraction'])
            _notify_real(cat, p_)
            return _co.note(cat, text, order, 'proposed', f"✍ sell {round(order['fraction'] * 100)}% — waiting for your OK", now, real_[1].get('symbol'), p_['id'])
        pos = _co.held_of(cat.get('positions'), order['coin'])
        if not pos:
            return _co.note(cat, text, order, 'refused', f"🫥 it holds no ${order['coin']}", now, order['coin'])
        if _real.is_real(cat):
            p_ = _real.propose(cat, 'sell', pos.get('mint'), pos.get('pairAddress'), pos.get('symbol'), f"your order: {text}", now, fraction=order['fraction'], px=pos.get('lastPx'))
            if not p_:
                return _co.note(cat, text, order, 'refused', '🫥 nothing real behind that coin to sell', now, pos.get('symbol'))
            _notify_real(cat, p_)
            return _co.note(cat, text, order, 'proposed', f"✍ sell {round(order['fraction'] * 100)}% — waiting for your wallet's signature", now, pos.get('symbol'), p_['id'])
        live = (await _pair_prices(http, [pos['pairAddress']])).get(pos['pairAddress']) or {}
        px = _num(live.get('priceNative')) or _num(pos.get('lastPx'))
        if not px:
            return _co.note(cat, text, order, 'refused', '📡 no live price right now — try again in a minute', now, pos.get('symbol'))
        if order['fraction'] >= 0.999:
            cat['positions'].remove(pos)
        _close(store, cat, pos, px, f"🧭 your order: {text}", order['fraction'], _num(live.get('marketCap') or live.get('fdv')))
        return _co.note(cat, text, order, 'filled', f"📄 paper: sold {round(order['fraction'] * 100)}% at the live price", now, pos.get('symbol'))
    p = await _order_pair(http, order['coin'])
    ok, why = _co.buy_guards(p, now * 1000)
    if not ok:
        return _co.note(cat, text, order, 'refused', why, now, order['coin'])
    sym = (p.get('baseToken') or {}).get('symbol') or order['coin']
    safe, swhy, _conv = await _safety(http, p)
    if not safe:
        return _co.note(cat, text, order, 'refused', f'🛡 {swhy}', now, sym)
    real = _real.is_real(cat)
    sol, capped = _co.size_of(order, _num((cat.get('risk') or {}).get('maxPositionSol')) or None, cat.get('budgetSol') if real else None)
    px = _num(p.get('priceNative'))
    if real:
        p_ = _real.propose(cat, 'buy', (p.get('baseToken') or {}).get('address'), p.get('pairAddress'), sym, f"your order: {text}", now, sol=sol, px=px)
        if not p_:
            return _co.note(cat, text, order, 'refused', '🫥 could not build the proposal', now, sym)
        _notify_real(cat, p_)
        return _co.note(cat, text, order, 'proposed', f"✍ buy {p_['sol']:g} SOL{capped} — guards passed, waiting for your wallet's signature", now, sym, p_['id'])
    if sol <= 0 or cat.get('balanceSol', 0) < sol or not px:
        return _co.note(cat, text, order, 'refused', f"💰 paper balance {cat.get('balanceSol', 0):.3f} SOL — not enough for {sol:g} SOL", now, sym)
    cat['balanceSol'] = round(cat['balanceSol'] - sol, 6)
    cat['positions'].append({'mint': (p.get('baseToken') or {}).get('address'), 'pairAddress': p.get('pairAddress'), 'symbol': sym, 'provider': 'DexScreener',
                             'url': p.get('url'), 'costSol': sol, 'notionalSol': round(sol * (1 - fee_side()), 6), 'entryPriceNative': px, 'entryPriceUsd': p.get('priceUsd'),
                             'entryChange': 0, 'currentChange': 0, 'peakChange': 0, 'openedAt': now, 'reason': public_words(f'🧭 your order: {text}'),
                             'entryLiq': _num((p.get('liquidity') or {}).get('usd')), 'conviction': 1.0, 'entryMarketCapUsd': _num(p.get('marketCap') or p.get('fdv')),
                             'entryVolH1': _num((p.get('volume') or {}).get('h1')), 'plannedSol': sol, 'firstEntryPriceNative': px, 'adds': 0, 'profitTaken': 0,
                             'peakPx': px, 'order': True})
    _log_event(store, cat, 'BUY', f"Bought {sol} SOL of {sym} at live price — 🧭 your order (paper).", None, p.get('pairAddress'), px, _num(p.get('marketCap') or p.get('fdv')))
    return _co.note(cat, text, order, 'filled', f"📄 paper: bought {sol:g} SOL{capped} at the live price — guards passed", now, sym)


class ActionPayload(BaseModel):
    action: str
    ownerId: Optional[str] = None      # 🔒 every action is the cat's own owner's (the browser id that created it)
    address: Optional[str] = None      # 💵 real mode: the signed-in wallet …
    session: Optional[str] = None      # … and its FEELESS session (one signature, 7 days)
    budgetSol: Any = None
    proposal: Optional[str] = None
    result: Optional[str] = None
    sig: Optional[str] = None
    amount: Any = None
    maxPositionSol: Any = None
    maxDailyLossSol: Any = None
    allowlist: Optional[str] = None
    blocklist: Optional[str] = None
    text: Optional[str] = None
    look: Optional[dict] = None        # 🎨 Fee's look (the creator's wallet only)
    limits: Optional[dict] = None      # 🎚 controls: a general agent's spend limits (clean_limits)
    mode: Optional[str] = None         # 👛 agent_mode: approve | auto (a GENERAL cat's switch)
    provider: Optional[str] = None     # 🔐 api_key: which drawer slot …
    secret: Optional[str] = None       # … and the key (empty = remove it); sealed at once, never echoed
    venues: Optional[list] = None      # 📈 venues: the FEELESS rails a trading cat may use
    brains: Optional[list] = None      # 🔁 models: switch its models (24 h after it was made)
    workMode: Optional[str] = None     # 🧭 work_mode: plan · jobs
    memory: Optional[str] = None       # 🔁 models: 'keep' its memory (cloud + decisions) or start 'fresh' with the new models


def owner_wallets():
    return [w.strip() for w in os.environ.get('FEELESS_ADMIN_WALLETS', '').split(',') if w.strip()]


async def _is_creator(addr):
    """👑 the creator through ANY linked wallet (reputation's `_is_staff`) — Fee's real switch is the creator's, whichever of their wallets signed."""
    try:
        async with httpx.AsyncClient(timeout=5) as h:
            r = await h.get(f'http://127.0.0.1:5077/api/reputation/admin/is-admin/{addr}')
            return bool(r.status_code == 200 and (r.json().get('staff') or r.json().get('owner')))
    except Exception:
        return False


def free_credit_ok(cat, creator=False):
    """💳 Live model credit costs real money: a real agent buys it (/cats/{id}/fund, purpose credit); only a paper rule cat or a creator wallet refills free."""
    return bool(creator or not (cat.get('agentWallet') or (cat.get('brainsCfg') or {}).get('kind') == 'general'))


def fee_owner_real(cat, action, signed, owners=None):
    """💵🐱 FEE GOES REAL — owner only (2026-10-23: "see NEXA trade real money as FeeCat"): Fee belongs to the system, so only a signed-in OWNER
    wallet (FEELESS_ADMIN_WALLETS — never a granted role) may switch her real / paper or answer her proposals. Real = every buy NEXA calls is
    a proposal that wallet signs (≤ its per-buy budget); FEELESS never moves the money. Pure (tests)."""
    return bool(cat.get('isLeader') and action in ('real', 'paper', 'proposal', 'look') + _LEADER_AGENT and signed and signed in (owner_wallets() if owners is None else owners))


_LEADER_AGENT = ('agent_wallet', 'agent_mode', 'agent_assign', 'agent_approve', 'skin', 'models', 'brief', 'brief_propose', 'brief_approve', 'brief_dismiss')   # 👛 Fee's own wallet: the creator's signed wallet only (N16)


LOOK_KEYS = ('coat', 'pattern', 'gear', 'eyes', 'aura')


def clean_fee_look(look):
    """🎨 The creator's look for Fee (owner, 2026-10-23: "creator controls Fee — coat / gear / eyes / name"): each part one short lowercase key
    (the page draws only keys it knows — an unknown one falls back to her default), her name ≤ 24 chars, her title ≤ 48. Pure (tests)."""
    l = look if isinstance(look, dict) else {}
    out = {k: str(l[k]).lower()[:16] for k in LOOK_KEYS if re.fullmatch(r'[A-Za-z0-9-]{1,16}', str(l.get(k) or ''))}
    for k, n in (('name', 24), ('title', 48)):
        v = ' '.join(re.sub(r'[<>{}\[\]]', '', str(l.get(k) or '')).split())[:n]
        if v:
            out[k] = public_words(v)
    return out


class RecoverPayload(BaseModel):
    handle: str
    pin: str
    ownerId: str


@app.post('/api/cats/{cat_id}/recovery-pin')
async def cat_recovery_pin(cat_id: str, payload: ActionPayload):
    """🔑 Its recovery PIN: made once, shown once, only the hash kept. A lost PIN can only be replaced by the owner's browser (`text` = 'replace')."""
    store = _load()
    cat = store['cats'].get(cat_id)
    if not cat or cat.get('isLeader'):
        raise HTTPException(404, 'Cat not found.')
    if not payload.ownerId or payload.ownerId != cat.get('ownerId'):
        raise HTTPException(403, 'Only its owner can make its recovery PIN.')
    if cat.get('recovery') and payload.text != 'replace':
        raise HTTPException(409, 'Its recovery PIN was already shown once.')
    pin = _recovery.new_pin()
    cat['recovery'], cat['recoverySet'] = _recovery.seal(pin), True
    keep_owned(cat); _save(store)
    return {'pin': pin}


@app.post('/api/cats/recover')
async def cat_recover(payload: RecoverPayload):
    """🔑 A new browser takes its agent back with the PIN. The PIN is single-use and never moves money; the owner makes a fresh one after."""
    if not payload.ownerId.strip() or len(payload.ownerId) > 100:
        raise HTTPException(400, 'No browser id.')
    store = _load()
    handle = payload.handle.strip().lstrip('@').lower()
    cat = next((c for c in store['cats'].values() if not c.get('isLeader') and handle and str(c.get('handle') or '').lower() == handle and c.get('recovery')), None)
    if not cat:
        raise HTTPException(403, 'That handle and PIN do not match.')
    result = _recovery.check(cat['recovery'], payload.pin, time.time())
    if result != 'ok':
        _save(store)
        raise HTTPException(429 if result == 'locked' else 403, 'Too many tries: this PIN is locked for an hour.' if result == 'locked' else 'That handle and PIN do not match.')
    cat['ownerId'] = payload.ownerId
    cat.pop('recovery'); cat['recoverySet'] = False
    _log_event(store, cat, 'STARTED', f"{cat['name']} was recovered on a new browser with its PIN.")
    keep_owned(cat); _save(store)
    return {'cat': {**_no_keys(cat), 'mine': True}}


@app.post('/api/cats/{cat_id}/action')
async def cat_action(cat_id: str, payload: ActionPayload, request: Request):
    store = _load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise HTTPException(404, 'Cat not found.')
    signed = _real.session_wallet(_real.load_sessions(DATA_DIR / 'chat_sessions.json'), payload.session)
    if cat.get('isLeader') and payload.action in ('real', 'paper', 'proposal', 'look') + _LEADER_AGENT and not request.headers.get('x-feeless-internal'):
        if not signed:   # a missing / expired sign-in used to fall through to the internal-key check and read as a mystery 403
            raise HTTPException(401, 'Sign in with your wallet first (one signature, no transaction) — your sign-in expired.')
        if not fee_owner_real(cat, payload.action, signed) and not await _is_creator(signed):
            raise HTTPException(403, "Only the creator's wallets can switch Fee real — this wallet isn't linked to the creator.")
    elif not fee_owner_real(cat, payload.action, signed) and (not payload.ownerId or payload.ownerId != cat.get('ownerId')):   # 🔒 the owner only
        _internal(request)                                             # … or HQ (reputation's admin run, internal key)
    if payload.action in ('real', 'proposal', 'agent_wallet', 'agent_mode', 'agent_approve', 'agent_assign') and (not signed or signed != payload.address):
        raise HTTPException(401, 'Sign in with your wallet first (one signature, no transaction).')

    if payload.action == 'real':   # 💵 option A: the cat proposes, this wallet signs every trade
        try:
            _real.go_real(cat, signed, payload.budgetSol, time.time()); cat.pop('paperByOwner', None)
        except ValueError as e:
            raise HTTPException(400, str(e))
        _log_event(store, cat, 'STARTED', f"{cat['name']} is REAL now: it proposes every trade to your wallet (≤ {cat['budgetSol']} SOL a buy); you sign each one.")
    elif payload.action == 'paper':
        _real.go_paper(cat); cat['paperByOwner'] = True
        _log_event(store, cat, 'STOPPED', f"{cat['name']} is back on paper — no more proposals.")
    elif payload.action == 'agent_wallet':   # 👛 its own Crossmint wallet (DECISIONS #2, owner 2026-10-29): the same wallet on a repeat
        if not cat.get('agentWallet'):
            mine_ = sum(1 for c_ in store['cats'].values() if (c_.get('agentWallet') or {}).get('owner') == signed)
            if mine_ >= _AGENT_MAX:
                raise HTTPException(400, f'Up to {_AGENT_MAX} cats with their own wallet per owner — you have {mine_}.')
            try:
                async with httpx.AsyncClient(timeout=40) as http_w:
                    if os.environ.get('CIRCLE_AGENT_API_KEY', '').strip():   # 🟦 the separate Circle account for family + agent wallets (never the FEELESS creator account)
                        rc_ = await http_w.post('http://127.0.0.1:5077/api/reputation/internal/agent-circle-wallet', headers=_internal_headers(), json={'catId': cat_id})
                        if rc_.status_code != 200:
                            raise ValueError(f"Circle did not make the wallet: {str((rc_.json() if rc_.content else {}).get('detail') or rc_.status_code)[:140]}")
                        w_ = rc_.json().get('wallet') or {}
                        store = _load(); cat = store['cats'][cat_id]   # the call took seconds: work on the store as it is now
                        cat['agentWallet'] = {**_aw.record('cat', cat_id, {'address': w_.get('address'), 'locator': f"circle:{w_.get('id')}"}, signed, time.time(), (cat.get('brainsCfg') or {}).get('kind')),
                                              'provider': 'circle', 'circleAcct': 'agent', 'circleId': w_.get('id')}
                    else:
                        rep_ = await _aw.create(http_w, os.environ.get('CROSSMINT_API_KEY', '').strip(), 'cat', cat_id)
                        cat['agentWallet'] = _aw.record('cat', cat_id, rep_, signed, time.time(), (cat.get('brainsCfg') or {}).get('kind'))
            except ValueError as e:
                raise HTTPException(400, str(e))
            ensure_real(cat)
            _log_event(store, cat, 'STARTED', f"{cat['name']} has its own wallet now: {cat['agentWallet']['address'][:6]}… — fund it to put it to work.")
    elif payload.action == 'agent_withdrew':   # ↩ reputation's /cats/{id}/withdraw (internal key only): the money went back to the owner's wallet
        a_ = payload.amount if isinstance(payload.amount, dict) else {}
        _log_event(store, cat, 'WITHDRAW', f"{a_.get('amount')} {a_.get('token')} sent back to its owner's wallet ({str(payload.sig)[:10]}…).")
    elif payload.action == 'agent_funded':   # 💵 reputation's /cats/{id}/fund/send (internal key only — the branch above): a verified, sent funding
        a_ = payload.amount if isinstance(payload.amount, dict) else {}
        if not payload.sig or any(str(x.get('sig')) == payload.sig for x in (cat.get('agentFunded') or []) + (cat.get('creditPaid') or [])):
            raise HTTPException(400, 'No signature, or that funding is on the record already.')
        cr_ = max(0.0, _num(a_.get('creditUsd')) or 0.0)
        if cr_:   # 🧠 the model-credit share of this payment
            cat['creditPaid'] = (list(cat.get('creditPaid') or []) + [{'sig': str(payload.sig)[:100], 'usd': cr_, 'token': a_.get('token'), 'at': round(time.time())}])[-50:]
            if cat.get('brainsCfg'):
                cat['brainsCfg']['credit'] = round((cat['brainsCfg'].get('credit') or 0) + cr_, 6); cat.pop('brainPaused', None)
            _log_event(store, cat, 'STARTED', f"{cat['name']}: ${cr_:g} of model credit added.")
        if not a_.get('catLamports'):   # all of it was credit: no wallet funding on the record
            keep_owned(cat); _save(store)
            return {'cat': {**_no_keys(cat), 'mine': not cat.get('isLeader')}}
        cat['agentFunded'] = (list(cat.get('agentFunded') or []) + [{'sig': str(payload.sig)[:100], 'state': payload.result or 'confirmed', 'at': round(time.time()),
                              **{k: a_.get(k) for k in ('usd', 'feeUsd', 'catLamports', 'feeLamports', 'solUsd', 'token')}}])[-50:]
        ensure_real(cat)   # funded: its orders now use its wallet
        got_ = f"{(a_.get('catLamports') or 0) / 1e6:.2f} USDC" if a_.get('token') == 'USDC' else f"{round((a_.get('catLamports') or 0) / 1e9, 4)} SOL"
        _log_event(store, cat, 'STARTED', f"{cat['name']} funded: ${a_.get('usd')} — {got_} into its wallet"
                   + (f" (one-time FEELESS fee ${a_.get('feeUsd'):g})" if a_.get('feeUsd') else '') + '.')
    elif payload.action == 'agent_assign':   # 👛 N16: Fee takes a wallet the creator already has (a user's cat always gets a fresh one)
        if not cat.get('isLeader'):
            raise HTTPException(400, 'Only Fee takes an assigned wallet — your own cats get a fresh wallet of their own.')
        addr_ = str(payload.text or '').strip()
        try:
            async with httpx.AsyncClient(timeout=15) as http_l:
                rep_ = await _aw.lookup(http_l, os.environ.get('CROSSMINT_API_KEY', '').strip(), addr_)
            cat['agentWallet'] = _aw.assigned(addr_, rep_, signed, time.time())
            if rep_ is None:   # 🟦 not Crossmint's — one of the creator's own CIRCLE wallets? then Circle signs and she trades from it
                async with httpx.AsyncClient(timeout=15) as http_c:
                    rc_ = await http_c.get('http://127.0.0.1:5077/api/reputation/internal/circle-wallet', params={'address': addr_}, headers=_internal_headers())
                if rc_.status_code == 200 and (rc_.json() or {}).get('id'):
                    cat['agentWallet'].update(provider='circle', circleId=rc_.json()['id'])
        except (ValueError, httpx.HTTPError) as e:
            raise HTTPException(400, str(e))
        prov_ = cat['agentWallet'].get('provider')
        _log_event(store, cat, 'STARTED', f"{cat['name']}'s wallet is {addr_[:6]}… — " + ('she trades from it (Crossmint holds its key).' if prov_ == 'crossmint'
                   else 'she trades from it (your Circle wallet — Circle signs, inside her caps).' if prov_ == 'circle'
                   else "WATCH-ONLY: neither Crossmint nor your Circle project holds its key, so she shows it but never trades from it."))
    elif payload.action == 'agent_mode':   # 👛 a GENERAL cat: approve every AI move, or let it do its thing
        if not cat.get('agentWallet'):
            raise HTTPException(400, 'Make its wallet first.')
        try:
            cat['agentWallet'] = _aw.set_mode(cat['agentWallet'], payload.mode, (cat.get('brainsCfg') or {}).get('kind'))
        except ValueError as e:
            raise HTTPException(400, str(e))
        _log_event(store, cat, 'STARTED', f"{cat['name']}: {'does its thing — AI moves go ahead on its own' if payload.mode == 'auto' else 'asks first — every AI move waits for your OK'}.")
    elif payload.action == 'agent_approve':   # ✋ ASK ME: the owner's OK on one proposal → its wallet sends it on the engine's next pass
        p_ = next((x for x in cat.get('proposals') or [] if x.get('id') == payload.proposal), None)
        if not (cat.get('agentWallet') or {}).get('address') or not p_ or p_.get('status') != 'pending':
            raise HTTPException(400, 'Nothing waiting to approve.')
        p_['approved'], p_['approvedBy'] = time.time(), signed
        _log_event(store, cat, 'TRADE', f"{cat['name']}: you approved {p_['side'].upper()} ${p_.get('symbol')} — its wallet sends it now.")
    elif payload.action == 'proposal':
        if signed != cat.get('realWallet'):
            raise HTTPException(403, "Only the cat's real wallet answers its proposals.")
        try:
            _real.resolve(cat, payload.proposal, payload.result, time.time(), payload.sig)
        except ValueError as e:
            raise HTTPException(400, str(e))
    elif payload.action == 'confirm_recovery':   # 🔐 the owner ticked "I saved my recovery phrase" before the first funding (kept as a timestamp)
        cat['recoveryConfirmedAt'] = time.time()
    elif payload.action == 'api_key':   # 🔐 the API drawer: seal one key (or remove it) — the response carries the last 4 only
        try:
            _ck.put(cat, payload.provider, payload.secret, data_dir=DATA_DIR) if payload.secret else _ck.drop(cat, payload.provider)
        except (ValueError, RuntimeError) as e:
            raise HTTPException(400, str(e))
    elif payload.action == 'venues':   # 📈 where a trading cat trades — FEELESS rails only
        try:
            cat['venues'] = _ck.venues(payload.venues)
        except ValueError as e:
            raise HTTPException(400, str(e))
    elif payload.action == 'chime':   # 🚀 the owner's advice — the brain reads it, it never trades on it
        if not cat.get('brainsCfg'):
            raise HTTPException(400, 'This Cat has no AI brain.')
        try:
            _lc.chime(cat['brainsCfg'], payload.text)
        except ValueError as e:
            raise HTTPException(400, str(e))
    elif payload.action == 'look':   # 🎨 the creator restyles Fee (a signed owner wallet only — fee_owner_real; a user's cat look lives in Build a cat)
        if not cat.get('isLeader') or not fee_owner_real(cat, 'look', signed):
            raise HTTPException(403, "Only FEELESS's creator wallet styles Fee — sign in with it.")
        cat['look'] = clean_fee_look(payload.look)
        if cat['look'].get('name'):
            cat['name'] = cat['look']['name']
        if cat['look'].get('title'):
            cat['title'] = cat['look']['title']
    elif payload.action == 'order':   # 🧭 a GENERAL cat: your order in plain words → one guarded proposal (real) or a paper fill
        if (cat.get('brainsCfg') or {}).get('kind') != 'general':
            raise HTTPException(400, 'Only a General AI cat takes orders — a Trading cat hunts on its own.')
        if not str(payload.text or '').strip():
            raise HTTPException(400, 'Write the order first — e.g. "buy 0.05 SOL of $BONK".')
        async with httpx.AsyncClient(timeout=15) as http_o:
            await _run_order(store, cat, payload.text, http_o)
    elif payload.action == 'pull':   # 🚀 pull everything: positions sold at the last live price, balance out, locked until a top-up
        for pos in list(cat['positions']):
            cat['positions'].remove(pos)
            _close(store, cat, pos, _num(pos.get('lastPx')) or pos['entryPriceNative'], 'owner pulled all funds')
        amount = cat['balanceSol']; cat['balanceSol'] = 0.0; cat['status'] = 'stopped'; cat['needsTopup'] = True
        _log_event(store, cat, 'WITHDRAW', f'Owner pulled all funds ({amount:.4f} SOL, paper). The Cat is locked until a top-up.')
    elif payload.action == 'topup':   # paper top-up: the starting balance back, and (pay as you go) the model credit back
        cat['balanceSol'] = round(cat['balanceSol'] + float(cat.get('startingBalanceSol') or 10), 6); cat['needsTopup'] = False
        if cat.get('brainsCfg') and free_credit_ok(cat, bool(signed and await _is_creator(signed))):
            cat['brainsCfg']['credit'] = round((cat['brainsCfg'].get('credit') or 0) + _lc.START_CREDIT, 6); cat.pop('brainPaused', None)
        _log_event(store, cat, 'STARTED', f'{cat["name"]} topped up.')
    elif payload.action == 'start':
        if cat.get('needsTopup'):
            raise HTTPException(400, 'Funds were pulled — top up before starting this Cat again.')
        if cat.get('brainsCfg') and not _lc.can_ask(cat['brainsCfg']) and cat['brainsCfg'].get('billing') == 'payg':
            raise HTTPException(400, 'Model credit is used up — top up to start again.')
        if cat['revoked']:
            raise HTTPException(400, 'This Cat has been revoked and cannot restart.')
        cat['status'] = 'running'
        cat['lastTick'] = time.time()
        _log_event(store, cat, 'STARTED', f'{cat["name"]} started paper trading.')
    elif payload.action == 'stop':
        cat['status'] = 'stopped'
        _log_event(store, cat, 'STOPPED', f'{cat["name"]} stopped by owner.')
    elif payload.action == 'run':
        if cat['status'] == 'running':
            await run_engine(store, [cat])
    elif payload.action == 'controls':
        if payload.maxPositionSol is not None:
            cat['risk']['maxPositionSol'] = float(payload.maxPositionSol)
        if payload.maxDailyLossSol is not None:
            cat['risk']['maxDailyLossSol'] = float(payload.maxDailyLossSol)
        if payload.allowlist is not None:
            cat['risk']['allowlist'] = [s.strip() for s in payload.allowlist.split(',') if s.strip()]
        if payload.blocklist is not None:
            cat['risk']['blocklist'] = [s.strip() for s in payload.blocklist.split(',') if s.strip()]
        if _real.is_real(cat) and payload.maxPositionSol is not None and cat.get('agentWallet'):   # its wallet's per-buy budget follows MAX A TRADE
            cat['budgetSol'] = round(max(_real.MIN_BUDGET, min(_real.MAX_BUDGET, float(payload.maxPositionSol))), 4)
        if payload.limits is not None:   # 🎚 a general agent: $ a task · $ a mind · steps · $ a day (enforced in _work_start + cat_agent._ask)
            cat['limits'] = clean_limits(payload.limits)
            if _num(payload.limits.get('taskUsd')):
                cat['taskCap'] = round(max(0.005, min(TASK_CAP_MAX, float(_num(payload.limits.get('taskUsd'))))), 4)
    elif payload.action == 'withdraw':
        amount = min(float(payload.amount or 0), cat['balanceSol'])
        cat['balanceSol'] = round(cat['balanceSol'] - amount, 6)
        _log_event(store, cat, 'WITHDRAW', f'Paper withdrawal of {amount:.4f} SOL recorded.')
    elif payload.action == 'skin':   # 🎨 its desk look (backdrop clip + card colour), set by its owner — everyone who opens this agent sees the same desk
        sk_ = payload.look or {}
        bg_, acc_ = str(sk_.get('bg') or ''), str(sk_.get('acc') or '')
        if bg_ not in DESK_SCENES or not re.fullmatch(r'#[0-9a-fA-F]{6}', acc_):
            raise HTTPException(400, 'Pick a backdrop and a card colour.')
        cat['skin'] = {'bg': bg_, 'acc': acc_.lower()}
    elif payload.action in ('brief', 'brief_propose', 'brief_approve', 'brief_dismiss'):   # 📜 a GENERAL agent's one brief for both minds (owner 2026-10-30)
        b_ = cat.get('brainsCfg') or {}
        if b_.get('kind') != 'general' and not cat.get('isLeader'):
            raise HTTPException(400, "A trader's brief is sealed when you buy it — only a general agent's brief can change.")
        if not b_.get('brains'):
            raise HTTPException(400, 'Give it a model first — its brief rides on its models.')
        now_ = time.time()
        if payload.action == 'brief':   # you rewrite it — once an hour (Fee's: the creator, any time)
            left_ = BRIEF_EVERY - (now_ - float(b_.get('briefAt') or 0))
            if left_ > 0 and not cat.get('isLeader'):
                raise HTTPException(400, f'You can change its brief once an hour — {max(1, round(left_ / 60))} min to go.')
            txt_ = ' '.join(str(payload.text or '').split())[:_lc.PROMPT_MAX]
            if len(txt_) < 20:
                raise HTTPException(400, 'Write a brief of at least a sentence.')
            b_.update(prompt=txt_, briefAt=now_, briefProposal=None)
        elif payload.action == 'brief_propose':   # its minds propose ONE better brief for both of them — at most once an hour, live only when you approve
            if now_ - float(b_.get('briefAskAt') or 0) < BRIEF_EVERY:
                raise HTTPException(400, 'Its minds can propose a new brief once an hour.')
            recent_ = ' | '.join(str(m.get('text') or '')[:160] for m in (cat.get('chat') or [])[-8:])
            msgs_ = [{'role': 'system', 'content': 'You and the other mind share ONE standing brief from your owner. Propose a better single brief that makes BOTH of you more useful '
                      'for what the owner actually asks, keeping every safety line. Answer ONLY JSON {"brief": "<= 1100 chars", "why": "one sentence"}.'},
                     {'role': 'user', 'content': f"Current brief: {b_.get('prompt') or '(none)'}\nRecent asks + answers: {recent_ or '(none yet)'}"}]
            text_, usd_ = await _or_call(b_['brains'][0], msgs_, max_tokens=700, **({'key': k_} if (k_ := _ck.key_for(cat, 'openrouter', data_dir=DATA_DIR)) else {}))
            got_ = _ca.parse_json(text_)
            if not k_:
                _lc.charge(b_, usd_)
            b_['briefAskAt'] = now_
            if not str(got_.get('brief') or '').strip():
                raise HTTPException(502, 'Its minds did not propose a brief this time.')
            b_['briefProposal'] = {'text': ' '.join(str(got_['brief']).split())[:_lc.PROMPT_MAX], 'why': str(got_.get('why') or '')[:200], 'at': now_}
        elif payload.action == 'brief_approve':
            pr_ = b_.get('briefProposal')
            if not pr_:
                raise HTTPException(400, 'Nothing to approve.')
            b_.update(prompt=pr_['text'], briefAt=now_, briefProposal=None)
        else:
            b_['briefProposal'] = None
        cat['brainsCfg'] = b_
    elif payload.action == 'work_mode':   # 🧭 how a general cat's two minds work: plan together → split → merge, or each its own job
        if payload.workMode not in _ca.MODES:
            raise HTTPException(400, 'Pick plan or jobs.')
        cat['workMode'] = payload.workMode
    elif payload.action == 'models':   # 🔁 owner 2026-10-30: you keep your agent forever; its models can be switched 24 h after you got it (Fee: any time, the creator)
        left = MODEL_LOCK_SEC - (time.time() - float(cat.get('createdAt') or 0))
        if left > 0 and not cat.get('isLeader'):
            raise HTTPException(400, f'Its models can change 24 h after you got it — {left / 3600:.1f} h to go.')
        if not cat.get('brainsCfg') and not cat.get('isLeader'):
            raise HTTPException(400, 'This cat has no AI models.')
        cat_ = await _or_models()
        try:   # the brief and credit carry over; its memory (cloud + decisions) too, unless you start fresh
            prev_ = cat.get('brainsCfg') or {'kind': 'trading', 'billing': 'payg'}
            cat['brainsCfg'] = _lc.clean({'brains': payload.brains, 'brainKind': prev_.get('kind') or 'trading', 'billing': prev_.get('billing') or 'payg', 'prompt': payload.text or ''},
                                         prev_ if cat.get('brainsCfg') else None, {m['id'] for m in cat_.get('models') or []} or None, max_models=await _model_limit(payload.session or ''))
        except ValueError as e:
            raise HTTPException(400, str(e))
        if payload.memory == 'fresh':   # 🧹 a clean slate for the new models: its old memory is deleted, never mixed in
            cat['brainsCfg'].update(cloud=[], decisions=[], minds={})
        elif payload.memory == 'sort':   # 🧠 the NEW lead model reads its old cloud and keeps only what still helps (the rest is deleted)
            asyncio.create_task(_sort_cloud(cat_id, cat['brainsCfg']['brains'][0]))
        _log_event(store, cat, 'LEARN', f"🔁 new models: {' + '.join(m.split('/')[-1] for m in cat['brainsCfg']['brains'])}")
    elif payload.action == 'delete':   # 🗑 forever means until YOU delete it: retired first, typed name, and never while its own wallet still holds money
        if not cat.get('revoked'):
            raise HTTPException(400, 'Retire it first, then delete it for good.')
        if str(payload.text or '').strip().lower() != str(cat.get('name') or '').strip().lower():
            raise HTTPException(400, "Type the agent's name to delete it for good.")
        w_ = (cat.get('agentWallet') or {}).get('address')
        if w_:
            try:
                async with httpx.AsyncClient(timeout=15) as h_:
                    bal_ = await _aw.balances(h_, os.environ.get('CROSSMINT_API_KEY', ''), w_)
            except ValueError as e:
                raise HTTPException(409, f"Couldn't read its wallet ({e}) — nothing deleted.")
            if float(bal_.get('sol') or 0) > 0.001 or float(bal_.get('usdc') or 0) > 0.01:
                raise HTTPException(409, f"Its wallet still holds {bal_.get('sol')} SOL / {bal_.get('usdc')} USDC — withdraw it first.")
        store['cats'].pop(cat_id, None)
        _WORK.pop(cat_id, None)
        _save(store)
        return {'cat': None, 'deleted': cat_id}
    elif payload.action == 'revoke':
        cat['revoked'] = True
        cat['status'] = 'stopped'
        _log_event(store, cat, 'STOPPED', f'{cat["name"]} was revoked.')
    else:
        raise HTTPException(400, f'Unknown action: {payload.action}')

    keep_owned(cat); _save(store)
    return {'cat': {**_no_keys(cat), 'mine': not cat.get('isLeader')}}   # the action passed the owner check (Fee's: the creator's signature)
