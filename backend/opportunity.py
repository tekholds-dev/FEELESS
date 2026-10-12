"""🎯 OPPORTUNITY: RANK, DON'T VETO (owner, 2026-10-11: "make them more decisive without removing hard safety").

Every coin the desk read goes through ONE hard-safety check (`hard_fail`): a genuine danger is a NO. Everything else is a SCORE 0–100 from
cited parts (momentum, acceleration, structure, liquidity, holders, volume, freshness, identity, data) minus penalties (chop, extension,
thin pool, stale data, identity doubt, weak holders, a failed setup, Devil's warnings) → a TIER:
  A (≥ 65) full Warden size · B (45–65) 75% · C (25–45) 50% · below 25 = not worth a seat.
The seats choose the best AVAILABLE valid opportunity instead of waiting for a perfect coin. A ranking, never a promise. Pure, tested."""

TIER_A, TIER_B, TIER_C = 65.0, 45.0, 25.0
TIER_STOP = {'A': 25.0, 'B': 18.0, 'C': 12.0}   # 🛑 the stop CEILING per tier (Reaper): 6h on the real card — 9 'bought into a fall' losses at −23…−37% were 3/4 of all the loss
TIER_SIZE = {'A': 1.0, 'B': 0.75, 'C': 0.5}   # on the Warden's own steps (1 · .75 · .5 · .25): B = 75% of a seat, C = 50%
MAX_MCAP = 200_000.0             # 🎯 the hard universe for NEW entries: live market cap under $200K (owner's spec, 2026-10-11) — mirrors agents.AGENT_MAX_MCAP
MIN_LIQ = 8_000.0                # mirrors agents.CONTROL_MIN_LIQ (a test keeps them equal) = the keeper's trench floor
FALL_HARD = -15.0                # a −15% 5-minute candle is a knife: NO · −8…−15 is a heavy penalty
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
    if v.get('mcap') is not None and _f(v['mcap']) >= mcap_cap:
        return f"market cap ${_f(v['mcap']) / 1e6:.1f}M ≥ ${mcap_cap / 1e6:.0f}M"
    liq = _f(n.get('liq') or v.get('liq'))
    if liq < min_liq:
        return f'pool ${liq / 1000:.0f}K under ${min_liq / 1000:.0f}K'
    if _f(v.get('rug')) >= 50:
        return f"rug meter {_f(v['rug']):.0f}"
    hd = [o[0] for o in x.get('objs') or [] if o and o[0] in HARD_DEVIL] + ([x['drule']] if x.get('drule') in HARD_DEVIL else [])
    if hd:
        return f'Devil hard veto: {hd[0]}'
    li = x.get('li') or {}
    if li.get('phase') == 'DISTRIBUTION':   # 🕵 exit-liquidity FOMO: up big while the early wallets sell into it — we would be their exit
        return 'distribution — ' + '; '.join((li.get('phaseWhy') or [])[:2])
    if li.get('press') == 'HIGH':
        return 'early wallets unloading — ' + str(li.get('pressWhy'))
    if ch.get('state') in HARD_CHART:
        return f"chart {ch['state']}"
    d5 = _f(n.get('d5'))
    if d5 > VERTICAL:
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
    add('liquidity', 10 if liq >= 100_000 else 6 if liq >= 40_000 else 2 if liq >= 20_000 else -4)
    t10 = v.get('top10')
    if t10 is not None:
        add('holders', 6 if _f(t10) < 20 else 0 if _f(t10) < 30 else -8)
    vol = _f(v.get('vol1h'))
    add('fresh volume', 8 if vol >= 200_000 else 5 if vol >= 50_000 else 2 if vol >= 10_000 else -4)
    if age is not None:
        add('launch freshness', 6 if _f(age) <= 6 else 3 if _f(age) <= 24 else 0)
    buy = n.get('buy')
    if buy is not None:
        add('buyers', max(-8, min(6, (_f(buy) - 52) * 0.6)))
    if x.get('social') or v.get('site') or v.get('x'):
        add('identity', 3)
    q = (ch.get('q') or {}).get('state')
    add('data', 4 if q in ('TRUSTED', 'USABLE_WITH_CAUTION') else -6 if q in ('STALE', 'SPARSE', 'NO_REAL_CANDLES') else 0)
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
