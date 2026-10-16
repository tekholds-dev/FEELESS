"""🎯 THE TRENCH UNIVERSE + the money-boundary constants (moved out of the old four-desk module, 2026-10-12). Pure.

Who may be looked at for a NEW entry (live cap inside the owner's band — default $12K–$300K —, a known launch age ≤ 6h, real volume), the keeper's pool floor, the hourly
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


CONTROL_MOVES_HR = 3       # 🎮 in control: at most this many SWITCHES an hour (a held coin sold for another) — churn × cost is what drained the card


FILL_MOVES_HR = 36         # 🪑 filling an EMPTY seat has its own runaway guard (owner, 2026-10-11: "no seat should be empty, 30 secs to choose"):
                           # one fill per seat per 10 min on average — a seat that empties is refilled, a loop that refills every tick is stopped


CONTROL_MIN_LIQ = 8_000.0    # 🗑 = the keeper's own trench floor ($8K): no lower is buyable at all (owner, 2026-10-11: "no min starting thresholds"); was $20K → $10K


AGENT_MIN_AGES = (0, 0.05, 0.25, 0.5, 1, 2, 3)   # 🐣 cfg `agentMinAgeH` (hours) — the agents' OWN youngest-coin line (creator limit); 0 = any age, stage-aware evidence decides


AGE_STAGES = (('NEWBORN', 0.25), ('EARLY', 1.0), ('DEVELOPING', 24.0), ('MATURE', float('inf')))


def min_age_of(cfg):
    """The agents' min-age line (hours). Its own key: the engine's trench drop keeps `trenchMinAgeH`. Unknown / unlisted → 0 (any age)."""
    v = (cfg or {}).get('agentMinAgeH')
    return _f(v) if v is not None and _f(v) in AGENT_MIN_AGES else 0.0


def stage_of(age_h):
    """NEWBORN (< 15 min) · EARLY (< 1h) · DEVELOPING (< 24h) · MATURE — context for which evidence a coin can have, never a gate."""
    return None if age_h is None else next(k for k, top in AGE_STAGES if _f(age_h) < top)


AGENT_MAX_MCAP = 300_000.0     # 🎯 owner, 2026-10-12 (latest): "trench better on coins from 12k-300k mc" — NEW entries inside the band (held coins keep running)


AGENT_MIN_MCAP = 12_000.0      # … and at least $12K live cap (under it the curve is still being sniped: the record reads −99% an hour for < 15-min coins)


# 🎛 THE OWNER'S MC BAND (realCfg `agentMcMin` / `agentMcMax`, HQ › Agents › controls): every reader of the universe — the lane, the hard
# wall, the open-mode wall, the ranking's band part — reads `band()`. The service sets it from the real card's config once a pass.
BAND_MINS = (0.0, 5_000.0, 10_000.0, 12_000.0, 20_000.0, 30_000.0, 50_000.0)
BAND_MAXS = (100_000.0, 150_000.0, 200_000.0, 300_000.0, 500_000.0, 1_000_000.0, 2_000_000.0, 5_000_000.0, 10_000_000.0)   # 2M–10M: Pump trending runners (owner, 2026-10-13: "wider tunes … these coins run booty vol")
_BAND = [AGENT_MIN_MCAP, AGENT_MAX_MCAP]


def clean_band(cfg):
    """realCfg → (min, max) from the fixed option lists; unknown / unset → the default 12K–300K; a min at or over the max → the default min."""
    c = cfg or {}
    mn = _f(c.get('agentMcMin')) if c.get('agentMcMin') is not None and _f(c.get('agentMcMin')) in BAND_MINS else AGENT_MIN_MCAP
    mx = _f(c.get('agentMcMax')) if c.get('agentMcMax') is not None and _f(c.get('agentMcMax')) in BAND_MAXS else AGENT_MAX_MCAP
    return (mn if mn < mx else min(AGENT_MIN_MCAP, mx / 2)), mx


# 🔥 THE OWNER'S VOLUME LIMITS (owner, 2026-10-13: "fix limits so I can tune for more volume and wider tunes to get Pump trending in there,
# moving real fast volume"): realCfg `agentMaxAgeH` (oldest coin a NEW entry may be; default 6h), `agentMinVol1h` (traded in the last hour;
# default $1K) and `agentPumpTrend` — off · first (a coin on Pump's own Trending board skips the age line and ranks up) · only (new entries
# come ONLY from Pump trending). Every safety gate, the MC band, the keeper's pool floor and the live checks still apply to every coin.
MAX_AGES = (1.0, 3.0, 6.0, 12.0, 24.0, 72.0, 168.0, 720.0)
MIN_VOLS = (1_000.0, 5_000.0, 10_000.0, 25_000.0, 50_000.0, 100_000.0, 250_000.0)
TREND_MODES = ('off', 'first', 'only')
TREND_RANK = 1.15        # a coin on Pump trending in `first` / `only` mode: ×1.15 rank and newness counted as fresh (it is running NOW)
GERM_MAXES = (0, 10, 15, 25)   # 🦠 cfg `agentGermMax`: a NEW entry sits at most this % from its germ floor (owner, 2026-10-16: "buying the floor is 15%
                               # max from floor"; replay on the 1m candles: 15% lost least of 8 / 15 / 25 — −3.4% vs −4.4% / −4.5% after costs). 0 = off.
GERM_MAX_DEFAULT = 15
_LIM = {'maxAgeH': 6.0, 'minVol': 1_000.0, 'trend': 'off', 'minAgeH': 0.0, 'germMax': GERM_MAX_DEFAULT, 'trending': frozenset()}


def clean_limits(cfg):
    c = cfg or {}
    a = _f(c.get('agentMaxAgeH')) if c.get('agentMaxAgeH') is not None and _f(c.get('agentMaxAgeH')) in MAX_AGES else 6.0
    v = _f(c.get('agentMinVol1h')) if c.get('agentMinVol1h') is not None and _f(c.get('agentMinVol1h')) in MIN_VOLS else AGENT_MIN_VOL1H
    t = c.get('agentPumpTrend') if c.get('agentPumpTrend') in TREND_MODES else 'off'
    g = int(_f(c.get('agentGermMax'))) if c.get('agentGermMax') is not None and int(_f(c.get('agentGermMax'))) in GERM_MAXES else GERM_MAX_DEFAULT
    return {'maxAgeH': a, 'minVol': v, 'trend': t, 'minAgeH': min_age_of(c), 'germMax': g}


def set_band(cfg):
    _BAND[:] = clean_band(cfg)
    _LIM.update(clean_limits(cfg))
    return band()


def set_trending(mints):
    """The mints on Pump's own Trending board right now (set by the service each agents pass from the ptrend list)."""
    _LIM['trending'] = frozenset(m for m in (mints or ()) if m)


def limits():
    return {k: v for k, v in _LIM.items() if k != 'trending'} | {'trendingN': len(_LIM['trending'])}


def on_trend(row):
    """Is this coin on Pump's Trending board AND the owner's trend mode on?"""
    r = row or {}
    return _LIM['trend'] != 'off' and (r.get('mint') in _LIM['trending'] or 'ptrend' in (r.get('src') or ()))


def max_age(row=None):
    """The oldest a coin may be for a NEW entry (hours): the owner's line; a Pump-trending coin in first / only mode has none."""
    return float('inf') if on_trend(row) else _LIM['maxAgeH']


def min_age():
    """🐣 The youngest a coin may be for a NEW entry (hours) — the owner's `agentMinAgeH`. It was shown on screen but enforced nowhere after the
    2026-10-12 refactor (the owner had 30 min set while 2–3-minute coins were bought and rugged). Pump trending does NOT waive it."""
    return _LIM['minAgeH']


def too_young(row):
    """→ reason or None. Unknown age is handled by the callers (it is never eligible)."""
    a, mn = (row or {}).get('ageH'), _LIM['minAgeH']
    if a is not None and mn > 0 and _f(a) < mn:
        return f"{_f(a) * 60:.0f} min old — your youngest-coin line is {mn * 60:g} min" if mn < 1 else f"{_f(a):.1f}h old — your youngest-coin line is {mn:g}h"
    return None


def germ_max():
    """🦠 The most % a NEW entry may sit above (or under) its germ floor — 0 = the line is off."""
    return _LIM['germMax']


def min_vol():
    return _LIM['minVol']


def band():
    """(min, max) live market cap for a NEW entry, right now."""
    return _BAND[0], _BAND[1]


def k_word(v):
    v = _f(v)
    return f"${v / 1e6:g}M" if v >= 1e6 else f"${v / 1e3:g}K" if v >= 1e3 else f"${v:g}"


def band_word(b=None):
    mn, mx = b or band()
    return f"{k_word(mn)}–{k_word(mx)}" if mn > 0 else f"under {k_word(mx)}"


MC_BANDS = ((12_000, 'NEWBORN MICRO'), (25_000, 'EARLY MICRO'), (50_000, 'EARLY TRENCH'), (100_000, 'BUILDING'), (200_000, 'MOMENTUM TRENCH'),
            (300_000, 'UPPER TRENCH'), (1_000_001, 'BREAKOUT TRENCH'))


def under_cap(row, cap=None):
    """Is this coin's LIVE market cap known and inside the band — min < cap < `cap` (default: the band's max)? (the NEW-entry universe)"""
    mc = (row or {}).get('mcap')
    mn, mx = band()
    return mc is not None and max(0.0, mn) < _f(mc) < _f(cap if cap is not None else mx) and _f(mc) > 0


def trench_band(mc):
    """The trench band name of a market cap — context and ranking, never a veto. None above $1M."""
    for top, name in MC_BANDS:
        if 0 < _f(mc) < top:
            return name
    return None




AGENT_MAX_AGE_H = 6.0          # 🕐 a KNOWN launch age ≤ 6h for a new entry (unknown age is not eligible; held coins keep running)


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


def in_lane(row, cap=None):
    """🗑 THE AGENTS' UNIVERSE for new entries: live market cap inside the owner's band (`band()`, default $12K–$300K; `cap` may only
    LOWER the top), ≥ the owner's hourly volume (default $1K), a known launch age ≤ the owner's line (default 6h; none for a Pump-trending
    coin in first / only mode); `only` mode = Pump trending coins only."""
    r = row or {}
    if r.get('mint') in _majors():   # 🪙 majors + xStocks are never a trench seat (MRNA / MU sat dead outside US market hours, 2026-10-11)
        return False
    top = min(band()[1], _f(cap)) if cap else band()[1]
    if _LIM['trend'] == 'only' and not on_trend(r):
        return False
    return (under_cap(r, top) and _f(r.get('vol1h')) >= min_vol()
            and r.get('ageH') is not None and _f(r.get('ageH')) <= max_age(r) and not too_young(r))


def _majors():
    try:
        import fuse as _fz
        return _fz.ALL_MAJORS
    except Exception:
        return {}


LANE_CAPS = (AGENT_MAX_MCAP,)   # 🎯 the default band's top — the live top is `band()[1]` (the owner's control); held winners keep running past it


LANE_NEED = 12          # safe, buyable coins wanted in the lane (4 seats × the ones the keeper / live check will refuse)


def lane_cap(rows=None, need=LANE_NEED):
    """The lane's top = the owner's band top (`band()[1]`). `rows` / `need` are kept for callers; the cap never widens past the band."""
    return band()[1]   # one rung: the owner's band top (the old $200K → $1M → $5M widening was retired — it seated MRNA / MU xStocks)


def lane_step(cap, ranked, need):
    """🪜 The lane follows the RESULT, not the board's flags: fewer ranked candidates than `need` (open seats + 2) → one step wider next pass;
    three times `need` or more → one step back toward $200K. (The board marked 16 sub-$200K coins safe, yet 33 of 35 failed the desk's
    hard checks and the seats sat empty while the cap never moved.) → the next cap"""
    caps = [band()[1]]
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
