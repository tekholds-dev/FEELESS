"""🤵 THE CONSIGLIERE — Reaper's partner agent (pure, tested `tests/test_consigliere.py`). Owner, 2026-10-18: "Reaper and his partner should
study my holds — why I wait for the spike at the germ floor … no strat fits all: figure out each coin and only use what's been working".

For each kind of coin (`bucket`: bought near its germ floor, or not) it replays two plans on every real closed trade — the trade's own
price path plus the 30 minutes after the sale (after_path) — and picks the one with the better record:
  · reaper  = what Reaper really did
  · patient = hold until the coin's own stop, or bank at a spike (+20 / +30 / +50 — the best of the three)
The patient plan wins a bucket only with ≥ MIN_N trades, an average ≥ EDGE points better than Reaper, and the NEWEST trades agreeing — so a
plan that stops working falls back to Reaper by itself. Never a buy, never a wider stop: it only decides whether Reaper's SOFT exits wait."""
import statistics

SPIKES = (20.0, 30.0, 50.0)
MIN_N = 20
EDGE = 1.0
GERM_NEAR = 15.0


from fnum import plain as _f  # noqa: E402


def bucket(germ_dist):
    """'germ' = bought within GERM_NEAR % of its germ floor, else 'other'."""
    return 'germ' if germ_dist is not None and abs(_f(germ_dist)) <= GERM_NEAR else 'other'


def bucket_of_pos(p):
    th = p.get('thesis') or {}
    g = th.get('germDist')
    if g is None:
        e = ((p.get('snaps') or {}).get('entry') or {}).get('germ')
        g = e if isinstance(e, (int, float)) else None
    return bucket(g)


def patient(path, stop, spike):
    """Hold until the stop or the spike; else where the whole move ended."""
    for v in path:
        if v <= -abs(_f(stop) or 15.0):
            return v
        if v >= spike:
            return spike
    return path[-1] if path else 0.0


def plans(positions, after, key_of, extra_spikes=()):
    """→ {bucket: {'plan': 'patient' | 'reaper', 'spike', 'n', 'patient', 'reaper', 'gain', 'newGain', 'why'}} from REAL closed trades."""
    rows = {}
    for p in sorted(positions or [], key=lambda p: _f(p.get('closedAt'))):
        if p.get('g4') or p.get('realPct') is None:
            continue
        aft = (after or {}).get(key_of(p))
        path = [x for x in (p.get('path') or []) if isinstance(x, (int, float))]
        if not aft or len(path) < 2:
            continue
        rows.setdefault(bucket_of_pos(p), []).append((path + list(aft), _f((p.get('thesis') or {}).get('stopPct')) or 15.0, _f(p['realPct'])))
    out = {}
    for b, v in rows.items():
        base = [x[2] for x in v]
        best = None
        for sp in tuple(SPIKES) + tuple(x for x in extra_spikes or () if x and x not in SPIKES):   # 🧠 + the take line OSSY / G4 really use
            r = [patient(path, stop, sp) for path, stop, _ in v]
            avg = sum(r) / len(r)
            if best is None or avg > best[1]:
                best = (sp, avg, r)
        sp, avg, r = best
        h = max(1, len(v) * 6 // 10)
        gain = avg - sum(base) / len(base)
        new_gain = (sum(r[h:]) - sum(base[h:])) / max(1, len(v) - h)
        win = len(v) >= MIN_N and gain >= EDGE and new_gain >= 0
        out[b] = {'plan': 'patient' if win else 'reaper', 'spike': sp, 'n': len(v), 'patient': round(avg, 1), 'reaper': round(sum(base) / len(base), 1),
                  'patientMed': round(statistics.median(r), 1), 'reaperMed': round(statistics.median(base), 1), 'gain': round(gain, 1), 'newGain': round(new_gain, 1),
                  'why': (f"patient (hold to its stop or +{sp:g}%) {avg:+.1f} avg vs Reaper {sum(base) / len(base):+.1f} on {len(v)} real {b} trades"
                          + ('' if win else ' — not proven, Reaper decides'))}
    return out
