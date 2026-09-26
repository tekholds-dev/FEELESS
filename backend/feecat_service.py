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
import math
import time
import uuid
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException
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


def _log_event(store, cat, kind, detail, pnl=None, pair=None, price=None):
    store['events'].insert(0, {
        'id': uuid.uuid4().hex, 'catId': cat['id'], 'catName': cat['name'],
        'type': kind, 'detail': detail, 'ts': time.time() * 1000,
        'pnlSol': pnl, 'decisionSource': 'selected_brain' if cat.get('brainProfile', {}).get('available') else 'rule_engine',
        'brainLabel': cat.get('brainLabel'), 'pairAddress': pair, 'priceNative': price,
    })
    store['events'] = store['events'][:200]


FEE_PER_SIDE = 0.01
ENGINE_VERSION = 'live-v2'  # v3 logic below is additive; keeps the existing track record
LEADER_ID = 'leader'
MARKET_FEED = 'http://127.0.0.1:5001/api/market/feed?kind={kind}&chain=solana&page={page}'
RULES = {'minLiquidity': 40_000, 'minVolume24h': 100_000, 'minMarketCap': 150_000, 'maxMarketCap': 50_000_000,
         'minAgeHours': 3, 'h1Min': 3, 'h1Max': 40, 'h6Max': 120, 'h24Max': 400, 'minBuySellRatio': 1.2,
         'stopLoss': -10, 'takeProfit': 22, 'trailArm': 12, 'trailGive': 8, 'maxHoldHours': 4, 'maxPositions': 4,
         'cooldownHours': 2,
         # v3 safety + exits
         'maxM5Chase': 8, 'maxTop10Pct': 35, 'maxInsiderPct': 20, 'maxDevPct': 10, 'maxSnipers': 15, 'maxBundled': 10,
         'breakEvenArm': 8, 'scaleOutFraction': 0.5, 'runnerTrailGive': 6, 'liqPullPct': 30, 'dumpSellRatio': 2.0}
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
    R = RULES
    snip, bund = len(d.get('sniperWallets') or []), len(d.get('bundledWallets') or [])
    checks = [(_num(d.get('top10Pct')) <= R['maxTop10Pct'], f"top 10 wallets hold {_num(d.get('top10Pct')):.0f}%"),
              (_num(d.get('insidersHoldingPct')) <= R['maxInsiderPct'], f"insiders hold {_num(d.get('insidersHoldingPct')):.0f}%"),
              (_num(d.get('devHoldingPct')) <= R['maxDevPct'], f"dev holds {_num(d.get('devHoldingPct')):.0f}%"),
              (snip <= R['maxSnipers'], f'{snip} snipers'), (bund <= R['maxBundled'], f'{bund} bundled wallets')]
    for ok, why in checks:
        if not ok:
            return False, why, 0
    # Cleaner distribution → more conviction.
    conviction = 1.5 - min(1.0, _num(d.get('top10Pct')) / R['maxTop10Pct']) * 0.6 - (0.2 if snip > 5 else 0) - (0.2 if bund else 0)
    return True, f"top10 {_num(d.get('top10Pct')):.0f}%, insiders {_num(d.get('insidersHoldingPct')):.0f}%, {snip} snipers, {bund} bundled", max(0.5, round(conviction, 2))


def _num(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


async def _market_candidates(http):
    pairs = {}
    for kind in ('trending', 'volume', 'gainers'):
        for page in (1, 2):
            try:
                r = await http.get(MARKET_FEED.format(kind=kind, page=page))
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
    R = RULES
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
    R = RULES
    return (f"🐱 Fee is buying ${sym} — {size} SOL (paper trade, live price).\n\n"
            f"Why this one passed every rule:\n"
            f"• Order flow: {b:.0f} buys vs {s:.0f} sells in the last hour ({(b / max(b + s, 1)) * 100:.0f}% buys) — buyers are in control.\n"
            f"• Momentum: 5m {_num(ch.get('m5')):+.1f}%, 1h {_num(ch.get('h1')):+.1f}%, 6h {_num(ch.get('h6')):+.1f}% — trending up without being vertical (my cap is +{R['h1Max']}% 1h / +{R['h6Max']}% 6h).\n"
            f"• Liquidity: {_fmt_usd(liq)} ({(liq / mc * 100) if mc else 0:.1f}% of {_fmt_usd(mc)} market cap) — deep enough to get out.\n"
            f"• Activity: {_fmt_usd(vol)} traded in 24h; pool is {age_h:.1f}h old (I skip anything under {R['minAgeHours']}h).\n"
            f"• Holders (FEELESS on-chain intel): {safety or 'checked'} — I skip anything with top-10 over {R['maxTop10Pct']}%, insiders over {R['maxInsiderPct']}%, dev over {R['maxDevPct']}% or heavy sniping/bundling.\n"
            f"• Size: {conviction}× conviction — cleaner holder distribution earns a bigger position.\n\n"
            f"Risk plan: stop at {R['stopLoss']}%, moved to break-even once it's up +{R['breakEvenArm']}%. At +{R['takeProfit']}% I sell half and let the rest run with a {R['runnerTrailGive']}% trailing stop. "
            f"I also bail instantly if liquidity drops {R['liqPullPct']}% or sellers outnumber buyers {R['dumpSellRatio']:.0f}:1 while I'm red, and I'm out after {R['maxHoldHours']}h no matter what. "
            f"Every trade pays 1% each way so you see real costs.\n\nNot financial advice — this is how a disciplined bot thinks, out loud.")


LEARN_BOUNDS = {'trailGive': (8, 16), 'runnerTrailGive': (6, 14), 'takeProfit': (22, 45), 'scaleOutFraction': (0.33, 0.5)}


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
        # Only a price-based exit (not a stop-loss) can be "too early".
        early = e['peakAfter'] >= 40 and ('trailing' in e['why'] or 'take-profit' in e['why'] or 'sell pressure' in e['why'] or 'time exit' in e['why'])
        if early:
            L['missed'] += 1
            P['trailGive'] = min(LEARN_BOUNDS['trailGive'][1], P['trailGive'] + 2)
            P['runnerTrailGive'] = min(LEARN_BOUNDS['runnerTrailGive'][1], P['runnerTrailGive'] + 2)
            P['takeProfit'] = min(LEARN_BOUNDS['takeProfit'][1], P['takeProfit'] + 5)
            P['scaleOutFraction'] = max(LEARN_BOUNDS['scaleOutFraction'][0], round(P['scaleOutFraction'] - 0.05, 2))
            note = f"Sold {e['symbol']} at {e['changeAtExit']:+.1f}%, it ran another +{e['peakAfter']:.0f}%. Loosening: trail {P['trailGive']}%, runner {P['runnerTrailGive']}%, TP +{P['takeProfit']}%, scale-out {int(P['scaleOutFraction']*100)}%."
        else:
            L['good'] += 1
            for k, (lo, hi) in LEARN_BOUNDS.items():
                base = RULES[k]
                P[k] = round(P[k] + (base - P[k]) * 0.25, 2)  # drift back toward the disciplined defaults
            note = f"Exit on {e['symbol']} held up (best after sell +{e['peakAfter']:.0f}%, low {e['lowAfter']:.0f}%). Keeping discipline."
        L['params'] = {k: P[k] for k in LEARN_BOUNDS}
        L['log'].insert(0, {'at': time.time(), 'note': note, 'symbol': e['symbol'], 'missed': early})
        L['log'] = L['log'][:40]
        _log_event(store, cat, 'LEARN', note)


def _post_as_fee(pair_address, text, register_call=False):
    try:
        key = (DATA_DIR / 'internal.key').read_text().strip()
        httpx.post('http://127.0.0.1:5077/api/reputation/internal/fee-post', json={'pairAddress': pair_address, 'text': text, 'registerCall': register_call},
                   headers={'x-feeless-internal': key}, timeout=15)
    except Exception as exc:
        print('fee post failed', exc)


def _close(store, cat, pos, price_native, why, fraction=1.0):
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
    _log_event(store, cat, 'SELL', f"Sold {part}{pos['symbol']} at {change:+.1f}% — {why}. Net {pnl:+.4f} SOL after fees (paper, live price).", pnl, pos.get('pairAddress'), price_native)
    if cat.get('isLeader') and pos.get('pairAddress'):
        held = (time.time() - pos.get('openedAt', time.time())) / 3600
        verdict = 'Took the win.' if pnl >= 0 else 'Cut it — protecting capital beats hoping.'
        if fraction < 1:
            _post_as_fee(pos['pairAddress'], f"🐱 Fee took {int(fraction * 100)}% off ${pos['symbol']} at {change:+.1f}% — {why}. Locked {pnl:+.4f} SOL.\nThe rest rides as a runner with a tighter trailing stop and a break-even floor. House money now.")
            return
        _post_as_fee(pos['pairAddress'], f"🐱 Fee sold ${pos['symbol']} at {change:+.1f}% after {held:.1f}h — {why}.\nNet {pnl:+.4f} SOL after the 1% fee each way (peak was {pos.get('peakChange', 0):+.1f}%).\n{verdict} The rules decide the exit, not feelings.")


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
            change = (px / pos['entryPriceNative'] - 1) * 100
            pos['currentChange'] = round(change, 2)
            pos['peakChange'] = max(pos.get('peakChange', 0), change)
            pos['lastPriceUsd'] = live.get('priceUsd')
            held_h = (now - pos['openedAt']) / 3600
            why = None
            liq_now = _num((live.get('liquidity') or {}).get('usd'))
            t5 = (live.get('txns') or {}).get('m5') or {}
            b5, s5 = _num(t5.get('buys')), _num(t5.get('sells'))
            floor = -1 if pos['peakChange'] >= R['breakEvenArm'] else R['stopLoss']
            give = R['runnerTrailGive'] if pos.get('scaled') else R['trailGive']
            if pos.get('entryLiq') and liq_now and liq_now < pos['entryLiq'] * (1 - R['liqPullPct'] / 100):
                why = f"liquidity pulled ({_fmt_usd(pos['entryLiq'])} → {_fmt_usd(liq_now)})"
            elif change <= floor:
                why = 'break-even stop' if floor > R['stopLoss'] else f'stop-loss {R["stopLoss"]}%'
            elif change >= R['takeProfit'] and not pos.get('scaled'):
                pos['scaled'] = True
                _close(store, cat, pos, px, f'take-profit +{R["takeProfit"]}% (scaling out)', R['scaleOutFraction'])
                continue
            elif pos['peakChange'] >= R['trailArm'] and change <= pos['peakChange'] - give:
                why = f'trailing stop (peak +{pos["peakChange"]:.1f}%)'
            elif change < 0 and s5 >= 10 and s5 >= b5 * R['dumpSellRatio']:
                why = f'sell pressure ({s5:.0f} sells vs {b5:.0f} buys in 5m)'
            elif held_h >= R['maxHoldHours'] * (1.5 if pos.get('scaled') else 1):
                why = f'time exit after {held_h:.1f}h'
            if why:
                cat['positions'].remove(pos)
                _close(store, cat, pos, px, why)
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
            reason = f'{reason}; holders: {safe_why}; conviction {conviction}×'
            px = _num(p.get('priceNative'))
            size = round(min(float(cat['risk']['maxPositionSol']), cat['balanceSol'] * 0.1 * conviction), 4)
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
            })
            _log_event(store, cat, 'BUY', f"Bought {size} SOL of {sym} at live price — {reason} (paper).", None, pa, px)
            if cat.get('isLeader'):
                _post_as_fee(pa, _buy_analysis(p, size, sym, safe_why, conviction), register_call=True)
        cat['lastTick'] = now


def _migrate(store):
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
            'strategy': 'trend', 'strategyLabel': 'Disciplined momentum', 'status': 'running', 'level': 1, 'xp': 0,
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


async def _engine_loop():
    while True:
        try:
            store = _load()
            _migrate(store)
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
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])


@app.on_event('startup')
async def _start_engine():
    asyncio.create_task(_engine_loop())


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
                                        'volumeSol', 'wins', 'losses', 'winRate', 'positions', 'pnlHistory', 'status')},
        'stats': {'trades': closed, 'best': max(pnls) if pnls else None, 'worst': min(pnls) if pnls else None,
                  'roiPct': round((cat.get('balanceSol', 0) + sum(p.get('costSol', 0) for p in cat.get('positions', [])) - cat.get('startingBalanceSol', 0)) / max(cat.get('startingBalanceSol', 1), 1e-9) * 100, 2)},
        'trades': trades[:80],
        'exits': list(reversed(cat.get('exits', [])))[:30],
        'learning': {'params': {**{k: RULES[k] for k in LEARN_BOUNDS}, **(learn.get('params') or {})}, 'defaults': {k: RULES[k] for k in LEARN_BOUNDS},
                     'missed': learn.get('missed', 0), 'good': learn.get('good', 0), 'log': learn.get('log', [])},
        'rules': {k: RULES[k] for k in ('stopLoss', 'breakEvenArm', 'maxHoldHours', 'maxTop10Pct', 'maxInsiderPct', 'maxSnipers', 'maxBundled', 'maxM5Chase')},
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
