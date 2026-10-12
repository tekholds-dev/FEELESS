"""⚡ THE OFFICE'S EDGE PASS — pure, deterministic, tested (`tests/test_office_edge.py`). No network, no wallet, no order: everything
here is a decision ABOUT the existing agent path on the creator's real card, or a study of what already happened.

  policy          the creator's limits: per control AGENTS CHOOSE or CREATOR OVERRIDE (take · stop · trailing · max hold · size · seats ·
                  empty-seat target · switching · entry) and the master authority (agents decide inside the limits | creator manual)
  ready           the restart / refill state: WARMING UP → POSITIONS RECONCILED → MARKET REFILLED → LIVE
  seat_state      an empty agent seat: FILLING (a cleared candidate exists) or NO VALID ENTRY with the reason — cash is a valid position
  switch_test     the superiority test a switch must pass (a winner is never surrendered; "greener" is not a reason)
  launch_context  what is MEASURABLE about how a coin launched (pad from the mint, curve vs pool, age) — unknown stays unknown
  missed_winners  the coins that ran while we did not hold them: why, per desk, with paper counterfactuals — never a trade
  review          the creator's asynchronous review queue (it is only ever READ by the page; no desk waits on it)
"""
import paper_desk as _pd   # 📝 the OFFLINE practice record (graded paper calls) — it has no live authority
import trench_kernel.universe as _uni
import trench_kernel.senses as _sn
import chart_intel as _ci
import market_data as _md

_f = _sn._f


def _med(xs):
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    return None if not n else round(xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2, 2)


# ── 🎛 THE CREATOR'S LIMITS ──────────────────────────────────────────────────────────────────────────────────────────────────────
AUTHORITY = ('agents', 'manual')                 # agents = CREATOR LIMITS + AGENTS DECIDE · manual = only the hard safety exits act
TP_OPTS, SL_OPTS, HOLD_OPTS, SIZE_OPTS = (5, 10, 15, 20, 30, 50), (3, 5, 8, 10, 15, 20), (5, 10, 15, 30, 60, 120), (10, 15, 25, 40)
BOUNDS = {'agentTp': (2.0, 200.0), 'agentSl': (2.0, 40.0), 'agentTrailArm': (2.0, 100.0), 'agentTrailPct': (1.0, 50.0), 'agentMaxHold': (5.0, 240.0), 'agentSizePct': (5.0, 50.0)}
TRAIL = ('auto', 'off', 'custom')
SEAT_TARGETS = (0, 30, 60)                       # 0 = AUTO (10s)
SEAT_TARGET_AUTO = 10
SWITCH = {'agents': (1.0, 30.0), 'off': None, 'conservative': (1.5, 45.0), 'normal': (1.0, 30.0), 'aggressive': (0.5, 15.0)}   # → (lean margin, minutes held). Aggressive only lowers the margin — never under these floors
SWITCH_FLOOR = (0.5, _uni.CONTROL_HOLD_MIN)
ENTRY = ('agents', 'go')                         # agents = a full GO at once, the duty's cleared case on the seat target · go = a full GO only
POLICY_KEYS = ('agentMinAgeH', 'agentAuthority', 'agentTp', 'agentSl', 'agentTrail', 'agentTrailArm', 'agentTrailPct', 'agentMaxHold', 'agentSizePct', 'agentSeatTarget', 'agentSwitch', 'agentEntry')


def _num(p, k):
    """0 = AGENTS CHOOSE; a number is kept only inside its bounds (clamped, never a silent wild value)."""
    v = _f((p or {}).get(k))
    lo, hi = BOUNDS[k]
    return 0.0 if v <= 0 else round(max(lo, min(hi, v)), 2)


def clean_policy(p):
    """The policy keys of a card config, validated. Anything unknown falls back to AGENTS CHOOSE (the behaviour before this existed)."""
    p = p or {}
    return {'agentAuthority': p.get('agentAuthority') if p.get('agentAuthority') in AUTHORITY else 'agents',
            'agentTp': _num(p, 'agentTp'), 'agentSl': _num(p, 'agentSl'), 'agentTrail': p.get('agentTrail') if p.get('agentTrail') in TRAIL else 'auto',
            'agentTrailArm': _num(p, 'agentTrailArm'), 'agentTrailPct': _num(p, 'agentTrailPct'), 'agentMaxHold': _num(p, 'agentMaxHold'), 'agentSizePct': _num(p, 'agentSizePct'),
            'agentSeatTarget': int(_f(p.get('agentSeatTarget'))) if int(_f(p.get('agentSeatTarget'))) in SEAT_TARGETS else 0,
            'agentSwitch': p.get('agentSwitch') if p.get('agentSwitch') in SWITCH else 'agents', 'agentEntry': p.get('agentEntry') if p.get('agentEntry') in ENTRY else 'agents',
            'agentMinAgeH': _uni.min_age_of(p)}


def policy(cfg):
    """The limits as the desks read them. None = AGENTS CHOOSE for that control. `who` says, per control, who decides right now.
    What each override MEANS (the desks obey exactly this — `controls` puts it on screen):
      take-profit   the line is yours: at it the coin is banked (the agents may still leave EARLIER on a broken thesis or the trail).
                    Under AGENTS CHOOSE the agents bank at their learned scalp line once one is adopted; before that, at your base
                    `agentTakePct` they READ the coin: still clean AND its thesis not weak / invalid → it runs under the trail,
                    anything else → banked.
      stop-loss     your maximum tolerated loss: the agents' own structure stop may be tighter, never wider
      max hold      the longest a coin is held: the agents' thesis windows may end it sooner, never later
      size          the most of the card one seat may be: the Warden may size smaller, never larger
      trailing      off = no give-back protection · custom = arm at +A%, bank P points under the peak
      switching     off · conservative (lean +1.5, 45 min) · normal (+1.0, 30 min) · aggressive (+0.5, 15 min) — never under the floors
      entry         a full 🟢 GO only, or (agents) the duty's cleared case on the empty-seat target too
    MANUAL authority: the agents make no discretionary move at all — only the hard safety exits and the overrides YOU set act."""
    c = clean_policy(cfg)
    trail = c['agentTrail'] if c['agentTrail'] != 'custom' or (c['agentTrailArm'] and c['agentTrailPct']) else 'auto'
    sw = SWITCH[c['agentSwitch']]
    seats = int(_f((cfg or {}).get('agentSeats')) or 4)
    want = int(_f((cfg or {}).get('coins')) or seats)
    who = lambda on: 'CREATOR OVERRIDE' if on else 'AGENTS CHOOSE'
    mode = (cfg or {}).get('agentMode') or 'auto'
    return {'authority': c['agentAuthority'], 'manual': c['agentAuthority'] == 'manual', 'tp': c['agentTp'] or None, 'sl': c['agentSl'] or None,
            'trail': {'mode': trail, 'arm': c['agentTrailArm'] or None, 'pct': c['agentTrailPct'] or None}, 'maxHold': c['agentMaxHold'] or None, 'sizePct': c['agentSizePct'] or None,
            'seats': max(1, min(seats, want)), 'seatTarget': c['agentSeatTarget'] or SEAT_TARGET_AUTO,
            'switch': {'mode': c['agentSwitch'], 'on': sw is not None, 'edge': None if sw is None else max(SWITCH_FLOOR[0], sw[0]), 'holdMin': None if sw is None else max(SWITCH_FLOOR[1], sw[1])},
            'entry': c['agentEntry'], 'exit': mode,
            'who': {'takeProfit': who(c['agentTp']), 'stopLoss': who(c['agentSl']), 'trailing': who(trail != 'auto'), 'maxHold': who(c['agentMaxHold']), 'positionSize': who(c['agentSizePct']),
                    'seatCount': 'CREATOR OVERRIDE', 'entryStyle': who(c['agentEntry'] != 'agents'), 'exitStyle': who(mode != 'auto'), 'switching': who(c['agentSwitch'] != 'agents'),
                    'emptySeat': who(c['agentSeatTarget']), 'minAge': who(c['agentMinAgeH'])}, 'minAgeH': c['agentMinAgeH'],
            'hard': {'catastrophicStop': _ci.CATASTROPHIC_STOP, 'movesPerHour': _uni.CONTROL_MOVES_HR, 'minPool': _uni.CONTROL_MIN_LIQ}}


# the creator's controls as the page draws them: one row per control, its options (0 / 'agents' = AGENTS CHOOSE), who decides now,
# and — under AGENTS CHOOSE — what the agents are actually using right now (`now`, filled by the service from live state; None = not known)
OPTIONS = {'agentAuthority': list(AUTHORITY), 'agentTp': [0, *TP_OPTS], 'agentSl': [0, *SL_OPTS], 'agentTrail': list(TRAIL), 'agentTrailArm': [0, 5, 10, 15, 20, 30],
           'agentTrailPct': [0, 3, 5, 8, 10, 15], 'agentMaxHold': [0, *HOLD_OPTS], 'agentSizePct': [0, *SIZE_OPTS], 'agentSeatTarget': list(SEAT_TARGETS),
           'agentSwitch': ['agents', 'off', 'conservative', 'normal', 'aggressive'], 'agentEntry': list(ENTRY), 'agentMinAgeH': list(_uni.AGENT_MIN_AGES)}
CONTROLS = (('agentTp', 'takeProfit', 'Take profit', '%', 'AT your line the coin is banked. They may still leave earlier on a broken thesis or the trail.'),
            ('agentSl', 'stopLoss', 'Stop-loss', '%', 'Your most tolerated loss. Their own structure stop may be tighter, never wider.'),
            ('agentTrail', 'trailing', 'Trailing protection', None, 'off = no give-back protection · custom = arm at +A%, bank P points under the peak.'),
            ('agentMaxHold', 'maxHold', 'Max hold', 'min', 'The longest a coin is held. Their thesis windows may end it sooner, never later.'),
            ('agentSizePct', 'positionSize', 'Seat size cap', '% of card', 'The most of the card one seat may be. The Warden may size smaller, never larger.'),
            ('agentSwitch', 'switching', 'Switching', None, 'How much stronger a challenger must read, and how long a coin is held, before its seat is given up. A winner is never surrendered.'),
            ('agentEntry', 'entryStyle', 'Entry', None, 'agents = a full GO, or the duty\'s cleared case on an empty seat · go = a full GO only.'),
            ('agentSeatTarget', 'emptySeat', 'Empty-seat target', 's', 'How soon a cleared case may fill an empty seat (a full GO never waits).'),
            ('agentMinAgeH', 'minAge', 'Youngest coin', 'h', '0 = any age: a newborn is judged on the evidence it CAN have (real candles so far, tape, pool, holder scan). A number = no coin younger than that.'))


def controls(cfg, now=None):
    """→ [{key, who, label, unit, value, options, agentsNow, means}] for the creator controls panel. `now` = {control key: what the agents
    use right now under AGENTS CHOOSE, as words} — handed in by the service from its live state, never invented here."""
    c, pol = clean_policy(cfg), policy(cfg)
    return [{'key': k, 'who': pol['who'][w], 'label': lab, 'unit': unit, 'value': c[k], 'options': OPTIONS[k], 'agentsNow': (now or {}).get(k), 'means': means}
            for k, w, lab, unit, means in CONTROLS]


def agents_now(take, tunables, thesis=None):
    """What the agents use right now for each control under AGENTS CHOOSE, in words, from the live office (`take` = office.take_info,
    `tunables` = Reaper's / Warden's live values). Every value names where it comes from."""
    t = tunables or {}
    th = thesis or {}
    return {'agentTp': (f"learned scalp line +{_f(take.get('active')):g}% ({take.get('evidenceN')} paths)" if (take or {}).get('source') == 'learned'
                        else f"at +{_f((take or {}).get('base')):g}% they read it: clean + thesis not weak → runs under the trail, else banked"),
            'agentSl': f"each entry's structure stop (≥ {_ci.STOP_FLOOR:g}%), never past {_f(t.get('stopPct')):g}%" + (f" · now {th['stopPct']:g}% on ${th['sym']}" if th.get('stopPct') and th.get('sym') else ''),
            'agentTrail': f"arms at +{_f(t.get('protectAt')):g}%, banks after giving back {_f(t.get('giveBackPct')):g}% of the peak",
            'agentMaxHold': f"thesis windows: {_ci.MIN_WINDOWS * _ci.WINDOW_MIN}–{_ci.MAX_WINDOWS * _ci.WINDOW_MIN} min, earned 5 min at a time",
            'agentSizePct': f"the Warden: ≤ {_f(t.get('maxSeatPct')):g}% of the card, smaller on risk",
            'agentSwitch': f"read margin ≥ {SWITCH['agents'][0]:+.1f} after {SWITCH['agents'][1]:g} min, or a broken read after {_uni.CONTROL_HOLD_MIN} min",
            'agentEntry': 'a full GO at once, or the duty\'s cleared case',
            'agentSeatTarget': f'{SEAT_TARGET_AUTO}s',
            'agentMinAgeH': 'any age — stage-aware evidence (NEWBORN · EARLY · DEVELOPING · MATURE); safety, pool, scan and the chart still decide'}


# ── 🔌 RESTART / REFILL: a gap in OUR data is never evidence about a coin ───────────────────────────────────────────────────────────
READY_PASSES = 2          # full agent passes with a real board before discretionary exits come back
READY_MIN_COINS = 10      # … each reading at least this many coins
RADAR_GRACE_SEC = 180     # a coin must be missing from the agents' table this long (while LIVE) before "off their radar" means anything
STATES = ('OFFICE WARMING UP', 'POSITIONS RECONCILED', 'MARKET REFILLED', 'LIVE')


def ready(boot, now):
    """`boot` = {at, passes, coins, reconciled}: when this process started, how many agent passes have finished since, how many coins
    the last one read, whether the real card's positions were read back with a live price. → {state, live, steps, why}
    Until LIVE, Reaper and the seat manager may NOT use 'off their radar', a missing table row or elapsed time as a reason to exit.
    The hard protections never wait for it (catastrophic stop, the stop, the pool rule, the keeper's own halts)."""
    b = boot or {}
    rec = bool(b.get('reconciled'))
    refilled = int(_f(b.get('passes'))) >= READY_PASSES and int(_f(b.get('coins'))) >= READY_MIN_COINS
    state = STATES[3] if rec and refilled else STATES[2] if refilled else STATES[1] if rec else STATES[0]
    why = 'live' if state == STATES[3] else (f"{int(_f(b.get('passes')))} of {READY_PASSES} agent passes since the restart" + ('' if int(_f(b.get('coins'))) >= READY_MIN_COINS else f", {int(_f(b.get('coins')))} coins read (needs {READY_MIN_COINS})")
                                             + ('' if rec else ' · positions not read back yet'))
    return {'state': state, 'live': state == STATES[3], 'steps': [[STATES[0], True], [STATES[1], rec], [STATES[2], refilled], [STATES[3], rec and refilled]], 'why': why,
            'sinceSec': round(now - _f(b.get('at'))) if b.get('at') else None}


def radar_gone(off_since, now, live=True):
    """Is a held coin REALLY off the agents' radar? Only when the office is LIVE and the coin has been missing for RADAR_GRACE_SEC."""
    return bool(live and off_since and now - _f(off_since) >= RADAR_GRACE_SEC)


# ── 🪑 EMPTY SEATS ───────────────────────────────────────────────────────────────────────────────────────────────────────────────
FAILED_SEC = 6 * 3600     # a coin the agents left at a loss is not bought back for 6h (never the same failed thesis again)
CHECK_WORD = {'scan': 'holder scan', 'age': 'too young', 'pool': 'pool under $20K', 'burn': 'burned us', 'devil': 'Devil objects', 'chart': 'entry timing not ready', 'data': 'data not ENTER-grade'}


def blockers(cases):
    """Why the pass's case files did not clear: the FIRST failing check of each → [[check, word, count]] (most common first)."""
    cnt = {}
    for c in cases or []:
        if c.get('cleared'):
            continue
        k = next((k[0] for k in c.get('checks') or [] if not k[1]), 'unknown')
        cnt[k] = cnt.get(k, 0) + 1
    return [[k, CHECK_WORD.get(k, k), n] for k, n in sorted(cnt.items(), key=lambda kv: -kv[1])]


SEAT_CODES = ('FILLING', 'NO VALID ENTRY', 'NO CLEARED CANDIDATE', 'WAITING FOR CONFIRMATION', 'WAITING FOR SEAT TIMER', 'BUY BUDGET', 'NO CASH',
              'WARDEN VETO', 'COURIER BLOCK', 'CREATOR POLICY', 'REBUY COOLDOWN', 'DATA DEGRADED', 'OFFICE NOT LIVE', 'EXECUTION BLOCK', 'OTHER')
BLOCK_CODE = {'chart': 'WAITING FOR CONFIRMATION', 'data': 'DATA DEGRADED', 'burn': 'REBUY COOLDOWN'}   # every other failing check = NO CLEARED CANDIDATE


def seat_state(ctx):
    """One line of truth for the agents' empty seats. `ctx` = {want, held, cases (the pass's case files), go (eligible GO coins),
    valid (candidates that would be allowed to fill NOW), movesLeft, courier, manual, live, freeUsd, minUsd, emptySince, target, now,
    nextTickIn, control (Agent Control on), timerIn (seconds before a cleared case may take a seat; GO never waits), vetoed (valid coins
    the Warden vetoed this tick), halt (the keeper's halt word)}. → {state, code, empty, valid, reason, emptyFor, target, nextIn, late,
    blockers, seats: [{seat, code, reason}]} — EVERY empty seat carries exactly one primary reason code (`SEAT_CODES`).
    FILLING = a valid candidate exists and the next tier tick takes it · NO VALID ENTRY = nothing clears (cash is a valid position)."""
    c = ctx or {}
    want, held, now = int(_f(c.get('want'))), int(_f(c.get('held'))), _f(c.get('now'))
    empty = max(0, want - held)
    valid = list(c.get('valid') or [])
    bl = blockers(c.get('cases'))
    base = {'empty': empty, 'want': want, 'held': held, 'valid': len(valid), 'validSyms': [str(x.get('symbol')) for x in valid][:4], 'target': int(_f(c.get('target')) or SEAT_TARGET_AUTO), 'blockers': bl,
            'emptyFor': round(now - _f(c['emptySince'])) if empty and c.get('emptySince') else None, 'nextIn': None,
            'cleared': sum(1 for x in c.get('cases') or [] if x.get('cleared'))}

    def out(state, code, reason, n_fill=0, rest=None, **kw):
        rest = rest or (code, reason)
        seats = [{'seat': held + i + 1, 'code': 'FILLING' if i < n_fill else rest[0], 'reason': (f"${valid[i].get('symbol')} cleared — the next tick fills it" if i < n_fill else rest[1])} for i in range(empty)]
        return {**base, 'state': state, 'code': code, 'reason': reason, 'seats': seats, **kw}
    if not empty:
        return out('FULL', 'FULL', f'{held} of {want} seats held')
    if c.get('control') is False:
        return out('AGENT CONTROL OFF', 'CREATOR POLICY', c.get('offWhy') or 'Agent Control is OFF — the agents fill nothing (your switch)')
    if c.get('manual'):
        return out('CREATOR MANUAL', 'CREATOR POLICY', 'you hold the decisions — the agents fill nothing')
    if c.get('live') is False:   # 🔌 after a restart nothing discretionary happens until the office has refilled and read every position back
        return out('OFFICE WARMING UP', 'OFFICE NOT LIVE', f"waits for LIVE — {c.get('readyWhy') or 'the office is refilling after a restart'}")
    if c.get('halt'):
        return out('NO VALID ENTRY', 'EXECUTION BLOCK', f"EXECUTION BLOCK — the keeper is halted: {c.get('halt')}")
    if c.get('courier') == 'BAD':
        return out('NO VALID ENTRY', 'COURIER BLOCK', 'COURIER BLOCK — Courier reads execution BAD (an EXECUTION BLOCK until the keeper lands again)')
    if int(_f(c.get('movesLeft'))) <= 0:
        return out('NO VALID ENTRY', 'BUY BUDGET', f"BUY BUDGET — the hourly budget of {int(_f(c.get('movesHr')) or _uni.FILL_MOVES_HR)} empty-seat fills is used (a runaway guard)")
    if _f(c.get('freeUsd')) < max(0.05, _f(c.get('minUsd'))):
        return out('NO VALID ENTRY', 'NO CASH', f"NO CASH — ${_f(c.get('freeUsd')):.2f} free card cash")
    n = len(c.get('cases') or [])
    first = bl[0] if bl else None
    why = 'no coin has a positive read this pass' if not n else f"0 of {n} case files clear — " + ', '.join(f'{w} ({k})' for _, w, k in bl[:3])
    rest = ('NO VALID ENTRY', why) if not n else (BLOCK_CODE.get(first[0], 'NO CLEARED CANDIDATE') if first else 'NO CLEARED CANDIDATE', why)
    if c.get('moved') and not valid:   # ⚡ cleared on the last read, but the newest price / chart says not now
        why = 'cleared, then moved since the read: ' + '; '.join(f"${x.get('symbol')} {x.get('why')}" for x in list(c['moved'])[:2])
        rest = ('WAITING FOR CONFIRMATION', why)
    if c.get('cooled'):   # the case files that DID clear all left the card lately (cooldown / a thesis that failed on real money)
        why = f"cleared but on the rebuy cooldown: {', '.join('$' + str(x) for x in list(c['cooled'])[:3])}" + (f' · {why}' if n else '')
        rest = ('REBUY COOLDOWN', why)
    if valid:
        k = min(len(valid), empty)
        if n and rest[0] != 'REBUY COOLDOWN':   # the seats a valid coin does not cover: no OTHER coin cleared
            rest = (rest[0], "no other coin cleared — " + ', '.join(f'{w} ({kk})' for _, w, kk in bl[:3]) if bl else 'no other coin cleared')
        if c.get('vetoed') and int(_f(c.get('vetoed'))) >= len(valid):
            return out('NO VALID ENTRY', 'WARDEN VETO', f"WARDEN VETO — the Warden vetoed {', '.join('$' + str(x.get('symbol')) for x in valid[:3])}")
        if not any(x.get('go') for x in valid) and _f(c.get('timerIn')) > 0:
            return out('FILLING', 'WAITING FOR SEAT TIMER', f"${valid[0].get('symbol')} cleared — the seat target lets it in {round(_f(c['timerIn']))}s", rest=('WAITING FOR SEAT TIMER', f"cleared case waits {round(_f(c['timerIn']))}s for the seat target"), nextIn=round(_f(c['timerIn'])))
        late = base['emptyFor'] is not None and base['emptyFor'] > base['target']
        return out('FILLING', 'FILLING', f"${valid[0].get('symbol')} cleared every desk — the next tick fills the seat", n_fill=k, rest=rest,
                   nextIn=max(0, round(_f(c.get('nextTickIn')))) if c.get('nextTickIn') is not None else None, late=late)
    return out('NO VALID ENTRY', rest[0], rest[1])






# ── 🧮 THE HOURLY BUY BUDGET COUNTS REAL BUYS ──────────────────────────────────────────────────────────────────────────────────────
BUY_LAND_SEC = 180     # a seat filled this recently may still be landing its buy: it counts until the ledger says otherwise


def note_lost(lost, closed, now):
    """🔁 NO SAME COIN AGAIN: every CONFIRMED agent exit that did not make money (real result ≤ 0) puts the coin on the 6h "lost"
    list — whatever rule sold it (stop, swap, flow exit, thesis, time, "left by another rule"). Only the desk's own pull wrote it
    before, so $DOTF came back 4× and $UDR / $SARP 3× in a day. → {mint: at} (entries older than FAILED_SEC dropped)"""
    out = {m: a for m, a in (lost or {}).items() if now - _f(a) < FAILED_SEC}
    for p in closed or []:
        r = p.get('realPct')
        if p.get('confirmed') and p.get('mint') and r is not None and _f(r) <= 0:
            out[p['mint']] = _f(p.get('closedAt')) or now
    return out


def real_buys(events, ledger, card, now, window=3600.0, moves=('fill', 'swap')):
    """How many of the agents' fills / switches in the last hour were REAL buys (`CONTROL_MOVES_HR` is "6 real buys an hour"): a move counts
    when the keeper's ledger has a FILLED buy of that coin for this card at / after it, or while its buy may still be landing
    (≤ BUY_LAND_SEC); a move whose coin never got a buy (the seat went back to cash) is not a buy. A move without a coin id counts (safe side).
    2026-10-11: two seats filled in the first tick after a restart never bought anything and still used 2 of the 6 — the card sat at 2/4
    with "buy budget used" while 4 real buys had happened."""
    t0 = _f(now) - window
    filled = {}
    for r in reversed(ledger or []):
        if _f(r.get('at')) < t0 - 60:
            break
        if r.get('card') == card and r.get('side') == 'buy' and r.get('status') == 'filled' and r.get('mint'):
            filled.setdefault(r['mint'], []).append(_f(r.get('at')))
    n = 0
    for e in events or []:
        if e.get('kind') != 'agent' or e.get('move') not in moves or _f(e.get('at')) < t0:
            continue
        m, at = e.get('mint'), _f(e.get('at'))
        if not m or any(x >= at - 5 for x in filled.get(m, ())) or _f(now) - at <= BUY_LAND_SEC:
            n += 1
    return n


NEAR_PATIENCE_SEC = 10       # a seat empty this long with NOTHING cleared takes the best near-ready coin (owner: "30 secs to choose") …
NEAR_MIN_ENTRY = 50.0        # 🎯 … AND an entry score (opportunity.score) of at least B-tier — never 'the least bad coin'
NEAR_MIN_SCORE = 15.0        # … scoring at least this (seat_ops.score WITHOUT its phase tilt — the tilt orders coins, it never keeps a seat empty) …
NEAR_SOFT = ('chart', 'data')   # … whose ONLY open checks are the entry moment / ENTER-grade data — every safety check passed




def cycle_due(pol, last_at, now):
    """🔁 THE ACTIVE CYCLE: every creator seat target (60s on the real card; never under 30s) the desk re-evaluates EVERY seat — empty seats
    look for a fill, held seats are compared with the best cleared challenger (`switch_test`). A due cycle is a DECISION (keep · protect ·
    take · exit · switch · fill · cash), never a forced trade: the superiority test, the Warden and the hourly buy budget still decide."""
    return _f(now) - _f(last_at) >= max(30.0, _f((pol or {}).get('seatTarget') or SEAT_TARGET_AUTO))




# ── 🚀 LAUNCH CONTEXT: only what is measurable ───────────────────────────────────────────────────────────────────────────────────
PADS = {'pump': 'Pump.fun', 'bonk': 'LetsBONK'}      # the launchpads whose mints carry their own suffix — the ONLY pads identified today
ESTABLISHED_H = 7 * 24.0
TYPES = ('bonding curve', 'migrated', 'established pool', 'unknown')
LAUNCH_RISK = {'unknown': 0.5, 'bonding curve': 0.5}    # 🛡 Warden: a seat in an unknown / pre-graduation launch is at most half size


def launch_context(row):
    """What FEELESS can MEASURE about how this coin launched, from the row the desks already hold (no fetch):
      pad    Pump.fun / LetsBONK from the mint's own suffix — anything else is UNKNOWN (Raydium / Meteora / Moonshot origin is not in
             the data the desks get, so it is not claimed)
      type   bonding curve (still on its launch curve) · migrated (a known pad's coin trading in a pool) · established pool (unknown
             origin, ≥ 7 days old) · unknown
    Fields that are not measured are None — never a guess. → dict"""
    r = row or {}
    v = r.get('vitals') or {}
    g = lambda k: r.get(k) if r.get(k) is not None else v.get(k)
    mint = str(r.get('mint') or '')
    pad_k = next((k for k in PADS if mint.endswith(k)), None)
    curve, age = g('curve'), g('ageH')
    if curve is True:
        typ = 'bonding curve'
    elif pad_k and curve is False:
        typ = 'migrated'
    elif not pad_k and age is not None and _f(age) >= ESTABLISHED_H:
        typ = 'established pool'
    else:
        typ = 'unknown'
    return {'pad': PADS.get(pad_k) if pad_k else 'UNKNOWN', 'padKey': pad_k or 'unknown', 'type': typ, 'key': f"{pad_k or 'unknown'}:{typ}", 'measured': curve is not None,
            'graduated': None if curve is None or not pad_k else (curve is False), 'curvePct': r.get('curvePct') if curve else None, 'ageH': age, 'poolAgeH': age if curve is False else None,
            'liq': g('liq') or None, 'mcap': g('mcap') or None, 'top10': g('top10'), 'dev': g('dev'), 'holders': g('holders'), 'txns1h': g('txns1h'), 'buyShare': g('buyShare'),
            'notMeasured': ['initial liquidity', 'initial market cap', 'migration time', 'supply'], 'source': 'mint suffix + the launch board row (curve flag, pool age)'}


def launch_gate(launch, lean, bar):
    """⏱ Trigger's stricter confidence for a MEASURED but UNKNOWN launch mechanism: an ENTER needs lean ≥ bar + PAD_UNKNOWN_BAR.
    → None (no change) or the WAIT reason. It can only turn an ENTER into a WAIT — never the other way, never on an unmeasured row."""
    ln = launch or {}
    need = _f(bar) + _pd.PAD_UNKNOWN_BAR
    if ln.get('type') == 'unknown' and ln.get('measured') and _f(lean) < need:
        return f"unknown launch context — needs lean {need:.2f}, has {_f(lean):+.1f}"
    return None


def pad_record(judged, min_n=5):
    """Each launch context on ITS OWN record: every judged call that stored its context (`pad`), result at 5 and 15 minutes.
    → {key: {n, med5, med15, won}} — `known` False under `min_n` (shown as "too few", never as a verdict)."""
    by = {}
    for d in judged or []:
        if d.get('pad') and d.get('p5') is not None:
            by.setdefault(d['pad'], []).append(d)
    return {k: {'n': len(v), 'med5': _med([_f(x['p5']) for x in v]), 'med15': _med([_f(x['p15']) for x in v if x.get('p15') is not None]),
                'won': round(sum(1 for x in v if _f(x['p5']) > 0) / len(v) * 100), 'known': len(v) >= min_n,
                'enterN': sum(1 for x in v if x.get('kind') == 'enter'), 'enterMed5': _med([_f(x['p5']) for x in v if x.get('kind') == 'enter'])} for k, v in by.items()}


# ── 🔎 THE WINNERS WE MISSED (paper only) ────────────────────────────────────────────────────────────────────────────────────────
WINNER_PCT = 50.0          # a coin that peaked this far above where the board first watched it, inside its watched hour
LOOKBACK_SEC = 6 * 3600
MISSED_KEEP = 240
LATE_1H = 100.0            # first seen already +100% on the hour = discovered too late
HORIZONS = (5, 10, 15, 30, 60)
REASONS = ('NEVER DISCOVERED', 'DISCOVERED TOO LATE', 'BAD DATA', 'WAITED TOO LONG', 'TRIGGER MISSED ENTRY', 'DEVIL OBJECTION', 'WARDEN ZEROED IT', 'LIQUIDITY RULE', 'AGE RULE', 'HOLDER RULE',
           'LAUNCHPAD RULE', 'NO SEAT', 'NO CASH', 'EXECUTION BLOCK', 'CREATOR POLICY', 'NO POSITIVE READ', 'CORRECT SKIP — UNTRADEABLE / UNSAFE', 'UNKNOWN')
WHO = {'BAD DATA': 'tally', 'NO POSITIVE READ': 'sherlock', 'WAITED TOO LONG': 'trigger', 'TRIGGER MISSED ENTRY': 'trigger', 'DEVIL OBJECTION': 'devil', 'WARDEN ZEROED IT': 'warden',
       'EXECUTION BLOCK': 'courier', 'LIQUIDITY RULE': 'trigger', 'AGE RULE': 'devil', 'HOLDER RULE': 'sherlock', 'CORRECT SKIP — UNTRADEABLE / UNSAFE': 'devil'}
SAFE_RULES = ('rug_meter', 'busted_read', 'data_integrity', 'rug_signs', 'avoid')     # Devil rules whose block stays right even when the coin pumped


def _outs(case):
    o = (case or {}).get('out') or {}
    return {f'p{h}': o.get(f'p{h}') for h in HORIZONS if o.get(f'p{h}') is not None}


def classify_miss(first, cases, seen, held=False):
    """WHY a winner was not held, from what was on file AT THE TIME. `first` = the first case file the Archivist holds for it (or
    None), `cases` = all of them in time order, `seen` = Tally's stamp for it when no case exists ({call, why, lean, c1} or None).
    → (reason, who, rule, correct) — `correct` = the block was still right from a risk view (never "it pumped, so it was wrong")."""
    if held:
        return 'HELD', None, None, None
    if not first:
        if not seen:
            return 'NEVER DISCOVERED', None, None, None
        why = str(seen.get('why') or '')
        if seen.get('call') == 'skip':
            if 'scan' in why:
                return 'CORRECT SKIP — UNTRADEABLE / UNSAFE', 'trigger', 'failed holder scan', True
            if 'pool' in why or '$20K' in why:
                return 'LIQUIDITY RULE', 'trigger', 'pool under $20K', True
            if 'candle' in why or '+15%' in why or 'E2' in why or 'PARABOLIC' in why:
                return 'TRIGGER MISSED ENTRY', 'trigger', 'no chasing a vertical candle', None
            return 'TRIGGER MISSED ENTRY', 'trigger', why[:60] or 'SKIP', None
        if _f(seen.get('lean')) <= 0:
            return 'NO POSITIVE READ', 'sherlock', f"lean {_f(seen.get('lean')):+.1f}", None
        return 'WAITED TOO LONG', 'trigger', why[:60] or 'WAIT', None
    d = first['d']
    blocked = list(d.get('blocked') or [])
    dv = d.get('devil') or ['—', []]
    rules = [str(x) for x in (dv[1] if len(dv) > 1 and isinstance(dv[1], list) else [])]
    data = (d.get('data') or {}).get('state')
    late = _f((d.get('tally') or {}).get('c1')) >= LATE_1H or any(r in ('ran', 'chart_late', 'chart_parabolic') for r in rules)
    if 'young' in rules and 'age' not in blocked:
        blocked.append('age')
    if data in _md.READ_FAIL:
        return 'BAD DATA', 'tally', f'data {data}', True
    if 'scan' in blocked and d.get('scanFailed'):
        return 'CORRECT SKIP — UNTRADEABLE / UNSAFE', 'sherlock', 'failed holder scan', True
    if any(r in SAFE_RULES for r in rules):
        return 'CORRECT SKIP — UNTRADEABLE / UNSAFE', 'devil', next(r for r in rules if r in SAFE_RULES), True
    if 'pool' in blocked:
        return ('LAUNCHPAD RULE' if (d.get('launch') or {}).get('type') == 'bonding curve' else 'LIQUIDITY RULE'), 'trigger', 'pool under $20K' + (' (still on its launch curve)' if (d.get('launch') or {}).get('type') == 'bonding curve' else ''), True
    if 'age' in blocked:
        return 'AGE RULE', 'devil', f"{_f(d.get('ageH')):.1f}h old" if d.get('ageH') is not None else 'age unknown', None
    if 'scan' in blocked:
        return 'HOLDER RULE', 'sherlock', 'holders not scanned in time', None
    if late:
        return 'DISCOVERED TOO LATE', 'tally', 'most of the move was already in when it was first read', None
    if 'burn' in blocked:
        return 'CREATOR POLICY', 'devil', 'burned us in the last 6h', None
    if 'devil' in blocked:
        soft = next((r for r in rules if r not in ('unscanned', 'young', 'ran', 'burned')), rules[0] if rules else 'objection')
        return 'DEVIL OBJECTION', 'devil', soft, False if not _pd.DEVIL_RULES.get(soft, (True,))[0] else None
    if 'data' in blocked and 'chart' not in blocked:
        return 'BAD DATA', 'tally', f'data {data or "not ENTER-grade"}', None
    if 'chart' in blocked or 'data' in blocked:
        ce = ((d.get('chart') or {}).get('entry') or [''])[0]
        return ('WAITED TOO LONG' if str(ce).startswith('WAIT') else 'TRIGGER MISSED ENTRY'), 'trigger', ((d.get('chart') or {}).get('entry') or ['', ''])[1] or ce or 'entry timing', None
    # it CLEARED: why was it not on the card?
    wd, act = d.get('warden'), d.get('action')
    if d.get('courier') == 'BAD':
        return 'EXECUTION BLOCK', 'courier', 'execution BAD', True
    if wd and _f(wd.get('allowed')) <= 0:
        return 'WARDEN ZEROED IT', 'warden', str(wd.get('rule')), None
    why = str(d.get('noFill') or '')
    if why:
        return ('NO CASH' if 'CASH' in why else 'NO SEAT' if 'FULL' in why or 'seat' in why else 'CREATOR POLICY' if 'MANUAL' in why or 'budget' in why else 'UNKNOWN'), None, why[:80], None
    return ('UNKNOWN' if act else 'NO SEAT'), None, 'cleared, not filled', None


def counterfactual(cases):
    """PAPER results of three entries the office COULD have made, read only from prices already settled on the case files (5 / 10 / 15 /
    30 / 60 minutes after each): at the first clear · at the first valid pullback · at the first confirmed breakout. None = no such
    moment on file. Nothing here can place, size or time a trade."""
    first = lambda pred: next((c for c in cases or [] if pred(c['d'])), None)
    pick = {'firstCleared': first(lambda d: d.get('cleared')),
            'firstPullback': first(lambda d: (d.get('chart') or {}).get('state') == 'PULLBACK IN UPTREND' and ((d.get('chart') or {}).get('entry') or [''])[0] == 'ENTER NOW'),
            'confirmedBreakout': first(lambda d: (d.get('chart') or {}).get('state') == 'CONFIRMED BREAKOUT')}
    return {k: None if not c else {'at': c['at'], **_outs(c)} for k, c in pick.items()}


def missed_winners(arch, brain_done, series, now, held=(), since=0.0, first_seen=None):
    """🔎 File an autopsy for every coin the board watched for an hour that peaked ≥ WINNER_PCT and that the card did not hold. Inputs
    are things ALREADY on disk / in memory: the brain's settled watch list (peak, the time each level was crossed), the Archivist's
    case files (what every desk said, hash-chained) and Tally's own tape stamps. `since` = only winners settled after this.
    → (archive with `missed` appended + bounded, new autopsies)"""
    a = dict(arch or {})
    have = {(m.get('mint'), int(_f(m.get('settledAt')))) for m in a.get('missed') or []}
    by = {}
    for c in a.get('cases') or []:
        by.setdefault(c['d'].get('mint'), []).append(c)
    new = []
    for d in brain_done or []:
        at = _f(d.get('at'))
        if at <= since or now - at > LOOKBACK_SEC or _f(d.get('peak')) < WINNER_PCT or (d.get('mint'), int(at)) in have:
            continue
        m = d['mint']
        start = at - 3600
        x = d.get('x') or {}
        hit = min((_f(t) for lv, t in x.items() if _f(lv) >= WINNER_PCT and t is not None and _f(t) > 0), default=None)   # a level never crossed is not a time
        cs = [c for c in by.get(m, []) if start - 1800 <= _f(c['at']) <= at]
        first = cs[0] if cs else None
        stamp = next((p for p in (series or {}).get(m) or [] if p.get('c')), None)
        fs_ = (first_seen or {}).get(m)
        if fs_ and (not stamp or _f(fs_.get('t')) < _f(stamp.get('t'))):   # the first stamp the desk kept past the tape's eviction is earlier
            stamp = fs_
        seen = None if not stamp else {'call': {'s': 'skip', 'w': 'wait', 'e': 'enter'}.get(stamp.get('c')), 'why': stamp.get('r'), 'lean': stamp.get('l'), 'at': stamp.get('t')}
        reason, who, rule, correct = classify_miss(first, cs, seen, m in (held or ()))
        if reason == 'HELD':
            continue
        fd = (first or {}).get('d') or {}
        seen_at = _f((first or {}).get('at')) or _f((seen or {}).get('at')) or None
        rec = {'mint': m, 'sym': d.get('sym'), 'settledAt': at, 'watchedFrom': start, 'peak': _f(d.get('peak')), 'end': _f(d.get('end')), 'gone': bool(d.get('gone')), 'hitAt': hit,
               'seen': bool(first or seen), 'seenAt': seen_at, 'leadMin': round((hit - seen_at) / 60, 1) if hit and seen_at else None,
               'reason': reason, 'who': who or WHO.get(reason), 'rule': rule, 'correct': correct, 'launch': fd.get('launch') or None,
               'desks': None if not first else {'tally': fd.get('tally'), 'data': (fd.get('data') or {}).get('state'), 'sherlock': fd.get('sherlock'), 'weather': (fd.get('weather') or {}).get('regime'),
                                               'trigger': fd.get('trigger'), 'devil': fd.get('devil'), 'warden': fd.get('warden'), 'courier': fd.get('courier'), 'blocked': fd.get('blocked')},
               'tape': seen if not first else None, 'counter': counterfactual(cs), 'cases': len(cs), 'feats': list(d.get('f') or [])[:8]}
        new.append(rec)
    if new:
        a['missed'] = (list(a.get('missed') or []) + new)[-MISSED_KEEP:]
    return a, new


def missed_summary(arch, now, n=12):
    """👨‍⚖️ The Judge's aggregate over the last 6h of autopsies: by reason, by blocking desk, by rule, the typical move missed, the
    typical head start we had, how many blocks were still right, and the paper counterfactuals. Counts are counts; nothing is weakened."""
    ms = [m for m in (arch or {}).get('missed') or [] if now - _f(m.get('settledAt')) <= LOOKBACK_SEC]
    cnt = lambda key: sorted(({'key': k, 'n': n_, 'medPeak': _med([_f(m['peak']) for m in ms if (m.get(key) or '—') == k])} for k, n_ in
                              {k: sum(1 for m in ms if (m.get(key) or '—') == k) for k in {(m.get(key) or '—') for m in ms}}.items()), key=lambda r: -r['n'])
    cf = {}
    for k in ('firstCleared', 'firstPullback', 'confirmedBreakout'):
        rows = [m['counter'][k] for m in ms if (m.get('counter') or {}).get(k)]
        cf[k] = {'n': len(rows), **{f'p{h}': _med([r.get(f'p{h}') for r in rows]) for h in HORIZONS}}
    return {'n': len(ms), 'hours': LOOKBACK_SEC / 3600, 'winnerPct': WINNER_PCT, 'medPeak': _med([_f(m['peak']) for m in ms]), 'medLeadMin': _med([m.get('leadMin') for m in ms]),
            'seen': sum(1 for m in ms if m.get('seen')), 'never': sum(1 for m in ms if not m.get('seen')), 'correct': sum(1 for m in ms if m.get('correct') is True),
            'falseBlock': sum(1 for m in ms if m.get('correct') is False), 'byReason': cnt('reason'), 'byAgent': cnt('who'), 'byRule': [r for r in cnt('rule') if r['key'] != '—'][:8],
            'counter': cf, 'items': sorted(ms, key=lambda m: -_f(m['peak']))[:n],
            'note': 'A block that kept the card out of an unsafe coin stays right even when the coin pumped. Nothing here loosens a rule: a change still needs evidence → Judge → shadow test → promotion.'}


# ── 📝 THE CREATOR'S REVIEW QUEUE (read-only for the office) ─────────────────────────────────────────────────────────────────────
REVIEW = ('missed', 'launchpad', 'entry', 'exit', 'vetoes', 'risk', 'data', 'rules')
REVIEW_LABEL = {'missed': 'MISSED WINNERS', 'launchpad': 'LAUNCHPAD LESSONS', 'entry': 'ENTRY MISTAKES', 'exit': 'EXIT MISTAKES', 'vetoes': 'FALSE VETOES', 'risk': 'RISK LESSONS',
                'data': 'DATA QUALITY', 'rules': 'RULE PROPOSALS'}


MARKS = ('agree', 'disagree', 'seen')     # the creator's mark on a review item — kept for the page only: no desk ever reads it
MARKS_KEEP = 300


def item_key(cat, it):
    """A stable id for one review item (the same coin / context / time → the same key pass after pass)."""
    return f"{cat}:{it.get('mint') or it.get('launch') or it.get('rule') or it.get('sym') or '-'}:{int(_f(it.get('at')))}"


def mark_review(marks, key, mark, note, now):
    """The creator marks a review item (agree · disagree · seen, with an optional note ≤ 280 chars). → new marks dict, bounded.
    Unknown mark → ValueError. 'clear' removes the mark. This is display state: the office never reads it back."""
    m = dict(marks or {})
    k = str(key or '')[:160]
    if not k:
        raise ValueError('No review item.')
    if mark == 'clear':
        m.pop(k, None)
        return m
    if mark not in MARKS:
        raise ValueError('Mark must be agree, disagree or seen.')
    m[k] = {'mark': mark, 'note': str(note or '')[:280], 'at': round(_f(now))}
    if len(m) > MARKS_KEEP:
        m = dict(sorted(m.items(), key=lambda kv: _f(kv[1].get('at')))[-MARKS_KEEP:])
    return m


def review(state, arch, office, now, n=8, marks=None):
    """📝 Everything waiting for the creator's eyes, by category. It is BUILT from the records and only ever READ by the page — no desk
    reads it back, nothing waits on it being opened or marked. Each item: coin · launch · time · move · what happened · what the office
    knew · which agent / rule mattered · counterfactual where one exists · the lesson · the evidence count · the creator's mark."""
    js = [d for d in _pd._judged(state or {}, 5) if now - _f(d.get('at')) <= LOOKBACK_SEC]
    ms = missed_summary(arch, now, n)
    item = lambda d, what, agent, rule, lesson, move=None: {'sym': d.get('sym'), 'mint': d.get('mint'), 'launch': d.get('pad'), 'at': d.get('at'), 'move': _f(d.get('p5')) if move is None else move, 'what': what,
                                                            'knew': {'lean': d.get('lean'), 'structure': d.get('cs'), 'entry': d.get('ce'), 'data': d.get('dq'), 'drivers': (d.get('drivers') or [])[:4]}, 'agent': agent, 'rule': rule,
                                                            'lesson': lesson, 'p15': d.get('p15'), 'p60': d.get('p60')}
    ent = [d for d in js if d.get('kind') == 'enter']
    entry = [item(d, f"ENTER, {_f(d['p5']):+.1f}% at 5 min", 'trigger', d.get('ce') or 'bar', 'entered a move that was already ending' if d.get('cs') in ('PARABOLIC', 'DISTRIBUTION') else 'the read did not hold for 5 minutes')
             for d in sorted(ent, key=lambda d: _f(d['p5'])) if _f(d['p5']) <= -10][:n]
    vet = [item(d, f"Devil objected, it ran {_f(d['p5']):+.1f}% in 5 min", 'devil', d.get('devilRule') or d.get('devilWhy'), 'this objection blocked a winner — its own record decides whether it keeps standing')
           for d in sorted(ent, key=lambda d: -_f(d['p5'])) if d.get('devil') == 'object' and _f(d['p5']) >= 10][:n]
    dq = [item(d, f"data {d.get('dq')} at the call", 'tally', d.get('dq'), 'nothing was entered on it' if d.get('kind') != 'enter' else 'ENTERED on data that was not ENTER-grade')
          for d in js if d.get('dq') and d['dq'] in _md.READ_FAIL][-n:]
    pos = [p for p in (arch or {}).get('positions') or [] if now - _f(p.get('closedAt')) <= 4 * LOOKBACK_SEC]
    exits = [{'sym': p.get('sym'), 'mint': p.get('mint'), 'at': p.get('closedAt'), 'move': p.get('realPct'), 'what': f"{p.get('rule')} at {_f(p.get('realPct')):+.1f}% after peaking {_f(p.get('peak')):+.1f}%" if p.get('confirmed') else f"{p.get('rule')} — exit NOT confirmed on the ledger",
              'agent': 'reaper', 'rule': p.get('rule'), 'knew': {'structure': (p.get('thesis') or {}).get('structure'), 'data': ((p.get('thesis') or {}).get('data') or {}).get('state')},
              'lesson': f"gave back {_f(p.get('peak')) - _f(p.get('realPct')):.1f} points from the peak" if _f(p.get('peak')) - _f(p.get('realPct')) >= 5 else 'left near its peak', 'launch': (p.get('launch') or {}).get('key')}
             for p in pos if p.get('confirmed') and p.get('realPct') is not None and (_f(p.get('peak')) - _f(p.get('realPct')) >= 5 or _f(p.get('realPct')) <= -10)][-n:]
    wl = (office or {}).get('wardenLog') or []
    risk = [{'sym': w.get('sym'), 'at': w.get('at'), 'move': None, 'what': f"{w.get('move')} ${_f(w.get('req')):.2f} → ${_f(w.get('allowed')):.2f}", 'agent': 'warden', 'rule': w.get('rule'), 'lesson': w.get('why')}
            for w in wl if _f(w.get('allowed')) < _f(w.get('req'))][-n:]
    pads = pad_record(_pd._judged(state or {}, 5))
    launch = [{'sym': None, 'launch': k, 'at': None, 'move': v['med5'], 'what': f"{v['n']} judged calls · typical {v['med5']:+.1f}% at 5 min" + (f" · {v['med15']:+.1f}% at 15" if v.get('med15') is not None else '') + f" · {v['won']}% up",
               'agent': 'judge', 'rule': 'launch context record', 'lesson': 'too few to read' if not v['known'] else 'this context loses on our calls' if _f(v['med5']) < 0 else 'this context holds up on our calls', 'n': v['n']}
              for k, v in sorted(pads.items(), key=lambda kv: -kv[1]['n'])][:n]
    rules = [{'sym': None, 'at': c.get('at'), 'move': None, 'what': f"{c.get('agent')}.{c.get('key')} {c.get('from')} → {c.get('to')}", 'agent': 'judge', 'rule': c.get('status'), 'lesson': str(c.get('why') or '')[:160],
              'n': len(c.get('shadow') or [])} for c in sorted(((office or {}).get('candidates') or {}).values(), key=lambda c: -_f(c.get('at')))][:n]
    miss = [{'sym': m.get('sym'), 'mint': m.get('mint'), 'launch': (m.get('launch') or {}).get('key'), 'at': m.get('settledAt'), 'move': m.get('peak'),
             'what': (f"seen {m['leadMin']:.0f} min before it crossed +{WINNER_PCT:g}%" if m.get('leadMin') is not None and m['leadMin'] > 0 else 'seen only after the move' if m.get('seen') else 'never discovered'),
             'agent': m.get('who'), 'rule': m.get('rule'), 'reason': m.get('reason'), 'correct': m.get('correct'), 'knew': m.get('desks') or m.get('tape'), 'counter': m.get('counter'),
             'lesson': 'correct skip — the block stays' if m.get('correct') is True else 'a block to re-examine on its own record' if m.get('correct') is False else 'an opportunity cost, not proof a rule is wrong'} for m in ms['items']]
    cats = {'missed': miss, 'launchpad': launch, 'entry': entry, 'exit': exits, 'vetoes': vet, 'risk': risk, 'data': dq, 'rules': rules}
    mk = marks or {}
    for cat, its in cats.items():
        for it in its:
            it['key'] = item_key(cat, it)
            it['mark'] = mk.get(it['key'])
    return {'at': now, 'order': list(REVIEW), 'labels': REVIEW_LABEL, 'counts': {k: len(v) for k, v in cats.items()}, 'open': {k: sum(1 for it in v if not it.get('mark')) for k, v in cats.items()},
            'items': cats, 'missedSummary': {k: v for k, v in ms.items() if k != 'items'}, 'marks': list(MARKS),
            'blocking': False, 'note': 'Review is asynchronous: the office never reads this queue (or your marks) back and never waits on it — the agents keep working while items wait.'}


# ── ⏱ SPEED: where the process loses time ────────────────────────────────────────────────────────────────────────────────────────
SPEED_KEEP = 60


def speed_note(sp, key, sec):
    """Append one measured duration (seconds) to a bounded list. → speed dict"""
    s = dict(sp or {})
    s[key] = (list(s.get(key) or []) + [round(_f(sec), 1)])[-SPEED_KEEP:]
    return s


def speed_view(sp):
    """Median / average / max of each measured stretch (None when nothing was measured yet — never a 0)."""
    out = {}
    for k in ('seatEmpty', 'validToFill', 'exitToFill'):
        xs = [x for x in (sp or {}).get(k) or [] if x is not None]
        out[k] = {'n': len(xs), 'med': _med(xs), 'avg': round(sum(xs) / len(xs), 1) if xs else None, 'max': max(xs) if xs else None}
    return out


# ── 🩺 LIVE OPERATION HEALTH: one compact line that says why the agents are or are not filling seats ──────────────────────────────
def ops(ready_, seat, courier, keeper, moves_hr=None):
    """→ {office, keeper, openSeats, valid, cleared, nextIn, block, code, execution, budget, cash}. Pure: every field is read from
    state the office already holds (no fetch). execution = BLOCKED (keeper halted / Courier BAD) · DEGRADED · HEALTHY."""
    s, r = seat or {}, ready_ or {}
    code = s.get('code') or ''
    halted = code == 'EXECUTION BLOCK'
    h = (courier or {}).get('health')
    ex = 'BLOCKED' if halted or h == 'BAD' else 'DEGRADED' if h == 'DEGRADED' else 'HEALTHY' if h == 'HEALTHY' else 'UNKNOWN'
    return {'office': 'LIVE' if r.get('live') else 'WARMING', 'keeper': '1 active' if keeper else 'NOT THIS PROCESS',
            'openSeats': int(_f(s.get('empty'))), 'valid': int(_f(s.get('valid'))), 'cleared': int(_f(s.get('cleared'))),
            'nextIn': s.get('nextIn'), 'block': None if not s.get('empty') or code == 'FILLING' else s.get('reason'), 'code': code or None,
            'execution': ex, 'budget': {'left': s.get('movesLeft'), 'of': moves_hr if moves_hr is not None else _uni.CONTROL_MOVES_HR},
            'cash': s.get('freeUsd')}


# ── 🕸 INTAKE: the full board, cheaply screened, with reserved room for what matters NOW ─────────────────────────────────────────────
INTAKE_MAX = 300
INTAKE_SLOTS = (('recheck', None), ('fresh', 60), ('new', 40), ('accel', 25), ('grad', 20), ('momentum', 25), ('outlets', 30), ('busy', 60), ('listed', 40))
GRAD_AGE_H = 6.0     # a pool younger than this that is off its launch curve = a recent graduation


def _pace(r):
    v1 = _f(r.get('vol1h'))
    return _f(r.get('vol5m')) * 12 / v1 if v1 > 0 else 0.0


OLD_INTAKE_H = 6.0    # 🆕 a coin older than this (the 6h new-entry universe) joins the table only as a recheck of something held


def stale_old(r):
    """A board row over 12h old that is NOT waking up (pace ≥ 2× its hour on ≥ $3K in 5 min, or a +5% 5-min move on ≥ $2K, or a fresh
    graduation) — it gives its intake slot to a fresh launch (owner, 2026-10-11: 0–12h coins must dominate)."""
    h = r.get('ageH')
    if h is None or _f(h) <= OLD_INTAKE_H:
        return False
    v5 = _f(r.get('vol5m'))
    return not ((v5 >= 3000 and _pace(r) >= 2) or (v5 >= 2000 and _f(r.get('chg5m')) >= 5))


def fresh_key(r):
    """Order inside a slot: the freshness ladder first (0–5m · 5–15m · 15–60m · 1–3h · 3–6h · 6h+), then the slot's own measure."""
    h = r.get('ageH')
    if h is None:
        return 6
    m = _f(h) * 60
    return 0 if m < 5 else 1 if m < 15 else 2 if m < 60 else 3 if m < 180 else 4 if m < 360 else 5


def intake(rows, recheck=(), listed=None, cap=INTAKE_MAX, cool=(), fresh=None, outlets=None):
    """→ the coins Tally reads this pass, each with `intake` = the reasons it got a seat at the table (deduped, ≤ cap).
    Reserved, in this order: RECHECK (held coins + last pass's cases + challengers — always) · NEW (the youngest launches the board has,
    ANY age: a coin seconds old reaches Tally on the next pass) · ACCEL (5-min volume pace vs its hour) · GRAD (off the curve, pool < 6h) ·
    MOMENTUM (5-min move on ≥ $2K) · BUSY (front-runners) · LISTED (on the most tracked lists). Cheap: board numbers only, no fetch."""
    by = {r['mint']: r for r in rows or [] if r.get('mint')}
    rs = [r for r in by.values() if not stale_old(r)]   # recheck still reads every held coin / case whatever its age (from `by`)
    lst = listed or {}
    cl = set(cool or ())
    fr, ot = fresh or {}, outlets or {}
    picks = {
        'recheck': [by[m] for m in dict.fromkeys(recheck or ()) if m in by],
        # 🆕 FRESH (reserved): the live launch / migration stream's coins, newest first — never behind an old volume leader, never cooled
        'fresh': sorted((r for r in rs if r['mint'] in fr), key=lambda r: (_f(r['ageH']) if r.get('ageH') is not None else 99.0, -_f(r.get('vol5m')))),
        # 🕸 OUTLETS (reserved): callouts · fed runners · radar · runner board — sources the board's own ranking may not lift. A callout / listing
        # is NEWS: an old coin may return through it (and through LISTED = re-entering a tracked ranking), never through plain 'busy'
        'outlets': sorted((r for r in by.values() if r['mint'] in ot and r['mint'] not in cl), key=lambda r: (-len(ot[r['mint']]), -_f(r.get('front')))),
        'new': sorted((r for r in rs if r.get('ageH') is not None), key=lambda r: (r['mint'] in cl, _f(r['ageH']))),   # ♻ a rejected launch with nothing new goes to the back
        'accel': sorted((r for r in rs if _f(r.get('vol5m')) >= 1000 and _pace(r) > 1.0), key=lambda r: (r['mint'] in cl, fresh_key(r), -_pace(r))),
        'grad': sorted((r for r in rs if r.get('curve') is False and r.get('ageH') is not None and _f(r['ageH']) <= GRAD_AGE_H), key=lambda r: (r['mint'] in cl, -_f(r.get('vol1h')))),
        'momentum': sorted((r for r in rs if _f(r.get('vol5m')) >= 2000 and r.get('chg5m') is not None and _f(r['chg5m']) > 0), key=lambda r: (r['mint'] in cl, fresh_key(r), -_f(r['chg5m']))),
        'busy': sorted((r for r in rs if r['mint'] not in cl), key=lambda r: (fresh_key(r), -_f(r.get('front')))),   # ♻ a rejected coin with nothing new gives its seat at the table to a coin that has news
        'listed': sorted((r for r in by.values() if lst.get(r['mint']) and r['mint'] not in cl), key=lambda r: (-len(lst[r['mint']]), -_f(r.get('front'))))}
    out, tags = [], {}
    for k, n in INTAKE_SLOTS:
        took = 0
        for r in picks[k]:
            if n is not None and took >= n:
                break
            if r['mint'] in tags:
                tags[r['mint']].append(k)
                continue
            if len(out) >= cap:
                break
            tags[r['mint']] = [k]; out.append(r); took += 1
    return [{**r, 'intake': tags[r['mint']]} for r in out]


SCAN_TIERS = ('near entry, only the holder scan missing', 'blocked only on holder data', 'fresh launch with strong tape + pool', 'challenger near the switch line', 'expired scan recheck', 'positive read')






SEAT_ACTIONS = ('HOLD', 'REVIEW', 'CHALLENGER FOUND', 'SWITCHING', 'TAKE / EXIT', 'FILLING', 'CASH — NO VALID ENTRY')


def seat_actions(seats, decisions, switch_eval, seat):
    """🪑 What each seat is doing THIS cycle (display only — `manage` / Reaper / `fill_plan` decided). Held seat: SWITCHING (a swap was
    decided) · TAKE / EXIT (a pull) · CHALLENGER FOUND (a cleared challenger was tested against it and the seat was kept — the failing line
    says why) · REVIEW (Reaper / the desk is re-reading it, nothing decided) · HOLD. Empty seat: FILLING, else CASH — NO VALID ENTRY + its code."""
    dec = {d.get('pair'): d for d in decisions or []}
    sw = switch_eval or {}
    ch = sw.get('challenger') or {}
    per_empty = list((seat or {}).get('seats') or [])
    out, k = [], 0
    for x in seats or []:
        if x.get('kind') == 'open' or not x.get('symbol'):
            e = per_empty[k] if k < len(per_empty) else {}
            k += 1
            code = e.get('code') or (seat or {}).get('code')
            out.append({'symbol': None, 'action': 'FILLING' if code == 'FILLING' else 'CASH — NO VALID ENTRY', 'code': code, 'why': e.get('reason') or (seat or {}).get('reason')})
            continue
        d = dec.get(x.get('pair')) or {}
        a = d.get('action')
        if a == 'swap':
            act = 'SWITCHING'
        elif a == 'pull':
            act = 'TAKE / EXIT'
        elif ch.get('cleared') and (sw.get('current') or {}).get('symbol') == x.get('symbol') and not sw.get('switch'):
            act = 'CHALLENGER FOUND'
        elif x.get('buying'):
            act = 'FILLING'
        elif a == 'hold' and 'not on the table' in str(d.get('why') or ''):
            act = 'REVIEW'
        else:
            act = 'HOLD'
        why = sw.get('why') if act == 'CHALLENGER FOUND' else d.get('why') or ''
        out.append({'symbol': x.get('symbol'), 'pct': x.get('pct'), 'action': act, 'why': why, 'to': d.get('toSym') or (ch.get('symbol') if act == 'CHALLENGER FOUND' else None)})
    return out


def cycle_view(intake_, table, cases, charts, first, now, last_at, every, n_cycle, prev=None):
    """🔁 One line per 60s cycle: what the desk looked at and what it found. Counts only — read from this pass's objects."""
    t = list(table or [])
    cl = [c for c in cases or [] if c.get('cleared')]
    best = (cl or list(cases or []) or [None])[0]
    bands = {}
    for x in t:
        if x.get('band'):
            bands[x['band']] = bands.get(x['band'], 0) + 1
    return {'n': n_cycle, 'at': now, 'lastAt': last_at, 'every': every, 'nextIn': max(0, round(_f(last_at) + _f(every) - _f(now))) if last_at else None,
            'board': (intake_ or {}).get('board'), 'newLaunches': (intake_ or {}).get('newLaunches'), 'newToDesk': sum(1 for v in (first or {}).values() if _f(v.get('t')) >= _f(now) - 1),
            'screened': (intake_ or {}).get('screened'), 'by': (intake_ or {}).get('by'), 'read': len({x.get('mint') for x in t}),
            'freshVsLast': None if prev is None else len({x.get('mint') for x in t} - set(prev)),
            'reviewed': sum(1 for c in (charts or {}).values() if (c or {}).get('src') == 'candles'), 'cases': len(cases or []), 'cleared': len(cl),
            'best': None if not best else {'symbol': best.get('symbol'), 'lean': best.get('lean'), 'cleared': bool(best.get('cleared')),
                                           'blocked': next((k[2] for k in best.get('checks') or [] if not k[1]), None)}, 'bands': bands}


# ── ⚡ LIVE CHECK: a case file keeps its thesis; the decision reads the NEWEST shared market state ──────────────────────────────────
LIVE_CHASE, LIVE_FALL = 15.0, -8.0   # since the case was read: up more than this = chasing, down more than this = falling (Trigger's own hard lines)
# 🚫 entries the chart itself refused, bought anyway by the best-available / ranked doors — the real card's record (2026-10-11, 173 agent exits):
# E2 "no chasing" n10 median −16.8% · E3 "too violent, no stop fits" n16 median −13.2% = 11 of the 26 stop-outs; ENTER NOW entries ≈ flat
LOSING_ENTRIES = ('E2', 'E3')




def freshness(now, price_at=(), tape_at=(), candle_at=(), liq_at=None, input_at=None, decision_at=None):
    """⏱ How old each input REALLY is, separately (seconds; None = nothing measured): the newest price, tape, real candle and pool reading
    behind the decisions, the agent pass the cases came from, and the last seat decision."""
    age = lambda ts: None if not [t for t in ts or () if t] else round(max(0.0, _f(now) - max(_f(t) for t in ts if t)), 1)
    one = lambda t: None if not t else round(max(0.0, _f(now) - _f(t)), 1)
    return {'price': age(price_at), 'tape': age(tape_at), 'candle': age(candle_at), 'liquidity': one(liq_at), 'agentInput': one(input_at), 'decision': one(decision_at)}


# ── ♻ SAME COIN AGAIN: a rejected coin with nothing new waits; a material change brings it straight back ─────────────────────────────
REVIEW_COOL_SEC = 240      # a deep-reviewed, rejected coin is not deep-reviewed again for 4 min …
SEEN_KEEP = 3000
MATERIAL = {'px': 5.0, 'liq': 25.0, 'vol5m': 100.0}   # … unless price moved ≥ 5%, the pool ≥ 25%, 5-min volume doubled — or a scan / graduation / chart / socials changed


def snap_of(row):
    v, ch = row.get('vitals') or {}, row.get('chart') or {}
    return {'px': _f(row.get('px')), 'liq': _f((row.get('nums') or {}).get('liq') or v.get('liq')), 'vol5m': _f(v.get('vol5m') or row.get('vol5m')),
            'safe': v.get('safe'), 'curve': v.get('curve'), 'chart': ch.get('state'), 'social': bool(row.get('site') or row.get('x') or (row.get('social') or {}).get('ok')), 'ageH': v.get('ageH')}


def material(prev, cur):
    """What changed enough to look again → words, or None. (A breakout / a new state, a scan landing, a graduation, socials appearing count.)"""
    if not prev:
        return 'first look'
    pct = lambda a, b: abs(b / a - 1) * 100 if a > 0 and b > 0 else 0.0
    if pct(prev.get('px', 0), cur.get('px', 0)) >= MATERIAL['px']:
        return f"price {(cur['px'] / prev['px'] - 1) * 100:+.1f}%"
    if pct(prev.get('liq', 0), cur.get('liq', 0)) >= MATERIAL['liq']:
        return 'pool moved'
    if prev.get('vol5m', 0) > 0 and cur.get('vol5m', 0) >= prev['vol5m'] * (1 + MATERIAL['vol5m'] / 100):
        return '5-min volume doubled'
    for k, w in (('safe', 'holder scan landed'), ('curve', 'graduated / migrated'), ('chart', 'chart changed'), ('social', 'socials changed')):
        if prev.get(k) != cur.get(k) and cur.get(k) is not None:
            return f"{w} ({cur.get(k)})" if k == 'chart' else w
    return None


def note_seen(mem, table, cases, reviewed, now):
    """Update the per-coin memory: first seen · last seen · last deep review · last reject reason · last material change. Bounded."""
    m = dict(mem or {})
    cs = {c['mint']: c for c in cases or []}
    for x in table or []:
        k = x.get('mint')
        if not k:
            continue
        e = dict(m.get(k) or {'first': now})
        cur = snap_of(x)
        ch = material(e.get('snap'), cur)
        if ch:
            e['changed'], e['changeWhy'] = now, ch
        e['last'], e['snap'] = now, cur
        if k in (reviewed or ()):
            e['review'] = now
        c = cs.get(k)
        if c and not c.get('cleared'):
            e['reject'] = next((w[2] for w in c.get('checks') or [] if not w[1]), 'not cleared')
        elif c:
            e.pop('reject', None)
        m[k] = e
    if len(m) > SEEN_KEEP:
        m = dict(sorted(m.items(), key=lambda kv: -_f(kv[1].get('last')))[:SEEN_KEEP])
    return m


STALE_COOL_MULT = 3   # a rejected coin over 12h old waits 3× the normal cooldown unless something material changes


def review_due(e, now):
    """May this coin get a DEEP review now? Never reviewed · not rejected last time · something material changed since that review ·
    or the cooldown ran out. → (due, why)"""
    if not e or not e.get('review'):
        return True, 'never deep-reviewed'
    if not e.get('reject'):
        return True, 'was not rejected'
    if _f(e.get('changed')) > _f(e['review']):
        return True, f"changed: {e.get('changeWhy')}"
    cool = REVIEW_COOL_SEC * (STALE_COOL_MULT if _f((e.get('snap') or {}).get('ageH')) > OLD_INTAKE_H else 1)   # 🧊 a 12h+ reject cools 3× longer
    if _f(now) - _f(e['review']) >= cool:
        return True, 'cooldown over'
    return False, f"rejected {round(_f(now) - _f(e['review']))}s ago ({e.get('reject')}) — nothing new"


FRESH_LABELS = ('0–5m', '5–15m', '15–60m', '1–3h', '3–6h', '6h+', 'age ?')


def _med_(xs):
    xs = sorted(x for x in xs if x is not None)
    return None if not xs else round(xs[len(xs) // 2], 1)


def fresh_view(table, deep=(), cleared=(), prev=(), ranked=None, positions=None, now=0.0, cooled=0):
    """🆕 THE FRESH-TRENCH PIPELINE for one cycle (owner, 2026-10-11: "I want to visibly confirm that bought coins are actually fresh"):
    rows per freshness bucket · deep reviewed / cleared per bucket · unique vs repeats vs new · median age reviewed · the top 5 ranked
    candidates (age · MC · source · volume / buyer velocity · tier) · median age at ENTRY of the agents' real buys (last 24h vs before)."""
    import opportunity as _opp
    rows = [x for x in table or [] if x.get('mint')]
    by = {x['mint']: x for x in rows}
    lab = lambda x: FRESH_LABELS[fresh_key((x or {}).get('vitals') or {})]
    cnt = lambda ms: {k: sum(1 for m in ms if m in by and lab(by[m]) == k) for k in FRESH_LABELS}
    am = lambda x: None if ((x or {}).get('vitals') or {}).get('ageH') is None else _f(x['vitals']['ageH']) * 60
    pv = set(prev or ())
    top = []
    for x in (ranked or [])[:5]:
        vpm, bpm = _opp.velocity(x)
        top.append({'symbol': x.get('symbol'), 'ageMin': None if am(x) is None else round(am(x)), 'mc': (x.get('vitals') or {}).get('mcap'), 'src': [s for s in x.get('src') or [] if s != 'open'][:3],
                    'vpm': vpm, 'bpm': bpm, 'tier': x.get('tier'), 'score': x.get('opp'), 'fresh': _opp.fresh_bucket(x)[0]})
    ent = [(p.get('since'), (p.get('launch') or {}).get('ageH')) for p in positions or [] if (p.get('launch') or {}).get('ageH') is not None]
    recent = [h * 60 for t, h in ent if now - _f(t) <= 86400]
    older = [h * 60 for t, h in ent if now - _f(t) > 86400]
    return {'buckets': cnt(by), 'deep': cnt(deep or ()), 'cleared': cnt(cleared or ()),
            'unique': len(by), 'repeats': len(set(by) & pv), 'newUnique': len(set(by) - pv), 'cooled': int(cooled or 0),
            'ageReviewedMin': _med_([am(by[m]) for m in deep or () if m in by]), 'ageTableMin': _med_([am(x) for x in rows]),
            'top': top, 'boughtAgeMin24h': _med_(recent), 'boughtAgeMinBefore': _med_(older), 'bought24h': len(recent),
            'ageClearedMin': _med_([am(by[m]) for m in cleared or () if m in by])}


def candle_order(rows, deep=None, held=None):
    """📈 THE CANDLE BUDGET FOLLOWS NEW / BUSY COINS. The candles service builds a limited number of new histories per call IN REQUEST
    ORDER, so the order IS the allocation: fresh 0–12h coins first (deep reviews first, then the freshness ladder, then 5-min $), then
    older coins, held coins LAST (the tier tick re-reads them every tick anyway). → ordered {mint: pool}"""
    hd, dp = dict(held or {}), dict(deep or {})
    rs = [r for r in rows or [] if r.get('mint') and r.get('pairAddress') and r['mint'] not in hd]
    rs.sort(key=lambda r: (fresh_key(r) > 4, r['mint'] not in dp, fresh_key(r), -_f(r.get('vol5m'))))
    out = {r['mint']: r['pairAddress'] for r in rs}
    for m, pa in dp.items():
        if m not in hd and m not in out:
            out[m] = pa
    out.update(hd)
    return out



INDEX_FIELDS = ('mint', 'symbol', 'firstSeen', 'lastSeen', 'launchAgeMin', 'fresh', 'liveMC', 'liquidity', 'vol5m', 'volVelocity', 'buyerVelocity', 'sources', 'launchpad',
                'realCandles', 'holderStatus', 'chartQuality', 'marketPhase', 'social', 'lastMaterialChange', 'lastReview', 'cooldownLeft', 'eligible', 'why')


def active_index(table, seen=None, now=0.0, cap=None):
    """🗂 THE ONE ACTIVE CANDIDATE INDEX: one line per mint built from THIS pass's desk row — the same object Tally, Sherlock, Trigger,
    Devil read and the Warden / Reaper / Judge are handed — plus the per-coin memory (first / last seen, last review, cooldown). Nothing
    here is a cached eligibility: `eligible` is recomputed every pass from the hard checks (opportunity.hard_fail) on live data."""
    import opportunity as _opp
    import seat_ops as _so
    import market_wake as _mw
    out = []
    for x in table or []:
        m = x.get('mint')
        if not m:
            continue
        v, n, ch = x.get('vitals') or {}, x.get('nums') or {}, x.get('chart') or {}
        e = (seen or {}).get(m) or {}
        vpm, bpm = _opp.velocity(x)
        why = _opp.hard_fail(x, cap or _opp.MAX_MCAP)
        due, _w = review_due(e, now)
        cool = 0 if due or not e.get('review') else max(0, round(REVIEW_COOL_SEC * (STALE_COOL_MULT if _f(v.get('ageH')) > OLD_INTAKE_H else 1) - (now - _f(e.get('review')))))
        out.append({'mint': m, 'symbol': x.get('symbol'), 'firstSeen': e.get('first'), 'lastSeen': e.get('last'),
                    'launchAgeMin': None if v.get('ageH') is None else round(_f(v['ageH']) * 60, 1), 'fresh': _opp.fresh_bucket(x)[0],
                    'liveMC': v.get('mcap'), 'liquidity': n.get('liq') or v.get('liq'), 'vol5m': n.get('v5'), 'volVelocity': vpm, 'buyerVelocity': bpm,
                    'sources': [s for s in x.get('src') or [] if s != 'open'], 'launchpad': (x.get('launch') or {}).get('pad'),
                    'realCandles': ch.get('src') == 'candles', 'holderStatus': {True: 'passed', False: 'failed'}.get(v.get('safe'), 'not read'),
                    'chartQuality': _so.chart_quality(ch)[0] if ch else None, 'marketPhase': _mw.market_phase(ch, x.get('li')), 'social': bool(x.get('social') or v.get('site') or v.get('x')),
                    'lastMaterialChange': e.get('changed'), 'lastReview': e.get('review'), 'cooldownLeft': cool, 'eligible': why is None, 'why': why})
    return sorted(out, key=lambda r: (not r['eligible'], fresh_key({'ageH': None if r['launchAgeMin'] is None else r['launchAgeMin'] / 60}), -_f(r['volVelocity'])))
