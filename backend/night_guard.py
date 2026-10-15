"""🌙 THE NIGHT GUARD — a circuit breaker on the real card (owner, 2026-10-15: "assure tonight when I'm asleep the agents don't get drug and I
wake up to losses"). Three trips, each a PAUSE ON NEW REAL BUYS (switch-ins included); every exit, stop, trail and rug shield keeps running:

  📉 DRAWDOWN   the card's value falls DRAW_PCT under its highest value of the last DRAW_WINDOW → pause DRAW_PAUSE
  🧊 STREAK     the last STREAK_N confirmed real exits all lost → pause STREAK_PAUSE
  ☠ RUG BURST   RUG_N exits at ≤ RUG_PCT inside RUG_WINDOW → pause RUG_PAUSE

After a pause the drawdown reference restarts from the card's value then (a fresh window), so one bad hour never pauses the whole night
and a paused card is never re-tripped by the same loss. It can only make the agents buy LESS. Owner switch: realCfg `nightGuard`.
"""
from __future__ import annotations

DRAW_PCT, DRAW_WINDOW, DRAW_PAUSE = 12.0, 6 * 3600.0, 2 * 3600.0
STREAK_N, STREAK_PAUSE = 4, 45 * 60.0
RUG_N, RUG_PCT, RUG_WINDOW, RUG_PAUSE = 2, -45.0, 3600.0, 90 * 60.0
KEEP = 400


def _f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def step(state, value, exits, now):
    """One look → (new state, verdict {paused, why, until, peak, drawPct}). `exits` = confirmed real exits [{at, pct}] oldest first."""
    st = dict(state or {})
    hist = [h for h in (st.get('hist') or []) if now - _f(h[0]) <= DRAW_WINDOW and _f(h[0]) >= _f(st.get('resetAt'))]
    v = _f(value)
    if v > 0:
        hist = (hist + [[round(now, 1), round(v, 4)]])[-KEEP:]
    st['hist'] = hist
    until = _f(st.get('until'))
    if until > now:
        return st, {'paused': True, 'why': st.get('why'), 'until': until, 'kind': st.get('kind')}
    if until and until <= now and not st.get('released'):   # a pause just ended: the drawdown window restarts from here
        st.update(released=True, resetAt=now, hist=[[round(now, 1), round(v, 4)]] if v > 0 else [])
        hist = st['hist']
    peak = max((_f(h[1]) for h in hist), default=0.0)
    draw = (1 - v / peak) * 100 if peak > 0 and v > 0 else 0.0
    last = [e for e in (exits or []) if _f(e.get('at')) > _f(st.get('streakFrom'))]
    trip = None
    if peak > 0 and draw >= DRAW_PCT:
        trip = ('draw', f"📉 card {draw:.0f}% under its {DRAW_WINDOW / 3600:.0f}h high (${peak:.2f} → ${v:.2f})", DRAW_PAUSE)
    elif len(last) >= STREAK_N and all(_f(e.get('pct')) < 0 for e in last[-STREAK_N:]):
        trip = ('streak', f"🧊 the last {STREAK_N} real exits all lost ({', '.join(f'{_f(e.get('pct')):+.0f}%' for e in last[-STREAK_N:])})", STREAK_PAUSE)
    else:
        rugs = [e for e in (exits or []) if _f(e.get('pct')) <= RUG_PCT and now - _f(e.get('at')) <= RUG_WINDOW and _f(e.get('at')) > _f(st.get('rugFrom'))]
        if len(rugs) >= RUG_N:
            trip = ('rug', f"☠ {len(rugs)} exits at {RUG_PCT:.0f}% or worse inside {RUG_WINDOW / 60:.0f} min", RUG_PAUSE)
    if trip:
        kind, why, pause = trip
        st.update(until=now + pause, why=why, kind=kind, released=False, trips=int(_f(st.get('trips'))) + 1, at=now, tripAts=(list(st.get('tripAts') or []) + [round(now, 1)])[-50:])
        if kind == 'streak':
            st['streakFrom'] = now
        if kind == 'rug':
            st['rugFrom'] = now
        return st, {'paused': True, 'why': why, 'until': now + pause, 'kind': kind, 'new': True}
    return st, {'paused': False, 'peak': round(peak, 4), 'drawPct': round(draw, 1)}


def view(state, verdict, now):
    v = verdict or {}
    return {'paused': bool(v.get('paused')), 'why': v.get('why'), 'leftMin': round(max(0, _f(v.get('until')) - now) / 60) if v.get('paused') else None,
            'drawPct': v.get('drawPct'), 'trips': int(_f((state or {}).get('trips'))), 'lines': {'draw': DRAW_PCT, 'streak': STREAK_N, 'rug': RUG_PCT}}


def morning(exits, state, since, now):
    """☀ The overnight report (owner's idea #2): what the agents' real exits did since `since` (last night 20:00), plain words, no promises.
    → text or None when nothing happened."""
    xs = [e for e in exits or [] if _f(e.get('at')) >= since and e.get('pct') is not None]
    trips = sum(1 for t in (state or {}).get('tripAts') or [] if _f(t) >= since)
    if not xs and not trips:
        return None
    won = [e for e in xs if _f(e.get('pct')) > 0]
    avg = sum(_f(e.get('pct')) for e in xs) / len(xs) if xs else 0.0
    worst = min(xs, key=lambda e: _f(e.get('pct'))) if xs else None
    best = max(xs, key=lambda e: _f(e.get('pct'))) if xs else None
    rules = {}
    for e in xs:
        if _f(e.get('pct')) < 0 and e.get('rule'):
            rules[e['rule']] = rules.get(e['rule'], 0) + 1
    out = f"☀ Overnight: {len(xs)} real exits, {len(won)} won ({round(100 * len(won) / len(xs)) if xs else 0}%), average {avg:+.1f}% a trade."
    if best and worst:
        out += f" Best ${best.get('sym') or '?'} {_f(best.get('pct')):+.0f}% · worst ${worst.get('sym') or '?'} {_f(worst.get('pct')):+.0f}%."
    if rules:
        k = max(rules, key=rules.get)
        out += f" Most losses left by {k} ({rules[k]}×)."
    if trips:
        out += f" 🌙 Night guard paused buying {trips}× ({(state or {}).get('why') or ''})."
    return out
