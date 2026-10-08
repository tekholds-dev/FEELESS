"""⭐ ARENA PRIME: FEELESS's own top-tier cards, run FULLY AUTO on paper (no wallet, no money) so the automation is proven in
public before any trader's config goes auto. Pure functions — the service feeds prices + candidates every tick.

Each Prime card runs its dial (Safe / Balanced / Degen) with every automation ON:
  • auto take-profit / stop-loss per coin (the dial's TP / SL),
  • auto-compound: a take-profit's gain is rolled into the card's other coins by weight (never left idle),
  • auto-rotate: every `rotateHours` (default 6h) the `rotateCount` (default 2) weakest coins are swapped for the best gated
    candidates not already on the card; a stop-loss is replaced at once,
  • every action is an event with its reason, so the card's whole life is replayable.
P&L never includes fees (same rule as real cards); a flat paper fee per trade is tracked SEPARATELY as `feesUsd`.
"""
import math

# Native/wrapped SOL mint used by real-card helpers. Kept local so arena_prime stays pure
# and does not import fuse_wallet (which imports this engine).
SOL_MINT = 'So11111111111111111111111111111111111111112'

# Three top tiers. Every coin on a Prime card is rated 3–5★ (anything weaker never gets in). Each card holds a STABLE anchor
# (a real major on Solana: SOL / JitoSOL / cbBTC …, rotated only on configured re-shapes, never stopped out) + deep pools + gated runners.
TEMPLATES = {   # anchors / pools / runners per card + the dial it runs
    # 5 top tiers. Majors = solid holds; "young" runners = pre-bond runners + clean graduated coins under 48h (every gate but pre-bond).
    'safe': {'label': '💎 Prime Diamond', 'tier': 'diamond', 'anchors': 1, 'pools': 0, 'runners': 3, 'tp': 900, 'sl': 35,
             'why': 'young coins held toward 10× — momentum decides ride / bank, the most active major anchors the card'},
    'balanced': {'label': '🥇 Prime Gold', 'tier': 'gold', 'anchors': 2, 'pools': 1, 'runners': 1, 'tp': 50, 'sl': 15,
                 'why': 'two majors + a deep pool + one runner kicker'},
    'degen': {'label': '🔥 Prime Blaze', 'tier': 'blaze', 'anchors': 1, 'pools': 1, 'runners': 2, 'tp': 100, 'sl': 20,
              'why': 'one major, one pool, two runners — doubles get banked'},
    'next': {'label': '⚡ Prime Next Level', 'tier': 'next', 'anchors': 0, 'pools': 0, 'runners': 4, 'tp': 300, 'sl': 25,
             'why': 'all runners, 4× take-profit, house money rides — the floor goes to cash'},
    'ever': {'label': '♾ Prime Everlasting', 'tier': 'ever', 'anchors': 4, 'pools': 1, 'runners': 0, 'tp': 40, 'sl': 0,
             'why': 'SOL / BTC / ETH / JitoSOL + PUMP — never stopped, only rotated if a pool weakens'},
}
MIN_STARS = 3
# 🔄 Phase cycle (Blaze + Next Level): each round re-deals the card into the next shape — rest in majors, strike with runners,
# rest again, then a half-and-half round. Same run (P&L continues); every phase change is an event with its reason.
# Every shape keeps at least ONE growth coin (a new major or a runner) — a card never sits in old majors only.
# `growth`: which growth coins fill the runner slots first — 'major' (new majors = young coins that arrived big, safer),
# 'runner' (fresh launchpad runners), 'mix' (one of each, then the best).
PHASES = {'anchor': {'anchors': 3, 'pools': 0, 'runners': 1, 'growth': 'major', 'why': 'anchor round — 3 majors + 1 new major'},
          'degen': {'anchors': 1, 'pools': 0, 'runners': 3, 'growth': 'runner', 'why': 'degen round — 1 major + 3 runners strike'},
          'mixed': {'anchors': 2, 'pools': 0, 'runners': 2, 'growth': 'mix', 'why': 'mixed round — 2 majors + a new major + a runner'},
          'safest': {'anchors': 3, 'pools': 0, 'runners': 1, 'growth': 'major', 'why': '🛡 safest run — 3 majors + 1 new major'},
          'breakeven': {'anchors': 0, 'pools': 1, 'runners': 3, 'byVol': True, 'growth': 'runner', 'why': '⚖ breakeven run — 1 high-volume pool + 3 high-volume runners'},
          'trench': {'anchors': 1, 'pools': 1, 'runners': 2, 'growth': 'trench', 'why': '🗑 trench round — 1 major + 1 pool + up to 2 fresh trench breakouts (the rest runners)'}}
TRENCH_COINS = (1, 2)   # 🗑 how many trench coins one card may hold (high risk — never more than 2)
SHAPES = tuple(PHASES)
CYCLE = ('anchor', 'degen', 'anchor', 'mixed')
CYCLE_TIERS = ('degen', 'next')
# 🔄 Round cycles per tier (HQ picks): off = keep the tier's own shape · classic = anchor→degen→anchor→mixed ·
# adaptive = a LOSING round rests in majors, a winning one (≥ +5%) presses with runners, flat = mixed · safe = anchor⇄mixed ·
# press = degen⇄mixed. Every phase change is the same run (P&L continues).
CYCLE_MODES = {'off': None, 'classic': CYCLE, 'adaptive': 'adaptive', 'safe': ('anchor', 'mixed'), 'press': ('degen', 'mixed'),
               'rescue': ('safest', 'breakeven'), 'auto': 'auto', 'trench': ('trench',)}
RESCUE_PCT = -50.0   # (default; HQ sets cfg rescuePct) 🛟 any card that falls 50% under its start switches to the rescue cycle (safest ⇄ breakeven)
ROTATE_MIN_DROP = 10.0   # rotation only swaps a coin that is actually losing (≤ −10% from entry) — winners are never churned
ROTATE_CONFIRM = 3       # … and only after it has been losing for 3 rounds in a row (on 5-min rounds = 15 min — not one noisy dip)
MIN_HOLD_MINS = 30       # … and only once it has been held 30 min (a fresh buy is never flipped straight back out)
STRICT_VOL1H, STRICT_BUYS = 20_000.0, 55.0   # 🌧 bad runner weather: runner picks need ≥ $20K 1h volume and ≥ 55% buys
CYCLE_EVERY = (1, 3, 6, 12)   # re-shape every N rounds (default 6: on 5-min rounds = every 30 min, not every round)


def cycle_seq(mode):
    """A named cycle, 'auto', or a CUSTOM pick of up to 3 shapes ('degen,safest,anchor'). None = no cycling."""
    if isinstance(mode, str) and ',' in mode:
        parts = [x.strip() for x in mode.split(',') if x.strip()][:3]
        return tuple(parts) if parts and all(x in PHASES for x in parts) else None
    return CYCLE_MODES.get(mode)


def owner_cycle(card, mode, now):
    """🎛 The owner picked a cycle for this tier: it runs NOW — any automatic safe / rescue fix and the streak are cleared."""
    c = {**card}
    if not c.get('cycleFix') and not int(c.get('streak') or 0):
        return c
    c.pop('cycleFix', None); c.pop('fixUntil', None); c['streak'] = 0
    c['events'] = (list(c.get('events') or []) + [{'kind': 'streak', 'at': now, 'why': f'owner picked the {mode} cycle — it runs from the next round'}])[-60:]
    return c


def valid_cycle(mode):
    return mode in CYCLE_MODES or cycle_seq(mode) is not None
DEFAULT_CYCLES = {'safe': 'safe', 'balanced': 'adaptive', 'degen': 'classic', 'next': 'press', 'ever': 'off'}   # every tier cycles its own way
# ⏱ every tier plays ITS OWN round length (so five cards are five different games, and the sims' clocks all get played live)
DEFAULT_CLOCKS = {'degen': 0.08, 'next': 0.25, 'balanced': 0.5, 'ever': 1.0, 'safe': 2.0}
DEFAULT_PAYOUTS = {'safe': 25, 'balanced': 50, 'degen': 0, 'next': 25, 'ever': 75}   # % of every profit take paid straight to the wallet
RUG_LIQ = 0.65  # (was 0.5 — tightened 2026-10-06: a pool that has lost a third of its depth is already being drained) # 🚨 rug shield: pool liquidity at ≤ 65% of entry = being pulled → sell at once
TRAIL_AT, TRAIL_KEEP = 50.0, 5.0   # 🔒 a coin that ran ≥ +50% is sold before it gives it all back (≤ +5% left)
FIX_DAY_PCT = -40.0   # 🔧 a tier card whose DAY falls to −40% gets its config fixed: re-dealt fresh on the safe cycle (logged)
RIDE_AT, RIDE_TRAIL = 150.0, 30.0
RIDE_ATS, RIDE_TRAILS = (0, 10, 15, 20, 25, 50, 100, 150), (5, 8, 10, 15, 20, 30)   # rideAt 0 = off; +10–25% = the owner's 5-min degen lock
# ✋ a level DRAGGED on the chart moves in 1% steps: any whole % inside these ranges is valid next to the editor's lists
STEP_RANGE = {'sl': (5, 50), 'tp': (10, 500), 'rideAt': (5, 200), 'rideTrail': (3, 50)}


def step_ok(key, v):
    """Is `v` a whole percent inside the drag range of `key` (sl · tp · rideAt · rideTrail)?"""
    lo, hi = STEP_RANGE.get(key, (1, 0))
    try:
        return float(v) == int(float(v)) and lo <= float(v) <= hi
    except (TypeError, ValueError):
        return False
KEEP_WINS = (0, 5, 10, 20)   # 🛡 a coin up ≥ this % (or ❄ frozen) is CARRIED into the next shape — a re-shape never sells a winner (0 = off)   # ⚙ Edit Fuse: ❄ freeze a coin running +X% · ⇄ swap it −Y% from its peak   # 🏇 ride a runner from +150%, sell only when it falls 30% from its new high
HOLD_MIN = 80.0      # 🏇 a held coin must stay ≥ +80% (a whole round ≥ +80% also earns a hold); under it → swapped
MIN_CYCLE_COINS = 3  # every cycle shape holds at least 3 coins (else the card keeps its current coins)
STREAK = 3
STREAK_PCT = 3.0   # only a REAL round counts toward a streak: ±0.04% noise on 5-min rounds used to trip the safe fix every 15 min
ADAPT_RED = 3.0   # adaptive: only a round at or below −3% rests in majors (−0.04% noise used to park the card in majors)
SAFE_FIX_ROUNDS = 8   # a losing-streak safe fix lasts this many rounds, then the card returns to its own cycle           # 3 losing rounds → safe config · 3 winning rounds → config locked + best coin frozen for a round
PCT_EPS = 0.05        # match the one-decimal card display: a shown −5.0% must satisfy the owner's −5% boundary


def next_phase(mode, rounds, last_pct):
    """The shape a cycling card deals into next round (None = no phase change)."""
    seq = cycle_seq(mode)
    if not seq:
        return None
    if seq == 'adaptive':
        # a real red round (≤ −3%) rests in majors; small moves stay MIXED (majors + growth coins); a strong round goes degen
        return 'anchor' if _f(last_pct) <= -ADAPT_RED else 'degen' if _f(last_pct) >= 5 else 'mixed'
    if seq == 'auto':   # 🤖 auto: deep red round → breakeven · red → safest · strong green → degen · otherwise mixed
        return 'breakeven' if _f(last_pct) <= -15 else 'safest' if _f(last_pct) <= -ADAPT_RED else 'degen' if _f(last_pct) >= 5 else 'mixed'   # −0.01% is noise, not red
    return seq[int(rounds or 0) % len(seq)]
HIT_PCT = 10.0      # a "good day" = the card is up ≥ +10% over 24h
DEFAULT_CFG = {'on': True, 'sizeUsd': 100.0, 'rotateHours': 1.0, 'rotateCount': 1, 'compound': True, 'paperFeeUsd': 0.01, 'floorPct': 60.0, 'slMode': 'replace',
               'cycles': dict(DEFAULT_CYCLES), 'trail': True, 'payouts': dict(DEFAULT_PAYOUTS), 'compoundStyle': 'smart', 'roundsPerRun': 0,
               'rotateMinDrop': ROTATE_MIN_DROP, 'cycleEvery': 6, 'rescuePct': 50.0, 'rotateConfirm': ROTATE_CONFIRM, 'minHoldMins': MIN_HOLD_MINS,
               'strictRunners': False, 'autoBrain': True}
RUN_ROUNDS = (0, 5, 10, 20, 50)   # rounds per run (0 = one endless run): when a run's rounds are done it closes on the record, the next starts
SL_MODES = ('replace', 'park', 'hold')   # on a stop: auto-replace · sell + park the slot (rebuy at entry with momentum) · hold
# 🃏 Every card plays its OWN exits — no two tiers share them by default. `tierCfg[tier]` overrides the shared paper config for these
# keys (a shared edit of a key = "apply to all cards": it clears that key's per-card overrides). tp / sl 0 = the tier template's.
TIER_KEYS = ('rideAt', 'rideTrail', 'rotateMinDrop', 'rotateConfirm', 'minHoldMins', 'instantSwapPct', 'tp', 'sl', 'trenchCoins')
DEFAULT_TIER_CFG = {
    'degen': {'rideAt': 15.0, 'rideTrail': 8.0, 'rotateConfirm': 2, 'minHoldMins': 10.0, 'instantSwapPct': 15.0, 'rotateMinDrop': 10.0},    # 🔥 5-min hunt
    'next': {'rideAt': 20.0, 'rideTrail': 10.0, 'rotateConfirm': 2, 'minHoldMins': 15.0, 'instantSwapPct': 20.0, 'rotateMinDrop': 15.0},   # ⚡ all runners
    'balanced': {'rideAt': 25.0, 'rideTrail': 15.0, 'rotateConfirm': 3, 'minHoldMins': 30.0, 'instantSwapPct': 0.0, 'rotateMinDrop': 10.0},
    'safe': {'rideAt': 50.0, 'rideTrail': 20.0, 'rotateConfirm': 3, 'minHoldMins': 60.0, 'instantSwapPct': 0.0, 'rotateMinDrop': 20.0},    # 💎 toward 10×
    'ever': {'rideAt': 100.0, 'rideTrail': 30.0, 'rotateConfirm': 4, 'minHoldMins': 120.0, 'instantSwapPct': 0.0, 'rotateMinDrop': 20.0},
}


def clean_exit(k, v):
    """One per-card exit value, validated exactly like the shared config (None = not allowed)."""
    v = _f(v)
    if k == 'rideAt':
        return float(v) if v in RIDE_ATS or step_ok(k, v) else None
    if k == 'rideTrail':
        return float(v) if v in RIDE_TRAILS or step_ok(k, v) else None
    if k == 'rotateMinDrop':
        return max(0.0, min(50.0, v))
    if k == 'rotateConfirm':
        return int(max(1, min(6, v)))
    if k == 'minHoldMins':
        return max(0.0, min(240.0, v))
    if k == 'instantSwapPct':
        return max(0.0, min(50.0, v))
    if k == 'tp':
        return float(v) if v == 0 or v in LEG_TPS or step_ok(k, v) else None
    if k == 'sl':
        return float(v) if v == 0 or v in LEG_SLS or step_ok(k, v) else None
    if k == 'trenchCoins':
        return int(v) if int(v) in TRENCH_COINS else None
    return None


def clean_tier_cfg(p):
    """{tier: {key: value}} — seeded with the unique defaults the first time, then exactly what HQ set (validated)."""
    raw = (p or {}).get('tierCfg')
    if not isinstance(raw, dict):
        return {t: dict(v) for t, v in DEFAULT_TIER_CFG.items()}
    out = {}
    for t in DEFAULT_TIER_CFG:
        row = {}
        for k, v in (raw.get(t) or {}).items() if isinstance(raw.get(t), dict) else ():
            cv = clean_exit(k, v) if k in TIER_KEYS else None
            if cv is not None:
                row[k] = cv
        out[t] = row
    return out


def unique_exits(tier_cfg):
    """🃏 Every card on its OWN exits: a key a card doesn't set comes back as its unique default, and a card whose whole exit set
    copies another card's is put back on its own defaults (the per-tier defaults never collide)."""
    out = {t: {**DEFAULT_TIER_CFG[t], **((tier_cfg or {}).get(t) or {})} for t in DEFAULT_TIER_CFG}
    seen = {}
    for t in DEFAULT_TIER_CFG:
        sig = tuple(_f(out[t].get(k)) for k in TIER_KEYS)
        if sig in seen:
            out[t] = dict(DEFAULT_TIER_CFG[t])
            sig = tuple(_f(out[t].get(k)) for k in TIER_KEYS)
        seen[sig] = t
    return out


CFG_RANGES = {'sizeUsd': (10, 10000), 'rotateHours': (0.08, 48), 'rotateCount': (1, 3), 'paperFeeUsd': (0, 5), 'floorPct': (5, 60), 'instantSwapPct': (0, 50)}


OWNER_OUT_SEC = 6 * 3600   # 🙅 a coin the owner removed by hand is not dealt back onto that card for 6 hours


def owner_out(card, mint, now):
    """Remember that the owner took this coin off the card (kept ≤ 40, old entries dropped)."""
    oo = {m: at for m, at in ((card or {}).get('ownerOut') or {}).items() if now - _f(at) < OWNER_OUT_SEC}
    oo[mint] = now
    card['ownerOut'] = dict(sorted(oo.items(), key=lambda kv: kv[1])[-40:])
    return card


COOL_ROUNDS = 3   # 🧊 a coin that just LEFT a card isn't dealt back into it for 3 rounds (min 15 min) — fresh coins flow in, no buy-back loop
LOSS_COOL_PCT = 8.0     # … where a LOSS means it left at −8% or worse (a scratch exit only sits out the 3 rounds)
LOSS_COOL_SEC = 86400   # 🩸 a coin that left at a LOSS stays out until its price is back above where it was sold (max 24h) — never re-buy a crash


def _stamp(v):
    return v if isinstance(v, dict) else {'at': _f(v)}


REBUY_DIPS = (0, 10, 15, 20)   # 🔁 cfg `rebuyDipPct`: 0 = off
REBUY_DIP_SEC = 86400          # … the rule watches a coin for a day after it left
REBUY_BOUNCE = 3.0             # … and "raised" = at least 3% up off the low it made


def dip_ready(stamp, px, dip_pct):
    """🔁 May a coin that LEFT this card come back? Only after a real dip that is turning: its lowest price since the exit is at
    least `dip_pct` under the exit price AND it now trades ≥ 3% above that low. No price / no low yet = no."""
    ex, low = _f((stamp or {}).get('px')), _f((stamp or {}).get('low'))
    return bool(ex > 0 and low > 0 and _f(px) > 0 and low <= ex * (1 - _f(dip_pct) / 100) and _f(px) >= low * (1 + REBUY_BOUNCE / 100))


def cool_track(card, prices):
    """Keep each cool stamp's LOW (the lowest price seen since the coin left) — `dip_ready` reads it. In place; returns the card."""
    for v in ((card or {}).get('cool') or {}).values():
        if isinstance(v, dict) and v.get('pair'):
            px = _f((prices or {}).get(v['pair']))
            if px > 0 and (not _f(v.get('low')) or px < _f(v['low'])):
                v['low'] = px
    return card


def cooling(card, now, rotate_hours, prices=None, running=()):
    """Mints this card dropped recently (still cooling down), plus loss exits still under their exit price.
    Counted in ROUNDS: a coin that left in round N sits out rounds N+1..N+3 and may come back at N+4 at the earliest (a time window
    alone let a coin sold mid-round back in on the 3rd bell — HIGGS was re-bought "within 3–4 rounds"). Old stamps without a round
    fall back to (COOL_ROUNDS + 1) rounds of time."""
    win = max(900.0, (COOL_ROUNDS + 1) * _f(rotate_hours) * 3600)
    rnd = int((card or {}).get('rounds') or 0)
    # 🚀 `running` = coins that are MOVING right now (up on the hour on real volume). For them only the short "no back-to-back"
    # rule holds: the long ones (left at a loss → out until it recovers, taken off by the owner → 6h) are about coins going
    # nowhere. 2026-10-06: 10 coins cleared every one of the owner's settings and 9 of them were locked out by these two rules —
    # the card "had not moved in an hour" while the coins it had already tried were the ones running.
    run = set(running or ())
    # 🙅 a coin the OWNER swapped out (pick / hand swap) stays out for hours, not rounds: $PENGU was picked off the card three times
    # in one afternoon and the engine brought it back each time as soon as its 3 rounds were up
    out = {m for m, at in ((card or {}).get('ownerOut') or {}).items() if now - _f(at) < (max(win, 1800.0) if m in run else OWNER_OUT_SEC)}
    dip = _f((card or {}).get('rebuyDip'))
    for m, v in ((card or {}).get('cool') or {}).items():
        s = _stamp(v); age = now - _f(s.get('at'))
        # 🔁 NO SAME COIN AGAIN (cfg `rebuyDipPct`, the owner's rule): a coin that left this card in the last day comes back only
        # after a real dip that is turning (`dip_ready`) — running or not. The short "no back-to-back" rule below still applies.
        if dip > 0 and age < REBUY_DIP_SEC and not dip_ready(s, (prices or {}).get(s.get('pair')), dip):
            out.add(m); continue
        by_round = s.get('round') is not None and 'rounds' in (card or {}) and rnd >= int(s['round'])   # a restarted run (rounds back to 0) falls back to time
        if (rnd - int(s['round']) <= COOL_ROUNDS) if by_round else age < win:
            out.add(m)
        elif s.get('loss') and s.get('pct') is not None and age < LOSS_COOL_SEC and _f(s.get('px')) > 0 and m not in run:   # stamps from before `pct` were "any exit under entry": not counted
            px = _f((prices or {}).get(s.get('pair')))
            if not px or px <= _f(s['px']):
                out.add(m)
    return out


def note_dropped(before, after, now, rotate_hours, prices=None):
    """Stamp every coin that left the card this tick (sold / rotated / re-shaped out) with its exit price + whether it lost;
    forget stamps once they can't cool anything any more."""
    if not after:
        return after
    keep = max(900.0, (COOL_ROUNDS + 2) * _f(rotate_hours) * 3600)
    rnd = int(after.get('rounds') or 0)
    held = {l['mint'] for l in after.get('legs') or []}
    # a re-deal / re-shape builds a NEW card dict: the stamps of the card before it must come along, or every cool-down ends there
    # (Human was sold at −18% and bought back two rounds later, straight after a floor re-deal)
    cool = {m: _stamp(v) for m, v in {**((before or {}).get('cool') or {}), **(after.get('cool') or {})}.items()}
    long_ = _f(after.get('rebuyDip')) > 0   # 🔁 the dip rule watches every coin that left for a day
    cool = {m: v for m, v in cool.items() if now - _f(v.get('at')) < (LOSS_COOL_SEC if (v.get('loss') or long_) else keep) or (v.get('round') is not None and rnd - int(v['round']) <= COOL_ROUNDS)}
    for l in (before or {}).get('legs') or []:
        if l['mint'] in held or l.get('symbol') == 'SOL':   # anchors cool too (cbBTC was sold and re-bought 3× in 30 min by re-shapes); SOL is the card's cash
            continue
        px = _f((prices or {}).get(l.get('pairAddress'))) or _f(l.get('entry'))
        # 🩸 a LOSS exit = down LOSS_COOL_PCT or more from entry. A scratch (−1%, a −5% instant swap) is noise: it only sits out
        # the 3 rounds. "Any exit under entry" locked 106 coins out of one card until they made new highs — it had nothing left to buy.
        pct_ = (px / _f(l['entry']) - 1) * 100 if _f(l.get('entry')) > 0 else 0.0
        cool[l['mint']] = {'at': now, 'round': rnd, 'px': px, 'low': px, 'pair': l.get('pairAddress'), 'pct': round(pct_, 2), 'loss': bool(pct_ <= -LOSS_COOL_PCT)}
    return cool_track({**after, 'cool': cool}, prices)


ENTRY_MAX_DROP_5M, ENTRY_MAX_DROP_1H = 3.0, 8.0


def trench_entry(row, mom=None):
    """🗑 SMART ENTRY for a trench drop: not falling right now (`entry_ok`), not mid-spike (5 min ≤ +3% — buys made into a faster
    candle lost 41–77% of the time on the record) and buyers at least 55% when known. No reading = that part is not judged."""
    m = {**((mom or {}).get((row or {}).get('pairAddress')) or {}), **{k: row[k] for k in ('chg5m', 'buyShare') if (row or {}).get(k) is not None}}
    if not entry_ok(row, mom) or (m.get('chg5m') is not None and _f(m['chg5m']) > CHASE_5M_TRENCH):
        return False
    bs = _f(m.get('buyShare')); bs = bs * 100 if 0 < bs <= 1 else bs
    return not (m.get('buyShare') is not None and bs < 55)


CHASE_5M_TRENCH = 3.0


def entry_ok(row, mom=None):
    """🚪 Real money never buys a coin that is FALLING RIGHT NOW: 5-minute move ≤ −3% or 1-hour move ≤ −8% (from the candidate's own
    reading, else the live momentum feed). No reading = not judged (the other gates still apply). The owner's card bought coins on
    the way down and cut them 13–28% lower minutes later — a filter before the buy is cheaper than a stop after it."""
    m = {**((mom or {}).get((row or {}).get('pairAddress')) or {}), **{k: row[k] for k in ('chg5m', 'chg1h') if (row or {}).get(k) is not None}}
    if m.get('chg5m') is not None and _f(m['chg5m']) <= -ENTRY_MAX_DROP_5M:
        return False
    return not (m.get('chg1h') is not None and _f(m['chg1h']) <= -ENTRY_MAX_DROP_1H)


HANDS_OFF_HOURS = (0, 1, 3, 6, 12)   # 🔒 hands-off lock: 0 = off


def hands_off_left(card, now):
    """🔒 Seconds left on the owner's hands-off lock (0 = not locked). While it runs, picks and hand swaps are refused — the engine,
    the stops, the rug shield and selling to cash all keep working. It only keeps the owner's own impulse swaps off the card."""
    return max(0.0, _f((card or {}).get('handsOffUntil')) - now)


def set_hands_off(card, hours, now):
    h = int(_f(hours)) if int(_f(hours)) in HANDS_OFF_HOURS else 0
    c = {**card, 'events': list(card.get('events') or [])}
    if h:
        c['handsOffUntil'] = now + h * 3600
        c['events'].append({'kind': 'hold', 'at': now, 'why': f'🔒 hands-off for {h}h — no picks or hand swaps; the engine and your stops keep working'})
    elif c.pop('handsOffUntil', None):
        c['events'].append({'kind': 'hold', 'at': now, 'why': '🔓 hands-off lock released'})
    return c


def pick_cool(card):
    """Coins the OWNER can't pick back yet → {mint: rounds left}. Only the short rule applies to the owner: a coin that left in the
    last `COOL_ROUNDS` rounds (no back-to-back). The long rules — "left at a loss, out until it recovers" and "you removed it, out 6h"
    — keep the ENGINE from dealing a coin back; they never block the owner's own pick (every pick was being refused: most of the
    lists had been on the card and left at a small loss)."""
    rnd = int((card or {}).get('rounds') or 0)
    out = {}
    for m, v in ((card or {}).get('cool') or {}).items():
        s = _stamp(v)
        if s.get('round') is not None and 0 <= rnd - int(s['round']) <= COOL_ROUNDS:
            out[m] = COOL_ROUNDS + 1 - (rnd - int(s['round']))
    return out


def cool_left(card, mint, now=None, rotate_hours=None, prices=None):
    """Rounds a coin must still sit out before the OWNER may pick / hand-swap it back (0 = free). See `pick_cool`."""
    return int(pick_cool(card).get(mint, 0))


def exit_plan(gain_pct, mom=None):
    """WHEN TO HODL vs SELL, from live momentum (chg1h, buyShare, vol accel = vol5m×12 vs vol1h):
      • 🚀 ride  — strong (1h ≥ +10%, buys ≥ 55%, volume not fading): take out ONLY the original cost (house money) once the
        coin has doubled, else just half the gain — the rest keeps running (this is how a 100×+ is held, not sold at +50%).
      • 🏦 bank  — fading (1h < 0, buys < 45% or volume dying): sell 75% of the coin now.
      • 💰 gain  — otherwise: sell just the gain, keep the cost basis riding.
    Returns (mode, fraction_of_units_to_sell, why). No momentum data → 'gain'."""
    m = mom or {}
    g = max(0.0, _f(gain_pct))
    if not m or g <= 0:
        return 'gain', (g / (100 + g)) if g else 0.0, 'no live momentum — sold the gain'
    ch, bs = _f(m.get('chg1h')), _f(m.get('buyShare'))
    accel = (_f(m.get('vol5m')) * 12 / _f(m.get('vol1h'))) if _f(m.get('vol1h')) else 1.0
    if ch >= 10 and bs >= 55 and accel >= 0.8:
        frac = (100 / (100 + g)) if g >= 100 else (g / (100 + g)) / 2
        return 'ride', frac, f"momentum strong (1h {ch:+.0f}%, {bs:.0f}% buys) — {'took out the original cost, house money rides' if g >= 100 else 'took half the gain, the rest rides'}"
    if ch < 0 or bs < 45 or accel < 0.4:
        return 'bank', 0.75, f"momentum fading (1h {ch:+.0f}%, {bs:.0f}% buys, volume ×{accel:.1f}) — banked 75%"
    return 'gain', g / (100 + g), 'steady momentum — sold the gain, cost keeps riding'


def fading(mom):
    m = mom or {}
    return bool(m) and (_f(m.get('chg1h')) < 0 and _f(m.get('buyShare')) < 50)


def stars(c, role):
    """1–5★ for a candidate. Anchors (real majors) = 5. Pools: 3 + deep (≥$1M) + busy (24h vol ≥ ½ depth). Runners by their
    gated score: ≥88 → 5, ≥75 → 4, ≥60 → 3, else 2 (kept off Prime)."""
    if role == 'anchor':
        return 5
    if role == 'pool':
        liq, vol = _f(c.get('liquidityUsd')), _f(c.get('volume24h'))
        return 3 + (liq >= 1_000_000) + (liq > 0 and vol / liq >= 0.5)
    sc = _f(c.get('score'))
    return 5 if sc >= 88 else 4 if sc >= 75 else 3 if sc >= 60 else 2


def rated(cands, role):
    """Only 3★+ candidates. ARENA-backed coins (on a battle / stage card, this round's runner picks, a lit card — `arena`
    flag set by the service) come first, then best stars; input order kept inside a level."""
    out = [{**c, 'stars': stars(c, role)} for c in cands]
    return sorted((c for c in out if c['stars'] >= MIN_STARS), key=lambda c: (bool(c.get('taken')), not c.get('arena'), -c['stars']))   # 🎲 coins on another tier go last


import card_dna as _dna


def _f(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else 0.0
    except (TypeError, ValueError):
        return 0.0


def at_or_below_loss(price, entry, threshold):
    """Honor the owner's exact loss boundary despite binary floating-point representation."""
    p, e = _f(price), _f(entry)
    return p > 0 and e > 0 and (p / e - 1) * 100 <= -_f(threshold) + PCT_EPS


def clean_cfg(p):
    out = dict(DEFAULT_CFG)
    for k, (lo, hi) in CFG_RANGES.items():
        if k in (p or {}):
            out[k] = min(hi, max(lo, _f(p[k])))
    if (p or {}).get('floorPct') is not None and _f(p['floorPct']) == 0:
        out['floorPct'] = 0.0   # 🧱 0 = card floor OFF (the owner's switch; every other value is clamped to its range)
    out['rotateHours'], out['rotateCount'] = round(float(out['rotateHours']), 2), int(out['rotateCount'])
    for k in ('on', 'compound'):
        if k in (p or {}):
            out[k] = bool(p[k])
    if (p or {}).get('slMode') in SL_MODES:
        out['slMode'] = p['slMode']
    cyc = (p or {}).get('cycles') if isinstance((p or {}).get('cycles'), dict) else {}
    out['cycles'] = {t: (cyc.get(t) if valid_cycle(cyc.get(t)) else DEFAULT_CYCLES.get(t, 'off')) for t in DEFAULT_CYCLES}
    out['rotateMinDrop'] = max(0.0, min(50.0, _f((p or {}).get('rotateMinDrop', ROTATE_MIN_DROP))))
    out['rideAt'] = float(_f((p or {}).get('rideAt'))) if (p or {}).get('rideAt') is not None and (_f((p or {}).get('rideAt')) in RIDE_ATS or step_ok('rideAt', (p or {}).get('rideAt'))) else RIDE_AT
    out['keepWinPct'] = float(_f((p or {}).get('keepWinPct'))) if (p or {}).get('keepWinPct') is not None and _f((p or {}).get('keepWinPct')) in KEEP_WINS else 5.0
    out['rideTrail'] = float(_f((p or {}).get('rideTrail'))) if (_f((p or {}).get('rideTrail')) in RIDE_TRAILS or step_ok('rideTrail', (p or {}).get('rideTrail'))) else RIDE_TRAIL
    rsc = _f((p or {}).get('rescuePct', -RESCUE_PCT))
    out['rescuePct'] = 0.0 if (p or {}).get('rescuePct') is not None and rsc == 0 else max(20.0, min(80.0, rsc))   # 0 = rescue off
    out['rotateConfirm'] = int(max(1, min(6, _f((p or {}).get('rotateConfirm', ROTATE_CONFIRM)))))
    out['minHoldMins'] = max(0.0, min(240.0, _f((p or {}).get('minHoldMins', MIN_HOLD_MINS))))
    ck = (p or {}).get('clocks') if isinstance((p or {}).get('clocks'), dict) else {}
    out['clocks'] = {t: (round(min(48.0, max(0.08, _f(ck[t]))), 2) if _f(ck.get(t)) > 0 else DEFAULT_CLOCKS[t]) for t in DEFAULT_CLOCKS}
    out['peakSellPct'] = float(_f((p or {}).get('peakSellPct'))) if _f((p or {}).get('peakSellPct')) in PEAK_SELLS else PEAK_SELL
    out['skimAt'] = float(_f((p or {}).get('skimAt'))) if _f((p or {}).get('skimAt')) in SKIM_ATS else 0.0
    out['tpStakeUsd'] = float(_f((p or {}).get('tpStakeUsd'))) if (p or {}).get('tpStakeUsd') is not None and _f((p or {}).get('tpStakeUsd')) in TP_STAKES else TP_STAKE_USD
    out['skimTo'] = (p or {}).get('skimTo') if (p or {}).get('skimTo') in SKIM_TOS else 'card'
    out['stackSkimUsd'] = float(_f((p or {}).get('stackSkimUsd'))) if _f((p or {}).get('stackSkimUsd')) in STACK_SKIMS else 0.0   # 💚 full stack: each locked coin keeps this $
    out['skimHoldRounds'] = int(_f((p or {}).get('skimHoldRounds'))) if int(_f((p or {}).get('skimHoldRounds'))) in SKIM_HOLDS else 2
    out['recyclePct'] = float(_f((p or {}).get('recyclePct'))) if _f((p or {}).get('recyclePct')) in RECYCLE_PCTS else 0.0
    out['recycleEvery'] = int(_f((p or {}).get('recycleEvery'))) if int(_f((p or {}).get('recycleEvery'))) in RECYCLE_EVERY else 3
    out['lockBankPct'] = float(_f((p or {}).get('lockBankPct'))) if (p or {}).get('lockBankPct') is not None and _f((p or {}).get('lockBankPct')) in LOCK_BANKS else LOCK_BANK
    out['runnerMinLiqK'] = int(_f((p or {}).get('runnerMinLiqK'))) if int(_f((p or {}).get('runnerMinLiqK'))) in RUNNER_LIQS else 0   # 🏊 real money buys a runner only in a pool this deep ($K); 0 = the keeper's own floor
    out['runnerMinBuy'] = int(_f((p or {}).get('runnerMinBuy'))) if int(_f((p or {}).get('runnerMinBuy'))) in RUNNER_BUYS else 0
    out['edgeFloor'] = int(_f((p or {}).get('edgeFloor'))) if int(_f((p or {}).get('edgeFloor'))) in EDGE_FLOORS else 0
    out['runnerMinVolK'] = int(_f((p or {}).get('runnerMinVolK'))) if int(_f((p or {}).get('runnerMinVolK'))) in RUNNER_VOLS else 0
    out['runnerMinChg1h'] = int(_f((p or {}).get('runnerMinChg1h'))) if int(_f((p or {}).get('runnerMinChg1h'))) in RUNNER_MOMS else 0
    out['pickVerify'] = bool((p or {}).get('pickVerify', True))   # ✅ a hand-picked young coin goes on a real card only once it passes every safety check
    ra_ = (p or {}).get('runnerMinAgeH')
    out['runnerMinAgeH'] = int(_f(ra_)) if ra_ is not None and int(_f(ra_)) in RUNNER_AGES else int(REAL_RUNNER_AGE_H)   # 🕐 the OWNER's youngest launch coin for real money
    out['rebuyDipPct'] = int(_f((p or {}).get('rebuyDipPct'))) if int(_f((p or {}).get('rebuyDipPct'))) in REBUY_DIPS else 0   # 🔁 a coin that left comes back only after this dip (0 = off)
    out['youngTicket'] = bool((p or {}).get('youngTicket', True))   # 🎟 a hand pick under 12h old goes in as a small ticket (owner's switch)
    out['scoutPct'] = int(_f((p or {}).get('scoutPct'))) if int(_f((p or {}).get('scoutPct'))) in SCOUT_PCTS else 0   # 🔭 scout ticket, % of the card (0 = off)
    out['trenchAuto'] = bool((p or {}).get('trenchAuto', True))   # 🗑 may the ENGINE seat a trench coin by itself? off = trench coins are the owner's hand picks only
    out['upMeta'] = bool((p or {}).get('upMeta', True))          # 🧭 the engine's own buys need a readable chart that is not trending down
    out['trailStep'] = bool((p or {}).get('trailStep', False))   # 🪜 a rider's trail widens as its peak gain grows
    out['comeback'] = bool((p or {}).get('comeback', True))      # 🔁 a rider that left is bought back when its dip recovers 15%
    out['newOnly'] = bool((p or {}).get('newOnly', False))   # 🆕 the engine fills seats with launch coins only — no majors, no old pools (the owner's own picks are untouched)
    out['moverSwap'] = bool((p or {}).get('moverSwap', True))   # 🚀 a mover takes the seat of a coin that is not moving
    out['edgeGate'] = bool((p or {}).get('edgeGate', True))   # 🧠 real money buys only runners the board's own record does not expect to lose (pick_edge.py)
    out['swapEdge'] = bool((p or {}).get('swapEdge', True))   # ⚖ rotate only when the next coin beats this one by more than the swap costs
    out['swapCapHr'] = int(_f((p or {}).get('swapCapHr'))) if int(_f((p or {}).get('swapCapHr'))) in SWAP_CAPS else 0   # 🤖 0 = auto
    out['coins'] = int(_f((p or {}).get('coins'))) if int(_f((p or {}).get('coins'))) in COIN_COUNTS else 0   # 🪙 0 = auto (size-aware), else the OWNER's count
    out['floorRestMins'] = float(_f((p or {}).get('floorRestMins'))) if _f((p or {}).get('floorRestMins')) in FLOOR_RESTS else 0.0
    out['strictRunners'] = bool((p or {}).get('strictRunners', False))
    out['autoBrain'] = bool((p or {}).get('autoBrain', True))   # 🔧 engine self-fix from the sim brain (HQ can switch it off)   # HQ: rescue when the card is this % under its start
    ce = (p or {}).get('cycleEvery')
    out['cycleEvery'] = 0 if ce is not None and int(_f(ce)) == 0 else int(_f(ce)) if int(_f(ce)) in CYCLE_EVERY else 6   # 0 = never re-shape
    if 'trail' in (p or {}):
        out['trail'] = bool(p['trail'])
    pay = (p or {}).get('payouts') if isinstance((p or {}).get('payouts'), dict) else {}
    out['payouts'] = {t: (int(pay[t]) if pay.get(t) in _dna.PAYOUTS else DEFAULT_PAYOUTS[t]) for t in DEFAULT_PAYOUTS}
    out['compoundStyle'] = (p or {}).get('compoundStyle') if (p or {}).get('compoundStyle') in ('smart', 'even') else 'smart'
    out['roundsPerRun'] = int(_f((p or {}).get('roundsPerRun'))) if int(_f((p or {}).get('roundsPerRun'))) in RUN_ROUNDS else 0
    out['trenchCoins'] = trench_n(p)
    ts_ = (p or {}).get('trenchStakePct')
    out['trenchStakePct'] = int(_f(ts_)) if ts_ is not None and int(_f(ts_)) in TRENCH_STAKES else 15   # 🎟 a trench coin's ticket, % of the card (0 = a full equal seat)
    tl_ = (p or {}).get('trenchSlPct')
    out['trenchHouseAt'] = int(_f((p or {}).get('trenchHouseAt'))) if int(_f((p or {}).get('trenchHouseAt'))) in HOUSE_ATS else 0   # 🏠 a trench / ticket coin's initial comes out at this gain (0 = off)
    out['trenchSlPct'] = int(_f(tl_)) if tl_ is not None and int(_f(tl_)) in TRENCH_SLS else 25         # … and its own stop (0 = the card's)
    out['tp'] = clean_exit('tp', (p or {}).get('tp')) or 0.0   # 🎯 card-level TP / SL (0 = the tier template's)
    out['sl'] = clean_exit('sl', (p or {}).get('sl')) or 0.0
    out['tierCfg'] = clean_tier_cfg(p)
    return out


GAP_PCT, GAP_SECS, AGREE_PCT = 50.0, 90.0, 10.0


def price_agrees(cand, prices):
    """A candidate may be bought only when the scan's price and the live price feed agree within AGREE_PCT. A coin whose two prices
    disagree is bought at one and marked at the other: it read −87% the moment it landed and was dumped. No live price yet = allowed."""
    live = _f((prices or {}).get(cand.get('pairAddress'))); scan = _f(cand.get('price'))
    return live <= 0 or scan <= 0 or abs(live / scan - 1) * 100 <= AGREE_PCT


def safe_anchor(l):
    """An anchor the engine never stops, rotates or rug-checks = an ESTABLISHED major. A new major sitting in an anchor seat keeps
    every protection a runner has (stop, instant swap, rug shield): it can still go to zero."""
    # 🎯 a coin the OWNER picked into the anchor seat is not a major either: $HODL sat there with no stop and no instant swap and was
    # down 54% ten minutes later. Only the engine's own established majors are exempt.
    return l.get('role') == 'anchor' and not l.get('newMajor') and not l.get('picked')


# 🧪 EVERY PAPER CARD IS ITS OWN EXPERIMENT (owner, 2026-10-07: "all paper needs unique coins and configs"). The exits were already
# each card's own (`DEFAULT_TIER_CFG`); the SELECTION was the same picker five times, so the cards held the same coins and proved
# nothing about what to buy. Each paper tier now picks by a different rule, and no coin sits on two cards (`unique_rows`):
#   💎 safe → 🚀 runner hunt (older coins already running on real volume) · 🥇 balanced → 🎯 sniper (record-backed, deep pool,
#   buyers in control) · ⚡ next → 👤 picks like the owner (pick_style) · ♾ ever → majors + stocks · 🔥 degen → the engine's order.
DEFAULT_TIER_PICK = {
    'safe': {'pickStyle': 'hunt', 'runnerMinAgeH': 12, 'runnerMinLiqK': 25, 'runnerMinVolK': 50, 'runnerMinChg1h': 40, 'runnerMinBuy': 0, 'edgeGate': False},
    'balanced': {'pickStyle': 'sniper', 'runnerMinAgeH': 12, 'runnerMinLiqK': 50, 'runnerMinVolK': 0, 'runnerMinChg1h': 0, 'runnerMinBuy': 65, 'edgeGate': True, 'edgeFloor': 3},
    'next': {'pickStyle': 'human'},
    'ever': {'pickStyle': 'majors'},
    'degen': {'pickStyle': 'engine'},
}
PICK_STYLES = {'hunt': '🚀 runner hunt', 'sniper': '🎯 sniper', 'human': '👤 picks like you', 'majors': '🪙 majors', 'engine': '🧠 engine order'}


def unique_rows(rows, taken):
    """Candidates no OTHER card holds (`taken` = their mints). An empty result stays empty — the seat waits rather than copy a card."""
    return [x for x in rows or [] if x.get('mint') not in (taken or ())]


def shared_leg(card, taken):
    """The first coin on this card that another card also holds → its pairAddress, or None. Never SOL (cash-like), a placeholder,
    a coin still being bought, a frozen / riding coin or the owner's pick."""
    for l in (card or {}).get('legs') or []:
        if l.get('mint') in (taken or ()) and l.get('symbol') != 'SOL' and not (l.get('placeholder') or l.get('buying') or l.get('frozen') or l.get('ride') or l.get('picked')):
            return l.get('pairAddress')
    return None


def tier_cfg(cfg, tid):
    """The shared paper config as ONE tier plays it: its own round clock (`clocks[tier]`). Locked tiers and the real card have their
    own whole config and never go through here."""
    hours = _f(((cfg or {}).get('clocks') or {}).get(tid))
    own = ((cfg or {}).get('tierCfg') or {}).get(tid) or {}   # 🃏 this card's own exits
    out = {**(cfg or {}), **(DEFAULT_TIER_PICK.get(tid) or {}), **{k: v for k, v in own.items() if k in TIER_KEYS}}
    return {**out, 'rotateHours': hours} if hours > 0 else out


# 💵 REAL-MONEY GUARD — hard floors the real card's config can never go under, whatever HQ or the self-fix writes.
# A real round trip costs ~2% (impact + slippage + network fee), so a rule that swaps on a 5% dip turns noise into loss:
# a $7 card once made 350 real swaps in 39h on a 5-min clock with no hold time and a −5% instant swap. The 5-min clock stays
# (protection + rides still run every tick); what is floored is how fast a coin may be flipped back out.
REAL_MIN_HOLD = 10.0      # minutes a real buy is held before a ROUND rotation may sell it (clocks ≤ 15 min) = 2 rounds of 5 min.
                          # ⚡ instant swap, stops and the rug shield are never delayed by it.
REAL_MIN_CONFIRM = 2      # losing rounds in a row before a real rotation (the owner's degen setting: 2 rounds on a 5-min clock)
REAL_MIN_INSTANT = 10.0   # ⚡ instant swap is OFF (0) or at least −10% — never inside normal memecoin noise
REAL_OWNER_RESHAPE = 3    # … unless the OWNER set it: their own 3 is kept (a fix still re-shapes every 6)
REAL_MAX_RESHAPE = 6      # a real card re-shapes at most every 6 rounds (0 = never stays never) — also while a safe / rescue fix is on
REAL_MIN_COIN_USD = 0.75  # a real coin under this pays > 0.7% per swap in flat costs → small cards hold fewer, bigger coins
REAL_DEAL_LEAD = 15.0     # seconds before the bell that a real card's round is decided (sells, then buys, finish inside the countdown)
COIN_COUNTS = (0, 2, 3, 4, 5, 6)   # coins on a card: 0 = auto by size · or exactly what the owner picks, at ANY card size
FLOOR_RESTS = (0, 15, 30, 60)   # 🛌 minutes a floored card rests in its anchors before the re-deal — the OWNER's switch (0 = no rest, re-deal at once)
RUNNER_LIQS = (0, 25, 50, 100)   # owner's runner pool floor for real money, $K (Edit Fuse › Rounds). The replay's losers sat in pools under $50K.


RUNNER_BUYS = (0, 55, 60, 65, 70)   # … and only while buyers are at least this share of its last hour's trades (0 = the board's own gate)
EDGE_FLOORS = (0, 3, 6)             # … and only when the record's estimate for coins like it is at least +this % (0 = just not negative)


RUNNER_VOLS = (0, 20, 50, 100)      # … and only with at least this much traded in the last hour ($K)
RUNNER_MOMS = (0, 20, 40)           # … and only while it is up at least this much on the hour (🚀 Runner hunt: +40% on real volume)


RUNNER_AGES = (0, 1, 6, 12)         # youngest launch coin real money may buy, hours (owner's setting; 12 = the replay-backed default)
MOVER_VOL1H = 50_000.0             # a "mover" when the card has no hunt selection of its own: ≥ $50K traded in the hour …
MOVER_CHG1H = 20.0                 # … and up ≥ 20% on it
FLAT_BAND = 10.0                   # a coin within ±10% of its entry …
FLAT_HOLD_SEC = 1200.0             # … after at least 20 minutes on the card is "not moving"
MOVER_EVERY_SEC = 1800.0           # at most one mover upgrade per card per 30 minutes


def movers(rows, cfg):
    """Runner candidates that are MOVING right now: the card's own 🚀 hunt selection when it has one, else ≥ $50K traded in the
    hour and up ≥ 20% on it. Best 1h move first."""
    hunt = _f((cfg or {}).get('runnerMinVolK')) > 0 and _f((cfg or {}).get('runnerMinChg1h')) > 0
    ok = (lambda x: is_hunt(x, cfg)) if hunt else (lambda x: _f(x.get('vol1h')) >= MOVER_VOL1H and x.get('chg1h') is not None and _f(x.get('chg1h')) >= MOVER_CHG1H)
    return sorted((x for x in rows or [] if not x.get('trenchOnly') and ok(x)), key=lambda x: -_f(x.get('chg1h')))


def flat_leg(card, prices, now, hold_sec=FLAT_HOLD_SEC, band=FLAT_BAND):
    """🚀 The seat a mover may take: a runner-seat coin that is NOT moving — within ±`band`% of its entry after `hold_sec` on the
    card. Never a riding / frozen / owner-picked / trench coin, one waiting on its buy or with a queued pick. Flattest first; None."""
    out = []
    for l in (card or {}).get('legs') or []:
        px = _f((prices or {}).get(l.get('pairAddress')))
        if (l.get('role') != 'runner' or l.get('ride') or l.get('frozen') or l.get('picked') or l.get('trench') or l.get('buying')
                or l.get('swapTo') or px <= 0 or _f(l.get('entry')) <= 0 or now - _f(l.get('at')) < hold_sec):
            continue
        g = (px / _f(l['entry']) - 1) * 100
        if abs(g) <= band:
            out.append((abs(g), l))
    return min(out, key=lambda t: t[0])[1] if out else None


# 🔭 SCOUT & PROMOTE (the owner's ask: "5 min should be cycling funds around to find the banger coins to hold through rounds").
# One seat is the SCOUT: a small ticket (`scoutPct` of the card) that hops onto whatever is moving, round after round, while the
# other seats HOLD (🍳 min hold). A scout that proves itself is PROMOTED: it becomes a holder at full size, and the weakest holder's
# seat becomes the next scout. So the fast clock searches with small money and only winners ever get real size.
SCOUT_PCTS = (0, 10, 15, 20)   # ticket, % of the card (0 = off)
SCOUT_PROMOTE = 20.0           # a scout up this much since it was bought is promoted to a holder
SCOUT_CUT = 10.0               # a scout down this much hops to the next mover at once
SCOUT_ROUNDS = 3               # … and so does one that has not reached +5% after this many rounds


def _gain(l, prices):
    px = _f((prices or {}).get(l.get('pairAddress')))
    return (px / _f(l['entry']) - 1) * 100 if px > 0 and _f(l.get('entry')) > 0 else 0.0


def scout_step(card, prices, hot, cfg, now, pools=(), anchors=()):
    """One scout decision for a card → the card (unchanged when there is nothing to do). `hot` = movers not on the card, best first.
    promote (≥ +SCOUT_PROMOTE) → cut / hop (≤ −SCOUT_CUT, or SCOUT_ROUNDS rounds without +5%) → open the first scout seat from the
    coin that is not moving. Every swap goes through `replace_leg` (true fills, events). Pure."""
    pct = _f((cfg or {}).get('scoutPct'))
    if pct <= 0 or card.get('holdAll') or card.get('flooredAt'):
        return card
    legs = card.get('legs') or []
    val = lambda l: _f(l.get('units')) * (_f(prices.get(l['pairAddress'])) or _f(l.get('entry')))
    total = sum(val(l) for l in legs) + max(0.0, _f(card.get('cash')))
    ticket = total * pct / 100
    rot = max(60.0, _f(cfg.get('rotateHours')) * 3600)
    on = {l['mint'] for l in legs}
    hot = [x for x in hot or [] if x.get('mint') not in on and _f(x.get('price')) > 0]
    sc = next((l for l in legs if l.get('scout')), None)

    def hop(c, pair, why, keep_scout=True):
        """Swap the coin at `pair` for the best mover as a scout-sized ticket; what is left of its money returns to card cash."""
        nc = replace_leg(c, pair, prices, list(pools), hot, list(anchors), cfg, now)
        nl = next(l for l in nc['legs'] if l['mint'] not in {x['mint'] for x in c['legs']})
        v = _f(nl['units']) * _f(nl['entry'])
        if v > ticket * 1.05 and v > 0:
            k = ticket / v
            nc['cash'] = round(_f(nc.get('cash')) + v - ticket, 6); nl['units'] = _f(nl['units']) * k; nl['costUsd'] = round(_f(nl.get('costUsd')) * k, 6)
        if keep_scout:
            nl['scout'] = True
        nc['events'] = nc['events'][:-1] + [{**nc['events'][-1], 'kind': 'rotate', 'why': why.format(sym=nl.get('symbol'), usd=_f(nl['units']) * _f(nl['entry']))}]
        return nc

    if sc:
        g = _gain(sc, prices)
        if g >= SCOUT_PROMOTE:   # 🏅 proven: it holds from now on (its 🍳 hold starts now); the weakest holder's seat scouts next
            c = {**card, 'legs': [({k: v for k, v in l.items() if k != 'scout'} | {'at': now, 'promotedAt': now}) if l is sc else dict(l) for l in legs],
                 'events': list(card.get('events') or []) + [{'at': now, 'kind': 'ride', 'symbol': sc.get('symbol'), 'usd': round(val(sc), 4),
                                                             'why': f"🏅 scout ${sc.get('symbol')} is up {g:+.0f}% — promoted to a holder"}]}
            weak = sorted((l for l in c['legs'] if l['mint'] != sc['mint'] and l.get('role') == 'runner' and not (l.get('ride') or l.get('frozen') or l.get('picked') or l.get('buying') or l.get('trench'))),
                          key=lambda l: _gain(l, prices))
            if weak and hot and _gain(weak[0], prices) < g:
                try:
                    before = _f(c.get('cash'))
                    c = hop(c, weak[0]['pairAddress'], "🔭 new scout ${sym} (${usd:.2f} ticket) takes the weakest seat — its money backs the promoted coin")
                    freed = _f(c.get('cash')) - before
                    pl = next(l for l in c['legs'] if l['mint'] == sc['mint']); ppx = _f(prices.get(pl['pairAddress'])) or _f(pl['entry'])
                    if freed > 0.01 and ppx > 0:   # the promoted coin gets the size the weak seat gave up
                        pl['units'] = _f(pl['units']) + freed / ppx; pl['costUsd'] = round(_f(pl.get('costUsd')) + freed, 6); c['cash'] = round(before, 6)
                except (ValueError, StopIteration):
                    pass
            return c
        stale = now - _f(sc.get('at')) >= SCOUT_ROUNDS * rot and g < 5
        if (g <= -SCOUT_CUT or stale) and hot:
            try:
                return hop(card, sc['pairAddress'], f"🔭 scout ${sc.get('symbol')} {'cut at ' + format(g, '+.0f') + '%' if g <= -SCOUT_CUT else 'went nowhere (' + format(g, '+.0f') + '%)'} — hops to ${{sym}} (${{usd:.2f}} ticket)")
            except (ValueError, StopIteration):
                return card
        return card
    fl = flat_leg(card, prices, now, max(FLAT_HOLD_SEC, _f(cfg.get('minHoldMins')) * 60)) if hot else None
    if fl:
        try:
            return hop(card, fl['pairAddress'], f"🔭 scout seat opened: ${fl.get('symbol')} was not moving — ${{sym}} goes in as a ${{usd:.2f}} ticket")
        except (ValueError, StopIteration):
            return card
    return card


# ⚡ META BY CLOCK — one coherent setup per round length, built from what this engine's own record showed (2026-10-06):
#   • exits inside 15 min were the leak (49 of 71, −$1.43) and scratch exits locked coins out → no instant swap on noise, a short hold
#   • trims of winners were the only steady plus (+$3.21, 80% won) → the SCALPER takes profit early and often
#   • the board's runners need ~3.5h to peak → the HOLDER freezes late, trails wide and holds
#   • selection decides more than exits → both buy only coins already moving on real volume, new coins only
# 5–10 min rounds = 🗡 META SCALPER: a 20% scout ticket hunts every round; everything else locks fast (+15%, 8% trail), banks a
# third at the lock, skims +20%, stops at −15%, holds 15 min so one candle cannot shake it out.
# 15 min and longer = 💎 META HOLDER: 10% scout, freeze +50% / 30% trail, no skim, stop −30%, hold 1–3h by clock, older coins.
# Every card gets its OWN variant (`seed`): the same idea with slightly different numbers, so no two cards trade in lockstep.
META_SCALP = {'trailStep': True, 'comeback': True, 'scoutPct': 20, 'rideAt': 15.0, 'rideTrail': 8.0, 'lockBankPct': 33.0, 'peakSellPct': 75.0, 'skimAt': 20.0, 'recyclePct': 0.0, 'sl': 15.0, 'tp': 100.0,
              'instantSwapPct': 0.0, 'rotateMinDrop': 10.0, 'minHoldMins': 15.0, 'cycleEvery': 6, 'newOnly': True, 'moverSwap': True,
              'runnerMinAgeH': 1, 'runnerMinLiqK': 25, 'runnerMinVolK': 50, 'runnerMinChg1h': 20, 'runnerMinBuy': 55, 'edgeGate': False, 'edgeFloor': 0}
META_HOLD = {'trailStep': False, 'comeback': True, 'scoutPct': 10, 'rideAt': 50.0, 'rideTrail': 30.0, 'lockBankPct': 0.0, 'peakSellPct': 50.0, 'skimAt': 0.0, 'recyclePct': 0.0, 'sl': 30.0, 'tp': 300.0,
             'instantSwapPct': 0.0, 'rotateMinDrop': 20.0, 'minHoldMins': 60.0, 'cycleEvery': 6, 'newOnly': True, 'moverSwap': True,
             'runnerMinAgeH': 12, 'runnerMinLiqK': 25, 'runnerMinVolK': 50, 'runnerMinChg1h': 40, 'runnerMinBuy': 0, 'edgeGate': False, 'edgeFloor': 0}
META_VARIANTS = {'scalp': ({}, {'rideAt': 20.0, 'rideTrail': 10.0}, {'scoutPct': 15, 'skimAt': 30.0}, {'lockBankPct': 25.0, 'rideTrail': 10.0}),
                 'hold': ({}, {'rideTrail': 20.0, 'scoutPct': 15}, {'rideAt': 100.0}, {'runnerMinChg1h': 20, 'rideTrail': 20.0})}


def meta_for(rotate_hours, seed=0):
    """⚡ The meta setup for a round length → {key, name, why, patch}. `seed` picks the card's own variant (0 = the base numbers).
    The patch never sets the clock or the round patience — those stay the owner's."""
    mins = _f(rotate_hours) * 60
    scalp = 0 < mins <= 10
    base, var = (META_SCALP, META_VARIANTS['scalp']) if scalp else (META_HOLD, META_VARIANTS['hold'])
    patch = {**base, **var[int(seed) % len(var)]}
    if not scalp:
        patch['minHoldMins'] = 60.0 if mins <= 30 else 120.0 if mins <= 60 else 180.0
    return {'key': 'scalp' if scalp else 'hold', 'name': '🗡 Meta scalper' if scalp else '💎 Meta holder', 'variant': int(seed) % len(var), 'patch': patch,
            'why': ('A scout ticket hunts every round; the rest lock gains fast (+%g%%, %g%% trail), bank at the lock, skim, and stop at −%g%%. No exit on one bad candle.'
                    % (patch['rideAt'], patch['rideTrail'], patch['sl'])) if scalp else
                   ('Buys coins already running, then gets out of their way: freeze +%g%%, %g%% trail, no skim, stop −%g%%, held at least %g min.'
                    % (patch['rideAt'], patch['rideTrail'], patch['sl'], patch['minHoldMins']))}


TRAIL_STEPS = ((80.0, 25.0), (30.0, 15.0))   # peak gain ≥ +80% → at least a 25% trail · ≥ +30% → at least 15%


def trail_for(base, peak_gain_pct):
    """🪜 STEPPED TRAIL: a rider's trail widens as its PEAK gain grows — tight while it is a small winner (the scalper's 8%), wider
    once it has really run, so a coin at +90% is not shaken out by the same 8% wiggle that protects a +16% one. Never tighter than
    the owner's own trail. (2026-10-06: $SNDWITCH was trimmed twice and swapped out on 8% dips on its way to +128%.)"""
    for at, rt in TRAIL_STEPS:
        if _f(peak_gain_pct) >= at:
            return max(_f(base), rt)
    return _f(base)


COMEBACK_SEC = 2 * 3600.0   # how long a rider that left is watched for a comeback
COMEBACK_UP = 15.0          # … and how far off its dip low it must recover to be bought back
COMEBACK_DEAD = 0.6         # a coin that fell 60% under its exit is not a dip, it is over


def comeback_note(store, before, after, prices, now):
    """🔁 Remember every RIDER that just left the card (its ride ended) → {mint: {pair, symbol, exit, low, at}}. Pure."""
    out = {m: dict(v) for m, v in (store or {}).items()}
    held = {l['mint'] for l in (after or {}).get('legs') or []}
    for l in (before or {}).get('legs') or []:
        if l['mint'] in held or not (l.get('ride') or l.get('rideFrom')):
            continue
        px = _f((prices or {}).get(l.get('pairAddress'))) or _f(l.get('high')) * 0.9
        if px > 0:
            out[l['mint']] = {'pair': l.get('pairAddress'), 'symbol': l.get('symbol'), 'exit': px, 'low': px, 'at': now}
    return out


def comeback_step(store, px_by_mint, now, up=COMEBACK_UP):
    """🔁 One look at the riders being watched → (store, ready {mint: % off its dip low}). The low is tracked; a coin is READY when
    it really dipped (≥ 3% under its exit) and has come back `up`% off that low. Dropped after COMEBACK_SEC, or when it fell
    COMEBACK_DEAD under its exit (not a dip — over). No price for a coin = it just waits."""
    keep, ready = {}, {}
    for m, v in (store or {}).items():
        if now - _f(v.get('at')) > COMEBACK_SEC:
            continue
        px = _f((px_by_mint or {}).get(m))
        if px <= 0:
            keep[m] = v; continue
        if px < _f(v['exit']) * (1 - COMEBACK_DEAD):
            continue
        low = min(_f(v.get('low')) or px, px)
        keep[m] = {**v, 'low': low}
        if low < _f(v['exit']) * 0.97 and px >= low * (1 + up / 100):
            ready[m] = round((px / low - 1) * 100, 1)
    return keep, ready


def flow_tag(x):
    """What a candidate looks like RIGHT NOW, in one tag → (tag, points). Entry setups first (5m / 1h / buyers), then its own chart
    (chart_read keys on the row): swept the low and came back · dip bought in an up-trend · trending up · at its highs · no chart yet.
    The real card's last 119 buys (2026-10-06): 99 had a chart too short to read and lost $1.01 (25% won); the 20 with a readable
    chart were +$0.07 (40% won) — so "no chart yet" ranks last, whatever its hourly move says."""
    if x.get('comeback'):
        return f"🔁 comeback: +{_f(x['comeback']):.0f}% off its dip", 95.0
    st = entry_setup(x)
    if st:
        ic, name, _ = ENTRY_SETUPS[st[0]]
        return f"{ic} {name.lower()}", 60 + st[1] * 0.4
    if x.get('cBars') is not None and not x.get('cBars'):
        return '🆕 no chart yet', 0.0
    if x.get('cBars'):
        pull, pos, up = _f(x.get('cPull')), _f(x.get('cPos')), x.get('cStruct') == 'up'
        if x.get('cFvg') == 'in' and up:
            return '🪜 back in its gap, trend up', 70.0
        if up and 5 <= pull <= 15:
            return '🧲 dip bought, trend up', 75.0
        if at_high(x) and x.get('cStruct') != 'down':
            return '🏔 at its highs', 40.0
        if up:
            return '📈 trending up', 62.0
        if pos >= 0.66 and x.get('cStruct') != 'down':
            return '⛰ upper range', 50.0
        if x.get('cStruct') == 'down':
            return '📉 trending down', 10.0
        return '➖ ranging', 35.0
    return '', 30.0


def flow_rank(rows):
    """Candidates in the order the card should take them: by `flow_tag` points plus a little for the size of the hourly move
    (capped — a +700% hour is a launch candle, not three times better than +60%). Adds `tag` to each row."""
    out = []
    for i, x in enumerate(rows or []):
        tag, pts = flow_tag(x)
        out.append((-(pts + min(25.0, max(0.0, _f(x.get('chg1h'))) / 4)), i, {**x, 'tag': tag}))
    return [x for _, _, x in sorted(out, key=lambda t: (t[0], t[1]))]


META_MIN_POS = 0.34
META_MIN_PULL = 5.0    # 🏔 closer than this % to its 4h high = AT ITS HIGHS: the engine waits for the dip, it never buys the top


def at_high(x):
    """Is the coin sitting at its highs (less than `META_MIN_PULL`% under its 4h high)? No chart reading = not judged."""
    return bool((x or {}).get('cBars')) and x.get('cPull') is not None and _f(x.get('cPull')) < META_MIN_PULL
META_WILD_PCT = 35.0   # = chart_read.WILD_PCT


# 🔥 DON'T CHASE. The board's own record (2026-10-06, 184 judged picks, typical result 3 hours later) by what the coin was doing at
# the buy: 5-min move −3…0% → +3% · 0…+3% → 0% · +3…+10% → −41% · over +10% → −77%; 1-hour move 0…+30% → +3…+6% · +30…+100% → −14%
# · over +100% → −55% (85 picks). Buying INTO the candle is the single worst entry on the record; that afternoon the owner's hand
# picks bought mid-spike lost 15–29% inside 1–5 minutes ($DEXPAD −29% in one minute, $BISCOTTI −24% in two).
CHASE_5M, CHASE_1H = 3.0, 100.0


def chase_why(x):
    """→ the plain reasons a coin is being CHASED right now ([] = it is not): up more than 3% in the last 5 minutes, or more than
    100% on the hour. No reading = not judged."""
    out = []
    if (x or {}).get('chg5m') is not None and _f(x['chg5m']) > CHASE_5M:
        out.append(f"running hot: +{_f(x['chg5m']):.0f}% in the last 5 min (coins bought mid-spike lost most on the record)")
    if (x or {}).get('chg1h') is not None and _f(x['chg1h']) > CHASE_1H:
        out.append(f"already +{_f(x['chg1h']):.0f}% on the hour (over +100% lost about half, typically)")
    return out


def meta_why(x):
    """Plain words for a candidate the engine will not buy yet ('' = it may): chasing first, then its chart."""
    import chart_read as _cr
    ch = chase_why(x)
    if ch and not (x or {}).get('comeback'):
        return ('too hot: +%.0f%% in 5 min — waits for it to cool' % _f(x.get('chg5m'))) if _f((x or {}).get('chg5m')) > CHASE_5M else ('too far: +%.0f%% on the hour' % _f(x.get('chg1h')))
    why = _cr.why_not(x)
    if not why and at_high(x) and not (x or {}).get('comeback'):
        return 'at its highs: %.0f%% under its 4h high — waits for a %.0f%%+ dip' % (_f(x.get('cPull')), META_MIN_PULL)
    return why


def meta_ready(x):
    """🧭 May the ENGINE buy this coin by itself? Not while its chart is too short to read, and not while it is trending down.
    A comeback (a rider the card already rode, recovering) always may. The owner's hand picks are never judged here.
    Why (real card, 2026-10-06): 99 of its last 119 buys had no readable chart — −$1.01, 25% won — against +$0.07 / 40% for the
    20 with one; that afternoon $darwin ("no chart yet", +22% on the hour) hit its −15% stop six minutes after it was bought."""
    if x.get('comeback'):
        return True
    if chase_why(x):
        return False            # 🔥 mid-spike: wait for the pause, never buy into the candle
    if x.get('cBars') is None:
        return False            # never read at all = unknown = not bought (the read is attached to every candidate on a real card)
    if not x.get('cBars') or x.get('cStruct') == 'down':
        return False
    if x.get('cWild') is not None and _f(x.get('cWild')) >= META_WILD_PCT:   # 🌪 fell a third inside one candle this hour: it gaps through any stop
        return False
    if at_high(x):              # 🏔 owner, 2026-10-06: "15% off dips is good, but if it's up wtf" — record: 5–15% under the high +26%, top of range ≈ flat
        return False
    # ranging at the BOTTOM of its range = drifting down without the label (record: bottom third −31% typical vs top third −2%)
    return not (x.get('cStruct') == 'range' and x.get('cPos') is not None and _f(x.get('cPos')) < META_MIN_POS)


BOTTOM_MIN_PULL, BOTTOM_MAX_POS, BOTTOM_MIN_VOL1H = 30.0, 0.35, 10_000.0


def buy_bottom(x):
    """🟢 BUY BOTTOM (the owner's name for it; their example: $LOOT, 55% under its high, at the bottom of its range, flat). A coin
    that RAN, gave most of it back and is now sitting at the low of its range without making new lows:
      • ≥ 30% under its high (the chart's own 4h high when we have it, else the 6h / 24h change),
      • in the bottom third of its range when the chart is readable,
      • not sliding right now (5 min ≥ −1%, 1 hour ≥ −10%), buyers ≥ 50% when known, still trading (≥ $10K this hour).
    → {'score', 'why', 'pull'} or None. A LIST for the owner to pick from, never an engine buy: on the pick record, coins bought in
    the bottom third of their range lost 31% typically three hours later — this list keeps its own 1-hour paper record."""
    g = lambda *ks: next((x.get(k) for k in ks if (x or {}).get(k) is not None), None)
    if g('cPull') is not None:
        pull = _f(x['cPull'])
    else:
        c6, c24 = g('chg6h', 'change6h'), g('chg24h', 'change24h')
        if c6 is None and c24 is None:
            return None
        pull = max(0.0, -min(_f(c6), _f(c24)))
    m5, h1, bs = g('chg5m', 'change5m'), g('chg1h', 'change1h'), g('buyShare')
    bs = None if bs is None else (_f(bs) * 100 if 0 < _f(bs) <= 1 else _f(bs))
    if pull < BOTTOM_MIN_PULL or (g('cPos') is not None and _f(x['cPos']) > BOTTOM_MAX_POS) or _f(g('vol1h')) < BOTTOM_MIN_VOL1H:
        return None
    if (m5 is not None and _f(m5) < -1) or (h1 is not None and _f(h1) < -10) or (bs is not None and bs < 50):
        return None
    score = min(60.0, pull * 0.8) + (min(20.0, max(0.0, bs - 50)) if bs is not None else 0.0) + (min(20.0, max(0.0, _f(m5)) * 4) if m5 is not None else 0.0)
    why = ' · '.join(p for p in (f"{pull:.0f}% under its high", 'bottom of its range' if g('cPos') is not None else '', f"5m {_f(m5):+.0f}%" if m5 is not None else '',
                                 f"buyers {bs:.0f}%" if bs is not None else '') if p)
    return {'score': round(score, 1), 'why': why, 'pull': round(pull, 1)}


SEAT_FALLBACK_SEC = 30.0   # 🪑 a seat with no qualifying coin takes the next-best one after 30 seconds


def seat_fallback_ok(x, mom=None):
    """May this watched coin take a seat that has been empty for 30s? Not falling right now, not mid-spike, not trending down,
    not too wild, not at its highs. (Chart too short / under the hunt line are the things the fallback waives.)"""
    if not entry_ok(x, mom) or chase_why(x) or x.get('cStruct') == 'down' or at_high(x):   # 🏔 never a coin sitting at its highs: the fallback
        return False                                                                          # was filling seats with coins that had already peaked
    return not (x.get('cWild') is not None and _f(x.get('cWild')) >= META_WILD_PCT)


# ⏭ Coming up = THREE doors (owner, 2026-10-07: "1 top trench, pump and volume — never in the highs"): the trench's top coin always
# first, then Pump trending and Volume by their own 1-hour record. The other lists stay in the picker; they no longer feed this row.
CATEGORIES = (('trench', '🗑 Trench'), ('ptrend', '🔥 Pump trending'), ('volume', '🌊 Volume'))


def category_picks(lists, ok, records=None, limit=6):
    """⏭ COMING UP = ONE coin per category, the best from the TOP of that list (owner: "pick 1 of the best from the top for swap in
    categories"). Each list is walked in its own order; the first coin `ok(row)` accepts (safety scan, pool floor, min age, a sane
    entry, not on the card / cooling) is that category's pick, never one an earlier category already took. Categories are ordered by
    their own 1-hour record (best median first; no record yet → after). → [{**row, cat, catLabel, rank}] (+ `misses` {cat: why})"""
    rec = records or {}
    def score(k):
        r = rec.get(k) or {}
        return _f(r.get('medPct')) if _f(r.get('n')) >= 5 else -1e9
    order = [CATEGORIES[0]] + sorted(CATEGORIES[1:], key=lambda kv: -score(kv[0]))   # trench is always first
    out, taken, misses = [], set(), {}
    for k, label in order:
        rows = (lists or {}).get(k) or []
        pick, why = None, {}
        for i, r in enumerate(rows[:60]):
            m = r.get('mint')
            if not m or m in taken:
                continue
            v = ok(r)   # True = takes it · a string = the first check it failed (counted, so the screen can say what blocks a list)
            if v is True:
                pick = {**r, 'cat': k, 'catLabel': label, 'rank': i + 1}
                break
            w = v if isinstance(v, str) and v else 'did not pass'
            why[w] = why.get(w, 0) + 1
        if pick:
            taken.add(pick['mint']); out.append(pick)
        else:
            top = sorted(why.items(), key=lambda kv: -kv[1])[:3]
            misses[k] = ('top 60: ' + ' · '.join(f'{n} {w}' for w, n in top)) if top else ('nothing in the top 60 passes' if rows else 'list empty right now')
    return out[:limit], misses


def door_watch(picks, lists, resolve, why, skip=None, limit=60):
    """🚪 Every Coming-up door shows ONE coin (owner: "1 trench, 1 pump, 1 volume"). A door with no ready pick shows the best coin of its
    list as WATCHING: the first row (walking from the top) that has data (`resolve(row)` → the coin's record or None), is not skipped
    (`skip(mint, rec)`: on the card, dollar-named, no price …) and has a reason it is not ready (`why(row, rec)` → text; True = it is
    ready, so it is not a watch row). → [{**rec, cat, catRank, tag, watchWhy}] — shown only, never seated by the engine."""
    have = {p_['cat'] for p_ in picks}
    taken = {p_['mint'] for p_ in picks}
    out = []
    for k, label in CATEGORIES:
        if k in have:
            continue
        for i, r in enumerate(((lists or {}).get(k) or [])[:limit]):
            m = r.get('mint')
            rec = resolve(r) if m else None
            if not m or not rec or m in taken or (skip and skip(m, rec)):
                continue
            w = why(r, rec)
            if w is True:
                continue
            taken.add(m)
            out.append({**rec, 'cat': k, 'catRank': i + 1, 'tag': f"{label} #{i + 1}", 'watchWhy': str(w) or 'not ready'})
            break
    return out


def meta_only(rows, cfg=None, mom=None):
    """Rows the engine may buy by itself. Two kinds keep their OWN entry rule instead of the chart gate: 🗑 trench rows
    (`trench_entry` — a coin minutes old has no chart to read, so the gate dropped every one and the trench drop never fired)
    and coins passing the card's own 🚀 hunt line, for which only "at its highs" is waived (a coin up 40% on the hour on real
    volume IS at its highs; the replay that backs the hunt had no such rule) — spike, too-wild and down-trend still apply."""
    out = []
    for x in rows or []:
        if x.get('trenchOnly'):
            ok = trench_entry(x, mom)
        elif cfg and is_hunt(x, cfg) and at_high(x):
            ok = meta_ready({**x, 'cPull': None})
        else:
            ok = meta_ready(x)
        if ok:
            out.append(x)
    return out


def is_hunt(x, cfg):
    """Does this coin pass the card's own 🚀 hunt selection (BOTH a 1h-volume and a 1h-move minimum set, and it clears them)?"""
    v, m = _f((cfg or {}).get('runnerMinVolK')), _f((cfg or {}).get('runnerMinChg1h'))
    return v > 0 and m > 0 and _f(x.get('vol1h')) >= v * 1000 and x.get('chg1h') is not None and _f(x.get('chg1h')) >= m


def deep_runners(rows, min_k, min_buy=0, min_vol_k=0, min_chg1h=0):
    """Runners the owner's own selection lets real money buy: pool ≥ `min_k` $K, buyers ≥ `min_buy`%, 1h volume ≥ `min_vol_k` $K,
    1h move ≥ `min_chg1h`% (each 0 = off; an unknown reading fails a rule that is on). New majors / trench coins keep their own rules."""
    if not (_f(min_k) or _f(min_buy) or _f(min_vol_k) or _f(min_chg1h)):
        return list(rows or [])
    ok = lambda x: (_f(x.get('liq')) >= _f(min_k) * 1000 and (not _f(min_buy) or _f(x.get('buyShare')) >= _f(min_buy))
                    and (not _f(min_vol_k) or _f(x.get('vol1h')) >= _f(min_vol_k) * 1000)
                    and (not _f(min_chg1h) or (x.get('chg1h') is not None and _f(x.get('chg1h')) >= _f(min_chg1h))))
    return [x for x in rows or [] if x.get('newMajor') or x.get('trenchOnly') or ok(x)]


REAL_RUNNER_AGE_H = 12.0  # real money never buys a runner younger than this (a 20-min-old coin with a $534K pool went −99.99% in an hour)


def real_guard(cfg, owner_set=()):
    """The real card's config with the hard floors applied. Returns (cfg, changed) — `changed` lists what was raised, in plain words.
    THE OWNER PICKS: a round min hold the owner set to OFF (0) in Edit Fuse stays off — the floor only lifts values nobody chose."""
    out, changed = dict(cfg or {}), []
    fast = _f(out.get('rotateHours')) * 60 <= 15
    hold_off = 'minHoldMins' in set(owner_set or ()) and _f(out.get('minHoldMins')) == 0
    if fast and not hold_off and _f(out.get('minHoldMins')) < REAL_MIN_HOLD:
        out['minHoldMins'] = REAL_MIN_HOLD; changed.append(f'hold ≥ {REAL_MIN_HOLD:g} min')
    if int(_f(out.get('rotateConfirm'))) < REAL_MIN_CONFIRM:
        out['rotateConfirm'] = REAL_MIN_CONFIRM; changed.append(f'{REAL_MIN_CONFIRM} losing rounds before a swap')
    if 0 < _f(out.get('instantSwapPct')) < REAL_MIN_INSTANT:
        out['instantSwapPct'] = REAL_MIN_INSTANT; changed.append(f'instant swap −{REAL_MIN_INSTANT:g}%')
    # THE OWNER PICKS: "re-shape every 3" saved by the owner in Edit Fuse is honoured (never under 3); a value nobody chose is raised to 6
    least = REAL_OWNER_RESHAPE if 'cycleEvery' in set(owner_set or ()) else REAL_MAX_RESHAPE
    if 0 < int(_f(out.get('cycleEvery'))) < least:
        out['cycleEvery'] = least; changed.append(f're-shape every {least} rounds')
    # always on for real money (not owner settings, so never listed as "raised"):
    #  • a safe / rescue FIX re-shaped the card EVERY round — on a 5-min clock that sold and re-bought 2–3 coins every 5 minutes
    out['fixEvery'] = REAL_MAX_RESHAPE
    out['dealLeadSec'] = REAL_DEAL_LEAD
    out['minCoinUsd'] = 0.0 if int(_f(out.get('coins'))) else REAL_MIN_COIN_USD   # the owner's coin count always wins over the size rule
    return out, changed


# 🌦 RUNNER WEATHER for real money, from the engine's own sims on real recorded prices (the freshest window with enough cards):
# clear = every gated runner is allowed · 🌧 rain (≤ −5%) = only strong runners in a deep pool · ⛈ storm (≤ −25%) = no runners,
# new majors only. Paper keeps trading everything — that is how the weather is measured.
RAIN_PCT, STORM_PCT, RAIN_SCORE = -5.0, -25.0, 60.0


def weather(sim):
    s6, s24 = (sim or {}).get('s6') or {}, (sim or {}).get('s24') or {}
    w = s6 if _f(s6.get('n')) >= 50 else s24 if _f(s24.get('n')) >= 100 else None
    if not w:
        return {'level': 'clear', 'avgPct': None, 'n': 0}
    avg = _f(w.get('avgPct'))
    return {'level': 'storm' if avg <= STORM_PCT else 'rain' if avg <= RAIN_PCT else 'clear', 'avgPct': round(avg, 2), 'n': int(_f(w.get('n')))}


def forecast(sim, cands=()):
    """🌦 The weather + where it is heading, in facts. `now` = `weather(sim)` (sim cards on real prices). `trend` = the last 6h of
    sims against the last 24h (≥ 3 pts apart). `breadth` = share of live launch coins green over the hour + their average buy
    share. `outlook` = tailwind / mixed / headwind from breadth and trend. A reading of right now — never a promise."""
    w = weather(sim)
    s6, s24 = (sim or {}).get('s6') or {}, (sim or {}).get('s24') or {}
    trend = 'steady'
    if _f(s6.get('n')) >= 50 and _f(s24.get('n')) >= 100:
        d = _f(s6.get('avgPct')) - _f(s24.get('avgPct'))
        trend = 'clearing' if d >= 3 else 'worsening' if d <= -3 else 'steady'
    live = [c for c in cands or [] if c.get('chg1h') is not None]
    breadth = round(sum(1 for c in live if _f(c.get('chg1h')) > 0) / len(live) * 100) if live else None
    bs = [_f(c.get('buyShare')) for c in live if c.get('buyShare') is not None]
    buyers = round(sum(bs) / len(bs)) if bs else None
    if breadth is None:
        outlook = 'mixed'
    elif w['level'] == 'storm' or breadth <= 35 or (trend == 'worsening' and breadth < 50):
        outlook = 'headwind'
    elif breadth >= 60 and trend != 'worsening' and w['level'] == 'clear':
        outlook = 'tailwind'
    else:
        outlook = 'mixed'
    buys = {'storm': 'real money buys new majors only', 'rain': 'real money buys only strong runners in deep pools', 'clear': 'every gated coin can be bought'}[w['level']]
    return {**w, 'trend': trend, 'breadthPct': breadth, 'buyersPct': buyers, 'coins': len(live), 'outlook': outlook, 'buys': buys}


# 🎯 BEST ENTRIES NOW — three classic setups, read from live numbers only (5m / 1h move, buyers, volume pace). A read of the
# tape, never a promise; the caller passes only coins that already clear the SAFETY gates.
ENTRY_SETUPS = {
    'sweep': ('🧹', 'Sweep & reclaim', 'flushed over the hour, buyers took it back in the last 5 min'),
    'breakout': ('🚀', 'Breakout', 'up on the hour and still pushing, volume speeding up'),
    'pullback': ('🧲', 'Pullback', 'strong hour, small dip now with buyers still in charge — the retrace into the move'),
}

ENTRY_RAN = 150.0   # more than +150% on the hour = it already ran (usually a launch pump): not an entry


def entry_setup(c):
    """→ (setup key, strength 0–100) or None. Needs a 5m AND a 1h reading, buyers, and ≥ $5K of 1h volume."""
    if c.get('chg5m') is None or c.get('chg1h') is None or c.get('buyShare') is None or _f(c.get('vol1h')) < 5000:
        return None
    m5, h1, buy = _f(c.get('chg5m')), _f(c.get('chg1h')), _f(c.get('buyShare'))
    pace = _f(c.get('vol5m')) * 12 / max(1.0, _f(c.get('vol1h')))        # > 1 = the last 5 min are busier than the hour's average
    if h1 <= -8 and m5 >= 2 and buy >= 58:
        return 'sweep', min(100.0, 40 + m5 * 4 + (buy - 58) * 2 + min(20.0, -h1 / 2))
    if 10 <= h1 <= ENTRY_RAN and m5 >= 3 and buy >= 58 and pace >= 1.5:
        return 'breakout', min(100.0, 40 + m5 * 3 + (buy - 58) * 2 + min(20.0, pace * 5))
    if 15 <= h1 <= ENTRY_RAN and -6 <= m5 <= -1 and buy >= 52:
        return 'pullback', min(100.0, 40 + min(25.0, h1 / 2) + (buy - 52) * 2)
    return None


def entries(cands, skip=(), n=3):
    """The n strongest setups among `cands` (one row per coin, coins in `skip` left out), strongest first."""
    rows, seen = [], set(skip or ())
    for c in cands or []:
        hit = entry_setup(c)
        if not hit or not c.get('mint') or c['mint'] in seen:
            continue
        seen.add(c['mint'])
        ico, name, why = ENTRY_SETUPS[hit[0]]
        rows.append({'mint': c['mint'], 'symbol': c.get('symbol'), 'pairAddress': c.get('pairAddress'), 'logo': c.get('logo'), 'setup': hit[0], 'ico': ico, 'name': name, 'why': why,
                     'strength': round(hit[1]), 'chg5m': c.get('chg5m'), 'chg1h': c.get('chg1h'), 'buyShare': c.get('buyShare'), 'liq': c.get('liq')})
    return sorted(rows, key=lambda r: -r['strength'])[:n]


def weather_runners(rows, level, deep_floor, liq_of, cfg=None):
    """Runner candidates real money may BUY in this weather (coins already held are never sold by the weather).
    In ANY weather a runner must be at least REAL_RUNNER_AGE_H old — unknown age = out (fail closed). New majors are days old by rule.
    🚀 A coin passing the card's own hunt selection (`is_hunt`: running on real volume) is bought in ANY weather: the weather is the
    typical result of buying runners with NO selection, and the rain rule ranks by the hand-written score the record showed to be
    upside down (the coins that went 2–5× scored ~54, under RAIN_SCORE)."""
    age_min = _f((cfg or {}).get('runnerMinAgeH')) if (cfg or {}).get('runnerMinAgeH') is not None else REAL_RUNNER_AGE_H   # the owner's own line (0 = any age; unknown age still out)
    rows = [x for x in rows if x.get('newMajor') or (x.get('ageH') is not None and _f(x.get('ageH')) >= age_min)]
    if level == 'storm':
        return [x for x in rows if x.get('newMajor') or is_hunt(x, cfg)]
    if level == 'rain':
        return [x for x in rows if x.get('newMajor') or is_hunt(x, cfg) or (_f(x.get('score')) >= RAIN_SCORE and _f(liq_of(x)) >= _f(deep_floor))]
    return list(rows)


# 🎯 TRUE FILLS (paper = exactly what a real wallet would get): constant-product price impact against the pool's quote-side
# reserve (≈ half its liquidity). Buy $u → average fill = mid × (1 + u/R); sell $v of coins → you receive v / (1 + v/R).
# The pool / FEELESS fee is a separate line (feesUsd), never inside P&L; impact IS the price you got, so it is in the fill.
IMPACT_MULT = 1.0   # 🎯 learned from REAL Fuse-wallet fills (fuse_wallet.calibrate): >1 = real impact was worse than the model
BELL_SEC = 10       # 🔔 every round opens with a 10s countdown on screen; the engine wakes exactly when the round is due


UNKNOWN_LIQ = 20_000.0   # no liquidity reading (fresh / curve coins) = treat the pool as THIN, never infinitely deep


def _r(liq):
    return (_f(liq) if _f(liq) > 0 else UNKNOWN_LIQ) / 2 / max(0.1, IMPACT_MULT)


SPREAD = 0.0   # 🎯 flat cost of ANY swap (pool fee + spread), learned from real fills: 357 real swaps cost a median 0.38% each
               # whatever their size — the impact model alone priced a $1 swap at ~0%, so paper looked better than real money


def buy_px(px, usd, liq):
    return px * (1 + SPREAD) * (1 + _f(usd) / _r(liq)) if px > 0 else px


def sell_usd(units, px, liq):
    v = _f(units) * _f(px)
    return v / (1 + SPREAD) / (1 + v / _r(liq))


# 💰 SKIM THE PROFIT, KEEP THE STAKE. A coin that is up keeps what was put into it riding; only the gain is sold — into the card's
# other coins (♻ recovery for the ones that are down) or held as cash (🏦 e.g. a tax reserve the owner withdraws).
# 🧷 AUTO PROFIT-TAKING NEVER EATS THE STAKE: every automatic take (skim, bank at the lock, peak sell, recycle) also sells a slice
# of what was PUT INTO the coin. Repeated, a winner was whittled to nothing ($phubber: $0.56 in, +63%, $0.09 left riding). Once
# those takes have removed `tpStakeUsd` of a coin's stake they stop for that coin; it rides on with stops / trail / rug shield.
TP_STAKE_USD = 0.25
TP_STAKES = (0, 0.1, 0.25, 0.5, 1.0)   # 0 = no limit (the old behaviour)


def tp_room(l, cfg, px=None):
    """🧷 KEEP $X RIDING (cfg `tpStakeUsd`, the owner's "stop at $1"): $ of this coin's VALUE that automatic profit-taking may
    still sell — everything above the amount that must stay in the coin (None = no limit; 0 = nothing may be sold).
    2026-10-07: it used to mean "$ of STAKE the takes may remove", so a riding +122% coin was skimmed, banked, peak-sold and
    skimmed again from $1.13 down to $0.14 while the setting read "$1". Now a coin is never left worth less than the number."""
    lim = _f((cfg or {}).get('tpStakeUsd', TP_STAKE_USD))
    if lim <= 0:
        return None
    p_ = _f(px) or _f(l.get('entry'))
    return max(0.0, _f(l.get('units')) * p_ - lim)


SKIM_ATS = (0, 10, 20, 30, 50, 100)   # auto: skim each time the coin gains this % since its entry / last skim (0 = off)
SKIM_TOS = ('card', 'cash', 'round')   # 'round' = parked in card cash for `skimHoldRounds` rounds, then back into the coins
SKIM_HOLDS = (1, 2, 3, 6)
RECYCLE_PCTS = (0, 50, 70, 100)        # ♻ every `recycleEvery` rounds this % of each coin's PROFIT goes back over the card's coins (0 = off)
RECYCLE_EVERY = (1, 2, 3, 4, 6, 12)
TRENCH_VICTIM_USD = 0.10              # … in place of the weakest coin, which must be making no more than 10c
TRENCH_DROP_SEC = 1800                # 🗑 a card on the trench cycle takes the best trench coin on the list every 30 minutes
SEAT_MIN_USD = 0.25                   # an empty seat is refilled once the card has at least this much free cash
SKIM_MIN_USD = 0.05                   # a gain smaller than this isn't worth a swap


STACK_SKIMS = (0, 0.5, 1, 2, 5)   # 💚 full-stack skim: the $ each locked coin keeps (0 = off)
STACK_SKIM_MIN = 0.05


def stack_skim(c, prices, liqs, now, cfg, fee=0.0):
    """💚 FULL STACK → SKIM TO THE STAKE (the owner's system: "once we lock all coins it's love — it skims down to a dollar, then
    anything above"). While EVERY coin on the card is locked (riding / frozen), each coin is cut down to `stackSkimUsd` of value
    and whatever it grows above that is taken again, tick after tick. The money goes where the card's skims go (`skimTo`: card
    cash · parked for rounds · held for the owner). The stake keeps riding with its trail and stops; a coin worth less than the
    stake is left alone. Mutates c; → $ taken."""
    keep = _f(cfg.get('stackSkimUsd'))
    if keep <= 0 or not stack(c, prices, cfg)['full']:
        return 0.0
    keep = max(keep, _f(cfg.get('tpStakeUsd', TP_STAKE_USD)))   # 🧷 … and never under the owner's "keep $X riding" floor
    to, took = cfg.get('skimTo', 'card'), 0.0
    for l in c['legs']:
        px = _f(prices.get(l['pairAddress']))
        units, cost = _f(l.get('units')), _f(l.get('costUsd'))
        value = units * px
        if px <= 0 or units <= 0 or l.get('buying') or l.get('placeholder') or value - keep < max(STACK_SKIM_MIN, keep * 0.03):
            continue
        part = (value - keep) / value
        got = sell_usd(units * part, px, (liqs or {}).get(l['pairAddress']) or l.get('liq'))
        l['units'] = units * (1 - part); l['costUsd'] = round(cost * (1 - part), 6); l['trimAt'] = now; l['skimPx'] = px; l['bankedAt'] = l.get('bankedAt') or now
        c['cash'] = round(_f(c.get('cash')) + got, 6)
        if to in ('cash', 'round'):
            c['holdCashUsd'] = round(_f(c.get('holdCashUsd')) + got, 6)
        if to == 'round':
            c['skimPark'] = list(c.get('skimPark') or []) + [{'usd': round(got, 6), 'round': int(c.get('rounds') or 0), 'at': now, 'symbol': l.get('symbol')}]
        c['takenUsd'] = _f(c.get('takenUsd')) + max(0.0, got - cost * part); c['feesUsd'] = _f(c.get('feesUsd')) + fee
        c.setdefault('events', []).append({'at': now, 'kind': 'skim', 'symbol': l.get('symbol'), 'usd': round(got, 4), 'to': ['cash' if to == 'cash' else 'card'], 'stack': True,
                                           'why': f"💚 full stack — ${l.get('symbol')} skimmed down to its ${keep:g} stake (${got:.2f} taken"
                                                  + (', held as cash for you)' if to == 'cash' else ', parked for the next rounds)' if to == 'round' else ', card cash)')})
        took += got
    return took


def lock_bank(c, l, px, liqs, now, cfg, fee=0.0, gain=None):
    """🏦 BANK ON THE LOCK: `lockBankPct` of a winner is sold when it locks, so a round-tripped run still paid. Once per ride
    (`bankedAt`). In place → $ banked."""
    bank = _f((cfg or {}).get('lockBankPct', LOCK_BANK)) / 100
    if bank <= 0 or l.get('bankedAt') or _f(l.get('units')) <= 0 or px <= 0:
        return 0.0
    room = tp_room(l, cfg, px)
    if room is not None:
        bank = min(bank, room / (_f(l['units']) * px))   # 🧷 the coin keeps at least the owner's $ floor riding
        if _f(l['units']) * bank * px < SKIM_MIN_USD:
            return 0.0
    sold = _f(l['units']) * bank
    got = sell_usd(sold, px, (liqs or {}).get(l['pairAddress']) or l.get('liq'))
    cost_part = _f(l.get('costUsd')) * bank
    l['units'] = _f(l['units']) - sold; l['costUsd'] = round(_f(l.get('costUsd')) - cost_part, 6); l['trimAt'] = l['bankedAt'] = now
    c['cash'] = _f(c.get('cash')) + got; c['takenUsd'] = _f(c.get('takenUsd')) + max(0.0, got - cost_part); c['feesUsd'] = _f(c.get('feesUsd')) + fee
    if (cfg or {}).get('skimTo') == 'round':   # 🅿 banked money parks like a skim
        c['holdCashUsd'] = round(_f(c.get('holdCashUsd')) + got, 6)
        c['skimPark'] = list(c.get('skimPark') or []) + [{'usd': round(got, 6), 'round': int(c.get('rounds') or 0), 'at': now, 'symbol': l.get('symbol')}]
    g_txt = f" (+{gain:.0f}%)" if gain is not None else ''
    c.setdefault('events', []).append({'at': now, 'kind': 'lock-bank', 'symbol': l['symbol'], 'usd': round(got, 4), 'to': ['cash'],
                                       'why': f"🏦 banked {bank * 100:g}% of ${l['symbol']} as it locked{g_txt} — the rest keeps riding"})
    return got


def _skim(c, l, px, liqs, now, to='card', fee=0.0, auto=None, frac=1.0, why=None, room=None, hold=None):
    """Sell the PROFIT of one coin (or `frac` of it), in place. → $ taken (0 = nothing to take). With frac 1 the part that stays is
    worth what the coin cost."""
    units, cost = _f(l.get('units')), _f(l.get('costUsd'))
    value = units * px
    gain = (value - cost) * max(0.0, min(1.0, _f(frac)))
    if units <= 0 or px <= 0 or gain < SKIM_MIN_USD:
        return 0.0
    part = gain / value
    if room is not None:                                  # 🧷 an AUTOMATIC take never leaves the coin worth less than the owner's $ floor
        part = min(part, room / value)
        if value * part < SKIM_MIN_USD:
            return 0.0
    sold = units * part
    got = sell_usd(sold, px, (liqs or {}).get(l['pairAddress']) or l.get('liq'))
    l['units'] = units - sold; l['costUsd'] = round(cost * (1 - part), 6)
    l['trimAt'] = now; l['skimPx'] = px                      # the keeper sells this trim; the next skim counts from this price
    c['cash'] = round(_f(c.get('cash')) + got, 6)
    if to == 'cash':
        c['holdCashUsd'] = round(_f(c.get('holdCashUsd')) + got, 6)   # held for the owner — never put back into coins
    elif to == 'round':   # 🅿 parked: out of the coins (so a rug cannot take it) for a few rounds, then it goes back to work
        c['holdCashUsd'] = round(_f(c.get('holdCashUsd')) + got, 6)
        c['skimPark'] = list(c.get('skimPark') or []) + [{'usd': round(got, 6), 'round': int(c.get('rounds') or 0), 'at': now, 'symbol': l.get('symbol'),
                                                          **({'hold': int(hold)} if hold and int(_f(hold)) in SKIM_HOLDS else {})}]   # 🅿 this park's OWN rounds (a per-coin choice)
    c['takenUsd'] = _f(c.get('takenUsd')) + max(0.0, got - cost * part)
    c['feesUsd'] = _f(c.get('feesUsd')) + fee
    c.setdefault('events', []).append({'at': now, 'kind': 'skim', 'symbol': l.get('symbol'), 'usd': round(got, 4), 'to': ['cash'] if to == 'cash' else ['card'],
                                       'why': why or f"💰 {'auto: +' + format(auto, 'g') + '% — ' if auto else ''}profit of ${l.get('symbol')} taken (${got:.2f}), its stake keeps riding — "
                                              + ('held as cash for you' if to == 'cash' else 'parked in card cash for the next rounds' if to == 'round' else 'put to work in your other coins')})
    return got


HOUSE_ATS = (0, 30, 50, 100, 200)   # 🏠 cfg `trenchHouseAt`: 0 = off


def _take_stake(c, l, px, liqs, now, to='cash', fee=0.0, auto=None):
    """🏠 TAKE THE INITIAL, LEAVE THE PROFIT (in place). Sells as much of a winning coin as it COST; what stays cost nothing —
    house money — and keeps riding with its stop / trail. Only when the coin is worth more than it cost (and both parts are worth
    sending). `to`: 'cash' held for the owner · 'round' parked a few rounds · 'card' back into the other coins. → $ taken."""
    units, cost = _f(l.get('units')), _f(l.get('costUsd'))
    value = units * px
    if units <= 0 or px <= 0 or cost < SKIM_MIN_USD or value - cost < SKIM_MIN_USD or l.get('house'):
        return 0.0
    part = cost / value
    sold = units * part
    got = sell_usd(sold, px, (liqs or {}).get(l['pairAddress']) or l.get('liq'))
    l['units'] = units - sold; l['costUsd'] = 0.0; l['house'] = True
    l['trimAt'] = now; l['skimPx'] = px
    c['cash'] = round(_f(c.get('cash')) + got, 6)
    if to == 'cash':
        c['holdCashUsd'] = round(_f(c.get('holdCashUsd')) + got, 6)
    elif to == 'round':
        c['holdCashUsd'] = round(_f(c.get('holdCashUsd')) + got, 6)
        c['skimPark'] = list(c.get('skimPark') or []) + [{'usd': round(got, 6), 'round': int(c.get('rounds') or 0), 'at': now, 'symbol': l.get('symbol')}]
    c['feesUsd'] = _f(c.get('feesUsd')) + fee
    c.setdefault('events', []).append({'at': now, 'kind': 'skim', 'symbol': l.get('symbol'), 'usd': round(got, 4), 'to': ['cash'] if to == 'cash' else ['card'], 'house': True,
                                       'why': f"🏠 {'auto: +' + format(auto, 'g') + '% — ' if auto else ''}initial of ${l.get('symbol')} taken out (${got:.2f}) — only its profit keeps riding — "
                                              + ('held as cash for you' if to == 'cash' else 'parked in card cash for the next rounds' if to == 'round' else 'put to work in your other coins')})
    return got


def stake_leg(card, pair, prices, liqs, now, to='cash'):
    """Owner's 🏠: take the initial out of ONE coin now, profit rides. Pure; ValueError when it can't."""
    c = {**card, 'legs': [dict(l) for l in card['legs']], 'events': list(card.get('events') or [])}
    l = next((x for x in c['legs'] if x['pairAddress'] == pair), None)
    if not l:
        raise ValueError('That coin is not on this card.')
    if l.get('buying') or l.get('placeholder'):
        raise ValueError('That coin is still being bought.')
    if l.get('house'):
        raise ValueError(f"${l.get('symbol')}'s initial is already out — what is left is profit.")
    if not _take_stake(c, l, _f((prices or {}).get(pair)) or _f(l.get('entry')), liqs, now, to if to in SKIM_TOS else 'cash'):
        raise ValueError(f"${l.get('symbol')} is not worth more than it cost yet — there is no initial to take out and still leave profit.")
    return c


def clamp_hold(c):
    """🅿 Parked profit can never be more than the card's REAL cash. On a real card the keeper's network fees come out of that same cash
    (hundreds of swaps), so the engine's earmark drifted above it (2026-10-08: $1.835 earmarked, $1.23 of cash — $0.60 of "parked" that no
    longer existed, shown on the card). The shortfall comes off the NEWEST park rows first (the oldest keep their rounds). Mutates c;
    → $ removed from the earmark. A paper card's cash is exact, so this only runs on real cards."""
    hold, cash = _f(c.get('holdCashUsd')), _f(c.get('cash'))
    if not c.get('real') or hold <= cash + 1e-6:
        return 0.0
    cut = hold - max(0.0, cash)
    c['holdCashUsd'] = round(max(0.0, cash), 6)
    left, rows = cut, [dict(p) for p in (c.get('skimPark') or [])]
    for p in reversed(rows):
        take = min(_f(p.get('usd')), left)
        p['usd'] = round(_f(p.get('usd')) - take, 6); left -= take
        if left <= 1e-9:
            break
    c['skimPark'] = [p for p in rows if _f(p.get('usd')) > 0.0005]
    return round(cut, 6)


def release_parked(c, cfg, now):
    """🅿 Parked profit whose rounds are up goes back to work: it leaves the held cash, and the normal idle-cash spread puts it into
    the card's coins at this round. Mutates c; → $ released."""
    park = list(c.get('skimPark') or [])
    if not park:
        return 0.0
    n = int(_f((cfg or {}).get('skimHoldRounds')) or 2); rnd = int(c.get('rounds') or 0)
    due = [p for p in park if rnd - int(p.get('round') or 0) >= int(p.get('hold') or n) or rnd < int(p.get('round') or 0)]   # each park keeps its own rounds; a restarted run releases everything
    if not due:
        return 0.0
    usd = min(sum(_f(p.get('usd')) for p in due), _f(c.get('holdCashUsd')))
    c['holdCashUsd'] = round(max(0.0, _f(c.get('holdCashUsd')) - usd), 6)
    c['skimPark'] = [p for p in park if p not in due]
    if usd > 0.005:
        c.setdefault('events', []).append({'at': now, 'kind': 'compound', 'usd': round(usd, 4), 'why': f"🅿 ${usd:.2f} of parked profit is back to work after {n} round{'s' if n != 1 else ''}"})
    return usd


def skim_leg(card, pair, prices, liqs, now, to='card', hold=None):
    """Owner's 💰: take the profit of ONE coin now. Pure; ValueError when the coin isn't on the card or has no profit to take."""
    c = {**card, 'legs': [dict(l) for l in card['legs']], 'events': list(card.get('events') or [])}
    l = next((x for x in c['legs'] if x['pairAddress'] == pair), None)
    if not l:
        raise ValueError('That coin is not on this card.')
    if l.get('buying') or l.get('placeholder'):
        raise ValueError('That coin is still being bought.')
    if not _skim(c, l, _f((prices or {}).get(pair)) or _f(l.get('entry')), liqs, now, to if to in SKIM_TOS else 'card', hold=hold):
        raise ValueError(f"${l.get('symbol')} has no profit to take right now.")
    return c


LOCK_BANKS, LOCK_BANK = (0, 25, 33, 50), 33.0
PEAK_SELLS, PEAK_SELL = (25, 50, 75, 100), 50.0   # 🏔 off its peak: % of the PROFIT sold while the coin keeps riding (100 = swap the whole coin)   # 🏦 % of a winner sold the moment it locks (0 = off)

# ⚖ SWAP ONLY WHEN IT PAYS. A rotation sells one coin and buys another: it costs the spread + price impact twice + two network fees.
SWAP_EDGE_MARGIN = 1.0     # the next coin must beat the old one by the swap's cost PLUS this many % (1h move)
CHURN_BUDGET_PCT = 2.0     # 🤖 auto cap: rotations may cost at most this % of the card an hour
SWAP_CAPS = (-1, 0, 2, 4, 6, 8, 12)   # swaps an hour: -1 = no cap · 0 = 🤖 auto (from the measured cost) · or the owner's number
PLAIN_ROTATE = ('weakest after', '🗑 trench cycle')   # the swaps the cap counts: engine rotations (never stops, rug exits, rides, picks)


def swap_cost_pct(usd, liq_out, liq_in, fee=0.0):
    """What a $usd swap from one pool into another loses, in % (true fills both ways + both network fees)."""
    usd = _f(usd)
    if usd <= 0:
        return 0.0
    back = sell_usd(1.0, usd, liq_out)
    got = back / buy_px(1.0, back, liq_in) if back > 0 else 0.0
    return round(max(0.0, (1 - (got - 2 * _f(fee)) / usd) * 100), 3)


def swap_edge(old_mom, new_mom, sol_1h, cost_pct, margin=SWAP_EDGE_MARGIN):
    """Which way to go — stay, or swap? (go, why). Three readings over the last hour: the coin we hold, the coin we could take, and
    SOL. Swap only when the next coin is beating SOL AND beats the coin we hold by more than the swap costs (+ margin). The gate
    only blocks on EVIDENCE: no 1h reading for the next coin → the rotation goes ahead as before (a patient loser still leaves)."""
    if not new_mom or new_mom.get('chg1h') is None:
        return True, 'no 1h reading for the next coin — rotated on patience alone'
    old, new, sol = _f((old_mom or {}).get('chg1h')), _f(new_mom.get('chg1h')), _f(sol_1h)
    need = _f(cost_pct) + _f(margin)
    if new <= sol:
        return False, f'next coin {new:+.1f}% 1h is not beating SOL ({sol:+.1f}%) — staying'
    if new - old <= need:
        return False, f'next coin {new:+.1f}% vs this one {old:+.1f}% 1h — a {new - old:.1f}% edge does not cover the {need:.1f}% it costs to swap'
    return True, f'next coin {new:+.1f}% vs this one {old:+.1f}% 1h (SOL {sol:+.1f}%) — a {new - old:.1f}% edge over a {need:.1f}% swap cost'


def swap_cap(cfg, card_usd, coins, liq=UNKNOWN_LIQ):
    """🤖 Swaps an hour this card may make by ROTATION, with the reason in plain words. Auto = tuned from what one swap costs on a
    card this size: a small card pays a bigger share per swap, so it gets fewer. → {cap (0 = none), auto, costPct, why}"""
    want = int(_f((cfg or {}).get('swapCapHr')))
    per = _f(card_usd) / max(1, int(coins or 1))
    cost = swap_cost_pct(per, liq, liq, _f((cfg or {}).get('paperFeeUsd')))
    if want < 0:
        return {'cap': 0, 'auto': False, 'costPct': cost, 'why': 'no hourly cap (your setting)'}
    if want > 0:
        return {'cap': want, 'auto': False, 'costPct': cost, 'why': f'{want} rotations an hour (your setting) — each costs about {cost:.1f}% of the coin it moves'}
    share = cost / max(1, int(coins or 1))   # one coin's swap as a share of the whole card
    cap = max(2, min(12, int(CHURN_BUDGET_PCT / share))) if share > 0 else 12
    return {'cap': cap, 'auto': True, 'costPct': cost,
            'why': f'🤖 {cap} rotations an hour: one swap costs about {cost:.1f}% of a ${per:.2f} coin ({share:.2f}% of the card), so {cap} keeps churn under {CHURN_BUDGET_PCT:g}% of the card an hour'}


def swaps_last_hour(card, now):
    return sum(1 for e in (card or {}).get('events') or [] if e.get('kind') == 'rotate' and now - _f(e.get('at')) < 3600 and str(e.get('why') or '').startswith(PLAIN_ROTATE))


def _leg(c, usd, now, role):
    mid = _f(c.get('price'))
    lv = c.get('liquidity')   # every candidate source names depth differently — a coin dealt with liq 0 read as "$0 pool" to the keeper
    liq = _f(c.get('liquidityUsd') or c.get('liq') or (lv.get('usd') if isinstance(lv, dict) else lv))
    px = buy_px(mid, usd, liq)
    return {'mint': c['mint'], 'pairAddress': c['pairAddress'], 'symbol': c.get('symbol'), 'role': role, 'entry': px, 'units': usd / px if px > 0 else 0.0,
            'costUsd': round(usd, 6), 'at': now, 'stars': c.get('stars') or stars(c, role), 'firstEntry': px, 'liq': liq, 'midAtEntry': mid,
            **({'newMajor': True} if c.get('newMajor') else {}), **({'arena': True} if c.get('arena') else {}), **({'trench': True} if c.get('trenchOnly') else {}),
            **({'division': c['division']} if c.get('division') else {}),   # 🏁 which Gauntlet division this coin came in from
            'bought': {'tag': flow_tag(c)[0], **{k: (None if c.get(k) is None else round(_f(c.get(k)), 1)) for k in ('chg1h', 'vol1h', 'ageH', 'buyShare')}, 'liq': round(liq) if liq else None}}   # 🧾 why it was bought: what the coin looked like at that moment


def _picks(t, pools, runners, anchors):
    """anchors → pools → runners, 3★+ only, one slot per coin (a SOL pool never doubles the SOL anchor). `byVol` shapes take the
    highest-volume pools / runners first (breakeven needs flow, not just score)."""
    seen, out = set(), []
    for src, role, n in ((anchors, 'anchor', t['anchors']), (pools, 'pool', t['pools']), (runners, 'runner', t['runners'])):
        k = 0
        ranked_ = rated(src, role)
        if t.get('byVol'):
            ranked_ = sorted(ranked_, key=lambda c: -(_f(c.get('vol1h')) or _f(c.get('volume24h')) / 24))
        if role == 'runner' and t.get('growth') == 'trench':   # 🗑 up to trenchN fresh trench coins first, then normal runners
            tr = [c for c in ranked_ if c.get('trenchOnly')][:int(t.get('trenchN') or 1)]
            ranked_ = tr + [c for c in ranked_ if not c.get('trenchOnly')]
        elif role == 'runner':
            ranked_ = [c for c in ranked_ if not c.get('trenchOnly')]
        if role == 'runner' and t.get('growth') in ('major', 'runner'):   # the shape's name decides: new majors first or runners first
            ranked_ = sorted(ranked_, key=lambda c: bool(c.get('newMajor')) != (t['growth'] == 'major'))
        elif role == 'runner' and t.get('growth') == 'mix':   # one new major + one runner first, then the best of the rest
            nm = [c for c in ranked_ if c.get('newMajor')]; rn = [c for c in ranked_ if not c.get('newMajor')]
            ranked_ = nm[:1] + rn[:1] + [c for c in ranked_ if c not in nm[:1] + rn[:1]]
        for c in ranked_:
            if k >= n:
                break
            if _f(c.get('price')) > 0 and c.get('mint') not in seen:
                seen.add(c.get('mint')); out.append((c, role)); k += 1
    return out


def rotate_anchors(anchors, offset=0):
    """Rotate the eligible-major basket at a scheduled re-shape. Initial deals begin with the most ACTIVE major (`fuse.rank_anchors`), and a one-anchor phase
    must not silently mean "SOL forever"; subsequent configured shapes walk the existing ranked majors without inventing a
    new threshold or bypassing any candidate gate."""
    rows = list(anchors or [])
    if not rows:
        return rows
    n = int(_f(offset)) % len(rows)
    return rows[n:] + rows[:n]


FRESH_SEC = 900.0   # a coin bought in the last 15 minutes is never sold by a re-shape (it has not had a round to prove anything)


def keep_winners(nc, old_legs, prices, liqs, pct, in_play_usd, now=None, hold_sec=0.0):
    """🛡 A re-shape never sells a winner: old coins up ≥ pct% (or ❄ frozen, or riding) are CARRIED into the new card as they are
    (same units + entry); the freshly dealt coins give up their slots and share what's left of the money, so the total stays exactly
    `in_play_usd`. Returns (card or None if every coin is kept → no re-shape, kept count)."""
    again = {l['mint'] for l in nc['legs']}   # ♻ a coin the new shape deals AGAIN is carried as it is — selling it to buy it straight back only pays fees
    # 🍳 the card's own min hold covers a re-shape too: a coin still inside it is carried, whatever the new shape wants
    new_ = lambda l: now is not None and _f(l.get('at')) > 0 and 0 <= now - _f(l['at']) < max(FRESH_SEC, _f(hold_sec))   # 🆕 just bought: sold 3.5 min later for the next shape = fees for nothing
    win = [l for l in old_legs if l.get('role') != 'anchor' and _f(l.get('entry')) > 0 and (l.get('frozen') or l.get('ride') or l.get('picked') or l['mint'] in again or new_(l) or
           (_f(pct) > 0 and ((_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] - 1) * 100 >= _f(pct)))]
    if not win:
        return nc, 0
    want = {l['mint']: _f(l['units']) for l in nc['legs']}
    def carry(l):   # a re-picked (unprotected) coin keeps its entry but only up to its new slot — the rest is trimmed, never sold whole + rebought
        prot = l.get('frozen') or l.get('ride') or l.get('picked') or new_(l) or (_f(pct) > 0 and ((_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] - 1) * 100 >= _f(pct))
        if prot or l['mint'] not in want or _f(l['units']) <= want[l['mint']]:
            return l
        k = want[l['mint']] / _f(l['units'])
        return {**l, 'units': want[l['mint']], 'costUsd': round(_f(l.get('costUsd')) * k, 6)}
    win = [carry(l) for l in win]
    keep_val = sum(value({'legs': [l], 'cash': 0.0}, prices, liqs) for l in win)
    wm = {l['mint'] for l in win}
    fresh = [l for l in nc['legs'] if l['mint'] not in wm]
    need = len(win) - (len(nc['legs']) - len(fresh))   # winners that need a slot of their own
    for _ in range(max(0, need)):
        drop = next((l for l in reversed(fresh) if l.get('role') != 'anchor'), None)
        if not drop:
            break
        fresh.remove(drop)
    left = _f(in_play_usd) - keep_val
    if left <= 0.01 or not fresh:
        return None, len(win)   # the winners ARE the card: nothing to re-shape
    f = left / (sum(_f(l['costUsd']) for l in fresh) or 1)
    fresh = [{**l, 'units': l['units'] * f, 'costUsd': round(_f(l['costUsd']) * f, 6)} for l in fresh]
    out = {**nc, 'legs': fresh + [{k: v for k, v in l.items() if k != 'picked'} for l in win]}
    # A shape is a fixed slot count. Carrying a winner must replace a fresh slot, never append a fifth coin;
    # conversely a sold/failed leg must not collapse a 4-slot shape to three when eligible fresh picks exist.
    target_n = len(nc['legs'])
    if len(out['legs']) > target_n:
        protected = {l['mint'] for l in win}
        while len(out['legs']) > target_n:
            drop = next((l for l in reversed(out['legs']) if l['mint'] not in protected), None)
            if not drop:
                break
            out['legs'].remove(drop)
    return out, len(win)   # a hand pick survives ONE re-shape


def size_slots(size_usd, min_coin_usd, want):
    """How many coins a card of this size holds: as many of the shape's `want` slots as keep every coin ≥ `min_coin_usd` (never under 1).
    Off (0 / None) = the full shape. A $2 card at $0.75 a coin holds 2 coins, a $5 card all 4."""
    m = _f(min_coin_usd)
    return int(want) if m <= 0 else max(1, min(int(want), int(_f(size_usd) // m)))


def grow_picks(picks, want, pools, runners, anchors):
    """More coins than the shape has: add the best candidates not on it yet — runners first, then pools, then majors — up to `want`.
    Never duplicates a coin; returns what exists when the feeds can't fill every extra seat."""
    out = list(picks); have = {c.get('mint') for c, _ in out}
    for src, role in ((runners, 'runner'), (pools, 'pool'), (anchors, 'anchor')):
        for c in rated(src, role):
            if len(out) >= want:
                return out
            if c.get('mint') not in have and _f(c.get('price')) > 0 and not c.get('trenchOnly'):   # 🗑 extra seats never take a trench coin
                out.append((c, role)); have.add(c.get('mint'))
    return out


def fit_count(picks, n):
    """Trim to n coins keeping the card's character: the first anchor, then the first non-anchor, then the rest in order."""
    if n <= 0 or n >= len(picks):
        return picks
    anchors_ = [p for p in picks if p[1] == 'anchor']; others = [p for p in picks if p[1] != 'anchor']
    keep = (anchors_[:1] + others[:1] + anchors_[1:] + others[1:])[:n]
    return [p for p in picks if any(p is k for k in keep)]


def fit_size(picks, size_usd, min_coin_usd):
    """Trim a dealt shape to the card's size, keeping its character: the first anchor, then the first non-anchor, then the rest in order."""
    n = size_slots(size_usd, min_coin_usd, len(picks))
    if n >= len(picks):
        return picks
    anchors_ = [p for p in picks if p[1] == 'anchor']; others = [p for p in picks if p[1] != 'anchor']
    order = anchors_[:1] + others[:1] + anchors_[1:] + others[1:]
    keep = order[:n]
    return [p for p in picks if p in keep]


TRENCH_STAKES = (0, 10, 15, 25)
TRENCH_SLS = (0, 15, 20, 25, 30)


def trench_n(cfg):
    """🗑 1 or 2 trench coins per card (owner's pick, default 1)."""
    n = int(_f((cfg or {}).get('trenchCoins')) or 1)
    return n if n in TRENCH_COINS else 1


def deal(tid, pools, runners, cfg, now, anchors=(), usd=None, keep=None, shape=None):
    """A fresh Prime card from the best 3★+ candidates (gated + ranked by the caller). Equal $ per coin. `keep` re-deals an
    existing card (after its floor) while keeping its start, events and record — P&L stays honest across re-deals."""
    t = {**TEMPLATES[tid], **(PHASES.get(shape) or {}), 'trenchN': trench_n(cfg)}
    # Each due shape advances the major basket. This makes one-anchor phases use different eligible majors over time while
    # keeping the configured number of anchors and the service's existing major ranking authoritative.
    every = int(_f(cfg.get('cycleEvery'))) or 1
    anchor_offset = int(_f((keep or {}).get('rounds')) // every) if shape else 0
    want = int(_f(cfg.get('coins')))
    picks = _picks(t, pools, runners, rotate_anchors(anchors, anchor_offset))
    target_slots = int(t.get('anchors', 0)) + int(t.get('pools', 0)) + int(t.get('runners', 0))
    if want:   # 🪙 the owner chose how many coins: more than the shape → the best coins not on it yet join; fewer → the shape is trimmed
        full_shape = len(picks) == target_slots
        picks = fit_count(grow_picks(picks, want, pools, runners, rotate_anchors(anchors, anchor_offset)), want)
        if full_shape or len(picks) == want:   # the shape itself was complete (or the owner's count was reached) → this deal is whole
            target_slots = len(picks)
    # A configured phase is atomic: never commit a partial 3-leg version of a 4-slot shape. Keep the current card until all
    # eligible slots exist, then reshape once. This permanently prevents feed scarcity from shrinking a live phase.
    if not picks or (shape and len(picks) != target_slots):
        return None
    size = usd if usd is not None else cfg['sizeUsd']
    picks = fit_size(picks, size, cfg.get('minCoinUsd'))   # 🪙 small cards hold fewer coins (each coin stays big enough for its fees)
    each = size / len(picks)
    base = {'id': f'prime-{tid}', 'tpl': tid, 'label': t['label'], 'at': now, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': size, 'dayAt': now, 'dayStartUsd': size, 'days': [], 'lowPct': 0.0}   # a fresh card starts at the $ it was dealt with
    c = {**base, **(keep or {})}
    c.update(lastRotateAt=now, legs=[_leg(x, each, now, r) for x, r in picks], cash=0.0, flooredAt=None)
    c['startUsd'] = (keep or {}).get('startUsd', size)
    c['putInUsd'] = _f((keep or {}).get('putInUsd')) or (put_in(keep) if keep else size)   # 💵 what was put in survives every restart
    c['feesUsd'] = round(_f(c['feesUsd']) + cfg['paperFeeUsd'] * len(picks), 4)
    c['events'] = list(c['events']) + [{'kind': 'phase' if shape else 'deal', 'at': now, 'n': len(picks), 'why': PHASES[shape]['why'] if shape else ('re-dealt after the floor' if keep else 'fresh card')}]
    if shape:
        c['phase'] = shape
    return c


def value(card, prices, liqs=None):
    """What the card is worth to its owner: coins at what SELLING them would really pay (pool impact — a $100K bag in a $30K pool is
    not worth $100K) + cash + parked SOL + what it already paid out to the wallet (never hidden). No liquidity known = mid price."""
    liqs = liqs or {}
    def coin(l):
        px = _f(prices.get(l['pairAddress'])) or l['entry']
        return sell_usd(l['units'], px, _f(liqs.get(l['pairAddress'])) or _f(l.get('liqNow')) or _f(l.get('liq')))
    v = sum(coin(l) for l in card['legs']) + card['cash'] + sum(_f(p['usd']) for p in (card.get('parked') or {}).values()) + _f(card.get('walletUsd')) + _f(card.get('rentUsd'))
    return round(v, 4)


def in_play(card, prices, liqs=None):
    """What can be re-dealt into coins: the card's value MINUS what was already paid out to the wallet and what sits parked
    (both stay theirs — re-buying coins with them would count the same dollars twice)."""
    return round(value(card, prices, liqs) - _f(card.get('walletUsd')) - _f(card.get('rentUsd')) - sum(_f(p.get('usd')) for p in (card.get('parked') or {}).values()), 4)


def tick(card, prices, pools, runners, cfg, now, anchors=(), mom=None, liqs=None, true_usd=None, blind=False):
    """One automation pass. Returns the updated card (mutated copy) — all actions logged as events with reasons.
    liqs = {pair: pool liquidity $} for TRUE fills (price impact on every paper buy / sell)."""
    liqs = liqs or {}
    t = card_template(card['tpl'], cfg)
    c = {**card, 'legs': [dict(l) for l in card['legs']], 'events': list(card['events'])}
    have = lambda: {l['mint'] for l in c['legs']}
    # 💵 a REAL card is judged on its true book (confirmed coins + SOL), never on the engine's estimate — an estimate that missed
    # unlanded / skipped buys once read −32% on a card really at −20% and the floor sold everything twice in 20 min
    V = (lambda: _f(true_usd)) if true_usd is not None and _f(true_usd) > 0 else (lambda: value(c, prices, liqs))
    # 🙈 BLIND = a real card whose true book can't be read this tick (an order in flight, no SOL price). The engine's estimate does
    # not see money in transit (coins sold, new coins not landed yet), so no CARD-WIDE call is made on it: no floor, no day fix,
    # no rescue. Found live: two picks mid-swap read −40% on a card that had lost nothing → the floor sold every coin.
    blind = bool(blind) and not (true_usd is not None and _f(true_usd) > 0)
    ev = lambda **e: c['events'].append({'at': now, **e})
    fee = cfg['paperFeeUsd']

    def best(role, trench=False):
        src = rated(runners if role == 'runner' else anchors if role == 'anchor' else pools, role)
        if role == 'runner':   # 🗑 a trench leg is replaced by the best trench coin first; trench-only coins never fill a normal slot
            src = ([x for x in src if x.get('trenchOnly')] + [x for x in src if not x.get('trenchOnly')]) if trench else [x for x in src if not x.get('trenchOnly')]
        if role == 'runner' and cfg.get('strictRunners'):   # 🌧 runner weather is bad: only runners with real flow + buyers get in
            src = [x for x in src if _f(x.get('vol1h')) >= STRICT_VOL1H and (x.get('buyShare') is None or _f(x.get('buyShare')) >= STRICT_BUYS)]
        return next((x for x in src if x['mint'] not in have() and _f(x.get('price')) > 0 and price_agrees(x, prices)), None)
    def fallback_coin():   # 🪑 the next-best watched coin (see reputation_service: `seatFallback`), never one on the card
        return next((x for x in cfg.get('seatFallback') or [] if x.get('mint') not in have() and _f(x.get('price')) > 0 and price_agrees(x, prices)), None)
    # A prior replace may have reserved its slot when that feed had no eligible candidate. Heal it as soon as one exists.
    # This runs before TP/stops/rotation, preserves the configured slot count, and spends only the cash already returned by that sale.
    for l in list(c['legs']):
        if not l.get('placeholder') or l.get('manualCash') or _f(l.get('units')) > 0:
            continue
        role_h = l.get('role') or 'runner'
        # the seat's own kind first; none eligible → any buyable coin (a seat must end in a coin, not wait on one feed)
        nxt = best(role_h, l.get('trench')) or next((x for x in (best(r_) for r_ in ('runner', 'pool') if r_ != role_h) if x), None)
        fb_used = False
        if not nxt and now - _f(l.get('at')) >= SEAT_FALLBACK_SEC:
            nxt = fallback_coin(); fb_used = bool(nxt)
        if not nxt and now - _f(l.get('at')) >= max(120.0, _f(cfg.get('rotateHours')) * 3600):
            # 🔔 NO COIN FOR A WHOLE ROUND → the seat is given up and its money goes back to work in the card's coins (it used to
            # sit reserved for as long as the feed stayed empty: $0.66 idle on a $2.40 card). The seat refills when a coin qualifies.
            c['legs'].remove(l)
            ev(kind='slot', symbol=l.get('symbol'), usd=round(_f(l.get('reserveUsd')), 4), why=f"no safe coin for ${l.get('symbol')}'s seat within a round — its money goes back into the card's coins; the seat refills when one qualifies", to=['card'])
            continue
        if not nxt or c['cash'] < 0.01:
            continue
        usd = min(c['cash'], _f(l.get('reserveUsd')) or (_f(l.get('wantUnits')) * (_f(prices.get(l['pairAddress'])) or _f(l.get('entry')))) or c['cash'])
        if usd < 0.01:
            continue
        c['legs'][c['legs'].index(l)] = _leg(nxt, usd, now, nxt.get('role') if nxt.get('role') in ('runner', 'pool') else role_h)
        c['cash'] = max(0.0, c['cash'] - usd)
        ev(kind='replace', symbol=l.get('symbol'), usd=round(usd, 4), why='reserved seat filled — next-best coin after 30s (none cleared the full line)' if fb_used else 'reserved replacement slot filled from eligible feed', to=[nxt.get('symbol')])
    c.setdefault('dayAt', c['at']); c.setdefault('dayStartUsd', c['startUsd']); c.setdefault('days', []); c.setdefault('lowPct', 0.0)

    # 🏦 a coin already riding that has not banked yet (the setting came on later, or its bank never reached the chain) banks once now
    for l in c['legs']:
        if l.get('ride') and not l.get('bankedAt') and not c.get('flooredAt'):
            px_b = _f(prices.get(l['pairAddress']))
            if px_b > 0 and px_b > _f(l.get('entry')):
                lock_bank(c, l, px_b, liqs, now, cfg, fee, (px_b / _f(l['entry']) - 1) * 100 if _f(l.get('entry')) > 0 else None)
    # 💰 AUTO SKIM (owner's setting): every `skimAt`% a coin gains since its entry / last skim, its profit is taken and its stake rides on
    stack_skim(c, prices, liqs, now, cfg, fee)   # 💚 every coin locked → each is skimmed down to its stake, and again as it grows
    # 🏠 TRENCH / TICKET COINS: at +`trenchHouseAt`% the initial comes out once and only profit rides (owner: "take initial and
    # just leave profit, for safety"). The money follows `skimTo` (held · parked · back into the other coins).
    ha = _f(cfg.get('trenchHouseAt'))
    if ha > 0 and not c.get('flooredAt'):
        for l in c['legs']:
            if not (l.get('trench') or l.get('ticket')) or l.get('house') or l.get('placeholder') or l.get('buying') or _f(l.get('units')) <= 0 or _f(l.get('entry')) <= 0:
                continue
            px_h = _f(prices.get(l['pairAddress']))
            if px_h > 0 and px_h >= _f(l['entry']) * (1 + ha / 100):
                _take_stake(c, l, px_h, liqs, now, cfg.get('skimTo') or 'card', fee, auto=ha)
    sk = _f(cfg.get('skimAt'))
    if sk > 0 and not c.get('flooredAt'):
        for l in c['legs']:
            if l.get('placeholder') or l.get('buying') or _f(l.get('units')) <= 0 or _f(l.get('entry')) <= 0:
                continue
            px_s = _f(prices.get(l['pairAddress']))
            if px_s > 0 and px_s >= (_f(l.get('skimPx')) or _f(l['entry'])) * (1 + sk / 100):
                _skim(c, l, px_s, liqs, now, cfg.get('skimTo') or 'card', fee, auto=sk, room=tp_room(l, cfg, px_s))
    # 🗑 TRENCH FILL: a card on the trench cycle holds its 1–2 trench coins as soon as the scan has one — it never waits up to
    # `cycleEvery` rounds for the next re-shape. The weakest normal runner (not winning > +10%, not frozen / riding / picked / waiting
    # on a buy) is sold for the best trench coin. No trench coin passing → the card keeps its normal runners.
    # The card's CURRENT cycle decides, not the shape it happens to be in: an owner who switched Trench off must not get one more
    # trench coin while the card waits (up to 6 rounds) for its next re-shape.
    if not c.get('holdAll') and not c.get('cycleFix') and 'trench' in str((cfg.get('cycles') or DEFAULT_CYCLES).get(card['tpl']) or '').split(','):
        # 🔁 NO LOOP: one trench fill per round, and never on a coin bought moments ago. A trench coin that died on arrival was replaced
        # by a normal runner, which this fill sold seconds later for the next trench coin — 2 real swaps a minute, every minute.
        first_fill = c.get('trenchFillAt') is None   # a card that just switched to trench takes its coins at once; after that the loop guard applies
        fill_due = first_fill or now - _f(c.get('trenchFillAt')) >= TRENCH_DROP_SEC   # 🗑 one trench drop every 30 min (owner's cadence; was once a round)
        cap_t = swap_cap(cfg, value(c, prices, liqs), len(c['legs']))
        if not first_fill and cap_t['cap'] and swaps_last_hour(c, now) >= cap_t['cap']:
            fill_due = False   # 🤖 the hourly cap covers trench fills too
        hold_s = max(120.0, _f(cfg.get('minHoldMins')) * 60)
        held_t = sum(1 for l in c['legs'] if l.get('trench'))
        # … and when the trench seat is already taken, the drop ROTATES it: a trench coin that is not winning gives its seat to the
        # best one on the list now (a winner / rider keeps the seat — nothing is dropped that tick)
        # 🗑 ONE trench coin every 30 minutes (owner: "every 30 mins it puts a trench in — it waits in queue for the weakest link, or
        # one only profiting no more than 10c"): it takes the seat of the WEAKEST coin whose profit is ≤ TRENCH_VICTIM_USD. No such
        # coin (every seat is winning more, riding, frozen, your pick or just bought) → the drop stays queued and is tried again
        # every tick until one qualifies; the 30 minutes then run from that swap.
        for _ in range((max(1, trench_n(cfg) - held_t) if first_fill else 1) if fill_due else 0):
            nxt = next((x for x in rated(runners, 'runner') if x.get('trenchOnly') and x['mint'] not in have() and _f(x.get('price')) > 0 and price_agrees(x, prices)), None)
            def gain(l):
                px = _f(prices.get(l['pairAddress'])); return (px / _f(l['entry']) - 1) * 100 if px > 0 and _f(l.get('entry')) > 0 else 0.0
            def profit(l):
                px = _f(prices.get(l['pairAddress'])); return _f(l.get('units')) * (px - _f(l.get('entry'))) if px > 0 else 0.0
            victims = [l for l in c['legs'] if l.get('role') == 'runner' and not l.get('frozen') and not l.get('ride')
                       and not l.get('picked') and not l.get('placeholder') and (_f(l.get('units')) > 0 or l.get('buying')) and profit(l) <= TRENCH_VICTIM_USD
                       and (first_fill or l.get('buying') or now - _f(l.get('at')) >= hold_s)]
            if not nxt or not victims:
                break
            l = min(victims, key=lambda x: (not x.get('buying'), gain(x)))   # a seat still waiting on its buy swaps for free
            px = _f(prices.get(l['pairAddress'])) or _f(l['entry'])
            units = _f(l['units']) or (_f(l.get('wantUnits')) if l.get('buying') else 0.0)
            out_usd = sell_usd(units, px, liqs.get(l['pairAddress']) or l.get('liq'))
            # 🎟 a trench coin is a SMALL ticket: at most `trenchStakePct` of the card goes in (the rest of the old coin's money
            # returns to card cash for the other coins), and it carries its own tighter stop — one pulled launch costs a slice, not a seat
            pct_t = _f(cfg.get('trenchStakePct'))
            use_usd = min(out_usd, value(c, prices, liqs) * pct_t / 100) if pct_t > 0 else out_usd
            nl_ = _leg(nxt, use_usd, now, 'runner')
            if _f(cfg.get('trenchSlPct')) > 0:
                nl_['sl'] = _f(cfg.get('trenchSlPct'))
            if pct_t > 0:
                nl_['ticket'] = True   # 🎟 never topped up to a full seat (the sweep put $0.30 back into a fresh coin 48s after it was bought)
            c['legs'][c['legs'].index(l)] = nl_
            c['cash'] = round(_f(c.get('cash')) + (out_usd - use_usd), 6)
            c['feesUsd'] = _f(c.get('feesUsd')) + 2 * fee
            ev(kind='rotate', symbol=l['symbol'], usd=round(use_usd, 4), why=f"🗑 trench drop — {gain(l):+.1f}% {'trench coin' if l.get('trench') else 'runner'} swapped for the best trench coin on the list"
                                                                               + (f" (${use_usd:.2f} ticket = {pct_t:g}% of the card, stop −{_f(cfg.get('trenchSlPct')):g}%)" if pct_t > 0 else ''), to=[nxt.get('symbol')])
            c['trenchFillAt'] = now

    # ⚡ INSTANT LOSS SWAP: this is deliberately NOT a round rule. Once a non-anchor coin reaches the owner's configured
    # loss from entry, it exits on this tick — no patience counter and no minimum-hold wait. Frozen/riding/manual Hold All still win.
    instant_loss = _f(cfg.get('instantSwapPct'))
    if instant_loss > 0 and not c.get('holdAll'):
        for l in list(c['legs']):
            if safe_anchor(l) or l.get('frozen') or l.get('ride') or l.get('placeholder') or l.get('buying') or int(l.get('freezeRounds') or 0) > 0:
                continue
            px = _f(prices.get(l['pairAddress']))
            if px <= 0 or _f(l.get('entry')) <= 0 or _f(l.get('units')) <= 0:
                continue
            dd = (px / _f(l['entry']) - 1) * 100
            if dd > -instant_loss + PCT_EPS:
                continue
            if dd <= -GAP_PCT and now - _f(l.get('at')) < GAP_SECS:
                continue   # "−87% ten seconds after the buy" is two price feeds disagreeing, not a loss — never sell on it (the rug shield still runs)
            out_usd = sell_usd(l['units'], px, liqs.get(l['pairAddress']) or l.get('liq'))
            # ⚡ sell AND buy: when no runner is eligible right now (weather / age / pool floor), the slot takes the best pool
            # instead of sitting in cash — "instant swap" must end in a coin whenever any eligible coin exists
            nxt = best(l.get('role') or 'runner', l.get('trench')) or (best('pool') if (l.get('role') or 'runner') == 'runner' else None)
            c['feesUsd'] += fee
            if nxt:
                c['legs'][c['legs'].index(l)] = _leg(nxt, out_usd, now, l.get('role') or 'runner')
                c['feesUsd'] += fee
                ev(kind='instant-swap', symbol=l['symbol'], usd=round(out_usd, 4),
                   why=f"{dd:.1f}% ≤ −{instant_loss:g}% instant-loss trigger — swapped now", to=[nxt.get('symbol')])
            else:
                # Risk comes off immediately even if the replacement feed is temporarily empty. Keep the slot + its proceeds
                # reserved so normal compounding cannot spend that money before an eligible replacement appears.
                c['legs'][c['legs'].index(l)] = {**l, 'units': 0.0, 'costUsd': 0.0, 'buying': False, 'placeholder': True,
                                                 'reserveUsd': round(out_usd, 6), 'entry': px, 'at': now}
                c['cash'] += out_usd
                ev(kind='instant-swap', symbol=l['symbol'], usd=round(out_usd, 4),
                   why=f"{dd:.1f}% ≤ −{instant_loss:g}% instant-loss trigger — sold now; replacement slot reserved", to=['cash'])

    # 0) a floored card sits in its anchor (cash-like) until the next day, then is re-dealt fresh at its current value
    if c.get('flooredAt') and not blind and now - c['flooredAt'] >= max(60.0, _f(cfg.get('floorRestMins')) * 60):   # floored → re-dealt with fresh 3★+ coins on the very next tick (a new run)
        v0 = V()
        keep = {k: c[k] for k in c if k not in ('legs', 'cash', 'lastRotateAt')}
        # a NEW run starts at today's value (its own −floor); the ended run is kept on the record, never hidden
        keep['runs'] = (list(c.get('runs') or []) + [{'at': now, 'startUsd': c['startUsd'], 'endUsd': round(v0, 4), 'pct': round((v0 / (_f(c['startUsd']) or 1) - 1) * 100, 2)}])[-10:]
        keep.update(startUsd=round(v0, 4), dayStartUsd=round(v0, 4), dayAt=now, lowPct=0.0, roundStartUsd=round(v0, 4))   # a new run = a new round baseline
        nc = deal(c['tpl'], pools, runners, cfg, now, anchors, usd=in_play(c, prices, liqs), keep=keep)
        if nc:
            c = nc

    # 0b) 🚨 RUG SHIELD (real-world add-on): a coin whose pool liquidity fell to ≤ half of what it had at entry is sold at once to
    #     cash — before the stop, the trail or the floor. Anchors (majors) are exempt; frozen coins too (the owner's call).
    now_ = now_picks(c) if not c.get('flooredAt') else set()   # ⚡ the owner said "swap in now": no wait for the bell
    if now_:
        apply_queued(c, prices, liqs, now, fee, only=now_, why='🎯 your pick — swapped in now')
    near = near_stop_picks(c, prices, t) if not c.get('flooredAt') else set()   # 🎯 your pick comes in 5 points before the stop, not after it
    if near:
        apply_queued(c, prices, liqs, now, fee, only=near, why=f'🎯 your pick — swapped in early: the coin was within {PICK_NEAR_STOP:g}% of its stop')
    for l in list(c['legs']):
        lq, lq0 = _f(liqs.get(l['pairAddress'])), _f(l.get('liq'))
        if safe_anchor(l) or l.get('frozen') or lq <= 0 or lq0 <= 0 or lq > lq0 * RUG_LIQ:
            continue
        px = _f(prices.get(l['pairAddress'])) or l['entry']
        usd = sell_usd(l['units'], px, lq)
        c['legs'].remove(l); c['cash'] += usd; c['feesUsd'] += fee
        ev(kind='rug', symbol=l['symbol'], usd=round(usd, 4), why=f"liquidity ${lq0 / 1000:.0f}K → ${lq / 1000:.0f}K (−{(1 - lq / lq0) * 100:.0f}%) — pulled, sold at once", to=['cash'])
    # 1) auto take-profit — HOW MUCH depends on momentum (exit_plan): ride / gain / bank → compound into the others or cash
    mom = mom or {}
    for l in c['legs']:
        px = _f(prices.get(l['pairAddress']))
        if px <= 0 or l['entry'] <= 0:
            continue
        if not l.get('priced') and l.get('at') and now - _f(l['at']) < 180:   # 🎯 first tick of a NEW coin: entry = the live routing price (a DexScreener
            l['units'] = _f(l.get('costUsd')) / px if px > 0 else l['units']   # gap once showed −87% on tick one and stopped it out at once)
            l['entry'] = l['firstEntry'] = px
        l['priced'] = True
        g = (px / l['entry'] - 1) * 100
        # 🏇 RUNNER RIDE: a coin up ≥ +150% is frozen through rounds (no TP, no stop, no rotation) and labelled a runner while it keeps
        # making highs; it is sold only when it falls 30% from its NEW high. (A 200× never gets cut at +150%.)
        l['roundMin'] = min(_f(l['roundMin']) if l.get('roundMin') is not None else g, g)
        ra, rt = _f(cfg.get('rideAt')) or RIDE_AT, _f(cfg.get('rideTrail')) or RIDE_TRAIL
        floor_g = min(HOLD_MIN, ra / 2)   # a +25% freeze can't demand +80% to keep holding
        if cfg.get('trailStep') and l.get('ride'):   # 🪜 the more it is up, the more room it gets (see trail_for)
            rt = trail_for(rt, (max(_f(l.get('high')), px) / l['entry'] - 1) * 100)
        if l.get('ride'):
            l['high'] = max(_f(l.get('high')), px)
            if g >= floor_g and px > l['high'] * (1 - rt / 100):
                continue   # still holding: above its floor and not rt% off its high
            why_end = (f"fell under +{floor_g:g}% ({g:+.0f}%)" if g < floor_g else f"fell {rt:g}% from its peak") + f" after riding to {l['high'] / (l.get('rideFrom') or l['entry']):.1f}×"
            # 🏔 OFF ITS PEAK ≠ OVER: while the coin is still well up (above its floor), only `peakSellPct` of its PROFIT is sold and
            # the coin keeps riding from here (the trail re-arms at this price). A big coin gets room to go again — the card keeps
            # cycling its other seats until the next one is found. Under the floor the ride really is over (swapped, as before).
            ps = _f(cfg.get('peakSellPct', PEAK_SELL))
            if g >= floor_g and 0 < ps < 100:
                took = _skim(c, l, px, liqs, now, cfg.get('skimTo') or 'card', fee, room=tp_room(l, cfg, px), frac=ps / 100,
                             why=f"🏔 ${l['symbol']} fell {rt:g}% from its peak (still {g:+.0f}%) — {ps:g}% of its profit sold, the rest keeps riding")
                l['high'] = px   # the next {rt}% is counted from here
                if took:
                    c['events'][-1]['kind'] = 'peak-sell'
                continue
            l['ride'] = False
            nxt = best(l.get('role') or 'runner', l.get('trench'))
            if nxt:   # 🏇 ride over → SWAPPED for the best coin of its kind (the gain moves into it)
                usd = sell_usd(l['units'], px, liqs.get(l['pairAddress']) or l.get('liq'))
                c['legs'][c['legs'].index(l)] = _leg(nxt, usd, now, l.get('role') or 'runner'); c['feesUsd'] += 2 * fee; c['takenUsd'] += max(0.0, usd - _f(l.get('costUsd')))
                ev(kind='ride-end', symbol=l['symbol'], usd=round(usd, 4), why=f"{why_end} — swapped", to=[nxt.get('symbol')])
                continue
            mode, frac, why = 'ride-end', 1.0, f"{why_end} — sold" 
        elif _f(cfg.get('rideAt', RIDE_AT)) > 0 and g >= ra and l.get('role') != 'anchor' and _f(l.get('units')) > 0:   # never 'ride' a coin you don't hold
            l.update(ride=True, high=px, rideFrom=l['entry'], rideAt=now)
            ev(kind='ride', symbol=l['symbol'], usd=round(l['units'] * px, 4), why=f"+{g:.0f}% ≥ +{ra:g}% — ❄ frozen (riding) until it falls {rt:g}% from its peak, then swapped", to=[l['symbol']])
            lock_bank(c, l, px, liqs, now, cfg, fee, g)
            continue
        elif g >= leg_tp(l, t):
            mode, frac, why = exit_plan(g, mom.get(l['pairAddress']))
        else:
            continue
        if True:
            before_units = _f(l.get('units'))
            sold = before_units * frac
            proceeds = sell_usd(sold, px, liqs.get(l['pairAddress']) or l.get('liq'))   # what the pool really pays
            # Only REALIZED PROFIT may be paid out. The sold slice's principal always stays in the card.
            # Splitting gross proceeds here used to siphon principal into walletUsd (100% payout could starve a live slot).
            total_cost = _f(l.get('costUsd')) or before_units * _f(l.get('entry'))
            sold_cost = total_cost * (sold / before_units) if before_units > 0 else 0.0
            profit = max(0.0, proceeds - sold_cost)
            l['units'] = max(0.0, before_units - sold)
            l['costUsd'] = max(0.0, total_cost - sold_cost)
            l['entry'] = px; c['feesUsd'] += fee
            c['takenUsd'] += proceeds
            others = [o for o in c['legs'] if o is not l and _f(prices.get(o['pairAddress'])) > 0 and (_f(o.get('units')) > 0 or o.get('buying')) and not o.get('placeholder')]   # never into an empty / reserved seat
            label = why if mode == 'ride-end' else f"+{g:.0f}% ≥ +{leg_tp(l, t):g}% · {why}"   # a held runner's exit explains itself
            # 🧬 payoutPct applies to realized PROFIT, never principal. Principal + retained profit stay available to compound/rebuy.
            dna = {'payoutPct': (cfg.get('payouts') or DEFAULT_PAYOUTS).get(card['tpl'], 0), 'compound': cfg.get('compoundStyle', 'smart') if cfg['compound'] else 'off'}
            out_usd, retained_profit = _dna.split_profit(profit, dna)
            # 💰 PROFIT ONLY: a card pays out only while the WHOLE card is above what it started with. One coin's win on a card that
            # is still down is not profit yet — it stays in the card (paper used to pay out $2.88 from a card that was −70%).
            # the line is the money the owner HAS IN: real = funded principal minus what they took out (`fundedUsd`); paper = the run's start
            # …and only the part ABOVE that line: the money still IN the card (paid-out money never counts — it can't pay out what
            # the card is using) must stay ≥ what was put in. Paper's line is everything ever put in (`put_in`), never a restart's lower start.
            room = max(0.0, V() - _f(c.get('walletUsd')) + proceeds - payout_line(c))
            if out_usd > room:
                retained_profit += out_usd - room; out_usd = round(room, 6)
            recycle_usd = sold_cost + retained_profit
            if out_usd > 0:
                c['walletUsd'] = round(_f(c.get('walletUsd')) + out_usd, 6)
                ev(kind='payout', symbol=l['symbol'], usd=round(out_usd, 4), why=f"{dna['payoutPct']}% of realized profit → owner's wallet", to=['wallet'])
            if recycle_usd > 0 and others and dna['compound'] != 'off':
                wts = _dna.compound_weights(others, mom) if dna['compound'] == 'smart' else {o['pairAddress']: 1 / len(others) for o in others}
                into = [o for o in others if wts.get(o['pairAddress'])]
                for o in into:
                    each = recycle_usd * wts[o['pairAddress']]
                    opx = buy_px(_f(prices.get(o['pairAddress'])), each, liqs.get(o['pairAddress']) or o.get('liq'))
                    o['units'] += each / opx; o['costUsd'] += each
                c['compoundedUsd'] += recycle_usd; c['feesUsd'] += fee * len(into)
                ev(kind='tp', symbol=l['symbol'], usd=round(recycle_usd, 4), why=label + (' · 🧲 smart compound' if dna['compound'] == 'smart' else ''), mode=mode, to=[o['symbol'] for o in into])
            elif recycle_usd > 0 or (proceeds > 0 and dna['compound'] == 'off'):
                # Compound-off still keeps principal + un-paid proceeds as card cash; it never silently disappears.
                rest = proceeds - out_usd
                c['cash'] += rest
                ev(kind='tp', symbol=l['symbol'], usd=round(rest, 4), why=label, mode=mode, to=['cash'])
            # 🚪 SOLD WHOLE = OFF THE CARD. A coin whose ride ended with no replacement ready used to stay as a 0-unit leg; the next
            # coin's "smart compound" then poured money back INTO it and the keeper re-bought the coin that had just been sold
            # (2026-10-06: $DONSOM sold 18:24:12, wanted again 13s later for $1.82). The seat refills when a coin qualifies.
            if _f(l.get('units')) <= 1e-12 and not l.get('buying') and l in c['legs'] and len(c['legs']) > 1:
                c['legs'].remove(l)
    # 2) stop-loss (sl 0 = never stopped) — what happens follows cfg slMode:
    #    replace → sold and swapped at once for the best gated coin of the same role
    #    park    → sold to cash, the SLOT is kept; bought back when price is back at the stop-out entry with momentum
    #    hold    → never sold on a stop (the floor still protects the card)
    mode = cfg.get('slMode', 'replace')
    c['parked'] = dict(c.get('parked') or {})
    for l in list(c['legs']):
        px = _f(prices.get(l['pairAddress']))
        lmode = l.get('slMode') if l.get('slMode') in SL_MODES else mode   # ❄/✂/🅿 per coin (HQ) beats the card's mode
        if safe_anchor(l) or not leg_sl(l, t) or lmode == 'hold' or l.get('frozen') or l.get('ride') or int(l.get('freezeRounds') or 0) > 0 or px <= 0 or l['entry'] <= 0:
            continue
        dd = (px / l['entry'] - 1) * 100
        l['peak'] = max(_f(l.get('peak')), dd)
        trail = cfg.get('trail', True) and _f(l['peak']) >= TRAIL_AT and dd <= TRAIL_KEEP   # 🔒 ran +50%, now giving it back
        # early cut: half the stop + fading — never on the owner's own pick, never in a coin's first 15 min (its "1h down" was
        # read BEFORE the buy: a 🟢 buy-bottom pick is down on the hour by definition — $LOOT was cut at −3% 4 min after the owner
        # picked it with a −6% stop). The owner's full stop still applies to every coin.
        early_ok = not l.get('picked') and now - _f(l.get('at') or l.get('firstEntry')) >= FRESH_SEC
        if not trail and dd > -leg_sl(l, t) and not (early_ok and dd <= -leg_sl(l, t) / 2 and fading(mom.get(l['pairAddress']))):
            continue
        out_usd = sell_usd(l['units'], px, liqs.get(l['pairAddress']) or l.get('liq'))
        why = (f"ran +{l['peak']:.0f}%, back to {dd:+.0f}% — locked before it turned red" if trail else
               f"{dd:.0f}% ≤ −{leg_sl(l, t):g}%" if dd <= -leg_sl(l, t) else f"{dd:.0f}% and fading (1h down, sellers lead) — cut early")
        c['feesUsd'] += fee
        nxt = best(l['role'], l.get('trench')) if lmode == 'replace' else None
        if nxt:
            c['legs'][c['legs'].index(l)] = _leg(nxt, out_usd, now, l['role']); c['feesUsd'] += fee
            ev(kind='sl', symbol=l['symbol'], usd=round(out_usd, 4), why=why, to=[nxt.get('symbol')])
        elif lmode == 'park':
            c['legs'].remove(l)
            c['parked'][l['pairAddress']] = {**{k: l.get(k) for k in ('mint', 'pairAddress', 'symbol', 'role', 'stars', 'firstEntry')}, 'usd': round(out_usd, 6),
                                             'backAt': l['entry'], 'at': now, 'price': px}
            ev(kind='park', symbol=l['symbol'], usd=round(out_usd, 4), why=f"{why} — sold to SOL, slot kept; buys back at ${l['entry']:.6g} with momentum", to=['parked'])
        else:
            # REPLACE means replace. If the preferred same-role feed is temporarily empty, keep a zero-unit placeholder instead
            # of deleting the slot. The next tick/round can fill that exact slot from the existing eligible feeds; real sync then
            # reserves confirmed card SOL for it. A transient feed gap must never turn a configured 4-coin card into 3 coins.
            if lmode == 'replace':
                c['legs'][c['legs'].index(l)] = {**{k: v for k, v in l.items() if k not in ('wantUnits', 'buyingSince')}, 'units': 0.0, 'costUsd': 0.0,   # never `wantUnits`: the seat is reserved, the STOPPED coin is not wanted back
                                                 'reserveUsd': round(out_usd, 6), 'buying': False, 'entry': px, 'at': now, 'placeholder': True}
                c['cash'] += out_usd
                ev(kind='sl', symbol=l['symbol'], usd=round(out_usd, 4), why=why + ' — replacement feed temporarily empty; slot reserved', to=['cash'])
            else:
                c['legs'].remove(l); c['cash'] += out_usd
                ev(kind='sl', symbol=l['symbol'], usd=round(out_usd, 4), why=why, to=['cash'])
    # 2b) parked coins come back: price ≥ the entry they stopped out from AND momentum not fading → bought back with the parked $
    for pa, pk in list(c['parked'].items()):
        px = _f(prices.get(pa))
        if px > 0 and px >= _f(pk['backAt']) and not fading(mom.get(pa)):
            c['legs'].append(_leg({**pk, 'price': px}, pk['usd'], now, pk.get('role') or 'runner')); c['feesUsd'] += fee
            del c['parked'][pa]
            ev(kind='rebuy', symbol=pk['symbol'], usd=round(pk['usd'], 4), why='back at its entry with momentum — bought back', to=[pk['symbol']])
    # 3) auto-rotate every rotateHours: the rotateCount weakest coins out, the best candidates in
    rotated_out = set()
    # the round ends, a 10s 🔔 countdown, then the deal. 💵 Real cards deal `dealLeadSec` EARLY (5s before the countdown opens): the keeper
    # sells first, then buys, one confirmed tx at a time — so the new coins are in when the countdown hits 0, not a minute after it.
    if now - c['lastRotateAt'] >= cfg['rotateHours'] * 3600 + BELL_SEC - _f(cfg.get('dealLeadSec')) and not c.get('flooredAt'):
        apply_queued(c, prices, liqs, now, fee)   # 🎯 the owner's picks go in first, at the bell
        # 🏇 a coin that stayed ≥ +80% the WHOLE round holds through the next one (same rule then keeps or swaps it)
        for l in c['legs']:
            if l.get('role') != 'anchor' and not l.get('ride') and l.get('roundMin') is not None and _f(l['roundMin']) >= HOLD_MIN:
                l.update(ride=True, high=max(_f(l.get('high')), _f(prices.get(l['pairAddress'])) or l['entry']), rideFrom=l['entry'], rideAt=now)
                ev(kind='ride', symbol=l['symbol'], why=f"stayed ≥ +{HOLD_MIN:g}% all round — 🏇 held through the next round", to=[l['symbol']])
            l['roundMin'] = None
        # ⏳ patience (why 5-min rounds work now): a coin is a rotation candidate only after it has been losing ≥ minDrop for
        # `rotateConfirm` rounds in a row AND held ≥ `minHoldMins` — one noisy 5-min dip never sells it (protection still runs every tick)
        for l in c['legs']:
            if l.get('role') == 'anchor' or not l['entry']:
                continue
            down = at_or_below_loss(_f(prices.get(l['pairAddress'])) or l['entry'], l['entry'], cfg.get('rotateMinDrop', ROTATE_MIN_DROP))
            l['loseRounds'] = int(l.get('loseRounds') or 0) + 1 if down else 0
        patient = lambda l: int(l.get('loseRounds') or 0) >= int(cfg.get('rotateConfirm', ROTATE_CONFIRM)) and now - _f(l.get('at')) >= _f(cfg.get('minHoldMins', MIN_HOLD_MINS)) * 60
        locked_round = int(c.get('lockRounds') or 0) > 0 or bool(c.get('holdAll'))   # ✋ hold all: no rotation (stops + rug shield still run)
        ranked = [] if locked_round else sorted((l for l in c['legs'] if l.get('role') != 'anchor' and not l.get('frozen') and not l.get('ride') and int(l.get('freezeRounds') or 0) <= 0 and l['entry'] > 0
                                                 and at_or_below_loss(_f(prices.get(l['pairAddress'])) or l['entry'], l['entry'], cfg.get('rotateMinDrop', ROTATE_MIN_DROP)) and patient(l) and (t['sl'] or l.get('role') == 'pool')), key=lambda l: (_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] if l['entry'] else 1)
        swapped = 0
        cap = swap_cap(cfg, V(), len(c['legs']))
        sol_1h = next((_f(x.get('chg1h')) for x in anchors or [] if x.get('symbol') == 'SOL' and x.get('chg1h') is not None), 0.0)
        for l in ranked[:cfg['rotateCount']]:
            if cap['cap'] and swaps_last_hour(c, now) >= cap['cap']:   # 🤖 the hourly cap: this round's losers wait (stops still protect them)
                ev(kind='keep', symbol=l['symbol'], why=f"hourly swap cap reached — {cap['why']}")
                break
            nxt = best(l['role'], l.get('trench'))
            if not nxt:
                continue
            px = _f(prices.get(l['pairAddress'])) or l['entry']
            usd = sell_usd(l['units'], px, liqs.get(l['pairAddress']) or l.get('liq'))
            if cfg.get('swapEdge', True):   # ⚖ stay or swap: only when the next coin beats this one by more than the swap costs
                cost = swap_cost_pct(usd, liqs.get(l['pairAddress']) or l.get('liq'), nxt.get('liquidityUsd') or nxt.get('liq'), fee)
                nm = {**{k: nxt.get(k) for k in ('chg1h',) if nxt.get(k) is not None}, **{k: v for k, v in (mom.get(nxt.get('pairAddress')) or {}).items() if v is not None}}
                go, why_e = swap_edge(mom.get(l['pairAddress']), nm, sol_1h, cost)
                if not go:
                    ev(kind='keep', symbol=l['symbol'], why=f"⚖ kept ${l['symbol']}: ${nxt.get('symbol')} — {why_e}")
                    continue
            c['legs'][c['legs'].index(l)] = _leg(nxt, usd, now, l['role']); c['feesUsd'] += 2 * fee; swapped += 1
            rotated_out.add(l.get('mint'))
            ev(kind='rotate', symbol=l['symbol'], usd=round(usd, 4), why=f"weakest after {cfg['rotateHours']}h", to=[nxt.get('symbol')])
        c['lastRotateAt'] = now
        # one ROUND per rotation: log this round's move, start the next one from today's value
        v_now = V()
        c['rounds'] = int(c.get('rounds') or 0) + 1
        c['lastRoundPct'] = round((v_now / (_f(c.get('roundStartUsd')) or _f(c['startUsd']) or 1) - 1) * 100, 2)
        c['roundStartUsd'] = round(v_now, 4); c['roundCrowned'] = False
        # ♻ PROFIT RECYCLE (owner's setting): every `recycleEvery` rounds, `recyclePct`% of each coin's PROFIT is sold — its stake and
        # the rest of the profit stay in the coin — and that money is spread over the card's other coins (the ones under an equal
        # share get the most). Winners fund the balance; a loser is never sold for it; nothing leaves the card.
        rp = _f(cfg.get('recyclePct'))
        if rp > 0 and int(c['rounds']) % max(1, int(cfg.get('recycleEvery') or 3)) == 0 and not c.get('flooredAt'):
            for l in list(c['legs']):
                if l.get('placeholder') or l.get('buying') or _f(l.get('units')) <= 0:
                    continue
                px_r = _f(prices.get(l['pairAddress'])) or _f(l.get('entry'))
                _skim(c, l, px_r, liqs, now, 'round' if cfg.get('skimTo') == 'round' else 'card', fee, room=tp_room(l, cfg, px_r), frac=rp / 100,
                      why=f"♻ round {c['rounds']}: {rp:g}% of ${l.get('symbol')}'s profit recycled into the card's other coins — its stake keeps riding")
        # 📈 streaks: 3 losing rounds → the config is changed (safe cycle); 3 winning rounds → config locked + best coin frozen one round
        for l in c['legs']:   # a coin frozen for one round was protected through this rotation — now it's free again
            if int(l.get('freezeRounds') or 0) > 0:
                l['freezeRounds'] = int(l['freezeRounds']) - 1
        lr = _f(c['lastRoundPct']); st = int(c.get('streak') or 0)
        auto_fix = _f(cfg.get('rescuePct', RESCUE_PCT)) != 0   # 🛟 Rescue OFF = the card keeps ITS config: no rescue cycle, no losing-streak safe fix
        st = (st + 1 if st >= 0 else 1) if lr >= STREAK_PCT else (st - 1 if st <= 0 else -1) if lr <= -STREAK_PCT else st   # noise keeps the streak as is
        if int(c.get('lockRounds') or 0) > 0:   # only a real win-lock counts down (✋ hold all has no counter)
            c['lockRounds'] = int(c['lockRounds']) - 1
        if c.get('cycleFix') == 'safe' and int(c.get('rounds') or 0) >= int(c.get('fixUntil') or 0):
            c.pop('cycleFix', None); st = 0   # the safe fix lasts SAFE_FIX_ROUNDS, then the card goes back to its own cycle (never re-armed the same round)
            ev(kind='streak', why=f'safe fix done — back to its own cycle')
        if st <= -STREAK and auto_fix:
            c['cycleFix'] = 'safe'; c['fixUntil'] = int(c.get('rounds') or 0) + SAFE_FIX_ROUNDS; st = 0
            ev(kind='streak', why=f'{STREAK} losing rounds in a row — config changed: safe cycle (majors-heavy)')
        elif st >= STREAK:
            c['lockRounds'] = 1; st = 0
            win = max((l for l in c['legs'] if l.get('role') != 'anchor' and l['entry'] > 0), key=lambda l: (_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'], default=None)
            if win:
                win['freezeRounds'] = 1
            frozen_txt = f" + ${win.get('symbol')} frozen" if win else ''
            ev(kind='streak', why=f"{STREAK} winning rounds in a row — config locked for a round{frozen_txt}")
        c['streak'] = st
        n_run = int(cfg.get('roundsPerRun') or 0)
        if n_run and c['rounds'] % n_run == 0:   # this run's rounds are done → it closes on the record, the next run starts from here
            c['runs'] = (list(c.get('runs') or []) + [{'at': now, 'startUsd': c['startUsd'], 'endUsd': round(v_now, 4), 'pct': round((v_now / (_f(c['startUsd']) or 1) - 1) * 100, 2), 'rounds': n_run}])[-10:]
            c['startUsd'], c['dayStartUsd'], c['lowPct'] = round(v_now, 4), round(v_now, 4), 0.0
            ev(kind='run', usd=round(v_now, 4), why=f'{n_run} rounds done — run closed on the record, a new run starts at ${v_now:.2f}')
    # 3b) 🔄 phase cycle: a cycling tier re-deals into the next phase shape every round (same run, P&L continues)
    rp = -_f(cfg.get('rescuePct', -RESCUE_PCT))
    if rp == 0 and c.get('cycleFix'):   # the owner switched rescue off while a fix was running → it ends NOW (it used to stay on for good)
        ev(kind='streak', why=f"rescue is off — {c['cycleFix']} fix ended, back to the card's own cycle")
        c.pop('cycleFix', None); c.pop('fixUntil', None)
    if rp < 0 and not blind and not c.get('cycleFix') == 'rescue' and (V() / (_f(c['startUsd']) or 1) - 1) * 100 <= rp:
        c['cycleFix'] = 'rescue'   # 🛟 fell rescuePct% under its start → safest ⇄ breakeven until a new run
        ev(kind='rescue', why=f'card ≤ {rp:.0f}% of its start — 🛟 rescue cycle: safest run ⇄ breakeven runners')
    every = reshape_every(c, cfg)   # a fix re-shapes every `fixEvery` · a picked cycle always cycles (0 = off only when no cycle is picked)
    phase = None if not every or c.get('holdAll') else next_phase(c.get('cycleFix') or (cfg.get('cycles') or DEFAULT_CYCLES).get(card['tpl'], 'off'), (int(c.get('rounds') or 0) // every), c.get('lastRoundPct'))
    majors_only = all(l.get('role') == 'anchor' for l in c['legs'])
    if every and int(c.get('rounds') or 0) % every and not (majors_only and phase and phase != 'anchor'):
        phase = None   # re-shape every N rounds only (less churn) — EXCEPT a majors-only card due a growth shape re-shapes at once
    grow_now = majors_only and phase and phase != 'anchor'   # a majors-only card due growth isn't held back by the win-lock
    current_shape = PHASES.get(c.get('phase')) or {}
    current_slots = int(current_shape.get('anchors', 0)) + int(current_shape.get('pools', 0)) + int(current_shape.get('runners', 0))
    # Legacy underfill can exist on or between boundaries. On a due boundary the configured NEXT phase gets first chance;
    # if that full shape is unavailable, we fall back to repairing the CURRENT phase instead of leaving a 3-leg live card.
    due_boundary = bool(every and int(c.get('rounds') or 0) % every == 0)
    # a card's full shape is what its owner asked for (`coins`), else the size-aware count — never "underfilled" against the template
    current_slots = (min(int(_f(cfg.get('coins'))), max(len(c.get('legs') or []), 1)) if int(_f(cfg.get('coins'))) else size_slots(V(), cfg.get('minCoinUsd'), current_slots)) if current_slots else 0
    underfilled = bool(current_slots and len(c.get('legs') or []) < current_slots and not c.get('cycleFix'))
    if underfilled and not due_boundary:
        phase, grow_now = c.get('phase'), True
    if c.pop('redealNow', None) and not c.get('flooredAt'):   # 🃏 one-tap re-deal: fresh coins NOW, same money + run (real cards keep their book)
        phase, grow_now, c['lastRotateAt'] = phase or c.get('phase') or 'mixed', True, now
    # ♻ SAME SHAPE AGAIN = NOTHING TO RE-SHAPE. A cycle whose next shape is the one the card already has (trench → trench) used to
    # re-deal anyway: every coin under +5% was sold for whatever ranked first that minute — the owner's $5 card sold break-even coins
    # every 30 min (≈ 11 real swaps an hour). Weak coins still leave one by one through rotation and the exits; a full card of the
    # same shape is left alone. (An underfilled card, a one-tap re-deal and a majors-only card due growth still deal.)
    if phase and phase == c.get('phase') and not underfilled and not grow_now and len(c.get('legs') or []) > 0:
        phase = None
    if phase and (c['lastRotateAt'] == now or underfilled) and not c.get('flooredAt') and (grow_now or not int(c.get('lockRounds') or 0)):
        # Protected coins do not block the whole scheduled shape. `keep_winners` carries riders, frozen/manual picks and configured
        # winners into the new shape, while the unprotected slots can still become majors/new majors as the saved cycle requires.
        ip = in_play(c, prices, liqs)
        # A phase re-shape runs on this same boundary. Do not immediately select the mint that was just rotated out.
        phase_pools = [x for x in pools if x.get('mint') not in rotated_out]
        phase_runners = [x for x in runners if x.get('mint') not in rotated_out]
        nc = deal(c['tpl'], phase_pools, phase_runners, cfg, now, anchors, usd=ip, keep={k: c[k] for k in c if k not in ('legs', 'cash', 'lastRotateAt')}, shape=phase)
        # Boundary fallback for legacy damage: never override a valid scheduled reshape, but if that complete shape cannot be
        # built and the live card is already short a slot, repair its current configured phase from the same eligible feeds.
        if not nc and underfilled and c.get('phase') and c.get('phase') != phase:
            repair_phase = c.get('phase')
            nc = deal(c['tpl'], phase_pools, phase_runners, cfg, now, anchors, usd=ip,
                      keep={k: c[k] for k in c if k not in ('legs', 'cash', 'lastRotateAt')}, shape=repair_phase)
            if nc:
                phase = repair_phase
        if nc:
            same = {l['mint'] for l in nc['legs']} <= {l['mint'] for l in c['legs']}
            nc, kept = keep_winners(nc, c['legs'], prices, liqs, cfg.get('keepWinPct', 5.0), ip, now, _f(cfg.get('minHoldMins')) * 60)
            if not nc and same:
                c['phase'] = phase   # ♻ the new shape deals the very coins the card holds → shape moves on, zero trades
            if nc:
                nc['feesUsd'] = round(_f(nc['feesUsd']) + fee * (len(c['legs']) - kept), 4)   # selling the old shape (kept coins aren't sold)
                if kept:
                    nc['events'] = list(nc.get('events') or []) + [{'kind': 'keep', 'at': now, 'why': f'🛡 {kept} winning / frozen coin{"s" if kept > 1 else ""} carried into the {phase} shape — never sold by a re-shape'}]
                c = nc
    # 4) idle cash goes back to work when compounding. Cash reserved for an empty replacement slot is untouchable.
    clamp_hold(c)                 # 🅿 never more parked than the card really holds in cash (fees come out of that cash)
    release_parked(c, cfg, now)   # 🅿 parked profit whose rounds are up joins the idle cash — BEFORE free cash is counted (it used to wait one more tick)
    # 🅿 PARKED MEANS PARKED (owner, 2026-10-07: "parked 6 rnds means just that"): nothing releases a park before its rounds are
    # up — not a queued pick, not an empty seat. A seat with no free cash is funded by trimming the coins above an equal share
    # (below), or waits. (Two earlier rules released the park for a pick: first all of it, then one seat's share.)
    reserved_cash = sum(_f(l.get('reserveUsd')) for l in c['legs'] if l.get('placeholder')) + _f(c.get('holdCashUsd'))   # + cash the owner sold out by hand
    free_cash = max(0.0, _f(c['cash']) - reserved_cash)
    # 🪑 AN EMPTY SEAT IS REFILLED: the owner asked for N coins; a seat lost to a refused buy ("slot back to card cash") used to stay
    # empty for good — the card sat on 3 coins with cash idle. As soon as there is cash for it, the best coin not on the card takes
    # the seat with an equal share (runner first, then pool). One seat a tick; never while floored / held.
    want_n = int(_f(cfg.get('coins')))
    c['seats'] = want_n   # the keeper sizes its smallest order to the card's seats (fuse_wallet.min_order)
    # 💵 on a real card a seat is only opened when the keeper can actually SEND its buy (cfg `minOrderUsd` = this card's smallest
    # order, 0 on paper) and a coin is only trimmed for it by an amount the keeper would really sell — else the seat waits, said once
    mo = _f(cfg.get('minOrderUsd'))
    seat_min = max(mo, 0.10) if mo > 0 else SEAT_MIN_USD
    # 🪑🪑 the owner may queue a pick for EVERY empty seat (`seatPick` + `seatQueue`): all of them are seated on this same tick.
    # The engine's own choice still fills one seat a tick.
    for _seat_n in range(8):
      if not c.get('seatPick') and c.get('seatQueue'):
          q_ = list(c['seatQueue']); c['seatPick'] = q_.pop(0)
          if q_: c['seatQueue'] = q_
          else: c.pop('seatQueue', None)
      seated_pick = False; seated_any = False
      if want_n and len(c['legs']) < want_n and not c.get('flooredAt') and not c.get('holdAll') and not c.get('rebuy'):   # 🔄 a rebuy's seat is spoken for
          _val = lambda x: (_f(x['units']) or (_f(x.get('wantUnits')) if x.get('buying') else 0.0)) * (_f(prices.get(x['pairAddress'])) or _f(x.get('entry')))
          share = (sum(_val(x) for x in c['legs']) + free_cash) / want_n
          role_s, nxt = next(((r, x) for r in ('runner', 'pool') for x in [best(r)] if x), (None, None))
          c.setdefault('seatEmptyAt', now)
          fb_seat = False
          if not nxt and now - _f(c.get('seatEmptyAt')) >= SEAT_FALLBACK_SEC:
              nxt = fallback_coin(); role_s, fb_seat = ('runner', True) if nxt else (None, False)
          sp_ = c.get('seatPick')   # 🪑 the owner's own pick for this seat comes first
          if sp_ and sp_.get('mint') not in {x['mint'] for x in c['legs']} and (_f(prices.get(sp_['pairAddress'])) or _f(sp_.get('price'))) > 0:
              role_s, nxt = 'runner', {**sp_, 'price': _f(prices.get(sp_['pairAddress'])) or _f(sp_.get('price')), 'liq': sp_.get('liquidityUsd')}
          elif sp_:
              c.pop('seatPick', None); sp_ = None
          # no cash for the seat (a rugged coin leaves nothing behind) → the coins sitting ABOVE the new equal share give up their
          # extra (never a locked / riding coin, never one still being bought): 3 coins × $1.03 become 4 × $0.77
          if nxt and free_cash < min(share, max(seat_min, share * 0.6)):
              need = share - free_cash
              for d_ in sorted((x for x in c['legs'] if not x.get('ride') and not x.get('frozen') and not x.get('buying') and not x.get('placeholder')
                                and _f(x.get('units')) > 0 and _val(x) > share * 1.05), key=_val, reverse=True):
                  if need < 0.05:
                      break
                  px_d = _f(prices.get(d_['pairAddress'])) or _f(d_.get('entry'))
                  cut = min(_val(d_) - share, need)
                  if cut < mo:
                      continue   # too small for the keeper to sell: the cut would never land and the seat would wait on it for good
                  part = cut / _val(d_)
                  got_d = sell_usd(_f(d_['units']) * part, px_d, liqs.get(d_['pairAddress']) or d_.get('liq'))
                  d_['units'] = _f(d_['units']) * (1 - part); d_['costUsd'] = round(_f(d_.get('costUsd')) * (1 - part), 6); d_['trimAt'] = now
                  c['cash'] = round(_f(c['cash']) + got_d, 6); free_cash += got_d; need -= cut; c['feesUsd'] += fee
          if nxt and free_cash < seat_min and mo > 0 and now - _f(c.get('seatWaitAt')) >= 1800:
              c['seatWaitAt'] = now
              ev(kind='seat-wait', usd=round(free_cash, 4), why=f"🪑 seat {len(c['legs']) + 1} of {want_n} is waiting: the card has ${free_cash:.2f} free and the smallest order it can send is "
                                                                f"${seat_min:.2f} — it fills by itself when there is enough (add money, or pick fewer coins in Shape)")
          if nxt and free_cash >= seat_min:
              c.pop('seatWaitAt', None)
              usd_s = min(free_cash, share)
              mine_ = bool(sp_ and sp_.get('mint') == nxt.get('mint'))
              tick_s = False
              if mine_:
                  usd_s, tick_s = (usd_s, False) if c.get('ticketOff') else young_ticket(sp_, share * want_n, usd_s)   # 🎟 a young hand pick is a small ticket (owner can switch it off)
              c['legs'].append(_leg(nxt, usd_s, now, role_s))
              seated_any = True
              if tick_s:
                  c['legs'][-1].update(ticket=True, sl=YOUNG_PICK_SL)
              if mine_:
                  c['legs'][-1]['picked'] = True; c.pop('seatPick', None); seated_pick = True
                  if sp_.get('trenchOnly'):
                      c['legs'][-1]['trench'] = True
              c['cash'] = round(_f(c['cash']) - usd_s, 6); free_cash -= usd_s
              ev(kind='seat', symbol=nxt.get('symbol'), usd=round(usd_s, 4), why=(f"🎯 your pick ${nxt.get('symbol')} fills seat {len(c['legs'])} of {want_n} with an equal share" if mine_ else
                                                                                 f"🪑 empty seat filled — ${nxt.get('symbol')} takes seat {len(c['legs'])} of {want_n} with an equal share" + (' · ⏱ next-best coin after 30s (none cleared the full line)' if fb_seat else '')), to=[nxt.get('symbol')])
      # 🪑 every empty seat is filled on this SAME tick (owner: "auto fills seats in 30 secs"; the engine used to seat one a tick)
      if not want_n or len(c['legs']) >= want_n:
          c.pop('seatEmptyAt', None)
      if not ((seated_pick and c.get('seatQueue')) or (seated_any and want_n and len(c['legs']) < want_n)):
          break
    if cfg['compound'] and free_cash > 0.01 and c['legs']:
        waiting = [l for l in c['legs'] if l.get('buying') and not l.get('placeholder')]   # 👛 a pending real buy owns its slice first
        # 🔔 AT A ROUND every idle dollar goes back to work: a coin skipped only because it was cut minutes ago counts again
        # (never one cut on this very tick), so card cash can't sit idle past the next bell
        round_now = _f(c.get('lastRotateAt')) == now
        # a locked (riding / frozen) coin is never topped up: what was just banked off it must not be bought straight back
        # … and neither is a coin whose profit was just skimmed (10 min): that money is for the OTHER coins
        # NO FALLBACK INTO LOCKED COINS: with every coin locked the cash stays card cash for the empty seats. The old fallback ("else
        # every coin") poured a real card's cash into its one FROZEN coin on paper — the keeper never buys a frozen coin, so the
        # engine then read AUTON as $6.26 (real: $0.49), the full-stack skim "took" $5.76 that was never in it and parked it
        # (2026-10-07). Unlocked coins skipped only for a 10-min cut / ticket / scout are still the fallback.
        targets = [l for l in c['legs'] if not l.get('placeholder') and not l.get('scout') and not l.get('ticket') and not l.get('house') and not l.get('ride') and not l.get('frozen') and not (l.get('trimAt') and now - _f(l.get('trimAt')) <= 600 and not (round_now and _f(l.get('trimAt')) < now))] \
            or [l for l in c['legs'] if not l.get('placeholder') and not l.get('ride') and not l.get('frozen') and not l.get('ticket') and not l.get('house') and not l.get('scout')]
        if targets:
            # ⚖ NO COIN GETS THE WHOLE POT. Idle cash fills the seats that are furthest under an equal share and never lifts a coin
            # above it. It used to go entirely to whichever coin was waiting on a buy: $1.15 of freed cash went into ONE coin, which
            # became half the card — and one coin then decided the card.
            # the equal share is counted over every coin that is NOT locked: a coin skipped only for 10 minutes (just cut) still counts,
            # so the one coin left can't take its share too; a locked rider's banked money does go to the others in full
            open_ = [l for l in c['legs'] if not l.get('placeholder') and not l.get('ride') and not l.get('frozen')]
            all_ = [l for l in c['legs'] if not l.get('placeholder')]
            card_share = (sum((_f(l.get('units')) or (_f(l.get('wantUnits')) if l.get('buying') else 0.0)) * (_f(prices.get(l['pairAddress'])) or _f(l.get('entry'))) for l in all_) + max(0.0, _f(c.get('cash')))) / max(1, len(all_))
            fills = spread_cash(targets, free_cash, prices, open_ if all(t in open_ for t in targets) else None, cap=card_share,
                                fresh={l['mint'] for l in targets if _f(l.get('at')) > 0 and 0 <= now - _f(l['at']) < FRESH_SEC})
            free_cash = sum(fills)   # what is really spent: cash that would push a coin over its equal share stays cash
            for l, each in zip(targets, fills):
                if each <= 0:
                    continue
                px = buy_px(_f(prices.get(l['pairAddress'])) or l['entry'], each, liqs.get(l['pairAddress']) or l.get('liq'))
                l['units'] += each / px; l['costUsd'] += each
            targets = [l for l, each in zip(targets, fills) if each > 0]
            c['compoundedUsd'] += free_cash
            last = c['events'][-1] if c['events'] else {}
            if free_cash < 0.01:
                pass
            elif last.get('kind') == 'compound' and now - _f(last.get('firstAt') or last.get('at')) < 1800:   # one line per half hour, not one a tick
                c['events'][-1] = {**last, 'at': now, 'firstAt': last.get('firstAt') or last.get('at'), 'usd': round(_f(last.get('usd')) + free_cash, 4), 'lastUsd': round(free_cash, 4),
                                   'n': int(last.get('n') or 1) + 1, 'to': [l['symbol'] for l in targets]}
            else:
                ev(kind='compound', usd=round(free_cash, 4), why='idle cash back into the card', to=[l['symbol'] for l in targets])
            c['cash'] = round(_f(c['cash']) - free_cash, 6)
    v = V(); start = _f(c['startUsd']) or 1
    day_pct = (v / (_f(c.get('dayStartUsd')) or start) - 1) * 100
    # 🔧 worst day hit −40% → fix the config — ONLY while rescue is on. Rescue OFF = the owner's config and coin floor are the only protection.
    if not blind and _f(cfg.get('rescuePct', RESCUE_PCT)) != 0 and day_pct <= FIX_DAY_PCT and not c.get('flooredAt') and not c.get('cycleFix') and (c.get('fixedAt') is None or now - _f(c['fixedAt']) >= 86400):
        # The safety state itself must never depend on candidate availability. Arm the safe cycle immediately; a complete safe
        # reshape may happen now, or on a later tick when all required eligible slots exist.
        c['cycleFix'] = 'safe'
        c['fixUntil'] = int(c.get('rounds') or 0) + SAFE_FIX_ROUNDS
        c['fixedAt'] = now
        ev(kind='fix', why=f"day {day_pct:.0f}% ≤ {FIX_DAY_PCT:.0f}% — safe cycle armed")
        keep = {k: c[k] for k in c if k not in ('legs', 'cash', 'lastRotateAt')}
        keep['runs'] = (list(c.get('runs') or []) + [{'at': now, 'startUsd': c['startUsd'], 'endUsd': round(v, 4), 'pct': round((v / start - 1) * 100, 2), 'fixed': True}])[-10:]
        keep.update(cycleFix='safe', fixUntil=c['fixUntil'], fixedAt=now, dayStartUsd=round(v, 4), dayAt=now, startUsd=round(v, 4), roundStartUsd=round(v, 4), lowPct=0.0)
        nc = deal(c['tpl'], pools, runners, cfg, now, anchors, usd=in_play(c, prices, liqs), keep=keep, shape='anchor')
        if nc:
            nc['events'].append({'at': now, 'kind': 'fix', 'why': f"day {day_pct:.0f}% ≤ {FIX_DAY_PCT:.0f}% — re-dealt into complete safe shape"})
            c = nc
        v = V()
    # 5) 🛡 FLOOR: the card is never allowed to sit below −floorPct (default −20%, so −25% is never reached short of a gap):
    #    every pool / runner is sold into the anchor (or cash) at once; the card re-deals fresh the next day.
    v = V(); start = _f(c['startUsd']) or 1
    pct = (v / start - 1) * 100
    if _f(cfg['floorPct']) > 0 and pct <= -cfg['floorPct'] and not c.get('flooredAt') and not blind:   # 0 = the owner switched the card floor OFF
        # 🧱 Floor money goes ONLY into an established major — never into a new major or the owner's pick that happens to sit in the
        # anchor seat (the card's whole $1.65 was moved into $KURA at 4–5% impact, then out again 37s later: −$0.14 for nothing).
        # 💵 A real card with rest OFF re-deals on the next tick, so it goes straight to cash: selling into an anchor only to sell
        # the anchor a minute later is two extra swaps of the whole card.
        to_cash = bool(_f(cfg.get('dealLeadSec'))) and not _f(cfg.get('floorRestMins'))
        anc = [] if to_cash else [l for l in c['legs'] if l.get('role') == 'anchor' and safe_anchor(l) and _f(prices.get(l['pairAddress'])) > 0]
        out = [l for l in c['legs'] if l not in anc]
        usd = sum(sell_usd(l['units'], _f(prices.get(l['pairAddress'])) or l['entry'], liqs.get(l['pairAddress']) or l.get('liq')) for l in out)
        c['feesUsd'] += fee * len(out)
        if anc:
            for a in anc:
                apx = _f(prices.get(a['pairAddress'])); a['units'] += usd / len(anc) / apx; a['costUsd'] += usd / len(anc)
        else:
            c['cash'] += usd
        c['legs'] = anc or []
        c['flooredAt'] = now
        ev(kind='floor', usd=round(usd, 4), why=f"card {pct:.0f}% ≤ −{cfg['floorPct']:g}% floor — everything into {'the anchor' if anc else 'cash'}", to=[a['symbol'] for a in anc] or ['cash'])
    c['lowPct'] = round(min(_f(c.get('lowPct')), pct), 2)
    # 6) the day record: every 24h the card's day move is logged — a good day is ≥ +10%
    if now - c['dayAt'] >= 86400:
        c['days'] = (c['days'] + [{'at': now, 'pct': round((v / (_f(c['dayStartUsd']) or 1) - 1) * 100, 2)}])[-30:]
        c['dayAt'], c['dayStartUsd'] = now, round(v, 4)
    if not c.get('flooredAt') and not c.get('holdAll'):
        balance_small(c, prices, liqs, now, fee, ev)
    for l in c['legs']:
        if _f(liqs.get(l['pairAddress'])) > 0:
            l['liqNow'] = _f(liqs[l['pairAddress']])
    c['feesUsd'] = round(c['feesUsd'], 4)
    c['events'] = c['events'][-60:]
    return c


SMALL_SHARE = 0.5   # a coin PUT IN with < half its equal share is topped up …
OVER_SHARE = 1.25   # … from card cash first, then from coins holding > 125% of their share


def spread_cash(legs, cash, prices, seats=None, cap=None, fresh=()):
    """How idle cash is split over a card's coins → [$ per leg]. Each coin is filled toward an EQUAL share of (coins + cash) in
    proportion to how far under it sits; a coin already at or over its share gets nothing. A coin still waiting on its buy counts as
    worth what it was given so far (often $0), so it is filled first — but only up to its share.
    `seats` = every coin that is not locked, when `legs` is only the coins that may be topped up right now: the equal share is then the
    whole card's, and cash that would lift a coin above it is NOT spent (it waits for the other coins). Without it, one eligible
    coin took all the cash: $0.92 into a $0.74 pick made it 60% of a four-coin card."""
    def val(l):
        px = _f((prices or {}).get(l['pairAddress'])) or _f(l.get('entry'))
        return (_f(l.get('units')) or (_f(l.get('wantUnits')) if l.get('buying') else 0.0)) * px
    vals = [val(l) for l in legs]
    every = seats if seats else legs
    share = (sum(val(l) for l in every) + _f(cash)) / len(every) if every else 0.0
    # 🆕 a coin bought minutes ago (`fresh`) is never lifted above the WHOLE card's equal share (`cap`): with two coins riding
    # (locked), the share of the two unlocked ones is half the card each — a replacement bought a minute earlier took the freed
    # cash and became the card's biggest seat before it had proved anything ($AGENCY: $0.48 seat → $2.03, then −9%).
    fr = set(fresh or ())
    room = [max(0.0, (min(share, _f(cap)) if cap is not None and seats and l.get('mint') in fr else share) - v) for l, v in zip(legs, vals)]
    total = sum(room)
    if total <= 0:
        return [0.0] * len(legs) if seats else ([_f(cash) / len(legs)] * len(legs) if legs else [])
    spend = min(_f(cash), total) if seats else _f(cash)
    return [spend * r / total for r in room]


def stack(card, prices, cfg=None):
    """🔒 The card in one line: how many coins are LOCKED (a winner the engine froze and is riding — it is only sold off its peak),
    how many are WINNING (up enough that a re-shape won't sell them) and how many are still PROVING themselves.
    → {seats, locked, winning, proving, full}. A full stack = every coin locked: the engine stops rotating and just guards them."""
    keep = _f((cfg or {}).get('keepWinPct', 5.0))
    seats = [l for l in (card or {}).get('legs') or [] if not l.get('placeholder') and (_f(l.get('units')) > 0 or l.get('buying'))]
    def gain(l):
        px = _f((prices or {}).get(l['pairAddress'])) or _f(l.get('entry'))
        return (px / _f(l['entry']) - 1) * 100 if _f(l.get('entry')) > 0 else 0.0
    locked = [l for l in seats if l.get('ride') or l.get('frozen')]
    winning = [l for l in seats if l not in locked and keep > 0 and gain(l) >= keep]
    return {'seats': len(seats), 'locked': len(locked), 'winning': len(winning), 'proving': len(seats) - len(locked) - len(winning),
            'full': bool(seats) and len(locked) == len(seats)}


def balance_small(c, prices, liqs, now, fee, ev):
    """⚖ Equal weight: a coin that went in tiny (it inherited a small slot — "$0.05 in a coin") is topped up to its equal share from card
    cash, then from the most overweight coins. A coin that is small because it LOST value is left alone (never averaging down) — only
    coins whose COST is under half a share qualify. Mutates c; logs one `balance` event per coin."""
    px = lambda l: _f(prices.get(l['pairAddress']))
    legs = [l for l in c['legs'] if _f(l.get('units')) > 0 and px(l) > 0 and not l.get('placeholder')]
    if len(legs) < 2:
        return
    val = lambda l: _f(l['units']) * px(l)
    share = (sum(val(l) for l in legs) + max(0.0, _f(c.get('cash')))) / len(legs)
    # a coin is "small" only when it WENT IN small. A coin whose profit was taken (💰 skim, 🏦 bank, ✂ cut → `skimPx` / `bankedAt` /
    # fresh `trimAt`) or that is locked / riding is small ON PURPOSE: topping it up would buy back what was just sold
    # ($1.93 was skimmed off $SpaceXSI and this rule put $1.13 of it straight back in four seconds later).
    taken = lambda l: l.get('scout') or l.get('ticket') or l.get('house') or l.get('skimPx') or l.get('bankedAt') or l.get('ride') or l.get('frozen') or (l.get('trimAt') and now - _f(l.get('trimAt')) < 600)
    small = [l for l in legs if not taken(l) and _f(l.get('costUsd')) < SMALL_SHARE * share and val(l) < SMALL_SHARE * share]
    for l in small:
        need = share - val(l)
        take = min(max(0.0, _f(c.get('cash'))), need)
        c['cash'] = _f(c.get('cash')) - take
        rest = need - take
        for d in sorted((x for x in legs if x not in small and not x.get('frozen') and not x.get('ride') and val(x) > OVER_SHARE * share), key=val, reverse=True):
            if rest < 0.01:
                break
            cut = min(val(d) - share, rest)
            old = _f(d['units'])
            d['units'] = max(0.0, old - cut / px(d))
            d['costUsd'] = round(_f(d.get('costUsd')) * (d['units'] / old), 6) if old else 0.0
            take += sell_usd(cut / px(d), px(d), liqs.get(d['pairAddress']) or d.get('liq'))
            c['feesUsd'] = _f(c.get('feesUsd')) + fee
            rest -= cut
        if take < 0.01:
            continue
        bpx = buy_px(px(l), take, liqs.get(l['pairAddress']) or l.get('liq'))
        l['units'] = _f(l['units']) + take / bpx
        l['costUsd'] = round(_f(l.get('costUsd')) + take, 6)
        c['feesUsd'] = _f(c.get('feesUsd')) + fee
        ev(kind='balance', symbol=l.get('symbol'), usd=round(take, 4), why=f"⚖ equal weight — ${l.get('symbol')} went in with ${val(l) - take:.2f}, topped up toward its ${share:.2f} share")


def reshape_every(card, cfg):
    """Rounds between re-shapes. A card whose owner PICKED a cycle always cycles: 're-shape every: off' (0) with a cycle picked used to
    freeze it on one shape forever ("next: steady") — it now re-shapes every REAL_MAX_RESHAPE rounds. A running fix uses `fixEvery`."""
    if card.get('cycleFix'):
        return max(1, int(_f(cfg.get('fixEvery'))))
    ce = cfg.get('cycleEvery')
    every = 6 if ce is None else int(_f(ce))
    mode = (cfg.get('cycles') or DEFAULT_CYCLES).get(card.get('tpl'), 'off')
    return every or (REAL_MAX_RESHAPE if mode and mode != 'off' else 0)


def cycle_peek(card, cfg):
    """🔄 What the card holds now and what it re-shapes into next (same rules as `tick`): {now, next, inRounds, mode, fix}.
    adaptive / auto pick by the last round's move, so `next` is the shape IF the next round moves like the last one."""
    cfg = cfg or {}
    mode = card.get('cycleFix') or (cfg.get('cycles') or DEFAULT_CYCLES).get(card.get('tpl'), 'off')
    every = reshape_every(card, cfg)
    if not every or card.get('holdAll'):
        return {'now': card.get('phase'), 'next': None, 'inRounds': None, 'mode': 'hold' if card.get('holdAll') else mode, 'fix': card.get('cycleFix')}
    r = int(card.get('rounds') or 0)
    n = every - (r % every)
    nxt = next_phase(mode, (r + n) // every, card.get('lastRoundPct'))
    return {'now': card.get('phase'), 'next': nxt, 'inRounds': n if nxt else None, 'mode': mode, 'fix': card.get('cycleFix')}


def put_in(card):
    """What was PUT IN a paper card, across every restart: set at its first deal (`putInUsd`, + any top-up) and never lowered by a
    floor re-deal. Legacy cards: the first recorded run's start."""
    if _f(card.get('putInUsd')) > 0:
        return _f(card['putInUsd'])
    runs = card.get('runs') or []
    return _f(runs[0].get('startUsd')) if runs and _f(runs[0].get('startUsd')) > 0 else _f(card.get('startUsd'))


def payout_line(card):
    """The money a card must keep IN before anything is paid out: real = funded principal (`fundedUsd`); paper = what was put in."""
    return _f(card.get('fundedUsd')) or max(_f(card.get('startUsd')), put_in(card))


def summary(card, prices, cfg=None):
    v = value(card, prices)
    start = _f(card.get('startUsd')) or 1
    rot = _f((cfg or {}).get('rotateHours')) or DEFAULT_CFG['rotateHours']
    paid = round(_f(card.get('walletUsd')), 4)
    legs = [{**{k: l[k] for k in ('mint', 'pairAddress', 'symbol', 'role', 'entry', 'units', 'costUsd')}, 'stars': l.get('stars') or 3,
             'house': bool(l.get('house')), 'ticket': bool(l.get('ticket')), 'frozen': bool(l.get('frozen')), 'slMode': l.get('slMode'), 'tp': l.get('tp'), 'sl': l.get('sl'), 'division': l.get('division'), 'swapTo': (l.get('swapTo') or {}).get('symbol'), 'ride': bool(l.get('ride')), 'high': l.get('high'), 'rideFrom': l.get('rideFrom'), 'bought': l.get('bought'), 'picked': bool(l.get('picked')), 'buying': bool(l.get('buying')),
             'loseRounds': int(l.get('loseRounds') or 0),
             'firstEntry': l.get('firstEntry') or l['entry'], 'at': l.get('at'), 'now': _f(prices.get(l['pairAddress'])) or l['entry'],
             'pnlPct': round(((_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] - 1) * 100, 2) if l['entry'] else 0.0,
             'liq': _f(l.get('liqNow')) or _f(l.get('liq')),
             'usd': round(value({'legs': [l], 'cash': 0.0}, prices), 4)} for l in card['legs']]
    return {**{k: card[k] for k in ('id', 'tpl', 'label', 'at', 'lastRotateAt', 'compoundedUsd', 'takenUsd', 'feesUsd', 'startUsd')}, 'cash': round(card['cash'], 4), 'walletUsd': round(_f(card.get('walletUsd')), 4),
            'flooredAt': card.get('flooredAt'), 'phase': card.get('phase'), 'cycleFix': card.get('cycleFix'), 'cycle': list(CYCLE) if card['tpl'] in CYCLE_TIERS else None, 'rounds': int(card.get('rounds') or 0), 'lastRoundPct': card.get('lastRoundPct'),
            'roundPct': round((v / (_f(card.get('roundStartUsd')) or start) - 1) * 100, 2), 'roundWins': int(card.get('roundWins') or 0),
            'stack': stack(card, prices, cfg),
            'swapCap': {**swap_cap(cfg or {}, v, len(card['legs'])), 'used': swaps_last_hour(card, _f((cfg or {}).get('_now')) or __import__('time').time())},
            'valueUsd': v, 'pnlPct': round((v / start - 1) * 100, 2), 'legs': legs, 'events': card['events'][-12:][::-1],
            'tp': card_template(card['tpl'], cfg)['tp'], 'sl': card_template(card['tpl'], cfg)['sl'], 'tier': TEMPLATES[card['tpl']]['tier'], 'why': TEMPLATES[card['tpl']].get('why'),
            'parked': list((card.get('parked') or {}).values()),
            # 🧮 the money in plain words: PUT IN → NOW = STILL IN THE CARD + PAID OUT; P&L = NOW − PUT IN (fees apart)
            'math': {'putIn': round(start if card.get('real') else put_in(card), 4), 'runStart': round(start, 4), 'heldUsd': round(v - paid, 4), 'paidOutUsd': paid, 'nowUsd': v,
                     'pnlUsd': round(v - (start if card.get('real') else put_in(card)), 4),
                     'compoundedUsd': round(_f(card.get('compoundedUsd')), 4), 'feesUsd': round(_f(card.get('feesUsd')), 4)},
            # a floored card is RESTING in its anchors until the re-deal — never a countdown stuck on "dealing…"
            'nextRoundAt': round((_f(card['flooredAt']) + max(60.0, _f((cfg or {}).get('floorRestMins')) * 60)) if card.get('flooredAt') else (_f(card.get('lastRotateAt')) + rot * 3600 + BELL_SEC), 1),
            'resting': bool(card.get('flooredAt')) and _f((cfg or {}).get('floorRestMins')) > 0, 'bellSec': BELL_SEC, 'real': bool(card.get('real')), 'realSince': card.get('realSince'),
            **record(card)}


def record(card):
    """Honest scoreboard: of the last 10 logged days, how many were up ≥ +10%; the worst the card has ever been."""
    days = (card.get('days') or [])[-10:]
    return {'days': days, 'goodDays': sum(1 for d in days if _f(d.get('pct')) >= HIT_PCT), 'loggedDays': len(days),
            'lowPct': _f(card.get('lowPct')), 'floored': bool(card.get('flooredAt')), 'runs': (card.get('runs') or [])[-5:]}


def clock_rank(rows, rotate_hours, mom=None):
    """⏱ Every round length wants different coins. FAST clocks (≤ 15 min) need coins that are moving NOW: last-hour volume and
    momentum come first, so a 5-min card gets the coins that can pay inside a few rounds. SLOW clocks (≥ 1 h) keep the caller's
    order (depth / score: coins that hold up). Stable: equal coins keep their incoming order. Never adds or removes a coin."""
    rows = list(rows or [])
    if _f(rotate_hours) * 60 > 15 or len(rows) < 2:
        return rows
    def heat(x):
        m = (mom or {}).get(x.get('pairAddress')) or {}
        vol = _f(x.get('vol1h')) or _f(m.get('vol1h')) or _f(x.get('volume24h')) / 24
        chg = _f(m.get('chg1h')) if m.get('chg1h') is not None else _f(x.get('change24h')) / 24
        return math.log10(max(1.0, vol)) * 10 + max(-20.0, min(40.0, chg))
    return [r for _, _, r in sorted(((-heat(r), i, r) for i, r in enumerate(rows)), key=lambda t: (t[0], t[1]))]


LEG_TPS = (25, 50, 100, 200, 300)   # a coin's OWN take-profit / stop (0 = follow the tier's)
LEG_SLS = (10, 15, 20, 30)


def card_template(tpl, cfg):
    """The tier template with the card's own TP / SL (cfg `tp` / `sl`, 0 = the template's)."""
    t = TEMPLATES[tpl]
    return {**t, **{k: _f((cfg or {}).get(k)) for k in ('tp', 'sl') if _f((cfg or {}).get(k)) > 0}}


def leg_tp(l, t):
    return _f(l.get('tp')) or t['tp']


GUARD_SEC = 6    # ⚡ the real card's coins are price-checked this often BETWEEN ticks
FAST_GAP_SEC, FAST_GAP_PCT = 90, 50.0   # a > 50% "loss" in a leg's first 90s is a price-feed gap: left to the full tick


def fast_stop(card, px_by_mint, cfg, now):
    """⚡ FAST STOP: a real card's coin AT ITS STOP is taken off the card NOW, by the 6-second guard itself — its seat becomes a
    reserved placeholder (the next tick refills it) and the keeper sells on its very next pass. → the new card, or the SAME object
    when no coin is at its stop. Only the plain stop: a rider's trail, the instant swap, park / hold modes, frozen coins and
    safe majors stay with the full tick. Why (2026-10-06, $AGENCY): −22% inside ONE minute at 17:33; the guard only WOKE the full
    engine pass (candidates, every card, charts), so the stop was logged at 17:35:02 and sold at 17:35:33 — −31% on a −15% stop."""
    t = card_template(card.get('tpl'), cfg)
    mode = cfg.get('slMode', 'replace')
    c = None
    for i, l in enumerate(card.get('legs') or []):
        px, entry, sl = _f((px_by_mint or {}).get(l.get('mint'))), _f(l.get('entry')), leg_sl(l, t)
        lmode = l.get('slMode') if l.get('slMode') in SL_MODES else mode
        if (px <= 0 or entry <= 0 or sl <= 0 or _f(l.get('units')) <= 0 or lmode != 'replace' or not l.get('real') or l.get('buying') or l.get('placeholder') or l.get('frozen')   # `real` = the wallet HOLDS it (set by sync_card): a coin just dealt and not bought yet has nothing to stop ($BTT was "stopped" before its buy)
                or l.get('ride') or int(l.get('freezeRounds') or 0) > 0 or safe_anchor(l)):
            continue
        dd = (px / entry - 1) * 100
        if dd > -sl or (dd <= -FAST_GAP_PCT and now - _f(l.get('at')) < FAST_GAP_SEC):
            continue
        if c is None:
            c = {**card, 'legs': [dict(x) for x in card['legs']], 'events': list(card.get('events') or [])}
        out_usd = sell_usd(_f(l['units']), px, l.get('liq'))
        c['legs'][i] = {**{k: v for k, v in l.items() if k not in ('wantUnits', 'buyingSince')}, 'units': 0.0, 'costUsd': 0.0, 'reserveUsd': round(out_usd, 6),
                        'buying': False, 'entry': px, 'at': now, 'placeholder': True}
        c['cash'] = round(_f(c.get('cash')) + out_usd, 6)
        c['events'].append({'at': now, 'kind': 'sl', 'symbol': l.get('symbol'), 'usd': round(out_usd, 4), 'to': ['cash'], 'fast': True,
                            'why': f"⚡ {dd:.0f}% ≤ −{sl:g}% — stopped at once, seat reserved for the next coin"})
    return c if c is not None else card


def guard_hits(card, px_by_mint, cfg):
    """⚡ FAST GUARD: which coins of a real card need the engine NOW (not at the next ~1-minute tick)? A coin at / under its stop
    or the instant-swap line, or a riding coin that fell its trail off the peak. → [symbol]. It only WAKES the tick — the tick
    still decides and still applies every rule (feed-gap check, patience, picks). Why: a stop set at −15% sold at −48% because
    the coin fell from +20% between two checks a minute apart. Majors, frozen coins and coins still being bought are not watched."""
    t, out = card_template(card.get('tpl'), cfg), []
    lines = [x for x in (_f(cfg.get('instantSwapPct')),) if x > 0]
    for l in card.get('legs') or []:
        px, entry = _f((px_by_mint or {}).get(l.get('mint'))), _f(l.get('entry'))
        if px <= 0 or entry <= 0 or _f(l.get('units')) <= 0 or l.get('buying') or l.get('placeholder') or l.get('frozen') or safe_anchor(l):
            continue
        if l.get('ride'):
            if _f(l.get('high')) > 0 and px <= _f(l['high']) * (1 - (_f(cfg.get('rideTrail')) or RIDE_TRAIL) / 100):
                out.append(l.get('symbol'))
            continue
        stops = lines + [x for x in (leg_sl(l, t),) if x > 0]
        if stops and (px / entry - 1) * 100 <= -min(stops):
            out.append(l.get('symbol'))
    return out


def leg_sl(l, t):
    return _f(l.get('sl')) or t['sl']


def set_leg(card, pair, frozen=None, sl_mode=None, tp=None, sl=None):
    """HQ per-coin config on a tier card: ❄ frozen (engine never rotates or stops it — the floor still protects the card)
    and its own stop mode (replace / park / hold, or '' = follow the card). Pure; ValueError if the coin isn't on the card."""
    c = {**card, 'legs': [dict(l) for l in card.get('legs') or []]}
    leg = next((l for l in c['legs'] if l['pairAddress'] == pair), None)
    if not leg:
        raise ValueError('That coin is not on this card.')
    if frozen is not None:
        leg['frozen'] = bool(frozen)
    if sl_mode is not None:
        if sl_mode and sl_mode not in SL_MODES:
            raise ValueError('stop mode must be replace, park or hold')
        leg['slMode'] = sl_mode or None
    for key, val, allowed in (('tp', tp, LEG_TPS), ('sl', sl, LEG_SLS)):   # 🎯 this coin's own TP / SL; 0 clears it back to the tier's
        if val is not None:
            if _f(val) and _f(val) not in allowed and not step_ok(key, val):
                lo, hi = STEP_RANGE[key]
                raise ValueError(f"{key.upper()} must be a whole % from {lo} to {hi} (or 0 to follow the tier)")
            if _f(val):
                leg[key] = _f(val)
            else:
                leg.pop(key, None)
    return c


def sell_leg_to_cash(card, pair, prices, now, pct=100.0):
    """Owner manual sell: remove one coin from the target and keep its proceeds as card cash.

    The zero-unit manualCash placeholder preserves the slot/role without asking the
    keeper to buy it again. On a real card, sync_card replaces this estimate with the
    confirmed SOL actually returned by the sell.
    """
    c = {**card, 'legs': [dict(l) for l in card['legs']], 'events': list(card.get('events') or [])}
    l = next((x for x in c['legs'] if x['pairAddress'] == pair), None)
    if not l:
        raise ValueError('That coin is not on this card.')
    if l.get('mint') == SOL_MINT:
        raise ValueError('SOL is already card cash.')
    px = _f(prices.get(pair)) or _f(l.get('entry'))
    pct = max(1.0, min(100.0, _f(pct) or 100.0))
    if pct < 100:   # ✂ sell PART of a coin: the slot keeps the rest; the cash is held for the owner (never auto-compounded back in)
        part = pct / 100.0
        usd = max(0.0, _f(l.get('units')) * px * part)
        l['units'] = _f(l.get('units')) * (1 - part); l['costUsd'] = _f(l.get('costUsd')) * (1 - part)
        l['trimAt'] = now   # the keeper sells a deliberate cut even inside its rebalance band (a 25% ✂ sat unsold: 33% over < the 50% band)
        c['cash'] = round(_f(c.get('cash')) + usd, 6)
        c['holdCashUsd'] = round(_f(c.get('holdCashUsd')) + usd, 6)
        c['events'].append({'at': now, 'kind': 'manual-sell', 'symbol': l.get('symbol'), 'usd': round(usd, 4),
                            'why': f'{pct:g}% sold by owner — proceeds held as card cash', 'to': ['cash']})
        return c
    usd = max(0.0, _f(l.get('units')) * px)
    sold = {**l, 'units': 0.0, 'costUsd': 0.0, 'wantUnits': 0.0, 'buying': False,
            'placeholder': True, 'manualCash': True, 'reserveUsd': 0.0, 'at': now}
    sold.pop('ride', None); sold.pop('frozen', None)
    c['legs'][c['legs'].index(l)] = sold
    c['cash'] = round(_f(c.get('cash')) + usd, 6)
    c['events'].append({'at': now, 'kind': 'manual-sell', 'symbol': l.get('symbol'), 'usd': round(usd, 4),
                        'why': 'sold by owner — proceeds stay inside this card as cash', 'to': ['cash']})
    return c


def card_snap(cards):
    """{tier: the card as a stable string} — taken when a tick LOADS the cards, compared when it saves (`merge_tick`)."""
    import json
    return {t: json.dumps(c, sort_keys=True, default=str) for t, c in (cards or {}).items()}


def merge_tick(snap, ticked, fresh):
    """A tick works for seconds between loading the cards and saving them. Anything written in between (the owner's pick, a skim,
    a lock, a config) must WIN: a card that changed on disk since the tick loaded it is kept as it is on disk and this tick's
    result for it is dropped (the next tick, seconds later, runs on the new card). A card deleted meanwhile stays deleted; one
    added meanwhile is kept. → the cards to save."""
    now_ = card_snap(fresh)
    out = {}
    for t, c in (ticked or {}).items():
        if t in snap and t not in now_:
            continue                       # removed while the tick ran
        out[t] = fresh[t] if t in snap and now_.get(t) != snap[t] else c
    for t, c in (fresh or {}).items():
        if t not in out and t not in snap:
            out[t] = c                     # added while the tick ran
    return out


def queue_swap(card, pair, cand):
    """🎯 The owner's PICK: at the next round, this coin leaves and `cand` (a coin they chose from the live lists) takes its seat and
    its money. cand=None cancels. Pure; ValueError if the coin isn't on the card or the pick already is."""
    c = {**card, 'legs': [dict(l) for l in card.get('legs') or []]}
    l = next((x for x in c['legs'] if x['pairAddress'] == pair), None)
    if not l:
        raise ValueError('That coin is not on this card.')
    if cand is None:
        l.pop('swapTo', None)
        return c
    if not cand.get('mint') or not cand.get('pairAddress') or _f(cand.get('price')) <= 0:
        raise ValueError('That pick has no live price right now.')
    if cand['mint'] in {x['mint'] for x in c['legs']}:
        raise ValueError('That coin is already on this card.')
    if any((x.get('swapTo') or {}).get('mint') == cand['mint'] for x in c['legs'] if x is not l):
        raise ValueError('That coin is already queued for another seat.')
    l['swapTo'] = {k: cand.get(k) for k in ('mint', 'pairAddress', 'symbol', 'price', 'liquidityUsd', 'division', 'trenchOnly', 'ack', 'ageH', 'now') if cand.get(k) is not None}
    return c


def now_picks(c):
    """⚡ Picks the owner asked to swap in NOW (not at the bell) → {pairAddress}. Same swap as the bell's, on the very next tick."""
    return {l['pairAddress'] for l in c.get('legs') or [] if (l.get('swapTo') or {}).get('now')}


REBUY_WAIT_SEC = 600.0   # a rebuy whose sell has not landed after 10 minutes is called off (its money is released)


def rebuy_out(card, pair, prices, liqs, now):
    """🔄 REBUY, step 1 (owner): sell this coin whole so it can be bought straight back at today's price — a NEW entry, so its stop,
    lock and trail count from here and the gain so far is realized. The coin leaves the card, its money is held aside (never spread
    into the other coins), and `rebuy` remembers it. Pure; ValueError when the coin is not on the card / not held / already queued."""
    c = {**card, 'legs': [dict(l) for l in card.get('legs') or []], 'events': list(card.get('events') or [])}
    l = next((x for x in c['legs'] if x.get('pairAddress') == pair), None)
    if not l:
        raise ValueError('That coin is not on this card.')
    if c.get('rebuy'):
        raise ValueError(f"${c['rebuy'].get('symbol')} is already being rebought — one at a time.")
    px = _f((prices or {}).get(pair))
    if _f(l.get('units')) <= 0 or l.get('buying') or px <= 0:
        raise ValueError('That coin is not held yet (or has no live price) — nothing to rebuy.')
    got = sell_usd(_f(l['units']), px, (liqs or {}).get(pair) or l.get('liq'))
    c['legs'] = [x for x in c['legs'] if x is not l]
    c['cash'] = round(_f(c.get('cash')) + got, 6); c['holdCashUsd'] = round(_f(c.get('holdCashUsd')) + got, 6)
    c['rebuy'] = {'mint': l['mint'], 'pairAddress': pair, 'symbol': l.get('symbol'), 'price': px, 'liquidityUsd': _f(l.get('liq')), 'usd': round(got, 6), 'at': now,
                  'gainPct': round((px / _f(l['entry']) - 1) * 100, 1) if _f(l.get('entry')) > 0 else 0.0, **({'trenchOnly': True} if l.get('trench') else {})}
    c['events'].append({'at': now, 'kind': 'rotate', 'symbol': l.get('symbol'), 'usd': round(got, 4), 'to': [l.get('symbol')],
                        'why': f"🔄 rebuy: ${l.get('symbol')} sold at {c['rebuy']['gainPct']:+.0f}% — it is bought back at today's price as soon as the sale lands (new entry)"})
    return c


def rebuy_in(card, still_held, now):
    """🔄 REBUY, step 2 (each tick): once the wallet no longer holds the coin, its money is released and the coin is queued for the
    empty seat as the owner's pick (`seatPick`, acknowledged) — the seat refill buys it on this tick. Still held after
    REBUY_WAIT_SEC → called off, money released. → card (unchanged while the sale is still in flight)."""
    rb = (card or {}).get('rebuy')
    if not rb:
        return card
    late = now - _f(rb.get('at')) > REBUY_WAIT_SEC
    if still_held and not late:
        return card
    c = {**card, 'events': list(card.get('events') or [])}
    c.pop('rebuy', None)
    c['holdCashUsd'] = round(max(0.0, _f(c.get('holdCashUsd')) - _f(rb.get('usd'))), 6)
    if still_held:
        c['events'].append({'at': now, 'kind': 'rotate', 'symbol': rb.get('symbol'), 'usd': 0.0, 'why': f"🔄 rebuy of ${rb.get('symbol')} called off — its sale had not landed after 10 minutes; the money is free again"})
        return c
    c['seatPick'] = {k: rb.get(k) for k in ('mint', 'pairAddress', 'symbol', 'price', 'liquidityUsd', 'trenchOnly') if rb.get(k) is not None} | {'ack': True}
    return c


SEAT_QUEUE_MAX = 5


def queue_seat(card, cand, more=False):
    """🪑 The owner's pick for the card's EMPTY seat: taken by the seat refill on the next tick (equal share; coins above it give
    up their extra when there is no cash). cand=None cancels. Pure; ValueError when the coin is on the card or has no live price."""
    c = {**card, 'legs': [dict(l) for l in card.get('legs') or []]}
    if cand is None:
        c.pop('seatPick', None); c.pop('seatQueue', None)
        return c
    if not cand.get('mint') or not cand.get('pairAddress') or _f(cand.get('price')) <= 0:
        raise ValueError('That pick has no live price right now.')
    if cand['mint'] in {x['mint'] for x in c['legs']} or any((x.get('swapTo') or {}).get('mint') == cand['mint'] for x in c['legs']):
        raise ValueError('That coin is already on this card.')
    pick = {k: cand.get(k) for k in ('mint', 'pairAddress', 'symbol', 'price', 'liquidityUsd', 'division', 'trenchOnly', 'ack', 'ageH') if cand.get(k) is not None}
    cur = c.get('seatPick')
    if not cur or cur.get('mint') == pick['mint'] or not more:
        c['seatPick'] = pick                      # the first pick (or a change of it)
    else:                                         # 🪑🪑 a pick for the NEXT empty seat: queued behind the first, one per coin
        c['seatQueue'] = ([x for x in c.get('seatQueue') or [] if x.get('mint') != pick['mint']] + [pick])[:SEAT_QUEUE_MAX]
    return c


def apply_queued(c, prices, liqs, now, fee=0.0, only=None, why='🎯 your pick — swapped in at the round'):
    """At the round: every queued pick is swapped in (the old coin is sold at what selling pays, the pick is bought with that money and
    carried as `picked` so a re-shape never drops it). Mutates the working card; returns how many swaps it made."""
    n = 0
    for i, l in enumerate(list(c['legs'])):
        to = l.get('swapTo')
        if not to or (only is not None and l['pairAddress'] not in only):
            continue
        px = _f(prices.get(l['pairAddress'])) or l['entry']
        units = _f(l['units']) or (_f(l.get('wantUnits')) if l.get('buying') else 0.0)
        usd = sell_usd(units, px, (liqs or {}).get(l['pairAddress']) or l.get('liq'))
        owner_out(c, l['mint'], now)   # 🙅 you picked it off the card → the ENGINE keeps it off for hours
        (c.get('ownerOut') or {}).pop(to.get('mint'), None)   # … and a coin you pick back in is yours again
        live = _f(prices.get(to['pairAddress'])) or _f(to.get('price'))
        # ⚖ a pick gets at most an EQUAL SHARE of the card: one that inherited an oversized seat ($1.04 of a $3 card) decided the
        # whole card when it fell. The rest goes to card cash and is spread over the other coins.
        total = sum((_f(x['units']) or (_f(x.get('wantUnits')) if x.get('buying') else 0.0)) * (_f(prices.get(x['pairAddress'])) or _f(x.get('entry'))) for x in c['legs']) + max(0.0, _f(c.get('cash')))
        share = total / len(c['legs']) if c['legs'] else usd
        spare = max(0.0, usd - share)
        if spare > 0.01:
            usd -= spare; c['cash'] = _f(c.get('cash')) + spare
        usd_t, tick_ = (usd, False) if c.get('ticketOff') else young_ticket(to, total, usd)
        if tick_:
            c['cash'] = _f(c.get('cash')) + (usd - usd_t); usd = usd_t
        c['legs'][i] = {**_leg({**to, 'price': live}, max(0.0, usd), now, 'anchor' if l.get('role') == 'anchor' and not tick_ else ('runner' if tick_ else l.get('role') or 'pool')), 'picked': True,
                        **({'ticket': True, 'sl': YOUNG_PICK_SL} if tick_ else {})}
        if tick_:
            why = f"{why} · 🎟 under 12h old: a ${usd:.2f} ticket ({YOUNG_PICK_PCT:g}% of the card), stop −{YOUNG_PICK_SL:g}%, never topped up"
        c['feesUsd'] = round(_f(c.get('feesUsd')) + 2 * fee, 4)
        c.setdefault('events', []).append({'at': now, 'kind': 'rotate', 'symbol': l.get('symbol'), 'usd': round(usd, 4), 'why': why, 'to': [to.get('symbol')]})
        n += 1
    return n


YOUNG_PICK_H, YOUNG_PICK_PCT, YOUNG_PICK_SL = 12.0, 15.0, 25.0


def young_ticket(pick, card_usd, usd):
    """🎟 A HAND PICK OF A YOUNG COIN IS A SMALL TICKET. A coin under 12 hours old (age known) goes in with at most 15% of the
    card and its own −25% stop; the rest of the seat's money returns to card cash for the other coins, and the ticket is never
    topped up. The owner may still pick anything — this only sizes it. Why: every big single loss on the real card was a hand
    pick minutes-to-hours old ($TRALA: $1.50 of a $4.60 card, pool pulled 90 seconds later; $SpaceX −98%). → (usd in, is ticket)"""
    age = (pick or {}).get('ageH')
    if age is None or _f(age) >= YOUNG_PICK_H or (pick or {}).get('trenchOnly'):
        return usd, False
    return min(usd, max(0.0, _f(card_usd)) * YOUNG_PICK_PCT / 100), True


PICK_NEAR_STOP = 5.0   # 🎯 a queued pick does not wait for the bell once the coin it replaces is this close (in % points) to its stop


def near_stop_picks(c, prices, t):
    """Coins with a queued pick (`swapTo`) that are within `PICK_NEAR_STOP` points of their own stop RIGHT NOW → {pairAddress}.
    The owner already chose what replaces them: swapping now saves the last points before the stop would sell it anyway.
    No live price, not bought yet, or no stop on the coin = not judged (the pick waits for the round as before)."""
    out = set()
    for l in c.get('legs') or []:
        px, e, sl = _f((prices or {}).get(l['pairAddress'])), _f(l.get('entry')), leg_sl(l, t)
        if l.get('swapTo') and px > 0 and e > 0 and sl > 0 and _f(l.get('units')) > 0 and not l.get('buying'):
            if (px / e - 1) * 100 <= -(sl - PICK_NEAR_STOP):
                out.add(l['pairAddress'])
    return out


def replace_leg(card, pair, prices, pools, runners, anchors, cfg, now):
    """HQ ⇄: swap ONE coin on a Prime card for the best 3★+ candidate of the same role not already on it (same $)."""
    c = {**card, 'legs': [dict(l) for l in card['legs']], 'events': list(card['events'])}
    l = next((x for x in c['legs'] if x['pairAddress'] == pair), None)
    if not l:
        raise ValueError('That coin is not on this card.')
    have = {x['mint'] for x in c['legs']}
    src = {'runner': runners, 'anchor': anchors}.get(l['role'], pools)
    nxt = next((x for x in rated(src, l['role']) if x['mint'] not in have and _f(x.get('price')) > 0), None)
    if not nxt:
        raise ValueError('No 3★+ replacement available right now.')
    # a coin whose real buy hasn't landed holds 0 units but is WAITING on its slice — that slice moves to the new coin (was a $0 coin)
    units = _f(l['units']) or (_f(l.get('wantUnits')) if l.get('buying') else 0.0)
    usd = units * (_f(prices.get(pair)) or l['entry'])
    # an EMPTY coin (buy never landed) still swaps: the new coin takes the empty slot and the keeper re-arms its buy from spare SOL
    c['legs'][c['legs'].index(l)] = {**_leg(nxt, max(0.0, usd), now, l['role']), 'picked': True}
    c['feesUsd'] = round(_f(c['feesUsd']) + 2 * cfg['paperFeeUsd'], 4)
    c['events'].append({'at': now, 'kind': 'rotate', 'symbol': l['symbol'], 'usd': round(usd, 4), 'why': '⇄ swapped by hand', 'to': [nxt.get('symbol')]})
    owner_out(c, l['mint'], now)
    return c


def crown_round(cards):
    """🏆 The finished round's best card (highest lastRoundPct, must be > 0) gets a round win. Mutates + returns the winner id."""
    done = [c for c in cards.values() if c.get('lastRoundPct') is not None and not c.get('roundCrowned')]
    if not done:
        return None
    best = max(done, key=lambda c: c['lastRoundPct'])
    for c in done:
        c['roundCrowned'] = True
    if best['lastRoundPct'] > 0:
        best['roundWins'] = int(best.get('roundWins') or 0) + 1
        return best['id']
    return None
