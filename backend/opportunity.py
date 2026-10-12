"""🎯 OPPORTUNITY: RANK, DON'T VETO (owner, 2026-10-11: "make them more decisive without removing hard safety").

Every coin the desk read goes through ONE hard-safety check (`hard_fail`): a genuine danger is a NO. Everything else is a SCORE 0–100 from
cited parts (momentum, acceleration, structure, liquidity, holders, volume, freshness, identity, data) minus penalties (chop, extension,
thin pool, stale data, identity doubt, weak holders, a failed setup, Devil's warnings) → a TIER:
  A (≥ 65) full Warden size · B (50–65) 75% · C (40–50) 50% · below 40 = REJECT (no seat — cash beats a bad setup).
The seats choose the best AVAILABLE valid opportunity instead of waiting for a perfect coin. A ranking, never a promise. Pure, tested."""

TIER_A, TIER_B, TIER_C = 65.0, 50.0, 40.0   # 🎯 C needs 40 now (was 25): below it is a REJECT — cash beats a clearly bad setup (owner, 2026-10-11)
TIER_STOP = {'A': 25.0, 'B': 18.0, 'C': 12.0}   # 🛑 the stop CEILING per tier (Reaper): 6h on the real card — 9 'bought into a fall' losses at −23…−37% were 3/4 of all the loss
TIER_SIZE = {'A': 1.0, 'B': 0.75, 'C': 0.5}   # on the Warden's own steps (1 · .75 · .5 · .25): B = 75% of a seat, C = 50%
MAX_MCAP = 200_000.0             # 🎯 the hard universe for NEW entries: live market cap under $200K (owner's spec, 2026-10-11) — mirrors agents.AGENT_MAX_MCAP
MIN_LIQ = 8_000.0                # mirrors agents.CONTROL_MIN_LIQ (a test keeps them equal) = the keeper's trench floor
FALL_HARD = -8.0                 # ≤ −8% in 5 min = falling NOW: NO (2026-10-12: $Squeeze C-tier 'falling −20' stopped −38% a minute later, $STRKT too)
VERTICAL = 40.0                  # +40% in 5 min = buying a vertical candle: NO · +15…+40 on a young coin is a penalty
HARD_DEVIL = ('rug_meter', 'burned', 'rug_signs', 'avoid', 'data_integrity', 'chart_bot_ladder', 'unscanned', 'busted_read')   # busted_read reaches Devil's VETO list only at hard severity (≤ −50% typical)
HARD_CHART = ('DATA INVALID', 'BOT LADDER', 'LIQUIDITY FAILURE')
GOOD = {'UPTREND': 18, 'PULLBACK IN UPTREND': 16, 'CONFIRMED BREAKOUT': 14, 'BREAKOUT ATTEMPT': 8, 'EARLY': 6, 'ACCUMULATION': 6, 'COMPRESSION': 4,
        'RANGE': 0, 'UNKNOWN': 0, 'PARABOLIC': -8, 'CHOP': -12, 'FAILED BREAKOUT': -14, 'DOWNTREND': -18}


def _f(v):
    try:
        x = float(v)
        return x if x == x else 0.0
    except (TypeError, ValueError):
        return 0.0


# 🆕 FRESHNESS LADDER (owner's trench-desk spec, 2026-10-12): the NEW-ENTRY universe is ≤ 6h old — 0–5m extreme · 5–15m very high ·
# 15–60m high · 1–3h medium-high · 3–6h medium. Older = no new autonomous entry (`hard_fail`); held winners keep running.
FRESH_LADDER = ((5 / 60, 'EXTREME 0–5m', 18), (0.25, 'VERY HIGH 5–15m', 15), (1.0, 'HIGH 15–60m', 12), (3.0, 'MEDIUM-HIGH 1–3h', 8), (6.0, 'MEDIUM 3–6h', 4))
MAX_AGE_H = 6.0                   # 🚫 a coin older than this (or of unknown age) never gets a NEW autonomous entry
OLD_H, OLD_PTS = 6.0, -10
YOUNG_VERTICAL = 100.0            # a coin under 15 min: its "5-min move" is mostly launch → now — only +100% in 5 min is a vertical candle


def age_min(row):
    v = (row or {}).get('vitals') or row or {}
    h = v.get('ageH')
    return None if h is None else _f(h) * 60


def reawake(row):
    """An old coin re-entering the action: volume pace ≥ 2× its hour on ≥ $3K in 5 min."""
    n = (row or {}).get('nums') or {}
    return _f(n.get('pace')) >= 2 and _f(n.get('v5')) >= 3000


def fresh_bucket(row):
    """→ (label, points). Age is the launch's, from the pool's creation; unknown age = no points."""
    am = age_min(row)
    if am is None:
        return None, 0
    for h, label, pts in FRESH_LADDER:
        if am < h * 60:
            return label, pts
    return ('6h+ no new entry', OLD_PTS)


def velocity(row):
    """🌊 Volume and buyer VELOCITY ($ / min, buys / min), normalised by the coin's own life: a 3-minute-old coin with $20K is judged on
    $20K / 3 min, not against an hour it has not lived. → (vol per min, buys per min) — None where the board has no reading."""
    x = row or {}
    v, n = x.get('vitals') or {}, x.get('nums') or {}
    am = age_min(x)
    life = max(1.0, min(60.0, am)) if am is not None else 60.0
    v5 = n.get('v5')
    vpm = (_f(v5) / 5.0) if v5 is not None and (am is None or am >= 5) else (_f(v.get('vol1h')) / life if v.get('vol1h') is not None else None)
    tx, buy = v.get('txns1h'), n.get('buy') if n.get('buy') is not None else v.get('buyShare')
    bpm = (_f(tx) * _f(buy) / 100.0 / life) if tx is not None and buy is not None else None
    return (None if vpm is None else round(vpm, 1)), (None if bpm is None else round(bpm, 2))


DEAD_5M_USD = 300.0     # 💀 under $300 traded in the last 5 min = nobody is trading it now …
DEAD_PACE, DEAD_PACE_USD = 0.2, 1500.0   # … or the 5 min ran under a fifth of the hour's pace with under $1.5K in it (the hour's volume is gone)


def dead_now(row):
    """💀 None = people are trading it NOW, else why it is dead. Reads Tally's 5-min $ (`nums.v5`) and pace; no reading = not judged.
    A dead coin can't go anywhere and can't be sold well either — it never takes a seat, and a held one gives its seat away."""
    n = (row or {}).get('nums') or {}
    if n.get('v5') is None:
        return None
    v5, pace = _f(n['v5']), n.get('pace')
    if v5 < DEAD_5M_USD:
        return f'dead — ${v5:,.0f} traded in the last 5 min'
    if pace is not None and _f(pace) < DEAD_PACE and v5 < DEAD_PACE_USD:
        return f'dead — 5-min volume ${v5:,.0f} is {_f(pace):.2f}× the hour\'s pace'
    return None


def hard_fail(row, mcap_cap=MAX_MCAP, min_liq=MIN_LIQ):
    """The ONLY reasons a coin is a NO: holder scan failed / never read (no holder safety at all) · a pool under the floor (a pull or no
    exit) · market cap ≥ the cap · rug meter ≥ 50 · a hard Devil rule (rug signs, burned us, an approved avoid, bad data, a bot ladder) ·
    a broken chart (invalid data, a bot ladder, a liquidity failure) · a vertical +40% / a −15% 5-min candle · no price. → reason or None."""
    x = row or {}
    v, n, ch = x.get('vitals') or {}, x.get('nums') or {}, x.get('chart') or {}
    if _f(x.get('px')) <= 0:
        return 'no live price'
    dead = dead_now(x)
    if dead:
        return dead
    if v.get('safe') is False:
        return 'failed the holder safety scan'
    if v.get('safe') is not True:
        return 'holders not read yet'
    if v.get('mcap') is None or _f(v['mcap']) <= 0:   # 🎯 unknown cap is not eligible until it is resolved
        return 'market cap unknown'
    if _f(v['mcap']) >= mcap_cap:
        return f"market cap ${_f(v['mcap']) / 1e3:.0f}K ≥ ${mcap_cap / 1e3:.0f}K"
    if v.get('ageH') is None:   # 🕐 unknown age never masquerades as fresh
        return 'launch age unknown'
    if _f(v['ageH']) > MAX_AGE_H:
        return f"{_f(v['ageH']):.1f}h old — no new entry past {MAX_AGE_H:g}h"
    liq = _f(n.get('liq') or v.get('liq'))
    if liq < min_liq:
        return f'pool ${liq / 1000:.0f}K under ${min_liq / 1000:.0f}K'
    if _f(v.get('rug')) >= 50:
        return f"rug meter {_f(v['rug']):.0f}"
    hd = [o[0] for o in x.get('objs') or [] if o and o[0] in HARD_DEVIL] + ([x['drule']] if x.get('drule') in HARD_DEVIL else [])
    if hd:
        return f'Devil hard veto: {hd[0]}'
    li = x.get('li') or {}
    if x.get('mp') in ('DISTRIBUTION', 'COLLAPSE'):   # 📈 the live chart's trench phase: never a new entry into distribution / a collapse
        return f"chart phase {x['mp']}"
    if li.get('phase') == 'DISTRIBUTION':   # 🕵 exit-liquidity FOMO: up big while the early wallets sell into it — we would be their exit
        return 'distribution — ' + '; '.join((li.get('phaseWhy') or [])[:2])
    if li.get('press') == 'HIGH':
        return 'early wallets unloading — ' + str(li.get('pressWhy'))
    if ch.get('state') in HARD_CHART:
        return f"chart {ch['state']}"
    d5 = _f(n.get('d5'))
    am_ = age_min(x)
    if d5 > (YOUNG_VERTICAL if am_ is not None and am_ < 15 else VERTICAL):   # 🆕 acceleration, not launch → now: a newborn's 5-min move is mostly its launch
        return f'+{d5:.0f}% in 5 min — a vertical candle'
    if d5 < FALL_HARD:
        return f'{d5:.0f}% in 5 min — a knife'
    return None


def judge_hits(row, pens):
    """👨‍⚖️ The Judge's PROMOTED rules that match this coin → [(words, points)] (bounded ranking penalties, never a veto)."""
    x = row or {}
    v, n, ch = x.get('vitals') or {}, x.get('nums') or {}, x.get('chart') or {}
    test = {'thin pool': lambda: 0 < _f(n.get('liq') or v.get('liq')) < 20_000, 'falling now': lambda: _f(n.get('d5')) < -3,
            'chart says wait': lambda: (ch.get('entry') or [None])[0] not in (None, 'ENTER NOW'), 'weak holders': lambda: _f(v.get('top10')) >= 30,
            'thin data': lambda: (ch.get('q') or {}).get('state') in ('SPARSE', 'NO_REAL_CANDLES', 'STALE'),
            'early selling': lambda: (x.get('li') or {}).get('press') in ('WATCH', 'HIGH'), 'crowd fomo': lambda: (x.get('li') or {}).get('phase') == 'CROWD FOMO',
            'bundled': lambda: (x.get('li') or {}).get('cls') in ('BUNDLED', 'INSIDER-LIKE CLUSTER')}
    return [(f'judge: {k}', _f(p)) for k, p in (pens or {}).items() if k in test and test[k]()]


def score(row, lost=(), meta=None, pens=None):
    """0–100 with its parts [(name, points)]. Base 50; each part is a reading of THIS pass (never a promise)."""
    x = row or {}
    v, n, ch = x.get('vitals') or {}, x.get('nums') or {}, x.get('chart') or {}
    f = ch.get('f') or {}
    parts = []
    add = lambda k, p: parts.append((k, round(p, 1))) if p else None
    d5, age, liq = _f(n.get('d5')), v.get('ageH'), _f(n.get('liq') or v.get('liq'))
    young = age is not None and _f(age) < 6
    add('momentum', max(-12, min(12, d5 * 1.5)) if -8 <= d5 <= 15 else 0)
    if d5 > 15:
        add('hot candle', -10 if young else -22)           # a young launch moves fast; a mature +15% candle is the top
    if d5 < -8:
        add('falling', -20)
    pace = _f(x.get('pace') or n.get('pace'))
    if pace:
        add('acceleration', max(-6, min(10, (pace - 1) * 6)))
    add('structure', GOOD.get(ch.get('state'), 0))
    if _f(ch.get('ext')) >= 75 and not young:
        add('extended', -8)
    add('liquidity', 4 if liq >= 20_000 else 1 if liq >= 12_000 else -4)   # 🆕 a deep pool is SAFETY, not an edge — it used to hand old coins +10
    t10 = v.get('top10')
    if t10 is not None:
        add('holders', 6 if _f(t10) < 20 else 0 if _f(t10) < 30 else -8)
    fb, fpts = fresh_bucket(x)
    if fb:
        add(f'freshness {fb}', fpts)
    vpm, bpm = velocity(x)
    if vpm is not None:   # 🌊 volume VELOCITY ($/min over the coin's own life): $100/min = 0 · $1K/min +8 · $5K/min +12
        import math
        add('volume velocity', max(-6.0, min(12.0, (math.log10(max(vpm, 1.0)) - 2.0) * 8.0)))
    if bpm is not None:
        add('buyer velocity', max(-4.0, min(8.0, (bpm - 1.0) * 2.0)))
    buy = n.get('buy')
    if buy is not None:
        add('buyers', max(-8, min(6, (_f(buy) - 52) * 0.6)))
    if x.get('social') or v.get('site') or v.get('x'):
        add('identity', 3)
    q = (ch.get('q') or {}).get('state')
    young_ = age is not None and _f(age) * 60 < 30
    add('data', 4 if q in ('TRUSTED', 'USABLE_WITH_CAUTION') else -6 if q == 'STALE' or (q in ('SPARSE', 'NO_REAL_CANDLES') and not young_) else 0)   # 🆕 a coin minutes old CAN'T have a long chart: judged by its stage
    if (meta or {}).get('verdict') == 'ORGANIC':
        add('organic tape', 8)
    elif (meta or {}).get('verdict') in ('BOT', 'ONE WALLET', 'DUMPING'):
        add(f"tape {meta['verdict'].lower()}", -25)
    lean = _f((x.get('why') or {}).get('lean'))
    add("agents' read", max(-10, min(10, lean * 3)))
    for w in x.get('warns') or []:
        k = (w or [None])[0]
        add(f'warning: {k}', -10 if k in ('busted_read', 'ran', 'identity') else -4)
    if x.get('mint') in (lost or ()):
        add('failed setup lately', -12)
    mc_ = _f(v.get('mcap'))
    if 0 < mc_ < MAX_MCAP:
        add('trench band (< $200K)', 6)   # the owner's own universe ranks first; the wider lane only fills what it cannot
    li = x.get('li') or {}
    pp = li.get('pump')
    if pp:   # 🎢 the Pump entry phase: early acceleration / first pullback / reclaim / healthy breakout preferred; late FOMO avoided
        add(f'pump {pp.lower()}', {'EARLY ACCELERATION': 8, 'FIRST PULLBACK': 8, 'RECLAIM': 7, 'BREAKOUT': 5, 'DISCOVERY': 2, 'RUNNING': 0, 'LATE FOMO': -12}.get(pp, 0))
    mp = x.get('mp')   # 📈 the live chart's TRENCH PHASE (market_wake.PHASES): prefer the early ones, avoid the late ones
    if mp:
        add(f'chart {mp.lower()}', {'EARLY ACCELERATION': 6, 'FIRST PULLBACK': 6, 'RECLAIM': 6, 'BREAKOUT': 4, 'DISCOVERY': 0, 'RUNNING': 0, 'LATE FOMO': -15, 'REVERSAL': -10}.get(mp, 0))
    ewp = li.get('ewp')
    if ewp:
        add(f'early wallets {ewp.lower()}', {'POSITIVE': 5, 'NEUTRAL': 0, 'WARNING': -6, 'DUMPING': -14}.get(ewp, 0))
    ph = li.get('phase')
    if ph in ('EARLY FOMO', 'ACCELERATING'):   # 🕵 enter early / accelerating, never the crowd's top
        add(f'phase {ph.lower()}' + ('' if li.get('healthy') is not False else ' (unhealthy)'), (8 if ph == 'ACCELERATING' else 6) if li.get('healthy') is not False else 0)
    elif ph == 'CROWD FOMO':
        add('crowd fomo (late)', -10 if li.get('healthy') is False else -6)
    if li.get('press') == 'WATCH':
        add('an early wallet is selling', -5)
    if _f(li.get('danger')):
        add('early wallets with a dump / rug record', -min(12, 6 * _f(li['danger'])))
    rec = li.get('clsRec') or {}
    if _f(rec.get('n')) >= 20:   # the launch class's OWN settled record decides whether bundled / sniped launches rank lower — never assumed
        add(f"{str(li.get('cls')).lower()} record", max(-10, min(6, _f(rec.get('med')) / 5)))
    if x.get('go'):
        add('GO (all four agree)', 15)
    for k, p in judge_hits(x, pens):
        add(k, p)
    total = max(0.0, min(100.0, 50 + sum(p for _k, p in parts)))
    return round(total, 1), parts


def tier_of_tag(tag):
    """'🤖 agents · B-tier' → 'B' (the tier a seat was bought on), else None."""
    t = str(tag or '')
    return t.split('-tier')[0][-1] if '-tier' in t and t.split('-tier')[0][-1:] in ('A', 'B', 'C') else None


def tier_of(s):
    return 'A' if s >= TIER_A else 'B' if s >= TIER_B else 'C' if s >= TIER_C else None


def rank(table, skip=(), lost=(), metas=None, stats=None, pens=None, cap=MAX_MCAP):
    """Every coin of the pass → hard NO, or a scored + tiered candidate (best first). `stats` (dict) collects the counts the page shows."""
    out, st = [], stats if stats is not None else {}
    st.update({'considered': 0, 'hard': 0, 'hardWhy': {}, 'warned': 0, 'A': 0, 'B': 0, 'C': 0, 'weak': 0})
    for x in table or []:
        m = x.get('mint')
        if not m or m in skip:
            continue
        st['considered'] += 1
        why = hard_fail(x, cap)
        if why:
            st['hard'] += 1
            k = why.split(' —')[0].split(' $')[0][:40]
            st['hardWhy'][k] = st['hardWhy'].get(k, 0) + 1
            continue
        if x.get('warns'):
            st['warned'] += 1
        s, parts = score(x, lost, (metas or {}).get(x.get('pair')), pens)
        t = tier_of(s)
        if not t:
            st['weak'] += 1
            continue
        st[t] += 1
        top = sorted(parts, key=lambda p: -abs(p[1]))[:3]
        out.append({**x, 'opp': s, 'oppRaw': round(50 + sum(p for _k, p in parts), 1), 'tier': t, 'oppParts': parts,   # raw = the order (a strong coin passes 100: a cap would tie them)
                    'nearReady': f"{t}-tier {s:.0f}/100 — " + ' · '.join(f"{k} {p:+.0f}" for k, p in top)})
    return sorted(out, key=lambda r: -r['oppRaw'])


# ── ⚡ OPEN MODE = TRUE TRENCHING (owner, 2026-10-12: "no reputation theater — newness, volume, buyers, liquidity, the live chart / tape,
# early wallets, momentum; the agents build their OWN live narrative"). Pure + tested (tests/test_trench_open.py).
NARRATIVES = ('HOT EARLY MOVE', 'BUILDING', 'BREAKOUT', 'RUNNING', 'STALLING', 'DISTRIBUTING', 'COLLAPSING')
SKIP_NARRATIVES = ('DISTRIBUTING', 'COLLAPSING')
OPEN_FRESH = ((5 / 60, 1.5), (0.25, 1.35), (1.0, 1.2), (3.0, 1.0), (6.0, 0.8))   # newness factor by age (h)


def narrative(row):
    """The coin's LIVE narrative from facts of THIS pass only (5-min move · volume pace · buyers · pool change · live chart phase · early
    wallets) — nothing inherited from old records. → (narrative, why)."""
    x = row or {}
    n, v, li = x.get('nums') or {}, x.get('vitals') or {}, x.get('li') or {}
    d5, pace, buy = _f(n.get('d5')), _f(n.get('pace') or x.get('pace')), n.get('buy')
    mp, ewp, lq = x.get('mp'), li.get('ewp'), n.get('liqD')
    age = v.get('ageH')
    if d5 <= -15 or mp == 'COLLAPSE' or (lq is not None and _f(lq) <= -40):
        return 'COLLAPSING', f"{d5:+.0f}% in 5 min" + (f", pool {_f(lq):+.0f}%" if lq is not None else '') + (f", chart {mp.lower()}" if mp else '')
    if ewp == 'DUMPING' or mp == 'DISTRIBUTION' or (d5 > 0 and buy is not None and _f(buy) < 45):
        return 'DISTRIBUTING', 'early wallets dumping' if ewp == 'DUMPING' else f"price up on {_f(buy):.0f}% buyers" if buy is not None and d5 > 0 else 'chart distribution'
    if age is not None and _f(age) < 0.25 and d5 > 0 and pace >= 1.5:
        return 'HOT EARLY MOVE', f"{_f(age) * 60:.0f} min old, {d5:+.0f}% on {pace:.1f}× volume pace"
    if mp == 'BREAKOUT' or mp == 'RECLAIM':
        return 'BREAKOUT', f"live chart {mp.lower()}"
    if d5 > 0 and (buy is None or _f(buy) >= 55) and pace >= 1.0:
        return 'RUNNING', f"{d5:+.1f}% on rising volume, buyers {_f(buy):.0f}%" if buy is not None else f"{d5:+.1f}% on rising volume"
    if abs(d5) < 1 and pace < 1.0:
        return 'STALLING', f"{d5:+.1f}% and volume slowing ({pace:.1f}×)"
    return 'BUILDING', f"{d5:+.1f}% in 5 min, volume pace {pace:.1f}×"


def open_score(row, weights=None, devil_strong=None):
    """NEWNESS × VOLUME VELOCITY × BUYER VELOCITY × LIVE MOMENTUM × early wallets (× the Judge's evidence weight when it has one).
    No holder, rug, creator, source or history part. → (score 0–~250, parts)."""
    import math
    x = row or {}
    n, v, li = x.get('nums') or {}, x.get('vitals') or {}, x.get('li') or {}
    age = v.get('ageH')
    f_new = next((m for h, m in OPEN_FRESH if age is not None and _f(age) < h), 0.5)
    vpm, bpm = velocity(x)
    f_vol = max(0.3, min(2.0, 0.4 + (math.log10(max(_f(vpm), 1.0)) * 0.35)))          # $10/min ≈ 0.75 · $1K/min ≈ 1.45 · $10K/min = 1.8
    f_buy = max(0.4, min(1.6, 0.6 + _f(bpm) * 0.2)) if bpm is not None else 0.8
    f_mom = max(0.4, min(1.5, 1.0 + _f(n.get('d5')) / 30.0))
    f_ewp = {'POSITIVE': 1.15, 'NEUTRAL': 1.0, 'WARNING': 0.8, 'DUMPING': 0.5}.get(li.get('ewp'), 1.0)
    f_judge = max(0.7, min(1.3, _f((weights or {}).get(x.get('mint'), 1.0)) or 1.0))
    import trench_crew as _crew
    f_devil, _objs = _crew.devil_factor(x, devil_strong)   # ⚖ Devil challenges: evidence lowers confidence, it never vetoes
    parts = [('newness', round(f_new, 2)), ('volume velocity', round(f_vol, 2)), ('buyer velocity', round(f_buy, 2)), ('momentum', round(f_mom, 2)),
             ('early wallets', round(f_ewp, 2)), ('judge weight', round(f_judge, 2)), ('devil', f_devil)]
    return round(100 * f_new * f_vol * f_buy * f_mom * f_ewp * f_judge * f_devil, 1), parts


def open_ok(row, min_liq=MIN_LIQ):
    """EXECUTION SAFETY only (not strategy): a live price · traded in the last 5 min · inside the universe (0 < cap < $200K, ≤ 6h old) · a
    pool the keeper can buy into · readable market data (not invalid / malformed / a bot ladder) · not a live collapse or distribution.
    → None or the reason."""
    x = row or {}
    v, n, ch = x.get('vitals') or {}, x.get('nums') or {}, x.get('chart') or {}
    if _f(x.get('px')) <= 0:
        return 'no live price'
    d = dead_now(x)
    if d:
        return d
    if not (0 < _f(v.get('mcap')) < MAX_MCAP):
        return 'outside 0 < cap < $200K'
    if v.get('ageH') is None or _f(v['ageH']) > MAX_AGE_H:
        return 'not ≤ 6h old'
    if _f(n.get('liq') or v.get('liq')) < min_liq:
        return 'pool under the keeper floor (cannot get in and back out)'
    if ch.get('state') in HARD_CHART:
        return f"market data {ch['state'].lower()}"
    import trench_crew as _crew
    if _crew.dev_dumping(x):
        return 'the dev is dumping now'
    nar, why = narrative(x)
    if nar in SKIP_NARRATIVES:
        return f"{nar.lower()}: {why}"
    return None
