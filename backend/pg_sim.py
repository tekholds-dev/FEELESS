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

import pick_edge as _edge

STEP_MIN = 5
CLOCKS = (5, 15, 30, 60)
TPS = (50, 100, 200, 300)
SLS = (15, 20, 30)
DROPS = (0, 5, 10, 20)
RIDES = (0, 15, 25, 50, 150)   # ❄ freeze a coin running at +X% (0 = off) — the tier engine's rideAt
TRAILS = (5, 8, 15, 30)        # … then sell it X% off its peak (rideTrail)
CONFIRMS = (1, 2, 3, 4)   # ⏳ rounds in a row a coin must be losing before it may be rotated
AGES = (0, 1, 6, 12)       # 🧬 selection gene: a coin must be at least this many hours old when it is bought (0 = any)
POOLS = (0, 25, 50, 100)   # 🧬 … and its pool at least this many $K (0 = any). Both read from the runner round's own snapshot.
RESTS = (0, 15, 30, 60)    # 🪑 minutes a seat stays in cash after its coin LEFT (stop / take / trail / off the feed) before a new coin may take it;
                           # the coin that left is not bought back for the same time (at least 3 rounds, like the engine's cool-down)
BUYS = (0, 60, 65, 70)     # 🧬 buyers' share of the last hour's trades a coin needs when bought (0 = any; unknown = out)
VOLS = (0, 50, 100)        # 🧬 1h volume a coin needs when bought, $K (0 = any)
MOMS = (0, 20, 40)         # 🧬 … and its 1h move at least +this % (0 = any): the coins that went 2–5× were already moving on real volume
FLOORS = (0, 3, 6)         # 🧠 with `edge` on: the record's estimate must be at least +this % (0 = just not negative)
EDGES = (0, 1)             # 🧠 1 = buy only coins the board's own record does not expect to lose (pick_edge.py, learned BEFORE the window)
# 🎯 THE SIM MUST LOSE WHEN A REAL CARD LOSES. Measured 2026-10-05 against the owner's real $5 card (360 fills) and the feed:
#   · a real swap costs ~1.5% (fill vs mid ≈ 0.25% on buys, 1.6% on sells, plus ~0.76% network on a $0.50 swap) — it was 0.6% here
#   · 290 coins that LEFT the feed were on average 18% under their last reading (23% of them down more than half)
# The old sim replayed only coins whose path covered the WHOLE window — the survivors — and let cards pick among them: it read
# "typical card +67% a day" while the real card lost. Every rule below removes one of those look-aheads.
SWAP_COST = 0.015
GONE_HAIRCUT = 0.18     # a coin that drops off the feed is sold this far under its last reading
ALIVE_GAP = 20 * 60     # no reading for 20 min = off the feed
MAX_STEP = 4.0


def _series(paths, start, steps):
    """{mint: [price or None per step]}. None = no live reading at that step (not listed yet, or it left the feed). EVERY coin
    with a reading inside the window is kept — the ones that died too. A path with a more than MAX_STEP× UP-tick in one step is a
    launch tick or a bad read (nobody bought the low side) and is left out; a crash of any size is real and stays."""
    out, end = {}, start + (steps - 1) * STEP_MIN * 60
    for m, pts in (paths or {}).items():
        pts = sorted((float(t), float(p)) for t, p in pts if p and float(p) > 0)
        if not pts or pts[-1][0] < start - ALIVE_GAP or pts[0][0] > end:
            continue
        row, j, last, last_t, bad = [], 0, None, 0.0, False
        for k in range(steps):
            t = start + k * STEP_MIN * 60
            seen = last if row and row[-1] is not None else None
            while j < len(pts) and pts[j][0] <= t:
                last, last_t = pts[j][1], pts[j][0]; j += 1
            px = last if last is not None and t - last_t <= ALIVE_GAP else None
            if px is not None and seen is not None and px > seen * MAX_STEP:
                bad = True; break
            row.append(px)
        if not bad and any(v is not None for v in row):
            out[m] = row
    return out


def random_cfg(rng):
    return {'clock': rng.choice(CLOCKS), 'tp': rng.choice(TPS), 'sl': rng.choice(SLS), 'minDrop': rng.choice(DROPS), 'rideAt': rng.choice(RIDES),
            'trail': rng.choice(TRAILS), 'confirm': rng.choice(CONFIRMS), 'age': rng.choice(AGES), 'pool': rng.choice(POOLS), 'edge': rng.choice(EDGES), 'rest': rng.choice(RESTS), 'buy': rng.choice(BUYS), 'floor': rng.choice(FLOORS), 'vol': rng.choice(VOLS), 'mom': rng.choice(MOMS)}


OFFER_MAX_AGE = 45 * 60   # a runner round older than this is not "what the board offers now"


def offers(rounds, start, steps):
    """What the runner board OFFERED at each step = the picks of the latest round dealt before it (best score first), each with its
    own snapshot (age, pool). This is the engine's real, gated choice at that time — the sim buys from it and from nothing else."""
    rs = sorted(((float(r.get('at') or 0), sorted((p for p in r.get('picks') or [] if p.get('mint')), key=lambda p: -_num(p.get('score')))) for r in rounds or []), key=lambda x: x[0])
    out, j = [], -1
    for k in range(steps):
        t = start + k * STEP_MIN * 60
        while j + 1 < len(rs) and rs[j + 1][0] <= t:
            j += 1
        out.append(rs[j][1] if j >= 0 and t - rs[j][0] <= OFFER_MAX_AGE else [])
    return out


def fits(p, cfg, table=None):
    """Does this offered coin pass the card's selection genes? Unknown age fails any age rule (fail closed). `edge` on = the
    record's estimate for the coin (edge.score against `table`) must not be negative."""
    age, pool = float(cfg.get('age') or 0), float(cfg.get('pool') or 0) * 1000
    if cfg.get('edge') and table and (_edge.score(p, table) or -1e9) < float(cfg.get('floor') or 0):
        return False
    if float(cfg.get('buy') or 0) > 0 and _num(p.get('buyShare')) < float(cfg['buy']):
        return False
    if float(cfg.get('vol') or 0) > 0 and _num(p.get('vol1h')) < float(cfg['vol']) * 1000:
        return False
    if float(cfg.get('mom') or 0) > 0 and (p.get('chg1h') is None or _num(p.get('chg1h')) < float(cfg['mom'])):
        return False
    return (age <= 0 or (p.get('ageH') is not None and _num(p.get('ageH')) >= age)) and _num(p.get('liq')) >= pool


def _ride(cfg):
    """(freeze at %, trail %, floor %)."""
    ra = float(cfg.get('rideAt', 0) or 0)
    tr = float(cfg.get('trail', 30) or 30)
    return ra, tr, min(80.0, ra / 2)


def simulate(series, mints, cfg, steps, cost=SWAP_COST, offer=None, seats=None, table=None):
    """One card, $100 over `seats` equal seats, walked step by step with ONLY what was known at each step. Returns the final %
    (swap costs included, as a real card would see it). A coin that leaves the feed is sold GONE_HAIRCUT under its last reading.
    `offer` (from `offers`) = what the runner board offered at each step: a new coin can only be one of those, live right now and
    passing the card's selection genes. Without it (tests, no rounds on record) any live coin may come in, best mover first.
    An empty seat is cash until a coin qualifies. → % ; sets cfg-independent `simulate.trades` to the number of buys made."""
    mints = [m for m in mints if m in series and series[m][0] is not None]
    seats = max(1, int(seats or len(mints) or 1))
    each = 100.0 / seats
    new = lambda m, usd, k: {'m': m, 'units': usd * (1 - cost) / series[m][k], 'entry': series[m][k], 'high': series[m][k], 'last': series[m][k], 'ride': False, 'rmin': 0.0}
    legs = [new(m, each, 0) for m in mints[:seats]]
    cash, every, buys = each * (seats - len(legs)), max(1, cfg['clock'] // STEP_MIN), len(legs)
    ra, tr, floor_g = _ride(cfg)
    rest_k = int(float(cfg.get('rest') or 0) // STEP_MIN)
    cool_k = max(rest_k, 3 * every) if 'rest' in cfg else 0
    waits, sold = [], {}   # steps at which a rested seat opens again · {mint: step it left}
    mints_on = {l['m'] for l in legs}
    for k in range(1, steps):
        n0 = len(legs)
        for l in list(legs):
            px = series[l['m']][k]
            if px is None:   # ☠ off the feed: no clean exit — sold well under its last reading
                cash += l['units'] * l['last'] * (1 - GONE_HAIRCUT) * (1 - cost); legs.remove(l); continue
            l['last'] = px
            g = (px / l['entry'] - 1) * 100
            l['rmin'] = min(l['rmin'], g)
            if l['ride']:
                l['high'] = max(l['high'], px)
                if g < floor_g or px < l['high'] * (1 - tr / 100):   # same rule as the engine: under half the freeze, or tr% off its peak
                    cash += l['units'] * px * (1 - cost); legs.remove(l)
                continue
            if ra > 0 and g >= ra:   # ❄ frozen: no TP / stop while it runs
                l.update(ride=True, high=px); continue
            if g >= cfg['tp'] or g <= -cfg['sl']:
                cash += l['units'] * px * (1 - cost); legs.remove(l)
        if len(legs) < n0:
            on_ = {l['m'] for l in legs}
            sold.update({m: k for m in mints_on - on_}); waits += [k + rest_k] * (n0 - len(legs))
        mints_on = {l['m'] for l in legs}
        if k % every == 0:   # round end: hold coins that stayed ≥ +80% all round, swap the worst loser, put idle cash back to work
            for l in legs:
                if ra > 0 and not l['ride'] and l['rmin'] >= min(80.0, ra):
                    l['ride'] = True
                l['rmin'] = (l['last'] / l['entry'] - 1) * 100   # next round's low starts here
            back = max(0, k - every)
            def pool():
                on = {l['m'] for l in legs} | {m for m, at in sold.items() if k - at < cool_k}
                if offer is not None:   # the board's own picks right now — by the record's estimate when the card uses it, else best score first
                    ok = [p for p in offer[k] if p['mint'] not in on and p['mint'] in series and series[p['mint']][k] is not None and fits(p, cfg, table)]
                    if cfg.get('edge') and table:
                        ok = sorted(ok, key=lambda p: -(_edge.score(p, table) or -1e9))
                    return [p['mint'] for p in ok]
                live = [m for m in series if m not in on and series[m][k] is not None and series[m][back] is not None]
                return sorted(live, key=lambda m: -(series[m][k] / series[m][back]))
            for l in legs:   # ⏳ patience: count rounds in a row each coin has been losing
                l['lose'] = l.get('lose', 0) + 1 if (l['last'] / l['entry'] - 1) * 100 <= -cfg['minDrop'] else 0
            losers = sorted((l for l in legs if not l['ride'] and l.get('lose', 0) >= cfg.get('confirm', 1)), key=lambda l: l['last'] / l['entry'])
            cand = pool() if losers else []
            if losers and cand:
                out = losers[0]
                usd = out['units'] * out['last'] * (1 - cost)
                legs.remove(out); legs.append(new(cand[0], usd, k)); buys += 1
            waits = [w for w in waits if w > k]
            while cash > 0.5 and len(legs) + len(waits) < seats:   # idle cash / an empty seat that is not resting → the next coin the board offers
                cand = pool()
                if not cand:
                    break
                part = cash / (seats - len(legs))
                legs.append(new(cand[0], part, k)); cash -= part; buys += 1
            mints_on = {l['m'] for l in legs}
    simulate.trades = buys
    value = cash + sum(l['units'] * l['last'] for l in legs)
    return round(value - 100.0, 3)


def run(paths, now, n=200, hours=24, seed=None, cost=SWAP_COST, rounds=None):
    """n sim cards over the last `hours` of recorded paths. Returns [{cfg, coins, pct}] (empty if there isn't enough history).
    With `rounds` (the runner board's own record) a card buys ONLY what the board offered at that moment — its real, gated picks —
    filtered by the card's selection genes; a card that never found a coin to buy is not counted. Without rounds: any coin live
    at the start, whatever became of it afterwards."""
    steps = int(hours * 60 // STEP_MIN)
    start = now - hours * 3600
    series = _series(paths, start, steps)
    live0 = sorted(m for m in series if series[m][0] is not None)
    offer = offers(rounds, start, steps) if rounds else None
    # 🧠 the edge table a card may use is learned ONLY from picks whose outcome was known before the window opened (no look-ahead)
    table = _edge.learn(_edge.samples(rounds, paths, start)) if rounds else None
    if len(live0) < 6 and not (offer and any(offer)):
        return []
    rng = random.Random(seed if seed is not None else int(now // 900))
    out = []
    for _ in range(n):
        cfg = random_cfg(rng)
        seats = rng.randint(4, 6)
        if offer is not None:
            if not table:
                cfg = {k: v for k, v in cfg.items() if k != 'edge'}   # record too short to learn from → the gene is not judged
            first = [p['mint'] for p in offer[0] if p['mint'] in series and series[p['mint']][0] is not None and fits(p, cfg, table)]
            pick = rng.sample(first, min(seats, len(first)))
        else:
            cfg = {k: v for k, v in cfg.items() if k not in ('age', 'pool', 'edge')}   # no snapshots to read them from
            seats = min(seats, len(live0)); pick = rng.sample(live0, seats)
        pct = simulate(series, pick, cfg, steps, cost, offer, seats, table)
        if simulate.trades:
            out.append({'cfg': cfg, 'coins': seats, 'pct': pct, 'trades': simulate.trades})
    return out


# 🎯 WHOLE-CONFIG PROOF, WALK-FORWARD. The trait scores below judge each setting ALONE (its median over cards whose other settings
# are random), so a setup that only works as a whole never showed up. `proven` plays ONE fixed config — SNIPER — on many separate
# windows, each replayed with only what was known before it (the edge table is learned before the window opens).
# It is NOT tuned to the record: a search that tuned it window by window did WORSE on the following 3 hours than this fixed setup
# (2026-10-05, 15 windows: tuned −2.7% vs fixed −0.5% on 5-min rounds) — tuning on two days of prices fits noise.
# WHAT MATTERED was never the exits (stop, freeze, trail, round length all read the same) — it was WHAT IS BOUGHT.
SNIPER = {'rest': 0, 'tp': 100, 'sl': 15, 'minDrop': 10, 'rideAt': 15, 'trail': 8, 'confirm': 4, 'age': 12, 'pool': 50, 'edge': 1, 'floor': 3, 'buy': 65, 'vol': 0, 'mom': 0}
# 🚀 RUNNER HUNT — the owner's point, measured: of 92 board picks 21% peaked at 2× or more within 6h (8% at 3×+), after a typical
# dip of only −6%, ~3.5h after the pick. What they shared when picked: ALREADY moving (+40% and more on the hour) on REAL volume
# ($75K–$245K in the hour, vs $32K for the ones that went nowhere) and NOT brand new. Sniper can never hold one (it sells 8% off a
# +15% peak). Hunt buys exactly those and gives them room: wide stop, freeze late, trail 30% off the peak. Under 6h old the same
# rule LOSES (−15% typical) — age is what separates a runner from a launch pump. The record gate must be OFF for it: the table
# marks every coin already up > 30% on the hour as a loser, because without the age + volume condition most of them are.
HUNT = {'rest': 0, 'tp': 300, 'sl': 30, 'minDrop': 10, 'rideAt': 50, 'trail': 30, 'confirm': 4, 'age': 12, 'pool': 25, 'edge': 0, 'floor': 0, 'buy': 0, 'vol': 50, 'mom': 40}
SETUPS = (('rhunt', '🚀 Runner hunt', 'coins already running on real volume, given room to become a 2–5×', HUNT, 6.0),
          ('sniper', '🎯 Sniper', 'few buys, only what the record backs: older coins, deep pools, buyers in control', None, 3.0))
FWD_HOURS = 3.0       # each window: the 3 hours (Hunt: 6 — a runner needs ~3.5h to peak) after a moment T, a T every half window back
                      # through the record (neighbouring windows share half their prices)
FWD_MIN = 10          # windows needed before anything may be called proven
PROVEN_WINDOWS = 0.6  # share of windows whose typical card must end up


def prep(paths, rounds, now, hours=12, offs=(0,)):
    """The replay material for each window ending `off` hours ago: (steps, series, offers, edge table learned before it)."""
    steps, out = int(hours * 60 // STEP_MIN), []
    for off in offs:
        start = now - off * 3600 - hours * 3600
        table = _edge.learn(_edge.samples(rounds, paths, start))
        of = offers(rounds, start, steps)
        if any(of):
            out.append((steps, _series(paths, start, steps), of, table))
    return out


def joint(windows, cfg, per=8, seed=1, cost=SWAP_COST):
    """ONE whole config played `per` times in every window (different first coins / seat counts). → {n, medPct, avgPct, upPct,
    worstPct, trades, windows, windowsUp, perWindow} — a card that never bought is not counted; no result at all → None."""
    res, by = [], {}
    for i, (steps, series, of, table) in enumerate(windows or []):
        c = cfg if table else {k: v for k, v in cfg.items() if k not in ('edge', 'floor')}
        rng = random.Random(seed * 1000 + i)
        for _ in range(per):
            seats = rng.randint(4, 6)
            first = [p['mint'] for p in of[0] if p['mint'] in series and series[p['mint']][0] is not None and fits(p, c, table)]
            pct = simulate(series, rng.sample(first, min(seats, len(first))), c, steps, cost, of, seats, table)
            if simulate.trades:
                res.append((pct, simulate.trades)); by.setdefault(i, []).append(pct)
    if not res:
        return None
    ps = [r[0] for r in res]
    per_w = [round(statistics.median(v), 2) for v in by.values()]
    return {'n': len(ps), 'medPct': round(statistics.median(ps), 2), 'avgPct': round(sum(ps) / len(ps), 2), 'upPct': round(sum(1 for p in ps if p > 0) / len(ps) * 100),
            'worstPct': round(min(ps), 1), 'trades': round(statistics.median(r[1] for r in res), 1), 'windows': len(by),
            'windowsUp': sum(1 for v in per_w if v > 0), 'perWindow': per_w}


def proven(paths, rounds, now, clock=15, cfg=None, hours=FWD_HOURS, step=None, span=48.0, key='sniper', name='🎯 Sniper',
           why='few buys, only what the record backs: older coins, deep pools, buyers in control'):
    """🎯 SNIPER (or `cfg`) on this round length, walk-forward: every `step` hours back through the record one `hours`-long window,
    each played with only what was known when it opened. medPct = the typical WINDOW (median of each window's typical card).
    `profitable` only with ≥ FWD_MIN windows, the typical window up AND ≥ 60% of windows up. Evidence from ~2 days, never a promise."""
    cfg = {'clock': int(clock), **(cfg or SNIPER)}
    step = step or hours / 2
    wins, off = [], 0.0
    while off + hours <= span:
        wins += [w for w in prep(paths, rounds, now, hours, (off,)) if w[3] or not cfg.get('edge')]   # record-backed setup: a window with no record learned before it is not judged
        off += step
    r = joint(wins, cfg, per=12, seed=3)
    if not r:
        return None
    pw = r.pop('perWindow')
    r.update(medPct=round(statistics.median(pw), 2), avgPct=round(sum(pw) / len(pw), 2), worstPct=round(min(pw), 1))
    ok = r['windows'] >= FWD_MIN and r['medPct'] > 0 and r['windowsUp'] >= r['windows'] * PROVEN_WINDOWS
    return {'key': key, 'name': name, 'why': why,
            'cfg': {k: str(v) for k, v in cfg.items() if k != 'clock'}, **r, 'hours': hours, 'profitable': bool(ok)}


def setups(paths, rounds, now, clock):
    """Every whole setup on this round length, each with its own walk-forward proof (best typical window first)."""
    out = []
    for key, name, why, cfg, hours in SETUPS:
        r = proven(paths, rounds, now, clock, cfg, hours, key=key, name=name, why=why)
        if r:
            out.append(r)
    return sorted(out, key=lambda r: (not r['profitable'], -r['medPct']))


def learn(results):
    """Trait scores: for every config value, median % (robust — one moonshot can't skew it), average % and share that ended up."""
    acc = {}
    for r in results or []:
        for trait, v in r['cfg'].items():
            acc.setdefault(trait, {}).setdefault(str(v), []).append(r['pct'])
    return {t: {v: {'n': len(ps), 'medPct': round(statistics.median(ps), 3), 'avgPct': round(sum(ps) / len(ps), 3),
                    'upPct': round(sum(1 for p in ps if p > 0) / len(ps) * 100, 1)} for v, ps in vals.items()} for t, vals in acc.items()}


RETIRE_SEC = 86400.0


def retire(score24, score6, prev=None, now=0.0, min_n=10):
    """☠ Settings that are LOSING are taken out of the brain's picks. A trait value is retired when its typical sim card lost money
    in BOTH windows (last 6h AND last 24h: median < 0 and fewer than half ended up, ≥ min_n sims each). It stays retired for a day,
    then is judged again on fresh sims (the sims keep testing every value, so a setting can earn its way back). A trait never loses
    ALL its values: when everything is negative the least-bad one stays (see `_alive`). → {trait: {value: {since, med6, med24}}}"""
    out = {}
    for t, vals in (score24 or {}).items():
        for v, s24 in vals.items():
            s6 = ((score6 or {}).get(t) or {}).get(v) or {}
            was = ((prev or {}).get(t) or {}).get(v)
            losing = (s24.get('n', 0) >= min_n and s6.get('n', 0) >= min_n and s24.get('medPct', 0) < 0 and s6.get('medPct', 0) < 0
                      and s24.get('upPct', 0) < 50 and s6.get('upPct', 0) < 50)
            if losing:
                out.setdefault(t, {})[v] = {'since': (was or {}).get('since') or now, 'med6': s6.get('medPct'), 'med24': s24.get('medPct')}
            elif was and now - float(was.get('since') or 0) < RETIRE_SEC:
                out.setdefault(t, {})[v] = was          # its day is not over: one good half-hour does not bring it back
    return out


def _alive(vals, retired_t):
    """A trait's values minus the retired ones — or all of them when that would leave nothing (the least-bad still has to be picked)."""
    keep = {v: s for v, s in vals.items() if v not in (retired_t or {})}
    return keep or vals


def best(score, min_n=10, retired=None):
    """The brain's pick: per trait the value whose TYPICAL card did best (median, then share up) over ≥ min_n sims."""
    out = {}
    for t, vals in (score or {}).items():
        ok = [(v, s) for v, s in _alive(vals, (retired or {}).get(t)).items() if s['n'] >= min_n] or [(v, s) for v, s in vals.items() if s['n'] >= min_n]
        if ok:
            v, s = max(ok, key=lambda vs: (vs[1].get('medPct', vs[1]['avgPct']), vs[1]['upPct']))
            out[t] = {'value': v, **s}
    return out


def by_clock(results, min_n=6, retired=None):
    """🕐 The brain's pick PER ROUND LENGTH: among the sim cards that played that clock, the trait values whose typical card did best.
    Every clock gets its own answer (a 5-min card should not run a 1-hour card's settings). `profitable` is only true when the
    TYPICAL card on that clock ended up — the pick is the least-bad config otherwise, and the screen says so."""
    out = {}
    for clock in sorted({str(r['cfg'].get('clock')) for r in results or []}, key=lambda v: float(v)):
        sub = [r for r in results if str(r['cfg'].get('clock')) == clock]
        if len(sub) < min_n * 2:
            continue
        pick = best({t: v for t, v in learn(sub).items() if t != 'clock'}, min_n, retired)
        sm = summary(sub)
        out[clock] = {'n': len(sub), 'medPct': sm.get('medianPct'), 'upPct': sm.get('upPct'), 'profitable': _num(sm.get('medianPct')) > 0,
                      'cfg': {t: p['value'] for t, p in pick.items()}, 'proof': {t: {'medPct': p.get('medPct'), 'n': p['n']} for t, p in pick.items()},
                      'strategies': strategies(sub, min_n, retired)}
    return out


STRATS = (('steady', '🛡 Steady', 'upPct', 'most sim cards ended up'),
          ('engine', '🧠 Engine pick', 'medPct', 'best typical card'),
          ('hunt', '🔥 Hunt', 'avgPct', 'biggest average — wilder swings'))


def strategies(sub, min_n=6, retired=None):
    """3 strategies for ONE round length, each built from what the sims on that clock actually did: per trait the value with the best
    share-ended-up (🛡), median (🧠) or average (🔥). Each carries its proof = every chosen setting's own sims on that clock.
    Never claims profit: `profitable` only when that proof's typical card ended up. Always 3 different configs."""
    score = {t: v for t, v in learn(sub).items() if t != 'clock'}
    out, seen = [], set()
    for key, name, metric, why in STRATS:
        pick = {}
        for t, vals in score.items():
            ok = sorted(((v, s) for v, s in _alive(vals, (retired or {}).get(t)).items() if s['n'] >= min_n), key=lambda vs: -vs[1].get(metric, 0)) \
                or sorted(((v, s) for v, s in vals.items() if s['n'] >= min_n), key=lambda vs: -vs[1].get(metric, 0))
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
