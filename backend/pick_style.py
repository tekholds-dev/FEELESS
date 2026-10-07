"""👤 Pick style — how the OWNER picks, learned from their own hand picks (pure, tested).

Every hand pick is noted with what the coin looked like at that moment (`snap`). `profile` turns the notes into a band per
feature (the middle 80% of the owner's picks + the median). `match` scores any live coin 0–100 by how many of those bands it
sits in and how close to the owner's typical value; `rank` puts the closest coins first. A paper card switched to this style
(`prime.humanTiers`) buys what the owner WOULD pick — it copies how they pick, never their trades, and never real money.
A description of a habit, not a claim that the habit wins: the card's own record says whether it does."""
import math

FEATS = (('ageH', 'age', True, 'h'), ('liq', 'pool', True, '$'), ('mcap', 'cap', True, '$'), ('vol1h', '1h volume', True, '$'),
         ('chg1h', '1h move', False, '%'), ('chg5m', '5m move', False, '%'), ('buyShare', 'buyers', False, '%'))
MIN_PICKS, KEEP, WINDOW = 8, 400, 120   # need 8 picks to speak; keep 400 notes; the style is the LAST 120 picks (habits drift)


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def snap(c):
    """What a coin looked like when it was picked → {feature: number} (missing readings left out), or None with under 3 readings."""
    out = {k: _f((c or {}).get(k)) for k, *_ in FEATS}
    out = {k: v for k, v in out.items() if v is not None and not (k in ('ageH', 'liq', 'mcap', 'vol1h') and v <= 0)}
    return out if len(out) >= 3 else None


def note(log, mint, symbol, feats, at):
    """Append one pick (the same coin within 10 minutes is one pick). Returns the new log, newest last, capped."""
    log = list(log or [])
    if not feats or any(x.get('mint') == mint and at - (x.get('at') or 0) < 600 for x in log[-20:]):
        return log
    return (log + [{'mint': mint, 'symbol': symbol, 'at': at, 'f': feats}])[-KEEP:]


def _q(xs, p):
    xs = sorted(xs); i = p * (len(xs) - 1); lo = int(i)
    return xs[lo] + (xs[min(lo + 1, len(xs) - 1)] - xs[lo]) * (i - lo)


def profile(log):
    """The owner's style from their last WINDOW picks → {'n', 'bands': {feat: {lo, mid, hi, n}}} or None under MIN_PICKS."""
    rows = [x.get('f') or {} for x in (log or [])[-WINDOW:]]
    if len(rows) < MIN_PICKS:
        return None
    bands = {}
    for k, _, is_log, _u in FEATS:
        xs = [r[k] for r in rows if _f(r.get(k)) is not None and (not is_log or r[k] > 0)]
        if len(xs) >= MIN_PICKS:
            bands[k] = {'lo': round(_q(xs, 0.1), 4), 'mid': round(_q(xs, 0.5), 4), 'hi': round(_q(xs, 0.9), 4), 'n': len(xs)}
    return {'n': len(rows), 'bands': bands} if len(bands) >= 3 else None


def match(c, prof):
    """How much a live coin looks like one of the owner's picks → 0–100 (None = cannot tell: no profile or under 3 shared readings).
    Inside a band = 60–100 by closeness to the owner's median; outside = 0–60 fading with distance (one band-width away = 0)."""
    if not prof:
        return None
    pts = []
    for k, _, is_log, _u in FEATS:
        b = prof['bands'].get(k); v = _f((c or {}).get(k))
        if not b or v is None or (is_log and v <= 0):
            continue
        t = (lambda x: math.log10(max(x, 1e-9))) if is_log else (lambda x: x)
        lo, mid, hi, x = t(b['lo']), t(b['mid']), t(b['hi']), t(v)
        width = max(hi - lo, 1e-6)
        if lo <= x <= hi:
            side = max((mid - lo) if x < mid else (hi - mid), 1e-6)
            pts.append(100 - 40 * min(1.0, abs(x - mid) / side))
        else:
            pts.append(max(0.0, 60 * (1 - (lo - x if x < lo else x - hi) / width)))
    return round(sum(pts) / len(pts)) if len(pts) >= 3 else None


def rank(cands, prof, floor=55):
    """Coins that look like the owner's picks first (best match first, tagged `styleMatch`), then the rest in their old order."""
    if not prof:
        return list(cands or [])
    scored = [({**c, 'styleMatch': m} if (m := match(c, prof)) is not None else c) for c in cands or []]
    hit = sorted((c for c in scored if (c.get('styleMatch') or 0) >= floor), key=lambda c: -c['styleMatch'])
    return hit + [c for c in scored if (c.get('styleMatch') or 0) < floor]


def _fmt(v, unit):
    if unit == '$':
        return f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v / 1e3:.0f}K" if v >= 1e3 else f"${v:.0f}"
    if unit == 'h':
        return f"{v * 60:.0f}m" if v < 1 else f"{v:.0f}h" if v < 48 else f"{v / 24:.0f}d"
    return f"{v:+.0f}%" if unit == '%' else f"{v:.0f}"


def words(prof):
    """The style in plain words, one short phrase per feature: 'age 40m–9h (typ. 3h)'."""
    if not prof:
        return []
    out = []
    for k, label, _lg, unit in FEATS:
        b = prof['bands'].get(k)
        if b:
            u = '' if k == 'buyShare' else unit
            f = (lambda v: f"{v:.0f}%") if k == 'buyShare' else (lambda v: _fmt(v, u))
            out.append(f"{label} {f(b['lo'])}–{f(b['hi'])} (typ. {f(b['mid'])})")
    return out
