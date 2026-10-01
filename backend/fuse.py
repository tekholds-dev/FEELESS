"""FUSE: fused pools. A Fuse is a named basket of live DEX pools with weights (e.g. SOL/USDC 40% · $FEE/SOL 40% ·
a hot meme 20%). Pure functions, no I/O — every number on a Fuse card comes from here, so it is tested once.

- index(): 100 at launch, then the weighted price move of the legs since launch (what the basket would be worth).
- score(): A–F grade from depth, turnover, volatility and on-chain safety, each component shown with its reason.
- split(): how a SOL amount is divided across legs for "Fuse in" (one normal wallet-signed swap per leg).
- creator_cut(): the creator's share of the FEELESS fee on a Fuse buy (tracked for payout, like FeeBack).
"""
import math

DEX_FEE_EST = 0.0025          # typical pool fee tier used for the APR estimate (shown as an estimate)
MAX_LEGS = 6
MAX_CREATOR_BPS = 5000        # a creator can take at most half of the FEELESS fee on their Fuse's buys


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def clean_legs(legs):
    """Validated legs: known chain + pair, positive weights normalised to 100, max MAX_LEGS, no duplicates."""
    seen, out = set(), []
    for leg in legs or []:
        pa, ch = str(leg.get('pairAddress') or '').strip(), str(leg.get('chainId') or '').strip()
        w = _f(leg.get('weight'))
        if not pa or not ch or w <= 0 or (ch, pa) in seen:
            continue
        seen.add((ch, pa))
        out.append({'chainId': ch, 'pairAddress': pa, 'weight': w, 'symbol': str(leg.get('symbol') or '')[:16]})
    out = out[:MAX_LEGS]
    total = sum(x['weight'] for x in out)
    for x in out:
        x['weight'] = round(x['weight'] / total * 100, 2) if total else 0
    return out


def leg_meta(pair):
    """What a Fuse card shows per leg, from a DexScreener pair."""
    liq = _f((pair.get('liquidity') or {}).get('usd')); vol = _f((pair.get('volume') or {}).get('h24'))
    tx = (pair.get('txns') or {}).get('h24') or {}
    buys, sells = _f(tx.get('buys')), _f(tx.get('sells'))
    return {'symbol': (pair.get('baseToken') or {}).get('symbol'), 'quote': (pair.get('quoteToken') or {}).get('symbol'),
            'priceUsd': _f(pair.get('priceUsd')), 'liquidityUsd': liq, 'volume24h': vol, 'change24h': _f((pair.get('priceChange') or {}).get('h24')),
            'aprEst': round(vol * DEX_FEE_EST / liq * 365 * 100, 1) if liq > 0 else 0.0, 'turnover': round(vol / liq, 2) if liq > 0 else 0.0,
            'buyShare': round(buys / (buys + sells) * 100) if buys + sells else None, 'dex': pair.get('dexId'), 'url': pair.get('url')}


def index(legs, base_prices, prices_now):
    """100 at launch; weighted price ratio of every leg since then. Missing prices count as unchanged."""
    total = sum(leg['weight'] for leg in legs)
    if not total:
        return 100.0
    v = 0.0
    for leg in legs:
        k = leg['pairAddress']; b, n = _f(base_prices.get(k)), _f(prices_now.get(k))
        v += leg['weight'] * ((n / b) if b > 0 and n > 0 else 1.0)
    return round(v / total * 100, 2)


def score(metas, risky=0):
    """A–F: depth (combined liquidity), turnover (volume/liquidity, healthy 0.3–5×), volatility (weighted |24h move|),
    safety (legs flagged risky by forensics). Returns grade, 0–100 points and the reason for each part."""
    if not metas:
        return {'grade': 'F', 'points': 0, 'parts': []}
    liq = sum(m['liquidityUsd'] for m in metas)
    depth = min(30, math.log10(liq + 1) * 5)                                     # $1M ≈ 30
    turns = [m['turnover'] for m in metas]
    healthy = sum(1 for x in turns if 0.3 <= x <= 5) / len(turns)
    turnover = 25 * healthy
    vol = sum(abs(m['change24h']) for m in metas) / len(metas)
    calm = max(0.0, 25 - vol / 4)                                                # 100% daily swings → 0
    safety = max(0.0, 20 - 10 * risky)
    pts = round(depth + turnover + calm + safety)
    grade = 'A' if pts >= 80 else 'B' if pts >= 65 else 'C' if pts >= 50 else 'D' if pts >= 35 else 'F'
    return {'grade': grade, 'points': pts, 'parts': [
        {'part': 'depth', 'points': round(depth), 'why': f'${liq:,.0f} combined liquidity'},
        {'part': 'turnover', 'points': round(turnover), 'why': f'{round(healthy * 100)}% of legs trade 0.3–5× their liquidity a day'},
        {'part': 'volatility', 'points': round(calm), 'why': f'average 24h move {vol:.1f}%'},
        {'part': 'safety', 'points': round(safety), 'why': f'{risky} leg(s) flagged by launch forensics' if risky else 'no leg flagged by launch forensics'}]}


def split(amount_sol, legs):
    """SOL per leg for "Fuse in" (rounded to 6 dp, remainder on the biggest leg so it always sums exactly)."""
    amt = _f(amount_sol)
    if amt <= 0 or not legs:
        return []
    parts = [{'pairAddress': leg['pairAddress'], 'chainId': leg['chainId'], 'symbol': leg.get('symbol'), 'sol': round(amt * leg['weight'] / 100, 6)} for leg in legs]
    diff = round(amt - sum(p['sol'] for p in parts), 6)
    if parts and diff:
        big = max(parts, key=lambda p: p['sol']); big['sol'] = round(big['sol'] + diff, 6)
    return parts


def creator_cut(fee_usd, creator_bps):
    """Creator's share of the FEELESS fee on a Fuse buy (capped at MAX_CREATOR_BPS)."""
    bps = max(0, min(MAX_CREATOR_BPS, int(_f(creator_bps))))
    return round(_f(fee_usd) * bps / 10000, 6)


def real_pools(pairs):
    """Pool picker order: real pools only (24h volume > 0 and liquidity < 2,000× volume — parked/fake pools show huge
    'liquidity' with no trading), busiest first."""
    vol = lambda p: _f((p.get('volume') or {}).get('h24')); liq = lambda p: _f((p.get('liquidity') or {}).get('usd'))
    return sorted((p for p in pairs or [] if vol(p) > 0 and 0 < liq(p) < vol(p) * 2000), key=lambda p: -vol(p))
