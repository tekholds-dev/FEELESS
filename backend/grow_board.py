"""💰 THE OWNER'S MONEY BOARD (owner 2026-11-06: "show me real good stuff with ways to grow and pay these ppl ... what it made in past 12-24hrs, better options").
Every way the Collective's money could work, side by side, on the venues' own numbers: pools, lending, staking and tokenized stocks. Each option gets hourly points, so the page can
draw what real money would have done over any window, price moves included. It measures. It never picks, never moves money, and past numbers promise nothing. Pure + tested; the service fetches."""
import math

SOL_MINT = 'So11111111111111111111111111111111111111112'
STABLES = {'USDC', 'USDT', 'USD1', 'PYUSD', 'USDG', 'USDS', 'FDUSD', 'USDE', 'DAI'}
MIN_LEND_TVL = 5e6
MIN_STOCK_LIQ = 2e5
KEEP = {'lend': 12, 'stake': 8, 'stock': 8}
HOURS = 300   # what the candle service holds: about 12 days of hourly bars


def _f(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    return x if math.isfinite(x) else 0.0


def pool_row(r):
    """A venue's pool row (range_pools). Both sides move unless one is a dollar."""
    x, y = str(r.get('symX') or ''), str(r.get('symY') or '')
    stable = (x.upper() in STABLES) + (y.upper() in STABLES)
    return {'id': r['pool'], 'kind': 'pool', 'name': r.get('name') or f'{x}-{y}', 'venue': r.get('venue'), 'tvl': r.get('tvl'), 'vol24': r.get('vol24'), 'yearPct': round(_f(r.get('rate')) * 36500, 2), 'per1k24': round(_f(r.get('rate')) * 1000, 4),
            'risk': 'none' if stable == 2 else 'half' if stable == 1 else 'both', 'readOnly': bool(r.get('readOnly')), 'pool': r}


def lend_rows(rows):
    """DefiLlama's own Solana rows: lending on dollars has no price risk, staking or lending SOL moves with SOL. Anything else single sided is left out, because its price is not read here."""
    out = {'lend': [], 'stake': []}
    for r in rows or []:
        if not isinstance(r, dict) or r.get('chain') != 'Solana' or r.get('exposure') != 'single' or r.get('ilRisk') != 'no' or r.get('outlier') or _f(r.get('tvlUsd')) < MIN_LEND_TVL or not r.get('pool'):
            continue
        sym = str(r.get('symbol') or ''); dollars = bool(r.get('stablecoin')) and sym.upper() in STABLES; sol = SOL_MINT in (r.get('underlyingTokens') or []) or sym.upper() == 'SOL'
        if not dollars and not sol:
            continue
        apy = _f(r.get('apy')); reward = _f(r.get('apyReward'))
        out['lend' if dollars else 'stake'].append({'id': f"llama:{r['pool']}", 'kind': 'lend' if dollars else 'stake', 'name': f"{sym} on {str(r.get('project') or '').replace('-', ' ')}", 'venue': r.get('project'), 'tvl': round(_f(r.get('tvlUsd')), 2), 'yearPct': round(apy, 2), 'rewardPct': round(reward, 2),
                                                    'per1k24': round(apy / 36500 * 1000, 4), 'risk': 'none' if dollars else 'coin', 'llama': r['pool'], 'mean30': round(_f(r.get('apyMean30d')), 2)})
    return [x for k in out for x in sorted(out[k], key=lambda y: -y['tvl'])[:KEEP[k]]]


def stock_rows(pairs):
    """Tokenized stocks on Solana, their deepest dollar pool each. They earn nothing by being held: only the price moves."""
    best = {}
    for p in pairs or []:
        if not isinstance(p, dict) or p.get('chainId') != 'solana':
            continue
        base, quote = (p.get('baseToken') or {}), (p.get('quoteToken') or {}); liq = _f((p.get('liquidity') or {}).get('usd')); sym = str(base.get('symbol') or '')
        if str(quote.get('symbol') or '').upper() in STABLES and sym.endswith('x') and sym[:-1].isupper() and liq >= MIN_STOCK_LIQ and liq > best.get(sym, {}).get('liq', 0):
            best[sym] = {'id': f"stock:{p.get('pairAddress')}", 'kind': 'stock', 'name': sym, 'venue': p.get('dexId'), 'tvl': round(liq, 2), 'liq': liq, 'yearPct': 0.0, 'per1k24': 0.0, 'risk': 'coin', 'pair': p.get('pairAddress')}
    return sorted(best.values(), key=lambda r: -r['tvl'])[:KEEP['stock']]


def board(pools, lends, stocks):
    seen = set(); rows = []
    for r in [pool_row(p) for p in pools or [] if p.get('pool')] + list(lends or []) + list(stocks or []):
        if r['id'] not in seen:
            seen.add(r['id']); rows.append(r)
    return rows


def _closes(bars):
    return {int(b[0]): (_f(b[4]), _f(b[5])) for b in bars or [] if isinstance(b, (list, tuple)) and len(b) >= 6 and _f(b[4]) > 0}


def pool_points(row, bars, sol_bars=None):
    """(points, why). Each hour: a = its coin's price, b = the other side's price, fee = fees that hour per dollar in the pool. No points, and why, when the other side cannot be priced.
    Fees are anchored to the venue's own last 24 hours (fees / depth). Candle volume can be far off a venue's (a real read showed $448 a day on $1,000), so it only spreads them across the hours."""
    p = row['pool']; x, y = str(p.get('symX') or '').upper(), str(p.get('symY') or '').upper(); own = _closes(bars); rate = _f(p.get('rate'))
    if not own:
        return [], 'No price history for this pool.'
    other = None
    if y not in STABLES and x not in STABLES:
        if 'SOL' not in (x, y):
            return [], 'Neither side is a dollar or SOL, so its other coin cannot be priced here.'
        sol = _closes(sol_bars)
        if not sol:
            return [], 'SOL price history could not be read.'
        t0 = max(own); near = abs(own[t0][0] / max(sol.get(t0, (1e-9,))[0], 1e-9) - 1) < 0.2
        if near:
            return [], 'Its price history follows SOL, so its other coin cannot be priced here.'
        other = sol
    out = []; last = sum(own[t][1] for t in sorted(own)[-24:]); per_vol = rate / last if last > 0 else 0.0
    for t in sorted(own):
        px, vol = own[t]; b = 1.0
        if other is not None:
            if t not in other:
                continue
            b = other[t][0]
        out.append({'t': t, 'a': px, 'b': b, 'fee': vol * per_vol if per_vol else rate / 24})
    return out[-HOURS:], ''


def lend_points(row, chart, sol_bars, now):
    """Hourly points from its real daily rates, last 12 days. SOL options move with SOL's real price. Rates are read per day, so an hour uses that day's rate."""
    days = sorted(((_ts(c.get('timestamp')), _f(c.get('apy'))) for c in chart or [] if isinstance(c, dict)), key=lambda x: x[0])
    days = [d for d in days if d[0]]
    if not days:
        return [], 'No rate history for this one.'
    sol = _closes(sol_bars) if row['kind'] == 'stake' else None
    if row['kind'] == 'stake' and not sol:
        return [], 'SOL price history could not be read.'
    start = int(now // 3600 * 3600) - HOURS * 3600; out = []; i = 0
    for t in range(start, int(now), 3600):
        while i + 1 < len(days) and days[i + 1][0] <= t:
            i += 1
        if days[i][0] > t:
            continue
        a = 1.0
        if sol is not None:
            if t not in sol:
                continue
            a = sol[t][0]
        out.append({'t': t, 'a': a, 'b': 1.0, 'fee': days[i][1] / 100 / 8760})
    return out, ''


def stock_points(bars):
    own = _closes(bars)
    return ([{'t': t, 'a': own[t][0], 'b': 1.0, 'fee': 0.0} for t in sorted(own)][-HOURS:], '') if own else ([], 'No price history for this one.')


def _ts(v):
    from datetime import datetime
    try:
        return int(datetime.fromisoformat(str(v).replace('Z', '+00:00')).timestamp())
    except (TypeError, ValueError):
        return 0


def view(row):
    """What the page gets for a row. The raw venue row stays only for pools, where its band card reads it."""
    return {k: v for k, v in row.items() if k != 'liq'}
