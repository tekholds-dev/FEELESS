"""🧠 Background playground: hundreds of simulated cards replayed over the REAL price paths the engine records (5-min samples of
every runner it picked). Pure, deterministic per seed, no network.

Each sim card = a random config (round clock, take-profit, stop, 🏇 hold rule, rotate-only-losers threshold) on 4–6 coins that all
have history in the window. It walks forward one sample at a time and only ever uses what was known at that moment (no look-ahead):
  • TP sells the coin to cash (or it is HELD when it runs ≥ +150% and keeps ≥ +80%, sold when it drops under +80% / 30% off its high);
  • a stop sells it; at every round end the worst coin under −minDrop is swapped for the best-moving coin of the PAST round;
  • every swap costs SWAP_COST (fees + price impact both ways), never zero.
`learn` turns the results into trait scores; `best` is the brain's pick (the config to try next on real cards). Ranking only.
"""
import random
import statistics

STEP_MIN = 5
CLOCKS = (5, 15, 30, 60)
TPS = (50, 100, 200, 300)
SLS = (15, 20, 30)
DROPS = (0, 5, 10, 20)
HOLDS = (True, False)
SWAP_COST = 0.006          # 0.6% per swap (network + FEELESS-free HQ route + impact) — the card always pays something to move


def _series(paths, start, steps):
    """{mint: [price per step]} for mints whose history covers the whole window (forward-filled within the window)."""
    out = {}
    for m, pts in (paths or {}).items():
        pts = sorted((float(t), float(p)) for t, p in pts if p and float(p) > 0)
        if not pts or pts[0][0] > start or pts[-1][0] < start + (steps - 1) * STEP_MIN * 60:
            continue
        row, j, last = [], 0, pts[0][1]
        for k in range(steps):
            t = start + k * STEP_MIN * 60
            while j < len(pts) and pts[j][0] <= t:
                last = pts[j][1]; j += 1
            row.append(last)
        out[m] = row
    return out


def random_cfg(rng):
    return {'clock': rng.choice(CLOCKS), 'tp': rng.choice(TPS), 'sl': rng.choice(SLS), 'minDrop': rng.choice(DROPS), 'hold': rng.choice(HOLDS)}


def simulate(series, mints, cfg, steps):
    """One card, $100 split evenly, walked step by step. Returns the final % (fees included, as a real card would see it)."""
    if not mints:
        return 0.0
    each = 100.0 / len(mints)
    legs = [{'m': m, 'units': each * (1 - SWAP_COST) / series[m][0], 'entry': series[m][0], 'high': series[m][0], 'ride': False, 'rmin': 0.0} for m in mints]
    cash, every = 0.0, max(1, cfg['clock'] // STEP_MIN)
    for k in range(1, steps):
        for l in list(legs):
            px = series[l['m']][k]
            g = (px / l['entry'] - 1) * 100
            l['rmin'] = min(l['rmin'], g)
            if l['ride']:
                l['high'] = max(l['high'], px)
                if g < 80 or px < l['high'] * 0.7:
                    cash += l['units'] * px * (1 - SWAP_COST); legs.remove(l)
                continue
            if cfg['hold'] and g >= 150:
                l.update(ride=True, high=px); continue
            if g >= cfg['tp'] or g <= -cfg['sl']:
                cash += l['units'] * px * (1 - SWAP_COST); legs.remove(l)
        if k % every == 0:   # round end: hold coins that stayed ≥ +80% all round, swap the worst loser for last round's best mover
            for l in legs:
                if cfg['hold'] and not l['ride'] and l['rmin'] >= 80:
                    l['ride'] = True
                l['rmin'] = (series[l['m']][k] / l['entry'] - 1) * 100   # next round's low starts here
            on = {l['m'] for l in legs}
            pool = [m for m in series if m not in on]
            past = lambda m: series[m][k] / series[m][max(0, k - every)] - 1
            losers = sorted((l for l in legs if not l['ride'] and (series[l['m']][k] / l['entry'] - 1) * 100 <= -cfg['minDrop']), key=lambda l: series[l['m']][k] / l['entry'])
            if losers and pool:
                out = losers[0]; best = max(pool, key=past)
                usd = out['units'] * series[out['m']][k] * (1 - SWAP_COST)
                legs.remove(out)
                legs.append({'m': best, 'units': usd * (1 - SWAP_COST) / series[best][k], 'entry': series[best][k], 'high': series[best][k], 'ride': False, 'rmin': 0.0})
            if cash > 0.5 and pool and len(legs) < len(mints):   # idle cash back into the past round's best mover
                best = max((m for m in series if m not in {l['m'] for l in legs}), key=past, default=None)
                if best:
                    legs.append({'m': best, 'units': cash * (1 - SWAP_COST) / series[best][k], 'entry': series[best][k], 'high': series[best][k], 'ride': False, 'rmin': 0.0}); cash = 0.0
    value = cash + sum(l['units'] * series[l['m']][steps - 1] for l in legs)
    return round(value - 100.0, 3)


def run(paths, now, n=200, hours=24, seed=None):
    """n sim cards over the last `hours` of recorded paths. Returns [{cfg, coins, pct}] (empty if there isn't enough history)."""
    steps = int(hours * 60 // STEP_MIN)
    series = _series(paths, now - hours * 3600, steps)
    if len(series) < 6:
        return []
    rng = random.Random(seed if seed is not None else int(now // 900))
    mints = sorted(series)
    out = []
    for _ in range(n):
        cfg = random_cfg(rng)
        pick = rng.sample(mints, rng.randint(4, min(6, len(mints))))
        out.append({'cfg': cfg, 'coins': len(pick), 'pct': simulate(series, pick, cfg, steps)})
    return out


def learn(results):
    """Trait scores: for every config value, average % and share of sims that ended up (fees included)."""
    score = {}
    for r in results or []:
        for trait, v in r['cfg'].items():
            s = score.setdefault(trait, {}).setdefault(str(v), {'n': 0, 'sum': 0.0, 'up': 0})
            s['n'] += 1; s['sum'] += r['pct']; s['up'] += 1 if r['pct'] > 0 else 0
    return {t: {v: {'n': s['n'], 'avgPct': round(s['sum'] / s['n'], 3), 'upPct': round(s['up'] / s['n'] * 100, 1)} for v, s in vals.items()} for t, vals in score.items()}


def best(score, min_n=10):
    """The brain's pick: per trait the value with the best average % (≥ min_n sims), plus the overall sim stats."""
    out = {}
    for t, vals in (score or {}).items():
        ok = [(v, s) for v, s in vals.items() if s['n'] >= min_n]
        if ok:
            v, s = max(ok, key=lambda vs: vs[1]['avgPct'])
            out[t] = {'value': v, **s}
    return out


def summary(results):
    pcts = [r['pct'] for r in results or []]
    if not pcts:
        return {'n': 0}
    return {'n': len(pcts), 'avgPct': round(statistics.mean(pcts), 3), 'medianPct': round(statistics.median(pcts), 3), 'upPct': round(sum(1 for p in pcts if p > 0) / len(pcts) * 100, 1),
            'bestPct': round(max(pcts), 3), 'worstPct': round(min(pcts), 3)}
