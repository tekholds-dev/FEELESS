"""Crowd edge: FeeCat learns from FEELESS traders. Pure functions (no I/O) — the service gathers verified trades + prices.

- trader_skill(): every VERIFIED FEELESS buy (≥ $1, ≥ 24h old) scored against the coin's price now: win = ≥ +10%.
- elites(): traders with a real record (≥ 6 scored buys, ≥ 55% wins, ≥ +10% average) — nothing self-reported.
- elite_flow(): which coins elites bought in the last few hours (distinct elites + $), the signal FeeCat reads.
FeeCat then files the 'crowd' tag in her setup memory, so following elites only keeps its weight if it actually pays.
"""
WIN_PCT = 10.0
MIN_AGE = 24 * 3600
MIN_USD = 1.0
ELITE_N, ELITE_WR, ELITE_AVG = 6, 55.0, 10.0
FLOW_WINDOW = 6 * 3600


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def buy_fill(t):
    """Entry price of a verified buy: its fill price, else $ paid / tokens."""
    return _f(t.get('fillPrice') or t.get('price')) or (_f(t.get('usd')) / _f(t.get('tokens')) if _f(t.get('tokens')) else 0.0)


def trader_skill(trades, prices, now):
    rows = []
    for t in trades or []:
        if t.get('side', 'buy') != 'buy' or _f(t.get('usd')) < MIN_USD or now - _f(t.get('ts')) < MIN_AGE:
            continue
        entry, px = buy_fill(t), _f(prices.get(t.get('token')))
        if entry > 0 and px > 0:
            rows.append((px / entry - 1) * 100)
    n = len(rows)
    return {'n': n, 'winRate': round(sum(r >= WIN_PCT for r in rows) / n * 100, 1) if n else 0.0, 'avgPct': round(sum(rows) / n, 2) if n else 0.0}


def elites(skills, exclude=()):
    return {w for w, s in skills.items() if w not in set(exclude) and s['n'] >= ELITE_N and s['winRate'] >= ELITE_WR and s['avgPct'] >= ELITE_AVG}


def elite_flow(trades_by_wallet, elite_set, now, window=FLOW_WINDOW):
    out = {}
    for w in elite_set:
        for t in trades_by_wallet.get(w) or []:
            if t.get('side', 'buy') == 'buy' and now - _f(t.get('ts')) <= window and t.get('token') and _f(t.get('usd')) >= MIN_USD:
                a = out.setdefault(t['token'], {'wallets': set(), 'usd': 0.0})
                a['wallets'].add(w); a['usd'] += _f(t.get('usd'))
    return {m: {'n': len(a['wallets']), 'usd': round(a['usd'], 2)} for m, a in out.items()}
