"""🧠 PICK EDGE — what the runner board's OWN record says about a coin before it is bought.

Found 2026-10-05 by replaying 200 rounds (50h) of the board's picks against their recorded prices: the typical pick was
−26% three hours later, and the board's score was upside down (score ≥ 80 → −82%, score < 60 → about flat). The coins that
lost were the fresh, thin, hyper-traded ones the score loved; the coins that held were older, in deeper pools, with calm
turnover and ≥ 70% buyers. Tested out of sample (learn on the first 50–70% of rounds, judge the rest): the best-ranked
third ended about flat (+1…+3%), the worst third −72…−75%.

So the card engine no longer trusts a hand-written score. Every sim tick it LEARNS, from rounds whose outcome is already
known, the typical 3-hour result per feature bucket (age, pool, market cap, 1h / 5m move, buyers, turnover, stage) and
ranks candidates by it. It re-learns as the market changes, and it switches itself off when it stops separating winners
from losers (`proof`). A ranking from a short record — never a promise.

Pure: no I/O, no clock. `paths` = {mint: [[t, price], …]}, `rounds` = [{at, picks: [snapshot]}].
"""
import bisect
import chart_read as _chart
import statistics

HORIZON = 3 * 3600     # the outcome a pick is judged on
GAP = 20 * 60          # no price reading for 20 min = the coin left the feed
GONE = 0.18            # … and is valued 18% under its last reading (measured: 290 such coins averaged −18%)
DEDUPE = 3 * 3600      # one sample per coin per 3h: a coin that stays on the board is not counted again and again
CAP = 100.0            # one moonshot / rug counts for at most ±100%
SHRINK = 10            # a bucket with n samples moves the score by n / (n + SHRINK) of what it showed
MIN_SAMPLES = 60       # fewer judged picks than this = no table (the engine falls back to its old order)
MIN_SPREAD = 10.0      # out of sample the best third must beat the worst third by this many points, or the table is not used


def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _b(v, cuts):
    for i, c in enumerate(cuts):
        if v < c:
            return i
    return len(cuts)


# feature → (plain name, bucket labels, snapshot → bucket index or None when unknown)
FEATURES = {
    'age': ('age', ('under 1h', '1–6h', '6–12h', '12–24h', 'over 24h'), lambda c: None if c.get('ageH') is None else _b(_f(c['ageH']), (1, 6, 12, 24))),
    'pool': ('pool', ('under $25K', '$25–50K', '$50–100K', '$100–250K', 'over $250K'), lambda c: None if not _f(c.get('liq')) else _b(_f(c['liq']) / 1000, (25, 50, 100, 250))),
    'mcap': ('market cap', ('under $50K', '$50–150K', '$150–500K', '$0.5–2M', 'over $2M'), lambda c: None if not _f(c.get('mcap')) else _b(_f(c['mcap']) / 1000, (50, 150, 500, 2000))),
    'chg1h': ('1h move', ('under −10%', '−10–0%', '0–10%', '10–30%', '30–100%', 'over +100%'), lambda c: None if c.get('chg1h') is None else _b(_f(c['chg1h']), (-10, 0, 10, 30, 100))),
    'chg5m': ('5m move', ('under −3%', '−3–0%', '0–3%', '3–10%', 'over +10%'), lambda c: None if c.get('chg5m') is None else _b(_f(c['chg5m']), (-3, 0, 3, 10))),
    'buy': ('buyers', ('under 50%', '50–55%', '55–60%', '60–70%', 'over 70%'), lambda c: None if c.get('buyShare') is None else _b(_f(c['buyShare']), (50, 55, 60, 70))),
    'turn': ('1h volume ÷ pool', ('under 0.25×', '0.25–0.5×', '0.5–1×', '1–2×', 'over 2×'),
             lambda c: None if not _f(c.get('liq')) or c.get('vol1h') is None else _b(_f(c['vol1h']) / _f(c['liq']), (0.25, 0.5, 1, 2))),
    'stage': ('stage', ('on the curve', 'graduated'), lambda c: None if not c.get('stage') else (0 if c['stage'] == 'curve' else 1)),
    # 📈 the coin's own CHART (chart_read.py, from recorded prices before the pick). 2026-10-06 on 179 judged picks: a chart too
    # short to read −72% typical vs −12% readable · structure up +1% / range −14% / down −40% · top third of its range −2% vs
    # bottom third −31% · 5–15% under its high +26% (73% up, 11 picks) vs > 35% under −41%. Fair value gaps and sweeps did NOT
    # separate winners here (kept in the read, not in the table) — a read earns its place only by this proof.
    'cread': ('chart', ('too short to read', 'readable'), lambda c: None if c.get('cBars') is None else (1 if c['cBars'] else 0)),
    'cstruct': ('chart structure', ('down', 'range', 'up'), lambda c: {'down': 0, 'range': 1, 'up': 2}.get(c.get('cStruct'))),
    'cpos': ('place in its range', ('bottom third', 'middle', 'top third'), lambda c: None if c.get('cPos') is None else _b(_f(c['cPos']), (0.33, 0.66))),
    'cpull': ('pullback from its high', ('under 5%', '5–15%', '15–35%', 'over 35%'), lambda c: None if c.get('cPull') is None else _b(_f(c['cPull']), (5, 15, 35))),
}


def _index(paths):
    out = {}
    for m, pts in (paths or {}).items():
        ps = sorted((_f(t), _f(p)) for t, p in pts or [] if _f(p) > 0)
        if ps:
            out[m] = ([t for t, _ in ps], [p for _, p in ps])
    return out


def _px(ix, m, t):
    """(last price at or before t, seconds since that reading) or (None, None)."""
    ts, xs = ix[m]
    i = bisect.bisect_right(ts, t) - 1
    return (xs[i], t - ts[i]) if i >= 0 else (None, None)


def samples(rounds, paths, upto, horizon=HORIZON):
    """Every pick whose outcome is KNOWN by `upto` → [{at, mint, snap, pct}] in time order. pct = price `horizon` later against the
    price when it was picked; a coin that left the feed by then is valued GONE under its last reading (never dropped — the dead
    ones are the lesson). One sample per coin per DEDUPE."""
    ix, out, last = _index(paths), [], {}
    for r in sorted(rounds or [], key=lambda r: _f(r.get('at'))):
        t0 = _f(r.get('at'))
        if t0 + horizon > upto:
            break
        for p in r.get('picks') or []:
            m = p.get('mint')
            if not m or m not in ix or t0 - last.get(m, -1e18) < DEDUPE:
                continue
            e, gap = _px(ix, m, t0)
            if not e or gap > GAP:
                continue
            x, g = _px(ix, m, t0 + horizon)
            last[m] = t0
            p = {**p, **_chart.keys(list(zip(*ix[m])), t0)}   # 📈 what its chart looked like when it was picked (only readings before t0 are used)
            out.append({'at': t0, 'mint': m, 'snap': p, 'pct': round(max(-CAP, min(CAP, (x * ((1 - GONE) if g > GAP else 1.0) / e - 1) * 100)), 2)})
    return out


def learn(rows):
    """→ {n, base, f: {feature: {bucket: {n, med}}}}: the typical outcome overall and per feature bucket. None under MIN_SAMPLES."""
    ys = [r['pct'] for r in rows or []]
    if len(ys) < MIN_SAMPLES:
        return None
    t = {'n': len(ys), 'base': round(statistics.median(ys), 2), 'f': {}}
    for k, (_, _, fn) in FEATURES.items():
        g = {}
        for r in rows:
            b = fn(r['snap'])
            if b is not None:
                g.setdefault(str(b), []).append(r['pct'])
        t['f'][k] = {b: {'n': len(v), 'med': round(statistics.median(v), 2)} for b, v in g.items()}
    return t


def score(c, table):
    """The record's estimate for this coin (≈ typical % three hours after buying it), or None without a table. Each feature moves
    the estimate away from the overall typical result by what its bucket showed, shrunk when the bucket is thin; unknown
    features are left out. Use it to RANK; treat the level as rough."""
    if not table:
        return None
    cs = []
    for k, (_, _, fn) in FEATURES.items():
        b = fn(c or {})
        cell = (table['f'].get(k) or {}).get(str(b)) if b is not None else None
        if cell:
            cs.append((cell['med'] - table['base']) * cell['n'] / (cell['n'] + SHRINK))
    return round(table['base'] + (sum(cs) / len(cs) ** 0.5 if cs else 0.0), 2)


def proof(rows, split=0.6):
    """Does the table actually separate winners from losers on picks it has NOT seen? Learn on the first `split` of the record,
    rank the rest, compare the best-ranked third with the worst. → {ok, n, top: {n, medPct, upPct}, bottom: {…}, spread} or
    {ok: False}. `ok` needs the top third to beat the bottom third by MIN_SPREAD points."""
    rows = list(rows or [])
    cut = int(len(rows) * split)
    table = learn(rows[:cut])
    test = rows[cut:]
    if not table or len(test) < 15:
        return {'ok': False, 'n': len(test)}
    ranked = sorted(test, key=lambda r: -(score(r['snap'], table) or 0))
    k = len(ranked) // 3
    side = lambda xs: {'n': len(xs), 'medPct': round(statistics.median(x['pct'] for x in xs), 1), 'upPct': round(sum(1 for x in xs if x['pct'] > 3) / len(xs) * 100)}
    top, bottom = side(ranked[:k]), side(ranked[-k:])
    spread = round(top['medPct'] - bottom['medPct'], 1)
    return {'ok': spread >= MIN_SPREAD, 'n': len(test), 'top': top, 'bottom': bottom, 'spread': spread}


def build(rounds, paths, now):
    """One call for the service: the table from everything judged so far + its out-of-sample proof + the plainest findings.
    → {table, proof, n, at, best: [...], worst: [...]} (table None when the record is too short OR the proof fails: no ranking, no gate)."""
    rows = samples(rounds, paths, now)
    pr = proof(rows)
    table = learn(rows) if pr.get('ok') else None
    cells = []
    full = learn(rows)
    for k, (name, labels, _) in FEATURES.items():
        for b, c in ((full or {}).get('f') or {}).get(k, {}).items():
            if c['n'] >= 12:
                cells.append({'feature': name, 'bucket': labels[int(b)], 'n': c['n'], 'medPct': c['med']})
    cells.sort(key=lambda c: c['medPct'])
    return {'table': table, 'proof': pr, 'n': len(rows), 'at': now, 'base': (full or {}).get('base'), 'worst': cells[:4], 'best': cells[-4:][::-1]}


def rank(rows, table):
    """Candidates best-estimate first (stable; rows without an estimate keep their order after the scored ones). Adds `edge`."""
    if not table:
        return list(rows or [])
    scored = [({**r, 'edge': score(r, table)}) for r in rows or []]
    return [r for _, _, r in sorted(((-(r['edge'] if r['edge'] is not None else -1e9), i, r) for i, r in enumerate(scored)), key=lambda t: (t[0], t[1]))]


def gate(rows, table, floor=0.0):
    """Real money: only coins the record does not expect to LOSE (estimate ≥ floor). No table = no gate (every row passes).
    Coins flagged `newMajor` / `trenchOnly` are judged by their own rules (majors by depth; trench is the owner's explicit choice)."""
    if not table:
        return list(rows or [])
    return [r for r in rows or [] if r.get('newMajor') or r.get('trenchOnly') or (score(r, table) or -1e9) >= floor]
