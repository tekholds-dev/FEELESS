"""🪑 THE FOUR-SEAT OPERATING MODEL — pure, deterministic, tested (`tests/test_seat_ops.py`). No network, no wallet, no order: every
function here ranks, labels or explains something the existing path (Trigger → Devil → Warden → keeper · Reaper) then decides.

  velocity        P/L VELOCITY from REAL valuation reads of a held seat: ACCELERATING · STABLE · STALLING · REVERSING (UNKNOWN until
                  enough reads exist — nothing is guessed, nothing is predicted)
  extension       may a WINNER earn one more 5-minute window past its base hold? (every extension re-earned, bounded by the thesis max)
  chart_quality   one word for the chart a decision stands on: CLEAN · EARLY · CHOPPY · EXTENDED · UNSTABLE · COLLAPSING · INVALID
  score           the seat score (0–100) a case or a held seat is RANKED by — hand-set weights, every part named; it orders coins
                  that already passed every gate, it never creates an entry
  bench           the ranked challengers behind the four seats (ready = cleared every desk AND the newest live check)
  seat_board      what each seat is doing THIS cycle: result · decided-at · market-input-at · velocity · score · best challenger · margin
  summary         OCCUPANCY x/4 · TARGET · BENCH · BUYS USED / LEFT · CASH
"""
import agents as _ag

_f = _ag._f

# ── 📈 P/L VELOCITY ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
VELOCITY = ('ACCELERATING', 'STABLE', 'STALLING', 'REVERSING')
VEL_EVERY = 10.0        # a new valuation read is kept at most this often (seconds)
VEL_KEEP_SEC = 900.0    # … for this long (15 min)
VEL_WIN = 180.0         # recent window = the last 3 minutes, prior window = the 3 before that
VEL_MIN_N = 3           # fewer real reads than this → UNKNOWN
VEL_MIN_SPAN = 90.0     # … or reads spanning less than this → UNKNOWN
VEL_EPS = 0.5           # % points per minute that count as movement (smaller = flat)


def vel_note(hist, now, pct, every=VEL_EVERY):
    """Keep one real valuation read: [[t, pct], …] (oldest first), at most one per `every` seconds, the last VEL_KEEP_SEC only."""
    h = [list(p) for p in (hist or []) if now - _f(p[0]) <= VEL_KEEP_SEC]
    if pct is None:
        return h
    if h and now - _f(h[-1][0]) < every:
        h[-1] = [h[-1][0], round(_f(pct), 3)] if now - _f(h[-1][0]) < 1 else h[-1]
        return h
    return h + [[now, round(_f(pct), 3)]]


def _at(h, t):
    """The read nearest to time t (at or before it if one exists)."""
    before = [p for p in h if _f(p[0]) <= t]
    return before[-1] if before else h[0]


def velocity(hist, now):
    """→ {state, slope (pts/min, last 3 min), prior (pts/min, the 3 min before), n, span, why}. From REAL reads only:
      REVERSING    the recent slope is falling (≤ −VEL_EPS) — giving back, or losing faster
      ACCELERATING the recent slope is rising (≥ VEL_EPS) and at least as fast as before (or twice the noise line)
      STALLING     it WAS rising and has gone flat / is slowing to under half its prior pace
      STABLE       flat both windows
      UNKNOWN      under VEL_MIN_N reads or a span under VEL_MIN_SPAN"""
    h = [p for p in (hist or []) if p and p[1] is not None]
    if len(h) < VEL_MIN_N or _f(h[-1][0]) - _f(h[0][0]) < VEL_MIN_SPAN:
        return {'state': 'UNKNOWN', 'slope': None, 'prior': None, 'n': len(h), 'span': round(_f(h[-1][0]) - _f(h[0][0])) if h else 0,
                'why': f'{len(h)} real read{"s" if len(h) != 1 else ""} so far — velocity needs {VEL_MIN_N} over {VEL_MIN_SPAN:g}s'}
    t1, p1 = _f(h[-1][0]), _f(h[-1][1])
    a = _at(h, t1 - VEL_WIN)
    ta, pa = _f(a[0]), _f(a[1])
    slope = (p1 - pa) / max(1e-9, (t1 - ta) / 60)
    b = _at(h, ta - VEL_WIN)
    tb, pb = _f(b[0]), _f(b[1])
    prior = (pa - pb) / ((ta - tb) / 60) if ta - tb >= 30 else None
    base = {'slope': round(slope, 2), 'prior': None if prior is None else round(prior, 2), 'n': len(h), 'span': round(t1 - _f(h[0][0])), 'pct': round(p1, 2)}
    if slope <= -VEL_EPS:
        return {**base, 'state': 'REVERSING', 'why': f'{slope:+.1f} pts/min over the last {round((t1 - ta) / 60, 1)} min' + (f' (was {prior:+.1f})' if prior is not None else '')}
    if slope >= VEL_EPS and (prior is None or slope >= prior or slope >= 2 * VEL_EPS):
        return {**base, 'state': 'ACCELERATING', 'why': f'{slope:+.1f} pts/min' + (f' vs {prior:+.1f} before' if prior is not None else '')}
    if prior is not None and prior >= VEL_EPS and slope < max(VEL_EPS, prior / 2):
        return {**base, 'state': 'STALLING', 'why': f'was {prior:+.1f} pts/min, now {slope:+.1f}'}
    return {**base, 'state': 'STABLE', 'why': f'{slope:+.1f} pts/min — flat'}


# ── ⏳ WINNERS EARN MORE TIME ────────────────────────────────────────────────────────────────────────────────────────────────────
BASE_WINDOWS = 6        # a thesis that still stands keeps its seat this many 5-minute windows (30 min — the card's record: 30+ min holds paid)
EXT_LIQ_MIN = 0.75      # … past that only a WINNER earns more: pool ≥ 75% of its entry depth …


def extension(pct, vel, verdict, liq_ratio=None, quality=None, challenger_margin=None, need=None):
    """May a position past its base windows EARN one more 5-minute window? Every line must hold: P/L positive · velocity ACCELERATING or
    STABLE (a stalling / reversing winner is compared, not protected) · thesis valid · pool healthy · the chart is not collapsing ·
    no materially better challenger. → (earned: bool, why)"""
    v = (vel or {}).get('state') if isinstance(vel, dict) else vel
    if _f(pct) <= 0:
        return False, f'{_f(pct):+.1f}% — only a winner earns extra time'
    if v not in ('ACCELERATING', 'STABLE'):
        return False, f'P/L velocity {v or "UNKNOWN"} — a winner that is not gaining or holding is not given more time'
    if verdict != 'valid':
        return False, f'thesis {verdict or "unread"}'
    if liq_ratio is not None and _f(liq_ratio) < EXT_LIQ_MIN:
        return False, f'pool at {round(_f(liq_ratio) * 100)}% of its entry depth'
    if quality in ('COLLAPSING', 'INVALID'):
        return False, f'chart {quality}'
    if challenger_margin is not None and need is not None and _f(challenger_margin) >= _f(need):
        return False, f'a challenger outscores it by {_f(challenger_margin):.0f} (≥ {_f(need):.0f})'
    return True, f'{_f(pct):+.1f}% and {v.lower()} · thesis valid · pool healthy — earned +5 min'


# ── 📊 CHART QUALITY ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
QUALITY = ('CLEAN', 'EARLY', 'CHOPPY', 'EXTENDED', 'UNSTABLE', 'COLLAPSING', 'INVALID')
QUALITY_PTS = {'CLEAN': 20, 'EARLY': 12, 'CHOPPY': 5, 'EXTENDED': 4, 'UNSTABLE': 3, 'COLLAPSING': 0, 'INVALID': 0, None: 6}
QUALITY_SIZE = {'CHOPPY': 0.75, 'EXTENDED': 0.5, 'UNSTABLE': 0.5}   # the Warden may shrink a seat on these — never grow one
_COLLAPSE = ('LIQUIDITY FAILURE', 'DOWNTREND', 'FAILED BREAKOUT', 'DISTRIBUTION')


def chart_quality(chart):
    """One word for a compact chart (chart_intel.compact) → (word | None, why). EARLY is a newborn with few real candles — never read as
    COLLAPSING. No chart = None (unknown, not bad)."""
    ch = chart or {}
    st, q = ch.get('state'), ch.get('q') or {}
    if not st or st == 'UNKNOWN':
        return None, 'no chart read this pass' if not st else 'structure unknown — not judged'
    if st == 'BOT LADDER':
        return 'INVALID', 'BOT LADDER: one bot trading it with itself'
    if st == 'DATA INVALID' or (q and q.get('readOk') is False):
        return 'INVALID', f"market data {q.get('state') or 'failed its integrity check'}"
    if st == 'EARLY' or q.get('state') == 'LIMITED_HISTORY':
        if st in _COLLAPSE:
            return 'COLLAPSING', f'{st} on a newborn'
        return 'EARLY', f"{ch.get('n') or 'a few'} real candles — limited history, not bad data"
    if st in _COLLAPSE:
        return 'COLLAPSING', st
    ext, chop, trend = ch.get('ext'), ch.get('chop'), ch.get('trend')
    if st == 'PARABOLIC' or (ext is not None and _f(ext) >= 70):
        return 'EXTENDED', f"{st}, extension {_f(ext):.0f}/100" if ext is not None else st
    if st == 'CHOP' or (chop is not None and _f(chop) >= 60):
        return 'CHOPPY', f"{st}, chop {_f(chop):.0f}/100" if chop is not None else st
    risk = (ch.get('risk') or [1.0])[0]
    if _f(risk) <= 0.5 and st not in ('STRONG UPTREND', 'UPTREND', 'PULLBACK IN UPTREND', 'CONFIRMED BREAKOUT'):
        return 'UNSTABLE', f"{st}: {(ch.get('risk') or [None, ''])[1]}"
    if st in ('STRONG UPTREND', 'UPTREND', 'PULLBACK IN UPTREND', 'CONFIRMED BREAKOUT', 'ACCUMULATION', 'COMPRESSION', 'BREAKOUT ATTEMPT') and (trend is None or _f(trend) >= 40):
        return 'CLEAN', st
    return 'CHOPPY' if st == 'RANGE' else 'UNSTABLE', st


# ── 🏅 THE SEAT SCORE ────────────────────────────────────────────────────────────────────────────────────────────────────────────
SCORE_MARGIN = {'agents': 15.0, 'normal': 15.0, 'conservative': 25.0, 'aggressive': 8.0}   # superiority a challenger needs over a held seat
ACCEL_EXTRA = 15.0      # … and this much more over a position whose P/L is ACCELERATING
VEL_PTS = {'ACCELERATING': 10, 'STABLE': 3, 'STALLING': -3, 'REVERSING': -10, 'UNKNOWN': 0}
THESIS_PTS = {'valid': 5, 'weak': -5, 'invalid': -15}


# ── 🧭 WHAT THE SEATS HUNT, BY PHASE (owner, 2026-10-11: "new coins mainly — trench — majors etc once we broke even and doubled or
# playing safe after good profit") ───────────────────────────────────────────────────────────────────────────────────────────────
UNIVERSE_SAFE_X = 2.0     # ≥ 2× everything put in → majors first (play safe)
YOUNG_H, OLD_H = 6.0, 72.0
MAJOR_AGE_H, MAJOR_LIQ = 168.0, 250_000.0


def universe(money):
    """→ (universe, why). 'trench' while the real card is under what was put in (RECOVERY: new coins first) · 'mixed' past breakeven ·
    'majors' at ≥ UNIVERSE_SAFE_X × put-in (protect it). Unknown money = 'mixed'. A TILT on the seat score only — no check moves."""
    v, p = _f((money or {}).get('value')), _f((money or {}).get('putIn'))
    if v <= 0 or p <= 0:
        return 'mixed', 'no money reading — no phase tilt'
    if v < p:
        return 'trench', f"RECOVERY ${v:.2f} of ${p:.2f} put in — new / trench coins first"
    if v >= UNIVERSE_SAFE_X * p:
        return 'majors', f"{v / p:.1f}× what was put in — majors first, play safe"
    return 'mixed', f"past breakeven ({v / p:.2f}×) — new coins and majors both"


def universe_pts(row, uni):
    """The phase tilt for one row → (pts, why) or None."""
    v, n = (row or {}).get('vitals') or {}, (row or {}).get('nums') or {}
    age, liq = v.get('ageH'), _f(n.get('liq') or v.get('liq'))
    if age is None or uni not in ('trench', 'majors'):
        return None
    major = _f(age) >= MAJOR_AGE_H and liq >= MAJOR_LIQ
    if uni == 'trench':
        if _f(age) <= YOUNG_H:
            return 12.0, f"{_f(age):.1f}h old — recovery hunts new coins"
        if _f(age) <= 24:
            return 6.0, f"{_f(age):.0f}h old — still young"
        if major or _f(age) >= OLD_H:
            return -10.0, f"{_f(age) / 24:.0f}d old — recovery hunts new coins, majors come after breakeven"
        return None
    if major:
        return 15.0, f"established ({_f(age) / 24:.0f}d, ${liq / 1000:.0f}K pool) — 2× reached, play safe"
    if _f(age) < 24:
        return -15.0, f"{_f(age):.1f}h old — 2× reached: no trench risk"
    return None


def score(row, ctx=None):
    """The seat score of one case row (0–100) with every part named → {score, parts: [[name, pts, why]], quality}. Hand-set weights (labelled
    so on the page): it RANKS coins that already passed every gate — it never makes an entry, never loosens a check.
    ctx = {pxAge (s), seen (the coin's memory: reject without a material change), lost (left at a loss on real money lately),
           vel (velocity of a HELD seat), verdict (its thesis), social (research packet)}"""
    r, c = row or {}, ctx or {}
    n, v = r.get('nums') or {}, r.get('vitals') or {}
    parts = []
    add = lambda name, pts, why: parts.append([name, round(pts, 1), why])
    lean = _f((r.get('why') or {}).get('lean'))
    add('read', 20 * max(0.0, min(1.0, lean / 3)), f'Sherlock lean {lean:+.1f}')
    d5, pace = n.get('d5'), n.get('pace')
    mom = 0.0 if d5 is None else max(0.0, min(10.0, _f(d5) / 1.2))
    mom += 0.0 if pace is None else max(0.0, min(5.0, (_f(pace) - 1) * 2.5))
    add('momentum', mom, f"{_f(d5):+.1f}% 5m · pace ×{_f(pace):.1f}" if d5 is not None else 'no 5-min read')
    qw, qwhy = chart_quality(r.get('chart'))
    add('structure', QUALITY_PTS.get(qw, 6), f'{qw or "UNKNOWN"} — {qwhy}')
    liq = _f(n.get('liq') or v.get('liq'))
    lp = 0.0 if liq < _ag.CONTROL_MIN_LIQ else 6 + min(9.0, 9 * (liq - _ag.CONTROL_MIN_LIQ) / 480_000)
    liqd = n.get('liqD')
    lp += 0 if liqd is None else 3 if _f(liqd) >= 5 else -5 if _f(liqd) <= -20 else 0
    add('liquidity', lp, f'pool ${liq / 1000:.0f}K' + (f' ({_f(liqd):+.0f}% since first read)' if liqd is not None else ''))
    safe = v.get('safe')
    hp = 10 if safe is True else 3 if safe is None else 0
    hp += 3 if safe is True and v.get('top10') is not None and _f(v['top10']) <= 25 else 0
    add('holders', hp, 'holder scan passed' + (f" · top-10 {_f(v['top10']):.0f}%" if v.get('top10') is not None else '') if safe is True else 'holders not scanned yet' if safe is None else 'failed the holder scan')
    age = c.get('pxAge')
    q = (r.get('chart') or {}).get('q') or {}
    fp = (5 if age is not None and _f(age) <= 30 else 3 if age is not None and _f(age) <= 120 else 0) + (5 if q.get('enterOk') else 0)
    add('live data', fp, (f'price {round(_f(age))}s old' if age is not None else 'price age unknown') + (' · ENTER-grade data' if q.get('enterOk') else ''))
    cross = ((c.get('social') or r.get('social') or {}).get('cross') or {})
    if cross.get('conflict'):
        add('identity', -15, 'the website shows a different contract')
    elif cross.get('confidence') is not None and _f(cross['confidence']) >= 70:
        add('identity', 5, f"identity confidence {_f(cross['confidence']):.0f}/100")
    lc = r.get('launch') or {}
    if lc.get('graduated') or lc.get('type') in ('migrated', 'established pool'):
        add('launch', 2, f"{lc.get('pad')} · {lc.get('type')}")
    e = c.get('seen') or {}
    if e.get('reject') and not (e.get('changed') and _f(e.get('changed')) > _f(e.get('review'))):
        add('stale reject', -10, f"rejected ({e['reject']}) with nothing new since")
    vol5 = _f(v.get('vol5m') or r.get('vol5m'))
    if (pace is not None and _f(pace) < 0.3) and vol5 < 500:
        add('dead volume', -10, f'${vol5:,.0f} in 5 min')
    if c.get('lost'):
        add('failed setup', -15, 'left the card at a loss lately')
    if age is not None and _f(age) > 180:
        add('stale snapshot', -5, f'price {round(_f(age))}s old')
    if c.get('vel'):
        st = (c['vel'] or {}).get('state') or 'UNKNOWN'
        add('velocity', VEL_PTS.get(st, 0), f"P/L {st.lower()}" + (f" ({c['vel'].get('why')})" if c['vel'].get('why') else ''))
    if c.get('verdict') in THESIS_PTS:
        add('thesis', THESIS_PTS[c['verdict']], f"thesis {c['verdict']}")
    up_ = universe_pts(r, c.get('universe'))
    if up_:
        add('phase', up_[0], up_[1])
    return {'score': round(max(0.0, min(100.0, sum(p[1] for p in parts))), 1), 'parts': parts, 'quality': qw}


def margin_need(mode, vel=None, pnl=None):
    """The score margin a challenger needs over a held seat: by switching mode, + ACCEL_EXTRA when that seat's P/L is accelerating."""
    need = SCORE_MARGIN.get(mode or 'agents', SCORE_MARGIN['agents'])
    st = (vel or {}).get('state') if isinstance(vel, dict) else vel
    return need + (ACCEL_EXTRA if st == 'ACCELERATING' else 0.0)


# ── 🪑 THE BENCH ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
BENCH_N = 20
NEAR = ('chart', 'data', 'scan')   # one of these the only failing check = NEAR READY (the entry moment / data / holder scan is still coming)


def bench(cases, scores, on=(), ready=None, cooled=(), n=BENCH_N):
    """The ranked challengers behind the seats (never a coin already on the card). `cases` = agents.investigate rows · `scores` {mint: score
    dict} · `ready` {mint: (ok, why)} = this tick's live check (None = not checked) · `cooled` = mints on the rebuy cooldown.
    Cleared + live-ok first, then score. → [{rank, mint, symbol, pair, score, ready, block, lean, quality, go}]"""
    out = []
    for c in cases or []:
        m = c.get('mint')
        if not m or m in set(on or ()):
            continue
        sc = (scores or {}).get(m) or {}
        lc = (ready or {}).get(m)
        fail = next((k for k in c.get('checks') or [] if not k[1]), None)
        fails = [k for k in c.get('checks') or [] if not k[1]]
        if m in set(cooled or ()):
            ok, block = False, 'rebuy cooldown'
        elif fail:
            ok, block = False, fail[2]
        elif lc is not None and not lc[0]:
            ok, block = False, f'live check: {lc[1]}'
        else:
            ok, block = True, None
        near = (not ok) and m not in set(cooled or ()) and ((len(fails) == 1 and fails[0][0] in NEAR) or (not fails and lc is not None and not lc[0]))
        out.append({'mint': m, 'symbol': c.get('symbol'), 'pair': c.get('pair'), 'score': sc.get('score'), 'ready': ok, 'near': bool(near), 'block': block,
                    'lean': c.get('lean'), 'quality': sc.get('quality'), 'go': bool(c.get('go'))})
    out.sort(key=lambda b: (not b['ready'], not b['near'], -_f(b['score'])))
    return [{**b, 'rank': i + 1} for i, b in enumerate(out[:n])]


# ── 🧾 EVERY SEAT, EVERY CYCLE ──────────────────────────────────────────────────────────────────────────────────────────────────
RESULTS = ('HOLD', 'PROTECT', 'TAKE', 'EXIT', 'SWAP')


def seat_result(report, decision):
    """One fresh word per held seat: SWAP (a switch was decided) · TAKE / EXIT (a pull: green / red) · PROTECT · HOLD."""
    d, r = decision or {}, report or {}
    if d.get('action') == 'swap':
        return 'SWAP'
    if r.get('deferred') and d.get('action') != 'pull':   # Reaper's time exit waits for a free buy: the seat keeps its coin
        return 'HOLD'
    if d.get('action') == 'pull' or r.get('action') == 'pull':
        return 'TAKE' if _f(r.get('pct', d.get('pct'))) >= 0 and r.get('state') != 'EXIT INVALIDATED' else 'EXIT'
    if r.get('state') == 'TAKE':
        return 'TAKE'
    if r.get('state') == 'PROTECT':
        return 'PROTECT'
    return 'HOLD'


def seat_board(seats, reports, decisions, vels, scores, bench_, tests, now, decided_at, input_at, seat=None, mode='agents'):
    """What every seat is doing THIS cycle (display — manage / Reaper / fill_plan decided). Held: coin · P/L · velocity · thesis · held ·
    protection · score · best challenger · margin · result + decided-at + market-input-at. Empty: next candidate · ready · block · next eval."""
    rep = {r.get('mint'): r for r in reports or []}
    dec = {d.get('pair'): d for d in decisions or []}
    best = next((b for b in bench_ or [] if b.get('ready')), (bench_ or [None])[0] if bench_ else None)
    tst = {t.get('mint'): t for t in tests or []}
    per_empty = list((seat or {}).get('seats') or [])
    out, k, used = [], 0, set()
    for i, x in enumerate(seats or []):
        if x.get('kind') == 'open' or not x.get('symbol'):
            e = per_empty[k] if k < len(per_empty) else {}
            k += 1
            nxt = next((b for b in bench_ or [] if b['mint'] not in used), None)
            if nxt:
                used.add(nxt['mint'])
            out.append({'seat': i + 1, 'empty': True, 'next': None if not nxt else {k_: nxt.get(k_) for k_ in ('symbol', 'mint', 'score', 'ready', 'block', 'quality')},
                        'ready': bool(nxt and nxt.get('ready')), 'block': e.get('reason') or (seat or {}).get('reason'), 'code': e.get('code') or (seat or {}).get('code'),
                        'nextEval': (seat or {}).get('nextIn'), 'decidedAt': decided_at})
            continue
        m = x.get('mint')
        r = rep.get(m) or {}
        d = dec.get(x.get('pair')) or {}
        vl = (vels or {}).get(m) or {'state': 'UNKNOWN'}
        sc = (scores or {}).get(m) or {}
        t = tst.get(m) or {}
        need = margin_need(mode, vl, x.get('pct'))
        mg = None if not best or best.get('score') is None or sc.get('score') is None else round(_f(best['score']) - _f(sc['score']), 1)
        prot = None
        if r.get('stop') is not None:
            prot = f"stop {r['stop']:+g}%" + (f" · take +{r['take']:g}%" if r.get('take') is not None else '')
        if r.get('state') == 'PROTECT':
            prot = (prot + ' · ' if prot else '') + 'trail armed'
        out.append({'seat': i + 1, 'empty': False, 'symbol': x.get('symbol'), 'mint': m, 'pct': x.get('pct') if x.get('pct') is not None else r.get('pct'),
                    'vel': vl.get('state'), 'velWhy': vl.get('why'), 'thesis': r.get('verdict') or ('no thesis' if r and not r.get('thesis') else None),
                    'structure': r.get('structure'), 'heldMin': r.get('heldMin'), 'protection': prot, 'score': sc.get('score'),
                    'challenger': None if not best else {'symbol': best.get('symbol'), 'score': best.get('score'), 'ready': best.get('ready')},
                    'margin': mg, 'need': need, 'switch': bool(t.get('switch')), 'switchWhy': t.get('why'),
                    'result': seat_result(r, d), 'why': (f"{r.get('rule')} waits — {r['deferred']}" if r.get('deferred') and d.get('action') != 'pull' else None) or d.get('why') or r.get('evidence') or x.get('why'), 'rule': r.get('rule'),
                    'decidedAt': decided_at, 'inputAt': (input_at or {}).get(m), 'buying': bool(x.get('buying'))})
    return out


def summary(held, target, bench_, used, budget, cash):
    """OCCUPANCY x/target · TARGET · BENCH (ready / depth) · BUYS USED / LEFT · SEATS OPEN · CASH."""
    ready = sum(1 for b in bench_ or [] if b.get('ready'))
    return {'occupancy': int(held), 'target': int(target), 'open': max(0, int(target) - int(held)), 'bench': len(bench_ or []), 'benchReady': ready,
            'buysUsed': int(used), 'buysLeft': max(0, int(budget) - int(used)), 'budget': int(budget), 'cash': None if cash is None else round(_f(cash), 2)}


def seat_room(requested, free, open_seats, min_usd=0.05):
    """🛡 Multi-seat sizing: with N seats open, one fill may take at most free ÷ N (never less than the smallest sendable order while the
    cash allows it) so the first valid seat cannot make the other valid seats impossible. → (multiplier ≤ 1, why) or (1, None)."""
    req, fr, k = _f(requested), _f(free), max(1, int(open_seats or 1))
    if k <= 1 or req <= 0:
        return 1.0, None
    room = max(fr / k, min(fr, min_usd))
    if req <= room + 1e-9:
        return 1.0, None
    return max(0.0, min(1.0, room / req)), f'{k} seats open: ${req:.2f} would leave the others short — ${room:.2f} each from ${fr:.2f} free'


def hard_cross(legs, px, stops=None, creator_sl=None, catastrophic=45.0):
    """☠ Which agent seats sit AT or under a hard line right now (Reaper's own structure stop, the creator's stop, the catastrophic −45%) →
    [mint]. Used by the fast guard ONLY to wake the tier tick early — Reaper still decides and the keeper still sells."""
    out = []
    for l in legs or []:
        m, e = l.get('mint'), _f(l.get('entry'))
        p = _f((px or {}).get(m) or (px or {}).get(l.get('pairAddress')))
        if not m or e <= 0 or p <= 0 or _f(l.get('units')) <= 0 or l.get('placeholder') or l.get('frozen'):
            continue
        pct = (p / e - 1) * 100
        line = max(-_f(catastrophic), _f((stops or {}).get(m, -_f(catastrophic))), -_f(creator_sl) if creator_sl else -_f(catastrophic))
        if pct <= line:
            out.append(m)
    return out


def bench_stats(bench_, prev=()):
    """BENCH DEPTH · READY · NEAR READY · NEW THIS CYCLE · DROPPED THIS CYCLE (vs the last cycle's bench mints)."""
    now_m = [b.get('mint') for b in bench_ or []]
    p = set(prev or ())
    return {'depth': len(now_m), 'ready': sum(1 for b in bench_ or [] if b.get('ready')), 'near': sum(1 for b in bench_ or [] if b.get('near')),
            'new': len([m for m in now_m if m not in p]) if prev is not None else None, 'dropped': len([m for m in p if m not in set(now_m)]), 'mints': now_m}


# ── ⏱ SEAT UTILIZATION ───────────────────────────────────────────────────────────────────────────────────────────────────────────
UTIL_WINDOW_H = 6
UTIL_DT_CAP = 120.0      # a gap longer than this (a restart, a stalled loop) is never counted as seat time of any kind
EMPTY_CAT = {'safety': ('COURIER BLOCK', 'EXECUTION BLOCK', 'WARDEN VETO', 'OFFICE NOT LIVE', 'CREATOR POLICY'), 'budget': ('BUY BUDGET',), 'cash': ('NO CASH',)}


def empty_cat(code):
    """Why an empty seat is empty, as one bucket: safety · budget · cash · waiting (no valid candidate yet: the search goes on)."""
    return next((k for k, v in EMPTY_CAT.items() if code in v), 'waiting')


def util_note(util, board, now, window_h=UTIL_WINDOW_H):
    """One tier tick of seat time: each seat of `board` (seat_board rows) adds the seconds since the last note to occupied, or to empty AND
    its bucket (waiting · safety · budget · cash). Hourly buckets, the last `window_h` hours kept. → new util state"""
    u = {'at': (util or {}).get('at'), 'h': {k: {s: dict(v) for s, v in seats.items()} for k, seats in ((util or {}).get('h') or {}).items()}}
    dt = 0.0 if not u['at'] else min(UTIL_DT_CAP, max(0.0, _f(now) - _f(u['at'])))
    u['at'] = now
    if dt > 0:
        hk = str(int(_f(now) // 3600))
        hb = u['h'].setdefault(hk, {})
        for x in board or []:
            k = str(x.get('seat'))
            b = hb.setdefault(k, {'occ': 0.0, 'empty': 0.0, 'waiting': 0.0, 'safety': 0.0, 'budget': 0.0, 'cash': 0.0})
            if x.get('empty'):
                b['empty'] += dt
                b[empty_cat(x.get('code'))] += dt
            else:
                b['occ'] += dt
    keep = {str(int(_f(now) // 3600) - i) for i in range(window_h)}
    u['h'] = {k: v for k, v in u['h'].items() if k in keep}
    return u


def util_view(util):
    """SEAT UTILIZATION % per seat and overall (window), with TIME EMPTY · TIME OCCUPIED · waiting / safety / budget / cash (seconds)."""
    tot, per = {'occ': 0.0, 'empty': 0.0, 'waiting': 0.0, 'safety': 0.0, 'budget': 0.0, 'cash': 0.0}, {}
    for seats in ((util or {}).get('h') or {}).values():
        for k, b in seats.items():
            p = per.setdefault(k, {kk: 0.0 for kk in tot})
            for kk in tot:
                p[kk] += _f(b.get(kk)); tot[kk] += _f(b.get(kk))
    pct = lambda b: None if b['occ'] + b['empty'] <= 0 else round(b['occ'] / (b['occ'] + b['empty']) * 100, 1)
    return {'all': {**{k: round(v) for k, v in tot.items()}, 'pct': pct(tot)}, 'seats': {k: {**{kk: round(v) for kk, v in b.items()}, 'pct': pct(b)} for k, b in sorted(per.items())},
            'windowH': UTIL_WINDOW_H}
