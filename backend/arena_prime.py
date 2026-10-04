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

# Three top tiers. Every coin on a Prime card is rated 3–5★ (anything weaker never gets in). Each card holds a STABLE anchor
# (a real major on Solana: SOL / JitoSOL / cbBTC …, rotated only on configured re-shapes, never stopped out) + deep pools + gated runners.
TEMPLATES = {   # anchors / pools / runners per card + the dial it runs
    # 5 top tiers. Majors = solid holds; "young" runners = pre-bond runners + clean graduated coins under 48h (every gate but pre-bond).
    'safe': {'label': '💎 Prime Diamond', 'tier': 'diamond', 'anchors': 1, 'pools': 0, 'runners': 3, 'tp': 900, 'sl': 35,
             'why': 'young coins held toward 10× — momentum decides ride / bank, SOL anchors the card'},
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
          'breakeven': {'anchors': 0, 'pools': 1, 'runners': 3, 'byVol': True, 'growth': 'runner', 'why': '⚖ breakeven run — 1 high-volume pool + 3 high-volume runners'}}
SHAPES = tuple(PHASES)
CYCLE = ('anchor', 'degen', 'anchor', 'mixed')
CYCLE_TIERS = ('degen', 'next')
# 🔄 Round cycles per tier (HQ picks): off = keep the tier's own shape · classic = anchor→degen→anchor→mixed ·
# adaptive = a LOSING round rests in majors, a winning one (≥ +5%) presses with runners, flat = mixed · safe = anchor⇄mixed ·
# press = degen⇄mixed. Every phase change is the same run (P&L continues).
CYCLE_MODES = {'off': None, 'classic': CYCLE, 'adaptive': 'adaptive', 'safe': ('anchor', 'mixed'), 'press': ('degen', 'mixed'),
               'rescue': ('safest', 'breakeven'), 'auto': 'auto'}
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
DEFAULT_PAYOUTS = {'safe': 25, 'balanced': 50, 'degen': 0, 'next': 25, 'ever': 75}   # % of every profit take paid straight to the wallet
RUG_LIQ = 0.5   # 🚨 rug shield: pool liquidity at ≤ 50% of entry = pulled → sell at once
TRAIL_AT, TRAIL_KEEP = 50.0, 5.0   # 🔒 a coin that ran ≥ +50% is sold before it gives it all back (≤ +5% left)
FIX_DAY_PCT = -40.0   # 🔧 a tier card whose DAY falls to −40% gets its config fixed: re-dealt fresh on the safe cycle (logged)
RIDE_AT, RIDE_TRAIL = 150.0, 30.0
RIDE_ATS, RIDE_TRAILS = (0, 25, 50, 100, 150), (10, 15, 20, 30)   # rideAt 0 = off (never freeze a runner)
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
CFG_RANGES = {'sizeUsd': (10, 10000), 'rotateHours': (0.08, 48), 'rotateCount': (1, 3), 'paperFeeUsd': (0, 5), 'floorPct': (5, 60)}


COOL_ROUNDS = 3   # 🧊 a coin that just LEFT a card isn't dealt back into it for 3 rounds (min 15 min) — fresh coins flow in, no buy-back loop
LOSS_COOL_SEC = 86400   # 🩸 a coin that left at a LOSS stays out until its price is back above where it was sold (max 24h) — never re-buy a crash


def _stamp(v):
    return v if isinstance(v, dict) else {'at': _f(v)}


def cooling(card, now, rotate_hours, prices=None):
    """Mints this card dropped recently (still cooling down), plus loss exits still under their exit price."""
    win = max(900.0, COOL_ROUNDS * _f(rotate_hours) * 3600)
    out = set()
    for m, v in ((card or {}).get('cool') or {}).items():
        s = _stamp(v); age = now - _f(s.get('at'))
        if age < win:
            out.add(m)
        elif s.get('loss') and age < LOSS_COOL_SEC and _f(s.get('px')) > 0:
            px = _f((prices or {}).get(s.get('pair')))
            if not px or px <= _f(s['px']):
                out.add(m)
    return out


def note_dropped(before, after, now, rotate_hours, prices=None):
    """Stamp every coin that left the card this tick (sold / rotated / re-shaped out) with its exit price + whether it lost;
    forget stamps once they can't cool anything any more."""
    if not after:
        return after
    keep = max(900.0, COOL_ROUNDS * _f(rotate_hours) * 3600)
    held = {l['mint'] for l in after.get('legs') or []}
    cool = {m: _stamp(v) for m, v in (after.get('cool') or {}).items()}
    cool = {m: v for m, v in cool.items() if now - _f(v.get('at')) < (LOSS_COOL_SEC if v.get('loss') else keep)}
    for l in (before or {}).get('legs') or []:
        if l.get('role') == 'anchor' or l['mint'] in held:
            continue
        px = _f((prices or {}).get(l.get('pairAddress'))) or _f(l.get('entry'))
        cool[l['mint']] = {'at': now, 'px': px, 'pair': l.get('pairAddress'), 'loss': bool(_f(l.get('entry')) > 0 and px < _f(l['entry']))}
    return {**after, 'cool': cool}


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
    out['rotateHours'], out['rotateCount'] = round(float(out['rotateHours']), 2), int(out['rotateCount'])
    for k in ('on', 'compound'):
        if k in (p or {}):
            out[k] = bool(p[k])
    if (p or {}).get('slMode') in SL_MODES:
        out['slMode'] = p['slMode']
    cyc = (p or {}).get('cycles') if isinstance((p or {}).get('cycles'), dict) else {}
    out['cycles'] = {t: (cyc.get(t) if valid_cycle(cyc.get(t)) else DEFAULT_CYCLES.get(t, 'off')) for t in DEFAULT_CYCLES}
    out['rotateMinDrop'] = max(0.0, min(50.0, _f((p or {}).get('rotateMinDrop', ROTATE_MIN_DROP))))
    out['rideAt'] = float(_f((p or {}).get('rideAt'))) if (p or {}).get('rideAt') is not None and _f((p or {}).get('rideAt')) in RIDE_ATS else RIDE_AT
    out['keepWinPct'] = float(_f((p or {}).get('keepWinPct'))) if (p or {}).get('keepWinPct') is not None and _f((p or {}).get('keepWinPct')) in KEEP_WINS else 5.0
    out['rideTrail'] = float(_f((p or {}).get('rideTrail'))) if _f((p or {}).get('rideTrail')) in RIDE_TRAILS else RIDE_TRAIL
    rsc = _f((p or {}).get('rescuePct', -RESCUE_PCT))
    out['rescuePct'] = 0.0 if (p or {}).get('rescuePct') is not None and rsc == 0 else max(20.0, min(80.0, rsc))   # 0 = rescue off
    out['rotateConfirm'] = int(max(1, min(6, _f((p or {}).get('rotateConfirm', ROTATE_CONFIRM)))))
    out['minHoldMins'] = max(0.0, min(240.0, _f((p or {}).get('minHoldMins', MIN_HOLD_MINS))))
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
    return out


# 🎯 TRUE FILLS (paper = exactly what a real wallet would get): constant-product price impact against the pool's quote-side
# reserve (≈ half its liquidity). Buy $u → average fill = mid × (1 + u/R); sell $v of coins → you receive v / (1 + v/R).
# The pool / FEELESS fee is a separate line (feesUsd), never inside P&L; impact IS the price you got, so it is in the fill.
IMPACT_MULT = 1.0   # 🎯 learned from REAL Fuse-wallet fills (fuse_wallet.calibrate): >1 = real impact was worse than the model
BELL_SEC = 10       # 🔔 every round opens with a 10s countdown on screen; the engine wakes exactly when the round is due


UNKNOWN_LIQ = 20_000.0   # no liquidity reading (fresh / curve coins) = treat the pool as THIN, never infinitely deep


def _r(liq):
    return (_f(liq) if _f(liq) > 0 else UNKNOWN_LIQ) / 2 / max(0.1, IMPACT_MULT)


def buy_px(px, usd, liq):
    return px * (1 + _f(usd) / _r(liq)) if px > 0 else px


def sell_usd(units, px, liq):
    v = _f(units) * _f(px)
    return v / (1 + v / _r(liq))


def _leg(c, usd, now, role):
    mid = _f(c.get('price'))
    lv = c.get('liquidity')   # every candidate source names depth differently — a coin dealt with liq 0 read as "$0 pool" to the keeper
    liq = _f(c.get('liquidityUsd') or c.get('liq') or (lv.get('usd') if isinstance(lv, dict) else lv))
    px = buy_px(mid, usd, liq)
    return {'mint': c['mint'], 'pairAddress': c['pairAddress'], 'symbol': c.get('symbol'), 'role': role, 'entry': px, 'units': usd / px if px > 0 else 0.0,
            'costUsd': round(usd, 6), 'at': now, 'stars': c.get('stars') or stars(c, role), 'firstEntry': px, 'liq': liq, 'midAtEntry': mid,
            **({'newMajor': True} if c.get('newMajor') else {}), **({'arena': True} if c.get('arena') else {})}


def _picks(t, pools, runners, anchors):
    """anchors → pools → runners, 3★+ only, one slot per coin (a SOL pool never doubles the SOL anchor). `byVol` shapes take the
    highest-volume pools / runners first (breakeven needs flow, not just score)."""
    seen, out = set(), []
    for src, role, n in ((anchors, 'anchor', t['anchors']), (pools, 'pool', t['pools']), (runners, 'runner', t['runners'])):
        k = 0
        ranked_ = rated(src, role)
        if t.get('byVol'):
            ranked_ = sorted(ranked_, key=lambda c: -(_f(c.get('vol1h')) or _f(c.get('volume24h')) / 24))
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
    """Rotate the eligible-major basket at a scheduled re-shape. Initial deals still begin with SOL, but a one-anchor phase
    must not silently mean "SOL forever"; subsequent configured shapes walk the existing ranked majors without inventing a
    new threshold or bypassing any candidate gate."""
    rows = list(anchors or [])
    if not rows:
        return rows
    n = int(_f(offset)) % len(rows)
    return rows[n:] + rows[:n]


def keep_winners(nc, old_legs, prices, liqs, pct, in_play_usd):
    """🛡 A re-shape never sells a winner: old coins up ≥ pct% (or ❄ frozen, or riding) are CARRIED into the new card as they are
    (same units + entry); the freshly dealt coins give up their slots and share what's left of the money, so the total stays exactly
    `in_play_usd`. Returns (card or None if every coin is kept → no re-shape, kept count)."""
    again = {l['mint'] for l in nc['legs']}   # ♻ a coin the new shape deals AGAIN is carried as it is — selling it to buy it straight back only pays fees
    win = [l for l in old_legs if l.get('role') != 'anchor' and _f(l.get('entry')) > 0 and (l.get('frozen') or l.get('ride') or l.get('picked') or l['mint'] in again or
           (_f(pct) > 0 and ((_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] - 1) * 100 >= _f(pct)))]
    if not win:
        return nc, 0
    want = {l['mint']: _f(l['units']) for l in nc['legs']}
    def carry(l):   # a re-picked (unprotected) coin keeps its entry but only up to its new slot — the rest is trimmed, never sold whole + rebought
        prot = l.get('frozen') or l.get('ride') or l.get('picked') or (_f(pct) > 0 and ((_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] - 1) * 100 >= _f(pct))
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
    return {**nc, 'legs': fresh + [{k: v for k, v in l.items() if k != 'picked'} for l in win]}, len(win)   # a hand pick survives ONE re-shape


def deal(tid, pools, runners, cfg, now, anchors=(), usd=None, keep=None, shape=None):
    """A fresh Prime card from the best 3★+ candidates (gated + ranked by the caller). Equal $ per coin. `keep` re-deals an
    existing card (after its floor) while keeping its start, events and record — P&L stays honest across re-deals."""
    t = {**TEMPLATES[tid], **(PHASES.get(shape) or {})}
    # Each due shape advances the major basket. This makes one-anchor phases use different eligible majors over time while
    # keeping the configured number of anchors and the service's existing major ranking authoritative.
    every = int(_f(cfg.get('cycleEvery'))) or 1
    anchor_offset = int(_f((keep or {}).get('rounds')) // every) if shape else 0
    picks = _picks(t, pools, runners, rotate_anchors(anchors, anchor_offset))
    if not picks or (shape and len(picks) < MIN_CYCLE_COINS):
        return None
    size = usd if usd is not None else cfg['sizeUsd']
    each = size / len(picks)
    base = {'id': f'prime-{tid}', 'tpl': tid, 'label': t['label'], 'at': now, 'cash': 0.0, 'feesUsd': 0.0, 'compoundedUsd': 0.0, 'takenUsd': 0.0,
            'events': [], 'startUsd': cfg['sizeUsd'], 'dayAt': now, 'dayStartUsd': cfg['sizeUsd'], 'days': [], 'lowPct': 0.0}
    c = {**base, **(keep or {})}
    c.update(lastRotateAt=now, legs=[_leg(x, each, now, r) for x, r in picks], cash=0.0, flooredAt=None)
    c['startUsd'] = (keep or {}).get('startUsd', cfg['sizeUsd'])
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
    v = sum(coin(l) for l in card['legs']) + card['cash'] + sum(_f(p['usd']) for p in (card.get('parked') or {}).values()) + _f(card.get('walletUsd'))
    return round(v, 4)


def in_play(card, prices, liqs=None):
    """What can be re-dealt into coins: the card's value MINUS what was already paid out to the wallet and what sits parked
    (both stay theirs — re-buying coins with them would count the same dollars twice)."""
    return round(value(card, prices, liqs) - _f(card.get('walletUsd')) - sum(_f(p.get('usd')) for p in (card.get('parked') or {}).values()), 4)


def tick(card, prices, pools, runners, cfg, now, anchors=(), mom=None, liqs=None, true_usd=None):
    """One automation pass. Returns the updated card (mutated copy) — all actions logged as events with reasons.
    liqs = {pair: pool liquidity $} for TRUE fills (price impact on every paper buy / sell)."""
    liqs = liqs or {}
    t = TEMPLATES[card['tpl']]
    c = {**card, 'legs': [dict(l) for l in card['legs']], 'events': list(card['events'])}
    have = lambda: {l['mint'] for l in c['legs']}
    # 💵 a REAL card is judged on its true book (confirmed coins + SOL), never on the engine's estimate — an estimate that missed
    # unlanded / skipped buys once read −32% on a card really at −20% and the floor sold everything twice in 20 min
    V = (lambda: _f(true_usd)) if true_usd is not None and _f(true_usd) > 0 else (lambda: value(c, prices, liqs))
    ev = lambda **e: c['events'].append({'at': now, **e})
    fee = cfg['paperFeeUsd']

    def best(role):
        src = rated(runners if role == 'runner' else anchors if role == 'anchor' else pools, role)
        if role == 'runner' and cfg.get('strictRunners'):   # 🌧 runner weather is bad: only runners with real flow + buyers get in
            src = [x for x in src if _f(x.get('vol1h')) >= STRICT_VOL1H and (x.get('buyShare') is None or _f(x.get('buyShare')) >= STRICT_BUYS)]
        return next((x for x in src if x['mint'] not in have() and _f(x.get('price')) > 0), None)
    c.setdefault('dayAt', c['at']); c.setdefault('dayStartUsd', c['startUsd']); c.setdefault('days', []); c.setdefault('lowPct', 0.0)

    # 0) a floored card sits in its anchor (cash-like) until the next day, then is re-dealt fresh at its current value
    if c.get('flooredAt') and now - c['flooredAt'] >= 60:   # floored → re-dealt with fresh 3★+ coins on the very next tick (a new run)
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
    for l in list(c['legs']):
        lq, lq0 = _f(liqs.get(l['pairAddress'])), _f(l.get('liq'))
        if l.get('role') == 'anchor' or l.get('frozen') or lq <= 0 or lq0 <= 0 or lq > lq0 * RUG_LIQ:
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
        if l.get('ride'):
            l['high'] = max(_f(l.get('high')), px)
            if g >= floor_g and px > l['high'] * (1 - rt / 100):
                continue   # still holding: above its floor and not rt% off its high
            why_end = (f"fell under +{floor_g:g}% ({g:+.0f}%)" if g < floor_g else f"fell {rt:g}% from its peak") + f" after riding to {l['high'] / (l.get('rideFrom') or l['entry']):.1f}×"
            l['ride'] = False
            nxt = best(l.get('role') or 'runner')
            if nxt:   # 🏇 ride over → SWAPPED for the best coin of its kind (the gain moves into it)
                usd = sell_usd(l['units'], px, liqs.get(l['pairAddress']) or l.get('liq'))
                c['legs'][c['legs'].index(l)] = _leg(nxt, usd, now, l.get('role') or 'runner'); c['feesUsd'] += 2 * fee; c['takenUsd'] += max(0.0, usd - _f(l.get('costUsd')))
                ev(kind='ride-end', symbol=l['symbol'], usd=round(usd, 4), why=f"{why_end} — swapped", to=[nxt.get('symbol')])
                continue
            mode, frac, why = 'ride-end', 1.0, f"{why_end} — sold" 
        elif _f(cfg.get('rideAt', RIDE_AT)) > 0 and g >= ra and l.get('role') != 'anchor' and _f(l.get('units')) > 0:   # never 'ride' a coin you don't hold
            l.update(ride=True, high=px, rideFrom=l['entry'], rideAt=now)
            ev(kind='ride', symbol=l['symbol'], usd=round(l['units'] * px, 4), why=f"+{g:.0f}% ≥ +{ra:g}% — ❄ frozen (riding) until it falls {rt:g}% from its peak, then swapped", to=[l['symbol']])
            continue
        elif g >= t['tp']:
            mode, frac, why = exit_plan(g, mom.get(l['pairAddress']))
        else:
            continue
        if True:
            sold = l['units'] * frac
            gain = sell_usd(sold, px, liqs.get(l['pairAddress']) or l.get('liq'))   # what the pool really pays
            l['units'] -= sold; l['entry'] = px; c['feesUsd'] += fee
            c['takenUsd'] += gain
            others = [o for o in c['legs'] if o is not l and _f(prices.get(o['pairAddress'])) > 0]
            label = why if mode == 'ride-end' else f"+{g:.0f}% ≥ +{t['tp']}% · {why}"   # a held runner's exit explains itself
            # 🧬 profit split (tier DNA): payoutPct → straight to the owner's wallet, the rest compounds — smart = into the strongest coins
            dna = {'payoutPct': (cfg.get('payouts') or DEFAULT_PAYOUTS).get(card['tpl'], 0), 'compound': cfg.get('compoundStyle', 'smart') if cfg['compound'] else 'off'}
            out_usd, back_usd = _dna.split_profit(gain, dna)
            if out_usd > 0:
                c['walletUsd'] = round(_f(c.get('walletUsd')) + out_usd, 6)
                ev(kind='payout', symbol=l['symbol'], usd=round(out_usd, 4), why=f"{dna['payoutPct']}% of the take → owner's wallet", to=['wallet'])
            if back_usd > 0 and others:
                wts = _dna.compound_weights(others, mom) if dna['compound'] == 'smart' else {o['pairAddress']: 1 / len(others) for o in others}
                into = [o for o in others if wts.get(o['pairAddress'])]
                for o in into:
                    each = back_usd * wts[o['pairAddress']]
                    opx = buy_px(_f(prices.get(o['pairAddress'])), each, liqs.get(o['pairAddress']) or o.get('liq'))
                    o['units'] += each / opx; o['costUsd'] += each
                c['compoundedUsd'] += back_usd; c['feesUsd'] += fee * len(into)
                ev(kind='tp', symbol=l['symbol'], usd=round(back_usd, 4), why=label + (' · 🧲 smart compound' if dna['compound'] == 'smart' else ''), mode=mode, to=[o['symbol'] for o in into])
            elif back_usd > 0 or (gain > 0 and dna['compound'] == 'off' and out_usd < gain):
                rest = gain - out_usd
                c['cash'] += rest
                ev(kind='tp', symbol=l['symbol'], usd=round(rest, 4), why=label, mode=mode, to=['cash'])
    # 2) stop-loss (sl 0 = never stopped) — what happens follows cfg slMode:
    #    replace → sold and swapped at once for the best gated coin of the same role
    #    park    → sold to cash, the SLOT is kept; bought back when price is back at the stop-out entry with momentum
    #    hold    → never sold on a stop (the floor still protects the card)
    mode = cfg.get('slMode', 'replace')
    c['parked'] = dict(c.get('parked') or {})
    for l in list(c['legs']):
        px = _f(prices.get(l['pairAddress']))
        lmode = l.get('slMode') if l.get('slMode') in SL_MODES else mode   # ❄/✂/🅿 per coin (HQ) beats the card's mode
        if l.get('role') == 'anchor' or not t['sl'] or lmode == 'hold' or l.get('frozen') or l.get('ride') or int(l.get('freezeRounds') or 0) > 0 or px <= 0 or l['entry'] <= 0:
            continue
        dd = (px / l['entry'] - 1) * 100
        l['peak'] = max(_f(l.get('peak')), dd)
        trail = cfg.get('trail', True) and _f(l['peak']) >= TRAIL_AT and dd <= TRAIL_KEEP   # 🔒 ran +50%, now giving it back
        if not trail and dd > -t['sl'] and not (dd <= -t['sl'] / 2 and fading(mom.get(l['pairAddress']))):   # early cut: half the stop + fading
            continue
        out_usd = sell_usd(l['units'], px, liqs.get(l['pairAddress']) or l.get('liq'))
        why = (f"ran +{l['peak']:.0f}%, back to {dd:+.0f}% — locked before it turned red" if trail else
               f"{dd:.0f}% ≤ −{t['sl']}%" if dd <= -t['sl'] else f"{dd:.0f}% and fading (1h down, sellers lead) — cut early")
        c['feesUsd'] += fee
        nxt = best(l['role']) if lmode == 'replace' else None
        if nxt:
            c['legs'][c['legs'].index(l)] = _leg(nxt, out_usd, now, l['role']); c['feesUsd'] += fee
            ev(kind='sl', symbol=l['symbol'], usd=round(out_usd, 4), why=why, to=[nxt.get('symbol')])
        elif lmode == 'park':
            c['legs'].remove(l)
            c['parked'][l['pairAddress']] = {**{k: l.get(k) for k in ('mint', 'pairAddress', 'symbol', 'role', 'stars', 'firstEntry')}, 'usd': round(out_usd, 6),
                                             'backAt': l['entry'], 'at': now, 'price': px}
            ev(kind='park', symbol=l['symbol'], usd=round(out_usd, 4), why=f"{why} — sold to SOL, slot kept; buys back at ${l['entry']:.6g} with momentum", to=['parked'])
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
    if now - c['lastRotateAt'] >= cfg['rotateHours'] * 3600 + BELL_SEC and not c.get('flooredAt'):   # the round ends, a 10s 🔔 countdown, then the deal
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
        for l in ranked[:cfg['rotateCount']]:
            nxt = best(l['role'])
            if not nxt:
                continue
            px = _f(prices.get(l['pairAddress'])) or l['entry']
            usd = sell_usd(l['units'], px, liqs.get(l['pairAddress']) or l.get('liq'))
            c['legs'][c['legs'].index(l)] = _leg(nxt, usd, now, l['role']); c['feesUsd'] += 2 * fee; swapped += 1
            rotated_out.add(l.get('mint'))
            ev(kind='rotate', symbol=l['symbol'], usd=round(usd, 4), why=f"weakest after {cfg['rotateHours']}h", to=[nxt.get('symbol')])
        c['lastRotateAt'] = now
        # one ROUND per rotation: log this round's move, start the next one from today's value
        v_now = V()
        c['rounds'] = int(c.get('rounds') or 0) + 1
        c['lastRoundPct'] = round((v_now / (_f(c.get('roundStartUsd')) or _f(c['startUsd']) or 1) - 1) * 100, 2)
        c['roundStartUsd'] = round(v_now, 4); c['roundCrowned'] = False
        # 📈 streaks: 3 losing rounds → the config is changed (safe cycle); 3 winning rounds → config locked + best coin frozen one round
        for l in c['legs']:   # a coin frozen for one round was protected through this rotation — now it's free again
            if int(l.get('freezeRounds') or 0) > 0:
                l['freezeRounds'] = int(l['freezeRounds']) - 1
        lr = _f(c['lastRoundPct']); st = int(c.get('streak') or 0)
        st = (st + 1 if st >= 0 else 1) if lr >= STREAK_PCT else (st - 1 if st <= 0 else -1) if lr <= -STREAK_PCT else st   # noise keeps the streak as is
        if int(c.get('lockRounds') or 0) > 0:   # only a real win-lock counts down (✋ hold all has no counter)
            c['lockRounds'] = int(c['lockRounds']) - 1
        if c.get('cycleFix') == 'safe' and int(c.get('rounds') or 0) >= int(c.get('fixUntil') or 0):
            c.pop('cycleFix', None); st = 0   # the safe fix lasts SAFE_FIX_ROUNDS, then the card goes back to its own cycle (never re-armed the same round)
            ev(kind='streak', why=f'safe fix done — back to its own cycle')
        if st <= -STREAK:
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
    if rp < 0 and not c.get('cycleFix') == 'rescue' and (V() / (_f(c['startUsd']) or 1) - 1) * 100 <= rp:
        c['cycleFix'] = 'rescue'   # 🛟 fell rescuePct% under its start → safest ⇄ breakeven until a new run
        ev(kind='rescue', why=f'card ≤ {rp:.0f}% of its start — 🛟 rescue cycle: safest run ⇄ breakeven runners')
    every = 1 if c.get('cycleFix') else int(cfg.get('cycleEvery') if cfg.get('cycleEvery') is not None else 6)
    phase = None if not every or c.get('holdAll') else next_phase(c.get('cycleFix') or (cfg.get('cycles') or DEFAULT_CYCLES).get(card['tpl'], 'off'), (int(c.get('rounds') or 0) // every), c.get('lastRoundPct'))
    majors_only = all(l.get('role') == 'anchor' for l in c['legs'])
    if every and int(c.get('rounds') or 0) % every and not (majors_only and phase and phase != 'anchor'):
        phase = None   # re-shape every N rounds only (less churn) — EXCEPT a majors-only card due a growth shape re-shapes at once
    grow_now = majors_only and phase and phase != 'anchor'   # a majors-only card due growth isn't held back by the win-lock
    if c.pop('redealNow', None) and not c.get('flooredAt'):   # 🃏 one-tap re-deal: fresh coins NOW, same money + run (real cards keep their book)
        phase, grow_now, c['lastRotateAt'] = phase or c.get('phase') or 'mixed', True, now
    if phase and c['lastRotateAt'] == now and not c.get('flooredAt') and (grow_now or not int(c.get('lockRounds') or 0)):
        # Protected coins do not block the whole scheduled shape. `keep_winners` carries riders, frozen/manual picks and configured
        # winners into the new shape, while the unprotected slots can still become majors/new majors as the saved cycle requires.
        ip = in_play(c, prices, liqs)
        # A phase re-shape runs on this same boundary. Do not immediately select the mint that was just rotated out.
        phase_pools = [x for x in pools if x.get('mint') not in rotated_out]
        phase_runners = [x for x in runners if x.get('mint') not in rotated_out]
        nc = deal(c['tpl'], phase_pools, phase_runners, cfg, now, anchors, usd=ip, keep={k: c[k] for k in c if k not in ('legs', 'cash', 'lastRotateAt')}, shape=phase)
        if nc:
            same = {l['mint'] for l in nc['legs']} <= {l['mint'] for l in c['legs']}
            nc, kept = keep_winners(nc, c['legs'], prices, liqs, cfg.get('keepWinPct', 5.0), ip)
            if not nc and same:
                c['phase'] = phase   # ♻ the new shape deals the very coins the card holds → shape moves on, zero trades
            if nc:
                nc['feesUsd'] = round(_f(nc['feesUsd']) + fee * (len(c['legs']) - kept), 4)   # selling the old shape (kept coins aren't sold)
                if kept:
                    nc['events'] = list(nc.get('events') or []) + [{'kind': 'keep', 'at': now, 'why': f'🛡 {kept} winning / frozen coin{"s" if kept > 1 else ""} carried into the {phase} shape — never sold by a re-shape'}]
                c = nc
    # 4) idle cash goes back to work when compounding
    if cfg['compound'] and c['cash'] > 0.01 and c['legs']:
        waiting = [l for l in c['legs'] if l.get('buying')]   # 👛 real card: SOL whose buy hasn't landed belongs to THAT coin first
        each = c['cash'] / len(waiting or c['legs'])
        for l in waiting or c['legs']:
            px = buy_px(_f(prices.get(l['pairAddress'])) or l['entry'], each, liqs.get(l['pairAddress']) or l.get('liq'))
            l['units'] += each / px; l['costUsd'] += each
        c['compoundedUsd'] += c['cash']; ev(kind='compound', usd=round(c['cash'], 4), why='idle cash back into the card', to=[l['symbol'] for l in c['legs']]); c['cash'] = 0.0
    v = V(); start = _f(c['startUsd']) or 1
    day_pct = (v / (_f(c.get('dayStartUsd')) or start) - 1) * 100
    if day_pct <= FIX_DAY_PCT and not c.get('flooredAt') and (c.get('fixedAt') is None or now - _f(c['fixedAt']) >= 86400):   # 🔧 worst day hit −40% → fix the config
        keep = {k: c[k] for k in c if k not in ('legs', 'cash', 'lastRotateAt')}
        keep['runs'] = (list(c.get('runs') or []) + [{'at': now, 'startUsd': c['startUsd'], 'endUsd': round(v, 4), 'pct': round((v / start - 1) * 100, 2), 'fixed': True}])[-10:]
        keep.update(cycleFix='safe', fixUntil=int(c.get('rounds') or 0) + SAFE_FIX_ROUNDS, fixedAt=now, dayStartUsd=round(v, 4), dayAt=now, startUsd=round(v, 4), roundStartUsd=round(v, 4), lowPct=0.0)   # a new run from here
        nc = deal(c['tpl'], pools, runners, cfg, now, anchors, usd=in_play(c, prices, liqs), keep=keep, shape='anchor')
        if nc:
            nc['events'].append({'at': now, 'kind': 'fix', 'why': f"day {day_pct:.0f}% ≤ {FIX_DAY_PCT:.0f}% — config fixed: re-dealt into majors, safe cycle from here"})
            c = nc
        v = V()
    # 5) 🛡 FLOOR: the card is never allowed to sit below −floorPct (default −20%, so −25% is never reached short of a gap):
    #    every pool / runner is sold into the anchor (or cash) at once; the card re-deals fresh the next day.
    v = V(); start = _f(c['startUsd']) or 1
    pct = (v / start - 1) * 100
    if pct <= -cfg['floorPct'] and not c.get('flooredAt'):
        anc = [l for l in c['legs'] if l.get('role') == 'anchor' and _f(prices.get(l['pairAddress'])) > 0]
        out = [l for l in c['legs'] if l.get('role') != 'anchor']
        usd = sum(sell_usd(l['units'], _f(prices.get(l['pairAddress'])) or l['entry'], liqs.get(l['pairAddress']) or l.get('liq')) for l in out)
        c['feesUsd'] += fee * len(out)
        if anc:
            for a in anc:
                apx = _f(prices.get(a['pairAddress'])); a['units'] += usd / len(anc) / apx; a['costUsd'] += usd / len(anc)
        else:
            c['cash'] += usd
        c['legs'] = anc or []
        c['flooredAt'] = now
        ev(kind='floor', usd=round(usd, 4), why=f"card {pct:.0f}% ≤ −{cfg['floorPct']:g}% floor — everything into the anchor", to=[a['symbol'] for a in anc] or ['cash'])
    c['lowPct'] = round(min(_f(c.get('lowPct')), pct), 2)
    # 6) the day record: every 24h the card's day move is logged — a good day is ≥ +10%
    if now - c['dayAt'] >= 86400:
        c['days'] = (c['days'] + [{'at': now, 'pct': round((v / (_f(c['dayStartUsd']) or 1) - 1) * 100, 2)}])[-30:]
        c['dayAt'], c['dayStartUsd'] = now, round(v, 4)
    for l in c['legs']:
        if _f(liqs.get(l['pairAddress'])) > 0:
            l['liqNow'] = _f(liqs[l['pairAddress']])
    c['feesUsd'] = round(c['feesUsd'], 4)
    c['events'] = c['events'][-60:]
    return c


def cycle_peek(card, cfg):
    """🔄 What the card holds now and what it re-shapes into next (same rules as `tick`): {now, next, inRounds, mode, fix}.
    adaptive / auto pick by the last round's move, so `next` is the shape IF the next round moves like the last one."""
    cfg = cfg or {}
    mode = card.get('cycleFix') or (cfg.get('cycles') or DEFAULT_CYCLES).get(card.get('tpl'), 'off')
    every = 1 if card.get('cycleFix') else int(cfg.get('cycleEvery') if cfg.get('cycleEvery') is not None else 6)
    if not every or card.get('holdAll'):
        return {'now': card.get('phase'), 'next': None, 'inRounds': None, 'mode': 'hold' if card.get('holdAll') else mode, 'fix': card.get('cycleFix')}
    r = int(card.get('rounds') or 0)
    n = every - (r % every)
    nxt = next_phase(mode, (r + n) // every, card.get('lastRoundPct'))
    return {'now': card.get('phase'), 'next': nxt, 'inRounds': n if nxt else None, 'mode': mode, 'fix': card.get('cycleFix')}


def summary(card, prices, cfg=None):
    v = value(card, prices)
    start = _f(card.get('startUsd')) or 1
    rot = _f((cfg or {}).get('rotateHours')) or DEFAULT_CFG['rotateHours']
    paid = round(_f(card.get('walletUsd')), 4)
    legs = [{**{k: l[k] for k in ('mint', 'pairAddress', 'symbol', 'role', 'entry', 'units', 'costUsd')}, 'stars': l.get('stars') or 3,
             'frozen': bool(l.get('frozen')), 'slMode': l.get('slMode'), 'ride': bool(l.get('ride')), 'high': l.get('high'), 'rideFrom': l.get('rideFrom'), 'buying': bool(l.get('buying')),
             'loseRounds': int(l.get('loseRounds') or 0),
             'firstEntry': l.get('firstEntry') or l['entry'], 'at': l.get('at'), 'now': _f(prices.get(l['pairAddress'])) or l['entry'],
             'pnlPct': round(((_f(prices.get(l['pairAddress'])) or l['entry']) / l['entry'] - 1) * 100, 2) if l['entry'] else 0.0,
             'liq': _f(l.get('liqNow')) or _f(l.get('liq')),
             'usd': round(value({'legs': [l], 'cash': 0.0}, prices), 4)} for l in card['legs']]
    return {**{k: card[k] for k in ('id', 'tpl', 'label', 'at', 'lastRotateAt', 'compoundedUsd', 'takenUsd', 'feesUsd', 'startUsd')}, 'cash': round(card['cash'], 4), 'walletUsd': round(_f(card.get('walletUsd')), 4),
            'flooredAt': card.get('flooredAt'), 'phase': card.get('phase'), 'cycleFix': card.get('cycleFix'), 'cycle': list(CYCLE) if card['tpl'] in CYCLE_TIERS else None, 'rounds': int(card.get('rounds') or 0), 'lastRoundPct': card.get('lastRoundPct'),
            'roundPct': round((v / (_f(card.get('roundStartUsd')) or start) - 1) * 100, 2), 'roundWins': int(card.get('roundWins') or 0),
            'valueUsd': v, 'pnlPct': round((v / start - 1) * 100, 2), 'legs': legs, 'events': card['events'][-12:][::-1],
            'tp': TEMPLATES[card['tpl']]['tp'], 'sl': TEMPLATES[card['tpl']]['sl'], 'tier': TEMPLATES[card['tpl']]['tier'], 'why': TEMPLATES[card['tpl']].get('why'),
            'parked': list((card.get('parked') or {}).values()),
            # 🧮 the money in plain words: PUT IN → NOW = STILL IN THE CARD + PAID OUT; P&L = NOW − PUT IN (fees apart)
            'math': {'putIn': round(start, 4), 'heldUsd': round(v - paid, 4), 'paidOutUsd': paid, 'nowUsd': v, 'pnlUsd': round(v - start, 4),
                     'compoundedUsd': round(_f(card.get('compoundedUsd')), 4), 'feesUsd': round(_f(card.get('feesUsd')), 4)},
            'nextRoundAt': round(_f(card.get('lastRotateAt')) + rot * 3600 + BELL_SEC, 1), 'bellSec': BELL_SEC, 'real': bool(card.get('real')), 'realSince': card.get('realSince'),
            **record(card)}


def record(card):
    """Honest scoreboard: of the last 10 logged days, how many were up ≥ +10%; the worst the card has ever been."""
    days = (card.get('days') or [])[-10:]
    return {'days': days, 'goodDays': sum(1 for d in days if _f(d.get('pct')) >= HIT_PCT), 'loggedDays': len(days),
            'lowPct': _f(card.get('lowPct')), 'floored': bool(card.get('flooredAt')), 'runs': (card.get('runs') or [])[-5:]}


def set_leg(card, pair, frozen=None, sl_mode=None):
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
    return c


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
