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
                 ('floor', 'last resort'), ('duty', 'duty'), ('go', 'GO'), ('armed', 'ARMED'), ('ready', 'READY')):   # 🎯 armed / ⚡ ready: every real seat since 2026-10-12 came through one of these two — they all read 'other', so the door said nothing
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
    """Confirmed real exits with a real result, oldest first — ONE record per sale: older archives hold the same sale filed under
    several records of a coin that left the card and came back (12 of 77 on 2026-10-13); the newest record of a sale is the trade."""
    by = {}
    for i, p in enumerate(positions or []):
        if p.get('confirmed') and p.get('realPct') is not None:
            by[(p.get('exit') or {}).get('sig') or f'#{i}'] = p
    return sorted(by.values(), key=lambda p: _f(p.get('closedAt')))


def _cells(rows, base):
    cells = {}
    for fs, r in rows:
        for f in fs:
            if f != 'door:other':    # a door nobody named is every trade: it says nothing
                cells.setdefault(f, []).append(r)
    return {f: {'n': len(v), 'med': round(_st.median(v), 2), 'est': round((len(v) * _st.median(v) + SHRINK_K * base) / (len(v) + SHRINK_K), 2)}
            for f, v in cells.items() if len(v) >= MIN_N}


def learn(ts):
    """The table from these trades + its LINE: the median estimate of the trades it learned from. A coin under the line sits in the
    worse half of what this card has really bought (2026-10-13: the old veto was "3 points under the card's typical trade" — with a
    typical trade of −23% the worst buckets read −25.7 and NOTHING was ever skipped; ranked against each other, the worse half of the
    real trades made −38.8% avg vs −7.8% for the better half, each judged only on the trades before it)."""
    rows = [(pos_feats(p), _cap(p['realPct'])) for p in ts]
    if not rows:
        return {'base': 0.0, 'n': 0, 'cells': {}, 'line': 0.0}
    base = _st.median([r for _, r in rows])
    t = {'base': round(base, 2), 'n': len(rows), 'cells': _cells(rows, base)}
    t['line'] = round(_st.median([estimate(t, fs)[0] for fs, _ in rows]), 2)
    return t


def estimate(table, fs):
    """→ (estimate %, the bucket that drags it most) — the MEAN of the learned buckets the coin falls into (one bad bucket every coin
    shares no longer decides alone); no bucket = the typical trade."""
    cells = (table or {}).get('cells') or {}
    hits = [(cells[f]['est'], f) for f in fs or [] if f in cells]
    if not hits:
        return _f((table or {}).get('base')), None
    return round(sum(e for e, _ in hits) / len(hits), 2), min(hits)[1]


def veto_of(table):
    """The line a coin must clear: the median estimate of the card's own real trades (older tables: 3 points under the typical trade)."""
    t = table or {}
    return _f(t['line']) if t.get('line') is not None else _f(t.get('base')) - VETO_BELOW


PROOF_FROM = 30     # the first trade judged (it needs this many before it)
PROOF_LAST = 120    # … and only the newest trades are replayed (the table is rebuilt for each: keep it cheap)
PROOF_SKIP = 5


def proof(ts):
    """ROLLING walk-forward on real money: every trade from the 30th is judged by a table built ONLY from the trades before it —
    above that table's line = it would have been taken first, under = ranked last. Proven while the taken side beats the skipped side."""
    n = len(ts)
    if n < PROOF_FROM + PROOF_TAKE:
        return {'ok': False, 'why': f'{n} real trades — needs {PROOF_FROM + PROOF_TAKE} to prove itself', 'n': n}
    take, skip = [], []
    for i in range(max(PROOF_FROM, n - PROOF_LAST), n):
        tbl = learn(ts[:i])
        (take if estimate(tbl, pos_feats(ts[i]))[0] >= veto_of(tbl) else skip).append(_cap(ts[i]['realPct']))
    avg = lambda v: round(sum(v) / len(v), 2) if v else None
    med = lambda v: round(_st.median(v), 2) if v else None
    ok = len(take) >= PROOF_TAKE and len(skip) >= PROOF_SKIP and avg(take) - avg(skip) >= PROOF_EDGE
    return {'ok': ok, 'n': n, 'test': len(take) + len(skip), 'take': {'n': len(take), 'avg': avg(take), 'med': med(take)},
            'skip': {'n': len(skip), 'avg': avg(skip), 'med': med(skip)},
            'why': (f"on {len(take) + len(skip)} real trades, each judged only by the trades before it: ranked first {len(take)} at {avg(take):+.1f}% avg vs ranked last {len(skip)} at {avg(skip):+.1f}%"
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
    if est < veto_of(mem):
        return f"🧠 real-money memory: coins like this ({cell}) returned {est:+.1f}% on our real card — in the worse half, not bought while a better one is ready"
    return None


TWIN_MIN, TWIN_N = 3, 3   # a past trade is a "twin" when it shares at least 3 entry features with the coin on the table


def twins(trades_, fs, n=TWIN_N):
    """🧬 The model's few-shot memory: our own REAL trades that looked most like this coin at entry (most shared entry features first,
    then newest), each with how it really ended — "SYM −31% · R5 stop · held 4m". Real results only; under 3 shared features = no twin.
    One short line, or None. It costs no call: it rides the case the model is already asked about."""
    want = {f for f in fs or [] if not f.startswith('door:')}
    if len(want) < TWIN_MIN:
        return None
    hits = []
    for p in trades_ or []:
        k = len(want & set(pos_feats(p)))
        if k >= TWIN_MIN:
            hits.append((k, _f(p.get('closedAt')), p))
    if not hits:
        return None
    hits.sort(key=lambda h: (-h[0], -h[1]))
    out = []
    for _k, _t, p in hits[:n]:
        held = (_f(p.get('closedAt')) - _f(p.get('since'))) / 60 if p.get('since') else None
        out.append(f"{p.get('sym')} {_cap(p['realPct']):+.0f}% · {str(p.get('rule') or 'exit').split(':')[0][:26]}" + (f" · held {held:.0f}m" if held is not None and 0 <= held < 6000 else ''))
    won = sum(1 for h in hits if _cap(h[2]['realPct']) > 0)
    return (f"{len(hits)} of our real trades looked like this at entry, {won} won — " + ' | '.join(out))[:300]

