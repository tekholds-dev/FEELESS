"""🎯 THE TRENCH UNIVERSE + the money-boundary constants (moved out of the old four-desk module, 2026-10-12). Pure.

Who may be looked at for a NEW entry (0 < live cap < $200K, a known launch age ≤ 6h, real volume), the keeper's pool floor, the hourly
runaway guards, the agents' own holder line and what counts as an agent seat. The kernel, the office and the service read THESE names —
nothing here is a verdict about a coin's quality (that is the ten-agent brain, trench_kernel/brain.py)."""


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


# ── 💵 AGENT SEATS on the real card — they stay until profit, then the agents decide ────────────────────────────────────────────────
AGENT_TAKES = (5, 10, 20, 30, 50)


DRAIN_PULL = 0.5   # an agent coin whose pool fell under half its entry depth is pulled at once


AGENT_MODES = ('auto', 'pull', 'swap')


AGENT_SEATS = (1, 2, 3, 4)


def is_agent(leg):
    return str(((leg or {}).get('bought') or {}).get('tag') or '').startswith('🤖')


CONTROL_HOLD_MIN = 15      # 🎮 in control: a coin is never switched in its first 15 minutes (the card's own record: exits inside 15 min lose)


CONTROL_MOVES_HR = 6       # 🎮 in control: at most this many SWITCHES an hour (a held coin sold for another) — churn × cost is what drained the card


FILL_MOVES_HR = 36         # 🪑 filling an EMPTY seat has its own runaway guard (owner, 2026-10-11: "no seat should be empty, 30 secs to choose"):
                           # one fill per seat per 10 min on average — a seat that empties is refilled, a loop that refills every tick is stopped


CONTROL_MIN_LIQ = 8_000.0    # 🗑 = the keeper's own trench floor ($8K): no lower is buyable at all (owner, 2026-10-11: "no min starting thresholds"); was $20K → $10K


AGENT_MIN_AGES = (0, 0.05, 0.25, 0.5, 1)   # 🐣 cfg `agentMinAgeH` (hours) — the agents' OWN youngest-coin line (creator limit); 0 = any age, stage-aware evidence decides


AGE_STAGES = (('NEWBORN', 0.25), ('EARLY', 1.0), ('DEVELOPING', 24.0), ('MATURE', float('inf')))


def min_age_of(cfg):
    """The agents' min-age line (hours). Its own key: the engine's trench drop keeps `trenchMinAgeH`. Unknown / unlisted → 0 (any age)."""
    v = (cfg or {}).get('agentMinAgeH')
    return _f(v) if v is not None and _f(v) in AGENT_MIN_AGES else 0.0


def stage_of(age_h):
    """NEWBORN (< 15 min) · EARLY (< 1h) · DEVELOPING (< 24h) · MATURE — context for which evidence a coin can have, never a gate."""
    return None if age_h is None else next(k for k, top in AGE_STAGES if _f(age_h) < top)


AGENT_MAX_MCAP = 200_000.0     # 🎯 owner's spec, 2026-10-11 (latest): NEW entries only under $200K live market cap (held coins keep running)


MC_BANDS = ((10_000, 'NEWBORN MICRO'), (25_000, 'EARLY MICRO'), (50_000, 'EARLY TRENCH'), (100_000, 'BUILDING'), (150_000, 'MOMENTUM TRENCH'), (200_000, 'UPPER TRENCH'))


def under_cap(row, cap=AGENT_MAX_MCAP):
    """Is this coin's LIVE market cap known and in (0, cap)? (the universe for NEW entries)"""
    mc = (row or {}).get('mcap')
    return mc is not None and 0 < _f(mc) < _f(cap)


def trench_band(mc):
    """The under-$200K trench band of a market cap — context and ranking, never a veto. None above the universe."""
    for top, name in MC_BANDS:
        if 0 < _f(mc) < top:
            return name
    return None


AGENT_MIN_MCAP = 0.0           # 🎯 owner's trench-desk spec, 2026-10-12: 0 < live cap < $200K (was $10K) …


AGENT_MAX_AGE_H = 6.0          # … and a KNOWN launch age ≤ 6h for a new entry (unknown age is not eligible; held coins keep running)


AGENT_MIN_VOL1H = 1_000.0      # … with real volume (≥ $1K traded in the last hour); no other starting minimum


# 🧪 THE AGENTS' OWN HOLDER LINE (owner, 2026-10-11: "seats not filled means they too strict"): the engine's runner gates (top-10 < 25%,
# snipers / bundlers < 10% · ≤ 1 bundled, dev < 5%) were tuned for full-size seats on older runners — a launch minutes old is concentrated
# by nature, so 17 of 30 young desk coins were a hard NO. For the agents' lane those three CONCENTRATION gates move to the lines below
# (the coin passes as `holderSoft` and the Warden takes a half seat, W21); every other safety gate — a flagged / rugger creator, the dev
# selling, a top-10 spike, mayhem, live mint / freeze authority — stays a hard NO, and an unread number fails closed.
AGENT_TOP10, AGENT_INSIDERS, AGENT_BUNDLED, AGENT_DEV = 40.0, 20.0, 4, 10.0


CONC_GATES = ('Top 10 under', 'Snipers/bundlers under', 'Dev holds under')


def agent_holder_pass(r):
    """A board row the holder scan FAILED only on concentration, inside the agents' own lines → the concentration labels it carries (it
    may take a half seat), else None (the scan's verdict stands)."""
    r = r or {}
    fails = [str(f) for f in r.get('fails') or []]
    if r.get('safe') is not False or not fails or not all(f.startswith(CONC_GATES) for f in fails):
        return None
    vals = (r.get('top10'), r.get('insiders'), r.get('bundled') if r.get('bundled') is not None else r.get('bundledN'), r.get('dev'))
    if any(v is None for v in vals):
        return None
    t10, ins, bun, dev = (_f(v) for v in vals)
    if t10 < AGENT_TOP10 and ins < AGENT_INSIDERS and bun <= AGENT_BUNDLED and dev < AGENT_DEV:
        return fails
    return None


def in_lane(row, cap=AGENT_MAX_MCAP):
    """🗑 THE AGENTS' UNIVERSE for new entries: 0 < live market cap < the cap, ≥ $1K traded in the hour, a known launch age ≤ 6h."""
    r = row or {}
    if r.get('mint') in _majors():   # 🪙 majors + xStocks are never a trench seat (MRNA / MU sat dead outside US market hours, 2026-10-11)
        return False
    return (under_cap(r, cap) and _f(r.get('mcap')) > AGENT_MIN_MCAP and _f(r.get('vol1h')) >= AGENT_MIN_VOL1H
            and r.get('ageH') is not None and _f(r.get('ageH')) <= AGENT_MAX_AGE_H)


def _majors():
    try:
        import fuse as _fz
        return _fz.ALL_MAJORS
    except Exception:
        return {}


LANE_CAPS = (200_000.0,)   # 🎯 HARD new-entry universe 0 < live cap < $200K (owner, 2026-10-11) — held winners keep running past it   # 🪜 the universe widens only when the one below cannot fill the seats


LANE_NEED = 12          # safe, buyable coins wanted in the lane (4 seats × the ones the keeper / live check will refuse)


def lane_cap(rows, need=LANE_NEED):
    """🪑 SEATS FULL, PERMANENTLY (owner, 2026-10-11: "seats always empty — perma fix"): the smallest cap in LANE_CAPS whose lane holds
    `need` coins that are actually buyable — holder scan passed, pool ≥ CONTROL_MIN_LIQ, real volume. Under $200K is always first in line
    (ranked first); the lane only reaches $1M / $5M while $200K alone cannot fill 4 seats (it held 1–3 safe coins a pass). → cap"""
    ok = lambda r: r.get('safe') is True and _f(r.get('liq')) >= CONTROL_MIN_LIQ
    for cap in LANE_CAPS:
        if sum(1 for r in rows or [] if in_lane(r, cap) and ok(r)) >= need:
            return cap
    return LANE_CAPS[-1]


def lane_step(cap, ranked, need):
    """🪜 The lane follows the RESULT, not the board's flags: fewer ranked candidates than `need` (open seats + 2) → one step wider next pass;
    three times `need` or more → one step back toward $200K. (The board marked 16 sub-$200K coins safe, yet 33 of 35 failed the desk's
    hard checks and the seats sat empty while the cap never moved.) → the next cap"""
    caps = list(LANE_CAPS)
    i = caps.index(cap) if cap in caps else 0
    if ranked < need and i < len(caps) - 1:
        return caps[i + 1]
    if ranked >= 3 * need and i > 0:
        return caps[i - 1]
    return caps[i]


ESTABLISHED_H = 168.0           # mirror of runners.PICK_OLD_H / PICK_OLD_LIQ (a test keeps them equal): the owner's verified-pick rule


ESTABLISHED_LIQ = 100_000.0


CONCENTRATION_FAILS = ('top 10',)   # the only scan fail an established coin may carry: exchange / pool wallets ARE its top 10


def established(row):
    """🏛 An established coin (> 7 days old, pool ≥ $100K) whose holder scan failed ONLY on top-10 concentration counts as scan-passed
    for the agents — the same rule the owner's verified picks use. Found 2026-10-11: Bonk, SNDK, LIT, USELESS, ANSEM ($100K–$7M pools,
    $100K–$460K an hour) all read "failed the holder safety scan" because exchange and pool wallets hold their supply, so the agents
    could never pick a high-volume coin. Any other fail (creator, dev, authority, unscanned) stands. → row (a copy, flagged) or the row."""
    r = row or {}
    if r.get('safe') is not False or r.get('ageH') is None or _f(r['ageH']) <= ESTABLISHED_H or _f(r.get('liq')) < ESTABLISHED_LIQ:
        return row
    fails = [str(x).lower() for x in r.get('fails') or []]
    if not fails or not all(any(k in x for k in CONCENTRATION_FAILS) for x in fails):
        return row
    return {**r, 'safe': True, 'established': True}


# ── 💵 THE REAL-MONEY PHASE (the one mission: RECOVERY < put-in ≤ GROWTH < 2× ≤ GRADUATED) ─────────────────────────────────────────
def underwater(state):
    """💵 Is the creator's real card worth less than what was put in? (`money` = {value, putIn}, stamped by the service each pass.) While it
    is, the team CANNOT leave the 5-minute stage (owner, 2026-10-10: "they can't get out of 5 min until they win real money back to breakeven")."""
    m = (state or {}).get('money') or {}
    return _f(m.get('putIn')) > 0 and _f(m.get('value')) < _f(m.get('putIn'))


GRADUATE_X = 2.0   # 🎓 owner, 2026-10-10: "breakeven is a milestone, not graduation" — the 5-minute real-money mission is conquered at 2× the put-in


def real_phase(money):
    """💵 THE REAL-MONEY MISSION, from the real card's own accounting only (`money` = {value, putIn}: its server value and everything
    put in — the numbers My cards shows; never paper, never gross proceeds, never paid-out totals).
      value < put-in            → RECOVERY  (phase 1: back to breakeven)
      put-in ≤ value < 2× put-in → GROWTH    (phase 2: breakeven is a milestone — the stage is STILL locked)
      value ≥ 2× put-in         → GRADUATED (the 5-minute real-money mission is conquered: the next stage becomes ELIGIBLE)
    Unknown money = UNKNOWN = locked: nothing but real equity can unlock a real-money stage."""
    m = money or {}
    p, known = _f(m.get('putIn')), m.get('value') is not None and _f(m.get('putIn')) > 0
    v = _f(m.get('value'))
    ph = 'UNKNOWN' if not known else 'RECOVERY' if v < p else 'GROWTH' if v < p * GRADUATE_X else 'GRADUATED'
    return {'known': known, 'putIn': round(p, 2) if known else None, 'value': round(v, 2) if known else None, 'phase': ph,
            'breakeven': round(p, 2) if known else None, 'double': round(p * GRADUATE_X, 2) if known else None,
            'toBreakeven': round(max(0.0, p - v), 2) if known else None, 'toDouble': round(max(0.0, p * GRADUATE_X - v), 2) if known else None,
            'eligible': ph == 'GRADUATED', 'x': GRADUATE_X}
