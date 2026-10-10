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
import agents as _ag
import chart_intel as _ci
import market_data as _md

_f = _ag._f


def _med(xs):
    xs = sorted(x for x in xs if x is not None)
    n = len(xs)
    return None if not n else round(xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2, 2)


# ── 🎛 THE CREATOR'S LIMITS ──────────────────────────────────────────────────────────────────────────────────────────────────────
AUTHORITY = ('agents', 'manual')                 # agents = CREATOR LIMITS + AGENTS DECIDE · manual = only the hard safety exits act
TP_OPTS, SL_OPTS, HOLD_OPTS, SIZE_OPTS = (5, 10, 15, 20, 30, 50), (3, 5, 8, 10, 15, 20), (5, 10, 15, 30, 60, 120), (10, 15, 25, 40)
BOUNDS = {'agentTp': (2.0, 200.0), 'agentSl': (2.0, 40.0), 'agentTrailArm': (2.0, 100.0), 'agentTrailPct': (1.0, 50.0), 'agentMaxHold': (5.0, 240.0), 'agentSizePct': (5.0, 50.0)}
TRAIL = ('auto', 'off', 'custom')
SEAT_TARGETS = (0, 30, 60)                       # 0 = AUTO (30s)
SEAT_TARGET_AUTO = 30
SWITCH = {'agents': (1.0, 30.0), 'off': None, 'conservative': (1.5, 45.0), 'normal': (1.0, 30.0), 'aggressive': (0.5, 15.0)}   # → (lean margin, minutes held). Aggressive only lowers the margin — never under these floors
SWITCH_FLOOR = (0.5, _ag.CONTROL_HOLD_MIN)
ENTRY = ('agents', 'go')                         # agents = a full GO at once, the duty's cleared case on the seat target · go = a full GO only
POLICY_KEYS = ('agentAuthority', 'agentTp', 'agentSl', 'agentTrail', 'agentTrailArm', 'agentTrailPct', 'agentMaxHold', 'agentSizePct', 'agentSeatTarget', 'agentSwitch', 'agentEntry')


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
            'agentSwitch': p.get('agentSwitch') if p.get('agentSwitch') in SWITCH else 'agents', 'agentEntry': p.get('agentEntry') if p.get('agentEntry') in ENTRY else 'agents'}


def policy(cfg):
    """The limits as the desks read them. None = AGENTS CHOOSE for that control. `who` says, per control, who decides right now."""
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
                    'emptySeat': who(c['agentSeatTarget'])},
            'hard': {'catastrophicStop': _ci.CATASTROPHIC_STOP, 'movesPerHour': _ag.CONTROL_MOVES_HR, 'minPool': _ag.CONTROL_MIN_LIQ}}


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


def seat_state(ctx):
    """One line of truth for the agents' empty seats. `ctx` = {want, held, cases (the pass's case files), go (eligible GO coins),
    valid (candidates that would be allowed to fill NOW), movesLeft, courier, manual, live, freeUsd, minUsd, emptySince, target, now,
    nextTickIn}. → {state, empty, valid, reason, emptyFor, target, nextIn, late, blockers}
    FILLING = a valid candidate exists and the next tier tick takes it · NO VALID ENTRY = nothing clears (cash is a valid position)."""
    c = ctx or {}
    want, held, now = int(_f(c.get('want'))), int(_f(c.get('held'))), _f(c.get('now'))
    empty = max(0, want - held)
    valid = list(c.get('valid') or [])
    bl = blockers(c.get('cases'))
    base = {'empty': empty, 'want': want, 'held': held, 'valid': len(valid), 'validSyms': [str(x.get('symbol')) for x in valid][:4], 'target': int(_f(c.get('target')) or SEAT_TARGET_AUTO), 'blockers': bl,
            'emptyFor': round(now - _f(c['emptySince'])) if empty and c.get('emptySince') else None, 'nextIn': None}
    if not empty:
        return {**base, 'state': 'FULL', 'reason': f'{held} of {want} seats held'}
    if c.get('manual'):
        return {**base, 'state': 'CREATOR MANUAL', 'reason': 'you hold the decisions — the agents fill nothing'}
    if c.get('courier') == 'BAD':
        return {**base, 'state': 'NO VALID ENTRY', 'reason': 'EXECUTION BLOCK — Courier reads execution BAD'}
    if int(_f(c.get('movesLeft'))) <= 0:
        return {**base, 'state': 'NO VALID ENTRY', 'reason': f'hourly budget used ({_ag.CONTROL_MOVES_HR} real buys an hour) — churn is not the goal'}
    if _f(c.get('freeUsd')) < max(0.05, _f(c.get('minUsd'))):
        return {**base, 'state': 'NO VALID ENTRY', 'reason': f"NO CASH — ${_f(c.get('freeUsd')):.2f} free card cash"}
    if valid:
        late = base['emptyFor'] is not None and base['emptyFor'] > base['target']
        return {**base, 'state': 'FILLING', 'reason': f"${valid[0].get('symbol')} cleared every desk — the next tick fills the seat", 'nextIn': max(0, round(_f(c.get('nextTickIn')))) if c.get('nextTickIn') is not None else None, 'late': late}
    n = len(c.get('cases') or [])
    why = 'no coin has a positive read this pass' if not n else f"0 of {n} case files clear — " + ', '.join(f'{w} ({k})' for _, w, k in bl[:3])
    return {**base, 'state': 'NO VALID ENTRY', 'reason': why}


def may_fill(case_row, pol, empty_since, now, last_fill_at=0.0):
    """May the duty's CLEARED case (Trigger's bar waived, every safety check passed) take an EMPTY seat now? A full 🟢 GO never waits.
    Under entry style 'go' only a GO fills. Otherwise one cleared fill per seat target: the seat does not wait for the 10-minute duty."""
    if (case_row or {}).get('go'):
        return True
    if (pol or {}).get('entry') == 'go':
        return False
    gap = _f((pol or {}).get('seatTarget') or SEAT_TARGET_AUTO)
    return bool(empty_since) and now - _f(last_fill_at) >= gap


# ── ⇄ SWITCHING: superiority, not churn ──────────────────────────────────────────────────────────────────────────────────────────
def switch_test(cur, new, pol):
    """May `new` (a case file) take the seat of `cur` (a held position)? → {switch, why, edge, need, current, challenger}
    cur = {symbol, pnl, heldMin, lean, verdict (thesis: valid | weak | invalid | unknown | None), structure, liq, frozen, riding}
    Every line must hold: switching is on · the challenger CLEARED every desk · the position is not a winner · it has been held long
    enough · the challenger's read beats its own by the margin · the position is weak (thesis not valid, or its read gone, or twice the
    hold with nothing to show). A new coin being greener, a candle, or five minutes passing is none of these."""
    sw = (pol or {}).get('switch') or {'on': True, 'edge': SWITCH['agents'][0], 'holdMin': SWITCH['agents'][1], 'mode': 'agents'}
    c, n = cur or {}, new or {}
    pnl, held, own = _f(c.get('pnl')), _f(c.get('heldMin')), _f(c.get('lean'))
    nl = _f(n.get('lean') if n.get('lean') is not None else ((n.get('why') or {}).get('lean')))
    edge = round(nl - own, 2)
    out = {'switch': False, 'edge': edge, 'need': sw.get('edge'), 'mode': sw.get('mode'),
           'current': {'symbol': c.get('symbol'), 'pnl': round(pnl, 2), 'heldMin': round(held, 1), 'lean': round(own, 2), 'thesis': c.get('verdict'), 'structure': c.get('structure')},
           'challenger': None if not n else {'symbol': n.get('symbol'), 'lean': round(nl, 2), 'cleared': bool(n.get('cleared')), 'structure': ((n.get('row') or n).get('chart') or {}).get('state'),
                                             'data': (((n.get('row') or n).get('chart') or {}).get('q') or {}).get('state')}}
    no = lambda why: {**out, 'why': why}
    if not sw.get('on'):
        return no('switching is OFF (your setting)')
    if not n:
        return no('no challenger this pass')
    if not n.get('cleared'):
        bad = next((k for k in n.get('checks') or [] if not k[1]), None)
        return no(f"challenger not cleared: {CHECK_WORD.get(bad[0], bad[0]) if bad else 'not every desk passed it'}")
    if c.get('frozen') or c.get('riding'):
        return no('the position is frozen / riding — never switched')
    if pnl > 0 and c.get('verdict') != 'invalid':
        return no(f'{pnl:+.1f}% — a winner is not surrendered for a new coin')
    if held < _f(sw.get('holdMin')):
        return no(f"held {held:.0f} min — needs {_f(sw.get('holdMin')):.0f}")
    if edge < _f(sw.get('edge')):
        return no(f"read margin {edge:+.1f} — needs {_f(sw.get('edge')):+.1f} (lean {nl:+.1f} vs {own:+.1f})")
    weak = c.get('verdict') in ('weak', 'invalid') or own <= 0 or held >= 2 * _f(sw.get('holdMin'))
    if not weak:
        return no('the position\'s own thesis still stands — opportunity cost alone is not enough yet')
    return {**out, 'switch': True, 'why': f"{pnl:+.1f}% after {held:.0f} min, thesis {c.get('verdict') or 'unread'}, lean {own:+.1f} → ${n.get('symbol')} cleared every desk with lean {nl:+.1f} (margin {edge:+.1f} ≥ {_f(sw.get('edge')):+.1f})"}


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
        return 'DEVIL OBJECTION', 'devil', soft, False if not _ag.DEVIL_RULES.get(soft, (True,))[0] else None
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


def missed_winners(arch, brain_done, series, now, held=(), since=0.0):
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
        hit = min((_f(t) for lv, t in x.items() if _f(lv) >= WINNER_PCT), default=None)
        cs = [c for c in by.get(m, []) if start - 1800 <= _f(c['at']) <= at]
        first = cs[0] if cs else None
        stamp = next((p for p in (series or {}).get(m) or [] if p.get('c')), None)
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


def review(state, arch, office, now, n=8):
    """📝 Everything waiting for the creator's eyes, by category. It is BUILT from the records and only ever READ by the page — no desk
    reads it back, nothing waits on it being opened. Each item: coin · launch · time · move · what happened · what the office knew ·
    which agent / rule mattered · counterfactual where one exists · the lesson · the evidence count."""
    js = [d for d in _ag._judged(state or {}, 5) if now - _f(d.get('at')) <= LOOKBACK_SEC]
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
    pads = pad_record(_ag._judged(state or {}, 5))
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
    return {'at': now, 'order': list(REVIEW), 'labels': REVIEW_LABEL, 'counts': {k: len(v) for k, v in cats.items()}, 'items': cats, 'missedSummary': {k: v for k, v in ms.items() if k != 'items'},
            'blocking': False, 'note': 'Review is asynchronous: the office never reads this queue back and never waits on it.'}


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
