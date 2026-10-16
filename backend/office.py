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

import paper_desk as _pd   # 📝 the OFFLINE practice record (graded paper calls) — it has no live authority
import trench_kernel.universe as _uni
import trench_kernel.senses as _sn
import trench_kernel.positions as _pos
import opportunity as _opp
import market_wake as _mw
import chart_intel as _ci
import exit_read as _er
import market_data as _md
import office_edge as _oe
import seat_ops as _so
import trench_rounds as _tr
import drain as _drn

_f, _med = _sn._f, _sn._med

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
FLOW_BANK_PCT = 4.0                  # 🌊 sellers take over a seat that is at least this green → banked into the last buyers (above a round trip's cost)
FLOW_CLIMAX_PCT = 15.0               # 🏔 a buying climax on a seat this green → banked into the climax
FLOW_TIGHT = 0.7                     # 🌊 sellers lead a RED seat → its stop tightens to 70% (never under chart_intel.STOP_FLOOR), it is not sold on one read
MIN_KEEP = 1.5                       # ☠ a trailing take only fires while there is still this much % to bank
DEAD_CASH_MIN = 15.0                 # 💀 dead this long (no trades / off their radar): exit to CASH even with no replacement ready
DEAD_HOLD_MIN = 5.0                  # 💀 minutes held before a dead coin (no trades) gives its seat away
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
               'youngH': (0.25, 0.25, 12.0, 'coins younger than this get half size (the ≤ 6h trench universe sizes uncertainty by its tier; only a newborn is halved here)'),
               'ddPct': (25.0, 15.0, 40.0, 'card drawdown from its 24h peak at which new seats are halved')},
    'courier': {'badFailPct': (50.0, 40.0, 60.0, 'failed sends in 15 min at which execution is BAD'),
                'degradedFailPct': (25.0, 15.0, 35.0, 'failed sends in the hour at which execution is DEGRADED'),
                'maxDeltaPct': (3.0, 2.0, 5.0, 'typical fill worse than the mid price by this much = DEGRADED')},
    'reaper': {'protectAt': (6.0, 4.0, 15.0, 'peak gain % at which the trailing protection arms'),
               'giveBackPct': (50.0, 30.0, 70.0, 'share of the peak gain it may give back before the rest is banked'),
               'stopPct': (30.0, 15.0, 40.0, 'the CEILING of a normal stop — each entry gets its own structure-aware stop under it (chart_intel.stop_for); the catastrophic stop is above it and is not tunable'),
               'timeMaxMin': (120.0, 60.0, 240.0, 'minutes after which a position with no read left is closed')},
})

CONSTITUTION = _frozen({
    'tally': {'icon': '📊', 'name': 'Tally', 'role': 'Market truth: ONE measured state per mint — tape, velocity, pool, sources.', 'ideology': 'Evidence first.',
              'ethics': ('Never certify market data merely because it rendered successfully.', 'Never invent a read.', 'Never silently substitute stale numbers.', 'Never promote a coin without enough observations.'),
              'forbidden': ('judging a coin', 'calling an entry', 'touching the card'),
              'hard': ('one MintState per mint — a coin is never two candidates', f'the tape keeps {_sn.SERIES_N} points a coin, one a pass', 'every section of a coin\'s state carries its own timestamp',
                       'a reading older than 150s is STALE and is said so', 'every chart passes market_data.quality before any desk reads structure from it',
                       'TRUSTED = real 1-minute OHLC, every integrity check passed, fresh, per-candle volume on ≥ 80% of moving bars, a live pool reading, confidence ≥ 80',
                       'a reconstructed tape, a sparse stream, missing volume or missing liquidity is LABELLED as that'),
              'data': ('quality', 'compact', 'word'), 'code': {'file': 'backend/trench_kernel/senses.py', 'fn': ('tally', 'sense')}, 'brain': ('tally',), 'office': ('tally_read',)},
    'sherlock': {'icon': '🔍', 'name': 'Sherlock', 'role': 'Investigation: what is known, what is still UNKNOWN, and what to fetch next.', 'ideology': 'Unknown is a question, not a verdict.',
                 'ethics': ('Know the launch mechanism before making a launch-specific claim: an unknown launch stays UNKNOWN.', 'Never infer chart structure from data Tally marks UNTRUSTED or MALFORMED.', 'Never describe chart structure without measured evidence.', 'Every claim carries measurable evidence.', 'Contradicting evidence is shown, never dropped.', 'An unknown is an open question, not a pass.'),
                 'forbidden': ('calling an entry', 'rejecting a coin because evidence has not arrived', 'fetching for itself (the one scheduler does)', 'touching the card'),
                 'hard': ('UNKNOWN / PENDING is a research state — it never moves a coin out of the ranking', 'its requests go to the ONE enrichment scheduler (priority: held · ready · armed · contending · movers)',
                          'early-wallet evidence moves a rank by its factor only (+8% … −15% at trust 1)'),
                 'chart': ('snapshot', 'classify'), 'code': {'file': 'backend/trench_kernel/brain.py', 'fn': ('sherlock',)}, 'office': ('scan_status',)},
    'weather': {'icon': '🌦', 'name': 'Weather', 'role': 'The trench\'s regime this pass, from the board and our own judged calls.', 'ideology': 'The environment changes strategy.',
                'ethics': ('Never apply the same thresholds blindly in every regime.', 'Never classify without the inputs: unknown inputs lower confidence.'),
                'forbidden': ('buying or selling', 'removing or loosening a safety gate', 'moving Trigger\'s bar outside its range', 'growing a position'),
                'hard': (f'bar adjustment stays inside {WEATHER_BAR_RANGE[0]:+.2f} … {WEATHER_BAR_RANGE[1]:+.2f}', f'size modifier stays inside ×{WEATHER_SIZE_RANGE[0]} … ×{WEATHER_SIZE_RANGE[1]}',
                         'never judged under 10 coins (THIN, low confidence)'),
                'code': {'file': 'backend/office.py', 'fn': ('weather', 'weather_adj')}},
    'trigger': {'icon': '⏱', 'name': 'Trigger', 'role': 'Entry timing from the LIVE narrative of this pass: ENTER · ARM · WAIT · NO.', 'ideology': 'Precision over frequency.',
                'ethics': ('Never enter because of chart structure when the chart-quality gate fails.', 'Never chase merely because price is rising.', 'Never call an entry clean unless every required check has its evidence.', 'A missed runner is counted, never hidden.'),
                'forbidden': ('entering past the hard wall', 'sizing a position', 'waiting on a round clock (rounds are learning windows)'),
                'hard': ('ENTER only on a HOT EARLY MOVE, a BREAKOUT or a RUNNING coin', 'COLLAPSING / DISTRIBUTING is never entered (the hard wall)',
                         'READY = ENTER + inside the wall + execution healthy + rank ≥ 120', f'a +{_ci.PARABOLIC_5M:g}% 5-minute move is PARABOLIC'),
                'chart': ('entry_call',), 'code': {'file': 'backend/trench_kernel/brain.py', 'fn': ('trigger', 'reduce')}},
    'devil': {'icon': '⚖', 'name': 'Devil', 'role': 'Adversarial challenge: every piece of evidence against the coin, graded by severity.', 'ideology': 'Challenge everything; block only at the wall.',
              'ethics': ('A failed market-data integrity check is a HARD objection.', 'Never object merely because a chart looks visually scary.', 'Object only with evidence.', 'A soft objection must be backed by its own record.', 'No random opposition, no canned lines.'),
              'forbidden': ('blocking a coin on a warning', 'inventing a hard rule after a loss', 'objecting without named evidence'),
              'hard': ('severities: INFO · WARNING · STRONG_WARNING · HARD_VETO — only the hard wall is a HARD_VETO', 'a strong warning costs ×0.85 of a rank, any other ×0.95, all together never under ×0.6',
                       'the hard wall: no live price · dead · outside the universe · pool under the keeper floor · invalid data / bot ladder · collapsing or distributing · the dev dumping now'),
              'chart': ('objections',), 'code': {'file': 'backend/trench_kernel/brain.py', 'fn': ('devil',)}, 'senses': ('evidence', 'busted'), 'office': ('devil_record',)},
    'warden': {'icon': '🛡', 'name': 'Warden', 'role': 'Risk and size of an existing real-card move. It never judges the coin.', 'ideology': 'Survival first.',
               'ethics': ('The creator\'s limits are boundaries, never targets: size, stop and hold are never set past them.', 'Unknown or degraded market data can only reduce risk, never increase it.', 'Never increase size because of excitement or recent profit.', 'Capital preservation outranks excitement, FOMO, win rate and agent ego.', 'Every size change names the rule that made it.'),
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
               'ethics': ('A restart or a refill gap is never evidence to exit: off-radar and time rules wait until the office is LIVE.', 'Never invent a chart-based exit thesis from corrupt data: when chart data degrades on a held coin, fall back to the hard risk / execution / liquidity rules and report DATA DEGRADED.', 'Never keep holding merely because a position is green.', 'Never keep holding merely to avoid realizing a loss.', 'Never hold because of hope.', 'Never claim an exit without a confirmed exit.', 'Never invent a price or a pool depth.'),
               'forbidden': ('buying', 'selling by itself: its exits go through the card\'s existing action path', 'giving a winner\'s seat to a new candidate',
                             'touching a coin the creator froze'),
               'hard': (f'catastrophic stop −{_ci.CATASTROPHIC_STOP:g}%: a constant no learning or promotion can move or switch off', f'a normal stop stays inside {_ci.STOP_FLOOR:g}% … {_ci.CATASTROPHIC_STOP - 5:g}%',
                        f'a thesis gets at least {_ci.MIN_WINDOWS} five-minute windows and at most {_ci.MAX_WINDOWS}; an invalidated thesis leaves at once', 'pool under half its entry depth = out now', 'a holder scan or a rug score is evidence for the brain, never an exit — the live chart, the tape and liquidity decide',
                        'the take line stays the card\'s own (agentTakePct / the learned scalp line)', 'no price = no ruling this tick'),
               'chart': ('thesis', 'review', 'stop_for'), 'code': {'file': 'backend/office.py', 'fn': ('reap', 'reaper_replay', 'merge_reaper', 'confirm_exits')}},
    'archivist': {'icon': '🗄', 'name': 'Archivist', 'role': 'The permanent decision lineage and the learning derived from it.', 'ideology': 'Every real decision becomes evidence.',
                  'ethics': ('Store the launch context a decision was made in.', 'File a missed winner with what was knowable then — never with hindsight.', 'Preserve the exact data-quality state that existed at decision time.', 'Never rewrite what the entry thesis originally was.', 'Never rewrite history.', 'Never turn a loss into a win.', 'Never discard inconvenient data: what rotates out is folded into the totals.'),
                  'forbidden': ('editing a filed decision', 'deleting a losing record', 'stating a pattern without its sample count'),
                  'hard': ('every decision record is hash-chained to the one before it', 'cases are bounded: the oldest fold into aggregates', 'a pattern is shown only from 5 records'),
                  'code': {'file': 'backend/office.py', 'fn': ('file_case', 'settle_cases', 'file_position', 'verify', 'patterns')}},
    'judge': {'icon': '👨‍⚖️', 'name': 'Judge', 'role': 'Scores every agent on its own record, itself included.', 'ideology': 'Judge the record, not the last result.',
              'ethics': ('Never weaken a safety rule because a blocked coin later pumped.', 'Score outcomes separately by launch context.', 'Score an agent negatively when it acted as though bad data was trustworthy.', 'Evaluate chart decisions using the information available at that time, not hindsight.', 'No agent is demoted on one or two outcomes.', 'A rule changes only after a shadow test beats the live rule.', 'The Judge is scored too.'),
              'forbidden': ('changing the immutable constitution', 'promoting an untested change', 'loosening a safety gate as a reward'),
              'hard': ('ONE lifecycle for all ten roles, judged on REAL exits only', 'PROBATION at 2 net real losses pinned on a role, its generation REPLACED at 3 (never in its first hour)',
                       'a replaced generation is SHADOW for 24h and has no live authority', f'a tunable candidate needs {PROPOSE_N} archived positions, then {SHADOW_N} in shadow',
                       'paper calls, streaks and lives decide nothing'),
              'code': {'file': 'backend/judge_review.py', 'fn': ('review', 'court', 'desk_stats')}, 'life': ('evaluate', 'attribute', 'improve', 'lessons'), 'office': ('scorecards', 'propose', 'promote', 'judge_candidates')},
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
    viable = sum(1 for m, n in (nums or {}).items() if (by.get(m) or {}).get('safe') is not False and _f(n.get('liq')) >= _uni.CONTROL_MIN_LIQ and -8 <= _f(n.get('d5')) <= 15
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
    # a row that failed BEFORE anything was signed (Jupiter busy: "build/sign: … (HTTP 429)") was never sent — it says nothing about landing.
    # 2026-10-12: four such rows on one $0.08 sell read "4 of 4 sends failed", execution BAD, and every seat sat blocked for 15 minutes.
    unsent = lambda r: r.get('status') == 'failed' and not r.get('sig') and any(w in str(r.get('err') or '') for w in ('build/sign', '(HTTP 429)', '(HTTP 5'))
    sends = [r for r in rows if r.get('status') in ('filled', 'failed') and not unsent(r)]
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
NEAR_SIZE = 1.0   # 🪑 W19: a best-available / seat-floor fill takes a FULL equal seat (owner, 2026-10-11: "use all card cash") — was 0.5


OPEN_RULES = ('W1', 'W3', 'W17')   # ⚡ open mode: execution health · pool share · each open seat its share of the cash
COST_MAX_PCT = 5.0   # 💸 W22: a seat whose measured round-trip drag (sell-back loss + 2× network fee ÷ size) is over this is not bought


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
    if c.get('kernelSize') is not None and _f(c['kernelSize']) < 1:   # ⚙ the brain's Warden opinion (unknown holders · a newborn · strong warnings): uncertainty → SIZE
        hit('W0 uncertainty', _f(c['kernelSize']), f"the brain sizes it ×{_f(c['kernelSize']):g}: {c.get('kernelWhy') or 'uncertainty'}")
    last = [_f(x) for x in (c.get('lastReal') or [])][-3:]
    if len(last) == 3 and all(x <= 0 for x in last):
        hit('W8 losing streak', 0.5, 'the last 3 real exits all lost')
    peak, val = _f(c.get('peak')), _f(c.get('value'))
    if peak > 0 and val > 0 and (1 - val / peak) * 100 >= T('ddPct'):
        hit('W9 drawdown', 0.5, f"the card is {(1 - val / peak) * 100:.0f}% under its 24h peak (line {T('ddPct'):g}%)")
    if val > 0 and req > val * T('maxSeatPct') / 100:
        hit('W10 concentration', val * T('maxSeatPct') / 100 / req, f"${req:.2f} is over {T('maxSeatPct'):g}% of the ${val:.2f} card")
    pol = c.get('policy') or {}
    if pol.get('sizePct') and val > 0 and req > val * _f(pol['sizePct']) / 100:   # 🎛 the creator's size cap: a boundary the office cannot size past
        hit('W14 creator size cap', val * _f(pol['sizePct']) / 100 / req, f"${req:.2f} is over your {_f(pol['sizePct']):g}% cap of the ${val:.2f} card")
    ln = c.get('launch') or {}
    if ln.get('measured') and _oe.LAUNCH_RISK.get(ln.get('type')):   # 🚀 launch mechanism risk: an unknown / pre-graduation launch is at most half size
        hit('W15 launch context', _oe.LAUNCH_RISK[ln['type']], f"launch: {ln.get('pad')} · {ln.get('type')}")
    cc = (c.get('social') or {}).get('cross') or {}
    if cc.get('conflict'):   # 🔎 the coin's own website shows another contract: a quarter seat at most (hype never grows one) — the proof rides with the rule
        hit('W16 identity', 0.25, f"the website shows a different contract than this mint — {cc.get('sourceUrl') or 'site'} shows {str(cc.get('sourceMint') or '?')[:10]}…, launch mint {str(cc.get('launchMint') or '?')[:10]}…")
        rules[-1]['evidence'] = {'sourceUrl': cc.get('sourceUrl'), 'sourceMint': cc.get('sourceMint'), 'launchMint': cc.get('launchMint'), 'at': (c.get('social') or {}).get('at')}
    elif cc.get('confidence') is not None and _f(cc['confidence']) < 40:
        hit('W16 identity', 0.5, f"identity confidence {_f(cc['confidence']):.0f}/100: {'; '.join(cc.get('flags') or [])[:120]}")
        rules[-1]['evidence'] = {'sourceUrl': cc.get('sourceUrl'), 'flags': list(cc.get('flags') or [])[:3], 'at': (c.get('social') or {}).get('at')}
    tier_m = _opp.TIER_SIZE.get(c.get('tier'), NEAR_SIZE) if c.get('near') else 1.0   # 🎯 W19 confidence tier: A full · B 75% · C 50% — applied ON TOP of the rest (below)
    if c.get('openSeats') and c.get('free') is not None:   # 🪑 multi-seat sizing: the first valid seat may not make the other open seats impossible
        m_, why_ = _so.seat_room(req, c.get('free'), c.get('openSeats'), floor)
        if why_:
            hit('W17 seat room', m_, why_)
    dq = (c.get('chart') or {}).get('q')
    if dq and _f(dq.get('risk')) < 1:   # 🧪 unknown / degraded market data can only shrink the seat (market_data.RISK) — there is no state that grows it
        hit('W13 market data', _f(dq.get('risk')), f"data {str(dq.get('state')).replace('_', ' ').lower()} ({dq.get('conf')}%): {dq.get('why')}")
    if c.get('chart'):   # 📈 chart risk (chart_intel.risk): the structure can shrink or veto the seat, never grow it
        cm, cwhy = (c['chart'].get('risk') or [1.0, ''])[:2]
        if _f(cm) < 1:
            hit('W12 chart risk', _f(cm), f"{c['chart'].get('state')}: {cwhy}")
        qw_, qwhy_ = _so.chart_quality(c['chart'])
        if qw_ in _so.QUALITY_SIZE:   # 📊 chart quality: a choppy / extended / unstable chart can only shrink a seat (after W12: a tie is W12's)
            hit('W18 chart quality', _so.QUALITY_SIZE[qw_], f'{qw_}: {qwhy_}')
    if c.get('holderSoft'):   # 🧪 W21: passed only on the agents' own (wider) concentration line — a half seat
        hit('W21 concentrated launch', 0.5, 'concentrated holders, inside the agents\' line: ' + '; '.join(c['holderSoft'][:3]))
    li_ = c.get('li') or {}
    if li_:   # 🕵 W20 exit risk: who could dump on us — a clustered / bundled launch still holding its early supply, early wallets selling now (shrinks only)
        if li_.get('press') == 'HIGH':
            hit('W20 exit risk', 0.0, f"early wallets unloading now: {li_.get('pressWhy')}")
        elif li_.get('cls') == 'INSIDER-LIKE CLUSTER' and _f(li_.get('early')) >= 20:
            hit('W20 exit risk', 0.5, f"insider-like cluster still holds {_f(li_['early']):.0f}% of supply — a small seat until it spreads out")
        elif li_.get('cls') in ('BUNDLED', 'INSIDER-LIKE CLUSTER') or li_.get('press') == 'WATCH' or _f(li_.get('danger')) > 0:
            hit('W20 exit risk', 0.75, '; '.join(x for x in (li_.get('cls') if li_.get('cls') in ('BUNDLED', 'INSIDER-LIKE CLUSTER') else None, li_.get('pressWhy'),
                                                              f"{int(_f(li_.get('danger')))} early wallet(s) with a dump / rug record" if _f(li_.get('danger')) else None) if x))
    if c.get('open'):   # ⚡ OPEN MODE (owner, 2026-10-12: "no gates — volume and newness only"): only execution, pool share and seat room size it
        import trench_crew as _crew
        cap_ = c.get('capital') or {}   # 💰 the capital desk (capital.py): size follows the agents' own REAL record
        live_ = cap_.get('state') in ('GROW', 'STEADY', 'PROTECT') and cap_.get('mult') is not None
        rules = _crew.warden_rules(rules, cap_.get('floor') if live_ else None); tier_m = 1.0   # 🪖 trench crew: execution rules as they are, uncertainty only SHRINKS (≥ ×0.5, or the capital desk's floor)
        if cap_.get('rugCapPct') and _f(c.get('value')) > 0 and req > 0:   # ☠ W24: the whole seat is what a rug takes — one rug may cost ≤ the rug budget of the CARD
            m24 = _f(c['value']) * _f(cap_['rugCapPct']) / 100 / req
            if m24 < 1:
                rules.append({'id': 'W24 rug budget', 'mult': round(_clamp(m24, 0.05, 1.0), 3), 'why': f"☠ a seat ≤ {_f(cap_['rugCapPct']):g}% of the ${_f(c['value']):.2f} card: about 1 seat in 8 rugs for the whole seat, in under a minute — no stop gets out"})
        if live_:
            rules.append({'id': 'W23 capital', 'mult': round(_clamp(_f(cap_['mult']), 0.25, 1.0), 3), 'why': f"💰 {cap_.get('state')}: {str(cap_.get('why'))[:170]}"})
    raw = min([r['mult'] for r in rules] or [1.0])
    if tier_m < 1:   # 🎯 size by CONFIDENCE: the tier multiplies whatever the other rules allowed (as the smallest rule it was masked: every seat came out ×0.4)
        rules.append({'id': 'W19 confidence tier', 'mult': round(tier_m, 3), 'why': f"{c.get('tier') or 'unconfirmed'}-tier: ×{tier_m:g} on top — {str(c.get('near'))[:140]}"})
        raw = raw * tier_m
    mult = max(s for s in WARDEN_STEPS if s <= raw + 1e-9)
    if mult == 0 and raw > 1e-9:   # 🪑 shrinking is never a veto: a seat cut below the smallest step keeps the smallest one (only a ×0 rule vetoes)
        mult = min(s for s in WARDEN_STEPS if s > 0)
    allowed = round(req * mult, 6)
    if 0 < allowed < floor <= req:   # a cut that would leave an unsendable order: the smallest sendable one instead — still under what was asked
        allowed = round(floor, 6)
        rules.append({'id': 'W11 smallest order', 'mult': round(floor / req, 3), 'why': f'×{mult:g} would be under the ${floor:.2f} the keeper can send — kept at the smallest order'})
    if allowed < floor:
        allowed, mult = 0.0, 0.0
    allowed = min(allowed, req)
    rt, fee = _f(c.get('rtPct')), _f(c.get('feeUsd'))
    if allowed > 0 and (rt or fee):   # 💸 W22 COST: a seat this size must be able to beat its OWN round trip (measured sell-back loss + the network fee both ways)
        drag = rt + 2 * fee / allowed * 100
        if drag > COST_MAX_PCT:
            rules.append({'id': 'W22 cost', 'mult': 0.0, 'why': f"SIZE TOO SMALL FOR COSTS — a ${allowed:.2f} seat pays ~{drag:.1f}% just to get in and out (> {COST_MAX_PCT:g}%); not a strategy failure"})
            allowed, mult = 0.0, 0.0
    return {'requested': round(req, 4), 'allowed': round(allowed, 4), 'mult': mult, 'eff': round(allowed / req, 3) if req > 0 else 0.0, 'veto': allowed <= 0,
            'rules': rules, 'decided': min(rules, key=lambda r: r['mult'])['id'] if rules else 'none — full size',
            'limits': {'steps': list(WARDEN_STEPS), 'floorUsd': floor, **tunes(office, 'warden')}}


# ── ☠ REAPER ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
REAPER_STATES = ('HOLD', 'PROTECT', 'TAKE', 'EXIT INVALIDATED')
PATH_KEEP = 240


def take_line(cfg, scalp=None):
    """The card's OWN take line for an agent coin: the learned scalp line when one is adopted and `agentScalp` is on, else `agentTakePct`."""
    tp = _oe.policy(cfg).get('tp')
    if tp:   # 🎛 CREATOR OVERRIDE: your take-profit is the line — the learned scalp line stands aside
        return _f(tp)
    if (cfg or {}).get('agentScalp', True) and (scalp or {}).get('tp'):
        return _f(scalp['tp'])
    return _f((cfg or {}).get('agentTakePct') or 10)


def take_info(cfg, scalp=None):
    """🎯 Which take line the real agent seats obey RIGHT NOW and where it comes from: the base (`agentTakePct`, the creator's setting) or
    the LEARNED scalp line (`agents.scalp_adopt`: ≥ SCALP_N of their own 5-minute paths, average > 0 AND > holding). The take line is not
    an office tunable, so it is never 'promoted' — a learned line is dropped by itself the pass it stops being proven."""
    base = _f((cfg or {}).get('agentTakePct') or 10)
    over = bool(_oe.policy(cfg).get('tp'))
    learned = bool(not over and (cfg or {}).get('agentScalp', True) and (scalp or {}).get('tp'))
    # `at`: what happens AT the line — 'bank' (a line someone chose: yours or their learned one) or 'read' (the base line under AGENTS CHOOSE:
    # the agents read the coin there and let a clean one run under the trail)
    return {'base': base, 'active': take_line(cfg, scalp), 'source': 'creator' if over else 'learned' if learned else 'base', 'at': 'bank' if over or learned else 'read', 'ruleId': 'R6 take line', 'who': 'CREATOR OVERRIDE' if over else 'AGENTS CHOOSE',
            'rule': 'cfg agentTp — your override' if over else 'agents.scalp_adopt — their own 5-min paths' if learned else 'cfg agentTakePct — your setting', 'scalpOn': bool((cfg or {}).get('agentScalp', True)),
            'evidenceN': (scalp or {}).get('n') if learned else None, 'shadowAvg': (scalp or {}).get('avg') if learned else None, 'adoptedAt': (scalp or {}).get('at') if learned else None,
            'needN': _pd.SCALP_N, 'promoted': None}


OBEY = {'R4d': 'drain exit (holders / pool / sellers)', 'R4f': 'flow exit (sellers took over)', 'R4c': 'flow exit (buying climax)', 'R11x': 'dead coin exit', 'R7b': 'trailing protection', 'R11': 'dead coin swap', 'R4e': 'hard safety exit', 'R5c': 'creator stop-loss', 'R9c': 'creator max hold', 'R1': 'hard safety exit', 'R2': 'hard safety exit', 'R3': 'hard safety exit', 'R5x': 'hard safety exit', 'R4': 'invalidation exit', 'R5t': 'invalidation exit', 'R5': 'structure-aware stop',
        'R6': 'take line', 'R7': 'trailing protection', 'R7s': 'trailing protection', 'R8': 'thesis review', 'R9': 'thesis review', 'R10': 'thesis hold', 'R10r': 'riding the volume', 'R0': 'waiting'}


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


def _li_snap(li, v=None):
    """🕵 What the launch looked like when we bought (kept on the position → the Judge's review): phase, class, first-10 / early supply,
    exit pressure, our buyer rank, age and cap at entry."""
    if not li:
        return None
    return {k: li.get(k) for k in ('phase', 'healthy', 'cls', 'first10', 'first25', 'early', 'trend', 'press', 'danger', 'rank', 'ageH', 'mcap', 'pump', 'ewp', 'vpm', 'bpm', 'fresh')}


RIDE_GIVE = 50.0       # 🏄 while a real crowd is buying, the trail lets the coin give back this % of its peak (the normal trail ~35%)
RIDE_HOLD_SEC = 90.0   # the ride outlives one quiet 90s window (the tape is read every 15s); past it the normal rules return


def reap(legs, table, prices, cfg, pos, now, scalp=None, control=False, weather_=None, tape=None, office=None, sized=None, charts=None, theses=None, pol=None, live=True, vels=None, margins=None, rug=None, press=None, real=False, flows=None, ai_exit=None, ai_words=None):
    """☠ One look at every position the agents hold on the real card (in control: every coin that is not frozen). It keeps each one's
    record (entry, peak, path, depth and top-10 at entry) and rules, in this order — the first that fires decides:
      R1 pool collapsed · R4 whale dump / R4r rug radar / R4e early wallets on the live tape · R5 stop* · (a holder scan or a rug score is evidence for the brain, never an exit) ·
      R6 the card's take line · R7 trailing protection · R8 momentum failed after 15 min* · R9 time with no read left* · else HOLD.
      (* only on coins the agents put on the card: other coins keep the card's own stop and are switched by `agents.manage`.)
    A ruling with `action: 'pull'` is a REQUEST: the service merges it into the card's existing agent decisions (merge_reaper) and the
    keeper sells; the position stays 'exit requested' until the ledger confirms it. No price = no ruling. → (positions, reports, gone)
    `vels` {mint: seat_ops.velocity} = P/L VELOCITY from real reads (REVERSING tightens the trail · a winner must be ACCELERATING / STABLE to
    EARN windows past its base) · `margins` {mint: (best challenger's score margin, the margin a switch needs)} · `rug` {pair: why} = the
    rug radar on the live tape (creator / top-holder dump) → R4r, a hard safety exit."""
    T = lambda k: tune(office, 'reaper', k)
    press = press or {}
    pos = {m: dict(v) for m, v in (pos or {}).items()}
    by = {x['mint']: x for x in table or []}
    take = take0 = take_line(cfg, scalp)
    tsrc = take_info(cfg, scalp)['source']
    runs = tsrc == 'base'   # AGENTS CHOOSE before a line is learned: at the take line they read the coin — Reaper keeps the trail on it above the line
    # 🎛 the creator's limits (office_edge.policy) + 🔌 `live`: until the office has refilled after a restart (and for RADAR_GRACE_SEC
    # after a coin drops off the table at any time) a missing row is OUR gap — "off their radar" and the time rules do not exist.
    # The price rules (catastrophic stop, stop, take, trail), the pool rule and the scan / rug rules never wait for it.
    pol = pol or _oe.policy(cfg)
    manual = bool(pol.get('manual'))
    out, on = [], set()
    for l in legs or []:
        m = l.get('mint')
        if not m or l.get('placeholder') or l.get('frozen') or not (control or _uni.is_agent(l)):
            continue
        on.add(m)
        base = {'mint': m, 'pair': l.get('pairAddress'), 'symbol': l.get('symbol'), 'owner': 'agents' if _uni.is_agent(l) else 'you' if l.get('picked') else 'card', 'action': None}
        px, entry = _f((prices or {}).get(l.get('pairAddress'))), _f(l.get('entry'))
        if l.get('buying') or _f(l.get('units')) <= 0 or entry <= 0 or (real and not l.get('real')):   # `real` card: the wallet must HOLD it (sync_card) — a seat is not a position until its buy lands
            out.append({**base, 'state': 'HOLD', 'rule': 'R0 waiting for the fill', 'evidence': 'the buy is not confirmed on the ledger yet', 'exec': 'unconfirmed'}); continue
        if px <= 0:
            out.append({**base, 'state': 'HOLD', 'rule': 'R0 no price', 'evidence': 'no live price this tick — nothing is ruled on a guess', 'exec': 'confirmed', 'entry': entry}); continue
        x = by.get(m)
        v = (x or {}).get('vitals') or {}
        pct = (px / entry - 1) * 100
        p = pos.get(m) or {'entry': entry, 'since': _f(l.get('at')) or now, 'peak': pct, 'low': pct, 'path': [], 'liq0': _f(l.get('liq')) or None, 'top0': v.get('top10'),
                           'sym': l.get('symbol'), 'tag': (l.get('bought') or {}).get('tag'), 'wx': (weather_ or {}).get('regime'), 'warden': (sized or {}).get(m), 'launch': (x or {}).get('launch'),
                           'li': _li_snap((x or {}).get('li'), (x or {}).get('vitals')), 'src': [s_ for s_ in (x or {}).get('src') or [] if s_ != 'open'][:4]}
        if abs(_f(p.get('entry')) - entry) > entry * 1e-6:   # a rebuy / top-up moved the book entry: the peak is measured from the new one
            p.update(entry=entry, peak=pct, low=pct, path=[])
        p['peak'], p['low'] = max(_f(p.get('peak')), pct), min(_f(p.get('low')), pct)
        if not p['path'] or now - _f(p.get('pathAt')) >= 45:
            p['path'] = (list(p['path']) + [round(pct, 2)])[-PATH_KEEP:]; p['pathAt'] = now
        p['pct'] = round(pct, 2)
        held = (now - _f(p['since'])) / 60
        lq1 = _f(l.get('liqNow')) or _f((x or {}).get('nums', {}).get('liq'))
        lq0 = _f(p.get('liq0'))
        n = (x or {}).get('nums') or {}
        broke = None
        if x or not live:   # 🔌 the off-radar clock starts only while the office is LIVE: a stamp from before a restart (or from the refill) never counts
            p.pop('offSince', None)
        else:
            p.setdefault('offSince', now)
        if not x:
            broke = 'off their radar' if _oe.radar_gone(p.get('offSince'), now, live) else None
        else:   # the live read of THIS pass: narrative collapsing / distributing · −3% in 5 min · buyers under 50%
            broke = _pos.broken_read(x)
        tp = (tape or {}).get(l.get('pairAddress'))
        fv_ = (flows or {}).get(l.get('pairAddress'))   # 🌊 the buy / sell vital (flow.vital) of this seat's last 90s — None = no fresh tape
        # 🏄 RIDE THE VOLUME (owner, 2026-10-14: "we scalp fine but they don't know how to hold on real volume"): a green seat whose last 90s are a
        # real crowd buying (BUYERS + hot = ≥ 8 distinct buyers, buys ≥ 1.3× sells) is NOT banked by the take line, the normal trail or a
        # time window — it rides with a wide trail (RIDE_GIVE % of its peak). Stops, rug / drain / dump exits and "sellers took over" act as ever.
        ride_ = bool(fv_ and fv_.get('state') == 'BUYERS' and fv_.get('hot') and pct > 0)
        ax_ = (ai_exit or {}).get(m)   # 🧠 the model's exit read — handed in ONLY when its own graded record proved the word (exit_read.effects)
        if ax_ == 'ride' and pct > 0 and not (fv_ and fv_.get('state') == 'SELLERS'):
            ride_ = True   # a proven RIDE = the same wide trail as a hot crowd buying (stops, rug / drain / dump exits act as ever)
        p['aiExit'] = ax_
        if ride_:
            p['rideAt'] = now
        elif p.get('rideAt') and now - _f(p['rideAt']) > RIDE_HOLD_SEC:
            p.pop('rideAt', None)
        riding_ = bool(p.get('rideAt')) and pct > 0
        ch = (charts or {}).get(m)
        if not p.get('thesis') and (theses or {}).get(m):
            p['thesis'] = dict((theses or {})[m])    # 🧾 the entry thesis: saved ONCE with the position (its own copy), never rewritten
        th = p.get('thesis')
        stop = min(_f(th['stopPct']), T('stopPct')) if th and th.get('stopPct') else T('stopPct')   # this entry's own stop, never wider than the tunable ceiling
        if pol.get('sl'):   # 🎛 CREATOR OVERRIDE: your maximum tolerated loss can only make the stop TIGHTER (the catastrophic stop stays above it, untouched)
            stop = min(stop, _f(pol['sl']))
        tier_ = _opp.tier_of_tag((l.get('bought') or {}).get('tag'))
        if tier_ in _opp.TIER_STOP:   # 🎯 a lower-confidence entry risks less: the stop ceiling follows its tier (A 25 · B 18 · C 12) — only ever TIGHTER
            stop = min(stop, _opp.TIER_STOP[tier_])
        if fv_ and fv_.get('state') == 'SELLERS' and pct < 0:   # 🌊 sellers lead a red seat: the stop tightens (never wider, never under the floor)
            stop = min(stop, max(_ci.STOP_FLOOR, stop * FLOW_TIGHT))
        noise_ = is_noise(x)   # 🔊 a coin with MASSIVE volume swings 20–30% on noise: wide stop + a later take (owner, 2026-10-15)
        if noise_ and not l.get('ownerLvAt'):
            stop = max(stop, NOISE_SL) if stop < _ci.CATASTROPHIC_STOP else stop
            stop = min(stop, _ci.CATASTROPHIC_STOP - 5)
        if ax_ == 'widen' and pct < 0 and not l.get('ownerLvAt') and not (fv_ and fv_.get('state') == 'SELLERS'):   # 🧠 a PROVEN model WIDEN: a red seat still bought gets room
            stop = min(max(stop, stop * _er.WIDEN), _er.WIDEN_MAX, _ci.CATASTROPHIC_STOP - 5)
            p['widened'] = round(stop, 1)
        own_ = l.get('ownerLvAt')   # ✋ YOUR line on ANY coin of the card (dragged on the chart): obeyed as set — wider or tighter (it was agent coins only: your GTA 10% read −30%)
        if own_ and _f(l.get('sl')) > 0:
            stop = min(_f(l["sl"]), _ci.CATASTROPHIC_STOP)   # the catastrophic −45% line stays under it
        take = _f(l.get('tp')) if own_ and _f(l.get('tp')) > 0 else take0
        if own_:
            p['owner'] = {'sl': _f(l.get('sl')) or None, 'tp': _f(l.get('tp')) or None, 'at': _f(l.get('ownerLvAt'))}   # filed with the position: "did your hand help?"
        p['stopNow'] = stop   # ⚡ the 6-second guard stops an agent seat at THIS line between ticks (`fast_reap`)
        tr_ = pol.get('trail') or {}
        arm = _f(tr_.get('arm')) if tr_.get('mode') == 'custom' else T('protectAt')
        pr_, prwhy_ = press.get(l.get('pairAddress')) or (None, None)   # 🕵 the early wallets selling on the live tape
        inval_ = _f((th or {}).get('invalidation'))
        chpx_ = _f(((ch or {}).get('f') or {}).get('px'))   # the live chart's last close (same FEELESS candles the screens draw)
        dq_ok_ = not (ch and ch.get('q') and not ch['q'].get('structOk'))   # 🧪 a degraded chart never decides a chart-based exit
        rs_ = _mw.run_state(pct, p['peak'], (vels or {}).get(m, {}).get('state'), bool(th) and dq_ok_ and inval_ > 0 and px < inval_ and 0 < chpx_ < inval_)   # ⚡ the run: live price AND live chart under the line
        runner_ = rs_ in ('ACCELERATING', 'RUNNING') and pct > 0   # 🏃 a winner the chart still backs: no time window sells it
        dead_ = (_opp.dead_now(x) if x else None) or ('off their radar (not a coin they trade any more)' if broke == 'off their radar' else None)
        if dead_ and live:
            p.setdefault('deadSince', now)
        else:
            p.pop('deadSince', None)
        tight = 0.6 if (vels or {}).get(m, {}).get('state') == 'REVERSING' or pr_ == 'WATCH' or ((ai_exit or {}).get(m) == 'tight' and pct > 0) else 1.0   # 📉 P/L REVERSING: the trail banks sooner (tighter protection, never looser)
        trail_line = (p['peak'] - _f(tr_.get('pct')) * tight) if tr_.get('mode') == 'custom' else p['peak'] * (1 - T('giveBackPct') * tight / 100)
        trail_on = tr_.get('mode') != 'off'
        max_hold = _f(pol.get('maxHold')) or None
        vl = (vels or {}).get(m) or {'state': 'UNKNOWN'}
        quality = _so.chart_quality(ch)[0] if ch else None
        mg_, need_ = (margins or {}).get(m) or (None, None)
        rv = _ci.review(th, ch, pct, held, p.get('granted')) if th else None
        base_w = max(int((th or {}).get('expectedHoldWindows') or _ci.MIN_WINDOWS), _so.BASE_WINDOWS)
        if rv and rv['window'] > int(p.get('lastWin') or 0):   # a 5-minute checkpoint: a thesis that still stands keeps its BASE windows; past them a WINNER must EARN each one
            p['lastWin'] = rv['window']
            if rv['verdict'] == 'valid':
                cap_w = int(th.get('maxHoldWindows') or _ci.MAX_WINDOWS)
                if rv['window'] + 1 <= base_w:
                    p['granted'] = min(cap_w, max(int(rv['granted']), rv['window'] + 1))
                else:
                    earned, ewhy = _so.extension(pct, vl, 'valid', (lq1 / lq0) if lq0 > 0 and lq1 > 0 else None, quality, mg_, need_)
                    p['extWhy'] = ewhy
                    if earned and rv['window'] + 1 <= cap_w:
                        p['granted'] = min(cap_w, max(int(rv['granted']), rv['window'] + 1))
                        p['ext'] = (list(p.get('ext') or []) + [{'at': now, 'window': rv['window'] + 1, 'why': ewhy}])[-12:]
        granted = int(p.get('granted') or (th or {}).get('expectedHoldWindows') or _ci.MIN_WINDOWS)
        if max_hold:
            granted = max(1, min(granted, int(max_hold // _ci.WINDOW_MIN) or 1))
        mine = _uni.is_agent(l)   # R5 / R8 / R9 act only on coins the agents put there (their read is the reason it is held); every coin gets R1–R4 + R7
        st, rule, ev, act = 'HOLD', 'R10 hold', f"{pct:+.1f}% · peak {p['peak']:+.1f}% · take line +{take:g}%", None
        dr_ = _drn.read((x or {}).get('vitals'), (x or {}).get('nums'), fv_, None, (rug or {}).get(l.get('pairAddress')))   # 🩸 the drain read of this seat (no fetch)
        p['drain'] = {'score': dr_['score'], 'state': dr_['state'], 'xl': dr_['xl']}
        drw_ = _drn.exit_why(dr_) if mine and live else None
        if lq0 > 0 and 0 < lq1 < lq0 * _uni.DRAIN_PULL:
            st, rule, ev, act = 'EXIT INVALIDATED', 'R1 liquidity collapse', f'pool ${lq1 / 1000:.1f}K = {round(lq1 / lq0 * 100)}% of its ${lq0 / 1000:.1f}K entry depth', 'pull'
        elif (rug or {}).get(l.get('pairAddress')):   # 🚨 the rug radar on the live tape: the creator / a top-holder wallet is dumping — a hard safety exit
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R4r rug radar', f"{rug[l.get('pairAddress')]} at {pct:+.1f}%", 'pull'
        elif drw_:   # 🩸 R4d DRAIN: holders leaving / the pool draining / sellers under a heavy top-10 bag — out before the chart is drained
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R4d drain', f"{drw_} at {pct:+.1f}%", 'pull'
        elif pr_ == 'HIGH' and live:   # 🕵 the launch's early buyers are unloading into us (creator / a dump-record wallet / a cluster): out before the timeout
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R4e early wallets unloading', f"{prwhy_} at {pct:+.1f}%", 'pull'
        elif tp == 'dump' and ((n.get('buy') is not None and _f(n['buy']) < DUMP_BUY_MAX) or (n.get('buy') is None and pct < 0)):   # 🩸 a REAL dump: sellers lead (buyers < 50%) — it used to sell ANY green coin on a 'dump' read with buyers at 61–81% (Macca +4%, Starman +3.6%, Dip +4.6%)
            st, rule, ev, act = ('TAKE' if pct > 0 else 'EXIT INVALIDATED'), 'R4 whale dump', f"the tape reads a dump at {pct:+.1f}%" + (f", buyers {_f(n['buy']):.0f}%" if n.get('buy') is not None else ''), 'pull'
        elif mine and live and fv_ and fv_.get('state') == 'SELLERS' and pct >= FLOW_BANK_PCT:   # 🌊 the buy / sell vital flipped to sellers on a green seat: bank it into the last buyers
            st, rule, ev, act = 'TAKE', 'R4f sellers took over', f"{pct:+.1f}% and {fv_.get('why')} — banked into the last buyers", 'pull'
        elif mine and live and fv_ and fv_.get('state') == 'PEAK' and fv_.get('tape') == 'climax' and pct >= FLOW_CLIMAX_PCT:   # 🏔 buyers paying up while the price stalls: the top forming
            st, rule, ev, act = 'TAKE', 'R4c buying climax', f"{pct:+.1f}% and {fv_.get('why')} — banked into the climax", 'pull'
        elif pct <= -_ci.CATASTROPHIC_STOP:   # 🧱 the hard ceiling, every coin Reaper watches — a constant: no tunable, promotion or thesis reaches it
            st, rule, ev, act = 'EXIT INVALIDATED', 'R5x catastrophic stop', f'{pct:+.1f}% ≤ −{_ci.CATASTROPHIC_STOP:g}% (hard-coded)', 'pull'
        elif pol.get('sl') and pct <= -_f(pol['sl']):   # 🎛 the creator's hard stop: every coin Reaper watches, in every mode
            st, rule, ev, act = 'EXIT INVALIDATED', 'R5c creator stop', f"{pct:+.1f}% ≤ −{_f(pol['sl']):g}% (your stop-loss override)", 'pull'
        elif max_hold and (mine or control) and held >= max_hold and live:   # 🎛 the creator's max hold: Reaper cannot hold past it (a time rule: waits for LIVE after a restart)
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R9c creator max hold', f"{held:.0f} min held ≥ your {max_hold:g}-minute max hold, {pct:+.1f}%", 'pull'
        elif manual and pol.get('tp') and pct >= _f(pol['tp']):   # 🎛 CREATOR MANUAL: the overrides YOU set still act — your take line
            st, rule, ev, act = 'TAKE', 'R6 take line', f"{pct:+.1f}% ≥ +{_f(pol['tp']):g}% (your take-profit, creator manual)", 'pull'
        elif manual and tr_.get('mode') == 'custom' and p['peak'] >= arm and pct <= trail_line and pct >= MIN_KEEP:   # … and your custom trail
            st, rule, ev, act = 'TAKE', 'R7 trailing protection', f"peaked {p['peak']:+.1f}%, now {pct:+.1f}% — {_f(tr_.get('pct')):g} points off the peak (your trail, creator manual)", 'pull'
        elif manual:   # 🎛 CREATOR MANUAL: only the hard safety exits above + your own overrides act — every discretionary call below is yours
            st, rule, ev = 'HOLD', 'R10 creator manual', f"{pct:+.1f}% · you hold the decisions — only the hard safety exits and your own limits act"
        elif mine and pct <= -stop:   # their own coins carry no card stop (ride-or-rug seats) — this is it; other coins keep the card's own stop
            st, rule, ev, act = 'EXIT INVALIDATED', 'R5 stop', f"{pct:+.1f}% ≤ −{stop:g}%" + (f" ({'; '.join((th.get('stopParts') or [])[:2])})" if th else ' (no thesis on file: the ceiling)'), 'pull'
        elif mine and live and dead_ and held >= DEAD_CASH_MIN and now - _f(p.get('deadSince') or now) >= DEAD_CASH_MIN * 60 and pct < take:   # 💀 dead 15 min: CASH beats a coin nobody trades — no replacement needed
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R11x dead coin → cash', f"{pct:+.1f}% — {dead_} for {round((now - _f(p.get('deadSince'))) / 60)} min; the seat refills from the live bench", 'pull'
        elif pct >= take and not runs and not riding_:
            st, rule, ev = 'TAKE', 'R6 take line', f"{pct:+.1f}% ≥ +{take:g}% ({tsrc} take) — the card's own take rule banks it"
        elif mine and rv and rv['verdict'] == 'invalid' and held >= 2:   # the reason it was bought is gone: out, green or red — P&L does not decide this
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R5t thesis invalidated', f"{pct:+.1f}% — entered on {th.get('structure')}; now {rv['why'][0]}", 'pull'
        elif trail_on and p['peak'] >= arm and pct <= trail_line and pct >= MIN_KEEP and not (riding_ and pct > p['peak'] * (1 - RIDE_GIVE / 100)):
            st, rule, ev, act = 'TAKE', ('R7v trail tightened' if tight < 1 else 'R7 trailing protection'), f"peaked {p['peak']:+.1f}%, now {pct:+.1f}% — " + (f"{_f(tr_.get('pct')) * tight:g} points off the peak (your trail" + (', tightened: P/L reversing)' if tight < 1 else ')') if tr_.get('mode') == 'custom' else f"gave back over {T('giveBackPct') * tight:g}% of it" + (' (tightened: P/L reversing)' if tight < 1 else '')), 'pull'
        elif mine and rs_ == 'BREAKING DOWN' and pct >= MIN_KEEP:   # ⚡ a green coin that just lost its invalidation line: banked now, not at the next window
            st, rule, ev, act = 'TAKE', 'R7b breakdown', f"{pct:+.1f}% and the price lost its invalidation line {inval_:.10g} — banked on the live chart", 'pull'
        elif mine and rv and rv['verdict'] == 'weak' and 'lower high' in rv['why'][0] and pct >= MIN_KEEP and vl.get('state') != 'ACCELERATING' and not riding_:   # green is not a reason to keep holding — unless its P/L is still accelerating (the trail protects it: let a winner work)
            st, rule, ev, act = 'TAKE', 'R7s structure turned', f"{pct:+.1f}% and {rv['why'][0]} — banked before it is given back", 'pull'
        elif mine and live and not riding_ and not (runner_ and not (mg_ is not None and _f(mg_) >= _f(need_))) and rv and rv['window'] >= granted and rv['verdict'] == 'valid' and rv['window'] >= base_w and pct < take:   # a runner keeps its seat on time — only a clearly better challenger takes it   # ⏳ past its base hold a seat is EARNED, never kept by default
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R9e no extension earned', f"{rv['window']} of {granted} windows used, {pct:+.1f}% — {p.get('extWhy') or 'a winner earns extra time, this seat did not'}", 'pull'
        elif mine and live and not runner_ and not riding_ and rv and rv['window'] >= granted and rv['verdict'] == 'weak' and pct < take:   # its windows are used up and the chart earned no more (time: LIVE only)
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R9 windows used', f"{rv['window']} of {granted} five-minute windows used, {pct:+.1f}%, {rv['why'][0]}", 'pull'
        elif mine and live and held >= DEAD_HOLD_MIN and pct < take and dead_:   # 💀 nobody trades it / they can't read it any more: the seat goes to a coin people ARE trading (swap only — merge_reaper)
            st, rule, ev, act = ('TAKE' if pct >= MIN_KEEP else 'EXIT INVALIDATED'), 'R11 dead coin', f"{pct:+.1f}% after {held:.0f} min — {dead_} (swapped as soon as a replacement clears; cash after {DEAD_CASH_MIN:g} min dead)", 'pull'
        elif mine and live and held >= MOMENTUM_MIN and broke and pct >= MIN_KEEP:
            st, rule, ev, act = 'TAKE', 'R8 momentum failed', f'{pct:+.1f}% and {broke} after {held:.0f} min — banked while it is still a gain', 'pull'
        elif mine and live and not runner_ and not th and held >= T('timeMaxMin') and broke and pct < take / 2:
            st, rule, ev, act = 'EXIT INVALIDATED', 'R9 time', f"{held:.0f} min held, {pct:+.1f}%, {broke} — no read left to wait on", 'pull'
        elif riding_:
            st, rule, ev = 'PROTECT', 'R10r riding the volume', f"{pct:+.1f}% · a real crowd is buying ({(fv_ or {}).get('why') or 'buyers lead the tape'}) — held past the take line; banks only {RIDE_GIVE:g}% off its peak {p['peak']:+.1f}% or when sellers take over"
        elif runs and pct >= take:   # AGENTS CHOOSE: past the base line the coin runs only while their read stays clean — the trail above banks it
            st, rule, ev = 'PROTECT', 'R6 take line', f"{pct:+.1f}% ≥ +{take:g}% (base take, AGENTS CHOOSE): they read it every pass — it runs while clean, the trail banks it under {max(MIN_KEEP, trail_line):+.1f}%" if trail_on and p['peak'] >= arm else f"{pct:+.1f}% ≥ +{take:g}% (base take, AGENTS CHOOSE): they read it every pass — it runs while clean"
        elif tp == 'dump':
            st, rule, ev = 'PROTECT', 'R4 whale dump', f'the tape reads a dump at {pct:+.1f}% — buyers still hold it'
        elif held >= MOMENTUM_MIN and broke:
            st, rule, ev = 'PROTECT', 'R8 momentum failed', f'{pct:+.1f}% and {broke} — it gives its seat to the next cleared read'
        elif trail_on and p['peak'] >= arm:
            st, rule, ev = 'PROTECT', 'R7 trailing protection', f"armed at peak {p['peak']:+.1f}%: banks under {max(MIN_KEEP, trail_line):+.1f}%"
        if not x and not broke and not act:
            ev += ' · not on the agents\' table (' + ('the office is refilling after a restart' if not live else f"{round(now - _f(p.get('offSince')))}s — under the {_oe.RADAR_GRACE_SEC}s grace") + '): nothing is ruled on that gap'
        if not live and not act:
            ev += ' · OFFICE WARMING UP — time and read exits wait for LIVE; price, pool and safety exits stand'
        degraded = bool((rv or {}).get('degraded')) or bool(ch and ch.get('q') and not ch['q'].get('structOk'))
        if degraded and not act:   # 🧪 the chart data degraded on a held coin: nothing chart-based is ruled — R1–R5x, the stop and the trail still stand
            ev += f" · DATA DEGRADED ({ch['q']['state'] if ch and ch.get('q') else 'no data'}) — held on the hard risk / liquidity / execution rules only"
        if st == 'HOLD' and rv and rv['verdict'] == 'valid':
            ev = f"{pct:+.1f}% · {'; '.join(rv['why'][:4])} · window {rv['window'] + 1} of {granted}"
        held_s = held * 60
        young_ = is_young(p)
        if not act and mine and live and young_ and pct >= SCALE_AT and not degraded_pre(ch, rv):   # 🍼 a coin < 5 min old at entry: ALL of it banked at +10% (rugs land in its first minutes)
            st, rule, ev, act = 'TAKE', 'R6y young coin banked', f"{pct:+.1f}% ≥ +{SCALE_AT:g}% on a coin {_f(young_) * 60:.0f} min old at entry: all of it sold now — {YOUNG_WHY}", 'pull'
        elif not act and mine and live and pct >= (NOISE_TP if noise_ else SCALE_AT) and not p.get('scaled') and not degraded_pre(ch, rv):   # 💰 SCALE-OUT: half banked at +10%, the rest rides the trail
            st, rule, ev, act = 'TAKE', 'R6h half banked', f"{pct:+.1f}% ≥ +{SCALE_AT:g}%: {SCALE_PCT:g}% sold now, the rest rides the trail (replay: +6.5% avg vs +4.3% real)", 'trim'
            p['scaled'] = now
        if l.get('picked'):
            study_note(p, rule, act, st, pct, px, now)   # 👤 your seat: every ruling change is filed — what the agents would have done, and when
        act, st, ev = owner_ask(p, l, act, st, rule, ev, pct, px, now)   # ✋ your SL / TP is set: a soft exit asks you first (hard safety exits never wait)
        if act and pct >= RUNWAY_KEEP and (str(rule).split(' ')[0] in RUNWAY_RULES) and (held_s < RUNWAY_SEC or str(rule).startswith('R5t')):
            ev += (f" · 🛫 runway: a green coin is not banked in its first {RUNWAY_SEC / 60:.0f} min ({round(RUNWAY_SEC - held_s)}s left) — the trail still sells it under +{RUNWAY_KEEP:g}%"
                   if not str(rule).startswith('R5t') else ' · 🛫 a broken thesis never sells a GREEN coin — the trail protects it')
            act, st = None, 'PROTECT'
        if act and soft_exit(rule) and str(rule).split(' ')[0] in BENCHED:   # 🪑 this rule's own record: holding beat its sales → it sells nothing
            ev += f" · 🪑 {str(rule).split(' ')[0]} is BENCHED — its sales typically lost to holding 30 min (its own record); the trail / stops still act"
            act, st = None, 'PROTECT'
        if act and soft_exit(rule):   # 📸 a profit-side exit needs its snapshots (the model's fresh read sets how many)
            ok_, seen_, need_ = soft_confirm(p, rule, now, (ai_words or {}).get(m))
            if not ok_:
                ev += f" · 📸 snapshot {seen_}/{need_} — sells only if the next read still says so" + (' (AI: RIDE)' if (ai_words or {}).get(m) == 'ride' else '')
                act, st = None, 'PROTECT'
        elif not act:
            p.pop('snap', None)
        p['decPx'], p['decAt'] = px, now   # ⚡ the price this decision stood on: the fast guard wakes Reaper when the live price moves materially from it
        if act:
            p.setdefault('askAt', now); p['askRule'] = rule
        p['state'], p['rule'] = st, rule
        p['chartNow'] = (ch or {}).get('state')
        decision = ('TAKE PROFIT' if st == 'TAKE' else 'EXIT') if act or (rule.startswith('R6') and st == 'TAKE') else 'PROTECT' if st == 'PROTECT' else 'HOLD 5 MORE' if rv and rv['verdict'] == 'valid' and rv['window'] >= 1 else 'HOLD'
        pos[m] = p
        out.append({**base, 'state': st, 'rule': rule, 'evidence': ev, 'action': act, 'exec': 'confirmed', 'entry': entry, 'px': px, 'pct': round(pct, 2), 'peak': round(p['peak'], 2),
                    'dd': round(p['peak'] - pct, 2), 'heldMin': round(held, 1), 'liq': lq1 or None, 'liqPct': round(lq1 / lq0 * 100) if lq0 > 0 and lq1 > 0 else None,
                    'flow': fv_, 'drain': ({'score': dr_['score'], 'state': dr_['state'], 'why': [q[0] for q in dr_['parts']][:2]} if dr_['state'] != 'CLEAR' else None),   # CLEAR = nothing to say (payload cap)
                    'trigger': None if not x else _opp.narrative(x)[0], 'devil': None, 'weather': (weather_ or {}).get('regime'),
                    'take': take, 'takeSource': tsrc, 'stop': -stop, 'hardStop': -_ci.CATASTROPHIC_STOP, 'decision': decision,
                    'armAt': round(arm, 2) if trail_on else None, 'trailAt': round(max(MIN_KEEP, trail_line), 2) if trail_on and p['peak'] >= arm else None, 'obeying': (f'{tsrc} take' if rule.startswith('R6') else OBEY.get(rule.split(' ')[0], 'thesis hold')),
                    'thesis': None if not th else {k: th.get(k) for k in ('structure', 'call', 'triggerRule', 'why', 'support', 'invalidation', 'stopPct', 'expectedHoldWindows', 'maxHoldWindows', 'reasons', 'risks', 'at')},
                    'structure': (ch or {}).get('state'), 'chartSrc': (ch or {}).get('src'), 'verdict': (rv or {}).get('verdict'), 'why': (rv or {}).get('why') or [], 'window': (rv or {}).get('window'), 'granted': granted if th else None,
                    'nextReview': (rv or {}).get('next') if rv else round((int(held // _ci.WINDOW_MIN) + 1) * _ci.WINDOW_MIN * 60 - held * 60),
                    'chart': None if not ch else {k: ch.get(k) for k in ('trend', 'chop', 'mom', 'ext')} | {k: (ch.get('f') or {}).get(k) for k in ('hh', 'hl', 'lh', 'll', 'lastHigh', 'lastLow', 'accel', 'decay', 'upWick', 'liqD')},
                    **{'posRound': _tr.position_round(_f(p.get('since')) or now, now), 'roundAction': _tr.action_word(st), 'mfe': round(_f(p.get('peak')), 2), 'mae': round(_f(p.get('low')), 2), 'src': p.get('src')},   # ⏱ the position's own 5-minute round
                    'ask': p.get('ask'), 'would': p.get('would') if l.get('picked') else None, 'study': list(p.get('study') or [])[-4:] if l.get('picked') else None, 'tape': tp, 'usd': round(_f(l.get('units')) * px, 4), 'warden': p.get('warden'), 'dataDegraded': degraded, 'data': _md.compact((ch or {}).get('q')),
                    'vel': vl.get('state'), 'velWhy': vl.get('why'), 'run': 'DEAD' if dead_ else ('HEALTHY' if rs_ == 'STALLING' and pct >= 0 and (rv or {}).get('verdict') == 'valid' else rs_), 'runner': runner_, 'deadMin': None if not p.get('deadSince') else round((now - _f(p['deadSince'])) / 60, 1), 'quality': quality, 'ext': len(p.get('ext') or []), 'extWhy': p.get('extWhy'), 'baseWindows': base_w if th else None,
                    'launch': p.get('launch'), 'onTable': bool(x), 'offRadarSec': None if x or not p.get('offSince') else round(now - _f(p.get('offSince'))), 'live': bool(live), 'limits': {'tp': pol.get('tp'), 'sl': pol.get('sl'), 'maxHold': max_hold, 'trail': tr_.get('mode'), 'manual': manual}})
    gone = []
    for m in [m for m in pos if m not in on]:
        p = pos.pop(m)
        gone.append({**p, 'mint': m, 'leftAt': now})
    return pos, out, gone


# 💰 SCALE-OUT (owner, 2026-10-15: "sell half at +10%, trail the rest"). After-path replay on 154 real exits whose coin reached +10% (held or
# within 30 min after our sale), fills at the price SEEN and a rug after the take = −100% on the rest: 75% at +10 → avg +6.5% / median
# +8.9% vs what we really got +4.3% / +5.2% (better 87, worse 67); 50% only +3.1% avg (an earlier replay overstated it as +8.6%).
# Selection bias: only coins that reached +10% — the live twin (after_path.scale_twin) keeps judging it on new exits. Once per position.
SCALE_AT = 10.0
SCALE_PCT = 75.0   # 2026-10-15: 50% left too much on the table for rugs after the take (honest replay: half +3.1% avg · 75% +6.5% · real +4.3%)


# ✋ YOUR LINE IS RESPECTED (owner, 2026-10-15: "if I adjust the SL and / or TP they need to respect it or give me a reason to approve their
# decision"): on a coin whose SL / TP you dragged, every discretionary exit (trail, thesis, time, flow banks, scale-out, dead coin …) becomes a
# QUESTION with its reason — the seat is held until you ✅ approve (the next tick sells) or ✋ keep your line (that rule is quiet 10 min).
# Hard safety exits never wait: pool collapse, scan / rug / drain / early-wallet dumps, the −45% line, your own stop and the creator overrides.
ASK_HARD = ('R1', 'R2', 'R3', 'R4', 'R4r', 'R4d', 'R4e', 'R5', 'R5x', 'R5c', 'R9c')
# ✋ YOUR COIN IS YOURS (owner, 2026-10-15: "they sold one of my entries … im tryna teach them"): on a coin YOU picked or put your lines on,
# ONLY these may sell without asking — a pulled pool (R1), the catastrophic −45% (R5x), your creator limits (R5c / R9c) and your OWN stop /
# take (R5 / R6, only when the line is yours). Every other rule — dump reads, rug radar, drain, scans, trails, thesis — becomes a question.
OWNER_HARD = ('R1', 'R5x', 'R5c', 'R9c')
DUMP_BUY_MAX = 50.0


def yours(l):
    """A coin the owner picked (leg `picked`) or put their own stop / take on (`ownerLvAt`)."""
    return bool((l or {}).get('picked') or (l or {}).get('ownerLvAt'))


def owner_hard(l, key):
    """May this rule sell the owner's coin without asking?"""
    if key in OWNER_HARD:
        return True
    own = bool((l or {}).get('ownerLvAt'))
    return (key == 'R5' and own and _f((l or {}).get('sl')) > 0) or (key == 'R6' and own and _f((l or {}).get('tp')) > 0)
ASK_OK_SEC = 180.0     # an approval lets that rule sell for this long
ASK_KEEP_SEC = 600.0   # "keep my line" quiets that rule this long


# 👤 YOUR SEAT IS STUDIED (owner, 2026-10-15: "add my own coins into seats — they track my every move and study during that seat, AI suggests"):
# on a coin you picked the agents never move by themselves; every time Reaper's ruling on it changes it is filed (`study`), and the FIRST
# time they would have sold is kept (`would`: rule, % and price). When the seat closes, `owner_seats` compares your real result with
# where the agents would have got out — measured, never a promise.
STUDY_KEEP = 14


def study_note(p, rule, act, st, pct, px, now):
    p['pick'] = True
    st_ = list(p.get('study') or [])
    key = f"{str(rule).split(' ')[0]}:{st}:{bool(act)}"
    if not st_ or st_[-1].get('k') != key:
        st_.append({'k': key, 'at': round(now), 'rule': str(rule)[:60], 'state': st, 'sell': bool(act), 'pct': round(pct, 2)})
        p['study'] = st_[-STUDY_KEEP:]
    if act and not p.get('would'):
        p['would'] = {'at': round(now), 'rule': str(rule)[:60], 'pct': round(pct, 2), 'px': px}


def owner_seats(positions):
    """👤 Your picked seats, closed: your real result vs the % the agents would have sold at (their first exit call on it).
    → {n, med, avg, cmp: {n, you, agents, youBetter}, last: [...]}"""
    import statistics
    rows = []
    for p in positions or []:
        if not p.get('pick'):
            continue
        r = p.get('realPct')
        rows.append({'sym': p.get('sym'), 'real': None if r is None else round(_f(r), 1), 'would': (p.get('would') or {}).get('pct'),
                     'rule': (p.get('would') or {}).get('rule'), 'at': p.get('closedAt'), 'peak': p.get('peak')})
    real = [x['real'] for x in rows if x['real'] is not None]
    both = [x for x in rows if x['real'] is not None and x['would'] is not None]
    return {'n': len(real), 'med': round(statistics.median(real), 1) if real else None, 'avg': round(sum(real) / len(real), 1) if real else None,
            'cmp': {'n': len(both), 'you': round(statistics.median([x['real'] for x in both]), 1) if both else None,
                    'agents': round(statistics.median([_f(x['would']) for x in both]), 1) if both else None,
                    'youBetter': sum(1 for x in both if x['real'] > _f(x['would']))},
            'last': rows[-6:][::-1]}


def owner_ask(p, l, act, st, rule, ev, pct, px, now):
    """→ (act, st, ev). Only for coins with YOUR line (leg ownerLvAt); hard rules pass through."""
    if not yours(l) or not act:   # 👤 a coin YOU picked is yours too: soft exits ask first
        if not act:
            p.pop('ask', None)
        return act, st, ev
    key = str(rule).split(' ')[0]
    if owner_hard(l, key):
        p.pop('ask', None)
        return act, st, ev
    ok_, no_ = p.get('askOk') or {}, p.get('askNo') or {}
    if ok_.get('rule') == key and now - _f(ok_.get('at')) <= ASK_OK_SEC:
        p.pop('ask', None)
        return act, st, ev + ' · ✅ you approved'
    if no_.get('rule') == key and now - _f(no_.get('at')) <= ASK_KEEP_SEC:
        return None, 'PROTECT', ev + ' · ✋ you kept your line — this rule is quiet for 10 min'
    old = p.get('ask') or {}
    p['ask'] = {'rule': key, 'name': rule, 'why': str(ev)[:220], 'pct': round(pct, 2), 'px': px, 'at': old.get('at') if old.get('rule') == key else now}
    return None, 'PROTECT', ev + ' · ✋ your SL / TP is set — Reaper ASKS you first (approve or keep your line)'


def pred_record(positions):
    """🔮 The agents' predictions (thesis `pred`, the real-money memory's estimate at the buy) vs the REAL result of each closed trade:
    → {n, hit (% same side of 0), err (median |pred − real|), better: {n, med} for trades it predicted ≥ the median prediction, worse: …}."""
    import statistics
    rows = [(_f((p.get('thesis') or {}).get('pred', {}).get('pct')), _f(p.get('realPct'))) for p in positions or []
            if p.get('confirmed') and p.get('realPct') is not None and isinstance((p.get('thesis') or {}).get('pred'), dict)]
    if not rows:
        return {'n': 0}
    cut = statistics.median([a for a, _ in rows])
    hi = [b for a, b in rows if a >= cut]
    lo = [b for a, b in rows if a < cut]
    return {'n': len(rows), 'hit': round(sum(1 for a, b in rows if (a > 0) == (b > 0)) / len(rows) * 100), 'err': round(statistics.median([abs(a - b) for a, b in rows]), 1),
            'better': {'n': len(hi), 'med': round(statistics.median(hi), 1) if hi else None}, 'worse': {'n': len(lo), 'med': round(statistics.median(lo), 1) if lo else None}}


def ask_grade(log, price_of, now, after=900.0):
    """Your answers to Reaper's questions, judged 15 min later: KEEP was right when the coin is at / above where it was asked, APPROVE was
    right when it is below. → (log, {kept: [n, right], approved: [n, right]})."""
    rows, rec = [dict(r) for r in log or []], {'kept': [0, 0], 'approved': [0, 0]}
    for r in rows:
        if r.get('res') is None and now - _f(r.get('at')) >= after:
            q = _f(price_of(r.get('mint')))
            if q > 0 and _f(r.get('px')) > 0:
                r['res'] = round((q / _f(r['px']) - 1) * 100, 2)
        if r.get('res') is not None:
            k = 'kept' if r.get('choice') == 'keep' else 'approved'
            rec[k][0] += 1
            rec[k][1] += int((r['res'] >= 0) if k == 'kept' else (r['res'] < 0))
    return rows[-200:], rec


# 🍼 YOUNG COINS BANK WHOLE (2026-10-15, 292 confirmed real agent exits): 141 coins < 5 min old at entry won 72% (median +5%) but held 12 of the
# 16 rugs (−75% avg) — a rug lands in the first minutes, mostly while the seat is UP (median peak +3.8%). Replay, oldest 60% / newest 40%,
# fills at the line − 1.5%: selling ALL at +10% → +1.4% / +1.8% avg vs real +0.0% / −2.2% (passes both halves); 75% at +10 (today) +1.0 / +0.8;
# banking at +3 or +5 LOSES in both halves (it cuts the winners). Coins 5 min+ gained nothing from any early take, so they keep the scale-out.
YOUNG_MAX_H = 5 / 60
YOUNG_WHY = 'replay on our own real exits: whole at +10% beat 75% in both halves (rugs come in the first minutes)'


def is_young(p):
    """The coin's launch age at entry (hours) when it is under YOUNG_MAX_H, else None. Unknown age = not young (the normal scale-out)."""
    for src in ((p or {}).get('launch') or {}, (p or {}).get('li') or {}):
        a = src.get('ageH')
        if a is not None:
            a = _f(a)
            return a if 0 <= a < YOUNG_MAX_H else None
    return None


def degraded_pre(ch, rv):
    return bool((rv or {}).get('degraded')) or bool(ch and ch.get('q') and not ch['q'].get('structOk'))


# 🔊 NOISE STOPS (owner, 2026-10-15: "pump-trending coins with massive volume get noise SL and TP, like 30–40% SL"): a coin trading ≥ NOISE_VOL an
# hour or on Pump's trending board gets a NOISE_SL stop (never past −40, the −45% catastrophic line stays under it) and its scale-out waits
# for NOISE_TP. The owner's own dragged line always wins. Owner's rule, not yet proven on our record — judge it on the R5 exits of big coins.
NOISE_VOL = 150_000.0
NOISE_SL = 35.0
NOISE_TP = 30.0


def is_noise(row):
    x = row or {}
    return _f((x.get('vitals') or {}).get('vol1h')) >= NOISE_VOL or _uni.on_trend(x)


# 🛫 THE RUNWAY (owner, 2026-10-15: "Reaper keeps exiting too fast, he scary"). 291 confirmed real exits: median hold 2–3 min on every rule, and
# what the coin did in the 30 min AFTER we sold (after_path, vs our entry): R7 trails banked +6% then 87% reached +10% (median peak +34%) ·
# R5t on green coins banked +10% then 94% ran on (median peak +70%) · R5 stops at −11% were mostly right (median end −13%). So a GREEN
# coin (≥ RUNWAY_KEEP) gets RUNWAY_SEC before any profit-side rule may bank it, and R5t never sells a green coin; under +2% the trail still
# sells, and stops / −45% / rug / drain / dump stay instant.
RUNWAY_SEC = 6 * 60.0
RUNWAY_KEEP = 2.0
RUNWAY_RULES = ('R6', 'R7', 'R7v', 'R7s', 'R7b', 'R5t', 'R8', 'R9', 'R9e', 'R4f')


# 📸 SNAPSHOT CONFIRMATION (owner, 2026-10-14: "we are still exiting trades too fast — listen to the AIs and take 2–3 snapshot decisions on
# whether to TP or SL"): a PROFIT-side / soft exit (take line, trails, structure turned, momentum failed, time, sellers took over, climax)
# fires only once it has been the ruling on SNAP_N consecutive reads at least SNAP_GAP apart — one red candle or a single soft read no
# longer sells a winner. The model's fresh exit read sets N: RIDE → 3, TIGHTEN → 1, none → 2. STOPS, the −45% line, rug / drain / dump,
# scan failures and a broken thesis on a loser stay INSTANT: waiting on a falling coin is how stops filled at −35%.
SOFT_EXITS = ('R6', 'R7', 'R7s', 'R7b', 'R7v', 'R8', 'R9', 'R9e', 'R4f', 'R4c')
BENCHED = set()   # 🪑 soft exit rules whose own after-sale record says holding beat selling (after_path.rule_bench; set by the service each pass)
SNAP_N, SNAP_RIDE_N, SNAP_TIGHT_N = 2, 3, 1
SNAP_GAP = 8.0       # seconds between two counted snapshots
SNAP_FORGET = 90.0   # a snapshot older than this no longer counts (the exit reading went away and came back)


def soft_exit(rule):
    return str(rule or '').split(' ')[0] in SOFT_EXITS


def soft_confirm(p, rule, now, word=None):
    """One more read says `rule` should sell → (confirmed, seen, need). Mutates the position's `snap` {rule, n, at}."""
    need = SNAP_RIDE_N if word == 'ride' else SNAP_TIGHT_N if word == 'tight' else SNAP_N
    key = str(rule or '').split(' ')[0]
    sn = p.get('snap') or {}
    if sn.get('rule') != key or now - _f(sn.get('at')) > SNAP_FORGET:
        sn = {'rule': key, 'n': 0, 'at': 0.0}
    if now - _f(sn.get('at')) >= SNAP_GAP or sn['n'] == 0:
        sn = {'rule': key, 'n': sn['n'] + 1, 'at': now}
    p['snap'] = sn
    return sn['n'] >= need, sn['n'], need


TIME_EXITS = ('R9', 'R9e')   # thesis-review TIME exits (windows used / no extension earned / time) — never R9c, the creator's own max hold
SWAP_EXITS = TIME_EXITS + ('R11',)   # exits that only SWAP (fire only while a replacement is ready); a dead coin is not 'flat churn' — it skips the 🪓 rule
TIME_CUT_PCT = -3.0          # 🪓 a time exit sells a coin that is LOSING at least this much …
SWAP_COST_PCT = 2.0          # … or one a clearly better coin beats by the switch margin: a flat round trip costs ~2% of a $0.12 seat


def merge_reaper(decisions, reports, buys_left=None, edge=None):
    """Reaper's requests join the card's EXISTING agent decisions (the list `agents.manage` returns and the service already acts on): a
    coin the desk would hold is pulled when Reaper asks; a swap / pull the desk already decided stands. No new action kind exists.
    🪓 … and a time exit fires only for a coin that is LOSING (≤ TIME_CUT_PCT) or one a clearly better coin beats (`edge` {mint: (score margin, need)}).
    🪑 With no buy to spare (`buys_left` = buys left this hour − seats already empty, ≤ 0) a TIME exit is deferred: the seat could not be refilled this hour, so selling a flat
    coin to cash only pays the exit and leaves the seat idle (2026-10-11: 15-minute R9 exits emptied seats the budget then kept empty).
    Stops, the rug / drain / scan exits, invalidation, trails, the take line and the creator's max hold are never deferred."""
    out = list(decisions or [])
    left = None if buys_left is None else int(buys_left)
    is_time = lambda r: str(r.get('rule') or '').split(' ')[0] in SWAP_EXITS
    is_flat = lambda r: str(r.get('rule') or '').split(' ')[0] in TIME_EXITS
    for r in sorted(reports or [], key=lambda r: (not is_time(r), _f(r.get('pct')))):   # the weakest flat coin uses a spare replacement first
        if r.get('action') not in ('pull', 'trim'):
            continue
        if left is not None and is_time(r):
            if left <= 0:
                r['deferred'] = 'no replacement is ready (or no buy is free) — a time exit only swaps, it never leaves the seat in cash (stops, invalidation and trails still act)'
                continue
            e_ = (edge or {}).get(r.get('mint'))
            better_ = bool(e_) and e_[0] is not None and _f(e_[0]) >= _f(e_[1])
            if is_flat(r) and _f(r.get('pct')) > TIME_CUT_PCT and not better_:   # 🪓 (2026-10-11: 113 swaps in 4h, nearly every flat coin sold ~1% lighter + fees — the churn WAS the loss)
                r['deferred'] = (f"flat ({_f(r.get('pct')):+.1f}%) and no clearly better coin" + (f" (best is +{_f(e_[0]):.0f} score, needs +{_f(e_[1]):.0f})" if e_ and e_[0] is not None else '')
                                 + f" — a swap costs ~{SWAP_COST_PCT:.0f}% round trip, so it keeps the seat and gets its chance to run (stops and trails still act)")
                continue
            left -= 1
        i = next((i for i, d in enumerate(out) if d.get('pair') == r['pair']), None)
        d = {'pair': r['pair'], 'symbol': r.get('symbol'), 'action': r['action'], 'why': f"☠ Reaper {r['rule']}: {r['evidence']}", 'reaper': r['rule']}
        if i is None:
            out.append(d)
        elif out[i].get('action') == 'hold':
            out[i] = d
    return out


def confirm_exits(exiting, gone, ledger, now, card=None, used=None):
    """📮→☠ A position that left the card is 'exit requested' until the keeper's ledger shows the confirmed sale; only then is it CLOSED
    with the real result. Not confirmed after EXIT_WAIT_SEC → filed as unconfirmed (no result claimed). → (still exiting, closed)
    ONE SALE = ONE RESULT: a coin that left the card and came straight back used to leave two or three waiting records, and the one
    later sale closed them all (12 of 77 archived "real results" were the same sale counted again — memory and the Judge learned each
    twice). The newest record of a coin takes the sale; an older one is filed as a duplicate with no result. `used` = sale
    signatures already filed. Each closed record carries `gap` = real result − the last tracked move (the fill vs what the path saw)."""
    ex = list(exiting or []) + [{**g, 'exit': {'state': 'requested'}} for g in gone or []]
    still, closed, taken = [], [], set(used or ())
    newest = {}
    for p in ex:
        if _f(p.get('since')) >= _f((newest.get(p.get('mint')) or {}).get('since')):
            newest[p.get('mint')] = p
    for p in sorted(ex, key=lambda p: newest.get(p.get('mint')) is not p):   # the newest record of each coin is matched first
        f = fill_state(ledger, p['mint'], 'sell', _f(p.get('askAt') or p.get('leftAt')) - 120, card)
        if f['state'] == 'confirmed' and (f.get('sig') in taken or newest.get(p.get('mint')) is not p):
            closed.append({**p, 'exit': {'state': 'duplicate', 'sig': f.get('sig'), 'at': f.get('at')}, 'confirmed': False, 'realPct': None, 'closedAt': now})
        elif f['state'] == 'confirmed':
            taken.add(f.get('sig'))
            gap = None if f.get('realPct') is None or p.get('pct') is None else round(_f(f['realPct']) - _f(p['pct']), 2)
            closed.append({**p, 'exit': f, 'confirmed': True, 'realPct': f.get('realPct'), 'gap': gap, 'closedAt': f['at']})
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
                for h_ in (5, 10, 15, 30):   # each horizon is stamped ONCE, from the same batched price read (no extra call)
                    if f'p{h_}' not in o and age >= h_:
                        o[f'p{h_}'] = pc
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
           'wx': p.get('wx'), 'warden': p.get('warden'), 'launch': p.get('launch'), 'tag': p.get('tag'), 'owner': p.get('owner'), 'take': p.get('take'), 'exitStructure': p.get('chartNow'), 'windows': p.get('lastWin'),
           'liq': p.get('liq'), 'liqPct': p.get('liqPct'), 'top10': p.get('top10'), 'quality': p.get('quality'), 'dd': bool(p.get('dataDegraded') or p.get('dd')), 'vel': (p.get('vel') or {}).get('state') if isinstance(p.get('vel'), dict) else p.get('vel'),
           'thesis': None if not p.get('thesis') else {k: p['thesis'].get(k) for k in ('structure', 'call', 'triggerRule', 'support', 'invalidation', 'stopPct', 'expectedHoldWindows', 'at', 'pred', 'votes', 'flow', 'distHigh', 'germ', 'germDist')},
           'li': p.get('li'), 'src': p.get('src'), 'gap': p.get('gap'), 'pick': bool(p.get('pick')), 'would': p.get('would'), 'study': list(p.get('study') or [])[-STUDY_KEEP:]}
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


VERIFY_FULL_SEC = 300.0   # the whole chain is re-hashed at most this often; between, only records added since the last check


def _tail_bad(rows, prev, start, h_of):
    bad = 0
    for r in rows[start:]:
        bad += r.get('h') != _hash(prev, h_of(r)); prev = r.get('h')
    return bad


def verify_inc(arch, memo, now):
    """`verify`, incrementally (the loop-lag catcher charged the full re-hash 28s in 8h — two desks ran it every pass): the same count
    when nothing changed; when records were only APPENDED (same anchors, the last checked record still carries its hash) only the new
    ones are hashed, chained from the last checked link; a rolled list, a changed anchor or `VERIFY_FULL_SEC` passed → the full chain.
    A rewrite in the middle is always found by the next full check. → (bad, memo)"""
    a = arch or {}
    cs, ps = a.get('cases') or [], a.get('positions') or []
    fp = (a.get('anchor', ''), a.get('posAnchor', ''), len(cs), cs[-1].get('h') if cs else None, len(ps), ps[-1].get('h') if ps else None)
    m = memo or {}
    if m.get('fp') == fp and now - _f(m.get('fullAt')) < VERIFY_FULL_SEC:
        return m['bad'], m
    old = m.get('fp')
    appended = (old and now - _f(m.get('fullAt')) < VERIFY_FULL_SEC and old[0] == fp[0] and old[1] == fp[1] and fp[2] >= old[2] and fp[4] >= old[4]
                and (old[2] == 0 or cs[old[2] - 1].get('h') == old[3]) and (old[4] == 0 or ps[old[4] - 1].get('h') == old[5]))
    if appended:
        bad = m['bad'] + _tail_bad(cs, old[3] if old[2] else a.get('anchor', ''), old[2], lambda r: r.get('d')) \
            + _tail_bad(ps, old[5] if old[4] else a.get('posAnchor', ''), old[4], lambda r: {k: v for k, v in r.items() if k != 'h'})
        return bad, {'fp': fp, 'bad': bad, 'fullAt': m.get('fullAt')}
    bad = verify(a)
    return bad, {'fp': fp, 'bad': bad, 'fullAt': now}


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
    late = [d for d in _pd._judged(state, 5) if d.get('ce') == 'ENTER NOW' and d.get('kind') == 'enter']
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
    for d in _pd._judged(state, 5):
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
    return {'readings': int(n.get('pts') or len(s)), 'of': _sn.SERIES_N, 'ageSec': age, 'stale': age is not None and age > STALE_SEC, 'intervalSec': round(sum(gaps) / len(gaps), 1) if gaps else None,
            'missing': miss, 'sources': [_sn.SOURCES.get(k, k) for k in src], 'confidence': round(min(1.0, int(n.get('pts') or 0) / 5) * (len(fields) - len(miss)) / len(fields), 2),
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






def devil_record(state, hours=72, now=0.0):
    """⚖ Every objection TYPE with its own history: how often it was raised and what those coins did 5 minutes later (saved = flat or
    down). Old calls without a stored rule id are read from their text. → [{rule, hard, n, med, saved}]"""
    g = {}
    for d in list(((state or {}).get('open') or {}).values()) + list((state or {}).get('done') or []):
        if d.get('devil') != 'object' or (now and now - _f(d.get('at')) > hours * 3600):
            continue
        g.setdefault(d.get('devilRule') or (_pd.devil_rule_of(d['devilWhy']) if d.get('devilWhy') else 'unrecorded'), []).append(d.get('p5'))
    out = []
    for k, v in g.items():
        ps = [_f(p) for p in v if p is not None]
        out.append({'rule': k, 'hard': _pd.DEVIL_RULES.get(k, (False, ''))[0], 'what': _pd.DEVIL_RULES.get(k, (False, k))[1], 'n': len(v), 'med': round(_med(ps), 1) if ps else None,
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


def scorecards(state, arch, office, real=None, courier_=None, life=None):
    """👨‍⚖️ Every agent on its OWN record — the four desks from their judged calls of this life, Weather / Warden / Reaper from the
    archive, Courier from the ledger, the Archivist from its hash chain, the Judge from whether its rulings held up at 15 minutes."""
    st, of, ar = state or {}, office or {}, arch or {}
    born = st.get('born') or {}
    js = _pd._judged(st, 5)
    life_of = lambda a: [d for d in js if _f(d.get('at')) >= _f(born.get(a))]
    jd = _pd.judge(st)   # 📝 the practice desk's rulings (display)
    lr = _pd.learn(st, 5)
    viol, lats, gen = of.get('viol') or {}, of.get('lat') or {}, of.get('gen') or {}
    out = {}

    def put(a, n, acc, status=None, why=None, **k):
        bad_data = int(k.pop('badData', 0) or 0)   # 🧪 acted as though bad data was trustworthy: each one counts as a rule violation
        v = int(_f((viol.get(a) or {}).get('rule'))) + bad_data
        stale = int(_f((viol.get(a) or {}).get('stale')))
        sc, conf = _score(n, acc, v, stale / 50)
        s_, w_ = (status, why) if status else standing(n, acc, v, k.pop('unsafe', False))
        out[a] = {'n': int(_f(n)), 'accuracy': None if acc is None else round(_f(acc)), 'confidence': conf, 'survival': sc, 'status': s_, 'why': w_, 'violations': v, 'stale': stale,
                  'gen': int((st.get('gen') or {}).get(a) or gen.get(a) or 1), 'latency': lat(lats.get(a)),
                  'fp': k.pop('fp', None), 'fn': k.pop('fn', None), 'missed': k.pop('missed', None), 'badApprovals': k.pop('badApprovals', None), 'usefulVetoes': k.pop('usefulVetoes', None),
                  'profit': k.pop('profit', None), 'loss': k.pop('loss', None), 'drawdown': k.pop('drawdown', None), 'badData': bad_data, **k}

    cb = lambda a, key: round(sum(_f(r['pct']) for r in jd['rulings'] if r.get(key) == a), 1)
    for a in ('tally', 'sherlock', 'trigger', 'devil'):
        d, c = life_of(a), lr['cards'][a]
        s = {'n': int(c['n'] or 0)}
        ent = [x for x in d if x.get('kind') == 'enter']
        k = {'profit': cb(a, 'credit'), 'loss': cb(a, 'blame'), 'unit': '% pts on the rulings shown (5-min calls)'}
        if a == 'tally':
            k.update(fp=sum(1 for x in d if x.get('tallyUp') and _f(x['p5']) <= -3), fn=sum(1 for x in d if not x.get('tallyUp') and _f(x['p5']) >= 3))
        elif a == 'sherlock':
            k.update(fp=sum(1 for x in d if _f(x.get('lean')) > 0 and _f(x['p5']) <= -3), fn=sum(1 for x in d if _f(x.get('lean')) <= 0 and _f(x['p5']) >= 3))
        elif a == 'trigger':
            k.update(fp=sum(1 for x in ent if _f(x['p5']) <= -3), missed=sum(1 for x in d if x.get('kind') == 'wait' and _f(x['p5']) >= _pd.JUDGE_MISS),
                     drawdown=round(min([_f(x['p5']) for x in ent] or [0.0]), 1))
        else:
            k.update(badApprovals=sum(1 for x in ent if x.get('devil') == 'agree' and _f(x['p5']) <= -3), usefulVetoes=sum(1 for x in ent if x.get('devil') == 'object' and _f(x['p5']) <= 0),
                     fp=sum(1 for x in ent if x.get('devil') == 'object' and _f(x['p5']) >= 3))
        dqd = [x for x in d if x.get('dq')]
        if a == 'tally':
            k.update(dataN=len(dqd), dataCaught=sum(1 for x in dqd if x['dq'] not in _md.ENTER_OK))
        elif a == 'sherlock':
            k.update(badData=sum(1 for x in dqd if x['dq'] in _md.READ_FAIL and x.get('cs') not in (None, 'UNKNOWN', _ci.DATA_INVALID)))
        elif a == 'trigger':
            k.update(badData=sum(1 for x in dqd if x.get('kind') == 'enter' and x.get('ce') == 'ENTER NOW' and x['dq'] not in _md.ENTER_OK))
        else:
            k.update(badData=sum(1 for x in dqd if x.get('kind') == 'enter' and x.get('devil') == 'agree' and x['dq'] in _md.READ_FAIL))
        cd = [x for x in d if x.get('cs') and x['cs'] not in ('UNKNOWN', _ci.DATA_INVALID)]   # 📈 chart-reading, judged only on what was known at the call (the structure stored WITH the call) vs what followed
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
        why = f"practice record: {acc if acc is not None else '—'}% right over {s['n']} graded paper calls (evidence only — its generation is judged on real exits)"
        put(a, s['n'], acc, 'alive', why, **k)
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
    held = [d for d in js if d.get('p15') is not None and _pd.ruling(d)['verdict'] in ('win', 'loss')]
    agree = sum(1 for d in held if (_f(d['p15']) > 0) == (_f(d['p5']) > 0))
    put('judge', len(held), round(agree / len(held) * 100) if held else None, unit='rulings that still held at 15 min', fp=len(held) - agree, rulings=jd['n'], trial=jd['trial'])
    for a, g in (life or {}).items():   # 🧬 ONE lifecycle: the generation + status every card shows come from the lifecycle book, for all ten
        if a in out:
            out[a].update(gen=g.get('generation'), record=out[a]['status'], status=str(g.get('status') or 'ACTIVE').lower(), lifeWhy=g.get('why'), net=g.get('net'),
                          winsAttributed=g.get('winsAttributed'), lossesAttributed=g.get('lossesAttributed'), lesson=g.get('lessonVector'))
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


def owner_tune(office, agent, values, why, now):
    """✋ THE OWNER'S CORRECTION of a tunable (bounded like every tunable, recorded in the lineage with its reason). For a value a biased test
    promoted: 2026-10-14 the trail was walked to arm +4% / give back 35% by a replay that ended where the agents SOLD (it could only ever
    favour a tighter trail). The shadow → promote loop keeps running and may move it again on new evidence."""
    o = dict(office or {})
    t = {a: dict(v) for a, v in (o.get('tune') or {}).items()}
    old = dict(t.get(agent) or {})
    for k, v in (values or {}).items():
        _d, lo, hi, _w = TUNABLE[agent][k]
        t.setdefault(agent, {})[k] = _clamp(_f(v), lo, hi)
    o['tune'] = t
    o['lineage'] = (list(o.get('lineage') or []) + [{'agent': agent, 'at': now, 'owner': True, 'old': old, 'new': dict(t[agent]), 'why': str(why)[:300]}])[-60:]
    return o


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


def model_candidate(office, key, direction, n_full, why, now):
    """🧠 The model coach may ASK for ONE Reaper setting to move one notch (`direction` up | down on REAPER_GRID). It becomes a shadow
    candidate like the Judge's own — nothing live changes; only the shadow test on positions closed AFTER it can promote it. Refused
    (→ office unchanged, reason) when the key is not on the grid, a candidate is already in shadow, fewer than PROPOSE_N full paths back
    it, the same value was judged in the last 24h, or there is no notch left. → (office, reason | None)"""
    grid = REAPER_GRID.get(key)
    if not grid or direction not in ('up', 'down'):
        return office, 'not a tunable the model may ask for'
    live = tune(office, 'reaper', key)
    nxt = [v for v in grid if v > live] if direction == 'up' else [v for v in reversed(grid) if v < live]
    if not nxt:
        return office, 'no notch left that way'
    v = nxt[0]
    if any(c['key'] == key and c['value'] == v and now - _f(c.get('doneAt') or c.get('at')) < 86400 for c in ((office or {}).get('candidates') or {}).values()):
        return office, 'that value was judged in the last 24h'
    try:
        return propose(office, 'reaper', key, v, {'n': int(n_full), 'from': 'model coach', 'why': str(why or '')[:120]}, now), None
    except ValueError as e:
        return office, str(e)


def judge_candidates(office, arch, cfg, scalp, now, after=None):
    """👨‍⚖️ Once a pass: (1) every position closed since a shadow candidate was proposed is replayed under the live rule AND the candidate;
    (2) a finished shadow test promotes or rejects; (3) with no candidate open, the archive is searched for ONE Reaper setting that
    would have beaten the live one on ≥ PROPOSE_N real positions → proposed (shadow only). → office"""
    o = dict(office or {})
    pos = [p for p in (arch or {}).get('positions') or [] if p.get('confirmed') and len(p.get('path') or []) >= 3]
    if after is not None:
        # 👁 THE WHOLE MOVE (after_path.py): a path that ends at our own sale can only ever favour a tighter trail. With after-paths on
        # file a position is judged on path + the 30 min after the exit — and only once that is filed (never on the truncated path).
        import after_path as _ap
        pos = [{**p, 'path': f, 'k': _ap.key_of(p)} for p, f in ((p, _ap.full(p, after)) for p in (arch or {}).get('positions') or [] if p.get('confirmed')) if f and len(f) >= 3]
    take = take_line(cfg, scalp)
    live = tunes(o, 'reaper')
    cs = {k: dict(v) for k, v in (o.get('candidates') or {}).items()}
    for cid, c in cs.items():
        if c['status'] != 'shadow' or c['agent'] != 'reaper':
            continue
        seen = int(_f(c.get('seenAt') or c['at']))
        if after is not None:   # an after-path lands 30 min after the close: keyed by position, never by a moving time mark
            sk = list(c.get('seenK') or [])
            new = [p for p in pos if _f(p.get('closedAt')) > _f(c['at']) and p['k'] not in sk]
            c['seenK'] = (sk + [p['k'] for p in new])[-300:]
        else:
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








# ── the live pipeline + the one payload the page reads ─────────────────────────────────────────────────────────────────────────────
# 🎯 ONE mission, ten different jobs: each desk answers ONLY its own question (they may disagree — nobody is folded into one score).
TEAM_GOAL = ('SURVIVE', 'PROTECT REAL CAPITAL', 'GET TO BREAKEVEN', 'BUILD TO 2× PUT-IN', 'THEN UNLOCK THE NEXT STAGE')
JOBS = _frozen({
    'tally': ('MARKET TRUTH', 'Is the data real, fresh and intact — and what does it measure?'),
    'sherlock': ('INVESTIGATION', 'What does the evidence say about this coin (structure, holders, flow), and what contradicts it?'),
    'weather': ('ENVIRONMENT', 'How favourable is the trench right now?'),
    'trigger': ('ENTRY TIMING', 'Is NOW the right entry — ENTER, WAIT or SKIP?'),
    'devil': ('ADVERSARIAL REVIEW', 'What evidence says the proposed entry is wrong?'),
    'warden': ('RISK', 'How much capital may be exposed? (cap or veto only)'),
    'courier': ('EXECUTION TRUTH', 'Can it be sent, and what did the chain confirm?'),
    'reaper': ('POSITION MANAGEMENT', 'Hold, protect, take or exit — and when is the next review?'),
    'archivist': ('MEMORY', 'What was decided, on what data, and what followed?'),
    'judge': ('GOVERNANCE', 'Which agents and rules are actually helping the mission?'),
})


STAGE_STATES = ('WAITING', 'WORKING', 'PASS', 'OBJECT', 'VETO', 'DONE', 'ERROR', 'STALE')








def evidence_refs(packet):
    """🧾 The proof a decision stood on, kept WITH the decision (never only a prose summary): the research packet's time, the mint match with
    the exact launch mint, the address the source showed and its URL, the narrative with the sources that support it, identity confidence,
    the legal level, and every evidence item as [kind, status, url]."""
    p = packet or {}
    if not p:
        return None
    cc, nar, lg = p.get('cross') or {}, p.get('narrative') or {}, p.get('legal') or {}
    return {'at': p.get('at'), 'mintMatch': cc.get('mintMatch'), 'launchMint': cc.get('launchMint') or p.get('mint'), 'sourceMint': cc.get('sourceMint'), 'sourceUrl': cc.get('sourceUrl'),
            'conflict': bool(cc.get('conflict')), 'identity': cc.get('confidence'), 'narrative': nar.get('class'), 'narrativeSources': [s_.get('url') or s_.get('source') for s_ in nar.get('sources') or []][:4],
            'legal': lg.get('level'), 'items': [[e.get('kind'), e.get('status'), e.get('url')] for e in p.get('evidence') or []]}




def contribution(state, arch, office, courier_=None, real=None, money=None):
    """🎯 What each desk measurably added to (or cost) the ONE mission. Only things the records can honestly answer are numbers; the
    rest is listed under `notMeasured` with the reason — no dollar is attributed to an agent that the ledger cannot attribute."""
    st, ar, of = state or {}, arch or {}, office or {}
    js = _pd._judged(st, 5)
    ent = [x for x in js if x.get('kind') == 'enter']
    pos = [p for p in ar.get('positions') or [] if p.get('confirmed') and p.get('realPct') is not None]
    mine = [p for p in pos if p.get('byReaper')]
    wl = of.get('wardenLog') or []
    dq_bad = [x for x in js if x.get('dq') and x['dq'] not in _md.ENTER_OK]
    acted_bad = [x for x in ent if x.get('dq') and x['dq'] not in _md.ENTER_OK and x.get('ce') == 'ENTER NOW']
    r, c_ = real or {}, courier_ or {}
    ph = _uni.real_phase(money)
    surr = [_f(p.get('peak')) - _f(p['realPct']) for p in mine if _f(p.get('peak')) > 1]
    out = {
        'tally': [['data errors caught', len(dq_bad), 'judged calls whose data was not ENTER-grade at the call'], ['integrity failures', sum(1 for x in dq_bad if x['dq'] in _md.READ_FAIL), 'of those: malformed / inconsistent / stale']],
        'sherlock': [['good reads', sum(1 for x in js if _f(x.get('lean')) > 0 and _f(x['p5']) > 0), 'positive reads that were up at 5 min'], ['bad reads', sum(1 for x in js if _f(x.get('lean')) > 0 and _f(x['p5']) <= -3), 'positive reads down 3%+ at 5 min']],
        'weather': [],
        'trigger': [['good entries found', sum(1 for x in ent if _f(x['p5']) > 0), 'ENTER calls up at 5 min'], ['bad entries', sum(1 for x in ent if _f(x['p5']) <= -3), 'ENTER calls down 3%+ at 5 min'],
                    ['entered on bad data', len(acted_bad), 'ENTER calls on data that was not ENTER-grade (the gate makes this 0)']],
        'devil': [['bad entries vetoed', sum(1 for x in ent if x.get('devil') == 'object' and _f(x['p5']) <= 0), 'paper entries it refused that were flat / down at 5 min'],
                  ['winners blocked', sum(1 for x in ent if x.get('devil') == 'object' and _f(x['p5']) >= 3), 'paper entries it refused that were up 3%+ at 5 min']],
        'warden': [['over-sizing prevented', round(sum(max(0.0, _f(w.get('req')) - _f(w.get('allowed'))) for w in wl), 2), f'$ kept out of seats over its last {len(wl)} sizings'],
                   ['losses prevented', round(sum((1 - _f(p['warden'])) * -_f(p['realPct']) for p in pos if p.get('warden') is not None and _f(p['warden']) < 1 and _f(p['realPct']) <= 0), 1), '% points not lost on seats it cut that then lost']],
        'courier': [['typical fill vs mid', None if c_.get('deltaMed') is None else -_f(c_['deltaMed']), '% (the cost of execution, measured on confirmed fills)'], ['sends confirmed', c_.get('fills'), f"of {c_.get('sends') or 0} this hour"]],
        'reaper': [['peak profit retained', round(sum(_f(p['realPct']) / _f(p['peak']) * 100 for p in mine if _f(p.get('peak')) > 1) / len(surr)) if surr else None, '% of the peak gain kept on exits it asked for'],
                   ['peak surrendered', round(sum(surr) / len(surr), 1) if surr else None, '% points given back from the peak, on average'],
                   ['exits won / lost', f"{sum(1 for p in mine if _f(p['realPct']) > 0)} / {sum(1 for p in mine if _f(p['realPct']) <= 0)}", 'confirmed real exits it asked for']],
        'archivist': [['decisions on file', int(_f(ar.get('filed')) or len(ar.get('cases') or [])), 'each with the data-quality state it was made on']],
        'judge': [],
    }
    team = {'realExits': r.get('n'), 'realWon': r.get('won'), 'realTypicalPct': r.get('med'), 'phase': ph['phase'], 'toBreakeven': ph['toBreakeven'], 'toDouble': ph['toDouble'],
            'drawdownPct': round((1 - _f(ph['value']) / _f(ph['putIn'])) * 100, 1) if ph['known'] and _f(ph['putIn']) > 0 and _f(ph['value']) < _f(ph['putIn']) else 0.0 if ph['known'] else None}
    return {'agents': out, 'team': team,
            'notMeasured': [['slippage saved', 'no counterfactual fill exists to compare with'], ['false data warnings', 'the true state of a feed we rejected is not known afterwards'],
                            ['unnecessary / late exits', 'prices after an exit are not followed yet'], ['$ per agent', 'the ledger records a fill per coin, not per desk — only the team\'s real result is in $']]}


def mission(money, stage, now, last=None, underwater=None):
    """🎯 THE ONE REAL-MONEY MISSION, from the SAME fields the real Fuse card shows (`money` = its server value and everything put in —
    never paper, never gross proceeds, never paid-out totals). Phase 1 RECOVERY: back to breakeven. Phase 2 GROWTH: breakeven → 2× the
    put-in. Breakeven is a milestone; the 5-minute stage stays LOCKED until real equity ≥ 2× put-in (`agents.real_phase`), and only then
    is the next stage ELIGIBLE under the existing progression rules. `underwater` (agents.underwater) is passed in, never recomputed."""
    v, p = (money or {}).get('value'), (money or {}).get('putIn')
    ph = _uni.real_phase(money)
    known = ph['known']
    return {'putIn': p, 'value': v, 'toBreakeven': round(_f(v) - _f(p), 2) if known else None, 'needX': round(_f(p) / _f(v), 1) if known and _f(v) > 0 else None,
            'phase': ph['phase'], 'breakevenTarget': ph['breakeven'], 'doubleTarget': ph['double'], 'toDouble': round(_f(v) - _f(ph['double']), 2) if known else None,
            'needX2': round(_f(ph['double']) / _f(v), 1) if known and _f(v) > 0 else None, 'underwater': bool(underwater),
            'stage': (stage or {}).get('h') or 5, 'locked': not ph['eligible'], 'lock': 'UNKNOWN' if not known else 'ELIGIBLE' if ph['eligible'] else 'LOCKED',
            'nextStage': 'ELIGIBLE' if ph['eligible'] else 'LOCKED', 'unlock': f"real equity ≥ ${_f(ph['double']):,.2f}" if known else 'real equity ≥ 2× put-in (the card\'s money is not read yet)',
            'lockRule': 'real card value < 2× real put-in → stage stays 5 min (agents.real_phase); breakeven is milestone 1, not graduation',
            'goal': ['SURVIVE', 'PROTECT REAL CAPITAL', 'GET TO BREAKEVEN', 'BUILD TO 2× PUT-IN', 'THEN UNLOCK THE NEXT STAGE'], 'source': 'the real card\'s server value and put-in (the numbers My cards shows)',
            'lastAction': last, 'priority': list(PRIORITY)}


def agent_cards(cards, ctx):
    """The ten live cards: constitution (immutable) + tunables (live value, default, bounds) + this pass's task / decision / inputs /
    output + the Judge's scorecard. Everything shown is state, a coded rule or a measurement."""
    out = []
    for a in CHAIN:
        c, k = CONSTITUTION[a], cards.get(a) or {}
        live = (ctx.get('live') or {}).get(a) or {}
        out.append({'key': a, 'job': JOBS[a][0], 'question': JOBS[a][1], 'icon': c['icon'], 'name': c['name'], 'role': c['role'], 'ideology': c['ideology'], 'ethics': list(c['ethics']), 'forbidden': list(c['forbidden']),
                    'hard': list(c['hard']), 'code': [{'file': c['code']['file'], 'fn': list(c['code']['fn'])}] + ([{'file': 'backend/trench_kernel/brain.py', 'fn': list(c['brain'])}] if c.get('brain') else [])
                    + ([{'file': 'backend/trench_kernel/senses.py', 'fn': list(c['senses'])}] if c.get('senses') else []) + ([{'file': 'backend/trench_kernel/lifecycle.py', 'fn': list(c['life'])}] if c.get('life') else []) + ([{'file': 'backend/office.py', 'fn': list(c['office'])}] if c.get('office') else [])
                    + ([{'file': 'backend/chart_intel.py', 'fn': list(c['chart'])}] if c.get('chart') else []) + ([{'file': 'backend/market_data.py', 'fn': list(c['data'])}] if c.get('data') else []),
                    'tunable': [{'key': t, 'value': tune(ctx.get('office'), a, t), 'default': d[0], 'lo': d[1], 'hi': d[2], 'what': d[3]} for t, d in (TUNABLE.get(a) or {}).items()],
                    'task': live.get('task'), 'decision': live.get('decision'), 'decisionAt': live.get('at'), 'rule': live.get('rule'), 'inputs': live.get('inputs'), 'output': live.get('output'),
                    'recent': live.get('recent') or [], 'card': k})
    return out


# ── ⚡ FAST REAP: the 6-second guard applies Reaper's own stop to the agents' seats between ticks ───────────────────────────────────
FAST_GAP_PCT, FAST_GAP_SEC = 50.0, 90.0   # a > 50% "loss" in a coin's first 90s is a feed gap, never sold (same rule as arena_prime.fast_stop)


SPIKE_PCT = 20.0      # a stop read that fell this far in ONE step from the previous read (≤ SPIKE_SEC old) waits one read to confirm
SPIKE_SEC = 15.0


def spike_held(mint, px, line_px, prev, now):
    """🕯 One bad print never sells a seat (owner, 2026-10-14: "don't SL someone due to a glitchy chart"): the previous read was above the
    stop line and ≤ 15s old, and this one is ≥ 20% under it → hold this read; the NEXT read (3s later) confirms a real dump."""
    at, p0 = (prev or {}).get(mint) or (0.0, 0.0)
    return bool(p0 > 0 and now - _f(at) <= SPIKE_SEC and px < p0 * (1 - SPIKE_PCT / 100) and p0 > line_px)


def fast_reap(legs, px_by_mint, pos, now, office=None, prev=None, ai_words=None):
    """→ [(pairAddress, why)] for agent coins the wallet holds that are AT Reaper's stop for them (`stopNow`, set on the position each
    tick) or the catastrophic −45%. Why (2026-10-11, 173 exits): agent seats carry no card stop and the card is held by the agents
    (`holdAll`), so `arena_prime.fast_stop` never ran for them — R5 stops set at −12…−25% filled at −18…−52% (sum −485% of −370%)."""
    out = []
    for l in legs or []:
        # ✋ YOUR stop line on YOUR pick is guarded every few seconds too (2026-10-15: it only ran on the engine tick — TOAST's −12% line
        # filled at −20%, PDOOM's −19% at −24%). Only a line YOU set (`ownerLvAt` + `sl`); a pick with no line of yours has no stop here.
        mine_ = (not _uni.is_agent(l)) and yours(l) and l.get('ownerLvAt') and 0 < _f(l.get('sl')) < 100
        if not (_uni.is_agent(l) or mine_) or l.get('placeholder') or l.get('buying') or l.get('frozen') or not l.get('real') or _f(l.get('units')) <= 0:
            continue
        px, entry = _f((px_by_mint or {}).get(l.get('mint'))), _f(l.get('entry'))
        p = (pos or {}).get(l.get('mint')) or {}
        stop = _f(l.get('sl')) if mine_ else _f(p.get('stopNow'))
        if px <= 0 or entry <= 0 or stop <= 0:
            continue
        dd = (px / entry - 1) * 100
        if dd <= -FAST_GAP_PCT and now - _f(l.get('at')) < FAST_GAP_SEC:
            continue
        line = min(stop, _ci.CATASTROPHIC_STOP)
        if dd <= -line and spike_held(l.get('mint'), px, entry * (1 - line / 100), prev, now):
            continue   # 🕯 a one-read cliff: confirmed (or not) by the next live read
        if dd <= -line:
            out.append((l.get('pairAddress'), f"☠ Reaper R5 stop (⚡ 6-second guard): {dd:+.1f}% ≤ −{line:g}%"))
            continue
        # 👁 REAPER READS THE LIVE CHART (owner, 2026-10-12: "reaper reviews live chart, not every 5 mins"): the same exits the tick makes
        # from the chart — a thesis invalidated (live price under the invalidation line, losing) and the trailing protection (a peak that
        # armed it given back) — are applied on every 6-second live read, not only when the tick comes round.
        if yours(l):   # ✋ your coin: only your own stop (stopNow is your line) and −45% act here — no thesis / trail bank by the agents
            continue
        inv = _f((p.get('thesis') or {}).get('invalidation'))
        if inv > 0 and px < inv and dd < 0:
            out.append((l.get('pairAddress'), f"☠ Reaper R5t thesis invalidated (👁 live chart): {dd:+.1f}% — price under its invalidation line"))
            continue
        peak = max(_f(p.get('peak')), dd)
        give = RIDE_GIVE if p.get('rideAt') and now - _f(p['rideAt']) <= RIDE_HOLD_SEC else tune(office, 'reaper', 'giveBackPct')   # 🏄 riding the volume: the wide trail
        if peak >= tune(office, 'reaper', 'protectAt') and dd <= peak * (1 - give / 100) and dd >= MIN_KEEP:
            if dd >= RUNWAY_KEEP and now - _f(l.get('at')) < RUNWAY_SEC:   # 🛫 green and still on its runway: not banked yet
                continue
            ok_, seen_, need_ = soft_confirm(p, 'R7', now, (ai_words or {}).get(l.get('mint')))   # 📸 the trail banks on its 2nd (RIDE: 3rd) read, not the first dip
            if ok_:
                out.append((l.get('pairAddress'), f"☠ Reaper R7 trailing protection (👁 live chart, 📸 {seen_}/{need_} reads): peaked {peak:+.1f}%, now {dd:+.1f}% — banked"))
        elif (p.get('snap') or {}).get('rule') == 'R7':
            p.pop('snap', None)
    return out


def owner_hand(positions):
    """✋ DID YOUR HAND HELP? Closed real positions where the owner dragged the coin's TP / SL vs the ones left to the agents —
    each side's count, typical and average real result. Shown, never acted on."""
    import statistics
    side = {'yours': [], 'agents': []}
    for p in positions or []:
        r = (p.get('exit') or {}).get('realPct') if isinstance(p.get('exit'), dict) else None
        r = p.get('realPct') if r is None else r
        if r is None:
            continue
        side['yours' if p.get('owner') else 'agents'].append(_f(r))
    return {k: {'n': len(v), 'med': round(statistics.median(v), 1) if v else None, 'avg': round(sum(v) / len(v), 1) if v else None} for k, v in side.items()}
