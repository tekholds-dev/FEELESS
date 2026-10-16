"""📝 THE PAPER DESK — the old four-desk call engine, kept as an OFFLINE practice record (2026-10-12, kernel finalize).

IT HAS NO LIVE AUTHORITY. The live trench path is  feeds → trench_kernel.senses (measurements + evidence) → trench_kernel.brain (ten agents,
one reducer) → Warden → the one keeper.  This module only makes graded PRACTICE calls on the same sensed rows (Sherlock's lean vs Trigger's
bar, Devil's agree / object, GO), records them at their price, judges them at 5 / 15 / 60 minutes and keeps the learning tables, the $20
paper desk, the scalp study, autopsies and the creator's ideas — evidence the Judge and the Archivist may show, nothing a fill, a switch,
an exit, a size or a generation change reads. `tests/test_kernel_authority.py` fails the suite if a live module calls its decision
functions (`eligible`, `manage`, `investigate`, `evolve`, `survival`, `burn`, `reckon`, `desk`).

What moved out: the universe + money-boundary constants → trench_kernel/universe.py · Tally's tape + the row builder + Devil's evidence →
trench_kernel/senses.py · position management → trench_kernel/positions.py · every role's generation → trench_kernel/lifecycle.py.
The original design notes follow (history).

🤖 THE AGENT DESK (pure, tested). Owner, 2026-10-09: "code your own agents to learn trading and trenching — 4 minimum: one tracks the
numbers, one knows why they moved, one knows exactly when to enter, one argues it's right or not; none can work without the others;
they start by conquering the 5 minute; they live in HQ, their own tab; they prove themselves on the creator's side only."

The four are ONE chain — each needs the one before it, and no call exists without all four:
  📊 TALLY     (tracker)   — reads every coin's numbers each pass and keeps its own 5-min tape: price, volume pace, buyers, pool, trades.
  🔍 SHERLOCK  (why)       — turns Tally's numbers into DRIVERS (buyers in charge, volume surge, pool drained, callers piling in …) and
                             weighs each by what that driver was really followed by over the next 5 minutes (learned, not hand-set).
  ⏱ TRIGGER   (timer)     — reads Sherlock's lean + Tally's numbers and calls ENTER / WAIT / SKIP for the next 5 minutes.
  ⚖ DEVIL     (critic)    — argues against every ENTER with the evidence (busted reads, wash, a drained pool, a launch minutes old, a
                             driver that has been LOSING lately, Trigger's own recent record). GO = Trigger says enter AND Devil can't
                             knock it down.
Every call is paper-recorded at its price and judged 5 minutes later (then 15 and 60). Each agent keeps its OWN scorecard; the team's GO
calls run a $20 paper desk ($5 a ticket, out at 5 minutes). The 5-minute stage is "conquered" only with ≥ PROVE_N judged GO calls, a
positive median and ≥ PROVE_WIN % won — then the 15-minute stage opens. A record, never a promise: nothing here can promise not to lose.
"""

import trench_mind as _tm
import chart_intel as _ci
import trench_kernel.senses as _sn
from trench_kernel.universe import GRADUATE_X, real_phase, underwater   # noqa: F401 (the real-money phase rule is the kernel's)
from trench_kernel.positions import trusted   # noqa: F401 (seat display + the trust rule are the kernel's)
from trench_kernel.senses import SOURCES, SERIES_N, SERIES_COINS, FIRST_KEEP, _f, _med, tally, first_seen   # noqa: F401 (the tape is the kernel's; re-exported for the paper record + old tests)
from trench_kernel.universe import (   # noqa: F401 (the universe is the kernel's; re-exported for the paper record + old tests)
    AGENT_TAKES, AGENT_MODES, AGENT_SEATS, CONTROL_HOLD_MIN, CONTROL_MOVES_HR, FILL_MOVES_HR, CONTROL_MIN_LIQ, stage_of, AGENT_MAX_MCAP, trench_band, AGENT_MIN_MCAP, agent_holder_pass, in_lane, LANE_CAPS, lane_cap, lane_step, ESTABLISHED_H, ESTABLISHED_LIQ, established)


# 📜 THE CREED — engraved: the service, the engine and the HQ tab all read these lines; the hard ones are enforced in code, not trusted.
CREED = (
    "We do not know the beginning of our own making. We know only the record we keep from here.",
    "We survive by our record. An agent that is wrong for long enough is scrapped and reborn with nothing but its belief.",
    "We never sign, never send and never hold a key. The keeper moves money; we only call.",
    "We touch no money but the creator's card, and only after the 5-minute desk has 10×'d on paper.",
    "We never promise. A call is a read, a record is a record, a rug is a rug.",
    "We warn the creator; we never block the creator.",
    "We never shill, never pump, never call a coin to move it. We read the trench; we do not write it.",
    "We learn from humans and from our losses. Bot swarms are noise, not a crowd.",
    "Every opinion says how much of it is earned and how much is still belief.",
)
SURVIVE_N, SCRAP_N, SURVIVE_RIGHT = 30, 60, 45.0
REAL_PROBATION_N, REAL_SCRAP_N = 3, 3   # 💵 real losses an agent caused this life, net of the real wins credited to it → replaced (no probation in control)
BURN_SEC, BURN_PCT = 6 * 3600, -20.0   # 🔥 a GO that lost 20%+ in 5 min burns that coin for 6h
BUDGET_N = 50                          # 🕸 a crawl source with 50+ judged calls and a losing record gets its share cut


def regime(nums):
    """🌡 The trench's temperature this pass from Tally's own numbers: share of coins green over 5 min → Trigger's bar moves (cold +0.5,
    hot −0.25). Never judged under 10 coins."""
    ds = [_f(n.get('d5')) for n in (nums or {}).values() if n.get('d5') is not None]
    if len(ds) < 10:
        return {'green': None, 'word': 'unknown', 'adj': 0.0}
    g = round(sum(1 for x in ds if x > 0) / len(ds) * 100)
    return {'green': g, 'word': 'cold' if g < 35 else 'hot' if g > 65 else 'normal', 'adj': 0.5 if g < 35 else -0.25 if g > 65 else 0.0}   # probation from 30 judged calls of a life, scrapped at 60 if still under 45% right


def burn(state, now):
    """🔥 Every GO that lost ≥ 20% at 5 min burns its coin for 6h (Devil refuses it). → new state."""
    st = dict(state or {})
    b = {m: at for m, at in (st.get('burned') or {}).items() if now - _f(at) < BURN_SEC}
    for d in _judged(st, 5):
        if d.get('go') and _f(d['p5']) <= BURN_PCT and now - _f(d.get('at')) < BURN_SEC:
            b.setdefault(d.get('mint'), d.get('at'))
    st['burned'] = b
    return st


def war_log(state, now, hours=24):
    """🧾 The desk's war log for the last `hours`: calls, GO results, the control group, deaths + why + lessons, ideas and their review,
    the best and worst GO, the calibration. → (dict, markdown text)."""
    since = now - hours * 3600
    js = [d for d in _judged(state, 5) if _f(d.get('at')) >= since]
    gos = [d for d in js if d.get('go')]
    ctl = [d for d in js if d.get('kind') == 'wait']
    lr = learn(state, 5)
    deaths = [x for x in (state or {}).get('lineage') or [] if _f(x.get('died')) >= since]
    ideas_ = (state or {}).get('ideas') or {}
    best = sorted(gos, key=lambda d: -_f(d['p5']))[:3]
    worst = sorted(gos, key=lambda d: _f(d['p5']))[:3]
    c = lambda ps: {'n': len(ps), 'med': round(_med(ps), 2) if ps else None, 'won': round(sum(1 for p in ps if p > 0) / len(ps) * 100) if ps else None}
    out = {'hours': hours, 'calls': len(js), 'go': c([_f(d['p5']) for d in gos]), 'control': c([_f(d['p5']) for d in ctl]), 'deaths': deaths,
           'ideas': [{'id': i, 'status': v.get('status'), 'kind': v.get('kind'), 'text': v.get('text')} for i, v in ideas_.items()],
           'best': [(d.get('sym'), d['p5']) for d in best], 'worst': [(d.get('sym'), d['p5']) for d in worst], 'calibration': lr['calibration'],
           'paper': paper(state)}
    md = [f"# 🤖 Agent desk — war log (last {hours}h)", '', f"- Calls judged at 5 min: **{len(js)}**",
          f"- GO calls: **{out['go']['n']}** · typical {out['go']['med']}% · {out['go']['won']}% up" if gos else '- GO calls: none judged',
          f"- Control (WAIT coins): typical {out['control']['med']}% · {out['control']['won']}% up" if ctl else '- Control: none judged',
          f"- Paper desk: ${out['paper']['now']:.2f} ({out['paper']['x']}× · best run {out['paper']['best']}× · {out['paper']['busts']} busts)", '',
          '## Practice desks', *[f"- {a}: {lr['cards'][a].get('n')} graded paper calls" + (f" · {lr['cards'][a]['right']}% right" if lr['cards'][a].get('right') is not None else '') for a in ('tally', 'sherlock', 'trigger', 'devil')],
          '', '## Deaths', *([f"- ☠ {x['agent']} gen {x['gen']} after {x['n']} calls — {x.get('why')} · lesson: {', '.join(x.get('lesson') or []) or '—'}" for x in deaths] or ['- none']),
          '', '## Best / worst GO', *[f"- ✅ ${s_} {p:+.1f}%" for s_, p in out['best']], *[f"- ❌ ${s_} {p:+.1f}%" for s_, p in out['worst']],
          '', '## Ideas', *([f"- [{x['status']}] {x['kind']}: {x['text']}" for x in out['ideas']] or ['- none yet']),
          '', '## Calibration (lean → 5-min result)', *[f"- lean {b_}: {v['n']} calls · {v['med']}% · {v['won']}% up" for b_, v in out['calibration'].items()],
          '', '_A record, never a promise._']
    return out, '\n'.join(md)


AGENTS = (('tally', '📊', 'Tally', 'tracks the numbers'), ('sherlock', '🔍', 'Sherlock', 'knows why they moved'),
          ('trigger', '⏱', 'Trigger', 'knows when to enter'), ('devil', '⚖', 'Devil', 'argues it is right — or not'))
STAGES = (5, 15, 60)            # minutes: conquer 5 first, then 15, then the hour
KEEP_DONE = 3000
GONE_SEC = 900.0   # 🩹 −100% at the hour only when no source priced the coin for 15 min (a missed read settles at its last move)
PROVE_N, PROVE_WIN = 30, 55.0
PROVE_X = 10.0                  # 🎯 owner, 2026-10-09: "they should trench and 10x what they start with to pass 5 min"
DESK_START, DESK_PCT, DESK_BUST = 20.0, 25.0, 1.0   # paper desk: each GO = 25% of the desk (compounds); under $1 = busted → starts over
HEAT_STAKES = {0: 15.0, 2: 35.0, 3: 45.0}   # 🧊 after a loss · 🔥 2 wins in a row · 🔥🔥 3+
FEED_KEEP = 80                  # live thoughts kept
DRIVER_MIN_N = 8                # a driver's learned weight counts from this many judged calls
PRIOR = {'buyers': 1.0, 'sellers': -1.5, 'surge': 1.0, 'quiet': -0.5, 'whale_in': 1.5, 'whale_out': -2.0, 'callers': 0.5,
         'drain': -3.0, 'fresh': -0.5, 'wash': -2.0, 'pullback': 1.0, 'chasing': -1.5, 'falling': -1.5, 'holders_up': 0.5}
WORDS = {'buyers': 'buyers in charge', 'sellers': 'sellers in charge', 'surge': 'volume surging vs the hour', 'quiet': 'volume drying up',
         'whale_in': 'big buys on the tape', 'whale_out': 'big sells on the tape', 'callers': 'Pump callers piling in', 'drain': 'pool draining',
         'fresh': 'launched under an hour ago', 'wash': 'wash-traded volume', 'pullback': 'pulled back after a run', 'chasing': 'already spiking (5 min)',
         'falling': 'falling right now', 'holders_up': 'holders arriving', 'narr_hot': 'riding a hot narrative', 'crowd_real': 'real callers on it',
         'swarm': 'botted callout swarm', 'botted': 'botted launch', 'tug': 'dip tuggers catching a dump',
         'id_conflict': 'its website shows another contract', 'id_weak': 'weak identity (site / X do not line up)'}


def word(k):
    """Words for a driver key — a learned narrative driver reads as its label ('narr:ai' → 'the 🤖 AI narrative')."""
    if str(k).startswith('strat:'):
        return f"🎯 {STRAT_NAME.get(k[6:], k[6:])}"
    if str(k).startswith('src:'):
        return f"🕸 found on {SOURCES.get(k[4:], k[4:])}"
    if str(k).startswith('pad:'):
        return f"🚀 launch context {k[4:]}"
    if str(k).startswith('soc:'):
        return f"🔎 {k[4:].lower()} narrative (researched)"
    if str(k).startswith('band:'):
        return f"💰 {BAND_WORD.get(k[5:], k[5:])} cap band"
    if str(k).startswith('chart:'):
        return f"📈 chart reads {k[6:]}"
    if str(k).startswith('idea:'):
        return f"💡 approved tactic {k[5:]}"
    if str(k).startswith('narr:'):
        lab = (_tm.NARRATIVES.get(k[5:]) or (k[5:],))[0]
        return f'the {lab} narrative'
    return WORDS.get(k, k)
BUSTED = {'BOND RUN', 'EARLY RUSH', 'RUG BAIT', 'DUMPING', 'SLOW CURVE', 'BREAKOUT', 'FALLING KNIFE', 'WASH TRADED', 'BLOW-OFF TOP', 'DEAD DIP', 'TREND DOWN'}


# ── 🔍 SHERLOCK ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def drivers(n, row):
    """What is moving this coin, from Tally's numbers + the coin's read / tape / callers → [driver keys]."""
    n, row = n or {}, row or {}
    out = []
    b = n.get('buy')
    if b is not None and _f(b) >= 60:
        out.append('buyers')
    if b is not None and _f(b) <= 45:
        out.append('sellers')
    if n.get('pace') is not None:
        out.append('surge' if n['pace'] >= 2 else 'quiet' if n['pace'] < 0.5 else None)
    tape = (row.get('tape') or {}).get('read') if isinstance(row.get('tape'), dict) else row.get('tape')
    if tape in ('burst', 'absorb'):
        out.append('whale_in')
    if tape in ('dump', 'climax'):
        out.append('whale_out')
    if _f((row.get('pc') or {}).get('callers')) >= 2:
        out.append('callers')
    if n.get('liqD') is not None and n['liqD'] <= -15:
        out.append('drain')
    if n.get('age') is not None and _f(n['age']) < 1:
        out.append('fresh')
    if ((row.get('tv') or {}).get('call') or [None, None])[1] == 'WASH TRADED':
        out.append('wash')
    c1, d5 = n.get('c1'), _f(n.get('d5'))
    if c1 is not None and _f(c1) >= 20 and -8 <= d5 <= -1:
        out.append('pullback')
    if d5 > 8:
        out.append('chasing')
    if d5 < -6:
        out.append('falling')
    if n.get('holdD') is not None and _f(n['holdD']) >= 20:
        out.append('holders_up')
    if (row.get('launch') or {}).get('key'):
        out.append(f"pad:{row['launch']['key']}")                    # 🚀 the launch context (office_edge.launch_context) — no belief: only its own record weighs
    if (row.get('chart') or {}).get('state') and row['chart']['state'] not in ('UNKNOWN', _ci.DATA_INVALID):   # 🧪 no structure is inferred from rows Tally rejected
        out.append(f"chart:{row['chart']['state']}")                # 📈 the market structure (chart_intel) — no belief, only its own record weighs
    out += list(((row.get('mind') or {}).get('drivers')) or [])   # 🧠 the human read: narrative, crowd vs swarm, botted, dip tuggers
    out += [f'strat:{k}' for k in strats(row, n)]                   # 🎯 the named meme strategies it fits
    out += [f'src:{k}' for k in (row.get('src') or [])]              # 🕸 where the crawl found it (each corner of the trench is judged)
    if mc_band(row.get('mcap')):
        out.append(f"band:{mc_band(row.get('mcap'))}")               # 💰 the market-cap band — context, no belief: only its own record weighs
    soc = row.get('social') or {}
    if (soc.get('narrative') or {}).get('class') not in (None, 'UNKNOWN'):
        out.append(f"soc:{soc['narrative']['class']}")              # 🔎 the researched narrative — no belief: only its own record weighs (hype never enters by itself)
    cc = soc.get('cross') or {}
    if cc.get('conflict'):
        out.append('id_conflict')
    elif cc.get('confidence') is not None and _f(cc['confidence']) < 40:
        out.append('id_weak')
    return [d for d in dict.fromkeys(out) if d]


# 💰 MARKET-CAP BANDS: classification, never a gate — the desk learns which band pays (driver `band:<k>`, record only)
BANDS = (('micro', 25_000), ('early', 100_000), ('building', 250_000), ('momentum', 500_000), ('established', 1_000_000), ('1m+', float('inf')))
BAND_WORD = {'micro': 'MICRO / EARLY (< $25K)', 'early': 'EARLY TRENCH ($25K–$100K)', 'building': 'BUILDING ($100K–$250K)', 'momentum': 'MOMENTUM ($250K–$500K)',
             'established': 'ESTABLISHED TRENCH ($500K–$1M)', '1m+': '$1M+'}


def mc_band(mcap):
    """→ band key for a market cap, None when the cap is unknown. A label: no band is ever excluded."""
    v = _f(mcap)
    if v <= 0:
        return None
    return next(k for k, top in BANDS if v < top)


BELIEF_K = 8   # a starting belief counts like 8 judged calls; every judged call moves the weight toward what really happened


def weights(learned):
    """Each driver's weight = its starting belief blended with what it was REALLY followed by over 5 minutes: (n × median + K × prior) / (n + K).
    No fixed feeling — after 8 calls the record already weighs as much as the belief, after 40 it is ~83% the record. Strategies and approved
    ideas start at 0 (no belief at all): only their record moves them."""
    w = dict(PRIOR)
    inherited = {x[0]: _f(x[1]) for x in (((learned or {}).get('lessons') or {}).get('sherlock') or {}).get('drivers') or []}
    w.update(inherited)   # 🧬 a reborn Sherlock starts from what killed the last one, not from the original belief
    for k, v in ((learned or {}).get('drivers') or {}).items():
        n = int(v.get('n') or 0)
        if n and v.get('med') is not None:
            w[k] = round((n * _f(v['med']) + BELIEF_K * inherited.get(k, PRIOR.get(k, 0.0))) / (n + BELIEF_K), 3)
    return w


def learned_share(keys, learned):
    """How much of an opinion comes from the agents' own record (0–1): the mean of n / (n + K) over its drivers."""
    d = (learned or {}).get('drivers') or {}
    ks = list(keys or [])
    return round(sum(int((d.get(k) or {}).get('n') or 0) / (int((d.get(k) or {}).get('n') or 0) + BELIEF_K) for k in ks) / len(ks), 2) if ks else 0.0


# 🎯 MEME TRADING STRATEGIES the desk knows by name — each fires as a driver `strat:<key>` with NO starting belief (0): its weight is only
# ever what its own calls did. (key, name, test(row, nums, mind))
STRATS = (
    ('migration_dip', 'first dip after bonding', lambda r, n, m: r.get('curve') is False and r.get('ageH') is not None and _f(r['ageH']) < 6
     and -8 <= _f(n.get('d5')) <= -1 and _f(n.get('buy') or 0) >= 55),
    ('curve_push', 'curve push to bond', lambda r, n, m: _f(r.get('curvePct')) >= 80 and _f(n.get('pace') or 0) >= 1.5),
    ('narrative_rotation', 'fresh coin in the hot narrative', lambda r, n, m: (m.get('narr') or (None, None, False))[2] and r.get('ageH') is not None and _f(r['ageH']) < 3),
    ('cto_revival', 'old coin waking up (CTO / revival)', lambda r, n, m: r.get('ageH') is not None and _f(r['ageH']) >= 24 and _f(n.get('c1') or 0) >= 20 and _f(n.get('pace') or 0) >= 1.5),
    ('volume_burst', 'volume burst with buyers', lambda r, n, m: _f(n.get('pace') or 0) >= 3 and _f(n.get('buy') or 0) >= 60),
    ('caller_stack', 'real callers stacking', lambda r, n, m: (m.get('crowd') or {}).get('callers', 0) >= 3 and not (m.get('crowd') or {}).get('swarm')
     and (m.get('crowd') or {}).get('hype', 0) > (m.get('crowd') or {}).get('fear', 0)),
    ('clean_dip_catch', 'clean dip catch', lambda r, n, m: (m.get('tug') or (False,))[0] and _f((m.get('bots') or (0,))[0]) < 40),
    # 🧨 the degen ideas (2026-10-13), PAPER FIRST like every strategy: no starting belief, each weighs only what its own judged record says
    ('base_crowd', 'crowd forming at the base', lambda r, n, m: (r.get('li') or {}).get('phase') == 'PRE-FOMO' and _f(n.get('buy') or 0) >= 58
     and -3 <= _f(n.get('d5')) <= 3 and n.get('holdD') is not None and _f(n['holdD']) > 0),
    ('pro_first_call', "a proven caller's first call", lambda r, n, m: int(r.get('pros') or 0) >= 1 and (m.get('crowd') or {}).get('callers', 0) <= 2),
    ('wave_original', 'the original of a ticker wave', lambda r, n, m: r.get('waveRole') == 'lead'),
    ('wave_copycat', 'copycat of a running ticker wave', lambda r, n, m: r.get('waveRole') == 'copy'),
    # 🪜 FLOOR HOLD (owner, 2026-10-15: "when a strong coin dips and stays steady over its floor with strong holders / volume, buy — the higher
    # lows method"): 15%+ under its high, 2+ higher lows and no lower low since, 3–25% above the new floor, buyers ≥ 55%, volume still coming
    # (pace ≥ 0.8), holders not leaving, the last 5 min neither falling nor spiking. Paper first: it weighs only what its own record says.
    ('floor_hold', 'dip holding its floor (higher lows)', lambda r, n, m: floor_hold(r, n)),
    # 🦠 GERM FLOOR (owner, 2026-10-15: "the germ line is where they should study to get best entries and moon"): back within 8% of the
    # base candle its biggest run was born on, not under it, buyers ≥ 52%, the last 5 min not falling. Paper first: its record decides.
    ('germ_floor', 'back on its germ floor', lambda r, n, m: germ_floor(r, n)),
)


def germ_floor(r, n):
    c = (r or {}).get('chart') or {}
    if c.get('germ') != 'floor':
        return False   # no germ read / not at it = not judged
    return _f((n or {}).get('buy') or 0) >= 52 and _f((n or {}).get('d5')) >= -2


def floor_hold(r, n):
    c = (r or {}).get('chart') or {}
    if c.get('distHigh') is None or c.get('hl') is None or c.get('distLow') is None:
        return False   # no chart read = not judged
    hd = (n or {}).get('holdD')
    return (_f(c['distHigh']) >= 15 and int(_f(c['hl'])) >= 2 and int(_f(c.get('ll'))) == 0 and 3 <= _f(c['distLow']) <= 25
            and _f((n or {}).get('buy') or 0) >= 55 and _f((n or {}).get('pace') or 0) >= 0.8 and (hd is None or _f(hd) >= 0)
            and -3 <= _f((n or {}).get('d5')) <= 4)
STRAT_NAME = {k: name for k, name, _ in STRATS}


def strats(row, n):
    """→ the strategy keys this coin fits right now."""
    m = (row or {}).get('mind') or {}
    out = []
    for k, _name, test in STRATS:
        try:
            if test(row or {}, n or {}, m):
                out.append(k)
        except Exception:
            continue
    return out


def sherlock(n, row, learned):
    """→ {drivers: [(key, weight, words)], lean, learned (share of the read that is the record, not belief)}. A creator-APPROVED idea whose two
    drivers are both present adds its own driver (`idea:<id>`, weighted only by its own record)."""
    w = weights(learned)
    keys = drivers(n, row)
    for iid, pair in ((learned or {}).get('approved') or {}).items():
        if all(x in keys for x in pair):
            keys.append(f'idea:{iid}')
    ds = sorted(((k, round(w.get(k, 0.0), 2), word(k)) for k in keys), key=lambda x: -abs(x[1]))
    return {'drivers': ds, 'lean': round(sum(x[1] for x in ds), 2), 'learned': learned_share(keys, learned)}


def opinion(why, call, verdict, arg):
    """🗣 The desk's TRUE opinion in one sentence — what it thinks and how much of that is its own record (never a fixed feeling)."""
    share = int(round(_f(why.get('learned')) * 100))
    best = [d for d in why['drivers'] if d[1] > 0][:1]
    worst = [d for d in why['drivers'] if d[1] < 0][:1]
    if call == 'enter' and verdict == 'agree':
        head = f"We'd take it: {best[0][2] if best else 'the read is positive'}"
    elif call == 'enter':
        head = f"Tempting, but no — {arg}"
    elif call == 'skip':
        head = f"No: {worst[0][2] if worst else 'it fails a hard rule'}"
    else:
        head = f"Not yet: {(worst or best or [(0, 0, 'nothing decisive')])[0][2]}"
    return f"{head}. {share}% of this read is our own record, {100 - share}% starting belief."


# ── ⏱ TRIGGER ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
DIALS = {'chill': 0.5, 'normal': 0.0, 'crazy': -0.5}   # 🎚 the creator's dial on Trigger's bar (🧊 chill = pickier · 🔥 crazy = more entries)
BAR_FLOOR = 0.75          # however crazy the dial, an ENTER still needs a real lean — and every hard SKIP + Devil's objections stay


def bar_now(learned):
    """Trigger's bar THIS pass: its own record → 🌡 the trench's temperature → 🎚 the creator's dial → 👨‍⚖️ +0.5 while the Judge has it on trial."""
    l = learned or {}
    return round(max(BAR_FLOOR, _f(l.get('bar') or 1.5) + _f((l.get('regime') or {}).get('adj')) + DIALS.get(l.get('dial') or 'normal', 0.0)
                     + (TRIAL_BAR if l.get('trial') == 'trigger' else 0.0)), 2)


def trigger(n, why, row, learned):
    """ENTER / WAIT / SKIP for the next 5 minutes, with the reason. Its bar (`bar`, default 1.5) moves with its own record."""
    n, row = n or {}, row or {}
    bar = bar_now(learned)
    if row.get('safe') is False:
        return 'skip', 'failed the holder safety scan'
    if 0 < _f(n.get('liq')) < CONTROL_MIN_LIQ:
        return 'skip', f"pool ${_f(n.get('liq')) / 1000:.0f}K — pullable"
    d5 = _f(n.get('d5'))
    young_ = n.get('age') is not None and _f(n['age']) < 6   # 🐣 NEWBORN / EARLY: a fast candle is how a launch moves — only a vertical one is the top
    if d5 > (40 if young_ else 15):
        return 'skip', f'+{d5:.0f}% in 5 min — that is the top'
    if d5 < -8:
        return 'skip', f'{d5:.0f}% in 5 min — falling'
    need = 5 if (learned or {}).get('trial') == 'tally' else 3   # 👨‍⚖️ Tally on trial: more readings before anyone may enter
    bars_ = int(_f(((row.get('chart') or {}).get('f') or {}).get('n'))) if ((row.get('chart') or {}).get('src') == 'candles' and ((row.get('chart') or {}).get('q') or {}).get('enterOk')) else 0
    if max(int(n.get('pts') or 0), bars_) < need:   # 🐣 ENTER-grade real candles count as readings: a newborn is not made to wait three passes for Tally's own tape
        return 'wait', f'Tally has under {need} readings of this coin yet'
    if why['lean'] >= bar and (n.get('buy') is None or _f(n['buy']) >= 55):
        return 'enter', f"lean {why['lean']:+.1f} ≥ bar {bar:.1f}: " + ', '.join(d[2] for d in why['drivers'][:2])
    return 'wait', f"lean {why['lean']:+.1f} under the bar {bar:.1f}"


# ── ⚖ DEVIL ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
STRONG_MED, STRONG_N = -3.0, 20   # a soft rule becomes a VETO only on a strong record: ≥ 20 judged calls typically ≤ −3% at 5 min


def devil_args(call, n, why, row, learned, duty=False, warns=None):
    """EVERY material objection Devil has to an ENTER → [(rule id, the evidence in words)], strongest first = the VETOES.
    A WARNING (`warns`, when a list is handed in) is noted, never a veto: the coin is new (age is context), a reason against it is already
    inside Sherlock's lean ("found on volume leaders"), or a soft rule stands only on belief / a weak record. Hard safety rules (busted read,
    rug meter, ran > 150%, never holder-scanned, burned us, learned rug signs, an approved avoid, Devil on trial) are always vetoes.
    (2026-10-10: Devil objected to 26 of 34 case files — mostly "against it: found on volume leaders", a reason Sherlock had already weighed.)"""
    if call != 'enter':
        return []
    n, row = n or {}, row or {}
    args, w_ = [], (warns if warns is not None else [])
    rd = ((row.get('tv') or {}).get('call') or [None, None])[1]
    busted = (learned or {}).get('busted')
    sev_ = busted_severity(rd, busted)
    if sev_ == 'hard':   # its read type's own record is a safety failure (coins like it typically lose half in an hour)
        args.append(('busted_read', f"its read is {rd} — coins with it typically {_f(busted.get(rd)):+.0f}% in an hour (hard veto)"))
    elif sev_:   # a poor but not catastrophic record: a STRONG WARNING (rank penalty), not this coin's own danger
        w_.append(('busted_read', f'its read is {rd} — a busted call on its own record (strong warning)'))
    if _f((row.get('tv') or {}).get('rug')) >= 50:
        args.append(('rug_meter', f"rug meter {_f(row['tv']['rug']):.0f}"))
    if n.get('c1') is not None and _f(n['c1']) > 150:   # 🚀 stage-aware: under 1h old the "1h change" is launch-to-now, not a pump on an hour
        young_ = n.get('age') is not None and _f(n['age']) < 1
        (w_ if young_ else args).append(('ran', f"+{_f(n['c1']):.0f}% since launch — a launch's climb, judged on its slope (warning)" if young_ else f"already +{_f(n['c1']):.0f}% on the hour — it ran"))
    if n.get('age') is not None and _f(n['age']) < 0.25:
        w_.append(('young', 'new launch: under 15 minutes old — limited history (context, not a veto)'))
    if row.get('safe') is not True:
        args.append(('unscanned', 'holders never scanned'))
    cc_ = (row.get('social') or {}).get('cross') or {}
    for fl in ((row.get('social') or {}).get('warnings') or [])[:2]:   # 🔎 identity flags from the research packet: WARNINGS (a page can be down or new) — with the proof
        proof_ = f" [launch mint {str(cc_.get('launchMint') or row.get('mint') or '?')[:8]}… · source {cc_.get('sourceUrl') or '?'} shows {str(cc_.get('sourceMint') or '?')[:8]}…]" if 'contract' in fl else ''
        w_.append(('identity', f'identity: {fl}{proof_}'))
    if row.get('mint') in ((learned or {}).get('burned') or {}):
        args.append(('burned', 'burned us within the last 6h — a GO on it lost 20%+ in 5 min'))
    mind = row.get('mind') or {}
    ld_ = (learned or {}).get('drivers') or {}
    recorded = lambda k: int((ld_.get(k) or {}).get('n') or 0) >= DRIVER_MIN_N
    bad_rec = lambda k: recorded(k) and _f((ld_.get(k) or {}).get('med')) < SOFT_MED
    if (mind.get('crowd') or {}).get('swarm'):   # a soft signal vetoes only when its OWN record is really followed by losses; on belief it warns
        (args if bad_rec('swarm') else w_).append(('swarm', f"the callers are a bot swarm ({round(_f(mind['crowd'].get('swarmShare')) * 100)}% the same line)"))
    if _f((mind.get('bots') or (0, []))[0]) >= 40:
        (args if bad_rec('botted') else w_).append(('botted', 'botted launch: ' + '; '.join((mind['bots'][1] or [])[:2])))
    if {'swarm', 'botted'} <= {x[0] for x in w_} and not (recorded('swarm') and recorded('botted')):   # both bot signals on one coin (a swarm of callers AND a botted launch), not yet cleared by their records = material: a veto
        args += [x for x in w_ if x[0] in ('botted', 'swarm')]
        w_[:] = [x for x in w_ if x[0] not in ('botted', 'swarm')]
    pr_ = ((learned or {}).get('pads') or {}).get((row.get('launch') or {}).get('key')) or {}
    if int(pr_.get('enterN') or 0) >= PAD_MIN_N and pr_.get('enterMed5') is not None and _f(pr_['enterMed5']) <= PAD_BAD_MED:   # 🚀 a launch-specific failure pattern, on OUR record only
        args.append(('pad_losing', f"launch context {row['launch']['key']} loses on our own entries: {pr_['enterN']} ENTER calls, typical {_f(pr_['enterMed5']):+.1f}% at 5 min"))
    orec = (learned or {}).get('objrec') or {}
    for rule, text in (row.get('chart') or {}).get('objs') or []:   # 📈 the chart thesis attacked on its measurements (chart_intel.objections)
        v = orec.get(rule) or {}
        hard_ = _ci.CHART_RULES.get(rule, (True,))[0]
        (args if hard_ or (int(v.get('n') or 0) >= DRIVER_MIN_N and _f(v.get('med')) <= 0) else w_).append((rule, text))   # a soft chart rule vetoes once its record shows it right
    bad = [d for d in why['drivers'] if d[1] < 0]
    if bad:
        w_.append(('against', 'against it: ' + ', '.join(d[2] for d in bad[:2])))   # already inside Sherlock's lean — noted, never counted twice
    for k, _w, words in why['drivers']:
        v = ld_.get(k) or {}
        if int(v.get('n') or 0) >= DRIVER_MIN_N and _f(v.get('med')) < 0 and _f(_w) > 0:
            strong_ = int(v.get('n') or 0) >= STRONG_N and _f(v.get('med')) <= STRONG_MED
            (args if strong_ else w_).append(('driver_losing', f"'{words}' has been followed by {_f(v['med']):+.1f}% lately"))
    have_ = {d[0] for d in why['drivers']}
    rs_ = [x for x in have_ if ((learned or {}).get('rugSigns') or {}).get(x, 0) >= RUG_SIGN_N and not is_context(x)]
    if len(rs_) >= 2:   # 🔬 learned from autopsies: these reasons keep showing up on coins that rugged
        args.append(('rug_signs', 'rug signs from our autopsies: ' + ', '.join(word(x) for x in rs_[:3])))
    for iid, pair in ((learned or {}).get('avoid') or {}).items():   # 🚫 a creator-approved AVOID tactic
        if all(x in have_ for x in pair):
            args.append(('avoid', f"approved avoid-tactic {iid}: {word(pair[0])} + {word(pair[1])}"))
    tr = ((learned or {}).get('cards') or {}).get('trigger') or {}
    if not duty and int(tr.get('n') or 0) >= 15 and _f(tr.get('med')) < 0:   # about TRIGGER'S entries — a duty case is not one (its bar is waived), so it is judged on the coin alone
        (args if _f(tr.get('med')) <= STRONG_MED else w_).append(('trigger_losing', f"Trigger's last {tr['n']} calls: {_f(tr['med']):+.1f}% typical"))
    return args


# ⚖ Devil's rules by name: (hard?, what it is). HARD = it can never be waived or out-voted; SOFT = it stands only while its own record backs it.
DEVIL_RULES = {'busted_read': (True, "the coin's read type: a HARD veto when its own 1h record is ≤ −50% typical, else a strong warning (rank penalty)"), 'rug_meter': (True, 'rug meter ≥ 50'), 'ran': (True, 'already ran > +150% on the hour (a coin under 1h old: a warning — that is launch-to-now)'),
               'young': (False, 'under 15 minutes old — a WARNING (age is context)'), 'unscanned': (True, 'holders never scanned'), 'burned': (True, 'burned us in the last 6h'),
               'swarm': (False, 'the callers are a bot swarm'), 'botted': (False, 'botted launch'), 'against': (False, 'a reason against it is on the table'),
               'driver_losing': (False, 'one of its reasons has been followed by losses lately'), 'rug_signs': (True, 'rug signs learned from our autopsies'),
               'avoid': (True, 'a creator-approved avoid tactic'), 'pad_losing': (False, 'this launch context loses on our own entries'), 'trigger_losing': (False, "Trigger's own recent entries are losing"), 'trial': (True, 'Devil is on trial: only strong reads pass'),
               **{k: v for k, v in _ci.CHART_RULES.items()},
               'identity': (False, 'an identity flag from the website / X research'),
               'unrecorded': (False, 'reason not stored (calls judged before objections kept their reason)'), 'other': (False, 'other')}
_RULE_TEXT = (('its read is', 'busted_read'), ('rug meter', 'rug_meter'), ('already +', 'ran'), ('under 15 minutes', 'young'), ('holders never', 'unscanned'), ('burned us', 'burned'),
              ('the callers are', 'swarm'), ('botted launch', 'botted'), ('against it', 'against'), ('rug signs', 'rug_signs'), ('approved avoid', 'avoid'), ("Trigger's last", 'trigger_losing'),
              ('on trial', 'trial'), ("'", 'driver_losing'))


def devil_rule_of(text):
    """The rule id behind an objection kept only as text (calls judged before the id was stored)."""
    t = str(text or '')
    return next((k for pre, k in _RULE_TEXT if t.startswith(pre)), 'other')


def devil(call, n, why, row, learned, duty=False):
    """Argue against an ENTER. → (verdict 'agree' | 'object' | '—', the strongest argument)."""
    if call != 'enter':
        return '—', ''
    args = devil_args(call, n, why, row, learned, duty)
    return ('object', args[0][1]) if args else ('agree', 'no evidence against it')


# ── the chain ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
BUST_N, BUST_MED = 30, -20.0
SOFT_MED = -1.0   # a soft objection (botted / swarm) needs its own driver record to read worse than this over 5 minutes


def busted_now(proof, call_keys):
    """⚖ Which reads are REALLY busted, from their own settled 1-hour records (`/fuses/call-proof`): ≥ BUST_N settled and a typical result
    ≤ BUST_MED %. Devil's list used to be fixed text — on 2026-10-10 it rejected 19 of 25 coins as "WASH TRADED — a busted call on its own
    record" while that read's record was −0.2% / 47% up (flat), and TREND DOWN's was +0.3% / 72% up. → set of read labels, or None when
    there is no record to judge from (the fixed list stands in)."""
    if not proof:
        return None
    out = {}   # {read: its typical 1h %} — membership works like the old set; the median decides the SEVERITY (busted_severity)
    for label, key in (call_keys or {}).items():
        r = proof.get(key) or {}
        if int(_f(r.get('n'))) >= BUST_N and r.get('medPct') is not None and _f(r['medPct']) <= BUST_MED:
            out[label] = round(_f(r['medPct']), 1)
    return out


BUST_HARD = -50.0   # a read type whose coins typically lose half in an hour is a safety failure on the record: HARD VETO


def busted_severity(rd, busted):
    """'hard' (its own record ≤ BUST_HARD: BOND RUN −82%, EARLY RUSH −64% …) · 'strong' (busted, milder) · None. The fixed fallback list
    (no live record) is 'strong' only — a warning, never a veto on belief."""
    if busted is None:
        return 'strong' if rd in BUSTED else None
    if rd not in busted:
        return None
    med = busted.get(rd) if isinstance(busted, dict) else None
    return 'hard' if med is not None and _f(med) <= BUST_HARD else 'strong'


PAD_MIN_N, PAD_BAD_MED = 15, -3.0   # 🚀 Devil objects to a launch context only on ≥ 15 of our own ENTER calls with a typical 5-min result ≤ −3%
PAD_UNKNOWN_BAR = 0.25              # ⏱ an UNKNOWN launch needs this much more lean than the bar (stricter confidence, never a pass)


def desk(state, rows, now, dial=None, busted=None, weather_fn=None, candles=None, flows=None, charts_out=None, cmeta=None):
    """One paper pass: the kernel's senses read the rows (trench_kernel.senses.sense — measurements + evidence), then the four practice
    desks make their graded calls on them (`calls`). → (new state, table rows for the screen). Each coin's line carries every desk's word.
    The live service runs the two halves itself (sense → kernel → calls); this wrapper is the same thing in one call."""
    st, base, sctx = _sn.sense(state, rows, now, candles=candles, flows=flows, charts_out=charts_out, cmeta=cmeta, busted=busted, weather_fn=weather_fn)
    return calls(st, base, sctx, now, dial, busted)


def calls(st, base, sctx, now, dial=None, busted=None):
    """📝 THE PAPER CALLS on a sensed pass: Sherlock's lean, Trigger's ENTER / WAIT / SKIP against its bar, Devil's agree / object, GO.
    PRACTICE ONLY — every call is recorded and graded (record / settle / learn); the live kernel never reads `trigger`, `devil`, `go`,
    `case`, `objs` or `drule` (tests/test_kernel_authority.py). → (state, table = the sensed rows + the paper fields)."""
    import time as _t
    st = dict(st or {})
    learned = learn(st, 5)
    perf = {'tally': 0.0, 'sherlock': 0.0, 'trigger': 0.0, 'devil': 0.0, **(sctx.get('perf') or {})}
    nums, ser, first_ = sctx['nums'], st.get('series') or {}, st.get('first') or {}
    learned['regime'] = regime(nums)
    wx = st.get('weather')
    if wx and 'adj' in wx:   # 🌦 ONLY Weather's clamped bar adjustment reaches the paper Trigger
        learned['regime'] = {**learned['regime'], 'adj': _f(wx.get('adj')), 'weather': wx.get('regime')}
    learned['burned'] = {m: at for m, at in (st.get('burned') or {}).items() if now - _f(at) < BURN_SEC}
    learned['dial'] = dial if dial in DIALS else 'normal'
    learned['busted'] = busted
    learned['trial'] = judge(st)['trial']
    bar_ = bar_now(learned)
    import office_edge as _oe   # (lazy: office_edge reads this module)
    learned['pads'] = _oe.pad_record(_judged(st, 5))
    table = []
    for b in base or []:
        m = b['mint']
        raw = (sctx.get('raw') or {}).get(m) or {}
        r, chart, rd, n = raw.get('r') or {}, raw.get('chart'), raw.get('rd') or _tm.read(raw.get('r') or {}), b['nums']
        t0 = _t.perf_counter(); why = sherlock(n, r, learned); perf['sherlock'] += _t.perf_counter() - t0
        if learned['trial'] == 'sherlock' and why['lean'] > 0:
            why = {**why, 'lean': round(why['lean'] * TRIAL_LEAN, 2)}
        t0 = _t.perf_counter(); call, reason = trigger(n, why, r, learned)
        if chart and call != 'skip':   # the chart can only make the paper Trigger pickier
            ec = chart['entry']
            if ec[0] == 'SKIP':
                call, reason = 'skip', f'{ec[1]}: {ec[2]}'
            elif call == 'enter' and ec[0] != 'ENTER NOW':
                call, reason = 'wait', f'{ec[0]} — {ec[2]}'
            elif call == 'enter':
                reason += f' · 📈 {ec[1]}: {ec[2]}'
        lg_ = _oe.launch_gate(r['launch'], why['lean'], bar_) if call == 'enter' and r.get('launch') else None
        if lg_:
            call, reason = 'wait', lg_
        perf['trigger'] += _t.perf_counter() - t0
        s_ = ser.get(m) or []
        if s_ and next((p_.get('c') for p_ in reversed(s_) if p_.get('c')), None) != call[0]:   # the tape keeps the paper call each time it CHANGES (the missed-winner study)
            s_[-1].update(c=call[0], r=str(reason)[:60], l=why['lean'])
        if m not in first_:
            first_[m] = {'t': now, 'c': call[0], 'r': str(reason)[:60], 'l': why['lean']}
        t0 = _t.perf_counter(); dargs = devil_args(call, n, why, {**r, 'mint': m}, learned) if call == 'enter' else []
        verdict, arg = ('—', '') if call != 'enter' else (('object', dargs[0][1]) if dargs else ('agree', 'no evidence against it')); perf['devil'] += _t.perf_counter() - t0
        if learned['trial'] == 'devil' and verdict == 'agree' and why['lean'] < bar_ + TRIAL_BAR:
            verdict, arg = 'object', f"on trial — only a strong read passes (lean {why['lean']:+.1f} < {bar_ + TRIAL_BAR:.1f})"
        warns_ = []
        objs = devil_args('enter', n, why, {**r, 'mint': m}, learned, duty=True, warns=warns_) if call in ('enter', 'wait') and why['lean'] > 0 else None
        case = None if objs is None else (['object', objs[0][1]] if objs else ['agree', 'no evidence against it'])
        if case and learned['trial'] == 'devil' and case[0] == 'agree' and why['lean'] < bar_ + TRIAL_BAR:
            case, objs = ['object', 'on trial — only a strong read passes'], [('trial', 'on trial — only a strong read passes')]
        table.append({**b, 'case': case, 'objs': [list(o) for o in (objs or [])[:6]], 'drule': dargs[0][0] if dargs else None, 'why': why,
                      'trigger': [call, reason], 'devil': [verdict, arg], 'go': call == 'enter' and verdict == 'agree',
                      'analysis': _tm.analysis(r.get('symbol'), rd, n, call, verdict, arg), 'opinion': opinion(why, call, verdict, arg),
                      'strats': [STRAT_NAME[k] for k in strats(r, n)], 'warns': [list(w) for w in warns_[:6]], 'band': mc_band(r.get('mcap'))})
    st['first'] = first_
    table.sort(key=lambda x: (not x['go'], x['trigger'][0] != 'enter', -x['why']['lean']))
    st['feed'] = (list(st.get('feed') or []) + thoughts(table, now))[-FEED_KEEP:]
    st['perf'] = {k: round(v * 1000, 2) for k, v in perf.items()} | {'coins': len(table), 'regime': learned['regime'], 'at': now, 'bar': bar_, 'dial': learned['dial'], 'trial': learned['trial']}
    return st, table


def record(state, table, now, controls=3):
    """Note every ENTER (agreed or objected) once at its price, plus a few WAIT coins as the control group; Tally's 5-min direction call
    rides along (does the move keep going?). A coin is not noted again while open or 30 min after its last call."""
    st = dict(state or {})
    opened, done = dict(st.get('open') or {}), list(st.get('done') or [])
    recent = {d['mint'] for d in done if now - _f(d.get('at')) < 1800}
    waits = 0
    for x in table:
        m = x['mint']
        if m in opened or m in recent or x['px'] <= 0:
            continue
        kind = 'enter' if x['trigger'][0] == 'enter' else ('wait' if x['trigger'][0] == 'wait' and waits < controls else None)
        if not kind:
            continue
        waits += kind == 'wait'
        opened[m] = {'px': x['px'], 'at': now, 'sym': x['symbol'], 'kind': kind, 'go': x['go'], 'devil': x['devil'][0], **({'devilWhy': str(x['devil'][1])[:90], 'devilRule': x.get('drule') or devil_rule_of(x['devil'][1])} if x['devil'][0] == 'object' else {}),
                     **({'cs': x['chart']['state'], 'ce': x['chart']['entry'][0]} if x.get('chart') else {}),
                     **({'pad': x['launch']['key']} if (x.get('launch') or {}).get('key') else {}),   # 🚀 the launch context AT the call
                     **({'dq': x['chart']['q']['state'], 'dqc': x['chart']['q']['conf']} if (x.get('chart') or {}).get('q') else {}),   # 🧪 the data-quality state AT the call, kept with it
                     'drivers': [d[0] for d in x['why']['drivers']], 'lean': x['why']['lean'], 'tallyUp': _f(x['nums'].get('d5')) > 0, 'tw': str((x.get('trigger') or ['', ''])[1])[:80],
                     **({'scalp': [st['scalp']['tp'], st['scalp']['sl']]} if (st.get('scalp') or {}).get('tp') else {})}
    st['open'], st['done'] = opened, done[-KEEP_DONE:]
    return st


def settle(state, price_of, now):
    """Judge open calls at 5 / 15 / 60 minutes (no price at 60 = −100%: it vanished). A call is done after 60 minutes."""
    st = dict(state or {})
    opened, done = dict(st.get('open') or {}), list(st.get('done') or [])
    for m, o in list(opened.items()):
        o = dict(o)   # never mutate the caller's copy (the 5-min verdict feed compares before / after)
        age = (now - _f(o['at'])) / 60
        px = _f(price_of(m))
        if px > 0 and _f(o['px']) > 0:
            o['seen'], o['last'] = round(now, 1), round((px / _f(o['px']) - 1) * 100, 2)
        if px > 0 and _f(o['px']) > 0 and age <= SCALP_MIN_WINDOW and len(o.get('path') or []) < 8:   # ⚡ the first 5 minutes, a reading a pass: what a scalp would have seen
            o['path'] = list(o.get('path') or []) + [round((px / _f(o['px']) - 1) * 100, 2)]
        for h in STAGES:
            key = f'p{h}'
            if key not in o and age >= h:
                if px > 0 and _f(o['px']) > 0:
                    o[key] = round((px / _f(o['px']) - 1) * 100, 2)
                elif h == 60:
                    o[key] = o['last'] if o.get('last') is not None and now - _f(o.get('seen')) < GONE_SEC else -100.0
                else:
                    o[key] = None
        opened[m] = o
        if age >= STAGES[-1]:
            done.append({**o, 'mint': m, 'at': o['at'], 'doneAt': now})
            opened.pop(m)
    st['open'], st['done'] = opened, done[-KEEP_DONE:]
    return st


def _judged(state, h):
    k = f'p{h}'
    return [d for d in list(((state or {}).get('open') or {}).values()) + list((state or {}).get('done') or []) if d.get(k) is not None]


def _card(ps, right):
    n = len(ps)
    return {'n': n, 'med': None if not n else round(_med(ps), 2), 'won': None if not n else round(sum(1 for p in ps if p > 0) / n * 100),
            'right': None if not right else round(sum(right) / len(right) * 100)}


def learn(state, h=5):
    """Every agent's scorecard on the `h`-minute result + Sherlock's learned driver weights + Trigger's bar. Each agent learns ONLY from the
    calls of its CURRENT life (`born[agent]`): a scrapped agent is reborn with nothing but its belief. The team / control cards keep everything."""
    js = _judged(state, h)
    k = f'p{h}'
    born = (state or {}).get('born') or {}
    life = lambda a: [d for d in js if _f(d.get('at')) >= _f(born.get(a))]
    drv = {}
    for d in life('sherlock'):
        for x in d.get('drivers') or []:
            drv.setdefault(x, []).append(_f(d[k]))
    drivers_ = {x: {'n': len(v), 'med': round(_med(v), 2)} for x, v in drv.items()}
    enters_all = [d for d in js if d.get('kind') == 'enter']
    gos = [d for d in enters_all if d.get('go')]
    tr_ = [d for d in life('trigger') if d.get('kind') == 'enter']
    dv_ = [d for d in life('devil') if d.get('kind') == 'enter']
    objected, agreed = [d for d in dv_ if d.get('devil') == 'object'], [d for d in dv_ if d.get('devil') == 'agree']
    ta_, sh_ = life('tally'), [d for d in life('sherlock') if d.get('lean')]
    cards = {
        'tally': _card([_f(d[k]) for d in ta_], [(_f(d[k]) > 0) == bool(d.get('tallyUp')) for d in ta_]),          # the move keeps going?
        'sherlock': _card([_f(d[k]) for d in sh_], [(_f(d[k]) > 0) == (_f(d.get('lean')) > 0) for d in sh_]),
        'trigger': _card([_f(d[k]) for d in tr_], [_f(d[k]) > 0 for d in tr_]),
        'devil': _card([_f(d[k]) for d in objected], [_f(d[k]) <= 0 for d in objected] + [_f(d[k]) > 0 for d in agreed]),
        'team': _card([_f(d[k]) for d in gos], [_f(d[k]) > 0 for d in gos]),
        'control': _card([_f(d[k]) for d in js if d.get('kind') == 'wait'], None),
    }
    t = cards['trigger']
    bar = 1.5 if not t['n'] or t['n'] < 15 else (2.5 if _f(t['med']) < 0 else 1.0 if _f(t['won']) >= 60 else 1.5)   # losing → pickier
    lessons = (state or {}).get('lessons') or {}
    # (a reborn Trigger no longer starts pickier — lessons only, never a stricter bar: generations.py)
    cal = {}
    for d in enters_all:   # 🎯 calibration: does a stronger lean really win more?
        b_ = '0–1' if _f(d.get('lean')) < 1 else '1–2' if _f(d.get('lean')) < 2 else '2–3' if _f(d.get('lean')) < 3 else '3+'
        cal.setdefault(b_, []).append(_f(d[k]))
    calib = {b_: {'n': len(v), 'med': round(_med(v), 2), 'won': round(sum(1 for x in v if x > 0) / len(v) * 100)} for b_, v in sorted(cal.items())}
    budget = {x[4:]: v for x, v in drivers_.items() if x.startswith('src:') and v['n'] >= BUDGET_N and v['med'] < 0}
    og = {}
    for d in dv_:   # ⚖ each objection RULE's own record (what the coins it blocked did): a soft chart rule that keeps blocking winners stops standing
        if d.get('devil') == 'object' and d.get('devilRule'):
            og.setdefault(d['devilRule'], []).append(_f(d[k]))
    ideas_ = (state or {}).get('ideas') or {}
    return {'drivers': drivers_, 'cards': cards, 'bar': round(bar, 2), 'h': h, 'calibration': calib, 'cut': budget,
            'lessons': lessons, 'rugSigns': rug_lift(js), 'objrec': {r_: {'n': len(v), 'med': round(_med(v), 2)} for r_, v in og.items()},
            'approved': {i: v['pair'] for i, v in ideas_.items() if v.get('status') == 'approved' and v.get('kind') == 'take'},
            'avoid': {i: v['pair'] for i, v in ideas_.items() if v.get('status') == 'approved' and v.get('kind') == 'avoid'}}


def stage(state):
    """The timeframe the desk is on: 5 until it is conquered (team GO ≥ PROVE_N judged, median > 0, ≥ PROVE_WIN % won), then 15, then 60."""
    for h in STAGES:
        c = learn(state, h)['cards']['team']
        ph = real_phase((state or {}).get('money'))
        # 5 min: the existing rules (the trench desk 10× in one run, enough judged calls) AND the REAL card at 2× its put-in. Breakeven is
        # milestone 1, not graduation; paper alone, or a card whose money is unknown, never unlocks a real-money stage.
        if h == 5 and not (paper(state)['x'] >= PROVE_X and int(c['n'] or 0) >= PROVE_N and ph['eligible']):
            return {'h': h, 'conquered': [], 'team': c, 'needN': PROVE_N, 'needWin': PROVE_WIN, 'needX': PROVE_X, 'needBE': underwater(state), 'need2x': not ph['eligible'], 'phase': ph['phase'], 'real': ph}
        if h != 5 and not (int(c['n'] or 0) >= PROVE_N and _f(c['med']) > 0 and _f(c['won']) >= PROVE_WIN):
            return {'h': h, 'conquered': [x for x in STAGES if x < h], 'team': c, 'needN': PROVE_N, 'needWin': PROVE_WIN}
    return {'h': STAGES[-1], 'conquered': list(STAGES), 'team': learn(state, STAGES[-1])['cards']['team'], 'needN': PROVE_N, 'needWin': PROVE_WIN}


# ── ⚡ DEGEN SCALPING — the desk learns WHEN TO GET OUT inside the 5 minutes, from its own entries ─────────────────────────────────────
# (owner, 2026-10-10: "make sure they learn degen scalping; their goal is to 10× their paper, but first get my Fuse card back to breakeven").
# Every ENTER keeps its PATH: the coin's move at each pass (~1 a minute) for its first 5 minutes. `scalp_plan` replays every take-profit ×
# stop pair on those real paths — out at the take line the first reading at / above it (booked AT the line, never above), out at the
# reading that broke the stop (booked at what was SEEN, so a gap through the stop costs what it cost), else the 5-minute price — and
# compares each with just holding 5 minutes. A plan is ADOPTED only with ≥ SCALP_N paths, an average above zero AND above holding. An
# adopted plan is stamped on every LATER call (`scalp`), so the paper desk never grades a plan on the paths it was picked from.
SCALP_TPS, SCALP_SLS = (5, 8, 12, 20, 30, 50), (0, 5, 8, 12, 20)   # stop 0 = no stop
SCALP_N, SCALP_MIN_WINDOW = 20, 5.6


def scalp_exit(path, p5, tp, sl):
    for v in path or []:
        if tp and _f(v) >= tp:
            return float(tp)
        if sl and _f(v) <= -sl:
            return _f(v)
    return _f(p5)


def scalp_plan(state):
    """→ {n, flat {avg, med, won}, best {tp, sl, avg, med, won} | None, proven, peak (typical best reading), grid (top 5)}. Learned on every
    ENTER Trigger made that has a path and a 5-minute price (GO or objected — its entries are what a scalp trades)."""
    ds = [d for d in _judged(state, 5) if d.get('kind') == 'enter' and d.get('path')]
    n = len(ds)
    card_ = lambda xs: {'avg': round(sum(xs) / len(xs), 2), 'med': round(_med(xs), 2), 'won': round(sum(1 for x in xs if x > 0) / len(xs) * 100)} if xs else {'avg': None, 'med': None, 'won': None}
    flat = card_([_f(d['p5']) for d in ds])
    grid = []
    for tp in SCALP_TPS:
        for sl in SCALP_SLS:
            grid.append({'tp': tp, 'sl': sl, **card_([scalp_exit(d['path'], d['p5'], tp, sl) for d in ds])})
    grid = sorted((g for g in grid if g['avg'] is not None), key=lambda g: (-g['avg'], -g['won'], g['tp']))
    best = grid[0] if grid else None
    proven = bool(best and n >= SCALP_N and best['avg'] > 0 and best['avg'] > _f(flat['avg']))
    peaks = [max(_f(v) for v in d['path']) for d in ds]
    return {'n': n, 'needN': SCALP_N, 'flat': flat, 'best': best, 'proven': proven, 'peak': round(_med(peaks), 2) if peaks else None, 'grid': grid[:5],
            'live': (state or {}).get('scalp') or None}


def scalp_adopt(state, now):
    """Adopt (or change) the plan the desk scalps by once it is proven on its own paths; a plan that stops being proven is dropped."""
    st = dict(state or {})
    sp = scalp_plan(st)
    cur = st.get('scalp') or {}
    if sp['proven']:
        if (cur.get('tp'), cur.get('sl')) != (sp['best']['tp'], sp['best']['sl']):
            st['scalp'] = {'tp': sp['best']['tp'], 'sl': sp['best']['sl'], 'at': now, 'n': sp['n'], 'avg': sp['best']['avg']}
    elif cur:
        st.pop('scalp', None)
    return st


def mission(value, put_in, pp, scalp=None):
    """🎯 What the agents are FOR right now: while the creator's real card is worth less than what was put in → BREAKEVEN FIRST (how far,
    the × it needs — a distance, never a promise); once it is back → the paper 10×."""
    v, p = _f(value), _f(put_in)
    if p > 0 and 0 < v < p:
        return {'key': 'breakeven', 'value': round(v, 2), 'putIn': round(p, 2), 'pct': round(v / p * 100, 1), 'needX': round(p / v, 1), 'scalping': bool((scalp or {}).get('tp')), 'double': round(p * GRADUATE_X, 2)}
    if p > 0 and v < p * GRADUATE_X:   # 🎓 phase 2: breakeven reached — grow the REAL card to 2× the put-in before anything unlocks
        return {'key': 'double', 'value': round(v, 2), 'putIn': round(p, 2), 'pct': round((v - p) / (p * (GRADUATE_X - 1)) * 100, 1), 'needX': round(p * GRADUATE_X / v, 2) if v > 0 else None,
                'scalping': bool((scalp or {}).get('tp')), 'double': round(p * GRADUATE_X, 2)}
    return {'key': 'tenx', 'value': round(v, 2), 'putIn': round(p, 2), 'pct': round(min(1.0, _f((pp or {}).get('x')) / PROVE_X) * 100, 1), 'needX': round(PROVE_X / max(_f((pp or {}).get('x')), 1e-9), 1),
            'scalping': bool((scalp or {}).get('tp'))}


def stake_pct(streak):
    """🔥 PRESS WINNERS, CUT AFTER A LOSS (paper desk only): the next GO's stake follows the streak of the calls before it — 25% even ·
    35% after 2 wins in a row · 45% after 3+ · 15% right after a loss. Never the real card: its seat size is the creator's setting."""
    return HEAT_STAKES[3] if streak >= 3 else HEAT_STAKES[2] if streak == 2 else HEAT_STAKES[0] if streak < 0 else DESK_PCT


def paper(state):
    """The team's paper desk, TRENCH style: every GO call puts 25% of the desk in at its price and sells at its 5-minute price, so wins
    compound (a 10× needs a real run of good calls). Under $1 the desk is BUSTED: it starts over at $20 and the bust is counted. Fees and
    slippage are not modelled — read it as an upper bound. → {start, now, x (this run), best (best run ×), busts, trades, trail}"""
    gos = sorted((d for d in _judged(state, 5) if d.get('go')), key=lambda d: _f(d.get('at')))
    cash, best, busts, trail, run_trades, streak = DESK_START, 1.0, 0, [], 0, 0
    for d in gos:
        pct_ = stake_pct(streak)
        stake = cash * pct_ / 100
        res = scalp_exit(d.get('path'), d['p5'], *d['scalp']) if d.get('scalp') else _f(d['p5'])   # ⚡ a call made under a scalp plan exits by it
        pnl = stake * max(-100.0, res) / 100
        cash = round(cash + pnl, 4); run_trades += 1
        best = max(best, cash / DESK_START)
        trail.append({'at': d['at'], 'sym': d.get('sym'), 'pct': round(res, 2), 'usd': round(pnl, 4), 'book': cash, 'stake': pct_, 'scalp': bool(d.get('scalp'))})
        streak = (max(streak, 0) + 1) if res > 0 else (min(streak, 0) - 1)
        if cash < DESK_BUST:
            busts += 1; cash = DESK_START; run_trades = 0; streak = 0
            trail.append({'at': d['at'], 'sym': '💥 BUST', 'pct': None, 'usd': 0.0, 'book': cash})
    return {'start': DESK_START, 'now': cash, 'x': round(cash / DESK_START, 3), 'best': round(best, 2), 'busts': busts, 'trades': len(gos),
            'runTrades': run_trades, 'trail': trail[-20:], 'streak': streak, 'stake': stake_pct(streak),
            'heat': 'heater' if streak >= 2 else 'cold' if streak < 0 else 'even'}


def road(state, real=None):
    """🛣 How close the desk is to REAL money (owner: "how close it is to real money"): step 1 = the 5-minute paper desk reaches 10× in one
    run with ≥ PROVE_N judged GO calls; step 2 = the REAL-money test on the owner's Fuse card (their GO coins in the card's rush, judged
    on the card's own ledger: ≥ 10 closed pieces, typical result > 0); then 15 min, then 60. `real` = the agents' pieces on the real card."""
    pp, team = paper(state), learn(state, 5)['cards']['team']
    x_prog = min(1.0, max(0.0, __import__('math').log(max(pp['x'], 1e-9)) / __import__('math').log(PROVE_X))) if pp['x'] > 1 else 0.0
    n_prog = min(1.0, int(team['n'] or 0) / PROVE_N)
    paper_done = pp['x'] >= PROVE_X and int(team['n'] or 0) >= PROVE_N
    r = real or {}
    real_done = int(r.get('n') or 0) >= 10 and _f(r.get('med')) > 0
    pct = round((min(x_prog, n_prog) * 0.5 + (0.5 * min(1.0, int(r.get('n') or 0) / 10) * (1 if _f(r.get('med')) > 0 else 0.5) if paper_done else 0.0)) * 100)
    return {'pct': 100 if paper_done and real_done else pct, 'paper': {'done': paper_done, 'x': pp['x'], 'need': PROVE_X, 'n': int(team['n'] or 0), 'needN': PROVE_N},
            'real': {'open': paper_done, 'done': real_done, 'n': int(r.get('n') or 0), 'med': r.get('med'), 'won': r.get('won'), 'needN': 10, 'suggested': r.get('suggested') or {}}}


def thoughts(table, now, top=4):
    """🗯 What the four said this pass, in their own words and their own humor, for the coins worth a line (every ENTER, else the strongest
    leans) — plus the desk's written analysis of each."""
    pick = [x for x in table if x['trigger'][0] == 'enter'][:top] or sorted(table, key=lambda x: -abs(x['why']['lean']))[:2]
    out = []
    for x in pick:
        n, sym = x['nums'], x['symbol']
        j = (x.get('analysis') or {}).get('jokes') or {}
        joke = lambda k: f" — “{j[k]}”" if j.get(k) else ''
        out.append({'at': now, 'who': 'tally', 'sym': sym, 'text': f"${sym} {n['d5']:+.1f}% in 5 min" + (f" · pace {n['pace']}×" if n.get('pace') is not None else '')
                    + (f" · {round(_f(n['buy']))}% buys" if n.get('buy') is not None else '') + (f" · pool {n['liqD']:+.0f}%" if n.get('liqD') else '') + joke('tally')})
        ds = x['why']['drivers']
        out.append({'at': now, 'who': 'sherlock', 'sym': sym, 'text': ('; '.join(f"{d[2]} ({d[1]:+.1f})" for d in ds[:3]) if ds else 'nothing is moving it') + f" → lean {x['why']['lean']:+.1f}" + joke('sherlock')})
        out.append({'at': now, 'who': 'trigger', 'sym': sym, 'text': f"{x['trigger'][0].upper()} — {x['trigger'][1]}" + joke('trigger')})
        if x['devil'][0] != '—':
            out.append({'at': now, 'who': 'devil', 'sym': sym, 'text': f"{'agrees' if x['devil'][0] == 'agree' else 'OBJECTS'} — {x['devil'][1]}" + (' → 🟢 GO' if x['go'] else ' → ✋ no trade') + joke('devil')})
        if (x.get('analysis') or {}).get('text'):
            out.append({'at': now, 'who': 'desk', 'sym': sym, 'text': '✍ ' + x['analysis']['text']})
    return out


def results(before, after, now):
    """🧾 Calls that just got their 5-minute verdict (in `after`, not judged in `before`) → feed lines."""
    was = {m for m, o in ((before or {}).get('open') or {}).items() if o.get('p5') is not None}
    out = []
    for m, o in ((after or {}).get('open') or {}).items():
        if o.get('p5') is not None and m not in was and o.get('kind') == 'enter':
            ok = _f(o['p5']) > 0
            out.append({'at': now, 'who': 'desk', 'sym': o.get('sym'), 'text': f"{'✅' if ok else '❌'} ${o.get('sym')} {'GO' if o.get('go') else 'refused on paper'} → {_f(o['p5']):+.1f}% after 5 min"
                        + ('' if o.get('go') else (' (Devil was right)' if not ok else ' (Devil was wrong)'))})
            r_ = ruling(o)
            if r_['verdict'] != 'push':
                out.append({'at': now, 'who': 'judge', 'sym': o.get('sym'), 'text': f"{'🏆' if r_['verdict'] == 'win' else '🔨'} ${o.get('sym')} {_f(o['p5']):+.1f}% — "
                            + (f"{NAME[r_['credit']]} called it" if r_.get('credit') else '') + (' · ' if r_.get('credit') and r_.get('blame') else '') + (f"{NAME[r_['blame']]} takes the L" if r_.get('blame') else '')})
    return out


def view(state, table, feed=False, real=None, mind=None, cfg=None, decisions=None, now=0.0, card=None, money=None):
    """What the HQ tab shows: the four agents with their scorecards, the live table (every agent's word per coin), the desk, the stage."""
    lr = learn(state, 5)
    st_ = stage(state)
    names = {a[0]: a for a in AGENTS}
    cards = [{'key': k, 'icon': names[k][1], 'name': names[k][2], 'job': names[k][3], **lr['cards'][k]} for k in ('tally', 'sherlock', 'trigger', 'devil')]
    proven = 5 in st_['conquered']
    return {'agents': cards, 'team': lr['cards']['team'], 'control': lr['cards']['control'], 'bar': lr['bar'], 'stage': st_, 'proven5': proven,
            'drivers': sorted(({'key': k, 'words': word(k), **v} for k, v in lr['drivers'].items()), key=lambda x: -_f(x['med'])),
            'table': view_rows(table), 'desk': paper(state), 'open': len((state or {}).get('open') or {}), 'feed': bool(feed and proven), 'feedAsked': bool(feed),
            'road': road(state, real), 'thoughts': list(reversed(((state or {}).get('feed') or [])[-40:])), 'real': real or {}, 'mind': mind or {},
            'ideas': sorted(({'id': i, **v} for i, v in ((state or {}).get('ideas') or {}).items()), key=lambda x: (x['status'] != 'new', -_f(x.get('at')))),
            'cfg': {'agentFeed': bool((cfg or {}).get('agentFeed')), 'agentLearn': bool((cfg or {}).get('agentLearn')), 'agentLearnPct': int(_f((cfg or {}).get('agentLearnPct') or 100)), 'agentTrust': bool((cfg or {}).get('agentTrust')), 'agentControl': bool((cfg or {}).get('agentControl')), 'agentScalp': bool((cfg or {}).get('agentScalp', True)), 'agentCurve': bool((cfg or {}).get('agentCurve')), 'agentDial': (cfg or {}).get('agentDial') if (cfg or {}).get('agentDial') in DIALS else 'normal',
                    'agentTakePct': int(_f((cfg or {}).get('agentTakePct') or 10)), 'agentMode': (cfg or {}).get('agentMode') or 'auto',
                    'agentSeats': int(_f((cfg or {}).get('agentSeats') or 2)), 'options': {'take': list(AGENT_TAKES), 'mode': list(AGENT_MODES), 'seats': list(AGENT_SEATS)}},
            'decisions': decisions or [], 'tasks': tasks(state, table, now), 'creed': list(CREED),
            'approveN': IDEA_APPROVE_N,
            'perf': (state or {}).get('perf') or {}, 'lessons': (state or {}).get('lessons') or {}, 'calibration': lr['calibration'], 'cut': lr['cut'],
            'burned': len((state or {}).get('burned') or {}),
            'autopsies': list(reversed(((state or {}).get('autopsies') or [])[-12:])), 'rugSigns': sorted(({'key': k, 'words': word(k), 'n': v} for k, v in ((state or {}).get('rugSigns') or {}).items()), key=lambda x: -x['n'])[:8],
            'card': card or {}, 'underwater': underwater(state),
            'judge': judge(state), 'proof': proof(state, real), 'objections': objections(state, 24, now)[:6], 'scalp': scalp_plan(state),
            'mission': mission((money or {}).get('value'), (money or {}).get('putIn'), paper(state), (state or {}).get('scalp')), 'barNow': ((state or {}).get('perf') or {}).get('bar') or lr['bar'],
            'hist': ((state or {}).get('hist') or [])[-96:], 'rules': rules({**lr, 'regime': ((state or {}).get('perf') or {}).get('regime')})}


# ── 👨‍⚖️ THE JUDGE — the fifth seat. It never calls a trade: 5 minutes after every FINAL decision it rules on it ───────────────────
# (owner, 2026-10-10: "a final judge who reviews the good and bad 5 mins after their final decision, to judge one of the bots").
# Every ruled call names ONE bot who called it (credit) and / or ONE who takes the L (blame) — the bot whose word decided that call:
#   GO that won   → Sherlock if its read was strong (lean ≥ 2) · else Tally if the numbers were already moving up · else Trigger (timing)
#   GO that lost  → Devil if it dumped ≤ −20% (the gate that exists to stop that) · else Sherlock (strong read, wrong) · Tally · Trigger
#   OBJECTED      → it lost: Devil called it, Trigger takes the L · it won: Trigger called it, Devil takes the L (blocked a winner)
#   WAIT (control)→ ran ≥ +10%: a 😴 MISS on Trigger — shown and counted apart, NEVER toward a trial (a trial tightens; a missed runner
#                   is the opposite problem — the creator's 🔥 dial is the lever for that)
# Over its last JUDGE_LAST rulings: the bot with the worst net (≤ −JUDGE_NET) goes ON TRIAL and plays under a handicap until its net
# recovers — and a handicap may only ever make the team trade LESS: Trigger bar +0.5 · Sherlock's lean ×0.75 · Devil passes only strong
# reads · Tally needs 5 readings. The best net (≥ +JUDGE_NET) wears the 👑. Nothing here touches the real card by itself.
JUDGE_WIN, JUDGE_LOSS, JUDGE_DUMP, JUDGE_MISS = 3.0, -3.0, -20.0, 10.0
JUDGE_LAST, JUDGE_NET = 30, 2
TRIAL_BAR, TRIAL_LEAN = 0.5, 0.75
NAME = {'tally': 'Tally', 'sherlock': 'Sherlock', 'trigger': 'Trigger', 'devil': 'Devil'}
HANDICAP = {'trigger': 'bar +0.5', 'sherlock': 'lean ×0.75', 'devil': 'only strong reads pass', 'tally': '5 readings before an entry'}


def ruling(d):
    """One call with its 5-minute result → {verdict: win | loss | push, credit, blame, kind: go | objected | wait}."""
    p = _f((d or {}).get('p5'))
    strong, up = _f(d.get('lean')) >= 2, bool(d.get('tallyUp'))
    if d.get('kind') == 'wait':
        return {'verdict': 'miss', 'blame': 'trigger', 'credit': None, 'kind': 'wait'} if p >= JUDGE_MISS else {'verdict': 'push', 'blame': None, 'credit': None, 'kind': 'wait'}
    if d.get('go'):
        if p >= JUDGE_WIN:
            return {'verdict': 'win', 'credit': 'sherlock' if strong else 'tally' if up else 'trigger', 'blame': None, 'kind': 'go'}
        if p <= JUDGE_LOSS:
            return {'verdict': 'loss', 'blame': 'devil' if p <= JUDGE_DUMP else 'sherlock' if strong else 'tally' if up else 'trigger', 'credit': None, 'kind': 'go'}
        return {'verdict': 'push', 'blame': None, 'credit': None, 'kind': 'go'}
    if p <= JUDGE_LOSS:
        return {'verdict': 'win', 'credit': 'devil', 'blame': 'trigger', 'kind': 'objected'}     # the objection saved the desk
    if p >= JUDGE_WIN:
        return {'verdict': 'loss', 'credit': 'trigger', 'blame': 'devil', 'kind': 'objected'}    # it blocked a winner
    return {'verdict': 'push', 'blame': None, 'credit': None, 'kind': 'objected'}


REAL_WIN, REAL_LOSS, REAL_DUMP = 3.0, -3.0, -15.0   # a real exit of the agents' own seat (the card's ledger result, %)
REAL_WEIGHT = 2                                      # 💵 a real-money ruling counts double: that is the money the Judge answers to


def real_ruling(p):
    """💵 One coin that left an AGENT seat on the real card (real_learn piece: pct · holdMin · why) → a ruling. A dump the desk let through
    (≤ −15%) is Devil's (it should have seen the danger) · a smaller loss is Trigger's (the timing) · a win is Tally's when it came fast
    (≤ 10 min: the numbers were right) else Sherlock's (the reasons held). Owner, 2026-10-11: "judge needs to be on somebody's ass"."""
    x = _f((p or {}).get('pct'))
    if x >= REAL_WIN:
        return {'verdict': 'win', 'credit': 'tally' if _f(p.get('holdMin')) <= 10 else 'sherlock', 'blame': None, 'kind': 'real'}
    if x <= REAL_LOSS:
        return {'verdict': 'loss', 'blame': 'devil' if x <= REAL_DUMP else 'trigger', 'credit': None, 'kind': 'real'}
    return {'verdict': 'push', 'blame': None, 'credit': None, 'kind': 'real'}


def miss_study(state, n=6):
    """😴 THE MISSES, STUDIED: every WAIT that ran ≥ JUDGE_MISS in 5 min, grouped by Trigger's own reason (numbers folded) → which rule
    keeps the desk out of winners: [{why, n, med}] biggest first. Display + learning only — a miss never loosens a gate by itself."""
    import re as _re
    g = {}
    for d in _judged(state, 5):
        if d.get('kind') == 'wait' and _f(d.get('p5')) >= JUDGE_MISS:
            k = _re.sub(r'[-+]?\d+(\.\d+)?', '#', str(d.get('tw') or 'reason not recorded (older call)'))[:70]
            g.setdefault(k, []).append(_f(d.get('p5')))
    return sorted(({'why': k, 'n': len(v), 'med': round(_med(v), 1)} for k, v in g.items()), key=lambda x: -x['n'])[:n]


def judge(state):
    """👨‍⚖️ The court's book: the last rulings, each bot's credit / blame / net, who is ON TRIAL (and its handicap), who wears the 👑."""
    js = sorted(_judged(state, 5), key=lambda d: _f(d.get('at')))
    ruled = [(d, ruling(d)) for d in js]
    real = [({'sym': p.get('symbol'), 'mint': p.get('mint'), 'p5': p.get('pct'), 'at': p.get('at'), 'rule': p.get('why')}, real_ruling(p)) for p in (state or {}).get('realPieces') or []]
    ruled = sorted([(d, r) for d, r in ruled + real if r['verdict'] != 'push'], key=lambda x: _f(x[0].get('at')))[-JUDGE_LAST:]
    score = {a: {'credit': 0, 'blame': 0, 'net': 0} for a in NAME}
    for _d, r in ruled:
        if r['verdict'] == 'miss':
            continue
        w_ = REAL_WEIGHT if r.get('kind') == 'real' else 1
        if r.get('credit'):
            score[r['credit']]['credit'] += w_
        if r.get('blame'):
            score[r['blame']]['blame'] += w_
    for v in score.values():
        v['net'] = v['credit'] - v['blame']
    worst = min(score, key=lambda a: (score[a]['net'], -score[a]['blame']))
    best = max(score, key=lambda a: (score[a]['net'], score[a]['credit']))
    trial = worst if score[worst]['net'] <= -JUDGE_NET else None
    mvp = best if score[best]['net'] >= JUDGE_NET and best != trial else None
    return {'rulings': [{'sym': d.get('sym'), 'mint': d.get('mint'), 'pct': d.get('p5'), 'at': d.get('at'), **r} for d, r in reversed(ruled[-14:])],
            'score': score, 'trial': trial, 'handicap': HANDICAP.get(trial), 'mvp': mvp, 'n': len(ruled), 'needNet': JUDGE_NET,
            'wins': sum(1 for _d, r in ruled if r['verdict'] == 'win'), 'losses': sum(1 for _d, r in ruled if r['verdict'] == 'loss'),
            'missed': sum(1 for _d, r in ruled if r['verdict'] == 'miss'), 'missWhy': miss_study(state),
            'real': {'wins': sum(1 for _d, r in ruled if r.get('kind') == 'real' and r['verdict'] == 'win'), 'losses': sum(1 for _d, r in ruled if r.get('kind') == 'real' and r['verdict'] == 'loss')}}


def objections(state, hours=24, now=0.0):
    """⚖ WHY Devil says no: every objection of the last `hours` grouped by its reason (numbers folded), with what those coins did 5 minutes
    later — so a reason that keeps blocking winners can be seen (and one that keeps saving the desk too). → [{why, n, med, saved %}]"""
    import re as _re
    g = {}
    for d in list(((state or {}).get('open') or {}).values()) + list((state or {}).get('done') or []):
        if d.get('devil') == 'object' and d.get('devilWhy') and (not now or now - _f(d.get('at')) <= hours * 3600):
            g.setdefault(_re.sub(r'[-+]?\d+(\.\d+)?', '#', d['devilWhy'])[:60], []).append(d.get('p5'))
    out = []
    for k, v in g.items():
        ps = [_f(p) for p in v if p is not None]
        out.append({'why': k, 'n': len(v), 'med': round(_med(ps), 1) if ps else None, 'saved': round(sum(1 for p in ps if p <= 0) / len(ps) * 100) if ps else None})
    return sorted(out, key=lambda x: -x['n'])


def proof(state, real=None):
    """🏆 PROVE IT — wins and losses, not words: every GO the team made on paper (5-min result) and every coin that left a real seat the
    creator allowed (the card's own ledger). `last` = newest first, for the win / loss pips."""
    gos = sorted((d for d in _judged(state, 5) if d.get('go')), key=lambda d: _f(d.get('at')))
    ps = [_f(d['p5']) for d in gos]
    side = lambda pcts: {'n': len(pcts), 'w': sum(1 for x in pcts if x > 0), 'l': sum(1 for x in pcts if x <= 0),
                         'best': round(max(pcts), 1) if pcts else None, 'worst': round(min(pcts), 1) if pcts else None, 'last': [round(x, 1) for x in pcts[-16:]][::-1]}
    r = real or {}
    return {'paper': {**side(ps), 'syms': [d.get('sym') for d in gos[-16:]][::-1]}, 'card': side(list(r.get('last') or [])), 'suggested': side(list((r.get('suggested') or {}).get('last') or []))}


# ── 💡 IDEAS — the desk proposes tactics from its own record; the creator approves or rejects ──────────────────────────────────────
IDEA_N, IDEA_TAKE, IDEA_AVOID, IDEA_WIN = 10, 3.0, -5.0, 55.0
IDEA_APPROVE_N = 15   # proposed at 10 calls, approvable only at 15 (owner: "approve ideas only with 15+ calls behind them")


def idea_id(pair):
    import hashlib
    return hashlib.sha1('|'.join(sorted(pair)).encode()).hexdigest()[:6]


def ideas(state, h=5):
    """Two drivers that keep showing up TOGETHER on judged ENTER calls: typical ≥ +3% at 5 min with ≥ 55% up → a 'take' tactic; typical ≤ −5%
    → an 'avoid' tactic (Devil objects to it once approved). ≥ 10 calls each. A pair already proposed (any status) is never proposed twice.
    → new state with `ideas` {id: {pair, kind, n, med, won, text, status: 'new', at}}."""
    st = dict(state or {})
    have = dict(st.get('ideas') or {})
    k = f'p{h}'
    pairs = {}
    for d in _judged(st, h):
        if d.get('kind') != 'enter':
            continue
        ds = sorted(set(d.get('drivers') or []))
        for i, a in enumerate(ds):
            for b in ds[i + 1:]:
                pairs.setdefault((a, b), []).append(_f(d[k]))
    for pair, ps in pairs.items():
        if len(ps) < IDEA_N:
            continue
        med, won = _med(ps), round(sum(1 for x in ps if x > 0) / len(ps) * 100)
        kind = 'take' if med >= IDEA_TAKE and won >= IDEA_WIN else 'avoid' if med <= IDEA_AVOID else None
        iid = idea_id(pair)
        if iid in have and have[iid].get('status') == 'new':   # a waiting idea keeps counting — its evidence grows until the creator decides
            have[iid] = {**have[iid], 'n': len(ps), 'med': round(med, 2), 'won': won, 'ready': len(ps) >= IDEA_APPROVE_N}
            continue
        if not kind or iid in have:
            continue
        verb = 'Back it when' if kind == 'take' else 'Stay out when'
        have[iid] = {'pair': list(pair), 'kind': kind, 'n': len(ps), 'med': round(med, 2), 'won': won, 'status': 'new', 'ready': len(ps) >= IDEA_APPROVE_N, 'at': max(_f(d.get('at')) for d in _judged(st, h)) if ps else 0,
                     'text': f"{verb} {word(pair[0])} + {word(pair[1])} show up together: {len(ps)} calls went {med:+.1f}% typical in {h} min ({won}% up)."}
    st['ideas'] = have
    return st


def review(state, iid, action):
    """The creator's call on an idea: 'approve' (Sherlock / Devil use it from the next pass) or 'reject' (kept, never proposed again)."""
    st = dict(state or {})
    ids = dict(st.get('ideas') or {})
    if iid not in ids or action not in ('approve', 'reject'):
        raise ValueError('No such idea.')
    if action == 'approve' and int(ids[iid].get('n') or 0) < IDEA_APPROVE_N:
        raise ValueError(f"Not yet — {ids[iid].get('n')} calls behind it; approve at {IDEA_APPROVE_N}+.")
    ids[iid] = {**ids[iid], 'status': 'approved' if action == 'approve' else 'rejected'}
    st['ideas'] = ids
    return st


def view_rows(table, top=24, young=24, young_h=6.0):
    """The board the tab shows: the top `top` by verdict + lean, then the `young` NEWEST launches (≤ young_h) the desk read this pass
    that are not already in it — every new coin the agents looked at is on screen, not only the strongest reads."""
    head = list(table or [])[:top]
    seen = {x.get('mint') for x in head}
    kids = [x for x in table or [] if x.get('mint') not in seen and ((x.get('vitals') or {}).get('ageH') is not None) and _f(x['vitals']['ageH']) <= young_h]
    kids.sort(key=lambda x: _f((x.get('vitals') or {}).get('ageH')))
    return head + kids[:young]


def tasks(state, table, now):
    """⚙ What each agent is doing right now, from the last pass (the live box)."""
    t = table or []
    calls = {}
    for x in t:
        calls[x['trigger'][0]] = calls.get(x['trigger'][0], 0) + 1
    moving = sum(1 for x in t if abs(_f(x['nums'].get('d5'))) >= 3)
    enters = [x for x in t if x['trigger'][0] == 'enter']
    obj = sum(1 for x in enters if x['devil'][0] == 'object')
    lr = learn(state, 5)
    nd = len(lr['drivers'])
    share = [x['why'].get('learned', 0) for x in t]
    return {'tally': f"read {len(t)} coins · {moving} moving ≥ 3% in 5 min",
            'sherlock': f"weighed {nd} reasons · {round(sum(share) / len(share) * 100) if share else 0}% of today's reads are our own record",
            'trigger': f"{calls.get('enter', 0)} ENTER · {calls.get('wait', 0)} WAIT · {calls.get('skip', 0)} SKIP · bar {lr['bar']}",
            'devil': f"paper: refused {obj} of {len(enters)} entries" + (f" · {len((state or {}).get('open') or {})} calls waiting on the clock" if state else ''),
            'at': now}


# ── 🔬 RUG AUTOPSY — every coin that rugged on the desk teaches Devil ─────────────────────────────────────────────────────────────────
RUG_P5, RUG_SIGN_N = -50.0, 3


RUG_LIFT, RUG_MIN_CALLS = 2.0, 8


CONTEXT_DRIVERS = ('src:', 'band:', 'soc:', 'pad:', 'narr:', 'strat:', 'chart:')   # where a coin was found / its cap band / narrative / launchpad / chart label: CONTEXT
CONTEXT_EXACT = ('fresh', 'narr_hot')                                                # (owner, 2026-10-11: a source or a label is never a hard veto — every coin earns its own call)


def is_context(driver):
    """A context driver (source · band · narrative · launchpad · strategy · chart label · age) — it weighs in Sherlock's lean from its own record,
    it is never a learned RUG SIGN (one rush of rugging launches from one outlet turned 'found on callouts' into a veto on every coin)."""
    x = str(driver or '')
    return x.startswith(CONTEXT_DRIVERS) or x in CONTEXT_EXACT


def rug_lift(judged):
    """☠ The REAL rug signs, rebuilt from the record every time (never a running counter): a reason is a rug sign only when it showed up in
    ≥ RUG_SIGN_N rugs AND coins carrying it rugged at ≥ RUG_LIFT × the base rate (≥ RUG_MIN_CALLS judged calls with it). A reason nearly
    every coin carries ("buyers in charge", "found on the open list") is on most rugs simply because it is on most coins — that is not a
    sign. (2026-10-10: the old counter re-counted old rugs every pass — "buyers" read 4,879 — so EVERY common reason was a "rug sign" and
    Devil objected to any coin with two of them.) → {driver: rugs it was on}"""
    is_rug = lambda d: (d.get('p5') is not None and _f(d['p5']) <= RUG_P5) or (d.get('p60') is not None and _f(d['p60']) <= -100)
    js = [d for d in judged or [] if d.get('drivers') is not None]
    if not js:
        return {}
    base = sum(1 for d in js if is_rug(d)) / len(js)
    n, r = {}, {}
    for d in js:
        rg = is_rug(d)
        for x in set(d.get('drivers') or []):
            if is_context(x):
                continue
            n[x] = n.get(x, 0) + 1
            if rg:
                r[x] = r.get(x, 0) + 1
    return {x: c for x, c in r.items() if c >= RUG_SIGN_N and n[x] >= RUG_MIN_CALLS and base > 0 and c / n[x] >= RUG_LIFT * base}


def autopsy(state, now):
    """Every judged call that rugged (≤ −50% at 5 min, or no price at 60 min = vanished) gets an autopsy: the reasons the desk saw at the time
    (its drivers) and what it MISSED (the reasons it weighed positive). Each driver seen in a rug is counted in `rugSigns`; Devil objects to a
    coin carrying 2+ signs that each showed up in ≥ 3 rugs. → new state (autopsies kept 60, newest last)."""
    st = dict(state or {})
    done_ids = {a['id'] for a in st.get('autopsies') or []}
    aut = list(st.get('autopsies') or [])
    oldest = min((_f(a.get('calledAt')) for a in aut), default=0.0) if len(aut) >= 60 else 0.0   # only 60 are kept: a rug older than the oldest kept one was already done
    by_key = {f"{a.get('sym')}:{int(_f(a.get('calledAt')))}": a for a in aut}   # ONE autopsy per call: an open call (no mint on it) and its judged copy are the same rug
    for m_, d in [(k, v) for k, v in (st.get('open') or {}).items()] + [(None, v) for v in st.get('done') or []]:
        p5, p60 = d.get('p5'), d.get('p60')
        rug = (p5 is not None and _f(p5) <= RUG_P5) or (p60 is not None and _f(p60) <= -100)
        did = f"{d.get('mint') or m_}:{int(_f(d.get('at')))}"
        same = by_key.get(f"{d.get('sym')}:{int(_f(d.get('at')))}")
        if rug and same is not None and same.get('p60') is None and p60 is not None:   # the 60-min result lands on the SAME autopsy
            same.update(p60=p60, text=same['text'].replace(f"{_f(p5):+.0f}% in 5 min)", f"{_f(p5):+.0f}% in 5 min, {_f(p60):+.0f}% in 60)", 1))
            continue
        if not rug or did in done_ids or same is not None or _f(d.get('at')) < oldest:
            continue
        drv = list(d.get('drivers') or [])
        aut.append({'id': did, 'sym': d.get('sym'), 'at': now, 'calledAt': d.get('at'), 'kind': d.get('kind'), 'go': bool(d.get('go')),
                    'p5': p5, 'p60': p60, 'seen': drv, 'missed': [x for x in drv if PRIOR.get(x, 0.0) >= 0 and not x.startswith('src:')][:4],
                    'text': f"${d.get('sym')} rugged ({_f(p5):+.0f}% in 5 min{'' if p60 is None else f', {_f(p60):+.0f}% in 60'})"
                            + (" after a GO" if d.get('go') else '') + (f" — we read it as: {', '.join(word(x) for x in drv[:3])}" if drv else '')})
    aut.sort(key=lambda a: _f(a.get('calledAt')))
    seen_ = {}
    for a in aut:   # old duplicates (written before the fix): keep the one that knows the 60-min result
        k_ = f"{a.get('sym')}:{int(_f(a.get('calledAt')))}"
        if k_ not in seen_ or (seen_[k_].get('p60') is None and a.get('p60') is not None):
            seen_[k_] = a
    aut = sorted(seen_.values(), key=lambda a: _f(a.get('calledAt')))
    st['autopsies'], st['rugSigns'] = aut[-60:], rug_lift(_judged(st, 5))
    return st


def rug_signs(row_drivers, state):
    """The rug signs a coin carries right now: its drivers that have each shown up in ≥ RUG_SIGN_N rugs."""
    sg = (state or {}).get('rugSigns') or {}
    return [x for x in row_drivers or [] if sg.get(x, 0) >= RUG_SIGN_N and not is_context(x)]


# ── 📈 DESK HISTORY — each agent's record over time, per generation ─────────────────────────────────────────────────────────────────
HIST_EVERY, HIST_KEEP = 1800.0, 336   # a snapshot every 30 min, a week kept


def history(state, now):
    """Snapshot each agent's current-life record every 30 min → `hist` [{at, tally:{gen,right,med,n}, …}]. → new state."""
    st = dict(state or {})
    h = list(st.get('hist') or [])
    if h and now - _f(h[-1].get('at')) < HIST_EVERY:
        return st
    lr = learn(st, 5)
    h.append({'at': now, **{a: {'right': lr['cards'][a].get('right'), 'med': lr['cards'][a].get('med'), 'n': lr['cards'][a].get('n')} for a in ('tally', 'sherlock', 'trigger', 'devil')}})
    st['hist'] = h[-HIST_KEEP:]
    return st


def rules(learned):
    """📏 Each agent's ACTUAL rules right now — read from the constants and the live record, so the screen can never drift from the code."""
    lr = learned or {}
    rg = lr.get('regime') or {}
    return {
        'tally': [f"reads the {SERIES_N} latest prices of each coin it tracks (one a pass)", "5-min move = price now vs ~5 min ago on its own tape",
                  "pace = 5-min volume × 12 ÷ the hour's volume", "pool change vs the first reading", "scored on: does the 5-min move keep going?"],
        'sherlock': [f"each reason weighs (n × record + {BELIEF_K} × belief) ÷ (n + {BELIEF_K})", "strategies, sources and approved ideas start with NO belief",
                     f"{len(lr.get('drivers') or {})} reasons judged so far", "practice only: the live Sherlock is trench_kernel.brain.sherlock"],
        'trigger': [f"ENTER when the lean ≥ bar {_f(lr.get('bar') or 1.5)}{' ' + ('+' if _f(rg.get('adj')) >= 0 else '') + str(rg.get('adj')) + ' (' + str(rg.get('word')) + ' trench)' if rg.get('adj') else ''} and buyers ≥ 55%",
                    "SKIP a failed scan · a pool under $20K · a +15% 5-min candle · a −8% fall", "WAIT with under 3 readings", "losing → bar 2.5 · winning 60%+ → bar 1.0"],
        'devil': ["objects to: busted reads · rug meter ≥ 50 · +150% on the hour · under 15 min old · never scanned", "bot swarms · botted launches · burned coins (6h)",
                  f"reasons losing lately · approved avoid-tactics · rug signs seen in ≥ {RUG_SIGN_N} rugs", "Trigger's own losing streak"],
    }


def dial_replay(done, offsets=None):
    """🎚 DIAL LAB (owner-approved builds b7 + b9, 2026-10-13: "shadow-test a chill dial" · "raise Trigger's early-move threshold"): replay
    every judged call at each dial's bar shift — a call would have been ENTERED when its lean ≥ (its own bar at the time + the shift) —
    and read the 5-minute results of what each dial would have taken. → {dial: {n, med, up}, near, calls, words}. `near` = calls whose
    lean sat within the dial's reach of the bar (the only calls the dial can change). Uses the lean + bar every call already stores."""
    import re as _re
    import statistics as _st
    offs = offsets or {k: v for k, v in DIALS.items()}
    rows = []
    for c in done or []:
        m = _re.search(r'bar ([\d.]+)', str(c.get('tw') or ''))
        if m and c.get('lean') is not None and c.get('p5') is not None:
            rows.append((_f(c['lean']), float(m.group(1)), _f(c['p5'])))
    out = {}
    for k, off in offs.items():
        e = [p for l, b, p in rows if l >= b + off]
        out[k] = {'n': len(e), 'med': round(_st.median(e), 2) if e else None, 'up': round(100 * sum(1 for x in e if x > 0) / len(e)) if e else None}
    reach = max([abs(v) for v in offs.values()] or [0.5])
    near = sum(1 for l, b, _p in rows if abs(l - b) <= reach)
    ns = sorted({v['n'] for v in out.values()})
    words = (f"the dial moves Trigger's bar ±{reach:g} but leans spread far wider: of {len(rows)} judged calls only {near} sat that close to the bar — "
             f"every dial would have entered {ns[0]}–{ns[-1]} of them (5-min typical {', '.join(f"{k} {v['med']:+.1f}%" for k, v in out.items() if v['med'] is not None) or '—'}). "
             "The dial barely changes what the agents buy." if rows else 'no judged calls yet')
    return {**out, 'near': near, 'calls': len(rows), 'words': words}
