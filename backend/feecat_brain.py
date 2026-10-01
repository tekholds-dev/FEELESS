"""Fee's setup memory: she learns which kinds of entries actually make money, from her own closed trades.

Every entry is described by a handful of bucketed features (1h move, order flow, liquidity depth, age, 5m heat,
market-cap band, lane). When a trade closes, its result is filed under each of those buckets. Before the next
entry she looks the setup up: buckets with a proven edge size her up, proven losers size her down, and a bucket
that keeps losing (enough samples, low win rate, negative average) vetoes the trade outright. Smoothed with a prior
so three lucky trades never rewrite her playbook. Pure functions; the service stores the memory.
"""

MIN_N = 4          # samples before a bucket counts at all
VETO_N = 5         # samples before a bucket can veto
MEMORY = 400       # closed trades remembered


def _b(v, edges, labels):
    for e, l in zip(edges, labels):
        if v < e:
            return l
    return labels[-1]


def setup_features(p: dict, now: float, fresh: bool = False, gap: bool = False) -> dict:
    num = lambda x, d=0.0: float(x) if isinstance(x, (int, float)) or (isinstance(x, str) and x.replace('.', '', 1).replace('-', '', 1).isdigit()) else d
    ch = p.get('priceChange') or {}
    tx = (p.get('txns') or {}).get('h1') or {}
    buys, sells = num(tx.get('buys')), num(tx.get('sells'))
    liq, mc = num((p.get('liquidity') or {}).get('usd')), num(p.get('marketCap') or p.get('fdv'))
    age_h = (now * 1000 - num(p.get('pairCreatedAt'), now * 1000)) / 3_600_000
    return {
        'h1': _b(num(ch.get('h1')), (5, 15, 30), ('<5%', '5-15%', '15-30%', '30%+')),
        'flow': _b(buys / max(sells, 1), (1.2, 2), ('<1.2x', '1.2-2x', '2x+')),
        'depth': _b(liq / mc * 100 if mc else 0, (5, 10), ('<5%', '5-10%', '10%+')),
        'age': _b(age_h, (6, 24, 72), ('<6h', '6-24h', '1-3d', '3d+')),
        'm5': _b(num(ch.get('m5')), (1, 3), ('<1%', '1-3%', '3%+')),
        'mc': _b(mc, (250_000, 1_000_000, 5_000_000), ('<250K', '250K-1M', '1-5M', '5M+')),
        'lane': 'fresh' if fresh else 'core',
        'gap': 'fvg' if gap else 'no-fvg',
    }


def remember(memory: list, setup: dict, ret_pct: float, pnl_sol: float, at: float) -> list:
    if not setup:
        return memory
    return (memory + [{'setup': setup, 'ret': round(float(ret_pct), 2), 'win': pnl_sol > 0, 'at': at}])[-MEMORY:]


def edge_table(memory: list) -> dict:
    """'feature=bucket' → {n, wins, winRate, avgRet, edge (-1..1)}. Win rate is smoothed toward 50% (prior 2/4)."""
    agg = {}
    for m in memory:
        for f, b in (m.get('setup') or {}).items():
            a = agg.setdefault(f'{f}={b}', {'n': 0, 'wins': 0, 'sum': 0.0})
            a['n'] += 1; a['wins'] += 1 if m['win'] else 0; a['sum'] += m['ret']
    out = {}
    for k, a in agg.items():
        wr = (a['wins'] + 2) / (a['n'] + 4)
        avg = a['sum'] / a['n']
        edge = max(-1.0, min(1.0, (wr - 0.5) * 1.4 + max(-0.6, min(0.6, avg / 40))))
        out[k] = {'n': a['n'], 'wins': a['wins'], 'winRate': round(a['wins'] / a['n'] * 100), 'avgRet': round(avg, 1), 'edge': round(edge, 3)}
    return out


PROBATION_MULT = 0.25


def setup_edge(setup: dict, table: dict) -> dict:
    """Size multiplier (0.5-1.5) and an optional veto for a new entry, with the buckets that decided it."""
    seen = [(f'{f}={b}', table[f'{f}={b}']) for f, b in setup.items() if table.get(f'{f}={b}', {}).get('n', 0) >= MIN_N]
    for k, s in seen:
        if s['n'] >= VETO_N and s['winRate'] <= 25 and s['avgRet'] <= -5:
            return {'mult': 0.0, 'veto': True, 'why': f"{k} lost {s['n'] - s['wins']}/{s['n']} (avg {s['avgRet']:+.1f}%)", 'used': [k]}
    if not seen:
        # Never-seen setup: probation size until her own results prove it (most of her losses were untested setups).
        return {'mult': PROBATION_MULT, 'veto': False, 'why': f'new setup — probation size ({PROBATION_MULT}×) until it proves itself', 'used': []}
    total = sum(s['n'] for _, s in seen)
    edge = sum(s['edge'] * s['n'] for _, s in seen) / total
    mult = round(max(0.5, min(1.5, 1 + edge * 0.6)), 2)
    best = max(seen, key=lambda kv: abs(kv[1]['edge']))
    return {'mult': mult, 'veto': False, 'why': f"{best[0]} {best[1]['winRate']}% wins over {best[1]['n']}", 'used': [k for k, _ in seen]}


def playbook(table: dict, top: int = 5) -> dict:
    """What she has learned, for humans: best and worst setups with enough samples."""
    rows = sorted(((k, v) for k, v in table.items() if v['n'] >= MIN_N), key=lambda kv: -kv[1]['edge'])
    fmt = lambda kv: {'setup': kv[0], **kv[1]}
    return {'best': [fmt(r) for r in rows[:top] if r[1]['edge'] > 0], 'worst': [fmt(r) for r in rows[::-1][:top] if r[1]['edge'] < 0]}


LIVES = 9


def discipline(exits: list, now: float, window: int = 10) -> dict:
    """Trader's discipline from her own recent closed trades (the part that keeps a bad day from becoming a bad week):
      - 9 lives: each losing exit in the last 24h costs a life, each winning one gives one back (max 9);
        at 0 lives she naps — no new entries until a loss rolls off (exits still run)
      - 5 losses in a row → stop trading 3h (tilt guard)
      - cold market (8+ recent trades, win rate < 25%, net red) → sit out 2h
      - 3 losses in a row → half size; negative expectancy → 0.7× size; proven edge (expectancy > 0, win rate ≥ 50%) → 1.2×
    Expectancy = average SOL made per trade — the number that actually decides if a strategy makes money."""
    done = [e for e in exits or [] if e.get('pnlSol') is not None]
    recent = done[-window:]
    streak = 0
    for e in reversed(done):
        if e['pnlSol'] < 0:
            streak += 1
        else:
            break
    n = len(recent)
    wins = sum(1 for e in recent if e['pnlSol'] > 0)
    net = sum(e['pnlSol'] for e in recent)
    exp = net / n if n else 0.0
    wr = wins / n if n else 0.0
    last = max((e.get('exitAt') or 0 for e in done), default=0)
    day = [e for e in done if now - (e.get('exitAt') or 0) < 86400]
    lives = max(0, min(LIVES, LIVES - sum(1 for e in day if e['pnlSol'] < 0) + sum(1 for e in day if e['pnlSol'] > 0)))
    out = {'streak': streak, 'trades': n, 'winRate': round(wr * 100), 'expectancySol': round(exp, 5), 'netSol': round(net, 5), 'pause': False, 'sizeMult': 1.0,
           'lives': lives, 'maxLives': LIVES}
    if lives == 0:
        return {**out, 'pause': True, 'sizeMult': 0.0, 'why': 'out of lives (9 losses in 24h) — napping until one rolls off'}
    if streak >= 5 and now - last < 3 * 3600:
        return {**out, 'pause': True, 'sizeMult': 0.0, 'why': f'{streak} losses in a row — stepping away for 3h instead of revenge trading'}
    if n >= 8 and wr < 0.25 and net < 0 and now - last < 2 * 3600:
        return {**out, 'pause': True, 'sizeMult': 0.0, 'why': f'cold market: {wins}/{n} recent trades won — sitting out 2h'}
    if streak >= 3:
        return {**out, 'sizeMult': 0.5, 'why': f'{streak} losses in a row — half size until a win'}
    if n >= 5 and exp < 0:
        return {**out, 'sizeMult': 0.7, 'why': f'negative expectancy ({exp:+.4f} SOL/trade) — smaller size'}
    if n >= 5 and exp > 0 and wr >= 0.5:
        return {**out, 'sizeMult': 1.2, 'why': f'edge confirmed ({wr:.0%} wins, {exp:+.4f} SOL/trade) — slightly bigger'}
    return {**out, 'why': 'normal size'}
