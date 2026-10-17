"""💰 CAPITAL DESK (pure, tested `tests/test_capital.py`; owner, 2026-10-13: "agents must be taught about capital management and how
to grow faster"). Size follows the agents' own REAL record — never a feeling:

`record(trades)` = the last `WINDOW` confirmed real exits → win rate, average win, average loss, payoff (avg win ÷ avg loss),
expectancy per trade and the Kelly fraction (the share of the card ONE bet may carry before growth turns into ruin).
`stance(rec, seats)`:
  PROVING  under `MIN_N` exits, or a winning record with fewer than `PROVE_N` — size as before (nothing is claimed)
  PROTECT  ≥ `MIN_N` exits and Kelly ≤ 0 (the average bet LOSES): the smallest seat (×0.25) until the record turns
  STEADY   ≥ `PROVE_N` exits, winning by a hair (half-Kelly of the card is under half a seat): every seat ×0.5 — the edge is too thin to press
  GROW     ≥ `PROVE_N` exits, expectancy AND Kelly > 0 and half-Kelly ≥ ¾ of a seat: a seat = HALF-Kelly of the card (never more than the
           equal seat the card's own rule asks for — the Warden cannot return more than requested), and an uncertain coin may take ×0.75
`leaks(trades)` = where the money went, by exit rule — the lesson the model coach and the page read.
Money compounds by itself: a seat is a share of what the card is worth NOW. A record, never a promise: 20 trades is a thin proof and
the stance falls back the moment the window stops winning."""
WINDOW = 30
MIN_N = 12
PROVE_N = 20
CAP = 100.0
PROTECT_MULT = 0.25
GROW_MIN, GROW_UNSURE = 0.5, 0.75   # a proven record never sizes under today's half seat · an uncertain coin's best size while growing
STEPS = (1.0, 0.75, 0.5, 0.25)


from fnum import nan_safe as _f


def _pcts(trades, n=WINDOW):
    rows = sorted((t for t in trades or [] if t.get('realPct') is not None), key=lambda t: _f(t.get('closedAt')))[-n:]
    return [max(-CAP, min(CAP, _f(t['realPct']))) for t in rows]


def record(trades, n=WINDOW):
    """→ {n, wonPct, avgWin, avgLoss, payoff, expPct, kelly} over the newest `n` confirmed real exits (results capped ±100%)."""
    r = _pcts(trades, n)
    if not r:
        return {'n': 0, 'wonPct': None, 'avgWin': None, 'avgLoss': None, 'payoff': None, 'expPct': None, 'kelly': None}
    w, l = [x for x in r if x > 0], [x for x in r if x <= 0]
    p = len(w) / len(r)
    aw, al = (sum(w) / len(w) if w else 0.0), (-sum(l) / len(l) if l else 0.0)
    payoff = aw / al if al > 0 else None
    kelly = (1.0 if w else 0.0) if al <= 0 else (p - (1 - p) / payoff if payoff else -1.0)
    return {'n': len(r), 'wonPct': round(p * 100), 'avgWin': round(aw, 1), 'avgLoss': round(-al, 1), 'payoff': None if payoff is None else round(payoff, 2),
            'expPct': round(p * aw - (1 - p) * al, 1), 'kelly': round(max(-1.0, min(1.0, kelly)), 2)}


def stance(rec, seats=4):
    """→ {state, mult, floor, why}: `mult` = the Warden's capital size (≤ 1), `floor` = how small an UNCERTAIN coin's seat may get."""
    r = rec or {}
    n, k = int(r.get('n') or 0), _f(r.get('kelly'))
    if n < MIN_N:
        return {'state': 'PROVING', 'mult': None, 'floor': None, 'why': f"{n} of {MIN_N} real exits — too few to size by; seats as before"}
    line = f"last {n} real exits: {r.get('wonPct')}% won, wins {_f(r.get('avgWin')):+.1f}% vs losses {_f(r.get('avgLoss')):+.1f}%"
    if k <= 0 or _f(r.get('expPct')) <= 0:
        return {'state': 'PROTECT', 'mult': PROTECT_MULT, 'floor': PROTECT_MULT, 'why': f"{line} → the average bet loses {abs(_f(r.get('expPct'))):.1f}%: smallest seats until that turns"}
    if n < PROVE_N:
        return {'state': 'PROVING', 'mult': None, 'floor': None, 'why': f"{line} → winning, but {n} of {PROVE_N} exits is not proof yet; seats as before"}
    raw = max(GROW_MIN, min(1.0, k / 2 * max(1, int(seats or 1))))   # half-Kelly of the card, in equal seats
    mult = max(s for s in STEPS if s <= raw + 1e-9)
    return {'state': 'GROW' if mult > GROW_MIN else 'STEADY', 'mult': mult, 'floor': min(GROW_UNSURE, mult),
            'why': f"{line} → +{_f(r.get('expPct')):.1f}% a bet, Kelly {k:.2f}: half-Kelly = {k / 2 * 100:.0f}% of the card a bet → ×{mult:g} of a seat"}


def leaks(trades, n=WINDOW, top=3):
    """Where the last `n` real exits lost / made the money, by exit rule → [{rule, n, sumPct, avgPct}] worst first."""
    rows = sorted((t for t in trades or [] if t.get('realPct') is not None), key=lambda t: _f(t.get('closedAt')))[-n:]
    by = {}
    for t in rows:
        k = str(t.get('rule') or 'other').split(':')[0].strip()[:32] or 'other'
        by.setdefault(k, []).append(max(-CAP, min(CAP, _f(t['realPct']))))
    out = [{'rule': k, 'n': len(v), 'sumPct': round(sum(v), 1), 'avgPct': round(sum(v) / len(v), 1)} for k, v in by.items()]
    return sorted(out, key=lambda x: x['sumPct'])[:top]


DOORS = (('armed', 'ARMED', '🎯 armed'), ('ready', 'READY', '⚡ ready'))   # the door a seat came through, read from its card tag
ARMED_BASE = 0.5      # an armed fill = half of what the Warden allows … until the armed door's OWN record proves it wins
BRAKE_PCT = 15.0      # 🧯 card worth this much less than its 24h high = smallest seats until it climbs back


def door(tag):
    t = str(tag or '')
    return next((k for k, word, _l in DOORS if word in t), 'other')


def doors(trades, seats=4):
    """Each door on its OWN last `WINDOW` real exits → {door: {label, record, state, mult, why}}."""
    out = {}
    for k, _w, label in DOORS:
        rec = record([t for t in trades or [] if door(t.get('tag')) == k])
        out[k] = {'label': label, 'record': rec, **stance(rec, seats)}
    return out


def armed_size(v):
    """How much of the Warden's size an ARMED fill takes: half (ARMED_BASE) — the full size only once the armed door's own record is in
    GROW; a quarter while that record is in PROTECT. Capital switched off / no record = half, as before."""
    d = ((v or {}).get('doors') or {}).get('armed') or {}
    if not (v or {}).get('on'):
        return ARMED_BASE
    if ORDER.get(v.get('state'), 1) == 0 or (v.get('brake') or {}).get('on'):
        return 1.0   # the Warden already cut this fill to the smallest seat: halving it again leaves an order too small to send
    return 1.0 if d.get('state') == 'GROW' and v.get('state') == 'GROW' else ARMED_BASE


BRAKE_HOURS = 6        # 🧯 the high the brake measures from = the last 6h (24h held a whole morning after one bad night — owner: "they get lazy")
BRAKE_MULT = 0.5       # half seats while braked (a quarter seat sat under the cost floor: braked = no trading = it could never climb back)
BRAKE_RELEASE = 3      # the brake lets go by itself once the agents' last N confirmed real exits all won


def brake(value, peak, pct=BRAKE_PCT, recent=None):
    """🧯 DRAWDOWN BRAKE → {on, downPct, why, released}: the card is worth ≥ `pct` % less than its BRAKE_HOURS high — unless the last
    BRAKE_RELEASE real exits (newest last) all won, which releases it (it has to be able to climb back by trading)."""
    v, p = _f(value), _f(peak)
    if v <= 0 or p <= 0 or v >= p:
        return {'on': False, 'downPct': 0.0, 'why': None}
    down = (1 - v / p) * 100
    rec = [x for x in (recent or []) if x is not None][-BRAKE_RELEASE:]
    if down >= pct and len(rec) >= BRAKE_RELEASE and all(_f(x) > 0 for x in rec):
        return {'on': False, 'downPct': round(down, 1), 'released': True, 'why': f"card {down:.0f}% off its {BRAKE_HOURS}h high, but its last {BRAKE_RELEASE} real exits all won — brake released"}
    return {'on': down >= pct, 'downPct': round(down, 1), 'why': f"card ${v:.2f} is {down:.0f}% off its {BRAKE_HOURS}h high ${p:.2f}" + (f" (brake at {pct:g}%): half seats until {BRAKE_RELEASE} straight real wins or it climbs back" if down >= pct else '')}


def for_door(v, tag_or_door):
    """The stance ONE fill is sized by: 🧯 the brake first, then its door's own record once that door has ≥ MIN_N exits, else the desk's."""
    v = v or {}
    cap_ = (v.get('rug') or {}).get('capPct')
    if (v.get('brake') or {}).get('on'):
        return {'state': 'PROTECT', 'mult': BRAKE_MULT, 'floor': BRAKE_MULT, 'why': '🧯 ' + str(v['brake'].get('why')), 'rugCapPct': cap_}
    if ORDER.get(v.get('state'), 1) == 0:   # the desk itself is in PROTECT (long record): no door lifts it
        return {**{k_: v.get(k_) for k_ in ('state', 'mult', 'floor', 'why')}, 'rugCapPct': cap_}
    k = tag_or_door if tag_or_door in ('armed', 'ready', 'other') else door(tag_or_door)
    d = (v.get('doors') or {}).get(k) or {}
    if int((d.get('record') or {}).get('n') or 0) >= MIN_N and d.get('state') in ('PROTECT', 'STEADY', 'GROW'):
        if ORDER.get(d['state'], 1) <= ORDER.get(v.get('state'), 1):   # a door may size DOWN from the desk's stance on its own record, never up past it
            return {'state': d['state'], 'mult': d['mult'], 'floor': d['floor'], 'why': f"{d.get('label')} door — {d.get('why')}", 'rugCapPct': cap_}
    return {**{k_: v.get(k_) for k_ in ('state', 'mult', 'floor', 'why')}, 'rugCapPct': cap_}


LONG = 150            # ☠ the long record: rugs are ~1 seat in 8 — a 30-exit window often holds none, so it can never be the one that presses size
LONG_MIN = 50
RUG_PCT = -45.0       # a seat that ended here or worse = a rug (the whole seat is the risk, whatever the stop line says)
RUG_RATE_MIN = 5.0    # % of seats rugged (long record) from which the rug budget applies
RUG_BUDGET_PCT = 8.0  # ☠ one rug may cost at most this share of the CARD: a seat is capped at budget ÷ the average rug loss
ORDER = {'PROTECT': 0, 'PROVING': 1, 'STEADY': 2, 'GROW': 3}


def rugs(trades, n=LONG):
    """The long record's tail → {n, rugs, ratePct, avgPct, capPct} — `capPct` = the largest seat (% of the card) one rug may take."""
    r = _pcts(trades, n)
    bad = [x for x in r if x <= RUG_PCT]
    rate = len(bad) / len(r) * 100 if r else 0.0
    avg = sum(bad) / len(bad) if bad else 0.0
    on = len(r) >= LONG_MIN and rate >= RUG_RATE_MIN
    return {'n': len(r), 'rugs': len(bad), 'ratePct': round(rate, 1), 'avgPct': round(avg, 1), 'on': on,
            'capPct': round(RUG_BUDGET_PCT / (abs(avg) / 100), 1) if on and avg < 0 else None}


def view(trades, seats=4, on=True, value=None, peak=None):
    """The one object the Warden, the page and the model coach read."""
    rec = record(trades)
    st = stance(rec, seats)
    lrec = record(trades, LONG)
    if lrec['n'] >= LONG_MIN:   # ☠ the long record (rugs included) is the ceiling: the short window can lower the stance, never lift it past this
        lst = stance(lrec, seats)
        if ORDER.get(lst['state'], 1) < ORDER.get(st['state'], 1):
            st = {**lst, 'why': f"the last {rec['n']} exits read {st['state']}, but the last {lrec['n']} (rugs included) read {lst['state']} — {lst['why']}"}
    rg = rugs(trades)
    return {'on': bool(on), 'record': rec, **st, 'leaks': leaks(trades), 'window': WINDOW, 'needN': PROVE_N, 'doors': doors(trades, seats), 'brake': brake(value, peak, recent=_pcts(trades, BRAKE_RELEASE)),
            'long': lrec, 'rug': rg}


def lesson(v):
    """One line for the model coach's case (evidence, never an instruction)."""
    r = (v or {}).get('record') or {}
    if not r.get('n'):
        return None
    dz = ' · '.join(f"{d['label']} {d['record']['wonPct']}% won {_f(d['record'].get('expPct')):+.1f}%/bet (n {d['record']['n']})" for d in (v.get('doors') or {}).values() if d['record'].get('n'))
    rg = v.get('rug') or {}
    lk = ' · '.join(f"{x['rule']} {x['sumPct']:+.0f}% over {x['n']}" for x in (v.get('leaks') or []) if x['sumPct'] < 0)
    return (f"{v.get('state')}: {r['n']} real exits, {r.get('wonPct')}% won, avg win {_f(r.get('avgWin')):+.1f}% vs avg loss {_f(r.get('avgLoss')):+.1f}% "
            f"(payoff {r.get('payoff')}), {_f(r.get('expPct')):+.1f}% a bet, Kelly {r.get('kelly')}" + (f" · ☠ {rg['rugs']} of the last {rg['n']} seats rugged ({rg['ratePct']}%, avg {rg['avgPct']}%)" if rg.get('rugs') else '') + (f" · by door: {dz}" if dz else '') + (f" · 🧯 {v['brake']['why']}" if (v.get('brake') or {}).get('on') else '') + (f" · losses come from: {lk}" if lk else ''))[:420]
