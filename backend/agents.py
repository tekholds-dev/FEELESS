"""🤖 THE AGENT DESK (pure, tested). Owner, 2026-10-09: "code your own agents to learn trading and trenching — 4 minimum: one tracks the
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

# 🕸 THE CRAWL: every place the desk pulls coins from each pass — each one is a driver `src:<key>` judged on its own record, so the agents
# learn which corner of the trench pays (owner: "access multiple ends to get info — only for trenching")
SOURCES = {'open': 'the open launch list', 'new': 'the newest launches (≤ 1h)', 'ptrend': 'Pump trending', 'calls': 'Pump callouts',
           'pump': 'Pump live', 'movers': 'movers', 'volume': 'volume leaders', 'fed': 'fed runners (paired launches)', 'wave': 'narrative leaders',
           'exhale': 'cooling-off coins', 'procall': 'proven callers', 'prebreak': 'before-the-break setups', 'double': 'double signal'}

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


def survival(state, h=5):
    """⚔ Each agent's life: generation, born, its record this life and its status — alive · probation (≥ 30 calls, under 45% right — Trigger:
    a losing median) · scrap (≥ 60 calls and still there)."""
    lr = learn(state, h)
    born, gen = (state or {}).get('born') or {}, (state or {}).get('gen') or {}
    out = {}
    for a in ('tally', 'sherlock', 'trigger', 'devil'):
        c = lr['cards'][a]
        n = int(c['n'] or 0)
        bad = (_f(c['med']) < 0 and _f(c['won']) < SURVIVE_RIGHT) if a == 'trigger' else (c['right'] is not None and _f(c['right']) < SURVIVE_RIGHT)
        status = 'scrap' if bad and n >= SCRAP_N else 'probation' if bad and n >= SURVIVE_N else 'alive'
        out[a] = {'gen': int(gen.get(a) or 1), 'born': _f(born.get(a)), 'n': n, 'right': c['right'], 'med': c['med'], 'status': status}
    return out


def second_opinion(state, agent, h=5):
    """⚖ Before an agent is scrapped, Devil reviews the life: if ONE call made up more than half of all its losses (one rug, not bad rules),
    the agent is spared ONCE this generation. → (spare, why)."""
    k = f'p{h}'
    born = _f(((state or {}).get('born') or {}).get(agent))
    js = [d for d in _judged(state, h) if _f(d.get('at')) >= born]
    if agent == 'trigger':
        js = [d for d in js if d.get('kind') == 'enter']
    losses = sorted((-_f(d[k]) for d in js if _f(d[k]) < 0), reverse=True)
    if not losses:
        return False, 'no losses to review'
    share = losses[0] / sum(losses)
    if share > 0.5:
        return True, f'one call was {round(share * 100)}% of its losses ({-losses[0]:.0f}%) — a rug, not bad rules'
    return False, f'the losses are spread over {len(losses)} calls — the rules are wrong'


def lesson(state, agent, h=5):
    """🧬 What killed an agent, for the next generation: Sherlock → the reasons whose real 5-min record was negative (they inherit it as their
    starting belief); Trigger → start 0.5 pickier per death (≤ +1.5); Tally / Devil → the worst-reading drivers of its life, as a note."""
    lr = learn(state, h)
    bad = sorted(((x, v['med'], v['n']) for x, v in lr['drivers'].items() if v['n'] >= 5 and v['med'] < 0), key=lambda t: t[1])[:6]
    prev = ((state or {}).get('lessons') or {}).get(agent) or {}
    out = {'drivers': [list(b) for b in bad], 'words': [f"{word(b[0])} ({b[1]:+.1f}%, n {b[2]})" for b in bad[:3]]}
    if agent == 'trigger':
        out['barBump'] = min(1.5, _f(prev.get('barBump')) + 0.5)
    return out


def evolve(state, now):
    """Scrap and rebirth: an agent whose status is 'scrap' gets a second opinion (spared ONCE per generation when one rug made most of its
    losses); otherwise it is reborn NOW (next generation, `born` = now) carrying the LESSON of what killed it; its last life goes to the
    lineage with the reason. → (new state, [scrapped agents])."""
    st = dict(state or {})
    sv = survival(st)
    dead, lines = [], []
    grace = dict(st.get('grace') or {})
    for a, v in sv.items():
        if v['status'] != 'scrap':
            continue
        spare, why_ = second_opinion(st, a)
        if spare and grace.get(a) != v['gen']:
            grace[a] = v['gen']
            lines.append({'at': now, 'who': 'devil', 'sym': '', 'text': f"⚖ second opinion on {a}: spared once — {why_}."})
            continue
        dead.append((a, v, why_))
    st['grace'] = grace
    if dead:
        born, gen, lin, les = dict(st.get('born') or {}), dict(st.get('gen') or {}), list(st.get('lineage') or []), dict(st.get('lessons') or {})
        for a, v, why_ in dead:
            les[a] = lesson(st, a)
            lin.append({'agent': a, 'gen': v['gen'], 'born': v['born'], 'died': now, 'n': v['n'], 'right': v['right'], 'med': v['med'], 'why': why_, 'lesson': les[a].get('words')})
            born[a], gen[a] = now, v['gen'] + 1
            lines.append({'at': now, 'who': a, 'sym': '', 'text': f"☠ scrapped after {v['n']} calls ({why_}) — reborn as generation {v['gen'] + 1}. I don't remember my last life. I carry what killed it: {', '.join(les[a].get('words') or ['nothing clear'])}."})
        st.update(born=born, gen=gen, lineage=lin[-40:], lessons=les)
    if lines:
        st['feed'] = (list(st.get('feed') or []) + lines)[-FEED_KEEP:]
    return st, [a for a, _, _ in dead]


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
           'paper': paper(state), 'life': survival(state)}
    md = [f"# 🤖 Agent desk — war log (last {hours}h)", '', f"- Calls judged at 5 min: **{len(js)}**",
          f"- GO calls: **{out['go']['n']}** · typical {out['go']['med']}% · {out['go']['won']}% up" if gos else '- GO calls: none judged',
          f"- Control (WAIT coins): typical {out['control']['med']}% · {out['control']['won']}% up" if ctl else '- Control: none judged',
          f"- Paper desk: ${out['paper']['now']:.2f} ({out['paper']['x']}× · best run {out['paper']['best']}× · {out['paper']['busts']} busts)", '',
          '## Agents', *[f"- {a}: gen {v['gen']} · {v['status']} · {v['n']} calls this life" + (f" · {v['right']}% right" if v['right'] is not None else '') for a, v in out['life'].items()],
          '', '## Deaths', *([f"- ☠ {x['agent']} gen {x['gen']} after {x['n']} calls — {x.get('why')} · lesson: {', '.join(x.get('lesson') or []) or '—'}" for x in deaths] or ['- none']),
          '', '## Best / worst GO', *[f"- ✅ ${s_} {p:+.1f}%" for s_, p in out['best']], *[f"- ❌ ${s_} {p:+.1f}%" for s_, p in out['worst']],
          '', '## Ideas', *([f"- [{x['status']}] {x['kind']}: {x['text']}" for x in out['ideas']] or ['- none yet']),
          '', '## Calibration (lean → 5-min result)', *[f"- lean {b_}: {v['n']} calls · {v['med']}% · {v['won']}% up" for b_, v in out['calibration'].items()],
          '', '_A record, never a promise._']
    return out, '\n'.join(md)


AGENTS = (('tally', '📊', 'Tally', 'tracks the numbers'), ('sherlock', '🔍', 'Sherlock', 'knows why they moved'),
          ('trigger', '⏱', 'Trigger', 'knows when to enter'), ('devil', '⚖', 'Devil', 'argues it is right — or not'))
STAGES = (5, 15, 60)            # minutes: conquer 5 first, then 15, then the hour
SERIES_N = 15                   # points kept per coin (one a pass, ~1 min apart)
SERIES_COINS = 160
KEEP_DONE = 3000
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
         'swarm': 'botted callout swarm', 'botted': 'botted launch', 'tug': 'dip tuggers catching a dump'}


def word(k):
    """Words for a driver key — a learned narrative driver reads as its label ('narr:ai' → 'the 🤖 AI narrative')."""
    if str(k).startswith('strat:'):
        return f"🎯 {STRAT_NAME.get(k[6:], k[6:])}"
    if str(k).startswith('src:'):
        return f"🕸 found on {SOURCES.get(k[4:], k[4:])}"
    if str(k).startswith('idea:'):
        return f"💡 approved tactic {k[5:]}"
    if str(k).startswith('narr:'):
        lab = (_tm.NARRATIVES.get(k[5:]) or (k[5:],))[0]
        return f'the {lab} narrative'
    return WORDS.get(k, k)
BUSTED = {'BOND RUN', 'EARLY RUSH', 'RUG BAIT', 'DUMPING', 'SLOW CURVE', 'BREAKOUT', 'FALLING KNIFE', 'WASH TRADED', 'BLOW-OFF TOP', 'DEAD DIP', 'TREND DOWN'}


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


def _med(xs):
    xs = sorted(xs); n = len(xs)
    return None if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


# ── 📊 TALLY ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def tally(state, rows, now):
    """Note this pass's numbers per coin (its own tape) → (series, nums{mint: numbers Tally reports})."""
    ser = {m: list(v) for m, v in ((state or {}).get('series') or {}).items()}
    nums = {}
    for r in rows or []:
        m, px = r.get('mint'), _f(r.get('price'))
        if not m or px <= 0:
            continue
        pt = {'t': now, 'px': px, 'v5': _f(r.get('vol5m')), 'v1': _f(r.get('vol1h')), 'b': r.get('buyShare'), 'liq': _f(r.get('liq')), 'h': r.get('holders')}
        s = (ser.get(m) or [])[-(SERIES_N - 1):] + [pt]
        ser[m] = s
        old = next((p for p in s if now - p['t'] >= 240), s[0])        # ~5 minutes back on Tally's own tape (else the oldest point)
        d5 = (px / old['px'] - 1) * 100 if old is not s[-1] and old['px'] > 0 else _f(r.get('chg5m'))
        pace = pt['v5'] * 12 / pt['v1'] if pt['v1'] > 0 else None
        liq0 = next((p['liq'] for p in s if p['liq'] > 0), 0.0)
        nums[m] = {'d5': round(d5, 2), 'c1': r.get('chg1h'), 'pace': None if pace is None else round(pace, 2), 'buy': r.get('buyShare'),
                   'liq': pt['liq'], 'liqD': round((pt['liq'] / liq0 - 1) * 100, 1) if liq0 > 0 and pt['liq'] > 0 else None,
                   'holdD': (_f(pt['h']) - _f(s[0].get('h'))) if pt['h'] is not None and s[0].get('h') is not None else None,
                   'age': r.get('ageH'), 'pts': len(s)}
    if len(ser) > SERIES_COINS:   # keep the most recently seen coins
        for m in sorted(ser, key=lambda k: ser[k][-1]['t'])[:len(ser) - SERIES_COINS]:
            ser.pop(m)
    return ser, nums


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
    out += list(((row.get('mind') or {}).get('drivers')) or [])   # 🧠 the human read: narrative, crowd vs swarm, botted, dip tuggers
    out += [f'strat:{k}' for k in strats(row, n)]                   # 🎯 the named meme strategies it fits
    out += [f'src:{k}' for k in (row.get('src') or [])]              # 🕸 where the crawl found it (each corner of the trench is judged)
    return [d for d in dict.fromkeys(out) if d]


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
)
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
    if 0 < _f(n.get('liq')) < 20_000:
        return 'skip', f"pool ${_f(n.get('liq')) / 1000:.0f}K — pullable"
    d5 = _f(n.get('d5'))
    if d5 > 15:
        return 'skip', f'+{d5:.0f}% in 5 min — that is the top'
    if d5 < -8:
        return 'skip', f'{d5:.0f}% in 5 min — falling'
    need = 5 if (learned or {}).get('trial') == 'tally' else 3   # 👨‍⚖️ Tally on trial: more readings before anyone may enter
    if int(n.get('pts') or 0) < need:
        return 'wait', f'Tally has under {need} readings of this coin yet'
    if why['lean'] >= bar and (n.get('buy') is None or _f(n['buy']) >= 55):
        return 'enter', f"lean {why['lean']:+.1f} ≥ bar {bar:.1f}: " + ', '.join(d[2] for d in why['drivers'][:2])
    return 'wait', f"lean {why['lean']:+.1f} under the bar {bar:.1f}"


# ── ⚖ DEVIL ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def devil(call, n, why, row, learned):
    """Argue against an ENTER. → (verdict 'agree' | 'object' | '—', the strongest argument). Its learned distrust: any driver of this call
    whose own 5-min record is negative, and Trigger's own record when it is losing."""
    if call != 'enter':
        return '—', ''
    n, row = n or {}, row or {}
    args = []
    rd = ((row.get('tv') or {}).get('call') or [None, None])[1]
    if rd in BUSTED:
        args.append(f'its read is {rd} — a busted call on its own record')
    if _f((row.get('tv') or {}).get('rug')) >= 50:
        args.append(f"rug meter {_f(row['tv']['rug']):.0f}")
    if n.get('c1') is not None and _f(n['c1']) > 150:
        args.append(f"already +{_f(n['c1']):.0f}% on the hour — it ran")
    if n.get('age') is not None and _f(n['age']) < 0.25:
        args.append('under 15 minutes old')
    if row.get('safe') is not True:
        args.append('holders never scanned')
    if row.get('mint') in ((learned or {}).get('burned') or {}):
        args.append('burned us within the last 6h — a GO on it lost 20%+ in 5 min')
    mind = row.get('mind') or {}
    if (mind.get('crowd') or {}).get('swarm'):
        args.append(f"the callers are a bot swarm ({round(_f(mind['crowd'].get('swarmShare')) * 100)}% the same line)")
    if _f((mind.get('bots') or (0, []))[0]) >= 40:
        args.append('botted launch: ' + '; '.join((mind['bots'][1] or [])[:2]))
    bad = [d for d in why['drivers'] if d[1] < 0]
    if bad:
        args.append('against it: ' + ', '.join(d[2] for d in bad[:2]))
    learned_d = (learned or {}).get('drivers') or {}
    for k, _w, words in why['drivers']:
        v = learned_d.get(k) or {}
        if int(v.get('n') or 0) >= DRIVER_MIN_N and _f(v.get('med')) < 0 and _f(_w) > 0:
            args.append(f"'{words}' has been followed by {_f(v['med']):+.1f}% lately")
    have_ = {d[0] for d in why['drivers']}
    rs_ = [x for x in have_ if ((learned or {}).get('rugSigns') or {}).get(x, 0) >= RUG_SIGN_N and not x.startswith('src:open')]
    if len(rs_) >= 2:   # 🔬 learned from autopsies: these reasons keep showing up on coins that rugged
        args.append('rug signs from our autopsies: ' + ', '.join(word(x) for x in rs_[:3]))
    for iid, pair in ((learned or {}).get('avoid') or {}).items():   # 🚫 a creator-approved AVOID tactic
        if all(x in have_ for x in pair):
            args.append(f"approved avoid-tactic {iid}: {word(pair[0])} + {word(pair[1])}")
    tr = ((learned or {}).get('cards') or {}).get('trigger') or {}
    if int(tr.get('n') or 0) >= 15 and _f(tr.get('med')) < 0:
        args.append(f"Trigger's last {tr['n']} calls: {_f(tr['med']):+.1f}% typical")
    return ('object', args[0]) if args else ('agree', 'no evidence against it')


# ── the chain ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def desk(state, rows, now, dial=None):
    """One pass of all four, in order. → (new state, table rows for the screen). Each coin's line carries every agent's word."""
    import time as _t
    st = dict(state or {})
    learned = learn(st, 5)   # 🧠 the live desk works from its OWN record every pass (it used to pass {} — learning only ever ran in tests)
    perf = {'tally': 0.0, 'sherlock': 0.0, 'trigger': 0.0, 'devil': 0.0}
    t0 = _t.perf_counter()
    ser, nums = tally(st, rows, now)
    perf['tally'] += _t.perf_counter() - t0
    st['series'] = ser
    learned['regime'] = regime(nums)
    learned['burned'] = {m: at for m, at in (st.get('burned') or {}).items() if now - _f(at) < BURN_SEC}
    learned['dial'] = dial if dial in DIALS else 'normal'
    learned['trial'] = judge(st)['trial']   # 👨‍⚖️ the bot the Judge has on trial plays under a handicap this pass (it only ever tightens)
    bar_ = bar_now(learned)
    table = []
    for r in rows or []:
        m = r.get('mint')
        if m not in nums:
            continue
        n = nums[m]
        t0 = _t.perf_counter(); why = sherlock(n, r, learned); perf['sherlock'] += _t.perf_counter() - t0
        if learned['trial'] == 'sherlock' and why['lean'] > 0:   # 👨‍⚖️ Sherlock on trial: its confidence is cut by a quarter
            why = {**why, 'lean': round(why['lean'] * TRIAL_LEAN, 2)}
        t0 = _t.perf_counter(); call, reason = trigger(n, why, r, learned); perf['trigger'] += _t.perf_counter() - t0
        t0 = _t.perf_counter(); verdict, arg = devil(call, n, why, {**r, 'mint': m}, learned); perf['devil'] += _t.perf_counter() - t0
        if learned['trial'] == 'devil' and verdict == 'agree' and why['lean'] < bar_ + TRIAL_BAR:   # 👨‍⚖️ Devil on trial: only strong reads pass
            verdict, arg = 'object', f"on trial — only a strong read passes (lean {why['lean']:+.1f} < {bar_ + TRIAL_BAR:.1f})"
        rd = r.get('mind') or _tm.read(r)
        table.append({'mint': m, 'symbol': r.get('symbol'), 'pair': r.get('pairAddress'), 'px': _f(r.get('price')), 'nums': n, 'why': why,
                      'trigger': [call, reason], 'devil': [verdict, arg], 'go': call == 'enter' and verdict == 'agree',
                      'mind': {'narr': rd['narr'][1], 'hot': rd['narr'][2], 'callers': rd['crowd']['callers'], 'swarm': rd['crowd']['swarm'],
                               'slang': rd['crowd']['slang'], 'bots': rd['bots'][0], 'tug': rd['tug'][0]},
                      'analysis': _tm.analysis(r.get('symbol'), rd, n, call, verdict, arg), 'opinion': opinion(why, call, verdict, arg),
                      'strats': [STRAT_NAME[k] for k in strats(r, n)],
                      'vitals': {k: r.get(k) for k in ('mcap', 'ageH', 'liq', 'vol1h', 'buyShare', 'top10', 'bundledN', 'snipersN', 'dev', 'holders', 'safe')}
                                | {'organic': (r.get('vital') or {}).get('organicPct'), 'rug': (r.get('tv') or {}).get('rug'), 'read': ((r.get('tv') or {}).get('call') or [None, None])[1]}})
    table.sort(key=lambda x: (not x['go'], x['trigger'][0] != 'enter', -x['why']['lean']))
    st['feed'] = (list(st.get('feed') or []) + thoughts(table, now))[-FEED_KEEP:]
    st['perf'] = {k: round(v * 1000, 2) for k, v in perf.items()} | {'coins': len(table), 'regime': learned['regime'], 'at': now, 'bar': bar_, 'dial': learned['dial'], 'trial': learned['trial']}   # ⚡ real ms per agent this pass
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
        opened[m] = {'px': x['px'], 'at': now, 'sym': x['symbol'], 'kind': kind, 'go': x['go'], 'devil': x['devil'][0],
                     'drivers': [d[0] for d in x['why']['drivers']], 'lean': x['why']['lean'], 'tallyUp': _f(x['nums'].get('d5')) > 0}
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
        for h in STAGES:
            key = f'p{h}'
            if key not in o and age >= h:
                o[key] = round((px / _f(o['px']) - 1) * 100, 2) if px > 0 and _f(o['px']) > 0 else (-100.0 if h == 60 else None)
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
    bar += _f((lessons.get('trigger') or {}).get('barBump'))   # a reborn Trigger starts pickier than the one that died
    cal = {}
    for d in enters_all:   # 🎯 calibration: does a stronger lean really win more?
        b_ = '0–1' if _f(d.get('lean')) < 1 else '1–2' if _f(d.get('lean')) < 2 else '2–3' if _f(d.get('lean')) < 3 else '3+'
        cal.setdefault(b_, []).append(_f(d[k]))
    calib = {b_: {'n': len(v), 'med': round(_med(v), 2), 'won': round(sum(1 for x in v if x > 0) / len(v) * 100)} for b_, v in sorted(cal.items())}
    budget = {x[4:]: v for x, v in drivers_.items() if x.startswith('src:') and v['n'] >= BUDGET_N and v['med'] < 0}
    ideas_ = (state or {}).get('ideas') or {}
    return {'drivers': drivers_, 'cards': cards, 'bar': round(bar, 2), 'h': h, 'calibration': calib, 'cut': budget,
            'lessons': lessons, 'rugSigns': (state or {}).get('rugSigns') or {},
            'approved': {i: v['pair'] for i, v in ideas_.items() if v.get('status') == 'approved' and v.get('kind') == 'take'},
            'avoid': {i: v['pair'] for i, v in ideas_.items() if v.get('status') == 'approved' and v.get('kind') == 'avoid'}}


def stage(state):
    """The timeframe the desk is on: 5 until it is conquered (team GO ≥ PROVE_N judged, median > 0, ≥ PROVE_WIN % won), then 15, then 60."""
    for h in STAGES:
        c = learn(state, h)['cards']['team']
        if h == 5 and not (paper(state)['x'] >= PROVE_X and int(c['n'] or 0) >= PROVE_N):   # 5 min: the trench desk must 10× in one run
            return {'h': h, 'conquered': [], 'team': c, 'needN': PROVE_N, 'needWin': PROVE_WIN, 'needX': PROVE_X}
        if h != 5 and not (int(c['n'] or 0) >= PROVE_N and _f(c['med']) > 0 and _f(c['won']) >= PROVE_WIN):
            return {'h': h, 'conquered': [x for x in STAGES if x < h], 'team': c, 'needN': PROVE_N, 'needWin': PROVE_WIN}
    return {'h': STAGES[-1], 'conquered': list(STAGES), 'team': learn(state, STAGES[-1])['cards']['team'], 'needN': PROVE_N, 'needWin': PROVE_WIN}


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
        pnl = stake * max(-100.0, _f(d['p5'])) / 100
        cash = round(cash + pnl, 4); run_trades += 1
        best = max(best, cash / DESK_START)
        trail.append({'at': d['at'], 'sym': d.get('sym'), 'pct': d['p5'], 'usd': round(pnl, 4), 'book': cash, 'stake': pct_})
        streak = (max(streak, 0) + 1) if _f(d['p5']) > 0 else (min(streak, 0) - 1)
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
            out.append({'at': now, 'who': 'desk', 'sym': o.get('sym'), 'text': f"{'✅' if ok else '❌'} ${o.get('sym')} {'GO' if o.get('go') else 'objected'} → {_f(o['p5']):+.1f}% after 5 min"
                        + ('' if o.get('go') else (' (Devil was right)' if not ok else ' (Devil was wrong)'))})
            r_ = ruling(o)
            if r_['verdict'] != 'push':
                out.append({'at': now, 'who': 'judge', 'sym': o.get('sym'), 'text': f"{'🏆' if r_['verdict'] == 'win' else '🔨'} ${o.get('sym')} {_f(o['p5']):+.1f}% — "
                            + (f"{NAME[r_['credit']]} called it" if r_.get('credit') else '') + (' · ' if r_.get('credit') and r_.get('blame') else '') + (f"{NAME[r_['blame']]} takes the L" if r_.get('blame') else '')})
    return out


def view(state, table, feed=False, real=None, mind=None, cfg=None, decisions=None, now=0.0, card=None):
    """What the HQ tab shows: the four agents with their scorecards, the live table (every agent's word per coin), the desk, the stage."""
    lr = learn(state, 5)
    st_ = stage(state)
    names = {a[0]: a for a in AGENTS}
    cards = [{'key': k, 'icon': names[k][1], 'name': names[k][2], 'job': names[k][3], **lr['cards'][k]} for k in ('tally', 'sherlock', 'trigger', 'devil')]
    proven = 5 in st_['conquered']
    return {'agents': cards, 'team': lr['cards']['team'], 'control': lr['cards']['control'], 'bar': lr['bar'], 'stage': st_, 'proven5': proven,
            'drivers': sorted(({'key': k, 'words': word(k), **v} for k, v in lr['drivers'].items()), key=lambda x: -_f(x['med'])),
            'table': table[:24], 'desk': paper(state), 'open': len((state or {}).get('open') or {}), 'feed': bool(feed and proven), 'feedAsked': bool(feed),
            'road': road(state, real), 'thoughts': list(reversed(((state or {}).get('feed') or [])[-40:])), 'real': real or {}, 'mind': mind or {},
            'ideas': sorted(({'id': i, **v} for i, v in ((state or {}).get('ideas') or {}).items()), key=lambda x: (x['status'] != 'new', -_f(x.get('at')))),
            'cfg': {'agentFeed': bool((cfg or {}).get('agentFeed')), 'agentLearn': bool((cfg or {}).get('agentLearn')), 'agentLearnPct': int(_f((cfg or {}).get('agentLearnPct') or 100)), 'agentTrust': bool((cfg or {}).get('agentTrust')), 'agentDial': (cfg or {}).get('agentDial') if (cfg or {}).get('agentDial') in DIALS else 'normal',
                    'agentTakePct': int(_f((cfg or {}).get('agentTakePct') or 10)), 'agentMode': (cfg or {}).get('agentMode') or 'auto',
                    'agentSeats': int(_f((cfg or {}).get('agentSeats') or 2)), 'options': {'take': list(AGENT_TAKES), 'mode': list(AGENT_MODES), 'seats': list(AGENT_SEATS)}},
            'decisions': decisions or [], 'tasks': tasks(state, table, now), 'creed': list(CREED), 'life': survival(state),
            'lineage': list(reversed(((state or {}).get('lineage') or [])[-10:])), 'approveN': IDEA_APPROVE_N,
            'perf': (state or {}).get('perf') or {}, 'lessons': (state or {}).get('lessons') or {}, 'calibration': lr['calibration'], 'cut': lr['cut'],
            'burned': len((state or {}).get('burned') or {}), 'scrapN': SCRAP_N, 'surviveN': SURVIVE_N,
            'autopsies': list(reversed(((state or {}).get('autopsies') or [])[-12:])), 'rugSigns': sorted(({'key': k, 'words': word(k), 'n': v} for k, v in ((state or {}).get('rugSigns') or {}).items()), key=lambda x: -x['n'])[:8],
            'growth': growth(state, lr), 'power': power(state, real, cfg, card), 'card': card or {},
            'judge': judge(state), 'proof': proof(state, real), 'barNow': ((state or {}).get('perf') or {}).get('bar') or lr['bar'],
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


def judge(state):
    """👨‍⚖️ The court's book: the last rulings, each bot's credit / blame / net, who is ON TRIAL (and its handicap), who wears the 👑."""
    js = sorted(_judged(state, 5), key=lambda d: _f(d.get('at')))
    ruled = [(d, ruling(d)) for d in js]
    ruled = [(d, r) for d, r in ruled if r['verdict'] != 'push'][-JUDGE_LAST:]
    score = {a: {'credit': 0, 'blame': 0, 'net': 0} for a in NAME}
    for _d, r in ruled:
        if r['verdict'] == 'miss':
            continue
        if r.get('credit'):
            score[r['credit']]['credit'] += 1
        if r.get('blame'):
            score[r['blame']]['blame'] += 1
    for v in score.values():
        v['net'] = v['credit'] - v['blame']
    worst = min(score, key=lambda a: (score[a]['net'], -score[a]['blame']))
    best = max(score, key=lambda a: (score[a]['net'], score[a]['credit']))
    trial = worst if score[worst]['net'] <= -JUDGE_NET else None
    mvp = best if score[best]['net'] >= JUDGE_NET and best != trial else None
    return {'rulings': [{'sym': d.get('sym'), 'mint': d.get('mint'), 'pct': d.get('p5'), 'at': d.get('at'), **r} for d, r in reversed(ruled[-14:])],
            'score': score, 'trial': trial, 'handicap': HANDICAP.get(trial), 'mvp': mvp, 'n': len(ruled), 'needNet': JUDGE_NET,
            'wins': sum(1 for _d, r in ruled if r['verdict'] == 'win'), 'losses': sum(1 for _d, r in ruled if r['verdict'] == 'loss'),
            'missed': sum(1 for _d, r in ruled if r['verdict'] == 'miss')}


def proof(state, real=None):
    """🏆 PROVE IT — wins and losses, not words: every GO the team made on paper (5-min result) and every coin that left a real seat the
    creator allowed (the card's own ledger). `last` = newest first, for the win / loss pips."""
    gos = sorted((d for d in _judged(state, 5) if d.get('go')), key=lambda d: _f(d.get('at')))
    ps = [_f(d['p5']) for d in gos]
    side = lambda pcts: {'n': len(pcts), 'w': sum(1 for x in pcts if x > 0), 'l': sum(1 for x in pcts if x <= 0),
                         'best': round(max(pcts), 1) if pcts else None, 'worst': round(min(pcts), 1) if pcts else None, 'last': [round(x, 1) for x in pcts[-16:]][::-1]}
    r = real or {}
    return {'paper': {**side(ps), 'syms': [d.get('sym') for d in gos[-16:]][::-1]}, 'card': side(list(r.get('last') or [])), 'suggested': side(list((r.get('suggested') or {}).get('last') or []))}


# ── 🧬 GROWTH — how an agent grows, and what the TEAM is allowed to hold on the creator's real card ─────────────────────────────────
# An agent grows only by SURVIVING judged calls: XP = calls judged this life. It levels up at the lines its life is already measured
# on (the probation line SURVIVE_N, the scrap line SCRAP_N) — and a level is only HELD while it is alive: on probation it is stunted
# back to a hatchling until its record recovers. `earned` = how much of its judgement is its OWN record instead of the belief it was
# born with. `genes` = lessons inherited from the life before it · `scars` = lives it lost · `skills` = tactics the creator approved.
TRUST_N = 10   # 🤝 suggestions the creator took and closed before a 2nd seat can be trusted (their typical result must be > 0)
LEVELS = ((0, '🥚', 'Egg'), (10, '🐣', 'Hatchling'), (SURVIVE_N, '🧒', 'Rookie'), (SCRAP_N, '🦾', 'Veteran'), (150, '🧠', 'Elder'), (400, '👑', 'Legend'))


def growth(state, learned=None):
    lr = learned or learn(state, 5)
    sv = survival(state)
    dr = lr.get('drivers') or {}
    lessons = (state or {}).get('lessons') or {}
    lineage = (state or {}).get('lineage') or []
    ideas_ = [v for v in ((state or {}).get('ideas') or {}).values() if v.get('status') == 'approved']
    out = {}
    for a, v in sv.items():
        n = int(v['n'] or 0)
        top = max(i for i, lv in enumerate(LEVELS) if n >= lv[0])
        stunted = v['status'] != 'alive' and top > 1
        i = 1 if stunted else top
        nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
        lo = LEVELS[i][0]
        earned = (sum(int(x.get('n') or 0) / (int(x.get('n') or 0) + BELIEF_K) for x in dr.values()) / len(dr) if dr else 0.0) if a == 'sherlock' else n / (n + SURVIVE_N)
        kind = 'take' if a == 'sherlock' else 'avoid' if a == 'devil' else None
        out[a] = {'level': i, 'icon': LEVELS[i][1], 'name': LEVELS[i][2], 'xp': n, 'next': nxt[0] if nxt else None, 'nextName': f'{nxt[1]} {nxt[2]}' if nxt else None,
                  'pct': 100 if not nxt else (0 if stunted else round(min(1.0, max(0.0, (n - lo) / max(1, nxt[0] - lo))) * 100)), 'stunted': stunted,
                  'earned': round(earned * 100), 'gen': v['gen'], 'status': v['status'], 'right': v['right'], 'med': v['med'],
                  'genes': list((lessons.get(a) or {}).get('words') or [])[:4], 'scars': sum(1 for x in lineage if x.get('agent') == a),
                  'skills': [' + '.join(word(k) for k in (x.get('pair') or [])) for x in ideas_ if x.get('kind') == kind][:4]}
    return out


def trusted(real):
    """🤝 Have the suggestions the creator took proven out? (≥ TRUST_N closed, typical result > 0)"""
    sg = (real or {}).get('suggested') or {}
    return int(sg.get('n') or 0) >= TRUST_N and _f(sg.get('med')) > 0


def seat_limit(cfg, proven, real):
    """How many coins the agents may hold on the real card RIGHT NOW — the one rule `_agents_go_rows` buys by:
    proven desk + feed on → `agentSeats` · else the 🎓 learning seat → 1 (2 once 🤝 trust is switched on AND earned) · else 0."""
    c = cfg or {}
    if c.get('agentFeed') and proven:
        return int(_f(c.get('agentSeats') or 2))
    if c.get('agentLearn'):
        return 2 if c.get('agentTrust') and trusted(real) else 1
    return 0


def power(state, real=None, cfg=None, card=None):
    """🪜 The team's power on the creator's card as three rungs — each with its real progress, nothing promised:
    🎓 learning seat (the creator's switch) → 🤝 trusted 2nd seat (their taken suggestions prove out) → 🏆 proven (paper 10× → `agentSeats`)."""
    c = cfg or {}
    rd = road(state, real)
    proven = rd['paper']['done']
    sg = (real or {}).get('suggested') or {}
    pp = rd['paper']
    held = sum(1 for x in ((card or {}).get('seats') or []) if x.get('kind') == 'agent')
    lim = seat_limit(c, proven, real)
    steps = [{'key': 'learn', 'icon': '🎓', 'seats': 1, 'on': bool(c.get('agentLearn')), 'done': bool(c.get('agentLearn')), 'pct': 100 if c.get('agentLearn') else 0, 'need': 'your switch'},
             {'key': 'trust', 'icon': '🤝', 'seats': 2, 'on': bool(c.get('agentTrust')), 'done': bool(c.get('agentLearn') and c.get('agentTrust') and trusted(real)),
              'pct': round(min(1.0, int(sg.get('n') or 0) / TRUST_N) * 100), 'need': f"{int(sg.get('n') or 0)}/{TRUST_N} closed" + (f" · {_f(sg.get('med')):+.1f}%" if sg.get('med') is not None else '')},
             {'key': 'proven', 'icon': '🏆', 'seats': int(_f(c.get('agentSeats') or 2)), 'on': bool(c.get('agentFeed')), 'done': bool(c.get('agentFeed') and proven),
              'pct': 100 if proven else round(min(1.0, max(0.0, __import__('math').log(max(pp['x'], 1.0)) / __import__('math').log(PROVE_X))) * 100), 'need': f"{pp['x']:.2f}× of {PROVE_X:g}× · {pp['n']}/{pp['needN']} calls"}]
    return {'seats': lim, 'held': held, 'steps': steps}


def card_seats(card, decisions=None, prices=None, cfg=None):
    """🎮 The creator's real card as SEATS, right now: who holds each one (🤖 the agents · 🤝 a coin they suggested and the creator took ·
    👤 the creator's own pick · ⚙ the engine · ▫ open), its live result since entry, and — for an agent seat — what they are doing with
    it (hold / pull / swap) and how far it is to their take line. Display only: nothing here buys or sells."""
    c = cfg or {}
    by = {x.get('pair'): x for x in decisions or []}
    take = _f(c.get('agentTakePct') or 10)
    seats = []
    for l in (card or {}).get('legs') or []:
        tag = str((l.get('bought') or {}).get('tag') or '')
        kind = 'open' if l.get('placeholder') else 'agent' if tag.startswith('🤖') else 'suggested' if tag.startswith('🤝') else 'yours' if l.get('picked') else 'engine'
        px, en = _f((prices or {}).get(l.get('pairAddress'))), _f(l.get('entry'))
        d = by.get(l.get('pairAddress')) or {}
        seats.append({'symbol': l.get('symbol'), 'pair': l.get('pairAddress'), 'mint': l.get('mint'), 'kind': kind, 'tag': tag, 'buying': bool(l.get('buying')),
                      'pct': round((px / en - 1) * 100, 1) if px > 0 and en > 0 and kind != 'open' else None,
                      'state': 'ride' if l.get('riding') else 'frozen' if l.get('frozen') else '', **({'take': take, 'action': d.get('action') or 'hold', 'why': d.get('why') or '', 'toSym': d.get('toSym')} if kind == 'agent' else {})})
    for _ in range(max(0, min(6, int(_f(c.get('coins')))) - len(seats))):
        seats.append({'kind': 'open', 'symbol': None, 'pct': None})
    return {'tpl': (card or {}).get('tpl'), 'seats': seats}


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


# ── 💵 AGENT SEATS on the real card — they stay until profit, then the agents decide ────────────────────────────────────────────────
AGENT_TAKES = (5, 10, 20, 30, 50)
DRAIN_PULL = 0.5   # an agent coin whose pool fell under half its entry depth is pulled at once
AGENT_MODES = ('auto', 'pull', 'swap')
AGENT_SEATS = (1, 2, 3, 4)


def is_agent(leg):
    return str(((leg or {}).get('bought') or {}).get('tag') or '').startswith('🤖')


def manage(legs, table, prices, cfg):
    """For every coin the agents put on the card: under `agentTakePct` profit it HOLDS (only the rug shield may cut it); in profit the agents
    read it again — still a clean read (Trigger not SKIP, lean ≥ 0, 5-min ≥ −3%, buyers ≥ 50%) → let it run; else EXIT: 'swap' for a fresh GO
    runner (mode auto / swap, when one exists off the card) or 'pull' to card cash with the seat left open. Not on the desk's list any more →
    pull (they can't see it, they bank it). → [{pair, symbol, action: hold | pull | swap, why, to}]"""
    take = _f((cfg or {}).get('agentTakePct') or 10)
    mode = (cfg or {}).get('agentMode') or 'auto'
    by = {x['mint']: x for x in table or []}
    on = {l.get('mint') for l in legs or []}
    gos = [x for x in table or [] if x.get('go') and x['mint'] not in on]
    out = []
    for l in legs or []:
        if not is_agent(l) or l.get('placeholder') or l.get('buying') or _f(l.get('units')) <= 0 or _f(l.get('entry')) <= 0:
            continue
        px = _f((prices or {}).get(l.get('pairAddress')))
        if px <= 0:
            continue
        pnl = (px / _f(l['entry']) - 1) * 100
        lq0, lq1 = _f(l.get('liq')), _f(l.get('liqNow'))
        if lq0 > 0 and 0 < lq1 < lq0 * DRAIN_PULL:   # 🩸 the pool is draining: out NOW, profit or not (a drained pool cannot be sold later)
            out.append({'pair': l['pairAddress'], 'symbol': l.get('symbol'), 'action': 'pull', 'why': f"{pnl:+.1f}% — pool fell to {round(lq1 / lq0 * 100)}% of entry depth: out now, before it can't be sold"}); continue
        if pnl < take:
            out.append({'pair': l['pairAddress'], 'symbol': l.get('symbol'), 'action': 'hold', 'why': f'{pnl:+.1f}% — holding until +{take:g}% (only the rug shield cuts it)'}); continue
        x = by.get(l.get('mint'))
        if x:
            n = x['nums']
            bad = (x['trigger'][0] == 'skip' and x['trigger'][1]) or (x['why']['lean'] < 0 and f"lean turned {x['why']['lean']:+.1f}") \
                or (_f(n.get('d5')) <= -3 and f"{_f(n['d5']):+.1f}% in 5 min") or (n.get('buy') is not None and _f(n['buy']) < 50 and f"buyers down to {_f(n['buy']):.0f}%")
            if not bad:
                out.append({'pair': l['pairAddress'], 'symbol': l.get('symbol'), 'action': 'hold', 'why': f"{pnl:+.1f}% and still clean (lean {x['why']['lean']:+.1f}, {_f(n.get('d5')):+.1f}% 5m) — let it run"}); continue
        else:
            bad = 'off the desk\'s radar — bank it'
        if mode in ('auto', 'swap') and gos:
            out.append({'pair': l['pairAddress'], 'symbol': l.get('symbol'), 'action': 'swap', 'why': f"{pnl:+.1f}%, {bad} → swap for ${gos[0]['symbol']}", 'to': gos[0]})
            gos = gos[1:]
        elif mode in ('auto', 'pull') or not gos:
            out.append({'pair': l['pairAddress'], 'symbol': l.get('symbol'), 'action': 'pull', 'why': f"{pnl:+.1f}%, {bad} → profit to cash, seat left open"})
    return out


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
            'devil': f"objected to {obj} of {len(enters)} entries" + (f" · {len((state or {}).get('open') or {})} calls waiting on the clock" if state else ''),
            'at': now}


# ── 🔬 RUG AUTOPSY — every coin that rugged on the desk teaches Devil ─────────────────────────────────────────────────────────────────
RUG_P5, RUG_SIGN_N = -50.0, 3


def autopsy(state, now):
    """Every judged call that rugged (≤ −50% at 5 min, or no price at 60 min = vanished) gets an autopsy: the reasons the desk saw at the time
    (its drivers) and what it MISSED (the reasons it weighed positive). Each driver seen in a rug is counted in `rugSigns`; Devil objects to a
    coin carrying 2+ signs that each showed up in ≥ 3 rugs. → new state (autopsies kept 60, newest last)."""
    st = dict(state or {})
    done_ids = {a['id'] for a in st.get('autopsies') or []}
    signs = dict(st.get('rugSigns') or {})
    aut = list(st.get('autopsies') or [])
    for d in list((st.get('open') or {}).values()) + list(st.get('done') or []):
        p5, p60 = d.get('p5'), d.get('p60')
        rug = (p5 is not None and _f(p5) <= RUG_P5) or (p60 is not None and _f(p60) <= -100)
        did = f"{d.get('mint')}:{int(_f(d.get('at')))}"
        if not rug or did in done_ids:
            continue
        drv = list(d.get('drivers') or [])
        for x in drv:
            signs[x] = signs.get(x, 0) + 1
        aut.append({'id': did, 'sym': d.get('sym'), 'at': now, 'calledAt': d.get('at'), 'kind': d.get('kind'), 'go': bool(d.get('go')),
                    'p5': p5, 'p60': p60, 'seen': drv, 'missed': [x for x in drv if PRIOR.get(x, 0.0) >= 0 and not x.startswith('src:')][:4],
                    'text': f"${d.get('sym')} rugged ({_f(p5):+.0f}% in 5 min{'' if p60 is None else f', {_f(p60):+.0f}% in 60'})"
                            + (" after a GO" if d.get('go') else '') + (f" — we read it as: {', '.join(word(x) for x in drv[:3])}" if drv else '')})
    st['autopsies'], st['rugSigns'] = aut[-60:], signs
    return st


def rug_signs(row_drivers, state):
    """The rug signs a coin carries right now: its drivers that have each shown up in ≥ RUG_SIGN_N rugs."""
    sg = (state or {}).get('rugSigns') or {}
    return [x for x in row_drivers or [] if sg.get(x, 0) >= RUG_SIGN_N and not x.startswith('src:open')]


# ── 📈 DESK HISTORY — each agent's record over time, per generation ─────────────────────────────────────────────────────────────────
HIST_EVERY, HIST_KEEP = 1800.0, 336   # a snapshot every 30 min, a week kept


def history(state, now):
    """Snapshot each agent's current-life record every 30 min → `hist` [{at, tally:{gen,right,med,n}, …}]. → new state."""
    st = dict(state or {})
    h = list(st.get('hist') or [])
    if h and now - _f(h[-1].get('at')) < HIST_EVERY:
        return st
    sv = survival(st)
    h.append({'at': now, **{a: {'gen': v['gen'], 'right': v['right'], 'med': v['med'], 'n': v['n']} for a, v in sv.items()}})
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
                     f"{len(lr.get('drivers') or {})} reasons judged so far", "a reborn Sherlock starts from the reasons that killed the last one"],
        'trigger': [f"ENTER when the lean ≥ bar {_f(lr.get('bar') or 1.5)}{' ' + ('+' if _f(rg.get('adj')) >= 0 else '') + str(rg.get('adj')) + ' (' + str(rg.get('word')) + ' trench)' if rg.get('adj') else ''} and buyers ≥ 55%",
                    "SKIP a failed scan · a pool under $20K · a +15% 5-min candle · a −8% fall", "WAIT with under 3 readings", "losing → bar 2.5 · winning 60%+ → bar 1.0"],
        'devil': ["objects to: busted reads · rug meter ≥ 50 · +150% on the hour · under 15 min old · never scanned", "bot swarms · botted launches · burned coins (6h)",
                  f"reasons losing lately · approved avoid-tactics · rug signs seen in ≥ {RUG_SIGN_N} rugs", "Trigger's own losing streak"],
    }
