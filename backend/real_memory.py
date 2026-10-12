"""🧠 REAL-MONEY MEMORY (owner, 2026-10-12: "build the agent to be more accurate, learn from all real money losses and go again — paper
money won't prove it"). Pure + tested (`tests/test_real_memory.py`).

Every confirmed agent exit on the real card (the archive's positions: what the coin looked like at the buy → what it really returned) is
filed by its ENTRY features: chart structure, the chart's entry rule, the door / tier it came through, launch phase, launch class, age.
A candidate's estimate = the WORST shrunk median of the buckets it falls into (a bucket needs MIN_N trades; shrinkage pulls small buckets
toward the card's typical result). A candidate whose estimate is ≥ VETO_BELOW points under the card's typical real trade is not bought.

It is USED only while it proves itself WALK-FORWARD on real money: learn on the oldest 60% of trades, screen the newest 40% — the trades it
keeps must beat the trades it skips by ≥ PROOF_EDGE points on average, with ≥ PROOF_TAKE kept. It relearns on every pass, so each new real
loss moves the table. First check (2026-10-12, 264 trades): kept 30 of 106 unseen at −0.2% median / +1.0% avg vs skipped −2.5% / −3.5%.
Small samples — a filter that makes the card lose less, not a promise of profit.
"""
import statistics as _st

MIN_N = 4            # a bucket needs this many real trades before it says anything
SHRINK_K = 6         # shrink each bucket toward the typical trade by this many pseudo-trades
VETO_BELOW = 3.0     # estimate ≥ 3 points WORSE than the card's typical real trade = not bought (a bucket every coin falls into carries the typical result: never a veto)
CAP = 100.0          # a result is capped at ±100% (a drained-pool valuation once read +68,986,873%)
PROOF_SPLIT = 0.6
PROOF_TAKE = 10
PROOF_EDGE = 2.0


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def _cap(x):
    return max(-CAP, min(CAP, _f(x)))


def door(tag):
    """The door a coin came through, from its card tag (agent_seat writes it)."""
    t = str(tag or '')
    for k, w in (('A', 'A-tier'), ('B', 'B-tier'), ('C', 'C-tier'), ('avail', 'best available'), ('floor', 'floor'),
                 ('floor', 'last resort'), ('duty', 'duty'), ('go', 'GO')):
        if w in t:
            return k
    return 'other'


def age_band(h):
    if h is None:
        return None
    h = _f(h)
    return '<1h' if h < 1 else '<6h' if h < 6 else '<24h' if h < 24 else '1d+'


def feats(structure=None, rule=None, tag=None, phase=None, cls=None, age_h=None):
    """Entry features, the SAME for a filed position and a live candidate. None = not read (never a bucket)."""
    out = []
    if structure:
        out.append(f'struct:{structure}')
    if rule:
        out.append(f"rule:{str(rule).split(' ')[0].rstrip('e')}")
    out.append(f'door:{door(tag)}')
    if phase:
        out.append(f'phase:{phase}')
    if cls and cls != 'UNKNOWN':
        out.append(f'cls:{cls}')
    a = age_band(age_h)
    if a:
        out.append(f'age:{a}')
    return out


def pos_feats(p):
    th, li, la = p.get('thesis') or {}, p.get('li') or {}, p.get('launch') or {}
    return feats(th.get('structure'), th.get('triggerRule'), p.get('tag'), li.get('phase'), li.get('cls'), la.get('ageH') if la.get('ageH') is not None else li.get('ageH'))


def trades(positions):
    """Confirmed real exits with a real result, oldest first."""
    return sorted([p for p in positions or [] if p.get('confirmed') and p.get('realPct') is not None], key=lambda p: _f(p.get('closedAt')))


def learn(ts):
    rows = [(pos_feats(p), _cap(p['realPct'])) for p in ts]
    if not rows:
        return {'base': 0.0, 'n': 0, 'cells': {}}
    base = _st.median([r for _, r in rows])
    cells = {}
    for fs, r in rows:
        for f in fs:
            cells.setdefault(f, []).append(r)
    return {'base': round(base, 2), 'n': len(rows),
            'cells': {f: {'n': len(v), 'med': round(_st.median(v), 2), 'est': round((len(v) * _st.median(v) + SHRINK_K * base) / (len(v) + SHRINK_K), 2)}
                      for f, v in cells.items() if len(v) >= MIN_N}}


def estimate(table, fs):
    """→ (estimate %, the bucket that decided it) — the WORST learned bucket the coin falls into; no bucket = the typical trade."""
    cells = (table or {}).get('cells') or {}
    hits = [(cells[f]['est'], f) for f in fs or [] if f in cells]
    if not hits:
        return _f((table or {}).get('base')), None
    return min(hits)


def veto_of(table):
    return _f((table or {}).get('base')) - VETO_BELOW


def proof(ts):
    """Walk-forward on real money: learn on the oldest PROOF_SPLIT, screen the rest."""
    n = len(ts)
    cut = int(n * PROOF_SPLIT)
    if n < 30 or cut < 20:
        return {'ok': False, 'why': f'{n} real trades — needs 30 to prove itself', 'n': n}
    tbl = learn(ts[:cut])
    take, skip = [], []
    for p in ts[cut:]:
        (take if estimate(tbl, pos_feats(p))[0] > veto_of(tbl) else skip).append(_cap(p['realPct']))
    avg = lambda v: round(sum(v) / len(v), 2) if v else None
    med = lambda v: round(_st.median(v), 2) if v else None
    ok = len(take) >= PROOF_TAKE and bool(skip) and avg(take) - avg(skip) >= PROOF_EDGE
    return {'ok': ok, 'n': n, 'test': n - cut, 'take': {'n': len(take), 'avg': avg(take), 'med': med(take)},
            'skip': {'n': len(skip), 'avg': avg(skip), 'med': med(skip)},
            'why': (f"on {n - cut} unseen real trades: kept {len(take)} at {avg(take):+.1f}% avg vs skipped {len(skip)} at {avg(skip):+.1f}%"
                    if take and skip else 'nothing to compare yet')}


def build(positions):
    """One pass: the table from EVERY real trade + its walk-forward proof."""
    ts = trades(positions)
    t = learn(ts)
    return {**t, 'proof': proof(ts), 'veto': round(veto_of(t), 2)}


def judge(mem, fs):
    """→ None (may buy) or the reason it is not bought. Only while the memory has proven itself."""
    if not (mem or {}).get('proof', {}).get('ok'):
        return None
    est, cell = estimate(mem, fs)
    if est <= veto_of(mem):
        return f"🧠 real-money memory: {cell} trades returned {est:+.1f}% on our real card — not bought"
    return None
