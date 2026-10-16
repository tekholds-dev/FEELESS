"""🎭 OFFICIAL COIN GUARD (owner, 2026-10-15: "insure there's no official coins … not buying a dup — there's a dup $STREAM in intake, the real STREAM
is at $20M"). Pure + tested.

A launch coin wearing the ticker of an ESTABLISHED coin is an impostor: the clone rule only compared coins on the agents' desk, and the real
coin (bigger than the owner's band) is never on it. Established = a protected major / xStock, any coin on the card, or any coin seen anywhere
in the feed with a live cap ≥ BIG_CAP. An impostor = same ticker family (taught_rules.family: GTA6 ↔ GTA 6 ↔ GT IV, SPACEX ↔ SPACEXAI), a
different mint, and a cap < 1 / CAP_RATIO of the real one (unknown cap = impostor of a major). It is dropped before Tally reads it."""
import taught_rules as _tr

BIG_CAP = 1_000_000.0
CAP_RATIO = 5.0


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def established(rows, majors=None, held=None, big=BIG_CAP):
    """{ticker: {sym, mint, cap}} — the biggest real coin per ticker (majors / held always count, cap ∞ when unknown)."""
    out = {}

    def put(sym, mint, cap):
        t = _tr.tick(sym)
        if len(t) < 2 or not mint:
            return
        if t not in out or cap > out[t]['cap']:
            out[t] = {'sym': sym, 'mint': mint, 'cap': cap}
    for mint, v in (majors or {}).items():
        put(v[0] if isinstance(v, (list, tuple)) else v, mint, float('inf'))
    for l in held or []:
        put(l.get('symbol'), l.get('mint'), max(_f(l.get('mcap')), BIG_CAP))
    for r in rows or []:
        if _f(r.get('mcap')) >= big:
            put(r.get('symbol'), r.get('mint'), _f(r.get('mcap')))
    return out


def check(row, est):
    """→ the reason this coin is an impostor of an established one, else None."""
    sym, mint = (row or {}).get('symbol'), (row or {}).get('mint')
    t = _tr.tick(sym)
    if len(t) < 2:
        return None
    cap = _f((row or {}).get('mcap'))
    for k, e in (est or {}).items():
        if e['mint'] == mint or k[:2] != t[:2] or not _tr.family(e['sym'], sym):
            continue
        if cap <= 0 or cap * CAP_RATIO < e['cap']:
            big = 'a protected major' if e['cap'] == float('inf') else f"${e['cap'] / 1e6:.1f}M"
            return f"🎭 impostor of the real ${e['sym']} ({big}) — same ticker, different coin"
    return None


def filter_rows(rows, est):
    """→ (kept, dropped[{symbol, mint, why}])."""
    keep, drop = [], []
    for r in rows or []:
        why = check(r, est)
        (drop.append({'symbol': r.get('symbol'), 'mint': r.get('mint'), 'why': why}) if why else keep.append(r))
    return keep, drop
