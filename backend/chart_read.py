"""📈 CHART READ — what a coin's own recent chart says, from recorded prices only (pure, tested, no network).

The pick record (pick_edge.py) judged coins on snapshot NUMBERS (age, pool, buyers, % moves). Traders read the CHART: structure,
imbalances (fair value gaps), liquidity sweeps, squeezes, where price sits in its range. This module turns the last hours of a
coin's 5-minute price readings into those reads so the record can test them the same way — a read is USED only if it separates
winners from losers on picks it has not seen. Candles are built from price readings (no wicks inside a reading), so a "gap" here is
the 3-candle imbalance on those candles: honest about what the data is.
"""
import statistics

BAR_SEC = 900          # 15-minute candles built from the 5-minute readings
LOOK_SEC = 4 * 3600    # how far back a read looks
MIN_BARS = 5           # fewer candles than this = no read (fail closed: unknown, never guessed)


def candles(points, t, bar=BAR_SEC, look=LOOK_SEC):
    """[(o, h, l, c)] oldest → newest for the `look` seconds before t; only buckets with a reading (no invented bars)."""
    b = {}
    for ts, px in points or []:
        if px and t - look <= ts <= t:
            b.setdefault(int((ts - (t - look)) // bar), []).append((ts, float(px)))
    out = []
    for k in sorted(b):
        xs = [p for _, p in sorted(b[k])]
        out.append((xs[0], max(xs), min(xs), xs[-1]))
    return out


def read(points, t):
    """→ {structure, fvg, sweep, squeeze, pos, pull, bars} or None when the chart is too short to read.
    structure: 'up' (higher highs AND higher lows over the last 3 candles) · 'down' · 'range'
    fvg: 'in' = price is back inside the newest unfilled bullish gap (low[i] > high[i-2]) · 'above' = gap below, not retested ·
         'lost' = price closed under the gap · 'none'
    sweep: True when the last candles took out the prior low and closed back above it (a liquidity sweep that reclaimed)
    squeeze: last 2 candles' range ÷ the typical candle range (< 0.6 = coiled, > 1.6 = expanding)
    pos: where the last close sits in the window's range, 0 = at the low … 1 = at the high · pull: % under the window high"""
    cs = candles(points, t)
    if len(cs) < MIN_BARS:
        return None
    hi, lo, last = max(c[1] for c in cs), min(c[2] for c in cs), cs[-1][3]
    a, b, c = cs[-3], cs[-2], cs[-1]
    structure = 'up' if c[1] > b[1] > a[1] and c[2] > b[2] > a[2] else 'down' if c[1] < b[1] < a[1] and c[2] < b[2] < a[2] else 'range'
    fvg = 'none'
    for i in range(len(cs) - 2, 1, -1):          # newest COMPLETED bullish imbalance first (the candle still forming cannot be "retested")
        top, bot = cs[i][2], cs[i - 2][1]
        if top > bot * 1.002:
            later = cs[i + 1:]
            if any(x[3] < bot for x in later):
                fvg = 'lost'
            elif last <= top:
                fvg = 'in'
            else:
                fvg = 'above'
            break
    prior_low = min(x[2] for x in cs[:-2])
    sweep = min(b[2], c[2]) < prior_low and last > prior_low
    rng = [x[1] - x[2] for x in cs]
    typical = statistics.median(rng[:-2]) or 0.0
    squeeze = round(((rng[-1] + rng[-2]) / 2) / typical, 2) if typical > 0 else None
    return {'structure': structure, 'fvg': fvg, 'sweep': bool(sweep), 'squeeze': squeeze, 'pos': round((last - lo) / (hi - lo), 3) if hi > lo else 0.5,
            'pull': round((1 - last / hi) * 100, 2) if hi > 0 else 0.0, 'bars': len(cs)}


def keys(points, t):
    """The flat fields the pick record learns from: cBars (0 = chart too short to read), cStruct, cPos, cPull, cFvg."""
    r = read(points, t)
    if not r:
        return {'cBars': 0}
    return {'cBars': r['bars'], 'cStruct': r['structure'], 'cPos': r['pos'], 'cPull': r['pull'], 'cFvg': r['fvg']}
