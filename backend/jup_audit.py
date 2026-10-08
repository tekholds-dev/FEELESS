"""🧪 Jupiter audit → coin facts, dev CREW read and the coin's VITAL verdict. Pure (no network) + tested.

Why (owner, 2026-10-08: "no new coins, I'm running in circles … the gates need to be broken … add popular crews and bad crews who run
coins … the long horizontal vitals aren't vital enough"): our own holder scan needs ~40 RPC calls for a brand-new coin and only one RPC
lane answered, so ~19 of 271 listed coins were ever scanned and an unscanned coin is never bought. Jupiter's token rows (100 a call,
already fetched for prices) carry an audit for EVERY coin: top-holder %, dev balance %, mint / freeze authority, holder count, the dev
wallet and how many coins that dev launched (devMints) and graduated (devMigrations), plus organic vs bot volume. That is a holder
reading for every coin at once (`lite_intel`) and the crew signal (`crew`).
"""


def _f(v, d=0.0):
    try:
        x = float(v)
        return x if x == x else d
    except (TypeError, ValueError):
        return d


def facts(tok):
    """A Jupiter /tokens/v2 row → plain facts (None = Jupiter did not say)."""
    t = tok or {}
    a = t.get('audit') or {}
    s1 = t.get('stats1h') or {}
    vol = _f(s1.get('buyVolume')) + _f(s1.get('sellVolume'))
    org = _f(s1.get('buyOrganicVolume')) + _f(s1.get('sellOrganicVolume'))
    num = lambda v: None if v is None else _f(v)
    return {'holders': num(t.get('holderCount')), 'top10': num(a.get('topHoldersPercentage')), 'devPct': num(a.get('devBalancePercentage')),
            'devMints': None if a.get('devMints') is None else int(_f(a.get('devMints'))),
            'devGrads': None if a.get('devMigrations') is None else int(_f(a.get('devMigrations'))),
            'dev': t.get('dev'), 'mintOff': a.get('mintAuthorityDisabled'), 'freezeOff': a.get('freezeAuthorityDisabled'),
            'organic': num(t.get('organicScore')), 'organicLabel': t.get('organicScoreLabel'),
            'organicPct': round(org / vol * 100, 1) if vol > 0 else None,
            'traders1h': num(s1.get('numTraders')), 'realBuyers1h': num(s1.get('numOrganicBuyers')),
            'holderChg1h': num(s1.get('holderChange')), 'netBuyers1h': num(s1.get('numNetBuyers')), 'liqChg1h': num(s1.get('liquidityChange')),
            'verified': bool(t.get('isVerified')), 'launchpad': t.get('launchpad')}


# 👥 CREW = the people who run the coin, read from the dev's own launch record (Jupiter counts every coin the dev wallet minted and how
# many graduated). A dev whose coins keep graduating is a crew the market follows; a wallet that has launched hundreds and graduated a
# handful is a serial launcher (most of its coins die fast). It is a READ, never a hard block — $TikTok's dev (1,076 launches, 22
# graduated) still ran +10,000% in an hour.
POPULAR_GRADS, POPULAR_RATE = 3, 0.2
SERIAL_MINTS, SERIAL_RATE = 50, 0.05


def crew(f):
    """→ {'kind': popular | serial | fresh | mixed | unknown, 'icon', 'label', 'why'} from the dev's launch record."""
    m, g = (f or {}).get('devMints'), (f or {}).get('devGrads')
    if m is None:
        return {'kind': 'unknown', 'icon': '❔', 'label': 'crew unknown', 'why': 'Jupiter has no launch record for this dev'}
    g = int(g or 0); rate = g / m if m else 0.0
    rec = f"dev launched {m} coin{'s' if m != 1 else ''}, {g} graduated"
    if g >= POPULAR_GRADS and rate >= POPULAR_RATE:
        return {'kind': 'popular', 'icon': '🔥', 'label': 'popular crew', 'why': f"{rec} ({rate * 100:.0f}%) — their coins tend to make it"}
    if m >= SERIAL_MINTS and rate < SERIAL_RATE:
        return {'kind': 'serial', 'icon': '☠', 'label': 'serial launcher', 'why': f"{rec} ({rate * 100:.1f}%) — most of their coins die; take profit fast"}
    if m <= 3:
        return {'kind': 'fresh', 'icon': '🆕', 'label': 'fresh dev', 'why': f"{rec} — no track record yet"}
    return {'kind': 'mixed', 'icon': '⚪', 'label': 'mixed crew', 'why': f"{rec} ({rate * 100:.0f}%)"}


def lite_intel(f):
    """A holder reading in `token_intel`'s shape from Jupiter's audit — used ONLY when our own RPC scan has not landed (the full scan still
    runs and replaces it). Insiders / bundles are unknown here (None); mint / freeze authority and the dev record ride along."""
    if not f or f.get('top10') is None:
        return None
    return {'top10Pct': round(_f(f['top10']), 2), 'devHoldingPct': None if f.get('devPct') is None else round(_f(f['devPct']), 4),
            'insidersHoldingPct': None, 'bundledWallets': None, 'sniperWallets': None, 'creator': f.get('dev'),
            'holders': f.get('holders'), 'source': 'jupiter', 'jup': f}


def authority_bad(f):
    """Mint or freeze authority still live = the dev can print or freeze — a hard no, whatever else reads well."""
    return bool(f) and (f.get('mintOff') is False or f.get('freezeOff') is False)


def verdict(f, scan=None):
    """🫀 THE VITAL (replaces the long chip row): one verdict + the 3 facts that decide it.
    → {'grade': A–F, 'score': 0–100, 'tone': good|warn|bad, 'word', 'flags': [(icon, text, tone)…≤3], 'bars': {holders, dev, crew, flow}}
    Every part is a reading, never a promise. Unknown = the bar sits at half and says so."""
    f = f or {}; s = scan or {}
    flags, pts = [], 50.0
    if authority_bad(f):
        return {'grade': 'F', 'score': 0, 'tone': 'bad', 'word': 'DEV CAN MINT / FREEZE', 'flags': [('⛔', 'mint or freeze authority still live', 'bad')],
                'organicPct': f.get('organicPct'), 'bars': {'flow': 0, 'growth': 0, 'holders': 0, 'dev': 0, 'crew': 0}}
    top10 = s.get('top10') if s.get('top10') is not None else f.get('top10')
    if top10 is None:
        hb = 0.5
    else:
        hb = max(0.0, min(1.0, (45 - _f(top10)) / 35))
        if _f(top10) >= 35:
            flags.append(('🐋', f"top-10 hold {_f(top10):.0f}%", 'bad'))
        elif _f(top10) <= 18:
            flags.append(('🧩', f"spread — top-10 {_f(top10):.0f}%", 'good'))
    bund = s.get('bundledN')
    ins = s.get('insiders')
    if bund is not None and int(bund) >= 3:
        flags.append(('📦', f"{int(bund)} bundled wallets", 'bad')); hb *= 0.6
    if ins is not None and _f(ins) >= 15:
        flags.append(('🕵', f"insiders {_f(ins):.0f}%", 'bad')); hb *= 0.6
    dev = s.get('dev') if s.get('dev') is not None else f.get('devPct')
    db = 0.5 if dev is None else max(0.0, min(1.0, (10 - _f(dev)) / 10))
    if dev is not None and _f(dev) >= 8:
        flags.append(('👤', f"dev holds {_f(dev):.0f}%", 'bad'))
    c = crew(f)
    cb = {'popular': 1.0, 'mixed': 0.55, 'fresh': 0.5, 'unknown': 0.5, 'serial': 0.15}[c['kind']]
    if c['kind'] in ('popular', 'serial'):
        flags.append((c['icon'], c['label'] + f" ({f.get('devGrads') or 0}/{f.get('devMints')})", 'good' if c['kind'] == 'popular' else 'bad'))
    # 📈 GROWTH (profit signals): holders arriving this hour, real buyers ahead of sellers, and the pool not being drained
    hc, nb, tr, lc = f.get('holderChg1h'), f.get('netBuyers1h'), f.get('traders1h'), f.get('liqChg1h')
    gb = 0.5 if hc is None else max(0.0, min(1.0, 0.3 + _f(hc) / 70))
    if lc is not None and _f(lc) <= -25:
        flags.append(('🩸', f"pool drained {_f(lc):.0f}% this hour", 'bad')); gb *= 0.4
    elif hc is not None and _f(hc) >= 15:
        flags.append(('📈', f"holders +{min(999, _f(hc)):.0f}% this hour", 'good'))
    if nb is not None and _f(tr) >= 100 and _f(nb) / _f(tr) >= 0.4:
        flags.append(('🧲', f"{int(_f(nb)):,} net buyers of {int(_f(tr)):,}", 'good')); gb = min(1.0, gb + 0.15)
    org = f.get('organicPct')
    fb = 0.5 if org is None else max(0.0, min(1.0, _f(org) / 40))
    if org is not None and _f(org) < 8 and _f(f.get('traders1h')) >= 200:
        flags.append(('🤖', f"bots — {_f(org):.0f}% of volume is organic", 'bad'))
    elif org is not None and _f(org) >= 30:
        flags.append(('🌱', f"{_f(org):.0f}% organic volume", 'good'))
    pts = round((hb * 0.3 + db * 0.15 + cb * 0.2 + fb * 0.2 + gb * 0.15) * 100)
    grade = 'A' if pts >= 80 else 'B' if pts >= 65 else 'C' if pts >= 50 else 'D' if pts >= 35 else 'F'
    tone = 'good' if pts >= 65 else 'warn' if pts >= 45 else 'bad'
    word = {'A': 'CLEAN', 'B': 'GOOD', 'C': 'MIXED', 'D': 'RISKY', 'F': 'DANGER'}[grade]
    order = {'bad': 0, 'good': 1, 'warn': 2}
    flags = sorted(flags, key=lambda x: order.get(x[2], 3))[:3]
    return {'grade': grade, 'score': int(pts), 'tone': tone, 'word': word, 'flags': flags, 'crew': c,
            'organicPct': org, 'bars': {'flow': round(fb, 2), 'growth': round(gb, 2), 'holders': round(hb, 2), 'dev': round(db, 2), 'crew': round(cb, 2)}}


# 🎛 THE OWNER'S VITAL FILTER (real card cfg `vitalMin` · `organicMin` · `noSerial`; Coming up + every engine door obeys it). Unknown = not judged.
VITAL_MINS = (0, 35, 50, 65)      # any · D+ · C+ · B+
ORGANIC_MINS = (0, 5, 10, 20, 30)


def filter_why(f, scan=None, cfg=None):
    """None = passes the owner's vital filter, else the reason (shown under Coming up)."""
    c = cfg or {}
    vm, om, ns = int(_f(c.get('vitalMin'))), int(_f(c.get('organicMin'))), bool(c.get('noSerial'))
    if not (vm or om or ns) or not f:
        return None
    v = verdict(f, scan)
    if vm and v['score'] < vm:
        return f"vital {v['grade']} {v['score']} — your filter wants {vm}+"
    if ns and v['crew']['kind'] == 'serial':
        return f"serial launcher ({f.get('devGrads') or 0}/{f.get('devMints')}) — your filter skips them"
    if om and f.get('organicPct') is not None and _f(f['organicPct']) < om:
        return f"{_f(f['organicPct']):.0f}% organic — your filter wants {om}%+"
    return None


# 🗑 TRENCH VITAL — the degen read for brand-new coins (owner: "create your own meta degen vitals for the trench swap"). A coin minutes old has
# no chart and no record, so the plain vital (spread, dev, crew, flow) says little. Two meters decide a trench entry:
#   🔥 HEAT  — is it SENDING right now: 5-min pace vs its hour, buyers' share, holders arriving, net buyers, a green 5 min that is not a
#             vertical candle (> +40% in 5 min = chasing).
#   ☠ RUG   — can it be pulled on you: top-10 / bundles / snipers / insiders, dev share, a serial launcher, bot volume, no site or 𝕏, a
#             draining pool, mint / freeze live, the first 15 minutes.
# CALL = 🔥 SEND IT (heat ≥ 60, rug ≤ 35) · ☠ RUG BAIT (rug ≥ 65) · 🧊 COLD (heat < 35) · 👀 WATCH. A read for a small ticket — never a promise.
def trench_verdict(f, row=None):
    f, r = f or {}, row or {}
    heat_p, rug_p, tags = [], [], []
    v1, v5 = _f(r.get('vol1h')), _f(r.get('vol5m'))
    if v1 > 0 and v5 > 0:
        pace = v5 * 12 / v1
        heat_p.append(min(1.0, pace / 2.5))
        if pace >= 1.5:
            tags.append(('⚡', f"5m pace {pace:.1f}×", 'good'))
        elif pace < 0.5:
            tags.append(('💤', f"5m pace {pace:.1f}× — fading", 'bad'))
    bs = r.get('buyShare')
    if bs is not None:
        heat_p.append(max(0.0, min(1.0, (_f(bs) - 40) / 30)))
    hc = f.get('holderChg1h')
    if hc is not None:
        heat_p.append(max(0.0, min(1.0, _f(hc) / 100)))
        if _f(hc) >= 50:
            tags.append(('👥', f"holders +{min(999, _f(hc)):.0f}%/h", 'good'))
    nb, tr = f.get('netBuyers1h'), f.get('traders1h')
    if nb is not None and _f(tr) >= 50:
        heat_p.append(max(0.0, min(1.0, _f(nb) / _f(tr) / 0.6)))
    c5 = r.get('chg5m')
    if c5 is not None:
        heat_p.append(1.0 if 2 <= _f(c5) <= 25 else 0.6 if 0 <= _f(c5) < 2 else 0.4 if _f(c5) <= 40 else 0.1 if _f(c5) > 40 else 0.15)
        if _f(c5) > 40:
            tags.append(('🧗', f"+{_f(c5):.0f}% in 5m — chasing", 'bad'))
    # ☠ rug side (each part 0–1, worst parts weigh most)
    t10 = r.get('top10') if r.get('top10') is not None else f.get('top10')
    if t10 is not None:
        rug_p.append(max(0.0, min(1.0, (_f(t10) - 15) / 30)))
    for k, cap, lab in (('bundledN', 6, 'bundled'), ('snipersN', 25, 'snipers')):
        if r.get(k) is not None:
            n = int(_f(r[k])); rug_p.append(min(1.0, n / cap))
            if n >= cap / 2:
                tags.append(('🎯' if k == 'snipersN' else '📦', f"{n} {lab}", 'bad'))
    if r.get('insiders') is not None:
        rug_p.append(min(1.0, _f(r['insiders']) / 25))
    dev = r.get('dev') if r.get('dev') is not None else f.get('devPct')
    if dev is not None:
        rug_p.append(min(1.0, _f(dev) / 15))
        if _f(dev) >= 8:
            tags.append(('👤', f"dev holds {_f(dev):.0f}%", 'bad'))
    cw = crew(f)['kind']
    if cw != 'unknown':
        rug_p.append({'serial': 0.8, 'fresh': 0.45, 'mixed': 0.35, 'popular': 0.1}[cw])
        if cw == 'popular':
            tags.append(('🔥', f"popular crew {f.get('devGrads')}/{f.get('devMints')}", 'good'))
        elif cw == 'serial':
            tags.append(('☠', f"serial launcher {f.get('devGrads') or 0}/{f.get('devMints')}", 'bad'))
    org = f.get('organicPct')
    if org is not None:
        rug_p.append(0.7 if _f(org) < 3 else 0.4 if _f(org) < 10 else 0.1)
    if not (r.get('site') or r.get('x')) and ('site' in r or 'x' in r):
        rug_p.append(0.6); tags.append(('🙈', 'no site or 𝕏', 'bad'))
    elif r.get('site') and r.get('x'):
        tags.append(('🌐', 'site + 𝕏', 'good'))
    if f.get('liqChg1h') is not None and _f(f['liqChg1h']) <= -25:
        rug_p.append(1.0); tags.append(('🩸', f"pool {_f(f['liqChg1h']):.0f}%/h", 'bad'))
    age = r.get('ageH')
    if age is not None and _f(age) < 0.25:
        rug_p.append(0.6); tags.append(('⏱', f"{max(1, round(_f(age) * 60))}m old", 'bad'))
    if authority_bad(f):
        rug_p.append(1.0); tags.insert(0, ('⛔', 'dev can mint / freeze', 'bad'))
    heat = round(sum(heat_p) / len(heat_p) * 100) if heat_p else None
    worst = sorted(rug_p, reverse=True)
    rug = round((sum(worst[:3]) / min(3, len(worst)) * 0.6 + sum(worst) / len(worst) * 0.4) * 100) if worst else None
    if authority_bad(f) or (rug is not None and rug >= 65):
        call = ('☠', 'RUG BAIT', 'bad')
    elif heat is not None and heat >= 60 and (rug is None or rug <= 35):
        call = ('🔥', 'SEND IT', 'good')
    elif heat is not None and heat < 35:
        call = ('🧊', 'COLD', 'warn')
    else:
        call = ('👀', 'WATCH', 'warn')
    order = {'bad': 0, 'good': 1}
    return {'heat': heat, 'rug': rug, 'call': call, 'tags': sorted(tags, key=lambda x: order.get(x[2], 2))[:4]}


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 🎢 CURVE READ + 🧲 DIP READ + 💀 DEAD CHECK (owner, 2026-10-08: "love SEND IT — more like that for fast volume on the curve, better vitals for
# dips, and Coming up coins shouldn't be dead"). Same shape as the trench read: two meters → one call → ≤ 4 tags. Hand-set weights; every call is
# scored on its own 1-hour record (`_call_track`) before the engine leans on it. A read, never a promise.
DEAD_VOL1H, DEAD_TX1H = 3000.0, 20   # under $3K traded in the hour, or under 20 trades, or nothing in the last 5 min = dead


def dead_why(r):
    """None = alive, else why it is dead (a coin nobody trades can't be sold either)."""
    r = r or {}
    v1, v5, tx = r.get('vol1h'), r.get('vol5m'), r.get('txns1h')
    if v5 is not None and _f(v5) <= 0 and v1 is not None:
        return 'dead — nothing traded in 5 min'
    if v1 is not None and _f(v1) < DEAD_VOL1H:
        return f"dead — ${_f(v1):,.0f} traded in the hour"
    if tx is not None and int(_f(tx)) < DEAD_TX1H:
        return f"dead — {int(_f(tx))} trades in the hour"
    return None


def _call(word, icon, tone):
    return (icon, word, tone)


def curve_verdict(f, row=None):
    """🎢 A coin still on its launch curve: 🎢 BOND (how far along the curve) × ⚡ PACE (curve speed + 5-min volume pace + buyers).
    Calls: 🎢 BOND RUN (≥ 70% along, pace ≥ 60) · 🚀 EARLY RUSH (< 40% along, pace ≥ 70, buyers ≥ 60%) · 🧨 DUMPING (5m ≤ −15% or sellers in
    charge) · ⏳ SLOW CURVE (pace < 35) · 👀 WATCH. Rug risk from the trench read still rides along (☠ RUG BAIT wins)."""
    f, r = f or {}, row or {}
    cp = r.get('curvePct')
    bond = None if cp is None else max(0, min(100, round(_f(cp))))
    parts, tags = [], []
    sp = r.get('curveSpeed')   # curve % gained per 10 min (runner board history)
    if sp is not None:
        parts.append(max(0.0, min(1.0, _f(sp) / 15)))
        if _f(sp) >= 8:
            tags.append(('🎢', f"curve +{_f(sp):.0f}%/10m", 'good'))
    v1, v5 = _f(r.get('vol1h')), _f(r.get('vol5m'))
    if v1 > 0 and v5 > 0:
        pace = v5 * 12 / v1; parts.append(min(1.0, pace / 2.5))
        if pace >= 1.5:
            tags.append(('⚡', f"5m pace {pace:.1f}×", 'good'))
    bs = r.get('buyShare')
    if bs is not None:
        parts.append(max(0.0, min(1.0, (_f(bs) - 40) / 30)))
    pace_v = round(sum(parts) / len(parts) * 100) if parts else None
    if bond is not None and bond >= 70:
        tags.insert(0, ('🔔', f"{bond}% to bond", 'good'))
    rug = trench_verdict(f, r)
    c5 = r.get('chg5m')
    if rug['call'][1] == 'RUG BAIT':
        call = rug['call']
    elif (c5 is not None and _f(c5) <= -15) or (bs is not None and _f(bs) < 40):
        call = _call('DUMPING', '🧨', 'bad'); tags.insert(0, ('🧨', f"{_f(c5):+.0f}% in 5m" if c5 is not None else 'sellers in charge', 'bad'))
    elif bond is not None and bond >= 70 and pace_v is not None and pace_v >= 60:
        call = _call('BOND RUN', '🎢', 'good')
    elif bond is not None and bond < 40 and pace_v is not None and pace_v >= 70 and (bs is None or _f(bs) >= 60):
        call = _call('EARLY RUSH', '🚀', 'good')
    elif pace_v is not None and pace_v < 35:
        call = _call('SLOW CURVE', '⏳', 'warn')
    else:
        call = _call('WATCH', '👀', 'warn')
    order = {'bad': 0, 'good': 1}
    return {'kind': 'curve', 'call': call, 'meters': [['🎢 BOND', bond], ['⚡ PACE', pace_v]], 'rug': rug['rug'],
            'tags': sorted(tags + [t for t in rug['tags'] if t[2] == 'bad'][:1], key=lambda x: order.get(x[2], 2))[:4]}


def is_dip(r):
    r = r or {}
    return (r.get('chg1h') is not None and _f(r['chg1h']) <= -10) or _f(r.get('cPull')) >= 20 or \
        (r.get('chg6h') is not None and _f(r['chg6h']) <= -25) or (r.get('chg24h') is not None and _f(r['chg24h']) <= -35)


def dip_verdict(f, row=None):
    """🧲 A coin well off its high: 🧲 BOUNCE (5 min turning up, buyers back, holders still arriving, net buyers) × 🔪 KNIFE (still falling,
    sellers in charge, holders leaving, pool draining). Calls: 🧲 BUY THE DIP (bounce ≥ 60, knife ≤ 40) · 🔪 FALLING KNIFE (knife ≥ 60) ·
    💤 DEAD DIP (dead) · 👀 WATCH."""
    f, r = f or {}, row or {}
    up, dn, tags = [], [], []
    c5, c1, bs = r.get('chg5m'), r.get('chg1h'), r.get('buyShare')
    deep = max(_f(r.get('cPull')), -_f(c1) if c1 is not None else 0, -_f(r.get('chg6h')) if r.get('chg6h') is not None else 0)
    if deep > 0:
        tags.append(('📉', f"{deep:.0f}% off", 'warn'))
    if c5 is not None:
        up.append(max(0.0, min(1.0, (_f(c5) + 1) / 6))); dn.append(max(0.0, min(1.0, -_f(c5) / 8)))
        if _f(c5) >= 2:
            tags.append(('↗', f"turning +{_f(c5):.0f}% in 5m", 'good'))
    if bs is not None:
        up.append(max(0.0, min(1.0, (_f(bs) - 45) / 20))); dn.append(max(0.0, min(1.0, (55 - _f(bs)) / 20)))
    hc = f.get('holderChg1h')
    if hc is not None:
        up.append(max(0.0, min(1.0, 0.4 + _f(hc) / 30))); dn.append(max(0.0, min(1.0, -_f(hc) / 10)))
        if _f(hc) < -3:
            tags.append(('🚪', f"holders {_f(hc):.0f}%/h", 'bad'))
    nb, tr = f.get('netBuyers1h'), f.get('traders1h')
    if nb is not None and _f(tr) >= 50:
        up.append(max(0.0, min(1.0, _f(nb) / _f(tr) / 0.5)))
    if f.get('liqChg1h') is not None and _f(f['liqChg1h']) <= -20:
        dn.append(1.0); tags.append(('🩸', f"pool {_f(f['liqChg1h']):.0f}%/h", 'bad'))
    bounce = round(sum(up) / len(up) * 100) if up else None
    knife = round(sum(dn) / len(dn) * 100) if dn else None
    dw = dead_why(r)
    if dw:
        call = _call('DEAD DIP', '💤', 'bad'); tags.insert(0, ('💤', dw.replace('dead — ', ''), 'bad'))
    elif authority_bad(f):
        call = _call('RUG BAIT', '☠', 'bad')
    elif knife is not None and knife >= 60:
        call = _call('FALLING KNIFE', '🔪', 'bad')
    elif bounce is not None and bounce >= 60 and (knife is None or knife <= 40):
        call = _call('BUY THE DIP', '🧲', 'good')
    else:
        call = _call('WATCH', '👀', 'warn')
    order = {'bad': 0, 'good': 1}
    return {'kind': 'dip', 'call': call, 'meters': [['🧲 BOUNCE', bounce], ['🔪 KNIFE', knife]], 'tags': sorted(tags, key=lambda x: order.get(x[2], 2))[:4]}


def pick_read(f, row=None):
    """The read that fits this coin: 🎢 on its curve → curve · 🧲 well off its high → dip · new (< 6h) / trench → trench (SEND IT) · else None."""
    r = row or {}
    if r.get('curvePct') is not None and _f(r['curvePct']) < 100:
        return curve_verdict(f, r)
    if is_dip(r):
        return dip_verdict(f, r)
    if r.get('trench') or r.get('trenchOnly') or (r.get('ageH') is not None and _f(r['ageH']) < 6):
        t = trench_verdict(f, r)
        return {**t, 'kind': 'trench', 'meters': [['🔥 HEAT', t['heat']], ['☠ RUG', t['rug']]]}
    return None


# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
# 🚀 MOVER · 🌊 FLOW · 🐋 TREND — one read per pick-list category (owner, 2026-10-08: "all other categories have meta data no other has —
# loving BOND RUN and it being measured"). Same shape as every read: two meters → one call → ≤ 4 tags; each call scored on its own record.
def _clip(x):
    return max(0.0, min(1.0, x))


def mover_verdict(f, row=None):
    """🚀 A coin running on the hour: 🚀 MOMENTUM (1h move, 5 min still going, buyers, pace) × 🧯 BLOW-OFF (5 min turning down after a
    huge hour, sellers taking over, pace fading, a vertical 5-min candle). BREAKOUT · BLOW-OFF TOP · COOLING · WATCH."""
    f, r = f or {}, row or {}
    c1, c5, bs = r.get('chg1h'), r.get('chg5m'), r.get('buyShare')
    v1, v5 = _f(r.get('vol1h')), _f(r.get('vol5m'))
    pace = v5 * 12 / v1 if v1 > 0 and v5 > 0 else None
    up, top, tags = [], [], []
    if c1 is not None:
        up.append(_clip(_f(c1) / 60)); top.append(_clip((_f(c1) - 150) / 300))
        tags.append(('🚀', f"{_f(c1):+.0f}% on the hour", 'good' if _f(c1) > 0 else 'bad'))
    if c5 is not None:
        up.append(_clip((_f(c5) + 1) / 8))
        top.append(_clip(-_f(c5) / 10) if c1 is not None and _f(c1) > 50 else 0.0)
        if _f(c5) > 40:
            top.append(1.0); tags.append(('🧗', f"+{_f(c5):.0f}% in 5m — vertical", 'bad'))
    if bs is not None:
        up.append(_clip((_f(bs) - 45) / 25)); top.append(_clip((50 - _f(bs)) / 15))
    if pace is not None:
        up.append(_clip(pace / 2)); top.append(_clip((0.6 - pace) / 0.6))
        if pace < 0.6:
            tags.append(('💤', f"pace {pace:.1f}× — fading", 'bad'))
    mom = round(sum(up) / len(up) * 100) if up else None
    blow = round(sum(top) / len(top) * 100) if top else None
    if authority_bad(f):
        call = ('☠', 'RUG BAIT', 'bad')
    elif blow is not None and blow >= 55:
        call = ('🧯', 'BLOW-OFF TOP', 'bad')
    elif mom is not None and mom >= 60 and (blow is None or blow <= 35):
        call = ('🚀', 'BREAKOUT', 'good')
    elif mom is not None and mom < 35:
        call = ('🧊', 'COOLING', 'warn')
    else:
        call = ('👀', 'WATCH', 'warn')
    order = {'bad': 0, 'good': 1}
    return {'kind': 'mover', 'call': call, 'meters': [['🚀 MOMENTUM', mom], ['🧯 BLOW-OFF', blow]], 'tags': sorted(tags, key=lambda x: order.get(x[2], 2))[:4]}


def flow_verdict(f, row=None):
    """🌊 A busy coin: 🌊 SURGE (5-min pace vs its hour, trades per hour, real buyers) × 🧪 WASH (bot share of volume, few real buyers for the
    trades, the same wallets trading). VOLUME SURGE · WASH TRADED · DRYING UP · WATCH."""
    f, r = f or {}, row or {}
    v1, v5, tx = _f(r.get('vol1h')), _f(r.get('vol5m')), r.get('txns1h')
    pace = v5 * 12 / v1 if v1 > 0 and v5 > 0 else None
    sg, ws, tags = [], [], []
    if pace is not None:
        sg.append(_clip(pace / 2.2))
        tags.append(('🌊', f"5m pace {pace:.1f}×", 'good' if pace >= 1.3 else 'bad' if pace < 0.5 else 'warn'))
    if tx is not None:
        sg.append(_clip(int(_f(tx)) / 1500))
    org = f.get('organicPct')
    if org is not None:
        ws.append(_clip((15 - _f(org)) / 15))
        if _f(org) < 5:
            tags.append(('🤖', f"{_f(org):.0f}% organic", 'bad'))
    rb, tr = f.get('realBuyers1h'), f.get('traders1h')
    if rb is not None and _f(tr) >= 100:
        share = _f(rb) / _f(tr); ws.append(_clip((0.08 - share) / 0.08)); sg.append(_clip(share / 0.2))
        tags.append(('🧍', f"{int(_f(rb))} real buyers / {int(_f(tr)):,} traders", 'good' if share >= 0.1 else 'bad'))
    surge = round(sum(sg) / len(sg) * 100) if sg else None
    wash = round(sum(ws) / len(ws) * 100) if ws else None
    dw = dead_why(r)
    if dw or (pace is not None and pace < 0.35):
        call = ('🏜', 'DRYING UP', 'bad')
    elif wash is not None and wash >= 65:
        call = ('🧪', 'WASH TRADED', 'bad')
    elif surge is not None and surge >= 60 and (wash is None or wash <= 40):
        call = ('🌊', 'VOLUME SURGE', 'good')
    else:
        call = ('👀', 'WATCH', 'warn')
    order = {'bad': 0, 'good': 1}
    return {'kind': 'flow', 'call': call, 'meters': [['🌊 SURGE', surge], ['🧪 WASH', wash]], 'tags': sorted(tags, key=lambda x: order.get(x[2], 2))[:4]}


def trend_verdict(f, row=None):
    """🐋 A major / stock / deep pool: 📈 TREND (5m · 1h · 6h · 24h all pointing the same way, buyers) × 🌀 CHOP (the timeframes disagree,
    thin volume for its size). TREND UP · TREND DOWN · CHOP · WATCH."""
    r = row or {}
    ch = [_f(r[k]) for k in ('chg5m', 'chg1h', 'chg6h', 'chg24h') if r.get(k) is not None]
    tags = []
    if not ch:
        return {'kind': 'trend', 'call': ('👀', 'WATCH', 'warn'), 'meters': [['📈 TREND', None], ['🌀 CHOP', None]], 'tags': []}
    ups = sum(1 for x in ch if x > 0); dns = sum(1 for x in ch if x < 0)
    agree = max(ups, dns) / len(ch)
    strength = _clip(sum(abs(x) for x in ch[1:] or ch) / (len(ch[1:] or ch) * 8))
    trend = round((agree * 0.6 + strength * 0.4) * 100)
    vol, mc = _f(r.get('vol24h') or r.get('vol1h', 0) * 24), _f(r.get('mcap'))
    turn = vol / mc if mc > 0 and vol > 0 else None
    chop = round((1 - agree) * 100 * (1.2 if turn is not None and turn < 0.02 else 1))
    chop = min(100, chop)
    tags.append(('🧭', ' · '.join(f"{lab} {x:+.1f}%" for lab, x in zip(('5m', '1h', '6h', '24h'), [r.get(k) for k in ('chg5m', 'chg1h', 'chg6h', 'chg24h')]) if x is not None)[:60], 'warn'))
    if turn is not None and turn < 0.02:
        tags.append(('🐢', f"{turn * 100:.1f}% of its cap traded", 'bad'))
    if agree >= 0.75 and ups > dns and trend >= 55:
        call = ('📈', 'TREND UP', 'good')
    elif agree >= 0.75 and dns > ups and trend >= 55:
        call = ('📉', 'TREND DOWN', 'bad')
    elif chop >= 45:
        call = ('🌀', 'CHOP', 'warn')
    else:
        call = ('👀', 'WATCH', 'warn')
    return {'kind': 'trend', 'call': call, 'meters': [['📈 TREND', trend], ['🌀 CHOP', chop]], 'tags': tags[:4]}


LENS_READ = {'movers': 'mover', 'ptrend': 'mover', 'volume': 'flow', 'majors': 'trend', 'stocks': 'trend', 'risers': 'trend', 'bottom': 'dip',
             'pump': 'auto', 'trench': 'trench', 'fresh': 'auto', 'arena': 'auto'}


def read_for_lens(lens, f, row=None):
    """The category's OWN read. A coin on its launch curve always gets the curve read (that is what matters most on the curve)."""
    r = row or {}
    if r.get('curvePct') is not None and _f(r['curvePct']) < 100:
        return curve_verdict(f, r)
    kind = LENS_READ.get(lens, 'auto')
    if kind == 'mover':
        return mover_verdict(f, r)
    if kind == 'flow':
        return flow_verdict(f, r)
    if kind == 'trend':
        return trend_verdict(f, r)
    if kind == 'dip':
        return dip_verdict(f, r)
    if kind == 'trench':
        t = trench_verdict(f, r)
        return {**t, 'kind': 'trench', 'meters': [['🔥 HEAT', t['heat']], ['☠ RUG', t['rug']]]}
    return pick_read(f, r)
