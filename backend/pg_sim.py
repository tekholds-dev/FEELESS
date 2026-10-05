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
RIDES = (0, 15, 25, 50, 150)   # ❄ freeze a coin running at +X% (0 = off) — the tier engine's rideAt
TRAILS = (5, 8, 15, 30)        # … then sell it X% off its peak (rideTrail)
CONFIRMS = (1, 2, 3, 4)   # ⏳ rounds in a row a coin must be losing before it may be rotated
SWAP_COST = 0.006          # 0.6% per swap (network + FEELESS-free HQ route + impact) — the card always pays something to move


MAX_STEP = 4.0


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
        # a price that jumps more than MAX_STEP× in one 5-min step is a launch tick or a bad read — nobody could have bought the
        # low side of it. One such path made the brain report "typical card +107%" and a best card of +3,709%.
        if any(b > a * MAX_STEP or b < a / MAX_STEP for a, b in zip(row, row[1:])):
            continue
        out[m] = row
    return out


def random_cfg(rng):
    return {'clock': rng.choice(CLOCKS), 'tp': rng.choice(TPS), 'sl': rng.choice(SLS), 'minDrop': rng.choice(DROPS), 'rideAt': rng.choice(RIDES),
            'trail': rng.choice(TRAILS), 'confirm': rng.choice(CONFIRMS)}


def _ride(cfg):
    """(freeze at %, trail %, floor %) — old saved configs carried `hold` (= the +150% rule, 30% trail)."""
    ra = float(cfg.get('rideAt', 150 if cfg.get('hold') else 0) or 0)
    tr = float(cfg.get('trail', 30) or 30)
    return ra, tr, min(80.0, ra / 2)


def simulate(series, mints, cfg, steps):
    """One card, $100 split evenly, walked step by step. Returns the final % (fees included, as a real card would see it)."""
    if not mints:
        return 0.0
    each = 100.0 / len(mints)
    legs = [{'m': m, 'units': each * (1 - SWAP_COST) / series[m][0], 'entry': series[m][0], 'high': series[m][0], 'ride': False, 'rmin': 0.0} for m in mints]
    cash, every = 0.0, max(1, cfg['clock'] // STEP_MIN)
    ra, tr, floor_g = _ride(cfg)
    for k in range(1, steps):
        for l in list(legs):
            px = series[l['m']][k]
            g = (px / l['entry'] - 1) * 100
            l['rmin'] = min(l['rmin'], g)
            if l['ride']:
                l['high'] = max(l['high'], px)
                if g < floor_g or px < l['high'] * (1 - tr / 100):   # same rule as the engine: under half the freeze, or tr% off its peak
                    cash += l['units'] * px * (1 - SWAP_COST); legs.remove(l)
                continue
            if ra > 0 and g >= ra:   # ❄ frozen: no TP / stop while it runs
                l.update(ride=True, high=px); continue
            if g >= cfg['tp'] or g <= -cfg['sl']:
                cash += l['units'] * px * (1 - SWAP_COST); legs.remove(l)
        if k % every == 0:   # round end: hold coins that stayed ≥ +80% all round, swap the worst loser for last round's best mover
            for l in legs:
                if ra > 0 and not l['ride'] and l['rmin'] >= min(80.0, ra):
                    l['ride'] = True
                l['rmin'] = (series[l['m']][k] / l['entry'] - 1) * 100   # next round's low starts here
            on = {l['m'] for l in legs}
            pool = [m for m in series if m not in on]
            past = lambda m: series[m][k] / series[m][max(0, k - every)] - 1
            for l in legs:   # ⏳ patience: count rounds in a row each coin has been losing
                l['lose'] = l.get('lose', 0) + 1 if (series[l['m']][k] / l['entry'] - 1) * 100 <= -cfg['minDrop'] else 0
            losers = sorted((l for l in legs if not l['ride'] and l.get('lose', 0) >= cfg.get('confirm', 1)), key=lambda l: series[l['m']][k] / l['entry'])
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
    """Trait scores: for every config value, median % (robust — one moonshot can't skew it), average % and share that ended up."""
    acc = {}
    for r in results or []:
        for trait, v in r['cfg'].items():
            acc.setdefault(trait, {}).setdefault(str(v), []).append(r['pct'])
    return {t: {v: {'n': len(ps), 'medPct': round(statistics.median(ps), 3), 'avgPct': round(sum(ps) / len(ps), 3),
                    'upPct': round(sum(1 for p in ps if p > 0) / len(ps) * 100, 1)} for v, ps in vals.items()} for t, vals in acc.items()}


def best(score, min_n=10):
    """The brain's pick: per trait the value whose TYPICAL card did best (median, then share up) over ≥ min_n sims."""
    out = {}
    for t, vals in (score or {}).items():
        ok = [(v, s) for v, s in vals.items() if s['n'] >= min_n]
        if ok:
            v, s = max(ok, key=lambda vs: (vs[1].get('medPct', vs[1]['avgPct']), vs[1]['upPct']))
            out[t] = {'value': v, **s}
    return out


def by_clock(results, min_n=6):
    """🕐 The brain's pick PER ROUND LENGTH: among the sim cards that played that clock, the trait values whose typical card did best.
    Every clock gets its own answer (a 5-min card should not run a 1-hour card's settings). `profitable` is only true when the
    TYPICAL card on that clock ended up — the pick is the least-bad config otherwise, and the screen says so."""
    out = {}
    for clock in sorted({str(r['cfg'].get('clock')) for r in results or []}, key=lambda v: float(v)):
        sub = [r for r in results if str(r['cfg'].get('clock')) == clock]
        if len(sub) < min_n * 2:
            continue
        pick = best({t: v for t, v in learn(sub).items() if t != 'clock'}, min_n)
        sm = summary(sub)
        out[clock] = {'n': len(sub), 'medPct': sm.get('medianPct'), 'upPct': sm.get('upPct'), 'profitable': _num(sm.get('medianPct')) > 0,
                      'cfg': {t: p['value'] for t, p in pick.items()}, 'proof': {t: {'medPct': p.get('medPct'), 'n': p['n']} for t, p in pick.items()},
                      'strategies': strategies(sub, min_n)}
    return out


STRATS = (('steady', '🛡 Steady', 'upPct', 'most sim cards ended up'),
          ('engine', '🧠 Engine pick', 'medPct', 'best typical card'),
          ('hunt', '🔥 Hunt', 'avgPct', 'biggest average — wilder swings'))


def strategies(sub, min_n=6):
    """3 strategies for ONE round length, each built from what the sims on that clock actually did: per trait the value with the best
    share-ended-up (🛡), median (🧠) or average (🔥). Each carries its proof = every chosen setting's own sims on that clock.
    Never claims profit: `profitable` only when that proof's typical card ended up. Always 3 different configs."""
    score = {t: v for t, v in learn(sub).items() if t != 'clock'}
    out, seen = [], set()
    for key, name, metric, why in STRATS:
        pick = {}
        for t, vals in score.items():
            ok = sorted(((v, s) for v, s in vals.items() if s['n'] >= min_n), key=lambda vs: -vs[1].get(metric, 0))
            if ok:
                pick[t] = ok
        if not pick:
            continue
        cfg = {t: ok[0][0] for t, ok in pick.items()}
        sig = tuple(sorted(cfg.items()))
        for t, ok in pick.items():   # same config as a strategy already listed → take this trait's runner-up value
            if sig not in seen:
                break
            if len(ok) > 1:
                cfg = {**cfg, t: ok[1][0]}; sig = tuple(sorted(cfg.items()))
        if sig in seen:
            continue
        seen.add(sig)
        # proof = each chosen setting's OWN sims on this clock (every value is backed by ≥ min_n of them); the strategy reads the
        # middle of those typical cards — an estimate from real paths, never a promise
        rows = [score[t][v] for t, v in cfg.items()]
        med = round(statistics.median(r['medPct'] for r in rows), 3)
        out.append({'key': key, 'name': name, 'why': why, 'cfg': cfg, 'n': min(r['n'] for r in rows), 'medPct': med,
                    'avgPct': round(statistics.median(r['avgPct'] for r in rows), 3), 'upPct': round(statistics.median(r['upPct'] for r in rows), 1),
                    'proof': {t: {'medPct': score[t][v]['medPct'], 'n': score[t][v]['n']} for t, v in cfg.items()}, 'profitable': med > 0})
    return out


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def summary(results):
    pcts = [r['pct'] for r in results or []]
    if not pcts:
        return {'n': 0}
    return {'n': len(pcts), 'avgPct': round(statistics.mean(pcts), 3), 'medianPct': round(statistics.median(pcts), 3), 'upPct': round(sum(1 for p in pcts if p > 0) / len(pcts) * 100, 1),
            'bestPct': round(max(pcts), 3), 'worstPct': round(min(pcts), 3)}
