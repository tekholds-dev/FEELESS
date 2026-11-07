"""📐 WHAT A RANGE REALLY DOES (owner 2026-11-07: "the best auto range strategy, if it is really effective"). Replays a concentrated pool position over real hourly prices and fees. Pure. It reads and measures: it never trades, and past numbers promise nothing.

The position follows the standard concentrated liquidity sums: inside its band it holds both sides and earns more fees the tighter the band, outside it holds one side and earns nothing. Going out of range and waiting costs nothing but lost fees; recentering pays a swap each time."""
import math

WIDTHS = (2, 5, 10, 20, 40)
SWAP_COST = 0.003   # about half the position is swapped at 0.3% or so, plus a little slippage
TYPICAL_WIDTH = 25
WAITS = (1, 6, 24)  # hours out of range before it recenters


def _value(px, lo, hi, liq):
    """What the position is worth at this price, in the second coin."""
    s, a, b = math.sqrt(px), math.sqrt(lo), math.sqrt(hi)
    if s <= a:
        return liq * (1 / a - 1 / b) * px
    if s >= b:
        return liq * (b - a)
    return liq * (1 / s - 1 / b) * px + liq * (s - a)


def _band(px, width):
    k = 1 + width / 100
    return px / k, px * k


def concentration(width):
    """How many times the fees of a full range position the same dollars earn in this band."""
    r = math.sqrt(1 + width / 100)
    return 1 / (1 - 1 / r)


def fee_boost(width):
    """A venue's fee rate is already per dollar of liquidity that is itself concentrated, so a band only earns more than an ordinary LP there, not more than a full range. Taken as a ±25% ordinary LP: an assumption, and the largest in this model."""
    return concentration(width) / concentration(TYPICAL_WIDTH)


def replay(points, width, wait=6, cost=SWAP_COST):
    """points = [{t, a, b, fee}]: price of its coin, of the other, and fees that hour per dollar in the pool. → {pct, feesPct, inRange, moves}, in the other coin's terms"""
    rows = [p for p in points or [] if p.get('a') and p.get('b')]
    if len(rows) < 3:
        return None
    px = rows[0]['a'] / rows[0]['b']; lo, hi = _band(px, width); liq = 1.0 / _value(px, lo, hi, 1.0); fees = 0.0; moves = 0; inside = 0; out = 0; boost = fee_boost(width)
    for p in rows[1:]:
        px = p['a'] / p['b']; worth = _value(px, lo, hi, liq) + fees
        if lo <= px <= hi:
            inside += 1; out = 0; fees += _value(px, lo, hi, liq) * max(0.0, p.get('fee') or 0.0) * boost
            continue
        out += 1
        if out >= wait:
            worth *= (1 - cost); moves += 1; fees = 0.0; lo, hi = _band(px, width); liq = worth / _value(px, lo, hi, 1.0); out = 0
    px = rows[-1]['a'] / rows[-1]['b']; end = _value(px, lo, hi, liq) + fees; start_px = rows[0]['a'] / rows[0]['b']
    # in dollars: the position is valued in the other coin, so bring both ends to dollars
    pct = (end * rows[-1]['b'] / rows[0]['b'] - 1) * 100; hold = ((1 + px / start_px) / 2 * rows[-1]['b'] / rows[0]['b'] - 1) * 100; full = (math.sqrt(px / start_px) * rows[-1]['b'] / rows[0]['b'] - 1) * 100 + sum(max(0.0, p.get('fee') or 0.0) for p in rows[1:]) * 100
    return {'width': width, 'wait': wait, 'pct': round(pct, 3), 'holdPct': round(hold, 3), 'fullPct': round(full, 3), 'inRange': round(100 * inside / (len(rows) - 1), 1), 'moves': moves, 'hours': len(rows)}


def sweep(points, widths=WIDTHS, waits=WAITS, cost=SWAP_COST):
    """Every band on the same history, best first."""
    rows = [x for x in (replay(points, w, h, cost) for w in widths for h in waits) if x]
    return sorted(rows, key=lambda r: -r['pct'])


def walk_forward(points, cost=SWAP_COST):
    """The only honest test: choose the band on the older half, then see what it does on the newer half it never saw, against just holding and a plain full range position."""
    n = len(points or []); cut = n // 2
    if n < 60:
        return None
    best = sweep(points[:cut], cost=cost)
    if not best:
        return None
    pick = best[0]; test = replay(points[cut:], pick['width'], pick['wait'], cost)
    return {'width': pick['width'], 'wait': pick['wait'], 'trainPct': pick['pct'], **{k: test[k] for k in ('pct', 'holdPct', 'fullPct', 'inRange', 'moves', 'hours')}} if test else None
