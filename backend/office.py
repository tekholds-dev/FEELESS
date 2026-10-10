"""🏢 THE OFFICE — the full decision chain for the creator's real-money Fuse card (HQ › Agents), pure + tested.

    Tally → Sherlock → Weather → Trigger → Devil → Warden → Courier → Reaper → Archivist → Judge

The first four desks + the Judge live in `agents.py`. This module adds the five that were missing and the rules that bind all ten:

  🌦 Weather    the trench's regime this pass (HOT · NORMAL · CHOP · THIN · HOSTILE) from measured inputs → bounded modifiers
  🛡 Warden     sizes an EXISTING real-card move: it may only reduce, cap or veto — never raise
  📮 Courier    execution truth from the keeper's own ledger: a fill is confirmed only with a filled row AND a signature
  ☠ Reaper     protects an OPEN position with deterministic rules; its exits go through the card's existing action path
  🗄 Archivist  the decision lineage of every case, hash-chained and bounded; learning is derived from those records only
  👨‍⚖️ Judge      a scorecard per agent; nobody is demoted on a thin sample; a rule changes only through a shadow test

Nothing here signs, sends, quotes or reads a chain. It is fed the numbers the service already holds and returns decisions + state.
"""
import hashlib
import json
from types import MappingProxyType

import agents as _ag
import chart_intel as _ci

_f, _med = _ag._f, _ag._med

CHAIN = ('tally', 'sherlock', 'weather', 'trigger', 'devil', 'warden', 'courier', 'reaper', 'archivist', 'judge')
PRIORITY = ('SURVIVE', 'PROTECT CAPITAL', 'EXECUTE CORRECTLY', 'LEARN', 'GROW')


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _frozen(x):
    if isinstance(x, dict):
        return MappingProxyType({k: _frozen(v) for k, v in x.items()})
    if isinstance(x, (list, tuple)):
        return tuple(_frozen(v) for v in x)
    return x


# ── 📜 THE CONSTITUTION ───────────────────────────────────────────────────────────────────────────────────────────────────────────
# IMMUTABLE CORE (identity · role · ideology · ethics · forbidden · hard rules · where the code lives). Frozen at import: no agent, no
# learning step and no endpoint can write to it. What CAN move is in TUNABLE, inside hard-coded bounds, and only through a shadow test.
WEATHER_BAR_RANGE = (-0.25, 1.0)     # the most Weather may move Trigger's bar (it can never reach a hard SKIP or Devil's objections)
WEATHER_SIZE_RANGE = (0.25, 1.0)     # the most Weather may shrink a move (never grow it)
WARDEN_STEPS = (1.0, 0.75, 0.5, 0.25, 0.0)
WARDEN_MIN_USD = 0.05                # a seat the keeper could not send is not a smaller risk, it is no trade
RUG_EXIT = 65.0                      # ☠ rug meter at which an open position is invalidated
TOP10_JUMP = 10.0                    # ☠ top-10 share up this many points since entry (and ≥ 30%) = holders concentrating
MIN_KEEP = 1.5                       # ☠ a trailing take only fires while there is still this much % to bank
MOMENTUM_MIN = 15.0                  # ☠ minutes held before a broken read counts (the card's record: exits inside 15 min lose)
EXIT_WAIT_SEC = 1800                 # 📮 an exit not confirmed on the ledger after 30 min is filed as UNCONFIRMED, never as done
JUDGE_MIN_N = 30                     # 👨‍⚖️ nobody is put on probation under this many judged samples …
JUDGE_DEMOTE_N = 60                  # … or demoted under this many
JUDGE_BAD = 45.0                     # accuracy % under which an agent's edge counts as degraded
PROPOSE_N = 10                       # a candidate rule change needs this many archived positions behind it
SHADOW_N = 20                        # … and this many NEW positions in shadow before it can be promoted
SHADOW_MARGIN = 0.5                  # … beating the live rule by this many % points on average, with a median no worse

TUNABLE = _frozen({
    'weather': {'hostileRugPct': (15.0, 10.0, 25.0, 'share of our judged calls that rugged in 6h at which the trench is HOSTILE'),
                'hotGreenPct': (65.0, 60.0, 75.0, 'share of coins green over 5 min above which the trench is HOT'),
                'coldGreenPct': (35.0, 25.0, 40.0, 'share of coins green over 5 min under which the trench is CHOP'),
                'thinLiqK': (30.0, 20.0, 50.0, 'median pool ($K) under which the trench is THIN')},
    'warden': {'poolSharePct': (1.0, 0.5, 2.0, 'most of a pool one seat may be'),
               'maxSeatPct': (40.0, 25.0, 50.0, 'most of the card one new seat may be'),
               'youngH': (6.0, 1.0, 12.0, 'coins younger than this get half size'),
               'ddPct': (25.0, 15.0, 40.0, 'card drawdown from its 24h peak at which new seats are halved')},
    'courier': {'badFailPct': (50.0, 40.0, 60.0, 'failed sends in 15 min at which execution is BAD'),
                'degradedFailPct': (25.0, 15.0, 35.0, 'failed sends in the hour at which execution is DEGRADED'),
                'maxDeltaPct': (3.0, 2.0, 5.0, 'typical fill worse than the mid price by this much = DEGRADED')},
    'reaper': {'protectAt': (6.0, 4.0, 15.0, 'peak gain % at which the trailing protection arms'),
               'giveBackPct': (50.0, 30.0, 70.0, 'share of the peak gain it may give back before the rest is banked'),
               'stopPct': (30.0, 15.0, 40.0, 'the CEILING of a normal stop — each entry gets its own structure-aware stop under it (chart_intel.stop_for); the catastrophic stop is above it and is not tunable'),
               'timeMaxMin': (120.0, 60.0, 240.0, 'minutes after which a position with no read left is closed')},
})

_HARD_TRIGGER = ('SKIP a coin that failed the holder scan', 'SKIP a pool under $20K', 'SKIP a +15% 5-minute candle', 'SKIP a −8% 5-minute fall',
                 f'the bar never goes under {_ag.BAR_FLOOR} whatever the dial or the weather')
CONSTITUTION = _frozen({
    'tally': {'icon': '📊', 'name': 'Tally', 'role': 'Discovery: the measurable reads of every coin, on its own tape.', 'ideology': 'Evidence first.',
              'ethics': ('Never invent a read.', 'Never silently substitute stale numbers.', 'Never promote a coin without enough observations.'),
              'forbidden': ('judging a coin', 'calling an entry', 'touching the card'),
              'hard': ('a coin needs 3 readings before anyone may enter (5 while Tally is on trial)', f'the tape keeps {_ag.SERIES_N} points a coin, one a pass',
                       'a reading older than 150s is STALE and is said so'),
              'code': {'file': 'backend/agents.py', 'fn': ('tally', 'regime')}, 'office': ('tally_read',)},
    'sherlock': {'icon': '🔍', 'name': 'Sherlock', 'role': 'Investigation: why the coin is moving, each reason weighed by its own record.', 'ideology': 'Reasons before action.',
                 'ethics': ('Never describe chart structure without measured evidence.', 'Every claim carries measurable evidence.', 'Contradicting evidence is shown, never dropped.', 'An unknown is an open question, not a pass.'),
                 'forbidden': ('calling an entry', 'overriding a failed scan', 'touching the card'),
                 'hard': (f'a reason\'s learned weight counts from {_ag.DRIVER_MIN_N} judged calls', f'a starting belief counts like {_ag.BELIEF_K} judged calls, never more'),
                 'chart': ('snapshot', 'classify'), 'code': {'file': 'backend/agents.py', 'fn': ('drivers', 'weights', 'sherlock', 'learned_share')}, 'office': ('sherlock_read', 'scan_status')},
    'weather': {'icon': '🌦', 'name': 'Weather', 'role': 'The trench\'s regime this pass, from the board and our own judged calls.', 'ideology': 'The environment changes strategy.',
                'ethics': ('Never apply the same thresholds blindly in every regime.', 'Never classify without the inputs: unknown inputs lower confidence.'),
                'forbidden': ('buying or selling', 'removing or loosening a safety gate', 'moving Trigger\'s bar outside its range', 'growing a position'),
                'hard': (f'bar adjustment stays inside {WEATHER_BAR_RANGE[0]:+.2f} … {WEATHER_BAR_RANGE[1]:+.2f}', f'size modifier stays inside ×{WEATHER_SIZE_RANGE[0]} … ×{WEATHER_SIZE_RANGE[1]}',
                         'never judged under 10 coins (THIN, low confidence)'),
                'code': {'file': 'backend/office.py', 'fn': ('weather', 'weather_adj')}},
    'trigger': {'icon': '⏱', 'name': 'Trigger', 'role': 'Entry timing: ENTER, WAIT or SKIP for the next 5 minutes.', 'ideology': 'Precision over frequency.',
                'ethics': ('Never chase merely because price is rising.', 'Never call an entry clean unless every required check has its evidence.', 'A missed runner is counted, never hidden.'),
                'forbidden': ('entering past a hard SKIP', 'entering against a Devil objection', 'sizing a position'),
                'hard': _HARD_TRIGGER + ('the chart can only make an entry pickier (ENTER NOW is required; it never upgrades a WAIT)', f'a +{_ci.PARABOLIC_5M:g}% 5-minute move is PARABOLIC: never entered'),
                'chart': ('entry_call',), 'code': {'file': 'backend/agents.py', 'fn': ('bar_now', 'trigger')}, 'office': ('trigger_checks',)},
    'devil': {'icon': '⚖', 'name': 'Devil', 'role': 'Adversarial challenge: prove the trade wrong before it is allowed.', 'ideology': 'Prove the trade wrong first.',
              'ethics': ('Never object merely because a chart looks visually scary.', 'Object only with evidence.', 'A soft objection must be backed by its own record.', 'No random opposition, no canned lines.'),
              'forbidden': ('approving a coin nobody scanned', 'waiving a hard objection', 'objecting without a named rule'),
              'hard': ('busted read (its own 1h record ≥ 30 settled, typical ≤ −20%)', 'rug meter ≥ 50', 'already ran > +150% on the hour', 'under 15 minutes old',
                       'holders never scanned', 'burned us in the last 6h', 'rug signs learned from autopsies', 'a creator-approved avoid tactic'),
              'chart': ('objections',), 'code': {'file': 'backend/agents.py', 'fn': ('devil_args', 'devil', 'busted_now', 'rug_lift')}, 'office': ('devil_record',)},
    'warden': {'icon': '🛡', 'name': 'Warden', 'role': 'Risk and size of an existing real-card move. It never judges the coin.', 'ideology': 'Survival first.',
               'ethics': ('Never increase size because of excitement or recent profit.', 'Capital preservation outranks excitement, FOMO, win rate and agent ego.', 'Every size change names the rule that made it.'),
               'forbidden': ('increasing a move above what was requested', 'opening a move nobody requested', 'judging whether the coin is good'),
               'hard': ('allowed size ≤ requested size, always', f'multipliers are {", ".join(f"{m:g}×" for m in WARDEN_STEPS)} — nothing above 1×',
                        'execution BAD = veto', f'a seat it cuts under ${WARDEN_MIN_USD:.2f} is a veto, not a smaller buy'),
               'chart': ('risk', 'stop_for'), 'code': {'file': 'backend/office.py', 'fn': ('warden',)}},
    'courier': {'icon': '📮', 'name': 'Courier', 'role': 'Execution truth, read from the keeper\'s own ledger.', 'ideology': 'A decision is not a trade until the chain says it is.',
                'ethics': ('Never report a fill that is not confirmed.', 'A failed or expired send is reported as that, with its error.'),
                'forbidden': ('sending, signing or quoting anything', 'calling a pending order filled', 'retrying an order'),
                'hard': ('confirmed = a ledger row with status filled AND a signature', 'one signature may back one fill per side (a duplicate = BAD)',
                         'a keeper halt or an order stuck > 180s = BAD'),
                'code': {'file': 'backend/office.py', 'fn': ('confirmed', 'fill_state', 'courier')}},
    'reaper': {'icon': '☠', 'name': 'Reaper', 'role': 'Protects an open position after entry, with deterministic exit rules.', 'ideology': 'Profit is not protected until the position is.',
               'ethics': ('Never keep holding merely because a position is green.', 'Never keep holding merely to avoid realizing a loss.', 'Never hold because of hope.', 'Never claim an exit without a confirmed exit.', 'Never invent a price or a pool depth.'),
               'forbidden': ('buying', 'selling by itself: its exits go through the card\'s existing action path', 'giving a winner\'s seat to a new candidate',
                             'touching a coin the creator froze'),
               'hard': (f'catastrophic stop −{_ci.CATASTROPHIC_STOP:g}%: a constant no learning or promotion can move or switch off', f'a normal stop stays inside {_ci.STOP_FLOOR:g}% … {_ci.CATASTROPHIC_STOP - 5:g}%',
                        f'a thesis gets at least {_ci.MIN_WINDOWS} five-minute windows and at most {_ci.MAX_WINDOWS}; an invalidated thesis leaves at once', 'pool under half its entry depth = out now', f'rug meter ≥ {RUG_EXIT:g} or a failed holder scan = out', f'top-10 up {TOP10_JUMP:g} pts since entry (and ≥ 30%) = out',
                        'the take line stays the card\'s own (agentTakePct / the learned scalp line)', 'no price = no ruling this tick'),
               'chart': ('thesis', 'review', 'stop_for'), 'code': {'file': 'backend/office.py', 'fn': ('reap', 'reaper_replay', 'merge_reaper', 'confirm_exits')}},
    'archivist': {'icon': '🗄', 'name': 'Archivist', 'role': 'The permanent decision lineage and the learning derived from it.', 'ideology': 'Every real decision becomes evidence.',
                  'ethics': ('Never rewrite what the entry thesis originally was.', 'Never rewrite history.', 'Never turn a loss into a win.', 'Never discard inconvenient data: what rotates out is folded into the totals.'),
                  'forbidden': ('editing a filed decision', 'deleting a losing record', 'stating a pattern without its sample count'),
                  'hard': ('every decision record is hash-chained to the one before it', 'cases are bounded: the oldest fold into aggregates', 'a pattern is shown only from 5 records'),
                  'code': {'file': 'backend/office.py', 'fn': ('file_case', 'settle_cases', 'file_position', 'verify', 'patterns')}},
    'judge': {'icon': '👨‍⚖️', 'name': 'Judge', 'role': 'Scores every agent on its own record, itself included.', 'ideology': 'Judge the record, not the last result.',
              'ethics': ('Evaluate chart decisions using the information available at that time, not hindsight.', 'No agent is demoted on one or two outcomes.', 'A rule changes only after a shadow test beats the live rule.', 'The Judge is scored too.'),
              'forbidden': ('changing the immutable constitution', 'promoting an untested change', 'loosening a safety gate as a reward'),
              'hard': (f'probation needs ≥ {JUDGE_MIN_N} samples, demotion ≥ {JUDGE_DEMOTE_N}', f'a candidate needs {PROPOSE_N} archived positions, then {SHADOW_N} in shadow',
                       'a trial only ever tightens'),
              'code': {'file': 'backend/agents.py', 'fn': ('ruling', 'judge', 'survival', 'evolve', 'reckon')}, 'office': ('scorecards', 'propose', 'promote', 'judge_candidates')},
})


def tune(state, agent, key):
    """A tunable's LIVE value: the promoted one when a shadow test put it there, else the hard-coded default — always inside its bounds."""
    d, lo, hi, _ = TUNABLE[agent][key]
    v = (((state or {}).get('tune') or {}).get(agent) or {}).get(key)
    return _clamp(_f(v), lo, hi) if v is not None else d


def tunes(state, agent):
    return {k: tune(state, agent, k) for k in (TUNABLE.get(agent) or {})}


# ── 🌦 WEATHER ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
REGIMES = {'HOT': (-0.25, 1.0), 'NORMAL': (0.0, 1.0), 'CHOP': (0.5, 0.75), 'THIN': (0.5, 0.5), 'HOSTILE': (1.0, 0.25)}   # → (bar adj, size ×)


def weather(nums, rows, state, now, courier_health=None, office=None):
    """🌦 The regime of the trench THIS pass, from what was measured: Tally's numbers (share green, typical 5-min move, pool depth),
    the board (launch velocity, viable coins, bot share) and our own judged calls (typical 5-min outcome in 2h, rug rate + survival
    in 6h, how this time of day has read). → {regime, confidence, inputs, why, mods: {barAdj, size}, at}. It buys nothing."""
    T = lambda k: tune(office, 'weather', k)
    ns = list((nums or {}).values())
    ds = [_f(n.get('d5')) for n in ns if n.get('d5') is not None]
    liqs = [_f(n.get('liq')) for n in ns if _f(n.get('liq')) > 0]
    green = round(sum(1 for x in ds if x > 0) / len(ds) * 100) if ds else None
    by = {r.get('mint'): r for r in rows or []}
    viable = sum(1 for m, n in (nums or {}).items() if (by.get(m) or {}).get('safe') is not False and _f(n.get('liq')) >= 20_000 and -8 <= _f(n.get('d5')) <= 15
                 and (n.get('buy') is None or _f(n['buy']) >= 55))
    new_n = sum(1 for r in rows or [] if r.get('ageH') is not None and _f(r['ageH']) <= 1)
    bots = sum(1 for r in rows or [] if _f(((r.get('mind') or {}).get('bots') or (0,))[0]) >= 40 or ((r.get('mind') or {}).get('crowd') or {}).get('swarm'))
    calls = list(((state or {}).get('open') or {}).values()) + list((state or {}).get('done') or [])
    recent = [_f(d['p5']) for d in calls if d.get('p5') is not None and now - _f(d.get('at')) <= 7200]
    six = [d for d in calls if d.get('p5') is not None and now - _f(d.get('at')) <= 21600]
    rugs = sum(1 for d in six if _f(d['p5']) <= -50 or d.get('p60') == -100.0)
    hour = [d for d in six if d.get('p60') is not None]
    block = int((now % 86400) // 14400)
    sess = [_f(d['p5']) for d in calls if d.get('p5') is not None and d.get('kind') == 'wait' and int((_f(d.get('at')) % 86400) // 14400) == block]
    inp = {'coins': len(ds), 'greenPct': green, 'med5': round(_med(ds), 2) if ds else None, 'liqMedK': round(_med(liqs) / 1000, 1) if liqs else None,
           'thinPct': round(sum(1 for x in liqs if x < 20_000) / len(liqs) * 100) if liqs else None, 'viable': viable, 'newLaunches': new_n,
           'botPct': round(bots / len(rows) * 100) if rows else None, 'out5': round(_med(recent), 2) if len(recent) >= 10 else None, 'out5N': len(recent),
           'rugPct': round(rugs / len(six) * 100, 1) if len(six) >= 10 else None, 'rugN': len(six),
           'survivePct': round(sum(1 for d in hour if _f(d['p60']) > -50) / len(hour) * 100) if len(hour) >= 10 else None,
           'sessionMed5': round(_med(sess), 2) if len(sess) >= 20 else None, 'sessionN': len(sess), 'execution': courier_health}
    why = []
    if inp['rugPct'] is not None and inp['rugPct'] >= T('hostileRugPct'):
        why.append(f"{inp['rugPct']:g}% of our last {len(six)} judged calls rugged (line {T('hostileRugPct'):g}%)")
    if inp['out5'] is not None and inp['out5'] <= -5:
        why.append(f"our calls of the last 2h read {inp['out5']:+.1f}% typical at 5 min")
    if inp['botPct'] is not None and inp['botPct'] >= 60:
        why.append(f"{inp['botPct']}% of the board is botted / swarmed")
    if courier_health == 'BAD':
        why.append('execution is BAD')
    if why:
        reg = 'HOSTILE'
    elif len(ds) < 10 or (inp['liqMedK'] is not None and inp['liqMedK'] < T('thinLiqK')) or viable < 3:
        reg = 'THIN'
        why.append(f"only {len(ds)} coins read" if len(ds) < 10 else f"median pool ${inp['liqMedK']:g}K (line ${T('thinLiqK'):g}K)" if inp['liqMedK'] is not None and inp['liqMedK'] < T('thinLiqK') else f'{viable} viable coins')
    elif green is not None and green < T('coldGreenPct'):
        reg = 'CHOP'; why.append(f"{green}% of coins green over 5 min (line {T('coldGreenPct'):g}%)")
    elif inp['med5'] is not None and abs(inp['med5']) < 0.5 and inp['out5'] is not None and inp['out5'] < 0:
        reg = 'CHOP'; why.append(f"typical 5-min move {inp['med5']:+.1f}% and our calls read {inp['out5']:+.1f}%")
    elif green is not None and green > T('hotGreenPct') and (inp['out5'] is None or inp['out5'] >= 0):
        reg = 'HOT'; why.append(f"{green}% of coins green over 5 min" + (f", our calls {inp['out5']:+.1f}%" if inp['out5'] is not None else ''))
    else:
        reg = 'NORMAL'; why.append(f"{green}% green, {viable} viable coins" if green is not None else 'nothing unusual measured')
    keys = ('greenPct', 'med5', 'liqMedK', 'botPct', 'out5', 'rugPct', 'survivePct', 'sessionMed5')
    known = sum(1 for k in keys if inp[k] is not None)
    bar, size = REGIMES[reg]
    return {'regime': reg, 'confidence': round(min(1.0, len(ds) / 40) * known / len(keys), 2), 'inputs': inp, 'why': why, 'at': now,
            'missing': [k for k in keys if inp[k] is None],
            'mods': {'barAdj': _clamp(bar, *WEATHER_BAR_RANGE), 'size': _clamp(size, *WEATHER_SIZE_RANGE)}}


def weather_adj(w):
    """The ONLY thing of Weather's that reaches Trigger: one number on its bar, clamped to WEATHER_BAR_RANGE whatever the object says.
    Trigger's hard SKIPs, the bar floor and every Devil objection are not parameters — Weather has no handle on them."""
    return _clamp(_f(((w or {}).get('mods') or {}).get('barAdj')), *WEATHER_BAR_RANGE)


def weather_size(w):
    m = ((w or {}).get('mods') or {}).get('size')
    return 1.0 if m is None else _clamp(_f(m), *WEATHER_SIZE_RANGE)


# ── 📮 COURIER ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def confirmed(row):
    """A fill is confirmed ONLY by a ledger row the keeper booked from the chain: status filled AND a signature. Nothing else is a fill."""
    return bool(row and row.get('status') == 'filled' and row.get('sig'))


def _delta(r):
    """How much worse than the mid price the fill was, % (positive = worse) — None when either price is missing."""
    mid, px = _f(r.get('midPx')), _f(r.get('px'))
    if mid <= 0 or px <= 0:
        return None
    return round(((px / mid - 1) if r.get('side') == 'buy' else (1 - px / mid)) * 100, 2)


def fill_state(ledger, mint, side, after=0.0, card=None, symbol=None):
    """📮 What the ledger says about the newest `side` order of `mint` since `after` → {state: confirmed | failed | refused | none, …}.
    'confirmed' needs `confirmed(row)`; a pending order has no ledger row yet, so it reads 'none' (the keeper's `pending` shows it)."""
    for r in reversed(ledger or []):
        if (r.get('mint') != mint if mint else r.get('symbol') != symbol) or r.get('side') != side or _f(r.get('at')) < after or (card and r.get('card') != card):
            continue
        if confirmed(r):
            cost = _f(r.get('costUsd'))
            return {'state': 'confirmed', 'sig': r.get('sig'), 'at': _f(r.get('at')), 'usd': _f(r.get('usd')), 'px': _f(r.get('px')), 'delta': _delta(r),
                    'feeUsd': _f(r.get('feeUsd')), **({'realPct': round(_f(r.get('realizedPnlUsd')) / cost * 100, 2), 'realUsd': round(_f(r.get('realizedPnlUsd')), 4)} if side == 'sell' and cost > 0 else {})}
        if r.get('status') in ('failed', 'skipped'):
            return {'state': 'failed' if r['status'] == 'failed' else 'refused', 'at': _f(r.get('at')), 'err': str(r.get('err') or '')[:120]}
    return {'state': 'none'}


def courier(ledger, book, now, card=None, office=None):
    """📮 Execution health from the keeper's own rows of the last hour (it sends nothing): sends, fills, failures, expiries, refusals,
    fill vs mid price, time to land, fees, retries, duplicate signatures, the order in flight. → {health: HEALTHY | DEGRADED | BAD, why, …}"""
    T = lambda k: tune(office, 'courier', k)
    rows = [r for r in ledger or [] if r.get('side') in ('buy', 'sell') and (not card or r.get('card') == card) and now - _f(r.get('at')) <= 3600]
    sends = [r for r in rows if r.get('status') in ('filled', 'failed')]
    s15 = [r for r in sends if now - _f(r.get('at')) <= 900]
    fails = lambda rs: sum(1 for r in rs if r.get('status') == 'failed')
    fills = [r for r in sends if confirmed(r)]
    deltas = [d for d in (_delta(r) for r in fills) if d is not None]
    lands = [_f(r.get('landSec')) for r in fills if r.get('landSec') is not None]
    seen, dup = set(), 0
    for r in fills:
        k = (r.get('sig'), r.get('side'))
        dup += k in seen; seen.add(k)
    unsigned = sum(1 for r in rows if r.get('status') == 'filled' and not r.get('sig'))
    p = (book or {}).get('pending') if isinstance((book or {}).get('pending'), dict) else None
    p_age = round(now - _f(p.get('sentAt') or p.get('at')), 1) if p else None
    why, health = [], 'HEALTHY'
    bad = lambda t: (why.append(t), 'BAD')[1]
    if (book or {}).get('halt'):
        health = bad(f"the keeper is halted: {str((book or {}).get('haltWhy') or 'halt')[:80]}")
    if p_age is not None and p_age > 180:
        health = bad(f'an order has been in flight for {p_age:.0f}s')
    if len(s15) >= 3 and fails(s15) / len(s15) * 100 >= T('badFailPct'):
        health = bad(f"{fails(s15)} of {len(s15)} sends failed in 15 min (line {T('badFailPct'):g}%)")
    if dup or unsigned:
        health = bad(f'{dup} duplicate signature(s), {unsigned} filled row(s) without a signature')
    if health != 'BAD':
        deg = []
        if len(sends) >= 4 and fails(sends) / len(sends) * 100 >= T('degradedFailPct'):
            deg.append(f"{fails(sends)} of {len(sends)} sends failed this hour (line {T('degradedFailPct'):g}%)")
        if len(deltas) >= 3 and _med(deltas) > T('maxDeltaPct'):
            deg.append(f"fills land {_med(deltas):.1f}% worse than mid (line {T('maxDeltaPct'):g}%)")
        if p_age is not None and p_age > 60:
            deg.append(f'an order has been in flight for {p_age:.0f}s')
        if sends and sends[-1].get('status') == 'failed':
            deg.append(f"the last send failed: {str(sends[-1].get('err') or '')[:60]}")
        if deg:
            health, why = 'DEGRADED', deg
    if not why:
        why = [f'{len(fills)} of {len(sends)} sends confirmed this hour' if sends else 'no sends this hour — nothing measured against it']
    refused = {}
    for r in rows:
        if r.get('status') == 'skipped':
            k = str(r.get('err') or 'refused').split(' ')[0:3]
            refused[' '.join(k)] = refused.get(' '.join(k), 0) + 1
    last = [{'at': _f(r.get('at')), 'sym': r.get('symbol'), 'side': r.get('side'), 'usd': round(_f(r.get('usd')), 4),
             'state': 'confirmed' if confirmed(r) else 'failed' if r.get('status') == 'failed' else 'refused' if r.get('status') == 'skipped' else str(r.get('status')),
             'midPx': _f(r.get('midPx')) or None, 'px': _f(r.get('px')) or None, 'delta': _delta(r) if confirmed(r) else None, 'impact': r.get('impactPct'),
             'feeUsd': _f(r.get('feeUsd')) if confirmed(r) else None, 'landSec': r.get('landSec'), 'retry': bool(r.get('retrySlipBps') or ':r' in str(r.get('id') or '')),
             'slipBps': r.get('retrySlipBps'), 'err': str(r.get('err') or '')[:90] or None, 'sig': r.get('sig') if confirmed(r) else None} for r in rows[-8:]][::-1]
    return {'health': health, 'why': why, 'at': now, 'sends': len(sends), 'fills': len(fills), 'failed': fails(sends),
            'expired': sum(1 for r in sends if 'expired' in str(r.get('err') or '')), 'refused': sum(refused.values()), 'refusedWhy': sorted(refused.items(), key=lambda kv: -kv[1])[:4],
            'retries': sum(1 for r in rows if r.get('retrySlipBps') or ':r' in str(r.get('id') or '')), 'duplicates': dup, 'unsigned': unsigned,
            'deltaMed': round(_med(deltas), 2) if deltas else None, 'deltaWorst': max(deltas) if deltas else None, 'landMed': round(_med(lands), 1) if lands else None,
            'feeMed': round(_med([_f(r.get('feeUsd')) for r in fills]), 5) if fills else None,
            'pending': {'sym': p.get('symbol'), 'side': p.get('side'), 'age': p_age} if p else None, 'last': last}


# ── 🛡 WARDEN ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def warden(requested, ctx, office=None, floor=WARDEN_MIN_USD):
    """🛡 How much of an EXISTING real-card move may go ahead. `requested` = the $ the card's own rule would spend; `ctx` = measured
    values (card value / put-in / peak, lives, last real results, the candidate's pool / age / 5-min move / top-10, the weather, the
    courier's health). Each rule that bites names itself; the smallest multiplier wins, snapped DOWN to a step. allowed ≤ requested,
    always: there is no rule here that can return more. → {requested, allowed, mult, veto, rules: [{id, mult, why}], limits}"""
    T = lambda k: tune(office, 'warden', k)
    req = max(0.0, _f(requested))
    c = ctx or {}
    rules = []
    hit = lambda rid, m, why: rules.append({'id': rid, 'mult': round(_clamp(m, 0.0, 1.0), 3), 'why': why})
    if c.get('courier') == 'BAD':
        hit('W1 execution', 0.0, 'Courier reads execution BAD — no new money until sends land')
    elif c.get('courier') == 'DEGRADED':
        hit('W1 execution', 0.5, 'Courier reads execution DEGRADED')
    ws = weather_size(c.get('weather'))
    if ws < 1:
        hit('W2 weather', ws, f"the trench is {(c.get('weather') or {}).get('regime')} (×{ws:g})")
    liq = _f(c.get('liq'))
    if liq > 0 and req > 0 and req > liq * T('poolSharePct') / 100:
        hit('W3 pool share', liq * T('poolSharePct') / 100 / req, f"${req:.2f} is over {T('poolSharePct'):g}% of a ${liq / 1000:.0f}K pool")
    if c.get('ageH') is None:
        hit('W4 age', 0.25, 'the coin\'s age is unknown')
    elif _f(c['ageH']) < T('youngH'):
        hit('W4 age', 0.5, f"{_f(c['ageH']):.1f}h old (under {T('youngH'):g}h)")
    if c.get('d5') is not None and abs(_f(c['d5'])) >= 10:
        hit('W5 volatility', 0.5, f"{_f(c['d5']):+.0f}% in 5 min")
    if c.get('top10') is not None and _f(c['top10']) >= 30:
        hit('W6 holders', 0.5, f"top-10 hold {_f(c['top10']):.0f}%")
    if c.get('lives') is not None and int(_f(c['lives'])) <= 3:
        hit('W7 lives', 0.5, f"{int(_f(c['lives']))} of {_ag.LIVES} lives left")
    last = [_f(x) for x in (c.get('lastReal') or [])][-3:]
    if len(last) == 3 and all(x <= 0 for x in last):
        hit('W8 losing streak', 0.5, 'the last 3 real exits all lost')
    peak, val = _f(c.get('peak')), _f(c.get('value'))
    if peak > 0 and val > 0 and (1 - val / peak) * 100 >= T('ddPct'):
        hit('W9 drawdown', 0.5, f"the card is {(1 - val / peak) * 100:.0f}% under its 24h peak (line {T('ddPct'):g}%)")
    if val > 0 and req > val * T('maxSeatPct') / 100:
        hit('W10 concentration', val * T('maxSeatPct') / 100 / req, f"${req:.2f} is over {T('maxSeatPct'):g}% of the ${val:.2f} card")
    if c.get('chart'):   # 📈 chart risk (chart_intel.risk): the structure can shrink or veto the seat, never grow it
        cm, cwhy = (c['chart'].get('risk') or [1.0, ''])[:2]
        if _f(cm) < 1:
            hit('W12 chart risk', _f(cm), f"{c['chart'].get('state')}: {cwhy}")
    raw = min([r['mult'] for r in rules] or [1.0])
    mult = max(s for s in WARDEN_STEPS if s <= raw + 1e-9)
    allowed = round(req * mult, 6)
    if 0 < allowed < floor <= req:   # a cut that would leave an unsendable order: the smallest sendable one instead — still under what was asked
        allowed = round(floor, 6)
        rules.append({'id': 'W11 smallest order', 'mult': round(floor / req, 3), 'why': f'×{mult:g} would be under the ${floor:.2f} the keeper can send — kept at the smallest order'})
    if allowed < floor:
        allowed, mult = 0.0, 0.0
    allowed = min(allowed, req)
    return {'requested': round(req, 4), 'allowed': round(allowed, 4), 'mult': mult, 'eff': round(allowed / req, 3) if req > 0 else 0.0, 'veto': allowed <= 0,
            'rules': rules, 'decided': min(rules, key=lambda r: r['mult'])['id'] if rules else 'none — full size',
            'limits': {'steps': list(WARDEN_STEPS), 'floorUsd': floor, **tunes(office, 'warden')}}


# ── ☠ REAPER ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
REAPER_STATES = ('HOLD', 'PROTECT', 'TAKE', 'EXIT INVALIDATED')
PATH_KEEP = 240


def take_line(cfg, scalp=None):
    """The card's OWN take line for an agent coin: the learned scalp line when one is adopted and `agentScalp` is on, else `agentTakePct`."""
    if (cfg or {}).get('agentScalp', True) and (scalp or {}).get('tp'):
        return _f(scalp['tp'])
    return _f((cfg or {}).get('agentTakePct') or 10)


def take_info(cfg, scalp=None):
    """🎯 Which take line the real agent seats obey RIGHT NOW and where it comes from: the base (`agentTakePct`, the creator's setting) or
    the LEARNED scalp line (`agents.scalp_adopt`: ≥ SCALP_N of their own 5-minute paths, average > 0 AND > holding). The take line is not
    an office tunable, so it is never 'promoted' — a learned line is dropped by itself the pass it stops being proven."""
    base = _f((cfg or {}).get('agentTakePct') or 10)
    learned = bool((cfg or {}).get('agentScalp', True) and (scalp or {}).get('tp'))
    return {'base': base, 'active': take_line(cfg, scalp), 'source': 'learned' if learned else 'base', 'ruleId': 'R6 take line',
            'rule': 'agents.scalp_adopt — their own 5-min paths' if learned else 'cfg agentTakePct — your setting', 'scalpOn': bool((cfg or {}).get('agentScalp', True)),
            'evidenceN': (scalp or {}).get('n') if learned else None, 'shadowAvg': (scalp or {}).get('avg') if learned else None, 'adoptedAt': (scalp or {}).get('at') if learned else None,
            'needN': _ag.SCALP_N, 'promoted': None}


OBEY = {'R1': 'hard safety exit', 'R2': 'hard safety exit', 'R3': 'hard safety exit', 'R5x': 'hard safety exit', 'R4': 'invalidation exit', 'R5t': 'invalidation exit', 'R5': 'structure-aware stop',
        'R6': 'take line', 'R7': 'trailing protection', 'R7s': 'trailing protection', 'R8': 'thesis review', 'R9': 'thesis review', 'R10': 'thesis hold', 'R0': 'waiting'}


def reaper_replay(path, p, take):
    """What Reaper's price rules would have banked on a recorded path of % readings (take line · trailing give-back · stop), in order —
    used by the Judge to shadow-test a candidate setting on REAL closed positions. → the % it would have left at."""
    peak = 0.0
    for x in path or []:
        x = _f(x); peak = max(peak, x)
        if x >= take:
            return take
        if x <= -_f(p['stopPct']):
            return x
        if peak >= _f(p['protectAt']) and x <= peak * (1 - _f(p['giveBackPct']) / 100) and x >= MIN_KEEP:
            return x
    return _f(path[-1]) if path else 0.0


def reap(legs, table, prices, cfg, pos, now, scalp=None, control=False, weather_=None, tape=None, office=None, sized=None, charts=None, theses=None):
    """☠ One look at every position the agents hold on the real card (in control: every coin that is not frozen). It keeps each one's
    record (entry, peak, path, depth and top-10 at entry) and rules, in this order — the first that fires decides:
      R1 pool collapsed · R2 invalidated (failed scan / rug meter) · R3 holders concentrating · R4 whale dump on the tape · R5 stop* ·
      R6 the card's take line · R7 trailing protection · R8 momentum failed after 15 min* · R9 time with no read left* · else HOLD.
      (* only on coins the agents put on the card: other coins keep the card's own stop and are switched by `agents.manage`.)
    A ruling with `action: 'pull'` is a REQUEST: the service merges it into the card's existing agent decisions (merge_reaper) and the
    keeper sells; the position stays 'exit requested' until the ledger confirms it. No price = no ruling. → (positions, reports, gone)"""
    T = lambda k: tune(office, 'reaper', k)
    pos = {m: dict(v) for m, v in (pos or {}).items()}
    by = {x['mint']: x for x in table or []}
    take = take_line(cfg, scalp)
    tsrc = take_info(cfg, scalp)['source']
    out, on = [], set()
    for l in legs or []:
        m = l.get('mint')
        if not m or l.get('placeholder') or l.get('frozen') or not (control or _ag.is_agent(l)):
            continue
        on.add(m)
        base = {'mint': m, 'pair': l.get('pairAddress'), 'symbol': l.get('symbol'), 'owner': 'agents' if _ag.is_agent(l) else 'card', 'action': None}
        px, entry = _f((prices or {}).get(l.get('pairAddress'))), _f(l.get('entry'))
        if l.get('buying') or _f(l.get('units')) <= 0 or entry <= 0:
            out.append({**base, 'state': 'HOLD', 'rule': 'R0 waiting for the fill', 'evidence': 'the buy is not confirmed on the ledger yet', 'exec': 'unconfirmed'}); continue
        if px <= 0:
            out.append({**base, 'state': 'HOLD', 'rule': 'R0 no price', 'evidence': 'no live price this tick — nothing is ruled on a guess', 'exec': 'confirmed', 'entry': entry}); continue
        x = by.get(m)
        v = (x or {}).get('vitals') or {}
        pct = (px / entry - 1) * 100
        p = pos.get(m) or {'entry': entry, 'since': _f(l.get('at')) or now, 'peak': pct, 'low': pct, 'path': [], 'liq0': _f(l.get('liq')) or None, 'top0': v.get('top10'),
                           'sym': l.get('symbol'), 'tag': (l.get('bought') or {}).get('tag'), 'wx': (weather_ or {}).get('regime'), 'warden': (sized or {}).get(m)}
        if abs(_f(p.get('entry')) - entry) > entry * 1e-6:   # a rebuy / top-up moved the book entry: the peak is measured from the new one
            p.update(entry=entry, peak=pct, low=pct, path=[])
        p['peak'], p['low'] = max(_f(p.get('peak')), pct), min(_f(p.get('low')), pct)
        if not p['path'] or now - _f(p.get('pathAt')) >= 45:
            p['path'] = (list(p['path']) + [round(pct, 2)])[-PATH_KEEP:]; p['pathAt'] = now
        p['pct'] = round(pct, 2)
        held = (now - _f(p['since'])) / 60
        lq1 = _f(l.get('liqNow')) or _f((x or {}).get('nums', {}).get('liq'))
        lq0 = _f(p.get('liq0'))
        top1, top0 = v.get('top10'), p.get('top0')
        lean = None if not x else _f(x['why']['lean'])
        n = (x or {}).get('nums') or {}
        broke = None
        if not x:
            broke = 'off their radar'
        elif x['trigger'][0] == 'skip':
            broke = x['trigger'][1] or 'Trigger says SKIP'
        elif lean < 0:
            broke = f'lean turned {lean:+.1f}'
        elif _f(n.get('d5')) <= -3:
            broke = f"{_f(n['d5']):+.1f}% in 5 min"
        elif n.get('buy') is not None and _f(n['buy']) < 50:
            broke = f"buyers down to {_f(n['buy']):.0f}%"
        tp = (tape or {}).get(l.get('pairAddress'))
        ch = (charts or {}).get(m)
        if not p.get('thesis') and (theses or {}).get(m):
            p['thesis'] = dict((theses or {})[m])    # 🧾 the entry thesis: saved ONCE with the position (its own copy), never rewritten
        th = p.get('thesis')
        stop = min(_f(th['stopPct']), T('stopPct')) if th and th.get('stopPct') else T('stopPct')   # this entry's own stop, never wider than the tunable ceiling
        rv = _ci.review(th, ch, pct, held, p.get('granted')) if th else None
        if rv and rv['window'] > int(p.get('lastWin') or 0):   # a 5-minute checkpoint: a thesis that still stands EARNS the next window (bounded)
            p['lastWin'] = rv['window']
            if rv['verdict'] == 'valid':
                p['granted'] = min(int(th.get('maxHoldWindows') or _ci.MAX_WINDOWS), max(int(rv['granted']), rv['window'] + 1))
        granted = int(p.get('granted') or (th or {}).get('expectedHoldWindows') or _ci.MIN_WINDOWS)
        mine = _ag.is_agent(l)   # R5 / R8 / R9 act only on coins the agents put there (their read is the reason it is held); every coin gets R1–R4 + R7
        st, rule, ev, act = 'HOLD', 'R10 hold', f"{pct:+.1f}% · peak {p['peak']:+.1f}% · take line +{take:g}%", None
        if lq0 > 0 and 0 < lq1 < lq0 * _ag.DRAIN_PULL:
            st, rule, ev, act = 'EXIT INVALIDATED', 'R1 liquidity collapse', f'pool ${lq1 / 1000:.1f}K = {round(lq1 / lq0 * 100)}% of its ${lq0 / 1000:.1f}K entry depth', 'pull'
        elif v.get('safe') is False or _f(v.get('rug')) >= RUG_EXIT:
            st, rule, ev, act = 'EXIT INVALIDATED', 'R2 hard invalidation', 'the holder scan now fails' if v.get('safe') is False else f"rug meter {_f(v.get('rug')):.0f} ≥ {RUG_EXIT:g}", 'pull'
        elif top1 is not None and top0 is not None and _f(top1) >= 30 and _f(top1) - _f(top0) >= TOP10_JUMP:
            st, rule, ev, act = 'EXIT INVALIDATED', 'R3 holders concentrating', f'top-10 {_f(top0):.0f}% → {_f(top1):.0f}% since entry', 'pull'
        elif tp == 'dump' and (pct > 0 or (n.get('buy') is not None and _f(n['buy']) < 45)):
            st, rule, ev, act = ('TAKE' if pct > 0 else 'EXIT INVALIDATED'), 'R4 whale dump', f"the tape reads a dump at {pct:+.1f}%" + (f", buyers {_f(n['buy']):.0f}%" if n.get('buy') is not None else ''), 'pull'
        elif pct <= -_ci.CATASTROPHIC_STOP:   # 🧱 the hard ceiling, every coin Reaper watches — a constant: no tunable, promotion or thesis reaches it
            st, rule, ev, act = 'EXIT INVALIDATED', 'R5x catastrophic stop', f'{pct:+.1f}% ≤ −{_ci.CATASTROPHIC_STOP:g}% (hard-coded)', 'pull'
        elif mine and pct <= -stop:   # their own coins carry no card stop (ride-or-rug seats) — this is it; other coins keep the card's own stop
            st, rule, ev, act = 'EXIT INVALIDATED', 'R5 stop', f"{pct:+.1f}% ≤ −{stop:g}%" + (f" ({'; '.join((th.get('stopParts') or [])[:2])})" if th else ' (no thesis on file: the ceiling)'), 'pull'
        elif pct >= take:
            st, rule, ev = 'TAKE', 'R6 take line', f"{pct:+.1f}% ≥ +{take:g}% ({tsrc} take) — the card's own take rule banks it"
        elif mine and rv and rv['verdict'] == 'invalid' and held >= 2:   # the reason it was bought is gone: out, green or red — P&L does not decide this
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R5t thesis invalidated', f"{pct:+.1f}% — entered on {th.get('structure')}; now {rv['why'][0]}", 'pull'
        elif p['peak'] >= T('protectAt') and pct <= p['peak'] * (1 - T('giveBackPct') / 100) and pct >= MIN_KEEP:
            st, rule, ev, act = 'TAKE', 'R7 trailing protection', f"peaked {p['peak']:+.1f}%, now {pct:+.1f}% — gave back over {T('giveBackPct'):g}% of it", 'pull'
        elif mine and rv and rv['verdict'] == 'weak' and 'lower high' in rv['why'][0] and pct >= MIN_KEEP:   # green is not a reason to keep holding
            st, rule, ev, act = 'TAKE', 'R7s structure turned', f"{pct:+.1f}% and {rv['why'][0]} — banked before it is given back", 'pull'
        elif mine and rv and rv['window'] >= granted and rv['verdict'] == 'weak' and pct < take:   # its windows are used up and the chart earned no more
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R9 windows used', f"{rv['window']} of {granted} five-minute windows used, {pct:+.1f}%, {rv['why'][0]}", 'pull'
        elif mine and held >= MOMENTUM_MIN and broke and pct >= MIN_KEEP:
            st, rule, ev, act = 'TAKE', 'R8 momentum failed', f'{pct:+.1f}% and {broke} after {held:.0f} min — banked while it is still a gain', 'pull'
        elif mine and not th and held >= T('timeMaxMin') and broke and pct < take / 2:
            st, rule, ev, act = 'EXIT INVALIDATED', 'R9 time', f"{held:.0f} min held, {pct:+.1f}%, {broke} — no read left to wait on", 'pull'
        elif tp == 'dump':
            st, rule, ev = 'PROTECT', 'R4 whale dump', f'the tape reads a dump at {pct:+.1f}% — buyers still hold it'
        elif held >= MOMENTUM_MIN and broke:
            st, rule, ev = 'PROTECT', 'R8 momentum failed', f'{pct:+.1f}% and {broke} — it gives its seat to the next cleared read'
        elif p['peak'] >= T('protectAt'):
            st, rule, ev = 'PROTECT', 'R7 trailing protection', f"armed at peak {p['peak']:+.1f}%: banks under {max(MIN_KEEP, p['peak'] * (1 - T('giveBackPct') / 100)):+.1f}%"
        if st == 'HOLD' and rv and rv['verdict'] == 'valid':
            ev = f"{pct:+.1f}% · {'; '.join(rv['why'][:4])} · window {rv['window'] + 1} of {granted}"
        if act:
            p.setdefault('askAt', now); p['askRule'] = rule
        p['state'], p['rule'] = st, rule
        p['chartNow'] = (ch or {}).get('state')
        decision = ('TAKE PROFIT' if st == 'TAKE' else 'EXIT') if act or rule.startswith('R6') else 'PROTECT' if st == 'PROTECT' else 'HOLD 5 MORE' if rv and rv['verdict'] == 'valid' and rv['window'] >= 1 else 'HOLD'
        pos[m] = p
        out.append({**base, 'state': st, 'rule': rule, 'evidence': ev, 'action': act, 'exec': 'confirmed', 'entry': entry, 'px': px, 'pct': round(pct, 2), 'peak': round(p['peak'], 2),
                    'dd': round(p['peak'] - pct, 2), 'heldMin': round(held, 1), 'liq': lq1 or None, 'liqPct': round(lq1 / lq0 * 100) if lq0 > 0 and lq1 > 0 else None,
                    'top10': top1, 'top10D': round(_f(top1) - _f(top0), 1) if top1 is not None and top0 is not None else None, 'lean': lean,
                    'trigger': (x or {}).get('trigger', [None])[0], 'devil': ((x or {}).get('case') or (x or {}).get('devil') or [None])[0], 'weather': (weather_ or {}).get('regime'),
                    'take': take, 'takeSource': tsrc, 'stop': -stop, 'hardStop': -_ci.CATASTROPHIC_STOP, 'decision': decision, 'obeying': (f'{tsrc} take' if rule.startswith('R6') else OBEY.get(rule.split(' ')[0], 'thesis hold')),
                    'thesis': None if not th else {k: th.get(k) for k in ('structure', 'call', 'triggerRule', 'why', 'support', 'invalidation', 'stopPct', 'expectedHoldWindows', 'maxHoldWindows', 'reasons', 'risks', 'at')},
                    'structure': (ch or {}).get('state'), 'chartSrc': (ch or {}).get('src'), 'verdict': (rv or {}).get('verdict'), 'why': (rv or {}).get('why') or [], 'window': (rv or {}).get('window'), 'granted': granted if th else None,
                    'nextReview': (rv or {}).get('next') if rv else round((int(held // _ci.WINDOW_MIN) + 1) * _ci.WINDOW_MIN * 60 - held * 60),
                    'chart': None if not ch else {k: ch.get(k) for k in ('trend', 'chop', 'mom', 'ext')} | {k: (ch.get('f') or {}).get(k) for k in ('hh', 'hl', 'lh', 'll', 'lastHigh', 'lastLow', 'accel', 'decay', 'upWick', 'liqD')},
                    'tape': tp, 'usd': round(_f(l.get('units')) * px, 4), 'warden': p.get('warden')})
    gone = []
    for m in [m for m in pos if m not in on]:
        p = pos.pop(m)
        gone.append({**p, 'mint': m, 'leftAt': now})
    return pos, out, gone


def merge_reaper(decisions, reports):
    """Reaper's requests join the card's EXISTING agent decisions (the list `agents.manage` returns and the service already acts on): a
    coin the desk would hold is pulled when Reaper asks; a swap / pull the desk already decided stands. No new action kind exists."""
    out = list(decisions or [])
    for r in reports or []:
        if r.get('action') != 'pull':
            continue
        i = next((i for i, d in enumerate(out) if d.get('pair') == r['pair']), None)
        d = {'pair': r['pair'], 'symbol': r.get('symbol'), 'action': 'pull', 'why': f"☠ Reaper {r['rule']}: {r['evidence']}", 'reaper': r['rule']}
        if i is None:
            out.append(d)
        elif out[i].get('action') == 'hold':
            out[i] = d
    return out


def confirm_exits(exiting, gone, ledger, now, card=None):
    """📮→☠ A position that left the card is 'exit requested' until the keeper's ledger shows the confirmed sale; only then is it CLOSED
    with the real result. Not confirmed after EXIT_WAIT_SEC → filed as unconfirmed (no result claimed). → (still exiting, closed)"""
    ex = list(exiting or []) + [{**g, 'exit': {'state': 'requested'}} for g in gone or []]
    still, closed = [], []
    for p in ex:
        f = fill_state(ledger, p['mint'], 'sell', _f(p.get('askAt') or p.get('leftAt')) - 120, card)
        if f['state'] == 'confirmed':
            closed.append({**p, 'exit': f, 'confirmed': True, 'realPct': f.get('realPct'), 'closedAt': f['at']})
        elif now - _f(p.get('leftAt')) >= EXIT_WAIT_SEC:
            closed.append({**p, 'exit': {**f, 'state': 'unconfirmed'}, 'confirmed': False, 'realPct': None, 'closedAt': now})
        else:
            still.append({**p, 'exit': {**f, 'state': 'requested' if f['state'] == 'none' else f['state']}})
    return still, closed


# ── 🗄 ARCHIVIST ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────
ARCH_CASES, ARCH_POS, CASE_GAP = 600, 300, 1800


def _hash(prev, rec):
    return hashlib.sha1((str(prev) + json.dumps(rec, sort_keys=True, default=str)).encode()).hexdigest()[:16]


def _fold(agg, c):
    """A case leaving the bounded list is folded into the totals (never just dropped): by regime · cleared / blocked · action."""
    o = c.get('out') or {}
    for k in (f"wx:{(c['d'].get('weather') or {}).get('regime')}", 'cleared' if c['d'].get('cleared') else 'blocked', f"act:{c['d'].get('action') or 'none'}"):
        a = agg.setdefault(k, {'n': 0, 'judged': 0, 'sum5': 0.0, 'up': 0, 'rug': 0})
        a['n'] += 1
        if o.get('p5') is not None:
            a['judged'] += 1; a['sum5'] = round(a['sum5'] + _f(o['p5']), 2); a['up'] += _f(o['p5']) > 0; a['rug'] += _f(o['p5']) <= -50 or o.get('p60') == -100.0
    return agg


def file_case(arch, d, now):
    """File one decision lineage (what every agent said about a coin at decision time). The decision part `d` is hash-chained to the
    record before it and is never written again; the outcome is added beside it later. One case per coin per 30 min, unless it carries
    a real action. → archive"""
    a = dict(arch or {})
    cases = list(a.get('cases') or [])
    if not d.get('action') and any(c['d'].get('mint') == d.get('mint') and now - _f(c['at']) < CASE_GAP for c in cases[-80:]):
        return a
    prev = cases[-1]['h'] if cases else a.get('anchor', '')
    cases.append({'at': now, 'd': d, 'h': _hash(prev, d), 'out': {}})
    a['filed'] = int(a.get('filed') or 0) + 1
    agg = dict(a.get('agg') or {})
    while len(cases) > ARCH_CASES:
        old = cases.pop(0)
        agg = _fold({k: dict(v) for k, v in agg.items()}, old); a['anchor'] = old['h']
    a.update(cases=cases, agg=agg)
    return a


def settle_cases(arch, price_of, now):
    """The outcome of every filed case at 5 and 60 minutes at the live price (no price at 60 = −100%: it vanished), plus its best and
    worst reading on the way. Only `out` is written — never the decision. → archive"""
    a = dict(arch or {})
    cases = []
    for c in a.get('cases') or []:
        o, age = dict(c.get('out') or {}), (now - _f(c['at'])) / 60
        if 'p60' not in o and _f(c['d'].get('px')) > 0:
            px = _f(price_of(c['d'].get('mint')))
            if px > 0:
                pc = round((px / _f(c['d']['px']) - 1) * 100, 2)
                o['max'], o['min'] = max(_f(o.get('max')), pc), min(_f(o.get('min')), pc)
                if 'p5' not in o and age >= 5:
                    o['p5'] = pc
            if age >= 60:
                o['p60'] = round((px / _f(c['d']['px']) - 1) * 100, 2) if px > 0 else -100.0
                o.setdefault('p5', o['p60'] if px <= 0 else None)
            c = {**c, 'out': o}
        cases.append(c)
    a['cases'] = cases
    return a


def file_position(arch, p, now):
    """A closed real position: its path, peak, low, the rule that asked for the exit, whether the exit is confirmed and the REAL result
    from the ledger. Losses are filed exactly like wins; what rotates out is counted in `posAgg`."""
    a = dict(arch or {})
    ps = list(a.get('positions') or [])
    rec = {'mint': p.get('mint'), 'sym': p.get('sym'), 'since': p.get('since'), 'closedAt': p.get('closedAt') or now, 'entry': p.get('entry'), 'peak': round(_f(p.get('peak')), 2),
           'low': round(_f(p.get('low')), 2), 'lastPct': p.get('pct'), 'path': list(p.get('path') or [])[-PATH_KEEP:], 'rule': p.get('askRule') or 'left the card by another rule',
           'byReaper': bool(p.get('askRule')), 'confirmed': bool(p.get('confirmed')), 'realPct': p.get('realPct'), 'exit': {k: v for k, v in (p.get('exit') or {}).items() if k in ('state', 'sig', 'at', 'usd', 'delta', 'realUsd', 'err')},
           'wx': p.get('wx'), 'warden': p.get('warden'), 'tag': p.get('tag'), 'take': p.get('take'), 'exitStructure': p.get('chartNow'), 'windows': p.get('lastWin'),
           'thesis': None if not p.get('thesis') else {k: p['thesis'].get(k) for k in ('structure', 'call', 'triggerRule', 'support', 'invalidation', 'stopPct', 'expectedHoldWindows', 'at')}}
    prev = ps[-1]['h'] if ps else a.get('posAnchor', '')
    rec['h'] = _hash(prev, {k: v for k, v in rec.items() if k != 'h'})
    ps.append(rec)
    agg = dict(a.get('posAgg') or {'n': 0, 'won': 0, 'lost': 0, 'sum': 0.0})
    while len(ps) > ARCH_POS:
        old = ps.pop(0); a['posAnchor'] = old['h']
        if old.get('realPct') is not None:
            agg = {'n': agg['n'] + 1, 'won': agg['won'] + (_f(old['realPct']) > 0), 'lost': agg['lost'] + (_f(old['realPct']) <= 0), 'sum': round(agg['sum'] + _f(old['realPct']), 2)}
    a.update(positions=ps, posAgg=agg)
    return a


def verify(arch):
    """How many filed records no longer match their hash chain (0 = nothing was rewritten)."""
    bad, prev = 0, (arch or {}).get('anchor', '')
    for c in (arch or {}).get('cases') or []:
        bad += c.get('h') != _hash(prev, c.get('d')); prev = c.get('h')
    prev = (arch or {}).get('posAnchor', '')
    for p in (arch or {}).get('positions') or []:
        bad += p.get('h') != _hash(prev, {k: v for k, v in p.items() if k != 'h'}); prev = p.get('h')
    return bad


def _stat(ps):
    ps = [_f(p) for p in ps if p is not None]
    return {'n': len(ps), 'med': round(_med(ps), 2) if ps else None, 'avg': round(sum(ps) / len(ps), 2) if ps else None, 'up': round(sum(1 for p in ps if p > 0) / len(ps) * 100) if ps else None}


PATTERN_N = 5


def patterns(arch, state=None):
    """🧠 What the stored records say — each line is computed from them and carries its sample count; under PATTERN_N it is not stated.
    → [{agent, text, n, value}]"""
    out = []
    add = lambda agent, text, s, value=None: s['n'] >= PATTERN_N and out.append({'agent': agent, 'text': text, 'n': s['n'], 'value': s['med'] if value is None else value})
    cases = [c for c in (arch or {}).get('cases') or [] if (c.get('out') or {}).get('p5') is not None]
    g = {}
    for c in cases:
        g.setdefault((c['d'].get('weather') or {}).get('regime') or '—', []).append(c['out']['p5'])
    for k, v in sorted(g.items()):
        s = _stat(v); s['n'] >= PATTERN_N and add('weather', f"in {k} weather our filed cases read {s['med']:+.1f}% typical at 5 min ({s['up']}% up)", s)
    cl, bl = _stat([c['out']['p5'] for c in cases if c['d'].get('cleared')]), _stat([c['out']['p5'] for c in cases if not c['d'].get('cleared')])
    if cl['n'] >= PATTERN_N and bl['n'] >= PATTERN_N:
        out.append({'agent': 'devil', 'text': f"cases the checks cleared read {cl['med']:+.1f}% at 5 min vs {bl['med']:+.1f}% for the ones they blocked", 'n': cl['n'] + bl['n'], 'value': round(cl['med'] - bl['med'], 2)})
    for lab, lo, hi in (('under 1h old', 0, 1), ('1–6h old', 1, 6), ('6h+ old', 6, 1e9)):
        s = _stat([c['out']['p5'] for c in cases if (c['d'].get('trigger') or [None])[0] == 'enter' and c['d'].get('ageH') is not None and lo <= _f(c['d']['ageH']) < hi])
        s['n'] >= PATTERN_N and add('trigger', f"Trigger's ENTER on coins {lab}: {s['med']:+.1f}% typical at 5 min ({s['up']}% up)", s)
    for lab, lo, hi in (('lean under 1', -99, 1), ('lean 1–2', 1, 2), ('lean 2+', 2, 99)):
        s = _stat([c['out']['p5'] for c in cases if lo <= _f((c['d'].get('sherlock') or {}).get('lean')) < hi])
        s['n'] >= PATTERN_N and add('sherlock', f"Sherlock {lab}: {s['med']:+.1f}% typical at 5 min ({s['up']}% up)", s)
    for r in devil_record(state):
        if r['n'] >= PATTERN_N and r['saved'] is not None:
            out.append({'agent': 'devil', 'text': f"objection '{r['rule']}' was followed by a flat or losing 5 min {r['saved']}% of the time ({r['med']:+.1f}% typical)", 'n': r['n'], 'value': r['saved']})
    for r in structure_record(state):
        if r['n'] >= PATTERN_N:
            out.append({'agent': 'sherlock', 'n': r['n'], 'value': r['med5'], 'text': f"{r['state']} calls: median 5m {r['med5']:+.1f}%" + (f", 15m {r['med15']:+.1f}%" if r['med15'] is not None else '')
                        + (f", 60m {r['med60']:+.1f}%" if r['med60'] is not None else '') + (f" — best window {r['best']}m" if r['best'] else '')})
    late = [d for d in _ag._judged(state, 5) if d.get('ce') == 'ENTER NOW' and d.get('kind') == 'enter']
    if len(late) >= PATTERN_N:
        n_late = sum(1 for d in late if _f(d['p5']) < 0 and max([_f(x) for x in d.get('path') or [0]]) < 1.0)
        out.append({'agent': 'trigger', 'n': len(late), 'value': round(n_late / len(late) * 100), 'text': f"Trigger entered too late {round(n_late / len(late) * 100)}% of the time (ENTER NOW that never went +1% and closed red at 5 min)"})
    pos = [p for p in (arch or {}).get('positions') or [] if p.get('confirmed') and p.get('realPct') is not None]
    gave = [_f(p['peak']) - _f(p['realPct']) for p in pos if p.get('byReaper') and _f(p.get('peak')) > 1]
    if len(gave) >= PATTERN_N:
        out.append({'agent': 'reaper', 'n': len(gave), 'value': round(sum(gave) / len(gave), 1), 'text': f"Reaper surrendered {sum(gave) / len(gave):.1f} points of peak gain on average before its exits filled"})
    g = {}
    for p in pos:
        if (p.get('thesis') or {}).get('structure'):
            g.setdefault(p['thesis']['structure'], []).append(p['realPct'])
    for k, v in sorted(g.items()):
        s = _stat(v); s['n'] >= PATTERN_N and add('archivist', f"real entries on {k}: {s['avg']:+.1f}% real on average ({s['up']}% won)", s, s['avg'])
    g = {}
    for p in pos:
        g.setdefault(p.get('rule') or '—', []).append(p)
    for k, v in sorted(g.items()):
        s = _stat([p['realPct'] for p in v])
        kept = [_f(p['realPct']) / _f(p['peak']) * 100 for p in v if _f(p.get('peak')) > 1]
        s['n'] >= PATTERN_N and add('reaper', f"exits by '{k}': {s['avg']:+.1f}% real on average" + (f", kept {sum(kept) / len(kept):.0f}% of the peak gain" if kept else ''), s, s['avg'])
    g = {}
    for p in pos:
        if p.get('warden') is not None:
            g.setdefault(f"{_f(p['warden']):g}×", []).append(p['realPct'])
    for k, v in sorted(g.items()):
        s = _stat(v); s['n'] >= PATTERN_N and add('warden', f"seats sized {k}: {s['avg']:+.1f}% real on average ({s['up']}% won)", s, s['avg'])
    g = {}
    for p in pos:
        if (p.get('exit') or {}).get('delta') is not None:
            g.setdefault('exit fills', []).append(p['exit']['delta'])
    for k, v in g.items():
        s = _stat(v); s['n'] >= PATTERN_N and add('courier', f"confirmed exits filled {s['med']:+.2f}% from the mid price (typical)", s)
    return out


def structure_record(state):
    """📈 What each market-structure call was REALLY followed by (the desk's own judged calls carry the structure read at decision time,
    `cs`): n, median at 5 / 15 / 60 min, the window with the best median. → [{state, n, med5, med15, med60, best, up}]"""
    g = {}
    for d in _ag._judged(state, 5):
        if d.get('cs') and d['cs'] != 'UNKNOWN':   # an unread chart is not a structure call
            g.setdefault(d['cs'], []).append(d)
    out = []
    for k, ds in g.items():
        med = lambda h: (lambda xs: round(_med(xs), 2) if len(xs) >= PATTERN_N else None)([_f(d[f'p{h}']) for d in ds if d.get(f'p{h}') is not None])
        m5, m15, m60 = med(5), med(15), med(60)
        best = max(((h, v) for h, v in ((5, m5), (15, m15), (60, m60)) if v is not None), key=lambda t: t[1], default=(None, None))[0]
        out.append({'state': k, 'n': len(ds), 'med5': m5 if m5 is not None else round(_med([_f(d['p5']) for d in ds]), 2), 'med15': m15, 'med60': m60, 'best': best,
                    'up': round(sum(1 for d in ds if _f(d['p5']) > 0) / len(ds) * 100)})
    return sorted(out, key=lambda r: -r['n'])


# ── exposure helpers: what each of the four original desks used for ONE coin (no new logic — the same numbers, laid out) ───────────
STALE_SEC = 150


def tally_read(row, series, now):
    """📊 Tally's read of one coin: how many readings, how fresh, how far apart, which measurements are missing, where it was found."""
    n = (row or {}).get('nums') or {}
    s = list(series or [])
    age = round(now - _f(s[-1]['t']), 1) if s else None
    gaps = [_f(b['t']) - _f(a['t']) for a, b in zip(s, s[1:])]
    fields = ('d5', 'c1', 'pace', 'buy', 'liq', 'liqD', 'holdD', 'age')
    miss = [k for k in fields if n.get(k) is None]
    src = [d[0][4:] for d in ((row or {}).get('why') or {}).get('drivers') or [] if str(d[0]).startswith('src:')]
    return {'readings': int(n.get('pts') or len(s)), 'of': _ag.SERIES_N, 'ageSec': age, 'stale': age is not None and age > STALE_SEC, 'intervalSec': round(sum(gaps) / len(gaps), 1) if gaps else None,
            'missing': miss, 'sources': [_ag.SOURCES.get(k, k) for k in src], 'confidence': round(min(1.0, int(n.get('pts') or 0) / 5) * (len(fields) - len(miss)) / len(fields), 2),
            'nums': {k: n.get(k) for k in fields}}


def scan_status(safe, inflight=False, failed_at=0.0, scanned_at=0.0, now=0.0, ttl=900):
    """🔍 Where a coin's holder scan stands: DONE · STALE (older than its TTL) · RUNNING · FAILED (the last try failed) · REQUESTED."""
    if inflight:
        return 'RUNNING'
    if safe is not None:
        return 'STALE' if scanned_at and now - scanned_at > ttl else 'DONE'
    if failed_at and now - failed_at < 120:
        return 'FAILED'
    return 'REQUESTED'


def sherlock_read(row, learned=None):
    """🔍 Sherlock's case on one coin: each reason with its weight and its own record, the evidence against, what is still unknown."""
    why = (row or {}).get('why') or {}
    ld = (learned or {}).get('drivers') or {}
    rs = [{'key': d[0], 'weight': d[1], 'words': d[2], 'n': int((ld.get(d[0]) or {}).get('n') or 0), 'med': (ld.get(d[0]) or {}).get('med')} for d in why.get('drivers') or []]
    v = (row or {}).get('vitals') or {}
    unk = [w for k, w in (('safe', 'holders not scanned'), ('ageH', 'age unknown'), ('top10', 'top-10 share unknown'), ('bundledN', 'bundles unknown'), ('organic', 'organic share unknown')) if v.get(k) is None]
    return {'lean': why.get('lean'), 'for': [r for r in rs if _f(r['weight']) > 0][:6], 'against': [r for r in rs if _f(r['weight']) < 0][:6],
            'earned': round(_ag.learned_share([d[0] for d in why.get('drivers') or []], learned or {}) * 100) if why.get('drivers') else None, 'unresolved': unk,
            'vitals': {k: v.get(k) for k in ('safe', 'ageH', 'liq', 'top10', 'bundledN', 'snipersN', 'dev', 'organic', 'rug', 'read')}}


def trigger_checks(row, perf=None):
    """⏱ Trigger's checks on one coin, each with its evidence — the same lines `agents.trigger` rules by, in the same order."""
    n, v, why = (row or {}).get('nums') or {}, (row or {}).get('vitals') or {}, (row or {}).get('why') or {}
    bar = _f((perf or {}).get('bar') or 1.5)
    need = 5 if (perf or {}).get('trial') == 'tally' else 3
    d5, liq = _f(n.get('d5')), _f(n.get('liq'))
    return [['scan', v.get('safe') is not False, 'holder scan did not fail' if v.get('safe') is not False else 'failed the holder scan', True],
            ['pool', not (0 < liq < 20_000), f'pool ${liq / 1000:.0f}K', True], ['top', d5 <= 15, f'{d5:+.1f}% in 5 min (≤ +15)', True], ['fall', d5 >= -8, f'{d5:+.1f}% in 5 min (≥ −8)', True],
            ['readings', int(n.get('pts') or 0) >= need, f"{int(n.get('pts') or 0)} of {need} readings", False],
            ['lean', _f(why.get('lean')) >= bar, f"lean {_f(why.get('lean')):+.1f} vs bar {bar:.2f}", False],
            ['buyers', n.get('buy') is None or _f(n['buy']) >= 55, 'buyers unknown' if n.get('buy') is None else f"buyers {_f(n['buy']):.0f}% (≥ 55)", False]] + (
        [] if not (row or {}).get('chart') else [['structure', row['chart']['entry'][0] != 'SKIP', f"{row['chart']['state']} ({row['chart']['src']}, {row['chart']['n']} candles)", True],
                                                 ['moment', row['chart']['entry'][0] == 'ENTER NOW', f"{row['chart']['entry'][0]} — {row['chart']['entry'][1]}", False]])


def devil_record(state, hours=72, now=0.0):
    """⚖ Every objection TYPE with its own history: how often it was raised and what those coins did 5 minutes later (saved = flat or
    down). Old calls without a stored rule id are read from their text. → [{rule, hard, n, med, saved}]"""
    g = {}
    for d in list(((state or {}).get('open') or {}).values()) + list((state or {}).get('done') or []):
        if d.get('devil') != 'object' or (now and now - _f(d.get('at')) > hours * 3600):
            continue
        g.setdefault(d.get('devilRule') or (_ag.devil_rule_of(d['devilWhy']) if d.get('devilWhy') else 'unrecorded'), []).append(d.get('p5'))
    out = []
    for k, v in g.items():
        ps = [_f(p) for p in v if p is not None]
        out.append({'rule': k, 'hard': _ag.DEVIL_RULES.get(k, (False, ''))[0], 'what': _ag.DEVIL_RULES.get(k, (False, k))[1], 'n': len(v), 'med': round(_med(ps), 1) if ps else None,
                    'saved': round(sum(1 for p in ps if p <= 0) / len(ps) * 100) if ps else None})
    return sorted(out, key=lambda r: -r['n'])


# ── 👨‍⚖️ JUDGE: one scorecard per agent ────────────────────────────────────────────────────────────────────────────────────────────
def lat(samples):
    s = sorted(_f(x) for x in samples or [])
    if not s:
        return {'last': None, 'p50': None, 'p95': None, 'max': None, 'n': 0}
    return {'last': round(_f(samples[-1]), 2), 'p50': round(s[len(s) // 2], 2), 'p95': round(s[min(len(s) - 1, int(len(s) * 0.95))], 2), 'max': round(s[-1], 2), 'n': len(s)}


def standing(n, acc, violations=0, unsafe=False):
    """The Judge's verdict on ONE record. Under JUDGE_MIN_N samples nothing but 'alive' is possible — one or two outcomes decide
    nothing. → (status alive | probation | demoted, why)"""
    n = int(_f(n))
    if n < JUDGE_MIN_N:
        return 'alive', f'{n} of {JUDGE_MIN_N} samples — not enough to judge'
    if unsafe and n >= JUDGE_DEMOTE_N:
        return 'demoted', f'unsafe risk behaviour over {n} samples'
    if violations and acc is None:
        return 'probation', f'{violations} rule violation(s) on record'
    if acc is not None and _f(acc) < JUDGE_BAD:
        return ('demoted', f'{_f(acc):.0f}% right over {n} samples — its edge has degraded') if n >= JUDGE_DEMOTE_N else ('probation', f'{_f(acc):.0f}% right over {n} samples (demoted at {JUDGE_DEMOTE_N} if it stays)')
    if violations:
        return 'probation', f'{violations} rule violation(s) on record'
    return 'alive', f"{_f(acc):.0f}% right over {n} samples" if acc is not None else f'{n} samples, no accuracy measure yet'


def _score(n, acc, viol=0, stale=0):
    conf = int(_f(n)) / (int(_f(n)) + 30)
    return round(_clamp(50 + ((_f(acc) if acc is not None else 50) - 50) * conf - 10 * viol - min(10, stale), 0, 100)), round(conf, 2)


def scorecards(state, arch, office, real=None, courier_=None):
    """👨‍⚖️ Every agent on its OWN record — the four desks from their judged calls of this life, Weather / Warden / Reaper from the
    archive, Courier from the ledger, the Archivist from its hash chain, the Judge from whether its rulings held up at 15 minutes."""
    st, of, ar = state or {}, office or {}, arch or {}
    born = st.get('born') or {}
    js = _ag._judged(st, 5)
    life = lambda a: [d for d in js if _f(d.get('at')) >= _f(born.get(a))]
    sv, jd = _ag.survival(st), _ag.judge(st)
    lr = _ag.learn(st, 5)
    viol, lats, gen = of.get('viol') or {}, of.get('lat') or {}, of.get('gen') or {}
    out = {}

    def put(a, n, acc, status=None, why=None, **k):
        v = int(_f((viol.get(a) or {}).get('rule')))
        stale = int(_f((viol.get(a) or {}).get('stale')))
        sc, conf = _score(n, acc, v, stale / 50)
        s_, w_ = (status, why) if status else standing(n, acc, v, k.pop('unsafe', False))
        out[a] = {'n': int(_f(n)), 'accuracy': None if acc is None else round(_f(acc)), 'confidence': conf, 'survival': sc, 'status': s_, 'why': w_, 'violations': v, 'stale': stale,
                  'gen': int((st.get('gen') or {}).get(a) or gen.get(a) or 1), 'latency': lat(lats.get(a)),
                  'fp': k.pop('fp', None), 'fn': k.pop('fn', None), 'missed': k.pop('missed', None), 'badApprovals': k.pop('badApprovals', None), 'usefulVetoes': k.pop('usefulVetoes', None),
                  'profit': k.pop('profit', None), 'loss': k.pop('loss', None), 'drawdown': k.pop('drawdown', None), **k}

    cb = lambda a, key: round(sum(_f(r['pct']) for r in jd['rulings'] if r.get(key) == a), 1)
    for a in ('tally', 'sherlock', 'trigger', 'devil'):
        d, c, s = life(a), lr['cards'][a], sv[a]
        ent = [x for x in d if x.get('kind') == 'enter']
        k = {'profit': cb(a, 'credit'), 'loss': cb(a, 'blame'), 'unit': '% pts on the rulings shown (5-min calls)'}
        if a == 'tally':
            k.update(fp=sum(1 for x in d if x.get('tallyUp') and _f(x['p5']) <= -3), fn=sum(1 for x in d if not x.get('tallyUp') and _f(x['p5']) >= 3))
        elif a == 'sherlock':
            k.update(fp=sum(1 for x in d if _f(x.get('lean')) > 0 and _f(x['p5']) <= -3), fn=sum(1 for x in d if _f(x.get('lean')) <= 0 and _f(x['p5']) >= 3))
        elif a == 'trigger':
            k.update(fp=sum(1 for x in ent if _f(x['p5']) <= -3), missed=sum(1 for x in d if x.get('kind') == 'wait' and _f(x['p5']) >= _ag.JUDGE_MISS),
                     drawdown=round(min([_f(x['p5']) for x in ent] or [0.0]), 1))
        else:
            k.update(badApprovals=sum(1 for x in ent if x.get('devil') == 'agree' and _f(x['p5']) <= -3), usefulVetoes=sum(1 for x in ent if x.get('devil') == 'object' and _f(x['p5']) <= 0),
                     fp=sum(1 for x in ent if x.get('devil') == 'object' and _f(x['p5']) >= 3))
        cd = [x for x in d if x.get('cs') and x['cs'] != 'UNKNOWN']   # 📈 chart-reading, judged only on what was known at the call (the structure stored WITH the call) vs what followed
        if a == 'sherlock' and cd:
            ok_ = sum(1 for x in cd if (_f(x['p5']) > 0) == (x['cs'] in _ci.BULL))
            k.update(chartN=len(cd), chartRight=round(ok_ / len(cd) * 100))
        if a == 'trigger':
            en = [x for x in cd if x.get('ce') == 'ENTER NOW' and x.get('kind') == 'enter']
            wt = [x for x in cd if x.get('ce') and x['ce'].startswith('WAIT') and x.get('kind') == 'wait']
            k.update(chartN=len(en), chartRight=round(sum(1 for x in en if _f(x['p5']) > 0) / len(en) * 100) if en else None,
                     waitedRight=round(sum(1 for x in wt if _f(x['p5']) <= 0) / len(wt) * 100) if wt else None, waitedN=len(wt))
        if a == 'devil':
            co = [x for x in ent if str(x.get('devilRule') or '').startswith('chart_')]
            k.update(chartN=len(co), chartRight=round(sum(1 for x in co if _f(x['p5']) <= 0) / len(co) * 100) if co else None)
        acc = c['won'] if a == 'trigger' else c['right']
        why = {'alive': f"{acc if acc is not None else '—'}% right over {s['n']} calls this life", 'probation': f"under {_ag.SURVIVE_RIGHT}% right over {s['n']} calls — scrapped at {_ag.SCRAP_N}",
               'scrap': f"still under {_ag.SURVIVE_RIGHT}% right at {s['n']} calls — reborn next pass"}[s['status']]
        if jd['trial'] == a:
            why += f" · on trial: {jd['handicap']}"
        put(a, s['n'], acc, s['status'] if s['status'] != 'scrap' else 'retired', why, **k)
    cases = [c for c in ar.get('cases') or [] if (c.get('out') or {}).get('p5') is not None and (c['d'].get('weather') or {}).get('regime')]
    ok = lambda c: (_f(c['out']['p5']) > 0) == (c['d']['weather']['regime'] in ('HOT', 'NORMAL'))
    put('weather', len(cases), round(sum(1 for c in cases if ok(c)) / len(cases) * 100) if cases else None,
        fp=sum(1 for c in cases if c['d']['weather']['regime'] in ('HOT', 'NORMAL') and _f(c['out']['p5']) <= -3), fn=sum(1 for c in cases if c['d']['weather']['regime'] not in ('HOT', 'NORMAL') and _f(c['out']['p5']) >= 3),
        unit='filed cases judged at 5 min')
    pos = [p for p in ar.get('positions') or [] if p.get('confirmed') and p.get('realPct') is not None]
    cut = [p for p in pos if p.get('warden') is not None and _f(p['warden']) < 1]
    useful, cost = [p for p in cut if _f(p['realPct']) <= 0], [p for p in cut if _f(p['realPct']) > 0]
    put('warden', len([p for p in pos if p.get('warden') is not None]), round(len(useful) / len(cut) * 100) if cut else None, usefulVetoes=len(useful), fp=len(cost),
        drawdown=round(sum((1 - _f(p['warden'])) * _f(p['realPct']) for p in useful), 1), profit=round(sum(_f(p['realPct']) for p in pos if p.get('warden') is not None and _f(p['realPct']) > 0), 1),
        loss=round(sum(_f(p['realPct']) for p in pos if p.get('warden') is not None and _f(p['realPct']) <= 0), 1), unit='real % on seats it sized', vetoes=int(_f((of.get('count') or {}).get('wardenVeto'))),
        sized=int(_f((of.get('count') or {}).get('wardenSized'))))
    c_ = courier_ or {}
    put('courier', c_.get('sends') or 0, round(_f(c_.get('fills')) / c_['sends'] * 100) if c_.get('sends') else None, status='alive' if not (c_.get('duplicates') or c_.get('unsigned')) else 'probation',
        why=f"{c_.get('fills') or 0} of {c_.get('sends') or 0} sends confirmed this hour · {c_.get('duplicates') or 0} duplicates · health {c_.get('health') or '—'}",
        loss=None if c_.get('deltaMed') is None else -_f(c_['deltaMed']), unit='% typical fill vs mid price', fp=c_.get('failed'))
    mine = [p for p in pos if p.get('byReaper')]
    kept = [_f(p['realPct']) / _f(p['peak']) * 100 for p in mine if _f(p.get('peak')) > 1]
    put('reaper', len(mine), round(sum(1 for p in mine if _f(p['realPct']) > 0) / len(mine) * 100) if mine else None, profit=round(sum(_f(p['realPct']) for p in mine if _f(p['realPct']) > 0), 1),
        loss=round(sum(_f(p['realPct']) for p in mine if _f(p['realPct']) <= 0), 1), drawdown=round(min([_f(p['low']) for p in mine] or [0.0]), 1), kept=round(sum(kept) / len(kept)) if kept else None,
        chartN=sum(1 for p in mine if p.get('thesis')), chartRight=(lambda th_: round(sum(1 for p in th_ if (_f(p['realPct']) > 0) == (p.get('exitStructure') in _ci.GOOD or 'take' in str(p.get('rule')).lower())) / len(th_) * 100) if th_ else None)([p for p in mine if p.get('thesis')]),
        unconfirmed=sum(1 for p in ar.get('positions') or [] if p.get('byReaper') and not p.get('confirmed')), unit='real % on exits it asked for')
    breaks = verify(ar)
    filed = len(ar.get('cases') or [])
    put('archivist', int(_f(ar.get('filed')) or filed), None if not filed else round((filed - breaks) / filed * 100), status='alive' if not breaks else 'probation',
        why=f"{int(_f(ar.get('filed')) or filed)} decisions filed · {len(ar.get('positions') or [])} positions · {breaks} hash breaks", unit='records whose hash chain holds')
    held = [d for d in js if d.get('p15') is not None and _ag.ruling(d)['verdict'] in ('win', 'loss')]
    agree = sum(1 for d in held if (_f(d['p15']) > 0) == (_f(d['p5']) > 0))
    put('judge', len(held), round(agree / len(held) * 100) if held else None, unit='rulings that still held at 15 min', fp=len(held) - agree, rulings=jd['n'], trial=jd['trial'])
    return out


# ── the learning path: Archivist evidence → Judge candidate → shadow test → evaluation → promotion ──────────────────────────────────
REAPER_GRID = {'giveBackPct': (30.0, 40.0, 50.0, 60.0, 70.0), 'protectAt': (4.0, 6.0, 8.0, 10.0, 15.0), 'stopPct': (15.0, 20.0, 25.0, 30.0, 40.0)}


def propose(office, agent, key, value, evidence, now):
    """The Judge puts ONE candidate change of a TUNABLE up for a shadow test. It must be a tunable (the constitution is not), inside its
    bounds, backed by ≥ PROPOSE_N archived records, and an agent has one candidate at a time. Nothing live changes. → office"""
    if agent not in TUNABLE or key not in TUNABLE[agent]:
        raise ValueError(f'{agent}.{key} is not a tunable parameter — the immutable core cannot be changed')
    d, lo, hi, _ = TUNABLE[agent][key]
    if not (lo <= _f(value) <= hi):
        raise ValueError(f'{agent}.{key} = {value} is outside its hard bounds {lo:g} … {hi:g}')
    if int(_f((evidence or {}).get('n'))) < PROPOSE_N:
        raise ValueError(f'a candidate needs {PROPOSE_N} archived records behind it')
    o = dict(office or {})
    cs = dict(o.get('candidates') or {})
    if any(c['agent'] == agent and c['status'] == 'shadow' for c in cs.values()):
        raise ValueError(f'{agent} already has a candidate in shadow')
    cid = f'{agent}.{key}.{int(now)}'
    cs[cid] = {'id': cid, 'agent': agent, 'key': key, 'value': _f(value), 'live': tune(o, agent, key), 'at': now, 'status': 'shadow', 'evidence': evidence, 'shadow': []}
    o['candidates'] = dict(sorted(cs.items(), key=lambda kv: -kv[1]['at'])[:12])
    return o


def evaluate(c):
    """A candidate against the live rule on the positions closed SINCE it was proposed (never the ones it was picked from)."""
    sh = list((c or {}).get('shadow') or [])
    lv, cd = [_f(x[0]) for x in sh], [_f(x[1]) for x in sh]
    n = len(sh)
    la, ca = (sum(lv) / n, sum(cd) / n) if n else (0.0, 0.0)
    return {'n': n, 'need': SHADOW_N, 'live': round(la, 2), 'cand': round(ca, 2), 'ready': n >= SHADOW_N,
            'better': n >= SHADOW_N and ca >= la + SHADOW_MARGIN and _f(_med(cd)) >= _f(_med(lv))}


def promote(office, cid, now):
    """Promotion: only a candidate whose shadow test is complete AND beat the live rule. The agent's next generation runs the new
    value; the old one goes to the lineage. Anything else raises — there is no other way to move a tunable."""
    o = dict(office or {})
    c = (o.get('candidates') or {}).get(cid)
    if not c or c['status'] != 'shadow':
        raise ValueError('no such candidate in shadow')
    e = evaluate(c)
    if not e['ready']:
        raise ValueError(f"shadow test incomplete: {e['n']} of {SHADOW_N} positions")
    if not e['better']:
        raise ValueError('the candidate did not beat the live rule')
    t = {a: dict(v) for a, v in (o.get('tune') or {}).items()}
    t.setdefault(c['agent'], {})[c['key']] = c['value']
    g = dict(o.get('gen') or {}); g[c['agent']] = int(g.get(c['agent']) or 1) + 1
    lin = list(o.get('lineage') or []) + [{'agent': c['agent'], 'gen': g[c['agent']] - 1, 'at': now, 'why': f"{c['key']} {c['live']:g} → {c['value']:g}: shadow {e['cand']:+.2f}% vs live {e['live']:+.2f}% over {e['n']} positions"}]
    o.update(tune=t, gen=g, lineage=lin[-40:], candidates={**o['candidates'], cid: {**c, 'status': 'promoted', 'doneAt': now, 'eval': e}})
    return o


def judge_candidates(office, arch, cfg, scalp, now):
    """👨‍⚖️ Once a pass: (1) every position closed since a shadow candidate was proposed is replayed under the live rule AND the candidate;
    (2) a finished shadow test promotes or rejects; (3) with no candidate open, the archive is searched for ONE Reaper setting that
    would have beaten the live one on ≥ PROPOSE_N real positions → proposed (shadow only). → office"""
    o = dict(office or {})
    pos = [p for p in (arch or {}).get('positions') or [] if p.get('confirmed') and len(p.get('path') or []) >= 3]
    take = take_line(cfg, scalp)
    live = tunes(o, 'reaper')
    cs = {k: dict(v) for k, v in (o.get('candidates') or {}).items()}
    for cid, c in cs.items():
        if c['status'] != 'shadow' or c['agent'] != 'reaper':
            continue
        seen = int(_f(c.get('seenAt') or c['at']))
        new = [p for p in pos if _f(p.get('closedAt')) > seen]
        if new:
            c['shadow'] = (list(c['shadow']) + [[reaper_replay(p['path'], live, take), reaper_replay(p['path'], {**live, c['key']: c['value']}, take)] for p in new])[-200:]
            c['seenAt'] = max(_f(p['closedAt']) for p in new)
        e = evaluate(c)
        if e['ready'] and not e['better']:
            c.update(status='rejected', doneAt=now, eval=e)
    o['candidates'] = cs
    for cid, c in list(cs.items()):
        if c['status'] == 'shadow' and evaluate(c)['ready'] and evaluate(c)['better']:
            o = promote(o, cid, now)
    if not any(c['status'] == 'shadow' for c in (o.get('candidates') or {}).values()) and len(pos) >= PROPOSE_N:
        base = sum(reaper_replay(p['path'], live, take) for p in pos) / len(pos)
        best = None
        for key, grid in REAPER_GRID.items():
            for v in grid:
                if v == live[key]:
                    continue
                avg = sum(reaper_replay(p['path'], {**live, key: v}, take) for p in pos) / len(pos)
                if avg >= base + SHADOW_MARGIN and (best is None or avg > best[2]):
                    best = (key, v, avg)
        if best and not any(c['key'] == best[0] and c['value'] == best[1] and now - _f(c.get('doneAt')) < 86400 for c in (o.get('candidates') or {}).values()):
            o = propose(o, 'reaper', best[0], best[1], {'n': len(pos), 'live': round(base, 2), 'cand': round(best[2], 2), 'from': 'archived real positions'}, now)
    return o


def demote(office, cards, now):
    """An office agent the Judge DEMOTED (enough samples, degraded edge) loses its promoted tunables — back to the hard-coded defaults —
    and starts its next generation. The four desks are scrapped by `agents.evolve`, never here."""
    o = dict(office or {})
    for a in ('weather', 'warden', 'courier', 'reaper'):
        if (cards.get(a) or {}).get('status') == 'demoted' and (o.get('tune') or {}).get(a):
            t = {k: dict(v) for k, v in (o.get('tune') or {}).items()}; t.pop(a, None)
            g = dict(o.get('gen') or {}); g[a] = int(g.get(a) or 1) + 1
            o.update(tune=t, gen=g, lineage=(list(o.get('lineage') or []) + [{'agent': a, 'gen': g[a] - 1, 'at': now, 'why': f"demoted: {cards[a]['why']} — tunables back to defaults"}])[-40:])
    return o


# ── the live pipeline + the one payload the page reads ─────────────────────────────────────────────────────────────────────────────
STAGE_STATES = ('WAITING', 'WORKING', 'PASS', 'OBJECT', 'VETO', 'DONE', 'ERROR', 'STALE')


def current_case(table, on=(), cfg=None, burned=(), reports=None):
    """The coin the office is working on right now: the strongest case file not on the card (cleared first), else the strongest read."""
    cs = _ag.investigate(table, set(on or ()), (cfg or {}).get('trenchMinAgeH', 1), burned or {}, top=1)
    return cs[0] if cs else None


def pipeline(case, ctx):
    """One line per desk for the CURRENT candidate: state + elapsed ms + the word that explains it. A desk downstream of a stop waits."""
    ms = (ctx or {}).get('ms') or {}
    if not case:
        return [{'agent': a, 'state': 'WAITING', 'ms': ms.get(a), 'word': 'no candidate this pass'} for a in CHAIN]
    row = case['row']
    t, s, w, c = ctx.get('tally') or {}, ctx.get('sherlock') or {}, ctx.get('weather') or {}, ctx.get('courier') or {}
    chk = {k[0]: k for k in case['checks']}
    tr = row['trigger']
    wd = ctx.get('warden')
    stop = False
    out = []

    def add(a, state, word):
        nonlocal stop
        out.append({'agent': a, 'state': 'WAITING' if stop and a not in ('archivist', 'judge') else state, 'ms': ms.get(a), 'word': word})
        if state in ('VETO', 'OBJECT', 'ERROR') and a in ('trigger', 'devil', 'warden', 'courier'):
            stop = True
    add('tally', 'STALE' if t.get('stale') else 'PASS' if int(_f(t.get('readings'))) >= 3 else 'WORKING', f"{t.get('readings')} readings · {t.get('ageSec')}s old" + (f" · missing {', '.join(t['missing'][:3])}" if t.get('missing') else ''))
    add('sherlock', 'PASS' if _f(s.get('lean')) > 0 else 'OBJECT', (f"{row['chart']['state']} · " if row.get('chart') else '') + f"lean {_f(s.get('lean')):+.1f} · {len(s.get('for') or [])} for / {len(s.get('against') or [])} against" + (f" · scan {ctx.get('scan')}" if ctx.get('scan') else ''))
    add('weather', 'OBJECT' if w.get('regime') == 'HOSTILE' else 'PASS', f"{w.get('regime') or '—'} · bar {weather_adj(w):+.2f} · size ×{weather_size(w):g}")
    hard = [k for k in case['checks'] if k[0] in ('scan', 'age', 'pool', 'burn') and not k[1]]
    moment = chk.get('chart')
    add('trigger', 'VETO' if tr[0] == 'skip' or hard else 'PASS' if tr[0] == 'enter' or (moment and moment[1]) else 'WORKING',
        f"{tr[0].upper()} — {tr[1]}" + (f" · duty blocked: {hard[0][2]}" if hard and tr[0] != 'skip' else f' · {moment[2]}' if moment and tr[0] == 'wait' else ' · duty waives the bar only' if tr[0] == 'wait' else ''))
    add('devil', 'PASS' if chk['devil'][1] else 'OBJECT', chk['devil'][2])
    add('warden', 'WAITING' if not wd else 'VETO' if wd['veto'] else 'DONE', 'sizes the move when a seat is open' if not wd else f"${wd['requested']:.2f} → ${wd['allowed']:.2f} (×{wd['eff']:g}) · {wd['decided']}")
    add('courier', 'VETO' if c.get('health') == 'BAD' else 'WORKING' if c.get('pending') else 'OBJECT' if c.get('health') == 'DEGRADED' else 'PASS', f"{c.get('health') or '—'} · {(c.get('why') or [''])[0]}")
    add('reaper', 'WAITING', 'takes over once the fill is confirmed')
    add('archivist', 'DONE' if ctx.get('filed') else 'WAITING', 'decision filed' if ctx.get('filed') else 'files it when the pass ends')
    add('judge', 'WAITING', 'rules 5 minutes after the final decision')
    return out


def lineage_of(case, ctx, action=None):
    """The decision record the Archivist files for a case: what every desk said at decision time (compact, numbers not prose)."""
    row = case['row']
    n, v = row.get('nums') or {}, row.get('vitals') or {}
    w, wd = ctx.get('weather') or {}, ctx.get('warden')
    return {'mint': case['mint'], 'sym': case.get('symbol'), 'px': case.get('px'), 'cleared': bool(case.get('cleared')), 'action': action, 'ageH': v.get('ageH'),
            'tally': {'pts': n.get('pts'), 'd5': n.get('d5'), 'buy': n.get('buy'), 'liq': n.get('liq'), 'pace': n.get('pace')},
            'sherlock': {'lean': (row.get('why') or {}).get('lean'), 'drivers': [d[0] for d in (row.get('why') or {}).get('drivers') or []][:6]},
            'weather': {'regime': w.get('regime'), 'barAdj': weather_adj(w), 'size': weather_size(w)}, 'trigger': [row['trigger'][0], str(row['trigger'][1])[:80], ctx.get('bar')],
            'devil': [(row.get('case') or row.get('devil') or ['—'])[0], [o[0] for o in row.get('objs') or []][:5]],
            'blocked': [k[0] for k in case.get('checks') or [] if not k[1]],
            'chart': None if not row.get('chart') else {'state': row['chart']['state'], 'entry': row['chart']['entry'][:2], 'trend': row['chart'].get('trend'), 'chop': row['chart'].get('chop'),
                                                        'mom': row['chart'].get('mom'), 'ext': row['chart'].get('ext'), 'src': row['chart'].get('src')},
            'warden': None if not wd else {'req': wd['requested'], 'allowed': wd['allowed'], 'mult': wd['eff'], 'rule': wd['decided']}, 'courier': (ctx.get('courier') or {}).get('health')}


def mission(money, lives, stage, duty_at, now, last=None, underwater=None):
    """🎯 The real-money mission, from the SAME fields the real Fuse card shows (`money` = its server value and put-in). The lock is
    `agents.underwater`: real value < real put-in — passed in, never recomputed from anything else."""
    v, p = (money or {}).get('value'), (money or {}).get('putIn')
    known = v is not None and p is not None and _f(p) > 0
    return {'putIn': p, 'value': v, 'toBreakeven': round(_f(v) - _f(p), 2) if known else None, 'needX': round(_f(p) / _f(v), 1) if known and _f(v) > 0 else None,
            'stage': (stage or {}).get('h') or 5, 'locked': bool(underwater), 'lock': 'LOCKED' if underwater else 'CLEARED' if known else 'UNKNOWN',
            'lockRule': 'real card value < real put-in → stage stays 5 min (agents.underwater)',
            'lives': lives, 'livesOf': _ag.LIVES, 'nextDutyIn': max(0, round(_f(duty_at) + _ag.DUTY_SEC - now)) if duty_at else 0, 'dutyEvery': _ag.DUTY_SEC, 'lastAction': last, 'priority': list(PRIORITY)}


def agent_cards(cards, ctx):
    """The ten live cards: constitution (immutable) + tunables (live value, default, bounds) + this pass's task / decision / inputs /
    output + the Judge's scorecard. Everything shown is state, a coded rule or a measurement."""
    out = []
    for a in CHAIN:
        c, k = CONSTITUTION[a], cards.get(a) or {}
        live = (ctx.get('live') or {}).get(a) or {}
        out.append({'key': a, 'icon': c['icon'], 'name': c['name'], 'role': c['role'], 'ideology': c['ideology'], 'ethics': list(c['ethics']), 'forbidden': list(c['forbidden']),
                    'hard': list(c['hard']), 'code': [{'file': c['code']['file'], 'fn': list(c['code']['fn'])}] + ([{'file': 'backend/office.py', 'fn': list(c['office'])}] if c.get('office') else [])
                    + ([{'file': 'backend/chart_intel.py', 'fn': list(c['chart'])}] if c.get('chart') else []),
                    'tunable': [{'key': t, 'value': tune(ctx.get('office'), a, t), 'default': d[0], 'lo': d[1], 'hi': d[2], 'what': d[3]} for t, d in (TUNABLE.get(a) or {}).items()],
                    'task': live.get('task'), 'decision': live.get('decision'), 'decisionAt': live.get('at'), 'rule': live.get('rule'), 'inputs': live.get('inputs'), 'output': live.get('output'),
                    'recent': live.get('recent') or [], 'card': k})
    return out
