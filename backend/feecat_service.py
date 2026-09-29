"""
FEELESS Cats — the paper-trading agent lab backend.

Paper trading against REAL live markets: every entry and exit is marked at the
actual DexScreener SOL-native price of a real Solana pair at that moment, with a
1% per-side fee/slippage haircut. Only the money is simulated — never the prices.

File-backed JSON store, zero external dependencies, standalone FastAPI app.
"""
import env_loader  # noqa: F401  (must run before reading os.environ)
import asyncio
import json
import os
import math
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATA_DIR = Path(__file__).parent / 'data'
DATA_DIR.mkdir(exist_ok=True)
STORE_PATH = DATA_DIR / 'feecats.json'

TICK_SECONDS = 20
SIGNAL_SYMBOLS = ['BRAIN', 'HOLDSWEET', 'UPTOBER', 'CHUBBY', 'TEXTIT', 'POLAR', 'INU', 'GOONER']
BRAIN_CATALOG = [
    {'id': 'claude-opus', 'provider': 'Anthropic', 'label': 'Claude Opus 5.5'},
    {'id': 'claude-fable', 'provider': 'Anthropic', 'label': 'Claude Fable 5.1'},
    {'id': 'gpt-astra', 'provider': 'OpenAI', 'label': 'GPT-6 Astra'},
    {'id': 'gpt-sol', 'provider': 'OpenAI', 'label': 'GPT-6 Sol'},
    {'id': 'muse', 'provider': 'Meta', 'label': 'Muse Spark 1.3'},
    {'id': 'grok', 'provider': 'xAI', 'label': 'Grok 4.7'},
    {'id': 'gemini', 'provider': 'Google', 'label': 'Gemini 3.8 Flash'},
    {'id': 'qwen', 'provider': 'Alibaba', 'label': 'Qwen 3.8 Max'},
    {'id': 'kimi', 'provider': 'Moonshot', 'label': 'Kimi K3'},
    {'id': 'deepseek', 'provider': 'DeepSeek', 'label': 'DeepSeek V4 Pro'},
]
STRATEGY_LABELS = {'balanced': 'Momentum', 'momentum': 'Breakouts', 'conservative': 'Scalping', 'signals': 'On-chain signals', 'trend': 'Trend following', 'conviction': 'Conviction'}


def _empty_store():
    return {'cats': {}, 'events': []}


def _load() -> dict:
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text())
        except Exception:
            pass
    return _empty_store()


def _save(store: dict):
    STORE_PATH.write_text(json.dumps(store, indent=2))


def _log_event(store, cat, kind, detail, pnl=None, pair=None, price=None, market_cap=None, entry_market_cap=None):
    store['events'].insert(0, {
        'id': uuid.uuid4().hex, 'catId': cat['id'], 'catName': cat['name'],
        'type': kind, 'detail': detail, 'ts': time.time() * 1000,
        'pnlSol': pnl, 'decisionSource': 'selected_brain' if cat.get('brainProfile', {}).get('available') else 'rule_engine',
        'brainLabel': cat.get('brainLabel'), 'pairAddress': pair, 'priceNative': price,
        # Persisted with the paper receipt so shared cards never invent MC data later.
        'marketCapUsd': market_cap, 'entryMarketCapUsd': entry_market_cap,
    })
    store['events'] = store['events'][:200]


FEE_PER_SIDE = 0.01
ENGINE_VERSION = 'live-v2'  # v3 logic below is additive; keeps the existing track record
LEADER_ID = 'leader'
MARKET_FEED = 'http://127.0.0.1:5001/api/market/feed?kind={kind}&chain=solana&page={page}'
RULES = {'minLiquidity': 40_000, 'minVolume24h': 100_000, 'minMarketCap': 150_000, 'maxMarketCap': 50_000_000,
         'minAgeHours': 3, 'h1Min': 3, 'h1Max': 40, 'h6Max': 120, 'h24Max': 400, 'minBuySellRatio': 1.2,
         'maxPositions': 5, 'cooldownHours': 2,
         # safety gates at entry
         'maxM5Chase': 8, 'maxTop10Pct': 35, 'maxInsiderPct': 20, 'maxDevPct': 10, 'maxSnipers': 15, 'maxBundled': 10,
         # Trench Lord v2 — thesis-based position management (see run_engine):
         # open with a starter, add on healthy dips (re-averaging the entry), hold while the thesis holds,
         # take profit in pieces, let a runner ride, and cut only when the thesis breaks or the hard stop hits.
         'starterFraction': 0.5, 'add1At': -18, 'add1Fraction': 0.3, 'add2At': -32, 'add2Fraction': 0.2,
         'hardStop': -45, 'lowCapHardStop': -55, 'lowCapMc': 300_000,
         'takeProfit1': 50, 'takeProfit1Sell': 0.3, 'takeProfit2': 120, 'takeProfit2Sell': 0.4, 'runnerTrail': 35,
         'liqPullPct': 30, 'dumpSellRatio': 2.0, 'thesisVolKeep': 0.3, 'deadMoneyHours': 24, 'maxHoldHours': 72,
         'maxExposure': 0.4,
         # fresh-launch lane at half size
         'freshMinMinutes': 10, 'freshMinLiquidity': 15_000, 'freshSize': 0.5}
_intel_cache = {}


async def _safety(http, p):
    """Rug/insider gate from FEELESS on-chain intel. Returns (ok, why, conviction 0.5–1.5)."""
    mint = (p.get('baseToken') or {}).get('address')
    if not mint:
        return False, 'no mint', 0
    hit = _intel_cache.get(mint)
    if hit and time.time() - hit[0] < 1800:
        d = hit[1]
    else:
        try:
            d = (await http.get(f'http://127.0.0.1:5077/api/reputation/intel/solana/{mint}', timeout=25)).json()
        except Exception:
            d = None
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
              (not d.get('flaggedFunders'), f"{len(d.get('flaggedFunders') or {})} sniper(s) funded by a known repeat rug/snipe funder")]
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
    return True, f"top10 {_num(d.get('top10Pct')):.0f}%, insiders {_num(d.get('insidersHoldingPct')):.0f}%, {snip} snipers, {bund} bundled, creator {rep.get('badge') or 'unknown'}", max(0.5, min(1.75, round(conviction, 2)))


def _num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


async def _market_candidates(http):
    pairs = {}
    for kind in ('trending', 'new'):
        for page in (1, 2):
            try:
                r = await http.get(MARKET_FEED.format(kind=kind, page=page))
                for p in (r.json() or {}).get('pairs') or []:
                    pairs[p.get('pairAddress')] = p
            except Exception:
                pass
        # Include the launchpad-native Pump index on page one; safety and liquidity gates still
        # decide whether Fee may enter. This prevents the engine from watching only older DEX lists.
        try:
            r = await http.get(MARKET_FEED.format(kind=kind, page=1) + '&scope=pump')
            for p in (r.json() or {}).get('pairs') or []:
                pairs[p.get('pairAddress')] = p
        except Exception:
            pass
    return list(pairs.values())


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
              (R['minMarketCap'] <= mc <= R['maxMarketCap'], 'market cap band'), (age_h >= R['minAgeHours'], 'too new'),
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
            f"• Activity: {_fmt_usd(vol)} traded in 24h; pool is {age_h:.1f}h old (I skip anything under {R['minAgeHours']}h).\n"
            f"• Holders (FEELESS on-chain intel): {safety or 'checked'} — I skip anything with top-10 over {R['maxTop10Pct']}%, insiders over {R['maxInsiderPct']}%, dev over {R['maxDevPct']}% or heavy sniping/bundling.\n"
            f"• Size: {conviction}× conviction — cleaner holder distribution earns a bigger position.\n\n"
            f"Plan (trench + stock mindset): this is a {int(R['starterFraction'] * 100)}% starter. If it dips {R['add1At']}% and {R['add2At']}% from here while liquidity, volume and buyers still hold, "
            f"I add and re-average my entry instead of panic-selling. I take {int(R['takeProfit1Sell'] * 100)}% profit at +{R['takeProfit1']}% and more at +{R['takeProfit2']}%, "
            f"then let the rest run with a {R['runnerTrail']}% trailing stop that never drops below break-even. "
            f"I only cut early if the thesis breaks (liquidity pulled {R['liqPullPct']}%+, sellers dumping {R['dumpSellRatio']:.0f}:1, or volume dies while red); hard stop {R['hardStop']}% from my average. "
            f"Every trade pays 1% each way so you see real costs.\n\nNot financial advice — this is how a disciplined bot thinks, out loud.")


LEARN_BOUNDS = {'runnerTrail': (25, 50), 'takeProfit1': (40, 100)}


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


def _post_as_fee(pair_address, text, register_call=False):
    try:
        key = (DATA_DIR / 'internal.key').read_text().strip()
        r = httpx.post('http://127.0.0.1:5077/api/reputation/internal/fee-post', json={'pairAddress': pair_address, 'text': text, 'registerCall': register_call},
                       headers={'x-feeless-internal': key}, timeout=15)
        if r.status_code != 200:
            print('fee post rejected', r.status_code, r.text[:200])
    except Exception as exc:
        print('fee post failed', exc)


def _close(store, cat, pos, price_native, why, fraction=1.0, market_cap=None):
    gross = pos['notionalSol'] * fraction * (price_native / pos['entryPriceNative'])
    proceeds = gross * (1 - FEE_PER_SIDE)
    pnl = round(proceeds - pos['costSol'] * fraction, 6)
    if fraction < 1:
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
    if fraction >= 1:
        cat.setdefault('exits', []).append({'pairAddress': pos['pairAddress'], 'symbol': pos['symbol'], 'exitPx': price_native, 'exitAt': time.time(),
                                            'why': why, 'pnlSol': pnl, 'changeAtExit': round((price_native / pos['entryPriceNative'] - 1) * 100, 2), 'peakAfter': 0.0, 'lowAfter': 0.0})
        cat['exits'] = cat['exits'][-60:]
    cat.setdefault('pnlHistory', []).append({'value': cat['realizedPnlSol'], 't': time.time()})
    cat['pnlHistory'] = cat['pnlHistory'][-60:]
    closed = cat.get('wins', 0) + cat.get('losses', 0)
    cat['winRate'] = round(cat['wins'] / closed * 100) if closed else None
    change = (price_native / pos['entryPriceNative'] - 1) * 100
    part = f'{int(fraction * 100)}% of ' if fraction < 1 else ''
    _log_event(store, cat, 'SELL', f"Sold {part}{pos['symbol']} at {change:+.1f}% — {why}. Net {pnl:+.4f} SOL after fees (paper, live price).", pnl, pos.get('pairAddress'), price_native, market_cap, pos.get('entryMarketCapUsd'))
    if cat.get('isLeader') and pos.get('pairAddress'):
        held = (time.time() - pos.get('openedAt', time.time())) / 3600
        verdict = 'Took the win.' if pnl >= 0 else 'The thesis broke, so I cut it — protecting capital beats hoping.'
        if fraction < 1:
            _post_as_fee(pos['pairAddress'], f"🐱 Fee took profit on ${pos['symbol']}: sold {int(fraction * 100)}% at {change:+.1f}% — {why}. Locked {pnl:+.4f} SOL.\nThe rest keeps riding with a trailing stop, and it can't turn into a loss: the floor is my break-even.")
            return
        _post_as_fee(pos['pairAddress'], f"🐱 Fee sold ${pos['symbol']} at {change:+.1f}% after {held:.1f}h — {why}.\nNet {pnl:+.4f} SOL after the 1% fee each way (peak was {pos.get('peakChange', 0):+.1f}%).\n{verdict} The rules decide the exit, not feelings.")


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


async def run_engine(store, cats):
    now = time.time()
    async with httpx.AsyncClient(timeout=10) as http:
        held = sorted({p['pairAddress'] for c in cats for p in c['positions'] if p.get('pairAddress')}
                      | {e['pairAddress'] for c in cats for e in c.get('exits', []) if now - e['exitAt'] < 24 * 3600})
        prices = await _pair_prices(http, held) if held else {}
        candidates = await _market_candidates(http)
    ranked, rejections = [], {}
    for p in candidates:
        score, reason = _qualifies(p, now)
        if score is None:
            fscore, freason = _fresh_qualifies(p, now)
            if fscore is not None:
                p['_fresh'] = True
                score, reason = fscore, freason
        if score is not None:
            ranked.append((score, reason, p))
        else:
            rejections[reason] = rejections.get(reason, 0) + 1
    store['scan'] = {'at': now, 'scanned': len(candidates), 'passed': len(ranked), 'rejections': rejections,
                     'top': [{'symbol': (p.get('baseToken') or {}).get('symbol'), 'reason': r, 'url': p.get('url')} for _, r, p in ranked[:5]]}
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
            elif pos['profitTaken'] and change <= 0:
                why = 'runner fell back to break-even after taking profit'
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
                # Each add has a band: a controlled dip, not a crash. No adds while the 5m candle is collapsing.
                ladder = [(R['add1At'], R['add2At'], R['add1Fraction']), (R['add2At'], hard + 5, R['add2Fraction'])]
                m5_change = _num((live.get('priceChange') or {}).get('m5'))
                step = ladder[pos['adds']] if pos['adds'] < len(ladder) else None
                if step and add_ok and step[1] < from_first <= step[0] and m5_change > -15:
                    # Buy the dip with a plan: lower price, thesis intact → add and re-average the entry.
                    add = round(min(pos['plannedSol'] * step[2], cat['balanceSol']), 4)
                    if add >= 0.01:
                        old_avg_mc = _num(pos.get('entryMarketCapUsd'))
                        tokens_old = pos['notionalSol'] / pos['entryPriceNative']; tokens_new = add * (1 - FEE_PER_SIDE) / px
                        pos['entryPriceNative'] = (pos['notionalSol'] + add * (1 - FEE_PER_SIDE)) / (tokens_old + tokens_new)
                        if old_avg_mc and mc_now:
                            pos['entryMarketCapUsd'] = round((old_avg_mc * tokens_old + mc_now * tokens_new) / (tokens_old + tokens_new), 2)
                        pos['costSol'] = round(pos['costSol'] + add, 6); pos['notionalSol'] = round(pos['notionalSol'] + add * (1 - FEE_PER_SIDE), 6)
                        pos['adds'] += 1; pos['peakChange'] = 0; pos['peakPx'] = px
                        cat['balanceSol'] = round(cat['balanceSol'] - add, 6); cat['volumeSol'] = round(cat.get('volumeSol', 0) + add, 6)
                        detail = (f"Added {add} SOL to {pos['symbol']} at {_fmt_usd(mc_now)} MC ({from_first:.0f}% from my first buy) — liquidity, volume and buyers still hold. "
                                  f"New average entry {_fmt_usd(pos.get('entryMarketCapUsd'))} MC (paper).")
                        _log_event(store, cat, 'BUY', detail, None, pos['pairAddress'], px, mc_now, pos.get('entryMarketCapUsd'))
                        if cat.get('isLeader'):
                            _post_as_fee(pos['pairAddress'], f"🐱 {detail}\nSame thesis, better price. Holding.")
            if why:
                cat['positions'].remove(pos)
                _close(store, cat, pos, px, why, market_cap=mc_now)
        day = time.strftime('%Y-%m-%d')
        if cat.get('dailyLoss', {}).get(day, 0) >= float(cat['risk'].get('maxDailyLossSol') or 0.5):
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
            reason = f'{reason}; holders: {safe_why}; conviction {conviction}×'
            px = _num(p.get('priceNative'))
            planned = round(min(float(cat['risk']['maxPositionSol']), cat['balanceSol'] * 0.1 * conviction) * (R['freshSize'] if p.get('_fresh') else 1), 4)
            size = round(planned * R['starterFraction'], 4)
            invested = sum(x['costSol'] for x in cat['positions'])
            if invested + planned > R['maxExposure'] * (cat['balanceSol'] + invested):
                break  # capital first: never more than maxExposure of equity at work
            if px <= 0 or size < 0.01 or cat['balanceSol'] < size:
                continue
            cat['balanceSol'] = round(cat['balanceSol'] - size, 6)
            cat['volumeSol'] = round(cat.get('volumeSol', 0) + size, 6)
            cat['positions'].append({
                'mint': (p.get('baseToken') or {}).get('address'), 'pairAddress': pa, 'symbol': sym, 'provider': 'DexScreener',
                'url': p.get('url'), 'costSol': size, 'notionalSol': round(size * (1 - FEE_PER_SIDE), 6),
                'entryPriceNative': px, 'entryPriceUsd': p.get('priceUsd'), 'entryChange': 0, 'currentChange': 0,
                'peakChange': 0, 'openedAt': now, 'reason': reason,
                'entryLiq': _num((p.get('liquidity') or {}).get('usd')), 'conviction': conviction,
                'entryMarketCapUsd': _num(p.get('marketCap') or p.get('fdv')),
                'entryVolH1': _num((p.get('volume') or {}).get('h1')), 'plannedSol': planned,
                'firstEntryPriceNative': px, 'adds': 0, 'profitTaken': 0, 'peakPx': px,
            })
            _log_event(store, cat, 'BUY', f"Bought {size} SOL of {sym} at live price — {reason} (paper).", None, pa, px, _num(p.get('marketCap') or p.get('fdv')))
            if cat.get('isLeader'):
                _post_as_fee(pa, _buy_analysis(p, size, sym, safe_why, conviction), register_call=True)
        cat['lastTick'] = now


def _migrate(store):
    if store.get('rulesVersion') != 'trench-lord-v2':
        # Trench Lord v2 changed what the hold/exit settings mean; drop old-engine overrides for them.
        ov = store.get('rulesOverride') or {}
        store['rulesOverride'] = {k: v for k, v in ov.items() if k in TUNABLE and k != 'maxHoldHours'}
        store['rulesVersion'] = 'trench-lord-v2'
    for cat in store['cats'].values():
        if cat.get('engine') != ENGINE_VERSION:
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


async def _engine_loop():
    while True:
        try:
            store = _load()
            _migrate(store)
            _apply_overrides(store)
            running = [c for c in store['cats'].values() if c['status'] == 'running' and not c['revoked']]
            if running:
                await run_engine(store, running)
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
    }


app = FastAPI(title='FEELESS Cats')
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in (os.environ.get('ALLOWED_ORIGINS') or '*').split(',') if o.strip()], allow_methods=['*'], allow_headers=['*'])


@app.on_event('startup')
async def _start_engine():
    asyncio.create_task(_engine_loop())
    asyncio.create_task(_tune_loop())


@app.get('/api/cats/brains')
async def brains():
    return {'brains': [{**b, 'status': 'rule_fallback', 'available': False, 'estimatedTokenCostUsd': 0} for b in BRAIN_CATALOG]}


class CreatePayload(BaseModel):
    ownerId: str
    name: str
    handle: str
    avatar: Any = 0
    brain: str = 'gpt-astra'
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


@app.post('/api/cats')
async def create_cat(payload: CreatePayload):
    store = _load()
    cat_id = uuid.uuid4().hex
    brain_info = next((b for b in BRAIN_CATALOG if b['id'] == payload.brain), BRAIN_CATALOG[0])
    now = time.time()
    cat = {
        'id': cat_id, 'ownerId': payload.ownerId, 'name': payload.name, 'handle': payload.handle,
        'avatar': payload.avatar, 'brain': payload.brain, 'brainLabel': brain_info['label'],
        'brainProfile': {'provider': brain_info['provider'], 'status': 'rule_fallback', 'available': False, 'estimatedTokenCostUsd': 0},
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
        'startingBalanceSol': float(payload.startingBalanceSol or 10),
    }
    store['cats'][cat_id] = cat
    _save(store)
    recovery_key = '-'.join(uuid.uuid4().hex[:4] for _ in range(4))
    return {'cat': cat, 'recoveryKey': recovery_key}


@app.get('/api/cats')
async def list_cats(ownerId: str):
    store = _load()
    cats = [c for c in store['cats'].values() if c['ownerId'] == ownerId]
    cats.sort(key=lambda c: -c['createdAt'])
    return {'cats': cats}


@app.get('/api/cats/leader')
async def leader():
    store = _load()
    _migrate(store)
    return {'cat': store['cats'].get(LEADER_ID), 'rules': RULES, 'feePerSide': FEE_PER_SIDE, 'scan': store.get('scan')}


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
    return {'trades': [e for e in store['events'] if e.get('pairAddress') == pairAddress and e['catId'] == catId and e['type'] in ('BUY', 'SELL')]}


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
    return {'rows': rows[:50]}


@app.get('/api/cats/activity')
async def activity(catId: Optional[str] = None):
    store = _load()
    events = store['events']
    if catId:
        events = [e for e in events if e['catId'] == catId]
    return {'events': events[:60]}


@app.get('/api/cats/health')
async def health():
    store = _load()
    return {'ok': True, 'cats': len(store['cats']), 'events': len(store['events'])}


TUNABLE = {'minLiquidity': (10_000, 500_000), 'minVolume24h': (20_000, 5_000_000), 'minMarketCap': (20_000, 5_000_000), 'maxMarketCap': (500_000, 500_000_000),
           'minAgeHours': (0.5, 72), 'maxPositions': (1, 8), 'maxTop10Pct': (15, 50), 'maxSnipers': (0, 40), 'maxBundled': (0, 20), 'maxM5Chase': (3, 20),
           'add1At': (-35, -8), 'add2At': (-50, -15), 'hardStop': (-60, -25), 'takeProfit1': (20, 150), 'takeProfit2': (50, 400),
           'runnerTrail': (15, 50), 'maxHoldHours': (6, 96), 'maxExposure': (0.1, 0.8)}


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
            'leader': {k: store['cats'][LEADER_ID].get(k) for k in ('status', 'risk')}}


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
    if body.get('strategyPreset') in ('feecat', 'trench', 'meme', 'scalper'):
        store['strategyPreset'] = body['strategyPreset']
    _apply_overrides(store)
    _save(store)
    return {'ok': True, 'rules': {k: RULES[k] for k in TUNABLE}, 'status': leader['status']}


def _internal(request):
    import hmac
    key = (DATA_DIR / 'internal.key').read_text().strip()
    if not hmac.compare_digest(request.headers.get('x-feeless-internal', ''), key):
        raise HTTPException(403, 'Internal only.')


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
    return {
        'cat': {k: cat.get(k) for k in ('id', 'name', 'title', 'avatar', 'strategyLabel', 'level', 'xp', 'balanceSol', 'startingBalanceSol', 'realizedPnlSol',
                                        'volumeSol', 'wins', 'losses', 'winRate', 'positions', 'pnlHistory', 'status', 'lastTick')},
        'stats': {'trades': closed, 'best': max(pnls) if pnls else None, 'worst': min(pnls) if pnls else None,
                  'roiPct': round((cat.get('balanceSol', 0) + sum(p.get('costSol', 0) for p in cat.get('positions', [])) - cat.get('startingBalanceSol', 0)) / max(cat.get('startingBalanceSol', 1), 1e-9) * 100, 2)},
        'trades': trades[:80],
        'exits': list(reversed(cat.get('exits', [])))[:30],
        'learning': {'params': {**{k: RULES[k] for k in LEARN_BOUNDS}, **{k: v for k, v in (learn.get('params') or {}).items() if k in LEARN_BOUNDS}}, 'defaults': {k: RULES[k] for k in LEARN_BOUNDS},
                     'entry': {**{k: RULES[k] for k in ENTRY_BOUNDS}, **(learn.get('entry') or {})}, 'mode': learn.get('mode', 'warming'), 'tunedAt': learn.get('tunedAt'), 'study': learn.get('study'),
                     'missed': learn.get('missed', 0), 'good': learn.get('good', 0), 'log': learn.get('log', [])},
        'rules': {k: RULES[k] for k in ('hardStop', 'add1At', 'add2At', 'takeProfit1', 'takeProfit2', 'runnerTrail', 'maxHoldHours', 'maxTop10Pct', 'maxInsiderPct', 'maxSnipers', 'maxBundled', 'maxM5Chase')},
    }


@app.get('/api/cats/{cat_id}')
async def get_cat(cat_id: str):
    store = _load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise HTTPException(404, 'Cat not found.')
    return {'cat': cat}


class ActionPayload(BaseModel):
    action: str
    amount: Any = None
    recoveryKey: Optional[str] = None
    maxPositionSol: Any = None
    maxDailyLossSol: Any = None
    allowlist: Optional[str] = None
    blocklist: Optional[str] = None


@app.post('/api/cats/{cat_id}/action')
async def cat_action(cat_id: str, payload: ActionPayload):
    store = _load()
    cat = store['cats'].get(cat_id)
    if not cat:
        raise HTTPException(404, 'Cat not found.')

    if payload.action == 'confirm_recovery':
        pass
    elif payload.action == 'start':
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
    elif payload.action == 'withdraw':
        amount = min(float(payload.amount or 0), cat['balanceSol'])
        cat['balanceSol'] = round(cat['balanceSol'] - amount, 6)
        _log_event(store, cat, 'WITHDRAW', f'Paper withdrawal of {amount:.4f} SOL recorded.')
    elif payload.action == 'revoke':
        cat['revoked'] = True
        cat['status'] = 'stopped'
        _log_event(store, cat, 'STOPPED', f'{cat["name"]} was revoked.')
    else:
        raise HTTPException(400, f'Unknown action: {payload.action}')

    _save(store)
    return {'cat': cat}
